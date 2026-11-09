"""`R-151u`: the estimated finish of a running audit is a statistic of similar past runs, never invented."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from auditmanager.execution.eta import MINIMUM_SAMPLES, Sample, estimated_finish, expected_seconds

START = datetime(2026, 11, 6, 4, 0, tzinfo=UTC)
SAMPLES = (
    Sample("ar", 10, 600.0), Sample("ar", 11, 660.0), Sample("ar", 9, 540.0),
    Sample("ar", 40, 3000.0), Sample("kj", 10, 100.0),
)


def test_the_median_of_the_same_profile_and_a_similar_page_count() -> None:
    assert expected_seconds(SAMPLES, analysis_profile_id="ar", page_count=10) == 600.0


def test_another_profile_or_a_far_page_count_is_not_similar() -> None:
    assert expected_seconds(SAMPLES, analysis_profile_id="kj", page_count=10) is None
    assert expected_seconds(SAMPLES, analysis_profile_id="ar", page_count=25) is None


def test_fewer_samples_than_the_minimum_give_no_estimate() -> None:
    few = SAMPLES[: MINIMUM_SAMPLES - 1]
    assert expected_seconds(few, analysis_profile_id="ar", page_count=10) is None


def test_the_finish_is_the_start_plus_the_expected_duration_and_needs_a_start() -> None:
    assert estimated_finish(SAMPLES, started_at=START, analysis_profile_id="ar", page_count=10) == START + timedelta(seconds=600)
    assert estimated_finish(SAMPLES, started_at=None, analysis_profile_id="ar", page_count=10) is None


def test_the_queue_and_the_run_status_answer_through_one_rule() -> None:
    """`UI-A-65` / `UI-B-45` (contract 1.40.0): the job's state decides first, then the same statistic as above."""
    from auditmanager.bootstrap.adapters import _estimated_finish
    from auditmanager.execution.eta import RUNNING_JOB_STATES, job_estimated_finish

    assert RUNNING_JOB_STATES == ("leased", "running")
    wanted = START + timedelta(seconds=600)
    for state in RUNNING_JOB_STATES:
        assert job_estimated_finish(
            SAMPLES, job_state=state, started_at=START, analysis_profile_id="ar", page_count=10
        ) == wanted
    for state in ("queued", "retry_wait", "succeeded", "failed", "cancelled", "dead_letter", None):
        assert job_estimated_finish(
            SAMPLES, job_state=state, started_at=START, analysis_profile_id="ar", page_count=10
        ) is None, state
    assert job_estimated_finish(
        (), job_state="running", started_at=START, analysis_profile_id="ar", page_count=10
    ) is None, "no history is no estimate"
    assert job_estimated_finish(
        SAMPLES, job_state="running", started_at=None, analysis_profile_id="ar", page_count=10
    ) is None, "a job that has not started has none"

    class _Row:
        state = "running"
        started_at = START
        analysis_profile_id = "ar"
        page_count = 10

    # The queue item's own helper is that function, not a second spelling of the rule.
    assert _estimated_finish(_Row(), SAMPLES) == wanted
    _Row.state = "queued"
    assert _estimated_finish(_Row(), SAMPLES) is None
