"""W57b saved PDF text read against real PostgreSQL and private S3.

The executor is intercepted after its saved source StageResult is bound and
before any provider dispatch. The fixture PDF has no embedded text on either
page, although the companion portal bundle carries recognised text.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy import text

import auditmanager.runs.executor as executor
from auditmanager.analysis.public import (
    AR_V2_RECORDED_BUNDLE_ID,
    AR_V2_RECORDED_PROFILE_ID,
    RecordedGenerationSettings,
)
from auditmanager.analysis.recognised.markdown import read_blocks
from auditmanager.documents.public import (
    MANIFEST_ROLE_MARKDOWN,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    MANIFEST_ROLE_STRUCTURED_COMPANION,
    DocumentRepository,
    ManifestEntry,
)
from auditmanager.norms.references.text_pages import reference_pages_from_text_layer
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.runs.reference_text_input import load_saved_reference_text
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_role
from tests.integration.analysis.recognised.recognised_support import members


SETTINGS = RecordedGenerationSettings(4096, "high", {"type": "adaptive"})


class _TextInspected(Exception):
    """Stop after source custody, before any provider or finding effect."""


def _publish(session, blob_store, payload: bytes, *, role: str, media_type: str):
    published = blob_store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=parse_blob_role(role),
        media_type=media_type,
    )
    blobs = BlobMetadataRepository()
    blobs.record_verified(
        session,
        VerifiedBlob(
            blob_id=published.blob_id,
            upload_token=f"w57b-text-accept-{role}",
            sha256=published.sha256,
            size=published.size,
            role=published.role,
            media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)
    return published


def _seed_version(session, blob_store, bundle) -> str:
    entries = []
    for manifest_role, blob_role, media_type, payload in (
        (MANIFEST_ROLE_SOURCE_DOCUMENT, "source_document", "application/pdf", bundle.pdf),
        (MANIFEST_ROLE_STRUCTURED_COMPANION, "source_structured_companion", "application/json", bundle.block_list),
        (MANIFEST_ROLE_MARKDOWN, "source_markdown", "text/markdown", bundle.markdown),
    ):
        published = _publish(
            session, blob_store, payload, role=blob_role, media_type=media_type,
        )
        entries.append(ManifestEntry(
            role=manifest_role,
            blob_id=published.blob_id,
            sha256=published.sha256,
            size_bytes=published.size,
            media_type=published.media_type,
        ))
    documents = DocumentRepository()
    project = documents.create_project(session, "Синтетический W57b проект")
    document_uid = documents.create_document(
        session, project_uid=project.project_uid,
        display_title="Сканированный АР", section="AR",
    )
    bodies = read_blocks(bundle.markdown.decode("utf-8"))
    assert len(bodies) == 2 and all(block.label == "text" and block.body for block in bodies)
    version_uid = documents.publish_version(
        session,
        document_uid=document_uid,
        media_type="application/pdf",
        byte_size=len(bundle.pdf),
        sha256=sha256_of(bundle.pdf),
        page_count=2,
        source_filename="image_only_with_block.pdf",
        entries=tuple(entries),
        text_character_count=0,
        textless_pages=(1, 2),
        recognised_character_count=sum(len(block.body) for block in bodies),
    )
    return str(version_uid)


def test_current_attempt_reads_saved_pdf_text_but_never_ocr(
    session, blob_store, recorded_adapter, provider_config, new_key, monkeypatch,
) -> None:
    bundle = members("image_only_with_block.zip")
    assert b"BLOCK" in bundle.markdown
    version_uid = _seed_version(session, blob_store, bundle)
    started = start_audit_run(
        session,
        version_uid=version_uid,
        analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
        prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
        provider_mode="recorded",
        idempotency_key=new_key("w57b-text-db-s3-accept"),
    )
    run_id = str(started.run_id)
    seen = []
    production_store = executor._publication_store

    def inspect_saved_source(
        worker_session, *, store, jobs, blobs, authority, stage_id, checkpoint=None,
    ):
        if stage_id != "document_context_build":
            return production_store(
                worker_session, store=store, jobs=jobs, blobs=blobs,
                authority=authority, stage_id=stage_id, checkpoint=checkpoint,
            )
        stage = next(
            row for row in RunRepository().stage_results(worker_session, run_id)
            if row.stage_id == "source_preparation"
        )
        assert stage.status == "succeeded"
        text_ref = next(
            ref for ref in stage.artifacts if ref["role"] == "prepared.text_layer"
        )
        bound = worker_session.execute(text(
            "SELECT count(*) FROM analysis_artifact_publication "
            "WHERE run_id = :run_id AND attempt_id = :attempt_id "
            "AND stage_id = 'source_preparation' AND blob_id = :blob_id "
            "AND state = 'bound'"
        ), {
            "run_id": run_id,
            "attempt_id": authority.attempt_id,
            "blob_id": text_ref["blob_id"],
        }).scalar_one()
        assert bound == 1

        checked = load_saved_reference_text(
            worker_session,
            authority=authority,
            blob_store=store,
            max_input_bytes=text_ref["size_bytes"],
        )
        assert checked.version_uid == version_uid
        assert checked.page_count == 2
        assert checked.text_layer.document_text == ""
        assert len(checked.text_layer.pages) == 2
        assert [page.text for page in checked.text_layer.pages] == ["", ""]
        pages = reference_pages_from_text_layer(
            text_layer=checked.text_layer,
            version_uid=checked.version_uid,
            page_count=checked.page_count,
        )
        assert [(page.page_number, page.char_start, page.text) for page in pages] == [
            (1, 0, None), (2, 0, None),
        ]

        def forbidden_open(*args, **kwargs):
            pytest.fail("forged Attempt reached S3")

        with monkeypatch.context() as patch:
            patch.setattr(store, "open_stream", forbidden_open)
            with pytest.raises(DomainError) as refused:
                load_saved_reference_text(
                    worker_session,
                    authority=replace(authority, execution_token="invalid-token"),
                    blob_store=store,
                    max_input_bytes=text_ref["size_bytes"],
                )
        assert refused.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
        seen.append(checked)
        raise _TextInspected

    monkeypatch.setattr(executor, "_publication_store", inspect_saved_source)
    with pytest.raises(_TextInspected):
        execute_run(
            session,
            run_id,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
            recorded_fixture_model_id="fixture/ar-v2-recorded",
            recorded_generation_settings=SETTINGS,
        )
    assert len(seen) == 1
    assert RunRepository().get(session, run_id).state == "running"
    assert session.execute(text(
        "SELECT count(*) FROM model_call WHERE run_id = :run_id"
    ), {"run_id": run_id}).scalar_one() == 0
    assert session.execute(text(
        "SELECT count(*) FROM provider_call_effect WHERE run_id = :run_id"
    ), {"run_id": run_id}).scalar_one() == 0
    assert session.execute(text(
        "SELECT count(*) FROM finding WHERE allocated_by_run_id = :run_id"
    ), {"run_id": run_id}).scalar_one() == 0
