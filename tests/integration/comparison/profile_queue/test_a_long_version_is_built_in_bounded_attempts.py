"""A version longer than one attempt holds is built completely by one item that gives itself back (`CMP-C1-FIX-C` item 2).

The queue fences an attempt after 900 s whatever its progress, and a `page_profile` item is a whole version: at the real set's
2.55 s a page a 500-page version needs about 1 276 s (`MEASURE-ENGINE-01.md` section 8.2 item 3). The attempt now builds at most
``PAGES_PER_ATTEMPT`` pages and answers a yield, which the queue puts back without spending an attempt, so the item keeps its
identity, its dedupe key and its attempt budget. Here the bound is made small (the handler takes it as a parameter) and the
version is a synthetic PDF of more pages than that, built by the real children, the real runner and PostgreSQL; the rule that
decides the shipped number is `tests/unit/comparison/profile_queue/test_page_profile_handler_unit.py`.
"""

from __future__ import annotations

from collections import Counter

from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile.runner import ChildResult
from auditmanager.comparison.public import PROFILE_NEEDS_REVIEW, PROFILE_READY, REASON_RENDER_FAILED


def rendered(spy) -> Counter[int]:
    """How many times a render child was started for each 0-based page."""
    return Counter(page for mode, page in spy.calls if mode == "render")


def test_a_version_of_more_pages_than_an_attempt_holds_is_built_completely_by_one_item_that_yields(lane, small_pdf, spy) -> None:
    seeded = lane.seed(small_pdf(14), 14)
    enqueued = lane.enqueue(seeded)
    runner = lane.runner(spy, pages_per_attempt=5)

    first = runner.execute(lane.claim(runner))
    assert first == "queued", "an attempt that left pages gives the item back; it is not a failure"
    assert [row.page_number for row in lane.rows(seeded.version_uid)] == [1, 2, 3, 4, 5]
    work = lane.work(enqueued.work_id)
    assert (work["state"], work["terminal"], work["attempt_count"]) == ("queued", False, 0), "the yield gave the charge back"
    assert work["dedupe_key"] == f"page_profile:{seeded.version_uid}" and work["payload"] == {"version_uid": seeded.version_uid}
    # a second request while the item waits is the same item: the callers that wait for the live item of a version see one
    again = lane.enqueue(seeded)
    assert again.created is False and again.work_id == enqueued.work_id

    outcomes = [first]
    for _ in range(2):
        lane.make_due(enqueued.work_id)
        outcomes.append(runner.execute(lane.claim(runner)))
    assert outcomes == ["queued", "queued", "succeeded"], "5 + 5 + 4 pages"

    rows = lane.rows(seeded.version_uid)
    assert [row.page_number for row in rows] == list(range(1, 15)) and {row.status for row in rows} == {PROFILE_READY}
    assert len({row.id for row in rows}) == 14
    assert rendered(spy) == Counter({page: 1 for page in range(14)}), "no page was started twice across the three attempts"
    assert [(a["attempt_no"], a["state"]) for a in lane.attempts(enqueued.work_id)] == [
        (1, "superseded"), (2, "superseded"), (3, "succeeded"),
    ]
    final = lane.work(enqueued.work_id)
    assert (final["state"], final["attempt_count"], final["failure_reason"]) == ("succeeded", 1, None)
    assert lane.work_of(seeded.project_uid) == [
        {"work_id": enqueued.work_id, "state": "succeeded", "dedupe_key": f"page_profile:{seeded.version_uid}",
         "payload": {"version_uid": seeded.version_uid}}
    ], "one item for the version, from its request to its end"


def test_yields_do_not_spend_the_attempt_budget_a_version_may_take_more_attempts_than_the_item_has(lane, small_pdf, spy) -> None:
    seeded = lane.seed(small_pdf(10), 10)
    enqueued = lane.enqueue(seeded)
    assert lane.work(enqueued.work_id)["max_attempts"] == 3
    runner = lane.runner(spy, pages_per_attempt=2)
    outcomes = []
    for _ in range(5):  # five attempts of two pages, against a budget of three
        lane.make_due(enqueued.work_id)
        outcomes.append(runner.execute(lane.claim(runner)))
    assert outcomes == ["queued"] * 4 + ["succeeded"]
    assert [row.page_number for row in lane.rows(seeded.version_uid)] == list(range(1, 11))
    assert len(lane.attempts(enqueued.work_id)) == 5 and lane.work(enqueued.work_id)["attempt_count"] == 1


def test_the_shipped_bound_builds_a_version_of_its_size_in_one_attempt_and_a_longer_one_in_two(lane, small_pdf) -> None:
    from auditmanager.comparison.profile_queue.handler import PAGES_PER_ATTEMPT as PAGE_PROFILE_BOUND

    seeded = lane.seed(small_pdf(PAGE_PROFILE_BOUND + 1), PAGE_PROFILE_BOUND + 1)
    enqueued = lane.enqueue(seeded)
    runner = lane.worker_runner()  # the runner the worker builds, with the shipped handler and its bound
    assert runner.execute(lane.claim(runner)) == "queued"
    assert len(lane.rows(seeded.version_uid)) == PAGE_PROFILE_BOUND
    lane.make_due(enqueued.work_id)
    assert runner.execute(lane.claim(runner)) == "succeeded"
    assert len(lane.rows(seeded.version_uid)) == PAGE_PROFILE_BOUND + 1


def test_a_retry_item_builds_the_page_that_failed_before_it_and_a_continuation_does_not_build_a_page_it_failed_itself_again(
    lane, small_pdf, spy
) -> None:
    """The retry sweep removes the failed rows that existed when the item was asked for. Were it to run again at each
    continuation, the page this item just failed to build would be removed and built once more by every attempt."""
    seeded = lane.seed(small_pdf(10), 10)
    spy.hooks[("render", 0)] = lambda: ChildResult(status="overrun", stage="render")  # page 1 fails whenever it is built
    first = build_version_page_profiles(lane.sessions, lane.blob_store, seeded.version_uid, runner=spy, pages=[1, 2])
    assert first.complete is False and [row.status for row in lane.rows(seeded.version_uid)] == [PROFILE_NEEDS_REVIEW, PROFILE_READY]
    spy.calls.clear()

    retry = lane.enqueue(seeded, retry_failed=True)
    runner = lane.runner(spy, pages_per_attempt=3)
    outcomes = []
    for _ in range(3):  # page 1 (swept) and pages 3 to 10: nine pages, three attempts
        lane.make_due(retry.work_id)
        outcomes.append(runner.execute(lane.claim(runner)))
    assert outcomes == ["queued", "queued", "succeeded"]

    assert rendered(spy)[0] == 1, "page 1 was built once by the retry item, not again by its continuations"
    rows = lane.rows(seeded.version_uid)
    assert [row.page_number for row in rows] == list(range(1, 11))
    assert [row.status for row in rows] == [PROFILE_NEEDS_REVIEW] + [PROFILE_READY] * 9
    assert rows[0].reason == REASON_RENDER_FAILED


def test_a_version_the_plain_pdf_upload_made_is_built_through_the_queue_and_a_manifest_with_two_sources_is_refused(
    lane, small_pdf, spy
) -> None:
    from sqlalchemy import text

    from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, MANIFEST_ROLE_SOURCE_DOCUMENT

    plain = lane.seed(small_pdf(3), 3, manifest_role=MANIFEST_ROLE_COMPARISON_PDF)
    lane.enqueue(plain)
    runner = lane.runner(spy)
    assert runner.execute(lane.claim(runner)) == "succeeded"
    assert [row.status for row in lane.rows(plain.version_uid)] == [PROFILE_READY] * 3

    both = lane.seed(small_pdf(2), 2, manifest_role=MANIFEST_ROLE_COMPARISON_PDF)
    with lane.sessions() as session:
        session.execute(text(
            "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
            "SELECT version_uid, :r, blob_id, sha256, size_bytes, media_type FROM input_manifest_entry WHERE version_uid = :v"
        ), {"r": MANIFEST_ROLE_SOURCE_DOCUMENT, "v": both.version_uid})
        session.commit()
    ambiguous = lane.enqueue(both)
    spy.calls.clear()
    assert runner.execute(lane.claim(runner)) == "failed", "waiting does not make a manifest choose: no retry"
    work = lane.work(ambiguous.work_id)
    assert (work["state"], work["failure_reason"], work["attempt_count"]) == ("failed", "page_profile_source_ambiguous", 1)
    assert spy.calls == [] and lane.rows(both.version_uid) == []
