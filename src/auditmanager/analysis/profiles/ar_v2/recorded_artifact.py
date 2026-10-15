"""Build deterministic AR v2 recorded observations without publishing them.

The bytes use the existing ``analysis.text_observations`` role so the later
grounding gate can read accepted evidence. Rejected proposals are diagnostics,
never observations. A later stage owner publishes these bytes and constructs
its own StageResult and call journal in one durable workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE,
    canonical_bytes,
    sha256_hex,
)
from auditmanager.analysis.profiles.ar_v2 import prompt_material, registered
from auditmanager.analysis.profiles.ar_v2.merge_input import prepare_merge
from auditmanager.analysis.profiles.ar_v2.recorded_input import (
    PdfPageSource,
    RecordedV2Input,
)
from auditmanager.analysis.profiles.ar_v2.recorded_response import RecordedReplayResult
from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES, SEVERITIES
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.shared.identity import ModelCallId, RunId, VersionUid


ARTIFACT_ROLE: Final[str] = "analysis.text_observations"
ARTIFACT_VERSION: Final[str] = "2.0.0"
STAGE_ID: Final[str] = "text_analysis"


class RecordedArtifactError(ValueError):
    """A replay cannot be represented as a grounded recorded artifact."""


@dataclass(frozen=True, slots=True)
class BuiltRecordedArtifact:
    """Immutable bytes and Blob metadata; no Blob identity is allocated here."""

    payload: bytes
    sha256: str
    role: str = ARTIFACT_ROLE
    version: str = ARTIFACT_VERSION
    media_type: str = ARTIFACT_MEDIA_TYPE

    @property
    def size_bytes(self) -> int:
        return len(self.payload)


def _require_identity(value: str, identity_type: type, reason: str) -> str:
    try:
        return str(identity_type.parse(value))
    except (TypeError, ValueError):
        raise RecordedArtifactError(reason) from None


def _verify_replay(prepared: RecordedV2Input, replay: RecordedReplayResult) -> None:
    if not isinstance(prepared, RecordedV2Input) or not isinstance(replay, RecordedReplayResult):
        raise RecordedArtifactError("recorded_inputs_required")
    if replay.provider_mode is not ProviderMode.RECORDED:
        raise RecordedArtifactError("recorded_mode_required")
    if (
        replay.model_id != prepared.request.model_id
        or prepared.request.body.get("model") != replay.model_id
        or replay.request_sha256 != prepared.request_sha256
        or replay.source_binding_sha256 != prepared.source_binding_sha256
        or replay.response_sha256 != replay.finished.response_sha256
    ):
        raise RecordedArtifactError("replay_provenance_mismatch")
    if prepared.text_layer.version_uid != prepared.version_uid:
        raise RecordedArtifactError("text_layer_version_mismatch")
    if prepared.page_sources != tuple(
        PdfPageSource(page.page_number, page.char_start, page.char_end)
        for page in prepared.text_layer.pages
    ):
        raise RecordedArtifactError("page_sources_mismatch")
    user_prompt = prompt_material.render_user_prompt(
        prepared.text_layer, recognised_context=prepared.recognised_context,
    )
    if prepared.request.body.get("messages") != [{"role": "user", "content": user_prompt}]:
        raise RecordedArtifactError("request_sources_mismatch")
    expected_binding = sha256_hex(canonical_bytes({
        "version_uid": prepared.version_uid,
        "text_layer_ref": prepared.text_layer_ref.to_document(),
        "recognised_ref": (
            None if prepared.recognised_ref is None
            else prepared.recognised_ref.to_document()
        ),
        "textless_pages": prepared.textless_pages,
        "request_sha256": prepared.request_sha256,
    }))
    if expected_binding != replay.source_binding_sha256:
        raise RecordedArtifactError("source_binding_mismatch")
    if replay.finished.merge != prepare_merge(replay.finished.grounding):
        raise RecordedArtifactError("merge_preparation_mismatch")


def build_recorded_observation_artifact(
    *,
    prepared: RecordedV2Input,
    replay: RecordedReplayResult,
    run_id: str,
    model_call_id: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
) -> BuiltRecordedArtifact:
    """Serialize verified recorded observations and all available diagnostics.

    ``run_id`` and ``model_call_id`` are allocated by a later durable caller.
    Same identities, verified input and replay produce byte-identical payloads.
    No model claim or rejected proposal receives a finding identity here.
    """
    _verify_replay(prepared, replay)
    run = _require_identity(run_id, RunId, "invalid_run_id")
    call = _require_identity(model_call_id, ModelCallId, "invalid_model_call_id")
    _require_identity(prepared.version_uid, VersionUid, "invalid_version_uid")
    profile = registered.resolve_recorded_profile(analysis_profile_id, prompt_bundle_id)

    observations = []
    for ordinal, item in enumerate(replay.finished.grounding.accepted):
        proposal = item.proposal
        if (
            proposal.category not in CATEGORIES
            or proposal.proposed_severity not in SEVERITIES
            or not item.evidence
            or len(item.evidence) != len(proposal.evidence)
        ):
            raise RecordedArtifactError("accepted_proposal_invalid")
        evidence = []
        for evidence_ordinal, anchor in enumerate(item.evidence):
            page = prepared.text_layer.page(anchor.page_number)
            if (
                page is None
                or anchor.block_id is not None
                or anchor.char_end - anchor.char_start != len(anchor.quote)
                or not page.contains(anchor.char_start, anchor.char_end)
                or prepared.text_layer.slice(anchor.char_start, anchor.char_end) != anchor.quote
            ):
                raise RecordedArtifactError("evidence_not_grounded_in_pdf")
            evidence.append({
                "evidence_ordinal": evidence_ordinal,
                "page_number": anchor.page_number,
                "quote": anchor.quote,
                "char_start": anchor.char_start,
                "char_end": anchor.char_end,
            })
        observations.append({
            "observation_ordinal": ordinal,
            "source_proposal_ordinal": item.proposal_ordinal,
            "category": proposal.category,
            "finding_text": proposal.finding_text,
            "recommendation_text": proposal.recommendation_text,
            "proposed_severity": proposal.proposed_severity,
            "model_call_id": call,
            "evidence": evidence,
        })

    diagnostics = [{
        "source_proposal_ordinal": item.proposal_ordinal,
        "failures": [{
            "evidence_ordinal": failure.evidence_ordinal,
            "page_number": failure.page_number,
            "quote": failure.quote,
            "reason": failure.reason,
        } for failure in item.failures],
    } for item in replay.finished.grounding.rejected]
    document = {
        "artifact_role": ARTIFACT_ROLE,
        "artifact_version": ARTIFACT_VERSION,
        "run_id": run,
        "stage_id": STAGE_ID,
        "version_uid": prepared.version_uid,
        "analysis_profile_id": str(profile.analysis_profile_id),
        "prompt_bundle_id": str(profile.prompt_bundle_id),
        "profile_content_sha256": profile.content_sha256,
        "provider_mode": ProviderMode.RECORDED.value,
        "model_id": replay.model_id,
        "model_call_id": call,
        "request_sha256": replay.request_sha256,
        "source_binding_sha256": replay.source_binding_sha256,
        "response_sha256": replay.response_sha256,
        "source_artifacts": {
            "text_layer": prepared.text_layer_ref.to_document(),
            "recognised_text": (
                None if prepared.recognised_ref is None
                else prepared.recognised_ref.to_document()
            ),
        },
        "textless_pages": prepared.textless_pages,
        "page_sources": [{
            "page_number": page.page_number,
            "char_start": page.char_start,
            "char_end": page.char_end,
        } for page in prepared.page_sources],
        "pages_analysed": list(prepared.text_layer.page_numbers),
        "observations": observations,
        "diagnostics": {
            "rejected": diagnostics,
            "malformed_count": replay.finished.grounding.malformed_count,
            "salvaged": replay.finished.grounding.salvaged,
            "truncated": replay.finished.truncated,
        },
    }
    payload = canonical_bytes(document)
    return BuiltRecordedArtifact(payload=payload, sha256=sha256_hex(payload))


__all__ = [
    "ARTIFACT_ROLE", "ARTIFACT_VERSION", "BuiltRecordedArtifact",
    "RecordedArtifactError", "build_recorded_observation_artifact",
]
