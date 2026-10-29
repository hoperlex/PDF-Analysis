"""Pause and cancellation are keyed; cleanup resumes from durable tokens."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.stage.lifecycle import StageUploadLifecycleService
from auditmanager.comparison.stage.uploads import (
    StageDeclaredFile, StageUploadPartService, StageUploadService,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.storage.public import (
    BlobMetadataRepository, TemporaryBlobLostError, UploadedPart,
)


class Store:
    def __init__(self) -> None:
        self.parts: dict[str, bytes] = {}
        self.aborts: list[str] = []
        self.refuse_abort_once = False

    def begin_multipart(self, token: str) -> None:
        assert token.startswith("mpu-")

    def upload_part(self, token: str, number: int, content: bytes) -> UploadedPart:
        self.parts[token] = content
        return UploadedPart(number, len(content), hashlib.sha256(content).hexdigest(), "receipt")

    def abort_multipart(self, token: str) -> bool:
        if self.refuse_abort_once:
            self.refuse_abort_once = False
            raise TemporaryBlobLostError()
        self.aborts.append(token)
        return self.parts.pop(token, None) is not None


def setup(database: Session):
    project, actor = f"prj_{new_ulid()}", f"usr_{new_ulid()}"
    database.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Lifecycle')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=database.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    content = b"incomplete-stage-upload"
    created = StageUploadService(sessions).create(
        project_uid=project,
        files=(StageDeclaredFile(
            "Том.pdf", "pdf", len(content), hashlib.sha256(content).hexdigest(),
        ),),
        user_uid=actor, idempotency_key=f"create-{new_ulid()}",
    )
    return sessions, created, actor, content


def test_pause_resume_and_cancel_reconcile_staged_multipart(
    comparison_session: Session,
) -> None:
    sessions, created, actor, content = setup(comparison_session)
    store = Store()
    files = StageUploadPartService(sessions, store, BlobMetadataRepository())
    lifecycle = StageUploadLifecycleService(sessions, store)
    upload_id, file_id = created.upload_id, created.files[0].file_id
    files.put_part(
        upload_id=upload_id, file_id=file_id, part_number=1, content=content,
        user_uid=actor, idempotency_key=f"part-{new_ulid()}",
    )
    token = comparison_session.execute(text(
        "SELECT multipart_token FROM stage_upload_file WHERE stage_upload_file_id = :file"
    ), {"file": file_id}).scalar_one()
    pause_key, resume_key, cancel_key = (f"{name}-{new_ulid()}" for name in ("pause", "resume", "cancel"))
    assert lifecycle.pause(upload_id=upload_id, user_uid=actor, idempotency_key=pause_key).state == "paused"
    assert lifecycle.pause(upload_id=upload_id, user_uid=actor, idempotency_key=pause_key).state == "paused"
    with pytest.raises(DomainError) as paused:
        files.put_part(
            upload_id=upload_id, file_id=file_id, part_number=1, content=content,
            user_uid=actor, idempotency_key=f"part-again-{new_ulid()}",
        )
    assert paused.value.code is ErrorCode.CONFLICT
    assert lifecycle.resume(upload_id=upload_id, user_uid=actor, idempotency_key=resume_key).state == "uploading"
    assert lifecycle.cancel(upload_id=upload_id, user_uid=actor, idempotency_key=cancel_key).state == "cancelled"
    assert store.aborts == [token] and store.parts == {}
    assert lifecycle.cancel(upload_id=upload_id, user_uid=actor, idempotency_key=cancel_key).state == "cancelled"
    assert store.aborts == [token, token]
    assert comparison_session.execute(text(
        "SELECT state FROM stage_upload_file WHERE stage_upload_file_id = :file"
    ), {"file": file_id}).scalar_one() == "cancelled"


def test_cancel_cleanup_failure_retries_from_cancelled_row(
    comparison_session: Session,
) -> None:
    sessions, created, actor, content = setup(comparison_session)
    store = Store()
    StageUploadPartService(sessions, store, BlobMetadataRepository()).put_part(
        upload_id=created.upload_id, file_id=created.files[0].file_id,
        part_number=1, content=content, user_uid=actor,
        idempotency_key=f"part-{new_ulid()}",
    )
    lifecycle = StageUploadLifecycleService(sessions, store)
    key = f"cancel-{new_ulid()}"
    store.refuse_abort_once = True
    with pytest.raises(DomainError):
        lifecycle.cancel(upload_id=created.upload_id, user_uid=actor, idempotency_key=key)
    assert StageUploadService(sessions).get(created.upload_id).state == "cancelled"
    assert lifecycle.cancel(upload_id=created.upload_id, user_uid=actor, idempotency_key=key).state == "cancelled"
    assert store.parts == {}
    assert lifecycle.sweep_cancelled() >= 1


def test_non_owner_cannot_pause_upload(comparison_session: Session) -> None:
    sessions, created, _actor, _content = setup(comparison_session)
    lifecycle = StageUploadLifecycleService(sessions, Store())
    with pytest.raises(DomainError) as denied:
        lifecycle.pause(
            upload_id=created.upload_id, user_uid=f"usr_{new_ulid()}",
            idempotency_key=f"pause-{new_ulid()}",
        )
    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    assert StageUploadService(sessions).get(created.upload_id).state == "uploading"
