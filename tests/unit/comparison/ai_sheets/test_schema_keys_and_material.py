"""The schema, the prompt pins, the content key and the stored-page material (`CMP-VC-AISHEET-01`)."""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from auditmanager.comparison.ai_sheets import schema as sc
from auditmanager.comparison.ai_sheets.material import MARK_MAX_COMMON, crop_from_tiles, find_marks_in
from auditmanager.comparison.ai_sheets.repository import content_key, prompt_version_of


def _fx() -> Any:
    name = "cmp_ai_sheets_fixtures"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "sheet_fixtures.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


fx = _fx()

#: Pinned so that an edit of the prompt or of the schema cannot go unnoticed: a new prompt is a new content key (nothing stored under
#: the old one is reused for it) and a new estimate. Change the text -> raise ``PROMPT_VERSION`` -> change these three lines.
PINNED_PROMPT_DIGEST = "77ea907c07c8fb32893a935fa2126ed1335d076e20d933489e08e7253a5d0940"
PINNED_SINGLE_DIGEST = "69f3966a6ee3c80e056c3b4c9469a0580c3dcce20f8caba3a20261974976d946"


def test_the_prompt_and_the_schema_are_pinned_to_their_version_name() -> None:
    assert (sc.PROMPT_VERSION, sc.PROMPT_DIGEST) == ("sheet-changes/2", PINNED_PROMPT_DIGEST)
    assert (sc.SINGLE_PROMPT_VERSION, sc.SINGLE_PROMPT_DIGEST) == ("sheet-single/2", PINNED_SINGLE_DIGEST)
    assert len(prompt_version_of(sc.PROMPT_VERSION, sc.PROMPT_DIGEST)) <= 64


def test_the_prompt_keeps_the_originals_rules_that_keep_the_answer_honest() -> None:
    text = sc.PROMPT_TEMPLATE
    assert text.count("{{BEGIN}}") == 1 and text.count("{{END}}") == 1
    for rule in ("«Было» берётся только из A, «стало» — только из B.", "Нечитаемое не угадывай", "Не объясняй причины",
                 "packet_id и part_id перепиши из задания дословно"):
        assert rule in text


def test_the_schema_requires_every_property_and_forbids_extras() -> None:
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"]), "every property required (a strict structural answer)"
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(sc.SHEET_CHANGES_SCHEMA)
    walk(sc.SINGLE_SCHEMA)


@pytest.mark.parametrize("answer,ok", [
    ({"sheet_kind": "a", "summary": "b", "objects": [], "marks": [], "limitation": ""}, True),
    ({"sheet_kind": "a", "summary": "b", "objects": [], "marks": []}, False),
    ({"sheet_kind": "a", "summary": "b", "objects": [], "marks": [], "limitation": "", "x": 1}, False),
    ({"sheet_kind": "a", "summary": 5, "objects": [], "marks": [], "limitation": ""}, False),
    ({"sheet_kind": "a", "summary": "b", "objects": [{"name": "n", "detail": "d"}] * 16, "marks": [], "limitation": ""}, False),
])
def test_the_small_validator_holds_the_single_schema(answer: Any, ok: bool) -> None:
    assert (sc.validate_answer(answer, sc.SINGLE_SCHEMA) == []) is ok


def test_an_enum_word_outside_the_schema_is_refused() -> None:
    answer = {"packet_id": "p", "part_id": "P1", "changes": [], "unresolved": [], "excluded": [
        {"candidate_ids": ["O1"], "reason": "because", "note": ""}], "context_requests": []}
    assert sc.validate_answer(answer, sc.SHEET_CHANGES_SCHEMA)


BASE = dict(project_uid="prj_1", kind="pair", subject_key="a" * 64, prompt_version="v", model="m")


def test_the_content_key_is_a_function_of_the_project_the_subject_the_prompt_and_the_model_only() -> None:
    key = content_key(**BASE)
    assert len(key) == 64 and key == content_key(**BASE)
    for name, other in (("project_uid", "prj_2"), ("kind", "single"), ("subject_key", "b" * 64), ("prompt_version", "w"), ("model", "n")):
        assert content_key(**{**BASE, name: other}) != key, name


# -- the stored pages ---------------------------------------------------------------------------------------------------------------


def _pyramid() -> tuple[dict[str, Any], Any, list[tuple[int, int, int]]]:
    """A page of 1000 x 800 pt with a pyramid of three levels (1000, 500 and 250 px wide) cut in tiles of 256 px."""
    levels = [
        {"level": 0, "width_px": 1000, "height_px": 800, "columns": 4, "rows": 4},
        {"level": 1, "width_px": 500, "height_px": 400, "columns": 2, "rows": 2},
        {"level": 2, "width_px": 250, "height_px": 200, "columns": 1, "rows": 1},
    ]
    asked: list[tuple[int, int, int]] = []

    def read(level: int, column: int, row: int) -> bytes:
        asked.append((level, column, row))
        image = Image.new("RGB", (256, 256), (level * 80, column * 60, row * 60))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    return {"tile_px": 256, "levels": levels}, read, asked


def test_a_crop_is_cut_from_the_finest_level_that_fits_the_picture() -> None:
    summary, read, asked = _pyramid()
    data = crop_from_tiles(summary, 1000, 800, read, [100, 100, 300, 250], long_side_px=1950)
    image = Image.open(io.BytesIO(data))
    assert image.size == (200, 150) and {a[0] for a in asked} == {0}, "level 0, one pixel to the point, never enlarged"
    asked.clear()
    small = crop_from_tiles(summary, 1000, 800, read, [100, 100, 300, 250], long_side_px=100)
    assert Image.open(io.BytesIO(small)).size[0] <= 100 and {a[0] for a in asked} == {1} and asked, "a coarser level, not a shrunk fine one"


def test_a_crop_reads_only_the_tiles_it_covers_and_a_page_without_a_pyramid_gives_none() -> None:
    summary, read, asked = _pyramid()
    crop_from_tiles(summary, 1000, 800, read, [10, 10, 100, 100], long_side_px=1950)
    assert asked == [(0, 0, 0)]
    assert crop_from_tiles({}, 1000, 800, read, [0, 0, 10, 10], long_side_px=100) is None
    assert crop_from_tiles(summary, 1000, 800, read, [2000, 2000, 2100, 2100], long_side_px=100) is None


class _Page:
    def __init__(self, number: int, words: list[tuple[float, float, float, float, str]]) -> None:
        self.row = type("R", (), {"page_number": number})()
        self.words = tuple(type("W", (), {"__getitem__": lambda s, i: s.t[i], "text": w[4], "t": w}) () for w in words)
        self.stamp = type("S", (), {"sheet_number": str(number), "sheet_title": "План"})()


def test_a_designation_is_looked_for_on_the_other_pages_of_both_versions_and_a_common_one_is_noise() -> None:
    def word(text: str, x: float = 10) -> tuple[float, float, float, float, str]:
        return (x, 10.0, x + 30, 20.0, text)

    def indexed(side_pages: dict[int, list[Any]]) -> dict[str, list[tuple[Any, Any]]]:
        from auditmanager.comparison.ai_sheets.candidates import norm_mark

        out: dict[str, list[tuple[Any, Any]]] = {}
        for number, words in side_pages.items():
            page = _Page(number, words)
            for w in page.words:
                out.setdefault(norm_mark(w.text), []).append((page, w))
        return out

    index = {
        "A": indexed({1: [word("Лк-1")], 2: [word("Лк-1"), word("ВВГ-1")]}),
        "B": indexed({1: [word("Лк-1")], 5: [word("Лк-1")]}),
    }
    hits = find_marks_in(index, ["Лк-1"], skip_pages={"A": 1, "B": 1}, limit=2)
    assert [(h["side"], h["page"]) for h in hits] == [("B", 5), ("A", 2)], "the sheets themselves are skipped; B first"
    noisy = {"B": indexed({n: [word("Щ-9")] for n in range(1, MARK_MAX_COMMON + 3)}), "A": {}}
    assert find_marks_in(noisy, ["Щ-9"], skip_pages={}, limit=2) == []
