"""Synthetic sheets for the tests of the AI description of sheet changes (`CMP-VC-AISHEET-01`).

Plain code, no pytest. A test builds a pair of pages by hand -- a table with ruling lines, a place with a changed label, a shift, the
engine's service notes -- and the engine's stored result for them, so that every candidate, every tier and every refusal can be checked
against a sheet whose truth is in the file. The integration tests load this file by path.

* :func:`page` -- a ``PageProfileData`` with the words and ruling lines given;
* :func:`table_pages` -- page A and page B of a sheet with a table of three rows (``Лк-1``, ``Лк-2``, ``Лк-3``): in B the quantity of
  ``Лк-1`` is 3 instead of 2, and a place near (600, 400) where the label ``Лк-1`` became ``Лк-3``, a shift, a service note, a revision
  tag, a change of spaces and a noise difference;
* :class:`FakeMaterial` -- the :class:`SheetMaterial` of a test: the pages as given and PNG pictures it draws itself.
"""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from PIL import Image

from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow, StampFields, VectorLine, Word

PAGE_W, PAGE_H = 842.0, 595.0


def png(width: int = 120, height: int = 80, colour: tuple[int, int, int] = (200, 200, 200), *, seed: int = 0) -> bytes:
    """A small PNG, the same for the same arguments (no metadata, a pinned level)."""
    image = Image.new("RGB", (max(1, width), max(1, height)), colour)
    if seed:
        image.putpixel((0, 0), (seed % 256, (seed // 256) % 256, 7))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=6, optimize=False)
    return buffer.getvalue()


def row_of(profile_id: str, version: str, number: int) -> PageProfileRow:
    return PageProfileRow(
        page_profile_id=profile_id, version_uid=version, page_number=number, content_key="c" * 64, algo_version="cmp-profile/3",
        status="ready", reason=None, summary={"tiles": {}}, profile_blob_id=None, preview_blob_id=None, thumbnail_blob_id=None,
        created_at=datetime(2026, 10, 29, tzinfo=timezone.utc),
    )


def page(
    profile_id: str, version: str, number: int, words: Sequence[tuple[float, float, float, float, str]],
    lines: Sequence[tuple[float, float, float, float]] = (), *, revision: str | None = None, sheet_number: str | None = "7",
    title: str | None = "План этажа",
) -> PageProfileData:
    return PageProfileData(
        row=row_of(profile_id, version, number), width_pt=PAGE_W, height_pt=PAGE_H, rotation=0, has_text_layer=True, scan=False,
        content_merkle="m" * 64, words=tuple(Word(*w) for w in words),
        lines=tuple(VectorLine(x0, top, x1, bottom, 0.5, None) for x0, top, x1, bottom in lines),
        stamp=StampFields(designation="ЭМ-12", sheet_number=sheet_number, sheet_title=title, revision_number=revision),
    )


def _table_lines() -> list[tuple[float, float, float, float]]:
    ys = (100.0, 120.0, 140.0, 160.0, 180.0)
    lines = [(50.0, y, 360.0, y) for y in ys]
    lines += [(x, 100.0, x, 180.0) for x in (50.0, 110.0, 300.0, 360.0)]
    return lines


def _table_words(qty_first: str) -> list[tuple[float, float, float, float, str]]:
    return [
        (55, 105, 80, 115, "Поз."), (115, 105, 200, 115, "Наименование"), (305, 105, 330, 115, "Кол."),
        (55, 125, 85, 135, "Лк-1"), (115, 125, 200, 135, "Люк 600х600"), (310, 125, 320, 135, qty_first),
        (55, 145, 85, 155, "Лк-2"), (115, 145, 200, 155, "Люк 800х800"), (310, 145, 320, 155, "4"),
        (55, 165, 85, 175, "Лк-3"), (115, 165, 200, 175, "Люк 400х400"), (310, 165, 320, 175, "1"),
    ]


def table_pages(a_id: str, b_id: str, version_a: str, version_b: str) -> tuple[PageProfileData, PageProfileData]:
    """Page A and page B of the sheet described in the module note."""
    a_words = _table_words("2") + [(600, 400, 630, 410, "Лк-1"), (580, 380, 640, 392, "Помещение"), (100, 450, 160, 470, "Щит")]
    b_words = _table_words("3") + [(600, 400, 630, 410, "Лк-3"), (580, 380, 640, 392, "Помещение"), (100, 450, 160, 470, "Щит")]
    return (
        page(a_id, version_a, 1, a_words, _table_lines(), revision="2"),
        page(b_id, version_b, 1, b_words, _table_lines(), revision="3"),
    )


def box(x0: float, y0: float, x1: float, y1: float) -> dict[str, float]:
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def table_result() -> dict[str, Any]:
    """The engine's stored result for :func:`table_pages` (identity registration)."""
    return {
        "format": 1, "canvas": {"width_pt": PAGE_W, "height_pt": PAGE_H},
        "how_compared": {"algo_version": "cmp-engine/2", "dpi": 100, "tolerance_pt": 0.5, "transform": [1, 0, 0, 1, 0, 0]},
        "text_changes": [
            {"kind": "changed", "before": "2", "after": "3", "box": box(310, 125, 320, 135)},
            {"kind": "changed", "before": "Лк-1", "after": "Лк-3", "box": box(600, 400, 630, 410)},
            {"kind": "added", "after": "3.1", "box": box(700, 20, 720, 30)},
            {"kind": "changed_spaces", "before": "Помещение ", "after": "Помещение", "box": box(580, 380, 640, 392)},
        ],
        "differences": [
            {"region_class": "graphic_changed", "layer": "main", "box": box(595, 395, 640, 415)},
            {"region_class": "shifted", "layer": "moved", "box": box(100, 450, 160, 470)},
            {"region_class": "graphic_changed", "layer": "noise", "box": box(10, 10, 14, 14)},
        ],
        "service_notes": [{"kind": "stamp", "change": "changed", "zone": "stamp", "field": "date", "before": "01.01", "after": "02.01"}],
        "aligned_blocks": [],
        "mask": None,
    }


class FakeMaterial:
    """The material of a test. ``crops`` records what was asked; a profile in ``no_picture`` has no pictures."""

    def __init__(self, pages: Mapping[str, PageProfileData], *, hits: Sequence[dict[str, Any]] = (), no_picture: Sequence[str] = ()) -> None:
        self.pages = dict(pages)
        self.hits = list(hits)
        self.no_picture = set(no_picture)
        self.crops: list[tuple[str, tuple[float, ...], int]] = []
        self.overviews: list[str] = []
        self.mark_requests: list[tuple[str, ...]] = []

    def page(self, page_profile_id: str) -> PageProfileData:
        return self.pages[page_profile_id]

    def overview(self, page_profile_id: str) -> bytes | None:
        self.overviews.append(page_profile_id)
        return None if page_profile_id in self.no_picture else png(280, 198, (240, 240, 240), seed=11)

    def crop(self, page_profile_id: str, box: Sequence[float], *, long_side_px: int) -> bytes | None:
        self.crops.append((page_profile_id, tuple(round(float(v), 1) for v in box), long_side_px))
        if page_profile_id in self.no_picture:
            return None
        width, height = max(8, int(box[2] - box[0])), max(8, int(box[3] - box[1]))
        scale = min(1.0, long_side_px / max(width, height))
        return png(max(8, int(width * scale)), max(8, int(height * scale)), seed=int(box[0]) + int(box[1]) * 7)

    def find_marks(self, versions: Mapping[str, str], marks: Sequence[str], *, skip_pages: Mapping[str, int | None], limit: int) -> list[Any]:
        from auditmanager.comparison.ai_sheets.material import MarkHit

        self.mark_requests.append(tuple(marks))
        out = []
        for number, hit in enumerate(self.hits, 1):
            if hit["mark"] in marks:
                out.append(MarkHit(**{**hit, "id": hit.get("id", f"X{number}")}))
        return out[: limit * max(1, len(marks))]
