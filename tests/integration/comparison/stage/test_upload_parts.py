"""A stage part has a durable owner before its bytes move to object storage."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.stage.uploads import (
    StageDeclaredFile, StageUploadPartService, StageUploadService,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.storage.public import (
    BlobMetadataRepository, TemporaryBlobLostError, UploadedPart, declare_blob,
    new_multipart_token, parse_blob_role,
)


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


class RecordingStore:
    def __init__(self, database: Session, file_id: str) -> None:
        self.database = database
        self.file_id = file_id
        self.calls: list[tuple[str, int]] = []
        self.fail_once = False

    def begin_multipart(self, token: str) -> None:
        owner = self.database.execute(
            text(
                "SELECT f.multipart_token, b.state FROM stage_upload_file f "
                "JOIN blob b ON b.sha256 = f.declared_sha256 "
                "WHERE f.stage_upload_file_id = :file"
            ), {"file": self.file_id},
        ).one()
        assert owner == (token, "temporary")
        self.calls.append(("begin", 0))

    def upload_part(self, token: str, part_number: int, content: bytes) -> UploadedPart:
        assert token.startswith("mpu-")
        self.calls.append(("part", part_number))
        if self.fail_once:
            self.fail_once = False
            raise TemporaryBlobLostError()
        return UploadedPart(
            part_number=part_number, size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(), etag="receipt",
        )


def test_part_receipt_replay_and_owner_precede_external_bytes(comparison_session: Session) -> None:
    project, actor = uid("prj"), uid("usr")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage parts')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    content = b"ordinary-pdf-placeholder"
    digest = hashlib.sha256(content).hexdigest()
    created = StageUploadService(sessions).create(
        project_uid=project,
        files=(StageDeclaredFile("Том.pdf", "pdf", len(content), digest),),
        user_uid=actor, idempotency_key=f"stage-create-{new_ulid()}",
    )
    file_id = created.files[0].file_id
    store = RecordingStore(comparison_session, file_id)
    service = StageUploadPartService(sessions, store, BlobMetadataRepository())
    request = {
        "upload_id": created.upload_id, "file_id": file_id, "part_number": 1,
        "content": content, "user_uid": actor,
        "idempotency_key": f"stage-part-{new_ulid()}",
    }
    receipt = service.put_part(**request)
    assert receipt.received_bytes == len(content)
    assert receipt.sha256 == digest
    assert store.calls == [("begin", 0), ("part", 1)]
    assert service.put_part(**request) == receipt
    assert service.put_part(**(request | {"idempotency_key": f"other-{new_ulid()}"})) == receipt
    assert store.calls == [("begin", 0), ("part", 1)]
    assert comparison_session.execute(
        text("SELECT state, size_bytes, sha256, etag FROM stage_upload_part WHERE stage_upload_file_id = :file"),
        {"file": file_id},
    ).one() == ("staged", len(content), digest, "receipt")

    with pytest.raises(DomainError) as reused:
        service.put_part(**(request | {"content": b"different"}))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_storage_refusal_releases_part_for_a_new_key(comparison_session: Session) -> None:
    project, actor = uid("prj"), uid("usr")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage retry')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    content = b"stage-raw"
    created = StageUploadService(sessions).create(
        project_uid=project,
        files=(StageDeclaredFile("Набор.zip", "zip", len(content), hashlib.sha256(content).hexdigest()),),
        user_uid=actor, idempotency_key=f"stage-create-{new_ulid()}",
    )
    file_id = created.files[0].file_id
    store = RecordingStore(comparison_session, file_id)
    service = StageUploadPartService(sessions, store, BlobMetadataRepository())
    request = {
        "upload_id": created.upload_id, "file_id": file_id, "part_number": 1,
        "content": content, "user_uid": actor,
        "idempotency_key": f"stage-part-{new_ulid()}",
    }
    store.fail_once = True
    with pytest.raises(DomainError):
        service.put_part(**request)
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_upload_part WHERE stage_upload_file_id = :file"),
        {"file": file_id},
    ).scalar_one() == 0
    receipt = service.put_part(**(request | {"idempotency_key": f"stage-retry-{new_ulid()}"}))
    assert receipt.received_bytes == len(content)


def test_new_key_replaces_a_stranded_declared_part_only_after_lease_is_free(
    comparison_session: Session,
) -> None:
    project, actor = uid("prj"), uid("usr")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stranded part')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    content = b"new-stage-part"
    digest = hashlib.sha256(content).hexdigest()
    created = StageUploadService(sessions).create(
        project_uid=project,
        files=(StageDeclaredFile("Том.pdf", "pdf", len(content), digest),),
        user_uid=actor, idempotency_key=f"stage-create-{new_ulid()}",
    )
    file_id = created.files[0].file_id
    token = new_multipart_token()
    BlobMetadataRepository().record_declared(
        comparison_session,
        declare_blob(
            sha256=digest, size=len(content), role=parse_blob_role("comparison_stage_raw"),
            media_type="application/pdf",
        ),
    )
    comparison_session.execute(text(
        "UPDATE stage_upload_file SET state = 'receiving', multipart_token = :token "
        "WHERE stage_upload_file_id = :file"
    ), {"token": token, "file": file_id})
    comparison_session.execute(text(
        "INSERT INTO stage_upload_part "
        "(stage_upload_file_id, part_number, state, size_bytes, sha256) "
        "VALUES (:file, 1, 'declared', :size, :digest)"
    ), {"file": file_id, "size": len(content), "digest": digest})
    store = RecordingStore(comparison_session, file_id)
    service = StageUploadPartService(sessions, store, BlobMetadataRepository())
    request = {
        "upload_id": created.upload_id, "file_id": file_id, "part_number": 1,
        "content": content, "user_uid": actor,
        "idempotency_key": f"stage-retry-{new_ulid()}",
    }
    with service._part_lease(file_id, 1):
        with pytest.raises(DomainError) as busy:
            service.put_part(**request)
    assert busy.value.code is ErrorCode.CONFLICT
    assert store.calls == []
    receipt = service.put_part(**request)
    assert receipt.received_bytes == len(content)
    assert store.calls == [("begin", 0), ("part", 1)]
    assert comparison_session.execute(text(
        "SELECT state FROM stage_upload_part WHERE stage_upload_file_id = :file"
    ), {"file": file_id}).scalar_one() == "staged"
