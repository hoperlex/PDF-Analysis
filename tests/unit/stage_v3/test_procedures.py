"""Actual copied procedures over source-bound synthetic responses; no provider."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pytest

from auditmanager.comparison.stage_ai.runtime import request_for_plan
from auditmanager.comparison.stage_ai.validation import StageAiValidationError
from auditmanager.comparison.stage_v3 import procedures as p
from auditmanager.comparison.stage_review.cards import prepare_cards
from tests.unit.stage_v3.recorded_fixture import synthetic_response


def snapshot():
    profiles, fragments = [], []
    for i, (side, value) in enumerate((("left", "100"), ("right", "120")), 1):
        profile = f"cpr_{i}"
        profiles.append({"profile_id": profile, "version_uid": f"ver_{i}", "page_number": 1, "side": side})
        fragments.append({"stage_text_fragment_id": f"stf_{i}", "page_profile_id": profile,
            "normalised_text": f"ширина прохода {value} мм", "box_anchor": {"x0": 10, "top": 20, "x1": 180, "bottom": 35}})
    return {"stage_pair_id": "pair-test", "stage_link_revision_id": "revision-test", "all_profiles": profiles,
            "fragments": fragments, "links": [], "differences": []}


def run_fixture(source):
    results, calls = {}, []
    for phase in ("review", "classify", "synthesize"):
        for _ in range(30):
            plans = p.plans_for(phase, source, results, "recorded-v3-fixture")
            pending = [plan for plan in plans if plan.group_id not in results]
            if not pending:
                break
            plan = pending[0]
            reply, payload = synthetic_response(request_for_plan(plan))
            results[plan.group_id] = p.parse(plan, {"output_text": reply.output_text, "stop_reason": reply.stop_reason}, source)
            calls.append(payload["_experimental_procedure"])
        else:
            pytest.fail("procedure loop did not terminate")
    return results, calls


def test_real_mapper_miner_dedupe_independent_verification_four_calls():
    source = snapshot()
    results, calls = run_fixture(source)
    assert calls == ["mapper", "miner", "dedupe", "verify"]
    cards = p.canonical_cards(source, results)
    assert len(cards) == 1 and cards[0]["class_name"] == "REVIEW"
    card = cards[0]
    assert card["experimental"]["parameters"][0]["old_value"] == "100"
    assert card["experimental"]["parameters"][0]["new_value"] == "120"
    assert card["experimental"]["parameters"][0]["verification"]["verdict"] == "CONFIRMED"
    assert set(card["evidence_ids"]) == {"stf_1", "stf_2"}
    assert card["experimental"]["coverage"]["complete"] is True
    assert card["experimental"]["norms_status"] == "not_checked"


def test_bad_mapper_coverage_refuses_before_mining():
    source = snapshot()
    plan = p.plans_for("review", source, {}, "fixture")[0]
    response, _ = synthetic_response(request_for_plan(plan))
    bad = json.loads(response.output_text)
    bad["regions"][0]["new_pages"] = [99]
    with pytest.raises(StageAiValidationError):
        p.parse(plan, {"output_text": json.dumps(bad), "stop_reason": "end_turn"}, source)


def test_miner_cannot_invent_a_source_or_one_sided_event():
    source = snapshot()
    results, _ = run_fixture(source)
    plan = p.plans_for("classify", source, results, "fixture")[0]
    response, _ = synthetic_response(request_for_plan(plan))
    bad = json.loads(response.output_text)
    bad["projectchanges"][0]["evidence_items"][0]["block_id"] = "invented"
    with pytest.raises(StageAiValidationError):
        p.parse(plan, {"output_text": json.dumps(bad), "stop_reason": "end_turn"}, source)
    bad = json.loads(response.output_text)
    bad["projectchanges"][0]["new_pages"] = []
    with pytest.raises(StageAiValidationError):
        p.parse(plan, {"output_text": json.dumps(bad), "stop_reason": "end_turn"}, source)


def test_verification_evidence_is_bound_to_the_parameter_batch():
    source = snapshot()
    results, _ = run_fixture(source)
    results = {k: v for k, v in results.items() if not k.startswith("v3:verify:")}
    plan = p.plans_for("synthesize", source, results, "fixture")[0]
    response, _ = synthetic_response(request_for_plan(plan))
    bad = json.loads(response.output_text)
    bad["results"][0]["evidence_refs"][0]["physical_page"] = 99
    with pytest.raises(StageAiValidationError):
        p.parse(plan, {"output_text": json.dumps(bad), "stop_reason": "end_turn"}, source)
    with pytest.raises(StageAiValidationError, match="incomplete"):
        p.canonical_cards(source, results)


def test_source_limits_refuse_without_truncation():
    source = snapshot()
    source["fragments"][0]["normalised_text"] = "x" * (p.MAX_CHARACTERS + 1)
    with pytest.raises(StageAiValidationError):
        p.source(source)
    source = snapshot(); source["fragments"].pop()
    with pytest.raises(StageAiValidationError, match="without_text"):
        p.source(source)


def test_exact_original_copies_and_no_original_runtime_imports():
    root = Path(p.__file__).parent / "original"
    manifest = json.loads((root / "SOURCE.json").read_text())
    for name, sha in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha
        if name.endswith(".py"):
            text = (root / name).read_text()
            assert "backend.app" not in text and "subprocess" not in text


def test_experimental_cards_do_not_invent_uncovered_raw_differences():
    assert prepare_cards({"raw": {"kind": "TEXT"}}, [], include_uncovered=False) == ()


def test_unmatched_original_supplemental_route_and_source_bound_hints():
    source = snapshot()
    for i, side in ((3, "left"), (4, "right")):
        profile = f"cpr_{i}"
        source["all_profiles"].append(dict(source["all_profiles"][0 if side == "left" else 1],
            profile_id=profile, page_number=2))
        source["fragments"].append(dict(source["fragments"][0 if side == "left" else 1],
            stage_text_fragment_id=f"stf_{i}", page_profile_id=profile))
    mapper = p.plans_for("review", source, {}, "fixture")[0]
    response, _ = synthetic_response(request_for_plan(mapper))
    mapping = json.loads(response.output_text)
    mapping["regions"][0].update(old_pages=[1], new_pages=[1])
    mapping.update(unmatched_old=[2], unmatched_new=[2])
    results = {mapper.group_id: p.parse(mapper, {"output_text": json.dumps(mapping), "stop_reason": "end_turn"}, source)}
    for phase in ("classify", "synthesize"):
        for _ in range(20):
            pending = [plan for plan in p.plans_for(phase, source, results, "fixture") if plan.group_id not in results]
            if not pending:
                break
            plan = pending[0]
            response, _ = synthetic_response(request_for_plan(plan))
            results[plan.group_id] = p.parse(plan, {"output_text": response.output_text, "stop_reason": "end_turn"}, source)
    assert sum(key.startswith("v3:unmatched:") for key in results) == 2
    cards = p.canonical_cards(source, results)
    assert cards and all(card["class_name"] == "REVIEW" for card in cards)
    assert p.reviewed(source, results)[3]["summary"]["complete"] is True


def test_invented_quote_and_verified_value_are_refused():
    source = snapshot()
    results, _ = run_fixture(source)
    plan = p.plans_for("classify", source, results, "fixture")[0]
    response, _ = synthetic_response(request_for_plan(plan))
    bad = json.loads(response.output_text)
    bad["projectchanges"][0]["evidence_items"][0]["relevant_fragment"] = "выдуманная цитата"
    with pytest.raises(StageAiValidationError):
        p.parse(plan, {"output_text": json.dumps(bad), "stop_reason": "end_turn"}, source)
    results = {key: value for key, value in results.items() if not key.startswith("v3:verify:")}
    plan = p.plans_for("synthesize", source, results, "fixture")[0]
    response, _ = synthetic_response(request_for_plan(plan))
    bad = json.loads(response.output_text)
    bad["results"][0]["new_value"] = "9999999"
    with pytest.raises(StageAiValidationError):
        p.parse(plan, {"output_text": json.dumps(bad), "stop_reason": "end_turn"}, source)


@pytest.mark.parametrize("value,text", [
    ("105 склад, 12,4 м²", "104 лестничная клетка 14,8 м2 105 склад 12,4 м2"),
    ("106 ТАМБУР, 4,2 м²", "106 тамбур 4,2 м2"),
    ("24,5", "101 холл 24,5 м2"),
    ("-12,4", "температура - 12,4 °c"),
])
def test_verifier_native_value_display_normalisation(value, text):
    assert p.value_in_native_text(value, text)


@pytest.mark.parametrize("value,text", [
    ("1,24", "12,4"), ("12,4", "1,24"), ("24,5", "124,5"),
    ("12 4", "124"), ("12,4", "12 4"), ("1, 24", "1 24"),
    ("-12,4", "12,4"), ("+12,4", "12,4"), ("24.5", "24,5"),
    ("12,4", "-12,4"), ("12,4", "+12,4"), ("12,4", "±12,4"), ("12,4", "−12,4"),
    ("12,4", "- 12,4"), ("12,4", "+ 12,4"), ("12,4", "± 12,4"),
    ("12,4", "температура−12,4 °c"), ("12,4", "температура-12,4 °c"),
    ("12,4", "температура+12,4 °c"), ("12,4", "температура±12,4 °c"),
    ("20", "10-20"),
    ("-20", "10-20"), ("12,4", "12,45"),
    ("105 склад, 12,4 м²", "106 склад 12,4 м2"),
    ("105 склад, 12,4 м²", "105 склад 12,5 м2"),
    ("А-105", "А105"), ("м,2", "м2"),
])
def test_verifier_native_value_preserves_numbers_and_significant_separators(value, text):
    assert not p.value_in_native_text(value, text)
