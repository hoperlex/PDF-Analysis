"""Across levels the mask is reduced by the MAXIMUM of each block, so a one-pixel change never disappears
(`CMP-VIEWER-01`, ADR-0025 decision 9; the original's ``tiles.py:1-8``)."""

from __future__ import annotations

import math

import numpy
import pytest

from auditmanager.comparison.engine.mask_codec import LAYERS, decode_mask
from auditmanager.comparison.tiles.reduction import axis_starts, reduce_max

TILE = 512


def _tile(mask, layer: str, level: int, column: int, row: int, *, raster_dpi: int = 100, mask_dpi: int = 100):
    """One layer of one tile, the way the reader asks for it."""
    num, den = (1 << level) * mask_dpi, raster_dpi
    level_w = math.ceil(mask.width_px / (1 << level)) if mask_dpi == raster_dpi else math.ceil(
        mask.width_px * raster_dpi / mask_dpi / (1 << level))
    level_h = math.ceil(mask.height_px / (1 << level)) if mask_dpi == raster_dpi else math.ceil(
        mask.height_px * raster_dpi / mask_dpi / (1 << level))
    tw, th = min(TILE, level_w - column * TILE), min(TILE, level_h - row * TILE)
    xs, x_end = axis_starts(column * TILE, tw, num, den, mask.width_px)
    ys, y_end = axis_starts(row * TILE, th, num, den, mask.height_px)
    return reduce_max(mask.packed[LAYERS.index(layer)], xs, x_end, ys, y_end)


def _brute(planes: "numpy.ndarray", layer: int, level: int, column: int, row: int) -> "numpy.ndarray":
    """The definition: a pixel of the tile is set when any mask pixel of its 2**level block is."""
    f = 1 << level
    h, w = planes.shape[1:]
    tw = min(TILE, math.ceil(w / f) - column * TILE)
    th = min(TILE, math.ceil(h / f) - row * TILE)
    out = numpy.zeros((th, tw), dtype=bool)
    for v in range(th):
        for u in range(tw):
            y0, x0 = (row * TILE + v) * f, (column * TILE + u) * f
            out[v, u] = planes[layer, y0 : y0 + f, x0 : x0 + f].any()
    return out


def test_the_reduction_is_the_definition_at_every_level_for_random_masks(support) -> None:
    rng = numpy.random.default_rng(11)
    planes = rng.random((8, 700, 1300)) < 0.0007  # a few dozen lone pixels per plane
    mask = decode_mask(support.mask_blob(planes))
    for level in range(0, 4):
        f = 1 << level
        columns, rows = math.ceil(math.ceil(1300 / f) / TILE), math.ceil(math.ceil(700 / f) / TILE)
        for layer, name in ((0, "main"), (6, "noise")):
            for column in range(columns):
                for row in range(rows):
                    got = _tile(mask, name, level, column, row)
                    assert numpy.array_equal(got, _brute(planes, layer, level, column, row)), (level, column, row, name)


@pytest.mark.parametrize("x, y", [(0, 0), (1, 1), (6622, 4676), (3311, 2000), (7, 8), (4095, 4095)])
def test_one_lone_pixel_survives_at_every_level_of_an_a1_sized_mask(support, x: int, y: int) -> None:
    width, height = 6623, 4677  # A1 at 200 dpi
    planes = numpy.zeros((8, height, width), dtype=bool)
    planes[3, y, x] = True
    mask = decode_mask(support.mask_blob(planes))
    for level in range(0, 5):
        f = 1 << level
        column, row = (x // f) // TILE, (y // f) // TILE
        tile = _tile(mask, "line_style", level, column, row)
        assert tile.sum() == 1, level
        assert tile[(y // f) - row * TILE, (x // f) - column * TILE], level
        assert not _tile(mask, "main", level, column, row).any()


def test_a_mean_would_lose_it_so_the_guard_is_about_the_maximum(support) -> None:
    """The mutation the proof quotes: block mean >= 0.5 instead of the maximum drops a lone pixel at level 1."""
    planes = numpy.zeros((8, 8, 16), dtype=bool)
    planes[0, 3, 5] = True
    mask = decode_mask(support.mask_blob(planes))
    assert _tile(mask, "main", 1, 0, 0).sum() == 1
    blocks = planes[0].reshape(4, 2, 8, 2).mean(axis=(1, 3)) >= 0.5
    assert blocks.sum() == 0


def test_a_mask_coarser_than_the_raster_is_repeated_not_dropped(support) -> None:
    """Mask at 50 dpi on a 100 dpi raster: one mask pixel covers 2 x 2 raster pixels, nothing is lost."""
    planes = numpy.zeros((8, 40, 60), dtype=bool)
    planes[0, 10, 20] = True
    mask = decode_mask(support.mask_blob(planes))
    tile = _tile(mask, "main", 0, 0, 0, raster_dpi=100, mask_dpi=50)
    assert tile.shape == (80, 120) and tile.sum() == 4
    assert tile[20:22, 40:42].all()
    top = _tile(mask, "main", 1, 0, 0, raster_dpi=100, mask_dpi=50)
    assert top.shape == (40, 60) and top.sum() == 1 and top[10, 20]


def test_a_mask_finer_than_the_raster_with_a_ratio_that_is_not_a_whole_number_keeps_every_pixel(support) -> None:
    """Mask at 150 dpi on a 100 dpi raster (k = 1.5 at level 0): every mask pixel falls in exactly one block."""
    rng = numpy.random.default_rng(5)
    planes = rng.random((8, 90, 150)) < 0.01
    mask = decode_mask(support.mask_blob(planes))
    tile = _tile(mask, "main", 0, 0, 0, raster_dpi=100, mask_dpi=150)
    assert tile.shape == (60, 100)
    assert tile.sum() >= 1
    # Every set mask pixel lights the tile pixel whose block contains it (a block runs from its start to the next).
    xs, _ = axis_starts(0, 100, 3, 2, 150)
    ys, _ = axis_starts(0, 60, 3, 2, 90)
    rows, columns = numpy.nonzero(planes[0])
    assert len(rows) >= 1
    for y, x in zip(rows, columns, strict=True):
        assert tile[numpy.searchsorted(ys, y, side="right") - 1, numpy.searchsorted(xs, x, side="right") - 1]
    assert int(tile.sum()) <= len(rows)


def test_a_partial_tile_at_the_edge_reads_only_what_exists(support) -> None:
    planes = numpy.zeros((8, 10, 20), dtype=bool)
    planes[0, 9, 19] = True
    mask = decode_mask(support.mask_blob(planes))
    tile = _tile(mask, "main", 0, 0, 0)
    assert tile.shape == (10, 20) and tile[9, 19] and tile.sum() == 1
    tile = _tile(mask, "main", 2, 0, 0)
    assert tile.shape == (3, 5) and tile[2, 4] and tile.sum() == 1


def test_axis_starts_never_leave_the_plane() -> None:
    starts, end = axis_starts(0, 600, 1, 1, 20)  # a tile longer than the plane
    assert starts.max() <= 19 and end == 20 and numpy.all(numpy.diff(starts) >= 0)
