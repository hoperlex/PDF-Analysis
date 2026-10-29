"""«Совмещать блоки»: the blocks of page B that the engine found moved, drawn back where they belong.

`CMP-VIEWER-01`, wave brief C1 section 4 item 3. The result lists ``aligned_blocks``:
``[{"box_a": [x0, y0, x1, y1], "dx_pt": float, "dy_pt": float}]``, boxes on page A's canvas in points. With
``align_blocks=true`` the viewer draws the part of page B **inside ``box_a``** (page B after the transform) **shifted by
``(-dx_pt, -dy_pt)``**: the content of the block is moved onto the place it has on page A, and the PDF is not changed.

Per tile that is three steps over the warped page B: **erase** every block's ``box_a`` (the block is no longer there),
**paste** each block at ``box_a - d`` (page B sampled through the transform followed by the move, so a block that was
displaced by a fraction of a pixel stays sharp), taking the darker of the paste and what is already there. The mask
layers were computed for the unaligned pages, so over the old and the new place of a block they describe a state that
is no longer drawn: :func:`block_pixels` gives those places so the layers are not painted on them (the original does
the same: ``tiles.py:241-246`` and ``:270-275``).

A tile that more than :data:`~auditmanager.comparison.tiles.limits.MAX_BLOCKS_PER_TILE` blocks touch is refused, not
drawn partly.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy

from auditmanager.comparison.tiles.grid import Affine, PageGrid
from auditmanager.comparison.tiles.limits import MAX_BLOCKS_PER_TILE
from auditmanager.comparison.tiles.warp import Fetch, Region, SourceBudget, warp_region

__all__ = ["AlignedBlock", "AlignedBlocksInvalid", "TooManyBlocks", "block_pixels", "parse_aligned_blocks", "warp_aligned"]


class AlignedBlocksInvalid(ValueError):
    """``aligned_blocks`` of a stored result is not what wave brief C1 section 4 item 3 says."""


class TooManyBlocks(Exception):
    """More aligned blocks touch the tile than one request may draw."""


@dataclass(frozen=True, slots=True)
class AlignedBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    dx: float
    dy: float


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise AlignedBlocksInvalid("number")
    return float(value)


def parse_aligned_blocks(value: object) -> tuple[AlignedBlock, ...]:
    """The blocks of a result's ``aligned_blocks`` (absent or ``None`` is none), or :class:`AlignedBlocksInvalid`."""
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise AlignedBlocksInvalid("shape")
    blocks: list[AlignedBlock] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("box_a"), Sequence) or len(item["box_a"]) != 4:
            raise AlignedBlocksInvalid("block")
        x0, y0, x1, y1 = (_number(v) for v in item["box_a"])
        if x1 <= x0 or y1 <= y0:
            raise AlignedBlocksInvalid("box")
        blocks.append(AlignedBlock(x0, y0, x1, y1, _number(item.get("dx_pt")), _number(item.get("dy_pt"))))
    return tuple(blocks)


def _region(
    grid: PageGrid, level: int, origin: tuple[int, int], size: tuple[int, int], x0: float, y0: float, x1: float, y1: float
) -> Region:
    """The pixels of the tile that a rectangle of points touches (every pixel it overlaps)."""
    ppp = grid.points_per_pixel(level)
    left, top = math.floor(x0 / ppp) - origin[0], math.floor(y0 / ppp) - origin[1]
    right, bottom = math.ceil(x1 / ppp) - origin[0], math.ceil(y1 / ppp) - origin[1]
    return Region(left, top, right, bottom).intersect(Region(0, 0, size[0], size[1]))


def _places(
    blocks: Sequence[AlignedBlock], grid: PageGrid, level: int, origin: tuple[int, int], size: tuple[int, int]
) -> list[tuple[AlignedBlock, Region, Region]]:
    """``(block, old place, new place)`` in the tile's pixels for every block that touches the tile."""
    touching = []
    for block in blocks:
        old = _region(grid, level, origin, size, block.x0, block.y0, block.x1, block.y1)
        new = _region(
            grid, level, origin, size, block.x0 - block.dx, block.y0 - block.dy, block.x1 - block.dx, block.y1 - block.dy
        )
        if not (old.empty and new.empty):
            touching.append((block, old, new))
    if len(touching) > MAX_BLOCKS_PER_TILE:
        raise TooManyBlocks
    return touching


def block_pixels(
    blocks: Sequence[AlignedBlock], grid: PageGrid, level: int, origin: tuple[int, int], size: tuple[int, int]
) -> "numpy.ndarray":
    """The tile's pixels that are the old or the new place of an aligned block (``bool``, ``(height, width)``)."""
    area = numpy.zeros((size[1], size[0]), dtype=bool)
    for _, old, new in _places(blocks, grid, level, origin, size):
        for region in (old, new):
            if not region.empty:
                area[region.top : region.bottom, region.left : region.right] = True
    return area


def warp_aligned(
    fetch: Fetch,
    budget: SourceBudget,
    *,
    blocks: Sequence[AlignedBlock],
    grid_a: PageGrid,
    level_a: int,
    origin: tuple[int, int],
    size: tuple[int, int],
    grid_b: PageGrid,
    to_a: Affine,
) -> "numpy.ndarray":
    """Page B on the tile with its aligned blocks moved: the unaligned warp, the old places erased, the new ones pasted."""
    whole = Region(0, 0, size[0], size[1])
    image = warp_region(fetch, budget, grid_a=grid_a, level_a=level_a, origin=origin, region=whole, grid_b=grid_b, to_a=to_a)
    places = _places(blocks, grid_a, level_a, origin, size)
    for _, old, _new in places:
        if not old.empty:
            image[old.top : old.bottom, old.left : old.right] = 255
    for block, _old, new in places:
        if new.empty:
            continue
        patch = warp_region(
            fetch, budget, grid_a=grid_a, level_a=level_a, origin=origin, region=new, grid_b=grid_b,
            to_a=to_a.translated(-block.dx, -block.dy),
        )
        target = image[new.top : new.bottom, new.left : new.right]
        numpy.minimum(target, patch, out=target)
    return image
