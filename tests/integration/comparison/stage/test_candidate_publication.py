"""Candidate PDF publication survives retry at both external-effect seams."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.stage.admission import StageCandidateAdmissionService
from auditmanager.comparison.stage.candidates import StageCandidateDecisionService
from auditmanager.comparison.stage.publication import StageCandidatePublicationService
from auditmanager.shared.identity import new_ulid
from auditmanager.storage.public import (
    BlobNotFoundError, PublishedBlob, TemporaryBlob, VerifiedBlob, declare_blob,
    parse_blob_role,
)

from tests.integration.comparison.stage.test_upload_admission import (
    PDF, RawStreamStore, archive, ready_raw,
)


class Store(RawStreamStore):
    def __init__(self, content: bytes, *, fail_after_publish: bool = False) -> None:
        super().__init__(content)
        self.canonical: dict[str, bytes] = {}
        self.temporary: dict[str, bytes] = {}
        self.stages = 0
        self.fail_after_publish = fail_after_publish
        raw = declare_blob(
            sha256=hashlib.sha256(content).hexdigest(), size=len(content),
            role=parse_blob_role("comparison_stage_raw"),
            media_type="application/zip" if content[:2] == b"PK" else "application/pdf",
        )
        self.canonical[str(raw.blob_id)] = content

    def inspect(self, blob_id: str) -> PublishedBlob:
        try:
            content = self.canonical[str(blob_id)]
        except KeyError:
            raise BlobNotFoundError(str(blob_id)) from None
        return PublishedBlob(
            blob_id=blob_id, role=parse_blob_role("comparison_stage_raw"),
            media_type="application/pdf", size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            published_at=datetime.now(timezone.utc),
        )

    def temporary_exists(self, temporary: TemporaryBlob) -> bool:
        return temporary.upload_token in self.temporary

    def stage_temporary(
        self, source, *, declared_sha256: str, declared_size: int,
        role, media_type: str, upload_token: str,
    ) -> TemporaryBlob:
        content = source.read()
        self.stages += 1
        self.temporary[upload_token] = content
        return TemporaryBlob(upload_token, declared_sha256, declared_size, role, media_type)

    def verify_temporary(self, temporary: TemporaryBlob) -> VerifiedBlob:
        content = self.temporary[temporary.upload_token]
        assert len(content) == temporary.declared_size
        assert hashlib.sha256(content).hexdigest() == temporary.declared_sha256
        declared = declare_blob(
            sha256=temporary.declared_sha256, size=temporary.declared_size,
            role=temporary.role, media_type=temporary.media_type,
        )
        return VerifiedBlob(
            declared.blob_id, temporary.upload_token, declared.sha256,
            declared.size, declared.role, declared.media_type,
        )

    def publish(self, verified: VerifiedBlob) -> PublishedBlob:
        content = self.temporary.pop(verified.upload_token)
        self.canonical[str(verified.blob_id)] = content
        if self.fail_after_publish:
            self.fail_after_publish = False
            raise RuntimeError("process stopped after canonical publication")
        return self.inspect(verified.blob_id)


def confirmed(database: Session, *, kind: str, content: bytes):
    sessions, upload_id, file_id = ready_raw(database, kind=kind, content=content)
    store = Store(content)
    proposed = StageCandidateAdmissionService(sessions, store).admit(
        upload_id=upload_id, file_id=file_id,
    )[0]
    actor = f"usr_{new_ulid()}"
    database.execute(text(
        "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
        "password_salt, password_hash) VALUES "
        "(:actor, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
    ), {
        "actor": actor, "login": f"stage-{new_ulid().lower()}",
        "salt": "a" * 32, "hash": "b" * 64,
    })
    confirmed = StageCandidateDecisionService(sessions).confirm(
        candidate_id=proposed.candidate_id, stage="P", section_code="AR",
        designation="АР-01", existing_document_uid=None,
        user_uid=actor, actor_roles=frozenset({"expert"}),
        idempotency_key=f"stage-confirm-{new_ulid()}",
    )
    return sessions, store, confirmed


def assert_version(database: Session, candidate_id: str) -> None:
    row = database.execute(text(
        "SELECT c.state, c.document_uid, c.version_uid, c.pdf_blob_id, "
        "v.sha256, v.upload_kind, k.project_stage, k.section_code "
        "FROM stage_upload_candidate c "
        "JOIN document_version v ON v.version_uid = c.version_uid "
        "JOIN version_classification_current k ON k.version_uid = v.version_uid "
        "WHERE c.stage_upload_candidate_id = :candidate"
    ), {"candidate": candidate_id}).one()
    assert row[0] == "published"
    assert row[1].startswith("doc_") and row[2].startswith("ver_")
    assert row[3].startswith("blob_")
    assert row[4] == hashlib.sha256(PDF).hexdigest()
    assert (row[5], row[6], row[7]) == ("comparison_pdf", "P", "AR")


def test_plain_pdf_reuses_verified_raw_blob_and_publishes_once(
    comparison_session: Session,
) -> None:
    sessions, store, candidate = confirmed(comparison_session, kind="pdf", content=PDF)
    service = StageCandidatePublicationService(sessions, store)
    published = service.publish(candidate_id=candidate.candidate_id)
    assert_version(comparison_session, candidate.candidate_id)
    assert service.publish(candidate_id=candidate.candidate_id) == published
    assert store.stages == 0
    assert comparison_session.execute(text(
        "SELECT count(*) FROM document_version WHERE document_uid = :document"
    ), {"document": published.document_uid}).scalar_one() == 1


def test_zip_member_publication_recovers_after_canonical_copy(
    comparison_session: Session,
) -> None:
    content = archive(("П/АР-01.pdf", PDF))
    sessions, store, candidate = confirmed(comparison_session, kind="zip", content=content)
    store.fail_after_publish = True
    service = StageCandidatePublicationService(sessions, store)
    with pytest.raises(RuntimeError, match="process stopped"):
        service.publish(candidate_id=candidate.candidate_id)
    assert comparison_session.execute(text(
        "SELECT state FROM stage_upload_candidate WHERE stage_upload_candidate_id = :candidate"
    ), {"candidate": candidate.candidate_id}).scalar_one() == "admitting"
    published = service.publish(candidate_id=candidate.candidate_id)
    assert_version(comparison_session, candidate.candidate_id)
    assert store.stages == 1
    assert service.publish(candidate_id=candidate.candidate_id) == published
    assert store.temporary == {}
