"""An Attempt lives while it shows signs of life; it has no age ceiling (`R-155c`, `R-155h`).

History. Owner rule 2026-10-29: do not limit the model's thinking; check that the session is alive. Before, the heartbeat
thread fenced every Attempt at a fixed 900 s counted from the claim, so a model that was thinking was indistinguishable from
one that hung. Then a live Attempt got a two-hour ceiling, and on 2026-11-17 the production run
``run_01M7MAMZTTDEQTT8VWNG63J7BB`` ended ``partial`` because that ceiling closed while its critic was working. Owner ruling
`R-155c`, «Без потолка»: no age ceiling; a **silence** ends an Attempt, not its age. `R-155h`: a model call's window is its stage
row's (up to 3600 s), not what a 600 s silence window leaves.

What these tests hold:

* the **Attempt context** on an explicit clock (``now=``): an Attempt that never signals has exactly the numbers it always had
  (900 s); the first sign of life makes it *live*; its ceiling is ``math.inf`` (never ``None``), so every limit derived from it
  stays finite; a call's budget is the ceiling alone, not the silence window;
* the **fence** of a live Attempt: between calls a silence of ``ATTEMPT_LOCAL_SILENCE_SECONDS`` (1800 s); inside a call no
  silence is counted, only the call's own window plus a grace; the end of a call restarts the count;
* the **heartbeat thread**, tick by tick on a fake clock (no minute is slept) and on a real thread with tiny constants: a
  silent non-live Attempt is fenced at 900 s and re-queued as before; a live one is **not** fenced at two hours while it
  signals, is not fenced for a call that runs longer than half an hour inside its window, and is failed
  (``attempt_stalled``, not re-queued) when it stalls or a call outlives its window;
* the **slot recovery** hook fires when the work thread of an Attempt whose authority was revoked has not returned within the
  grace, and does not when it returned (it stopped the heartbeat) or when the Attempt ended itself.

No database: the repository the thread calls is a recorder. The path from a stall to a failed Run is proved against a real
database in ``tests/integration/jobs/test_stalled_attempt_fails_the_run.py``.
"""

from __future__ import annotations

import math
import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.jobs import lease as lease_module
from auditmanager.jobs.lease import (
    ATTEMPT_CALL_GRACE_SECONDS,
    ATTEMPT_HARD_CAP_SECONDS,
    ATTEMPT_LOCAL_SILENCE_SECONDS,
    ATTEMPT_RETURN_GRACE_SECONDS,
    ATTEMPT_STALL_SECONDS,
    ATTEMPT_WATCHDOG_SECONDS,
    FENCE_CALL_OVERRAN,
    FENCE_HARD_CAP,
    FENCE_STALLED,
    FENCE_WATCHDOG,
    HEARTBEAT_SECONDS,
    INTERRUPTED_ATTEMPT_STALLED,
    AttemptContext,
    LeaseHeartbeat,
    RevokedAttempt,
    current_slot_recovery,
    install_slot_recovery,
    model_call_budget_seconds,
    model_call_finished,
    model_call_started,
)

START = 1000.0


def context(**options: Any) -> AttemptContext:
    return AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=START, **options)


# --------------------------------------------------------------------------------------------
# The constants and the context's defaults
# --------------------------------------------------------------------------------------------


def test_the_owner_decided_constants() -> None:
    assert ATTEMPT_WATCHDOG_SECONDS == 900, "an Attempt that never signals keeps its 900 s"
    assert ATTEMPT_HARD_CAP_SECONDS is not None, "never None: the limits derived from it stay well defined"
    assert isinstance(ATTEMPT_HARD_CAP_SECONDS, float) and math.isinf(ATTEMPT_HARD_CAP_SECONDS), "`R-155c`: no age ceiling"
    assert ATTEMPT_STALL_SECONDS == 600
    assert ATTEMPT_LOCAL_SILENCE_SECONDS == 1800, "half an hour of silence outside a call"
    assert ATTEMPT_CALL_GRACE_SECONDS > 0 and ATTEMPT_RETURN_GRACE_SECONDS > 0
    fresh = context()
    assert (fresh.watchdog_seconds, fresh.stall_seconds, fresh.local_silence_seconds) == (900.0, 600.0, 1800.0)
    assert math.isinf(fresh.hard_cap_seconds) and fresh.hard_cap_seconds > 0


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


def test_there_is_no_ceiling_whether_or_not_the_attempt_is_live() -> None:
    attempt = context()
    assert math.isinf(attempt.hard_remaining_seconds(START))
    assert math.isinf(attempt.hard_remaining_seconds(START + 1000))
    assert math.isinf(attempt.hard_remaining_seconds(START + 90_000)), "a day later it still has none"
    attempt.progress(now=START + 5)
    assert math.isinf(attempt.hard_remaining_seconds(START + 1000))


def test_a_finite_ceiling_given_to_the_context_still_works() -> None:
    """The ceiling is a field of the context, so a test (or a later setting) may still give one."""
    attempt = context(hard_cap_seconds=7200.0)
    assert attempt.hard_remaining_seconds(START) == 7200.0
    assert attempt.hard_remaining_seconds(START + 1000) == 6200.0
    assert attempt.hard_remaining_seconds(START + 9000) == 0.0


# --------------------------------------------------------------------------------------------
# Live: finite limits derived from an infinite ceiling
# --------------------------------------------------------------------------------------------


def test_the_first_sign_of_life_makes_the_attempt_live() -> None:
    attempt = context()
    assert attempt.live is False
    attempt.progress(now=START + 10)
    assert attempt.live is True


def test_a_live_attempt_has_the_silence_window_not_the_watchdog_and_it_is_finite() -> None:
    attempt = context()
    attempt.progress(now=START + 10)
    assert attempt.remaining_seconds(START + 10) == 600.0
    assert attempt.remaining_seconds(START + 310) == 300.0
    assert attempt.remaining_seconds(START + 609) == 1.0
    assert attempt.remaining_seconds(START + 610) == 0.0, "stall: 600 s without a sign of life"
    assert attempt.remaining_seconds(START + 9999) == 0.0, "never negative"
    assert all(math.isfinite(attempt.remaining_seconds(START + step)) for step in (0, 10, 5000, 80_000)), \
        "the smaller of an infinity and a finite window is finite"


def test_a_sign_of_life_extends_the_attempt_past_the_watchdog() -> None:
    attempt = context()
    for elapsed in range(10, 1501, 30):  # the last sign of life is at 1480 s
        attempt.progress(now=START + elapsed)
    assert attempt.remaining_seconds(START + 1500) == 580.0
    # An Attempt that had not signalled would have been fenced at 900 s.
    assert context().remaining_seconds(START + 1500) == 0.0
    assert attempt.remaining_seconds(START + 1500) > 0.0


def test_a_live_attempt_that_keeps_signalling_is_never_ended_by_its_age() -> None:
    attempt = context()
    for hours in (1, 2, 3, 12):
        instant = START + hours * 3600
        attempt.progress(now=instant)
        assert attempt.remaining_seconds(instant) == 600.0, f"{hours} h in, the silence window is whole"
        assert attempt.fence_remaining_seconds(instant) == 1800.0
        assert attempt.fence_reason(instant) is None


def test_a_finite_ceiling_still_ends_a_live_attempt_that_keeps_signalling() -> None:
    attempt = context(hard_cap_seconds=7200.0)
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
    assert math.isinf(attempt.hard_remaining_seconds())


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
            attempt.call_started(window_seconds=1.0)
            attempt.call_finished()

    def read() -> None:
        try:
            for _ in range(20_000):
                now = time.monotonic()
                remaining = attempt.remaining_seconds(now)
                assert 0.0 <= remaining <= 600.0 or not attempt.live
                fence = attempt.fence_remaining_seconds(now)
                assert 0.0 <= fence <= 1801.0 or not attempt.live
        except BaseException as error:  # noqa: BLE001 -- reported below
            failures.append(error)

    writer = threading.Thread(target=signal)
    reader = threading.Thread(target=read)
    writer.start(), reader.start()
    reader.join(timeout=30)
    stop.set()
    writer.join(timeout=5)
    assert not failures


# --------------------------------------------------------------------------------------------
# A call's budget: the ceiling alone (`R-155h`)
# --------------------------------------------------------------------------------------------


def test_a_live_attempts_call_budget_is_not_cut_to_the_silence_window() -> None:
    """The ~540 s every call was cut to: 600 s of silence window less the 60 s margin. A live Attempt now leaves a call the
    absolute ceiling alone, which is infinite, so the call's own window (its row's, up to 3600 s) is what governs it."""
    attempt = context()
    attempt.progress(now=START + 10)
    assert attempt.remaining_seconds(START + 10) == 600.0 and math.isinf(attempt.call_budget_seconds(START + 10))
    assert math.isinf(attempt.call_budget_seconds(START + 700)), "even after 690 s without a sign of life"
    capped = context(hard_cap_seconds=7200.0)
    capped.progress(now=START + 10)
    assert capped.call_budget_seconds(START + 7100) == 100.0, "a finite ceiling still bounds it"


def test_a_not_live_attempts_call_budget_is_the_watchdog_as_before() -> None:
    attempt = context()
    assert attempt.call_budget_seconds(START + 100) == attempt.remaining_seconds(START + 100) == 800.0
    assert attempt.call_budget_seconds(START + 950) == 0.0
    assert attempt.live is False, "asking is not a sign of life"


def test_the_budget_of_any_context_is_read_through_one_function() -> None:
    assert model_call_budget_seconds(SimpleNamespace(remaining_seconds=lambda: 47.5)) == 47.5, "the comparison work's context"
    attempt = context()
    attempt.progress(now=START)
    assert math.isinf(model_call_budget_seconds(attempt))


# --------------------------------------------------------------------------------------------
# The fence of a live Attempt: a silence, outside a call and inside one
# --------------------------------------------------------------------------------------------


def test_a_not_live_attempt_is_fenced_by_the_watchdog_at_900_seconds() -> None:
    attempt = context()
    assert attempt.fence_reason(START + 899) is None
    assert attempt.fence_reason(START + 900) == FENCE_WATCHDOG
    assert attempt.fence_remaining_seconds(START + 100) == attempt.remaining_seconds(START + 100) == 800.0
    assert attempt.fence_remaining_seconds(START + 9000) == 0.0, "never negative"


def test_a_not_live_attempt_in_a_call_keeps_the_watchdog() -> None:
    """The window of the first call of an Attempt that never signalled is cut to the watchdog, so it ends before the fence."""
    attempt = context()
    attempt.call_started(now=START + 10, window_seconds=3600.0)
    assert not attempt.live, "a call starting does not make an Attempt live"
    assert attempt.in_call
    assert attempt.fence_reason(START + 900) == FENCE_WATCHDOG


def test_a_live_attempt_between_calls_is_fenced_after_half_an_hour_of_silence() -> None:
    attempt = context()
    attempt.progress(now=START + 100)
    assert attempt.fence_reason(START + 100 + 600) is None, "not at its stall window: that bounds a call, not the worker"
    assert attempt.fence_reason(START + 100 + 1799) is None
    assert attempt.fence_reason(START + 100 + 1800) == FENCE_STALLED
    assert attempt.fence_remaining_seconds(START + 100 + 600) == 1200.0
    assert attempt.fence_remaining_seconds(START + 100 + 9000) == 0.0, "never negative"


def test_a_sign_of_life_between_calls_restarts_the_count() -> None:
    attempt = context()
    attempt.progress(now=START + 100)
    attempt.progress(now=START + 1800)  # a page was rendered
    assert attempt.fence_reason(START + 1800 + 1799) is None
    assert attempt.fence_reason(START + 1800 + 1800) == FENCE_STALLED


def test_a_call_longer_than_half_an_hour_within_its_window_is_not_fenced() -> None:
    """`R-155h`: a cross-check call has 3600 s. Its silence is not counted; only its own window plus a grace is."""
    attempt = context()
    attempt.progress(now=START + 100)
    attempt.call_started(now=START + 200, window_seconds=3600.0)
    assert attempt.in_call
    for waited in (600, 1800, 1801, 3000, 3600, 3600 + ATTEMPT_CALL_GRACE_SECONDS - 1):
        assert attempt.fence_reason(START + 200 + waited) is None, f"fenced {waited} s into a call of 3600 s"
    assert attempt.fence_reason(START + 200 + 3600 + ATTEMPT_CALL_GRACE_SECONDS) == FENCE_CALL_OVERRAN, \
        "a call that outlives its window by the grace is a hung adapter"


def test_a_call_without_a_window_of_its_own_gets_the_longest_the_contract_admits() -> None:
    attempt = context()
    attempt.progress(now=START)
    attempt.call_started(now=START)
    assert attempt.fence_reason(START + 7200) is None
    assert attempt.fence_reason(START + 7200 + ATTEMPT_CALL_GRACE_SECONDS) == FENCE_CALL_OVERRAN


def test_the_end_of_a_call_is_a_sign_of_life_and_the_silence_counts_from_it() -> None:
    attempt = context()
    attempt.progress(now=START + 100)
    attempt.call_started(now=START + 200, window_seconds=3600.0)
    attempt.call_finished(now=START + 3500)
    assert not attempt.in_call
    # Fresh at the end of the call: 3300 s after the last sign before the call would be a stall, but it is not.
    assert attempt.fence_reason(START + 3500 + 1799) is None
    assert attempt.fence_reason(START + 3500 + 1800) == FENCE_STALLED


def test_a_call_starting_is_a_sign_of_life_of_a_live_attempt() -> None:
    attempt = context()
    attempt.progress(now=START + 10)
    attempt.call_started(now=START + 700, window_seconds=600.0)  # after 690 s of the worker's own work
    attempt.call_finished(now=START + 700)
    assert attempt.remaining_seconds(START + 700) == 600.0, "the last sign is the call's end"


def test_a_call_starting_leaves_an_attempt_that_is_not_live_as_it_is() -> None:
    attempt = context()
    attempt.call_started(now=START + 100, window_seconds=300.0)
    attempt.call_finished(now=START + 400)
    assert not attempt.live
    assert attempt.remaining_seconds(START + 400) == 500.0, "the watchdog's fixed deadline, as before"


def test_overlapping_calls_do_not_end_each_others_tracking() -> None:
    attempt = context()
    attempt.progress(now=START)
    attempt.call_started(now=START + 10, window_seconds=3600.0)
    attempt.call_started(now=START + 20, window_seconds=600.0)
    attempt.call_finished(now=START + 700)  # the short one ends
    assert attempt.in_call, "the long one is still in flight"
    assert attempt.fence_reason(START + 700 + 2000) is None, "and is not taken for a stall"
    attempt.call_finished(now=START + 3000)
    assert not attempt.in_call
    attempt.call_finished(now=START + 3001)  # an unmatched end changes nothing but the sign of life
    assert not attempt.in_call


def test_a_finite_ceiling_is_a_fence_of_its_own_kind() -> None:
    attempt = context(hard_cap_seconds=7200.0)
    attempt.progress(now=START + 7000)
    assert attempt.fence_reason(START + 7199) is None
    assert attempt.fence_reason(START + 7200) == FENCE_HARD_CAP
    assert attempt.fence_remaining_seconds(START + 7100) == 100.0


def test_the_fence_distance_of_a_live_attempt_is_always_finite() -> None:
    attempt = context()
    attempt.progress(now=START)
    for instant in (START, START + 3600, START + 86_400):
        assert math.isfinite(attempt.fence_remaining_seconds(instant))
    attempt.call_started(now=START + 90_000, window_seconds=3600.0)
    assert attempt.fence_remaining_seconds(START + 90_000) == 3600.0 + ATTEMPT_CALL_GRACE_SECONDS


def test_the_adapters_announce_through_helpers_that_leave_a_foreign_context_alone() -> None:
    model_call_started(None, 10.0)
    model_call_finished(None)
    model_call_started(SimpleNamespace(remaining_seconds=lambda: 1.0), 10.0)  # the comparison work's: no such methods
    model_call_finished(SimpleNamespace(remaining_seconds=lambda: 1.0))
    attempt = context()
    model_call_started(attempt, 120.0)
    assert attempt.in_call
    model_call_finished(attempt)
    assert not attempt.in_call


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
        self.failures: list[str | None] = []
        self.reclaimed = threading.Event()
        self.current = True
        self.state_after_loss: str | None = "lost"

    def __call__(self) -> _Repository:  # lease.JobRepository() -> this recorder
        return self

    def heartbeat(self, _session: object, _authority: object) -> bool:
        self.beats += 1
        return self.current

    def attempt_state(self, _session: object, _attempt_id: str) -> str | None:
        return self.state_after_loss

    def reclaim_expired(self, _session: object, *, force_attempt_id: str | None = None,
                        fail_reason: str | None = None) -> None:
        self.reclaims.append(force_attempt_id)
        self.failures.append(fail_reason)
        self.reclaimed.set()


class _Ticks:
    """Stands in for the thread's stop event: every ``wait`` is one heartbeat period of the fake
    clock, ``on_tick(elapsed)`` runs after it, and the loop is stopped after ``limit`` ticks.
    The wait for the work thread's return (the slot recovery grace) is told apart by its length."""

    def __init__(self, clock: _Clock, limit: int, on_tick: Any = None) -> None:
        self._clock = clock
        self._limit = limit
        self._on_tick = on_tick
        self.count = 0
        self.graces: list[float] = []
        self.returned = False

    def wait(self, timeout: float) -> bool:
        if timeout != HEARTBEAT_SECONDS and timeout == float(lease_module.ATTEMPT_RETURN_GRACE_SECONDS):
            self.graces.append(timeout)
            return self.returned
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


@pytest.fixture
def recovery() -> Any:
    """A slot-recovery hook that records what it was told; the module's hook is put back afterwards."""
    told: list[RevokedAttempt] = []
    before = current_slot_recovery()
    install_slot_recovery(told.append)
    try:
        yield told
    finally:
        install_slot_recovery(before)


def heartbeat_thread(limit: int, on_tick: Any = None, *, clock: _Clock) -> tuple[LeaseHeartbeat, _Ticks]:
    thread = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_1", attempt_id="att_1"))  # type: ignore[arg-type]
    ticks = _Ticks(clock, limit, on_tick)
    thread._stop = ticks  # type: ignore[assignment]
    return thread, ticks


def fenced_at(repository: _Repository, ticks: _Ticks) -> float | None:
    """Seconds after the claim at which the thread fenced the Attempt, or ``None``."""
    return None if not repository.reclaims else ticks.count * float(HEARTBEAT_SECONDS)


def test_a_silent_attempt_is_not_fenced_before_900_seconds_and_is_at_900_and_requeued_as_before(
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
    assert repository.failures == [None], "the watchdog's fence is the reclaim as it always was: it may re-queue"
    assert clock.now - START == 900.0, "exactly at the watchdog, as before"
    assert ticks.count == 45, "the fence, and the thread then waits for its work thread to return"
    assert repository.beats == 44


def test_a_live_attempt_silent_between_calls_is_failed_as_stalled_after_half_an_hour_not_at_its_stall_window(
    repository: _Repository, clock: _Clock,
) -> None:
    """`STALL-LOCAL-WORK-01` kept the heartbeat from fencing a live Attempt at 600 s (the stand's own work is no silence of the
    model); `R-155c` bounds that work by a silence of its own, 1800 s, and ends the run without re-queueing it."""
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    seen = {}

    def on_tick(elapsed: float) -> None:
        if elapsed == 60.0:  # the only sign of life
            thread.context.progress(now=clock.now)
        if elapsed == 1000.0:  # past 60 s + the 600 s stall window
            seen["reclaims"] = list(repository.reclaims)

    ticks._on_tick = on_tick
    thread._run()
    assert seen == {"reclaims": []}, "not fenced at 660 s: the stall window bounds a call, not the worker"
    assert repository.reclaims == ["att_1"]
    assert repository.failures == [INTERRUPTED_ATTEMPT_STALLED] == ["attempt_stalled"], "the run fails, it is not re-queued"
    assert fenced_at(repository, ticks) == 1860.0, "60 s + 1800 s of silence"


def test_a_live_attempt_that_keeps_signalling_is_not_fenced_at_two_hours_or_three(
    repository: _Repository, clock: _Clock,
) -> None:
    """`R-155c`, «Без потолка»: the run that ended at 7200 s while its critic worked would go on now."""
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    reached: dict[str, Any] = {}

    def on_tick(elapsed: float) -> None:
        if elapsed <= 4 * 3600.0:
            thread.context.progress(now=clock.now)
        if elapsed == 7200.0 + 20.0:  # the tick after the old ceiling
            reached["after_two_hours"] = list(repository.reclaims), repository.beats
        if elapsed == 3 * 3600.0:
            reached["after_three_hours"] = list(repository.reclaims)

    ticks._on_tick = on_tick
    thread._run()
    assert reached["after_two_hours"] == ([], 360), "not fenced past the old two-hour ceiling"
    assert reached["after_three_hours"] == []
    assert repository.failures == ["attempt_stalled"]
    assert fenced_at(repository, ticks) == 4 * 3600.0 + 1800.0, "it ends 1800 s after the last sign of life, at four hours"


def test_a_call_longer_than_half_an_hour_inside_its_window_is_not_fenced_and_one_that_outlives_it_is(
    repository: _Repository, clock: _Clock,
) -> None:
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    seen = {}

    def on_tick(elapsed: float) -> None:
        if elapsed == 100.0:  # a live Attempt starts a 3600 s call and signals nothing more
            thread.context.progress(now=clock.now)
            thread.context.call_started(now=clock.now, window_seconds=3600.0)
        if elapsed in (2000.0, 3600.0, 3700.0):
            seen[elapsed] = list(repository.reclaims)

    ticks._on_tick = on_tick
    thread._run()
    assert seen == {2000.0: [], 3600.0: [], 3700.0: []}, "silent for half an hour inside its own window: not fenced"
    assert repository.failures == ["attempt_stalled"]
    assert fenced_at(repository, ticks) == 100.0 + 3600.0 + float(ATTEMPT_CALL_GRACE_SECONDS), "window plus the grace"


def test_the_end_of_a_call_restarts_the_silence_count(repository: _Repository, clock: _Clock) -> None:
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)

    def on_tick(elapsed: float) -> None:
        if elapsed == 100.0:
            thread.context.progress(now=clock.now)
            thread.context.call_started(now=clock.now, window_seconds=3600.0)
        if elapsed == 3000.0:
            thread.context.call_finished(now=clock.now)

    ticks._on_tick = on_tick
    thread._run()
    assert fenced_at(repository, ticks) == 3000.0 + 1800.0, "counted from the end of the call, not from before it"
    assert repository.failures == ["attempt_stalled"]


def test_a_finite_ceiling_still_fences_through_the_re_queueing_reclaim(
    repository: _Repository, clock: _Clock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lease_module, "ATTEMPT_HARD_CAP_SECONDS", 7200)
    thread, ticks = heartbeat_thread(limit=1000, clock=clock)
    ticks._on_tick = lambda _elapsed: thread.context.progress(now=clock.now)
    thread._run()
    assert repository.reclaims == ["att_1"]
    assert repository.failures == [None], "a ceiling is not a stall"
    assert fenced_at(repository, ticks) == 7200.0
    assert repository.beats == 359


def test_the_context_reads_the_module_limits_when_the_thread_is_built(
    repository: _Repository, clock: _Clock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A test (or a later setting) that moves a module constant governs the next Attempt."""
    monkeypatch.setattr(lease_module, "ATTEMPT_WATCHDOG_SECONDS", 0.0)
    monkeypatch.setattr(lease_module, "ATTEMPT_HARD_CAP_SECONDS", 77)
    monkeypatch.setattr(lease_module, "ATTEMPT_STALL_SECONDS", 33)
    monkeypatch.setattr(lease_module, "ATTEMPT_LOCAL_SILENCE_SECONDS", 44)
    monkeypatch.setattr(lease_module, "ATTEMPT_CALL_GRACE_SECONDS", 55)
    thread, ticks = heartbeat_thread(limit=5, clock=clock)
    assert (thread.context.hard_cap_seconds, thread.context.stall_seconds) == (77.0, 33.0)
    assert (thread.context.local_silence_seconds, thread.context.call_grace_seconds) == (44.0, 55.0)
    thread._run()
    assert repository.reclaims == ["att_1"] and ticks.count == 1, "a zero watchdog fences at the first tick"


# --------------------------------------------------------------------------------------------
# Slot recovery: a revoked Attempt's work thread that does not return
# --------------------------------------------------------------------------------------------


def test_a_stalled_attempts_work_thread_that_does_not_return_in_the_grace_tells_the_process(
    repository: _Repository, clock: _Clock, recovery: list[RevokedAttempt],
) -> None:
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    thread.context.progress(now=START)
    thread._run()
    assert repository.failures == ["attempt_stalled"]
    assert ticks.graces == [float(ATTEMPT_RETURN_GRACE_SECONDS)], "it waited the grace for the work thread"
    (told,) = recovery
    assert (told.run_id, told.attempt_id) == ("run_1", "att_1")
    assert told.reason == "fenced:stalled" and told.grace_seconds == float(ATTEMPT_RETURN_GRACE_SECONDS)


def test_a_work_thread_that_returns_in_the_grace_is_not_a_lost_slot(
    repository: _Repository, clock: _Clock, recovery: list[RevokedAttempt],
) -> None:
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    ticks.returned = True  # the work thread stopped the heartbeat while it waited
    thread.context.progress(now=START)
    thread._run()
    assert repository.failures == ["attempt_stalled"] and ticks.graces == [float(ATTEMPT_RETURN_GRACE_SECONDS)]
    assert recovery == []


def test_a_cancelled_attempt_whose_thread_does_not_return_is_a_lost_slot_too(
    repository: _Repository, clock: _Clock, recovery: list[RevokedAttempt],
) -> None:
    """``cancelRun`` only marks the database (`cancel_for_run`): the lease is released and the Attempt ``cancelled``; the work
    thread learns it at its next write. The heartbeat is what sees the lease go, and it starts the same count."""
    repository.current = False
    repository.state_after_loss = "cancelled"
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    thread._run()
    assert repository.reclaims == [], "nothing is fenced: someone else already did it"
    (told,) = recovery
    assert told.reason == "revoked:cancelled"


def test_an_attempt_that_ended_itself_is_not_revoked(
    repository: _Repository, clock: _Clock, recovery: list[RevokedAttempt],
) -> None:
    """`finish_execution` releases the lease before the work thread stops the heartbeat; a tick that lands in between must not
    start a count that would end the worker."""
    repository.current = False
    repository.state_after_loss = "succeeded"
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    thread._run()
    assert recovery == [] and ticks.graces == []
    repository.state_after_loss = "failed"
    thread, ticks = heartbeat_thread(limit=2000, clock=clock)
    thread._run()
    assert recovery == [] and ticks.graces == []


def test_a_lapsed_lease_that_no_reclaim_has_taken_yet_is_revoked_too(
    repository: _Repository, clock: _Clock, recovery: list[RevokedAttempt],
) -> None:
    repository.current = False
    repository.state_after_loss = "running"
    thread, _ticks = heartbeat_thread(limit=2000, clock=clock)
    thread._run()
    (told,) = recovery
    assert told.reason == "revoked:running"


def test_without_an_installed_recovery_the_lost_slot_is_logged_not_silent(
    repository: _Repository, clock: _Clock, caplog: pytest.LogCaptureFixture,
) -> None:
    before = current_slot_recovery()
    install_slot_recovery(None)
    try:
        thread, _ticks = heartbeat_thread(limit=2000, clock=clock)
        thread.context.progress(now=START)
        with caplog.at_level("ERROR", logger=lease_module.__name__):
            thread._run()
    finally:
        install_slot_recovery(before)
    assert any("no slot recovery installed" in record.getMessage() for record in caplog.records)


def test_a_hook_that_raises_does_not_end_the_heartbeat_thread(
    repository: _Repository, clock: _Clock, caplog: pytest.LogCaptureFixture,
) -> None:
    def broken(_notice: RevokedAttempt) -> None:
        raise RuntimeError("the hook failed")

    before = current_slot_recovery()
    install_slot_recovery(broken)
    try:
        thread, _ticks = heartbeat_thread(limit=2000, clock=clock)
        thread.context.progress(now=START)
        with caplog.at_level("ERROR", logger=lease_module.__name__):
            thread._run()  # returns, instead of raising
    finally:
        install_slot_recovery(before)
    assert any("slot recovery failed" in record.getMessage() for record in caplog.records)


# --------------------------------------------------------------------------------------------
# The same on a real thread, with tiny constants
# --------------------------------------------------------------------------------------------


def _tiny(monkeypatch: pytest.MonkeyPatch, **limits: float) -> None:
    monkeypatch.setattr(lease_module, "HEARTBEAT_SECONDS", 0.01)
    for name, value in limits.items():
        monkeypatch.setattr(lease_module, name, value)


def test_a_real_heartbeat_thread_fences_a_silent_attempt_and_fails_a_live_one_only_by_silence(
    repository: _Repository, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _tiny(monkeypatch, ATTEMPT_WATCHDOG_SECONDS=0.3, ATTEMPT_STALL_SECONDS=0.3, ATTEMPT_LOCAL_SILENCE_SECONDS=0.5,
          ATTEMPT_CALL_GRACE_SECONDS=0.2, ATTEMPT_RETURN_GRACE_SECONDS=30.0)

    started = time.monotonic()
    silent = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_1", attempt_id="att_s"))  # type: ignore[arg-type]
    silent.start()
    try:
        assert repository.reclaimed.wait(timeout=10)
    finally:
        silent.stop()
    assert time.monotonic() - started >= 0.3, "a silent attempt waits out its watchdog"
    assert repository.reclaims == ["att_s"] and repository.failures == [None]

    repository.reclaims.clear(), repository.failures.clear(), repository.reclaimed.clear()
    live = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_1", attempt_id="att_l"))  # type: ignore[arg-type]
    live.start()
    began = time.monotonic()
    try:
        while time.monotonic() - began < 1.0:  # signals for longer than the watchdog and the silence
            live.context.progress()
            assert not repository.reclaimed.is_set(), "fenced while it was still signalling"
            time.sleep(0.03)
        # Silent from 1.0 s: the stall window (0.3 s) would have fenced it at 1.3 s. At 1.4 s it is still not, because the
        # silence limit outside a call is 0.5 s ... which it reaches at 1.5 s.
        assert repository.reclaimed.wait(timeout=10)
    finally:
        live.stop()
    assert time.monotonic() - began >= 1.45, "fenced after the 0.5 s of silence, not after the 0.3 s stall window"
    assert repository.reclaims == ["att_l"] and repository.failures == ["attempt_stalled"]


def test_a_real_thread_leaves_a_live_attempt_alone_for_a_call_longer_than_the_silence_limit(
    repository: _Repository, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _tiny(monkeypatch, ATTEMPT_LOCAL_SILENCE_SECONDS=0.3, ATTEMPT_CALL_GRACE_SECONDS=0.3,
          ATTEMPT_RETURN_GRACE_SECONDS=30.0)
    live = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_1", attempt_id="att_c"))  # type: ignore[arg-type]
    live.start()
    try:
        live.context.progress()
        live.context.call_started(window_seconds=1.0)  # in a call of one second: five times the silence limit
        began = time.monotonic()
        assert not repository.reclaimed.wait(timeout=1.0), "fenced inside its own window"
        assert repository.reclaimed.wait(timeout=10), "never fenced although the call outlived its window and its grace"
    finally:
        live.stop()
    assert time.monotonic() - began >= 1.25
    assert repository.failures == ["attempt_stalled"]


def test_a_real_thread_tells_the_process_when_the_work_thread_does_not_return_and_not_when_it_does(
    repository: _Repository, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _tiny(monkeypatch, ATTEMPT_LOCAL_SILENCE_SECONDS=0.1, ATTEMPT_RETURN_GRACE_SECONDS=0.3)
    told: list[RevokedAttempt] = []
    informed = threading.Event()
    before = current_slot_recovery()
    install_slot_recovery(lambda notice: (told.append(notice), informed.set()))
    try:
        # A work thread that returns (stops its heartbeat) once it is fenced: the process is not told.
        returning = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_r", attempt_id="att_r"))  # type: ignore[arg-type]
        returning.start()
        returning.context.progress()
        assert repository.reclaimed.wait(timeout=10)
        returning.stop()  # the work thread's `finally`
        assert not informed.wait(timeout=0.8) and told == []

        # One that hangs: the grace passes and the hook is called, once, from the heartbeat thread.
        repository.reclaimed.clear()
        hung = LeaseHeartbeat(object(), SimpleNamespace(run_id="run_h", attempt_id="att_h"))  # type: ignore[arg-type]
        hung.start()
        hung.context.progress()
        try:
            assert informed.wait(timeout=10), "the hook did not fire for a work thread that never returned"
        finally:
            hung.stop()
    finally:
        install_slot_recovery(before)
    (notice,) = told
    assert (notice.run_id, notice.attempt_id, notice.reason) == ("run_h", "att_h", "fenced:stalled")
