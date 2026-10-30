"""Source binding, atomic validation and conservative Stage AI publication rules."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, replace

import pytest

from auditmanager.comparison.stage_ai import (
    AtomicEvidence, EvidenceGroup, Fragment, ReviewGroup, ReviewItem, StageAiValidationError,
    SynthesisGroup, accept_review_group, build_classification_request, build_review_requests,
    build_synthesis_request, parse_classification, parse_review_chunk, parse_synthesis,
)
from auditmanager.comparison.stage_ai.validation import parse_document, supported_claim


def uid(prefix: str, number: int) -> str:
    return f"{prefix}_{number:026d}"


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def fragment(number: int, side: str, text: str = "Нагрузка 10 кВт", *, profile: int | None = None) -> Fragment:
    return Fragment(uid("stf", number), uid("cpr", profile or (1 if side == "left" else 2)),
                    side, text, sha(f"{number}:{text}"), (10.0, 10.0, 80.0, 20.0))


def review_group(*, deterministic: str = "CHANGED") -> ReviewGroup:
    left, right = fragment(1, "left"), fragment(2, "right", "Нагрузка 20 кВт")
    item = ReviewItem(uid("std", 1), (left.fragment_id,), (right.fragment_id,), deterministic)
    return ReviewGroup("sheet-group-1", (left, right), (item,), (left.profile_id,), (right.profile_id,))


def review_answer(plan, *, status="CHANGED", confidence="high", summary="Нагрузка 10 кВт → 20 кВт"):
    source = plan.payload
    left = [f["fragment_id"] for f in source["fragments"] if f["side"] == "left"
            and f["fragment_id"] in source["required_fragment_ids"]]
    right = [f["fragment_id"] for f in source["fragments"] if f["side"] == "right"
             and f["fragment_id"] in source["required_fragment_ids"]]
    return {"group_id": plan.group_id, "chunk_id": plan.unit_key, "source_sha256": plan.source_sha256,
            "decisions": [{"left_fragment_ids": left, "right_fragment_ids": right,
                           "status": status, "confidence": confidence, "summary": summary,
                           "reason": "Сопоставлены исходные фрагменты.",
                           "actual_right_profile_ids": sorted({f["profile_id"] for f in source["fragments"]
                                                               if f["fragment_id"] in right}) if status == "MOVED" else []}]}


def evidence(number=1, *, status="CHANGED", hint="PROJECT_CHANGE") -> AtomicEvidence:
    left = () if status == "ADDED" else (uid("stf", number * 2),)
    right = () if status == "REMOVED" else (uid("stf", number * 2 + 1),)
    return AtomicEvidence(uid("std", number), sha(str(number)), status, left, right,
                          "" if status == "ADDED" else "Нагрузка 10 кВт",
                          "" if status == "REMOVED" else "Нагрузка 20 кВт",
                          "Изменена нагрузка.", hint)


def classification_answer(plan, *, class_name="PROJECT_CHANGE", system="electrical", title="Изменена нагрузка"):
    return {"group_id": plan.group_id, "source_sha256": plan.source_sha256,
            "cards": [{"class": class_name, "category": "electrical_load", "title": title,
                       "system": system, "evidence_ids": [e["evidence_id"] for e in plan.payload["atomic_evidence"]]}]}


def synthesis_plan(*, status="CHANGED", hint="PROJECT_CHANGE", source_uncertain=False):
    item = evidence(status=status, hint=hint)
    classification = build_classification_request(EvidenceGroup("group", (item,)), model="pinned-model")
    answer = classification_answer(classification, class_name="REVIEW" if hint == "REVIEW" else hint)
    cards = parse_classification(classification, answer).cards
    return build_synthesis_request(SynthesisGroup("group", (item,), cards, source_uncertain), model="pinned-model")


def synthesis_answer(plan, *, decision="REAL_CHANGE", kind="QUANTITY_OR_CAPACITY_CHANGED"):
    return {"group_id": plan.group_id, "source_sha256": plan.source_sha256,
            "evidence_ids": [e["evidence_id"] for e in plan.payload["atomic_evidence"]],
            "decision": decision, "type": kind,
            "title": "Изменена нагрузка", "reason": "Нагрузка 10 кВт → 20 кВт"}


def test_request_key_binds_source_prompt_schema_and_pinned_model() -> None:
    group = review_group()
    first = build_review_requests(group, model="model-a")[0]
    again = build_review_requests(group, model="model-a")[0]
    other_model = build_review_requests(group, model="model-b")[0]
    other_source = build_review_requests(replace(group, fragments=(group.fragments[0],
        replace(group.fragments[1], text="Нагрузка 30 кВт", content_key=sha("30")))), model="model-a")[0]
    assert first == again and len({first.content_key, other_model.content_key, other_source.content_key}) == 3
    assert first.estimate_group().prompt_chars == first.prompt_chars
    assert first.estimate_group().calls == 1 and first.estimate_group().images == 0
    schema = first.response_schema
    schema["properties"].clear()
    assert first.response_schema["properties"]
    assert first.request_document()["metadata"]["source_sha256"] == first.source_sha256


def test_chunk_limit_and_whole_group_acceptance() -> None:
    fragments, items = [], []
    for number in range(1, 42):
        left, right = fragment(number * 2, "left"), fragment(number * 2 + 1, "right")
        fragments.extend((left, right))
        items.append(ReviewItem(uid("std", number), (left.fragment_id,), (right.fragment_id,), "SAME"))
    group = ReviewGroup("large-group", tuple(fragments), tuple(items), (uid("cpr", 1),), (uid("cpr", 2),))
    plans = build_review_requests(group, model="model")
    assert [len(plan.payload["items"]) for plan in plans] == [40, 1]
    responses = {plan.unit_key: review_answer(plan, status="SAME", summary="Смысл совпадает") for plan in plans}
    result = accept_review_group(group, plans, responses)
    assert len(result.raw_evidence_ids) == 41 and len(result.decisions) == 2
    with pytest.raises(StageAiValidationError, match="chunk_coverage"):
        accept_review_group(group, plans, {plans[0].unit_key: responses[plans[0].unit_key]})


def test_overlapping_items_are_never_split_across_chunk() -> None:
    shared = fragment(1, "left")
    right = tuple(fragment(number + 1, "right") for number in range(1, 42))
    items = tuple(ReviewItem(uid("std", n), (shared.fragment_id,), (r.fragment_id,), "CHANGED")
                  for n, r in enumerate(right, 1))
    group = ReviewGroup("connected", (shared, *right), items, (shared.profile_id,), (uid("cpr", 2),))
    with pytest.raises(ValueError, match="connected_component"):
        build_review_requests(group, model="model")


@pytest.mark.parametrize("mutation", ["digest", "unknown", "duplicate", "missing", "extra_key"])
def test_reviewer_rejects_entire_invalid_chunk(mutation: str) -> None:
    plan = build_review_requests(review_group(), model="model")[0]
    answer = review_answer(plan)
    if mutation == "digest": answer["source_sha256"] = "f" * 64
    elif mutation == "unknown": answer["decisions"][0]["left_fragment_ids"] = [uid("stf", 999)]
    elif mutation == "duplicate": answer["decisions"].append(copy.deepcopy(answer["decisions"][0]))
    elif mutation == "missing": answer["decisions"] = []
    else: answer["decisions"][0]["invented"] = True
    with pytest.raises(StageAiValidationError):
        parse_review_chunk(plan, answer)


def test_ai_same_never_removes_raw_change_and_low_confidence_is_uncertain() -> None:
    group = review_group()
    original = asdict(group)
    plan = build_review_requests(group, model="model")[0]
    decision = parse_review_chunk(plan, review_answer(plan, status="SAME"))[0]
    assert decision.status == "UNCERTAIN" and decision.model_status == "SAME"
    assert "same_conflicts_with_deterministic_change" in decision.policy_reasons
    low = parse_review_chunk(plan, review_answer(plan, status="SAME", confidence="medium"))[0]
    assert low.status == "UNCERTAIN" and "same_moved_requires_high_confidence" in low.policy_reasons
    result = accept_review_group(group, (plan,), {plan.unit_key: review_answer(plan, status="SAME")})
    assert result.raw_evidence_ids == (group.items[0].evidence_id,)
    assert asdict(group) == original


def test_moved_membership_uses_profiles_not_display_page_numbers() -> None:
    group = review_group(deterministic="SAME")
    plan = build_review_requests(group, model="model")[0]
    inside = parse_review_chunk(plan, review_answer(plan, status="MOVED"))[0]
    assert inside.status == "SAME" and inside.actual_right_profile_ids == ()
    outside_group = replace(group, accepted_right_profiles=(uid("cpr", 7),))
    outside_plan = build_review_requests(outside_group, model="model")[0]
    outside = parse_review_chunk(outside_plan, review_answer(outside_plan, status="MOVED"))[0]
    assert outside.status == "MOVED" and outside.actual_right_profile_ids == (uid("cpr", 2),)


def test_unsupported_reviewer_numbers_become_safe_uncertain_text() -> None:
    plan = build_review_requests(review_group(), model="model")[0]
    decision = parse_review_chunk(plan, review_answer(plan, summary="Нагрузка 999 кВт"))[0]
    assert decision.status == "UNCERTAIN" and "999" not in decision.summary
    assert "unsupported_model_claim" in decision.policy_reasons


def test_classifier_preserves_evidence_and_stable_card_identity() -> None:
    group = EvidenceGroup("group", (evidence(),))
    plan = build_classification_request(group, model="model")
    first = parse_classification(plan, classification_answer(plan)).cards[0]
    second = parse_classification(plan, classification_answer(plan, title="Нагрузка скорректирована", system="unknown")).cards[0]
    assert first.card_key == second.card_key and first.evidence_digest == second.evidence_digest
    assert first.class_name == "PROJECT_CHANGE" and first.system == "electrical"
    assert first.evidence_ids == (group.evidence[0].evidence_id,)


@pytest.mark.parametrize("mutation", ["system", "missing", "hallucinated", "duplicate", "unsupported"])
def test_classifier_rejects_invalid_group_atomically(mutation: str) -> None:
    plan = build_classification_request(EvidenceGroup("group", (evidence(),)), model="model")
    answer = classification_answer(plan)
    if mutation == "system": answer["cards"][0]["system"] = "made-up"
    elif mutation == "missing": answer["cards"] = []
    elif mutation == "hallucinated": answer["cards"][0]["evidence_ids"] = [uid("std", 999)]
    elif mutation == "duplicate": answer["cards"].append(copy.deepcopy(answer["cards"][0]))
    else: answer["cards"][0]["title"] = "Нагрузка 999 кВт"
    with pytest.raises(StageAiValidationError):
        parse_classification(plan, answer)


def test_classifier_deterministic_hints_override_and_uncertain_cannot_promote() -> None:
    service = build_classification_request(EvidenceGroup("group", (evidence(hint="SERVICE_STRUCTURE"),)), model="model")
    card = parse_classification(service, classification_answer(service)).cards[0]
    assert card.class_name == "SERVICE_STRUCTURE" and card.model_class == "PROJECT_CHANGE"
    uncertain = build_classification_request(EvidenceGroup("group", (evidence(hint="REVIEW"),)), model="model")
    with pytest.raises(StageAiValidationError, match="must_remain_review"):
        parse_classification(uncertain, classification_answer(uncertain))


def test_synthesis_accepts_bound_two_sided_change() -> None:
    plan = synthesis_plan()
    result = parse_synthesis(plan, synthesis_answer(plan))
    assert result.decision == "REAL_CHANGE" and result.source_sha256 == plan.source_sha256


@pytest.mark.parametrize("case", ["one_sided", "uncertain_link", "review", "unchanged", "unsupported", "wrong_ids", "wrong_type"])
def test_synthesis_refuses_unproved_high_level_claim(case: str) -> None:
    plan = synthesis_plan(status="ADDED" if case == "one_sided" else "SAME" if case == "unchanged" else "CHANGED",
                          hint="REVIEW" if case == "review" else "PROJECT_CHANGE",
                          source_uncertain=case == "uncertain_link")
    answer = synthesis_answer(plan)
    if case == "one_sided": answer["reason"] = "Нагрузка 20 кВт"
    elif case == "unsupported": answer["title"] = "Нагрузка 999 кВт"
    elif case == "wrong_ids": answer["evidence_ids"] = [uid("std", 999)]
    elif case == "wrong_type": answer["type"] = "DETAIL_LEVEL_INCREASED"
    with pytest.raises(StageAiValidationError):
        parse_synthesis(plan, answer)


def test_detail_only_cannot_claim_a_new_object() -> None:
    plan = synthesis_plan()
    answer = synthesis_answer(plan, decision="DETAIL_ONLY", kind="DETAIL_LEVEL_INCREASED")
    answer["title"] = "Добавлена новая нагрузка"
    with pytest.raises(StageAiValidationError, match="detail_claims_new_object"):
        parse_synthesis(plan, answer)


def test_strict_json_and_exact_numeric_grounding() -> None:
    with pytest.raises(StageAiValidationError):
        parse_document('{"group_id":"a","group_id":"b"}')
    with pytest.raises(StageAiValidationError):
        parse_document('{"value": NaN}')
    assert not supported_claim("Нагрузка 10 кВт", "Нагрузка 100 кВт")
    assert supported_claim("Нагрузка 10 кВт", "Нагрузка 10 кВт")
    assert not supported_claim("ЩР-99", "ЩР-1")
    assert not supported_claim("ЩР99", "ЩР1")
    assert not supported_claim("−10", "10")
    assert not supported_claim("±10", "10")


def test_synthesis_rechecks_stored_card_evidence_digest() -> None:
    item = evidence()
    plan = build_classification_request(EvidenceGroup("group", (item,)), model="model")
    card = parse_classification(plan, classification_answer(plan)).cards[0]
    with pytest.raises(ValueError, match="digest_mismatch"):
        build_synthesis_request(SynthesisGroup("group", (item,),
                                               (replace(card, evidence_digest="f" * 64),)), model="model")


def test_mapping_response_and_json_response_have_identical_validation() -> None:
    plan = build_classification_request(EvidenceGroup("group", (evidence(),)), model="model")
    answer = classification_answer(plan)
    assert parse_classification(plan, answer) == parse_classification(plan, json.dumps(answer, ensure_ascii=False))
