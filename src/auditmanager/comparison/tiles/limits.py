"""The numbers of the pair tile, each with the decision that sets it.

`CMP-VIEWER-01`. ADR-0025 decision 9 and the addendum of 2026-10-27 set the pixel cap and say that the API
reads bytes and reduces them with ``numpy``; the other figures are this lane's own and bound the work of ONE tile
request (the report measures what one request costs on a 2A0-sized mask).
"""

from __future__ import annotations

from typing import Final

from auditmanager.comparison.profile.limits import TILE_PX

__all__ = [
    "COMPOSE_SLOTS",
    "COMPOSE_WAIT_SECONDS",
    "DECODE_SLOTS",
    "MASK_CACHE_BYTES",
    "MASK_FORMAT",
    "MASK_HEADER_BYTES",
    "MASK_LAYER_COUNT",
    "MASK_MAGIC",
    "MAX_BLOCKS_PER_TILE",
    "MAX_PLANE_PIXELS",
    "MAX_SOURCE_TILES",
    "PNG_COMPRESSION",
    "SOURCE_ARCHIVE_CACHE_BYTES",
    "SOURCE_TILE_CACHE_BYTES",
    "TILE_PX",
]

#: Mask format 1 (wave brief C1 section 4 item 1): a 16-byte header ``<4sBBHII`` (magic, format, layer count, a
#: reserved ``H``, width, height), then ``zlib`` of the bit-packed planes.
MASK_MAGIC: Final[bytes] = b"AMCM"
MASK_FORMAT: Final[int] = 1
MASK_LAYER_COUNT: Final[int] = 8
MASK_HEADER_BYTES: Final[int] = 16
#: One plane is at most 40 Mpx (ADR-0025 decision 9): the pixel cap of the working raster, which is the grid of a mask.
MAX_PLANE_PIXELS: Final[int] = 40_000_000

#: The pages of one tile request: the tiles of page B that one request may read to build one tile (a tile of
#: 512 px at one source level needs 1 to 4; a rotated or strongly scaled transform needs more). Past it the
#: request is refused, not degraded.
MAX_SOURCE_TILES: Final[int] = 16
#: Aligned blocks (``align_blocks``) that may touch one tile; each is one small warp.
MAX_BLOCKS_PER_TILE: Final[int] = 64

#: Tiles composed at the same time in this process (CPU and memory of ``numpy``/OpenCV); a request that cannot get
#: a slot in :data:`COMPOSE_WAIT_SECONDS` answers ``dependency_unavailable`` and the viewer retries.
COMPOSE_SLOTS: Final[int] = 4
COMPOSE_WAIT_SECONDS: Final[float] = 30.0
#: Masks inflated at the same time: one decode holds the compressed bytes and the inflated planes (up to 40 MB).
DECODE_SLOTS: Final[int] = 2
#: Inflated masks kept for the next tile of the same pair (a viewer asks for a dozen at once). A 2A0 mask is
#: 40 MB inflated, so this keeps two of them.
MASK_CACHE_BYTES: Final[int] = 96 * 1024 * 1024
#: Decoded tiles of a page's pyramid (RGB arrays, up to 786 KB each) and stored archives of page profiles
#: (1 to 3 MB each) kept for the next tile.
SOURCE_TILE_CACHE_BYTES: Final[int] = 48 * 1024 * 1024
SOURCE_ARCHIVE_CACHE_BYTES: Final[int] = 32 * 1024 * 1024

#: PNG compression of the answer: tiles are viewed once, so speed wins over size.
PNG_COMPRESSION: Final[int] = 1
