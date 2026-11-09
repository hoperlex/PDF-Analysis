"""windowed-global-v1: rebinding of the windowed plan, cross-batch candidates, Consolidator calls, groups, cards.

Intended behaviour is taken from consolidation.py's docstrings and docs/program/BLOCK4-STAGE-1030.md:
the local Dedupe compares eight-event batches, the global stage compares ONLY pairs that no local call
has seen together, at most 128 ranked pairs and four pairs per call; a duplicate recommendation needs an
exact quote covering both events; typed conflicts and source-conflict hints stop an automatic group;
every original event, hint and verification is retained; a recommendation is never an expert act.
"""
from __future__ import annotations

import copy

import pytest

from auditmanager.comparison.stage_ai.validation import StageAiValidationError, digest
from auditmanager.comparison.stage_v3 import consolidation as c
from auditmanager.comparison.stage_v3 import windowed as w
from auditmanager.comparison.stage_v3.policy import GLOBAL_LIMITS, GLOBAL_VERSION, LIMITS, VERSION
from tests.unit.stage_v3.windowed_events import event, miner_result
from tests.unit.stage_v3.windowed_fixture import (MAPPER_SOURCE, MODEL, PHASES, answer_of, count, drive, hint_for,
                                                  mapping_edit, procedures, region, row_of, snapshot_of)

REGIONS = 9
SAME_TRANSITION = ["ширина прохода 120 мм"] * REGIONS


def combine(*edits):
    def edit(procedure, plan, answer):
        for part in edits:
            if part is not None:
                part(procedure, plan, answer)
    return edit


def decide(choose):
    """An `edit` that answers every requested pair with `choose(pair)`; DUPLICATE quotes every supplied passage."""
    def edit(procedure, plan, answer):
        if procedure != "consolidate":
            return
        for decision, pair in zip(answer["decisions"], plan.payload["pairs"]):
            kind = choose(pair)
            decision["decision"] = kind
            if kind == "DUPLICATE":
                decision["source_evidence"] = [{"source_id": row["source_id"], "quote": row["quote"]}
                                               for row in pair["source_passages"]]
    return edit


def nine_regions(new_texts=SAME_TRANSITION):
    source = snapshot_of([["ширина прохода 100 мм"]] * REGIONS, [[text] for text in new_texts])
    mapping = mapping_edit([region(f"R{n:03d}", [n], [n]) for n in range(1, REGIONS + 1)])
    return source, mapping


def events_of(run, source):
    """The merged events in the order the local Dedupe saw them, with the batch each one was compared in."""
    changes = w.merged_changes(run.results)[0]
    batch = {row["projectchange_id"]: index for index, rows in enumerate(w._dedupe_batches(changes)) for row in rows}
    return changes, batch


@pytest.fixture(scope="module")
def base():
    source, mapping = nine_regions()
    run = drive(c, source, edit=mapping)
    changes, batch = events_of(run, source)
    return source, mapping, run, changes, batch


def consolidate_plans(run):
    return [plan for plan in run.plans.values() if plan.payload["_experimental_procedure"] == "consolidate"]


# --- the plan is the windowed plan, rebound ------------------------------------------------------------------

def test_the_global_plan_rebinds_every_windowed_request_to_its_own_bundle_and_limits(base):
    source, _mapping, run, _changes, _batch = base
    windowed = w.plans_for("review", source, {}, MODEL)[0]
    plan = c.plans_for("review", source, {}, MODEL)[0]
    assert plan.group_id == windowed.group_id and plan.phase == windowed.phase
    assert plan.prompt_version == c.BUNDLE != w.BUNDLE
    assert plan.content_key != windowed.content_key and plan.source_sha256 != windowed.source_sha256
    assert plan.payload["plan_version"] == GLOBAL_VERSION != VERSION
    assert plan.payload["source_limits"] == GLOBAL_LIMITS
    assert plan.payload["pages"] == windowed.payload["pages"] and plan.instructions == windowed.instructions
    miner = c.plans_for("classify", source, run.results, MODEL)
    assert [p.group_id for p in miner] == [p.group_id for p in w.plans_for("classify", source, run.results, MODEL)]
    assert all(p.prompt_version == c.BUNDLE for p in miner)


def test_global_limits_extend_the_windowed_limits_by_exactly_the_consolidation_window():
    assert GLOBAL_VERSION == "windowed-global-v1"
    assert GLOBAL_LIMITS == {**LIMITS, "global_candidate_pairs": 128, "global_pairs_per_call": 4}


def test_the_global_run_calls_everything_windowed_calls_and_then_the_consolidator_in_the_last_phase(base):
    _source, _mapping, run, _changes, _batch = base
    names = procedures(run)
    assert names[0] == "mapper" and names[-2:] == ["consolidate", "consolidate"]
    assert (count(run, "miner"), count(run, "dedupe"), count(run, "verify"), count(run, "consolidate")) == (9, 2, 9, 2)
    assert len(names) == 1 + 9 + 2 + 9 + 2
    assert all(plan.phase == "synthesize" for plan in consolidate_plans(run))


def test_no_candidate_pair_means_no_consolidator_call():
    source = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])
    run = drive(c, source)
    assert procedures(run) == ["mapper", "miner", "dedupe", "verify"]
    cards = c.canonical_cards(source, run.results)
    assert len(cards) == 1
    coverage = cards[0]["experimental"]["global_consolidation"]["coverage"]
    assert (coverage["candidate_pairs"], coverage["planned_pairs"], coverage["compared_pairs"], coverage["not_compared_pairs"]) == (0, 0, 0, 0)


def test_the_consolidator_waits_for_every_local_dedupe_and_every_verification(base):
    source, mapping, _run, _changes, _batch = base
    run = drive(c, source, edit=mapping, phases=PHASES[:2])
    plans = c.plans_for("synthesize", source, run.results, MODEL)
    assert {p.payload["_experimental_procedure"] for p in plans} == {"dedupe"} and len(plans) == 2
    assert all(p.payload["plan_version"] == GLOBAL_VERSION for p in plans)
    for plan in plans:
        run.results[plan.group_id] = c.parse(plan, row_of(answer_of(plan)), source)
    plans = c.plans_for("synthesize", source, run.results, MODEL)
    assert {p.payload["_experimental_procedure"] for p in plans} == {"verify"} and len(plans) == 9
    for plan in plans[:-1]:
        run.results[plan.group_id] = c.parse(plan, row_of(answer_of(plan)), source)
    assert [p.payload["_experimental_procedure"] for p in c.plans_for("synthesize", source, run.results, MODEL)
            if p.group_id not in run.results] == ["verify"]                      # one verification missing: still no consolidation


# --- candidates: only pairs no local call has compared ------------------------------------------------------------

def test_only_events_from_different_local_dedupe_batches_are_ever_paired(base):
    _source, _mapping, run, changes, batch = base
    ids = [row["projectchange_id"] for row in changes]
    last = ids[8]
    assert [batch[i] for i in ids] == [0] * 8 + [1]
    pairs = [pair for plan in consolidate_plans(run) for pair in plan.payload["pairs"]]
    assert len(pairs) == 8                                                       # 8 x 1 across the two batches, none inside a batch
    for pair in pairs:
        first, second = pair["event_ids"]
        assert first < second and batch[first] != batch[second] and last in pair["event_ids"]
        assert pair["pair_id"].startswith("vgp_") and len(pair["pair_id"]) == 4 + 24
        assert pair["candidate_reason"] == "cross_location_subject_and_transition"
    assert len({pair["pair_id"] for pair in pairs}) == 8


def test_consolidator_calls_carry_at_most_four_pairs_and_say_what_they_do_not_claim(base):
    _source, _mapping, run, _changes, _batch = base
    plans = consolidate_plans(run)
    assert [len(plan.payload["pairs"]) for plan in plans] == [4, 4]
    for plan in plans:
        payload = plan.payload
        assert payload["plan_version"] == GLOBAL_VERSION and payload["scope_coverage"] == {
            "global_semantic_complete": False, "all_original_records_retained": True}
        assert payload["_validation"]["pair_ids"] == [pair["pair_id"] for pair in payload["pairs"]]
        assert plan.group_id == "v3:consolidate:" + digest([pair["pair_id"] for pair in payload["pairs"]])[:24]
        assert plan.max_output_tokens == 6000
        assert plan.instructions.startswith(c.PROMPT) and "АДАПТАЦИЯ" in plan.instructions
        assert "Никакого экспертного решения" in plan.instructions


def test_a_pair_request_carries_both_events_their_sources_and_the_independent_check(base):
    _source, _mapping, run, changes, _batch = base
    pair = consolidate_plans(run)[0].payload["pairs"][0]
    assert [event_["event_id"] for event_ in pair["events"]] == pair["event_ids"]
    for event_ in pair["events"]:
        assert len(event_["source_ids"]) == 2 and event_["input_truncated"] == []
        assert event_["parameters"][0]["verification_verdict"] == "CONFIRMED"
        assert (event_["parameters"][0]["old_value"], event_["parameters"][0]["new_value"]) == ("100", "120")
    quotes = {(row["source_id"], row["quote"]) for row in pair["source_passages"]}
    assert len(quotes) == len(pair["source_passages"]) == 4
    assert {quote for _, quote in quotes} == {"ширина прохода 100 мм", "ширина прохода 120 мм"}
    assert pair["typed_conflicts"] == [] and pair["typed_conflict_count"] == 0 and pair["typed_conflicts_truncated"] is False
    assert pair["source_conflict_hint_ids"] == []
    assert pair["hint_coverage"] == {"related": 0, "provided": 0, "all_originals_retained": True}


def cross_pairs(first, second):
    """Candidate pairs for `first` (local batch 0, padded to eight) against `second` (the next batch)."""
    fillers = [event(f"F{n}", blocks=[f"fill{n}"], subject="Фон", summary="Фон") for n in range(8 - len(first))]
    results = {"v3:miner:a": miner_result(*first, *fillers), "v3:miner:b": miner_result(*second)}
    changes, _ = w.merged_changes(results)
    return c._candidate_pairs(None, results, changes), changes


def reasons(first, second):
    (pairs, scope), _ = cross_pairs(first, second)
    return {tuple(sorted(pair["event_ids"])): pair["candidate_reason"] for pair in pairs}, scope


def test_events_of_one_local_batch_are_never_candidates_even_when_they_share_a_source():
    same = [event(f"E{n}", blocks=["shared"]) for n in range(8)]
    found, scope = reasons(same, [])
    assert found == {} and scope["candidate_pairs"] == 0


def test_a_shared_native_source_makes_a_cross_batch_pair():
    found, _ = reasons([event("E1", blocks=["b1"], subject="Фон", summary="Фон")],
                       [event("E2", blocks=["b1"], subject="Иное", summary="Иное")])
    assert found == {("v3:miner:a:E1", "v3:miner:b:E2"): "shared_native_source"}


def test_similar_subject_on_overlapping_old_and_new_pages_makes_a_pair():
    found, _ = reasons([event("E1", blocks=["b1"], old_pages=(1, 2), new_pages=(3,))],
                       [event("E2", blocks=["b2"], old_pages=(2,), new_pages=(3, 4))])
    assert found == {("v3:miner:a:E1", "v3:miner:b:E2"): "cross_batch_subject_and_page_similarity"}


def test_a_similar_subject_alone_is_not_enough_pages_must_overlap_on_both_sides():
    found, _ = reasons([event("E1", blocks=["b1"], old_pages=(1,), new_pages=(1,))],
                       [event("E2", blocks=["b2"], old_pages=(1,), new_pages=(2,))])
    assert found == {}
    found, _ = reasons([event("E1", blocks=["b1"], old_pages=(1,), new_pages=(1,))],
                       [event("E2", blocks=["b2"], old_pages=(2,), new_pages=(1,))])
    assert found == {}


def test_the_same_value_transition_links_events_on_different_pages_only_when_the_subject_is_close():
    near = [event("E1", blocks=["b1"], parameters=[("100", "120")], old_pages=(1,), new_pages=(1,))]
    found, _ = reasons(near, [event("E2", blocks=["b2"], parameters=[("100", "120")], old_pages=(5,), new_pages=(5,))])
    assert found == {("v3:miner:a:E1", "v3:miner:b:E2"): "cross_location_subject_and_transition"}
    found, _ = reasons(near, [event("E2", blocks=["b2"], parameters=[("100", "130")], old_pages=(5,), new_pages=(5,))])
    assert found == {}                                                           # a different transition: no link
    far = event("E2", blocks=["b2"], parameters=[("100", "120")], old_pages=(5,), new_pages=(5,),
                subject="Совершенно иной предмет", summary="Другое событие целиком")
    found, _ = reasons(near, [far])
    assert found == {}                                                           # same transition, unrelated subject


def test_a_shared_designation_links_events_on_different_pages():
    text = dict(subject="Кабель питания", summary="Кабель ВВГ-3 питания заменён", old_pages=(1,), new_pages=(1,))
    found, _ = reasons([event("E1", blocks=["b1"], **text)], [event("E2", blocks=["b2"], **dict(text, old_pages=(7,), new_pages=(7,)))])
    assert found == {("v3:miner:a:E1", "v3:miner:b:E2"): "cross_location_subject_and_transition"}


def test_pairs_are_ranked_source_first_then_similarity_and_ties_break_by_pair_id():
    first = [event("E1", blocks=["b1"], subject="Фон", summary="Фон"),
             event("E2", blocks=["b2"], old_pages=(1,), new_pages=(1,))]
    second = [event("E3", blocks=["b1"], subject="Иное", summary="Иное"),         # shares a source with E1
              event("E4", blocks=["b4"], old_pages=(1,), new_pages=(1,))]         # similar to E2
    (pairs, scope), _ = cross_pairs(first, second)
    assert [pair["event_ids"] for pair in pairs] == [["v3:miner:a:E1", "v3:miner:b:E3"], ["v3:miner:a:E2", "v3:miner:b:E4"]]
    assert pairs[0]["rank"] > 5 > pairs[1]["rank"] > 1
    assert scope["candidate_pairs"] == scope["planned_pairs"] == 2 and scope["not_planned_pairs"] == 0
    assert scope["global_semantic_complete"] is False
    ties = [event(f"T{n}", blocks=["shared"]) for n in range(3)]
    (pairs, _), _ = cross_pairs(ties, [event("Z", blocks=["shared"])])
    assert [pair["pair_id"] for pair in pairs] == sorted(pair["pair_id"] for pair in pairs)


def test_the_comparison_window_is_128_pairs_and_everything_outside_it_is_counted_and_fingerprinted():
    groups = "abc"
    results = {f"v3:miner:{key}": miner_result(*[event(f"{key}{n}", blocks=["shared"]) for n in range(8)]) for key in groups}
    changes, _ = w.merged_changes(results)
    pairs, scope = c._candidate_pairs(None, results, changes)
    # Three local batches of eight: every cross-batch pair is a candidate (192). They all share a source and
    # a subject, so they all rank alike and the documented tie-break (pair id) decides who is inside the window.
    cross = sorted("vgp_" + digest(sorted((left, right)))[:24]
                   for left in (row["projectchange_id"] for row in changes)
                   for right in (row["projectchange_id"] for row in changes)
                   if left < right and left.split(":")[2] != right.split(":")[2])
    assert len(cross) == 192
    assert len(pairs) == GLOBAL_LIMITS["global_candidate_pairs"] == 128
    assert [pair["pair_id"] for pair in pairs] == cross[:128]
    assert (scope["candidate_pairs"], scope["planned_pairs"], scope["not_planned_pairs"]) == (192, 128, 64)
    assert scope["excluded_pair_ids_sha256"] == digest(cross[128:])
    assert scope["candidate_policy"] == "all_cross_batch_source_or_subject_page_candidates" and scope["feature_text_limit"] == 1000
    assert scope["global_semantic_complete"] is False


def test_with_more_candidates_than_the_window_the_run_makes_128_pairs_worth_of_calls_and_loses_no_event():
    regions = 24
    source = snapshot_of([["ширина прохода 100 мм"]] * regions, [["ширина прохода 120 мм"]] * regions)
    mapping = mapping_edit([region(f"R{n:03d}", [n], [n]) for n in range(1, regions + 1)])
    run = drive(c, source, edit=mapping)
    pairs = [pair for plan in consolidate_plans(run) for pair in plan.payload["pairs"]]
    assert count(run, "consolidate") == 32 and len(pairs) == 128 and all(len(p.payload["pairs"]) == 4 for p in consolidate_plans(run))
    manifest = c.final_report_metadata(source, run.results)["global_consolidation"]
    assert (manifest["coverage"]["candidate_pairs"], manifest["coverage"]["planned_pairs"],
            manifest["coverage"]["compared_pairs"], manifest["coverage"]["not_planned_pairs"]) == (192, 128, 128, 64)
    assert manifest["coverage"]["not_compared_pairs"] == 64 and manifest["coverage"]["global_semantic_complete"] is False
    cards = c.canonical_cards(source, run.results)
    assert len(cards) == regions                                             # no event disappears when its pair is outside the window
    assert len(manifest["original_events"]) == regions


# --- parse: the Consolidator's answer -----------------------------------------------------------------------------------

def separate(plan):
    return answer_of(plan)


def refuses(plan, answer, source, reason, **kwargs):
    with pytest.raises(StageAiValidationError, match=reason):
        c.parse(plan, row_of(answer, **kwargs), source)


def test_every_requested_pair_must_be_decided_exactly_once_with_unchanged_event_ids(base):
    source, _mapping, run, _changes, _batch = base
    plan = consolidate_plans(run)[0]
    good = separate(plan)
    assert c.parse(plan, row_of(good), source) == good
    refuses(plan, dict(good, decisions=good["decisions"][:-1]), source, "v3_global_partition_invalid")           # one left out
    refuses(plan, dict(good, decisions=good["decisions"] + [good["decisions"][0]]), source, "v3_response_array_budget")
    refuses(plan, dict(good, decisions=[good["decisions"][0]] * 4), source, "v3_global_partition_invalid")       # one four times
    swapped = copy.deepcopy(good)
    swapped["decisions"][0]["event_ids"].reverse()
    refuses(plan, swapped, source, "v3_global_partition_invalid")
    foreign = copy.deepcopy(good)
    foreign["decisions"][0]["pair_id"] = "vgp_unknown"
    refuses(plan, foreign, source, "v3_global_partition_invalid")


def test_a_decision_needs_a_reason_of_bounded_length(base):
    source, _mapping, run, _changes, _batch = base
    plan = consolidate_plans(run)[0]
    for reason in ("", "   ", "я" * 1601):
        answer = separate(plan)
        answer["decisions"][0]["reason"] = reason
        refuses(plan, answer, source, "v3_global_reason_invalid")
    answer = separate(plan)
    answer["decisions"][0]["reason"] = "я" * 1600
    assert c.parse(plan, row_of(answer), source) == answer


def test_an_incomplete_wrong_pair_or_off_schema_answer_is_refused(base):
    source, _mapping, run, _changes, _batch = base
    plan = consolidate_plans(run)[0]
    refuses(plan, separate(plan), source, "v3_global_response_incomplete", stop_reason="max_tokens")
    refuses(plan, dict(separate(plan), pair="another-pair"), source, "v3_global_pair_mismatch")
    refuses(plan, dict(separate(plan), decisions=[dict(separate(plan)["decisions"][0], decision="MERGE")]), source, "v3_response_enum_schema")
    refuses(plan, dict(separate(plan), groups=[]), source, "v3_response_object_schema")


def test_a_quote_must_be_literally_inside_a_passage_that_was_sent(base):
    source, _mapping, run, _changes, _batch = base
    plan = consolidate_plans(run)[0]
    pair = plan.payload["pairs"][0]
    passage = pair["source_passages"][0]
    answer = separate(plan)
    answer["decisions"][0]["source_evidence"] = [{"source_id": passage["source_id"], "quote": passage["quote"][:7]}]
    assert c.parse(plan, row_of(answer), source) == answer
    for evidence in ({"source_id": passage["source_id"], "quote": "выдуманная цитата"},
                     {"source_id": "stf_unknown", "quote": passage["quote"]},
                     {"source_id": passage["source_id"], "quote": ""}):
        answer["decisions"][0]["source_evidence"] = [evidence]
        refuses(plan, answer, source, "v3_global_quote_not_in_input")
    other = next(row for row in pair["source_passages"] if row["quote"] != passage["quote"])
    answer["decisions"][0]["source_evidence"] = [{"source_id": other["source_id"], "quote": passage["quote"]}]
    refuses(plan, answer, source, "v3_global_quote_not_in_input")                  # a real quote, but of another source


def test_a_duplicate_recommendation_needs_proof_from_the_sources_of_both_events(base):
    source, _mapping, run, _changes, _batch = base
    plan = consolidate_plans(run)[0]
    pair = plan.payload["pairs"][0]
    first = pair["events"][0]["source_ids"]
    both = [{"source_id": row["source_id"], "quote": row["quote"]} for row in pair["source_passages"]]
    answer = separate(plan)
    answer["decisions"][0].update(decision="DUPLICATE", source_evidence=[])
    refuses(plan, answer, source, "v3_global_duplicate_without_bilateral_event_proof")
    answer["decisions"][0]["source_evidence"] = [row for row in both if row["source_id"] in first]
    refuses(plan, answer, source, "v3_global_duplicate_without_bilateral_event_proof")      # proof of one event only
    answer["decisions"][0]["source_evidence"] = both
    assert c.parse(plan, row_of(answer), source) == answer
    answer["decisions"][0].update(decision="RELATED", source_evidence=[])                  # other decisions need no proof
    assert c.parse(plan, row_of(answer), source) == answer


def test_plans_that_are_not_consolidations_follow_the_windowed_rules():
    plan = c.plans_for("review", MAPPER_SOURCE, {}, MODEL)[0]
    answer = answer_of(plan)
    answer["regions"] = [region("R001", [1, 2], [1]), region("R002", [2], [2])]
    with pytest.raises(StageAiValidationError, match="v3_windowed_source_bound_response_invalid") as caught:
        c.parse(plan, row_of(answer), MAPPER_SOURCE)
    assert "overlapping" in str(caught.value.__cause__)
    answer["regions"] = [region("R001", [1], [1]), region("R002", [2], [2])]
    assert c.parse(plan, row_of(answer), MAPPER_SOURCE) == answer


# --- groups, conflicts, cards ----------------------------------------------------------------------------------------------

def run_with(base, choose, *edits, new_texts=None):
    source, mapping, run, changes, _batch = base
    if new_texts is not None:
        source, mapping = nine_regions(new_texts)
    return source, drive(c, source, edit=combine(mapping, *edits, decide(choose)))


def pair_has(*ids):
    return lambda pair: "DUPLICATE" if set(ids) <= set(pair["event_ids"]) else "SEPARATE"


def decisions_of(source, run):
    manifest = c.final_report_metadata(source, run.results)["global_consolidation"]
    return manifest, {tuple(row["event_ids"]): row for row in manifest["decisions"]}


def test_separate_decisions_group_nothing_and_every_card_keeps_its_originals(base):
    source, _mapping, run, changes, _batch = base
    cards = c.canonical_cards(source, run.results)
    manifest, decisions = decisions_of(source, run)
    assert len(cards) == REGIONS and manifest["groups"] == []
    assert {row["model_decision"] for row in decisions.values()} == {"SEPARATE"} == {row["applied_decision"] for row in decisions.values()}
    for card in cards:
        meta = card["experimental"]
        assert meta["plan_version"] == GLOBAL_VERSION and meta["limits"] == GLOBAL_LIMITS
        assert meta["global_consolidation"]["group_ids"] == [] and len(meta["original_events"]) == 1
        assert meta["global_consolidation"]["manifest_sha256"] == manifest["manifest_sha256"]
        assert meta["norms_status"] == "not_checked" and card["class_name"] == "REVIEW"


def test_the_manifest_retains_every_original_event_verification_and_a_reproducible_digest(base):
    source, _mapping, run, changes, _batch = base
    manifest, _ = decisions_of(source, run)
    assert manifest["version"] == "source-bound-global/1"
    assert [row["projectchange_id"] for row in manifest["original_events"]] == [row["projectchange_id"] for row in changes]
    assert len(manifest["parameter_verifications"]) == REGIONS and manifest["original_hints"] == []
    assert manifest["coverage"]["compared_pairs"] == manifest["coverage"]["planned_pairs"] == 8
    assert manifest["coverage"]["not_compared_pairs"] == 0
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    assert manifest["manifest_sha256"] == digest(unsigned)
    assert c.final_report_metadata(source, run.results)["global_consolidation"] == manifest          # deterministic
    # the raw saved answers are not what the manifest refers to by reference: changing the copy changes nothing saved
    saved = copy.deepcopy(run.results)
    manifest["original_events"][0]["change_summary"] = "изменено"
    assert run.results == saved


def test_a_duplicate_recommendation_with_exact_quotes_merges_two_cards_and_loses_nothing(base):
    source, _mapping, _run, changes, _batch = base
    ids = [row["projectchange_id"] for row in changes]
    first, last = ids[0], ids[8]
    source, run = run_with(base, pair_has(first, last))
    manifest, decisions = decisions_of(source, run)
    decision = decisions[tuple(sorted((first, last)))]
    assert (decision["model_decision"], decision["applied_decision"]) == ("DUPLICATE", "DUPLICATE")
    assert decision["source_evidence"] and decision["typed_conflict_count"] == 0 and decision["input_truncated"] is False
    assert manifest["groups"] == [{"group_id": manifest["groups"][0]["group_id"], "event_ids": sorted((first, last))}]
    assert manifest["groups"][0]["group_id"].startswith("vgg_")
    cards = c.canonical_cards(source, run.results)
    assert len(cards) == REGIONS - 1
    merged = next(card for card in cards if len(card["experimental"]["original_events"]) == 2)
    meta = merged["experimental"]
    assert {row["projectchange_id"] for row in meta["original_events"]} == {first, last}
    assert len(meta["related_events"]) == 1 and len(meta["sources"]) == 4 and len(merged["evidence_ids"]) == 4
    assert meta["global_consolidation"]["group_ids"] == [manifest["groups"][0]["group_id"]]
    assert meta["global_consolidation"]["event_ids"] == sorted((first, last))
    evidence = [identifier for card in cards for identifier in card["evidence_ids"]]
    assert len(evidence) == len(set(evidence)) == 2 * REGIONS                  # still an exact partition of the sources
    assert len(manifest["original_events"]) == REGIONS                          # the merge removed no original


def test_duplicate_recommendations_chain_into_one_group(base):
    _source, _mapping, _run, changes, _batch = base
    ids = [row["projectchange_id"] for row in changes]
    last = ids[8]
    source, run = run_with(base, lambda pair: "DUPLICATE" if last in pair["event_ids"] and
                           (ids[0] in pair["event_ids"] or ids[1] in pair["event_ids"]) else "SEPARATE")
    manifest, _ = decisions_of(source, run)
    assert [group["event_ids"] for group in manifest["groups"]] == [sorted((ids[0], ids[1], last))]
    cards = c.canonical_cards(source, run.results)
    assert len(cards) == REGIONS - 2
    merged = next(card for card in cards if len(card["experimental"]["original_events"]) == 3)
    assert len(merged["experimental"]["related_events"]) == 2


@pytest.mark.parametrize("decision", ["RELATED", "NEEDS_CONTEXT", "SEPARATE"])
def test_only_a_duplicate_recommendation_ever_groups(base, decision):
    _source, _mapping, _run, changes, _batch = base
    source, run = run_with(base, lambda pair: decision)
    manifest, decisions = decisions_of(source, run)
    assert manifest["groups"] == [] and {row["applied_decision"] for row in decisions.values()} == {decision}
    assert len(c.canonical_cards(source, run.results)) == REGIONS


def designation(procedure, _plan, answer):
    if procedure == "miner":
        answer["projectchanges"][0]["engineering_subject"] = "Кабель ВВГ-3"


def test_conflicting_typed_values_stop_the_group_and_keep_both_values(base):
    _source, _mapping, run, changes, _batch = base
    ids = [row["projectchange_id"] for row in changes]
    last, other = ids[8], ids[0]
    page = changes[8]["new_pages"][0]
    texts = list(SAME_TRANSITION)
    texts[page - 1] = "ширина прохода 130 мм"                                     # the last event reads 100 -> 130, the others 100 -> 120
    source, run = run_with(base, pair_has(other, last), designation, new_texts=texts)
    manifest, decisions = decisions_of(source, run)
    decision = decisions[tuple(sorted((other, last)))]
    assert decision["model_decision"] == "DUPLICATE" and decision["applied_decision"] == "RELATED_CONFLICT"
    assert decision["typed_conflict_count"] >= 1 and decision["typed_conflicts"]
    conflict = decision["typed_conflicts"][0]
    assert {conflict["left"]["new_value"], conflict["right"]["new_value"]} == {"120", "130"}
    assert manifest["groups"] == [] and len(c.canonical_cards(source, run.results)) == REGIONS


def test_a_source_conflict_observation_on_the_same_source_stops_the_group(base):
    _source, _mapping, _run, changes, _batch = base
    ids = [row["projectchange_id"] for row in changes]
    last, other = ids[8], ids[0]
    page = changes[8]["new_pages"][0]
    hint_source = nine_regions()[0]

    def conflict_hint(procedure, plan, answer):
        if procedure == "miner" and plan.payload["region"]["region_id"] == f"R{page:03d}":
            answer["unresolved_hints"] = [hint_for(hint_source, f"stf_{page}", "OLD", page, old_pages=[page], new_pages=[page])]
            answer["unresolved_hints"][0]["kind"] = "SOURCE_CONFLICT"
    source, run = run_with(base, pair_has(other, last), designation, conflict_hint)
    manifest, decisions = decisions_of(source, run)
    decision = decisions[tuple(sorted((other, last)))]
    assert decision["applied_decision"] == "RELATED_CONFLICT" and decision["typed_conflict_count"] == 0
    assert len(decision["source_conflict_hint_ids"]) == 1 and decision["source_conflict_hint_ids"][0].endswith(":H1")
    assert manifest["groups"] == [] and len(manifest["original_hints"]) == 1


def test_input_cut_for_the_model_prevents_an_automatic_group(base):
    _source, _mapping, _run, changes, _batch = base
    ids = [row["projectchange_id"] for row in changes]
    last, other = ids[8], ids[0]
    page = changes[8]["new_pages"][0]

    def long_summary(procedure, plan, answer):
        if procedure == "miner" and plan.payload["region"]["region_id"] == f"R{page:03d}":
            answer["projectchanges"][0]["change_summary"] = "Синтетический ответ требует проверки. " * 40
    source, run = run_with(base, pair_has(other, last), designation, long_summary)
    pair = next(p for plan in consolidate_plans(run) for p in plan.payload["pairs"] if last in p["event_ids"] and other in p["event_ids"])
    cut = next(event_ for event_ in pair["events"] if event_["event_id"] == last)
    assert cut["input_truncated"] == ["change_summary"] and len(cut["change_summary"]) == 1200
    manifest, decisions = decisions_of(source, run)
    decision = decisions[tuple(sorted((other, last)))]
    assert decision["applied_decision"] == "NEEDS_CONTEXT" and decision["input_truncated"] is True
    assert manifest["groups"] == []
    assert len(c.canonical_cards(source, run.results)) == REGIONS


def test_cards_are_refused_until_every_planned_pair_has_an_answer(base):
    source, _mapping, run, _changes, _batch = base
    missing = consolidate_plans(run)[1].group_id
    partial = {key: value for key, value in run.results.items() if key != missing}
    pending = [plan.group_id for plan in c.plans_for("synthesize", source, partial, MODEL) if plan.group_id not in partial]
    assert pending == [missing]
    with pytest.raises(StageAiValidationError, match="v3_global_consolidation_incomplete"):
        c.canonical_cards(source, partial)
    assert len(c.canonical_cards(source, run.results)) == REGIONS


def test_a_saved_decision_for_a_pair_that_is_no_longer_a_candidate_is_ignored(base):
    source, _mapping, run, _changes, _batch = base
    results = copy.deepcopy(run.results)
    plan = consolidate_plans(run)[0]
    results["v3:consolidate:stale"] = {"pair": "pair-test", "decisions": [{"pair_id": "vgp_stale", "event_ids": ["a", "b"],
        "decision": "DUPLICATE", "reason": "устарело", "source_evidence": []}]}
    manifest = c.final_report_metadata(source, results)["global_consolidation"]
    assert manifest["coverage"]["compared_pairs"] == 8 and manifest["groups"] == []
    assert plan.group_id in results
