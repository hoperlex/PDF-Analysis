"""What ``enqueue_version_page_profiles`` writes and what it refuses (`CMP-PROFILE-QUEUE-01`), against PostgreSQL.

No child runs here: the items stay queued and the rows of ``comparison_work`` are read back. Shown: the row is the
item the worker will claim (module ``versions``, kind ``page_profile``, the version as its whole payload, the author);
one live item per version and one per retry request, however often the call is made; a version of another project, an
unknown one and a malformed identity are refused before anything is written; the call writes in the caller's
transaction and commits nothing of its own.
"""

from __future__ import annotations

import pytest

from auditmanager.comparison.public import enqueue_version_page_profiles
from auditmanager.shared.errors import DomainError, ErrorCode

USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_the_item_is_what_the_worker_claims_a_versions_page_profile_item_with_the_version_as_its_payload(lane, small_pdf) -> None:
    seeded = lane.seed(small_pdf(2), 2)
    enqueued = lane.enqueue(seeded)
    assert enqueued.created is True
    work = lane.work(enqueued.work_id)
    assert (work["state"], work["module"], work["kind"], work["priority"]) == ("queued", "versions", "page_profile", 0)
    assert work["payload"] == {"version_uid": seeded.version_uid}
    assert work["dedupe_key"] == f"page_profile:{seeded.version_uid}"
    assert (work["project_uid"], work["created_by_user_uid"]) == (seeded.project_uid, USER)
    assert (work["attempt_count"], work["max_attempts"], work["terminal"]) == (0, 3, False)


def test_a_version_has_one_live_item_however_often_the_call_is_made(lane, small_pdf) -> None:
    seeded = lane.seed(small_pdf(2), 2)
    first = lane.enqueue(seeded)
    second = lane.enqueue(seeded)
    third = lane.enqueue(seeded)
    assert (first.created, second.created, third.created) == (True, False, False)
    assert second.work_id == third.work_id == first.work_id
    assert len(lane.work_of(seeded.project_uid)) == 1


def test_two_versions_are_two_items_and_a_retry_request_is_a_third_with_a_key_of_its_own(lane, small_pdf) -> None:
    one = lane.seed(small_pdf(2), 2)
    other = lane.seed(small_pdf(2), 2, project_uid=one.project_uid)
    plain, plain_other = lane.enqueue(one), lane.enqueue(other)
    retry = lane.enqueue(one, retry_failed=True)
    retry_again = lane.enqueue(one, retry_failed=True)
    assert len({plain.work_id, plain_other.work_id, retry.work_id}) == 3
    assert retry_again.work_id == retry.work_id and retry_again.created is False
    keys = sorted(w["dedupe_key"] for w in lane.work_of(one.project_uid))
    assert keys == sorted([
        f"page_profile:{one.version_uid}",
        f"page_profile:{one.version_uid}:retry_failed",
        f"page_profile:{other.version_uid}",
    ])
    assert lane.work(retry.work_id)["payload"] == {"version_uid": one.version_uid, "retry_failed": True}


def test_a_cancelled_item_frees_the_key_and_the_next_call_makes_a_new_item(lane, small_pdf) -> None:
    seeded = lane.seed(small_pdf(2), 2)
    first = lane.enqueue(seeded)
    assert lane.cancel(first.work_id) == "cancelled"
    second = lane.enqueue(seeded)
    assert second.created is True and second.work_id != first.work_id
    assert [w["state"] for w in lane.work_of(seeded.project_uid)] == ["cancelled", "queued"]


def test_a_version_of_another_project_is_not_found_and_nothing_is_written(lane, small_pdf) -> None:
    mine, theirs = lane.seed(small_pdf(1), 1), lane.seed(small_pdf(1), 1)
    with lane.sessions() as session:
        with pytest.raises(DomainError) as raised:
            enqueue_version_page_profiles(
                session, project_uid=mine.project_uid, version_uid=theirs.version_uid, created_by_user_uid=USER,
            )
        session.rollback()
    assert raised.value.code is ErrorCode.NOT_FOUND
    assert lane.work_of(mine.project_uid) == [] and lane.work_of(theirs.project_uid) == []


def test_an_unknown_version_and_a_malformed_identity_are_refused_before_anything_is_written(lane, small_pdf) -> None:
    seeded = lane.seed(small_pdf(1), 1)
    for version_uid, code in (
        ("ver_01ZZZZZZZZZZZZZZZZZZZZZZZZ", ErrorCode.NOT_FOUND),
        ("not-an-identity", ErrorCode.VALIDATION_FAILED),
        (seeded.project_uid, ErrorCode.VALIDATION_FAILED),  # an identity of another entity
    ):
        with lane.sessions() as session:
            with pytest.raises(DomainError) as raised:
                enqueue_version_page_profiles(
                    session, project_uid=seeded.project_uid, version_uid=version_uid, created_by_user_uid=USER,
                )
            session.rollback()
        assert raised.value.code is code, version_uid
    assert lane.work_of(seeded.project_uid) == []


def test_the_call_writes_in_the_callers_transaction_and_commits_nothing_of_its_own(lane, small_pdf) -> None:
    seeded = lane.seed(small_pdf(1), 1)
    with lane.sessions() as session:
        enqueued = enqueue_version_page_profiles(
            session, project_uid=seeded.project_uid, version_uid=seeded.version_uid, created_by_user_uid=USER,
        )
        assert enqueued.created is True
        session.rollback()
    assert lane.work_of(seeded.project_uid) == [], "the caller rolled back, so no item exists"
