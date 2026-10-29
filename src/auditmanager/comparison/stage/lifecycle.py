"""Keyed pause/resume/cancel with durable multipart cleanup intent."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest import domain_error_from_storage
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage.public import MultipartStaging, StorageError

from .leases import upload_process_lease
from .uploads import StageUploadRow, StageUploadService

__all__ = ["StageUploadLifecycleService"]


class StageUploadLifecycleService:
    def __init__(
        self, session_factory: sessionmaker[Session], store: MultipartStaging,
    ) -> None:
        self._sessions = session_factory
        self._store = store
        self._commands = CommandRepository()

    def pause(self, *, upload_id: str, user_uid: str, idempotency_key: str) -> StageUploadRow:
        return self._change(
            upload_id=upload_id, user_uid=user_uid, idempotency_key=idempotency_key,
            command="pause_stage_upload", from_states=("uploading",), to_state="paused",
        )

    def resume(self, *, upload_id: str, user_uid: str, idempotency_key: str) -> StageUploadRow:
        return self._change(
            upload_id=upload_id, user_uid=user_uid, idempotency_key=idempotency_key,
            command="resume_stage_upload", from_states=("paused",), to_state="uploading",
        )

    def cancel(self, *, upload_id: str, user_uid: str, idempotency_key: str) -> StageUploadRow:
        with upload_process_lease(self._sessions, upload_id):
            with session_scope(self._sessions) as session:
                state = self._owner_state(session, upload_id, user_uid)
                claim = self._commands.begin(
                    session, command_type="cancel_stage_upload",
                    idempotency_key=IdempotencyKey(idempotency_key),
                    fingerprint=self._fingerprint("cancel_stage_upload", upload_id, user_uid),
                )
                if not isinstance(claim, CommandReplay):
                    if state not in ("uploading", "paused", "failed"):
                        raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_state")
                    bound = session.execute(text(
                        "SELECT 1 FROM stage_upload_candidate c "
                        "JOIN stage_upload_file f ON f.stage_upload_file_id = c.stage_upload_file_id "
                        "WHERE f.stage_upload_id = :upload "
                        "AND c.state IN ('confirmed', 'admitting', 'published') LIMIT 1"
                    ), {"upload": upload_id}).first()
                    if bound is not None:
                        raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_candidate_state")
                    session.execute(text(
                        "UPDATE stage_upload SET state = 'cancelled', "
                        "updated_at = clock_timestamp() WHERE stage_upload_id = :upload"
                    ), {"upload": upload_id})
                    session.execute(text(
                        "UPDATE stage_upload_file SET state = 'cancelled', "
                        "updated_at = clock_timestamp() WHERE stage_upload_id = :upload"
                    ), {"upload": upload_id})
                    session.execute(text(
                        "UPDATE stage_upload_candidate SET state = 'failed', "
                        "updated_at = clock_timestamp() "
                        "WHERE stage_upload_file_id IN ("
                        "SELECT stage_upload_file_id FROM stage_upload_file "
                        "WHERE stage_upload_id = :upload) AND state = 'proposed'"
                    ), {"upload": upload_id})
                    self._commands.succeed(session, claim.command_id, {"upload_id": upload_id})
            # The cancelled row and each write-once token are the cleanup
            # journal. A crash or store refusal leaves them for this same call
            # or the explicit sweep to resume after restart.
            self._reconcile_under_lease(upload_id)
            return StageUploadService(self._sessions).get(upload_id)

    def reconcile_cancelled(self, *, upload_id: str) -> int:
        """Abort only temporary multipart objects of a cancelled batch."""
        with upload_process_lease(self._sessions, upload_id):
            return self._reconcile_under_lease(upload_id)

    def _reconcile_under_lease(self, upload_id: str) -> int:
        with session_scope(self._sessions) as session:
            state = session.execute(text(
                "SELECT state FROM stage_upload WHERE stage_upload_id = :upload"
            ), {"upload": upload_id}).scalar_one_or_none()
            if state is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUpload")
            if state != "cancelled":
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_state")
            tokens = tuple(session.execute(text(
                "SELECT multipart_token FROM stage_upload_file "
                "WHERE stage_upload_id = :upload AND multipart_token IS NOT NULL "
                "AND source_blob_id IS NULL ORDER BY stage_upload_file_id"
            ), {"upload": upload_id}).scalars())
        try:
            for token in tokens:
                self._store.abort_multipart(str(token))
        except StorageError as exc:
            raise domain_error_from_storage(exc) from None
        return len(tokens)

    def sweep_cancelled(self, *, limit: int = 100) -> int:
        """Retry cleanup from persisted cancelled batches after process restart."""
        if not 1 <= limit <= 1000:
            raise ValueError("sweep limit must be from 1 to 1000")
        with session_scope(self._sessions) as session:
            ids = tuple(session.execute(text(
                "SELECT DISTINCT u.stage_upload_id FROM stage_upload u "
                "JOIN stage_upload_file f ON f.stage_upload_id = u.stage_upload_id "
                "WHERE u.state = 'cancelled' AND f.multipart_token IS NOT NULL "
                "AND f.source_blob_id IS NULL ORDER BY u.stage_upload_id LIMIT :limit"
            ), {"limit": limit}).scalars())
        for upload_id in ids:
            self.reconcile_cancelled(upload_id=str(upload_id))
        return len(ids)

    def _change(
        self, *, upload_id: str, user_uid: str, idempotency_key: str,
        command: str, from_states: tuple[str, ...], to_state: str,
    ) -> StageUploadRow:
        with upload_process_lease(self._sessions, upload_id):
            with session_scope(self._sessions) as session:
                state = self._owner_state(session, upload_id, user_uid)
                claim = self._commands.begin(
                    session, command_type=command,
                    idempotency_key=IdempotencyKey(idempotency_key),
                    fingerprint=self._fingerprint(command, upload_id, user_uid),
                )
                if isinstance(claim, CommandReplay):
                    return StageUploadService._read(session, upload_id)
                if state not in from_states:
                    raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_state")
                session.execute(text(
                    "UPDATE stage_upload SET state = :state, updated_at = clock_timestamp() "
                    "WHERE stage_upload_id = :upload"
                ), {"state": to_state, "upload": upload_id})
                self._commands.succeed(session, claim.command_id, {"upload_id": upload_id})
                return StageUploadService._read(session, upload_id)

    @staticmethod
    def _owner_state(session: Session, upload_id: str, user_uid: str) -> str:
        row = session.execute(text(
            "SELECT state, actor_user_uid FROM stage_upload "
            "WHERE stage_upload_id = :upload FOR UPDATE"
        ), {"upload": upload_id}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUpload")
        if str(row[1]) != user_uid:
            raise DomainError(ErrorCode.PERMISSION_DENIED)
        return str(row[0])

    @staticmethod
    def _fingerprint(command: str, upload_id: str, user_uid: str):
        return payload_fingerprint({
            "command": f"{command}.v1", "upload_id": upload_id, "user_uid": user_uid,
        })
