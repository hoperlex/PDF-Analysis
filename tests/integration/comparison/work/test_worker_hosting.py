"""The worker hosts the comparison loop as a second claimant (`CMP-WORK-01`, ADR-0025 decisions 4, 6, 23).

The real ``WorkerService`` over the lane's database, with a stub handler and a stub Run executor that
claims the Job through ``jobs`` as the shipped executor does. What is shown: an item runs in a slot of
the worker's pool and names the worker on its attempt; it counts against the slots and a drain waits
for it; Runs keep strict priority at the service level too (and are never preempted by an item in
flight); a module that is off claims nothing yet the expired leases are still reclaimed; and the
service refuses to start while an enabled module has live work no handler serves.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from auditmanager.comparison.public import ComparisonWorkRunner, UnhandledKindError
from auditmanager.jobs.public import JobRepository
from auditmanager.workers.public import WorkerService

pytestmark = pytest.mark.usefixtures("quiet_runs")

# The stub handler lives in the conftest; this one blocks until the test lets it go.

WAIT = 30.0


def _wait_for(predicate: Callable[[], object], what: str, timeout: float = WAIT) -> object:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError(f"timed out after {timeout:.0f} s waiting for {what}")


@pytest.fixture
def start_service(engine, sessions) -> Iterator[Callable[..., WorkerService]]:  # type: ignore[no-untyped-def]
    started: list[WorkerService] = []

    def start(runner: ComparisonWorkRunner, *, slots: int = 1, execute=None) -> WorkerService:  # type: ignore[no-untyped-def]
        service = WorkerService(
            engine=engine, session_factory=sessions, execute=execute or (lambda run_id, worker: None),
            version="cmp-work-01-test", slots=slots, poll_seconds=0.2, heartbeat_seconds=0.5,
            reclaim_seconds=0.5, comparison_work=runner,
        )
        service.start()
        started.append(service)
        return service

    yield start
    for service in started:
        service.drain(timeout=WAIT)
        service.stop()


@pytest.fixture
def run_executor(sessions):  # type: ignore[no-untyped-def]
    """A stand-in for ``run_to_terminal`` that claims the Job as the shipped executor does."""
    order: list[str] = []
    gate = threading.Event()
    gate.set()

    def execute(run_id: str, worker: str) -> None:
        jobs = JobRepository(worker_id=worker)
        with sessions() as session:
            authority = jobs.start_execution(session, run_id=run_id)
            session.commit()
        order.append("run")
        gate.wait(timeout=WAIT)
        with sessions() as session:
            jobs.finish_execution(session, authority, publishes_result=False)
            session.commit()

    execute.order = order  # type: ignore[attr-defined]
    execute.gate = gate  # type: ignore[attr-defined]
    return execute


def test_a_worker_runs_a_queued_item_to_its_end_and_names_itself_on_the_attempt(
    queue, make_runner, start_service
) -> None:
    work_id = queue.enqueue(payload={"page": 1})
    service = start_service(make_runner())
    _wait_for(lambda: queue.work(work_id)["state"] == "succeeded", "the item to succeed")
    (attempt,) = queue.attempts(work_id)
    assert (attempt["state"], attempt["worker_id"]) == ("succeeded", service.worker_id)


class Blocking:
    """A handler that says it has entered and then waits for the test, so a slot stays occupied."""

    def __init__(self, kind: str, *, expected: int = 1) -> None:
        self.kind = kind
        self.entered = threading.Semaphore(0)
        self.release = threading.Event()
        self.order: list[str] = []

    def run(self, item: Any) -> Any:
        from auditmanager.comparison.public import Completed

        self.order.append(item.work_id)
        self.entered.release()
        assert self.release.wait(timeout=WAIT), "the test never released the handler"
        return Completed()

    def wait_entered(self, count: int = 1) -> None:
        for _ in range(count):
            assert self.entered.acquire(timeout=WAIT), "no item reached the handler"


def test_an_item_in_flight_occupies_a_slot_and_a_drain_waits_for_it_and_takes_no_more(
    queue, make_runner, start_service
) -> None:
    first, second = queue.enqueue(priority=10), queue.enqueue()
    handler = Blocking(queue.kind)
    service = start_service(make_runner(handler=handler))
    handler.wait_entered()
    assert service.busy == 1, "an item in flight counts against the slots"
    time.sleep(1.0)
    assert queue.work(second)["state"] == "queued", "one slot, one item"
    assert service.drain(timeout=0.3) is False, "a drain waits for the item in flight"
    handler.release.set()
    assert service.drain(timeout=WAIT) is True
    assert queue.work(first)["state"] == "succeeded"
    time.sleep(0.6)
    assert queue.work(second)["state"] == "queued", "a draining worker claims nothing new"


def test_two_slots_run_two_items_at_once(queue, make_runner, start_service) -> None:
    ids = {queue.enqueue(), queue.enqueue()}
    handler = Blocking(queue.kind)
    service = start_service(make_runner(handler=handler), slots=2)
    handler.wait_entered(2)
    assert service.busy == 2
    assert set(handler.order) == ids
    handler.release.set()
    _wait_for(lambda: all(queue.work(w)["state"] == "succeeded" for w in ids), "both items to succeed")


def test_runs_keep_strict_priority_at_the_service_level(
    queue, sessions, make_runner, start_service, queue_run, run_executor
) -> None:
    work_id = queue.enqueue()
    run_id = queue_run()
    handler = Blocking(queue.kind)
    handler.release.set()
    original_run = handler.run
    handler.run = lambda item: (run_executor.order.append("item"), original_run(item))[1]  # type: ignore[method-assign]
    start_service(make_runner(handler=handler), execute=run_executor)
    _wait_for(lambda: queue.work(work_id)["state"] == "succeeded", "the item to succeed")
    assert run_executor.order == ["run", "item"], "the Run was taken first"
    with sessions() as session:
        from sqlalchemy import text
        assert session.execute(
            text("SELECT state FROM job WHERE run_id = :r"), {"r": run_id}).scalar_one() == "failed"


def test_a_run_that_arrives_while_an_item_runs_waits_for_that_item_and_goes_before_the_next_one(
    queue, make_runner, start_service, queue_run, run_executor
) -> None:
    first, second = queue.enqueue(priority=10), queue.enqueue()
    handler = Blocking(queue.kind)
    original_run = handler.run
    handler.run = lambda item: (run_executor.order.append("item"), original_run(item))[1]  # type: ignore[method-assign]
    start_service(make_runner(handler=handler), execute=run_executor)
    handler.wait_entered()
    queue_run()
    time.sleep(1.2)
    assert run_executor.order == ["item"], "an item in flight is not preempted by a Run"
    handler.release.set()
    _wait_for(lambda: queue.work(second)["state"] == "succeeded", "the second item to succeed")
    assert run_executor.order == ["item", "run", "item"], "the Run went between the two items"
    assert queue.work(first)["state"] == "succeeded"


def test_a_module_that_is_off_claims_nothing_yet_its_expired_leases_are_still_reclaimed(
    queue, make_runner, make_worker, start_service
) -> None:
    work_id = queue.enqueue()
    dead = queue.claim(make_worker())
    queue.expire_lease(dead.attempt_id)
    start_service(make_runner(modules=frozenset()))
    _wait_for(lambda: queue.work(work_id)["state"] == "queued", "the expired lease to be reclaimed")
    time.sleep(1.0)
    row = queue.work(work_id)
    assert (row["state"], row["attempt_count"]) == ("queued", 1), "reclaimed, never re-claimed"
    assert [a["state"] for a in queue.attempts(work_id)] == ["lost"]


def test_a_module_that_is_on_runs_what_a_dead_worker_left(queue, make_runner, make_worker, start_service) -> None:
    work_id = queue.enqueue()
    dead = queue.claim(make_worker())
    queue.expire_lease(dead.attempt_id)
    start_service(make_runner())
    _wait_for(lambda: queue.work(work_id)["state"] == "succeeded", "the item to be re-run to its end")
    assert [(a["attempt_no"], a["state"]) for a in queue.attempts(work_id)] == [(1, "lost"), (2, "succeeded")]


def test_the_worker_refuses_to_start_while_an_enabled_module_has_live_work_no_handler_serves(
    queue, engine, sessions, make_runner
) -> None:
    class SomeoneElses:
        kind = "cw_handled_elsewhere"

        def run(self, item: Any) -> Any:
            raise AssertionError("never claimed")

    work_id = queue.enqueue()
    runner = make_runner(handler=SomeoneElses())  # type: ignore[arg-type]
    service = WorkerService(
        engine=engine, session_factory=sessions, execute=lambda run_id, worker: None,
        version="cmp-work-01-test", comparison_work=runner,
    )
    with pytest.raises(UnhandledKindError) as refused:
        service.start()
    assert queue.kind in refused.value.kinds
    with pytest.raises(RuntimeError):
        service.worker_id  # noqa: B018  (never registered: the refusal came first)
    service.stop()
    assert queue.work(work_id)["state"] == "queued"
    # With the module off the same build starts: the refusal is for an enabled module only.
    off = make_runner(handler=SomeoneElses(), modules=frozenset())  # type: ignore[arg-type]
    off.verify()
