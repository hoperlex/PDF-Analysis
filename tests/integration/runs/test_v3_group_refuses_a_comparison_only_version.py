"""`CMP-C0-FIX-01` item 4: the AR v3 group start refuses a comparison-only version by its kind.

A version whose ``upload_kind`` is ``comparison_pdf`` is a plain PDF admitted for comparison (ADR-0025 decision 11): it has
no ``source.document`` entry and no portal block list. ``startRun`` and ``reauditRun`` already refuse it with
``analysis_input_invalid``, reason ``comparison_only_version`` (`CMP-INGEST-01`); ``start_ar_v3_group`` refused it only
by accident of its other checks -- ``version_classification_required`` for an unclassified one, ``missing_required_input``
(a *fault*, where the truth is a *kind*) for a classified one. The refusal is now asked first, right after the version is
read, and writes nothing. The module runs on the lane's migrated PostgreSQL inside a transaction that is rolled back.

Each test is shown failing with the call removed (report section 5).
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.documents.public import (
    MANIFEST_ROLE_COMPARISON_PDF,
    UPLOAD_KIND_COMPARISON_PDF,
    UPLOAD_KIND_PORTAL_BUNDLE,
    DocumentRepository,
    ManifestEntry,
)
from auditmanager.norms.public import SetIdentity
from auditmanager.runs.commands import COMPARISON_ONLY_VERSION_REASON
from auditmanager.runs.v3_group import ReviewedScope, TrustedPack, start_ar_v3_group
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import NormRetrievalSetId
from auditmanager.shared.identity.ids import UserUid
from auditmanager.storage.models import derive_blob_id

PROFILE_ID = "ap_01M5M28ZCDD8VPSP1BTAEW92YE"
BUNDLE_ID = "pb_01M5M28ZCDVCR37BX1884JGSPM"
CHUNKING = "characters-v2:1200"
SHA = "a" * 64
SIZE = 1024
TABLES = ("command_record", "ar_v3_run_group", "audit_run", "job")


def _pack() -> TrustedPack:
    """A pack that passes the group start's own validation; the refusals below come before any norm is read."""
    profile = resolve_beta_v3_profile(PROFILE_ID, BUNDLE_ID)
    scopes = tuple(
        ReviewedScope(
            scope_id=scope_id,
            identity=SetIdentity(
                map_sha256=f"{index:x}" * 64, snapshot_id=profile.snapshot_id,
                reviewed_content_key="ar-v3-beta-synthetic", embedding_build=f"bge-m3-dense-v1:{CHUNKING}",
            ),
            chunking_profile=CHUNKING, set_id=str(NormRetrievalSetId.new()), set_sha256="1" * 64,
        )
        for index, scope_id in enumerate(profile.scopes, 1)
    )
    return TrustedPack(str(profile.analysis_profile_id), str(profile.prompt_bundle_id), scopes)


def _blob(session: Session) -> Any:
    blob_id = derive_blob_id(sha256=SHA, size=SIZE)
    session.execute(text("INSERT INTO blob (blob_id) VALUES (:id) ON CONFLICT DO NOTHING"), {"id": str(blob_id)})
    state = session.execute(text("SELECT state FROM blob WHERE blob_id = :id"), {"id": str(blob_id)}).scalar_one()
    if state == "temporary":
        session.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :id"), {"id": str(blob_id)})
        session.execute(text(
            "UPDATE blob SET state = 'available', sha256 = :sha, size_bytes = :size, "
            "media_type = 'application/pdf' WHERE blob_id = :id"), {"id": str(blob_id), "sha": SHA, "size": SIZE})
    return blob_id


def _version(session: Session, *, kind: str, role: str, section: str | None) -> str:
    """One version of the given kind whose manifest holds one entry of ``role``; classified ``R`` / ``section``
    when a section is given."""
    documents = DocumentRepository()
    project = documents.create_project(session, "AR v3 group, kind check")
    document = documents.create_document(session, project_uid=project.project_uid, display_title="AR")
    version = documents.publish_version(
        session, document_uid=document, media_type="application/pdf", byte_size=SIZE, sha256=SHA, page_count=1,
        source_filename="a.pdf", upload_kind=kind,
        entries=(ManifestEntry(role=role, blob_id=_blob(session), sha256=SHA, size_bytes=SIZE,
                               media_type="application/pdf"),),
    )
    if section is not None:
        actor = str(UserUid.new())
        session.execute(text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, password_salt, "
            "password_hash) VALUES (:id, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"),
            {"id": actor, "login": actor.lower(), "salt": "0" * 32, "hash": "0" * 64})
        documents.insert_classification(
            session, version_uid=version, project_stage="R", section_code=section, confirmed_by_user_uid=actor)
    return str(version)


def _written(session: Session) -> list[int]:
    return [session.execute(text(f"SELECT count(*) FROM {name}")).scalar_one() for name in TABLES]


def _start(session: Session, version_uid: str, key: str) -> None:
    start_ar_v3_group(
        session, version_uid=version_uid, idempotency_key=key, provider_mode="recorded", pack=_pack(),
        input_budget_characters=1000,
    )


def test_a_classified_comparison_only_version_is_refused_by_its_kind_and_nothing_is_written(session: Session) -> None:
    version = _version(session, kind=UPLOAD_KIND_COMPARISON_PDF, role=MANIFEST_ROLE_COMPARISON_PDF, section="AR")
    before = _written(session)
    with pytest.raises(DomainError) as refused:
        _start(session, version, "v3-comparison-only-classified")
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields == {"reason": COMPARISON_ONLY_VERSION_REASON} == {"reason": "comparison_only_version"}
    assert _written(session) == before, "the refusal wrote a command, a group, a run or a job"


def test_an_unclassified_comparison_only_version_is_refused_by_its_kind_before_the_classification_is_asked(
    session: Session,
) -> None:
    version = _version(session, kind=UPLOAD_KIND_COMPARISON_PDF, role=MANIFEST_ROLE_COMPARISON_PDF, section=None)
    with pytest.raises(DomainError) as refused:
        _start(session, version, "v3-comparison-only-unclassified")
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields == {"reason": "comparison_only_version"}


def test_a_comparison_only_version_in_another_section_is_refused_by_its_kind_not_by_its_section(session: Session) -> None:
    version = _version(session, kind=UPLOAD_KIND_COMPARISON_PDF, role=MANIFEST_ROLE_COMPARISON_PDF, section="KJ")
    with pytest.raises(DomainError) as refused:
        _start(session, version, "v3-comparison-only-kj")
    assert refused.value.detail_fields == {"reason": "comparison_only_version"}


def test_the_refusal_is_by_the_kind_alone_a_portal_version_keeps_its_own_answers(session: Session) -> None:
    """The same manifest, the same section, the other kind: the old checks speak as before (nothing is widened)."""
    unclassified = _version(session, kind=UPLOAD_KIND_PORTAL_BUNDLE, role=MANIFEST_ROLE_COMPARISON_PDF, section=None)
    with pytest.raises(DomainError) as refused:
        _start(session, unclassified, "v3-portal-unclassified")
    assert refused.value.code is ErrorCode.VERSION_CLASSIFICATION_REQUIRED

    classified = _version(session, kind=UPLOAD_KIND_PORTAL_BUNDLE, role=MANIFEST_ROLE_COMPARISON_PDF, section="AR")
    with pytest.raises(DomainError) as missing:
        _start(session, classified, "v3-portal-no-source")
    assert missing.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert missing.value.detail_fields == {"reason": "missing_required_input"}
