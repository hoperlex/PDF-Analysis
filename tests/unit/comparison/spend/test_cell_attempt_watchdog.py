"""`D-674` (`HOSTS-DEBTS-01`): the attempt watchdog of a comparison item follows the frozen cell's timeout, for a job with a cell only.

The queue fences an attempt 900 s after it began, and a pull call's window is ``min(its timeout, what the watchdog leaves - 60 s)``, so a call of a job
with a cell was held to about 840 s and the 1800 s of the sheet changes and the 2400 s of the report (the original's values) were unreachable. Now the
call's context grants the attempt ``elapsed + cell timeout + 60 s`` when the call is bound -- never less than the 900 s -- and the same grant reaches
the heartbeat that fences (``WorkItem.watchdog``). A job without a cell binds as before and keeps 900 s exactly.

Container-free. The task table of ``tests/unit/executors/test_pull_adapter.py``, a fake of the two statements of the context, and the heartbeat of
``tests/unit/comparison/work/test_runner_unit.py``.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import CellSettings
from auditmanager.comparison.spend.cell import host_call_of
from auditmanager.comparison.spend.pull_images import ComparisonCallContext
from auditmanager.comparison.work.model import ATTEMPT_WATCHDOG_SECONDS, ItemAuthority, ItemWatchdog, WorkItem
from auditmanager.executors import pull
from auditmanager.executors.public import DEADLINE_MARGIN_SECONDS
from auditmanager.executors.pull import PullAdapter, answer_window
from tests.unit.comparison.spend.test_caller_unit import FakeItem, Log, _call, _consent, _make, _reply, _route, Adapter
from tests.unit.comparison.work.test_runner_unit import FakeRepository, _beat, _wait
from tests.unit.executors.test_pull_adapter import MODEL, REQUEST, Clock, FakeStore, Sessions, revision

ELAPSED = 30.0


#: A cell's timeout is the constant of its kind (`LIMITS-01`, `R-153o`), so a timeout under test is reached by naming the kind that has it.
KIND_OF_TIMEOUT = {900: "comparison_pair_check", 1800: "comparison_sheet_changes", 2400: "comparison_report"}


def cell(timeout: int) -> CellSettings:
    made = CellSettings(f"{KIND_OF_TIMEOUT[timeout]}:main", MODEL, "medium")
    assert made.timeout_seconds == timeout
    return made


def work_item() -> WorkItem:
    return WorkItem(
        work_id="cq_X", attempt_id="cqa_X", attempt_no=1, project_uid="prj_X", module="versions", kind="ai_sheets", payload={},
        comparison_upload_id=None, created_by_user_uid=None, max_attempts=3, authority=ItemAuthority("cq_X", "cqa_X", "token"))


class Attempt:
    """The row of ``comparison_work_attempt`` the context reads, and the clock of the database it is read on."""

    def __init__(self, elapsed: float = ELAPSED, running: bool = True) -> None:
        self.elapsed, self.running = elapsed, running

    def sessions(self) -> Any:
        attempt = self

        @contextmanager
        def open_session() -> Any:
            class Session:
                def execute(self, statement: Any, parameters: dict[str, Any]) -> Any:
                    assert "comparison_work_attempt" in str(statement) and parameters["attempt"] == "cqa_X"
                    if not attempt.running:
                        value = None
                    elif "watchdog" in parameters:  # created_at + watchdog - now
                        value = parameters["watchdog"] - attempt.elapsed
                    else:  # now - created_at
                        value = attempt.elapsed
                    return SimpleNamespace(scalar_one_or_none=lambda: value)

            yield Session()

        return open_session


def bound(timeout: int | None, attempt: Attempt | None = None) -> tuple[ComparisonCallContext, WorkItem]:
    item, context = work_item(), ComparisonCallContext((attempt or Attempt()).sessions())
    if timeout is None:
        context.bind(item, "cmc_1")
    else:
        context.bind(item, "cmc_1", window_seconds=timeout)
    return context, item


# --- the context ---------------------------------------------------------------------------------------------------------


def test_a_job_with_no_cell_keeps_the_queues_900_seconds_exactly() -> None:
    context, item = bound(None)
    assert ATTEMPT_WATCHDOG_SECONDS == 900.0
    assert context.remaining_seconds() == 900.0 - ELAPSED
    assert item.watchdog.limit(ATTEMPT_WATCHDOG_SECONDS) == 900.0, "the heartbeat fences at the queue's number"
    window = answer_window(3600, context)
    assert window == 900.0 - ELAPSED - DEADLINE_MARGIN_SECONDS, "a call of a job without a cell is held as it always was"


@pytest.mark.parametrize("timeout", [1800, 2400])
def test_a_cells_timeout_is_reachable_as_the_window_of_its_call(timeout: int) -> None:
    context, item = bound(timeout)
    window = answer_window(timeout, context)
    assert window == float(timeout), f"the call may wait the cell's {timeout} s, not about 840 s"
    assert item.watchdog.limit(ATTEMPT_WATCHDOG_SECONDS) == ELAPSED + timeout + DEADLINE_MARGIN_SECONDS, "and the heartbeat fences after the call, not before"


def test_a_cell_with_a_short_timeout_never_lowers_the_watchdog() -> None:
    context, item = bound(600)
    assert context.remaining_seconds() == 900.0 - ELAPSED and item.watchdog.limit(ATTEMPT_WATCHDOG_SECONDS) == 900.0
    assert answer_window(600, context) == 600.0


def test_the_grant_counts_the_time_the_attempt_has_already_run() -> None:
    """A second call of the same item, after 1000 s of work: it still gets its whole window."""
    attempt = Attempt(elapsed=1000.0)
    context, item = bound(1800, attempt)
    assert answer_window(1800, context) == 1800.0
    assert item.watchdog.limit(ATTEMPT_WATCHDOG_SECONDS) == 1000.0 + 1800 + DEADLINE_MARGIN_SECONDS


def test_each_call_is_judged_on_its_own_and_the_heartbeat_never_loses_a_grant() -> None:
    attempt = Attempt()
    item, context = work_item(), ComparisonCallContext(attempt.sessions())
    context.bind(item, "cmc_1", window_seconds=2400)
    granted = item.watchdog.limit(ATTEMPT_WATCHDOG_SECONDS)
    context.bind(item, "cmc_2")  # the next call of the item names no cell window
    assert context.remaining_seconds() == 900.0 - ELAPSED, "the context is back at the queue's number for it"
    assert item.watchdog.limit(ATTEMPT_WATCHDOG_SECONDS) == granted, "a grant only ever raises what the heartbeat allows"


def test_an_attempt_that_is_not_running_is_granted_nothing() -> None:
    context, item = bound(1800, Attempt(running=False))
    assert context.remaining_seconds() == 0.0 and item.watchdog.limit(ATTEMPT_WATCHDOG_SECONDS) == 900.0


def test_the_margin_is_the_one_a_pull_call_keeps_today() -> None:
    assert DEADLINE_MARGIN_SECONDS == pull.DEADLINE_MARGIN_SECONDS == 60


# --- the watchdog of the item ----------------------------------------------------------------------------------------------


def test_a_grant_only_raises_the_limit() -> None:
    watchdog = ItemWatchdog()
    assert watchdog.limit(900.0) == 900.0
    watchdog.allow(600.0)
    assert watchdog.limit(900.0) == 900.0
    watchdog.allow(2000.0)
    watchdog.allow(1500.0)
    assert watchdog.limit(900.0) == 2000.0 and watchdog.limit(5000.0) == 5000.0, "the queue's own number can still be the larger"


def test_a_granted_item_is_not_fenced_at_the_queues_watchdog_and_an_ungranted_one_is() -> None:
    granted, plain = work_item(), work_item()
    granted.watchdog.allow(60.0)
    fenced: list[int] = []
    beats = []
    for item in (granted, plain):
        beat = _beat(FakeRepository([]), item, watchdog=0.15, fence=lambda session, attempt_id, item=item: fenced.append(id(item)))
        beat.start()
        beats.append(beat)
    _wait(plain.lease_lost.is_set, "the plain item's watchdog")
    time.sleep(0.3)
    assert not granted.lease_lost.is_set(), "past the queue's watchdog but inside its grant: still beating"
    for beat in beats:
        beat.stop()
    assert fenced == [id(plain)], "only the item without a grant was fenced"


# --- the whole chain: the window the task is given ------------------------------------------------------------------------------


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(pull.time, "sleep", fake.sleep)
    return fake


def _answered(c: Clock, store: FakeStore) -> None:
    if store.task is not None and store.task.state == "open":
        store.claim()
        store.answered('{"observations": []}', MODEL)


@pytest.mark.parametrize("timeout", [1800, 2400])
def test_the_task_of_a_call_carries_the_cells_timeout_as_its_window(clock: Clock, timeout: int) -> None:
    context, _item = bound(timeout)
    store = FakeStore(clock, _answered)
    adapter = PullAdapter(session_factory=Sessions(), revision=revision(deadline=3600), context=context, repository=store,  # type: ignore[arg-type]
                          poll_seconds=2.0, monotonic=clock.monotonic, host_call=host_call_of(cell(timeout), provider="claude_code", access="subscription"))
    adapter.complete(REQUEST)
    assert store.payload is not None and store.payload["host"]["timeout_seconds"] == timeout
    assert store.inserted["deadline_seconds"] == float(timeout)
    # before the grant the same call was held to the queue's watchdog less what had run and the margin
    unbound, _ = bound(None)
    assert answer_window(timeout, unbound) == 900.0 - ELAPSED - DEADLINE_MARGIN_SECONDS < timeout


# --- the caller binds the cell's window only for a job that has a cell -----------------------------------------------------------------


class RecordingContext:
    def __init__(self) -> None:
        self.bound: list[tuple[str, dict[str, Any]]] = []

    def bind(self, item: Any, call_id: str, **window: Any) -> None:
        self.bound.append((call_id, window))


def test_the_wrapper_names_the_cells_timeout_when_it_binds_the_context_of_a_call_and_names_none_otherwise() -> None:
    for consent, expected in ((_consent(cell=cell(1800)), {"window_seconds": 1800}), (_consent(), {})):
        log = Log()
        context = RecordingContext()
        _call(_make(log), FakeItem(log), _route(Adapter(log, reply=_reply()), call_context=context), consent)
        assert context.bound == [("cmc_01", expected)]
