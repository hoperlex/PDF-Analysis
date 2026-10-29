"""Verify a stage upload's raw multipart object before PDF/ZIP admission.

This is an internal step. The public completion operation remains sealed until
the validated candidate rows and their recovery path are implemented too.
"""

from __future__ import annotations

from typing import NoReturn, Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest import domain_error_from_storage
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId, IdempotencyKey
from auditmanager.storage.public import (
    BlobIntegrityError, BlobMetadataRepository, BlobNotFoundError, BlobStore,
    MultipartStaging, StorageError, TemporaryBlobLostError, UploadedPart,
    VerifiedBlob, declare_blob, parse_blob_id, parse_blob_role,
)

from .limits import PART_BYTES
from .uploads import StageUploadFileRow, StageUploadService

__all__ = ["StageRawCompletionService", "StageRawStore"]

_COMMAND = "stage_raw_completion"
_RAW_ROLE = parse_blob_role("comparison_stage_raw")


class StageRawStore(BlobStore, MultipartStaging, Protocol):
    """The ordinary Blob read and multipart publication ports on one store."""


class StageRawCompletionService:
    def __init__(
        self, session_factory: sessionmaker[Session], store: StageRawStore,
        blobs: BlobMetadataRepository,
    ) -> None:
        self._sessions = session_factory
        self._store = store
        self._blobs = blobs
        self._commands = CommandRepository()

    @staticmethod
    def _file(session: Session, upload_id: str, file_id: str) -> StageUploadFileRow:
        upload = StageUploadService._read(session, upload_id)
        for item in upload.files:
            if item.file_id == file_id:
                return item
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadFile")

    def complete_raw(
        self, *, upload_id: str, file_id: str, user_uid: str, idempotency_key: str,
    ) -> StageUploadFileRow:
        """Publish only the measured raw object; no member or document is admitted here."""
        fingerprint = payload_fingerprint({
            "command": "complete_stage_upload_file.raw.v1", "upload_id": upload_id,
            "file_id": file_id, "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            claim = self._commands.begin(
                session, command_type=_COMMAND, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._file(session, upload_id, file_id)
            row = session.execute(
                text(
                    "SELECT u.state, f.state, f.multipart_token, f.source_blob_id, "
                    "f.declared_sha256, f.declared_size_bytes, f.media_kind "
                    "FROM stage_upload_file f JOIN stage_upload u ON u.stage_upload_id = f.stage_upload_id "
                    "WHERE u.stage_upload_id = :upload AND f.stage_upload_file_id = :file "
                    "FOR UPDATE OF u, f"
                ), {"upload": upload_id, "file": file_id},
            ).first()
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadFile")
            upload_state, file_state, token, source_blob_id, digest, size, kind = row
            if upload_state != "uploading" or file_state not in ("declared", "receiving", "received"):
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_state")
            if token is None:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="parts", constraint="stage_upload_parts_complete",
                )
            declaration = declare_blob(
                sha256=str(digest), size=int(size), role=_RAW_ROLE,
                media_type="application/zip" if kind == "zip" else "application/pdf",
            )
            if source_blob_id is not None:
                if str(source_blob_id) != str(declaration.blob_id) or not self._blobs.require(
                    session, declaration.blob_id,
                ).is_available:
                    raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="comparison_stage_raw")
                self._commands.succeed(session, claim.command_id, {"file_id": file_id})
                return self._file(session, upload_id, file_id)
            parts = session.execute(
                text(
                    "SELECT part_number, state, size_bytes, sha256, etag FROM stage_upload_part "
                    "WHERE stage_upload_file_id = :file ORDER BY part_number"
                ), {"file": file_id},
            ).all()
            needed = (int(size) + PART_BYTES - 1) // PART_BYTES
            if (
                len(parts) != needed
                or [int(part[0]) for part in parts] != list(range(1, needed + 1))
                or any(part[1] != "staged" for part in parts)
                or sum(int(part[2]) for part in parts) != int(size)
            ):
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="parts", constraint="stage_upload_parts_complete",
                )
            offered = tuple(
                UploadedPart(int(number), int(part_size), str(part_sha), str(etag))
                for number, _state, part_size, part_sha, etag in parts
            )
            session.execute(
                text(
                    "UPDATE stage_upload_file SET state = 'received', updated_at = clock_timestamp() "
                    "WHERE stage_upload_file_id = :file"
                ), {"file": file_id},
            )
            command_id = claim.command_id

        if source_blob_id is None:
            def checkpoint(verified: VerifiedBlob) -> None:
                with session_scope(self._sessions) as session:
                    self._blobs.record_verified(session, verified)

            try:
                self._store.complete_multipart(
                    str(token), offered, declared_sha256=str(digest), declared_size=int(size),
                    role=_RAW_ROLE, media_type=declaration.media_type,
                    before_publish=checkpoint,
                )
            except TemporaryBlobLostError as exc:
                try:
                    self._store.inspect(declaration.blob_id)
                except BlobNotFoundError:
                    self._fail(command_id, file_id, domain_error_from_storage(exc), terminal=True)
                except StorageError as inner:
                    self._fail(command_id, file_id, domain_error_from_storage(inner))
            except BlobIntegrityError as exc:
                self._fail(command_id, file_id, domain_error_from_storage(exc), terminal=True)
            except StorageError as exc:
                self._fail(command_id, file_id, domain_error_from_storage(exc))

        with session_scope(self._sessions) as session:
            self._blobs.mark_available(session, parse_blob_id(str(declaration.blob_id)))
            session.execute(
                text(
                    "UPDATE stage_upload_file SET source_blob_id = :blob, state = 'received', "
                    "updated_at = clock_timestamp() WHERE stage_upload_file_id = :file "
                    "AND (source_blob_id IS NULL OR source_blob_id = :blob)"
                ), {"blob": str(declaration.blob_id), "file": file_id},
            )
            session.execute(
                text(
                    "UPDATE stage_upload_part SET state = 'completed', updated_at = clock_timestamp() "
                    "WHERE stage_upload_file_id = :file AND state = 'staged'"
                ), {"file": file_id},
            )
            self._commands.succeed(session, command_id, {"file_id": file_id})
            return self._file(session, upload_id, file_id)

    def _fail(
        self, command_id: CommandId, file_id: str, refusal: DomainError, *, terminal: bool = False,
    ) -> NoReturn:
        with session_scope(self._sessions) as session:
            if terminal:
                session.execute(
                    text(
                        "UPDATE stage_upload_file SET state = 'failed', failure_reason = :reason, "
                        "updated_at = clock_timestamp() WHERE stage_upload_file_id = :file"
                    ), {"file": file_id, "reason": refusal.code.value},
                )
            self._commands.fail(session, command_id, refusal.code)
        raise refusal
