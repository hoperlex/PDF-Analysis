"""The plan of a series from the adjacent sheet pairs (`CMP-SERIES-01`): only neighbours, the immediate statuses, the
forcing link reasons and the pairs of a sheet split across versions."""

from __future__ import annotations

import pytest

from auditmanager.comparison.matrix.model import PageRef
from auditmanager.comparison.matrix.pairs import AdjacentSheetPairs, SheetPairSpec, SplitSpec, TransitionPairs
from auditmanager.comparison.series.planning import assert_adjacent, link_reasons, plan_series

V = ["ver_A", "ver_B", "ver_C", "ver_D"]


def ref(version: str, number: int) -> PageRef:
    return PageRef(version, number, f"cpr_{version}_{number}")


def spec(a: PageRef | None, b: PageRef | None, relation: str = "matched", *, confidence: str | None = "high",
         flags: tuple[str, ...] = (), ai: bool = False, split: SplitSpec | None = None, row: str = "r") -> SheetPairSpec:
    return SheetPairSpec(
        row_id=row, page_a=a, page_b=b, relation=relation, confidence=confidence if relation == "matched" else None,
        flags=flags, ai_dependent=ai, edit_ids=(), ai_link_ids=(), candidates=(), split=split,
    )


def pairs_of(order: list[str], by_transition: list[list[SheetPairSpec]]) -> AdjacentSheetPairs:
    transitions = tuple(TransitionPairs(a, b, tuple(p)) for (a, b), p in zip(zip(order, order[1:]), by_transition))
    return AdjacentSheetPairs("cmx_1", 4, "cvo_1", tuple(order), transitions)


def test_a_series_has_one_transition_for_each_pair_of_neighbours_and_never_another() -> None:
    plan = plan_series(pairs_of(V, [[spec(ref("ver_A", 1), ref("ver_B", 1))]] * 3))
    assert [(t.source_version_uid, t.target_version_uid) for t in plan.transitions] == [
        ("ver_A", "ver_B"), ("ver_B", "ver_C"), ("ver_C", "ver_D")]
    assert [t.transition_no for t in plan.transitions] == [1, 2, 3]
    assert (plan.matrix_id, plan.edit_no, plan.order_id, plan.order) == ("cmx_1", 4, "cvo_1", tuple(V))


def test_a_non_adjacent_pair_of_versions_is_refused() -> None:
    skipping = AdjacentSheetPairs(
        "cmx_1", 0, None, tuple(V),
        (TransitionPairs("ver_A", "ver_C", ()), TransitionPairs("ver_C", "ver_D", ())))
    with pytest.raises(ValueError, match="adjacent"):
        plan_series(skipping)
    with pytest.raises(ValueError):
        assert_adjacent(V, [("ver_A", "ver_B"), ("ver_B", "ver_D")])
    with pytest.raises(ValueError):  # a repeat of a transition is not the neighbours either
        assert_adjacent(V, [("ver_A", "ver_B"), ("ver_A", "ver_B"), ("ver_B", "ver_C"), ("ver_C", "ver_D")])
    assert_adjacent(V, list(zip(V, V[1:])))


def test_a_matched_pair_is_compared_and_the_others_are_reported_at_once() -> None:
    plan = plan_series(pairs_of(V[:2], [[
        spec(ref("ver_A", 1), ref("ver_B", 1)),
        spec(ref("ver_A", 2), None, "removed"),
        spec(None, ref("ver_B", 2), "added"),
        spec(ref("ver_A", 3), None, "unmatched"),
        spec(None, ref("ver_B", 3), "unmatched"),
    ]]))
    pairs = plan.transitions[0].pairs
    assert [p.pair_no for p in pairs] == [1, 2, 3, 4, 5]
    assert [p.status for p in pairs] == [None, "removed", "added", "unmatched", "unmatched"]
    assert [p.compare for p in pairs] == [True, False, False, False, False]
    assert pairs[0].page_a_profile_id == "cpr_ver_A_1" and pairs[0].page_b_profile_id == "cpr_ver_B_1"
    assert (pairs[1].page_a_profile_id, pairs[1].page_b_profile_id) == ("cpr_ver_A_2", None)
    assert (pairs[2].page_a_profile_id, pairs[2].page_b_profile_id) == (None, "cpr_ver_B_2")


@pytest.mark.parametrize(("confidence", "flags", "expected"), [
    ("high", (), ()),
    ("medium", (), ("MATCH_LOW_CONFIDENCE",)),
    ("high", ("bridge",), ("MATCH_LOW_CONFIDENCE",)),
    ("group", (), ("TABLE_GROUP",)),
    ("ai", (), ("AI_MATCH",)),
    ("manual", (), ()),
    ("high", ("duplicate",), ("DUPLICATE_SHEET",)),
    ("medium", ("duplicate", "scan"), ("MATCH_LOW_CONFIDENCE", "DUPLICATE_SHEET")),
    (None, (), ()),
])
def test_the_forcing_link_reasons_are_the_originals(confidence: str | None, flags: tuple[str, ...], expected: tuple[str, ...]) -> None:
    assert link_reasons(confidence, flags) == expected


def test_a_sheet_split_across_versions_is_compared_with_each_of_its_parts() -> None:
    source = ref("ver_A", 5)
    part_1, part_2 = ref("ver_B", 5), ref("ver_B", 6)
    split = SplitSpec(kind="split", role="part", source=source, parts=(part_1, part_2), covered_percent=97.5)
    plan = plan_series(pairs_of(V[:2], [[
        spec(ref("ver_A", 1), ref("ver_B", 1)),
        spec(source, part_1, split=split, flags=("split",)),
        spec(None, part_2, "added", split=split, flags=("split",)),
        spec(source, None, "removed", split=split, flags=("split",)),
    ]]))
    pairs = plan.transitions[0].pairs
    assert [(p.page_a_profile_id, p.page_b_profile_id, p.compare) for p in pairs] == [
        ("cpr_ver_A_1", "cpr_ver_B_1", True),
        ("cpr_ver_A_5", "cpr_ver_B_5", True),
        ("cpr_ver_A_5", "cpr_ver_B_6", True),  # the second part has the older sheet as its page A
    ]
    one, two = pairs[1].part, pairs[2].part
    assert one is not None and two is not None
    assert (one.kind, one.role, one.source_profile_id, one.text_percent) == ("split", "part", "cpr_ver_A_5", 97.5)
    assert [p["page_number"] for p in one.parts] == [6] and [p["page_number"] for p in two.parts] == [5]
    assert pairs[0].part is None


def test_a_typical_sheet_repeated_per_floor_is_compared_whole_with_each_copy() -> None:
    source = ref("ver_A", 2)
    floors = SplitSpec(kind="floors", role="whole", source=source, parts=(ref("ver_B", 2), ref("ver_B", 3)), covered_percent=60.0)
    plan = plan_series(pairs_of(V[:2], [[
        spec(source, ref("ver_B", 2), split=floors, flags=("split",)),
        spec(None, ref("ver_B", 3), "added", split=floors, flags=("split",)),
    ]]))
    first, second = plan.transitions[0].pairs
    assert (first.page_a_profile_id, second.page_a_profile_id) == ("cpr_ver_A_2", "cpr_ver_A_2")
    assert first.part is not None and first.part.role == "whole" and first.part.kind == "floors"


def test_a_cell_without_its_page_profile_is_refused() -> None:
    with pytest.raises(ValueError, match="page profile"):
        plan_series(pairs_of(V[:2], [[spec(PageRef("ver_A", 1, None), ref("ver_B", 1))]]))


def test_flags_and_the_ai_mark_are_kept_on_the_pair() -> None:
    plan = plan_series(pairs_of(V[:2], [[
        spec(ref("ver_A", 1), ref("ver_B", 1), confidence="ai", flags=("scan", "duplicate"), ai=True)]]))
    pair = plan.transitions[0].pairs[0]
    assert pair.confidence == "ai" and pair.flags == ("scan", "duplicate") and pair.ai_dependent is True
