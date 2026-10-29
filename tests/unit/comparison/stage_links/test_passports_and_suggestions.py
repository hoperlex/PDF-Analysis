"""Stage sheet hints never convert an uncertain stamp into a canonical link."""

from __future__ import annotations

from auditmanager.comparison.stage_links.passports import SheetPassport, from_stamp
from auditmanager.comparison.stage_links.suggestions import suggest_sheets


def page(profile: str, side: str, number: int, **fields: str) -> SheetPassport:
    return SheetPassport(profile, f"ver_{profile}", number, side, **fields)


def test_passport_reads_only_explicit_stamp_tokens() -> None:
    parsed = from_stamp(
        profile_id="cpr_left", version_uid="ver_left", page_number=7,
        side="left", sheet_title="План 2-го этажа, корпус 4",
        sheet_number=" АР-07 ",
    )
    assert (parsed.sheet_type, parsed.building, parsed.floor, parsed.level,
            parsed.sheet_number) == ("план", "4", "2", None, "ар-07")
    roof = from_stamp(
        profile_id="cpr_roof", version_uid="ver_roof", page_number=8,
        side="right", sheet_title="План кровли корпус 4", sheet_number=None,
    )
    assert roof.floor == "кровля" and roof.sheet_type == "план"
    unknown = from_stamp(
        profile_id="cpr_unknown", version_uid="ver_unknown", page_number=1,
        side="right", sheet_title="Общие данные", sheet_number=None,
    )
    assert (unknown.sheet_type, unknown.building, unknown.floor,
            unknown.level, unknown.sheet_number) == (None,) * 5


def test_unique_semantic_match_is_high_and_ambiguous_one_is_review() -> None:
    left = (page("cpr_a", "left", 1, sheet_type="план", building="4", floor="2"),)
    right = (page("cpr_b", "right", 1, sheet_type="план", building="4", floor="2"),)
    suggestions = suggest_sheets(left, right)
    assert [(item.score, item.confidence) for item in suggestions] == [(11, "high")]
    assert suggestions[0].reasons == ("building", "floor", "sheet_type", "page_order")
    duplicate = right + (page("cpr_c", "right", 2, sheet_type="план", building="4", floor="2"),)
    assert [item.confidence for item in suggest_sheets(left, duplicate)] == ["review", "review"]


def test_conflicting_building_floor_or_type_cannot_be_overruled_by_order() -> None:
    left = (page(
        "cpr_left", "left", 1, sheet_type="план", building="4", floor="2",
        sheet_number="7",
    ),)
    for field, changed in (("building", "5"), ("floor", "3"), ("sheet_type", "разрез")):
        right = (page(
            "cpr_right", "right", 1,
            **({"sheet_type": "план", "building": "4", "floor": "2", "sheet_number": "7"}
               | {field: changed}),
        ),)
        assert suggest_sheets(left, right) == ()


def test_weak_match_remains_review_and_many_to_many_is_only_a_hint() -> None:
    left = (
        page("cpr_a", "left", 1, sheet_type="схема", sheet_number="5"),
        page("cpr_b", "left", 2, sheet_type="схема", sheet_number="5"),
    )
    right = (page("cpr_c", "right", 1, sheet_type="схема", sheet_number="5"),)
    suggestions = suggest_sheets(left, right)
    assert len(suggestions) == 2
    assert {item.left_profile_id for item in suggestions} == {"cpr_a", "cpr_b"}
    assert all(item.confidence == "review" for item in suggestions)


def test_candidate_list_keeps_the_five_best_per_left_in_stable_order() -> None:
    left = (page("cpr_left", "left", 1, sheet_type="схема"),)
    right = tuple(
        page(f"cpr_{number:02d}", "right", number + 2, sheet_type="схема")
        for number in range(8)
    )
    hints = suggest_sheets(left, right)
    assert len(hints) == 5
    assert [hint.right_profile_id for hint in hints] == [f"cpr_{number:02d}" for number in range(5)]
    assert all(hint.confidence == "review" for hint in hints)
