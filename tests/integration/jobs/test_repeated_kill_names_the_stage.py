"""A worker killed in the same stage again and again leaves a run that says which (`RUN-ROBUSTNESS-01`, D-169).

`W55B-REHEARSAL-01` §4.2.2: a run whose worker the kernel kills for memory is resumed (nothing it
did can have spent a provider call), the same pages kill the next worker, and the third loss
dead-letters the Job; the run then showed ``analysis_failed`` with no stage and no detail. Lease
recovery now names the stage when the last two lost Attempts died inside the same one, in
``terminal_detail.stage_id`` -- a key ``analysis_failed`` already declares safe -- and the run
still carries ``interrupted_reason: attempt_budget_exhausted``.

HEAVY: real PostgreSQL (and MinIO for the seeded version), the way ``test_d150_and_worker_claims``
is. Each case claims, starts a stage the way the executor does (``stage_started``, which is
committed before a deterministic stage runs), lets the lease lapse, and reclaims.
"""

from __future__ import annotations

from sqlalchemy import text

from auditmanager.jobs.public import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import ErrorCode, screen_details
from auditmanager.shared.identity import RunId


def _queued_run(session, seeded) -> str:
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    JobRepository().enqueue(session, run_id=run_id)
    return run_id


def _attempt(session, run_id: str, stage_id: str | None):
    """Claim the run, start ``stage_id`` as the executor does, and lose the worker."""
    runs = RunRepository()
    if runs.get(session, run_id).state == "queued":
        runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    authority = JobRepository().start_execution(session, run_id=run_id)
    if stage_id is not None:
        runs.stage_started(session, run_id=run_id, stage_id=stage_id)
    session.execute(text(
        "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
        "WHERE lease_id = :lease_id"
    ), {"lease_id": authority.lease_id})
    assert JobRepository().reclaim_expired(session) >= 1
    return authority


def _run_row(session, run_id: str):
    return session.execute(text(
        "SELECT r.state, r.terminal_reason, r.terminal_detail, r.interrupted_reason, j.state "
        "FROM audit_run r JOIN job j ON j.run_id = r.run_id WHERE r.run_id = :run_id"
    ), {"run_id": run_id}).one()


def _exhaust(session, seeded, stages: list[str | None]) -> tuple:
    run_id = _queued_run(session, seeded)
    for stage_id in stages:
        _attempt(session, run_id, stage_id)
    return _run_row(session, run_id)


def test_the_same_stage_killing_three_workers_is_named_on_the_run(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    state, reason, detail, interrupted, job = _exhaust(
        session, seeded, ["page_geometry_extraction"] * 3
    )
    assert (state, job) == ("failed", "dead_letter")
    assert reason == "analysis_failed"
    assert detail == {"stage_id": "page_geometry_extraction"}
    assert interrupted == "attempt_budget_exhausted"
    # The run reading screens its detail against the keys the code declares safe: it passes.
    assert screen_details(ErrorCode.ANALYSIS_FAILED, detail) == detail


def test_an_earlier_attempt_lost_elsewhere_does_not_hide_the_last_two(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    state, reason, detail, _interrupted, _job = _exhaust(
        session, seeded, ["source_preparation", "page_geometry_extraction", "page_geometry_extraction"]
    )
    assert (state, reason) == ("failed", "analysis_failed")
    assert detail == {"stage_id": "page_geometry_extraction"}


def test_workers_lost_in_different_stages_are_restarts_and_no_stage_is_named(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    for stages in (
        ["source_preparation", "page_geometry_extraction", "document_context_build"],
        ["page_geometry_extraction", "page_geometry_extraction", "document_context_build"],
        ["page_geometry_extraction", "document_context_build", "source_preparation"],
    ):
        state, reason, detail, interrupted, job = _exhaust(session, seeded, stages)
        assert (state, reason, job) == ("failed", "analysis_failed", "dead_letter"), stages
        assert detail is None, (stages, detail)
        assert interrupted == "attempt_budget_exhausted"


def test_workers_lost_before_any_stage_name_none(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    state, reason, detail, interrupted, _job = _exhaust(session, seeded, [None, None, None])
    assert (state, reason, interrupted) == ("failed", "analysis_failed", "attempt_budget_exhausted")
    assert detail is None


def test_a_stage_the_third_attempt_never_started_is_not_blamed_on_it(session, blob_store, helpers):
    """Two kills in the geometry stage, then a worker lost before it started any: the last two
    lost Attempts did not die in one stage."""
    seeded = helpers.seed_version(session, blob_store)
    _state, _reason, detail, _interrupted, _job = _exhaust(
        session, seeded, ["page_geometry_extraction", "page_geometry_extraction", None]
    )
    assert detail is None


def test_a_run_that_has_not_used_its_budget_is_resumed_and_names_nothing(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    for _ in range(2):
        _attempt(session, run_id, "page_geometry_extraction")
    state, reason, detail, interrupted, job = _run_row(session, run_id)
    assert (state, job) == ("running", "queued")
    assert (reason, detail, interrupted) == (None, None, None)


def test_an_uncertain_provider_effect_keeps_its_own_reason_and_names_no_stage(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    jobs = JobRepository()
    runs = RunRepository()
    # Two workers lost inside the text stage before any call was made: resumed. The third
    # sends a live call and is lost: the outcome is unknown, whatever the last two said.
    for _ in range(2):
        _attempt(session, run_id, "text_analysis")
    authority = jobs.start_execution(session, run_id=run_id)
    runs.stage_started(session, run_id=run_id, stage_id="text_analysis")
    jobs.prepare_provider_call(
        session, authority, provider="anthropic", model_identity="claude-opus-5",
        provider_mode="live", parameters={}, request_sha256="d" * 64,
    )
    session.execute(text(
        "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
        "WHERE lease_id = :lease_id"
    ), {"lease_id": authority.lease_id})
    assert jobs.reclaim_expired(session) >= 1
    state, reason, detail, interrupted, _job = _run_row(session, run_id)
    assert (state, reason, interrupted) == ("failed", "analysis_failed", "provider_outcome_unknown")
    assert detail is None
