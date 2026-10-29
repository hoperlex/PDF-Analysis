"""An Attempt lives while its model call shows signs of life (`AR-V3-LIVENESS-01`, lane B).

Owner rule 2026-10-29: do not limit the model's thinking; check that the session is alive and
extend the limits. Before, the heartbeat thread fenced every Attempt at a fixed 900 s counted from
the claim, so a model that was thinking was indistinguishable from one that hung (the live Runs
were cut at exactly 780 s, 900 s less the 60 s margin of the call).

What these tests hold:

* the **Attempt context** on an explicit clock (``now=``): an Attempt that never signals has
  exactly today's numbers; the first sign of life makes it *live*; a live one has the smaller of
  its silence window (600 s) and its ceiling (7200 s); a sign of life extends it past 900 s;
* the **heartbeat thread** fences a silent non-live Attempt at 900 s and not before, fences a live
  one at its stall and at its ceiling, and does not fence a live one that keeps signalling past
  900 s -- driven tick by tick on a fake clock (no minute is slept), and once on a real thread
  with tiny constants.

No database: the repository the thread calls is a recorder.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.jobs import lease as lease_module
from auditmanager.jobs.lease import (
    ATTEMPT_HARD_CAP_SECONDS,
    ATTEMPT_STALL_SECONDS,
    ATTEMPT_WATCHDOG_SECONDS,
    HEARTBEAT_SECONDS,
    AttemptContext,
    LeaseHeartbeat,
)

START = 1000.0


def context(**options: Any) -> AttemptContext:
    return AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=START, **options)


# --------------------------------------------------------------------------------------------
# The constants and the context's defaults
# --------------------------------------------------------------------------------------------


def test_the_owner_decided_constants() -> None:
    assert ATTEMPT_WATCHDOG_SECONDS == 900, "an Attempt that never signals keeps its 900 s"
    assert ATTEMPT_HARD_CAP_SECONDS == 7200
    assert ATTEMPT_STALL_SECONDS == 600
    fresh = context()
    assert (fresh.watchdog_seconds, fresh.hard_cap_seconds, fresh.stall_seconds) == (900.0, 7200.0, 600.0)


def test_the_constructor_keeps_its_old_shape() -> None:
    positional = AttemptContext("run_1", "att_1", START, 50.0)
    assert positional.watchdog_seconds == 50.0 and positional.call_id is None
    positional.bind_call("call_1")
    assert positional.call_id == "call_1"
    assert context(watchdog_seconds=30.0, call_id="call_9").call_id == "call_9"


# --------------------------------------------------------------------------------------------
# Not live: today's numbers, exactly
# --------------------------------------------------------------------------------------------


def test_an_attempt_that_never_signals_has_todays_numbers() -> None:
    attempt = context()
    assert attempt.live is False
    assert attempt.remaining_seconds(START) == 900.0
    assert attempt.remaining_seconds(START + 450) == 450.0
    assert attempt.remaining_seconds(START + 899) == 1.0
    assert attempt.remaining_seconds(START + 900) == 0.0
    assert attempt.remaining_seconds(START + 5000) == 0.0, "never negative"
    assert attempt.live is False, "asking is not a sign of life"


def test_a_custom_watchdog_is_the_deadline_of_an_attempt_that_never_signals() -> None:
    attempt = context(watchdog_seconds=120.0)
    assert attempt.remaining_seconds(START + 20) == 100.0
    assert attempt.remaining_seconds(START + 120) == 0.0


def test_the_ceiling_is_reported_whether_or_not_the_attempt_is_live() -> None:
    attempt = context()
    assert attempt.hard_remaining_seconds(START) == 7200.0
    assert attempt.hard_remaining_seconds(START + 1000) == 6200.0
    assert attempt.hard_remaining_seconds(START + 9000) == 0.0
    attempt.progress(now=START + 5)
    assert attempt.hard_remaining_seconds(START + 1000) == 6200.0


# --------------------------------------------------------------------------------------------
# Live: the minimum of the silence window and the ceiling
# --------------------------------------------------------------------------------------------


def test_the_first_sign_of_life_makes_the_attempt_live() -> None:
    attempt = context()
    assert attempt.live is False
    attempt.progress(now=START + 10)
    assert attempt.live is True


def test_a_live_attempt_has_the_silence_window_not_the_watchdog() -> None:
    attempt = context()
    attempt.progress(now=START + 10)
    assert attempt.remaining_seconds(START + 10) == 600.0
    assert attempt.remaining_seconds(START + 310) == 300.0
    assert attempt.remaining_seconds(START + 609) == 1.0
    assert attempt.remaining_seconds(START + 610) == 0.0, "stall: 600 s without a sign of life"
    assert attempt.remaining_seconds(START + 9999) == 0.0, "never negative"


def test_a_sign_of_life_extends_the_attempt_past_the_watchdog() -> None:
    attempt = context()
    for elapsed in range(10, 1501, 30):  # the last sign of life is at 1480 s
        attempt.progress(now=START + elapsed)
    assert attempt.remaining_seconds(START + 1500) == 580.0
    # An Attempt that had not signalled would have been fenced at 900 s.
    assert context().remaining_seconds(START + 1500) == 0.0
    assert attempt.remaining_seconds(START + 1500) > 0.0


def test_a_live_attempt_that_keeps_signalling_ends_at_its_ceiling() -> None:
    attempt = context()
    attempt.progress(now=START + 7190)
    assert attempt.remaining_seconds(START + 7190) == 10.0, "the ceiling (10 s) is smaller than the window (600 s)"
    assert attempt.remaining_seconds(START + 7199) == 1.0
    assert attempt.remaining_seconds(START + 7200) == 0.0
    attempt.progress(now=START + 7300)
    assert attempt.remaining_seconds(START + 7300) == 0.0, "a late sign of life does not lift the ceiling"
    assert attempt.hard_remaining_seconds(START + 7300) == 0.0


def test_a_sign_of_life_never_moves_backwards() -> None:
    attempt = context()
    attempt.progress(now=START + 100)
    attempt.progress(now=START + 40)  # an older instant: ignored
    assert attempt.remaining_seconds(START + 100) == 600.0


def test_progress_without_an_instant_reads_the_monotonic_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [START + 30.0]
    monkeypatch.setattr(lease_module, "monotonic", lambda: now[0])
    attempt = context()
    attempt.progress()
    now[0] = START + 130.0
    assert attempt.live is True
    assert attempt.remaining_seconds() == 500.0
    assert attempt.hard_remaining_seconds() == 7070.0


def test_custom_limits_govern_a_live_attempt() -> None:
    attempt = context(hard_cap_seconds=100.0, stall_seconds=30.0)
    attempt.progress(now=START + 1)
    assert attempt.remaining_seconds(START + 1) == 30.0
    attempt.progress(now=START + 90)
    assert attempt.remaining_seconds(START + 90) == 10.0, "the ceiling"


def test_signalling_from_another_thread_never_tears_the_reading() -> None:
    attempt = context()
    stop = threading.Event()
    failures: list[BaseException] = []

    def signal() -> None:
        while not stop.is_set():
            attempt.progress()

    def read() -> None:
        try:
            for _ in range(20_000):
                remaining = attempt.remaining_seconds(time.monotonic())
                assert 0.0 <= remaining <= 7200.0
        except BaseException as error:  # noqa: BLE001 -- reported below
            failures.append(error)

    writer = threading.Thread(target=signal)
    reader = threading.Thread(target=read)
    writer.start(), reader.start()
    reader.join(timeout=20)
    stop.set()
    writer.join(timeout=5)
    assert not failures


# --------------------------------------------------------------------------------------------
# The heartbeat thread, tick by tick on a fake clock
# --------------------------------------------------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> float:
        return self.now


class _Repository:
    """What the heartbeat thread calls; nothing here touches a database."""

    def __init__(self) -> None:
        self.beats = 0
        self.reclaims: list[Any] = []
        self.reclaimed = threading.Event()

    def __call__(self) -> _Repository:  # lease.JobRepository() -> this recorder
        return self

    def heartbeat(self, _session: object, _authority: object) -> bool:
        self.beats += 1
        return True

    def reclaim_expired(self, _session: object, *, force_attempt_id: str | None = None) -> None:
        self.reclaims.append(force_attempt_id)
        self.reclaimed.set()


class _Ticks:
    """Stands in for the thread's stop event: every ``wait`` is one heartbeat period of the fake
    clock, ``on_tick(elapsed)`` runs after it, and the loop is stopped after ``limit`` ticks."""

    def __init__(self, clock: _Clock, limit: int, on_tick: Any = None) -> None:
        self._clock = clock
        self._limit = limit
        self._on_tick = on_tick
        self.count = 0

    def wait(self, timeout: float) -> bool:
        if self.count >= self._limit:
            return True
        self.count += 1
        self._clock.now += timeout
        if self._on_tick is not None:
            self._on_tick(self._clock.now - START)
        return False

    def set(self) -> None:
        self._limit = 0


@pytest.fixture
def repository(monkeypatch: pytest.MonkeyPatch) -> _Repository:
    recorder = _Repository()
    monkeypatch.setattr(lease_module, "JobRepository", recorder)
    return recorder


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake = _Clock()
    monkeypatch.setattr(lease_module, "monotonic", fake)
    return fake


def heartbeat_thread(limit: int, on_tick: Any = None, *, clock: _Clock) -> tuple[LeaseHeartbeat, _Ticks]:
    thread = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_1", attempt_id="att_1"))  # type: ignore[arg-type]
    ticks = _Ticks(clock, limit, on_tick)
    thread._stop = ticks  # type: ignore[assignment]
    return thread, ticks


def fenced_at(repository: _Repository, ticks: _Ticks) -> float | None:
    """Seconds after the claim at which the thread fenced the Attempt, or ``None``."""
    return None if not repository.reclaims else ticks.count * float(HEARTBEAT_SECONDS)


def test_a_silent_attempt_is_not_fenced_before_900_seconds_and_is_at_900(
    repository: _Repository, clock: _Clock,
) -> None:
    assert HEARTBEAT_SECONDS == 20
    thread, ticks = heartbeat_thread(limit=200, clock=clock)
    seen = {}

    def on_tick(elapsed: float) -> None:
        if elapsed == 880.0:  # the last tick before the watchdog; the thread has beaten 43 times
            seen["reclaims"], seen["beats"] = list(repository.reclaims), repository.beats

    ticks._on_tick = on_tick
    thread._run()
    assert seen == {"reclaims": [], "beats": 43}
    assert repository.reclaims == ["att_1"], "fenced, naming the Attempt"
    assert clock.now - START == 900.0, "exactly at the watchdog, as before"
    assert ticks.count == 45, "and the thread ended with the fence"
    assert repository.beats == 44


def test_a_live_attempt_that_goes_silent_is_fenced_after_the_stall_window(
    repository: _Repository, clock: _Clock,
) -> None:
    thread, ticks = heartbeat_thread(limit=400, clock=clock)
    signalled = []

    def on_tick(elapsed: float) -> None:
        if elapsed == 60.0:  # the only sign of life
            thread.context.progress(now=clock.now)
            signalled.append(elapsed)

    ticks._on_tick = on_tick
    thread._run()
    assert signalled == [60.0]
    assert repository.reclaims == ["att_1"]
    assert fenced_at(repository, ticks) == 660.0, "60 s + the 600 s window, not the 900 s watchdog"


def test_a_live_attempt_that_keeps_signalling_is_not_fenced_at_900_seconds(
    repository: _Repository, clock: _Clock,
) -> None:
    thread, ticks = heartbeat_thread(limit=400, clock=clock)
    reached = {}

    def on_tick(elapsed: float) -> None:
        if elapsed <= 2000.0:
            thread.context.progress(now=clock.now)
        if elapsed == 1000.0:  # past the watchdog, still signalling
            reached["fenced_before"] = list(repository.reclaims)
            reached["beats"] = repository.beats

    ticks._on_tick = on_tick
    thread._run()
    assert reached["fenced_before"] == [], "a signalling attempt outlives the 900 s watchdog"
    assert reached["beats"] == 49
    assert fenced_at(repository, ticks) == 2600.0, "600 s after the last sign of life, at 2000 s"


def test_a_live_attempt_that_never_stops_signalling_is_fenced_at_the_ceiling(
    repository: _Repository, clock: _Clock,
) -> None:
    thread, ticks = heartbeat_thread(limit=1000, clock=clock)
    ticks._on_tick = lambda _elapsed: thread.context.progress(now=clock.now)
    thread._run()
    assert repository.reclaims == ["att_1"]
    assert fenced_at(repository, ticks) == 7200.0, "the absolute ceiling of two hours"
    assert repository.beats == 359


def test_the_context_reads_the_module_limits_when_the_thread_is_built(
    repository: _Repository, clock: _Clock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A test (or a later setting) that moves a module constant governs the next Attempt."""
    monkeypatch.setattr(lease_module, "ATTEMPT_WATCHDOG_SECONDS", 0.0)
    monkeypatch.setattr(lease_module, "ATTEMPT_HARD_CAP_SECONDS", 77)
    monkeypatch.setattr(lease_module, "ATTEMPT_STALL_SECONDS", 33)
    thread, ticks = heartbeat_thread(limit=5, clock=clock)
    assert thread.context.hard_cap_seconds == 77.0 and thread.context.stall_seconds == 33.0
    thread._run()
    assert repository.reclaims == ["att_1"] and ticks.count == 1, "a zero watchdog fences at the first tick"


# --------------------------------------------------------------------------------------------
# The same thing on a real thread, with tiny constants
# --------------------------------------------------------------------------------------------


def test_a_real_heartbeat_thread_fences_a_silent_then_a_stalled_attempt(
    repository: _Repository, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lease_module, "HEARTBEAT_SECONDS", 0.01)
    monkeypatch.setattr(lease_module, "ATTEMPT_WATCHDOG_SECONDS", 0.3)
    monkeypatch.setattr(lease_module, "ATTEMPT_STALL_SECONDS", 0.6)
    monkeypatch.setattr(lease_module, "ATTEMPT_HARD_CAP_SECONDS", 60)

    started = time.monotonic()
    silent = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_1", attempt_id="att_s"))  # type: ignore[arg-type]
    silent.start()
    try:
        assert repository.reclaimed.wait(timeout=10)
    finally:
        silent.stop()
    assert time.monotonic() - started >= 0.3, "a silent attempt waits out its watchdog"
    assert repository.reclaims == ["att_s"]

    repository.reclaims.clear()
    repository.reclaimed.clear()
    live = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_1", attempt_id="att_l"))  # type: ignore[arg-type]
    live.start()
    began = time.monotonic()
    try:
        while time.monotonic() - began < 0.8:  # signals for longer than the watchdog
            live.context.progress()
            assert not repository.reclaimed.is_set(), "fenced while it was still signalling"
            time.sleep(0.03)
        stopped_signalling = time.monotonic()
        assert repository.reclaimed.wait(timeout=10)
    finally:
        live.stop()
    assert time.monotonic() - stopped_signalling >= 0.3, "fenced after the silence window, not at once"
    assert repository.reclaims == ["att_l"]
