"""`UI-A-65` / `UI-B-45` (contract 1.40.0) on real PostgreSQL: `RunStatus.estimated_finish_at` is the estimate the execution
queue shows for the run's job, by one rule.

Every test builds its own runs and jobs on the suite's rolled-back session. The history the estimate is a median of is the
latest completed runs of the whole database, so the completed runs are seeded under a **profile of their own** (a fresh
``analysis_profile_id`` each test), which no other suite's runs share: the median is over exactly the runs seeded here.
A run's duration is from its job's first attempt to its terminal time, both read from the database's own clock, so the
durations here are a few milliseconds -- positive, which is all the estimate asks, and the assertions compare the
estimate with the history the same function reads and not with a number written in the test.
"""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import text

from auditmanager.api.schemas.runs import run_status_body
from auditmanager.bootstrap.adapters import ExecutionAdapter, _run_status_view
from auditmanager.execution.eta import MINIMUM_SAMPLES, history
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.identity import AnalysisProfileId, RunId


def _new_run(session, seeded, profile: str) -> tuple[str, str]:
    """A queued run of ``profile`` on the seeded version, with its job."""
    run_id = str(RunId.new())
    repo = RunRepository()
    repo.create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=profile, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
    )
    repo.advance(session, run_id=run_id, from_state="created", to_state="queued")
    return run_id, JobRepository().enqueue(session, run_id=run_id)


def _completed(session, seeded, profile: str) -> str:
    """A run that was claimed, ran and published: it enters the history with a positive duration."""
    run_id, _ = _new_run(session, seeded, profile)
    JobRepository().start_execution(session, run_id=run_id)
    repo = RunRepository()
    repo.advance(session, run_id=run_id, from_state="queued", to_state="running")
    repo.advance(session, run_id=run_id, from_state="running", to_state="validating")
    repo.terminate(session, run_id=run_id, from_state="validating", to_state="published")
    return run_id


def _adapter(session) -> ExecutionAdapter:
    return ExecutionAdapter(lambda: nullcontext(session), runs=None)  # type: ignore[arg-type]


def _queue_item(session, job_id: str):
    adapter, cursor = _adapter(session), None
    for _ in range(500):
        page = adapter.list_queue(cursor=cursor, limit=200)
        for item in page.items:
            if item.job_id == job_id:
                return item
        cursor = page.page.next_cursor
        if cursor is None:
            break
    raise AssertionError("the job is not in the queue's listing")


def _first_attempt(session, job_id: str) -> datetime:
    return session.execute(
        text("SELECT min(created_at) FROM attempt WHERE job_id = :job"), {"job": job_id}
    ).scalar_one()


def test_a_running_run_carries_the_estimate_its_queue_item_carries(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    profile = str(AnalysisProfileId.new())
    for _ in range(MINIMUM_SAMPLES):
        _completed(session, seeded, profile)
    run_id, job_id = _new_run(session, seeded, profile)
    JobRepository().start_execution(session, run_id=run_id)
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")

    status = _run_status_view(session, run_id)
    item = _queue_item(session, job_id)
    assert status.state == "running" and item.state == "running"
    assert status.estimated_finish_at is not None, "three similar completed runs are enough"
    assert item.estimated_finish_at == status.estimated_finish_at, "one rule: the queue and the run page cannot differ"

    # ... and it is the rule written in `execution.eta`: the first attempt plus the median of the similar history.
    ours = [sample.seconds for sample in history(session) if sample.analysis_profile_id == profile]
    assert len(ours) == MINIMUM_SAMPLES and all(seconds > 0 for seconds in ours)
    assert status.estimated_finish_at == _first_attempt(session, job_id) + timedelta(seconds=median(ours))

    body = run_status_body(status)
    assert body["estimated_finish_at"].endswith("Z") and body["state"] == "running"


def test_the_estimate_is_absent_without_enough_history_and_never_invented(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    profile = str(AnalysisProfileId.new())
    for _ in range(MINIMUM_SAMPLES - 1):
        _completed(session, seeded, profile)
    run_id, job_id = _new_run(session, seeded, profile)
    JobRepository().start_execution(session, run_id=run_id)
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
    status = _run_status_view(session, run_id)
    assert status.state == "running" and status.estimated_finish_at is None
    assert _queue_item(session, job_id).estimated_finish_at is None, "the queue says the same"
    assert "estimated_finish_at" not in run_status_body(status), "absent is omitted, not null"


def test_a_run_that_is_not_being_worked_on_has_none(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    profile = str(AnalysisProfileId.new())
    finished = [_completed(session, seeded, profile) for _ in range(MINIMUM_SAMPLES)]
    # A queued run (no attempt yet): enough history, nothing to add it to.
    queued, queued_job = _new_run(session, seeded, profile)
    status = _run_status_view(session, queued)
    assert status.state == "queued" and status.estimated_finish_at is None
    assert _queue_item(session, queued_job).estimated_finish_at is None
    # A finished run: no estimate of an end that has happened.
    for run_id in finished:
        done = _run_status_view(session, run_id)
        assert done.state == "published" and done.estimated_finish_at is None
