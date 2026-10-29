"""The rows of a drawing's table, found by its ruling lines (`CMP-VC-AISHEET-01`).

A port of the original's ``sheet_changes/tables.py`` (`23f379fd`, lines 1-186) with the page profile's vector lines and words in place of
PyMuPDF drawings: a row is the band between the nearest horizontal rulings that pass through the column of a pointer (in CAD tables the
row separators are often cut by column, so a line "across the whole width" cannot be looked for); its width is the chain of the segments
of those rulings; its cells are the vertical rulings inside the band. The header is the nearest band above in which header words
("Поз.", "Наименование", "Кол." ...) stand. There is no general table parser.

Coordinates are points of the displayed page, as the profile's words are. A *word* here is any sequence ``(x0, top, x1, bottom, text)``.
Pure: no database, no PDF library.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Final

__all__ = [
    "HEADER_WORDS",
    "Rulings",
    "header_for",
    "lines_text",
    "row_at",
    "row_key",
    "rows_below",
]

ROW_MAX_PT: Final[float] = 420.0  # above this it is not a table row but an area of the sheet (tables.py:18)
CHAIN_GAP_PT: Final[float] = 3.0  # a gap between the segments of one ruling (tables.py:19)
SAME_Y_PT: Final[float] = 0.8  # tables.py:20
HEADER_WORDS: Final = re.compile(
    r"^(поз|обозначен|наименован|кол|марка|тип|примечан|площад|ед\.?|масса|№|номер|код|состав|схема|данные|материал)",
    re.IGNORECASE,
)  # tables.py:21-22
MAX_ROWS: Final[int] = 40  # tables.py:23
_MARK: Final = re.compile(r"^[A-Za-zА-Яа-яЁё]{1,4}[-.]?[0-9][0-9A-Za-zА-Яа-яЁё*/.\-]*$")  # tables.py:177


class Rulings:
    """The horizontal and vertical segments of a page in the displayed system (``tables.py:26-76``)."""

    def __init__(self, lines: Sequence[Any]) -> None:
        self.h: list[tuple[float, float, float]] = []  # (x0, x1, y)
        self.v: list[tuple[float, float, float]] = []  # (x, y0, y1)
        for line in lines:
            self._add(float(line[0]), float(line[1]), float(line[2]), float(line[3]))

    def _add(self, x0: float, y0: float, x1: float, y1: float) -> None:
        if abs(y0 - y1) < 0.6 and abs(x1 - x0) > 1.5:
            self.h.append((min(x0, x1), max(x0, x1), (y0 + y1) / 2))
        elif abs(x0 - x1) < 0.6 and abs(y1 - y0) > 1.5:
            self.v.append(((x0 + x1) / 2, min(y0, y1), max(y0, y1)))

    def h_through(self, x: float) -> list[float]:
        return sorted({round(y, 1) for a, b, y in self.h if a - 0.5 <= x <= b + 0.5})

    def chain(self, y: float, x: float) -> tuple[float, float] | None:
        """The segment of the ruling at height ``y`` that holds ``x``, with the cut by column joined (``tables.py:60-72``)."""
        segments = sorted((a, b) for a, b, yy in self.h if abs(yy - y) <= SAME_Y_PT)
        merged: list[list[float]] = []
        for a, b in segments:
            if merged and a <= merged[-1][1] + CHAIN_GAP_PT:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        for a, b in merged:
            if a - 0.5 <= x <= b + 0.5:
                return a, b
        return None

    def v_in(self, x0: float, x1: float, y0: float, y1: float) -> list[float]:
        mid = (y0 + y1) / 2
        return sorted({round(x, 1) for x, a, b in self.v if x0 + 1 < x < x1 - 1 and a <= mid <= b})


def _band(rulings: Rulings, x: float, y: float) -> tuple[float, float] | None:
    ys = rulings.h_through(x)
    top = max((v for v in ys if v < y - 0.5), default=None)
    bottom = min((v for v in ys if v > y + 0.5), default=None)
    if top is None or bottom is None or bottom - top > ROW_MAX_PT:
        return None
    return top, bottom


def lines_text(words: Sequence[Sequence[Any]]) -> str:
    """The words in reading order, one text line per visual line, joined with « / » (``tables.py:88-96``)."""
    rows: list[list[Sequence[Any]]] = []
    for w in sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        cy = (w[1] + w[3]) / 2
        if rows and abs(((rows[-1][0][1] + rows[-1][0][3]) / 2) - cy) <= 2.5:
            rows[-1].append(w)
        else:
            rows.append([w])
    return " / ".join(" ".join(str(w[4]) for w in sorted(r, key=lambda w: w[0])) for r in rows)


def row_at(rulings: Rulings, words: Sequence[Sequence[Any]], box: Sequence[float]) -> dict[str, Any] | None:
    """The table row ``box`` falls in; ``None`` when it is not a table (``tables.py:99-113``)."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    band = _band(rulings, cx, cy)
    if not band:
        return None
    top, bottom = band
    extents = [e for e in (rulings.chain(top, cx), rulings.chain(bottom, cx)) if e]
    if not extents:
        return None
    x0, x1 = min(e[0] for e in extents), max(e[1] for e in extents)
    if x1 - x0 < 30:
        return None
    return _row(rulings, words, x0, x1, top, bottom)


def _row(rulings: Rulings, words: Sequence[Sequence[Any]], x0: float, x1: float, top: float, bottom: float) -> dict[str, Any]:
    xs = [x0, *rulings.v_in(x0, x1, top, bottom), x1]
    inside = [w for w in words if x0 <= (w[0] + w[2]) / 2 <= x1 and top <= (w[1] + w[3]) / 2 <= bottom]
    cells = []
    for a, b in zip(xs, xs[1:]):
        cell_words = [w for w in inside if a <= (w[0] + w[2]) / 2 < b]
        if cell_words:
            cells.append({"x": [round(a, 1), round(b, 1)], "text": lines_text(cell_words)})
    return {
        "box": [round(x0, 1), round(top, 1), round(x1, 1), round(bottom, 1)], "cells": cells,
        "text": " ¦ ".join(c["text"] for c in cells), "graphic_cell": False,
    }


def header_for(rulings: Rulings, words: Sequence[Sequence[Any]], row: dict[str, Any]) -> dict[str, Any] | None:
    """The nearest band above the row with header words, not farther than twenty bands (``tables.py:128-143``)."""
    x0, top, x1, _ = row["box"]
    cx = (row["cells"][0]["x"][0] + row["cells"][0]["x"][1]) / 2 if row["cells"] else (x0 + x1) / 2
    y = top
    for _ in range(20):
        band = _band(rulings, cx, y - 1.0)
        if not band:
            return None
        header = _row(rulings, words, x0, x1, band[0], band[1])
        first = [str(w[4]) for w in words if x0 <= (w[0] + w[2]) / 2 <= x1 and band[0] <= (w[1] + w[3]) / 2 <= band[1]]
        kinds = {m.group(1).lower() for t in first if len(t) <= 12 and (m := HEADER_WORDS.match(t))}
        if len(kinds) >= 2 and len(first) <= 30:
            return header
        y = band[0]
    return None


def rows_below(
    rulings: Rulings, words: Sequence[Sequence[Any]], header: dict[str, Any], key_x: float, x0: float, x1: float,
) -> list[dict[str, Any]]:
    """Every row of the table under its header, by the key column -- for a small table whole (``tables.py:146-174``)."""
    out: list[dict[str, Any]] = []
    y = header["box"][3]
    for _ in range(MAX_ROWS):
        band = _band(rulings, key_x, y + 1.0)
        if not band:
            break
        # The end of the table: the lower ruling of the band is narrower than the table, or the band has no column separators.
        bottom = rulings.chain(band[1], key_x)
        if not bottom or (bottom[1] - bottom[0]) < 0.6 * (x1 - x0):
            break
        heights = sorted(r["box"][3] - r["box"][1] for r in out)
        if heights and band[1] - band[0] > max(3 * heights[len(heights) // 2], 80):
            break  # a band far taller than the rows is no longer the table
        if not rulings.v_in(x0, x1, band[0], band[1]):
            if band[1] - band[0] <= 25:  # a section row («Лючки металлические внутренние»)
                y = band[1]
                continue
            break
        row = _row(rulings, words, x0, x1, band[0], band[1])
        if not row["cells"]:
            if band[1] - band[0] > 60:
                break
        else:
            out.append(row)
        y = band[1]
    return out


def row_key(row: dict[str, Any]) -> str:
    """The key of a row for the preliminary pairing: the first short cell that is a designation (``tables.py:180-186``)."""
    for cell in row["cells"][:3]:
        text = cell["text"].split(" / ")[0].strip()
        if text and len(text) <= 18 and (_MARK.match(text) or re.match(r"^\d+(\.\d+)*\*?$", text)):
            return text
    return ""
