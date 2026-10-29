"""A running worker reclaims a killed process's temporaries, not only at its start
(`DEBT-TEMP-SWEEP-01`, D-170).

The sweep itself (exact names, age, owner, links, errors) is proved in
``tests/unit/jobs/test_stale_temporaries.py``, and the two process starts that call it in
``tests/unit/runs/test_serving_start_sweeps_temporaries.py``. What neither can show: the sweep at
start takes only what is older than the live attempt's ceiling plus a minute, and the files of the
kill that *caused* the restart are younger, so they stay for as long as the worker is not
restarted again. These tests show that a **started worker service** sweeps again and again while it runs,
keeps going when a sweep fails, stops when the service stops, refuses a zero interval, and --
through the real sweep, with a clock moved forward -- removes the stale stage files, keeps a
file younger than the live margin and a file it did not write.

No database, no container: the service runs over a registry and a session factory that answer
and do nothing else, and a wake-up that only waits.
"""

from __future__ import annotations

import inspect
import logging
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from auditmanager.jobs import temporaries
from auditmanager.jobs.public import ATTEMPT_HARD_CAP_SECONDS, SweepReport
from auditmanager.workers import service as service_module
from auditmanager.workers.service import WorkerService, sweep_running_temporaries

SOURCE = "am-source-a1b2c3d4.pdf"
GEOMETRY = "am-geometry-e5f6g7h8.pdf"
BUNDLE = "auditmanager-bundle-i9j0k1l2"
FOREIGN = "drawing-notes.pdf"


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def commit(self) -> None:
        return None


class _Registry:
    """Registers, heartbeats and refuses intake: nothing here touches a database."""

    def register(self, _session: object, *, version: str, slots: int) -> str:
        return "wrk_unit"

    def heartbeat(self, _session: object, _worker_id: str) -> bool:
        return True

    def intake_enabled(self, _session: object, _worker_id: str) -> bool:
        return False


class _Jobs:
    def reclaim_expired(self, _session: object) -> None:
        return None

    def next_queued_run(self, _session: object) -> None:
        return None


class _QuietWakeup:
    listening = False

    def wait(self, timeout: float, *, stop: threading.Event) -> bool:
        stop.wait(timeout)
        return False

    def close(self) -> None:
        return None


@pytest.fixture
def make_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., WorkerService]]:
    monkeypatch.setattr(service_module, "JobRepository", _Jobs)
    made: list[WorkerService] = []

    def make(**options: Any) -> WorkerService:
        service = WorkerService(
            engine=cast(Any, None), session_factory=cast(Any, _Session),
            execute=lambda _run, _worker: None, version="unit", registry=cast(Any, _Registry()),
            heartbeat_seconds=3600.0, **options,
        )
        service.wakeup = cast(Any, _QuietWakeup())
        made.append(service)
        return service

    try:
        yield make
    finally:
        for service in made:
            service.stop()


class _CountingSweep:
    """Counts its calls; may raise on the first; says when it has been called ``wanted`` times."""

    def __init__(self, wanted: int, *, first_raises: bool = False) -> None:
        self.calls = 0
        self._first_raises = first_raises
        self.enough = threading.Event()
        self._wanted = wanted

    def __call__(self) -> SweepReport:
        self.calls += 1
        if self.calls >= self._wanted:
            self.enough.set()
        if self._first_raises and self.calls == 1:
            raise RuntimeError("the sweep itself failed")
        return SweepReport()


def test_a_started_worker_sweeps_again_and_again_and_stops_sweeping_when_it_stops(
    make_service: Callable[..., WorkerService],
) -> None:
    sweep = _CountingSweep(wanted=3)
    service = make_service(temporaries_sweep=sweep, temporaries_sweep_seconds=0.02)

    service.start()
    assert sweep.enough.wait(timeout=10), f"only {sweep.calls} sweep(s) ran while the worker ran"
    service.stop()

    settled = sweep.calls
    time.sleep(0.3)
    assert sweep.calls == settled, "the sweep went on after the service stopped"


def test_a_sweep_that_raises_is_logged_at_error_and_the_next_pass_still_runs(
    make_service: Callable[..., WorkerService], caplog: pytest.LogCaptureFixture,
) -> None:
    sweep = _CountingSweep(wanted=3, first_raises=True)
    service = make_service(temporaries_sweep=sweep, temporaries_sweep_seconds=0.02)

    with caplog.at_level(logging.ERROR, logger="auditmanager.workers.service"):
        service.start()
        assert sweep.enough.wait(timeout=10), "the loop died with the sweep's first failure"
        service.stop()

    failures = [r for r in caplog.records if "temporaries sweep failed" in r.getMessage()]
    assert len(failures) == 1
    assert failures[0].levelno == logging.ERROR and failures[0].exc_info is not None
    assert "wrk_unit" in failures[0].getMessage()
    assert not service.failed, "housekeeping must not take the worker down"


@pytest.mark.parametrize("seconds", [0, -1.0])
def test_a_service_refuses_an_interval_that_would_spin(seconds: float) -> None:
    with pytest.raises(ValueError, match="positive interval"):
        WorkerService(
            engine=cast(Any, None), session_factory=cast(Any, _Session),
            execute=lambda _run, _worker: None, version="unit",
            temporaries_sweep_seconds=seconds,
        )


def test_the_default_interval_is_minutes_and_the_default_sweep_is_the_running_one() -> None:
    parameters = inspect.signature(WorkerService.__init__).parameters
    assert parameters["temporaries_sweep"].default is sweep_running_temporaries
    assert 60 <= parameters["temporaries_sweep_seconds"].default <= 3600


# --- the real sweep, behind a clock that can be moved forward --------------------------------


class _Directory:
    """A temporary directory the real sweep reads, and the clock it reads the age against."""

    def __init__(self, path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.path = path
        monkeypatch.setattr(tempfile, "tempdir", str(path))
        self._moment = time.time()
        monkeypatch.setattr(temporaries, "time", SimpleNamespace(time=lambda: self._moment))
        self.created = time.time()

    def advance_to(self, seconds_after_creation: float) -> None:
        self._moment = self.created + seconds_after_creation

    def populate(self) -> None:
        (self.path / SOURCE).write_bytes(b"%PDF-1.7\n" + b"x" * 1000)
        (self.path / GEOMETRY).write_bytes(b"%PDF-1.7\n" + b"y" * 1000)
        bundle = self.path / BUNDLE
        bundle.mkdir()
        (bundle / "member.pdf").write_bytes(b"%PDF-1.7\n" + b"z" * 500)
        (self.path / FOREIGN).write_bytes(b"not ours")

    def names(self) -> set[str]:
        return {entry.name for entry in self.path.iterdir()}


@pytest.fixture
def directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Directory:
    return _Directory(tmp_path, monkeypatch)


def test_the_running_sweep_leaves_what_a_live_attempt_could_still_hold(directory: _Directory) -> None:
    directory.populate()
    # 200 s past a live attempt's ceiling: beyond the start sweep's minute, short of the live
    # margin (300 s).
    directory.advance_to(ATTEMPT_HARD_CAP_SECONDS + 200)

    report = sweep_running_temporaries()

    assert report.removed == ()
    assert directory.names() == {SOURCE, GEOMETRY, BUNDLE, FOREIGN}


def test_the_running_sweep_removes_the_stale_stage_temporaries_and_only_those(
    directory: _Directory,
) -> None:
    directory.populate()
    directory.advance_to(ATTEMPT_HARD_CAP_SECONDS + 400)

    report = sweep_running_temporaries()

    assert report.removed == (GEOMETRY, SOURCE, BUNDLE)
    assert report.failed == ()
    assert directory.names() == {FOREIGN}


def test_a_started_worker_with_the_default_sweep_reclaims_a_killed_stage_file(
    directory: _Directory, make_service: Callable[..., WorkerService],
) -> None:
    """The default wiring: no sweep is passed, and the started service still reclaims."""
    directory.populate()
    directory.advance_to(ATTEMPT_HARD_CAP_SECONDS + 400)
    service = make_service(temporaries_sweep_seconds=0.02)

    service.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and directory.names() != {FOREIGN}:
        time.sleep(0.02)
    service.stop()

    assert directory.names() == {FOREIGN}
