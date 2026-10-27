"""Tiles of levels 0 and 1, rendered on request in a ceilinged child, never in this process.

`CMP-PROFILE-01`, ADR-0025 addendum of 2026-10-27: the worker stores previews, thumbnails and the tile
levels 2 and up; levels 0 and 1 (84 to 94 % of a pyramid's bytes) are rendered again when a viewer asks
for one, **in a child process under the 768 MiB ceiling**. This module is what the API process runs for
such a request, and it is why the API process never loads PDFium for a tile: it imports the standard
library and the runner (``subprocess``), starts :mod:`.child.program` in ``tile`` mode with a bare
environment and reads the PNG the child wrote. ``tests/unit/comparison/profile/test_api_never_loads_pdfium.py``
holds that to a fresh interpreter and ``sys.modules``.

**Bounded.** At most :data:`TILE_SLOTS` children run at once (the production host has 4 GiB beside the
API, the database and the object store); a request that cannot get a slot within :data:`SLOT_WAIT_SECONDS`
answers ``dependency_unavailable`` (``page_tile_render``), which a viewer retries, and a child that ends
without a result (overrun, signal, CPU or wall) answers the same: the tile is an interactive read, so the
typed reason ``RENDER_FAILED`` of a stored profile has no row to live in here. The source PDF comes from
a small cache of private temporary files (:class:`~auditmanager.comparison.profile.source.SourceFileCache`).
"""

from __future__ import annotations

import logging
import tempfile
import threading
from pathlib import Path
from typing import Any, Final

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.runner import ChildRunner, SubprocessChildRunner
from auditmanager.comparison.profile.source import SourceFileCache, SourceVersion
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "SLOT_WAIT_SECONDS", "TILE_SLOTS", "TileRenderer"]

DEPENDENCY: Final[str] = "page_tile_render"
TILE_SLOTS: Final[int] = 2
SLOT_WAIT_SECONDS: Final[float] = 30.0
_LOG = logging.getLogger(__name__)


class TileRenderer:
    """Renders one tile of a stored version's page in a child; thread-safe."""

    def __init__(
        self,
        *,
        runner: ChildRunner | None = None,
        cache: SourceFileCache | None = None,
        slots: int = TILE_SLOTS,
        slot_wait_seconds: float = SLOT_WAIT_SECONDS,
        tile_limits: limits.ChildLimits = limits.TILE_LIMITS,
    ) -> None:
        self._runner = runner
        self._cache = cache or SourceFileCache()
        self._slots = threading.BoundedSemaphore(slots)
        self._wait = slot_wait_seconds
        self._limits = tile_limits

    def _runner_or_default(self) -> ChildRunner:
        if self._runner is None:
            self._runner = SubprocessChildRunner()
        return self._runner

    def render(self, store: Any, source: SourceVersion, *, page_number: int, level: int, column: int, row: int) -> bytes:
        """The PNG of the tile, ``not_found`` when it is not in the pyramid, ``dependency_unavailable``
        when no slot is free or the child ended without a result."""
        if not self._slots.acquire(timeout=self._wait):
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)
        try:
            with self._cache.acquire(store, source) as path, tempfile.TemporaryDirectory(prefix="cmp-tile-") as out:
                result = self._runner_or_default().run(
                    {
                        "mode": "tile",
                        "pdf": path,
                        "page": page_number - 1,
                        "level": level,
                        "column": column,
                        "row": row,
                        "out_dir": out,
                        **limits.render_settings(),
                    },
                    self._limits,
                )
                if result.status == "range":
                    raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="PageTile")
                if not result.ok:
                    _LOG.warning("comparison_tile_render_failed end=%s stage=%s", result.end, result.stage)
                    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)
                return (Path(out) / "tile.png").read_bytes()
        finally:
            self._slots.release()
