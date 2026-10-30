"""HIGH proof, complete displacement and manual supersession are repair authority."""

from dataclasses import replace

import pytest

from auditmanager.comparison.stage_repair import (
    ContentScore, MapLink, RepairRefused, SheetTitle,
    plan_repairs, precheck_purpose, revert_eligibility,
)


def _plan(links, left, right, *, problems=None, scores=(), used=frozenset()):
    return plan_repairs(
        run_id="run-1", base_revision_id="revision-1", links=links,
        left_sheets=[SheetTitle(key, title) for key, title in left],
        right_sheets=[SheetTitle(key, title) for key, title in right],
        problem_link_ids=(frozenset(problems) if problems is not None else
                          frozenset(link.item_id for link in links if link.relation == "paired")),
        content_scores=scores, already_repaired_run_ids=used,
    )


def _score(left, right, value, *, components=2, strong=1, anchors=3):
    return ContentScore(left, right, value, components, strong, anchors)


def test_purpose_precheck_preserves_unknown_and_reports_conflict():
    unknown = precheck_purpose([], ["План второго этажа"])
    assert (unknown.status, unknown.confidence) == ("PAIR_OK", "low")
    assert precheck_purpose(["План кровли"], ["План подвала"]).confidence == "high"
    conflict = precheck_purpose(["Фасад северный"], ["Схема питания"])
    assert (conflict.status, conflict.reason) == ("PAIR_REVIEW_REQUIRED", "sheet_purpose_conflict")


def test_exact_title_swap_is_complete_and_can_change_expert_links():
    links = (MapLink("a", "l1", "r1"), MapLink("b", "l2", "r2"))
    left = (("l1", "План кровли"), ("l2", "Схема питания"))
    right = (("r1", "Схема питания"), ("r2", "План кровли"))
    plan = _plan(links, left, right)
    assert plan is not None and plan.before_snapshot == links
    assert [(row.left_profile_id, row.right_profile_id, row.confidence)
            for row in plan.after_snapshot] == [
        ("l2", "r1", "automatic_repair"), ("l1", "r2", "automatic_repair"),
    ]
    assert {change.rule for change in plan.changes} == {"TITLE_EXACT"}
    assert plan == _plan(links, left, right)


def test_complete_chain_consumes_free_page_and_records_released_page():
    links = (MapLink("a", "l1", "r1"), MapLink("b", "l2", "r2"),
             MapLink("c", "l3", None, "only_left", "unpaired"))
    plan = _plan(links,
                 (("l1", "План кровли"), ("l2", "Схема питания"), ("l3", "Узел крепления")),
                 (("r1", "Схема питания"), ("r2", "Узел крепления")))
    assert plan is not None
    assert [(row.left_profile_id, row.right_profile_id) for row in plan.after_snapshot] == [
        ("l2", "r1"), ("l3", "r2"), ("l1", None),
    ]
    assert plan.after_snapshot[-1].item_id is None


def test_displacement_of_nonproblem_link_drops_entire_chain():
    links = (MapLink("a", "l1", "r1"), MapLink("b", "l2", "r2"))
    assert _plan(links, (("l1", "План кровли"), ("l2", "Схема питания")),
                 (("r1", "Схема питания"), ("r2", "План кровли")), problems={"a"}) is None


def test_many_to_many_link_is_never_repaired():
    links = (MapLink("a", "l1", "r1"), MapLink("b", "l1", "r2"))
    assert _plan(links, (("l1", "План кровли"), ("l2", "Схема питания")),
                 (("r1", "Схема питания"), ("r2", "План кровли"))) is None


def test_mutual_fuzzy_title_needs_margin_on_both_sides():
    links = (MapLink("a", "l1", "r1"), MapLink("b", "l2", None, "only_left", "unpaired"))
    left = (("l1", "Схема аварийного освещения"), ("l2", "План второго этажа корпус А"))
    right = (("r1", "План второго этажа корпус Б"),)
    plan = _plan(links, left, right)
    assert plan is not None and plan.changes[0].rule == "TITLE_MUTUAL_FUZZY"
    assert plan.changes[0].score >= 0.94
    ambiguous_left = (*left, ("l3", "План второго этажа корпус В"))
    assert _plan(links, ambiguous_left, right) is None


def test_content_mutual_best_swap_requires_all_thresholds_and_anchors():
    links = (MapLink("a", "l1", "r1"), MapLink("b", "l2", "r2"))
    left, right = (("l1", ""), ("l2", "")), (("r1", ""), ("r2", ""))
    scores = (_score("l1", "r1", .10), _score("l2", "r1", .60),
              _score("l1", "r2", .60), _score("l2", "r2", .10))
    plan = _plan(links, left, right, scores=scores)
    assert plan is not None and len(plan.changes) == 2
    assert {change.rule for change in plan.changes} == {"CONTENT_MUTUAL_BEST"}
    assert _plan(links, left, right, scores=tuple(replace(cell, independent_components=1)
                                               for cell in scores)) is None
    assert _plan(links, left, right, scores=tuple(replace(cell, strong_anchor_count=0, anchor_count=2)
                                               for cell in scores)) is None
    low_reverse = tuple(replace(cell, score=.51) if cell.left_profile_id == "l2"
                        and cell.right_profile_id == "r2" else cell for cell in scores)
    assert _plan(links, left, right, scores=low_reverse) is None


def test_content_threshold_boundaries_and_improvement():
    links = (MapLink("a", "l1", "r1"),)
    left, right = (("l1", ""), ("l2", ""), ("l3", "")), (("r1", ""),)
    scores = (_score("l1", "r1", .10), _score("l2", "r1", .44), _score("l3", "r1", .30))
    assert _plan(links, left, right, scores=scores) is not None
    assert _plan(links, left, right, scores=tuple(replace(c, score=.43) if c.left_profile_id == "l2"
                                               else c for c in scores)) is None
    poor_improvement = (_score("l1", "r1", .27), _score("l2", "r1", .44), _score("l3", "r1", .10))
    assert _plan(links, left, right, scores=poor_improvement) is None


def test_incomplete_matrix_and_second_cycle_refuse_explicitly():
    link = (MapLink("a", "l1", "r1"),)
    with pytest.raises(RepairRefused, match="content_matrix_incomplete"):
        _plan(link, (("l1", ""), ("l2", "")), (("r1", ""),),
              scores=(_score("l1", "r1", .1),))
    with pytest.raises(RepairRefused, match="repair_cycle_already_used"):
        _plan(link, (("l1", ""),), (("r1", ""),), used=frozenset({"run-1"}))


def test_revert_requires_recorded_after_snapshot_and_no_later_manual_act():
    plan = _plan((MapLink("a", "l1", "r1"), MapLink("b", "l2", "r2")),
                 (("l1", "План кровли"), ("l2", "Схема питания")),
                 (("r1", "Схема питания"), ("r2", "План кровли")))
    assert plan is not None
    runtime_rows = tuple(replace(row, item_id=f"new-{index}") for index, row in enumerate(plan.after_snapshot))
    assert revert_eligibility(plan, runtime_rows, later_manual_edit=False).eligible
    assert revert_eligibility(plan, runtime_rows, later_manual_edit=True).reason == "superseded_by_manual_edit"
    assert not revert_eligibility(plan, plan.before_snapshot, later_manual_edit=False).eligible
    assert revert_eligibility(plan, runtime_rows, later_manual_edit=False,
                              already_reverted=True).reason == "already_reverted"
