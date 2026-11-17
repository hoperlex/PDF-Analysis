"""A stalled Attempt fails its Run, once, and is not re-queued (`R-155c`, RUN-RESTART-01 lane L2).

Production run ``run_01M7MAMZTTDEQTT8VWNG63J7BB`` ended ``partial`` when the Attempt's two-hour ceiling closed while its critic was
working. With no ceiling, what ends an Attempt that has stopped is a silence: the heartbeat of a **live** Attempt that shows no sign of
life for 30 minutes outside a model call (or whose call outlives its own window by a grace) fences it -- and the fence must **end the
Run**, because the ordinary forced reclaim re-queues a lost Attempt unless a provider effect is ambiguous or its budget is spent, and
resuming a worker that hung would only hang again.

HEAVY: real PostgreSQL (and MinIO for the seeded version), the way ``test_repeated_kill_names_the_stage`` is. The repository cases run
inside the harness's rolled-back transaction. The heartbeat cases commit, because the heartbeat thread (the code under test) opens
connections of its own: the real ``LeaseHeartbeat`` runs on tiny constants against the real tables and fences, or leaves alone, a real
Attempt.
"""

from __future__ import annotations

import threading
import time

import pytest
from sqlalchemy import text

import auditmanager.jobs.lease as lease_module
from auditmanager.jobs.lease import LeaseHeartbeat, RevokedAttempt, current_slot_recovery, install_slot_recovery
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import ErrorCode, screen_details
from auditmanager.shared.identity import RunId

STAGE = "page_geometry_extraction"


def _queued_run(session, seeded) -> str:
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    JobRepository().enqueue(session, run_id=run_id)
    return run_id


def _claim(session, run_id: str, stage_id: str | None = STAGE):
    """Claim the run and start ``stage_id`` as the executor does; the Attempt is live in the caller's eyes."""
    runs = RunRepository()
    if runs.get(session, run_id).state == "queued":
        runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    authority = JobRepository().start_execution(session, run_id=run_id)
    if stage_id is not None:
        runs.stage_started(session, run_id=run_id, stage_id=stage_id)
    return authority


def _row(session, run_id: str):
    return session.execute(text(
        "SELECT r.state, r.terminal_reason, r.terminal_detail, r.interrupted_reason, j.state AS job_state "
        "FROM audit_run r JOIN job j ON j.run_id = r.run_id WHERE r.run_id = :run_id"
    ), {"run_id": run_id}).one()


def _attempt_and_lease(session, attempt_id: str):
    return session.execute(text(
        "SELECT a.state, l.released_at IS NOT NULL AS released FROM attempt a JOIN lease l ON l.attempt_id = a.attempt_id "
        "WHERE a.attempt_id = :attempt_id"
    ), {"attempt_id": attempt_id}).one()


def _jobs_of(session, run_id: str) -> list[str]:
    return [str(state) for (state,) in session.execute(text(
        "SELECT state FROM job WHERE run_id = :run_id ORDER BY created_at"), {"run_id": run_id})]


# --- the repository: a forced reclaim that says the Attempt stalled -------------------------------------------------------


def test_the_plain_forced_reclaim_requeues_a_lost_attempt_as_it_always_did(session, blob_store, helpers):
    """The control: what the stall must NOT be. A fenced Attempt with no ambiguous effect and budget left is resumed."""
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    authority = _claim(session, run_id)
    assert JobRepository().reclaim_expired(session, force_attempt_id=authority.attempt_id) == 1
    row = _row(session, run_id)
    assert (row.state, row.job_state) == ("running", "queued")
    assert row.interrupted_reason is None


def test_a_stalled_attempt_fails_the_run_instead_of_requeueing_it(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    authority = _claim(session, run_id)

    assert JobRepository().reclaim_expired(
        session, force_attempt_id=authority.attempt_id, fail_reason="attempt_stalled",
    ) == 1

    row = _row(session, run_id)
    assert (row.state, row.terminal_reason, row.interrupted_reason) == ("failed", "analysis_failed", "attempt_stalled")
    assert row.job_state == "failed", "the Job ends; it is not queued, and not dead-lettered as an exhausted budget"
    assert _jobs_of(session, run_id) == ["failed"], "nothing was queued"
    assert tuple(_attempt_and_lease(session, authority.attempt_id)) == ("lost", True)
    assert row.terminal_detail == {"stage_id": STAGE}, "the stage the worker stopped in is named"
    assert screen_details(ErrorCode.ANALYSIS_FAILED, row.terminal_detail) == row.terminal_detail
    # No later pass takes the run back: another sweep finds nothing to recover.
    assert JobRepository().reclaim_expired(session) == 0
    assert _row(session, run_id).state == "failed"


def test_a_stall_before_any_stage_names_none(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    authority = _claim(session, run_id, stage_id=None)
    JobRepository().reclaim_expired(session, force_attempt_id=authority.attempt_id, fail_reason="attempt_stalled")
    row = _row(session, run_id)
    assert (row.state, row.interrupted_reason, row.terminal_detail) == ("failed", "attempt_stalled", None)


def test_a_stall_after_an_earlier_loss_fails_the_run_on_the_first_stall_not_the_third(session, blob_store, helpers):
    """A run that was already resumed once is still failed by a stall: the stall is not counted against a budget."""
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    first = _claim(session, run_id, stage_id="source_preparation")
    assert JobRepository().reclaim_expired(session, force_attempt_id=first.attempt_id) == 1
    assert _row(session, run_id).job_state == "queued"
    second = _claim(session, run_id, stage_id=STAGE)
    JobRepository().reclaim_expired(session, force_attempt_id=second.attempt_id, fail_reason="attempt_stalled")
    row = _row(session, run_id)
    assert (row.state, row.interrupted_reason, row.job_state) == ("failed", "attempt_stalled", "failed")
    assert row.terminal_detail == {"stage_id": STAGE}, "the stalled Attempt's stage, not the earlier one's"


def test_a_stall_inside_a_live_call_is_still_a_stall_and_the_effect_is_settled_unknown(session, blob_store, helpers):
    """The call-overran fence: a live provider call was prepared and never completed. The effect is outcome-unknown as for any lost
    Attempt, and the run's reason is the stall, not ``provider_outcome_unknown``."""
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    authority = _claim(session, run_id, stage_id="text_analysis")
    JobRepository().prepare_provider_call(
        session, authority, provider="anthropic", model_identity="claude-opus-5",
        provider_mode="live", parameters={}, request_sha256="d" * 64,
    )
    JobRepository().reclaim_expired(session, force_attempt_id=authority.attempt_id, fail_reason="attempt_stalled")
    row = _row(session, run_id)
    assert (row.state, row.interrupted_reason, row.job_state) == ("failed", "attempt_stalled", "failed")
    effect = session.execute(text(
        "SELECT state FROM provider_call_effect WHERE attempt_id = :attempt_id"), {"attempt_id": authority.attempt_id},
    ).scalar_one()
    assert effect == "outcome_unknown"


def test_a_stall_verdict_after_the_attempt_finished_itself_changes_nothing(session, blob_store, helpers):
    """Post-terminal work of the thread that signals nothing: the lease is released and the Attempt ``succeeded``, so the forced
    reclaim has nothing to fence and the heartbeat reads ``succeeded`` -- not a revocation."""
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    authority = _claim(session, run_id)
    JobRepository().finish_execution(session, authority, publishes_result=True)
    assert JobRepository().reclaim_expired(
        session, force_attempt_id=authority.attempt_id, fail_reason="attempt_stalled",
    ) == 0
    row = _row(session, run_id)
    assert (row.state, row.interrupted_reason, row.job_state) == ("running", None, "succeeded")
    assert JobRepository.attempt_state(session, authority.attempt_id) == "succeeded"


def test_a_reason_without_an_attempt_is_refused(session):
    with pytest.raises(ValueError):
        JobRepository().reclaim_expired(session, fail_reason="attempt_stalled")


def test_the_state_of_an_attempt_is_readable_for_the_heartbeat(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    authority = _claim(session, run_id)
    assert JobRepository.attempt_state(session, authority.attempt_id) == "running"
    JobRepository().reclaim_expired(session, force_attempt_id=authority.attempt_id, fail_reason="attempt_stalled")
    assert JobRepository.attempt_state(session, authority.attempt_id) == "lost"
    assert JobRepository.attempt_state(session, "att_does_not_exist") is None


# --- the heartbeat thread against the real tables -------------------------------------------------------------------------


@pytest.fixture
def tiny_limits(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lease_module, "HEARTBEAT_SECONDS", 0.1)
    monkeypatch.setattr(lease_module, "ATTEMPT_LOCAL_SILENCE_SECONDS", 0.6)
    monkeypatch.setattr(lease_module, "ATTEMPT_CALL_GRACE_SECONDS", 0.4)
    monkeypatch.setattr(lease_module, "ATTEMPT_RETURN_GRACE_SECONDS", 0.5)


@pytest.fixture
def recovery():
    told: list[RevokedAttempt] = []
    informed = threading.Event()
    before = current_slot_recovery()
    install_slot_recovery(lambda notice: (told.append(notice), informed.set()))
    try:
        yield told, informed
    finally:
        install_slot_recovery(before)


def _committed_claim(sessions, blob_store, helpers):
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        run_id = _queued_run(session, seeded)
        session.commit()
    with sessions() as session:
        authority = _claim(session, run_id)
        session.commit()
    return run_id, authority


def _heartbeat_for(engine, authority) -> LeaseHeartbeat:
    return LeaseHeartbeat(engine, authority)


def _wait_for(predicate, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_a_live_attempt_that_goes_silent_is_failed_by_the_heartbeat_and_a_hung_thread_is_reported(
    engine, sessions, quiet_queue, blob_store, helpers, tiny_limits, recovery,
):
    told, informed = recovery
    run_id, authority = _committed_claim(sessions, blob_store, helpers)
    heartbeat = _heartbeat_for(engine, authority)
    heartbeat.start()
    began = time.monotonic()
    try:
        heartbeat.context.progress()  # live, then silent: the work thread has hung
        assert _wait_for(lambda: _state(sessions, run_id) == "failed", 15), "the stalled Attempt did not fail its Run"
        assert time.monotonic() - began >= 0.55, "fenced before its silence limit"
        with sessions() as session:
            row = _row(session, run_id)
            assert (row.state, row.interrupted_reason, row.job_state) == ("failed", "attempt_stalled", "failed")
            assert tuple(_attempt_and_lease(session, authority.attempt_id)) == ("lost", True)
            assert _jobs_of(session, run_id) == ["failed"]
        # The work thread never stops the heartbeat: after the grace the process is told.
        assert informed.wait(timeout=10), "the slot recovery was not told about a thread that never returned"
    finally:
        heartbeat.stop()
    (notice,) = told
    assert (notice.run_id, notice.attempt_id, notice.reason) == (run_id, authority.attempt_id, "fenced:stalled")


def test_a_live_attempt_in_a_call_longer_than_its_silence_limit_is_left_alone_until_the_call_overruns(
    engine, sessions, quiet_queue, blob_store, helpers, tiny_limits, recovery,
):
    run_id, authority = _committed_claim(sessions, blob_store, helpers)
    heartbeat = _heartbeat_for(engine, authority)
    heartbeat.start()
    try:
        heartbeat.context.progress()
        heartbeat.context.call_started(window_seconds=1.5)  # a call 2.5 times the silence limit
        began = time.monotonic()
        time.sleep(1.4)
        assert _state(sessions, run_id) == "running", "failed inside its own call window"
        assert _wait_for(lambda: _state(sessions, run_id) == "failed", 15), "a call that overran its window was not fenced"
        assert time.monotonic() - began >= 1.85, "fenced before the call's window and grace (1.5 s + 0.4 s)"
        with sessions() as session:
            assert _row(session, run_id).interrupted_reason == "attempt_stalled"
    finally:
        heartbeat.stop()


def test_a_cancelled_attempt_whose_thread_does_not_return_is_reported_and_one_that_returns_is_not(
    engine, sessions, quiet_queue, blob_store, helpers, tiny_limits, recovery,
):
    """``cancelRun`` only marks the database (`cancel_for_run`): the lease is released and the Attempt ``cancelled``. The heartbeat
    sees the lease go (its extension finds nothing) and reads why; it starts the same count as for a stall."""
    told, informed = recovery
    run_id, authority = _committed_claim(sessions, blob_store, helpers)
    heartbeat = _heartbeat_for(engine, authority)
    heartbeat.start()
    try:
        heartbeat.context.progress()
        heartbeat.context.call_started(window_seconds=3600.0)  # inside a call: the stall fence does not apply
        with sessions() as session:
            JobRepository().cancel_for_run(session, run_id=run_id)
            session.commit()
        assert informed.wait(timeout=15), "a cancelled Attempt's hung thread was not reported"
    finally:
        heartbeat.stop()
    (notice,) = told
    assert notice.reason == "revoked:cancelled" and notice.run_id == run_id

    # The same cancel, but the work thread returns (it stops the heartbeat) within the grace: nothing is reported.
    told.clear(), informed.clear()
    run_two, authority_two = _committed_claim(sessions, blob_store, helpers)
    returning = _heartbeat_for(engine, authority_two)
    returning.start()
    try:
        with sessions() as session:
            JobRepository().cancel_for_run(session, run_id=run_two)
            session.commit()
        time.sleep(0.25)  # the heartbeat has seen it and is waiting for the thread
        returning.stop()  # the work thread's `finally`
        assert not informed.wait(timeout=1.0), "a thread that returned was reported as a lost slot"
    finally:
        returning.stop()
    assert told == []


def test_an_attempt_that_finished_itself_is_never_reported(
    engine, sessions, quiet_queue, blob_store, helpers, tiny_limits, recovery,
):
    """`finish_execution` releases the lease before the work thread stops the heartbeat; a tick that lands in between finds a
    released lease and a ``succeeded`` Attempt, and must not start a count."""
    told, informed = recovery
    run_id, authority = _committed_claim(sessions, blob_store, helpers)
    heartbeat = _heartbeat_for(engine, authority)
    heartbeat.start()
    try:
        with sessions() as session:
            JobRepository().finish_execution(session, authority, publishes_result=True)
            session.commit()
        assert not informed.wait(timeout=1.5), "an Attempt that ended itself was reported"
    finally:
        heartbeat.stop()
    assert told == []


def _state(sessions, run_id: str) -> str:
    with sessions() as session:
        return str(session.execute(text("SELECT state FROM audit_run WHERE run_id = :run_id"), {"run_id": run_id}).scalar_one())
