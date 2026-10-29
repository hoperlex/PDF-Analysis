"""The candidates of a sheet from the engine's pointers and the two pages (`CMP-VC-AISHEET-01`; the port of ``collect.py``)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from auditmanager.comparison.ai_sheets import tables as tb
from auditmanager.comparison.ai_sheets.candidates import PageText, collect, pointers_of


def _fixtures() -> Any:
    name = "cmp_ai_sheets_fixtures"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "sheet_fixtures.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


fx = _fixtures()


def _collected(result: dict[str, Any] | None = None) -> Any:
    page_a, page_b = fx.table_pages("cpr_a", "cpr_b", "ver_a", "ver_b")
    texts = [PageText(p.words, p.lines, revision_number=p.stamp.revision_number) for p in (page_a, page_b)]
    return collect(result or fx.table_result(), texts[0], texts[1], [1, 0, 0, 1, 0, 0])


def test_the_rows_of_a_table_come_from_its_ruling_lines() -> None:
    page_a, _ = fx.table_pages("cpr_a", "cpr_b", "ver_a", "ver_b")
    rulings = tb.Rulings(page_a.lines)
    row = tb.row_at(rulings, page_a.words, [310, 125, 320, 135])
    assert row is not None and row["box"] == [50.0, 120.0, 360.0, 140.0]
    assert [c["text"] for c in row["cells"]] == ["Лк-1", "Люк 600х600", "2"]
    header = tb.header_for(rulings, page_a.words, row)
    assert header is not None and "Наименование" in header["text"]
    assert tb.row_key(row) == "Лк-1"
    rows = tb.rows_below(rulings, page_a.words, header, 80.0, 50.0, 360.0)
    assert [tb.row_key(r) for r in rows] == ["Лк-1", "Лк-2", "Лк-3"]


def test_a_band_with_no_header_is_not_a_table() -> None:
    page_a, _ = fx.table_pages("cpr_a", "cpr_b", "ver_a", "ver_b")
    rulings = tb.Rulings([(50.0, 100.0, 360.0, 100.0), (50.0, 140.0, 360.0, 140.0), (110.0, 100.0, 110.0, 140.0)])
    row = tb.row_at(rulings, [(55, 125, 85, 135, "Лк-1"), (115, 125, 200, 135, "Люк"), (310, 125, 320, 135, "2")], [310, 125, 320, 135])
    assert row is not None
    assert tb.header_for(rulings, page_a.words, row) is None


def test_the_table_the_place_and_the_shift_are_three_candidates_in_that_order() -> None:
    collected = _collected()
    assert [(c["id"], c["kind"]) for c in collected.candidates] == [("O1", "table"), ("O2", "place"), ("O3", "shift")]
    table = collected.candidates[0]
    assert table["full"] is True and [r["key"] for r in table["rows_a"]] == ["Лк-1", "Лк-2", "Лк-3"]
    assert table["pointers"] == ["T1"]
    assert table["pairs"] and {p["key"] for p in table["pairs"]} == {"Лк-1", "Лк-2", "Лк-3"}
    place = collected.candidates[1]
    assert place["pointers"] == ["T2", "D1"] or sorted(place["pointers"]) == ["D1", "T2"]
    assert place["labels_a"] == ["Лк-1"] and place["labels_b"] == ["Лк-3"]
    assert "Лк-1" in place["words_a"] and "Лк-3" in place["words_b"]
    shift = collected.candidates[2]
    assert shift["pointers"] == ["D2"] and shift["context_a"][0] < 100 < shift["context_a"][2]


def test_every_pointer_has_exactly_one_fate_and_the_excluded_have_their_reason() -> None:
    collected = _collected()
    assert set(collected.ledger) == set(collected.pointers) == {"T1", "T2", "T3", "T4", "D1", "D2", "D3", "S1"}
    assert collected.ledger["T3"] == {"status": "excluded", "reason": "revision_tag", "reason_text": collected.ledger["T3"]["reason_text"]}
    assert collected.ledger["T4"]["reason"] == "whitespace"
    assert collected.ledger["D3"]["reason"] == "engine_noise"
    assert collected.ledger["S1"]["reason"] == "service"
    assert collected.ledger["T1"] == {"status": "candidate", "candidate": "O1"}
    assert sum(collected.counts.values()) == len(collected.pointers)


def test_a_revision_tag_is_only_the_tag_of_the_current_change() -> None:
    result = fx.table_result()
    result["text_changes"][2]["after"] = "2.1"  # the tag of change 2, not of the current change (3)
    collected = _collected(result)
    assert collected.ledger["T3"]["status"] == "candidate"


def test_a_text_region_that_overlaps_a_text_change_is_linked_not_a_candidate() -> None:
    result = fx.table_result()
    result["differences"].append({"region_class": "text", "layer": "main", "box": fx.box(305, 120, 325, 140)})
    collected = _collected(result)
    assert collected.ledger["D4"]["status"] == "linked" and collected.ledger["D4"]["candidate"] == "O1"
    assert "D4" not in {p for c in collected.candidates for p in c["pointers"]}


def test_a_weak_pointer_inside_a_place_is_attached_to_it() -> None:
    result = fx.table_result()
    result["text_changes"].append({"kind": "moved", "before": "Лк-1", "after": "Лк-1", "box": fx.box(602, 402, 628, 408)})
    collected = _collected(result)
    assert collected.ledger["T5"] == {"status": "attached", "candidate": "O2"}


def test_a_moved_label_outside_every_place_is_excluded_not_asked() -> None:
    result = fx.table_result()
    result["text_changes"].append({"kind": "moved", "before": "Лк-9", "after": "Лк-9", "box": fx.box(300, 520, 330, 530)})
    assert _collected(result).ledger["T5"]["reason"] == "label_move"


def test_the_pointers_copy_the_engines_texts_and_never_rewrite_them() -> None:
    result = fx.table_result()
    pointers = pointers_of(result, [1, 0, 0, 1, 0, 0])
    by_id = {p["id"]: p for p in pointers}
    assert (by_id["T1"]["before"], by_id["T1"]["after"]) == ("2", "3")
    assert result == fx.table_result(), "the stored result is read, not changed"


def test_the_box_on_page_b_is_the_inverse_of_the_registration_matrix() -> None:
    result = fx.table_result()
    shifted = pointers_of(result, [1, 0, 0, 1, 10, 20])  # B -> A moves by (10, 20): a box of A is 10 left and 20 above on B
    by_id = {p["id"]: p for p in shifted}
    assert by_id["T1"]["bbox_b"] == pytest.approx([300.0, 105.0, 310.0, 115.0])
