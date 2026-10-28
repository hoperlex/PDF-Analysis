"""The vector line segments a page keeps: ``pdfplumber`` lines, the edges of rectangles and the straight segments of curves.

`CMP-PROFILE-01`, `CMP-C1-FIX-A` item 8. The profile used to keep ``page.lines`` only, so a frame, a stamp or a table drawn as
rectangles (``re S``) or as a closed polyline was not in it: the frame of the sheet was not found, the margin zones were
absent, and the registration by vector lines (`CMP-ENGINE-01`, ``registration.refine_by_lines``) had fewer lines to vote on
(`CMP-ENGINE-01` section 11 item 4; `CMP-SERIES-01` section 9 item 7, "a form drawn with rectangles"). The permit's table is
found by its vertical lines, and a table drawn as thin filled rectangles has no other.

What becomes a segment, in this order (the lines come first and unchanged, so a page without rectangles or curves has the
rows it had):

* every ``pdfplumber`` **line**;
* the four **edges of a stroked rectangle**; a rectangle that is only filled is an area, not a drawn line -- a page-sized
  white background would otherwise become a frame at the page edge -- unless one of its sides is :data:`THIN_FILL_PT` or
  less: a line drawn as an area (a rule of a table), kept as **one segment along its long side**, its line width the thin
  side. A filled dot (both sides thin) is nothing;
* the **straight segments of a stroked curve**: the ``l`` and closing ``h`` steps of its path, never a ``c`` step (a Bezier
  is not a segment; ``pdfplumber``'s own ``pts`` are its end points, so the chord would be wrong). A path of more than
  :data:`MAX_PATH_STEPS` steps is a drawn figure, not a rule, and is left out.

A segment is its box ``[x0, top, x1, bottom]`` like a line (the direction of a diagonal is not kept), with its line width and
stroking colour. The module imports nothing from the product or from ``pdfplumber``: it reads the dictionaries.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Final

__all__ = ["MAX_PATH_STEPS", "THIN_FILL_PT", "collect", "curve_boxes", "rectangle_boxes"]

#: A filled rectangle with a side this thin (points) or thinner is a rule drawn as an area. Engine-independent: a CAD export
#: draws a 0.18 mm line as a 0.5 pt rectangle; a fill of a cell is wider than this on both sides.
THIN_FILL_PT: Final[float] = 2.0
#: A stroked path of more steps than this is a figure (a hatch, a symbol, a map outline), not a rule.
MAX_PATH_STEPS: Final[int] = 64

Box = tuple[float, float, float, float]


def rectangle_boxes(rect: dict[str, Any]) -> list[Box]:
    """The segments of one ``pdfplumber`` rectangle (see the module note)."""
    x0, x1 = sorted((float(rect["x0"]), float(rect["x1"])))
    top, bottom = sorted((float(rect["top"]), float(rect["bottom"])))
    if rect.get("stroke"):
        return [(x0, top, x1, top), (x0, bottom, x1, bottom), (x0, top, x0, bottom), (x1, top, x1, bottom)]
    if not rect.get("fill"):
        return []
    thin_across, thin_along = (bottom - top) <= THIN_FILL_PT, (x1 - x0) <= THIN_FILL_PT
    if thin_across and thin_along:
        return []  # a filled dot is no line
    if thin_across:
        middle = (top + bottom) / 2
        return [(x0, middle, x1, middle)]
    if thin_along:
        middle = (x0 + x1) / 2
        return [(middle, top, middle, bottom)]
    return []


def _box(a: tuple[float, float], b: tuple[float, float]) -> Box:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def curve_boxes(curve: dict[str, Any]) -> list[Box]:
    """The straight segments of one stroked ``pdfplumber`` curve (see the module note)."""
    if not curve.get("stroke"):
        return []
    path = curve.get("path") or ()
    if len(path) > MAX_PATH_STEPS:
        return []
    out: list[Box] = []
    start: tuple[float, float] | None = None
    here: tuple[float, float] | None = None
    for step in path:
        op = step[0]
        if op == "m":
            start = here = (float(step[1][0]), float(step[1][1]))
        elif op == "l" and here is not None:
            point = (float(step[1][0]), float(step[1][1]))
            out.append(_box(here, point))
            here = point
        elif op == "c" and len(step) >= 4:
            here = (float(step[3][0]), float(step[3][1]))
        elif op == "h" and here is not None and start is not None:
            if here != start:
                out.append(_box(here, start))
            here = start
    return out


def collect(
    lines: Iterable[dict[str, Any]], rects: Iterable[dict[str, Any]], curves: Iterable[dict[str, Any]],
    place: Callable[[float, float, float, float], list[float]], colour: Callable[[Any], Any],
) -> list[list[Any]]:
    """The rows ``[x0, top, x1, bottom, linewidth, colour]`` of the page: lines, then rectangles, then curves.

    ``place`` moves a box into the displayed page's frame and rounds it; ``colour`` rounds a colour."""
    rows: list[list[Any]] = [
        place(l["x0"], l["top"], l["x1"], l["bottom"]) + [round(float(l.get("linewidth") or 0), 3), colour(l.get("stroking_color"))]
        for l in lines
    ]
    for rect in rects:
        if rect.get("stroke"):
            width, color = float(rect.get("linewidth") or 0), rect.get("stroking_color")
        else:
            width = min(abs(float(rect["x1"]) - float(rect["x0"])), abs(float(rect["bottom"]) - float(rect["top"])))
            color = rect.get("non_stroking_color")
        for box in rectangle_boxes(rect):
            rows.append(place(*box) + [round(width, 3), colour(color)])
    for curve in curves:
        width, color = float(curve.get("linewidth") or 0), curve.get("stroking_color")
        for box in curve_boxes(curve):
            rows.append(place(*box) + [round(width, 3), colour(color)])
    return rows
