"""A worker whose slot thread hangs after its authority was revoked exits, so a fresh one starts (`R-155c`).

The fence of an Attempt (the silence watchdog, ``cancelRun``, a reclaim by another process) revokes its authority, not its thread;
a slot is a thread, and ``AUDITMANAGER_WORKER_SLOTS`` defaults to 1, so one hung thread blocked every run behind it for ever. The
rule: the heartbeat of a revoked Attempt waits ``ATTEMPT_RETURN_GRACE_SECONDS`` for its work thread to return, and if it has not,
tells the worker service (``jobs.public.install_slot_recovery``), which stops claiming, marks itself failed and stops waiting for
that run; ``workers.__main__.run_until_stopped`` then drains the other slots for the usual bounded time and the process exits
non-zero. The container's restart policy (``restart: unless-stopped``, ``infra/deploy/compose.server.yml`` ``worker:``) starts a fresh
worker; state is durable and the leases are reclaimed.

No database and no container: a recorder stands in for the job repository, the service runs over the stubs of
``tests/unit/shared/test_tempsweep.py``, and the constants are tiny. The exit is the return value of ``run_until_stopped`` -- the
process's ``os._exit`` is the one line of ``main`` that is not tested.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any, cast

import pytest

from auditmanager.jobs import lease as lease_module
from auditmanager.jobs.lease import (
    LeaseHeartbeat,
    RevokedAttempt,
    current_slot_recovery,
    install_slot_recovery,
)
from auditmanager.workers import service as service_module
from auditmanager.workers.__main__ import run_until_stopped
from auditmanager.workers.service import WorkerService
from tests.unit.shared.test_tempsweep import _Jobs, _QuietWakeup, _Registry, _Session


@pytest.fixture
def make_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., WorkerService]]:
    monkeypatch.setattr(service_module, "JobRepository", _Jobs)
    made: list[WorkerService] = []
    before = current_slot_recovery()

    def make(**options: Any) -> WorkerService:
        service = WorkerService(
            engine=cast(Any, None), session_factory=cast(Any, _Session),
            execute=lambda _run, _worker: None, version="unit", registry=cast(Any, _Registry()),
            heartbeat_seconds=3600.0, temporaries_sweep_seconds=3600.0, **options,
        )
        service.wakeup = cast(Any, _QuietWakeup())
        made.append(service)
        return service

    try:
        yield make
    finally:
        for service in made:
            service.stop()
        install_slot_recovery(before)


def _hold_a_slot(service: WorkerService, run_id: str, *, release: threading.Event) -> threading.Event:
    """Put a run in a slot of ``service`` whose thread stays until ``release``; returns the event set once it runs."""
    running = threading.Event()

    def execute(_run: str, _worker: str) -> None:
        running.set()
        release.wait(timeout=60)

    service._execute = execute  # type: ignore[attr-defined]
    service._worker_id = "wrk_unit"  # type: ignore[attr-defined]  # registered, as `start` would
    future = service._pool.submit(service._run_one, run_id)  # type: ignore[attr-defined]
    with service._lock:  # type: ignore[attr-defined]
        service._in_flight[future] = run_id  # type: ignore[attr-defined]
    future.add_done_callback(service._finished)  # type: ignore[attr-defined]
    assert running.wait(timeout=10)
    return running


NOTICE = RevokedAttempt(run_id="run_hung", attempt_id="att_hung", reason="fenced:stalled", grace_seconds=120.0)


def test_a_started_service_installs_its_recovery_and_a_stopped_one_removes_it(
    make_service: Callable[..., WorkerService],
) -> None:
    install_slot_recovery(None)
    service = make_service()
    service.start()
    assert current_slot_recovery() == service._slot_lost  # type: ignore[attr-defined]
    service.stop()
    assert current_slot_recovery() is None
    other = lambda _notice: None  # noqa: E731
    install_slot_recovery(other)  # another owner's hook is not removed by a service that is not its owner
    service.stop()
    assert current_slot_recovery() is other


def test_a_lost_slot_stops_claiming_marks_the_worker_failed_and_is_logged_with_its_reason(
    make_service: Callable[..., WorkerService], caplog: pytest.LogCaptureFixture,
) -> None:
    service = make_service()
    service._worker_id = "wrk_unit"  # type: ignore[attr-defined]
    assert not service.failed
    with caplog.at_level(logging.ERROR, logger="auditmanager.workers.service"):
        service._slot_lost(NOTICE)  # type: ignore[attr-defined]
    assert service.failed and service._draining.is_set()  # type: ignore[attr-defined]
    (record,) = [r for r in caplog.records if "slot" in r.getMessage()]
    message = record.getMessage()
    assert record.levelno == logging.ERROR
    assert "run_hung" in message and "att_hung" in message and "fenced:stalled" in message and "wrk_unit" in message
    assert "restart" in message, "the reason says what happens next"


def test_a_drain_does_not_wait_for_a_run_whose_slot_was_lost_but_does_for_another(
    make_service: Callable[..., WorkerService],
) -> None:
    service = make_service(slots=2)
    hung, healthy = threading.Event(), threading.Event()
    _hold_a_slot(service, "run_hung", release=hung)
    _hold_a_slot(service, "run_ok", release=healthy)
    assert service.busy == 2

    service._slot_lost(NOTICE)  # type: ignore[attr-defined]
    assert service.busy == 2, "the thread does hold its slot"
    assert service.drain(timeout=0.3) is False, "the healthy run is still waited for"

    healthy.set()
    assert service.drain(timeout=10) is True, "and once it ends, the hung one is not"
    assert service.busy == 1
    hung.set()


def test_a_worker_whose_only_slot_hangs_exits_at_once_with_a_failure_code(
    make_service: Callable[..., WorkerService],
) -> None:
    service = make_service()
    release = threading.Event()
    _hold_a_slot(service, "run_hung", release=release)
    stop = threading.Event()

    outcome: list[int] = []
    waiter = threading.Thread(target=lambda: outcome.append(run_until_stopped(
        service, stop, drain_seconds=30.0, poll_seconds=0.02)))
    waiter.start()
    time.sleep(0.2)
    assert waiter.is_alive() and not outcome, "healthy: it runs until it is stopped"

    began = time.monotonic()
    service._slot_lost(NOTICE)  # type: ignore[attr-defined]
    waiter.join(timeout=10)
    try:
        assert not waiter.is_alive(), "the worker did not exit"
        assert outcome == [1], "a non-zero code, for the restart policy"
        assert time.monotonic() - began < 5, "it did not wait out the 30 s drain for a thread that is not coming back"
        assert service._stopped.is_set(), "the service was stopped"  # type: ignore[attr-defined]
    finally:
        release.set()
        stop.set()


def test_the_exit_code_is_zero_for_a_drained_service_that_did_not_fail(
    make_service: Callable[..., WorkerService],
) -> None:
    service = make_service()
    service._worker_id = "wrk_unit"  # type: ignore[attr-defined]
    stop = threading.Event()
    stop.set()
    assert run_until_stopped(service, stop, drain_seconds=1.0, poll_seconds=0.01) == 0


def test_a_run_still_in_flight_after_the_drain_makes_the_code_non_zero(
    make_service: Callable[..., WorkerService],
) -> None:
    service = make_service()
    release = threading.Event()
    _hold_a_slot(service, "run_slow", release=release)
    stop = threading.Event()
    stop.set()
    try:
        assert run_until_stopped(service, stop, drain_seconds=0.2, poll_seconds=0.01) == 1
    finally:
        release.set()


# --- the whole chain: a hung work thread, a fenced Attempt, a heartbeat, the service, the exit -------------------------


class _Repository:
    """The recorder the heartbeat thread calls in place of the job repository."""

    def __init__(self) -> None:
        self.reclaims: list[tuple[str | None, str | None]] = []

    def __call__(self) -> _Repository:
        return self

    def heartbeat(self, _session: object, _authority: object) -> bool:
        return True

    def attempt_state(self, _session: object, _attempt_id: str) -> str | None:
        return "lost"

    def reclaim_expired(self, _session: object, *, force_attempt_id: str | None = None,
                        fail_reason: str | None = None) -> None:
        self.reclaims.append((force_attempt_id, fail_reason))


def test_a_hung_slot_thread_after_a_stall_fence_ends_the_worker_process(
    make_service: Callable[..., WorkerService], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The chain of the production incident: a work thread that stops showing life and never returns. The heartbeat fences the
    Attempt (the run fails as ``attempt_stalled``), waits the grace for the thread, tells the service, and the worker exits."""
    repository = _Repository()
    monkeypatch.setattr(lease_module, "JobRepository", repository)
    monkeypatch.setattr(lease_module, "HEARTBEAT_SECONDS", 0.01)
    monkeypatch.setattr(lease_module, "ATTEMPT_LOCAL_SILENCE_SECONDS", 0.2)
    monkeypatch.setattr(lease_module, "ATTEMPT_RETURN_GRACE_SECONDS", 0.3)

    release = threading.Event()
    heartbeats: list[LeaseHeartbeat] = []
    in_work = threading.Event()

    def hung_work(run_id: str, _worker: str) -> None:
        heartbeat = LeaseHeartbeat(object(), SimpleNamespace(run_id=run_id, attempt_id="att_hung"))  # type: ignore[arg-type]
        heartbeats.append(heartbeat)
        heartbeat.start()
        heartbeat.context.progress()  # live, and then silent for good
        in_work.set()
        release.wait(timeout=60)  # hung: never returns, never stops the heartbeat
        heartbeat.stop()

    service = make_service()
    service.start()  # registers, installs the recovery
    service._execute = hung_work  # type: ignore[attr-defined]
    future = service._pool.submit(service._run_one, "run_hung")  # type: ignore[attr-defined]
    with service._lock:  # type: ignore[attr-defined]
        service._in_flight[future] = "run_hung"  # type: ignore[attr-defined]
    future.add_done_callback(service._finished)  # type: ignore[attr-defined]
    assert in_work.wait(timeout=10)

    stop = threading.Event()
    began = time.monotonic()
    try:
        code = run_until_stopped(service, stop, drain_seconds=30.0, poll_seconds=0.02)
        still_hung = not future.done()
    finally:
        release.set()
    assert code == 1
    assert still_hung, "the worker left while the thread was still stuck in its slot"
    assert time.monotonic() - began < 10
    assert repository.reclaims == [("att_hung", "attempt_stalled")], "the run was failed, not re-queued"
