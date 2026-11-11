"""The comparison loop claims only when it may (`CMP-WORK-01`, ADR-0025 decisions 4, 6 and 23).

The runner's gates, against the real reads they stand for: the module flag (a module that is off
has its queued work paused), the global pause (``execution_control.paused``, read through
``execution/public.py``) and the strict priority of Runs (``jobs/public.py``'s ``next_queued_run``,
the very hint the worker's dispatch loop uses). ADR verification 4 and 15.

`D-684` adds the third hold: the night window of the vectors (``vector_control.window_state``, ADR-0029 decision 8). While it is ``draining``
or ``encoding`` the loop starts no new attempt, so the encoder never runs beside one on the 4 GB host; ``closed`` and ``skipped`` hold nothing,
and an attempt that is already running is not touched (the window's drain waits for it).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.public import JobRepository

pytestmark = pytest.mark.usefixtures("quiet_runs")


def test_a_module_that_is_off_has_its_queued_work_paused_and_turning_it_on_resumes_it(
    queue, make_runner, worker_id
) -> None:
    versions, stages = queue.enqueue(module="versions"), queue.enqueue(module="stages")
    only_versions = make_runner(modules=frozenset({"versions"}))
    taken = only_versions.claim(worker_id)
    assert taken is not None and taken.work_id == versions
    assert only_versions.claim(worker_id) is None, "the stages item waits while that module is off"
    assert queue.work(stages)["state"] == "queued", "paused by the flag, not by a state change"
    both = make_runner(modules=frozenset({"versions", "stages"}))
    assert both.claim(worker_id).work_id == stages


def test_with_no_module_on_nothing_is_claimed(queue, make_runner, worker_id) -> None:
    work_id = queue.enqueue(module="versions")
    assert make_runner(modules=frozenset()).claim(worker_id) is None
    assert queue.work(work_id)["state"] == "queued"
    assert make_runner(modules=frozenset({"versions"})).claim(worker_id).work_id == work_id


def test_the_global_pause_stops_every_claim_and_lifting_it_resumes_them(queue, sessions, make_runner, worker_id) -> None:
    work_id = queue.enqueue()
    runner = make_runner()
    with sessions() as session:
        JobRepository().set_paused(session, paused=True)
        session.commit()
    assert runner.claim(worker_id) is None
    assert queue.work(work_id)["state"] == "queued"
    with sessions() as session:
        JobRepository().set_paused(session, paused=False)
        session.commit()
    assert runner.claim(worker_id).work_id == work_id


def test_a_claimable_run_keeps_the_comparison_loop_from_claiming_until_the_run_is_taken(
    queue, sessions, make_runner, worker_id, queue_run
) -> None:
    work_id = queue.enqueue()
    runner = make_runner()
    run_id = queue_run()
    assert runner.claim(worker_id) is None, "a Run is claimable: the Run goes first"
    assert queue.work(work_id)["state"] == "queued"
    with sessions() as session:
        JobRepository().cancel_for_run(session, run_id=run_id)
        session.commit()
    assert runner.claim(worker_id).work_id == work_id, "no Run is claimable any more"


def test_a_run_that_arrives_while_an_item_runs_waits_for_that_one_item_and_the_next_item_waits_for_the_run(
    queue, sessions, make_runner, worker_id, queue_run
) -> None:
    first, second = queue.enqueue(priority=10), queue.enqueue()
    runner = make_runner()
    item = runner.claim(worker_id)
    assert item.work_id == first
    run_id = queue_run()
    assert runner.execute(item) == "succeeded", "an item in flight is never preempted"
    assert runner.claim(worker_id) is None, "between items the Run goes first"
    with sessions() as session:
        JobRepository().cancel_for_run(session, run_id=run_id)
        session.commit()
    assert runner.claim(worker_id).work_id == second


def test_the_gates_are_checked_before_the_queue_is_touched(queue, make_runner, worker_id) -> None:
    from auditmanager.comparison.public import ClaimGates

    work_id = queue.enqueue()
    for gates in (
        ClaimGates(paused=lambda s: True, run_claimable=lambda s: False),
        ClaimGates(paused=lambda s: False, run_claimable=lambda s: True),
    ):
        assert make_runner(gates=gates).claim(worker_id) is None
        assert queue.work(work_id)["state"] == "queued"
    open_gates = ClaimGates(paused=lambda s: False, run_claimable=lambda s: False)
    item = make_runner(gates=open_gates).claim(worker_id)
    assert item.work_id == work_id


# -- `D-684`: the night window of the vectors holds new attempts ---------------------------------------------------------------


@pytest.fixture
def vector_window(sessions: sessionmaker[Session]) -> Iterator[Callable[[str, str | None], None]]:
    """``put(state, reason)`` sets ``vector_control.window_state``; what the row held before the test is put back afterwards."""

    def put(state: str, reason: str | None = None) -> None:
        with sessions() as session:
            session.execute(
                text("UPDATE vector_control SET window_state = :s, window_reason = :r WHERE control_key = 'default'"),
                {"s": state, "r": reason},
            )
            session.commit()

    with sessions() as session:
        state, reason = session.execute(
            text("SELECT window_state, window_reason FROM vector_control WHERE control_key = 'default'")
        ).one()
    put("closed")
    try:
        yield put
    finally:
        put(str(state), None if reason is None else str(reason))


@pytest.mark.parametrize("state", ["draining", "encoding"])
def test_a_new_attempt_is_not_started_while_the_vector_window_is_open_and_is_when_it_closes(
    queue, make_runner, worker_id, vector_window, state: str
) -> None:
    work_id = queue.enqueue()
    runner = make_runner()
    vector_window(state)
    assert runner.claim(worker_id) is None, f"the window is {state}: no new attempt, the encoder needs the memory"
    assert queue.work(work_id)["state"] == "queued", "held, not changed: the item waits where it was"
    assert queue.attempts(work_id) == [], "and no attempt was made for it"
    vector_window("closed")
    item = runner.claim(worker_id)
    assert item is not None and item.work_id == work_id, "the moment the window closes the same item is claimed"


@pytest.mark.parametrize(("state", "reason"), [("closed", None), ("skipped", "encoder_failed")])
def test_a_closed_or_skipped_vector_window_holds_nothing(
    queue, make_runner, worker_id, vector_window, state: str, reason: str | None
) -> None:
    work_id = queue.enqueue()
    vector_window(state, reason)
    item = make_runner().claim(worker_id)
    assert item is not None and item.work_id == work_id, "a night that did not take place costs no comparison work"


def test_an_attempt_that_is_running_when_the_vector_window_opens_is_not_killed_and_the_next_waits(
    queue, make_runner, worker_id, vector_window
) -> None:
    first, second = queue.enqueue(priority=10), queue.enqueue()
    runner = make_runner()
    item = runner.claim(worker_id)
    assert item is not None and item.work_id == first
    vector_window("draining")
    assert runner.execute(item) == "succeeded", "the drain waits for the running attempt; the window never ends it"
    assert queue.work(first)["state"] == "succeeded"
    assert runner.claim(worker_id) is None, "the next item waits for the window"
    assert queue.work(second)["state"] == "queued"
    vector_window("closed")
    assert runner.claim(worker_id).work_id == second


def test_the_queue_summary_reports_the_hold_the_loop_obeys(sessions, vector_window) -> None:
    from auditmanager.comparison.public import ComparisonOverviewService

    service = ComparisonOverviewService(session_factory=sessions)
    assert service.get_queue_summary(modules="versions")["paused"] is False
    vector_window("encoding")
    assert service.get_queue_summary(modules="versions")["paused"] is True, "the queue screen says what the loop does: nothing is issued"
    vector_window("skipped", "encoder_failed")
    assert service.get_queue_summary(modules="versions")["paused"] is False
