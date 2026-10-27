"""How a ``page_profile`` item ends, stops and is retried (`CMP-PROFILE-QUEUE-01`), against PostgreSQL, MinIO and the
real page children.

The runner and the gates are the real ones; the only stand-in is a spy around the real child runner that, at a chosen
``(mode, page)`` call, requests a cancel, lets the lease run out, fails to start a child or reports a child that ended
without a result -- the states a stop button, a killed worker, a broken host and a starved page leave. The item's own
heartbeat thread is kept silent (an interval of an hour) wherever a stop is shown, so that the stop is the handler's
check between pages and not the thread's flag. What is shown: the build stops **between pages** (the page in flight is
finished and stored, nothing after it is started); an item that stopped is not lost (the pages stored stay and a later
item builds the rest without rewriting them); a child that never started retries the attempt; a page that ended without
a result is a stored page, not a failed item, and the retry item builds only it.
"""

from __future__ import annotations

from typing import Any

from auditmanager.comparison.profile.runner import ChildResult, ChildStartError
from auditmanager.comparison.public import (
    CANCEL_REQUESTED,
    PROFILE_NEEDS_REVIEW,
    PROFILE_READY,
    REASON_RENDER_FAILED,
)

QUIET = 3600.0  # a heartbeat interval at which the thread never beats during a test


def pages_started(spy: Any) -> set[int]:
    """The 0-based pages a child was started (or asked) for."""
    return {page for _, page in spy.calls}


def test_a_cancel_requested_while_the_item_runs_stops_the_build_between_pages_and_a_later_item_builds_the_rest(
    lane, small_pdf, spy
) -> None:
    seeded = lane.seed(small_pdf(6), 6)
    enqueued = lane.enqueue(seeded)
    answers: list[str] = []
    spy.hooks[("render", 1)] = lambda: answers.append(lane.cancel(enqueued.work_id))  # during page 2 (0-based 1)

    runner = lane.runner(spy, heartbeat_seconds=QUIET)
    assert runner.execute(lane.claim(runner)) == "cancelled"

    assert answers == [CANCEL_REQUESTED]
    rows = lane.rows(seeded.version_uid)
    assert [row.page_number for row in rows] == [1, 2], "the page in flight was finished and stored"
    assert pages_started(spy) == {0, 1}, "no child was started for a page after the cancel"
    work = lane.work(enqueued.work_id)
    assert (work["state"], work["terminal"], work["cancel_requested"]) == ("cancelled", True, True)
    assert [(a["attempt_no"], a["state"]) for a in lane.attempts(enqueued.work_id)] == [(1, "cancelled")]

    # Nothing is lost: a later item builds pages 3 to 6 and leaves pages 1 and 2 exactly as they were.
    ids = [row.id for row in rows]
    later = lane.enqueue(seeded)
    assert later.created is True and later.work_id != enqueued.work_id
    resumed = lane.runner()
    assert resumed.execute(lane.claim(resumed)) == "succeeded"
    after = lane.rows(seeded.version_uid)
    assert [row.page_number for row in after] == [1, 2, 3, 4, 5, 6]
    assert [row.id for row in after][:2] == ids


def test_a_lease_that_runs_out_mid_build_stops_it_between_pages_and_the_reclaimed_item_finishes_the_version(
    lane, small_pdf, spy
) -> None:
    seeded = lane.seed(small_pdf(6), 6)
    enqueued = lane.enqueue(seeded)
    held: list[str] = []
    spy.hooks[("render", 2)] = lambda: lane.expire_lease(held[0])  # during page 3 (0-based 2)

    runner = lane.runner(spy, heartbeat_seconds=QUIET)
    item = lane.claim(runner)
    held.append(item.attempt_id)
    assert runner.execute(item) is None, "an attempt that lost its lease has its answer dropped"

    rows = lane.rows(seeded.version_uid)
    assert [row.page_number for row in rows] == [1, 2, 3], "the page in flight finished; nothing after it started"
    assert pages_started(spy) == {0, 1, 2}
    assert lane.work(enqueued.work_id)["state"] == "running", "the reclaim, not the stopped holder, ends the attempt"

    assert runner.reclaim() == 1
    assert lane.work(enqueued.work_id)["state"] == "queued"
    lane.make_due(enqueued.work_id)
    ids = [row.id for row in rows]
    resumed = lane.runner()
    assert resumed.execute(lane.claim(resumed)) == "succeeded"
    assert [(a["attempt_no"], a["state"]) for a in lane.attempts(enqueued.work_id)] == [(1, "lost"), (2, "succeeded")]
    after = lane.rows(seeded.version_uid)
    assert [row.page_number for row in after] == [1, 2, 3, 4, 5, 6]
    assert [row.id for row in after][:3] == ids, "the pages stored before the loss were not rewritten"


def test_a_child_that_never_started_fails_the_attempt_with_a_retry_and_the_next_attempt_resumes(
    lane, small_pdf, spy
) -> None:
    seeded = lane.seed(small_pdf(4), 4)
    enqueued = lane.enqueue(seeded)

    def no_start() -> None:
        raise ChildStartError("the child died before it set its limits")

    spy.hooks[("render", 2)] = no_start  # pages 1 and 2 are stored, then the host fails

    runner = lane.runner(spy)
    assert runner.execute(lane.claim(runner)) == "queued", "a retry: the item goes back to the queue"
    rows = lane.rows(seeded.version_uid)
    assert [row.page_number for row in rows] == [1, 2]
    work = lane.work(enqueued.work_id)
    assert (work["state"], work["terminal"], work["attempt_count"]) == ("queued", False, 1)
    assert [(a["state"], a["failure_reason"]) for a in lane.attempts(enqueued.work_id)] == [
        ("failed", "page_profile_child_start_failed")
    ]

    lane.make_due(enqueued.work_id)
    ids = [row.id for row in rows]
    resumed = lane.runner()
    assert resumed.execute(lane.claim(resumed)) == "succeeded"
    assert [(a["attempt_no"], a["state"]) for a in lane.attempts(enqueued.work_id)] == [(1, "failed"), (2, "succeeded")]
    after = lane.rows(seeded.version_uid)
    assert [row.page_number for row in after] == [1, 2, 3, 4] and [row.id for row in after][:2] == ids


def test_a_child_that_never_starts_again_spends_the_attempt_budget_and_the_item_fails_with_its_reason(
    lane, small_pdf, spy
) -> None:
    seeded = lane.seed(small_pdf(2), 2)
    enqueued = lane.enqueue(seeded)

    def no_start() -> None:
        raise ChildStartError("still no child")

    spy.hooks[("render", 0)] = no_start
    runner = lane.runner(spy)
    outcomes = []
    for _ in range(3):  # max_attempts is 3
        lane.make_due(enqueued.work_id)
        outcomes.append(runner.execute(lane.claim(runner)))
    assert outcomes == ["queued", "queued", "failed"]
    work = lane.work(enqueued.work_id)
    assert (work["state"], work["failure_reason"], work["terminal"]) == ("failed", "page_profile_child_start_failed", True)
    assert lane.rows(seeded.version_uid) == []


def test_a_page_that_ends_without_a_result_is_a_stored_page_and_the_item_still_succeeds_then_a_retry_item_builds_only_it(
    lane, small_pdf, spy
) -> None:
    seeded = lane.seed(small_pdf(3), 3)
    first = lane.enqueue(seeded)
    spy.hooks[("render", 1)] = lambda: ChildResult(status="overrun", stage="render")

    runner = lane.runner(spy)
    assert runner.execute(lane.claim(runner)) == "succeeded", "a page that failed is stored; the version goes on"
    rows = lane.rows(seeded.version_uid)
    assert [row.status for row in rows] == [PROFILE_READY, PROFILE_NEEDS_REVIEW, PROFILE_READY]
    assert rows[1].reason == REASON_RENDER_FAILED
    assert (rows[1].profile_blob_id, rows[1].preview_blob_id, rows[1].thumbnail_blob_id) == (None, None, None)

    # A plain item finds a row for every page and builds nothing; the retry item is the one that asks for the failed page.
    plain = lane.enqueue(seeded)
    assert plain.created is True and plain.work_id != first.work_id
    again = lane.runner()
    assert again.execute(lane.claim(again)) == "succeeded"
    assert [row.id for row in lane.rows(seeded.version_uid)] == [row.id for row in rows]

    retry = lane.enqueue(seeded, retry_failed=True)
    assert retry.created is True and lane.work(retry.work_id)["payload"]["retry_failed"] is True
    rebuilt = lane.runner()
    assert rebuilt.execute(lane.claim(rebuilt)) == "succeeded"
    after = lane.rows(seeded.version_uid)
    assert [row.status for row in after] == [PROFILE_READY] * 3
    assert after[0].id == rows[0].id and after[2].id == rows[2].id, "the ready pages were not touched"
    assert after[1].id != rows[1].id and after[1].profile_blob_id is not None


def test_a_version_the_database_does_not_know_fails_the_item_at_once_without_a_retry(lane, small_pdf) -> None:
    seeded = lane.seed(small_pdf(1), 1)
    with lane.sessions() as session:
        enqueued = lane.repository.enqueue(
            session, project_uid=seeded.project_uid, module="versions", kind="page_profile",
            payload={"version_uid": "ver_01ZZZZZZZZZZZZZZZZZZZZZZZZ"},
        )
        session.commit()
    runner = lane.runner()
    assert runner.execute(lane.claim(runner)) == "failed"
    work = lane.work(enqueued.work_id)
    assert (work["state"], work["failure_reason"], work["attempt_count"]) == ("failed", "page_profile_version_not_found", 1)


def test_a_version_whose_source_cannot_be_read_is_retried_until_the_budget_is_spent(lane, small_pdf) -> None:
    seeded = lane.seed(small_pdf(2), 2, with_manifest=False)  # no source document in its manifest
    with lane.sessions() as session:
        enqueued = lane.repository.enqueue(
            session, project_uid=seeded.project_uid, module="versions", kind="page_profile",
            payload={"version_uid": seeded.version_uid},
        )
        session.commit()
    runner = lane.runner()
    outcomes = []
    for _ in range(3):
        lane.make_due(enqueued.work_id)
        outcomes.append(runner.execute(lane.claim(runner)))
    assert outcomes == ["queued", "queued", "failed"]
    assert lane.work(enqueued.work_id)["failure_reason"] == "page_profile_source_unreadable"
    assert lane.rows(seeded.version_uid) == []


def test_a_payload_of_another_shape_fails_the_item_at_once_without_a_retry_and_without_a_child(lane, small_pdf, spy) -> None:
    seeded = lane.seed(small_pdf(1), 1)
    made = []
    for payload in ({"version_uid": "not-an-identity"}, {"version_uid": seeded.version_uid, "path": "/x.pdf"}, {}):
        with lane.sessions() as session:
            made.append(lane.repository.enqueue(
                session, project_uid=seeded.project_uid, module="versions", kind="page_profile", payload=payload,
            ))
            session.commit()
    runner = lane.runner(spy)
    for enqueued in made:
        assert runner.execute(lane.claim(runner)) == "failed"
        work = lane.work(enqueued.work_id)
        assert (work["state"], work["failure_reason"], work["attempt_count"]) == ("failed", "page_profile_payload_invalid", 1)
    assert spy.calls == [] and lane.rows(seeded.version_uid) == []
