"""Read saved recorded AR v2 evidence into a deterministic finding plan.

The caller owns persisted StageResult provenance and Attempt fencing. This
read-only bridge checks exact saved Blob bytes and the caller's recorded call
facts before any finding identity may be allocated in a later transaction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from auditmanager.analysis.public import (
    ArtifactRef, CONTRACT_VERSION, MERGE_ARTIFACT_ROLE, MERGE_ARTIFACT_VERSION,
    RECORDED_OBSERVATION_ARTIFACT_ROLE,
    MergePreparation, RecordedArtifactError, StageResult, StageStatus,
    ARTIFACT_MEDIA_TYPE, canonical_bytes, default_registry,
    read_recorded_merge_input, sha256_hex,
)
from auditmanager.findings.merge_publication_plan import (
    MergePublicationPlan, plan_v2_merge_publication,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore, derive_blob_id, parse_blob_id


class SavedRecordedPlanError(ValueError):
    """Saved evidence does not support a complete recorded finding plan."""


@dataclass(frozen=True, slots=True)
class SavedRecordedPublicationPlan:
    plan: MergePublicationPlan
    model_id: str
    model_call_id: str
    request_sha256: str
    response_sha256: str
    source_binding_sha256: str
    text_artifact_sha256: str
    merge_artifact_sha256: str


def _one_reference(result: StageResult, *, stage_id: str, role: str) -> ArtifactRef:
    definition = default_registry().stage(stage_id)
    if (not isinstance(result, StageResult)
            or result.stage_id != stage_id
            or result.stage_version != definition.stage_version
            or result.contract_version != CONTRACT_VERSION
            or result.status is not StageStatus.SUCCEEDED
            or len(result.artifacts) != 1
            or result.artifacts[0].role != role):
        raise SavedRecordedPlanError("saved_stage_result_invalid")
    reference = result.artifacts[0]
    if (reference.media_type != ARTIFACT_MEDIA_TYPE
            or reference.blob_id != str(derive_blob_id(
                sha256=reference.sha256, size=reference.size_bytes,
            ))):
        raise SavedRecordedPlanError("saved_artifact_reference_invalid")
    return reference


def _read_merge_document(blob_store: BlobStore, reference: ArtifactRef) -> dict[str, object]:
    try:
        payload = blob_store.read(parse_blob_id(reference.blob_id), verify=True)
    except DomainError:
        raise
    except Exception as exc:  # noqa: BLE001 - typed Blob boundary
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the saved recorded merge Blob could not be read",
            stage_id="finding_merge", reason="input_unreadable",
        ) from exc
    if len(payload) != reference.size_bytes or sha256_hex(payload) != reference.sha256:
        raise SavedRecordedPlanError("saved_merge_digest_mismatch")
    try:
        document = json.loads(payload)
        if not isinstance(document, dict) or canonical_bytes(document) != payload:
            raise ValueError
    except (UnicodeDecodeError, TypeError, ValueError):
        raise SavedRecordedPlanError("saved_merge_not_canonical") from None
    if (document.get("artifact_role") != MERGE_ARTIFACT_ROLE
            or document.get("artifact_version") != MERGE_ARTIFACT_VERSION):
        raise SavedRecordedPlanError("saved_merge_role_or_version_invalid")
    return document


def plan_recorded_saved_publication(
    blob_store: BlobStore,
    *,
    text_result: StageResult,
    merge_result: StageResult,
    run_id: str,
    version_uid: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    model_id: str,
    model_call_id: str,
    request_sha256: str,
    response_sha256: str,
    source_binding_sha256: str,
    text_layer_ref: ArtifactRef,
    recognised_ref: ArtifactRef | None,
) -> SavedRecordedPublicationPlan:
    """Verify saved stages and reconstruct the complete pure publication plan.

    The two stage Blobs are read once each. The caller must recheck persisted
    rows and current Attempt authority inside the later publishing transaction.
    """
    text_ref = _one_reference(
        text_result, stage_id="text_analysis", role=RECORDED_OBSERVATION_ARTIFACT_ROLE,
    )
    merge_ref = _one_reference(
        merge_result, stage_id="finding_merge", role=MERGE_ARTIFACT_ROLE,
    )
    if (text_result.metrics.get("provider_mode") != "recorded"
            or text_result.metrics.get("model_call_count") != 1
            or merge_result.metrics.get("text_artifact_sha256") != text_ref.sha256):
        raise SavedRecordedPlanError("saved_stage_binding_invalid")
    if (not isinstance(text_layer_ref, ArtifactRef)
            or (recognised_ref is not None and not isinstance(recognised_ref, ArtifactRef))):
        raise SavedRecordedPlanError("saved_source_reference_invalid")

    try:
        recorded = read_recorded_merge_input(
            blob_store, text_ref, run_id=run_id, version_uid=version_uid,
            analysis_profile_id=analysis_profile_id,
            prompt_bundle_id=prompt_bundle_id,
        )
    except (RecordedArtifactError, TypeError, ValueError) as exc:
        raise SavedRecordedPlanError("saved_text_observations_invalid") from exc
    if ((recorded.text_layer_ref, recorded.recognised_ref) != (text_layer_ref, recognised_ref)
            or recorded.model_id != model_id
            or recorded.model_call_id != model_call_id
            or recorded.request_sha256 != request_sha256
            or recorded.response_sha256 != response_sha256
            or recorded.source_binding_sha256 != source_binding_sha256):
        raise SavedRecordedPlanError("saved_call_or_source_binding_invalid")

    document = _read_merge_document(blob_store, merge_ref)
    preparation = MergePreparation(recorded.source_proposal_ordinals, document)
    try:
        plan = plan_v2_merge_publication(recorded.grounding, preparation)
    except ValueError as exc:
        raise SavedRecordedPlanError("saved_merge_partition_invalid") from exc
    if (merge_result.metrics.get("observation_count") != plan.observation_count
            or merge_result.metrics.get("group_count") != plan.finding_count):
        raise SavedRecordedPlanError("saved_merge_metrics_invalid")
    return SavedRecordedPublicationPlan(
        plan, recorded.model_id, recorded.model_call_id, recorded.request_sha256,
        recorded.response_sha256, recorded.source_binding_sha256,
        text_ref.sha256, merge_ref.sha256,
    )


__all__ = [
    "SavedRecordedPlanError", "SavedRecordedPublicationPlan",
    "plan_recorded_saved_publication",
]
