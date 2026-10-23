"""Profile-specific AR v3 CITE stage declaration beside the frozen legacy registry.

The nine legacy stages and family contract stay at 1.2.0. This extension is
strictly for the beta profile's review artifact, before finding publication.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID, CONTRACT_VERSION,
    StageResult, StageStatus,
)
from auditmanager.shared.errors import DomainError, ErrorCode


CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "contracts/analysis/ar_v3_beta/v1/stage.json"
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SUCCESS_METRICS = (
    "model_call_id", "candidate_sha256", "provider_body_sha256",
    "provider_response_sha256", "set_sha256", "reply_blob_sha256",
    "provisional_citation_count", "withheld_proposal_count",
    "rejected_proposal_count",
)


@dataclass(frozen=True, slots=True)
class V3CiteStageContract:
    stage_id: str
    stage_version: str
    output_role: str
    output_media_type: str
    required_input_roles: tuple[str, ...]
    required_prior_stages: tuple[str, ...]
    success_metric_keys: tuple[str, ...]


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="AR v3 beta CITE stage declaration is invalid",
        stage_id="text_analysis", reason=reason,
    )


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate stage manifest key")
        result[key] = value
    return result


def load_v3_cite_stage_contract(path: Path = CONTRACT_PATH) -> V3CiteStageContract:
    """Read exact profile stage semantics without changing the legacy registry."""
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs,
        )
        stage = document["stage"]
        policy = document["beta_policy"]
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise _refuse("stage_manifest_unreadable") from exc
    if (not isinstance(document, dict)
            or set(document) != {
                "contract", "extension_version", "analysis_contract_version",
                "analysis_profile_id", "prompt_bundle_id", "stage", "beta_policy",
            }
            or not isinstance(stage, dict)
            or set(stage) != {
                "stage_id", "stage_version", "requires_prior_stages",
                "input_roles", "output_role", "output_media_type",
                "success_metric_keys", "partial_allowed", "skipped_allowed",
            }
            or not isinstance(policy, dict)
            or set(policy) != {
                "scenario", "numeric_output_policy", "canonical_finding_publication",
            }
            or document["contract"] != "auditmanager.analysis.ar_v3_beta_stage_extension"
            or document["extension_version"] != "1.0.0"
            or document["analysis_contract_version"] != CONTRACT_VERSION
            or document["analysis_profile_id"] != str(AR_V3_BETA_PROFILE_ID)
            or document["prompt_bundle_id"] != str(AR_V3_BETA_BUNDLE_ID)
            or stage["stage_id"] != "ar_v3_citation_review"
            or stage["stage_version"] != "1.0.0"
            or stage["requires_prior_stages"] != ["source_preparation"]
            or stage["input_roles"] != [
                "prepared.text_layer", "norms.retrieval_set",
                "analysis.v3_provider_reply",
            ]
            or stage["output_role"] != "analysis.v3_beta_review"
            or stage["output_media_type"] != "application/json"
            or stage["success_metric_keys"] != list(_SUCCESS_METRICS)
            or stage["partial_allowed"] is not False
            or stage["skipped_allowed"] is not False
            or policy != {
                "scenario": "new_multi_apartment_residential_F1.3",
                "numeric_output_policy": "expert_review_required",
                "canonical_finding_publication": False,
            }):
        raise _refuse("stage_manifest_drift")
    return V3CiteStageContract(
        stage["stage_id"], stage["stage_version"], stage["output_role"],
        stage["output_media_type"], tuple(stage["input_roles"]),
        tuple(stage["requires_prior_stages"]), tuple(_SUCCESS_METRICS),
    )


def require_v3_cite_stage_result(
    result: StageResult, *, contract: V3CiteStageContract | None = None,
) -> None:
    """Check a proposed StageResult shape before the future CITE writer persists it."""
    profile_stage = contract or load_v3_cite_stage_contract()
    if (not isinstance(result, StageResult)
            or result.contract_version != CONTRACT_VERSION
            or result.stage_id != profile_stage.stage_id
            or result.stage_version != profile_stage.stage_version
            or result.status not in {StageStatus.SUCCEEDED, StageStatus.FAILED}):
        raise _refuse("stage_result_identity_invalid")
    if result.status is StageStatus.FAILED:
        if result.artifacts or result.error is None or result.metrics:
            raise _refuse("failed_stage_result_invalid")
        return
    if (result.error is not None or len(result.artifacts) != 1
            or result.artifacts[0].role != profile_stage.output_role
            or result.artifacts[0].media_type != profile_stage.output_media_type
            or set(result.metrics) != set(profile_stage.success_metric_keys)):
        raise _refuse("succeeded_stage_result_invalid")
    for key in _SUCCESS_METRICS[1:6]:
        value = result.metrics[key]
        if not isinstance(value, str) or _SHA.fullmatch(value) is None:
            raise _refuse("stage_result_digest_invalid")
    if (not isinstance(result.metrics["model_call_id"], str)
            or not result.metrics["model_call_id"]):
        raise _refuse("stage_result_call_invalid")
    for key in _SUCCESS_METRICS[6:]:
        value = result.metrics[key]
        if type(value) is not int or value < 0:
            raise _refuse("stage_result_count_invalid")


__all__ = [
    "CONTRACT_PATH", "V3CiteStageContract", "load_v3_cite_stage_contract",
    "require_v3_cite_stage_result",
]
