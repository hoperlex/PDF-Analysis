"""The API-side tile path (`CMP-PROFILE-01`): bounded children, typed answers, a bounded source cache.

No PDF here: the runner is a fake that records what it was asked and what ceilings it was given, so what is under
test is the policy -- how many children at once, what each kind of end becomes for a caller, what the cache keeps.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.runner import ChildResult
from auditmanager.comparison.profile.source import SourceFileCache, SourceVersion
from auditmanager.comparison.profile.tiles import DEPENDENCY, TileRenderer
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id

PNG = b"\x89PNG\r\n\x1a\n" + b"tile"


def _source(label: str, size: int = 100) -> SourceVersion:
    digest = (label * 64)[:64]
    return SourceVersion(
        "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", 3, digest, size,
        str(derive_blob_id(sha256=digest, size=size)),
    )


class _Store:
    def __init__(self) -> None:
        self.streams = 0

    def open_stream(self, blob_id, *, expected_sha256, expected_size, **_):
        self.streams += 1
        yield b"x" * expected_size


class _Runner:
    """Writes ``tile.png`` for ``ok``, or answers what it was told to."""

    def __init__(self, status: str = "ok", delay: float = 0.0) -> None:
        self.status, self.delay = status, delay
        self.calls: list[tuple[dict, limits.ChildLimits]] = []
        self.active = self.peak = 0
        self._lock = threading.Lock()

    def run(self, settings, child_limits) -> ChildResult:
        with self._lock:
            self.calls.append((dict(settings), child_limits))
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(self.delay)
            if self.status == "ok":
                (Path(settings["out_dir"]) / "tile.png").write_bytes(PNG)
            return ChildResult(self.status, facts={}, stage="render")
        finally:
            with self._lock:
                self.active -= 1


def _render(renderer: TileRenderer, store: _Store, source: SourceVersion | None = None) -> bytes:
    return renderer.render(store, source or _source("a"), page_number=2, level=1, column=3, row=4)


def test_a_tile_is_asked_of_one_child_with_the_ceilings_of_the_addendum() -> None:
    runner = _Runner()
    assert _render(TileRenderer(runner=runner, cache=SourceFileCache()), _Store()) == PNG
    settings, ceiling = runner.calls[0]
    assert (settings["mode"], settings["page"], settings["level"], settings["column"], settings["row"]) == ("tile", 1, 1, 3, 4)
    assert settings["pixel_cap"] == 40_000_000 and settings["tile_px"] == 512 and os.path.isabs(settings["pdf"])
    assert ceiling.address_space == 768 * 1024 * 1024 and ceiling.cpu_seconds == 300
    assert ceiling.wall_seconds <= 290, "an interactive read ends inside the BFF's and the proxy's clock"


@pytest.mark.parametrize("status", ["overrun", "cpu", "wall", "signal:SIGABRT", "error:ValueError", "refused", "exit:3"])
def test_a_child_that_ends_without_a_tile_is_dependency_unavailable_for_the_caller(status: str) -> None:
    with pytest.raises(DomainError) as raised:
        _render(TileRenderer(runner=_Runner(status), cache=SourceFileCache()), _Store())
    assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and dict(raised.value.detail_fields) == {"dependency": DEPENDENCY}


def test_a_tile_outside_the_pyramid_is_not_found() -> None:
    with pytest.raises(DomainError) as raised:
        _render(TileRenderer(runner=_Runner("range"), cache=SourceFileCache()), _Store())
    assert raised.value.code is ErrorCode.NOT_FOUND


def test_at_most_the_configured_children_run_at_once_and_a_request_without_a_slot_is_refused() -> None:
    runner = _Runner(delay=0.5)
    renderer = TileRenderer(runner=runner, cache=SourceFileCache(), slots=2, slot_wait_seconds=0.05)
    store, outcomes = _Store(), []

    def request() -> None:
        try:
            outcomes.append(_render(renderer, store))
        except DomainError as failure:
            outcomes.append(failure.code)

    threads = [threading.Thread(target=request) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert runner.peak == 2, "the bound of two children at once held"
    assert outcomes.count(PNG) == 2 and outcomes.count(ErrorCode.DEPENDENCY_UNAVAILABLE) == 3
    # The slots were all released: the next request is served.
    assert _render(TileRenderer(runner=_Runner(), cache=SourceFileCache(), slots=1), store) == PNG


def test_the_slot_is_released_when_the_child_fails() -> None:
    renderer = TileRenderer(runner=_Runner("overrun"), cache=SourceFileCache(), slots=1, slot_wait_seconds=0.05)
    for _ in range(3):
        with pytest.raises(DomainError) as raised:
            _render(renderer, _Store())
        assert raised.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and dict(raised.value.detail_fields) == {"dependency": DEPENDENCY}


def test_the_cache_streams_a_source_once_for_many_tiles_and_removes_its_files() -> None:
    cache, store, paths = SourceFileCache(), _Store(), []
    source = _source("b", 50)
    for _ in range(4):
        with cache.acquire(store, source) as path:
            paths.append(path)
            assert os.path.getsize(path) == 50
    assert store.streams == 1 and len(set(paths)) == 1 and len(cache) == 1
    cache.clear()
    assert len(cache) == 0 and not os.path.exists(paths[0])


def test_the_cache_is_bounded_in_files_and_keeps_a_file_that_is_in_use() -> None:
    cache, store = SourceFileCache(max_files=2, max_bytes=10**9), _Store()
    with cache.acquire(store, _source("1")) as busy:
        for label in ("2", "3", "4"):
            with cache.acquire(store, _source(label)):
                pass
        assert os.path.exists(busy), "a file a child may be reading is never evicted"
        assert len(cache) <= 3
    with cache.acquire(store, _source("5")):
        pass
    assert len(cache) == 2
    cache.clear()


def test_the_cache_is_bounded_in_bytes() -> None:
    cache, store = SourceFileCache(max_files=10, max_bytes=250), _Store()
    for label in ("1", "2", "3", "4"):
        with cache.acquire(store, _source(label, 100)):
            pass
    assert len(cache) == 2
    cache.clear()


def test_a_source_that_cannot_be_streamed_leaves_nothing_behind() -> None:
    class Broken:
        def open_stream(self, *args, **kwargs):
            raise OSError("the store went away")
            yield b""  # pragma: no cover

    cache = SourceFileCache()
    with pytest.raises(DomainError) as raised:
        with cache.acquire(Broken(), _source("9")):
            pass
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID and len(cache) == 0
