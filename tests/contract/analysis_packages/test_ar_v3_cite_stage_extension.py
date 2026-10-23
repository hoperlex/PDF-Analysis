"""AR v3 CITE has one profile-owned stage beside the nine legacy stages."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from auditmanager.analysis.public import (
    ArtifactRef, StageError, StageResult, StageStatus, default_registry,
)
from auditmanager.runs.v3_cite_stage_contract import (
    CONTRACT_PATH, load_v3_cite_stage_contract, require_v3_cite_stage_result,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id


def _success() -> StageResult:
    digest = "a" * 64
    return StageResult(
        stage_id="ar_v3_citation_review", stage_version="1.0.0",
        status=StageStatus.SUCCEEDED,
        artifacts=(ArtifactRef(
            "analysis.v3_beta_review",
            str(derive_blob_id(sha256=digest, size=401)),
            digest, 401, "application/json",
        ),),
        metrics={
            "model_call_id": "call_test",
            "candidate_sha256": digest,
            "provider_body_sha256": digest,
            "provider_response_sha256": digest,
            "set_sha256": digest,
            "reply_blob_sha256": digest,
            "provisional_citation_count": 1,
            "withheld_proposal_count": 2,
            "rejected_proposal_count": 0,
        },
    )


def test_extension_is_profile_specific_and_legacy_registry_stays_nine():
    stage = load_v3_cite_stage_contract()
    assert CONTRACT_PATH.is_file()
    assert stage.stage_id == "ar_v3_citation_review"
    assert stage.required_prior_stages == ("source_preparation",)
    assert stage.required_input_roles == (
        "prepared.text_layer", "norms.retrieval_set", "analysis.v3_provider_reply",
    )
    assert stage.output_role == "analysis.v3_beta_review"
    assert len(default_registry().stage_ids) == 9
    assert stage.stage_id not in default_registry().stage_ids


def test_success_and_explicit_failed_shape_are_accepted():
    require_v3_cite_stage_result(_success())
    failure = DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                          stage_id="text_analysis", reason="bad_reply")
    failed = StageResult(
        stage_id="ar_v3_citation_review", stage_version="1.0.0",
        status=StageStatus.FAILED, error=StageError.from_domain_error(failure),
    )
    require_v3_cite_stage_result(failed)


@pytest.mark.parametrize("change", [
    "stage_id", "prior", "input", "output", "numeric", "family", "extra",
])
def test_manifest_drift_refuses(tmp_path, change):
    document = json.loads(CONTRACT_PATH.read_text())
    if change == "stage_id":
        document["stage"]["stage_id"] = "norm_verification"
    elif change == "prior":
        document["stage"]["requires_prior_stages"] = ["finding_merge"]
    elif change == "input":
        document["stage"]["input_roles"].remove("analysis.v3_provider_reply")
    elif change == "output":
        document["stage"]["output_role"] = "norms.verification_report"
    elif change == "numeric":
        document["beta_policy"]["numeric_output_policy"] = "model_verdict"
    elif change == "family":
        document["analysis_contract_version"] = "1.3.0"
    else:
        document["unknown"] = True
    path = tmp_path / "stage.json"
    path.write_text(json.dumps(document))
    with pytest.raises(DomainError) as caught:
        load_v3_cite_stage_contract(path)
    assert caught.value.detail_fields["reason"] == "stage_manifest_drift"


def test_duplicate_manifest_key_refuses(tmp_path):
    source = CONTRACT_PATH.read_text()
    path = tmp_path / "stage.json"
    path.write_text(source.replace(
        '"extension_version": "1.0.0",',
        '"extension_version": "1.0.0", "extension_version": "1.0.0",',
    ))
    with pytest.raises(DomainError) as caught:
        load_v3_cite_stage_contract(path)
    assert caught.value.detail_fields["reason"] == "stage_manifest_unreadable"


@pytest.mark.parametrize("change", [
    "wrong_role", "missing_ref", "bad_digest", "negative_count", "partial",
    "wrong_stage", "failed_with_ref",
])
def test_stage_result_mutations_refuse(change):
    result = _success()
    if change == "wrong_role":
        result = replace(result, artifacts=(replace(
            result.artifacts[0], role="norms.verification_report"),))
    elif change == "missing_ref":
        result = replace(result, artifacts=())
    elif change == "bad_digest":
        result = replace(result, metrics={**result.metrics,
                                          "set_sha256": "not-a-digest"})
    elif change == "negative_count":
        result = replace(result, metrics={**result.metrics,
                                          "withheld_proposal_count": -1})
    elif change == "partial":
        failure = DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                              stage_id="text_analysis", reason="partial")
        result = replace(result, status=StageStatus.PARTIAL,
                         error=StageError.from_domain_error(failure))
    elif change == "wrong_stage":
        result = replace(result, stage_id="norm_verification")
    else:
        failure = DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                              stage_id="text_analysis", reason="failed")
        result = replace(result, status=StageStatus.FAILED,
                         error=StageError.from_domain_error(failure))
    with pytest.raises(DomainError) as caught:
        require_v3_cite_stage_result(result)
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
