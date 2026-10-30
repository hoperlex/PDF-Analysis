"""Optional legacy metadata stays neutral; new model hints remain strictly typed."""

from dataclasses import asdict

import pytest

from auditmanager.comparison.stage_ai.classifier import build_classification_request, parse_classification
from auditmanager.comparison.stage_ai.model import EvidenceGroup
from auditmanager.comparison.stage_ai.validation import StageAiValidationError
from tests.unit.comparison.stage_ai.test_core import classification_answer, evidence
from tests.unit.comparison.stage_ai.test_graphic import graphic_scene
from tests.unit.comparison.stage_ai.test_runtime import phase_to_end, uid


def plan_and_answer():
    plan = build_classification_request(EvidenceGroup("group", (evidence(),)), model="model")
    return plan, classification_answer(plan)


@pytest.mark.parametrize("hints", [
    {"materiality": "material", "importance": "high", "detail_increased": True},
    {"materiality": "non_material", "importance": "normal", "detail_increased": False},
])
def test_genuine_model_hints_are_retained_without_changing_evidence_identity(hints):
    plan, answer = plan_and_answer()
    neutral = parse_classification(plan, answer).cards[0]
    answer["cards"][0].update(hints)
    card = parse_classification(plan, answer).cards[0]
    assert {key: asdict(card)[key] for key in hints} == hints
    assert card.card_key == neutral.card_key and card.evidence_digest == neutral.evidence_digest


def test_legacy_missing_hints_are_unknown_without_category_based_importance():
    plan, answer = plan_and_answer()
    card = parse_classification(plan, answer).cards[0]
    assert card.category == "electrical_load"
    assert (card.materiality, card.importance, card.detail_increased) == ("unknown", "unknown", False)


@pytest.mark.parametrize("hints", [
    {"materiality": "critical"}, {"materiality": None}, {"materiality": []},
    {"importance": "low"}, {"importance": 1},
    {"detail_increased": "true"}, {"detail_increased": 1}, {"detail_increased": None},
    {"expert_verdict": "accepted"},
])
def test_invalid_hints_and_expert_verdict_keys_refuse_the_whole_group(hints):
    plan, answer = plan_and_answer()
    answer["cards"][0].update(hints)
    with pytest.raises(StageAiValidationError):
        parse_classification(plan, answer)


@pytest.mark.parametrize("kind", ["title", "cards"])
def test_metadata_extension_preserves_existing_caps(kind):
    plan, answer = plan_and_answer()
    answer["cards"][0].update(materiality="material", importance="high", detail_increased=True)
    if kind == "title":
        answer["cards"][0]["title"] = "а" * 261
    else:
        answer["cards"] *= 401
    with pytest.raises(StageAiValidationError):
        parse_classification(plan, answer)


def test_hint_schema_and_prompt_have_new_content_identity():
    plan, _answer = plan_and_answer()
    assert plan.prompt_version == "stage-classifier/2"
    card = plan.response_schema["properties"]["cards"]["items"]
    assert {"materiality", "importance", "detail_increased"} <= set(card["required"])
    assert card["properties"]["importance"]["enum"] == ["high", "normal", "unknown"]
    assert "Не выводи high только из category" in plan.instructions


def test_graphical_pages_do_not_promote_conflicting_hints():
    runtime, item, repo, jobs, caller = graphic_scene()
    original = caller.transform

    def hints(source, answer, number):
        answer = original(source, answer, number)
        for card in answer["cards"]:
            card.update(materiality="material", importance="high" if number == 1 else "normal",
                        detail_increased=number == 1)
        return answer

    caller.transform = hints
    runtime.advance(item, run_id=uid("crn", 1), phase="classify")
    runtime.advance(item, run_id=uid("crn", 1), phase="classify")
    jobs.state, jobs.record.consent_no = "running", 2
    assert phase_to_end(runtime, item, "classify")["completed"] == 1
    card = next(iter(repo.answers.values()))["cards"][0]
    assert card["materiality"] == "material" and card["importance"] == "unknown" and card["detail_increased"] is False
