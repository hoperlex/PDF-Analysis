"""The order-independent comparison of two whole specifications that passed the check (`CMP-VC-SPEC-01`, part B).

Ports ``specification_compare.compare`` of the original (PDF-proverka at ``23f379fd``): identical records cancel, an unambiguous
identity pairs the rest, what stays ambiguous is reported ``unclear`` and never guessed, and an addition or a removal is published only
from a complete comparison.
"""

from __future__ import annotations

import random

from auditmanager.api.schemas import models
from auditmanager.comparison.specification import views, whole


def _row(pos: str, name: str, mark: str = "", qty: str = "1", *, code: str = "", section: str = "", parent: str = "", unit: str = "",
         page: int = 1, line: int = 1, note: str = "") -> dict:
    return {
        "id": f"p{page}:{line}", "section": section, "parent": parent,
        "fields": {"pos": pos, "name": name, "mark": mark, "code": code, "supplier": "", "unit": unit, "quantity": qty, "mass": "", "note": note},
        "sources": [{"page": page, "sheet": str(page), "block_id": f"p{page}", "line_start": line, "line_end": line, "quote": name}],
    }


def _side(*rows: dict, complete: bool = True) -> dict:
    return {"complete": complete, "rows": list(rows) if complete else []}


BASE = [_row("1", "Щит освещения", "ЩО-1", "1", line=1), _row("2", "Выключатель 16 А", "АВ-16", "12", line=2),
        _row("3", "Выключатель 63 А", "АВ-63", "2", line=3), _row("4", "Кабель ВВГнг", "КБ-3", "320", line=4, unit="м"),
        _row("5", "Светильник", "СВ-36", "24", line=5)]


def _kinds(result: dict) -> list[tuple[str, str]]:
    return [(c["kind"], c["label"]) for c in whole.changes_of(result)]


def test_two_equal_specifications_have_no_change() -> None:
    result = whole.compare(_side(*BASE), _side(*BASE))
    assert whole.changes_of(result) == [] and result["counts"]["paired"] == 5 and result["counts"]["unchanged"] == 5


def test_the_answer_does_not_depend_on_the_order_of_the_rows_or_their_pages() -> None:
    new = [dict(BASE[0]), _row("3", "Выключатель 63 А", "АВ-63", "3", line=3), dict(BASE[1]), dict(BASE[3]), _row("7", "Светильник LED", "СД-40", "6", line=6)]
    straight = _kinds(whole.compare(_side(*BASE), _side(*new)))
    assert sorted(k for k, _ in straight) == ["added", "changed", "removed"]
    for seed in range(6):
        a, b = list(BASE), list(new)
        random.Random(seed).shuffle(a)
        random.Random(seed + 9).shuffle(b)
        # a row's page and line are where it was found, not what it is
        b = [{**r, "sources": [{**r["sources"][0], "page": 1 + (seed % 3), "line_start": 90 - i, "line_end": 90 - i}]} for i, r in enumerate(b)]
        assert sorted(_kinds(whole.compare(_side(*a), _side(*b)))) == sorted(straight)


def test_a_changed_quantity_is_was_now_and_a_page_move_is_no_change() -> None:
    new = [{**r, "sources": [{**r["sources"][0], "page": 4}]} for r in BASE]
    assert whole.changes_of(whole.compare(_side(*BASE), _side(*new))) == []
    new[2] = _row("3", "Выключатель 63 А", "АВ-63", "3", line=3, page=4)
    changes = whole.changes_of(whole.compare(_side(*BASE), _side(*new)))
    assert [(c["kind"], c["fields"]) for c in changes] == [("changed", {"quantity": ["2", "3"]})]
    assert changes[0]["a"]["quantity"] == "2" and changes[0]["b"]["quantity"] == "3" and "Количество: 2 → 3" in changes[0]["text"]


def test_a_quantity_is_compared_as_a_number() -> None:
    new = [_row(r["fields"]["pos"], r["fields"]["name"], r["fields"]["mark"], "12,0" if r["fields"]["quantity"] == "12" else r["fields"]["quantity"], unit=r["fields"]["unit"]) for r in BASE]
    assert whole.changes_of(whole.compare(_side(*BASE), _side(*new))) == []


def test_an_added_and_a_removed_position_are_published_from_a_complete_comparison_only() -> None:
    new = [r for r in BASE if r["fields"]["pos"] != "5"] + [_row("6", "Заземлитель стальной", "ЗУ-01", "4", line=9)]
    complete = whole.changes_of(whole.compare(_side(*BASE), _side(*new)))
    assert [c["kind"] for c in complete] == ["removed", "added"] and complete[0]["b"] is None and complete[1]["a"] is None
    incomplete = whole.compare(_side(*BASE), _side(complete=False))
    assert incomplete["complete"] is False and whole.changes_of(incomplete) == []  # five "removals" would be a lie
    assert whole.changes_of(whole.compare(_side(complete=False), _side(*BASE))) == []


def test_a_renumbered_position_and_a_moved_position_are_not_content_changes() -> None:
    renumbered = [dict(BASE[0]), _row("9", "Выключатель 16 А", "АВ-16", "12", line=2)] + BASE[2:]
    assert [(c["kind"], c["fields"]) for c in whole.changes_of(whole.compare(_side(*BASE), _side(*renumbered)))] == [("renumbered", {"pos": ["2", "9"]})]
    old = [_row("1", "Автомат", "АВ-1", "2", section="Щиты"), _row("2", "Кабель", "КБ-1", "5", section="Кабели")]
    new = [_row("1", "Автомат", "АВ-1", "2", section="Резерв"), _row("2", "Кабель", "КБ-1", "5", section="Кабели")]
    assert [c["kind"] for c in whole.changes_of(whole.compare(_side(*old), _side(*new)))] == ["moved"]


def test_rows_that_share_an_identity_are_unclear_and_the_nearest_quantity_does_not_decide() -> None:
    old = [_row("1", "Кабель силовой", qty="10", line=1), _row("2", "Кабель силовой", qty="20", line=2)]
    new = [_row("1", "Кабель силовой", qty="15", line=1), _row("2", "Кабель силовой", qty="25", line=2)]
    result = whole.compare(_side(*old), _side(*new))
    changes = whole.changes_of(result)
    assert [c["kind"] for c in changes] == ["unclear"] and len(result["unresolved"][0]["old_rows"]) == 2
    assert result["counts"]["paired"] == 0 and result["counts"]["added"] == 0 and result["counts"]["removed"] == 0


def test_identical_duplicates_cancel_keeping_the_multiplicity() -> None:
    old = [_row("1", "Клемма", "К-1", "1"), _row("2", "Клемма", "К-1", "1"), _row("3", "Клемма", "К-1", "1")]
    new = [_row("1", "Клемма", "К-1", "1"), _row("2", "Клемма", "К-1", "1")]
    assert [c["kind"] for c in whole.changes_of(whole.compare(_side(*old), _side(*new)))] == ["removed"]


def test_a_renamed_section_title_is_one_change_and_its_positions_are_compared_as_the_same_section() -> None:
    old = [_row(str(i), f"Позиция {i}", f"М-{i}", "1", section="Щит ЩУ-1") for i in range(1, 5)]
    new = [_row(str(i), f"Позиция {i}", f"М-{i}", "2" if i == 2 else "1", section="Щит ЩУ-1М") for i in range(1, 5)]
    changes = whole.changes_of(whole.compare(_side(*old), _side(*new)))
    assert sorted(c["kind"] for c in changes) == ["changed", "changed"]
    assert any("Заголовок группы изменён" in c["text"] for c in changes) and any(c["fields"] == {"quantity": ["1", "2"]} for c in changes)


def test_a_code_decides_before_a_name_and_two_codes_are_a_substitution_not_a_pair() -> None:
    old = [_row("1", "Автомат", code="A-100", qty="2")]
    new = [_row("1", "Автомат", code="B-200", qty="2")]
    kinds = [c["kind"] for c in whole.changes_of(whole.compare(_side(*old), _side(*new)))]
    assert kinds == ["unclear"]  # a different code is never "the same position with a new code" by the name alone


def test_the_changes_validate_against_the_contract_models() -> None:
    new = [dict(BASE[0]), _row("3", "Выключатель 63 А", "АВ-63", "3", line=3), dict(BASE[1]), _row("7", "Светильник LED", "СД-40", "6", line=6)]
    changes = whole.changes_of(whole.compare(_side(*BASE), _side(*new)))
    assert [c["id"] for c in changes] == [f"s{k}" for k in range(1, len(changes) + 1)]
    refs = {"a": {1: {"version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "page_number": 1}}, "b": {1: {"version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "page_number": 1}}}
    for change in changes:
        models.ComparisonSpecChange.model_validate(views.change_dict(change, refs=refs))
