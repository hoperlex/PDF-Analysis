"""Durable declaration and read side of a C3 stage PDF/ZIP upload.

Declaring a batch moves no bytes. Its files and command outcome commit together;
the installation-wide lock makes the active-upload limit true under concurrency.
Multipart staging and candidate publication use these rows in later commands.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.ingest import domain_error_from_storage
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey, StageUploadFileId, StageUploadId
from auditmanager.storage.public import (
    BlobMetadataRepository, MultipartStaging, StorageError, declare_blob,
    new_multipart_token, parse_blob_role,
)

from .limits import (
    MAX_ACTIVE_ACCOUNT, MAX_ACTIVE_INSTALLATION, MAX_FILES, PART_BYTES, RAW_BATCH_BYTES,
)

__all__ = [
    "StageDeclaredFile", "StageUploadCandidateRow", "StageUploadFileRow",
    "StageUploadRow", "StagePartReceipt", "StageUploadPartService", "StageUploadService",
]

_CREATE_COMMAND = "create_stage_upload"
_PUT_PART_COMMAND = "upload_stage_upload_part"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RAW_ROLE = parse_blob_role("comparison_stage_raw")


@dataclass(frozen=True, slots=True)
class StageDeclaredFile:
    display_name: str
    media_kind: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class StageUploadFileRow:
    file_id: str
    upload_id: str
    declaration: StageDeclaredFile
    state: str
    received_parts: int
    received_bytes: int
    created_at: datetime
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class StageUploadCandidateRow:
    candidate_id: str
    file_id: str
    member_number: int
    display_name: str
    state: str
    proposed_stage: str | None
    proposed_section: str | None
    designation: str | None
    confirmed_stage: str | None
    confirmed_section: str | None
    document_uid: str | None
    version_uid: str | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class StageUploadRow:
    upload_id: str
    project_uid: str
    state: str
    files: tuple[StageUploadFileRow, ...]
    candidates: tuple[StageUploadCandidateRow, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StagePartReceipt:
    upload_id: str
    file_id: str
    part_number: int
    size_bytes: int
    sha256: str
    received_bytes: int


def _display_hint(value: str) -> str:
    clean = "".join(
        "_" if unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} else char
        for char in unicodedata.normalize("NFC", value)
    ).strip()
    if not 1 <= len(clean) <= 255:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="files", constraint="stage_upload_display_name",
        )
    return clean


class StageUploadService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory
        self._commands = CommandRepository()

    @staticmethod
    def _read(session: Session, upload_id: str) -> StageUploadRow:
        upload = session.execute(
            text(
                "SELECT stage_upload_id, project_uid, state, created_at, updated_at "
                "FROM stage_upload WHERE stage_upload_id = :upload"
            ),
            {"upload": upload_id},
        ).first()
        if upload is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUpload")
        files = session.execute(
            text(
                "SELECT f.stage_upload_file_id, f.stage_upload_id, f.display_name, f.media_kind, "
                "f.declared_size_bytes, f.declared_sha256, f.state, f.created_at, f.failure_reason, "
                "count(p.part_number) FILTER (WHERE p.state IN ('staged', 'completed')), "
                "COALESCE(sum(p.size_bytes) FILTER (WHERE p.state IN ('staged', 'completed')), 0) "
                "FROM stage_upload_file f LEFT JOIN stage_upload_part p "
                "ON p.stage_upload_file_id = f.stage_upload_file_id "
                "WHERE f.stage_upload_id = :upload "
                "GROUP BY f.stage_upload_file_id ORDER BY f.created_at, f.stage_upload_file_id"
            ),
            {"upload": upload_id},
        ).all()
        candidates = session.execute(
            text(
                "SELECT c.stage_upload_candidate_id, c.stage_upload_file_id, c.member_number, "
                "c.display_name, c.state, c.proposed_stage, c.proposed_section, c.designation, "
                "c.confirmed_stage, c.confirmed_section, c.document_uid, c.version_uid "
                "FROM stage_upload_candidate c JOIN stage_upload_file f "
                "ON f.stage_upload_file_id = c.stage_upload_file_id "
                "WHERE f.stage_upload_id = :upload ORDER BY c.stage_upload_file_id, c.member_number"
            ),
            {"upload": upload_id},
        ).all()
        return StageUploadRow(
            upload_id=str(upload[0]), project_uid=str(upload[1]), state=str(upload[2]),
            files=tuple(
                StageUploadFileRow(
                    file_id=str(row[0]), upload_id=str(row[1]),
                    declaration=StageDeclaredFile(str(row[2]), str(row[3]), int(row[4]), str(row[5])),
                    state=str(row[6]), created_at=row[7], failure_reason=row[8],
                    received_parts=int(row[9]), received_bytes=int(row[10]),
                )
                for row in files
            ),
            candidates=tuple(StageUploadCandidateRow(*tuple(row), None) for row in candidates),
            created_at=upload[3], updated_at=upload[4],
        )

    def get(self, upload_id: str) -> StageUploadRow:
        with session_scope(self._sessions) as session:
            return self._read(session, upload_id)

    def page(
        self, *, project_uid: str, after_upload_id: str | None, limit: int,
    ) -> tuple[tuple[StageUploadRow, ...], str | None]:
        with session_scope(self._sessions) as session:
            if session.execute(
                text("SELECT 1 FROM project WHERE project_uid = :project"),
                {"project": project_uid},
            ).first() is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Project")
            ids = session.execute(
                text(
                    "SELECT stage_upload_id FROM stage_upload "
                    "WHERE project_uid = :project AND stage_upload_id > :after "
                    "ORDER BY stage_upload_id LIMIT :take"
                ),
                {"project": project_uid, "after": after_upload_id or "", "take": limit + 1},
            ).scalars().all()
            visible = tuple(self._read(session, str(uid)) for uid in ids[:limit])
            return visible, visible[-1].upload_id if len(ids) > limit else None

    def create(
        self, *, project_uid: str, files: tuple[StageDeclaredFile, ...],
        user_uid: str, idempotency_key: str,
    ) -> StageUploadRow:
        if not 1 <= len(files) <= MAX_FILES:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="files", constraint="stage_upload_file_count",
            )
        declared = tuple(
            StageDeclaredFile(
                _display_hint(item.display_name), item.media_kind,
                item.size_bytes, item.sha256,
            ) for item in files
        )
        if any(
            item.media_kind not in ("pdf", "zip") or not 1 <= item.size_bytes <= RAW_BATCH_BYTES
            or _SHA.fullmatch(item.sha256) is None
            for item in declared
        ) or sum(item.size_bytes for item in declared) > RAW_BATCH_BYTES:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="files", constraint="stage_upload_raw_budget",
            )
        fingerprint = payload_fingerprint({
            "command": "create_stage_upload.v1", "project_uid": project_uid,
            "files": [
                [f.display_name, f.media_kind, f.size_bytes, f.sha256] for f in declared
            ],
            "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            if session.execute(
                text("SELECT 1 FROM project WHERE project_uid = :project"),
                {"project": project_uid},
            ).first() is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Project")
            claim = self._commands.begin(
                session, command_type=_CREATE_COMMAND,
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._read(session, str(claim.outcome["upload_id"]))
            session.execute(text("SELECT pg_advisory_xact_lock(hashtext('stage_upload:active'))"))
            mine, total = session.execute(
                text(
                    "SELECT count(*) FILTER (WHERE actor_user_uid = :actor), count(*) "
                    "FROM stage_upload WHERE state IN ('uploading', 'paused', 'admitting')"
                ),
                {"actor": user_uid},
            ).one()
            if int(mine) >= MAX_ACTIVE_ACCOUNT or int(total) >= MAX_ACTIVE_INSTALLATION:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_active")
            upload_id = str(StageUploadId.new())
            session.execute(
                text(
                    "INSERT INTO stage_upload "
                    "(stage_upload_id, project_uid, declared_files, declared_bytes, "
                    "part_size_bytes, actor_user_uid, command_id) "
                    "VALUES (:upload, :project, :files, :bytes, :part, :actor, :command)"
                ),
                {
                    "upload": upload_id, "project": project_uid,
                    "files": len(declared), "bytes": sum(f.size_bytes for f in declared),
                    "part": PART_BYTES, "actor": user_uid, "command": str(claim.command_id),
                },
            )
            for item in declared:
                session.execute(
                    text(
                        "INSERT INTO stage_upload_file "
                        "(stage_upload_file_id, stage_upload_id, media_kind, display_name, "
                        "declared_size_bytes, declared_sha256) "
                        "VALUES (:file, :upload, :kind, :name, :bytes, :sha)"
                    ),
                    {
                        "file": str(StageUploadFileId.new()), "upload": upload_id,
                        "kind": item.media_kind, "name": item.display_name,
                        "bytes": item.size_bytes, "sha": item.sha256,
                    },
                )
            self._commands.succeed(session, claim.command_id, {"upload_id": upload_id})
            return self._read(session, upload_id)


class StageUploadPartService:
    """Write one bounded part with a committed database owner before S3 is called.

    A declared part blocks another writer of the same number until it is either
    receipted or reconciled. A storage refusal removes that declaration so a new
    keyed attempt can resend the bytes. The file token and content-derived Blob
    declaration survive process death and name the bytes for reconciliation.
    """

    def __init__(
        self, session_factory: sessionmaker[Session], store: MultipartStaging,
        blobs: BlobMetadataRepository,
    ) -> None:
        self._sessions = session_factory
        self._store = store
        self._blobs = blobs
        self._commands = CommandRepository()

    def put_part(
        self, *, upload_id: str, file_id: str, part_number: int, content: bytes,
        user_uid: str, idempotency_key: str,
    ) -> StagePartReceipt:
        size = len(content)
        digest = hashlib.sha256(content).hexdigest()
        fingerprint = payload_fingerprint({
            "command": "upload_stage_upload_part.v1", "upload_id": upload_id,
            "file_id": file_id, "part_number": part_number,
            "size_bytes": size, "sha256": digest, "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            claim = self._commands.begin(
                session, command_type=_PUT_PART_COMMAND,
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return StagePartReceipt(**claim.outcome)
            row = session.execute(
                text(
                    "SELECT u.state, f.state, f.declared_size_bytes, f.declared_sha256, "
                    "f.media_kind, f.multipart_token, f.source_blob_id "
                    "FROM stage_upload_file f JOIN stage_upload u ON u.stage_upload_id = f.stage_upload_id "
                    "WHERE u.stage_upload_id = :upload AND f.stage_upload_file_id = :file "
                    "FOR UPDATE OF u, f"
                ),
                {"upload": upload_id, "file": file_id},
            ).first()
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadFile")
            upload_state, file_state, declared_size, declared_sha, kind, token, source_blob_id = row
            if upload_state != "uploading" or file_state not in ("declared", "receiving") or source_blob_id is not None:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_state")
            needed = (int(declared_size) + PART_BYTES - 1) // PART_BYTES
            expected = PART_BYTES if part_number < needed else int(declared_size) - PART_BYTES * (needed - 1)
            if not 1 <= part_number <= needed or size != expected:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="content", constraint="stage_upload_part_size",
                )
            existing = session.execute(
                text(
                    "SELECT state, size_bytes, sha256 FROM stage_upload_part "
                    "WHERE stage_upload_file_id = :file AND part_number = :number FOR UPDATE"
                ),
                {"file": file_id, "number": part_number},
            ).first()
            if existing is not None and existing[0] == "declared":
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_part_in_progress")
            if existing is not None and existing[0] == "staged" and existing[1] == size and existing[2] == digest:
                received = self._received_bytes(session, file_id)
                receipt = StagePartReceipt(upload_id, file_id, part_number, size, digest, received)
                self._commands.succeed(session, claim.command_id, {
                    "upload_id": upload_id, "file_id": file_id, "part_number": part_number,
                    "size_bytes": size, "sha256": digest, "received_bytes": received,
                })
                return receipt
            if token is None:
                declaration = declare_blob(
                    sha256=str(declared_sha), size=int(declared_size), role=_RAW_ROLE,
                    media_type="application/zip" if kind == "zip" else "application/pdf",
                )
                self._blobs.record_declared(session, declaration)
                token = new_multipart_token()
                session.execute(
                    text(
                        "UPDATE stage_upload_file SET multipart_token = :token, state = 'receiving', "
                        "updated_at = clock_timestamp() WHERE stage_upload_file_id = :file"
                    ), {"token": token, "file": file_id},
                )
            if existing is None:
                session.execute(
                    text(
                        "INSERT INTO stage_upload_part "
                        "(stage_upload_file_id, part_number, state, size_bytes, sha256) "
                        "VALUES (:file, :number, 'declared', :size, :sha)"
                    ), {"file": file_id, "number": part_number, "size": size, "sha": digest},
                )
            else:
                session.execute(
                    text(
                        "UPDATE stage_upload_part SET state = 'declared', size_bytes = :size, "
                        "sha256 = :sha, etag = NULL, updated_at = clock_timestamp() "
                        "WHERE stage_upload_file_id = :file AND part_number = :number"
                    ), {"file": file_id, "number": part_number, "size": size, "sha": digest},
                )
            command_id = claim.command_id

        try:
            self._store.begin_multipart(str(token))
            staged = self._store.upload_part(str(token), part_number, content)
        except StorageError as exc:
            refusal = domain_error_from_storage(exc)
            with session_scope(self._sessions) as session:
                session.execute(
                    text(
                        "DELETE FROM stage_upload_part WHERE stage_upload_file_id = :file "
                        "AND part_number = :number AND state = 'declared' AND sha256 = :sha"
                    ), {"file": file_id, "number": part_number, "sha": digest},
                )
                self._commands.fail(session, command_id, refusal.code)
            raise refusal from None

        if staged.sha256 != digest or staged.size_bytes != size:
            raise RuntimeError("multipart staging returned facts different from the sent part")
        with session_scope(self._sessions) as session:
            changed = session.execute(
                text(
                    "UPDATE stage_upload_part SET state = 'staged', size_bytes = :size, "
                    "sha256 = :sha, etag = :etag, updated_at = clock_timestamp() "
                    "WHERE stage_upload_file_id = :file AND part_number = :number "
                    "AND state = 'declared' AND sha256 = :sha"
                ),
                {"file": file_id, "number": part_number, "size": size,
                 "sha": digest, "etag": staged.etag},
            ).rowcount
            if changed != 1:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_part_state")
            received = self._received_bytes(session, file_id)
            receipt = StagePartReceipt(upload_id, file_id, part_number, size, digest, received)
            self._commands.succeed(session, command_id, {
                "upload_id": upload_id, "file_id": file_id, "part_number": part_number,
                "size_bytes": size, "sha256": digest, "received_bytes": received,
            })
            session.execute(
                text("UPDATE stage_upload SET updated_at = clock_timestamp() WHERE stage_upload_id = :upload"),
                {"upload": upload_id},
            )
            return receipt

    @staticmethod
    def _received_bytes(session: Session, file_id: str) -> int:
        return int(session.execute(
            text(
                "SELECT COALESCE(sum(size_bytes), 0) FROM stage_upload_part "
                "WHERE stage_upload_file_id = :file AND state = 'staged'"
            ), {"file": file_id},
        ).scalar_one())
