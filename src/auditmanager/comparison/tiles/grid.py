"""The pyramid grid of a page and the affine that carries page B onto page A.

`CMP-VIEWER-01`. The grid of a pair tile is the pyramid of **page A's page profile** (`CMP-PROFILE-01`): 512 px tiles
cut from the working raster at the page's registration dpi, level ``n + 1`` being level ``n`` reduced by two. A tile of
any mode at one ``(level, column, row)`` therefore covers the same canvas square, which is what lets the viewer lay
page A, page B and the layers over one another and swipe between them.

Coordinates throughout are points of the page as displayed, origin at the top left (the page profile's frame); a pixel
of level ``n`` is ``72 * 2**n / dpi`` points wide.

**The transform.** ``how_compared.transform`` is ``[a, b, c, d, e, f]``, the affine that maps page B points onto page A
points. The order is the PDF matrix order (``fitz.Matrix(a, b, c, d, e, f)`` in the original,
``backend/.../engine.py:_fitz_matrix``): ``x' = a*x + c*y + e``, ``y' = b*x + d*y + f``. This is the one place the
convention is written.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from auditmanager.comparison.tiles.limits import TILE_PX

__all__ = ["Affine", "Level", "PageGrid", "TransformInvalid"]


class TransformInvalid(ValueError):
    """The stored transform is not six finite numbers of an invertible affine."""


@dataclass(frozen=True, slots=True)
class Level:
    level: int
    width_px: int
    height_px: int
    columns: int
    rows: int
    stored: bool


@dataclass(frozen=True, slots=True)
class PageGrid:
    """The working raster of one page and its pyramid, from the page profile's summary."""

    dpi: int
    width_px: int
    height_px: int
    width_pt: float
    height_pt: float
    tile_px: int
    levels: tuple[Level, ...]

    @classmethod
    def from_summary(cls, summary: Mapping[str, Any]) -> "PageGrid | None":
        """The grid of a profile, or ``None`` when the page has no pyramid (refused, or ended without a result)."""
        raster, tiles = summary.get("raster"), summary.get("tiles")
        if not isinstance(raster, Mapping) or not isinstance(tiles, Mapping):
            return None
        raw_levels = tiles.get("levels")
        if not isinstance(raw_levels, Sequence) or not raw_levels:
            return None
        try:
            levels = tuple(
                Level(
                    int(item["level"]), int(item["width_px"]), int(item["height_px"]),
                    int(item["columns"]), int(item["rows"]), bool(item["stored"]),
                )
                for item in raw_levels
            )
            grid = cls(
                dpi=int(raster["dpi"]), width_px=int(raster["width_px"]), height_px=int(raster["height_px"]),
                width_pt=float(summary["width_pt"]), height_pt=float(summary["height_pt"]),
                tile_px=int(tiles.get("tile_px") or TILE_PX), levels=levels,
            )
        except (KeyError, TypeError, ValueError):
            return None
        if grid.dpi < 1 or grid.width_px < 1 or grid.height_px < 1 or grid.tile_px < 1:
            return None
        if [item.level for item in levels] != list(range(len(levels))):
            return None
        return grid

    def level(self, number: int) -> Level | None:
        return self.levels[number] if 0 <= number < len(self.levels) else None

    def tile_box(self, level: int, column: int, row: int) -> tuple[int, int, int, int] | None:
        """``(left, top, right, bottom)`` of a tile in its level's pixels, or ``None`` when it is not in the pyramid."""
        info = self.level(level)
        if info is None or not (0 <= column < info.columns and 0 <= row < info.rows):
            return None
        left, top = column * self.tile_px, row * self.tile_px
        return left, top, min(left + self.tile_px, info.width_px), min(top + self.tile_px, info.height_px)

    def points_per_pixel(self, level: int) -> float:
        """The width of one pixel of ``level``, in points."""
        return 72.0 * (1 << level) / self.dpi


@dataclass(frozen=True, slots=True)
class Affine:
    """``x' = a*x + c*y + e``, ``y' = b*x + d*y + f``."""

    a: float
    b: float
    c: float
    d: float
    e: float
    f: float

    @classmethod
    def from_sequence(cls, values: object) -> "Affine":
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != 6:
            raise TransformInvalid("shape")
        numbers: list[float] = []
        for item in values:
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                raise TransformInvalid("number")
            numbers.append(float(item))
        transform = cls(*numbers)
        if abs(transform.determinant) < 1e-9:
            raise TransformInvalid("singular")
        return transform

    @property
    def determinant(self) -> float:
        return self.a * self.d - self.b * self.c

    @property
    def scale(self) -> float:
        """The mean linear scale: page A points per page B point."""
        return math.sqrt(abs(self.determinant))

    def apply(self, x: float, y: float) -> tuple[float, float]:
        return self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f

    def inverse(self) -> "Affine":
        det = self.determinant
        a, b, c, d = self.d / det, -self.b / det, -self.c / det, self.a / det
        return Affine(a, b, c, d, -(a * self.e + c * self.f), -(b * self.e + d * self.f))

    def translated(self, dx: float, dy: float) -> "Affine":
        """The same map followed by a move of ``(dx, dy)`` in the target."""
        return Affine(self.a, self.b, self.c, self.d, self.e + dx, self.f + dy)
