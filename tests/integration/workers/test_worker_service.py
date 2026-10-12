"""`W54-WORKER-01` (R-105, F-8) -- the worker service against real PostgreSQL and MinIO.

HEAVY: these need the lane's database at migration head ``0019`` and its object store, and
run only in the owner's window. Every claim is made by the shipped code -- ``WorkerService``
over ``jobs``' claim and ``runs``' ``run_to_terminal`` -- with the recorded adapter; nothing
is patched. A "killed" worker is the state a ``SIGKILL`` leaves in the database (a Lease
naming a worker that no longer heartbeats, past its expiry), written through the same
repositories, because a process kill leaves nothing else behind.

``quiet_queue`` parks every Job other suites left in the shared lane database for the
length of each test, and each test's own Jobs carry priority 100, so a worker started here
can only reach the work the test queued (D-152's lesson, applied from the start).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.text import ProviderMode, RecordedAdapter
from auditmanager.bootstrap.adapters import RunAdapter
from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.runs import RunRepository, start_audit_run
from auditmanager.runs.commands import cancel_audit_run
from auditmanager.runs.public import (
    ReclaimingCarrier,
    reconcile_at_startup,
    run_to_terminal,
    start_serving_carrier,
)
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.workers.__main__ import health
from auditmanager.workers.public import WorkerRegistry, WorkerService, set_worker_intake
from auditmanager.workers.service import IDENTITY_FILE

pytestmark = pytest.mark.usefixtures("quiet_queue")

_TERMINALS = {"published", "partial", "failed", "cancelled"}


class GatedAdapter:
    """The recorded adapter with a barrier in front of its one call (see the composition
    suite's twin): ``entered`` is set when a slot reaches the provider, ``release`` is
    waited on until the test sets it."""

    def __init__(self, delegate: RecordedAdapter) -> None:
        self._delegate = delegate
        self.entered = threading.Event()
        self.release = threading.Event()

    @property
    def provider_mode(self) -> ProviderMode:
        return self._delegate.provider_mode

    def complete(self, request: Any) -> Any:
        self.entered.set()
        assert self.release.wait(timeout=90), "the test never released the provider"
        return self._delegate.complete(request)


def _wait_for(predicate: Callable[[], Any], *, timeout: float = 60.0, what: str) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError(f"timed out after {timeout:.0f} s waiting for {what}")


def _queue_run(sessions: sessionmaker[Session], blob_store: Any, helpers: Any) -> str:
    """A committed, queued run with its Job at the top of the dispatcher's order."""
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        started = start_audit_run(
            session,
            version_uid=seeded.version_uid,
            analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id,
            provider_mode="recorded",
            idempotency_key=IdempotencyKey(f"w54-worker-{uuid4().hex}"),
        )
        run_id = str(started.run_id)
        RunRepository().advance(session, run_id=run_id, from_state="created", to_state="queued")
        jobs = JobRepository()
        job_id = jobs.enqueue(session, run_id=run_id)
        jobs.set_priority(session, job_id=job_id, priority=100)
        session.commit()
    return run_id


def _row(sessions: sessionmaker[Session], run_id: str) -> dict[str, Any]:
    with sessions() as session:
        row = session.execute(text(
            "SELECT r.state AS run_state, j.state AS job_state, j.job_id, "
            "(SELECT count(*) FROM attempt a WHERE a.job_id = j.job_id) AS attempts "
            "FROM audit_run r JOIN job j ON j.run_id = r.run_id WHERE r.run_id = :run_id"
        ), {"run_id": run_id}).mappings().one()
        return dict(row)


def _run_state(sessions: sessionmaker[Session], run_id: str) -> str:
    return str(_row(sessions, run_id)["run_state"])


def _leases(sessions: sessionmaker[Session], run_id: str) -> list[dict[str, Any]]:
    with sessions() as session:
        return [dict(row) for row in session.execute(text(
            "SELECT l.worker_id, l.released_at, a.state AS attempt_state "
            "FROM lease l JOIN attempt a ON a.attempt_id = l.attempt_id "
            "JOIN job j ON j.job_id = l.job_id WHERE j.run_id = :run_id "
            "ORDER BY l.acquired_at"
        ), {"run_id": run_id}).mappings().all()]


def _cancel(sessions: sessionmaker[Session], run_id: str) -> None:
    with sessions() as session:
        if RunRepository().get(session, run_id).state in {"created", "queued", "running"}:
            cancel_audit_run(
                session, run_id=run_id, roles=frozenset({"expert"}),
                idempotency_key=f"w54-worker-cleanup-{uuid4().hex}",
            )
            session.commit()


@pytest.fixture
def start_worker(
    engine: Engine, sessions: sessionmaker[Session], blob_store: Any,
    provider_config: Any, tmp_path: Path,
) -> Iterator[Callable[..., WorkerService]]:
    started: list[WorkerService] = []

    def start(
        adapter: Any, *, poll_seconds: float = 0.3, heartbeat_seconds: float = 0.5,
        reclaim_seconds: float = 1.0, state_dir: Path | None = None,
    ) -> WorkerService:
        def execute(run_id: str, worker_id: str) -> None:
            run_to_terminal(
                sessions, run_id, blob_store=blob_store, adapter=adapter,
                provider_config=provider_config, worker_id=worker_id,
            )

        service = WorkerService(
            engine=engine, session_factory=sessions, execute=execute,
            version="w54-worker-suite", poll_seconds=poll_seconds,
            heartbeat_seconds=heartbeat_seconds, reclaim_seconds=reclaim_seconds,
            state_dir=state_dir,
        )
        service.start()
        started.append(service)
        return service

    try:
        yield start
    finally:
        for service in started:
            service.drain(timeout=30)
            service.stop()


# --- only the worker claims -----------------------------------------------------------------


def test_the_api_role_claims_nothing_and_the_worker_runs_it(
    sessions, blob_store, helpers, recorded_adapter, provider_config, start_worker,
) -> None:
    """`EXECUTION_ROLE=api`: the API's own path accepts and queues; only the worker claims."""
    carrier = ReclaimingCarrier(sessions)
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        session.commit()
    api_runs = RunAdapter(
        sessions, blob_store=blob_store, adapter=recorded_adapter,
        provider_config=provider_config, provider_mode="recorded",
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, carrier=carrier,
    )
    start_serving_carrier(carrier)
    try:
        view = api_runs.start_run(
            version_uid=seeded.version_uid,
            idempotency_key=f"w54-api-role-{uuid4().hex}",
        )
        run_id = str(view.run_id)
        assert view.state == "queued"
        with sessions() as session:
            JobRepository().set_priority(
                session, job_id=_row(sessions, run_id)["job_id"], priority=100,
            )
            session.commit()
        # The API process is serving (its reclaim thread is running) and the run is
        # durable work; nothing in this process may claim it.
        time.sleep(2.0)
        assert _row(sessions, run_id) | {"job_id": None} == {
            "run_state": "queued", "job_state": "queued", "job_id": None, "attempts": 0,
        }

        worker = start_worker(recorded_adapter)
        _wait_for(lambda: _run_state(sessions, run_id) in _TERMINALS, what="the worker's run")
        assert _run_state(sessions, run_id) == "published"
        leases = _leases(sessions, run_id)
        assert [lease["worker_id"] for lease in leases] == [worker.worker_id]
    finally:
        carrier.shutdown()


def test_a_notification_wakes_the_worker_before_its_poll(
    sessions, blob_store, helpers, recorded_adapter, start_worker,
) -> None:
    """The poll is 120 s; the run is claimed within seconds, so the `NOTIFY` of the
    accepting commit is what woke the worker."""
    worker = start_worker(recorded_adapter, poll_seconds=120.0, reclaim_seconds=120.0)
    _wait_for(lambda: worker.wakeup.listening, timeout=15, what="the LISTEN connection")
    time.sleep(0.5)  # past the loop's first, immediate poll
    run_id = _queue_run(sessions, blob_store, helpers)
    _wait_for(lambda: _run_state(sessions, run_id) in _TERMINALS, timeout=45,
              what="a run claimed on notification")
    assert _run_state(sessions, run_id) == "published"


# --- lost LISTEN is logged, and the poll carries on ----------------------------------------


def test_a_lost_listen_is_logged_and_the_poll_still_claims(
    sessions, blob_store, helpers, recorded_adapter, start_worker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="auditmanager.workers.service")
    worker = start_worker(recorded_adapter, poll_seconds=0.5)
    pid = _wait_for(lambda: worker.wakeup.backend_pid, timeout=15, what="the LISTEN backend")
    with sessions() as session:
        assert session.execute(
            text("SELECT pg_terminate_backend(:pid)"), {"pid": pid}
        ).scalar_one() is True
    _wait_for(
        lambda: any("was lost" in r.getMessage() for r in caplog.records),
        timeout=15, what="the lost-LISTEN warning",
    )
    lost = [r for r in caplog.records if "was lost" in r.getMessage()]
    assert lost[0].levelno == logging.WARNING
    assert "0.5 s poll" in lost[0].getMessage(), lost[0].getMessage()

    run_id = _queue_run(sessions, blob_store, helpers)
    _wait_for(lambda: _run_state(sessions, run_id) in _TERMINALS, what="a run after the loss")
    assert _run_state(sessions, run_id) == "published"
    _wait_for(
        lambda: any("re-established" in r.getMessage() for r in caplog.records),
        timeout=15, what="the LISTEN to come back",
    )


# --- drain and intake -------------------------------------------------------------------------


def test_drain_finishes_the_run_in_flight_and_claims_no_more(
    sessions, blob_store, helpers, recorded_adapter, start_worker,
) -> None:
    gated = GatedAdapter(recorded_adapter)
    worker = start_worker(gated)
    first = _queue_run(sessions, blob_store, helpers)
    assert gated.entered.wait(timeout=60), "the worker never reached the provider"
    second = _queue_run(sessions, blob_store, helpers)
    try:
        assert worker.drain(timeout=0.2) is False, "drain returned with a run in flight"
        gated.release.set()
        assert worker.drain(timeout=90) is True
        assert _run_state(sessions, first) == "published"
        time.sleep(1.5)  # several polls: a draining worker must take nothing
        assert _row(sessions, second)["attempts"] == 0
        assert _run_state(sessions, second) == "queued"
    finally:
        gated.release.set()
        _cancel(sessions, second)


def test_intake_off_leaves_new_runs_queued_and_on_resumes(
    sessions, blob_store, helpers, recorded_adapter, start_worker,
) -> None:
    worker = start_worker(recorded_adapter)

    def switch(enabled: bool) -> None:
        with sessions() as session:
            record = set_worker_intake(
                session, worker_id=worker.worker_id, enabled=enabled,
                roles=frozenset({"admin"}), idempotency_key=f"w54-intake-{uuid4().hex}",
                actor_uid="usr_01M2545JSD15ETSNNV904X991K",
            )
            session.commit()
        assert record.intake_enabled is enabled

    switch(False)
    run_id = _queue_run(sessions, blob_store, helpers)
    try:
        time.sleep(2.0)
        assert _row(sessions, run_id)["attempts"] == 0
        switch(True)
        _wait_for(lambda: _run_state(sessions, run_id) in _TERMINALS, what="the resumed intake")
        assert _run_state(sessions, run_id) == "published"
    finally:
        _cancel(sessions, run_id)


# --- the API and a second worker reclaim; a live worker is left alone -----------------------


def test_an_api_restart_leaves_the_workers_run_alone(
    sessions, blob_store, helpers, recorded_adapter, start_worker,
) -> None:
    gated = GatedAdapter(recorded_adapter)
    worker = start_worker(gated)
    run_id = _queue_run(sessions, blob_store, helpers)
    try:
        assert gated.entered.wait(timeout=60)
        # What an API process does when it (re)starts under EXECUTION_ROLE=api: the
        # startup reconciliation, then its reclaim-only carrier.
        reconcile_at_startup(sessions)
        carrier = ReclaimingCarrier(sessions)
        start_serving_carrier(carrier)
        time.sleep(1.0)
        carrier.shutdown()
        row = _row(sessions, run_id)
        assert (row["run_state"], row["job_state"], row["attempts"]) == ("running", "running", 1)
        assert _leases(sessions, run_id) == [{
            "worker_id": worker.worker_id, "released_at": None, "attempt_state": "running",
        }]
        gated.release.set()
        _wait_for(lambda: _run_state(sessions, run_id) in _TERMINALS, what="the worker's run")
        assert _run_state(sessions, run_id) == "published"
    finally:
        gated.release.set()


def _killed_worker_holding(sessions: sessionmaker[Session], run_id: str) -> str:
    """The database a SIGKILLed worker leaves: its claim, and a lease past its expiry."""
    with sessions() as session:
        dead = WorkerRegistry().register(session, version="killed", slots=1)
        session.commit()
    with sessions() as session:
        RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
        authority = JobRepository(worker_id=dead).start_execution(session, run_id=run_id)
        session.execute(text(
            "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
            "WHERE lease_id = :lease_id"
        ), {"lease_id": authority.lease_id})
        session.commit()
    return dead


def test_the_api_reclaims_a_killed_workers_lease(
    sessions, blob_store, helpers,
) -> None:
    run_id = _queue_run(sessions, blob_store, helpers)
    dead = _killed_worker_holding(sessions, run_id)
    carrier = ReclaimingCarrier(sessions)
    start_serving_carrier(carrier)
    try:
        _wait_for(lambda: _row(sessions, run_id)["job_state"] == "queued",
                  timeout=20, what="the API's reclaim")
        assert _leases(sessions, run_id)[0]["worker_id"] == dead
        assert _leases(sessions, run_id)[0]["attempt_state"] == "lost"
        assert _leases(sessions, run_id)[0]["released_at"] is not None
    finally:
        carrier.shutdown()
        _cancel(sessions, run_id)


def test_a_killed_workers_run_is_reclaimed_and_finished_by_another_worker(
    sessions, blob_store, helpers, recorded_adapter, start_worker,
) -> None:
    run_id = _queue_run(sessions, blob_store, helpers)
    dead = _killed_worker_holding(sessions, run_id)
    worker = start_worker(recorded_adapter)
    _wait_for(lambda: _run_state(sessions, run_id) in _TERMINALS, what="the reclaimed run")
    assert _run_state(sessions, run_id) == "published"
    leases = _leases(sessions, run_id)
    assert [(lease["worker_id"], lease["attempt_state"]) for lease in leases] == [
        (dead, "lost"), (worker.worker_id, "succeeded"),
    ]


def test_a_claim_for_a_worker_whose_intake_is_off_is_refused_and_leaves_the_run(
    sessions, blob_store, helpers,
) -> None:
    run_id = _queue_run(sessions, blob_store, helpers)
    with sessions() as session:
        worker_id = WorkerRegistry().register(session, version="intake-off", slots=1)
        WorkerRegistry().set_intake(session, worker_id=worker_id, enabled=False)
        session.commit()
    try:
        with sessions() as session:
            with pytest.raises(ExecutionNotClaimed):
                JobRepository(worker_id=worker_id).start_execution(session, run_id=run_id)
            session.rollback()
        assert _row(sessions, run_id) | {"job_id": None} == {
            "run_state": "queued", "job_state": "queued", "job_id": None, "attempts": 0,
        }
    finally:
        _cancel(sessions, run_id)


# --- the registry side of a worker ----------------------------------------------------------


def test_the_worker_registers_heartbeats_and_reports_itself_healthy(
    sessions, recorded_adapter, start_worker, tmp_path: Path,
) -> None:
    worker = start_worker(recorded_adapter, heartbeat_seconds=0.3, state_dir=tmp_path)
    assert (tmp_path / IDENTITY_FILE).read_text().strip() == worker.worker_id
    with sessions() as session:
        first = WorkerRegistry().get(session, worker.worker_id)
    assert first is not None and first.state == "online" and first.slots == 1
    _wait_for(
        lambda: _heartbeat_of(sessions, worker.worker_id) > first.heartbeat_at,
        timeout=10, what="a registry heartbeat",
    )
    assert health({"AUDITMANAGER_WORKER_STATE_DIR": str(tmp_path)}) == 0


def _heartbeat_of(sessions: sessionmaker[Session], worker_id: str) -> Any:
    with sessions() as session:
        record = WorkerRegistry().get(session, worker_id)
    assert record is not None
    return record.heartbeat_at


def test_a_worker_whose_registry_row_vanished_stops_claiming_and_fails(
    sessions, recorded_adapter, start_worker,
) -> None:
    """The schema was reset under a running worker: it must exit and come back as a new
    identity rather than claim under one the registry no longer knows."""
    worker = start_worker(recorded_adapter, heartbeat_seconds=0.3)
    with sessions() as session:
        session.execute(text("DELETE FROM worker WHERE worker_id = :worker_id"),
                        {"worker_id": worker.worker_id})
        session.commit()
    _wait_for(lambda: worker.failed, timeout=10, what="the worker to notice")
    assert worker.drain(timeout=5) is True
