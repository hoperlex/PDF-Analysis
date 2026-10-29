"""Page geometry of the sheet-changes packet (`CMP-VC-AISHEET-01`).

A port of the original's ``version_comparison_ai/geometry.py`` (`23f379fd`, lines 1-80) onto this tree's contract:

* every box is ``[x0, y0, x1, y1]`` in points of the displayed page, origin top left, X right, Y down;
* the engine's boxes (``ComparisonBox`` ``{x, y, width, height}``) are on the canvas of the **older** page A, which is the
  coordinate system of page A;
* ``how_compared.transform`` is the affine ``[a, b, c, d, e, f]`` that maps a point of page **B** onto page A
  (``x' = a x + c y + e``, ``y' = b x + d y + f``, the PDF's matrix order); the inverse maps a box of A onto page B.

Pure: no database, no library.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final

__all__ = [
    "IDENTITY",
    "Rect",
    "a_to_b_page",
    "b_page_to_a",
    "box_of",
    "box_to_dict",
    "clip",
    "contains",
    "expand",
    "intersects",
    "invert",
    "map_rect",
    "rounded",
    "union",
]

Rect = list[float]

IDENTITY: Final[tuple[float, ...]] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def apply(matrix: Sequence[float], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def invert(matrix: Sequence[float]) -> tuple[float, ...]:
    a, b, c, d, e, f = (float(v) for v in matrix)
    det = a * d - b * c
    if abs(det) < 1e-12:
        raise ValueError("the registration matrix is degenerate")
    ia, ib, ic, id_ = d / det, -b / det, -c / det, a / det
    return ia, ib, ic, id_, -(ia * e + ic * f), -(ib * e + id_ * f)


def map_rect(matrix: Sequence[float], rect: Sequence[float]) -> Rect:
    points = [apply(matrix, x, y) for x, y in ((rect[0], rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (rect[2], rect[3]))]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def b_page_to_a(matrix: Sequence[float], rect: Sequence[float]) -> Rect:
    """A box of page B in the system of page A (the canvas): the engine's matrix."""
    return map_rect(matrix, rect)


def a_to_b_page(matrix: Sequence[float], rect: Sequence[float]) -> Rect:
    """A box of the canvas (page A) on page B: the inverse matrix."""
    return map_rect(invert(matrix), rect)


def union(rects: Iterable[Sequence[float] | None]) -> Rect | None:
    rs = [list(r) for r in rects if r]
    if not rs:
        return None
    return [min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)]


def expand(rect: Sequence[float], dx: float, dy: float | None = None) -> Rect:
    dy = dx if dy is None else dy
    return [rect[0] - dx, rect[1] - dy, rect[2] + dx, rect[3] + dy]


def contains(outer: Sequence[float], inner: Sequence[float]) -> bool:
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def intersects(a: Sequence[float], b: Sequence[float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def clip(rect: Sequence[float], width: float, height: float) -> Rect:
    return [max(0.0, rect[0]), max(0.0, rect[1]), min(width, rect[2]), min(height, rect[3])]


def rounded(rect: Sequence[float] | None, digits: int = 2) -> Rect | None:
    return None if rect is None else [round(float(v), digits) for v in rect]


def box_of(box: Mapping[str, Any] | None) -> Rect | None:
    """``[x0, y0, x1, y1]`` from the contract's ``ComparisonBox`` (or ``None``)."""
    if not box:
        return None
    x, y = float(box["x"]), float(box["y"])
    return [x, y, x + float(box["width"]), y + float(box["height"])]


def box_to_dict(rect: Sequence[float]) -> dict[str, float]:
    """The contract's ``ComparisonBox`` from ``[x0, y0, x1, y1]``."""
    x0, y0, x1, y1 = (float(v) for v in rect)
    return {"x": round(x0, 2), "y": round(y0, 2), "width": round(max(0.0, x1 - x0), 2), "height": round(max(0.0, y1 - y0), 2)}
