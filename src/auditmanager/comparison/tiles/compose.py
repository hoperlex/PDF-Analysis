"""The overlay: both pages on one canvas and the chosen layers painted over them.

`CMP-VIEWER-01`. The composition is the original's (``tiles.py:250-289`` and ``engine.py:410-423``): where the two pages
agree the ink keeps its own colour (the darker of the two pixels), and each selected mask layer is painted over them in
a solid colour, later layers over earlier ones; ``service_zones`` is a hatch tint over everything. A layer is painted as
a solid colour on purpose: at the top of the pyramid a changed pixel of the mask has been reduced by the maximum to a
whole pixel of the tile, and a translucent one would fade out.

The palette is the original's (``engine.py:30-42``) where the layers correspond, and one colour where the original had
two (``a_only`` red and ``b_only`` blue are one ``main`` plane here: the engine stores one plane for what is in one page
and not in the other). Colours here are PNG pixels, not stylesheet colours.

Images are ``(h, w, 3)`` ``uint8`` in OpenCV's channel order (BGR) from decoding to encoding; the palette is written in
RGB and reversed once.
"""

from __future__ import annotations

import struct
from collections.abc import Mapping
from typing import Final

import cv2
import numpy

from auditmanager.comparison.tiles.limits import PNG_COMPRESSION, TILE_PX

__all__ = ["DRAW_ORDER", "PALETTE_RGB", "TileUnreadable", "decode_png", "encode_png", "min_composite", "paint_layers"]

#: Painted bottom to top: the last one wins where two layers meet.
DRAW_ORDER: Final[tuple[str, ...]] = (
    "light_elements",
    "within_tolerance",
    "noise",
    "line_style",
    "moved",
    "color_change",
    "main",
)
PALETTE_RGB: Final[dict[str, tuple[int, int, int]]] = {
    "main": (212, 48, 58),
    "light_elements": (236, 160, 166),
    "color_change": (144, 69, 170),
    "line_style": (0, 150, 136),
    "moved": (40, 140, 60),
    "within_tolerance": (196, 178, 60),
    "noise": (120, 130, 150),
}
_ZONE_TINT_RGB: Final[tuple[int, int, int]] = (255, 230, 160)
_ZONE_WEIGHT: Final[float] = 0.18
_HATCH_PERIOD: Final[int] = 6
_PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"


class TileUnreadable(ValueError):
    """Stored tile bytes that are not a PNG of a size a tile can have."""


def decode_png(data: bytes) -> "numpy.ndarray":
    """A stored tile as a BGR array. The size is read from the header first: a tile is at most one tile wide."""
    if len(data) < 24 or data[:8] != _PNG_SIGNATURE:
        raise TileUnreadable("signature")
    width, height = struct.unpack(">II", data[16:24])
    if not (1 <= width <= TILE_PX and 1 <= height <= TILE_PX):
        raise TileUnreadable("size")
    image = cv2.imdecode(numpy.frombuffer(data, dtype=numpy.uint8), cv2.IMREAD_COLOR)
    if image is None or image.shape[:2] != (height, width):
        raise TileUnreadable("decode")
    return image


def encode_png(image: "numpy.ndarray") -> bytes:
    ok, encoded = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION])
    if not ok:  # pragma: no cover - cv2 fails only on an impossible array
        raise TileUnreadable("encode")
    return bytes(encoded)


def min_composite(page_a: "numpy.ndarray", page_b: "numpy.ndarray") -> "numpy.ndarray":
    """Both pages on one sheet: the darker pixel of the two (the original's ``np.minimum(a, b)``)."""
    return numpy.minimum(page_a, page_b)


def paint_layers(
    image: "numpy.ndarray", masks: Mapping[str, "numpy.ndarray"], origin: tuple[int, int]
) -> "numpy.ndarray":
    """Paint the ``bool`` masks (by layer name) over ``image`` in place and return it.

    ``origin`` is the tile's first pixel in its level: the hatch of ``service_zones`` is laid on the level's pixels, not
    on the tile's, so it runs unbroken across tile seams.
    """
    for name in DRAW_ORDER:
        mask = masks.get(name)
        if mask is not None:
            image[mask] = PALETTE_RGB[name][::-1]
    zones = masks.get("service_zones")
    if zones is not None and zones.any():
        height, width = zones.shape
        rows = numpy.arange(origin[1], origin[1] + height)[:, None]
        columns = numpy.arange(origin[0], origin[0] + width)[None, :]
        hatched = zones & (((rows + columns) // _HATCH_PERIOD) % 2 == 0)
        tint = numpy.array(_ZONE_TINT_RGB[::-1], dtype=numpy.float32)
        image[hatched] = (image[hatched].astype(numpy.float32) * (1.0 - _ZONE_WEIGHT) + tint * _ZONE_WEIGHT).astype(
            numpy.uint8
        )
    return image
