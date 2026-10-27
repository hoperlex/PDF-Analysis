"""The comparison loop claims only when it may (`CMP-WORK-01`, ADR-0025 decisions 4, 6 and 23).

The runner's gates, against the real reads they stand for: the module flag (a module that is off
has its queued work paused), the global pause (``execution_control.paused``, read through
``execution/public.py``) and the strict priority of Runs (``jobs/public.py``'s ``next_queued_run``,
the very hint the worker's dispatch loop uses). ADR verification 4 and 15.
"""

from __future__ import annotations

import pytest

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
