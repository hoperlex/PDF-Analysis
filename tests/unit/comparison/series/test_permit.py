"""«Разрешение на внесение изменений» (`CMP-SERIES-01`): the table is read from a real page profile and the reconciliation
of the declared against the found changes is judged against the synthetic corpus' answer key."""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.series import permit


def words_and_lines(data: Any) -> tuple[list[permit.PermitWord], list[tuple[float, float, float]]]:
    words = [(w.x0, w.top, w.x1, w.bottom, w.text) for w in data.words]
    vertical = [(line.x0, line.top, line.bottom) for line in data.lines if abs(line.x1 - line.x0) <= 0.5]
    return words, vertical


def test_the_permit_table_of_the_fourth_version_is_read_as_the_key_declares_it(v4_first_page: Any, vs1_key: dict[str, Any]) -> None:
    words, vertical = words_and_lines(v4_first_page)
    rows = permit.parse_page(words, vertical, v4_first_page.height_pt)
    assert rows is not None
    declared = vs1_key["transitions"][2]["permit"]["declared"]
    assert [(r["izm"], r["sheet"], r["text"]) for r in rows] == [
        (int(entry["change_no"]), entry["sheet_no"], entry["text"]) for entry in declared]
    assert [r["refs"] for r in rows] == [[{"set": "main", "sheet": entry["sheet_no"]}] for entry in declared]


def test_a_page_without_the_table_has_no_rows() -> None:
    words = [(70.0, 40.0, 120.0, 50.0, "Общие"), (125.0, 40.0, 180.0, 50.0, "данные")]
    assert permit.parse_page(words, [(70.0, 30.0, 400.0)], 842.0) is None


@pytest.mark.parametrize(("text", "expected"), [
    ("4,5", [("main", "4"), ("main", "5")]),
    ("СО л. 2", [("СО", "2")]),
    ("2-4", [("main", "2"), ("main", "3"), ("main", "4")]),
    ("все", [("all", "*")]),
    ("", []),
    ("7а", [("main", "7а")]),
])
def test_sheet_references(text: str, expected: list[tuple[str, str]]) -> None:
    assert [(r["set"], r["sheet"]) for r in permit.parse_sheet_refs(text)] == expected


def test_a_reference_that_is_not_a_number_is_kept_as_unparsed() -> None:
    refs = permit.parse_sheet_refs("общие данные, 5")
    assert {"set": "unparsed", "sheet": "общие данные"} in refs and {"set": "main", "sheet": "5"} in refs


def stamp(number: str, name: str = "Лист", designation: str = "СИНТ-01-ЭМ") -> dict[str, str]:
    return {"sheet_number": number, "sheet_name": name, "designation": designation}


def found(key: str, page: int, status: str) -> dict[str, Any]:
    return {"key": key, "b_page": page, "status": status, "title": f"t{page}"}


def permit_of(*rows: tuple[int, str, str]) -> list[dict[str, Any]]:
    return [{"page": 1, "rows": [
        {"izm": i, "sheet": s, "text": t, "refs": permit.parse_sheet_refs(s)} for i, s, t in rows]}]


def test_the_reconciliation_names_the_four_classes_of_the_key(vs1_key: dict[str, Any]) -> None:
    """V3 -> V4: sheet 5 declared and found, sheet 7 declared and not found, sheet 4 declared on a scan (needs a review),
    sheet 3 changed and not declared."""
    key = vs1_key["transitions"][2]["permit"]
    permits = permit_of(*[(int(e["change_no"]), e["sheet_no"], e["text"]) for e in key["declared"]])
    pairs = {  # the statuses the engine gives (the key's own expected statuses)
        "E01": (1, "different"), "E02": (2, "same"), "E03": (3, "different"), "E04": (4, "needs_review"),
        "E05": (5, "different"), "E07": (7, "same"),
    }
    stamps = {page: stamp(str(page)) for _id, (page, _s) in pairs.items()}
    permits[0]["page"] = 1  # the permit table stands on sheet 1 (E01), the key's ``carrier_sheet``
    out = permit.reconcile(
        permits, 2, stamps, [found(name, page, status) for name, (page, status) in pairs.items()])
    assert out["izm_new"] == [3]
    assert [e["keys"] for e in out["declared_and_found"]] == [["E05"]]
    assert [e["keys"] for e in out["declared_no_diff"]] == [["E07"]]
    assert [e["keys"] for e in out["needs_review"]] == [["E04"]] and out["needs_review"][0]["reason"] == "sheet_needs_review"
    assert [e["keys"] for e in out["diff_not_declared"]] == [["E03"]]  # E01 differs too, but it carries the permit
    by_pair = permit.pair_permits(out)
    assert by_pair["E05"] == {"state": "declared_and_found", "items": [{"text": "Дополнена трасса кабельного лотка", "state": "declared_and_found"}]}
    assert by_pair["E07"]["state"] == "declared_no_diff" and by_pair["E04"]["state"] == "needs_review"
    assert by_pair["E03"] == {"state": "diff_not_declared", "items": []}
    assert "E02" not in by_pair


def test_a_changed_sheet_that_does_not_carry_the_permit_and_is_not_declared_is_reported() -> None:
    permits = permit_of((3, "5", "новое"))
    permits[0]["page"] = 1
    out = permit.reconcile(permits, 2, {1: stamp("1"), 2: stamp("2"), 5: stamp("5")},
                           [found("p1", 1, "different"), found("p2", 2, "different"), found("p5", 5, "different")])
    assert [e["keys"] for e in out["diff_not_declared"]] == [["p2"]]  # sheet 1 carries the permit


def test_only_changes_above_the_older_version_last_izm_are_declared() -> None:
    permits = permit_of((1, "2", "старое"), (3, "5", "новое"))
    permits[0]["page"] = 9
    out = permit.reconcile(permits, 2, {2: stamp("2"), 5: stamp("5")}, [found("p2", 2, "different"), found("p5", 5, "different")])
    assert [e["keys"] for e in out["declared_and_found"]] == [["p5"]]
    assert [e["keys"] for e in out["diff_not_declared"]] == [["p2"]]


def test_a_repeated_sheet_number_and_a_missing_sheet_need_a_review_not_a_class() -> None:
    permits = permit_of((3, "5", "дубль"), (3, "9", "нет такого"))
    out = permit.reconcile(
        permits, 2, {5: stamp("5"), 8: stamp("5")}, [found("a", 5, "same"), found("b", 8, "different")])
    reasons = {e["ref"]: e["reason"] for e in out["needs_review"]}
    assert reasons == {"л.5": "duplicate_sheet_number", "л.9": "sheet_not_in_version"}
    assert not out["declared_and_found"] and not out["declared_no_diff"]
    assert sorted(permit.pair_permits(out)) == ["a", "b"]  # the missing sheet names no pair


def test_a_main_number_that_only_the_specification_set_has_means_that_sheet() -> None:
    permits = permit_of((3, "7", "сечение"))
    permits[0]["page"] = 9
    out = permit.reconcile(permits, 2, {6: stamp("7", "Спецификация оборудования")}, [found("spec", 6, "same")])
    assert [e["keys"] for e in out["declared_no_diff"]] == [["spec"]]
    # but not when the number is ambiguous in the specification set, and never the other way round
    out = permit.reconcile(permits, 2, {6: stamp("7", "Спецификация А"), 7: stamp("7", "Спецификация Б")},
                           [found("a", 6, "same"), found("b", 7, "same")])
    assert [e["reason"] for e in out["needs_review"]] == ["sheet_not_in_version"]
    out = permit.reconcile(permit_of((3, "СО л. 7", "x")), 2, {6: stamp("7")}, [found("main7", 6, "same")])
    assert [e["reason"] for e in out["needs_review"]] == ["sheet_not_in_version"]


def test_all_sheets_declared_leaves_no_difference_undeclared() -> None:
    out = permit.reconcile(permit_of((3, "все", "везде")), 2, {1: stamp("1")}, [found("p1", 1, "different")])
    assert out["all_sheets_declared"] is True and out["diff_not_declared"] == []


def test_the_specification_set_is_not_the_main_set() -> None:
    """«4» and «СО л. 4» are different sheets (``permit.py:11``)."""
    permits = permit_of((3, "СО л. 1", "спец"))
    stamps = {1: stamp("1"), 2: stamp("1", "Спецификация оборудования")}
    out = permit.reconcile(permits, 2, stamps, [found("main1", 1, "same"), found("so1", 2, "different")])
    assert [e["keys"] for e in out["declared_and_found"]] == [["so1"]]
    assert permit.sheet_ref(stamp("1", "Спецификация"))["set"] == "СО"
    assert permit.sheet_ref(stamp("3", designation="СИНТ-01-ЭМ.СО"))["set"] == "СО"
    assert permit.sheet_ref({}) is None


def test_the_last_izm_of_a_version_is_read_from_its_permits_and_its_stamps() -> None:
    assert permit.izm_of([{"izm": 3}, {"izm": 1}], ["2", None, "Изм.4"]) == 4
    assert permit.izm_of([], []) == 0
