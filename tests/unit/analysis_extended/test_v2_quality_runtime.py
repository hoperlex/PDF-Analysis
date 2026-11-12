"""Fresh v2 quality authority exercises the existing stages; legacy authority stays frozen."""
import json
from dataclasses import replace

import pytest

from auditmanager.analysis.public import ModelResponse, v2_quality_policy
from auditmanager.runs import preflight, stage_layout
from tests.unit.analysis_extended import test_original_review_runtime as harness
from tests.unit.analysis_extended.test_v2_quality import review_record
from tests.unit.runs.test_cost_preflight import registry, service, version, estimate
from tests.unit.runs import test_stage_plan_consent as planned


@pytest.fixture(autouse=True)
def fresh_v2_environment(monkeypatch):
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v2")
    monkeypatch.delenv("AUDITMANAGER_EXTENDED_ANALYSIS", raising=False)
    monkeypatch.delenv("AUDITMANAGER_V2_QUALITY", raising=False)


class QualityAdapter(harness.WorkflowAdapter):
    omit_reviews = False
    unchecked = False

    def complete(self, request):
        payload = json.loads(request.body["messages"][0]["content"])
        if payload.get("version") != "substantive-v2-v1":
            return super().complete(request)
        self.requests.append(request)
        sources = {source["source_id"]: source for source in payload["sources"]}
        reviews = []
        for item in payload["observations"]:
            images = set(item["source_ids"]) & set(payload["attached_image_ids"])
            quotes = [{"source_id": ref, "quote": sources[ref]["quote"][:100]}
                for ref in item["source_ids"] if sources.get(ref, {}).get("quote")]
            row = review_record(input_id=item["input_id"], source_ids=item["source_ids"],
                source_evidence=quotes[:1], visual_evidence=[{"source_id": ref, "explanation": "Факт виден на изображении"}
                    for ref in sorted(images)[:1]])
            if self.unchecked:
                row["substantive_checks"]["alternatives"]["checked"] = False
            reviews.append(row)
        return ModelResponse(json.dumps({"reviews": [] if self.omit_reviews else reviews}), "end_turn", 100, 100, 1)


def run_quality(monkeypatch, adapter=QualityAdapter):
    monkeypatch.setattr(harness, "WorkflowAdapter", adapter)
    return harness.run_v2(monkeypatch, {**harness.MARKED, "quality_policy": v2_quality_policy()})


def test_fresh_quality_run_reviews_inside_the_same_six_stages_and_preserves_every_origin(monkeypatch):
    state, adapter, saved = run_quality(monkeypatch)
    assert [row["id"] for row in state["procedures"]] == ["block_analysis", "comprehensive_analysis", "finding_merge",
        "norm_verification", "finding_review", "finding_correction"]
    assert state["input_passport"]["crop_verification"] == "verified"
    assert state["input_passport"]["crop_count"] == 10
    assert state["consolidation"]["version"] == "ensemble-linked-v1"
    assert sum(group["origin_count"] for group in state["consolidated_observations"] ) == len(state["observations"])
    assert len({row["observation_id"] for row in state["observations"]}) == len(state["observations"])
    assert state["original_review"]["mode"] == "substantive"
    assert state["substantive_review"]["reviewed"] == len(state["observations"])
    assert all(row["critic"]["model_called"] for row in state["observations"])
    assert any(json.loads(request.body["messages"][0]["content"]).get("version") == "substantive-v2-v1" for request in adapter.requests)
    assert next(row for row in state["procedures"] if row["id"] == "finding_review")["status"] == "completed"


def test_missing_critic_records_stay_unreviewed_not_structural_pass(monkeypatch):
    class Missing(QualityAdapter):
        omit_reviews = True
    state, _, _ = run_quality(monkeypatch, Missing)
    assert next(row for row in state["procedures"] if row["id"] == "finding_review")["status"] == "partial"
    assert all(row["critic"]["original_verdict"] == "not_reviewed" for row in state["observations"])
    assert state["substantive_review"]["reviewed"] == 0
    assert state["observations"]


def test_unchecked_alternatives_cannot_become_pass_even_if_the_model_accepts(monkeypatch):
    class Unchecked(QualityAdapter):
        unchecked = True
    state, _, _ = run_quality(monkeypatch, Unchecked)
    assert all(row["critic"]["original_verdict"] != "pass" for row in state["observations"])
    assert all(row["critic"]["llm_decision"] == "needs_human" for row in state["observations"])


def test_fresh_preflight_prices_the_review_and_rollback_keeps_legacy_authority(registry, monkeypatch):
    monkeypatch.delenv("AUDITMANAGER_V2_QUALITY", raising=False)
    policy = service(registry)
    current = estimate(policy, version("AR", 500, 1))
    authority = json.loads(current.authority_json)["extended_review"]
    assert authority["quality_policy"] == v2_quality_policy()
    assert stage_layout.rows_in_use(authority) == policy.stage_rows_in_use() == ("text", "blocks", "cross_check", "norms", "review")
    monkeypatch.setenv("AUDITMANAGER_V2_QUALITY", "0")
    legacy = estimate(policy, version("AR", 500, 1))
    assert "quality_policy" not in json.loads(legacy.authority_json)["extended_review"]
    assert current.as_dict()["calls"] > legacy.as_dict()["calls"]
    assert current.as_dict()["estimated_cost_micros"] > legacy.as_dict()["estimated_cost_micros"]
    assert stage_layout.rows_in_use(harness.MARKED) == ("text", "blocks", "cross_check", "norms")


def test_fresh_planned_consent_prices_and_binds_the_critic_model(registry, monkeypatch):
    monkeypatch.setattr(planned.Preflight, "version", planned.source_version("AR", 500, 1))
    policy = planned.service(registry)
    draft = planned.draft()
    value = planned.estimate(policy, draft)
    assert value.stage_plan.rows == ("text", "blocks", "cross_check", "norms", "review")
    assert all(cell.row != "correction" for cell in value.stage_plan.cells)
    assert sum(row["calls"] for row in value.as_dict()["models"]) == value.as_dict()["calls"]
    accepted = value.approve(planned.confirm(value), actor_user_uid="expert")
    assert accepted["extended_review"]["quality_policy"] == v2_quality_policy()
    assert accepted["stage_plan_digest"] == value.stage_plan.digest
    answer = planned.start_readiness(policy, planned.SettingsSession(), draft, version_uid=planned.VERSION)
    assert answer["ready"] and answer["estimate_digest"] == value.estimate_digest
    assert "review:main" in {cell["cell_key"] for cell in answer["cells"]}

    # The active critic must have a host; the unused correction row need not have one.
    unavailable = replace(draft, cells=tuple(replace(cell, model_id="gpt-6-sol", effort="medium")
        if cell.row in {"review", "correction"} else cell for cell in draft.cells))
    blocked = planned.start_readiness(policy, planned.SettingsSession(), unavailable, version_uid=planned.VERSION)
    assert not blocked["ready"]
    assert [cell["cell_key"] for cell in blocked["cells"] if not cell["available"]] == ["review:main"]
    monkeypatch.setenv("AUDITMANAGER_V2_QUALITY", "0")
    legacy = planned.estimate(policy, draft)
    assert legacy.estimate_digest != value.estimate_digest
    assert value.as_dict()["calls"] > legacy.as_dict()["calls"]
