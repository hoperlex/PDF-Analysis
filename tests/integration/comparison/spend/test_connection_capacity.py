"""`EXEC2-CAP-01` (ADR-0026 decision 1) -- a comparison model call takes one unit of its connection's capacity, the way
a Run does, and the two are decided under one lock.

Real PostgreSQL (the lane's stack: see ``conftest.py``). These tests are written and **not run** in EXEC-2 (`R-149d`,
D-292); each would pass against PostgreSQL. ``test_connection_single_user.py`` is untouched and says the same of the
default capacity of one; this file says it of more.

* a Run and a call draw on the same units: a call is refused while the Runs and the other calls hold every unit, and a
  Run's claim is refused while a call does (``test_a_comparison_call_takes_a_unit...``, ``test_the_free_unit_question...``, which also holds the occupancy read to the same count);
* calls overlap up to the capacity and no further (``test_calls_overlap...``);
* a call and a Run's claim never both take the last unit -- by the lock and in a race
  (``test_a_comparison_call_waits...``, ``test_a_call_and_a_claim_racing...``);
* the capacity is the connection's **current** revision's, not the one the route froze;
* a call of an attempt that is over holds nothing, at any capacity.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import CallRefused
from auditmanager.executors.queries import Occupancy, occupancy_of
from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.shared.errors import ErrorCode

_SUPPORT_NAME = "exec2_cap_connection_capacity_support"
if _SUPPORT_NAME in sys.modules:
    cap: ModuleType = sys.modules[_SUPPORT_NAME]
else:
    _spec = importlib.util.spec_from_file_location(
        _SUPPORT_NAME,
        Path(__file__).resolve().parents[2] / "jobs" / "connection_capacity_support.py",
    )
    assert _spec is not None and _spec.loader is not None
    cap = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT_NAME] = cap
    _spec.loader.exec_module(cap)


def _run_claim_is_refused(sessions: Any, revision: str | None) -> bool:
    """Queue a Run on ``revision`` and try the shipped claim: ``True`` if it was refused (and then the Run and its Job
    are exactly as they were), ``False`` if it claimed (the Run is then ended and cancelled again)."""
    run_id = cap.queue_run(sessions, revision)
    try:
        try:
            authority = cap.claim(sessions, run_id)
        except ExecutionNotClaimed as refusal:
            assert refusal.code is ErrorCode.CONFLICT
            assert cap.job_state(sessions, run_id) == "queued" and cap.attempts(sessions, run_id) == 0
            return True
        cap.finish(sessions, authority)
        return False
    finally:
        cap.cancel(sessions, run_id)


def _a_backend_waits_on_a_lock(engine: Any) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname = current_database() "
            "AND pid <> pg_backend_pid() AND state = 'active' AND wait_event_type = 'Lock')"
        )).scalar_one())


# --- a call takes a unit the Runs draw on ------------------------------------------------------------------------------


def test_a_comparison_call_takes_a_unit_from_the_same_budget_as_the_runs(
    caller: Any, queue: Any, sessions: Any, h: Any, clean_day: None,
) -> None:
    """Capacity two, one Run active. The call takes the last unit, so while it is in flight a Run's claim is
    refused; when it returns the unit is free again."""
    _connection, revision = cap.new_connection(sessions, capacity=2)
    item = queue.claimed()
    running = cap.queue_run(sessions, revision)
    authority = cap.claim(sessions, running)
    during: list[bool] = []
    adapter = h.ScriptedAdapter(
        reply=h.reply(cost=0.1), on_call=lambda request: during.append(_run_claim_is_refused(sessions, revision)),
    )
    try:
        h.make_call(caller, item, adapter, revision)
        assert adapter.calls == 1, "the call was refused although a unit was free"
        assert during == [True], "a Run was claimed while a Run and a call held both units"
        assert _run_claim_is_refused(sessions, revision) is False
    finally:
        cap.finish(sessions, authority)
        cap.cancel(sessions, running)


def test_a_comparison_call_is_refused_when_the_runs_hold_every_unit_and_is_not_when_one_is_free(
    caller: Any, queue: Any, journal: Any, sessions: Any, h: Any, clean_day: None,
) -> None:
    _connection, revision = cap.new_connection(sessions, capacity=2)
    item = queue.claimed()
    runs = [cap.queue_run(sessions, revision) for _ in range(2)]
    authorities = []
    try:
        authorities.append(cap.claim(sessions, runs[0]))
        free = h.ScriptedAdapter(reply=h.reply(cost=0.1))
        h.make_call(caller, item, free, revision, label="one unit free")
        assert free.calls == 1
        authorities.append(cap.claim(sessions, runs[1]))
        full = h.ScriptedAdapter(reply=h.reply())
        with pytest.raises(CallRefused) as refusal:
            h.make_call(caller, item, full, revision, label="no unit free")
        assert refusal.value.reason == "connection_busy" and refusal.value.pauses_job is False
        assert full.calls == 0
        assert [row["state"] for row in journal.rows(item.work_id)] == ["completed"], "a refused call left a row"
    finally:
        for authority in authorities:
            cap.finish(sessions, authority)
        for run_id in runs:
            cap.cancel(sessions, run_id)


# --- the question both sides ask ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(("capacity", "runs", "calls", "free"), [
    (1, 0, 0, True), (1, 1, 0, False), (1, 0, 1, False),
    (2, 1, 0, True), (2, 0, 1, True), (2, 1, 1, False), (2, 0, 2, False),
    (3, 2, 0, True), (3, 1, 1, True), (3, 2, 1, False), (3, 0, 3, False),
])
def test_the_free_unit_question_a_runs_claim_and_the_occupancy_read_agree_on_what_is_in_use(
    capacity: int, runs: int, calls: int, free: bool,
    queue: Any, journal: Any, sessions: Any, repository: Any,
) -> None:
    connection, revision = cap.new_connection(sessions, capacity=capacity)
    claimed = [cap.claim(sessions, cap.queue_run(sessions, revision)) for _ in range(runs)]
    run_ids = list(cap.active_runs(sessions, connection))
    try:
        for index in range(calls):
            item = queue.claimed(call=index)
            journal.insert(item.work_id, item.attempt_id, state="sent" if index % 2 else "prepared",
                           estimate_micros=1, connection_revision_id=revision)
        with sessions() as session:
            assert repository.connection_has_free_unit(session, connection) is free
            # and the read model counts the same rows the decision does
            assert occupancy_of(session, connection) == Occupancy(capacity, runs, calls)
        assert _run_claim_is_refused(sessions, revision) is (not free)
    finally:
        for authority in claimed:
            cap.finish(sessions, authority)
        for run_id in run_ids:
            cap.cancel(sessions, run_id)


def test_a_call_of_an_attempt_that_is_over_holds_no_unit_at_any_capacity(
    queue: Any, journal: Any, sessions: Any, repository: Any,
) -> None:
    connection, revision = cap.new_connection(sessions, capacity=2)
    held, over = queue.claimed(), queue.claimed()
    journal.insert(held.work_id, held.attempt_id, state="sent", estimate_micros=1, connection_revision_id=revision)
    journal.insert(over.work_id, over.attempt_id, state="sent", estimate_micros=1, connection_revision_id=revision)
    with sessions() as session:
        assert repository.connection_has_free_unit(session, connection) is False       # two live calls, capacity two
    queue.expire_and_reclaim(over, settlers=())                                           # the reclaim ends one attempt
    with sessions() as session:
        assert repository.connection_has_free_unit(session, connection) is True


def test_a_comparison_call_that_has_no_connection_takes_no_unit(
    queue: Any, journal: Any, sessions: Any, repository: Any,
) -> None:
    connection, _revision = cap.new_connection(sessions, capacity=1)
    item = queue.claimed()
    journal.insert(item.work_id, item.attempt_id, state="sent", estimate_micros=1, connection_revision_id=None)
    with sessions() as session:
        assert repository.connection_has_free_unit(session, connection) is True


# --- the capacity is the current revision's ---------------------------------------------------------------------------------


def test_the_capacity_is_the_connections_current_revision_and_not_the_one_the_route_froze(
    caller: Any, queue: Any, sessions: Any, h: Any, clean_day: None,
) -> None:
    """The route names revision 1 (capacity absent, so one) and a Run is active. Revision 2 raises the capacity: the
    call is now admitted, though its route still names revision 1."""
    connection, first_revision = cap.new_connection(sessions)
    item = queue.claimed()
    running = cap.queue_run(sessions, first_revision)
    authority = cap.claim(sessions, running)
    try:
        refused = h.ScriptedAdapter(reply=h.reply())
        with pytest.raises(CallRefused):
            h.make_call(caller, item, refused, first_revision, label="capacity one")
        assert refused.calls == 0
        cap.new_revision_with_capacity(sessions, connection, 2, 2)
        admitted = h.ScriptedAdapter(reply=h.reply(cost=0.1))
        h.make_call(caller, item, admitted, first_revision, label="capacity two")
        assert admitted.calls == 1
    finally:
        cap.finish(sessions, authority)
        cap.cancel(sessions, running)


# --- calls overlap up to the capacity ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("capacity", [1, 2, 3])
def test_calls_overlap_up_to_the_capacity_and_no_further(
    capacity: int, caller: Any, queue: Any, sessions: Any, h: Any, clean_day: None,
) -> None:
    """Three calls of three items on one connection, each started from inside the previous one's flight."""
    _connection, revision = cap.new_connection(sessions, capacity=capacity)
    items = [queue.claimed(call=index) for index in range(3)]
    refused: list[str] = []
    completed: list[int] = []

    def call_at(index: int) -> None:
        def on_call(request: Any) -> None:
            if index + 1 < len(items):
                try:
                    call_at(index + 1)
                except CallRefused as refusal:
                    refused.append(refusal.reason)

        adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1), on_call=on_call)
        h.make_call(caller, items[index], adapter, revision, label=f"call-{index}")
        completed.append(index)

    call_at(0)
    assert len(completed) == min(capacity, 3), (capacity, completed, refused)
    assert refused == ([] if capacity >= 3 else ["connection_busy"])


# --- the lock, and the race ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("capacity", "expected"), [(2, "connection_busy"), (3, "sent")])
def test_a_comparison_call_waits_for_a_run_claim_that_holds_the_connection_lock_and_then_counts_it(
    capacity: int, expected: str, caller: Any, queue: Any, journal: Any, sessions: Any,
    comparison_engine: Any, h: Any, clean_day: None,
) -> None:
    """One Run is active. A second Run's claim has taken the connection's lock and has not committed; the call queues
    on that lock rather than reading around it. When the claim commits, two units are in use: at capacity two the call
    is refused, at capacity three it is sent."""
    _connection, revision = cap.new_connection(sessions, capacity=capacity)
    item = queue.claimed()
    first, second = cap.queue_run(sessions, revision), cap.queue_run(sessions, revision)
    first_authority = cap.claim(sessions, first)
    holder = sessions()
    result: list[object] = []
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1))
    second_authority = None
    committed = False

    def call() -> None:
        try:
            h.make_call(caller, item, adapter, revision)
            result.append("sent")
        except CallRefused as refusal:
            result.append(refusal.reason)

    try:
        second_authority = JobRepository().start_execution(holder, run_id=second)       # lock taken, nothing committed
        thread = threading.Thread(target=call)
        thread.start()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not _a_backend_waits_on_a_lock(comparison_engine):
            if result:
                break
            time.sleep(0.05)
        assert not result, f"the call did not wait for the Run's claim: {result}"
        assert _a_backend_waits_on_a_lock(comparison_engine)
        holder.commit()
        committed = True
        thread.join(30)
        assert result == [expected], result
        assert adapter.calls == (1 if expected == "sent" else 0)
        assert len(journal.rows(item.work_id)) == (1 if expected == "sent" else 0)
    finally:
        holder.close()
        cap.finish(sessions, first_authority)
        if committed and second_authority is not None:
            cap.finish(sessions, second_authority)
        cap.cancel(sessions, first)
        cap.cancel(sessions, second)


def test_a_call_and_a_claim_racing_for_the_last_unit_have_exactly_one_winner(
    caller: Any, queue: Any, sessions: Any, h: Any, clean_day: None,
) -> None:
    """Capacity two, one Run active. A comparison call and a second Run's claim start together: whichever the lock
    lets in first takes the last unit and the other is refused. Never both, never neither."""
    connection, revision = cap.new_connection(sessions, capacity=2)
    item = queue.claimed()
    first, second = cap.queue_run(sessions, revision), cap.queue_run(sessions, revision)
    first_authority = cap.claim(sessions, first)
    start = threading.Barrier(2)
    outcome: dict[str, Any] = {}
    claimed_authority: list[Any] = []

    def claim_run() -> None:
        start.wait(timeout=30)
        try:
            claimed_authority.append(cap.claim(sessions, second))
            outcome["run"] = "claimed"
        except ExecutionNotClaimed:
            outcome["run"] = "refused"
        except BaseException as failure:
            outcome["run"] = failure

    def make_call() -> None:
        start.wait(timeout=30)
        adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1), on_call=lambda request: time.sleep(1.0))
        try:
            h.make_call(caller, item, adapter, revision)
            outcome["call"] = "sent"
        except CallRefused as refusal:
            outcome["call"] = refusal.reason
        except BaseException as failure:
            outcome["call"] = failure

    threads = [threading.Thread(target=claim_run), threading.Thread(target=make_call)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
        assert (outcome["run"] == "claimed") != (outcome["call"] == "sent"), outcome
        assert outcome["run"] in ("claimed", "refused") and outcome["call"] in ("sent", "connection_busy"), outcome
        assert len(cap.active_runs(sessions, connection)) == (2 if outcome["run"] == "claimed" else 1)
    finally:
        cap.finish(sessions, first_authority)
        for authority in claimed_authority:
            cap.finish(sessions, authority)
        cap.cancel(sessions, first)
        cap.cancel(sessions, second)
