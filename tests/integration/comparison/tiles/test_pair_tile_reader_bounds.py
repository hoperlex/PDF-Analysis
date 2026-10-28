"""The bounds of one tile request, with the real database and object store (`CMP-VIEWER-01`): one download of a mask
and of each archive for a dozen concurrent tiles, a limited number of tiles composed at once, and a request that cannot
get a slot answers `dependency_unavailable` instead of queueing without end."""

from __future__ import annotations

import threading
from typing import Any

import pytest

from auditmanager.comparison.tiles.reader import PairTileReader
from auditmanager.shared.errors import DomainError, ErrorCode

A1_W, A1_H = 6623, 4678


class _CountingStore:
    """The lane's object store, counting reads per blob."""

    def __init__(self, store: Any) -> None:
        self._store = store
        self.reads: dict[str, int] = {}
        self._lock = threading.Lock()

    def read(self, blob_id, *, verify: bool = True) -> bytes:
        with self._lock:
            self.reads[str(blob_id)] = self.reads.get(str(blob_id), 0) + 1
        return self._store.read(blob_id, verify=verify)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._store, name)


def test_a_dozen_concurrent_tiles_of_one_pair_read_the_mask_and_each_archive_once(session_factory, blob_store, world, make_pair, support) -> None:
    blob = support.packed_mask_blob(A1_W, A1_H, {"main": [(3001, 2003)], "noise": [(10, 10)]})
    pair = make_pair(mask=blob, result={"mask": {"format": 1, "dpi": 200, "width_px": A1_W, "height_px": A1_H}})
    store = _CountingStore(blob_store)
    reader = PairTileReader(session_factory, store)
    wanted = [(2, c, r) for c in range(4) for r in range(3)]  # level 2 is stored: 1656 x 1170 px, 4 x 3 tiles
    results: list[tuple[tuple[int, int, int], bytes]] = []
    failures: list[BaseException] = []

    def ask(key: tuple[int, int, int]) -> None:
        try:
            results.append((key, reader.read_tile(sheet_pair_id=pair, mode="overlay", level=key[0], column=key[1], row=key[2],
                                                  layers=["main", "noise"])))
        except BaseException as failure:  # noqa: BLE001
            failures.append(failure)

    threads = [threading.Thread(target=ask, args=(key,)) for key in wanted]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    assert failures == [] and len(results) == 12
    mask_id = _mask_blob_id(session_factory, pair)
    assert store.reads[mask_id] == 1
    archives = {blob_id: count for blob_id, count in store.reads.items() if blob_id != mask_id}
    assert len(archives) == 2 and set(archives.values()) == {1}, archives  # page A's archive and page B's, once each
    assert reader.masks.cache.loads == 1


def _mask_blob_id(session_factory, pair: str) -> str:
    from sqlalchemy import text

    from auditmanager.shared.db import session_scope

    with session_scope(session_factory) as session:
        return str(session.execute(
            text("SELECT r.mask_blob_id FROM comparison_sheet_pair p JOIN comparison_sheet_pair_result r "
                 "ON r.comparison_sheet_pair_result_id = p.result_id WHERE p.comparison_sheet_pair_id = :p"), {"p": pair}).scalar_one())


def test_a_request_that_cannot_get_a_compose_slot_is_refused_and_a_plain_page_tile_is_not_held_up(session_factory, blob_store, world, make_pair) -> None:
    pair = make_pair()
    reader = PairTileReader(session_factory, blob_store, slots=1, slot_wait_seconds=0.05)
    assert reader._slots.acquire(timeout=1)  # another request holds the only slot
    try:
        for mode in ("overlay", "b"):
            with pytest.raises(DomainError) as refused:
                reader.read_tile(sheet_pair_id=pair, mode=mode, level=2, column=0, row=0)
            assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
            assert refused.value.detail_fields == {"dependency": "comparison_pair_tiles"}
        assert reader.read_tile(sheet_pair_id=pair, mode="a", level=2, column=0, row=0).startswith(b"\x89PNG")
    finally:
        reader._slots.release()
    assert reader.read_tile(sheet_pair_id=pair, mode="overlay", level=2, column=0, row=0).startswith(b"\x89PNG")


def test_the_same_request_gives_the_same_bytes(session_factory, blob_store, world, make_pair, support) -> None:
    blob = support.packed_mask_blob(A1_W, A1_H, {"main": [(500, 500)], "service_zones": [(x, 600) for x in range(400, 700)]})
    pair = make_pair(mask=blob, result={"mask": {"format": 1, "dpi": 200, "width_px": A1_W, "height_px": A1_H}})
    reader = PairTileReader(session_factory, blob_store)
    first = reader.read_tile(sheet_pair_id=pair, mode="overlay", level=2, column=0, row=0, layers=["service_zones", "main"])
    second = PairTileReader(session_factory, blob_store).read_tile(
        sheet_pair_id=pair, mode="overlay", level=2, column=0, row=0, layers=["main", "service_zones"])
    assert first == second
