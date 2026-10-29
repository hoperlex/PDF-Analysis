"""A version of identical bytes takes over the stored profiles of its project instead of profiling them again (`CMP-C1-FIX-C` item 3).

`MEASURE-ENGINE-01.md` section 9 item 4: v4, byte-identical to v3, cost 63 s of wall and 59 s of child CPU to produce profiles whose
blobs the store then shared with v3's. The page content Merkle is a product of the extraction child, so it cannot key a cache that
skips the work; what is known beforehand is the source bytes. Here the real children are behind a spy: a version that takes
another's rows must not start one, a version that cannot must start exactly the children it needs, and nothing of another project
is ever taken. Against PostgreSQL and the object store, through the real runner and the real builder.
"""

from __future__ import annotations

from collections import Counter

from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile.runner import ChildResult
from auditmanager.comparison.public import PROFILE_NEEDS_REVIEW, PROFILE_READY, REASON_RENDER_FAILED
from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, MANIFEST_ROLE_SOURCE_DOCUMENT


def started(spy) -> Counter[tuple[str, int]]:
    return Counter(spy.calls)


def facts(rows) -> list[tuple]:
    """What a profile row says, apart from its own identity."""
    return [
        (r.page_number, r.status, r.reason, r.content_key, r.profile_blob_id, r.preview_blob_id, r.thumbnail_blob_id) for r in rows
    ]


def build_first(lane, pdf, pages, spy):
    seeded = lane.seed(pdf, pages)
    report = build_version_page_profiles(lane.sessions, lane.blob_store, seeded.version_uid, runner=spy)
    assert report.complete and report.reused == 0
    return seeded


def test_a_version_of_identical_bytes_in_the_same_project_takes_the_rows_and_starts_no_child(lane, small_pdf, spy) -> None:
    pdf = small_pdf(5)
    donor = build_first(lane, pdf, 5, spy)
    first_rows = lane.rows(donor.version_uid)
    assert len(first_rows) == 5 and len(spy.calls) == 10, "two children a page for the first version"
    spy.calls.clear()

    # the second copy is what the comparison upload makes of a re-sent file: another role, the same bytes
    again = lane.seed(pdf, 5, project_uid=donor.project_uid, manifest_role=MANIFEST_ROLE_COMPARISON_PDF)
    lane.enqueue(again)
    runner = lane.runner(spy)
    assert runner.execute(lane.claim(runner)) == "succeeded"

    assert spy.calls == [], "no render child and no extraction child was started for a version whose bytes were profiled"
    rows = lane.rows(again.version_uid)
    assert facts(rows) == facts(first_rows), "the same pages, statuses, content keys and blobs"
    assert {r.id for r in rows}.isdisjoint({r.id for r in first_rows}), "rows of its own"
    assert [r.status for r in rows] == [PROFILE_READY] * 5
    assert lane.rows(donor.version_uid) == first_rows, "the donor's rows were not touched"


def test_the_report_says_which_pages_were_taken_over_and_they_do_not_count_against_the_bound(lane, small_pdf, spy) -> None:
    pdf = small_pdf(12)
    donor = build_first(lane, pdf, 12, spy)
    spy.calls.clear()
    again = lane.seed(pdf, 12, project_uid=donor.project_uid)
    enqueued = lane.enqueue(again)
    runner = lane.runner(spy, pages_per_attempt=5)  # a bound of five pages: taking over twelve is not building twelve
    assert runner.execute(lane.claim(runner)) == "succeeded", "one attempt, no yield"
    assert [(a["attempt_no"], a["state"]) for a in lane.attempts(enqueued.work_id)] == [(1, "succeeded")]
    assert spy.calls == [] and len(lane.rows(again.version_uid)) == 12

    # asked directly, the builder names what it took and from whom
    third = lane.seed(pdf, 12, project_uid=donor.project_uid)
    report = build_version_page_profiles(lane.sessions, lane.blob_store, third.version_uid, runner=spy)
    assert (report.reused, report.remaining, report.complete) == (12, 0, True)
    assert {page.timings["reused_from"] for page in report.pages} <= {donor.version_uid, again.version_uid}
    assert spy.calls == []


def test_identical_bytes_in_another_project_are_profiled_again_and_nothing_is_taken_across_projects(lane, small_pdf, spy) -> None:
    pdf = small_pdf(3)
    donor = build_first(lane, pdf, 3, spy)
    first_rows = lane.rows(donor.version_uid)
    spy.calls.clear()

    elsewhere = lane.seed(pdf, 3)  # a project of its own: the same bytes
    assert elsewhere.project_uid != donor.project_uid
    report = build_version_page_profiles(lane.sessions, lane.blob_store, elsewhere.version_uid, runner=spy)
    assert (report.reused, report.complete) == (0, True)
    assert started(spy) == Counter({(mode, page): 1 for mode in ("render", "extract") for page in range(3)}), "every page was built"
    assert lane.rows(donor.version_uid) == first_rows


def test_a_page_the_donor_could_not_build_is_built_here_and_the_rest_is_taken(lane, small_pdf, spy) -> None:
    """A page that ended without a result says what a host could not do, not what the page is: it is never copied."""
    pdf = small_pdf(4)
    spy.hooks[("render", 1)] = lambda: ChildResult(status="overrun", stage="render")  # page 2 fails for the donor
    donor = build_first(lane, pdf, 4, spy)
    donor_rows = lane.rows(donor.version_uid)
    assert [r.status for r in donor_rows] == [PROFILE_READY, PROFILE_NEEDS_REVIEW, PROFILE_READY, PROFILE_READY]
    assert donor_rows[1].reason == REASON_RENDER_FAILED
    spy.calls.clear()
    spy.hooks.clear()  # the host is fine now

    again = lane.seed(pdf, 4, project_uid=donor.project_uid)
    report = build_version_page_profiles(lane.sessions, lane.blob_store, again.version_uid, runner=spy)
    assert (report.reused, report.complete) == (3, True)
    assert started(spy) == Counter({("render", 1): 1, ("extract", 1): 1}), "only the page the donor lacked was built"
    rows = lane.rows(again.version_uid)
    assert [r.status for r in rows] == [PROFILE_READY] * 4, "the failed page was built properly here"
    assert facts(rows)[0] == facts(donor_rows)[0] and facts(rows)[2:] == facts(donor_rows)[2:]
    assert rows[1].id != donor_rows[1].id and rows[1].profile_blob_id is not None


def test_bytes_that_differ_are_never_taken_over_even_when_the_page_counts_agree(lane, small_pdf, spy) -> None:
    donor = build_first(lane, small_pdf(3), 3, spy)
    spy.calls.clear()
    other = lane.seed(small_pdf(3), 3, project_uid=donor.project_uid)  # three pages of other words
    report = build_version_page_profiles(lane.sessions, lane.blob_store, other.version_uid, runner=spy)
    assert (report.reused, report.complete) == (0, True)
    assert len(spy.calls) == 6
    assert {r.content_key for r in lane.rows(other.version_uid)}.isdisjoint({r.content_key for r in lane.rows(donor.version_uid)})


def test_the_roles_of_the_two_copies_do_not_matter_a_portal_version_is_a_donor_for_a_comparison_version(lane, small_pdf, spy) -> None:
    pdf = small_pdf(2)
    portal = lane.seed(pdf, 2, manifest_role=MANIFEST_ROLE_SOURCE_DOCUMENT)
    build_version_page_profiles(lane.sessions, lane.blob_store, portal.version_uid, runner=spy)
    spy.calls.clear()
    plain = lane.seed(pdf, 2, project_uid=portal.project_uid, manifest_role=MANIFEST_ROLE_COMPARISON_PDF)
    report = build_version_page_profiles(lane.sessions, lane.blob_store, plain.version_uid, runner=spy)
    assert report.reused == 2 and spy.calls == []
