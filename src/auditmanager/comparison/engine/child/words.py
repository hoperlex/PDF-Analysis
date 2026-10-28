"""Words of a page: comparison, warnings, release marks, the frame and the kind of a sheet (pure Python).

`CMP-ENGINE-01`. The words come from the page profile (``pdfplumber``: text, box in points in the frame of the page as
displayed). Ports of ``engine.py`` (``_compare_words``, ``_warning_lines``, ``_reading_order_words``), ``separation.py``
(``WARNING_PATTERNS``), ``stamp.py`` (``RELEASE_PATTERNS``, ``release_blocks``, ``detect_frame``, the zone of the title
block in ``parse``, ``classify_kind``). The line numbers in the docstrings are those of the original at ``23f379fd``.
A word is ``{"text", "pt": [x0, y0, x1, y1], "dir": None}``: the profile has no direction of a line, so the shape of
the box decides whether an inscription is turned (``textdiff._vertical``).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from . import settings

__all__ = [
    "DATE_RE",
    "MM",
    "RELEASE_PATTERNS",
    "WARNING_PATTERNS",
    "center",
    "classify_kind",
    "compare_words",
    "detect_frame",
    "in_rects",
    "make_words",
    "norm",
    "rect_through",
    "reading_order_words",
    "release_blocks",
    "stamp_zone",
    "warning_lines",
]

MM = 72.0 / 25.4

#: ``separation.py:38-45``: a warning is a short inscription (or a large one) that says one of these.
WARNING_PATTERNS = (
    re.compile(r"не\s*согласован", re.I),
    re.compile(r"строить\s*опасно", re.I),
    re.compile(r"аннулирован", re.I),
    re.compile(r"для\s*согласования", re.I),
    re.compile(r"не\s*для\s*строительства", re.I),
    re.compile(r"\bкопия\b", re.I),
)
#: ``stamp.py:26``: the usual marks «В производство работ».
RELEASE_PATTERNS = (re.compile(r"в\s*производств", re.I), re.compile(r"к\s*производств", re.I))
_DATE_FULL = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
#: ``service.py:255``: a date in a release mark.
DATE_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{2,4}\b")
_LABEL_ROW = {"изм.", "изм", "кол.уч.", "кол.уч", "кол. уч.", "лист", "№док.", "№ док.", "№док", "подп.", "подпись", "дата"}


def make_words(rows: Iterable[Sequence[Any]], matrix: Any = None) -> list[dict[str, Any]]:
    """Words ``{"text", "pt", "dir"}`` from profile rows ``[x0, top, x1, bottom, text]``.

    ``matrix`` (a 2 x 3 array, B to A) moves the box into the coordinates of A (``engine._rect_b_to_a``)."""
    out = []
    for row in rows:
        text = str(row[4]).strip()
        if not text:
            continue
        rect = [float(row[0]), float(row[1]), float(row[2]), float(row[3])]
        if matrix is not None:
            rect = rect_through(matrix, rect)
        out.append({"text": text, "pt": rect, "dir": None})
    return out


def apply_point(m: Any, x: float, y: float) -> tuple[float, float]:
    """A point through a 2 x 3 affine matrix (``engine._apply``)."""
    return m[0][0] * x + m[0][1] * y + m[0][2], m[1][0] * x + m[1][1] * y + m[1][2]


def rect_through(m: Any, r: Sequence[float]) -> list[float]:
    """The bounding box of a rectangle through an affine matrix (``engine._rect_b_to_a``)."""
    pts = [apply_point(m, x, y) for x, y in ((r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3]))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def center(r: Sequence[float]) -> tuple[float, float]:
    return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def in_rects(r: Sequence[float], rects: Sequence[Sequence[float]]) -> bool:
    """The centre of ``r`` lies in one of ``rects`` (``engine._in_rects``)."""
    cx, cy = center(r)
    return any(z[0] <= cx <= z[2] and z[1] <= cy <= z[3] for z in rects)


def reading_order_words(words: list[dict]) -> list[dict]:
    """Words of a zone in reading order, rows from top to bottom, left to right (``engine.py:133``)."""
    return sorted(words, key=lambda w: (round(center(w["pt"])[1] / 3.0), w["pt"][0]))


def compare_words(wa: list[dict], wb: list[dict], same_pt: float) -> dict[str, Any]:
    """Words of the main area of A and B (B already in the coordinates of A), ``engine.py:142-178``.

    * the same: the same text not farther than ``same_pt`` (the tolerance);
    * moved: the same text farther than that and not farther than ``WORD_MOVE_PT``;
    * only in A / only in B: the rest.

    The nearest pairs are chosen greedily by distance inside each text."""
    index_b: dict[str, list[int]] = defaultdict(list)
    for i, w in enumerate(wb):
        index_b[w["text"]].append(i)
    candidates: list[tuple[float, int, int]] = []
    for ia, w in enumerate(wa):
        cx, cy = center(w["pt"])
        for jb in index_b.get(w["text"], ()):
            bx, by = center(wb[jb]["pt"])
            d = math.hypot(bx - cx, by - cy)
            if d <= settings.WORD_MOVE_PT:
                candidates.append((d, ia, jb))
    candidates.sort()
    used_a: set[int] = set()
    used_b: set[int] = set()
    moved: list[dict] = []
    same = 0
    for d, ia, jb in candidates:
        if ia in used_a or jb in used_b:
            continue
        used_a.add(ia)
        used_b.add(jb)
        if d <= same_pt:
            same += 1
        else:
            moved.append({"text": wa[ia]["text"], "a_pt": wa[ia]["pt"], "b_in_a_pt": wb[jb]["pt"],
                          "shift_pt": round(d, 2), "dir": wa[ia].get("dir")})
    return {
        "only_a": [w for i, w in enumerate(wa) if i not in used_a],
        "only_b": [w for i, w in enumerate(wb) if i not in used_b],
        "moved": moved,
        "same": same,
    }


def warning_lines(words: list[dict]) -> list[dict[str, Any]]:
    """Warnings baked into the main stream: rows with «НЕ СОГЛАСОВАНО» and the like (``engine.py:111-134``).

    A warning is an inscription of its own: a row of one phrase (up to four words) or one set clearly larger than the
    body text. The word «копия» in the title of a sheet taken from a list is not a warning."""
    heights = sorted(w["pt"][3] - w["pt"][1] for w in words)
    median_h = heights[len(heights) // 2] if heights else 0.0
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (center(w["pt"])[1], w["pt"][0])):
        if rows and abs(center(rows[-1][0]["pt"])[1] - center(w["pt"])[1]) <= 3:
            rows[-1].append(w)
        else:
            rows.append([w])
    out: list[dict[str, Any]] = []
    for row in rows:
        text = " ".join(x["text"] for x in sorted(row, key=lambda x: x["pt"][0]))
        row_h = max(x["pt"][3] - x["pt"][1] for x in row)
        prominent = len(row) <= 4 or (median_h > 0 and row_h >= 1.5 * median_h)
        if prominent and any(p.search(text) for p in WARNING_PATTERNS):
            out.append({"text": text[:120], "bbox_pt": [min(x["pt"][0] for x in row), min(x["pt"][1] for x in row),
                                                       max(x["pt"][2] for x in row), max(x["pt"][3] for x in row)]})
    return out


# -- the title block, the release mark and the frame ---------------------------------------------

def _low(text: str) -> str:
    return (text or "").strip().lower()


def _union(rects: Iterable[Sequence[float]]) -> list[float] | None:
    rects = [list(r) for r in rects]
    if not rects:
        return None
    return [min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]


def _text_lines(words: list[dict], tol: float = 2.0) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (center(w["pt"])[1], w["pt"][0])):
        if rows and abs(center(rows[-1][0]["pt"])[1] - center(w["pt"])[1]) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w["pt"][0]) for r in rows]


def text_blocks(words: list[dict]) -> list[tuple[list[float], str]]:
    """Blocks of text built from words (the profile has no blocks as ``PyMuPDF`` returns them): rows by height, rows
    that follow one another with a gap of at most half a line and that overlap in x join into a block."""
    rows = _text_lines(words, tol=3.0)
    blocks: list[list[list[dict]]] = []
    for row in rows:
        box = _union(w["pt"] for w in row)
        height = max(1.0, box[3] - box[1])
        placed = False
        for block in reversed(blocks[-6:]):
            last = _union(w["pt"] for line in block for w in line)
            if box[1] - last[3] <= 0.6 * height and min(box[2], last[2]) - max(box[0], last[0]) > 0:
                block.append(row)
                placed = True
                break
        if not placed:
            blocks.append([row])
    out = []
    for block in blocks:
        members = [w for line in block for w in line]
        out.append((_union(w["pt"] for w in members) or [0, 0, 0, 0], " ".join(w["text"] for line in block for w in line)))
    return out


def release_blocks(words: list[dict]) -> list[dict[str, Any]]:
    """Release marks «В производство работ»: a block with the mark and the blocks next to it (``stamp.py:157-190``).

    The mark is usually split into several blocks (the heading, the position, the name with the date), so the blocks
    that lie within 12 mm above or below and overlap it horizontally join the heading."""
    items = text_blocks(words)
    out: list[dict[str, Any]] = []
    for bbox, text in items:
        if not any(p.search(text) for p in RELEASE_PATTERNS):
            continue
        cluster = [bbox]
        texts = [text]
        changed = True
        while changed:
            changed = False
            box = _union(cluster)
            assert box is not None
            for other, other_text in items:
                if other in cluster:
                    continue
                h_overlap = min(box[2], other[2]) - max(box[0], other[0]) > -10 * MM
                v_gap = max(other[1] - box[3], box[1] - other[3])
                if h_overlap and v_gap <= 12 * MM and (other[2] - other[0]) < 120 * MM:
                    cluster.append(other)
                    texts.append(other_text)
                    changed = True
        joined = " ".join(texts)
        dates = _DATE_FULL.findall(joined)
        out.append({"bbox": _union(cluster), "text": joined, "date": dates[-1] if dates else ""})
    return out


def detect_frame(page_w: float, page_h: float, segments: Iterable[Sequence[float]]) -> list[float] | None:
    """The frame of a GOST sheet by long lines near the edges: about 20 mm at the left, 5 mm at the others
    (``stamp.py:56-71``). ``segments`` are ``(x0, y0, x1, y1)`` boxes of the long lines."""
    segments = list(segments)

    def near(values: list[float], lo: float, hi: float) -> float | None:
        hits = [v for v in values if lo <= v <= hi]
        return min(hits, key=lambda v: abs(v - (lo + hi) / 2)) if hits else None

    verticals = [s[0] for s in segments if abs(s[0] - s[2]) < 0.8 and abs(s[3] - s[1]) >= 0.4 * page_h]
    horizontals = [s[1] for s in segments if abs(s[1] - s[3]) < 0.8 and abs(s[2] - s[0]) >= 0.4 * page_w]
    left = near(verticals, 12 * MM, 28 * MM)
    right = near(verticals, page_w - 9 * MM, page_w - 2 * MM)
    top = near(horizontals, 2 * MM, 9 * MM)
    bottom = near(horizontals, page_h - 9 * MM, page_h - 2 * MM)
    if sum(v is not None for v in (left, right, top, bottom)) < 3:
        return None
    return [left if left is not None else 20 * MM, top if top is not None else 5 * MM,
            right if right is not None else page_w - 5 * MM, bottom if bottom is not None else page_h - 5 * MM]


def stamp_zone(words: list[dict], page_w: float, page_h: float, frame: list[float] | None) -> list[float] | None:
    """The zone of the title block (``stamp.py:78-111``): from the row of signature labels, else by the frame."""
    corner = [w for w in words if w["pt"][0] > page_w - 205 * MM and w["pt"][1] > page_h - 70 * MM]
    best: list[dict] | None = None
    for row in _text_lines(corner):
        labels = [w for w in row if _low(w["text"]) in _LABEL_ROW]
        kinds = {_low(w["text"]).rstrip(".").replace(" ", "") for w in labels}
        if len(kinds) >= 3 and (best is None or center(row[0]["pt"])[1] > center(best[0]["pt"])[1]):
            best = labels
    right_edge = frame[2] if frame else page_w
    bottom_edge = frame[3] if frame else page_h
    if not best:
        if frame:
            return [right_edge - 185 * MM - 1 * MM, bottom_edge - 55 * MM - 1 * MM, page_w, page_h]
        return None
    label_y = max(center(w["pt"])[1] for w in best)
    label_left = min(w["pt"][0] for w in best)
    short = label_y > bottom_edge - 9 * MM
    top = bottom_edge - 15 * MM - 1.5 * MM if short else max(bottom_edge - 55 * MM - 1.5 * MM, label_y - 24 * MM)
    return [label_left - 1.5 * MM, top, page_w, page_h]


def classify_kind(words: list[dict], designation: str | None, page_h: float) -> str:
    """``spec`` for a specification sheet (``stamp.classify_kind``, ``stamp.py:193-204``), else ``other``."""
    top = {_low(w["text"]) for w in words if w["pt"][1] < page_h * 0.3}
    if (designation or "").upper().endswith(".СО") or (
        {"поз."} & top and any(t.startswith("наименование") for t in top) and any(t.startswith("кол") for t in top)
    ):
        return "spec"
    return "other"


def norm(text: Any) -> str:
    """Whitespace normalised text (``service._norm``, ``service.py:261``)."""
    return " ".join(str(text or "").split())
