"""The mask of a result, read with a bound (mask format 1).

`CMP-VIEWER-01`, ADR-0025 decision 9 and wave brief C1 section 4 item 1. The engine writes one blob per non-``same``
result: a 16-byte little-endian header ``struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width_px, height_px)`` and then
``zlib.compress(numpy.packbits(planes, axis=-1, bitorder="big").tobytes(), 6)``, where ``planes`` is a ``bool`` array of
shape ``(8, height_px, width_px)`` in the order of the contract enum ``ComparisonLayer``.

This module is the **reader** the brief asks the viewer to write against that text; the engine owns the codec
(``comparison/engine/mask_codec.py``), and at the integrator's call this file's :func:`read_mask` is replaced by its
``decode_mask`` (the one seam: :class:`MaskPlanes` is what the rest of the package takes).

**Bounded.** A blob is stored data, but it is read in the API process on a viewer's request, so nothing in it is
trusted to say how big it is: a wrong magic, format or layer count, a plane over 40 Mpx, and a body whose length after
inflation differs from ``8 * height_px * ceil(width_px / 8)`` are refused, and the inflation itself is limited to that
length plus one byte (``zlib.decompressobj().decompress(body, limit)``) -- never an unbounded ``zlib.decompress`` of a
stored body, which a few kilobytes can turn into gigabytes.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Final

import numpy

from auditmanager.comparison.tiles.limits import (
    MASK_FORMAT,
    MASK_HEADER_BYTES,
    MASK_LAYER_COUNT,
    MASK_MAGIC,
    MAX_PLANE_PIXELS,
)

__all__ = ["LAYER_NAMES", "MaskPlanes", "MaskRefused", "read_mask"]

#: The planes of a mask, in the order of the contract enum ``ComparisonLayer``.
LAYER_NAMES: Final[tuple[str, ...]] = (
    "main",
    "light_elements",
    "color_change",
    "line_style",
    "moved",
    "within_tolerance",
    "noise",
    "service_zones",
)
_HEADER: Final[struct.Struct] = struct.Struct("<4sBBHII")


class MaskRefused(ValueError):
    """The bytes are not a mask this reader admits. ``reason`` is a short stable word for the log."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class MaskPlanes:
    """The eight planes of one mask, bit-packed: ``data[layer, y, x // 8] >> (7 - x % 8) & 1`` is the pixel ``(x, y)``."""

    width_px: int
    height_px: int
    data: "numpy.ndarray"  # shape (8, height_px, ceil(width_px / 8)), dtype uint8

    @property
    def row_bytes(self) -> int:
        return (self.width_px + 7) // 8

    @property
    def nbytes(self) -> int:
        return int(self.data.nbytes)

    def plane(self, name: str) -> "numpy.ndarray":
        """The packed plane of one layer, shape ``(height_px, row_bytes)``."""
        return self.data[LAYER_NAMES.index(name)]


def read_mask(blob: bytes) -> MaskPlanes:
    """The planes of a mask blob, or :class:`MaskRefused`."""
    if len(blob) < MASK_HEADER_BYTES:
        raise MaskRefused("short_header")
    magic, fmt, layers, _reserved, width, height = _HEADER.unpack_from(blob, 0)
    if magic != MASK_MAGIC:
        raise MaskRefused("magic")
    if fmt != MASK_FORMAT:
        raise MaskRefused("format")
    if layers != MASK_LAYER_COUNT:
        raise MaskRefused("layer_count")
    if width < 1 or height < 1:
        raise MaskRefused("empty_plane")
    if width * height > MAX_PLANE_PIXELS:
        raise MaskRefused("plane_over_cap")
    row_bytes = (width + 7) // 8
    expected = MASK_LAYER_COUNT * height * row_bytes
    inflater = zlib.decompressobj()
    try:
        # One byte more than expected: a body that inflates to more is told from one that fits exactly.
        body = inflater.decompress(memoryview(blob)[MASK_HEADER_BYTES:], expected + 1)
    except zlib.error:
        raise MaskRefused("not_deflate") from None
    if len(body) != expected:
        raise MaskRefused("length")
    if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
        raise MaskRefused("length")
    data = numpy.frombuffer(body, dtype=numpy.uint8).reshape(MASK_LAYER_COUNT, height, row_bytes)
    return MaskPlanes(width_px=int(width), height_px=int(height), data=data)
