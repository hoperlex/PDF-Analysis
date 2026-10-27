"""The statements the batch operations add to those of the upload (`CMP-INGEST-02`; migration ``0038``).

Every statement is written out (``docs/program/P02_SEAMS.md`` section 3.5: no base repository, no generic CRUD). The
database owns the edges between states and the columns that never change; the use cases check the state first so that
the refusal a caller reads is a typed ``conflict``, not a driver error. What this module reads and writes are the
batch's own five tables; ``comparison_work`` is reached through the queue's public repository only.

The statements of ``CMP-INGEST-01`` (:class:`~auditmanager.ingest.comparison_pdf.public.ComparisonUploadRepository`)
are reused as they are; these are the ones it does not have: the listing, the cancel's four updates, the pause flag,
the release mark of a set and the tokens of the uploads a cancel leaves open in the store.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.ingest.comparison_batch.rules import REASON_BATCH_CANCELLED
from auditmanager.ingest.comparison_pdf.repository import UploadRow

__all__ = ["ComparisonBatchRepository"]

#: Sets that a cancel leaves out. ``done`` keeps its versions and ``excluded`` is already out; the transient ``ready``
#: and ``admitting`` are never seen at rest (a confirmation holds the batch's lock for its whole transaction).
_CANCELLED_SET_STATES: Final[tuple[str, ...]] = (
    "uploading", "reading", "needs_confirmation", "ready", "failed",
)

_UPLOAD_COLUMNS = (
    "comparison_upload_id, project_uid, state, declared_files, declared_bytes, declared_pages, "
    "part_size_bytes, pause_requested, actor_user_uid, actor_label, command_id, created_at, updated_at"
)


def _upload(row: Any) -> UploadRow:
    values = tuple(row)
    return UploadRow(
        upload_id=values[0], project_uid=values[1], state=values[2], declared_files=int(values[3]),
        declared_bytes=int(values[4]), declared_pages=int(values[5]), part_size_bytes=int(values[6]),
        pause_requested=bool(values[7]), actor_user_uid=values[8], actor_label=values[9],
        command_id=values[10], created_at=values[11], updated_at=values[12],
    )


class ComparisonBatchRepository:
    """Stateless; every method takes the caller's session and never commits."""

    __slots__ = ()

    # -- the listing -----------------------------------------------------------------------------------

    def list_uploads(
        self, session: Session, project_uid: str, *, after: tuple[datetime, str] | None, limit: int
    ) -> tuple[UploadRow, ...]:
        """The project's batches, newest first. ``after`` is the ``(created_at, id)`` of the last row of the
        previous page (a keyset: no offset, no row number, so a batch created meanwhile never shifts a page)."""
        rows = session.execute(
            text(
                f"SELECT {_UPLOAD_COLUMNS} FROM comparison_upload WHERE project_uid = :project "
                "AND (CAST(:after_at AS timestamptz) IS NULL "
                "     OR (created_at, comparison_upload_id) < (CAST(:after_at AS timestamptz), CAST(:after_id AS text))) "
                "ORDER BY created_at DESC, comparison_upload_id DESC LIMIT :limit"
            ),
            {
                "project": project_uid,
                "after_at": None if after is None else after[0],
                "after_id": None if after is None else after[1],
                "limit": limit,
            },
        ).all()
        return tuple(_upload(row) for row in rows)

    # -- pause and resume ------------------------------------------------------------------------------

    def set_pause(self, session: Session, upload_id: str, *, to_state: str, pause_requested: bool) -> None:
        """``processing`` to ``paused`` or back, with the pause flag in step (the flag is read by nothing else)."""
        session.execute(
            text(
                "UPDATE comparison_upload SET state = :state, pause_requested = :flag, "
                "updated_at = clock_timestamp() WHERE comparison_upload_id = :id"
            ),
            {"id": upload_id, "state": to_state, "flag": pause_requested},
        )

    # -- cancel ----------------------------------------------------------------------------------------

    def cancel_rows(self, session: Session, upload_id: str) -> dict[str, int]:
        """The database side of «Отменить пакет», in the order that keeps every guard satisfied.

        1. a file that never completed (``declared``, ``uploading``) is ``failed`` with ``batch_cancelled``; a
           ``verified`` file, whose bytes are published, is never touched, and a file already ``failed`` keeps its
           own reason;
        2. the parts that were declared or staged are ``aborted`` (a ``completed`` part belongs to a published file);
        3. every set that has not made versions is ``excluded`` (a ``done`` set keeps its document and versions), so a
           confirmation that arrives late is refused as ``comparison_set_state``;
        4. the batch is ``cancelled`` (terminal: it leaves the active states, which frees the account's slot).

        Nothing here deletes a row, a version or a blob.
        """
        files = session.execute(
            text(
                "UPDATE comparison_upload_file SET state = 'failed', failure_reason = :reason, "
                "updated_at = clock_timestamp() WHERE comparison_upload_id = :id "
                "AND state IN ('declared', 'uploading')"
            ),
            {"id": upload_id, "reason": REASON_BATCH_CANCELLED},
        ).rowcount
        parts = session.execute(
            text(
                "UPDATE comparison_upload_part SET state = 'aborted', updated_at = clock_timestamp() "
                "WHERE state IN ('declared', 'staged') AND comparison_upload_file_id IN ("
                "  SELECT comparison_upload_file_id FROM comparison_upload_file WHERE comparison_upload_id = :id)"
            ),
            {"id": upload_id},
        ).rowcount
        sets = session.execute(
            text(
                "UPDATE comparison_upload_set SET state = 'excluded', failure_reason = NULL, "
                "terminal_at = clock_timestamp(), updated_at = clock_timestamp() "
                "WHERE comparison_upload_id = :id AND state = ANY(:states)"
            ),
            {"id": upload_id, "states": list(_CANCELLED_SET_STATES)},
        ).rowcount
        session.execute(
            text(
                "UPDATE comparison_upload SET state = 'cancelled', pause_requested = false, "
                "updated_at = clock_timestamp(), terminal_at = clock_timestamp() WHERE comparison_upload_id = :id"
            ),
            {"id": upload_id},
        )
        return {"files": int(files), "parts": int(parts), "sets": int(sets)}

    def open_tokens(self, session: Session, upload_id: str) -> tuple[str, ...]:
        """The multipart tokens of the batch's files that were never verified: the uploads a cancel (or an
        abandonment) may have left open in the store. A verified file's upload is consumed and its blob published;
        it is never named here."""
        rows = session.execute(
            text(
                "SELECT multipart_token FROM comparison_upload_file WHERE comparison_upload_id = :id "
                "AND multipart_token IS NOT NULL AND state <> 'verified' ORDER BY comparison_upload_file_id"
            ),
            {"id": upload_id},
        ).all()
        return tuple(str(row[0]) for row in rows)

    def idle_seconds(self, session: Session, upload_id: str) -> float:
        """Seconds since the batch last changed, on the database's clock."""
        value = session.execute(
            text(
                "SELECT extract(epoch FROM clock_timestamp() - updated_at) FROM comparison_upload "
                "WHERE comparison_upload_id = :id"
            ),
            {"id": upload_id},
        ).scalar_one()
        return float(value)

    # -- sets ------------------------------------------------------------------------------------------

    def count_open_sets(self, session: Session, upload_id: str) -> int:
        """Sets that count toward the limit of decision 9 once a retry would admit one more: every set that is
        neither ``failed`` nor ``excluded``."""
        return int(
            session.execute(
                text(
                    "SELECT count(*) FROM comparison_upload_set WHERE comparison_upload_id = :id "
                    "AND state NOT IN ('failed', 'excluded')"
                ),
                {"id": upload_id},
            ).scalar_one()
        )

    def mark_set_released(self, session: Session, set_id: str, *, work: Mapping[str, str]) -> None:
        """Record that the set's page profiles have been put on the queue: ``proposal.processing.work`` maps each
        version to the item that carries it. The mark is what stops a second release (the hook and the drive both
        ask); the proposal is not a frozen column."""
        session.execute(
            text(
                "UPDATE comparison_upload_set SET proposal = jsonb_set(proposal, '{processing}', "
                "CAST(:mark AS jsonb), true), updated_at = clock_timestamp() "
                "WHERE comparison_upload_set_id = :id"
            ),
            {"id": set_id, "mark": json.dumps({"work": dict(work)}, sort_keys=True)},
        )

    def record_exclusion(self, session: Session, set_id: str, *, user_uid: str) -> None:
        """Who left the set out, kept in the set's own record beside what it held."""
        session.execute(
            text(
                "UPDATE comparison_upload_set SET proposal = jsonb_set(proposal, '{exclusion}', "
                "CAST(:note AS jsonb), true), updated_at = clock_timestamp() WHERE comparison_upload_set_id = :id"
            ),
            {"id": set_id, "note": json.dumps({"by": user_uid})},
        )


def released(set_proposal: Mapping[str, Any]) -> bool:
    """Whether the set's profiles have been put on the queue."""
    return "processing" in set_proposal


def confirmed_versions(set_proposal: Mapping[str, Any]) -> Sequence[str]:
    """The versions a confirmed set made, in the confirmed order."""
    confirmed = set_proposal.get("confirmed")
    if not isinstance(confirmed, Mapping):
        return ()
    files = confirmed.get("files", ())
    ordered = sorted(files, key=lambda item: int(item["position"]))
    return tuple(str(item["version_uid"]) for item in ordered)
