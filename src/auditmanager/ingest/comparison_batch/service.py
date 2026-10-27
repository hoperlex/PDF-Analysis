"""The use cases of the batch operations: list, exclude, retry, pause, resume, cancel, and the two hooks.

The six functions serve the contract's ``listComparisonUploads``, ``excludeComparisonUploadSet``,
``retryComparisonUploadSet``, ``pauseComparisonUpload``, ``resumeComparisonUpload`` and ``cancelComparisonUpload``; the
rules are ADR-0025 decisions 9, 10 and 16. The state machine itself is :class:`~.lifecycle.BatchLifecycle`.

What each act needs
-------------------
================= =================================== ==========================================================
act               batch state                         other conditions
================= =================================== ==========================================================
pause             ``processing``                      none (the set in hand finishes, no new set is released)
resume            ``paused``                          none
cancel            ``uploading``, ``proposed``,        none; a finished batch is ``comparison_upload_state``
                  ``processing``, ``paused``
exclude a set     ``proposed``, ``processing``,       the set is ``needs_confirmation`` or ``failed``; ``done`` and
                  ``paused``                          ``excluded`` are ``comparison_set_state``; ``excluded`` is final
retry a set       ``proposed``, ``processing``,       the set is ``failed`` for a reason a retry can fix
                  ``paused``                          (:data:`~.rules.RETRYABLE_SET_REASONS`, and for the sets limit
                                                      only while the batch has room)
================= =================================== ==========================================================

**Every act is an expert's** (decision 16): the role is checked first, before anything is read, and the edge checks it
too. **Every act is keyed**: the key is claimed inside the transaction that acts, a repeat answers the recorded outcome
with the batch's (or the set's) current state, a different payload under the key is ``idempotency_key_reuse``, and a
refused act leaves no record (it rolls back with the claim, so the client retries under the same key once the state
allows). The outcome records the actor's identity beside the batch's, which is the trail a batch has (it carries no
actor column per act).

**What a cancel never does.** It deletes nothing: the batch's document versions, their bytes and their blobs are not
named by any statement it makes, and the store is touched only by the sweep, from the database's decision.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.commands import CommandRepository, CommandReplay, CommandStarted, payload_fingerprint
from auditmanager.ingest.comparison_batch.lifecycle import BatchLifecycle
from auditmanager.ingest.comparison_batch.repository import ComparisonBatchRepository
from auditmanager.ingest.comparison_batch.rules import (
    ACTIVE_FOR_SET_OPERATIONS,
    COMMAND_CANCEL_UPLOAD,
    COMMAND_EXCLUDE_SET,
    COMMAND_PAUSE_UPLOAD,
    COMMAND_RESUME_UPLOAD,
    COMMAND_RETRY_SET,
    EXCLUDABLE_SET_STATES,
    REASON_SETS_LIMIT,
    RETRYABLE_SET_REASONS,
)
from auditmanager.ingest.comparison_batch.views import UploadPageView
from auditmanager.ingest.comparison_pdf.public import (
    ACTIVE_BATCH_STATES,
    MAX_SETS,
    ComparisonUploadRepository,
    ComparisonUploadService,
    SetView,
    UploadView,
    require_expert,
)
from auditmanager.ingest.comparison_pdf.repository import SetRow, UploadRow
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey, ProjectUid

__all__ = ["ComparisonBatchService"]

#: ``decide(session, upload, set_row)``: the act itself, run under the batch's lock after the key is claimed.
_Decide = Callable[[Session, UploadRow, "SetRow | None"], None]


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


def _not_found(aggregate_type: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate_type)


class ComparisonBatchService:
    """Constructed with its dependencies; it builds no engine and reads no ``DATABASE_URL``.

    ``uploads`` is the upload service of ``CMP-INGEST-01``: the batch and the sets this service answers with are
    read through it (the same views, the same mapping onto the contract), after the transaction that acted.
    """

    __slots__ = ("_uploads", "_factory", "_documents", "_commands", "_repo", "_batches", "_lifecycle")

    def __init__(
        self,
        uploads: ComparisonUploadService,
        *,
        session_factory: sessionmaker[Session] | None = None,
        lifecycle: BatchLifecycle | None = None,
    ) -> None:
        self._uploads = uploads
        self._factory = session_factory
        self._documents = DocumentRepository()
        self._commands = CommandRepository()
        self._repo = ComparisonUploadRepository()
        self._batches = ComparisonBatchRepository()
        self._lifecycle = lifecycle or BatchLifecycle()

    # -- the listing -----------------------------------------------------------------------------------

    def list_uploads(self, *, project_uid: str, after: tuple[datetime, str] | None, limit: int) -> UploadPageView:
        """The project's batches, newest first, without their files. An unknown project is ``not_found``."""
        with session_scope(self._factory) as session:
            self._documents.get_project(session, ProjectUid.parse(project_uid))
            rows = self._batches.list_uploads(session, project_uid, after=after, limit=limit + 1)
            page = rows[:limit]
            items = tuple(
                UploadView(
                    upload_id=row.upload_id, project_uid=row.project_uid, state=row.state,
                    part_size_bytes=row.part_size_bytes, declared_files=row.declared_files,
                    declared_bytes=row.declared_bytes, created_at=row.created_at, updated_at=row.updated_at,
                    files=None,
                )
                for row in page
            )
            more = len(rows) > limit
            return UploadPageView(
                items=items, next_after=(page[-1].created_at, page[-1].upload_id) if more and page else None
            )

    # -- the batch -------------------------------------------------------------------------------------

    def pause_upload(
        self, *, upload_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> UploadView:
        """Stop the release of the next confirmed set; the set in hand and its items in flight finish."""

        def decide(session: Session, upload: UploadRow, _row: SetRow | None) -> None:
            if upload.state != "processing":
                raise _conflict("comparison_upload_state")
            self._batches.set_pause(session, upload.upload_id, to_state="paused", pause_requested=True)

        self._act(
            command_type=COMMAND_PAUSE_UPLOAD, upload_id=upload_id, set_id=None, user_uid=user_uid,
            actor_roles=actor_roles, idempotency_key=idempotency_key, decide=decide,
        )
        return self._uploads.get_upload(upload_id=upload_id)

    def resume_upload(
        self, *, upload_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> UploadView:
        """Run a paused batch again: the next confirmed set is released at once if none is in flight."""

        def decide(session: Session, upload: UploadRow, _row: SetRow | None) -> None:
            if upload.state != "paused":
                raise _conflict("comparison_upload_state")
            self._batches.set_pause(session, upload.upload_id, to_state="processing", pause_requested=False)
            running = replace(upload, state="processing", pause_requested=False)
            self._lifecycle.ensure_driver(session, running)
            self._lifecycle.advance(session, running)

        self._act(
            command_type=COMMAND_RESUME_UPLOAD, upload_id=upload_id, set_id=None, user_uid=user_uid,
            actor_roles=actor_roles, idempotency_key=idempotency_key, decide=decide,
        )
        return self._uploads.get_upload(upload_id=upload_id)

    def cancel_upload(
        self, *, upload_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> UploadView:
        """«Отменить пакет»: the files that never completed fail, their parts are aborted, the sets that made no
        versions are left out, the batch is ``cancelled`` and its account's slot is free. Versions the batch already
        made, and their bytes, stay. A finished batch is ``conflict`` (``comparison_upload_state``)."""

        def decide(session: Session, upload: UploadRow, _row: SetRow | None) -> None:
            if upload.state not in ACTIVE_BATCH_STATES:
                raise _conflict("comparison_upload_state")
            self._lifecycle.cancel(session, upload, reason="cancelled", created_by_user_uid=user_uid)

        self._act(
            command_type=COMMAND_CANCEL_UPLOAD, upload_id=upload_id, set_id=None, user_uid=user_uid,
            actor_roles=actor_roles, idempotency_key=idempotency_key, decide=decide,
        )
        return self._uploads.get_upload(upload_id=upload_id)

    # -- one set ---------------------------------------------------------------------------------------

    def exclude_set(
        self, *, upload_id: str, set_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> SetView:
        """Leave one set out of the batch: its files stay as history and nothing is admitted from it. A set that
        is ``done`` (it made versions) or already ``excluded`` is ``conflict`` (``comparison_set_state``); there is
        no way back from ``excluded``."""

        def decide(session: Session, upload: UploadRow, row: SetRow | None) -> None:
            assert row is not None
            if upload.state not in ACTIVE_FOR_SET_OPERATIONS:
                raise _conflict("comparison_upload_state")
            if row.state not in EXCLUDABLE_SET_STATES:
                raise _conflict("comparison_set_state")
            self._repo.set_state(session, row.set_id, to_state="excluded")
            self._batches.record_exclusion(session, row.set_id, user_uid=user_uid)
            self._settle(session, upload.upload_id)

        self._act(
            command_type=COMMAND_EXCLUDE_SET, upload_id=upload_id, set_id=set_id, user_uid=user_uid,
            actor_roles=actor_roles, idempotency_key=idempotency_key, decide=decide,
        )
        return self._set_view(upload_id, set_id)

    def retry_set(
        self, *, upload_id: str, set_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> SetView:
        """Queue a failed set again, only for a reason a retry can fix. A set in any other state, or failed for any
        other reason (the document's or a decision's, which a retry would meet again), is ``conflict``
        (``comparison_set_state``)."""

        def decide(session: Session, upload: UploadRow, row: SetRow | None) -> None:
            assert row is not None
            if upload.state not in ACTIVE_FOR_SET_OPERATIONS:
                raise _conflict("comparison_upload_state")
            if row.state != "failed" or row.failure_reason not in RETRYABLE_SET_REASONS:
                raise _conflict("comparison_set_state")
            if row.failure_reason == REASON_SETS_LIMIT and self._batches.count_open_sets(
                session, upload.upload_id
            ) >= MAX_SETS:
                raise _conflict("comparison_set_state")
            self._repo.set_state(session, row.set_id, to_state="reading")
            self._repo.set_state(session, row.set_id, to_state="needs_confirmation")

        self._act(
            command_type=COMMAND_RETRY_SET, upload_id=upload_id, set_id=set_id, user_uid=user_uid,
            actor_roles=actor_roles, idempotency_key=idempotency_key, decide=decide,
        )
        return self._set_view(upload_id, set_id)

    # -- the hooks the adapter calls -------------------------------------------------------------------

    def after_declaration(self, *, upload_id: str) -> None:
        """Give the batch its drive. Idempotent (one live drive per batch); the client's retry of the declaration,
        under the same key, runs it again."""
        with session_scope(self._factory) as session:
            self._lifecycle.after_declaration(session, upload_id)

    def after_confirmation(self, *, upload_id: str, set_id: str) -> None:
        """What a confirmed set needs next (see :meth:`BatchLifecycle.after_confirmation`). Idempotent: a replay of
        the confirmation under the same key runs it again, which is how a failed hook is repaired."""
        with session_scope(self._factory) as session:
            self._lifecycle.after_confirmation(session, upload_id, set_id)

    # -- helpers ---------------------------------------------------------------------------------------

    def _act(
        self,
        *,
        command_type: str,
        upload_id: str,
        set_id: str | None,
        user_uid: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
        decide: _Decide,
    ) -> None:
        """Check the role, lock the batch (and the set), claim the key and run ``decide``, in one transaction."""
        require_expert(actor_roles)
        key = IdempotencyKey(idempotency_key)
        payload: dict[str, Any] = {"command": f"{command_type}.v1", "upload_id": upload_id}
        outcome: dict[str, Any] = {"upload_id": upload_id, "actor_user_uid": user_uid}
        if set_id is not None:
            payload["set_id"] = set_id
            outcome["set_id"] = set_id
        fingerprint = payload_fingerprint(payload)
        with session_scope(self._factory) as session:
            upload = self._repo.get_upload(session, upload_id, for_update=True)
            if upload is None:
                raise _not_found("ComparisonUpload")
            row: SetRow | None = None
            if set_id is not None:
                row = self._repo.get_set(session, set_id, for_update=True)
                if row is None or row.upload_id != upload_id:
                    raise _not_found("ComparisonUploadSet")
            claim = self._commands.begin(
                session, command_type=command_type, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                return
            assert isinstance(claim, CommandStarted)
            decide(session, upload, row)
            self._commands.succeed(session, claim.command_id, outcome)

    def _settle(self, session: Session, upload_id: str) -> None:
        """After a set was left out: a batch with nothing left to decide is finished (see the lifecycle)."""
        upload = self._repo.get_upload(session, upload_id, for_update=True)
        assert upload is not None
        sets = self._repo.list_sets(session, upload_id)
        upload = self._lifecycle.promote_if_confirmed(session, upload)  # a confirmation whose hook never ran
        if upload.state == "proposed" and sets and all(row.state == "excluded" for row in sets):
            self._repo.set_upload_state(session, upload_id, to_state="completed")
            return
        if upload.state == "processing":
            self._lifecycle.advance(session, upload)

    def _set_view(self, upload_id: str, set_id: str) -> SetView:
        for view in self._uploads.get_proposal(upload_id=upload_id).sets:
            if view.set_id == set_id:
                return view
        raise _not_found("ComparisonUploadSet")  # pragma: no cover - the act just read the set
