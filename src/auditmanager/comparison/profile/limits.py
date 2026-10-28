"""The numbers of the page profile, each with the decision that sets it.

`CMP-PROFILE-01`. ADR-0025 decisions 8 and 9 and the addendum of 2026-10-27 ("values from
CMP-MEASURE-01A", ``docs/program/compare/MEASURE-RENDER-01.md``) fix the ceilings and the caps;
this module restates them once so that the builder, the on-request tile path and the tests read
the same figures, and so that a test can lower one without editing the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from auditmanager.comparison.profile.child.geometry import (
    pyramid_levels,
    raster_size,
    registration_dpi,
)

__all__ = [
    "ALGO_VERSION",
    "ChildLimits",
    "EXTRACT_LIMITS",
    "FILE_BYTES",
    "FIRST_STORED_TILE_LEVEL",
    "MASK_DPI",
    "MASK_INK_BELOW",
    "MAX_ON_REQUEST_TILE_LEVEL",
    "MAX_REGISTRATION_DPI",
    "MIN_REGISTRATION_DPI",
    "MIB",
    "PIXEL_CAP",
    "PREVIEW_LONG_SIDE_PX",
    "REASON_FRAME_MISMATCH",
    "REASON_PAGE_TOO_LARGE",
    "REASON_RENDER_FAILED",
    "RENDER_LIMITS",
    "STATUS_NEEDS_REVIEW",
    "STATUS_READY",
    "STATUS_REFUSED",
    "THUMBNAIL_LONG_SIDE_PX",
    "TILE_LIMITS",
    "TILE_PX",
    "pyramid_levels",
    "raster_size",
    "registration_dpi",
    "render_settings",
]

MIB: Final[int] = 1024 * 1024

#: Names the algorithm that makes a profile. It is part of the content key and of the unique key
#: ``(version, page, algo_version)`` of the table: changing any rule below means a new value, and
#: the profiles of the old one stay as they are. At most 64 characters (``ck_..._algo_version``).
#: ``2``: the content Merkle covers the default visibility of the optional-content groups a page refers to
#: (``CMP-C1-FIX-A`` item 7), so the profiles of ``1`` are not current and a new preparation builds them again.
ALGO_VERSION: Final[str] = "cmp-profile/2"

STATUS_READY: Final[str] = "ready"
STATUS_NEEDS_REVIEW: Final[str] = "needs_review"
STATUS_REFUSED: Final[str] = "refused"
#: Any end of a child without a result (ADR-0025 addendum item 1): ``MemoryError``, a signal, a
#: CPU or wall stall, an exception. Never ``same``.
REASON_RENDER_FAILED: Final[str] = "RENDER_FAILED"
#: The page cannot be kept under the pixel cap at a useful dpi (decision 9). Not rendered.
REASON_PAGE_TOO_LARGE: Final[str] = "PAGE_TOO_LARGE"
#: PDFium and the extraction disagree about the displayed size of the page (more than half a point), so
#: the words and the raster cannot be laid over one another: the page is stored with what each saw and
#: is not trusted by the engine until someone looks.
REASON_FRAME_MISMATCH: Final[str] = "FRAME_MISMATCH"

# -- raster and pixels (decision 9) ------------------------------------------------------------
#: The working raster of a page: at most 40 Mpx.
PIXEL_CAP: Final[int] = 40_000_000
#: The registration dpi is ``min(200, floor(sqrt(40e6 / (w_in * h_in))))``...
MAX_REGISTRATION_DPI: Final[int] = 200
#: ...and a page that would need less than this is refused: below one pixel to the point a sheet is
#: not a drawing any more (an A1 plan is 6623 x 4678 at 200 dpi; the largest page this admits is
#: about 6300 x 6300 pt, 2.2 m a side).
MIN_REGISTRATION_DPI: Final[int] = 72
PREVIEW_LONG_SIDE_PX: Final[int] = 1400
THUMBNAIL_LONG_SIDE_PX: Final[int] = 220
TILE_PX: Final[int] = 512
#: The worker stores the pyramid from this level up (the addendum: levels 0 and 1 are 84 to 94 % of
#: its bytes) and renders levels 0 and 1 again on request.
FIRST_STORED_TILE_LEVEL: Final[int] = 2
MAX_ON_REQUEST_TILE_LEVEL: Final[int] = FIRST_STORED_TILE_LEVEL - 1
#: The ink mask: a 36 dpi grey render, a pixel is ink below this grey value (0 black, 255 white).
MASK_DPI: Final[int] = 36
MASK_INK_BELOW: Final[int] = 230
#: Any single file a child writes may not pass this (``RLIMIT_FSIZE``).
FILE_BYTES: Final[int] = 256 * MIB


@dataclass(frozen=True, slots=True)
class ChildLimits:
    """The ceilings of one child: address space in bytes, CPU seconds, wall seconds."""

    address_space: int
    cpu_seconds: int
    wall_seconds: float


#: Render, registration and tile children (addendum item 1): 768 MiB, 300 s CPU, 600 s wall, the wall
#: below the 900 s attempt watchdog of ``jobs/lease.py``.
RENDER_LIMITS: Final[ChildLimits] = ChildLimits(768 * MIB, 300, 600.0)
#: The child that runs pdfplumber words and lines: 1024 MiB (the heaviest real extraction needs
#: 704 MiB; VmPeak 658 to 674 MiB).
EXTRACT_LIMITS: Final[ChildLimits] = ChildLimits(1024 * MIB, 300, 600.0)
#: A tile child serves an HTTP request: the same memory and CPU ceilings, a wall clock that ends
#: inside the proxy's 300 s (an A1 tile takes well under a second).
TILE_LIMITS: Final[ChildLimits] = ChildLimits(768 * MIB, 300, 120.0)


def render_settings(**overrides: int) -> dict[str, int]:
    """The values of the render and tile jobs that define their output."""
    settings = {
        "pixel_cap": PIXEL_CAP,
        "max_dpi": MAX_REGISTRATION_DPI,
        "min_dpi": MIN_REGISTRATION_DPI,
        "preview_px": PREVIEW_LONG_SIDE_PX,
        "thumbnail_px": THUMBNAIL_LONG_SIDE_PX,
        "tile_px": TILE_PX,
        "first_stored_level": FIRST_STORED_TILE_LEVEL,
        "mask_dpi": MASK_DPI,
        "mask_ink_below": MASK_INK_BELOW,
    }
    settings.update(overrides)
    return settings
