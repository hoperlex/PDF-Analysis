"""The geometry of a portal block on a PDF page: numbers in, numbers out, no I/O.

`W55B-GEOMETRY-01` (plan section B3.7; ``P02_SEAMS`` sections 4.5 and 4.9). Three questions,
each answered here from plain numbers so that every branch can be tested without a PDF,
a renderer or a store:

1. **What does the page look like?** :func:`displayed_size` -- the PDF's CropBox, clipped to
   its MediaBox, after ``/Rotate``: the width and height in points of the page a viewer
   shows, and the page PDFium draws.
2. **Does the portal's page raster describe that page?** :func:`check_page` -- the portal's
   ``rotation`` must be the PDF's own ``/Rotate``, and the aspect of its ``width_px`` x
   ``height_px`` must be the displayed page's within :data:`PAGE_BOX_TOLERANCE`. Anything
   else is :data:`GEOMETRY_MISMATCH`: a page whose blocks would be cut from a box other than
   the one the portal measured gets no crop, because a wrong crop is worse than none.
3. **Which pixels are a block's crop?** :func:`plan_crop` -- the scale, the whole page's
   canvas at that scale, and the integer clip rectangle on it, under the frozen budget.

The page-box tolerance, exactly
-------------------------------
``r = (width_px / height_px) / (width_pt / height_pt)``, the portal's aspect over the PDF's
displayed aspect. Scale the portal's page so that one side equals the PDF's: the other side
then differs from the PDF's by ``r - 1`` (fitted by height) or ``1/r - 1`` (fitted by width)
of its own length. "0.5 % per side" is both of those within 0.005, which is
``max(r, 1/r) - 1 <= 0.005`` (:func:`aspect_deviation`); equality passes. The real АР pages
differ by about 0.06 % (`W55B-FREEZE-01`).

Rotation, and which side is trusted
-----------------------------------
The block's ``bbox_norm`` lives in the page's normalised top-left space **after** rotation
(``coordinate_space: normalized_page_top_left``). PDFium renders a page in exactly that
orientation (its ``/Rotate`` applied, clockwise), so a normalised box maps onto the displayed
page the same way for every rotation, and the four rotations differ only in which side of
the box is the displayed width (:data:`_QUARTER_TURNS`). The **PDF's** ``/Rotate`` is what is
rendered and so what is trusted; the portal's ``rotation`` is only compared with it. When the
two disagree the portal measured some other orientation of the page, and the page is a
mismatch -- never a guess at which one it meant.

The scale rule
--------------
``scale`` is pixels per point of the displayed page.

* **Base:** the portal's own raster density, ``width_px / width_pt`` -- the crop has the
  resolution of the page image the portal recognised the block on (:func:`base_scale`).
* **Floor:** raised, if needed, so the crop's long side is at least
  :data:`MIN_LONG_SIDE_PX`.
* **Cap:** lowered, if needed, so the crop holds at most :data:`MAX_PIXELS` pixels.
* The scale is kept to :data:`SCALE_DIGITS` decimals, so the recorded ``render_profile.scale``
  is exactly the scale that was rendered. Both bounds are computed with the integer clip's
  worst rounding included (half a pixel of canvas rounding; a pixel at each outward edge),
  so the rectangle meets them by construction.

**The corner where the two bounds meet.** At the floor the crop has a long side of 800 px and
so at most 800 x 800 = 640 000 pixels, far under the cap; at the cap it holds about
4 000 000 pixels and so has a long side of at least 2 000 px, far over the floor. The two
cannot conflict for a crop of positive size. Should integer rounding ever make them (it does
not for any box this module accepts), **the cap wins**: it bounds the memory of a render, and
the floor is a resolution wish. :func:`plan_crop` encodes that order.

**A degenerate box.** PDFium positions a clip with 32-bit floats, which hold every integer up
to 2**24 exactly. A box so small that the floor would need a page canvas wider than that
(:data:`MAX_CANVAS_SIDE`: a long side under ``800 / 2**24`` of the page's longer side, about a
sixth of a pixel of a 300 dpi A4 raster) cannot be rendered accurately and raises
:class:`DegenerateCrop`; the stage refuses the bundle rather than cutting a crop it cannot
vouch for.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

#: `W55B-FREEZE-01`: a crop's long side is at least this many pixels.
MIN_LONG_SIDE_PX: Final[int] = 800
#: `W55B-FREEZE-01`: a crop holds at most this many pixels.
MAX_PIXELS: Final[int] = 4_000_000
#: `W55B-FREEZE-01`: "0.5 % per side" (see the module docstring for the exact rule).
PAGE_BOX_TOLERANCE: Final[float] = 0.005
#: The decimals ``scale`` is kept to, so the recorded scale is the rendered one.
SCALE_DIGITS: Final[int] = 6
#: The widest page canvas a clip is positioned on (PDFium's float32 holds integers to 2**24).
MAX_CANVAS_SIDE: Final[int] = 2**24

#: ``geometry`` of a page (and of every block on it), ``P02_SEAMS`` section 4.9.
GEOMETRY_OK: Final[str] = "ok"
GEOMETRY_MISMATCH: Final[str] = "geometry_mismatch"

#: The rotations a page and the portal may declare.
ROTATIONS: Final[tuple[int, ...]] = (0, 90, 180, 270)
#: The rotations that exchange the displayed width and height.
_QUARTER_TURNS: Final[frozenset[int]] = frozenset({90, 270})

_STEP: Final[float] = 10.0**-SCALE_DIGITS
#: How much shorter (rounding of the canvas) and longer (that, plus a pixel at each outward
#: edge) than ``side_pt * scale`` an integer clip side can be.
_ROUNDING_LOSS: Final[float] = 0.5
_ROUNDING_GAIN: Final[float] = 2.5


class DegenerateCrop(ValueError):
    """A block's box cannot be rendered as a crop under the rules of this module."""


@dataclass(frozen=True, slots=True)
class Box:
    """A rectangle in PDF user space, in points, as ``[x0, y0, x1, y1]`` (any corner order)."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def left(self) -> float:
        return min(self.x0, self.x1)

    @property
    def right(self) -> float:
        return max(self.x0, self.x1)

    @property
    def bottom(self) -> float:
        return min(self.y0, self.y1)

    @property
    def top(self) -> float:
        return max(self.y0, self.y1)

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom


def normalised_rotation(degrees: int) -> int:
    """``degrees`` as one of :data:`ROTATIONS`; anything not a multiple of 90 is refused."""
    if isinstance(degrees, bool) or not isinstance(degrees, int) or degrees % 90 != 0:
        raise ValueError("a page rotation is a multiple of 90 degrees")
    return degrees % 360


def effective_box(cropbox: Box, mediabox: Box) -> Box:
    """The CropBox clipped to the MediaBox: what a viewer shows of the page.

    An intersection that is empty has zero width or height; :func:`check_page` then marks
    the page a mismatch instead of dividing by it.
    """
    left = max(cropbox.left, mediabox.left)
    bottom = max(cropbox.bottom, mediabox.bottom)
    right = max(left, min(cropbox.right, mediabox.right))
    top = max(bottom, min(cropbox.top, mediabox.top))
    return Box(left, bottom, right, top)


def displayed_size(cropbox: Box, mediabox: Box, rotation: int) -> tuple[float, float]:
    """``(width, height)`` in points of the page as displayed: the box after ``/Rotate``."""
    box = effective_box(cropbox, mediabox)
    if normalised_rotation(rotation) in _QUARTER_TURNS:
        return box.height, box.width
    return box.width, box.height


def aspect_deviation(
    portal_width_px: int, portal_height_px: int, page_width_pt: float, page_height_pt: float
) -> float:
    """``max(r, 1/r) - 1`` for ``r`` the portal's aspect over the page's (module docstring)."""
    ratio = (portal_width_px / portal_height_px) / (page_width_pt / page_height_pt)
    return max(ratio, 1.0 / ratio) - 1.0


def check_page(
    *,
    portal_width_px: int,
    portal_height_px: int,
    portal_rotation: int,
    page_width_pt: float,
    page_height_pt: float,
    page_rotation: int,
) -> str:
    """:data:`GEOMETRY_OK` when the portal's raster describes the displayed page.

    ``page_*`` are the displayed page (:func:`displayed_size`) and its ``/Rotate``.
    """
    if normalised_rotation(portal_rotation) != normalised_rotation(page_rotation):
        return GEOMETRY_MISMATCH
    if min(portal_width_px, portal_height_px) <= 0 or min(page_width_pt, page_height_pt) <= 0:
        return GEOMETRY_MISMATCH
    deviation = aspect_deviation(
        portal_width_px, portal_height_px, page_width_pt, page_height_pt
    )
    if deviation > PAGE_BOX_TOLERANCE:
        return GEOMETRY_MISMATCH
    return GEOMETRY_OK


def base_scale(portal_width_px: int, page_width_pt: float) -> float:
    """The portal raster's density over the displayed page, in pixels per point."""
    return portal_width_px / page_width_pt


@dataclass(frozen=True, slots=True)
class CropPlan:
    """One crop: the scale, the page canvas at that scale, and the clip on that canvas.

    ``width`` x ``height`` is the size of the bitmap the renderer allocates and fills: the
    clip, never the page.
    """

    scale: float
    canvas_width: int
    canvas_height: int
    left: int
    top: int
    width: int
    height: int

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def long_side(self) -> int:
        return max(self.width, self.height)


def _validated_bbox(bbox_norm: tuple[float, float, float, float]) -> tuple[float, ...]:
    if len(bbox_norm) != 4:
        raise DegenerateCrop("a box has four coordinates")
    x0, y0, x1, y1 = (float(value) for value in bbox_norm)
    if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in (x0, y0, x1, y1)):
        raise DegenerateCrop("a normalised box lies in [0, 1]")
    if not (x0 < x1 and y0 < y1):
        raise DegenerateCrop("a normalised box has a positive width and height")
    return x0, y0, x1, y1


def _layout(
    bbox: tuple[float, ...], page_width_pt: float, page_height_pt: float, scale: float
) -> CropPlan:
    """The canvas and the integer clip for one scale; the clip covers the box (outward)."""
    if not (math.isfinite(scale) and scale > 0):
        raise DegenerateCrop("a crop's scale is positive")
    canvas_width = max(1, int(math.floor(page_width_pt * scale + 0.5)))
    canvas_height = max(1, int(math.floor(page_height_pt * scale + 0.5)))
    if max(canvas_width, canvas_height) > MAX_CANVAS_SIDE:
        raise DegenerateCrop("the block is too small to be positioned on a page canvas")
    x0, y0, x1, y1 = bbox
    left = min(max(0, math.floor(x0 * canvas_width)), canvas_width - 1)
    top = min(max(0, math.floor(y0 * canvas_height)), canvas_height - 1)
    right = max(left + 1, min(canvas_width, math.ceil(x1 * canvas_width)))
    bottom = max(top + 1, min(canvas_height, math.ceil(y1 * canvas_height)))
    return CropPlan(
        scale=scale,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        left=left,
        top=top,
        width=right - left,
        height=bottom - top,
    )


def _round_up(scale: float) -> float:
    return round(math.ceil(scale / _STEP) * _STEP, SCALE_DIGITS)


def _round_down(scale: float) -> float:
    return round(math.floor(scale / _STEP) * _STEP, SCALE_DIGITS)


def _floor_scale(clip_long_pt: float) -> float:
    """The least scale whose clip has a long side of at least :data:`MIN_LONG_SIDE_PX`.

    The integer clip is never shorter than ``side_pt * scale - 0.5`` (the canvas is rounded
    to the nearest pixel, the clip's edges outward), so ``(800 + 0.5) / side_pt`` suffices.
    """
    return _round_up((MIN_LONG_SIDE_PX + _ROUNDING_LOSS) / clip_long_pt)


def _cap_scale(clip_width_pt: float, clip_height_pt: float) -> float:
    """The greatest scale whose clip holds at most :data:`MAX_PIXELS` pixels.

    The integer clip is never longer than ``side_pt * scale + 2.5`` per side (half a pixel
    of canvas rounding, a pixel at each outward edge), so the scale is the positive root of
    ``(w * s + 2.5) * (h * s + 2.5) = MAX_PIXELS``.
    """
    a = clip_width_pt * clip_height_pt
    b = _ROUNDING_GAIN * (clip_width_pt + clip_height_pt)
    c = _ROUNDING_GAIN**2 - MAX_PIXELS
    return _round_down((-b + math.sqrt(b * b - 4 * a * c)) / (2 * a))


def plan_crop(
    bbox_norm: tuple[float, float, float, float],
    page_width_pt: float,
    page_height_pt: float,
    base: float,
) -> CropPlan:
    """The crop of ``bbox_norm`` on a displayed page, under the floor and the cap.

    ``scale = min(max(base, floor), cap)``: the base raised to the floor, then lowered to
    the cap, which wins (module docstring). Both bounds are computed with the integer clip's
    worst rounding included, so the plan meets them by construction, not by a search.
    """
    bbox = _validated_bbox(bbox_norm)
    if not (page_width_pt > 0 and page_height_pt > 0):
        raise DegenerateCrop("a page has a positive width and height")
    clip_width = (bbox[2] - bbox[0]) * page_width_pt
    clip_height = (bbox[3] - bbox[1]) * page_height_pt
    scale = round(base, SCALE_DIGITS) if math.isfinite(base) and base > 0 else 0.0
    scale = max(scale, _floor_scale(max(clip_width, clip_height)))  # the floor
    scale = min(scale, _cap_scale(clip_width, clip_height))  # the cap, which wins
    plan = _layout(bbox, page_width_pt, page_height_pt, scale)
    if plan.pixels > MAX_PIXELS:  # pragma: no cover - excluded by _cap_scale's bound
        raise DegenerateCrop("the crop exceeds the pixel budget")
    return plan


__all__ = [
    "GEOMETRY_MISMATCH",
    "GEOMETRY_OK",
    "MAX_CANVAS_SIDE",
    "MAX_PIXELS",
    "MIN_LONG_SIDE_PX",
    "PAGE_BOX_TOLERANCE",
    "ROTATIONS",
    "SCALE_DIGITS",
    "Box",
    "CropPlan",
    "DegenerateCrop",
    "aspect_deviation",
    "base_scale",
    "check_page",
    "displayed_size",
    "effective_box",
    "normalised_rotation",
    "plan_crop",
]
