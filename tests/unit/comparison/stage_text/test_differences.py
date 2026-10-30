"""Raw deltas and cross-sheet suggestions stay separate from exact exclusions."""

from __future__ import annotations

import hashlib

import pytest

from auditmanager.comparison.stage_text import (
    SheetLink, TextFragment, build_raw_differences, find_cross_sheet_hints,
)
from auditmanager.comparison.stage_text.fragments import canonical_text
from auditmanager.comparison.stage_text.differences import build_grouped_raw_differences


def _fragment(side: str, profile: str, value: str, ordinal: int = 1) -> TextFragment:
    key = hashlib.sha256(f"{side}:{profile}:{ordinal}:{value}".encode()).hexdigest()
    return TextFragment(key, profile, side, ordinal, value, canonical_text(value),
                        {"x0": 10.0, "top": 10.0, "x1": 80.0, "bottom": 18.0})


def _manifest(fragments: tuple[TextFragment, ...], profiles: tuple[str, ...]):
    return {profile: frozenset(f.content_key for f in fragments if f.profile_id == profile)
            for profile in profiles}


def _diff(fragments: tuple[TextFragment, ...]):
    profiles = ("cpr_left", "cpr_right")
    return build_raw_differences([SheetLink(*profiles)], fragments,
                                 {profile: (100, 100) for profile in profiles},
                                 _manifest(fragments, profiles))


def test_numeric_change_is_raw_changed_and_exact_row_is_excluded() -> None:
    left_same = _fragment("left", "cpr_left", "Кабель ВВГ 3х4")
    right_same = _fragment("right", "cpr_right", "Кабель ВВГ 3х4")
    left_value = _fragment("left", "cpr_left", "Нагрузка 10 кВт", 2)
    right_value = _fragment("right", "cpr_right", "Нагрузка 20 кВт", 2)
    result = _diff((left_same, left_value, right_same, right_value))
    assert len(result.exact_exclusions) == 1
    assert [(d.status, d.left_content_key, d.right_content_key) for d in result.differences] == [
        ("changed", left_value.content_key, right_value.content_key),
    ]


def test_ambiguous_candidates_remain_removed_and_added() -> None:
    left = _fragment("left", "cpr_left", "Нагрузка 10 кВт")
    right_a = _fragment("right", "cpr_right", "Нагрузка 20 кВт")
    right_b = _fragment("right", "cpr_right", "Нагрузка 30 кВт", 2)
    result = _diff((left, right_a, right_b))
    assert not result.exact_exclusions
    assert [item.status for item in result.differences] == ["removed", "added", "added"]


def test_short_weak_similarity_cannot_erase_unmatched_text() -> None:
    result = _diff((_fragment("left", "cpr_left", "Шкаф А"),
                    _fragment("right", "cpr_right", "Шкаф Б")))
    assert [item.status for item in result.differences] == ["removed", "added"]


def test_different_room_identity_is_not_a_changed_pair() -> None:
    result = _diff((_fragment("left", "cpr_left", "Помещение 101 площадь 20 м2"),
                    _fragment("right", "cpr_right", "Помещение 102 площадь 30 м2")))
    assert [item.status for item in result.differences] == ["removed", "added"]


def test_candidate_budget_refuses_before_any_partial_output() -> None:
    left = tuple(_fragment("left", "cpr_left", f"Нагрузка {n} кВт", n) for n in range(318))
    right = tuple(_fragment("right", "cpr_right", f"Нагрузка {n + 500} кВт", n) for n in range(318))
    with pytest.raises(ValueError, match="stage_text_candidate_budget_exceeded"):
        _diff(left + right)


def test_cross_sheet_hint_is_only_recommendation() -> None:
    source = _fragment("left", "cpr_left", "Узел подключения кабеля")
    expected = _fragment("right", "cpr_right", "Иная спецификация")
    found = _fragment("right", "cpr_right_elsewhere", "Узел подключения кабеля")
    all_fragments = (source, expected, found)
    manifest = _manifest(all_fragments, ("cpr_left", "cpr_right", "cpr_right_elsewhere"))
    hints = find_cross_sheet_hints([SheetLink("cpr_left", "cpr_right")], all_fragments,
                                   manifest, frozenset())
    assert [(h.source_content_key, h.target_content_key) for h in hints] == [
        (source.content_key, found.content_key),
    ]
    raw = build_raw_differences([SheetLink("cpr_left", "cpr_right")],
                                (source, expected),
                                {"cpr_left": (100, 100), "cpr_right": (100, 100)},
                                _manifest((source, expected), ("cpr_left", "cpr_right")))
    assert [row.status for row in raw.differences] == ["removed", "added"]


def test_repeated_text_does_not_recommend_a_sheet() -> None:
    source = _fragment("left", "cpr_left", "Узел подключения кабеля")
    target_a = _fragment("right", "cpr_right_a", "Узел подключения кабеля")
    target_b = _fragment("right", "cpr_right_b", "Узел подключения кабеля")
    items = (source, target_a, target_b)
    assert find_cross_sheet_hints([SheetLink("cpr_left", "cpr_right_a")], items,
                                  _manifest(items, ("cpr_left", "cpr_right_a", "cpr_right_b")),
                                  frozenset()) == ()


def test_hint_manifest_mismatch_refuses() -> None:
    source = _fragment("left", "cpr_left", "Узел подключения кабеля")
    with pytest.raises(ValueError, match="fragment_manifest_mismatch"):
        find_cross_sheet_hints([], (), {"cpr_left": frozenset({source.content_key})},
                               frozenset())


def test_independent_sheet_groups_do_not_share_the_single_group_link_budget() -> None:
    links = [SheetLink(f"left_{n}", f"right_{n}") for n in range(40)]
    fragments = tuple(fragment for n in range(40) for fragment in (
        _fragment("left", f"left_{n}", "Нагрузка 10 кВт"),
        _fragment("right", f"right_{n}", "Нагрузка 20 кВт"),
    ))
    profiles = tuple(f.profile_id for f in fragments)
    result = build_grouped_raw_differences(
        links, fragments, {profile: (100, 100) for profile in profiles},
        _manifest(fragments, profiles),
    )
    assert len(result.differences) == 40
    assert all(row.status == "changed" for row in result.differences)
