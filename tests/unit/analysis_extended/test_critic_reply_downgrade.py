"""`REVIEW-FIX-ANALYSIS-1102` (S1-sprints-03): one unsatisfiable critic row no longer refuses the reply.

A rejection-type reason with ``enough_source`` needs the decision ``reject``, and ``reject`` needs
confidence 0.75, a source check and verbatim evidence. A row below those thresholds could never satisfy
both guards, so it is kept as a request for a human and says so in its stored note.
"""
import json

import pytest

from auditmanager.analysis.extended.review import parse_critic_reply

QUOTE = "Размер проёма 1200 мм принят по проекту"
SOURCES = [{"source_id": "s1", "kind": "text", "source_type": "native_text", "page_number": 1, "quote": QUOTE}]


def _observations(*keys):
    return {key: {"title": f"Наблюдение {key}", "description": "Описание", "source_ids": ["s1"]} for key in keys}


def _row(key="o1", **override):
    row = {"input_id": key, "source_ids": ["s1"], "llm_decision": "reject",
        "human_taxonomy_reason": "value_already_correct", "confidence": 0.6, "explanation": "Значение уже верно",
        "evidence_checked": True, "source_dependency": "enough_source", "needs_correction": False,
        "suggested_fix": "", "source_evidence": [{"source_id": "s1", "quote": "Размер проёма 1200 мм"}]}
    return row | override


def _parse(*rows, keys=("o1",)):
    return parse_critic_reply(json.dumps({"reviews": list(rows)}, ensure_ascii=False),
        observations=_observations(*keys), sources=SOURCES)


def test_a_low_confidence_rejection_is_kept_as_a_request_for_a_human_with_the_models_text():
    (stored,) = _parse(_row())
    assert stored["llm_decision"] == "needs_human"
    assert stored["llm_decision_original"] == "reject"
    assert stored["program_downgrade"] == "rejection_below_thresholds"
    # the line the reviewer reads says the program lowered the recommendation, and keeps the model's text
    assert stored["explanation"].startswith("Программа понизила рекомендацию модели")
    assert stored["explanation"].endswith("Значение уже верно")
    # the model's own reason and numbers are not rewritten, and no expert act is claimed
    assert stored["human_taxonomy_reason"] == "value_already_correct" and stored["confidence"] == 0.6
    assert stored["expert_decision"] is False and stored["status"] == "requires_expert_review"


@pytest.mark.parametrize("override", [
    {"evidence_checked": False, "confidence": 0.95},
    {"source_evidence": [], "confidence": 0.95},
    {"llm_decision": "accept", "confidence": 0.5},
    {"llm_decision": "rewrite", "needs_correction": True, "suggested_fix": "Уточнить", "confidence": 0.5},
], ids=["source-not-checked", "no-evidence", "accept-with-rejection-reason", "rewrite-with-rejection-reason"])
def test_each_threshold_that_is_missed_downgrades_instead_of_refusing(override):
    (stored,) = _parse(_row(**override))
    assert stored["llm_decision"] == "needs_human" and stored["llm_decision_original"] == override.get("llm_decision", "reject")


def test_the_other_rows_of_the_reply_survive_one_downgraded_row():
    supported = _row("o2", confidence=0.9)
    first, second = _parse(_row("o1"), supported, keys=("o1", "o2"))
    assert first["llm_decision"] == "needs_human" and "program_downgrade" in first
    assert second["llm_decision"] == "reject" and "program_downgrade" not in second
    assert second["explanation"] == "Значение уже верно"


def test_a_supported_rejection_is_not_touched():
    (stored,) = _parse(_row(confidence=0.75))
    assert stored["llm_decision"] == "reject"
    assert not {"llm_decision_original", "program_downgrade"} & set(stored)


@pytest.mark.parametrize("override,code", [
    # not a rejection-type reason: a reject below the thresholds is still refused
    ({"human_taxonomy_reason": "acceptable_design_solution"}, "critic_rejection_without_evidence"),
    # thresholds met but the decision contradicts the reason: still refused, not rewritten by the program
    ({"llm_decision": "accept", "confidence": 0.95}, "critic_reason_decision_inconsistent"),
    # the downgrade does not excuse a correction request without text
    ({"needs_correction": True, "suggested_fix": " "}, "critic_correction_intent_invalid"),
    # source dependency other than enough_source keeps its own rule
    ({"source_dependency": "needs_more_context"}, "critic_insufficient_source_decision"),
], ids=["other-reason", "supported-but-contradicting", "empty-fix", "needs-more-context"])
def test_the_other_guards_still_refuse(override, code):
    with pytest.raises(ValueError, match=code):
        _parse(_row(**override))
