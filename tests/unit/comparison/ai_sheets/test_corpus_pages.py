"""The candidates of two sheets of the synthetic corpus VS-1, read from its real PDFs (`CMP-VC-AISHEET-01`).

The pages are opened with ``pdfplumber`` (the library the page profile uses) and the engine's stored result is written from the
answer key ``fixtures/comparison/vs1/answer_key.json``, which the fixtures lane authored next to the content: no page profile, no
engine and no database take part. What this proves is that the port of the original's table and place logic reads a *real* drawing
-- ruling lines from vector edges, words in reading order -- and not only the hand-made pages of the other tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pdfplumber
import pytest

from auditmanager.comparison.ai_sheets.candidates import PageText, collect

CORPUS = Path(__file__).resolve().parents[4] / "fixtures" / "comparison" / "vs1"
IDENTITY = [1, 0, 0, 1, 0, 0]


def _page(name: str, number: int) -> tuple[PageText, float]:
    with pdfplumber.open(CORPUS / f"{name}.pdf") as pdf:
        page = pdf.pages[number - 1]
        words = [(w["x0"], w["top"], w["x1"], w["bottom"], w["text"]) for w in page.extract_words()]
        lines = [(e["x0"], e["top"], e["x1"], e["bottom"]) for e in page.edges]
        return PageText(words, lines, revision_number="1"), float(page.height)


def _sheet(sheet_id: str) -> dict[str, Any]:
    key = json.loads((CORPUS / "answer_key.json").read_text(encoding="utf-8"))
    return next(s for s in key["transitions"][0]["sheets"] if s["sheet_id"] == sheet_id)


def _result(sheet: dict[str, Any], height: float) -> dict[str, Any]:
    def box(bb: list[float]) -> dict[str, float]:
        x0, y0, x1, y1 = bb  # the key is in PDF points, origin at the lower left; the profile is origin top left
        return {"x": x0, "y": height - y1, "width": x1 - x0, "height": y1 - y0}

    content = [c for c in sheet["text_changes"] if c["zone"] == "content"]
    return {
        "format": 1, "canvas": {"width_pt": 1190.55, "height_pt": height}, "how_compared": {"transform": IDENTITY},
        "text_changes": [
            {"kind": "moved" if c["kind"] == "text_moved" else "changed", "before": c["before"], "after": c["after"],
             "box": box(c["bbox_before"])}
            for c in content
        ],
        "differences": [], "service_notes": [],
    }


def test_the_load_table_of_e03_is_found_by_its_ruling_lines_and_the_changed_cell_is_in_its_row() -> None:
    a, height = _page("v1", 3)
    b, _ = _page("v2", 3)
    collected = collect(_result(_sheet("E03"), height), a, b, IDENTITY)
    assert [c["kind"] for c in collected.candidates] == ["table"]
    table = collected.candidates[0]
    assert table["full"] is True and len(table["rows_a"]) == len(table["rows_b"]) == 6
    row_a = next(r for r in table["rows_a"] if r["key"] == "3")
    row_b = next(r for r in table["rows_b"] if r["key"] == "3")
    assert "3,0" in row_a["text"] and "3,6" in row_b["text"] and "3,0" not in row_b["text"]
    assert collected.ledger["T1"] == {"status": "candidate", "candidate": "O1"}
    others = [r for r in table["rows_a"] if r["key"] != "3"]
    assert all(r["text"] == next(x["text"] for x in table["rows_b"] if x["key"] == r["key"]) for r in others), "only row 3 differs"


def test_a_label_that_only_moved_on_e02_is_not_asked_about() -> None:
    a, height = _page("v1", 2)
    b, _ = _page("v2", 2)
    collected = collect(_result(_sheet("E02"), height), a, b, IDENTITY)
    assert collected.candidates == [], "a label moved with its text unchanged is not a construction change (rule 8 of the prompt)"
    assert collected.ledger["T1"]["reason"] == "label_move"
