"""«Совмещать блоки» (wave brief C1 section 4 item 3): the part of page B inside ``box_a``, shifted by
``(-dx_pt, -dy_pt)`` after the transform; the old place erased; the layers not painted over either place."""

from __future__ import annotations

import numpy
import pytest

from auditmanager.comparison.tiles.aligned import (
    AlignedBlock,
    AlignedBlocksInvalid,
    TooManyBlocks,
    block_pixels,
    parse_aligned_blocks,
    warp_aligned,
)
from auditmanager.comparison.tiles.grid import Affine
from auditmanager.comparison.tiles.limits import MAX_BLOCKS_PER_TILE
from auditmanager.comparison.tiles.warp import SourceBudget

IDENTITY = Affine.from_sequence([1, 0, 0, 1, 0, 0])


def _page_with_square(support, width: int, height: int, x: int, y: int, side: int = 20):
    page = numpy.full((height, width, 3), 255, dtype=numpy.uint8)
    page[y : y + side, x : x + side] = 0
    return support.Pyramid(page)


def _aligned(a, b, blocks, column: int = 0, row: int = 0, to_a=IDENTITY, level: int = 0):
    info = a.grid.level(level)
    size = (min(512, info.width_px - column * 512), min(512, info.height_px - row * 512))
    return warp_aligned(
        b.fetch, SourceBudget(), blocks=blocks, grid_a=a.grid, level_a=level, origin=(column * 512, row * 512),
        size=size, grid_b=b.grid, to_a=to_a,
    ), size


def test_the_block_is_drawn_shifted_by_minus_d_and_its_old_place_is_erased(support) -> None:
    a = _page_with_square(support, 600, 400, 0, 0, 1)
    b = _page_with_square(support, 600, 400, 100, 100)
    block = AlignedBlock(95, 95, 125, 125, 30, 10)  # box_a on A's canvas, d = (30, 10)
    image, _ = _aligned(a, b, [block])
    assert (image[90:110, 70:90] == 0).all()  # the square, at (100, 100) - (30, 10)
    assert (image[100:120, 100:120] == 255).all()  # its old place: erased
    assert (image[90:110, 70:90].sum() == 0) and int((image == 0).all(axis=2).sum()) == 400


def test_without_blocks_it_is_the_plain_warp(support) -> None:
    a = _page_with_square(support, 600, 400, 0, 0, 1)
    b = _page_with_square(support, 600, 400, 100, 100)
    image, _ = _aligned(a, b, [])
    assert numpy.array_equal(image, b.fetch(0, 0, 0)[:, :])


def test_a_block_whose_new_place_is_on_another_tile_is_drawn_there(support) -> None:
    a = _page_with_square(support, 1200, 400, 0, 0, 1)
    b = _page_with_square(support, 1200, 400, 530, 100)  # in tile column 1
    block = AlignedBlock(525, 95, 555, 125, 40, 0)  # moves left across the seam: new place x 485..515
    first, _ = _aligned(a, b, [block], column=0)
    second, _ = _aligned(a, b, [block], column=1)
    assert (first[100:120, 490:510] == 0).all() and (first[100:120, 510:512] == 255).all()
    assert (second[100:120, 0:20] == 255).all()  # erased where it was
    assert (second == 0).all(axis=2).sum() == 0


def test_the_darker_pixel_wins_where_a_pasted_block_meets_other_ink(support) -> None:
    page = numpy.full((300, 300, 3), 255, dtype=numpy.uint8)
    page[100:120, 100:120] = 0       # the block
    page[100:120, 70:90] = 128       # other ink exactly where the block will land
    a = support.Pyramid(numpy.full((300, 300, 3), 255, dtype=numpy.uint8))
    b = support.Pyramid(page)
    image, _ = _aligned(a, b, [AlignedBlock(95, 95, 125, 125, 30, 0)])
    assert (image[100:120, 70:90] == 0).all()


def test_the_old_and_the_new_place_are_the_pixels_the_layers_are_not_painted_on(support) -> None:
    a = _page_with_square(support, 600, 400, 0, 0, 1)
    block = AlignedBlock(95, 95, 125, 125, 30, 10)
    area = block_pixels([block], a.grid, 0, (0, 0), (512, 400))
    assert area[95:125, 95:125].all() and area[85:115, 65:95].all()
    assert area.sum() == 2 * 30 * 30  # the two places do not overlap


def test_a_tile_touched_by_more_blocks_than_a_request_may_draw_is_refused(support) -> None:
    a = _page_with_square(support, 600, 400, 0, 0, 1)
    b = _page_with_square(support, 600, 400, 100, 100)
    blocks = [AlignedBlock(10 + i, 10, 20 + i, 20, 1, 1) for i in range(MAX_BLOCKS_PER_TILE + 1)]
    with pytest.raises(TooManyBlocks):
        _aligned(a, b, blocks)
    with pytest.raises(TooManyBlocks):
        block_pixels(blocks, a.grid, 0, (0, 0), (512, 400))
    _aligned(a, b, blocks[:MAX_BLOCKS_PER_TILE])


def test_a_block_away_from_the_tile_costs_nothing(support) -> None:
    a = _page_with_square(support, 1200, 400, 0, 0, 1)
    b = _page_with_square(support, 1200, 400, 100, 100)
    far = AlignedBlock(1000, 200, 1100, 300, 5, 5)
    plain, _ = _aligned(a, b, [])
    image, _ = _aligned(a, b, [far])
    assert numpy.array_equal(image, plain)


def test_the_result_is_read_strictly() -> None:
    assert parse_aligned_blocks(None) == () and parse_aligned_blocks([]) == ()
    block, = parse_aligned_blocks([{"box_a": [1, 2, 30, 40], "dx_pt": 1.5, "dy_pt": -2}])
    assert block == AlignedBlock(1.0, 2.0, 30.0, 40.0, 1.5, -2.0)
    for bad in ("x", {"box_a": [1, 2, 3, 4]}, [3], [{"box_a": [1, 2, 3], "dx_pt": 0, "dy_pt": 0}],
                [{"box_a": [5, 2, 3, 4], "dx_pt": 0, "dy_pt": 0}], [{"box_a": [1, 2, 3, 4], "dx_pt": "1", "dy_pt": 0}],
                [{"box_a": [1, 2, 3, 4], "dx_pt": 0}], [{"box_a": [1, 2, 3, float("nan")], "dx_pt": 0, "dy_pt": 0}],
                [{"box_a": [1, 2, 3, 4], "dx_pt": True, "dy_pt": 0}]):
        with pytest.raises(AlignedBlocksInvalid):
            parse_aligned_blocks(bad)
