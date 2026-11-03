"""`UI-PARITY-QUEUE-A` on real PostgreSQL: what a queue row says about the work, the state filter, the period, and a cursor
across a filter.

Every test builds its own runs and jobs on the suite's rolled-back session and asserts about *those* (the lane database
carries other suites' rows, so a count over the whole queue would be an assertion about someone else's data). The period
tests move their jobs to a decade no other row is in (``created_at`` is a plain column; its order against the other rows
is what the query reads, and the fixture states the dates it uses).
"""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from auditmanager.api.schemas.common import decode_cursor
from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.execution.public import ExecutionRepository
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId

#: A window in which no other row of any suite lives.
WINDOW = datetime(2031, 3, 1, tzinfo=timezone.utc)


def _run(session, seeded) -> str:
    run_id = str(RunId.new())
    repo = RunRepository()
    repo.create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
    )
    repo.advance(session, run_id=run_id, from_state="created", to_state="queued")
    return run_id


def _queued(session, seeded) -> tuple[str, str]:
    run_id = _run(session, seeded)
    return run_id, JobRepository().enqueue(session, run_id=run_id)


def _everything(adapter: ExecutionAdapter, **filters):
    """Every item of the listing under these filters, by walking its cursors."""
    items, cursor = [], None
    for _ in range(500):
        page = adapter.list_queue(cursor=cursor, limit=200, **filters)
        items.extend(page.items)
        cursor = page.page.next_cursor
        if cursor is None:
            return items
    raise AssertionError("the listing did not end")


def _adapter(session) -> ExecutionAdapter:
    return ExecutionAdapter(lambda: nullcontext(session), runs=None)  # type: ignore[arg-type]


def _item(adapter: ExecutionAdapter, job_id: str):
    return next(item for item in _everything(adapter) if item.job_id == job_id)


# ------------------------------------------------------------------------------ what a row says about the work


def test_a_queued_job_names_its_project_document_and_version_and_has_neither_start_nor_end(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id, job_id = _queued(session, seeded)
    item = _item(_adapter(session), job_id)
    assert (item.project_uid, item.project_name) == (seeded.project_uid, "Синтетический проект")
    assert (item.document_uid, item.document_name) == (seeded.document_uid, "СП-7-АР")
    assert (item.version_uid, item.version_ordinal) == (seeded.version_uid, 1)
    assert item.run_id == run_id and item.state == "queued"
    # No attempt, no end, no reason: each is unset, which is how the wire omits it.
    unset = item.model_dump(mode="json", exclude_unset=True)
    for absent in ("started_at", "finished_at", "error_code", "interrupted_reason", "binding_state", "wait_reason"):
        assert absent not in unset, absent


def test_a_claimed_job_starts_when_its_first_attempt_was_created(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id, job_id = _queued(session, seeded)
    JobRepository().start_execution(session, run_id=run_id)
    first = session.execute(
        text("SELECT min(created_at) FROM attempt WHERE job_id = :job"), {"job": job_id}
    ).scalar_one()
    item = _item(_adapter(session), job_id)
    assert item.state == "running"
    assert item.started_at == first, "the start is the first attempt's creation, read from the attempt"
    assert item.finished_at is None and item.error_code is None


def test_a_failed_job_carries_its_end_and_the_reason_the_run_recorded(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id, job_id = _queued(session, seeded)
    jobs = JobRepository()
    authority = jobs.start_execution(session, run_id=run_id)
    jobs.finish_execution(session, authority, publishes_result=False)
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
    RunRepository().terminate(
        session, run_id=run_id, from_state="running", to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        interrupted_reason="executor_process_ended_before_terminal",
    )
    row = session.execute(
        text("SELECT terminal_at FROM job WHERE job_id = :job"), {"job": job_id}
    ).scalar_one()
    item = _item(_adapter(session), job_id)
    assert item.state == "failed"
    assert item.finished_at == row, "the end is the job's own terminal time"
    assert item.started_at is not None and item.started_at <= item.finished_at
    assert item.error_code is not None and item.error_code.value == "analysis_failed"
    assert item.interrupted_reason == "executor_process_ended_before_terminal"


def test_a_cancelled_job_has_an_end_and_no_error(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    run_id, job_id = _queued(session, seeded)
    JobRepository().cancel_for_run(session, run_id=run_id)
    item = _item(_adapter(session), job_id)
    assert item.state == "cancelled" and item.finished_at is not None
    assert item.error_code is None and item.interrupted_reason is None
    assert item.started_at is None, "it never had an attempt, and nothing is guessed in its place"


def test_the_item_a_priority_change_answers_is_the_listed_one(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    _, job_id = _queued(session, seeded)
    JobRepository().set_priority(session, job_id=job_id, priority=7)
    row = ExecutionRepository().get_queue_item(session, job_id)
    assert row is not None and row.priority == 7
    listed = _item(_adapter(session), job_id)
    assert (row.project_name, row.document_name, row.version_ordinal) == (
        listed.project_name, listed.document_name, listed.version_ordinal,
    )


# ------------------------------------------------------------------------------ the filters


def _four_states(session, seeded):
    """One job in each of queued, running, cancelled, failed -- the four a test can reach by the real commands."""
    jobs = JobRepository()
    queued_run, queued = _queued(session, seeded)
    running_run, running = _queued(session, seeded)
    jobs.start_execution(session, run_id=running_run)
    cancelled_run, cancelled = _queued(session, seeded)
    jobs.cancel_for_run(session, run_id=cancelled_run)
    failed_run, failed = _queued(session, seeded)
    authority = jobs.start_execution(session, run_id=failed_run)
    jobs.finish_execution(session, authority, publishes_result=False)
    return {"queued": queued, "running": running, "cancelled": cancelled, "failed": failed}


def test_the_state_filter_keeps_the_jobs_in_that_state_and_only_those(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    mine = _four_states(session, seeded)
    adapter = _adapter(session)
    for state, job_id in mine.items():
        listed = _everything(adapter, state=state)
        assert {item.state for item in listed} == {state}, f"{state}: another state came through the filter"
        assert job_id in {item.job_id for item in listed}
        assert not ({other for name, other in mine.items() if name != state} & {item.job_id for item in listed})
    assert {item.job_id for item in _everything(adapter)} >= set(mine.values()), "no filter lists every state"


def test_a_filtered_listing_is_the_unfiltered_one_with_the_other_states_removed_in_the_same_order(
    session, blob_store, helpers,
):
    seeded = helpers.seed_version(session, blob_store)
    for _ in range(3):
        run_id, _ = _queued(session, seeded)
        JobRepository().cancel_for_run(session, run_id=run_id)
    _queued(session, seeded)
    adapter = _adapter(session)
    unfiltered = [item.job_id for item in _everything(adapter) if item.state == "cancelled"]
    filtered = [item.job_id for item in _everything(adapter, state="cancelled")]
    assert len(filtered) >= 3 and filtered == unfiltered


def test_the_period_is_half_open_over_the_creation_of_the_job(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    ids = []
    for day in range(3):
        _, job_id = _queued(session, seeded)
        session.execute(
            text("UPDATE job SET created_at = :at WHERE job_id = :job"),
            {"at": WINDOW + timedelta(days=day), "job": job_id},
        )
        ids.append(job_id)
    first, second, third = ids
    adapter = _adapter(session)

    def listed(**filters):
        return [i.job_id for i in _everything(adapter, **filters) if i.job_id in ids]

    day = timedelta(days=1)
    assert listed(created_from=WINDOW, created_to=WINDOW + 3 * day) == [first, second, third]
    assert listed(created_from=WINDOW + day, created_to=WINDOW + 3 * day) == [second, third], "the lower bound is included"
    assert listed(created_from=WINDOW, created_to=WINDOW + 2 * day) == [first, second], "the upper bound is not"
    assert listed(created_from=WINDOW + day, created_to=WINDOW + day) == [], "an empty interval holds nothing"
    assert listed(created_from=WINDOW + 3 * day, created_to=WINDOW) == [], "an inverted one holds nothing"
    assert listed(created_from=WINDOW + 2 * day) == [third], "an open end is unbounded"
    assert listed(created_to=WINDOW + day) == [first]
    # The same instant with another offset is the same bound.
    plus_five = timezone(timedelta(hours=5))
    assert listed(
        created_from=(WINDOW + day).astimezone(plus_five), created_to=(WINDOW + 3 * day).astimezone(plus_five),
    ) == [second, third]
    # The period composes with the state: all three are queued, none are cancelled.
    assert listed(state="queued", created_from=WINDOW, created_to=WINDOW + 3 * day) == [first, second, third]
    assert listed(state="cancelled", created_from=WINDOW, created_to=WINDOW + 3 * day) == []


# ------------------------------------------------------------------------------ a cursor across a filter


def test_paging_under_a_filter_walks_exactly_the_filtered_list_and_ends(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    cancelled = []
    for _ in range(5):
        run_id, job_id = _queued(session, seeded)
        JobRepository().cancel_for_run(session, run_id=run_id)
        cancelled.append(job_id)
    _queued(session, seeded)
    adapter = _adapter(session)
    whole = [item.job_id for item in _everything(adapter, state="cancelled")]
    walked, cursor, pages = [], None, 0
    while True:
        page = adapter.list_queue(cursor=cursor, limit=2, state="cancelled")
        assert len(page.items) <= 2 and {item.state for item in page.items} == {"cancelled"}
        walked.extend(item.job_id for item in page.items)
        pages += 1
        cursor = page.page.next_cursor
        if cursor is None:
            break
        assert decode_cursor(cursor)[:2] == ("q2", "cancelled"), "a filtered page issues the filtered format"
    assert walked == whole and pages >= 3 and set(cancelled) <= set(walked)


def test_a_cursor_issued_under_one_filter_is_refused_under_another_and_under_none(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    for _ in range(3):
        run_id, _ = _queued(session, seeded)
        JobRepository().cancel_for_run(session, run_id=run_id)
    adapter = _adapter(session)
    filtered = adapter.list_queue(cursor=None, limit=1, state="cancelled")
    cursor = filtered.page.next_cursor
    assert cursor is not None
    plain = adapter.list_queue(cursor=None, limit=1)
    plain_cursor = plain.page.next_cursor
    assert plain_cursor is not None and decode_cursor(plain_cursor)[0] == "q1", "the unfiltered format is unchanged"

    refusals = [
        {"state": "queued"},
        {},
        {"state": "cancelled", "created_from": WINDOW},
        {"state": "cancelled", "created_to": WINDOW},
    ]
    for other in refusals:
        with pytest.raises(DomainError) as error:
            adapter.list_queue(cursor=cursor, limit=1, **other)
        assert error.value.code is ErrorCode.VALIDATION_FAILED, other
        assert dict(error.value.detail_fields) == {"field": "cursor", "constraint": "scope"}, other
    with pytest.raises(DomainError) as error:
        adapter.list_queue(cursor=plain_cursor, limit=1, state="cancelled")
    assert dict(error.value.detail_fields) == {"field": "cursor", "constraint": "scope"}
    # Under its own filter it still reads, and so does the unfiltered one under none.
    assert adapter.list_queue(cursor=cursor, limit=1, state="cancelled").items
    assert adapter.list_queue(cursor=plain_cursor, limit=1).items


def test_a_period_cursor_is_bound_to_the_period_too(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    ids = []
    for day in range(3):
        _, job_id = _queued(session, seeded)
        session.execute(text("UPDATE job SET created_at = :at WHERE job_id = :job"),
                        {"at": WINDOW + timedelta(days=day), "job": job_id})
        ids.append(job_id)
    adapter = _adapter(session)
    bounds = {"created_from": WINDOW, "created_to": WINDOW + timedelta(days=3)}
    first = adapter.list_queue(cursor=None, limit=1, **bounds)
    assert [item.job_id for item in first.items] == [ids[0]] and first.page.next_cursor is not None
    second = adapter.list_queue(cursor=first.page.next_cursor, limit=1, **bounds)
    assert [item.job_id for item in second.items] == [ids[1]]
    with pytest.raises(DomainError) as error:
        adapter.list_queue(cursor=first.page.next_cursor, limit=1, created_from=WINDOW,
                           created_to=WINDOW + timedelta(days=2))
    assert dict(error.value.detail_fields) == {"field": "cursor", "constraint": "scope"}
