"""`EXEC-PAR-QUEUE-01` -- the worker service with several slots and one run per executor connection.

Real PostgreSQL, no object store: the run each slot executes is a stand-in (``Plant``) that makes
the **shipped claim** (``JobRepository.start_execution``) and holds the run until the test lets
it go. Everything the tests assert on is the dispatch loop's behaviour and the database's: which
runs are active together, which stay queued, what a drain waits for.

The poll interval is long (30 s) wherever a test must show that a slot is refilled by the loop
itself and not by a poll: the queue is full before the service starts, so no notification is
waiting, and the only way a second run can start inside the test's window is the immediate refill
after a claim (or, after a run ends, the wake-up its end sets).
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.shared.errors import ErrorCode
from auditmanager.workers.public import WorkerService
from auditmanager.workers.service import CLAIM_RETRY_LIMIT

pytestmark = pytest.mark.usefixtures("quiet_queue")

_SUPPORT_NAME = "exec_par_queue_connection_limit_support"
if _SUPPORT_NAME in sys.modules:
    support: ModuleType = sys.modules[_SUPPORT_NAME]
else:
    _spec = importlib.util.spec_from_file_location(
        _SUPPORT_NAME,
        Path(__file__).resolve().parents[1] / "jobs" / "connection_limit_support.py",
    )
    assert _spec is not None and _spec.loader is not None
    support = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT_NAME] = support
    _spec.loader.exec_module(support)

WAIT_SECONDS = 30.0
#: How long a test watches for something that must NOT happen.
QUIET_SECONDS = 2.0


def _wait_for(predicate: Callable[[], Any], *, what: str, timeout: float = WAIT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out after {timeout:.0f} s waiting for {what}")


class Plant:
    """The stand-in for ``run_to_terminal``: claim for real, then hold until released.

    ``connection_of`` maps a run to its connection so that the plant can record, at the moment each
    run starts, how many runs of the same connection were live: the figure the limit bounds.
    """

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions
        self._lock = threading.Lock()
        self.connection_of: dict[str, str | None] = {}
        self.gates: defaultdict[str, threading.Event] = defaultdict(threading.Event)
        self.live: set[str] = set()
        self.started: list[str] = []
        self.calls: list[str] = []
        self.most_live = 0
        self.most_live_on_one_connection = 0
        self.refuse_always = False

    def __call__(self, run_id: str, worker_id: str) -> None:
        with self._lock:
            self.calls.append(run_id)
        if self.refuse_always:
            raise ExecutionNotClaimed(ErrorCode.CONFLICT, message="refused by the test")
        with self._sessions() as session:
            authority = JobRepository(worker_id=worker_id).start_execution(session, run_id=run_id)
            session.commit()
        with self._lock:
            self.live.add(run_id)
            self.started.append(run_id)
            self.most_live = max(self.most_live, len(self.live))
            connection = self.connection_of.get(run_id)
            if connection is not None:
                together = sum(1 for other in self.live if self.connection_of.get(other) == connection)
                self.most_live_on_one_connection = max(self.most_live_on_one_connection, together)
        try:
            assert self.gates[run_id].wait(timeout=WAIT_SECONDS), "the test never released the run"
        finally:
            support.finish(self._sessions, authority)
            with self._lock:
                self.live.discard(run_id)

    def release(self, *run_ids: str) -> None:
        for run_id in run_ids:
            self.gates[run_id].set()

    def release_all(self) -> None:
        for gate in list(self.gates.values()):
            gate.set()

    def is_live(self, *run_ids: str) -> bool:
        with self._lock:
            return set(run_ids) <= self.live

    def has_started(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self.started


@pytest.fixture
def plant(sessions: sessionmaker[Session]) -> Plant:
    return Plant(sessions)


@pytest.fixture
def start_service(
    engine: Engine, sessions: sessionmaker[Session], plant: Plant,
) -> Iterator[Callable[..., WorkerService]]:
    started: list[WorkerService] = []

    def start(*, slots: int, poll_seconds: float = 30.0) -> WorkerService:
        service = WorkerService(
            engine=engine, session_factory=sessions, execute=plant,
            version="exec-par-queue-suite", slots=slots, poll_seconds=poll_seconds,
            heartbeat_seconds=0.5, reclaim_seconds=300.0,
        )
        service.start()
        started.append(service)
        return service

    try:
        yield start
    finally:
        plant.release_all()
        for service in started:
            service.drain(timeout=WAIT_SECONDS)
            service.stop()


def _queue(
    sessions: sessionmaker[Session], plant: Plant, revision: str | None, connection: str | None,
) -> str:
    run_id = support.queue_run(sessions, revision)
    plant.connection_of[run_id] = connection
    return run_id


def test_two_slots_run_different_connections_together_and_one_connection_one_at_a_time(
    sessions: sessionmaker[Session], plant: Plant,
    start_service: Callable[..., WorkerService],
) -> None:
    """Queue order is x1, x2, y1. A slot is never spent waiting for x2: y1 runs beside x1."""
    x, x_revision = support.new_connection(sessions)
    y, y_revision = support.new_connection(sessions)
    x1 = _queue(sessions, plant, x_revision, x)
    x2 = _queue(sessions, plant, x_revision, x)
    y1 = _queue(sessions, plant, y_revision, y)
    runs = (x1, x2, y1)
    try:
        start_service(slots=2)
        _wait_for(lambda: plant.is_live(x1, y1), what="x1 and y1 to run together")
        assert sorted(support.active_runs(sessions, x) + support.active_runs(sessions, y)) == sorted([x1, y1])
        time.sleep(QUIET_SECONDS)
        assert not plant.has_started(x2), "the second run of a busy connection started"
        assert support.job_state(sessions, x2) == "queued" and support.attempts(sessions, x2) == 0

        plant.release(x1)
        _wait_for(lambda: plant.is_live(x2), what="x2 to run once its connection was free")
        assert plant.most_live_on_one_connection == 1
        assert plant.most_live == 2
    finally:
        plant.release_all()
        for run_id in runs:
            _wait_for(lambda: not plant.is_live(run_id), what="the stand-in to finish")
            support.cancel(sessions, run_id)


def test_the_default_single_slot_runs_one_run_at_a_time(
    sessions: sessionmaker[Session], plant: Plant,
    start_service: Callable[..., WorkerService],
) -> None:
    x, x_revision = support.new_connection(sessions)
    y, y_revision = support.new_connection(sessions)
    first = _queue(sessions, plant, x_revision, x)
    second = _queue(sessions, plant, y_revision, y)
    try:
        start_service(slots=1)
        _wait_for(lambda: plant.is_live(first), what="the first run")
        time.sleep(QUIET_SECONDS)
        assert not plant.has_started(second), "one slot ran two runs at once"
        plant.release(first)
        _wait_for(lambda: plant.is_live(second), what="the second run after the first ended")
        assert plant.most_live == 1
    finally:
        plant.release_all()
        for run_id in (first, second):
            _wait_for(lambda: not plant.is_live(run_id), what="the stand-in to finish")
            support.cancel(sessions, run_id)


def test_a_drain_waits_for_every_run_in_flight_and_takes_no_new_one(
    sessions: sessionmaker[Session], plant: Plant,
    start_service: Callable[..., WorkerService],
) -> None:
    x, x_revision = support.new_connection(sessions)
    y, y_revision = support.new_connection(sessions)
    z, z_revision = support.new_connection(sessions)
    first = _queue(sessions, plant, x_revision, x)
    second = _queue(sessions, plant, y_revision, y)
    service = start_service(slots=3, poll_seconds=0.3)
    late = None
    try:
        _wait_for(lambda: plant.is_live(first, second), what="both runs")
        assert service.drain(timeout=0.3) is False, "drain returned with two runs in flight"
        late = _queue(sessions, plant, z_revision, z)   # a free slot and a free connection
        time.sleep(QUIET_SECONDS)                        # several polls: a draining worker takes nothing
        assert not plant.has_started(late)
        assert support.job_state(sessions, late) == "queued"

        plant.release(first)
        _wait_for(lambda: not plant.is_live(first), what="the first run to end")
        assert service.drain(timeout=0.3) is False, "drain returned while one run was still in flight"
        plant.release(second)
        assert service.drain(timeout=WAIT_SECONDS) is True
        assert support.job_state(sessions, first) == support.job_state(sessions, second) == "succeeded"
        assert support.job_state(sessions, late) == "queued" and not plant.has_started(late)
    finally:
        plant.release_all()
        for run_id in (first, second, late):
            if run_id is not None:
                _wait_for(lambda: not plant.is_live(run_id), what="the stand-in to finish")
                support.cancel(sessions, run_id)


def test_a_run_that_keeps_losing_its_claim_does_not_spin_the_dispatch_loop(
    sessions: sessionmaker[Session], plant: Plant,
    start_service: Callable[..., WorkerService],
) -> None:
    """Eight lost claims in a row end the immediate retries; the timed poll (30 s) takes over."""
    run_id = _queue(sessions, plant, None, None)
    plant.refuse_always = True
    try:
        start_service(slots=2, poll_seconds=30.0)
        _wait_for(lambda: len(plant.calls) >= CLAIM_RETRY_LIMIT, what="the retries to be spent")
        time.sleep(QUIET_SECONDS)
        assert len(plant.calls) == CLAIM_RETRY_LIMIT, plant.calls
        assert support.job_state(sessions, run_id) == "queued" and support.attempts(sessions, run_id) == 0
    finally:
        plant.refuse_always = False
        support.cancel(sessions, run_id)
