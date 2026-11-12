"""Proposal advice stays source-bound, fresh-consent-only and separate from human decisions."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from auditmanager.analysis.extended.finding_proposals import (
    build_proposal_review_request, parse_proposal_review_reply, proposal_policy, validate_proposal_policy,
)
from auditmanager.analysis.extended.substantive_review import build_substantive_request
from auditmanager.analysis.extended.v2_quality import quality_policy
from tests.unit.analysis_extended.test_v2_quality import review_record
from tests.unit.analysis_extended.test_v2_quality_runtime import QualityAdapter
from tests.unit.analysis_extended import test_original_review_runtime as harness


def row(**changes):
    return review_record(proposed_severity="operational",
        recommendation_text="Сверить обозначение аппарата на схеме и в спецификации.", **changes)


def parse(rows, *, rejected=None):
    return parse_proposal_review_reply(json.dumps({"reviews": rows}),
        inputs={"o1": {"source_ids": ["s1"], "context_complete": True}},
        sources=[{"source_id": "s1", "quote": "Реальная цитата"}],
        attached_image_ids=set(), rejected=rejected)


def test_advice_fields_survive_but_do_not_become_an_expert_decision():
    source = row()
    before = deepcopy(source)
    (accepted,) = parse([source])
    assert accepted["proposed_severity"] == "operational"
    assert accepted["recommendation_text"] == source["recommendation_text"]
    assert accepted["expert_decision"] is False
    assert source == before


@pytest.mark.parametrize("change", [
    {"proposed_severity": "confirmed"}, {"recommendation_text": ""}, {"recommendation_text": "   "},
    {"recommendation_text": "x" * 4001},
    {"source_evidence": [{"source_id": "s1", "quote": "Придуманная цитата"}]},
])
def test_bad_proposals_and_forged_evidence_are_retained_as_refusals(change):
    source = {**row(), **change}
    refused = []
    assert parse([source], rejected=refused) == []
    assert len(refused) == 1 and refused[0]["record"] == source


def test_a_duplicate_cannot_replace_the_first_source_bound_proposal():
    refused = []
    accepted = parse([row(), {**row(), "proposed_severity": "critical"}], rejected=refused)
    assert len(accepted) == 1 and accepted[0]["proposed_severity"] == "operational"
    assert len(refused) == 1 and refused[0]["reply_ordinal"] == 1


def test_a_refused_first_record_cannot_supply_the_proposal_of_a_later_valid_record():
    refused = []
    invalid = {**row(), "proposed_severity": "critical",
        "source_evidence": [{"source_id": "s1", "quote": "Придуманная цитата"}]}
    valid = {**row(), "proposed_severity": "economic"}
    (accepted,) = parse([invalid, valid], rejected=refused)
    assert accepted["proposed_severity"] == "economic"
    assert refused[0]["record"] == invalid and refused[0]["reply_ordinal"] == 0


def test_a_new_prompt_is_separately_bound_without_changing_the_legacy_request():
    kwargs = dict(model_id="model", run_id="run", section="EOM", items=[], sources=[], context={}, image_ids=set())
    old = build_substantive_request(**kwargs)
    before = deepcopy(old.body)
    new = build_proposal_review_request(**kwargs)
    assert old.body == before and old.request_sha256 != new.request_sha256
    assert "proposed_severity" not in old.body["output_config"]["format"]["schema"]["properties"]["reviews"]["items"]["properties"]
    assert "proposed_severity" in new.body["output_config"]["format"]["schema"]["properties"]["reviews"]["items"]["required"]
    frozen = proposal_policy()
    assert validate_proposal_policy(frozen)
    frozen["bundle_sha256"] = "0" * 64
    assert validate_proposal_policy(frozen, compare_bundle=False)
    with pytest.raises(ValueError, match="requires_consent"):
        validate_proposal_policy(frozen)


def test_fresh_v2_preserves_advice_through_the_existing_six_procedures(monkeypatch):
    class Adapter(QualityAdapter):
        def complete(self, request):
            response = super().complete(request)
            payload = json.loads(request.body["messages"][0]["content"])
            if payload.get("version") == "substantive-v2-v1":
                document = json.loads(response.output_text)
                for advice in document["reviews"]:
                    advice.update(proposed_severity="economic", recommendation_text="Сверить указанное решение по исходной схеме.")
                return replace(response, output_text=json.dumps(document))
            return response
    monkeypatch.setattr(harness, "WorkflowAdapter", Adapter)
    state, adapter, _ = harness.run_v2(monkeypatch,
        {**harness.MARKED, "quality_policy": quality_policy(), "finding_proposals": proposal_policy()})
    assert len(state["procedures"]) == 6
    assert state["finding_proposals"] == proposal_policy()
    assert state["observations"] and all(item["proposed_severity"] == "economic" for item in state["observations"])
    assert all(item["recommendation_text"] == "Сверить указанное решение по исходной схеме." for item in state["observations"])
    assert all(item["critic"]["expert_decision"] is False for item in state["observations"])
    assert all("decided_severity" not in item for item in state["observations"])
