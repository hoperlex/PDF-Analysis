"""Raw multipart completion is content-keyed and crash-recoverable."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from collections.abc import Callable

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.stage.completion import StageRawCompletionService
from auditmanager.comparison.stage.uploads import (
    StageDeclaredFile, StageUploadPartService, StageUploadService,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.storage.public import (
    BlobMetadataRepository, BlobNotFoundError, PublishedBlob, TemporaryBlobLostError,
    UploadedPart, VerifiedBlob,
)

def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


class CompletionStore:
    def __init__(self, database: Session, file_id: str) -> None:
        self.database = database
        self.file_id = file_id
        self.completions = 0
        self.lose_after_publish_once = False
        self.published: PublishedBlob | None = None

    def begin_multipart(self, token: str) -> None:
        assert self.database.execute(
            text("SELECT multipart_token FROM stage_upload_file WHERE stage_upload_file_id = :file"),
            {"file": self.file_id},
        ).scalar_one() == token

    def upload_part(self, _token: str, part_number: int, content: bytes) -> UploadedPart:
        return UploadedPart(
            part_number=part_number, size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(), etag="receipt",
        )

    def complete_multipart(
        self, token: str, parts: tuple[UploadedPart, ...], *,
        declared_sha256: str, declared_size: int, role: str, media_type: str,
        before_publish: Callable[[VerifiedBlob], None],
    ) -> PublishedBlob:
        row = self.database.execute(
            text(
                "SELECT f.state, b.state, b.blob_id FROM stage_upload_file f "
                "JOIN blob b ON b.sha256 = f.declared_sha256 "
                "WHERE f.stage_upload_file_id = :file"
            ), {"file": self.file_id},
        ).one()
        assert row[:2] == ("received", "temporary")
        assert len(parts) == 1 and parts[0].size_bytes == declared_size
        assert parts[0].sha256 == declared_sha256
        verified = VerifiedBlob(
            blob_id=row[2], upload_token=token, sha256=declared_sha256,
            size=declared_size, role=role, media_type=media_type,
        )
        before_publish(verified)
        assert self.database.execute(
            text("SELECT state FROM blob WHERE blob_id = :blob"), {"blob": row[2]},
        ).scalar_one() == "verifying"
        self.completions += 1
        self.published = PublishedBlob(
            blob_id=row[2], role=role, media_type=media_type,
            size=declared_size, sha256=declared_sha256, published_at=datetime.now(UTC),
        )
        if self.lose_after_publish_once:
            self.lose_after_publish_once = False
            raise TemporaryBlobLostError()
        return self.published

    def inspect(self, _blob_id: str) -> PublishedBlob:
        if self.published is None:
            raise BlobNotFoundError()
        return self.published


@pytest.mark.parametrize("lost_after_publish", [False, True])
def test_raw_completion_uses_verified_checkpoint_and_replays_without_store(
    comparison_session: Session, lost_after_publish: bool,
) -> None:
    project, actor = uid("prj"), uid("usr")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Raw completion')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    content = b"small-raw-zip-placeholder"
    digest = hashlib.sha256(content).hexdigest()
    upload = StageUploadService(sessions).create(
        project_uid=project,
        files=(StageDeclaredFile("Набор.zip", "zip", len(content), digest),),
        user_uid=actor, idempotency_key=f"stage-create-{new_ulid()}",
    )
    file_id = upload.files[0].file_id
    store = CompletionStore(comparison_session, file_id)
    store.lose_after_publish_once = lost_after_publish
    blobs = BlobMetadataRepository()
    completer = StageRawCompletionService(sessions, store, blobs)
    request = {
        "upload_id": upload.upload_id, "file_id": file_id, "user_uid": actor,
        "idempotency_key": f"stage-raw-{new_ulid()}",
    }
    with pytest.raises(DomainError) as incomplete:
        completer.complete_raw(**request)
    assert incomplete.value.code is ErrorCode.VALIDATION_FAILED
    StageUploadPartService(sessions, store, blobs).put_part(
        upload_id=upload.upload_id, file_id=file_id, part_number=1,
        content=content, user_uid=actor, idempotency_key=f"stage-part-{new_ulid()}",
    )
    completed = completer.complete_raw(**request)
    assert completed.state == "received"
    assert completed.received_bytes == len(content)
    assert store.completions == 1
    assert completer.complete_raw(**request) == completed
    assert completer.complete_raw(**(request | {"idempotency_key": f"stage-raw-replay-{new_ulid()}"})) == completed
    assert store.completions == 1
    assert comparison_session.execute(
        text(
            "SELECT f.source_blob_id, b.state FROM stage_upload_file f "
            "JOIN blob b ON b.blob_id = f.source_blob_id WHERE f.stage_upload_file_id = :file"
        ), {"file": file_id},
    ).one()[1] == "available"
    assert comparison_session.execute(
        text("SELECT state FROM stage_upload_part WHERE stage_upload_file_id = :file"),
        {"file": file_id},
    ).scalar_one() == "completed"
