"""Read a recorded AR v2 request from a saved run's published source artifacts.

This is a read-only run boundary. The active executor never calls it. A future
executor must hold Job/Attempt authority and journal the replay separately.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    AR_V2_RECORDED_BUNDLE_ID,
    AR_V2_RECORDED_PROFILE_ID,
    ArtifactRef,
    ModelAdapter,
    ProviderConfig,
    ROLE_PAGE_INVENTORY,
    ROLE_RECOGNISED_TEXT,
    ROLE_TEXT_LAYER,
    RecordedGenerationSettings,
    RecordedV2Input,
    default_registry,
    prepare_recorded_v2_input,
    read_artifact,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.runs.executor import plan_recorded_v2_execution
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import BlobStore, parse_blob_id


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the saved recorded AR v2 source cannot be bound to this run",
        stage_id="text_analysis",
        reason=reason,
    )


def _source_refs(row: StageResultRow) -> dict[str, ArtifactRef]:
    definition = default_registry().stage("source_preparation")
    if row.status != "succeeded" or row.stage_version != definition.stage_version:
        raise _refuse("source_stage_not_succeeded")
    permitted = frozenset({ROLE_PAGE_INVENTORY, ROLE_TEXT_LAYER, ROLE_RECOGNISED_TEXT})
    refs: dict[str, ArtifactRef] = {}
    for raw in row.artifacts:
        if not isinstance(raw, Mapping):
            raise _refuse("invalid_source_reference")
        try:
            ref = ArtifactRef(**dict(raw))
        except (TypeError, ValueError):
            raise _refuse("invalid_source_reference") from None
        if ref.role not in permitted or ref.role in refs:
            raise _refuse("duplicate_or_unexpected_source_role")
        refs[ref.role] = ref
    if ROLE_PAGE_INVENTORY not in refs or ROLE_TEXT_LAYER not in refs:
        raise _refuse("missing_source_reference")
    return refs


def load_recorded_v2_input(
    session: Session,
    *,
    run_id: str,
    blob_store: BlobStore,
    adapter: ModelAdapter,
    provider_config: ProviderConfig,
    fixture_model_id: str,
    settings: RecordedGenerationSettings,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
) -> RecordedV2Input:
    """Bind saved stage references and verified Blob reads to one offline request.

    The service reads only. A portal version always requires its marked OCR
    artifact, even if its textless-page list is empty; missing OCR is never
    silently replaced with unmarked PDF or portal descriptions.
    """
    run_repo = runs or RunRepository()
    document_repo = documents or DocumentRepository()
    run = run_repo.get(session, run_id)
    plan_recorded_v2_execution(
        run=run,
        adapter=adapter,
        provider_config=provider_config,
        registered_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
        registered_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
    )
    if run.state != "running":
        raise _refuse("source_read_requires_running_run")

    version = document_repo.get_version(session, VersionUid.parse(run.version_uid))
    if str(version.version_uid) != run.version_uid or str(version.project_uid) != run.project_uid:
        raise _refuse("run_version_mismatch")
    matching = tuple(
        row for row in run_repo.stage_results(session, run_id)
        if row.stage_id == "source_preparation"
    )
    if len(matching) != 1:
        raise _refuse("source_stage_result_missing_or_duplicate")
    refs = _source_refs(matching[0])
    has_portal = version.textless_pages is not None
    if has_portal != (ROLE_RECOGNISED_TEXT in refs):
        raise _refuse("recognised_reference_mismatch")

    text_ref = refs[ROLE_TEXT_LAYER]
    text_document, text_read_sha256 = read_artifact(
        blob_store, parse_blob_id(text_ref.blob_id), expected_role=ROLE_TEXT_LAYER,
    )
    recognised_ref = refs.get(ROLE_RECOGNISED_TEXT)
    recognised_document: Mapping[str, Any] | None = None
    recognised_read_sha256: str | None = None
    if recognised_ref is not None:
        recognised_document, recognised_read_sha256 = read_artifact(
            blob_store, parse_blob_id(recognised_ref.blob_id),
            expected_role=ROLE_RECOGNISED_TEXT,
        )
    prepared = prepare_recorded_v2_input(
        version_uid=run.version_uid,
        textless_pages=version.textless_pages,
        text_layer_document=text_document,
        text_layer_ref=text_ref,
        text_layer_read_sha256=text_read_sha256,
        recognised_document=recognised_document,
        recognised_ref=recognised_ref,
        recognised_read_sha256=recognised_read_sha256,
        analysis_profile_id=AR_V2_RECORDED_PROFILE_ID,
        prompt_bundle_id=AR_V2_RECORDED_BUNDLE_ID,
        fixture_model_id=fixture_model_id,
        settings=settings,
    )
    if len(prepared.text_layer.pages) != version.page_count:
        raise _refuse("source_page_count_mismatch")
    return prepared


__all__ = ["load_recorded_v2_input"]
