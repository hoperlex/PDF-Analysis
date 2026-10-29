"""Builders and fixtures of the pair-tile unit tests (`CMP-VIEWER-01`).

``mask_blob`` writes a mask **per the text of wave brief C1 section 4 item 1** and not with the engine's codec: a
16-byte little-endian header ``struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width_px, height_px)`` and then
``zlib.compress(numpy.packbits(planes, axis=-1, bitorder="big").tobytes(), 6)`` for a ``bool`` array of shape
``(8, height_px, width_px)`` in the order of ``ComparisonLayer``. ``Pyramid`` is a page's tiles the way the page
profile cuts them: 512 px tiles of the working raster, level ``n + 1`` being level ``n`` reduced by two.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Iterable
from types import SimpleNamespace

import numpy
import pytest

from auditmanager.comparison.profile.child.geometry import pyramid_levels
from auditmanager.comparison.tiles.grid import PageGrid
from auditmanager.comparison.engine.mask_codec import LAYERS as LAYER_NAMES

TILE = 512


def mask_blob(planes: "numpy.ndarray", *, level: int = 6, reserved: int = 0, magic: bytes = b"AMCM",
              fmt: int = 1, layers: int = 8) -> bytes:
    height, width = planes.shape[1], planes.shape[2]
    header = struct.pack("<4sBBHII", magic, fmt, layers, reserved, width, height)
    return header + zlib.compress(numpy.packbits(planes, axis=-1, bitorder="big").tobytes(), level)


def planes_with(width: int, height: int, pixels: dict[str, Iterable[tuple[int, int]]]) -> "numpy.ndarray":
    planes = numpy.zeros((8, height, width), dtype=bool)
    for name, points in pixels.items():
        for x, y in points:
            planes[LAYER_NAMES.index(name), y, x] = True
    return planes


class Pyramid:
    """A synthetic page: level 0 is ``image`` (BGR), the other levels are 2 x 2 box averages (rounded up at the
    odd edge by repeating the last row/column, which is all the tests need)."""

    def __init__(self, image: "numpy.ndarray", dpi: int = 72, width_pt: float | None = None, height_pt: float | None = None):
        height, width = image.shape[:2]
        self.dpi = dpi
        self.images = [image]
        for _ in pyramid_levels(width, height, TILE)[1:]:
            previous = self.images[-1]
            h, w = previous.shape[:2]
            padded = numpy.pad(previous, ((0, h % 2), (0, w % 2), (0, 0)), mode="edge").astype(numpy.uint16)
            self.images.append(
                ((padded[0::2, 0::2] + padded[1::2, 0::2] + padded[0::2, 1::2] + padded[1::2, 1::2] + 2) // 4).astype(numpy.uint8)
            )
        levels = pyramid_levels(width, height, TILE)
        self.summary = {
            "width_pt": width_pt if width_pt is not None else width * 72.0 / dpi,
            "height_pt": height_pt if height_pt is not None else height * 72.0 / dpi,
            "raster": {"dpi": dpi, "width_px": width, "height_px": height},
            "tiles": {"tile_px": TILE, "levels": [
                {"level": item.level, "width_px": item.width_px, "height_px": item.height_px,
                 "columns": item.columns, "rows": item.rows, "stored": item.level >= 2} for item in levels]},
        }
        grid = PageGrid.from_summary(self.summary)
        assert grid is not None
        self.grid = grid
        self.reads: list[tuple[int, int, int]] = []

    def fetch(self, level: int, column: int, row: int):
        box = self.grid.tile_box(level, column, row)
        if box is None:
            return None
        self.reads.append((level, column, row))
        left, top, right, bottom = box
        return self.images[level][top:bottom, left:right].copy()


def noise_page(width: int, height: int, seed: int = 7) -> "numpy.ndarray":
    """A page of white paper with a few thousand dark marks: every shift of it is visible."""
    rng = numpy.random.default_rng(seed)
    page = numpy.full((height, width, 3), 255, dtype=numpy.uint8)
    for _ in range(max(40, width * height // 3000)):
        x, y = int(rng.integers(0, width - 3)), int(rng.integers(0, height - 3))
        page[y : y + 3, x : x + 3] = int(rng.integers(0, 120))
    return page


@pytest.fixture(scope="session")
def support() -> SimpleNamespace:
    """The builders above (a conftest cannot be imported by a test under the importlib import mode)."""
    return SimpleNamespace(
        mask_blob=mask_blob, planes_with=planes_with, Pyramid=Pyramid, noise_page=noise_page, TILE=TILE,
        packed_plane=lambda mask, name: mask.packed[LAYER_NAMES.index(name)],
    )
