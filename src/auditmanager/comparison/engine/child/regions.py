"""Regions of difference: grouping, classes, and the checks that look at the pixels around a region
(port of ``engine.py:105-136``, ``:186-239``, ``:759-898``).

`CMP-ENGINE-01`. A *region* is a group of difference pixels that belong together. The original closes the union of
the difference layers with a disk of ``REGION_CLOSE_MM`` and labels the connected components of the whole canvas
(``:759-763``); here the closing is done a band of rows at a time (:func:`close_union`), the components are labelled on
the result reduced by ``factor`` (2 for a canvas over 12 Mpx, else 1: exact), and the counts of each layer's pixels in
each region are taken from the sparse coordinates of the layer, so no whole-canvas label array of full size is held.

The class of a region (``:827-863``), in the order the original tries them: ``style`` (only 1-3 px of changed pen
width, no pixel of removed/added/light/colour), ``text`` (a word only in A or only in B touches it), ``text_moved``
(the same words moved, nothing else beyond noise), ``changed`` (pixels in A only and in B only), ``added``, ``removed``,
``style`` again (colour or light edges next to a changed pen), ``style`` by the drawing order of crossing lines
(:func:`overdraw`), ``color``, ``light``. A region of class ``added``, ``removed``, ``changed``, ``style`` or ``light``
whose pixels are explained by the shift of a neighbouring inscription or block is ``shifted`` (``text_moved`` when the
words moved) and not a change (:func:`shift_explains`). A region of ``added``, ``removed`` or ``changed`` with no word
under it that looks like a line of glyphs is an inscription drawn without a text layer, which the text channel could not
read (:func:`glyph_line`).

Every check that costs more than a few array operations has a **budget** (:data:`WINDOW_PIXELS`, a count of components,
the time the caller allows): when it is spent the region is classified by the cheap rules alone, which never turn a
region into a shift. The caller reports that (``PARTIAL_COVERAGE``).
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any

import cv2
import numpy

from . import settings
from .geometry import Canvas, bands
from .layers import disk
from .planes import PlaneStore
from .words import center, in_rects

__all__ = [
    "BudgetSpent",
    "RectIndex",
    "close_union",
    "glyph_line",
    "label_regions",
    "overdraw",
    "reduction_factor",
    "shift_explains",
]

#: The largest window (pixels) a single check may unpack.
WINDOW_PIXELS = 4_000_000
#: The most components of one region the shift check will try to explain, and the largest one it will match.
SHIFT_MAX_COMPONENTS = 400
SHIFT_MAX_COMPONENT_PIXELS = 250_000
_UNION_LAYERS = ("a_only", "b_only", "light_a", "light_b", "color", "style")


def reduction_factor(width: int, height: int) -> int:
    """1 up to 12 Mpx (exact), 2 up to 24 Mpx, 3 above: the label array of the reduced canvas costs 4 bytes a pixel."""
    pixels = width * height
    return 1 if pixels <= 12_000_000 else 2 if pixels <= 24_000_000 else 3


class RectIndex:
    """A grid over rectangles in points: ``query(box)`` returns the payloads whose rectangle meets ``box``."""

    def __init__(self, cell: float = 60.0) -> None:
        self._cell = cell
        self._cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        self._items: list[tuple[list[float], Any]] = []

    def add(self, rect: Sequence[float], payload: Any) -> None:
        index = len(self._items)
        self._items.append(([float(v) for v in rect], payload))
        c = self._cell
        for cx in range(int(rect[0] // c), int(rect[2] // c) + 1):
            for cy in range(int(rect[1] // c), int(rect[3] // c) + 1):
                self._cells[(cx, cy)].append(index)

    def query(self, box: Sequence[float]) -> list[Any]:
        c = self._cell
        seen: set[int] = set()
        out: list[Any] = []
        for cx in range(int(box[0] // c), int(box[2] // c) + 1):
            for cy in range(int(box[1] // c), int(box[3] // c) + 1):
                for index in self._cells.get((cx, cy), ()):
                    if index in seen:
                        continue
                    seen.add(index)
                    rect, payload = self._items[index]
                    if not (rect[2] < box[0] or rect[0] > box[2] or rect[3] < box[1] or rect[1] > box[3]):
                        out.append(payload)
        return out


# -- grouping -----------------------------------------------------------------------------------

def close_union(store: PlaneStore, canvas: Canvas, *, band_pixels: int) -> None:
    """``union`` = the six difference layers, ``grouped`` = ``union`` closed by a disk of ``REGION_CLOSE_MM``, or
    ``union`` (``:759-762``), both stored as planes, a band of rows at a time."""
    close_px = max(1, int(round(settings.REGION_CLOSE_MM * canvas.dpi / 25.4)))
    radius = close_px // 2 + 1
    kernel = disk(radius)
    store.data.setdefault("union", numpy.zeros_like(store.data["a_only"]))
    store.data.setdefault("grouped", numpy.zeros_like(store.data["a_only"]))
    for band in bands(store.width, store.height, pixels=band_pixels, margin=radius + 2):
        union = numpy.zeros((band.ext1 - band.ext0, store.width), numpy.uint8)
        for name in _UNION_LAYERS:
            union |= store.rows(name, band.ext0, band.ext1)
        grouped = cv2.morphologyEx(union, cv2.MORPH_CLOSE, kernel) | union
        lo, hi = band.core0 - band.ext0, band.core1 - band.ext0
        store.put_rows("union", band.core0, union[lo:hi])
        store.put_rows("grouped", band.core0, grouped[lo:hi])


def label_regions(store: PlaneStore, *, band_pixels: int) -> tuple[Any, Any, int]:
    """Label the connected components of ``grouped`` on the reduced canvas: ``(labels, stats, factor)``.

    ``labels`` has the shape of the reduced canvas, ``stats`` is OpenCV's ``(x, y, w, h, area)`` per label in reduced
    pixels; multiply by ``factor`` to get canvas pixels."""
    factor = reduction_factor(store.width, store.height)
    rh, rw = -(-store.height // factor), -(-store.width // factor)
    reduced = numpy.zeros((rh, rw), numpy.uint8)
    rows_per = max(factor, (band_pixels // max(1, store.width)) // factor * factor)
    for y0 in range(0, store.height, rows_per):
        y1 = min(store.height, y0 + rows_per)
        rows = store.rows("grouped", y0, y1)
        if factor > 1:
            pad_h, pad_w = (-rows.shape[0]) % factor, (-rows.shape[1]) % factor
            if pad_h or pad_w:
                rows = numpy.pad(rows, ((0, pad_h), (0, pad_w)))
            rows = rows.reshape(rows.shape[0] // factor, factor, rows.shape[1] // factor, factor).max(axis=(1, 3))
        reduced[y0 // factor : y0 // factor + rows.shape[0]] = rows
    n, labels, stats, _ = cv2.connectedComponentsWithStats(reduced, connectivity=8)
    del reduced
    return labels, stats, factor


def layer_counts(store: PlaneStore, labels: Any, n: int, factor: int, names: Sequence[str], *, band_pixels: int,
                 exclude: Callable[[int, int], Any] | None = None) -> dict[str, Any]:
    """For each layer, the number of its pixels in each label. ``exclude(y0, y1)`` may return a mask of rows to
    leave out (the places of moved inscriptions, ``:766-775``)."""
    counts: dict[str, Any] = {name: numpy.zeros(n, dtype=numpy.int64) for name in names}
    rows_per = max(1, band_pixels // max(1, store.width))
    for y0 in range(0, store.height, rows_per):
        y1 = min(store.height, y0 + rows_per)
        skip = exclude(y0, y1) if exclude is not None else None
        for name in names:
            source = "union" if name == "out" else name
            rows = store.rows(source, y0, y1)
            if name == "out" and skip is not None:
                rows = rows & (1 - skip)
            ys, xs = numpy.nonzero(rows)
            if len(ys):
                counts[name] += numpy.bincount(labels[(ys + y0) // factor, xs // factor], minlength=n)
    return counts


# -- checks on the pixels around a region -------------------------------------------------------

def shift_explains(store: PlaneStore, vectors: Sequence[tuple[float, float]], box_px: Sequence[int], canvas: Canvas,
                   deadline: float) -> bool:
    """The region is explained as a whole by the shifts of neighbouring inscriptions or of a block (``:186-239``).

    Each connected part of the difference (a mark, a line) looks for its own shift within ``SHIFT_REFINE_PT`` of the
    shift of a neighbouring inscription: the rows of a legend drift apart by different distances, the mark and the
    caption by slightly different ones. A part is explained when, at the shifted place, the other version draws the
    same figure (nearly every one of its pixels lies on a line). A new line or mark beside the inscription is not
    explained that way: there is no such figure nearby in the other version."""
    x0, y0, x1, y1 = (int(v) for v in box_px)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(store.width, x1), min(store.height, y1)
    if x1 <= x0 or y1 <= y0 or (x1 - x0) * (y1 - y0) > WINDOW_PIXELS:
        return False
    sel = numpy.zeros((y1 - y0, x1 - x0), numpy.uint8)
    for name in ("a_only", "b_only", "light_a", "light_b", "style"):
        sel |= store.window(name, x0, y0, x1, y1)
    total = int(sel.sum())
    if not total:
        return False
    radius = int(round(settings.SHIFT_REFINE_PT * canvas.s))
    k = numpy.ones((3, 3), numpy.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(sel, connectivity=8)
    if n - 1 > SHIFT_MAX_COMPONENTS:
        return False
    explained = 0
    for i in range(1, n):
        if time.process_time() > deadline:
            return False
        cx, cy, cw, ch, _area = (int(v) for v in stats[i])
        if cw * ch > SHIFT_MAX_COMPONENT_PIXELS:
            continue
        comp = (labels[cy : cy + ch, cx : cx + cw] == i).astype(numpy.uint8)
        gx, gy = x0 + cx, y0 + cy
        ink_a = store.window("any_a", gx, gy, gx + cw, gy + ch) & comp
        ink_b = store.window("any_b", gx, gy, gx + cw, gy + ch) & comp
        for src, dst, sign in ((ink_a, "any_b", 1), (ink_b, "any_a", -1)):
            if not src.any():
                continue
            best = 0
            for vx, vy in vectors:
                dx, dy = int(round(sign * vx * canvas.s)), int(round(sign * vy * canvas.s))
                X0, Y0 = gx + dx - radius, gy + dy - radius
                X1, Y1 = X0 + cw + 2 * radius, Y0 + ch + 2 * radius
                if X0 < 0 or Y0 < 0 or X1 > store.width or Y1 > store.height:
                    continue
                win = cv2.dilate(store.window(dst, X0, Y0, X1, Y1), k).astype(numpy.float32)
                score = cv2.matchTemplate(win, src.astype(numpy.float32), cv2.TM_CCORR)
                best = max(best, int(round(float(score.max()))))
            explained += min(int(src.sum()), best)
    return explained >= settings.SHIFT_EXPLAINED_SHARE * total


def _is_stroke(component: Any) -> bool:
    """A component that is one straight stroke of any width up to a quarter of its length (``:186-189``)."""
    (_cx, _cy), (rw, rh), _angle = cv2.minAreaRect(cv2.findNonZero(component))
    return min(rw, rh) <= max(2.5, settings.GLYPH_STROKE_RATIO * max(rw, rh))


class BudgetSpent(Exception):
    """The time allowed for the analysis of regions ran out inside a check."""


def glyph_line(mask: Any, mm_px: float, common: Any | None = None, deadline: float | None = None) -> bool:
    """The area looks like a line of an inscription: at least three glyphs of one height in a row (``:192-232``).

    The gap between the glyphs of an inscription is empty. A line common to A and B in the gap makes it one figure (a
    cloud of changes, an outline) cut by crossing lines into similar pieces. An arc wider than twice its height (a
    cloud) and a filled blot are not glyphs; a row of straight strokes only is a hatch or parallel lines."""
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    glyphs: list[tuple[Any, Any, bool]] = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[i])
        if not (1.0 * mm_px <= h <= 6 * mm_px and w <= 6 * mm_px):
            continue
        if w > settings.GLYPH_MAX_ASPECT * h or area > settings.GLYPH_MAX_FILL * w * h:
            continue
        glyphs.append((stats[i], centroids[i], _is_stroke((labels[y : y + h, x : x + w] == i).astype(numpy.uint8))))
    glyphs.sort(key=lambda g: g[1][0])
    for i in range(len(glyphs)):
        if deadline is not None and i % 64 == 0 and time.process_time() > deadline:
            raise BudgetSpent()
        chain = [glyphs[i]]
        for g in glyphs[i + 1 :]:
            last = chain[-1]
            if g[1][0] > last[0][0] + last[0][2] + 9 * mm_px:
                break  # sorted by centre, no glyph is wider than 6 mm: none from here on can be within 3 mm of `last`
            same_row = abs(g[1][1] - last[1][1]) <= 1.0 * mm_px
            similar = 0.6 <= g[0][3] / max(1, last[0][3]) <= 1.6
            gap_x0, gap_x1 = last[0][0] + last[0][2], g[0][0]
            close = -0.25 * min(g[0][3], last[0][3]) <= gap_x1 - gap_x0 <= 3 * mm_px
            if close and common is not None and gap_x1 > gap_x0:
                gy0 = max(last[0][1], g[0][1])
                gy1 = min(last[0][1] + last[0][3], g[0][1] + g[0][3])
                if gy1 > gy0 and common[gy0:gy1, gap_x0:gap_x1].any():
                    close = False
            if same_row and similar and close:
                chain.append(g)
        if len(chain) >= 3 and not all(g[2] for g in chain):
            return True
    return False


def overdraw(bgr_a: Any, bgr_b: Any, color: Any, dark_a: Any, dark_b: Any, box: Sequence[int], pad: int) -> bool:
    """The colour changed because of the order in which crossing lines are drawn, not because a line was recoloured
    (``:79-108``). Windows are given whole (rendered around the box); ``box`` is relative to them."""
    x0, y0, x1, y1 = box
    h, w = color.shape
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    sel = numpy.zeros((Y1 - Y0, X1 - X0), bool)
    sel[y0 - Y0 : y1 - Y0, x0 - X0 : x1 - X0] = color[y0:y1, x0:x1].astype(bool)
    if not sel.any():
        return False
    lab_a = cv2.cvtColor(numpy.ascontiguousarray(bgr_a[Y0:Y1, X0:X1]), cv2.COLOR_BGR2Lab).astype(numpy.float32)
    lab_b = cv2.cvtColor(numpy.ascontiguousarray(bgr_b[Y0:Y1, X0:X1]), cv2.COLOR_BGR2Lab).astype(numpy.float32)

    def explained(points: Any, lab: Any, dark: Any) -> float:
        palette = numpy.unique(lab[dark[Y0:Y1, X0:X1].astype(bool)].astype(numpy.int16), axis=0).astype(numpy.float32)
        if not len(palette):
            return 0.0
        pts = points[:: max(1, len(points) // 200)]
        dist = numpy.linalg.norm(pts[:, None, :] - palette[None, :, :], axis=2).min(axis=1)
        return float((dist < settings.OVERDRAW_DELTA).mean())

    share = settings.OVERDRAW_MIN_SHARE
    return explained(lab_a[sel], lab_b, dark_b) >= share and explained(lab_b[sel], lab_a, dark_a) >= share


def rect_arrays(rects: Sequence[Sequence[int]], rows: int, width: int, y_offset: int) -> Any:
    """A 0/1 mask of ``rows`` x ``width`` with the rectangles (canvas pixels) that fall in rows from ``y_offset``."""
    out = numpy.zeros((rows, width), numpy.uint8)
    for x0, y0, x1, y1 in rects:
        x0, x1 = max(0, x0), min(width, x1)
        y0, y1 = max(0, y0 - y_offset), min(rows, y1 - y_offset)
        if x1 > x0 and y1 > y0:
            out[y0:y1, x0:x1] = 1
    return out


__all__ += ["WINDOW_PIXELS", "layer_counts", "rect_arrays", "center", "in_rects"]
