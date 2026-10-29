"""The page-profile pyramid as arrays (`CMP-VIEWER-01`): stored levels from a cached archive, levels 0 and 1 from the
page-profile reader (which owns the child), and a tile that is not the size of its slot refused."""

from __future__ import annotations

import datetime
import hashlib

import numpy
import pytest

from auditmanager.comparison.profile.models import PageProfileRow
from auditmanager.comparison.profile.pack import build_pack
from auditmanager.comparison.tiles.compose import encode_png
from auditmanager.comparison.tiles.source import ProfileTiles
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id


class _Store:
    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}
        self.reads = 0

    def put(self, data: bytes) -> str:
        blob_id = str(derive_blob_id(sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
        self.blobs[blob_id] = data
        return blob_id

    def read(self, blob_id, *, verify: bool = True) -> bytes:
        self.reads += 1
        return self.blobs[str(blob_id)]


class _Reader:
    """Stands for ``PageProfileReader``: it serves rows and the on-request levels, and counts."""

    def __init__(self, row: PageProfileRow, rendered: dict[tuple[int, int, int], bytes]) -> None:
        self.row, self.rendered, self.rows_read, self.rendered_calls = row, rendered, 0, []

    def get_profile(self, page_profile_id: str) -> PageProfileRow:
        self.rows_read += 1
        return self.row

    def read_tile(self, page_profile_id: str, *, level: int, column: int, row: int) -> bytes:
        self.rendered_calls.append((level, column, row))
        return self.rendered[(level, column, row)]


def _world(support, *, break_tile: tuple[int, int, int] | None = None):
    page = support.noise_page(1300, 900)
    pyramid = support.Pyramid(page)
    store = _Store()
    stored, rendered = [], {}
    for level, image in enumerate(pyramid.images):
        info = pyramid.grid.level(level)
        for column in range(info.columns):
            for row in range(info.rows):
                tile = pyramid.fetch(level, column, row)
                if break_tile == (level, column, row):
                    tile = tile[:-1]  # one row short
                png = encode_png(tile)
                if info.stored:
                    stored.append((level, column, row, png))
                else:
                    rendered[(level, column, row)] = png
    archive = store.put(build_pack({"schema": "t"}, mask=None, tiles=stored))
    row = PageProfileRow(
        page_profile_id="cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV", version_uid="ver_x", page_number=1, content_key="k",
        algo_version="a", status="ready", reason=None, summary=pyramid.summary, profile_blob_id=archive,
        preview_blob_id=None, thumbnail_blob_id=None, created_at=datetime.datetime.now(datetime.UTC),
    )
    reader = _Reader(row, rendered)
    return pyramid, store, reader, ProfileTiles(reader, store)


def test_a_stored_level_comes_from_one_read_of_the_archive_and_a_rendered_one_from_the_reader(support) -> None:
    pyramid, store, reader, tiles = _world(support)
    row = tiles.profile("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    grid = tiles.grid(row)
    assert grid is not None and [lv.stored for lv in grid.levels] == [False, False, True]
    for level, column, tile_row in ((2, 0, 0), (2, 0, 0)):
        assert numpy.array_equal(tiles.array(row, grid, level, column, tile_row), pyramid.fetch(level, column, tile_row))
    assert store.reads == 1 and reader.rendered_calls == []
    tile = tiles.array(row, grid, 0, 1, 1)
    assert numpy.array_equal(tile, pyramid.fetch(0, 1, 1)) and reader.rendered_calls == [(0, 1, 1)]
    tiles.array(row, grid, 0, 1, 1)
    assert reader.rendered_calls == [(0, 1, 1)], "a decoded tile is kept"
    assert reader.rows_read == 1, "a frozen profile row is read once"


def test_a_tile_outside_the_pyramid_is_not_found(support) -> None:
    _, _, _, tiles = _world(support)
    row = tiles.profile("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    grid = tiles.grid(row)
    for level, column, tile_row in ((3, 0, 0), (0, 3, 0), (0, 0, 2), (2, 1, 0)):
        with pytest.raises(DomainError) as refused:
            tiles.array(row, grid, level, column, tile_row)
        assert refused.value.code is ErrorCode.NOT_FOUND, (level, column, tile_row)


def test_a_stored_tile_that_is_not_the_size_of_its_slot_is_an_integrity_error(support) -> None:
    _, _, _, tiles = _world(support, break_tile=(2, 0, 0))
    row = tiles.profile("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    with pytest.raises(DomainError) as refused:
        tiles.array(row, tiles.grid(row), 2, 0, 0)
    assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR


def test_a_tile_that_is_not_a_png_is_an_integrity_error(support) -> None:
    pyramid, store, reader, tiles = _world(support)
    reader.rendered[(0, 0, 0)] = b"GIF89a-not-a-png"
    row = tiles.profile("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    with pytest.raises(DomainError) as refused:
        tiles.array(row, tiles.grid(row), 0, 0, 0)
    assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR


def test_a_profile_without_a_pyramid_has_no_grid(support) -> None:
    _, _, reader, tiles = _world(support)
    row = tiles.profile("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    failed = PageProfileRow(
        page_profile_id=row.page_profile_id, version_uid=row.version_uid, page_number=1, content_key="k",
        algo_version="a", status="needs_review", reason="RENDER_FAILED", summary={"schema": "x"},
        profile_blob_id=None, preview_blob_id=None, thumbnail_blob_id=None, created_at=row.created_at,
    )
    assert tiles.grid(failed) is None
