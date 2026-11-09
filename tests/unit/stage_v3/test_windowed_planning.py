"""windowed-v1 planning: source admission, catalogue, source packs, region and unmatched plans, call counts.

Intended behaviour is taken from the plan's own text (`stage_v3/windowed.py`, `policy.py`) and from
docs/program/SPRINT3-STAGE-1030.md: every admitted block is retained, the Mapper sees a bounded
catalogue, the Miner sees every block through bounded Cartesian source packs, the unmatched review
is bounded and never invents a counterpart. Nothing here calls a provider.
"""
from __future__ import annotations

import copy
import json

import pytest

from auditmanager.comparison.stage_ai.validation import StageAiValidationError, canonical_json
from auditmanager.comparison.stage_v3 import procedures as legacy
from auditmanager.comparison.stage_v3 import windowed as w
from auditmanager.comparison.stage_v3.policy import LIMITS, VERSION
from tests.unit.stage_v3.windowed_fixture import MODEL, drive, mapping_edit, numbered, region, snapshot_of


def block(page_number, number, text):
    return {"block_id": f"b{number}", "modality": "TEXT", "block_type": "TEXT", "structured_md": text, "tables": [],
            "source_pdf": "ver", "bbox": [1, 2, 3, 4]}


def size_of(text):
    """The packer's own measure of one block: its canonical encoding plus a fixed 250-character allowance."""
    return len(canonical_json(block(1, 1, text))) + 250


def text_of_size(target):
    base = size_of("")
    assert target >= base
    return "x" * (target - base)


def page_of(side, number, texts):
    return {"side": side, "physical_page": number, "source_pdf": "ver", "profile_id": f"p{side}{number}",
            "original_page_number": number, "blocks": [block(number, index, text) for index, text in enumerate(texts, 1)]}


def flat(packs):
    return [item["block_id"] for pack in packs for page in pack for item in page["blocks"]]


# --- the plan's limits are the documented ones ------------------------------------------------------

def test_the_documented_limits_are_the_ones_in_force():
    assert VERSION == "windowed-v1"
    assert (LIMITS["pages"], LIMITS["characters"], LIMITS["fragments"]) == (64, 240_000, 1600)
    assert (LIMITS["pack_characters"], LIMITS["pack_blocks"]) == (60_000, 64)
    assert (LIMITS["catalogue_blocks_per_page"], LIMITS["catalogue_snippet_characters"]) == (2, 256)
    assert (LIMITS["classification_units"], LIMITS["events"], LIMITS["parameters"]) == (128, 512, 1024)
    assert LIMITS["request_characters"] == 240_000


# --- source admission: sizing and boundaries --------------------------------------------------------

def test_source_numbers_pages_per_side_in_version_and_page_order_and_orders_blocks_by_position():
    source = snapshot_of([["a"], ["b"]], [["c"], ["d"]])
    source["all_profiles"].reverse()          # input order must not matter
    source["fragments"].reverse()
    pages, records = w.source(source)
    assert [(page["side"], page["physical_page"], page["original_page_number"]) for page in pages] == [
        ("OLD", 1, 1), ("OLD", 2, 2), ("NEW", 1, 1), ("NEW", 2, 2)]
    assert set(records) == {("OLD", 1), ("OLD", 2), ("NEW", 1), ("NEW", 2)}
    assert records[("NEW", 2)]["blocks"][0]["structured_md"] == "d"
    # blocks of one page: by top, then x0, then id
    source = snapshot_of([["x", "y", "z"]], [["q"]])
    for fragment, (top, x0) in zip(source["fragments"][:3], ((30, 5), (10, 50), (10, 20))):
        fragment["box_anchor"].update(top=top, x0=x0)
    _pages, records = w.source(source)
    assert [row["structured_md"] for row in records[("OLD", 1)]["blocks"]] == ["z", "y", "x"]


def test_source_orders_two_versions_of_one_side_by_version_uid():
    source = snapshot_of([["old one"], ["old two"]], [["new"]])
    source["all_profiles"][0]["version_uid"] = "ver_b"
    source["all_profiles"][1]["version_uid"] = "ver_a"
    pages, _records = w.source(source)
    assert [(page["side"], page["physical_page"], page["source_pdf"]) for page in pages if page["side"] == "OLD"] == [
        ("OLD", 1, "ver_a"), ("OLD", 2, "ver_b")]


@pytest.mark.parametrize("old,new,accepted", [
    (1, 1, True),       # the smallest admissible pair
    (32, 32, True),     # exactly 64 pages
    (33, 32, False),    # 65 pages
    (63, 1, True),
    (1, 64, False),
    (0, 1, False),      # one side only
    (1, 0, False),
    (0, 0, False),      # empty input
])
def test_source_page_count_boundaries(old, new, accepted):
    source = snapshot_of([["t"]] * old, [["t"]] * new)
    if accepted:
        pages, _ = w.source(source)
        assert len(pages) == old + new
    else:
        with pytest.raises(StageAiValidationError, match="v3_windowed_source_budget"):
            w.source(source)


def test_source_is_wider_than_the_legacy_native_plan():
    source = snapshot_of([["t"]] * 9, [["t"]] * 9)       # 18 pages: legacy admits 16
    assert len(w.source(source)[0]) == 18
    with pytest.raises(StageAiValidationError, match="v3_native_source_budget"):
        legacy.source(source)


def test_source_fragment_boundary_1600_accepted_1601_refused():
    ok = snapshot_of([["t"] * 800], [["t"] * 800])
    assert len(ok["fragments"]) == 1600
    assert sum(len(page["blocks"]) for page in w.source(ok)[0]) == 1600
    with pytest.raises(StageAiValidationError, match="v3_windowed_source_budget"):
        w.source(snapshot_of([["t"] * 801], [["t"] * 800]))


def test_source_character_boundary_240000_accepted_240001_refused_without_truncation():
    ok = snapshot_of([["a" * 120_000]], [["b" * 120_000]])
    pages, _ = w.source(ok)
    assert sum(len(item["structured_md"]) for page in pages for item in page["blocks"]) == 240_000
    with pytest.raises(StageAiValidationError, match="v3_windowed_source_budget"):
        w.source(snapshot_of([["a" * 120_001]], [["b" * 120_000]]))


def test_source_refuses_a_page_without_native_text():
    source = snapshot_of([["a"], ["b"]], [["c"]])
    source["fragments"] = [row for row in source["fragments"] if row["page_profile_id"] != "cpr_left_2"]
    with pytest.raises(StageAiValidationError, match="v3_native_page_without_text"):
        w.source(source)


# --- catalogue (what the Mapper sees) ---------------------------------------------------------------

def test_catalogue_keeps_two_blocks_per_page_and_says_what_it_left_out():
    pages = [page_of("OLD", 1, ["one"]), page_of("OLD", 2, ["one", "two"]), page_of("NEW", 1, ["one", "two", "three", "four", "five"])]
    before = copy.deepcopy(pages)
    result = w.catalogue(pages)
    assert [(row["full_block_count"], len(row["blocks"]), row["omitted_block_count"]) for row in result] == [
        (1, 1, 0), (2, 2, 0), (5, 2, 3)]
    assert all(row["catalogue_only"] is True for row in result)
    assert [item["structured_md"] for item in result[2]["blocks"]] == ["one", "two"]      # the first ones, in order
    assert pages == before                                                              # the retained source is untouched


@pytest.mark.parametrize("length,truncated", [(255, False), (256, False), (257, True)])
def test_catalogue_excerpt_boundary_is_256_characters(length, truncated):
    row = w.catalogue([page_of("OLD", 1, ["я" * length])])[0]["blocks"][0]
    assert len(row["structured_md"]) == min(length, 256)
    assert row["excerpt_truncated"] is truncated


def test_the_mapper_plan_is_one_call_over_the_whole_catalogue_and_never_carries_full_text():
    texts = [f"позиция {number} " + "ф" * 300 for number in range(1, 6)]
    source = snapshot_of([texts, ["короткий"]], [["новый"]])
    plans = w.plans_for("review", source, {}, MODEL)
    assert len(plans) == 1
    plan = plans[0]
    assert plan.group_id == w.MAPPER_GROUP == "v3:mapper:catalogue"
    assert plan.phase == "review" and plan.max_output_tokens == 8000 and plan.prompt_version == w.BUNDLE
    payload = plan.payload
    assert payload["plan_version"] == VERSION and payload["source_limits"] == LIMITS
    assert payload["_experimental_procedure"] == "mapper"
    assert [(row["side"], row["physical_page"]) for row in payload["pages"]] == [("OLD", 1), ("OLD", 2), ("NEW", 1)]
    first = payload["pages"][0]
    assert (first["full_block_count"], first["omitted_block_count"], len(first["blocks"])) == (5, 3, 2)
    assert payload["catalogue_coverage"] == {"all_pages": 3, "all_source_text_provided": False,
        "representative_blocks_per_page": 2, "full_native_source_retained": True}
    assert "позиция 3" not in plan.payload_json and "ф" * 257 not in plan.payload_json
    assert "ОГРАНИЧЕННЫЙ NATIVE-TEXT ПРОХОД windowed-v1" in plan.instructions


def test_the_largest_admissible_catalogue_still_fits_one_request():
    texts = ["я" * 300, "я" * 300, "я" * 300]
    source = snapshot_of([texts] * 32, [texts] * 32)          # 64 pages, 2 x 256 characters each in the catalogue
    plan = w.plans_for("review", source, {}, MODEL)[0]
    assert len(plan.payload["pages"]) == 64
    assert len(plan.payload_json) <= LIMITS["request_characters"]


def test_a_request_over_the_encoded_budget_is_refused_before_any_plan_exists():
    ok = w._plan("mapper", phase="review", group_id="g", pair="p", model=MODEL, payload={"filler": "я" * 1000})
    assert ok.group_id == "g"
    with pytest.raises(StageAiValidationError, match="v3_windowed_encoded_request_budget"):
        w._plan("mapper", phase="review", group_id="g", pair="p", model=MODEL, payload={"filler": "я" * LIMITS["request_characters"]})


def test_each_procedure_has_its_documented_output_budget_and_schema():
    expected = {"mapper": 8000, "miner": 8000, "unmatched": 8000, "dedupe": 4000, "verify": 4000}
    for procedure, tokens in expected.items():
        plan = w._plan(procedure, phase="classify", group_id=procedure, pair="p", model=MODEL, payload={})
        assert plan.max_output_tokens == tokens
        assert plan.payload["_experimental_procedure"] == procedure
    with pytest.raises(KeyError):
        w._plan("consolidate", phase="synthesize", group_id="g", pair="p", model=MODEL, payload={})


def test_later_phases_without_a_mapper_answer_are_refused():
    source = snapshot_of([["a"]], [["b"]])
    for phase in ("classify", "synthesize"):
        with pytest.raises(StageAiValidationError, match="v3_mapper_missing"):
            w.plans_for(phase, source, {}, MODEL)


# --- source packs: windows, first/last, single, empty -----------------------------------------------

def test_packs_of_nothing_are_nothing():
    assert w._packs([]) == []
    assert w._packs([page_of("OLD", 1, [])]) == []


def test_a_single_block_is_a_single_pack():
    packs = w._packs([page_of("OLD", 1, ["only"])])
    assert [[(page["side"], page["physical_page"], [item["block_id"] for item in page["blocks"]]) for page in pack] for pack in packs] == [
        [("OLD", 1, ["b1"])]]


@pytest.mark.parametrize("blocks,sizes", [(1, [1]), (64, [64]), (65, [64, 1]), (128, [64, 64]), (129, [64, 64, 1])])
def test_pack_block_count_boundary_is_64_and_the_last_pack_takes_the_remainder(blocks, sizes):
    page = page_of("OLD", 1, ["t"] * blocks)
    packs = w._packs([page])
    assert [sum(len(row["blocks"]) for row in pack) for pack in packs] == sizes
    assert flat(packs) == [item["block_id"] for item in page["blocks"]]          # nothing lost, order kept


def test_pack_character_boundary_two_blocks_filling_exactly_60000_share_a_pack_and_one_more_splits():
    first = text_of_size(30_000)
    page = page_of("OLD", 1, [first, text_of_size(30_000)])
    assert [len(pack[0]["blocks"]) for pack in w._packs([page])] == [2]       # 30000 + 30000 = 60000: fits
    page = page_of("OLD", 1, [first, text_of_size(30_001)])
    assert [len(pack[0]["blocks"]) for pack in w._packs([page])] == [1, 1]    # 60001: does not


def test_pack_invariants_hold_for_mixed_block_sizes():
    texts = [text_of_size(size) for size in (9_000, 25_000, 31_000, 4_000, 59_000, 400, 22_000, 22_000, 22_000)]
    page = page_of("OLD", 1, texts)
    packs = w._packs([page])
    sizes = {item["block_id"]: len(canonical_json(item)) + 250 for item in page["blocks"]}
    assert flat(packs) == [item["block_id"] for item in page["blocks"]]
    totals = [sum(sizes[item["block_id"]] for row in pack for item in row["blocks"]) for pack in packs]
    assert all(total <= LIMITS["pack_characters"] for total in totals)
    for index in range(len(packs) - 1):                          # greedy: the next block really did not fit
        following = flat([packs[index + 1]])[0]
        assert totals[index] + sizes[following] > LIMITS["pack_characters"]


def test_a_block_over_the_pack_budget_is_refused_and_one_exactly_at_it_is_not():
    assert flat(w._packs([page_of("OLD", 1, [text_of_size(60_000)])])) == ["b1"]
    with pytest.raises(StageAiValidationError, match="v3_windowed_single_block_budget"):
        w._packs([page_of("OLD", 1, [text_of_size(60_001)])])


def test_a_page_split_across_packs_is_regrouped_per_pack_and_the_source_record_is_not_touched():
    page = page_of("OLD", 1, ["t"] * 100)
    before = copy.deepcopy(page)
    packs = w._packs([page])
    assert [[(row["side"], row["physical_page"], len(row["blocks"])) for row in pack] for pack in packs] == [
        [("OLD", 1, 64)], [("OLD", 1, 36)]]
    assert page == before and len(page["blocks"]) == 100


def test_packs_run_across_pages_in_order_and_split_inside_a_page():
    pages = [page_of("OLD", 1, ["t"] * 40), page_of("OLD", 2, ["t"] * 40)]
    packs = w._packs(pages)
    assert [[(row["physical_page"], len(row["blocks"])) for row in pack] for pack in packs] == [
        [(1, 40), (2, 24)], [(2, 16)]]


# --- region plans: the Cartesian call count ----------------------------------------------------------

def plans_for_mapping(source, mapping_regions, **unmatched):
    results = {w.MAPPER_GROUP: {"pair": source["stage_pair_id"], "regions": mapping_regions,
        "unmatched_old": unmatched.get("old", []), "unmatched_new": unmatched.get("new", []), "coverage_notes": []}}
    return w.plans_for("classify", source, results, MODEL), results


def test_a_region_that_fits_one_window_is_one_miner_call_with_a_full_region_flag():
    source = snapshot_of([numbered(3)], [numbered(4)])
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1])])
    assert len(plans) == 1
    plan = plans[0]
    assert plan.group_id.startswith("v3:miner:") and len(plan.group_id) == len("v3:miner:") + 24
    assert plan.phase == "classify" and plan.max_output_tokens == 8000
    coverage = plan.payload["scope_coverage"]
    assert coverage == {"region_id": "R1", "old_packs": 1, "new_packs": 1,
        "comparison": "bounded_cartesian_source_packs", "full_region_in_single_request": True}
    assert plan.payload["_validation"]["block_ids"] == ["stf_1", "stf_2", "stf_3", "stf_4", "stf_5", "stf_6", "stf_7"]
    assert plan.payload["_validation"]["parent_region_id"] == "R1"
    assert plan.payload["region"]["old_pages"] == [1] and plan.payload["region"]["new_pages"] == [1]


@pytest.mark.parametrize("old,new,calls", [(64, 64, 1), (65, 64, 2), (64, 65, 2), (65, 65, 4), (129, 65, 6), (1, 130, 3)])
def test_miner_call_count_is_old_packs_times_new_packs(old, new, calls):
    source = snapshot_of([numbered(old)], [numbered(new)])
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1])])
    assert len(plans) == calls
    assert len({plan.group_id for plan in plans}) == calls
    assert all(plan.payload["scope_coverage"]["full_region_in_single_request"] is (calls == 1) for plan in plans)


def test_every_block_of_a_region_reaches_a_miner_call_and_no_call_exceeds_a_pack_per_side():
    source = snapshot_of([numbered(130)], [numbered(70)])
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1])])
    old_ids = [f"stf_{n}" for n in range(1, 131)]
    new_ids = [f"stf_{n}" for n in range(131, 201)]
    seen = set()
    for plan in plans:
        ids = plan.payload["_validation"]["block_ids"]
        seen.update(ids)
        assert len([i for i in ids if i in set(old_ids)]) <= 64 and len([i for i in ids if i in set(new_ids)]) <= 64
        assert ids == [i for page in plan.payload["pages"] for item in page["blocks"] for i in [item["block_id"]]]
    assert seen == set(old_ids + new_ids)
    # the Cartesian product: each old block is compared against every new pack and vice versa
    assert sum(1 for plan in plans if "stf_1" in plan.payload["_validation"]["block_ids"]) == 2
    assert sum(1 for plan in plans if "stf_200" in plan.payload["_validation"]["block_ids"]) == 3


def test_the_region_plan_is_deterministic_and_each_pack_pair_has_its_own_stable_identity():
    source = snapshot_of([numbered(70)], [numbered(70)])
    first, _ = plans_for_mapping(source, [region("R1", [1], [1])])
    second, _ = plans_for_mapping(copy.deepcopy(source), [region("R1", [1], [1])])
    assert [plan.group_id for plan in first] == [plan.group_id for plan in second]
    assert [plan.content_key for plan in first] == [plan.content_key for plan in second]
    assert len({plan.group_id for plan in first}) == 4
    # identity is the region and the exact blocks; a changed text keeps the identity but never the content key,
    # so a saved reply is never reused for different text
    other, _ = plans_for_mapping(snapshot_of([numbered(70)], [numbered(70, "иной {n}")]), [region("R1", [1], [1])])
    assert [plan.group_id for plan in other] == [plan.group_id for plan in first]
    assert {plan.content_key for plan in first}.isdisjoint({plan.content_key for plan in other})
    shifted, _ = plans_for_mapping(snapshot_of([numbered(71)], [numbered(70)]), [region("R1", [1], [1])])
    assert {plan.group_id for plan in first}.isdisjoint({plan.group_id for plan in shifted})   # other blocks, other identity


def test_two_regions_are_planned_one_after_the_other_and_never_share_blocks():
    source = snapshot_of([numbered(3), numbered(3)], [numbered(3), numbered(3)])
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1]), region("R2", [2], [2])])
    assert [plan.payload["_validation"]["parent_region_id"] for plan in plans] == ["R1", "R2"]
    assert set(plans[0].payload["_validation"]["block_ids"]).isdisjoint(plans[1].payload["_validation"]["block_ids"])


def test_the_classification_unit_budget_is_128_calls():
    # 8 x 16 = 128 packs pairs: admitted. 9 x 15 = 135: refused as a whole, nothing is silently dropped.
    ok = snapshot_of([numbered(8 * 64)], [numbered(16 * 64)])
    plans, _ = plans_for_mapping(ok, [region("R1", [1], [1])])
    assert len(plans) == 128
    over = snapshot_of([numbered(9 * 64)], [numbered(15 * 64)])
    with pytest.raises(StageAiValidationError, match="v3_windowed_classification_unit_budget"):
        plans_for_mapping(over, [region("R1", [1], [1])])


# --- unmatched pages: bounded, never an invented counterpart ----------------------------------------

def test_an_unmatched_page_gets_at_most_two_opposite_candidates_and_says_the_search_is_incomplete():
    old = [numbered(2), ["кабель ВВГнг прокладка лоток трасса"]]
    new = [numbered(2),
           ["кабель ВВГнг прокладка лоток трасса новая"],       # best overlap
           ["кабель ВВГнг прокладка"],                          # second
           ["кабель прочее"],                                   # third: over the limit of two
           ["вообще иное слово"]]                               # no overlap at all
    source = snapshot_of(old, new)
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1])], old=[2], new=[2, 3, 4, 5])
    unmatched = [plan for plan in plans if plan.group_id.startswith("v3:unmatched:")]
    first = next(plan for plan in unmatched if plan.payload["_validation"]["primary_keys"] == [["OLD", 2]])
    assert first.payload["scope_coverage"] == {"candidate_pages_per_primary": 2,
        "candidate_selection": "bounded_original_supplemental", "global_candidate_search_complete": False}
    pages = [(page["side"], page["physical_page"]) for page in first.payload["pages"]]
    assert pages[0] == ("OLD", 2) and sorted(pages[1:]) == [("NEW", 2), ("NEW", 3)]
    assert first.payload["region"]["old_pages"] == [2] and first.payload["region"]["new_pages"] == [2, 3]
    # every unmatched primary page on both sides has its own plan: the miner plan plus 5 unmatched ones
    assert len(plans) == 1 + 5
    assert sorted(tuple(map(tuple, plan.payload["_validation"]["primary_keys"])) for plan in unmatched) == [
        (("NEW", 2),), (("NEW", 3),), (("NEW", 4),), (("NEW", 5),), (("OLD", 2),)]


def test_an_unmatched_page_without_any_lexical_counterpart_is_reviewed_alone():
    source = snapshot_of([numbered(2), ["уникальное содержание страницы"]], [numbered(2), ["совсем другой набор слов"]])
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1])], old=[2], new=[2])
    alone = [plan for plan in plans if plan.group_id.startswith("v3:unmatched:")]
    assert len(alone) == 2
    for plan in alone:
        side = plan.payload["_validation"]["primary_keys"][0][0]
        assert [(page["side"], page["physical_page"]) for page in plan.payload["pages"]] == [(side, 2)]
        scoped = plan.payload["region"]
        assert scoped["region_id"] == f"ONE-{side}-2"
        assert (scoped["old_pages"] if side == "OLD" else scoped["new_pages"]) == [2]
        assert (scoped["new_pages"] if side == "OLD" else scoped["old_pages"]) == []        # no fabricated counterpart
        assert scoped["confidence"] == 0


def test_a_long_primary_page_is_reviewed_in_complete_packs_each_addressing_the_page():
    texts = ["общий текст страницы номер %d" % n for n in range(70)]
    source = snapshot_of([numbered(2), texts], [["общий текст страницы номер 3"]])
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1])], old=[2])
    unmatched = [plan for plan in plans if plan.group_id.startswith("v3:unmatched:")]
    assert len(unmatched) == 2                                             # 70 blocks = 64 + 6, one candidate pack
    primary = [[row for row in plan.payload["pages"] if (row["side"], row["physical_page"]) == ("OLD", 2)][0] for plan in unmatched]
    assert [len(row["blocks"]) for row in primary] == [64, 6]
    assert all(plan.payload["_validation"]["primary_keys"] == [["OLD", 2]] for plan in unmatched)


def test_a_mapping_without_unmatched_pages_plans_no_unmatched_calls():
    source = snapshot_of([numbered(2)], [numbered(2)])
    plans, _ = plans_for_mapping(source, [region("R1", [1], [1])])
    assert [plan.group_id.startswith("v3:miner:") for plan in plans] == [True]


# --- the driver: the whole plan, end to end, by name -------------------------------------------------

def test_the_whole_plan_for_one_region_is_mapper_miner_dedupe_verify():
    run = drive(w, snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]]))
    assert [name for name, _ in run.calls] == ["mapper", "miner", "dedupe", "verify"]
    assert w.MAPPER_GROUP in run.results


def test_call_count_of_a_larger_run_is_mapper_plus_miner_packs_plus_dedupe_batches_plus_one_verify_per_parameter():
    source = snapshot_of([numbered(65, "позиция {n} диаметр {n} мм")], [["позиция новая диаметр 250 мм"]])
    run = drive(w, source)
    names = [name for name, _ in run.calls]
    assert names.count("mapper") == 1
    assert names.count("miner") == 2                    # two old packs x one new pack
    assert names.count("dedupe") == 1                   # two events fit one batch of eight
    assert names.count("verify") == 2                   # one request per retained parameter, not per batch of eight
    assert names == ["mapper", "miner", "miner", "dedupe", "verify", "verify"]
    for plan in run.plans.values():
        if plan.payload["_experimental_procedure"] == "verify":
            assert len(plan.payload["items"]) == 1


def test_the_unmatched_calls_are_part_of_the_run_and_the_raw_snapshot_is_not_touched():
    source = snapshot_of([["ширина прохода 100 мм"], ["ширина прохода 100 мм прочее"]], [["ширина прохода 120 мм"], ["ширина прохода 120 мм иное"]])
    before = copy.deepcopy(source)
    run = drive(w, source, edit=mapping_edit([region("R001", [1], [1])], unmatched_old=[2], unmatched_new=[2]))
    names = [name for name, _ in run.calls]
    assert names.count("unmatched") == 2 and names.count("miner") == 1
    assert source == before                              # raw deterministic evidence is never rewritten
    assert json.dumps(source, sort_keys=True) == json.dumps(before, sort_keys=True)
