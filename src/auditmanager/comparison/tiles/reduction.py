"""Mask reduction across pyramid levels: the **maximum** of the block, so a one-pixel change never disappears.

`CMP-VIEWER-01`, ADR-0025 decision 9 and the original's ``tiles.py:1-8`` ("при уменьшении слои отличий берутся
МАКСИМУМОМ по блоку: мелкое отличие не исчезает при отдалении"). A tile of level ``L`` shows ``2**L`` pixels of the
mask grid in one pixel of its own; that pixel is set when **any** mask pixel in its block is set. A mean (or a nearest
pixel) would drop a lone changed pixel at the first zoom-out; the max cannot.

The planes are bit-packed, so the reduction is done on the packed bytes where it is cheap: the rows of a block are
OR-ed together as bytes (one eighth of the data), and only the strip that is left is unpacked and reduced across
columns. A 40 Mpx plane at the top of the pyramid costs a few megabytes of work, not a 40 MB unpack.

The grid of a mask need not be the grid of the page's raster (the engine registers at ``how_compared.dpi``, the
pyramid is cut at the page's registration dpi, and they are equal by the shared rule, but this module does not
assume it): a tile pixel covers ``k = 2**level * mask_dpi / raster_dpi`` mask pixels along each axis. For ``k >= 1``
every mask pixel belongs to exactly one tile pixel (blocks start at ``floor(i * k)``), so the max loses nothing; for
``k < 1`` the mask is coarser than the tile and a mask pixel is repeated.
"""

from __future__ import annotations

import numpy

__all__ = ["axis_starts", "reduce_max"]


def axis_starts(first: int, count: int, scale_num: int, scale_den: int, limit: int) -> tuple["numpy.ndarray", int]:
    """The block starts of ``count`` tile pixels beginning at pixel ``first``, and the end of the last block.

    ``scale_num / scale_den`` is ``k`` (mask pixels per tile pixel). Tile pixel ``i`` starts at mask pixel
    ``floor(i * k)``; the last block ends at ``ceil((first + count) * k)``. Both are clamped into ``[0, limit)`` /
    ``(0, limit]`` so a partial tile at the edge of the grid reads only what exists.
    """
    index = numpy.arange(first, first + count, dtype=numpy.int64)
    starts = (index * scale_num) // scale_den
    end = -((-(first + count) * scale_num) // scale_den)
    starts = numpy.minimum(starts, limit - 1)
    end = int(min(max(end, int(starts[-1]) + 1), limit))
    return starts, end


def reduce_max(
    plane: "numpy.ndarray",
    x_starts: "numpy.ndarray",
    x_end: int,
    y_starts: "numpy.ndarray",
    y_end: int,
) -> "numpy.ndarray":
    """One packed plane ``(height, ceil(width / 8))`` reduced to the tile: ``bool`` ``(len(y_starts), len(x_starts))``.

    ``x_starts`` / ``y_starts`` are the first mask column / row of each tile pixel (non-decreasing, inside the plane),
    ``x_end`` / ``y_end`` the end of the last block. A pixel is set when any mask pixel of its block is set.
    """
    y0, x0 = int(y_starts[0]), int(x_starts[0])
    if y_end <= y0 or x_end <= x0:
        return numpy.zeros((len(y_starts), len(x_starts)), dtype=bool)
    byte0, byte1 = x0 // 8, (x_end + 7) // 8
    window = plane[y0:y_end, byte0:byte1]
    rows = numpy.bitwise_or.reduceat(window, y_starts - y0, axis=0)
    bits = numpy.unpackbits(rows, axis=1)
    offset = x0 - byte0 * 8
    bits = bits[:, offset : offset + (x_end - x0)]
    return numpy.maximum.reduceat(bits, x_starts - x0, axis=1).astype(bool)
