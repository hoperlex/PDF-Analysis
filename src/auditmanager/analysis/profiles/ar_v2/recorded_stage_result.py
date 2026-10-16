"""Seal a complete recorded AR v2 artifact into a registry-bound StageResult.

The caller must first publish the exact bytes and retain the returned Blob
reference. This pure seal proves the reference, call facts and artifact agree;
it does not prove Blob availability or persist any row. Truncated replies need
a later explicit coverage and partial-status policy and are refused here.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from auditmanager.analysis.engine.registry import default_registry
from auditmanager.analysis.engine.result import ArtifactRef, StageResult, StageStatus
from auditmanager.analysis.engine.serialization import ARTIFACT_MEDIA_TYPE, canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.recorded_artifact import (
    ARTIFACT_ROLE, ARTIFACT_VERSION, STAGE_ID, BuiltRecordedArtifact,
)
from auditmanager.analysis.profiles.ar_v2.recorded_call import RecordedCallFacts
from auditmanager.analysis.profiles.ar_v2.recorded_input import RecordedV2Input
from auditmanager.analysis.profiles.ar_v2.registered import (
    RecordedProfileError, resolve_recorded_profile,
)
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.provenance import CALL_SUCCEEDED, CALL_TRUNCATED
from auditmanager.shared.identity import RunId, VersionUid


class RecordedStageSealError(ValueError):
    """The recorded bytes cannot support a successful text stage result."""


def _document(artifact: BuiltRecordedArtifact) -> dict[str, Any]:
    if not isinstance(artifact, BuiltRecordedArtifact):
        raise RecordedStageSealError("recorded_artifact_required")
    if (artifact.role != ARTIFACT_ROLE or artifact.version != ARTIFACT_VERSION
            or artifact.media_type != ARTIFACT_MEDIA_TYPE
            or sha256_hex(artifact.payload) != artifact.sha256):
        raise RecordedStageSealError("recorded_artifact_digest_mismatch")
    try:
        document = json.loads(artifact.payload)
        if not isinstance(document, dict) or canonical_bytes(document) != artifact.payload:
            raise ValueError
    except (TypeError, ValueError, UnicodeDecodeError):
        raise RecordedStageSealError("recorded_artifact_not_canonical") from None
    return document


def seal_recorded_v2_stage_result(
    *, artifact: BuiltRecordedArtifact, published_ref: ArtifactRef,
    call: RecordedCallFacts, prepared: RecordedV2Input,
    run_id: str, version_uid: str,
    started_at: datetime, finished_at: datetime,
) -> StageResult:
    """Make one successful text-analysis result from a complete recorded reply.

    The Blob publisher must supply its returned ``ArtifactRef``; constructing a
    matching reference locally would not prove that any Blob was stored. The
    later durable caller owns availability, call-journal and run transactions.
    """
    document = _document(artifact)
    if not isinstance(published_ref, ArtifactRef) or (
        published_ref.role != artifact.role
        or published_ref.sha256 != artifact.sha256
        or published_ref.size_bytes != artifact.size_bytes
        or published_ref.media_type != artifact.media_type
    ):
        raise RecordedStageSealError("published_artifact_ref_mismatch")
    if not isinstance(call, RecordedCallFacts) or call.provider_mode is not ProviderMode.RECORDED:
        raise RecordedStageSealError("recorded_call_required")
    if not isinstance(prepared, RecordedV2Input):
        raise RecordedStageSealError("recorded_source_required")
    try:
        expected_run = str(RunId.parse(run_id))
        expected_version = str(VersionUid.parse(version_uid))
        profile = resolve_recorded_profile(
            document.get("analysis_profile_id"), document.get("prompt_bundle_id")
        )
    except (TypeError, ValueError, RecordedProfileError):
        raise RecordedStageSealError("recorded_identity_invalid") from None
    if (
        document.get("artifact_role") != ARTIFACT_ROLE
        or document.get("artifact_version") != ARTIFACT_VERSION
        or document.get("stage_id") != STAGE_ID
        or document.get("run_id") != expected_run
        or document.get("version_uid") != expected_version
        or document.get("analysis_profile_id") != str(profile.analysis_profile_id)
        or document.get("prompt_bundle_id") != str(profile.prompt_bundle_id)
        or document.get("profile_content_sha256") != profile.content_sha256
        or document.get("provider_mode") != ProviderMode.RECORDED.value
        or document.get("model_id") != call.model_id
        or document.get("model_call_id") != call.model_call_id
        or document.get("request_sha256") != call.request_sha256
        or document.get("source_binding_sha256") != call.source_binding_sha256
        or document.get("response_sha256") != call.response_sha256
    ):
        raise RecordedStageSealError("recorded_stage_provenance_mismatch")
    expected_pages = [{
        "page_number": page.page_number,
        "char_start": page.char_start,
        "char_end": page.char_end,
    } for page in prepared.text_layer.pages]
    retained_pages = [{
        "page_number": page.page_number,
        "char_start": page.char_start,
        "char_end": page.char_end,
    } for page in prepared.page_sources]
    expected_source_artifacts = {
        "text_layer": prepared.text_layer_ref.to_document(),
        "recognised_text": (
            None if prepared.recognised_ref is None
            else prepared.recognised_ref.to_document()
        ),
    }
    expected_binding = sha256_hex(canonical_bytes({
        "version_uid": prepared.version_uid,
        "text_layer_ref": expected_source_artifacts["text_layer"],
        "recognised_ref": expected_source_artifacts["recognised_text"],
        "textless_pages": prepared.textless_pages,
        "request_sha256": prepared.request_sha256,
    }))
    if (
        prepared.version_uid != expected_version
        or prepared.text_layer.version_uid != expected_version
        or prepared.request.model_id != call.model_id
        or prepared.request.body.get("model") != call.model_id
        or prepared.request_sha256 != call.request_sha256
        or prepared.source_binding_sha256 != expected_binding
        or call.source_binding_sha256 != expected_binding
        or document.get("source_binding_sha256") != expected_binding
        or retained_pages != expected_pages
        or document.get("page_sources") != expected_pages
        or document.get("pages_analysed") != list(prepared.text_layer.page_numbers)
        or document.get("textless_pages") != (
            None if prepared.textless_pages is None else list(prepared.textless_pages)
        )
        or document.get("source_artifacts") != expected_source_artifacts
    ):
        raise RecordedStageSealError("recorded_source_provenance_mismatch")
    diagnostics = document.get("diagnostics")
    if not isinstance(diagnostics, dict) or (
        type(diagnostics.get("truncated")) is not bool
        or type(diagnostics.get("salvaged")) is not bool
        or call.status not in {CALL_SUCCEEDED, CALL_TRUNCATED}
    ):
        raise RecordedStageSealError("recorded_stage_diagnostics_invalid")
    if diagnostics["truncated"] or diagnostics["salvaged"] or call.status != CALL_SUCCEEDED:
        raise RecordedStageSealError("truncated_reply_needs_partial_coverage_policy")
    if (
        not isinstance(started_at, datetime) or not isinstance(finished_at, datetime)
        or started_at.tzinfo is None or started_at.utcoffset() is None
        or finished_at.tzinfo is None or finished_at.utcoffset() is None
        or finished_at < started_at
    ):
        raise RecordedStageSealError("stage_times_invalid")
    if any(type(value) is not int or value < 0 for value in (
        call.input_tokens, call.output_tokens, call.latency_ms,
    )):
        raise RecordedStageSealError("recorded_call_usage_invalid")
    stage = default_registry().stage(STAGE_ID)
    if (
        not stage.succeeded_requires_all_required_outputs
        or stage.missing_outputs(frozenset({published_ref.role}))
    ):
        raise RecordedStageSealError("stage_output_policy_mismatch")
    result = StageResult(
        stage_id=stage.stage_id,
        stage_version=stage.stage_version,
        status=StageStatus.SUCCEEDED,
        artifacts=(published_ref,),
        metrics={
            "provider_mode": ProviderMode.RECORDED.value,
            "model_call_count": 1,
            "input_tokens": call.input_tokens,
            "output_tokens": call.output_tokens,
            "latency_ms": call.latency_ms,
        },
        started_at=started_at,
        finished_at=finished_at,
    )
    result.to_document()  # enforce metric and time serialization before return
    return result


__all__ = ["RecordedStageSealError", "seal_recorded_v2_stage_result"]
