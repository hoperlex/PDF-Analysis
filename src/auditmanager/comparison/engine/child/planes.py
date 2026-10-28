"""Bit planes of the whole canvas, one bit a pixel, written and read a band or a window at a time.

`CMP-ENGINE-01`. A 40 Mpx canvas costs 5 MB a plane here and 40 MB as ``uint8``; the engine keeps a dozen planes and
unpacks only the rows of the band it works on or the window around a region. Packing is along the width, most
significant bit first, a row padded to a whole byte, which is the layout of the mask blob (``mask_codec``): the
planes of the mask are these arrays, stacked.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy

__all__ = ["PlaneStore"]

_POPCOUNT = numpy.array([bin(i).count("1") for i in range(256)], dtype=numpy.uint8)


class PlaneStore:
    def __init__(self, width: int, height: int, names: Iterable[str]) -> None:
        self.width = int(width)
        self.height = int(height)
        self.row_bytes = (self.width + 7) // 8
        self.data: dict[str, Any] = {name: numpy.zeros((self.height, self.row_bytes), dtype=numpy.uint8) for name in names}

    # -- whole rows (the band loop) --------------------------------------------------------------

    def put_rows(self, name: str, y0: int, rows: Any) -> None:
        """Store ``rows`` (``(n, width)``, anything truthy) at rows ``y0`` and below."""
        self.data[name][y0 : y0 + rows.shape[0]] = numpy.packbits(rows.astype(bool, copy=False), axis=1)

    def rows(self, name: str, y0: int, y1: int) -> Any:
        """Rows ``[y0, y1)`` as ``uint8`` zeros and ones, shape ``(y1 - y0, width)``."""
        return numpy.unpackbits(self.data[name][y0:y1], axis=1, count=self.width)

    # -- windows (the region analysis) -----------------------------------------------------------

    def window(self, name: str, x0: int, y0: int, x1: int, y1: int) -> Any:
        """The window ``[x0, x1) x [y0, y1)`` as ``uint8`` zeros and ones, clipped to the canvas."""
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(self.width, x1), min(self.height, y1)
        if x1 <= x0 or y1 <= y0:
            return numpy.zeros((max(0, y1 - y0), max(0, x1 - x0)), dtype=numpy.uint8)
        b0, b1 = x0 // 8, (x1 + 7) // 8
        unpacked = numpy.unpackbits(self.data[name][y0:y1, b0:b1], axis=1)
        return numpy.ascontiguousarray(unpacked[:, x0 - b0 * 8 : x1 - b0 * 8])

    def put_window(self, name: str, x0: int, y0: int, window: Any) -> None:
        """Replace the bits of the window whose top left is ``(x0, y0)`` (clipped to the canvas)."""
        h, w = window.shape
        x1, y1 = x0 + w, y0 + h
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(self.width, x1), min(self.height, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        window = window[cy0 - y0 : cy1 - y0, cx0 - x0 : cx1 - x0]
        b0, b1 = cx0 // 8, (cx1 + 7) // 8
        unpacked = numpy.unpackbits(self.data[name][cy0:cy1, b0:b1], axis=1)
        unpacked[:, cx0 - b0 * 8 : cx1 - b0 * 8] = window.astype(bool, copy=False)
        self.data[name][cy0:cy1, b0:b1] = numpy.packbits(unpacked, axis=1)

    def or_window(self, name: str, x0: int, y0: int, window: Any) -> None:
        current = self.window(name, x0, y0, x0 + window.shape[1], y0 + window.shape[0])
        self.put_window(name, max(0, x0), max(0, y0), current | (window[: current.shape[0], : current.shape[1]] > 0))

    # -- facts -------------------------------------------------------------------------------------

    def count(self, name: str) -> int:
        """The number of set pixels (the padding bits of a row are never set)."""
        return int(_POPCOUNT[self.data[name]].sum(dtype=numpy.int64))

    def any(self, name: str) -> bool:
        return bool(self.data[name].any())

    def packed(self, names: Iterable[str]) -> Any:
        """The named planes stacked ``(len(names), height, row_bytes)``, for the mask blob."""
        return numpy.stack([self.data[name] for name in names])
