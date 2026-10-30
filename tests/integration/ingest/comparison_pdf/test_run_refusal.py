"""Ordinary section runs accept a classified comparison PDF as their source."""

from __future__ import annotations

import pytest

from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.comparison_pdf.public import ConfirmedFile
from auditmanager.runs import RunRepository, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey
from tests.integration.ingest.comparison_pdf.support import EXPERT, upload_batch, vs1

PROFILE = "ap_01ARZ3NDEKTSV4RRFFQ69G5FAV"
BUNDLE = "pb_01ARZ3NDEKTSV4RRFFQ69G5FAV"


@pytest.fixture
def comparison_version(comparison, project, user, session_factory):
    view = upload_batch(comparison, str(project.project_uid), {"a.pdf": vs1()["v1.pdf"]}, user=user)
    proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
    done = comparison.confirm_set(
        upload_id=view.upload_id, set_id=proposed.set_id, files=[ConfirmedFile(f.file_id) for f in proposed.files],
        designation=None, existing_document_uid=None, project_stage="R", section_code="AR", user_uid=user,
        actor_roles=EXPERT, idempotency_key="confirm")
    with session_factory() as session:
        return DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))[0]


class TestSectionRunOnComparisonPdf:
    def test_source_manifest_role_is_adapted_for_ordinary_run(self, comparison_version):
        from auditmanager.runs.commands import _resolve_references

        _version, blobs = _resolve_references(
            None, version_uid=comparison_version.version_uid, analysis_profile_id=PROFILE,
            prompt_bundle_id=BUNDLE, documents=DocumentRepository(), version=comparison_version,
        )
        assert blobs["source.document"] == blobs["comparison.source_pdf"]

    def test_start_creates_run_for_classified_comparison_pdf(self, comparison_version, session_factory):
        with session_factory() as session:
            started = start_audit_run(
                session, version_uid=comparison_version.version_uid, analysis_profile_id=PROFILE,
                prompt_bundle_id=BUNDLE, provider_mode="recorded", idempotency_key=IdempotencyKey("start-1"),
            )
            session.commit()
        with session_factory() as session:
            run = RunRepository().get(session, started.run_id)
            assert run.version_uid == str(comparison_version.version_uid)
            assert run.frozen_input_digest

    def test_six_check_group_still_needs_portal_inputs(self, comparison_version):
        from auditmanager.runs.commands import refuse_comparison_only_version

        with pytest.raises(DomainError) as refused:
            refuse_comparison_only_version(comparison_version)
        assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
        assert refused.value.detail_fields == {"reason": "comparison_only_version"}
