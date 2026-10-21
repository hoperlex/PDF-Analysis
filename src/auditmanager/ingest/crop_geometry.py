"""Whether a portal bundle holds an IMAGE block the run cannot cut (`RUN-ROBUSTNESS-01`, D-159).

`W55B-GEOMETRY-01` cuts one crop per IMAGE block of every page whose box agrees with the
portal's raster (``analysis.geometry.maths``). A block whose box is so small that its crop
would need a page canvas wider than ``2**24`` pixels cannot be rendered accurately, and the
stage then fails the *whole run* ``portal_block_degenerate`` (`R-121`: the owner kept that
behaviour, and no crop-less block exists in W55b). `R-121` registered the debt this module
pays: **move the refusal to the upload**, so that a version which would fail every run is never
accepted, and an accepted version never fails a run for this reason.

The decision needs the PDF's page sizes and the block list's raster, both known at upload, and
the stage's own arithmetic. That arithmetic belongs to ``analysis`` and ingest may not import
it (the context boundary, ``tests/contract/architecture``), so it is restated here, function
for function, and ``tests/integration/ingest/test_uncuttable_image_block.py`` holds the two to
each other over thousands of boxes, pages and rasters, the boundary of every rule included.
Nothing here is a different rule, and a change to ``maths.py`` that is not made here fails that
test.

What is restated, and only that:

* :func:`page_agrees` -- ``maths.check_page``: the portal's rotation equals the page's, both
  sizes are positive, and the aspect ratios differ by at most
  :data:`PAGE_BOX_TOLERANCE`. A page that does not agree cuts no crop, so a block on it cannot
  fail the run;
* :func:`cannot_cut` -- ``maths.plan_crop``: the scale is the portal's density raised to the
  floor of :data:`MIN_LONG_SIDE_PX` and lowered to the cap of :data:`MAX_PIXELS`; the plan fails
  when its canvas is wider than :data:`MAX_CANVAS_SIDE`, when any step of the arithmetic
  fails, or when the box is not a positive box inside the page.

Every value is a number of the block list, never a string of it: nothing a caller wrote is
echoed in a refusal.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Final

__all__ = [
    "MAX_CANVAS_SIDE",
    "MAX_PIXELS",
    "MIN_LONG_SIDE_PX",
    "PAGE_BOX_TOLERANCE",
    "cannot_cut",
    "page_agrees",
    "uncuttable_image_block",
]

#: `W55B-FREEZE-01`: a crop's long side is at least this many pixels.
MIN_LONG_SIDE_PX: Final[int] = 800
#: `W55B-FREEZE-01`: a crop holds at most this many pixels.
MAX_PIXELS: Final[int] = 4_000_000
#: `W55B-FREEZE-01`: "0.5 % per side".
PAGE_BOX_TOLERANCE: Final[float] = 0.005
#: The decimals a scale is kept to.
SCALE_DIGITS: Final[int] = 6
#: The widest page canvas a clip is positioned on (PDFium's float32 holds integers to 2**24).
MAX_CANVAS_SIDE: Final[int] = 2**24

_STEP: Final[float] = 10.0**-SCALE_DIGITS
#: How much shorter (rounding of the canvas) and longer (that, plus a pixel at each outward
#: edge) than ``side_pt * scale`` an integer clip side can be.
_ROUNDING_LOSS: Final[float] = 0.5
_ROUNDING_GAIN: Final[float] = 2.5


def page_agrees(
    *,
    portal_width_px: int,
    portal_height_px: int,
    portal_rotation: int,
    page_width_pt: float,
    page_height_pt: float,
    page_rotation: int,
) -> bool:
    """``maths.check_page`` is ``ok``: the portal's raster describes the displayed page."""
    if portal_rotation % 360 != page_rotation % 360:
        return False
    if min(portal_width_px, portal_height_px) <= 0 or min(page_width_pt, page_height_pt) <= 0:
        return False
    ratio = (portal_width_px / portal_height_px) / (page_width_pt / page_height_pt)
    deviation = max(ratio, 1.0 / ratio) - 1.0
    return not deviation > PAGE_BOX_TOLERANCE


def _round_up(scale: float) -> float:
    return round(math.ceil(scale / _STEP) * _STEP, SCALE_DIGITS)


def _round_down(scale: float) -> float:
    return round(math.floor(scale / _STEP) * _STEP, SCALE_DIGITS)


def _floor_scale(clip_long_pt: float) -> float:
    return _round_up((MIN_LONG_SIDE_PX + _ROUNDING_LOSS) / clip_long_pt)


def _cap_scale(clip_width_pt: float, clip_height_pt: float) -> float:
    a = clip_width_pt * clip_height_pt
    b = _ROUNDING_GAIN * (clip_width_pt + clip_height_pt)
    c = _ROUNDING_GAIN**2 - MAX_PIXELS
    return _round_down((-b + math.sqrt(b * b - 4 * a * c)) / (2 * a))


def cannot_cut(
    bbox_norm: Sequence[float],
    page_width_pt: float,
    page_height_pt: float,
    page_width_px: int,
) -> bool:
    """``maths.plan_crop`` refuses this box (``DegenerateCrop``) or fails in its arithmetic.

    ``page_width_px`` is the portal's raster width of the page: the base scale is
    ``page_width_px / page_width_pt`` (``maths.base_scale``).
    """
    try:
        if len(bbox_norm) != 4:
            return True
        x0, y0, x1, y1 = (float(value) for value in bbox_norm)
        if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (x0, y0, x1, y1)):
            return True
        if not (x0 < x1 and y0 < y1):
            return True
        if not (page_width_pt > 0 and page_height_pt > 0):
            return True
        base = page_width_px / page_width_pt
        clip_width = (x1 - x0) * page_width_pt
        clip_height = (y1 - y0) * page_height_pt
        scale = round(base, SCALE_DIGITS) if math.isfinite(base) and base > 0 else 0.0
        scale = max(scale, _floor_scale(max(clip_width, clip_height)))  # the floor
        scale = min(scale, _cap_scale(clip_width, clip_height))  # the cap, which wins
        if not (math.isfinite(scale) and scale > 0):
            return True
        canvas_width = max(1, int(math.floor(page_width_pt * scale + 0.5)))
        canvas_height = max(1, int(math.floor(page_height_pt * scale + 0.5)))
        if max(canvas_width, canvas_height) > MAX_CANVAS_SIDE:
            return True
        left = min(max(0, math.floor(x0 * canvas_width)), canvas_width - 1)
        top = min(max(0, math.floor(y0 * canvas_height)), canvas_height - 1)
        right = max(left + 1, min(canvas_width, math.ceil(x1 * canvas_width)))
        bottom = max(top + 1, min(canvas_height, math.ceil(y1 * canvas_height)))
        return (right - left) * (bottom - top) > MAX_PIXELS
    except (ArithmeticError, ValueError):
        return True


def uncuttable_image_block(
    document: dict[str, Any], geometry: Sequence[Sequence[float]]
) -> bool:
    """Whether the stage would fail the run on a page or a block of ``document``.

    ``document`` is the parsed block list and ``geometry[i]`` is ``(width_pt, height_pt,
    rotation)`` of PDF page ``i`` as displayed (:mod:`auditmanager.ingest.pdf_reader`). The
    block list has passed the schema, so its pages run ``0 .. n-1`` and every block names one
    of them. The stage checks **every** page's box (a raster so large that the division
    overflows fails the run on a page without a single block, and fails here the same way) and
    then cuts the IMAGE blocks of the pages that agree.
    """
    pages = document["pages"]
    try:
        agreeing = [
            page_agrees(
                portal_width_px=int(page["width_px"]),
                portal_height_px=int(page["height_px"]),
                portal_rotation=int(page["rotation"]),
                page_width_pt=geometry[index][0],
                page_height_pt=geometry[index][1],
                page_rotation=int(geometry[index][2]),
            )
            for index, page in enumerate(pages)
        ]
    except (ArithmeticError, ValueError):
        return True  # `check_page` raises on this page: the stage fails the run on it
    for block in document["blocks"]:
        if block["block_type"] != "image":
            continue
        index = int(block["page_index"])
        if not agreeing[index]:
            continue  # no crop is cut on a page whose box disagrees
        if cannot_cut(
            block["coords_norm"],
            geometry[index][0],
            geometry[index][1],
            int(pages[index]["width_px"]),
        ):
            return True
    return False
