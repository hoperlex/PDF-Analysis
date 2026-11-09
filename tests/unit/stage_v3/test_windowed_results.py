"""windowed-v1 results: merging, ordering, dedupe batches, verification units, source-bound refusals, coverage, cards."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from auditmanager.comparison.stage_ai.validation import StageAiValidationError, canonical_json, digest
from auditmanager.comparison.stage_v3 import procedures as legacy
from auditmanager.comparison.stage_v3 import windowed as w
from auditmanager.comparison.stage_v3.original import dedupe as original_dedupe
from auditmanager.comparison.stage_v3.policy import LIMITS, VERSION
from tests.unit.stage_v3.windowed_events import event, hint, miner_result
from tests.unit.stage_v3.windowed_fixture import (MAPPER_SOURCE, MODEL, PHASES, answer_of, drive, evidence_for, hint_for,
                                                  mapping_edit, numbered, region, row_of, snapshot_of)

REFUSAL = "v3_windowed_source_bound_response_invalid"


def refused(plan, answer, source, cause, *, parser=w.parse):
    """The windowed parser wraps every rule in one public reason; the rule itself is the cause."""
    with pytest.raises(StageAiValidationError, match=REFUSAL) as caught:
        parser(plan, row_of(answer), source)
    assert cause.lower() in str(caught.value.__cause__).lower(), repr(caught.value.__cause__)


# --- merged_changes: identity, ordering, copies, budgets ---------------------------------------------

def test_merged_changes_prefixes_every_id_with_its_group_and_reads_only_miner_and_unmatched_groups():
    results = {
        "v3:unmatched:b": miner_result(event("PC1"), hints=[hint("H1")]),
        "v3:miner:a": miner_result(event("PC1"), event("PC2")),
        "v3:mapper:catalogue": {"regions": [], "projectchanges": [event("MAPPER")]},
        "v3:dedupe:x": {"decisions": [], "projectchanges": [event("DEDUPE")]},
        "v3:verify:y": {"results": [], "projectchanges": [event("VERIFY")]},
        "v3:consolidate:z": {"decisions": []},
    }
    changes, hints = w.merged_changes(results)
    assert [row["projectchange_id"] for row in changes] == ["v3:miner:a:PC1", "v3:miner:a:PC2", "v3:unmatched:b:PC1"]
    assert [row["hint_id"] for row in hints] == ["v3:unmatched:b:H1"]


def test_merged_changes_order_does_not_depend_on_the_order_results_arrived():
    forward = {"v3:miner:a": miner_result(event("PC1")), "v3:miner:b": miner_result(event("PC1")),
               "v3:unmatched:c": miner_result(event("PC1"))}
    backward = dict(reversed(list(forward.items())))
    assert w.merged_changes(forward) == w.merged_changes(backward)
    assert [row["projectchange_id"] for row in w.merged_changes(backward)[0]] == [
        "v3:miner:a:PC1", "v3:miner:b:PC1", "v3:unmatched:c:PC1"]


def test_merged_changes_returns_copies_so_a_saved_result_cannot_be_rewritten_through_them():
    results = {"v3:miner:a": miner_result(event("PC1", parameters=[("1", "2")]), hints=[hint("H1")])}
    saved = copy.deepcopy(results)
    changes, hints = w.merged_changes(results)
    changes[0]["changed_parameters"][0]["new_value"] = "9999"
    changes[0]["projectchange_id"] = "other"
    hints[0]["hint_id"] = "other"
    assert results == saved


def test_merged_changes_budgets_events_512_parameters_1024_hints_1024():
    def results(events, hints=0):
        return {"v3:miner:a": miner_result(*events, hints=[hint(f"H{n}") for n in range(hints)])}
    w.merged_changes(results([event(f"E{n}") for n in range(512)]))
    with pytest.raises(StageAiValidationError, match="v3_windowed_result_budget"):
        w.merged_changes(results([event(f"E{n}") for n in range(513)]))
    w.merged_changes(results([event(f"E{n}", parameters=[("1", "2")] * 2) for n in range(512)]))        # 1024 parameters
    with pytest.raises(StageAiValidationError, match="v3_windowed_result_budget"):
        w.merged_changes(results([event(f"E{n}", parameters=[("1", "2")] * 2) for n in range(511)]
                                 + [event("last", parameters=[("1", "2")] * 3)]))                       # 1025
    w.merged_changes(results([], hints=1024))
    with pytest.raises(StageAiValidationError, match="v3_windowed_result_budget"):
        w.merged_changes(results([], hints=1025))


def test_merged_changes_of_nothing_is_nothing():
    assert w.merged_changes({}) == ([], [])
    assert w.merged_changes({"v3:miner:a": miner_result()}) == ([], [])


# --- dedupe batches --------------------------------------------------------------------------------

@pytest.mark.parametrize("events,sizes", [(0, []), (1, [1]), (8, [8]), (9, [8, 1]), (16, [8, 8]), (17, [8, 8, 1])])
def test_dedupe_batches_hold_at_most_eight_events_in_order(events, sizes):
    rows = [event(f"E{n}") for n in range(events)]
    batches = w._dedupe_batches(rows)
    assert [len(batch) for batch in batches] == sizes
    assert [row["projectchange_id"] for batch in batches for row in batch] == [row["projectchange_id"] for row in rows]


def test_dedupe_batches_also_split_on_120000_compact_characters_and_refuse_a_single_oversized_event():
    big = lambda n: event(f"E{n}", summary="я" * 50_000)
    assert [len(batch) for batch in w._dedupe_batches([big(n) for n in range(3)])] == [2, 1]
    assert len(canonical_json(original_dedupe.compact_change(big(0)))) < 60_000
    with pytest.raises(StageAiValidationError, match="v3_windowed_dedupe_item_budget"):
        w._dedupe_batches([event("E", summary="я" * 120_001)])


# --- synthesize: dedupe first, then one verification unit per parameter ------------------------------

TWO_PACKS = snapshot_of([numbered(65, "узел {n} диаметр {n} мм")], [["узел новый диаметр 250 мм"]])


def test_dedupe_plans_come_first_and_verification_waits_for_every_dedupe_answer():
    run = drive(w, TWO_PACKS, phases=PHASES[:2])
    plans = w.plans_for("synthesize", TWO_PACKS, run.results, MODEL)
    assert [plan.payload["_experimental_procedure"] for plan in plans] == ["dedupe"]
    plan = plans[0]
    events = [row["projectchange_id"] for row in w.merged_changes(run.results)[0]]
    assert len(events) == 2
    assert plan.payload["_validation"]["change_ids"] == events
    assert [row["projectchange_id"] for row in plan.payload["projectchanges"]] == events
    assert plan.payload["scope_coverage"] == {"dedupe_scope": "bounded_batch", "global_semantic_dedupe_complete": False}
    assert plan.group_id == "v3:dedupe:" + digest(events)[:24]
    assert plan.max_output_tokens == 4000
    run.results[plan.group_id] = w.parse(plan, row_of(answer_of(plan)), TWO_PACKS)
    later = w.plans_for("synthesize", TWO_PACKS, run.results, MODEL)
    assert [p.payload["_experimental_procedure"] for p in later] == ["verify", "verify"]


def test_a_run_whose_miner_found_nothing_has_no_dedupe_and_no_verification_call():
    def nothing(procedure, _plan, answer):
        if procedure == "miner":
            answer["projectchanges"] = []
    source = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])
    run = drive(w, source, edit=nothing)
    assert [name for name, _ in run.calls] == ["mapper", "miner"]
    assert w.canonical_cards(source, run.results) == []


def verification_plans(source, edit):
    run = drive(w, source, edit=edit, phases=PHASES[:2])
    for plan in w.plans_for("synthesize", source, run.results, MODEL):
        run.results[plan.group_id] = w.parse(plan, row_of(answer_of(plan, edit)), source)
    return run, w.plans_for("synthesize", source, run.results, MODEL)


VERIFY_SOURCE = snapshot_of(
    [["труба Ду 50", "длинный комментарий к узлу про разное, ширина прохода 100 мм здесь", "прочее"]],
    [["труба Ду 50 новая", "ширина прохода 120 мм и длинное продолжение комментария про узел"]])


def one_event_with_four_sources(old_value, new_value):
    def edit(procedure, _plan, answer):
        if procedure == "miner":
            change = answer["projectchanges"][0]
            change["evidence_items"] = [evidence_for(VERIFY_SOURCE, "stf_1", "OLD", 1), evidence_for(VERIFY_SOURCE, "stf_2", "OLD", 1),
                                        evidence_for(VERIFY_SOURCE, "stf_4", "NEW", 1), evidence_for(VERIFY_SOURCE, "stf_5", "NEW", 1)]
            change["changed_parameters"] = [{"name": "Ширина", "old_value": old_value, "new_value": new_value,
                                             "unit": "мм", "location": "Тест"}]
    return edit


def test_verification_sends_per_side_the_source_that_carries_the_value_even_when_it_is_longer():
    _run, plans = verification_plans(VERIFY_SOURCE, one_event_with_four_sources("100", "120"))
    assert len(plans) == 1
    item = plans[0].payload["items"][0]
    assert [row["block_id"] for row in item["sources"]] == ["stf_2", "stf_5"]
    assert item["source_selection"] == {"scope": "bounded_parameter_value_sources", "available_source_count": 4,
        "provided_source_count": 2, "omitted_source_ids": ["stf_1", "stf_4"], "full_event_context_provided": False}
    assert plans[0].payload["_validation"]["work_item_ids"] == [item["work_item_id"]]


def test_verification_falls_back_to_the_shortest_source_per_side_when_no_source_carries_the_value():
    _run, plans = verification_plans(VERIFY_SOURCE, one_event_with_four_sources("777", "888"))
    item = plans[0].payload["items"][0]
    assert [row["block_id"] for row in item["sources"]] == ["stf_1", "stf_4"]
    assert item["source_selection"]["omitted_source_ids"] == ["stf_2", "stf_5"]


def test_verification_with_one_source_per_side_says_the_whole_event_context_was_provided():
    source = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])
    _run, plans = verification_plans(source, None)
    selection = plans[0].payload["items"][0]["source_selection"]
    assert selection["full_event_context_provided"] is True and selection["omitted_source_ids"] == []


def test_a_verifier_may_not_cite_a_source_that_was_left_out_of_its_request():
    _run, plans = verification_plans(VERIFY_SOURCE, one_event_with_four_sources("100", "120"))
    plan = plans[0]
    answer = answer_of(plan)
    answer["results"][0]["evidence_refs"] = [{"side": "OLD", "physical_page": 1, "block_id": "stf_1"}]      # omitted
    refused(plan, answer, VERIFY_SOURCE, "verification source binding")
    answer = answer_of(plan)
    assert w.parse(plan, row_of(answer), VERIFY_SOURCE) == answer                                          # control


def test_every_retained_parameter_is_its_own_verification_request():
    def three_parameters(procedure, _plan, answer):
        if procedure == "miner":
            answer["projectchanges"][0]["changed_parameters"] = [
                {"name": f"П{n}", "old_value": "100", "new_value": "120", "unit": "мм", "location": "Тест"} for n in range(3)]
    source = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])
    _run, plans = verification_plans(source, three_parameters)
    assert len(plans) == 3 and all(len(plan.payload["items"]) == 1 for plan in plans)
    assert len({plan.group_id for plan in plans}) == 3


# --- parse: refusals of bad input ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def scene():
    run = drive(w, TWO_PACKS)
    by_kind = {}
    for group, plan in run.plans.items():
        by_kind.setdefault(plan.payload["_experimental_procedure"], []).append(plan)
    return run, by_kind


def test_a_response_that_did_not_end_its_turn_is_refused_under_its_own_reason(scene):
    _run, plans = scene
    plan = plans["mapper"][0]
    with pytest.raises(StageAiValidationError, match="^v3_response_not_complete$"):
        w.parse(plan, row_of(answer_of(plan), stop_reason="max_tokens"), TWO_PACKS)


def test_an_answer_for_another_pair_is_refused(scene):
    _run, plans = scene
    plan = plans["mapper"][0]
    answer = answer_of(plan)
    answer["pair"] = "another-pair"
    refused(plan, answer, TWO_PACKS, "wrong pair")


def test_an_answer_that_breaks_the_closed_schema_is_refused_with_the_schema_reason(scene):
    _run, plans = scene
    plan = plans["mapper"][0]
    answer = answer_of(plan)
    answer["unexpected"] = 1
    with pytest.raises(StageAiValidationError):
        w.parse(plan, row_of(answer), TWO_PACKS)


def mapper_plan():
    return w.plans_for("review", MAPPER_SOURCE, {}, MODEL)[0]


def test_the_mapper_may_not_put_one_page_into_two_regions():
    plan = mapper_plan()
    answer = answer_of(plan)
    answer["regions"] = [region("R001", [1, 2], [1]), region("R002", [2], [2])]
    refused(plan, answer, MAPPER_SOURCE, "overlapping windowed regions")
    answer["regions"] = [region("R001", [1], [1]), region("R002", [2], [2])]                     # control
    assert w.parse(plan, row_of(answer), MAPPER_SOURCE) == answer


def test_the_mapper_must_account_for_every_page():
    plan = mapper_plan()
    answer = answer_of(plan)
    answer["regions"] = [region("R001", [1], [1, 2])]
    refused(plan, answer, MAPPER_SOURCE, "coverage failure")
    answer["unmatched_old"] = [2]
    assert w.parse(plan, row_of(answer), MAPPER_SOURCE) == answer


def test_the_mapper_may_cite_only_blocks_that_the_catalogue_showed():
    plan = mapper_plan()
    shown = {"side": "OLD", "physical_page": 1, "block_id": "stf_2", "block_type": "TEXT", "relevance": "тест"}
    answer = answer_of(plan)
    answer["regions"][0]["important_text_blocks"] = [shown]                                       # second block: in the catalogue
    assert w.parse(plan, row_of(answer), MAPPER_SOURCE) == answer
    answer["regions"][0]["important_text_blocks"] = [dict(shown, block_id="stf_3")]               # third block: retained, not shown
    refused(plan, answer, MAPPER_SOURCE, "mapper cites unavailable catalogue block")
    answer["regions"][0]["important_text_blocks"] = []
    answer["regions"][0]["important_table_blocks"] = [dict(shown, block_type="TABLE")]            # not native TEXT
    refused(plan, answer, MAPPER_SOURCE, "mapper cites unavailable catalogue block")


def miner_plans(scene):
    run, plans = scene
    return plans["miner"]


def test_a_miner_may_cite_only_blocks_that_are_in_its_own_source_pack(scene):
    first, second = miner_plans(scene)
    assert "stf_65" not in first.payload["_validation"]["block_ids"] and "stf_65" in second.payload["_validation"]["block_ids"]
    answer = answer_of(first)
    answer["projectchanges"][0]["evidence_items"][0] = evidence_for(TWO_PACKS, "stf_65", "OLD", 1)     # real, but in the other pack
    refused(first, answer, TWO_PACKS, "untraceable")
    answer = answer_of(second)
    assert answer["projectchanges"][0]["evidence_items"][0]["block_id"] == "stf_65"
    assert w.parse(second, row_of(answer), TWO_PACKS) == answer                                       # same block, own pack: fine


def test_a_miner_event_must_quote_its_block_exactly_and_may_not_carry_a_crop(scene):
    first, _second = miner_plans(scene)
    for field, value in (("relevant_fragment", "выдуманная цитата"), ("bbox", [0, 0, 1, 1]), ("block_type", "TABLE"),
                         ("crop_ref", "crop-1"), ("source_pdf", "ver_other"), ("block_id", "invented")):
        answer = answer_of(first)
        answer["projectchanges"][0]["evidence_items"][0][field] = value
        refused(first, answer, TWO_PACKS, "untraceable")


def test_a_miner_event_may_carry_at_most_eight_evidence_items_and_a_bounded_identity(scene):
    first, _second = miner_plans(scene)
    answer = answer_of(first)
    answer["projectchanges"][0]["evidence_items"] = answer["projectchanges"][0]["evidence_items"] * 5      # 10 items, both sides
    refused(first, answer, TWO_PACKS, "event evidence budget")
    answer = answer_of(first)
    answer["projectchanges"][0]["projectchange_id"] = "X" * 129
    refused(first, answer, TWO_PACKS, "event identity budget")
    answer = answer_of(first)
    answer["projectchanges"][0]["projectchange_id"] = ""
    refused(first, answer, TWO_PACKS, "event identity budget")


def test_a_miner_hint_may_name_only_pages_of_its_own_pack(scene):
    first, _second = miner_plans(scene)
    answer = answer_of(first)
    answer["unresolved_hints"] = [hint_for(TWO_PACKS, "stf_1", "OLD", 1, old_pages=[1], new_pages=[1])]
    assert w.parse(first, row_of(answer), TWO_PACKS) == answer
    answer["unresolved_hints"][0]["old_pages"] = [2]
    refused(first, answer, TWO_PACKS, "hint outside source pack")


def test_a_miner_event_needs_both_sides_and_pages_inside_the_region(scene):
    first, _second = miner_plans(scene)
    answer = answer_of(first)
    answer["projectchanges"][0]["new_pages"] = []
    refused(first, answer, TWO_PACKS, "MINER_ONE_SIDED_PROJECTCHANGE")
    answer = answer_of(first)
    answer["projectchanges"][0]["old_pages"] = [7]
    refused(first, answer, TWO_PACKS, "MINER_PAGE_OUTSIDE_REGION")


def test_the_miner_result_budget_is_64_events_per_unit(scene):
    first, _second = miner_plans(scene)
    answer = answer_of(first)
    changes = []
    for number in range(65):
        row = copy.deepcopy(answer["projectchanges"][0])
        row["projectchange_id"] = f"PC{number}"
        changes.append(row)
    answer["projectchanges"] = changes
    refused(first, answer, TWO_PACKS, "unit result budget")


def test_the_dedupe_answer_must_be_an_exact_partition_with_valid_actions(scene):
    _run, plans = scene
    plan = plans["dedupe"][0]
    ids = plan.payload["_validation"]["change_ids"]
    decision = lambda kind, members: {"decision": kind, "projectchange_ids": members, "reason": "тест"}
    good = {"pair": "pair-test", "decisions": [decision("KEEP_SEPARATE", [ids[0]]), decision("KEEP_SEPARATE", [ids[1]])], "notes": []}
    assert w.parse(plan, row_of(good), TWO_PACKS) == good
    merged = dict(good, decisions=[decision("MERGE_DUPLICATES", ids)])
    assert w.parse(plan, row_of(merged), TWO_PACKS) == merged
    refused(plan, dict(good, decisions=[decision("KEEP_SEPARATE", [ids[0]])]), TWO_PACKS, "dedupe partition")             # one left out
    refused(plan, dict(good, decisions=[decision("KEEP_SEPARATE", [ids[0]])] * 2), TWO_PACKS, "dedupe partition")        # one twice
    refused(plan, dict(good, decisions=[decision("KEEP_SEPARATE", ids + ["v3:miner:zz:PC1"])]), TWO_PACKS, "dedupe partition")
    refused(plan, dict(good, decisions=[decision("KEEP_SEPARATE", ids)]), TWO_PACKS, "dedupe action invalid")             # keeps two
    refused(plan, dict(good, decisions=[decision("MERGE_DUPLICATES", [ids[0]]), decision("KEEP_SEPARATE", [ids[1]])]),
            TWO_PACKS, "dedupe action invalid")                                                                          # merges one


def test_the_verifier_cannot_change_a_confirmed_value_or_confirm_a_value_the_cited_text_lacks(scene):
    _run, plans = scene
    plan = plans["verify"][0]
    answer = answer_of(plan)
    assert answer["results"][0]["verdict"] == "CONFIRMED"
    assert w.parse(plan, row_of(answer), TWO_PACKS) == answer
    changed = copy.deepcopy(answer)
    changed["results"][0]["new_value"] = "9999"
    refused(plan, changed, TWO_PACKS, "confirmation changed values")
    corrected = copy.deepcopy(answer)
    corrected["results"][0].update(verdict="CORRECTED", new_value="9999")
    refused(plan, corrected, TWO_PACKS, "value absent from cited source")
    partition = copy.deepcopy(answer)
    partition["results"][0]["work_item_id"] = "VERIFY-unknown"
    refused(plan, partition, TWO_PACKS, "verification partition")
    unsourced = copy.deepcopy(answer)
    unsourced["results"][0]["evidence_refs"] = []
    refused(plan, unsourced, TWO_PACKS, "verification source binding")


def test_the_legacy_dispatcher_hands_windowed_plans_to_the_windowed_rules(scene):
    first, second = miner_plans(scene)
    assert first.prompt_version == w.BUNDLE != legacy.BUNDLE
    good = answer_of(first)
    assert legacy.parse(first, row_of(good), TWO_PACKS) == good == w.parse(first, row_of(good), TWO_PACKS)
    bad = answer_of(first)
    bad["projectchanges"][0]["evidence_items"][0] = evidence_for(TWO_PACKS, "stf_65", "OLD", 1)
    with pytest.raises(StageAiValidationError, match=REFUSAL):                        # a legacy parse would not know "pack"
        legacy.parse(first, row_of(bad), TWO_PACKS)


# --- unmatched answers ----------------------------------------------------------------------------------

UNMATCHED_SOURCE = snapshot_of([["ширина прохода 100 мм"], ["ширина прохода 100 мм прочее"]],
                               [["ширина прохода 120 мм"], ["ширина прохода 120 мм иное"]])
ALONE_SOURCE = snapshot_of([["ширина прохода 100 мм"], ["уникальное содержание страницы"]],
                           [["ширина прохода 120 мм"], ["совсем другой набор слов"]])


def unmatched_plans(source):
    run = drive(w, source, edit=mapping_edit([region("R001", [1], [1])], unmatched_old=[2], unmatched_new=[2]))
    return [plan for plan in run.plans.values() if plan.payload["_experimental_procedure"] == "unmatched"]


def test_an_unmatched_answer_must_address_its_primary_page_with_its_own_source():
    plans = unmatched_plans(UNMATCHED_SOURCE)
    plan = next(p for p in plans if p.payload["_validation"]["primary_keys"] == [["OLD", 2]])
    good = answer_of(plan)
    assert w.parse(plan, row_of(good), UNMATCHED_SOURCE) == good
    elsewhere = copy.deepcopy(good)
    page = next(page for page in plan.payload["pages"] if page["side"] == "NEW")
    number = page["physical_page"]
    elsewhere["unresolved_hints"] = [hint_for(UNMATCHED_SOURCE, page["blocks"][0]["block_id"], "NEW", number,
                                              old_pages=[], new_pages=[number])]
    refused(plan, elsewhere, UNMATCHED_SOURCE, "unmatched result without primary source")
    silent = dict(good, unresolved_hints=[], projectchanges=[])
    refused(plan, silent, UNMATCHED_SOURCE, "did not address primary pages")


def test_a_page_without_a_counterpart_can_yield_only_an_observation_never_a_bilateral_event():
    mapping = {"pair": "pair-test", "regions": [region("R001", [1], [1])], "unmatched_old": [2], "unmatched_new": [2],
               "coverage_notes": []}
    plans = [plan for plan in w.plans_for("classify", ALONE_SOURCE, {w.MAPPER_GROUP: mapping}, MODEL)
             if plan.group_id.startswith("v3:unmatched:")]
    plan = next(p for p in plans if p.payload["_validation"]["primary_keys"] == [["OLD", 2]])
    assert plan.payload["region"]["new_pages"] == []
    block = plan.payload["pages"][0]["blocks"][0]["block_id"]
    answer = {"pair": "pair-test", "region_id": "ONE-OLD-2", "projectchanges": [], "coverage_notes": [],
              "unresolved_hints": [hint_for(ALONE_SOURCE, block, "OLD", 2, old_pages=[2], new_pages=[])]}
    assert w.parse(plan, row_of(answer), ALONE_SOURCE) == answer
    invented = copy.deepcopy(answer)
    invented["projectchanges"] = [event("PC1", old_pages=(2,), new_pages=(1,))]
    invented["projectchanges"][0]["evidence_items"] = [evidence_for(ALONE_SOURCE, block, "OLD", 2)]
    refused(plan, invented, ALONE_SOURCE, "MINER_")


def test_a_dedupe_merge_is_lossless_and_the_merged_event_gets_its_own_verification_requests():
    run = drive(w, TWO_PACKS, phases=PHASES[:2])
    (dedupe,) = w.plans_for("synthesize", TWO_PACKS, run.results, MODEL)
    ids = dedupe.payload["_validation"]["change_ids"]
    originals = {row["projectchange_id"]: row for row in w.merged_changes(run.results)[0]}
    answer = {"pair": "pair-test", "notes": [], "decisions": [
        {"decision": "MERGE_DUPLICATES", "projectchange_ids": ids, "reason": "один и тот же узел"}]}
    run.results[dedupe.group_id] = w.parse(dedupe, row_of(answer), TWO_PACKS)
    merged, _hints, ledger, _cov, _records = w.reviewed(TWO_PACKS, run.results)
    assert len(merged) == 1
    event = merged[0]
    assert sorted(event["dedupe_lineage"]) == sorted(ids) and event["dedupe_reason"] == "один и тот же узел"
    assert {row["block_id"] for row in event["evidence_items"]} == {"stf_1", "stf_65", "stf_66"}      # every original source kept
    assert len(event["changed_parameters"]) == 2                                                    # both originals' parameters kept
    assert sorted(event["old_pages"]) == [1] and {member["projectchange_id"] for member in event["dedupe_members"]} == set(ids)
    assert all(originals[identity]["change_summary"] for identity in ids)                           # the saved originals are untouched
    assert len(ledger["verification_work_items"]) == 2
    verify = w.plans_for("synthesize", TWO_PACKS, run.results, MODEL)
    assert [p.payload["_experimental_procedure"] for p in verify] == ["verify", "verify"]
    assert all(item["projectchange_id"] == event["projectchange_id"] for p in verify for item in p.payload["items"])


# --- reviewed: coverage is only as complete as the answered windows ----------------------------------------

def test_a_region_counts_as_analysed_only_when_every_one_of_its_windows_has_an_answer(scene):
    run, plans = scene
    first, second = miner_plans(scene)
    answered = lambda *drop: {key: value for key, value in run.results.items() if key not in drop}
    nothing = w.reviewed(TWO_PACKS, {w.MAPPER_GROUP: run.results[w.MAPPER_GROUP]})[3]["summary"]
    assert (nothing["pages_analysed"], nothing["pages_pending"], nothing["complete"]) == (0, 2, False)
    half = w.reviewed(TWO_PACKS, answered(second.group_id))[3]["summary"]
    assert (half["pages_analysed"], half["pages_pending"], half["complete"]) == (0, 2, False)
    whole = w.reviewed(TWO_PACKS, run.results)[3]["summary"]
    assert (whole["pages_analysed"], whole["pages_pending"], whole["complete"]) == (2, 0, True)


def test_the_coverage_summary_never_claims_semantic_completeness(scene):
    run, _plans = scene
    summary = w.reviewed(TWO_PACKS, run.results)[3]["summary"]
    assert summary["native_text_plan"] == VERSION
    assert summary["catalogue_complete"] is True and summary["semantic_comparison_complete"] is False
    assert summary["unmatched_candidate_search_complete"] is True               # nothing was unmatched


def test_unmatched_pages_mark_the_candidate_search_as_incomplete():
    run = drive(w, UNMATCHED_SOURCE, edit=mapping_edit([region("R001", [1], [1])], unmatched_old=[2], unmatched_new=[2]))
    summary = w.reviewed(UNMATCHED_SOURCE, run.results)[3]["summary"]
    assert summary["unmatched_candidate_search_complete"] is False and summary["complete"] is True
    # an unmatched page whose request has no answer yet is still pending
    pending = {key: value for key, value in run.results.items() if not key.startswith("v3:unmatched:")}
    assert w.reviewed(UNMATCHED_SOURCE, pending)[3]["summary"]["complete"] is False


# --- cards ---------------------------------------------------------------------------------------------------

def test_cards_carry_the_plan_its_limits_its_coverage_statement_and_never_claim_a_norm_check(scene):
    run, _plans = scene
    cards = w.canonical_cards(TWO_PACKS, run.results)
    assert len(cards) == 1                                                      # both events share the new block
    card = cards[0]
    meta = card["experimental"]
    assert card["class_name"] == "REVIEW" and meta["norms_status"] == "not_checked" and meta["native_text_only"] is True
    assert meta["plan_version"] == VERSION and meta["limits"] == LIMITS
    assert meta["scope_coverage"]["semantic_comparison_complete"] is False
    assert meta["scope_coverage"]["miner"] == "bounded_cartesian_region_source_packs"
    assert set(card["evidence_ids"]) == {"stf_1", "stf_65", "stf_66"}
    assert len(meta["related_events"]) == 1
    assert all(parameter["verification"]["verdict"] == "CONFIRMED" for parameter in meta["parameters"])


def test_a_long_card_shows_an_excerpt_and_keeps_the_full_text_in_its_sources():
    full = "ширина прохода 100 мм " + "я" * 25_000
    source = snapshot_of([[full]], [["ширина прохода 120 мм"]])

    def quote_a_part(procedure, _plan, answer):          # a model reply may not exceed 20,000 characters per field
        if procedure == "miner":
            change = answer["projectchanges"][0]
            change["old_state"] = full[:200]
            for item in change["evidence_items"]:
                item["relevant_fragment"] = item["relevant_fragment"][:2000]

    run = drive(w, source, edit=quote_a_part)
    card = w.canonical_cards(source, run.results)[0]
    before = card["experimental"]["display_text"]["before"]
    assert card["experimental"]["display_text"]["limit_characters"] == 20_000
    assert before["excerpt"] is True and before["full_characters"] == len(full)
    assert before["display_characters"] <= 20_000 and before["displayed_characters"] < len(full)
    assert before["full_sha256"] == hashlib.sha256(full.encode("utf-8")).hexdigest()
    assert any(row["quote"] == full for row in card["experimental"]["sources"])           # never rewritten
    after = card["experimental"]["display_text"]["after"]
    assert after["excerpt"] is False and after["full_characters"] == len("ширина прохода 120 мм")


def test_cards_are_refused_while_a_verification_answer_is_missing(scene):
    run, plans = scene
    without = {key: value for key, value in run.results.items() if key != plans["verify"][0].group_id}
    with pytest.raises(StageAiValidationError, match="v3_verification_incomplete"):
        w.canonical_cards(TWO_PACKS, without)


def test_an_unresolved_observation_becomes_its_own_card_with_its_source():
    def add_hint(procedure, _plan, answer):
        if procedure == "miner":
            answer["projectchanges"] = []
            answer["unresolved_hints"] = [hint_for(snapshot, "stf_1", "OLD", 1, old_pages=[1], new_pages=[1])]
    snapshot = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])
    run = drive(w, snapshot, edit=add_hint)
    assert [name for name, _ in run.calls] == ["mapper", "miner"]
    cards = w.canonical_cards(snapshot, run.results)
    assert len(cards) == 1 and cards[0]["title"] == "Неподтверждённое наблюдение V3"
    assert cards[0]["evidence_ids"] == ["stf_1"] and cards[0]["experimental"]["observation"]["hint_id"].endswith(":H1")


def test_a_full_run_never_rewrites_the_saved_raw_comparison():
    source = copy.deepcopy(TWO_PACKS)
    source["differences"] = [{"stage_text_difference_id": "std_1", "status": "changed", "content_key": "k"}]
    before = copy.deepcopy(source)
    run = drive(w, source)
    w.canonical_cards(source, run.results)
    assert source == before
