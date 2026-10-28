"""Page B laid onto page A's tile grid.

`CMP-VIEWER-01`. The tile of ``mode=b`` and the lower sheet of an overlay are page B **warped onto page A's canvas** with
``how_compared.transform``: for every pixel of the output tile, find the point of page B that the transform sends there
and read page B's own pyramid at that point. Page B is never re-rendered here (the API never calls PDFium): its
tiles come from the page profile through a ``fetch`` callable, stored levels from the archive and levels 0 and 1 from a
ceilinged child.

**Which level of B.** One pixel of A's level ``L`` spans ``rho * 2**L`` pixels of B's level 0, where
``rho = (dpi_B / dpi_A) / scale(transform)``. B is read at level ``floor(log2(rho * 2**L))`` (never below 0): one output
pixel then spans one to two source pixels, so the bilinear sampling below does not alias. For two pages of equal dpi
and an identity transform this is level ``L`` of B itself and the warp is the identity.

**Bounded.** The source tiles one output tile needs are the tiles under the preimage of its corners plus a margin; the
count is checked **before** anything is fetched or allocated, and a transform that needs more than
:data:`~auditmanager.comparison.tiles.limits.MAX_SOURCE_TILES` is refused (:class:`TooManySourceTiles`).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy

from auditmanager.comparison.tiles.grid import Affine, PageGrid
from auditmanager.comparison.tiles.limits import MAX_SOURCE_TILES

__all__ = ["Region", "SourceBudget", "TooManySourceTiles", "choose_source_level", "warp_region"]

_WHITE = 255
_MARGIN_PX = 2

#: ``fetch(level, column, row)`` -> the decoded tile, an ``(h, w, 3)`` ``uint8`` array, or ``None`` outside the pyramid.
Fetch = Callable[[int, int, int], "numpy.ndarray | None"]


class TooManySourceTiles(Exception):
    """The tile needs more of page B than one request may read."""


@dataclass(frozen=True, slots=True)
class Region:
    """A rectangle of an output tile, in the tile's pixels: ``[left, right) x [top, bottom)``."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def empty(self) -> bool:
        return self.right <= self.left or self.bottom <= self.top

    def intersect(self, other: "Region") -> "Region":
        return Region(
            max(self.left, other.left), max(self.top, other.top),
            min(self.right, other.right), min(self.bottom, other.bottom),
        )


class SourceBudget:
    """Counts the distinct source tiles one request has asked for, and refuses the one past the limit."""

    def __init__(self, limit: int = MAX_SOURCE_TILES) -> None:
        self._limit = limit
        self._seen: set[tuple[int, int, int]] = set()

    def admit(self, keys: set[tuple[int, int, int]]) -> None:
        if len(self._seen | keys) > self._limit:
            raise TooManySourceTiles
        self._seen |= keys

    @property
    def count(self) -> int:
        return len(self._seen)


def choose_source_level(grid_a: PageGrid, level_a: int, grid_b: PageGrid, to_a: Affine) -> int:
    """The level of page B whose pixels are one to two per output pixel."""
    rho = (grid_b.dpi / grid_a.dpi) / to_a.scale
    wanted = math.floor(math.log2(rho * (1 << level_a)) + 1e-6)
    return max(0, min(wanted, len(grid_b.levels) - 1))


def _sampling(
    grid_a: PageGrid, level_a: int, origin: tuple[int, int], grid_b: PageGrid, level_b: int, to_a: Affine
) -> "numpy.ndarray":
    """The ``2 x 3`` matrix that sends an output pixel index ``(u, v)`` (relative to ``origin``, the tile's first
    pixel in level ``level_a``) to a pixel index of page B's level ``level_b``; pixel centres sit on integers."""
    back = to_a.inverse()
    ppp = grid_a.points_per_pixel(level_a)
    k_b = grid_b.dpi / (72.0 * (1 << level_b))
    x0, y0 = origin
    # The point on A of pixel (u, v) is ppp * (x0 + u + 0.5, y0 + v + 0.5); B is back(that); B's pixel index follows.
    centre_x, centre_y = ppp * (x0 + 0.5), ppp * (y0 + 0.5)
    return numpy.array(
        [
            [back.a * ppp * k_b, back.c * ppp * k_b, (back.a * centre_x + back.c * centre_y + back.e) * k_b - 0.5],
            [back.b * ppp * k_b, back.d * ppp * k_b, (back.b * centre_x + back.d * centre_y + back.f) * k_b - 0.5],
        ],
        dtype=numpy.float64,
    )


def warp_region(
    fetch: Fetch,
    budget: SourceBudget,
    *,
    grid_a: PageGrid,
    level_a: int,
    origin: tuple[int, int],
    region: Region,
    grid_b: PageGrid,
    to_a: Affine,
) -> "numpy.ndarray":
    """Page B warped onto ``region`` of the output tile; a white ``(region.height, region.width, 3)`` array where B has nothing.

    ``origin`` is the tile's first pixel in level ``level_a`` (``column * 512``, ``row * 512``); ``region`` is the
    part of the tile to fill, in the tile's pixels.
    """
    out_w, out_h = region.width, region.height
    level_b = choose_source_level(grid_a, level_a, grid_b, to_a)
    info = grid_b.level(level_b)
    assert info is not None
    # The tile's pixel (u, v) is the region's (u - region.left, v - region.top): shift the origin by the region.
    matrix = _sampling(grid_a, level_a, (origin[0] + region.left, origin[1] + region.top), grid_b, level_b, to_a)
    corners = numpy.array(
        [[0, 0, 1], [out_w - 1, 0, 1], [0, out_h - 1, 1], [out_w - 1, out_h - 1, 1]], dtype=numpy.float64
    )
    source = corners @ matrix.T
    tile_px = grid_b.tile_px
    first_col = math.floor((source[:, 0].min() - _MARGIN_PX) / tile_px)
    last_col = math.floor((source[:, 0].max() + _MARGIN_PX) / tile_px)
    first_row = math.floor((source[:, 1].min() - _MARGIN_PX) / tile_px)
    last_row = math.floor((source[:, 1].max() + _MARGIN_PX) / tile_px)
    first_col, last_col = max(first_col, 0), min(last_col, info.columns - 1)
    first_row, last_row = max(first_row, 0), min(last_row, info.rows - 1)
    white = numpy.full((out_h, out_w, 3), _WHITE, dtype=numpy.uint8)
    if first_col > last_col or first_row > last_row:
        return white  # the whole region lies outside page B
    keys = {(level_b, c, r) for c in range(first_col, last_col + 1) for r in range(first_row, last_row + 1)}
    budget.admit(keys)
    mosaic = numpy.full(
        ((last_row - first_row + 1) * tile_px, (last_col - first_col + 1) * tile_px, 3), _WHITE, dtype=numpy.uint8
    )
    for _, column, row in sorted(keys):
        tile = fetch(level_b, column, row)
        if tile is None:
            continue
        y, x = (row - first_row) * tile_px, (column - first_col) * tile_px
        mosaic[y : y + tile.shape[0], x : x + tile.shape[1]] = tile
    matrix[0, 2] -= first_col * tile_px
    matrix[1, 2] -= first_row * tile_px
    return cv2.warpAffine(
        mosaic, matrix, (out_w, out_h),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(_WHITE, _WHITE, _WHITE),
    )
