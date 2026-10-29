"""A page's pyramid as arrays: the tiles of a page profile, kept for the next request.

`CMP-VIEWER-01`. The tiles of page A and page B are the page profile's (`CMP-PROFILE-01`): levels 2 and up are members of
the archive named by ``profile_blob_id``, levels 0 and 1 are rendered on request by the profile's ``TileRenderer`` in a
ceilinged child (two at a time). **This module never starts a process and never imports a PDF library**; for a rendered
level it calls the page-profile reader, which owns the child. What it adds is memory: a stored archive is read from the
object store once and opened once for the dozen tiles a viewer asks for together, and a decoded tile is kept (within a
byte budget) because page B's tiles are shared by neighbouring output tiles.
"""

from __future__ import annotations

from typing import Any

import numpy

from auditmanager.comparison.profile.models import PageProfileRow
from auditmanager.comparison.profile.pack import PackReader, PackUnreadable
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.tiles import errors
from auditmanager.comparison.tiles.cache import ByteCache
from auditmanager.comparison.tiles.compose import TileUnreadable, decode_png
from auditmanager.comparison.tiles.grid import PageGrid
from auditmanager.comparison.tiles.limits import SOURCE_ARCHIVE_CACHE_BYTES, SOURCE_TILE_CACHE_BYTES
from auditmanager.storage.public import BlobNotFoundError, StorageError, parse_blob_id

__all__ = ["ProfileTiles"]

_ROWS_KEPT = 512


class ProfileTiles:
    def __init__(
        self,
        reader: PageProfileReader,
        blob_store: Any,
        *,
        tile_cache_bytes: int = SOURCE_TILE_CACHE_BYTES,
        archive_cache_bytes: int = SOURCE_ARCHIVE_CACHE_BYTES,
    ) -> None:
        self._reader = reader
        self._store = blob_store
        self._tiles: ByteCache[tuple[str, int, int, int], numpy.ndarray] = ByteCache(tile_cache_bytes)
        self._archives: ByteCache[str, PackReader] = ByteCache(archive_cache_bytes)
        # A profile row is frozen once written, so it is kept by identity; a few hundred small objects.
        self._rows: ByteCache[str, PageProfileRow] = ByteCache(_ROWS_KEPT)

    def profile(self, page_profile_id: str) -> PageProfileRow:
        """The row of a page profile (``not_found`` if there is none)."""
        return self._rows.get_or_load(page_profile_id, lambda: (self._reader.get_profile(page_profile_id), 1))

    @staticmethod
    def grid(row: PageProfileRow) -> PageGrid | None:
        return PageGrid.from_summary(row.summary)

    def png(self, row: PageProfileRow, grid: PageGrid, level: int, column: int, tile_row: int) -> bytes:
        """The stored PNG of one tile; ``not_found`` outside the pyramid."""
        info = grid.level(level)
        if info is None or grid.tile_box(level, column, tile_row) is None:
            raise errors.not_found("PageTile")
        if not info.stored:
            # Levels 0 and 1: the page-profile reader renders it in a child under the kernel ceiling.
            return self._reader.read_tile(row.page_profile_id, level=level, column=column, row=tile_row)
        if row.profile_blob_id is None:
            raise errors.not_found("PageTile")
        archive = self._archive(row.profile_blob_id)
        data = archive.tile(level, column, tile_row)
        if data is None:
            raise errors.not_found("PageTile")
        return data

    def array(self, row: PageProfileRow, grid: PageGrid, level: int, column: int, tile_row: int) -> numpy.ndarray:
        """One tile as a BGR array of exactly the size its slot in the pyramid has."""

        def load() -> tuple[numpy.ndarray, int]:
            data = self.png(row, grid, level, column, tile_row)
            try:
                image = decode_png(data)
            except TileUnreadable as failure:
                raise errors.integrity(f"tile {failure} {row.page_profile_id} {level}/{column}/{tile_row}") from None
            left, top, right, bottom = grid.tile_box(level, column, tile_row)  # type: ignore[misc]
            if image.shape[:2] != (bottom - top, right - left):
                raise errors.integrity(f"tile size {row.page_profile_id} {level}/{column}/{tile_row}")
            image.setflags(write=False)
            return image, int(image.nbytes)

        return self._tiles.get_or_load((row.page_profile_id, level, column, tile_row), load)

    def _archive(self, blob_id: str) -> PackReader:
        def load() -> tuple[PackReader, int]:
            try:
                data = self._store.read(parse_blob_id(blob_id), verify=True)
            except BlobNotFoundError:
                raise errors.not_found("PageTile") from None
            except StorageError as failure:
                raise errors.storage_failure(failure, blob_id) from None
            try:
                return PackReader(data), len(data)
            except PackUnreadable:
                raise errors.integrity("archive", blob_id) from None

        return self._archives.get_or_load(blob_id, load)
