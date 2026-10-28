"""Page B laid onto page A's grid (`CMP-VIEWER-01`): exact where it can be, bounded where it cannot."""

from __future__ import annotations

import numpy
import pytest

from auditmanager.comparison.tiles.grid import Affine
from auditmanager.comparison.tiles.warp import (
    Region,
    SourceBudget,
    TooManySourceTiles,
    choose_source_level,
    warp_region,
)

IDENTITY = Affine.from_sequence([1, 0, 0, 1, 0, 0])


def _tile_of(pyramid, level: int, column: int, row: int):
    return pyramid.fetch(level, column, row)


def _warp(a, b, to_a, level: int, column: int, row: int, budget: SourceBudget | None = None, region: Region | None = None):
    info = a.grid.level(level)
    width = min(512, info.width_px - column * 512)
    height = min(512, info.height_px - row * 512)
    return warp_region(
        b.fetch, budget or SourceBudget(), grid_a=a.grid, level_a=level, origin=(column * 512, row * 512),
        region=region or Region(0, 0, width, height), grid_b=b.grid, to_a=to_a,
    )


def test_the_identity_is_the_page_itself_at_every_level_and_every_tile(support) -> None:
    page = support.noise_page(1300, 900)
    a, b = support.Pyramid(page), support.Pyramid(page)
    for level in (0, 1, 2):
        info = a.grid.level(level)
        for column in range(info.columns):
            for row in range(info.rows):
                assert numpy.array_equal(_warp(a, b, IDENTITY, level, column, row), a.fetch(level, column, row)), (level, column, row)


def test_a_translation_moves_the_page_by_exactly_that_many_pixels(support) -> None:
    """At 72 dpi a pixel is a point. B's content is 10 points to the right and 4 down of A's, so the transform
    that maps B onto A moves it back by (-10, -4): output(x, y) = B(x + 10, y + 4)."""
    page = support.noise_page(900, 700)
    a, b = support.Pyramid(page), support.Pyramid(page)
    shifted = Affine.from_sequence([1, 0, 0, 1, -10, -4])
    out = _warp(a, b, shifted, 0, 0, 0)
    assert numpy.array_equal(out, page[4:516, 10:522])
    # the tile to the right takes its pixels from B's neighbouring tiles
    out = _warp(a, b, shifted, 0, 1, 0)
    assert out.shape == (512, 388, 3)
    assert numpy.array_equal(out[:, :378], page[4:516, 522:900])
    # beyond B's page there is white paper
    assert (out[:, 378:] == 255).all()
    below = _warp(a, b, shifted, 0, 0, 1)
    assert below.shape == (188, 512, 3) and numpy.array_equal(below[:184], page[516:700, 10:522])
    assert (below[184:] == 255).all()


def test_a_scale_of_two_reads_a_coarser_level_of_b(support) -> None:
    """B is A's page drawn half the size at the same dpi: the transform doubles it, and B is read one level DOWN
    (finer) so that an output pixel spans one source pixel."""
    page = support.noise_page(2048, 1536)
    small = page[::2, ::2]
    a, b = support.Pyramid(page), support.Pyramid(small)
    assert choose_source_level(a.grid, 0, b.grid, Affine.from_sequence([2, 0, 0, 2, 0, 0])) == 0
    assert choose_source_level(a.grid, 1, b.grid, Affine.from_sequence([2, 0, 0, 2, 0, 0])) == 0
    assert choose_source_level(a.grid, 2, b.grid, Affine.from_sequence([2, 0, 0, 2, 0, 0])) == 1
    out = _warp(a, b, Affine.from_sequence([2, 0, 0, 2, 0, 0]), 0, 0, 0)
    assert out.shape == (512, 512, 3)
    # Pixel centres: A(x, y) samples B at ((x + .5) / 2 - .5); even columns land between two B pixels (mean), odd on one.
    expected = (small[0:256, 0:256].astype(numpy.float32))
    assert abs(float(out[::2, ::2][:200, :200].mean()) - float(expected[:200, :200].mean())) < 6


def test_the_source_level_follows_the_resolution_ratio(support) -> None:
    page = support.noise_page(1024, 768)
    a, hi = support.Pyramid(page, dpi=72), support.Pyramid(page, dpi=144, width_pt=1024 / 72 * 72 / 2 * 1.0, height_pt=384)
    # B at twice A's dpi: one A pixel spans two B pixels at level 0, so level 1 of B matches level 0 of A.
    assert choose_source_level(a.grid, 0, hi.grid, IDENTITY) == 1
    assert choose_source_level(a.grid, 2, hi.grid, IDENTITY) == min(3, len(hi.grid.levels) - 1)


def test_a_region_outside_page_b_is_white_and_reads_nothing(support) -> None:
    page = support.noise_page(900, 700)
    a, b = support.Pyramid(page), support.Pyramid(page)
    far = Affine.from_sequence([1, 0, 0, 1, 5000, 5000])
    budget = SourceBudget()
    out = _warp(a, b, far, 0, 0, 0, budget)
    assert (out == 255).all() and budget.count == 0 and b.reads == []


def test_the_source_tiles_one_tile_needs_are_counted_and_bounded(support) -> None:
    page = support.noise_page(2600, 2600)
    a, b = support.Pyramid(page), support.Pyramid(page)
    # a mild transform: a 512 px output tile reads at most a 2 x 2 block of source tiles
    mild = Affine.from_sequence([1, 0, 0, 1, -100, -100])
    budget = SourceBudget()
    _warp(a, b, mild, 0, 2, 2, budget)
    assert 1 <= budget.count <= 4
    # a turn of 45 degrees with a strong shrink makes one output tile cover a large, tilted piece of page B
    wild = Affine.from_sequence([0.25, 0.25, -0.25, 0.25, 700, 0])
    probe = SourceBudget(limit=1000)
    _warp(a, b, wild, 0, 1, 1, probe)
    assert probe.count > 4
    with pytest.raises(TooManySourceTiles):
        _warp(a, b, wild, 0, 1, 1, SourceBudget(limit=4))
    with pytest.raises(TooManySourceTiles):
        _warp(a, b, mild, 0, 2, 2, SourceBudget(limit=0))


def test_the_budget_is_per_request_and_counts_a_tile_once(support) -> None:
    page = support.noise_page(1200, 900)
    a, b = support.Pyramid(page), support.Pyramid(page)
    budget = SourceBudget(limit=4)
    for _ in range(3):
        _warp(a, b, Affine.from_sequence([1, 0, 0, 1, -3, -3]), 0, 0, 0, budget)
    assert budget.count <= 4


def test_the_warp_of_a_region_equals_that_region_of_the_warp(support) -> None:
    page = support.noise_page(900, 700)
    a, b = support.Pyramid(page), support.Pyramid(page)
    t = Affine.from_sequence([1.0, 0.0, 0.0, 1.0, -6.25, 3.5])
    whole = _warp(a, b, t, 0, 0, 0)
    part = _warp(a, b, t, 0, 0, 0, region=Region(100, 50, 300, 200))
    assert numpy.array_equal(part, whole[50:200, 100:300])
