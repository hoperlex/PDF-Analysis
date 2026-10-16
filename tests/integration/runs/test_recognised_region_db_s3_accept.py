"""Read a saved OCR region from a real running Attempt, PostgreSQL and S3.

The publication-store seam before the third deterministic stage is intercepted
after the executor has committed and bound source and geometry. No provider
response or finding is made.
"""

from __future__ import annotations

import hashlib
import json
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
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.runs.recognised_region_input import load_saved_recognised_region
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_role
from tests.integration.analysis.recognised.recognised_support import members


QUOTE = "Синтетический распознанный текст страницы 1."
SETTINGS = RecordedGenerationSettings(4096, "high", {"type": "adaptive"})


class _RegionInspected(Exception):
    """Stop after saved geometry, before the next stage or provider call."""


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
            upload_token=f"w56b-region-accept-{role}",
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
    project = documents.create_project(session, "Синтетический OCR проект")
    document_uid = documents.create_document(
        session, project_uid=project.project_uid,
        display_title="Сканированный АР", section="AR",
    )
    bodies = read_blocks(bundle.markdown.decode("utf-8"))
    assert len(bodies) == 2 and all(block.label == "text" for block in bodies)
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


def test_current_attempt_reads_two_saved_ocr_blobs_and_stale_attempt_refuses(
    session, blob_store, recorded_adapter, provider_config, new_key, monkeypatch,
) -> None:
    bundle = members("image_only_with_block.zip")
    assert QUOTE.encode("utf-8") in bundle.markdown
    source_block = next(
        block for block in json.loads(bundle.block_list)["blocks"]
        if block["page_index"] == 0 and block["block_type"] == "text"
    )
    version_uid = _seed_version(session, blob_store, bundle)
    started = start_audit_run(
        session,
        version_uid=version_uid,
        analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
        prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
        provider_mode="recorded",
        idempotency_key=new_key("w56b-region-db-s3-accept"),
    )
    run_id = str(started.run_id)
    seen = []

    production_store = executor._publication_store

    def inspect_after_geometry(
        worker_session, *, store, jobs, blobs, authority, stage_id, checkpoint=None,
    ):
        if stage_id != "document_context_build":
            return production_store(
                worker_session, store=store, jobs=jobs, blobs=blobs,
                authority=authority, stage_id=stage_id, checkpoint=checkpoint,
            )
        rows = RunRepository().stage_results(worker_session, run_id)
        stages = {row.stage_id: row for row in rows}
        assert {"source_preparation", "page_geometry_extraction"} <= stages.keys()
        assert stages["source_preparation"].status == "succeeded"
        assert stages["page_geometry_extraction"].status == "succeeded"
        recognised_ref = next(
            ref for ref in stages["source_preparation"].artifacts
            if ref["role"] == "prepared.recognised_text"
        )
        portal_ref = next(
            ref for ref in stages["page_geometry_extraction"].artifacts
            if ref["role"] == "geometry.portal_blocks"
        )
        bound = {tuple(row) for row in worker_session.execute(text(
            "SELECT stage_id, blob_id FROM analysis_artifact_publication "
            "WHERE run_id = :run_id AND attempt_id = :attempt_id "
            "AND state = 'bound'"
        ), {"run_id": run_id, "attempt_id": authority.attempt_id}).all()}
        assert (
            "source_preparation", recognised_ref["blob_id"]
        ) in bound
        assert (
            "page_geometry_extraction", portal_ref["blob_id"]
        ) in bound

        ceiling = recognised_ref["size_bytes"] + portal_ref["size_bytes"]
        checked = load_saved_recognised_region(
            worker_session,
            authority=authority,
            blob_store=store,
            max_input_bytes=ceiling,
            portal_block_id=source_block["block_id"],
            page_number=1,
            quote=QUOTE,
        )
        assert checked.candidate.version_uid == version_uid
        assert checked.candidate.quote_source == "recognised"
        assert checked.candidate.page_number == 1
        assert checked.candidate.bbox_norm == tuple(source_block["coords_norm"])
        assert checked.candidate.results_sha256 == hashlib.sha256(bundle.markdown).hexdigest()
        assert checked.candidate.blocks_sha256 == hashlib.sha256(bundle.block_list).hexdigest()
        assert checked.recognised_ref.blob_id == recognised_ref["blob_id"]
        assert checked.portal_blocks_ref.blob_id == portal_ref["blob_id"]

        with pytest.raises(DomainError) as refused:
            load_saved_recognised_region(
                worker_session,
                authority=replace(authority, execution_token="invalid-token"),
                blob_store=store,
                max_input_bytes=ceiling,
                portal_block_id=source_block["block_id"],
                page_number=1,
                quote=QUOTE,
            )
        assert refused.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
        seen.append(checked)
        raise _RegionInspected

    monkeypatch.setattr(executor, "_publication_store", inspect_after_geometry)
    with pytest.raises(_RegionInspected):
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
