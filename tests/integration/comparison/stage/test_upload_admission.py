"""The first stage ZIP caller admits a whole validated set or no candidates."""

from __future__ import annotations

import hashlib
import io
import tempfile
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.stage.admission import StageCandidateAdmissionService
from auditmanager.comparison.stage.uploads import StageDeclaredFile, StageUploadService
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.storage.public import (
    BlobMetadataRepository, VerifiedBlob, declare_blob, new_multipart_token,
    parse_blob_role,
)

PDF = Path("tests/e2e/pc01/journey/fixtures/w28-live/w28_own_document.pdf").read_bytes()


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def archive(*members: tuple[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as writer:
        for name, data in members:
            writer.writestr(name, data)
    return output.getvalue()


class RawStreamStore:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.reads = 0

    def open_stream(self, _blob_id: str, *, expected_sha256: str, expected_size: int):
        assert len(self.content) == expected_size
        assert hashlib.sha256(self.content).hexdigest() == expected_sha256
        self.reads += 1

        def chunks():
            for offset in range(0, len(self.content), 997):
                yield self.content[offset:offset + 997]

        return chunks()


def ready_raw(
    database: Session, *, kind: str, content: bytes,
) -> tuple[sessionmaker[Session], str, str]:
    project, actor = uid("prj"), uid("usr")
    database.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Stage admission')"),
        {"project": project},
    )
    sessions = sessionmaker(
        bind=database.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    digest = hashlib.sha256(content).hexdigest()
    created = StageUploadService(sessions).create(
        project_uid=project,
        files=(StageDeclaredFile(f"Набор.{kind}", kind, len(content), digest),),
        user_uid=actor, idempotency_key=f"stage-create-{new_ulid()}",
    )
    file_id = created.files[0].file_id
    role = parse_blob_role("comparison_stage_raw")
    declared = declare_blob(
        sha256=digest, size=len(content), role=role,
        media_type="application/zip" if kind == "zip" else "application/pdf",
    )
    blobs = BlobMetadataRepository()
    blobs.record_declared(database, declared)
    blobs.record_verified(database, VerifiedBlob(
        blob_id=declared.blob_id, upload_token=new_multipart_token(),
        sha256=digest, size=len(content), role=role, media_type=declared.media_type,
    ))
    blobs.mark_available(database, declared.blob_id)
    database.execute(
        text(
            "UPDATE stage_upload_file SET state = 'received', source_blob_id = :blob "
            "WHERE stage_upload_file_id = :file"
        ), {"blob": str(declared.blob_id), "file": file_id},
    )
    return sessions, created.upload_id, file_id


def test_plain_pdf_becomes_one_proposed_candidate_after_envelope(comparison_session: Session) -> None:
    sessions, upload_id, file_id = ready_raw(comparison_session, kind="pdf", content=PDF)
    store = RawStreamStore(PDF)
    admitted = StageCandidateAdmissionService(sessions, store).admit(
        upload_id=upload_id, file_id=file_id,
    )
    assert len(admitted) == 1
    assert admitted[0].member_number == 1
    assert admitted[0].state == "proposed"
    assert admitted[0].document_uid is None
    assert store.reads == 1
    assert StageCandidateAdmissionService(sessions, store).admit(
        upload_id=upload_id, file_id=file_id,
    ) == admitted
    assert store.reads == 1
    facts = comparison_session.execute(
        text(
            "SELECT pdf_facts FROM stage_upload_candidate "
            "WHERE stage_upload_candidate_id = :candidate"
        ), {"candidate": admitted[0].candidate_id},
    ).scalar_one()
    assert facts["page_count"] >= 1
    assert facts["member_sha256"] == hashlib.sha256(PDF).hexdigest()
    assert facts["member_size"] == len(PDF)
    assert comparison_session.execute(
        text("SELECT state FROM stage_upload WHERE stage_upload_id = :upload"),
        {"upload": upload_id},
    ).scalar_one() == "completed"


def test_process_lease_refuses_a_second_admission_and_recovers_a_dead_one(
    comparison_session: Session,
) -> None:
    sessions, upload_id, file_id = ready_raw(comparison_session, kind="pdf", content=PDF)
    service = StageCandidateAdmissionService(sessions, RawStreamStore(PDF))
    with service._lease():
        with pytest.raises(DomainError) as busy:
            service.admit(upload_id=upload_id, file_id=file_id)
    assert busy.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert comparison_session.execute(
        text("SELECT state FROM stage_upload_file WHERE stage_upload_file_id = :file"),
        {"file": file_id},
    ).scalar_one() == "received"

    comparison_session.execute(
        text("UPDATE stage_upload_file SET state = 'admitting' WHERE stage_upload_file_id = :file"),
        {"file": file_id},
    )
    comparison_session.execute(
        text("UPDATE stage_upload SET state = 'admitting' WHERE stage_upload_id = :upload"),
        {"upload": upload_id},
    )
    assert len(service.admit(upload_id=upload_id, file_id=file_id)) == 1


def test_zip_set_commits_all_candidates_after_every_pdf_passes(
    comparison_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = tmp_path / "stage-admission"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    content = archive(("П/Лист 1.pdf", PDF), ("Р/Лист 1.pdf", PDF))
    sessions, upload_id, file_id = ready_raw(comparison_session, kind="zip", content=content)
    admitted = StageCandidateAdmissionService(sessions, RawStreamStore(content)).admit(
        upload_id=upload_id, file_id=file_id,
    )
    assert [(item.member_number, item.display_name) for item in admitted] == [
        (1, "Лист 1.pdf"), (2, "Лист 1.pdf"),
    ]
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_upload_candidate WHERE pdf_blob_id IS NOT NULL AND stage_upload_file_id = :file"),
        {"file": file_id},
    ).scalar_one() == 0
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("members", [
    (("__MACOSX/hidden.pdf", PDF),),
    (("good.pdf", PDF), ("bad.pdf", b"%PDF-1.7\nnot a readable document")),
])
def test_refused_zip_set_leaves_no_candidate_and_releases_temp_files(
    comparison_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    members: tuple[tuple[str, bytes], ...],
) -> None:
    temporary = tmp_path / "stage-refused"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    content = archive(*members)
    sessions, upload_id, file_id = ready_raw(comparison_session, kind="zip", content=content)
    with pytest.raises(DomainError) as refused:
        StageCandidateAdmissionService(sessions, RawStreamStore(content)).admit(
            upload_id=upload_id, file_id=file_id,
        )
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_upload_candidate WHERE stage_upload_file_id = :file"),
        {"file": file_id},
    ).scalar_one() == 0
    assert comparison_session.execute(
        text("SELECT state FROM stage_upload_file WHERE stage_upload_file_id = :file"),
        {"file": file_id},
    ).scalar_one() == "failed"
    assert list(temporary.iterdir()) == []
