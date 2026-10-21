"""Exact saved recorded Blobs reconstruct a rule-checked finding plan."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from auditmanager.analysis.engine.result import ArtifactRef, StageResult, StageStatus
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.registered import PROFILE_ID, PROMPT_BUNDLE_ID
from auditmanager.analysis.stages.finding_merge import (
    MergeEvidence, MergeObservation, merge_grounded,
)
from auditmanager.findings.recorded_saved_plan import (
    SavedRecordedPlanError, plan_recorded_saved_publication,
)
from auditmanager.storage.public import derive_blob_id
from tests.integration.analysis.test_ar_v2_recorded_artifact import (
    CALL, RUN, VERSION, _build, _prepared, _replay,
)


_STAGE_REGISTRY_CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "contracts" / "analysis" / "v1" / "stage-registry.json"
)
# text_analysis was sealed at 1.0.0 until W57A-SEAL-01B moved it to 1.1.0.
_RETIRED_TEXT_STAGE_VERSION = "1.0.0"


def _stage_version(stage_id: str) -> str:
    """The version the sealed stage-registry contract declares today.

    Read from the contract file itself, not from the registry object the code
    under test consults, and never written out by hand: a reseal then moves
    this test with the contract instead of leaving a stale pin behind.
    """
    document = json.loads(_STAGE_REGISTRY_CONTRACT.read_text(encoding="utf-8"))
    versions = {entry["stage_id"]: entry["stage_version"] for entry in document["stages"]}
    return versions[stage_id]


def _ref(role: str, payload: bytes) -> ArtifactRef:
    digest = sha256_hex(payload)
    return ArtifactRef(
        role, str(derive_blob_id(sha256=digest, size=len(payload))),
        digest, len(payload), "application/json",
    )


class _Store:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads
        self.reads: list[str] = []

    def read(self, blob_id, *, verify: bool = True) -> bytes:
        assert verify
        key = str(blob_id)
        self.reads.append(key)
        return self.payloads[key]


def _case(tmp_path: Path, *, ocr_only: bool = False):
    prepared = _prepared(with_ocr=ocr_only)
    replay = _replay(tmp_path, prepared, ocr_only=ocr_only)
    built = _build(prepared, replay)
    text_ref = _ref(built.role, built.payload)
    merge_payload = canonical_bytes(replay.finished.merge.artifact)
    merge_ref = _ref("findings.merged", merge_payload)
    text_result = StageResult(
        "text_analysis", _stage_version("text_analysis"), StageStatus.SUCCEEDED, (text_ref,),
        {"provider_mode": "recorded", "model_call_count": 1},
    )
    merge_result = StageResult(
        "finding_merge", _stage_version("finding_merge"), StageStatus.SUCCEEDED, (merge_ref,),
        {"text_artifact_sha256": text_ref.sha256,
         "observation_count": len(replay.finished.grounding.accepted),
         "group_count": len(replay.finished.merge.artifact["groups"])},
    )
    store = _Store({text_ref.blob_id: built.payload, merge_ref.blob_id: merge_payload})
    arguments = {
        "text_result": text_result, "merge_result": merge_result,
        "run_id": RUN, "version_uid": VERSION,
        "analysis_profile_id": str(PROFILE_ID),
        "prompt_bundle_id": str(PROMPT_BUNDLE_ID),
        "model_id": replay.model_id,
        "model_call_id": CALL,
        "request_sha256": replay.request_sha256,
        "response_sha256": replay.response_sha256,
        "source_binding_sha256": prepared.source_binding_sha256,
        "text_layer_ref": prepared.text_layer_ref,
        "recognised_ref": prepared.recognised_ref,
    }
    return store, arguments


def test_saved_plan_preserves_finding_fields_and_rejections_without_replay(tmp_path: Path) -> None:
    store, arguments = _case(tmp_path)
    result = plan_recorded_saved_publication(store, **arguments)

    assert result.plan.finding_count == 1
    assert result.plan.observation_count == 1
    member = result.plan.groups[0].canonical
    assert member.proposal.finding_text == "Размер стены"
    assert member.proposal.recommendation_text == "Проверить"
    assert member.proposal.proposed_severity == "operational"
    assert member.evidence[0].quote == "Стена: 200 мм"
    assert result.plan.rejected[0].proposal_ordinal == 1
    assert result.plan.rejected[0].failures[0].reason == "quotation_absent"
    assert result.plan.malformed_count == 1
    assert result.model_call_id == CALL
    assert result.model_id == arguments["model_id"]
    assert result.text_artifact_sha256 == arguments["text_result"].artifacts[0].sha256
    assert result.merge_artifact_sha256 == arguments["merge_result"].artifacts[0].sha256
    assert store.reads == [
        arguments["text_result"].artifacts[0].blob_id,
        arguments["merge_result"].artifacts[0].blob_id,
    ]
    store.reads.clear()
    assert plan_recorded_saved_publication(store, **arguments) == result
    assert len(store.reads) == 2


def test_all_rejected_is_a_complete_zero_finding_plan(tmp_path: Path) -> None:
    store, arguments = _case(tmp_path, ocr_only=True)
    result = plan_recorded_saved_publication(store, **arguments)
    assert (result.plan.finding_count, result.plan.observation_count) == (0, 0)
    assert len(result.plan.rejected) == 1
    assert result.plan.rejected[0].failures[0].reason == "quote_in_recognised_text"
    assert len(store.reads) == 2


def test_saved_plan_retains_two_merged_members_and_rejected_gap(tmp_path: Path) -> None:
    store, arguments = _case(tmp_path)
    old_text_ref = arguments["text_result"].artifacts[0]
    text_document = json.loads(store.payloads[old_text_ref.blob_id])
    second = dict(text_document["observations"][0])
    second.update(
        observation_ordinal=1, source_proposal_ordinal=2,
        finding_text="Второе замечание о стене",
    )
    text_document["observations"].append(second)
    text_payload = canonical_bytes(text_document)
    text_ref = _ref("analysis.text_observations", text_payload)
    evidence = text_document["observations"][0]["evidence"][0]
    merge_evidence = MergeEvidence(
        evidence["page_number"], evidence["char_start"],
        evidence["char_end"], evidence["quote"],
    )
    merge_document = merge_grounded((
        MergeObservation(0, "dimensions", (merge_evidence,)),
        MergeObservation(1, "dimensions", (merge_evidence,)),
    ))
    merge_payload = canonical_bytes(merge_document)
    merge_ref = _ref("findings.merged", merge_payload)
    store.payloads = {
        text_ref.blob_id: text_payload,
        merge_ref.blob_id: merge_payload,
    }
    arguments["text_result"] = replace(
        arguments["text_result"], artifacts=(text_ref,),
    )
    arguments["merge_result"] = replace(
        arguments["merge_result"], artifacts=(merge_ref,),
        metrics={"text_artifact_sha256": text_ref.sha256,
                 "observation_count": 2, "group_count": 1},
    )
    plan = plan_recorded_saved_publication(store, **arguments).plan
    assert (plan.finding_count, plan.observation_count) == (1, 2)
    assert tuple(member.source_proposal_ordinal for member in plan.groups[0].members) == (0, 2)
    assert plan.groups[0].canonical.observation_ordinal == 0
    assert plan.rejected[0].proposal_ordinal == 1


@pytest.mark.parametrize("field,value,reason", [
    ("run_id", "run_01M2545JSD15ETSNNV904X991K", "saved_text_observations_invalid"),
    ("version_uid", "ver_01M2545JSD15ETSNNV904X991K", "saved_text_observations_invalid"),
    ("model_call_id", "mc_01M2545JSD15ETSNNV904X991K", "saved_call_or_source_binding_invalid"),
    ("model_id", "fixture/other-model", "saved_call_or_source_binding_invalid"),
    ("request_sha256", "0" * 64, "saved_call_or_source_binding_invalid"),
    ("response_sha256", "0" * 64, "saved_call_or_source_binding_invalid"),
    ("source_binding_sha256", "0" * 64, "saved_call_or_source_binding_invalid"),
])
def test_wrong_run_version_or_call_fact_is_refused(
    tmp_path: Path, field: str, value: str, reason: str,
) -> None:
    store, arguments = _case(tmp_path)
    arguments[field] = value
    # The reason is part of the claim: a bare SavedRecordedPlanError also matches
    # a refusal at an earlier gate (a stale stage_version once did exactly that).
    with pytest.raises(SavedRecordedPlanError, match=f"^{reason}$"):
        plan_recorded_saved_publication(store, **arguments)


def test_changed_source_or_stage_binding_is_refused(tmp_path: Path) -> None:
    store, arguments = _case(tmp_path)
    arguments["text_layer_ref"] = replace(arguments["text_layer_ref"], sha256="0" * 64)
    with pytest.raises(SavedRecordedPlanError, match="saved_call_or_source_binding_invalid"):
        plan_recorded_saved_publication(store, **arguments)

    store, arguments = _case(tmp_path)
    arguments["merge_result"] = replace(
        arguments["merge_result"], metrics={
            **arguments["merge_result"].metrics, "text_artifact_sha256": "0" * 64,
        },
    )
    with pytest.raises(SavedRecordedPlanError, match="saved_stage_binding_invalid"):
        plan_recorded_saved_publication(store, **arguments)
    assert store.reads == []


def test_changed_blob_bytes_and_forged_merge_are_refused(tmp_path: Path) -> None:
    store, arguments = _case(tmp_path)
    text_ref = arguments["text_result"].artifacts[0]
    store.payloads[text_ref.blob_id] += b" "
    with pytest.raises(SavedRecordedPlanError, match="saved_text_observations_invalid"):
        plan_recorded_saved_publication(store, **arguments)

    store, arguments = _case(tmp_path)
    merge_ref = arguments["merge_result"].artifacts[0]
    document = json.loads(store.payloads[merge_ref.blob_id])
    document["groups"] = []
    forged = canonical_bytes(document)
    forged_ref = _ref("findings.merged", forged)
    store.payloads = {
        arguments["text_result"].artifacts[0].blob_id:
            store.payloads[arguments["text_result"].artifacts[0].blob_id],
        forged_ref.blob_id: forged,
    }
    arguments["merge_result"] = replace(
        arguments["merge_result"], artifacts=(forged_ref,),
    )
    with pytest.raises(SavedRecordedPlanError, match="saved_merge_partition_invalid"):
        plan_recorded_saved_publication(store, **arguments)


def test_wrong_stage_and_metric_are_refused_before_publication(tmp_path: Path) -> None:
    store, arguments = _case(tmp_path)
    arguments["text_result"] = replace(
        arguments["text_result"], stage_version="0.0.0",
    )
    with pytest.raises(SavedRecordedPlanError, match="saved_stage_result_invalid"):
        plan_recorded_saved_publication(store, **arguments)
    assert store.reads == []

    store, arguments = _case(tmp_path)
    arguments["merge_result"] = replace(
        arguments["merge_result"], metrics={
            **arguments["merge_result"].metrics, "observation_count": 999,
        },
    )
    with pytest.raises(SavedRecordedPlanError, match="saved_merge_metrics_invalid"):
        plan_recorded_saved_publication(store, **arguments)


def test_text_stage_saved_under_the_retired_version_is_refused(tmp_path: Path) -> None:
    # The pin this file carried until the gate of 43670efc: a text stage recorded
    # under the version it had before W57A-SEAL-01B is not the stage the registry
    # now declares, so its evidence is refused before any Blob is read.
    assert _stage_version("text_analysis") != _RETIRED_TEXT_STAGE_VERSION
    store, arguments = _case(tmp_path)
    arguments["text_result"] = replace(
        arguments["text_result"], stage_version=_RETIRED_TEXT_STAGE_VERSION,
    )
    with pytest.raises(SavedRecordedPlanError, match="^saved_stage_result_invalid$"):
        plan_recorded_saved_publication(store, **arguments)
    assert store.reads == []


def test_merge_byte_digest_and_canonical_form_are_required(tmp_path: Path) -> None:
    store, arguments = _case(tmp_path)
    merge_ref = arguments["merge_result"].artifacts[0]
    store.payloads[merge_ref.blob_id] += b" "
    with pytest.raises(SavedRecordedPlanError, match="saved_merge_digest_mismatch"):
        plan_recorded_saved_publication(store, **arguments)

    store, arguments = _case(tmp_path)
    merge_ref = arguments["merge_result"].artifacts[0]
    document = json.loads(store.payloads[merge_ref.blob_id])
    noncanonical = json.dumps(document, ensure_ascii=False).encode("utf-8")
    noncanonical_ref = _ref("findings.merged", noncanonical)
    store.payloads[noncanonical_ref.blob_id] = noncanonical
    arguments["merge_result"] = replace(
        arguments["merge_result"], artifacts=(noncanonical_ref,),
    )
    with pytest.raises(SavedRecordedPlanError, match="saved_merge_not_canonical"):
        plan_recorded_saved_publication(store, **arguments)
