"""`HOSTS-BACKEND-01` (ADR-0028 decision 9): a call to a host agent, and what counts as its sign of life.

The task carries the six members of the cell (provider, access, model, effort, timeout, cell key -- and no answer cap, `R-153n`); the window it is given is the **smaller** of
the cell's timeout and what the watchdog leaves less the margin; and a claim -- or an extension of it, which the agent makes only while its CLI produced output --
is a sign of life that the Attempt's context records (``AttemptContext.progress``), so a hung CLI, whose claim lapses, stops signalling. A call made on a
connection's own revision is as it was: no ``host`` in its payload, no sign of life taken from its claim. No database and no sleeping (the scripted task table of
``test_pull_adapter``).
"""

from __future__ import annotations

import math
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from auditmanager.analysis.public import ProxyDispatchError
from auditmanager.executors import pull
from auditmanager.executors.pull import HostCall, PullAdapter, answer_window
from auditmanager.jobs.lease import AttemptContext
from tests.unit.executors.test_pull_adapter import MODEL, REQUEST, Clock, FakeStore, Sessions, revision

CALL = HostCall(provider="claude_code", access="subscription", model_id=MODEL, effort="medium", timeout_seconds=900,
                cell_key="text:main")
T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(pull.time, "sleep", fake.sleep)
    return fake


def _adapter(clock: Clock, store: FakeStore, *, context: object | None = None, host_call: HostCall | None = CALL) -> PullAdapter:
    return PullAdapter(session_factory=Sessions(), revision=revision(deadline=3600), context=context,
                       repository=store, poll_seconds=2.0, monotonic=clock.monotonic, host_call=host_call)  # type: ignore[arg-type]


def _context(*, used: float = 0.0) -> AttemptContext:
    return AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic() - used, call_id="mc_1")


def _answer(c: Clock, store: FakeStore) -> None:
    if store.task is not None and store.task.state == "open":
        store.claim()
        store.answered('{"observations": []}', MODEL)


# --- the six members --------------------------------------------------------------------------------------------------


def test_the_task_of_a_cell_carries_the_six_members_and_no_answer_cap_beside_the_prompt(clock: Clock) -> None:
    store = FakeStore(clock, _answer)
    _adapter(clock, store, context=_context()).complete(REQUEST)
    assert store.payload is not None
    host = store.payload["host"]
    assert set(host) == {"provider", "access", "model_id", "effort", "timeout_seconds", "cell_key"}
    assert "max_output_tokens" not in host and "max_tokens" not in host, "no answer cap reaches a model"
    assert (host["provider"], host["access"], host["model_id"], host["effort"], host["cell_key"]) == (
        "claude_code", "subscription", MODEL, "medium", "text:main")
    assert {"system", "user_text", "output_schema"} <= set(store.payload)


def test_a_call_that_is_not_a_cells_carries_no_host_members(clock: Clock) -> None:
    store = FakeStore(clock, _answer)
    _adapter(clock, store, host_call=None).complete(REQUEST)
    assert store.payload is not None and "host" not in store.payload


def test_a_host_call_names_the_model_of_the_connection_it_is_made_on() -> None:
    with pytest.raises(ValueError):
        PullAdapter(session_factory=Sessions(), revision=revision(), context=None,
                    host_call=replace(CALL, model_id="claude-sonnet-5-5"))


# --- the window ---------------------------------------------------------------------------------------------------------


def test_the_window_is_the_cells_timeout_cut_to_what_the_watchdog_leaves_less_the_margin() -> None:
    assert answer_window(CALL.timeout_seconds, None) == 900.0, "no context: the cell's own timeout"
    fresh = _context()
    assert answer_window(600, fresh) == 600.0, "a cell that asks for less than the watchdog leaves gets what it asked for"
    window_fresh = answer_window(CALL.timeout_seconds, fresh)
    assert window_fresh is not None and window_fresh <= fresh.watchdog_seconds - pull.DEADLINE_MARGIN_SECONDS, "and one that asks for more is cut"
    near_end = _context(used=fresh.watchdog_seconds - 200)
    window = answer_window(CALL.timeout_seconds, near_end)
    assert window is not None and window <= 200 - pull.DEADLINE_MARGIN_SECONDS + 1, "the watchdog's remainder less the margin bounds it"
    assert answer_window(CALL.timeout_seconds, _context(used=fresh.watchdog_seconds - pull.DEADLINE_MARGIN_SECONDS)) is None


def test_a_live_attempts_call_has_its_rows_window_not_the_540_seconds_the_silence_window_left() -> None:
    """`R-155h`: the cross-check row has 3600 s, text and blocks 1800 s, norms/critic/refinement 600 s. A live Attempt used to leave
    a call at most its 600 s silence window less the 60 s margin; it has no age ceiling now (`R-155c`), so the call's window is the
    row's, whatever the Attempt has run and however long it has been quiet."""
    live = _context(used=10_000)  # claimed almost three hours ago
    live.progress()
    assert math.isinf(live.hard_cap_seconds)
    for row, window in {"text": 1800, "blocks": 1800, "cross_check": 3600, "norms": 600, "review": 600, "correction": 600}.items():
        assert answer_window(window, live) == float(window), row
    assert answer_window(3600, live) != 540.0
    live_but_quiet = _context(used=10_000)
    live_but_quiet.progress(now=time.monotonic() - 1500)  # 25 minutes since its last sign: the stall window is long gone
    assert live_but_quiet.remaining_seconds() == 0.0
    assert answer_window(3600, live_but_quiet) == 3600.0, "the silence window does not cut a call"


def test_an_attempt_that_has_shown_no_life_keeps_the_watchdogs_cut_on_its_first_call() -> None:
    fresh = _context()
    window = answer_window(3600, fresh)
    assert window is not None and window <= fresh.watchdog_seconds - pull.DEADLINE_MARGIN_SECONDS


def test_the_task_of_a_cross_check_call_carries_3600_seconds_and_the_call_is_announced_to_the_attempt(clock: Clock) -> None:
    class Announced:
        """A real context that records the announcements and whether the call was in flight while the runner was waited for."""

        def __init__(self) -> None:
            self.real = _context(used=10_000)
            self.real.progress()
            self.events: list[tuple[str, float | None]] = []
            self.in_call_while_waiting: list[bool] = []
            self.run_id, self.attempt_id, self.call_id = "run_1", "att_1", "mc_1"

        def __getattr__(self, name: str) -> object:
            return getattr(self.real, name)

        def call_started(self, *, window_seconds: float | None = None) -> None:
            self.events.append(("started", window_seconds))
            self.real.call_started(window_seconds=window_seconds)

        def call_finished(self) -> None:
            self.events.append(("finished", None))
            self.real.call_finished()

    announced = Announced()

    def script(c: Clock, store: FakeStore) -> None:
        announced.in_call_while_waiting.append(announced.real.in_call)
        _answer(c, store)

    store = FakeStore(clock, script)
    cross_check = replace(CALL, timeout_seconds=3600, cell_key="cross_check:main")
    _adapter(clock, store, context=announced, host_call=cross_check).complete(REQUEST)
    assert store.payload is not None and store.payload["host"]["timeout_seconds"] == 3600
    assert store.inserted["deadline_seconds"] == 3600.0
    assert announced.events == [("started", 3600.0), ("finished", None)]
    assert announced.in_call_while_waiting and all(announced.in_call_while_waiting), "in flight while it waited"
    assert announced.real.in_call is False and announced.real.fence_reason() is None


def test_a_call_that_ends_in_failure_is_announced_as_finished(clock: Clock) -> None:
    announced = _context(used=10)
    announced.progress()
    store = FakeStore(clock)  # nobody claims: the task expires
    with pytest.raises(ProxyDispatchError):
        _adapter(clock, store, context=announced, host_call=replace(CALL, timeout_seconds=30)).complete(REQUEST)
    assert announced.in_call is False, "the finally ended it"


def test_a_call_refused_for_lack_of_time_is_never_announced(clock: Clock) -> None:
    tired = _context(used=_context().watchdog_seconds - 10)
    store = FakeStore(clock)
    with pytest.raises(ProxyDispatchError):
        _adapter(clock, store, context=tired).complete(REQUEST)
    assert tired.in_call is False


def test_the_timeout_in_the_task_is_the_window_it_was_given_within_the_contracts_bounds() -> None:
    assert CALL.members(900.4)["timeout_seconds"] == 900
    assert CALL.members(0.2)["timeout_seconds"] == 1, "at least one second"
    assert CALL.members(99999)["timeout_seconds"] == 7200, "at most the contract's 7200"


def test_a_cell_with_too_little_time_left_is_refused_before_a_task_is_written(clock: Clock) -> None:
    store = FakeStore(clock)
    tired = _context(used=_context().watchdog_seconds - 10)
    with pytest.raises(ProxyDispatchError) as raised:
        _adapter(clock, store, context=tired).complete(REQUEST)
    assert raised.value.dispatch_class == "not_sent" and store.task is None


# --- the sign of life ----------------------------------------------------------------------------------------------------


class Watched:
    """An attempt's context that remembers the moments a sign of life was recorded (it wraps the real one, so ``live`` and the remainder are real)."""

    def __init__(self) -> None:
        self._real = AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic(), call_id="mc_1")
        self.signs: list[float | None] = []
        self.run_id, self.attempt_id, self.call_id = "run_1", "att_1", "mc_1"

    def progress(self, now: float | None = None) -> None:
        self.signs.append(now)
        self._real.progress(now)

    def remaining_seconds(self, now: float | None = None) -> float:
        return self._real.remaining_seconds(now)

    @property
    def live(self) -> bool:
        return self._real.live


def _watched() -> Watched:
    return Watched()


def test_a_claim_and_each_extension_of_it_is_a_sign_of_life(clock: Clock) -> None:
    def script(c: Clock, store: FakeStore) -> None:
        if store.task is None:
            return
        if c.now >= 1004 and store.task.state == "open":
            store.claim()
        elif store.task.state == "claimed" and c.now < 1030:
            # the agent extends its lease every ~40 s while its CLI outputs: here, each poll moves the lease on
            store.task = replace(store.task, claim_expires_at=T0 + timedelta(seconds=c.now))
        if c.now >= 1030:
            store.answered('{"observations": []}', MODEL)

    store, context = FakeStore(clock, script), _watched()
    _adapter(clock, store, context=context).complete(REQUEST)
    assert len(context.signs) >= 3, "the claim, then every extension"
    assert context.live is True


def test_a_lease_that_does_not_move_is_not_a_second_sign_of_life(clock: Clock) -> None:
    """A hung CLI: the agent stops extending, the lease stays where it was, and the Attempt hears nothing more."""
    def script(c: Clock, store: FakeStore) -> None:
        if store.task is not None and store.task.state == "open":
            store.claim()
        if c.now >= 1040 and store.task is not None and store.task.state == "claimed":
            store.answered('{"observations": []}', MODEL)

    store, context = FakeStore(clock, script), _watched()
    _adapter(clock, store, context=context).complete(REQUEST)
    assert len(context.signs) == 1, "only the claim itself"


def test_an_unclaimed_task_is_no_sign_of_life(clock: Clock) -> None:
    store, context = FakeStore(clock), _watched()
    store_task_never_claimed = pytest.raises(ProxyDispatchError)
    with store_task_never_claimed:
        _adapter(clock, store, context=context, host_call=replace(CALL, timeout_seconds=30)).complete(REQUEST)
    assert context.signs == [] and context.live is False
    assert clock.now - 1000 <= 34, "it waited the cell's 30 s, not the revision's 3600 s"


def test_a_connections_own_call_takes_no_sign_of_life_from_its_claim(clock: Clock) -> None:
    """The single-model agent extends its claim whatever its CLI does; counting that would let a hung CLI hold the Attempt to its cap."""
    def script(c: Clock, store: FakeStore) -> None:
        if store.task is not None and store.task.state == "open":
            store.claim()
        if c.now >= 1010 and store.task is not None and store.task.state == "claimed":
            store.answered('{"observations": []}', MODEL)

    store, context = FakeStore(clock, script), _watched()
    _adapter(clock, store, context=context, host_call=None).complete(REQUEST)
    assert context.signs == [] and context.live is False
