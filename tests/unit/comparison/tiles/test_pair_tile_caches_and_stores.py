"""The bounded memory of the pair tile: a byte-budgeted LRU, one decode per mask, one read per archive
(`CMP-VIEWER-01`)."""

from __future__ import annotations

import hashlib
import threading
import time

import numpy
import pytest

from auditmanager.comparison.tiles.cache import ByteCache
from auditmanager.comparison.tiles.masks import MaskStore
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobNotFoundError, derive_blob_id


def test_a_key_is_loaded_once_however_many_threads_ask_at_once() -> None:
    cache: ByteCache[str, bytes] = ByteCache(1024)
    calls = []
    gate = threading.Event()

    def loader():
        calls.append(1)
        gate.wait(2)
        return b"x" * 100, 100

    results = []
    threads = [threading.Thread(target=lambda: results.append(cache.get_or_load("k", loader))) for _ in range(12)]
    for thread in threads:
        thread.start()
    time.sleep(0.2)
    gate.set()
    for thread in threads:
        thread.join(5)
    assert len(calls) == 1 and len(results) == 12 and cache.loads == 1


def test_the_budget_is_in_bytes_and_the_least_recently_used_goes_first() -> None:
    cache: ByteCache[str, bytes] = ByteCache(250)
    for key in "abc":
        cache.get_or_load(key, lambda k=key: (k.encode() * 100, 100))
    assert len(cache) == 2 and cache.size_bytes == 200
    cache.get_or_load("b", lambda: (b"never", 1))  # b is hit, so c is the oldest after d arrives
    cache.get_or_load("d", lambda: (b"d" * 100, 100))
    assert cache.get_or_load("b", lambda: (b"reloaded", 1)) == b"b" * 100
    assert cache.get_or_load("c", lambda: (b"c-again", 7)) == b"c-again"
    assert cache.size_bytes <= 250


def test_a_value_larger_than_the_whole_budget_is_returned_but_not_kept_and_a_failure_caches_nothing() -> None:
    cache: ByteCache[str, bytes] = ByteCache(100)
    assert cache.get_or_load("big", lambda: (b"y" * 500, 500)) == b"y" * 500
    assert len(cache) == 0 and cache.size_bytes == 0

    def fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        cache.get_or_load("k", fail)
    assert cache.get_or_load("k", lambda: (b"ok", 2)) == b"ok"


def test_a_waiter_after_a_failed_load_loads_for_itself() -> None:
    cache: ByteCache[str, bytes] = ByteCache(100)
    started, release = threading.Event(), threading.Event()
    outcome: dict[str, object] = {}

    def failing():
        started.set()
        release.wait(2)
        raise RuntimeError("first loader fails")

    def first():
        try:
            cache.get_or_load("k", failing)
        except RuntimeError as failure:
            outcome["first"] = str(failure)

    def second():
        outcome["second"] = cache.get_or_load("k", lambda: (b"second", 6))

    one = threading.Thread(target=first)
    one.start()
    started.wait(2)
    two = threading.Thread(target=second)
    two.start()
    time.sleep(0.1)
    release.set()
    one.join(5)
    two.join(5)
    assert outcome == {"first": "first loader fails", "second": b"second"}


class _FakeStore:
    """An object store that holds named blobs, counts reads and remembers how many reads overlapped."""

    def __init__(self, blobs: dict[str, bytes]) -> None:
        self.blobs = {str(derive_blob_id(sha256=hashlib.sha256(data).hexdigest(), size=len(data))): data for data in blobs.values()}
        self.ids = {name: str(derive_blob_id(sha256=hashlib.sha256(data).hexdigest(), size=len(data))) for name, data in blobs.items()}
        self.reads, self.active, self.peak = 0, 0, 0
        self._lock = threading.Lock()

    def read(self, blob_id, *, verify: bool = True) -> bytes:
        assert verify, "a stored blob is always read verified"
        with self._lock:
            self.reads += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.05)
        with self._lock:
            self.active -= 1
        try:
            return self.blobs[str(blob_id)]
        except KeyError:
            raise BlobNotFoundError(blob_id=str(blob_id)) from None


def _run_all(function, count: int) -> list:
    results: list = []
    errors: list = []

    def call():
        try:
            results.append(function())
        except Exception as failure:  # noqa: BLE001 - the test reports it
            errors.append(failure)

    threads = [threading.Thread(target=call) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(15)
    assert not errors, errors
    return results


def test_a_mask_is_downloaded_and_inflated_once_for_a_dozen_concurrent_tiles(support) -> None:
    store = _FakeStore({"m": support.mask_blob(numpy.zeros((8, 40, 80), dtype=bool))})
    masks = MaskStore(store)
    results = _run_all(lambda: masks.planes(store.ids["m"]), 12)
    assert store.reads == 1 and len(results) == 12 and all(r is results[0] for r in results)


def test_masks_are_inflated_at_most_decode_slots_at_a_time(support) -> None:
    blobs = {str(n): support.mask_blob(support.planes_with(8, 8, {"main": [(n, 0)]})) for n in range(6)}
    store = _FakeStore(blobs)
    masks = MaskStore(store, decode_slots=2)
    threads = [threading.Thread(target=lambda i=i: masks.planes(i)) for i in store.ids.values()]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(15)
    assert store.reads == 6 and store.peak <= 2


def test_a_blob_that_is_not_a_mask_is_an_integrity_error_and_is_read_again_next_time(support) -> None:
    store = _FakeStore({"bad": b"AMCM" + b"\0" * 40})
    masks = MaskStore(store)
    for attempt in (1, 2):
        with pytest.raises(DomainError) as refused:
            masks.planes(store.ids["bad"])
        assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR, attempt
    assert store.reads == 2 and len(masks.cache) == 0


def test_a_mask_blob_that_is_missing_is_not_found() -> None:
    store = _FakeStore({"other": b"x"})
    with pytest.raises(DomainError) as refused:
        MaskStore(store).planes(str(derive_blob_id(sha256="0" * 64, size=3)))
    assert refused.value.code is ErrorCode.NOT_FOUND


def test_the_mask_cache_holds_inflated_bytes_within_its_budget(support) -> None:
    blobs = {str(n): support.mask_blob(numpy.zeros((8, 100, 160), dtype=bool) | (numpy.arange(160) == n)) for n in range(4)}
    store = _FakeStore(blobs)
    one = 8 * 100 * 20
    masks = MaskStore(store, cache_bytes=2 * one + 10)
    for blob_id in store.ids.values():
        masks.planes(blob_id)
    assert len(masks.cache) == 2 and masks.cache.size_bytes == 2 * one
