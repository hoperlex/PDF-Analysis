"""`W54-WORKER-01` in the jobs boundary: D-150, the worker on the Lease, the wake-up.

HEAVY: real PostgreSQL (and MinIO for the seeded version). The first group runs inside
one rolled-back transaction, as the W53 queue suites do; the wake-up group commits,
because a ``NOTIFY`` is delivered only by a commit.

D-150 (decided at `W54-FREEZE-01`): a recorded call spends nothing, so lease reclaim
settles a recorded effect left ``prepared`` as ``not_processed`` and no recorded effect
blocks the resume. A live effect that may have been sent still fails the run -- that
inverse is asserted here too, so a change that stopped looking at the mode would redden.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.jobs.public import JOB_WAKEUP_CHANNEL, JobRepository
from auditmanager.runs.commands import cancel_audit_run
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.identity import RunId
from auditmanager.workers.public import WorkerRegistry


def _queued_run(session, seeded, *, mode: str) -> str:
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode=mode, frozen_input_digest="a" * 64, command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    JobRepository().enqueue(session, run_id=run_id)
    return run_id


def _claim(session, run_id: str, jobs: JobRepository):
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
    return jobs.start_execution(session, run_id=run_id)


def _expire_and_reclaim(session, authority) -> None:
    session.execute(text(
        "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
        "WHERE lease_id = :lease_id"
    ), {"lease_id": authority.lease_id})
    assert JobRepository().reclaim_expired(session) >= 1


def _states(session, run_id: str) -> tuple[str, str]:
    return tuple(session.execute(text(
        "SELECT r.state, j.state FROM audit_run r JOIN job j ON j.run_id = r.run_id "
        "WHERE r.run_id = :run_id"
    ), {"run_id": run_id}).one())


def _prepare(session, jobs: JobRepository, authority, *, mode: str, digest: str):
    return jobs.prepare_provider_call(
        session, authority, provider="anthropic", model_identity="claude-opus-5",
        provider_mode=mode, parameters={}, request_sha256=digest * 64,
    )


# --- D-150 ----------------------------------------------------------------------------------


def test_a_recorded_prepared_effect_is_settled_not_processed_and_the_run_resumes(
    session, blob_store, helpers,
) -> None:
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded, mode="recorded")
    jobs = JobRepository()
    authority = _claim(session, run_id, jobs)
    effect = _prepare(session, jobs, authority, mode="recorded", digest="1")
    _expire_and_reclaim(session, authority)

    state, dispatch_class = session.execute(text(
        "SELECT state, dispatch_class FROM provider_call_effect WHERE model_call_id = :id"
    ), {"id": str(effect)}).one()
    assert (state, dispatch_class) == ("not_processed", "not_sent")
    assert _states(session, run_id) == ("running", "queued"), (
        "a recorded run was failed as if its replay might have been paid"
    )
    assert session.execute(text(
        "SELECT count(*) FROM audit_event WHERE event_type = 'provider.not_processed' "
        "AND aggregate_id = :attempt_id AND payload->>'dispatch_class' = 'not_sent'"
    ), {"attempt_id": authority.attempt_id}).scalar_one() == 1


def test_a_completed_recorded_effect_does_not_block_the_resume(
    session, blob_store, helpers,
) -> None:
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded, mode="recorded")
    jobs = JobRepository()
    authority = _claim(session, run_id, jobs)
    effect = _prepare(session, jobs, authority, mode="recorded", digest="2")
    jobs.record_provider_response(
        session, authority, model_call_id=effect, response_sha256="3" * 64,
        input_tokens=10, output_tokens=20, latency_ms=30,
    )
    jobs.complete_provider_call(session, authority, call={
        "model_call_id": str(effect), "provider": "anthropic", "model_id": "claude-opus-5",
        "provider_mode": "recorded", "parameters": {}, "request_sha256": "2" * 64,
        "response_sha256": "3" * 64, "input_tokens": 10, "output_tokens": 20,
        "latency_ms": 30, "cost_usd": 0.0, "cost_basis": "estimated",
        "status": "succeeded",
    })
    _expire_and_reclaim(session, authority)

    assert session.execute(text(
        "SELECT state FROM provider_call_effect WHERE model_call_id = :id"
    ), {"id": str(effect)}).scalar_one() == "completed"
    assert _states(session, run_id) == ("running", "queued")


def test_a_live_prepared_effect_still_fails_the_run(session, blob_store, helpers) -> None:
    """The inverse of D-150: a live call may have been sent and paid for."""
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded, mode="live")
    jobs = JobRepository()
    authority = _claim(session, run_id, jobs)
    effect = _prepare(session, jobs, authority, mode="live", digest="4")
    _expire_and_reclaim(session, authority)

    assert session.execute(text(
        "SELECT state FROM provider_call_effect WHERE model_call_id = :id"
    ), {"id": str(effect)}).scalar_one() == "outcome_unknown"
    assert _states(session, run_id) == ("failed", "failed")


# --- the worker on the Lease -------------------------------------------------------------------


def test_a_workers_claim_records_it_on_the_lease_and_in_its_held_runs(
    session, blob_store, helpers,
) -> None:
    seeded = helpers.seed_version(session, blob_store)
    registry = WorkerRegistry()
    worker_id = registry.register(session, version="jobs-suite", slots=1)
    own = _queued_run(session, seeded, mode="recorded")
    in_process = _queued_run(session, seeded, mode="recorded")

    authority = _claim(session, own, JobRepository(worker_id=worker_id))
    _claim(session, in_process, JobRepository())

    leases = dict(session.execute(text(
        "SELECT j.run_id, l.worker_id FROM lease l JOIN job j ON j.job_id = l.job_id "
        "WHERE j.run_id = ANY(:runs)"
    ), {"runs": [own, in_process]}).all())
    assert leases == {own: worker_id, in_process: None}
    assert JobRepository().runs_held_by(session, [worker_id]) == {worker_id: (own,)}

    JobRepository(worker_id=worker_id).finish_execution(
        session, authority, publishes_result=False,
    )
    assert JobRepository().runs_held_by(session, [worker_id]) == {worker_id: ()}


def test_an_unregistered_worker_cannot_claim(session, blob_store, helpers) -> None:
    from auditmanager.jobs.public import ExecutionNotClaimed

    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded, mode="recorded")
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
    with pytest.raises(ExecutionNotClaimed, match="not registered"):
        JobRepository(worker_id="wrk_01M2545JSD15ETSNNV904X991K").start_execution(
            session, run_id=run_id,
        )


# --- the wake-up ---------------------------------------------------------------------------


@pytest.fixture
def listener(engine):
    pooled = engine.raw_connection()
    pooled.detach()
    connection = pooled.driver_connection
    connection.rollback()
    connection.autocommit = True
    connection.execute(f"LISTEN {JOB_WAKEUP_CHANNEL}")
    try:
        yield connection
    finally:
        connection.close()


def _notified(connection, timeout: float) -> bool:
    return bool(list(connection.notifies(timeout=timeout, stop_after=1)))


def test_enqueue_wakes_the_workers_only_when_it_commits(
    sessions, blob_store, helpers, listener,
) -> None:
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        session.commit()
    with sessions() as session:
        _queued_run(session, seeded, mode="recorded")
        session.rollback()
    assert not _notified(listener, 0.5), "a rolled-back enqueue woke a worker"

    with sessions() as session:
        run_id = _queued_run(session, seeded, mode="recorded")
        session.commit()
    try:
        assert _notified(listener, 5.0), "a committed enqueue woke no worker"
    finally:
        with sessions() as cleanup:
            cancel_audit_run(
                cleanup, run_id=run_id, roles=frozenset({"expert"}),
                idempotency_key=f"w54-wakeup-cleanup-{uuid4().hex}",
            )
            cleanup.commit()


def test_unpausing_dispatch_wakes_the_workers(sessions, listener) -> None:
    with sessions() as session:
        paused = session.execute(text(
            "SELECT paused FROM execution_control WHERE singleton"
        )).scalar_one_or_none()
    try:
        with sessions() as session:
            JobRepository().set_paused(session, paused=True)
            session.commit()
        assert not _notified(listener, 0.3), "pausing woke a worker"
        with sessions() as session:
            JobRepository().set_paused(session, paused=False)
            session.commit()
        assert _notified(listener, 5.0), "unpausing woke no worker"
    finally:
        with sessions() as session:
            JobRepository().set_paused(session, paused=bool(paused))
            session.commit()
