"""Real child + durable journal before both provider branches, on two-page PDFs.

The invalid-input AR v3 case supplies only the reviewed-pack selection/binding:
no norm content is read because source preparation must fail before that stage.
"""

from __future__ import annotations

import hashlib
import io
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID
from auditmanager.analysis.stages import source_preparation
from auditmanager.documents.public import DocumentRepository, ManifestEntry, MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.runs import execute_run
from auditmanager.runs.commands import cancel_audit_run
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, parse_blob_role
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE, resolve_reference_profile


def _seed(session, store, *, broken=False, v3=False):
    writer = PdfWriter()
    for ordinal in (1, 2):
        page = writer.add_blank_page(width=400, height=500)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        if broken and ordinal == 2:
            font[NameObject("/Subtype")] = NameObject("/Type0")
            font[NameObject("/DescendantFonts")] = ArrayObject()
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): writer._add_object(font),
        })})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 30 400 Td (Source text) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    payload = io.BytesIO()
    writer.write(payload)
    data = payload.getvalue()
    blob = store.put_blob(data, declared_sha256=hashlib.sha256(data).hexdigest(),
                          declared_size=len(data), role=parse_blob_role("source_document"),
                          media_type="application/pdf")
    blobs = BlobMetadataRepository()
    blobs.record_verified(session, VerifiedBlob(
        blob_id=blob.blob_id, upload_token="pdf-precheck-test", sha256=blob.sha256,
        size=blob.size, role=blob.role, media_type=blob.media_type,
    ))
    blobs.mark_available(session, blob.blob_id)
    documents = DocumentRepository()
    project = documents.create_project(session, "PDF precheck test")
    document = documents.create_document(session, project_uid=project.project_uid,
                                          display_title="PDF check", section="AR")
    version = documents.publish_version(
        session, document_uid=document, media_type="application/pdf", byte_size=len(data),
        sha256=blob.sha256, page_count=2, source_filename="source.pdf",
        entries=(ManifestEntry(role=MANIFEST_ROLE_SOURCE_DOCUMENT, blob_id=blob.blob_id,
                               sha256=blob.sha256, size_bytes=blob.size,
                               media_type="application/pdf"),),
    )
    run_id = str(RunId.new())
    RunRepository().create(
        session, run_id=run_id, project_uid=str(project.project_uid), version_uid=str(version),
        analysis_profile_id=str(AR_V3_BETA_PROFILE_ID if v3 else V1_REFERENCE_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(AR_V3_BETA_BUNDLE_ID if v3 else V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id),
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
    )
    return run_id


def _events(session, run_id):
    return session.execute(text(
        "SELECT payload FROM audit_event WHERE aggregate_type='AuditRun' "
        "AND aggregate_id=:run_id AND event_type='stage.pdf_precheck' "
        "ORDER BY occurred_at,audit_event_id"
    ), {"run_id": run_id}).scalars().all()


def test_completed_precheck_is_visible_to_another_session_before_provider_binding(
    engine, blob_store, recorded_adapter, provider_config,
):
    with Session(engine) as session:
        run_id = _seed(session, blob_store)
        session.commit()
        called = []

        def providers(_session, run, context):
            with Session(engine) as observer:
                events = _events(observer, run_id)
                assert events[0]["phase"] == "started"
                assert events[-1]["phase"] == "completed"
                assert events[-1]["completed_pages"] == events[-1]["total_pages"] == 2
                assert any(event["phase"] == "checking" and event["completed_pages"] == 2 for event in events)
                assert RunRepository().stage_statuses(observer, run_id)["source_preparation"] == "succeeded"
            called.append(run.run_id)
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE)

        result = execute_run(
            session, run_id, blob_store=blob_store, adapter=recorded_adapter,
            provider_config=provider_config, providers=providers,
            text_profiles=resolve_reference_profile,
        )
        session.commit()
        assert called == [run_id]
        assert result.stage_statuses["source_preparation"] == "succeeded"
        assert result.model_attempts.attempts == 0


@pytest.mark.parametrize("v3", [False, True], ids=["ordinary", "ar-v3"])
def test_interpreter_refusal_is_durable_and_never_reaches_either_provider_branch(
    engine, blob_store, recorded_adapter, provider_config, monkeypatch, v3,
):
    if v3:
        monkeypatch.setattr(TrustedPackRegistry, "select_beta", lambda self: object())
        from auditmanager.runs import v3_review_terminal
        monkeypatch.setattr(v3_review_terminal, "resolve_v3_execution_binding",
                            lambda *args, **kwargs: SimpleNamespace())
    with Session(engine) as session:
        run_id = _seed(session, blob_store, broken=True, v3=v3)
        session.commit()

        def no_provider(*args, **kwargs):
            pytest.fail("provider binding reached after a PDF interpreter refusal")

        result = execute_run(
            session, run_id, blob_store=blob_store, adapter=recorded_adapter,
            provider_config=provider_config, providers=no_provider,
            text_profiles=resolve_reference_profile,
            ar_v3_pack_registry=TrustedPackRegistry.empty() if v3 else None,
        )
        session.commit()
        assert result.terminal_state == "failed"
        assert result.model_attempts.attempts == 0
        with Session(engine) as observer:
            events = _events(observer, run_id)
            assert events[0]["phase"] == "started"
            assert events[-1]["phase"] == "failed"
            assert events[-1]["completed_pages"] == 1
            assert events[-1]["reason"] == "source_unreadable"
            assert not any(event["phase"] == "completed" for event in events)
            assert RunRepository().stage_statuses(observer, run_id) == {"source_preparation": "failed"}
            assert observer.execute(text("SELECT count(*) FROM model_call WHERE run_id=:run_id"),
                                    {"run_id": run_id}).scalar_one() == 0


def test_cancel_after_a_page_fences_loser_progress_and_never_binds_a_provider(
    engine, blob_store, recorded_adapter, provider_config, monkeypatch,
):
    with Session(engine) as session:
        run_id = _seed(session, blob_store)
        session.commit()
        real_extract = source_preparation.extract_document

        def extract(source, **kwargs):
            report = kwargs["progress"]

            def cancel_after_page(receipt):
                report(receipt)
                if receipt.completed_pages == 1:
                    with Session(engine) as other:
                        cancel_audit_run(other, run_id=run_id, roles=frozenset({"expert"}),
                                         idempotency_key="pdf-precheck-cancel-" + run_id)
                        other.commit()

            return real_extract(source, **{**kwargs, "progress": cancel_after_page})

        monkeypatch.setattr(source_preparation, "extract_document", extract)

        def no_provider(*args, **kwargs):
            pytest.fail("provider reached after cancellation")

        with pytest.raises(DomainError) as raised:
            execute_run(session, run_id, blob_store=blob_store, adapter=recorded_adapter,
                        provider_config=provider_config, providers=no_provider,
                        text_profiles=resolve_reference_profile)
        assert raised.value.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}
        session.rollback()
        with Session(engine) as observer:
            assert RunRepository().get(observer, run_id).state == "cancelled"
            assert not any(event["phase"] in {"completed", "failed"} for event in _events(observer, run_id))
            assert observer.execute(text("SELECT count(*) FROM model_call WHERE run_id=:run_id"),
                                    {"run_id": run_id}).scalar_one() == 0
