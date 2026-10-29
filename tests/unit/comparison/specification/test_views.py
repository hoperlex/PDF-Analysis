"""The contract-shaped dictionaries of positions and changes (`CMP-VC-SPEC-01`): they validate against the generated models, a
value longer than the contract's bound is cut visibly, and an empty optional value is omitted."""

from __future__ import annotations

from auditmanager.api.schemas import models
from auditmanager.comparison.specification import diff, table, views

REF = {"version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "page_number": 3, "page_profile_id": "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"}


def _items(*rows: dict[str, str]) -> list[dict]:
    parsed = [{"cells": dict(r), "bbox": [0, 0, 1, 1], "centered": False, "bold": False} for r in rows]
    return table.assemble([{"page": 3, "rows": parsed}])["items"]


def test_a_position_omits_what_is_empty_and_keeps_what_the_sheet_says() -> None:
    item = _items({"pos": "3", "mark": "АВ-63", "name": "Выключатель  автоматический", "quantity": "2,0"})[0]
    position = views.position_dict(item, page_ref=REF)
    assert position == {"name": "Выключатель автоматический", "pos": "3", "mark": "АВ-63", "quantity": "2,0", "page": REF}
    models.ComparisonSpecPosition.model_validate(position)


def test_a_value_longer_than_the_contract_bound_is_cut_with_an_ellipsis_and_still_validates() -> None:
    item = _items({"pos": "1", "mark": "М" * 500, "name": "Н" * 900, "quantity": "1", "note": "П" * 900})[0]
    position = views.position_dict(item)
    assert len(position["name"]) == 400 and position["name"].endswith("…") and len(position["mark"]) == 200 and len(position["note"]) == 400
    models.ComparisonSpecPosition.model_validate(position)


def test_a_sub_row_names_its_parent_and_an_ambiguous_row_says_so() -> None:
    items = _items({"mark": "ВВГнг", "name": "Кабель"}, {"name": "3х1.5", "quantity": "100"})
    items[0]["ambiguous"] = True
    position = views.position_dict(items[0])
    assert position["parent"] == "Кабель" and position["ambiguous"] is True
    models.ComparisonSpecPosition.model_validate(position)


def test_a_page_view_validates_and_counts_the_ambiguous_rows() -> None:
    items = _items({"pos": "1", "mark": "М-1", "name": "Щит", "quantity": "1"}, {"pos": "2", "mark": "М-2", "name": "Кабель", "quantity": "5"})
    items[1]["ambiguous"] = True
    view = views.page_view("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV", is_specification=True, items=items, refs={3: REF})
    models.ComparisonSpecPage.model_validate(view)
    assert view["ambiguous_rows"] == 1 and view["spec_version"] == table.SPEC_VERSION and len(view["positions"]) == 2


def test_a_pair_view_validates_with_its_totals_and_both_sides_of_a_change() -> None:
    a = _items({"pos": "1", "mark": "М-1", "name": "Щит", "quantity": "1"}, {"pos": "2", "mark": "М-2", "name": "Кабель", "quantity": "5"})
    b = _items({"pos": "1", "mark": "М-1", "name": "Щит", "quantity": "2"}, {"pos": "3", "mark": "М-3", "name": "Автомат", "quantity": "5"})
    changes = diff.compare(a, b)["changes"]
    view = views.pair_view("ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV", is_specification=True, changes=changes, refs={"a": {3: REF}, "b": {3: REF}})
    models.ComparisonSheetPairSpecPositions.model_validate(view)
    assert view["totals"] == {"changed": 1, "removed": 1, "added": 1, "unclear": 0, "renumbered": 0, "moved": 0}
    changed = view["changes"][0]
    assert changed["fields"] == [{"field": "quantity", "was": "1", "now": "2"}] and "old" in changed and "new" in changed
