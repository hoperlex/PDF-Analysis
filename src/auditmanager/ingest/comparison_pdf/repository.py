"""Persistence of a comparison upload: the batch, its sets, its files and their parts (migration ``0038``).

Every statement is written out (``docs/program/P02_SEAMS.md`` section 3.5: no base repository, no generic CRUD).
The database is the owner of the state: the edges between states, the columns that never change, the write-once
token and blob reference and the part-for-a-file-with-no-token refusal are triggers and constraints of ``0038``;
this module never asks them to be repeated and never works around one. A statement that would move a state along
an edge the migration does not declare is refused by the database with ``AM001``; the use cases check the state
first, so the refusal the caller reads is a typed ``conflict`` and not a driver error.

**What this module does not write.** ``excluded`` and ``cancelled`` states, ``paused``/``processing`` and the retry
of a failed set are `CMP-INGEST-02`'s (the batch operations over comparison work). The states written here are
the ones this lane's operations move through: ``uploading``, ``proposed`` and ``completed`` of a batch;
``uploading``, ``reading``, ``needs_confirmation``, ``ready``, ``admitting``, ``done`` and ``failed`` of a set;
``declared``, ``uploading``, ``verified`` and ``failed`` of a file; ``declared``, ``staged`` and ``completed`` of a
part.

The file's token is minted by the caller (``storage.public.new_multipart_token``) and persisted here **before** the
first part exists; this module never calls the store.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import new_ulid

__all__ = [
    "ACTIVE_BATCH_STATES",
    "ComparisonUploadRepository",
    "FileRow",
    "OrderRow",
    "PartRow",
    "SetRow",
    "UploadRow",
    "new_file_id",
    "new_order_id",
    "new_set_id",
    "new_upload_id",
]

#: A batch is *active* while a person can still add to it, confirm it or wait for it: ``uploading``,
#: ``proposed``, ``processing``, ``paused``. ``completed`` and ``cancelled`` are the terminal states.
ACTIVE_BATCH_STATES: Final[tuple[str, ...]] = ("uploading", "proposed", "processing", "paused")
#: The advisory lock every batch creation takes first, so two requests cannot both pass the count of active
#: batches (``text`` hashed by the server; the key is this string and nothing else uses it).
_ACTIVE_LOCK_KEY: Final[str] = "comparison_upload:active"

_UPLOAD_COLUMNS = (
    "comparison_upload_id, project_uid, state, declared_files, declared_bytes, declared_pages, "
    "part_size_bytes, pause_requested, actor_user_uid, actor_label, command_id, created_at, updated_at, "
    "compare_after_preparation"
)
_SET_COLUMNS = (
    "comparison_upload_set_id, comparison_upload_id, state, designation, existing_document_uid, "
    "document_uid, project_stage, section_code, proposal, failure_reason, confirmed_by_user_uid, "
    "confirmed_at, created_at, updated_at"
)
_FILE_COLUMNS = (
    "comparison_upload_file_id, comparison_upload_id, set_id, display_name, declared_size_bytes, "
    "declared_sha256, declared_page_count, state, multipart_token, blob_id, failure_reason, created_at, "
    "updated_at"
)


def new_upload_id() -> str:
    return f"cbt_{new_ulid()}"


def new_set_id() -> str:
    return f"cus_{new_ulid()}"


def new_file_id() -> str:
    return f"cuf_{new_ulid()}"


def new_order_id() -> str:
    return f"cvo_{new_ulid()}"


@dataclass(frozen=True, slots=True)
class UploadRow:
    upload_id: str
    project_uid: str
    state: str
    declared_files: int
    declared_bytes: int
    declared_pages: int
    part_size_bytes: int
    pause_requested: bool
    actor_user_uid: str
    actor_label: str
    command_id: str
    created_at: datetime
    updated_at: datetime
    #: `CMP-SERIES-01`: «После подготовки сравнить все соседние версии» -- the flag the batch was declared with.
    compare_after_preparation: bool = False


@dataclass(frozen=True, slots=True)
class SetRow:
    set_id: str
    upload_id: str
    state: str
    designation: str | None
    existing_document_uid: str | None
    document_uid: str | None
    project_stage: str | None
    section_code: str | None
    proposal: Mapping[str, Any]
    failure_reason: str | None
    confirmed_by_user_uid: str | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FileRow:
    file_id: str
    upload_id: str
    set_id: str | None
    display_name: str
    declared_size_bytes: int
    declared_sha256: str
    declared_page_count: int | None
    state: str
    multipart_token: str | None
    blob_id: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PartRow:
    file_id: str
    part_number: int
    state: str
    size_bytes: int | None
    sha256: str | None
    etag: str | None


@dataclass(frozen=True, slots=True)
class OrderRow:
    order_id: str
    project_uid: str
    document_uid: str
    revision_no: int
    version_uids: tuple[str, ...]
    source: str
    actor_user_uid: str
    created_at: datetime


def _upload(row: Any) -> UploadRow:
    values = tuple(row)
    return UploadRow(
        upload_id=values[0], project_uid=values[1], state=values[2], declared_files=int(values[3]),
        declared_bytes=int(values[4]), declared_pages=int(values[5]), part_size_bytes=int(values[6]),
        pause_requested=bool(values[7]), actor_user_uid=values[8], actor_label=values[9],
        command_id=values[10], created_at=values[11], updated_at=values[12],
        compare_after_preparation=bool(values[13]),
    )


def _set(row: Any) -> SetRow:
    values = tuple(row)
    proposal = values[8]
    return SetRow(
        set_id=values[0], upload_id=values[1], state=values[2], designation=values[3],
        existing_document_uid=values[4], document_uid=values[5], project_stage=values[6],
        section_code=values[7], proposal=proposal if isinstance(proposal, dict) else json.loads(proposal),
        failure_reason=values[9], confirmed_by_user_uid=values[10], confirmed_at=values[11],
        created_at=values[12], updated_at=values[13],
    )


def _file(row: Any) -> FileRow:
    values = tuple(row)
    return FileRow(
        file_id=values[0], upload_id=values[1], set_id=values[2], display_name=values[3],
        declared_size_bytes=int(values[4]), declared_sha256=values[5],
        declared_page_count=None if values[6] is None else int(values[6]), state=values[7],
        multipart_token=values[8], blob_id=values[9], failure_reason=values[10], created_at=values[11],
        updated_at=values[12],
    )


def _part(row: Any) -> PartRow:
    values = tuple(row)
    return PartRow(
        file_id=values[0], part_number=int(values[1]), state=values[2],
        size_bytes=None if values[3] is None else int(values[3]), sha256=values[4], etag=values[5],
    )


def _order(row: Any) -> OrderRow:
    values = tuple(row)
    versions = values[4]
    return OrderRow(
        order_id=values[0], project_uid=values[1], document_uid=values[2], revision_no=int(values[3]),
        version_uids=tuple(versions if isinstance(versions, list) else json.loads(versions)),
        source=values[5], actor_user_uid=values[6], created_at=values[7],
    )


class ComparisonUploadRepository:
    """The statements of this lane's operations. Stateless; every method takes the caller's session."""

    __slots__ = ()

    # -- the batch -------------------------------------------------------------------------------------

    def lock_creation(self, session: Session) -> None:
        """Serialise batch creations until the transaction ends (the active-batch count is read under it)."""
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": _ACTIVE_LOCK_KEY}
        )

    def count_active(self, session: Session, actor_user_uid: str) -> tuple[int, int]:
        """``(batches of this account, batches of the installation)`` that are still active."""
        row = session.execute(
            text(
                "SELECT count(*) FILTER (WHERE actor_user_uid = :actor), count(*) "
                "FROM comparison_upload WHERE state = ANY(:states)"
            ),
            {"actor": actor_user_uid, "states": list(ACTIVE_BATCH_STATES)},
        ).one()
        return int(row[0]), int(row[1])

    def insert_upload(
        self,
        session: Session,
        *,
        upload_id: str,
        project_uid: str,
        declared_files: int,
        declared_bytes: int,
        declared_pages: int,
        part_size_bytes: int,
        actor_user_uid: str,
        actor_label: str,
        command_id: str,
        compare_after_preparation: bool = False,
    ) -> UploadRow:
        row = session.execute(
            text(
                "INSERT INTO comparison_upload (comparison_upload_id, project_uid, declared_files, "
                "declared_bytes, declared_pages, part_size_bytes, actor_user_uid, actor_label, command_id, "
                "compare_after_preparation) "
                "VALUES (:id, :project, :files, :bytes, :pages, :part, :actor, :label, :command, :compare) "
                f"RETURNING {_UPLOAD_COLUMNS}"
            ),
            {
                "id": upload_id, "project": project_uid, "files": declared_files, "bytes": declared_bytes,
                "pages": declared_pages, "part": part_size_bytes, "actor": actor_user_uid,
                "label": actor_label, "command": command_id, "compare": compare_after_preparation,
            },
        ).one()
        return _upload(row)

    def get_upload(self, session: Session, upload_id: str, *, for_update: bool = False) -> UploadRow | None:
        row = session.execute(
            text(
                f"SELECT {_UPLOAD_COLUMNS} FROM comparison_upload WHERE comparison_upload_id = :id"
                + (" FOR UPDATE" if for_update else "")
            ),
            {"id": upload_id},
        ).first()
        return None if row is None else _upload(row)

    def set_upload_state(self, session: Session, upload_id: str, *, to_state: str) -> None:
        session.execute(
            text(
                "UPDATE comparison_upload SET state = :state, updated_at = clock_timestamp(), "
                "terminal_at = CASE WHEN CAST(:state AS text) IN ('completed', 'cancelled') THEN clock_timestamp() "
                "ELSE terminal_at END WHERE comparison_upload_id = :id"
            ),
            {"id": upload_id, "state": to_state},
        )

    def touch_upload(self, session: Session, upload_id: str) -> None:
        session.execute(
            text("UPDATE comparison_upload SET updated_at = clock_timestamp() WHERE comparison_upload_id = :id"),
            {"id": upload_id},
        )

    def project_stored_bytes(self, session: Session, project_uid: str) -> int:
        """What the project stores, in bytes: its sources, its derived data and what batches in flight declared.

        The distinct blobs named by the manifests of the project's versions, by the profile, preview and
        thumbnail of its versions' pages, and by the verified files of its comparison batches (a refused file's
        published blob counts too: the store never deletes one), plus the declared bytes of the files of batches
        still active that hold no blob yet. A blob is counted once however many rows name it.
        """
        row = session.execute(
            text(
                "WITH named AS ("
                "  SELECT e.blob_id FROM input_manifest_entry e "
                "    JOIN document_version v ON v.version_uid = e.version_uid "
                "    JOIN document d ON d.document_uid = v.document_uid WHERE d.project_uid = :project "
                "  UNION SELECT b FROM comparison_page_profile p "
                "    JOIN document_version v ON v.version_uid = p.version_uid "
                "    JOIN document d ON d.document_uid = v.document_uid "
                "    CROSS JOIN LATERAL (VALUES (p.profile_blob_id), (p.preview_blob_id), "
                "                               (p.thumbnail_blob_id)) AS blobs (b) "
                "    WHERE d.project_uid = :project AND b IS NOT NULL "
                "  UNION SELECT f.blob_id FROM comparison_upload_file f "
                "    JOIN comparison_upload u ON u.comparison_upload_id = f.comparison_upload_id "
                "    WHERE u.project_uid = :project AND f.blob_id IS NOT NULL"
                ") "
                "SELECT coalesce((SELECT sum(b.size_bytes) FROM blob b JOIN named n ON n.blob_id = b.blob_id), 0) "
                "     + coalesce((SELECT sum(f.declared_size_bytes) FROM comparison_upload_file f "
                "         JOIN comparison_upload u ON u.comparison_upload_id = f.comparison_upload_id "
                "         WHERE u.project_uid = :project AND u.state = ANY(:states) "
                "           AND f.blob_id IS NULL AND f.state <> 'failed'), 0)"
            ),
            {"project": project_uid, "states": list(ACTIVE_BATCH_STATES)},
        ).scalar_one()
        return int(row)

    # -- files and parts -------------------------------------------------------------------------------

    def insert_file(
        self,
        session: Session,
        *,
        file_id: str,
        upload_id: str,
        display_name: str,
        size_bytes: int,
        sha256: str,
        page_count: int | None,
    ) -> FileRow:
        row = session.execute(
            text(
                "INSERT INTO comparison_upload_file (comparison_upload_file_id, comparison_upload_id, "
                "display_name, declared_size_bytes, declared_sha256, declared_page_count) "
                "VALUES (:id, :upload, :name, :size, :sha, :pages) "
                f"RETURNING {_FILE_COLUMNS}"
            ),
            {
                "id": file_id, "upload": upload_id, "name": display_name, "size": size_bytes, "sha": sha256,
                "pages": page_count,
            },
        ).one()
        return _file(row)

    def get_file(self, session: Session, file_id: str, *, for_update: bool = False) -> FileRow | None:
        row = session.execute(
            text(
                f"SELECT {_FILE_COLUMNS} FROM comparison_upload_file WHERE comparison_upload_file_id = :id"
                + (" FOR UPDATE" if for_update else "")
            ),
            {"id": file_id},
        ).first()
        return None if row is None else _file(row)

    def list_files(self, session: Session, upload_id: str) -> tuple[FileRow, ...]:
        rows = session.execute(
            text(
                f"SELECT {_FILE_COLUMNS} FROM comparison_upload_file WHERE comparison_upload_id = :id "
                "ORDER BY created_at, comparison_upload_file_id"
            ),
            {"id": upload_id},
        ).all()
        return tuple(_file(row) for row in rows)

    def files_of_set(self, session: Session, set_id: str) -> tuple[FileRow, ...]:
        rows = session.execute(
            text(
                f"SELECT {_FILE_COLUMNS} FROM comparison_upload_file WHERE set_id = :id "
                "ORDER BY comparison_upload_file_id"
            ),
            {"id": set_id},
        ).all()
        return tuple(_file(row) for row in rows)

    def staged_part_counts(self, session: Session, upload_id: str) -> dict[str, int]:
        """File identity to the number of its parts that are staged or completed."""
        rows = session.execute(
            text(
                "SELECT p.comparison_upload_file_id, count(*) FROM comparison_upload_part p "
                "JOIN comparison_upload_file f ON f.comparison_upload_file_id = p.comparison_upload_file_id "
                "WHERE f.comparison_upload_id = :id AND p.state IN ('staged', 'completed') "
                "GROUP BY p.comparison_upload_file_id"
            ),
            {"id": upload_id},
        ).all()
        return {row[0]: int(row[1]) for row in rows}

    def persist_token_and_start(self, session: Session, file_id: str, *, token: str) -> None:
        """Write the multipart token (write-once) and move the file to ``uploading``; the first part follows."""
        session.execute(
            text(
                "UPDATE comparison_upload_file SET multipart_token = :token, state = 'uploading', "
                "failure_reason = NULL, updated_at = clock_timestamp() WHERE comparison_upload_file_id = :id"
            ),
            {"id": file_id, "token": token},
        )

    def restart_file(self, session: Session, file_id: str) -> None:
        """A failed file that is sent again: ``failed -> uploading`` with the old reason cleared."""
        session.execute(
            text(
                "UPDATE comparison_upload_file SET state = 'uploading', failure_reason = NULL, "
                "updated_at = clock_timestamp() WHERE comparison_upload_file_id = :id"
            ),
            {"id": file_id},
        )

    def record_blob(self, session: Session, file_id: str, *, blob_id: str) -> None:
        """Bind the published blob (write-once); the file stays ``uploading`` until it has been read."""
        session.execute(
            text(
                "UPDATE comparison_upload_file SET blob_id = :blob, updated_at = clock_timestamp() "
                "WHERE comparison_upload_file_id = :id"
            ),
            {"id": file_id, "blob": blob_id},
        )

    def mark_file_verified(self, session: Session, file_id: str, *, set_id: str | None) -> None:
        session.execute(
            text(
                "UPDATE comparison_upload_file SET state = 'verified', set_id = :set, "
                "updated_at = clock_timestamp() WHERE comparison_upload_file_id = :id"
            ),
            {"id": file_id, "set": set_id},
        )

    def mark_file_failed(self, session: Session, file_id: str, *, reason: str) -> None:
        session.execute(
            text(
                "UPDATE comparison_upload_file SET state = 'failed', failure_reason = :reason, "
                "updated_at = clock_timestamp() WHERE comparison_upload_file_id = :id"
            ),
            {"id": file_id, "reason": reason[:128]},
        )

    def get_part(self, session: Session, file_id: str, part_number: int) -> PartRow | None:
        row = session.execute(
            text(
                "SELECT comparison_upload_file_id, part_number, state, size_bytes, sha256, etag "
                "FROM comparison_upload_part WHERE comparison_upload_file_id = :id AND part_number = :n"
            ),
            {"id": file_id, "n": part_number},
        ).first()
        return None if row is None else _part(row)

    def list_parts(self, session: Session, file_id: str) -> tuple[PartRow, ...]:
        rows = session.execute(
            text(
                "SELECT comparison_upload_file_id, part_number, state, size_bytes, sha256, etag "
                "FROM comparison_upload_part WHERE comparison_upload_file_id = :id ORDER BY part_number"
            ),
            {"id": file_id},
        ).all()
        return tuple(_part(row) for row in rows)

    def insert_part(self, session: Session, file_id: str, part_number: int) -> None:
        """A part row, ``declared``: its owner exists before its bytes are staged (the database refuses a
        part for a file whose token has not been persisted)."""
        session.execute(
            text(
                "INSERT INTO comparison_upload_part (comparison_upload_file_id, part_number) VALUES (:id, :n) "
                "ON CONFLICT (comparison_upload_file_id, part_number) DO NOTHING"
            ),
            {"id": file_id, "n": part_number},
        )

    def mark_part_staged(
        self, session: Session, file_id: str, part_number: int, *, size_bytes: int, sha256: str, etag: str
    ) -> None:
        session.execute(
            text(
                "UPDATE comparison_upload_part SET state = 'staged', size_bytes = :size, sha256 = :sha, "
                "etag = :etag, updated_at = clock_timestamp() "
                "WHERE comparison_upload_file_id = :id AND part_number = :n"
            ),
            {"id": file_id, "n": part_number, "size": size_bytes, "sha": sha256, "etag": etag},
        )

    def complete_parts(self, session: Session, file_id: str) -> None:
        session.execute(
            text(
                "UPDATE comparison_upload_part SET state = 'completed', updated_at = clock_timestamp() "
                "WHERE comparison_upload_file_id = :id AND state = 'staged'"
            ),
            {"id": file_id},
        )

    def delete_parts(self, session: Session, file_id: str) -> None:
        """The parts of a file whose store-side upload is gone (an integrity refusal consumed it): the rows
        described chunks that no longer exist, and a re-sent file declares its parts again."""
        session.execute(
            text("DELETE FROM comparison_upload_part WHERE comparison_upload_file_id = :id"), {"id": file_id}
        )

    # -- the sets --------------------------------------------------------------------------------------

    def insert_set(self, session: Session, *, set_id: str, upload_id: str, proposal: Mapping[str, Any]) -> SetRow:
        row = session.execute(
            text(
                "INSERT INTO comparison_upload_set (comparison_upload_set_id, comparison_upload_id, proposal) "
                f"VALUES (:id, :upload, CAST(:proposal AS jsonb)) RETURNING {_SET_COLUMNS}"
            ),
            {"id": set_id, "upload": upload_id, "proposal": json.dumps(dict(proposal), ensure_ascii=False)},
        ).one()
        return _set(row)

    def get_set(self, session: Session, set_id: str, *, for_update: bool = False) -> SetRow | None:
        row = session.execute(
            text(
                f"SELECT {_SET_COLUMNS} FROM comparison_upload_set WHERE comparison_upload_set_id = :id"
                + (" FOR UPDATE" if for_update else "")
            ),
            {"id": set_id},
        ).first()
        return None if row is None else _set(row)

    def find_set_by_key(self, session: Session, upload_id: str, grouping_key: str) -> SetRow | None:
        """The set of this batch whose grouping key is ``grouping_key`` (the key is held in the proposal)."""
        row = session.execute(
            text(
                f"SELECT {_SET_COLUMNS} FROM comparison_upload_set WHERE comparison_upload_id = :id "
                "AND proposal ->> 'grouping_key' = :key ORDER BY created_at LIMIT 1"
            ),
            {"id": upload_id, "key": grouping_key},
        ).first()
        return None if row is None else _set(row)

    def list_sets(self, session: Session, upload_id: str) -> tuple[SetRow, ...]:
        rows = session.execute(
            text(
                f"SELECT {_SET_COLUMNS} FROM comparison_upload_set WHERE comparison_upload_id = :id "
                "ORDER BY created_at, comparison_upload_set_id"
            ),
            {"id": upload_id},
        ).all()
        return tuple(_set(row) for row in rows)

    def count_sets(self, session: Session, upload_id: str) -> int:
        return int(
            session.execute(
                text("SELECT count(*) FROM comparison_upload_set WHERE comparison_upload_id = :id"),
                {"id": upload_id},
            ).scalar_one()
        )

    def write_set_proposal(
        self,
        session: Session,
        set_id: str,
        *,
        proposal: Mapping[str, Any],
        designation: str | None,
        project_stage: str | None,
        section_code: str | None,
        existing_document_uid: str | None,
    ) -> None:
        session.execute(
            text(
                "UPDATE comparison_upload_set SET proposal = CAST(:proposal AS jsonb), designation = :designation, "
                "project_stage = :stage, section_code = :section, existing_document_uid = :existing, "
                "updated_at = clock_timestamp() WHERE comparison_upload_set_id = :id"
            ),
            {
                "id": set_id, "proposal": json.dumps(dict(proposal), ensure_ascii=False),
                "designation": designation, "stage": project_stage, "section": section_code,
                "existing": existing_document_uid,
            },
        )

    def set_state(self, session: Session, set_id: str, *, to_state: str, failure_reason: str | None = None) -> None:
        session.execute(
            text(
                "UPDATE comparison_upload_set SET state = :state, failure_reason = :reason, "
                "terminal_at = CASE WHEN CAST(:state AS text) IN ('done', 'excluded') THEN clock_timestamp() ELSE NULL END, "
                "updated_at = clock_timestamp() WHERE comparison_upload_set_id = :id"
            ),
            {"id": set_id, "state": to_state, "reason": failure_reason},
        )

    def confirm_set(
        self,
        session: Session,
        set_id: str,
        *,
        designation: str | None,
        existing_document_uid: str | None,
        project_stage: str | None,
        section_code: str | None,
        confirmed_by_user_uid: str,
    ) -> None:
        """Record the user's word on a set: what it is, who said so and when. The state moves separately
        (the database refuses ``ready`` without a confirmer and a time, so this comes first)."""
        session.execute(
            text(
                "UPDATE comparison_upload_set SET designation = :designation, existing_document_uid = :existing, "
                "project_stage = :stage, section_code = :section, confirmed_by_user_uid = :actor, "
                "confirmed_at = clock_timestamp(), updated_at = clock_timestamp() "
                "WHERE comparison_upload_set_id = :id"
            ),
            {
                "id": set_id, "designation": designation, "existing": existing_document_uid,
                "stage": project_stage, "section": section_code, "actor": confirmed_by_user_uid,
            },
        )

    def finish_set(
        self, session: Session, set_id: str, *, document_uid: str, proposal: Mapping[str, Any]
    ) -> None:
        """Bind the document the set became and keep what the user confirmed (members, order, labels and the
        version each file made) in the set's proposal. The state moves to ``done`` separately."""
        session.execute(
            text(
                "UPDATE comparison_upload_set SET document_uid = :document, proposal = CAST(:proposal AS jsonb), "
                "updated_at = clock_timestamp() WHERE comparison_upload_set_id = :id"
            ),
            {
                "id": set_id, "document": document_uid,
                "proposal": json.dumps(dict(proposal), ensure_ascii=False),
            },
        )

    def set_states_of(self, session: Session, upload_id: str) -> tuple[str, ...]:
        rows = session.execute(
            text("SELECT state FROM comparison_upload_set WHERE comparison_upload_id = :id"), {"id": upload_id}
        ).all()
        return tuple(row[0] for row in rows)

    def file_states_of(self, session: Session, upload_id: str) -> tuple[tuple[str, str | None], ...]:
        rows = session.execute(
            text("SELECT state, failure_reason FROM comparison_upload_file WHERE comparison_upload_id = :id"),
            {"id": upload_id},
        ).all()
        return tuple((row[0], row[1]) for row in rows)

    def done_set_documents(self, session: Session, project_uid: str) -> tuple[tuple[str, str], ...]:
        """``(designation, document_uid)`` of every set of the project's batches that became a document."""
        rows = session.execute(
            text(
                "SELECT s.designation, s.document_uid FROM comparison_upload_set s "
                "JOIN comparison_upload u ON u.comparison_upload_id = s.comparison_upload_id "
                "WHERE u.project_uid = :project AND s.state = 'done' AND s.designation IS NOT NULL "
                "AND s.document_uid IS NOT NULL ORDER BY s.terminal_at DESC, s.comparison_upload_set_id DESC"
            ),
            {"project": project_uid},
        ).all()
        return tuple((row[0], row[1]) for row in rows)

    def version_labels(self, session: Session, document_uid: str) -> dict[str, str]:
        """The label the user confirmed for each version a comparison upload made in this document.

        A version has no label column: the label lives in the confirmed proposal of the set that made it
        (``proposal.confirmed.files[].version_uid`` and ``.version_label``).
        """
        rows = session.execute(
            text(
                "SELECT f ->> 'version_uid', f ->> 'version_label' "
                "FROM comparison_upload_set s, jsonb_array_elements(s.proposal -> 'confirmed' -> 'files') AS f "
                "WHERE s.document_uid = :document AND s.state = 'done'"
            ),
            {"document": document_uid},
        ).all()
        return {row[0]: row[1] for row in rows if row[0] and row[1]}

    # -- the order of the versions of a document --------------------------------------------------------

    def lock_document_order(self, session: Session, document_uid: str) -> None:
        """The advisory lock the chain trigger takes for this document, taken first so the stale check and the
        insert are one decision (the trigger's own lock is re-entrant in this transaction)."""
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended('comparison_version_order:' || :doc, 0))"),
            {"doc": document_uid},
        )

    def latest_order(self, session: Session, document_uid: str) -> OrderRow | None:
        row = session.execute(
            text(
                "SELECT comparison_version_order_id, project_uid, document_uid, revision_no, version_uids, "
                "source, actor_user_uid, created_at FROM comparison_version_order "
                "WHERE document_uid = :doc ORDER BY revision_no DESC LIMIT 1"
            ),
            {"doc": document_uid},
        ).first()
        return None if row is None else _order(row)

    def latest_order_of_command(self, session: Session, command_id: str) -> OrderRow | None:
        """The revision a command appended (a command makes at most one: ``uq_comparison_version_order_command``)."""
        row = session.execute(
            text(
                "SELECT comparison_version_order_id, project_uid, document_uid, revision_no, version_uids, "
                "source, actor_user_uid, created_at FROM comparison_version_order WHERE command_id = :command"
            ),
            {"command": command_id},
        ).first()
        return None if row is None else _order(row)

    def insert_order(
        self,
        session: Session,
        *,
        order_id: str,
        project_uid: str,
        document_uid: str,
        revision_no: int,
        version_uids: Sequence[str],
        source: str,
        actor_user_uid: str,
        actor_label: str,
        command_id: str,
    ) -> OrderRow:
        row = session.execute(
            text(
                "INSERT INTO comparison_version_order (comparison_version_order_id, project_uid, document_uid, "
                "revision_no, version_uids, source, actor_user_uid, actor_label, command_id) "
                "VALUES (:id, :project, :doc, :revision, CAST(:versions AS jsonb), :source, :actor, :label, "
                ":command) RETURNING comparison_version_order_id, project_uid, document_uid, revision_no, "
                "version_uids, source, actor_user_uid, created_at"
            ),
            {
                "id": order_id, "project": project_uid, "doc": document_uid, "revision": revision_no,
                "versions": json.dumps(list(version_uids)), "source": source, "actor": actor_user_uid,
                "label": actor_label, "command": command_id,
            },
        ).one()
        return _order(row)

    def list_orders(
        self, session: Session, document_uid: str, *, before_revision: int | None, limit: int
    ) -> tuple[OrderRow, ...]:
        """Newest first. ``before_revision`` is the oldest revision the previous page held (keyset paging)."""
        rows = session.execute(
            text(
                "SELECT comparison_version_order_id, project_uid, document_uid, revision_no, version_uids, "
                "source, actor_user_uid, created_at FROM comparison_version_order WHERE document_uid = :doc "
                "AND (CAST(:before AS integer) IS NULL OR revision_no < CAST(:before AS integer)) "
                "ORDER BY revision_no DESC LIMIT :limit"
            ),
            {"doc": document_uid, "before": before_revision, "limit": limit},
        ).all()
        return tuple(_order(row) for row in rows)
