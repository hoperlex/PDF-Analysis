"""The mask blob, format 1: eight bit-packed planes of one comparison, one blob per pair that is not ``same``.

`CMP-ENGINE-01`, wave brief ``docs/program/dispatch/CMP-WAVE-C1.md`` section 4 item 1 (the binding text), ADR-0025
decision 9. The engine writes the blob in the worker; the viewer reads it, in the API process, which never calls
PDFium and reduces the planes with ``numpy``. This module is the one place that knows the bytes, and it imports
only the standard library and ``numpy``.

The bytes
---------
A 16-byte little-endian header, ``struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width_px, height_px)``: the magic, the
format (1), the number of planes (8), a reserved ``0`` and the size of the grid; then
``zlib.compress(numpy.packbits(planes, axis=-1, bitorder="big").tobytes(), 6)`` where ``planes`` is a ``bool``
array of shape ``(8, height_px, width_px)`` in the order of the contract enum ``ComparisonLayer``: ``main``,
``light_elements``, ``color_change``, ``line_style``, ``moved``, ``within_tolerance``, ``noise``,
``service_zones``. The grid covers the canvas of page A at ``how_compared.dpi``: ``width_px = ceil(width_pt * dpi /
72)``, likewise the height; pixel ``(x, y)`` is the square of the canvas from ``(x, y) * 72 / dpi`` points, the
origin at the top left. Each row of a plane is packed on its own (most significant bit first) and padded to a whole
byte, so the body of a decoded blob is ``8 * height_px * ceil(width_px / 8)`` bytes.

What a decoder refuses
----------------------
A wrong magic, format, number of planes or reserved word, a grid of no pixels, a plane of more than 40 Mpx
(decision 9), a body that decompresses to anything but the length above, and a body that would need more than
:data:`MAX_BODY_BYTES` once decompressed. **The decompression is bounded**: the decompressor is asked for at most the
expected length plus one byte, so a hostile or damaged blob that claims a small grid and expands to gigabytes is
refused after one small allocation, never inflated (an unbounded ``zlib.decompress`` of stored bytes is the failure
this module exists to avoid). **It is streamed**: the body is inflated a piece at a time into one array allocated at the
expected length, so the process holds the body once, not twice (:func:`_inflate_into`).
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Any, Final

import numpy

__all__ = [
    "COMPRESSION_LEVEL",
    "DecodedMask",
    "HEADER_BYTES",
    "LAYERS",
    "LAYER_COUNT",
    "MASK_FORMAT",
    "MASK_MAGIC",
    "MAX_BODY_BYTES",
    "MAX_PLANE_PIXELS",
    "MaskFormatError",
    "IN_CHUNK_BYTES",
    "OUT_CHUNK_BYTES",
    "body_bytes",
    "decode_mask",
    "encode_mask",
    "encode_packed_planes",
    "packed_width",
]

#: The format of the blob; a decoder refuses any other.
MASK_FORMAT: Final[int] = 1
MASK_MAGIC: Final[bytes] = b"AMCM"
#: The order of the planes: the contract enum ``ComparisonLayer``.
LAYERS: Final[tuple[str, ...]] = (
    "main",
    "light_elements",
    "color_change",
    "line_style",
    "moved",
    "within_tolerance",
    "noise",
    "service_zones",
)
LAYER_COUNT: Final[int] = len(LAYERS)
_HEADER: Final[struct.Struct] = struct.Struct("<4sBBHII")
HEADER_BYTES: Final[int] = _HEADER.size
#: A plane is at most 40 Mpx (ADR-0025 decision 9, the working-raster cap of the page profile).
MAX_PLANE_PIXELS: Final[int] = 40_000_000
#: The most a decoded body may hold: twice what eight 40 Mpx planes of byte-aligned rows need (40 MB). A grid one
#: pixel wide pads every row to a byte, so its body is eight times the pixel count; such a shape is no canvas.
MAX_BODY_BYTES: Final[int] = 80_000_000
COMPRESSION_LEVEL: Final[int] = 6
#: The decoder inflates one piece of at most this many bytes at a time into the buffer it allocated once, from slices of at
#: most this many compressed bytes (``CMP-C1-FIX-A`` item 6).
OUT_CHUNK_BYTES: Final[int] = 1 << 20
IN_CHUNK_BYTES: Final[int] = 1 << 16


class MaskFormatError(ValueError):
    """The bytes are not a mask blob of format 1 (the reason is a short code in ``args[0]``)."""


def packed_width(width_px: int) -> int:
    """Bytes in one packed row of ``width_px`` pixels."""
    return (int(width_px) + 7) // 8


def body_bytes(width_px: int, height_px: int) -> int:
    """The length of the decompressed body of a ``width_px`` x ``height_px`` mask."""
    return LAYER_COUNT * int(height_px) * packed_width(width_px)


def _check_grid(width_px: int, height_px: int) -> None:
    if width_px < 1 or height_px < 1:
        raise MaskFormatError("grid_empty")
    if width_px * height_px > MAX_PLANE_PIXELS:
        raise MaskFormatError("plane_over_cap")
    if body_bytes(width_px, height_px) > MAX_BODY_BYTES:
        raise MaskFormatError("body_over_cap")
    if width_px > 0xFFFFFFFF or height_px > 0xFFFFFFFF:  # pragma: no cover - the cap above is far lower
        raise MaskFormatError("grid_too_large")


def _header(width_px: int, height_px: int) -> bytes:
    return _HEADER.pack(MASK_MAGIC, MASK_FORMAT, LAYER_COUNT, 0, width_px, height_px)


def encode_mask(planes: Any, *, level: int = COMPRESSION_LEVEL) -> bytes:
    """The blob of ``planes``, a boolean array of shape ``(8, height_px, width_px)`` (``ComparisonLayer`` order)."""
    array = numpy.asarray(planes)
    if array.ndim != 3 or array.shape[0] != LAYER_COUNT:
        raise MaskFormatError("planes_shape")
    _, height_px, width_px = (int(v) for v in array.shape)
    _check_grid(width_px, height_px)
    packed = numpy.packbits(array.astype(bool, copy=False), axis=-1, bitorder="big")
    return _header(width_px, height_px) + zlib.compress(packed.tobytes(), level)


def encode_packed_planes(packed: Any, width_px: int, height_px: int, *, level: int = COMPRESSION_LEVEL) -> bytes:
    """The same blob, from planes already packed row by row.

    ``packed`` is a ``uint8`` array ``(8, height_px, ceil(width_px / 8))`` or a sequence of eight such planes
    ``(height_px, ceil(width_px / 8))``. The engine packs a band of rows at a time and never holds the eight planes
    unpacked (a 40 Mpx page would need 320 MB), and the sequence form lets it compress them one after the other
    without stacking them into one array (another 40 MB); packing is along the width only, so the bytes
    decompress to the body :func:`encode_mask` would build. The padding bits of the last byte of a row are cleared
    here, so the body equals the canonical one whatever the caller left in them (and the caller's arrays are not
    changed)."""
    width_px, height_px = int(width_px), int(height_px)
    planes = [numpy.asarray(plane) for plane in packed]
    shape = (height_px, packed_width(width_px))
    if len(planes) != LAYER_COUNT or any(p.dtype != numpy.uint8 or p.shape != shape for p in planes):
        raise MaskFormatError("planes_shape")
    _check_grid(width_px, height_px)
    spare = packed_width(width_px) * 8 - width_px
    keep = numpy.uint8((0xFF << spare) & 0xFF)
    compressor = zlib.compressobj(level)
    parts = [_header(width_px, height_px)]
    for plane in planes:
        if spare and (plane[:, -1] & ~keep).any():
            plane = plane.copy()
            plane[:, -1] &= keep
        parts.append(compressor.compress(numpy.ascontiguousarray(plane).data))
    parts.append(compressor.flush())
    return b"".join(parts)


@dataclass(frozen=True, slots=True)
class DecodedMask:
    """A decoded blob: the grid and the packed planes. Planes are unpacked on demand, one at a time."""

    width_px: int
    height_px: int
    #: ``uint8`` array ``(8, height_px, ceil(width_px / 8))``, the body as stored.
    packed: Any

    def plane(self, layer: str | int) -> Any:
        """One plane as a boolean array ``(height_px, width_px)``; ``layer`` is a name of :data:`LAYERS` or its index."""
        index = LAYERS.index(layer) if isinstance(layer, str) else int(layer)
        if not 0 <= index < LAYER_COUNT:
            raise IndexError(index)
        rows = numpy.unpackbits(self.packed[index], axis=-1, bitorder="big", count=self.width_px)
        return rows.astype(bool, copy=False)

    def planes(self) -> Any:
        """All eight planes as a boolean array ``(8, height_px, width_px)`` (up to 320 MB for a 40 Mpx grid)."""
        return numpy.stack([self.plane(index) for index in range(LAYER_COUNT)])


def _inflate_into(source: memoryview, expected: int) -> Any:
    """Inflate the zlib stream ``source`` into a buffer of exactly ``expected`` bytes allocated once, and return it.

    A one-call ``decompress`` builds the body in a growing output buffer and then copies it into the ``bytes`` it returns, so
    for a moment the 40 MB of a 2A0 mask are held twice (``CMP-VIEWER-01`` section 12 item 3: +75 MiB of resident set,
    where a streaming reader peaks at +41). Here the decompressor is asked for :data:`OUT_CHUNK_BYTES` at a time from at
    most :data:`IN_CHUNK_BYTES` of input, each piece is copied into the preallocated array, and the most that is ever held
    beyond the array is one piece and one slice of the compressed bytes.

    **Bounded**: a piece is never asked for more than one byte beyond what is still expected, so a stream that claims a small
    grid and expands to gigabytes stops after the one byte that proves it is too long; it is refused, never inflated.
    ``max_length`` of ``0`` means *no limit* to zlib, so the room is never allowed to reach it."""
    body: Any = None  # allocated when the first piece proves that the stream produces anything
    sink: memoryview | None = None
    decompressor = zlib.decompressobj()
    filled = position = 0
    try:
        while not decompressor.eof:
            room = expected + 1 - filled  # at least 1: filled > expected is refused below
            tail = decompressor.unconsumed_tail
            if tail:
                chunk = tail
            elif position < len(source):
                chunk = source[position : position + IN_CHUNK_BYTES]
                position += len(chunk)
            else:
                break  # the input is spent and the stream did not end
            piece = decompressor.decompress(chunk, min(room, OUT_CHUNK_BYTES))
            if filled + len(piece) > expected:
                raise MaskFormatError("body_length")
            if piece:
                if body is None:
                    body = numpy.empty(expected, dtype=numpy.uint8)
                    sink = memoryview(body)
                assert sink is not None
                sink[filled : filled + len(piece)] = piece
                filled += len(piece)
            if not piece and tail and decompressor.unconsumed_tail == tail:
                raise MaskFormatError("body_corrupt")  # no progress: neither output nor input was taken
    except zlib.error as failure:
        raise MaskFormatError("body_corrupt") from failure
    complete = body is not None and filled == expected and decompressor.eof
    if not complete or decompressor.unused_data or decompressor.unconsumed_tail or position < len(source):
        raise MaskFormatError("body_length")
    body.flags.writeable = False  # what a cache shares is never changed (the one-call decoder returned a read-only view too)
    return body


def decode_mask(data: bytes) -> DecodedMask:
    """Parse and verify a blob; :class:`MaskFormatError` for anything that is not format 1 of the stated size."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise MaskFormatError("not_bytes")
    view = memoryview(data)
    if len(view) < HEADER_BYTES:
        raise MaskFormatError("header_short")
    magic, version, layers, reserved, width_px, height_px = _HEADER.unpack_from(view)
    if magic != MASK_MAGIC:
        raise MaskFormatError("magic")
    if version != MASK_FORMAT:
        raise MaskFormatError("format")
    if layers != LAYER_COUNT:
        raise MaskFormatError("layer_count")
    if reserved != 0:
        raise MaskFormatError("reserved")
    _check_grid(width_px, height_px)
    body = _inflate_into(view[HEADER_BYTES:], body_bytes(width_px, height_px))
    packed = body.reshape(LAYER_COUNT, height_px, packed_width(width_px))
    return DecodedMask(width_px=width_px, height_px=height_px, packed=packed)
