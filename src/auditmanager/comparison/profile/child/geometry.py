"""Pure page, raster and pyramid arithmetic, shared by the worker and the child programs.

`CMP-PROFILE-01` (ADR-0025 decision 9 and the addendum of 2026-10-27). This file imports the
standard library only, because the child programs load it as a top-level module
(``child/program.py`` puts this directory on ``sys.path`` after the kernel ceilings are set) and
the product imports it as ``auditmanager.comparison.profile.child.geometry``: one rule, written
once, read by both sides.

**The registration dpi rule.** The working raster of a page is at most ``pixel_cap`` pixels
(40 Mpx). The dpi is ``min(max_dpi, floor(sqrt(pixel_cap / (w_in * h_in))))``, then lowered one
step at a time while the raster that PDFium actually allocates (``ceil`` of each side) is still
over the cap, and a page whose dpi would fall under ``min_dpi`` cannot be kept under the cap at a
resolution that is any use for registration: it is **refused**, not rendered at a lower dpi and
not clipped. The worked cases of the measurement (``MEASURE-RENDER-01`` finding 7): 1682 x 1189 mm
gives 113 dpi, 2102 x 594 mm gives 143 dpi, an A1 sheet gives the 200 dpi ceiling.

**The pyramid.** Level 0 is the working raster. Level ``n + 1`` is level ``n`` reduced by two
(``PIL.Image.reduce(2)``: ``ceil`` of each side), and the pyramid stops at the first level whose
long side is at most one tile. A level is cut into tiles of ``tile_px`` pixels from the top-left;
the last column and row are partial.
"""

from __future__ import annotations

import math
from typing import NamedTuple

__all__ = [
    "PT_PER_INCH",
    "PageRefused",
    "PyramidLevel",
    "TileOutOfRange",
    "pyramid_levels",
    "raster_size",
    "registration_dpi",
    "tile_box",
]

PT_PER_INCH = 72.0


class PageRefused(Exception):
    """The page cannot be kept under the pixel cap at a useful resolution. Not rendered."""

    def __init__(self, reason: str, width_pt: float, height_pt: float) -> None:
        super().__init__(reason)
        self.reason = reason
        self.width_pt = width_pt
        self.height_pt = height_pt


class TileOutOfRange(Exception):
    """The requested tile is not part of the page's pyramid, or not served on request."""


class PyramidLevel(NamedTuple):
    level: int
    width_px: int
    height_px: int
    columns: int
    rows: int


def raster_size(width_pt: float, height_pt: float, dpi: float) -> tuple[int, int]:
    """The pixel size PDFium allocates for a page of ``width_pt`` x ``height_pt`` at ``dpi``."""
    scale = dpi / PT_PER_INCH
    return max(1, math.ceil(width_pt * scale)), max(1, math.ceil(height_pt * scale))


def registration_dpi(
    width_pt: float, height_pt: float, *, pixel_cap: int, max_dpi: int, min_dpi: int
) -> int | None:
    """The dpi the page is rendered at, or ``None`` when the page is over the cap at ``min_dpi``."""
    if not (
        isinstance(width_pt, (int, float))
        and isinstance(height_pt, (int, float))
        and math.isfinite(width_pt)
        and math.isfinite(height_pt)
        and width_pt > 0
        and height_pt > 0
    ):
        return None
    area_in2 = (width_pt / PT_PER_INCH) * (height_pt / PT_PER_INCH)
    dpi = min(max_dpi, math.floor(math.sqrt(pixel_cap / area_in2)))
    while dpi >= min_dpi:
        width_px, height_px = raster_size(width_pt, height_pt, dpi)
        if width_px * height_px <= pixel_cap:
            return int(dpi)
        dpi -= 1
    return None


def pyramid_levels(width_px: int, height_px: int, tile_px: int) -> list[PyramidLevel]:
    """Every level of the pyramid of a ``width_px`` x ``height_px`` working raster."""
    levels: list[PyramidLevel] = []
    width, height, level = width_px, height_px, 0
    while True:
        levels.append(
            PyramidLevel(level, width, height, math.ceil(width / tile_px), math.ceil(height / tile_px))
        )
        if max(width, height) <= tile_px:
            return levels
        width, height, level = math.ceil(width / 2), math.ceil(height / 2), level + 1


def tile_box(
    level: PyramidLevel, column: int, row: int, tile_px: int
) -> tuple[int, int, int, int] | None:
    """``(left, top, right, bottom)`` of a tile in its level, or ``None`` when it is not there."""
    if not (0 <= column < level.columns and 0 <= row < level.rows):
        return None
    return (
        column * tile_px,
        row * tile_px,
        min((column + 1) * tile_px, level.width_px),
        min((row + 1) * tile_px, level.height_px),
    )
