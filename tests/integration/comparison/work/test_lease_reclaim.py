"""A lease that is not renewed is reclaimed (`CMP-WORK-01`, ADR-0025 decisions 4 and 5; ADR verification 4's reclaim half).

A killed worker leaves a lease that nobody renews, and the reclaim pass decides what happens to its
item: back to the queue, failed when the attempt budget is spent, cancelled when a cancel was
requested, or ``spend_unknown`` when a registered settler says a model call may have spent. The old
holder is fenced for good: its heartbeat, its ``finish`` and its ``require_current`` all refuse.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import Completed, ComparisonWorkRepository
from auditmanager.shared.errors import DomainError, ErrorCode


def _reclaim(queue, sessions, **options) -> int:  # type: ignore[no-untyped-def]
    with sessions() as session:
        recovered = queue.repository.reclaim_expired(session, **options)
        session.commit()
    return recovered


def test_an_expired_lease_is_reclaimed_the_item_returns_to_the_queue_and_the_next_claim_is_a_new_attempt(
    queue, sessions, make_worker
) -> None:
    work_id = queue.enqueue()
    dead = queue.claim(make_worker())
    queue.expire_lease(dead.attempt_id)
    assert _reclaim(queue, sessions) == 1
    row = queue.work(work_id)
    assert (row["state"], row["attempt_count"], row["delayed"]) == ("queued", 1, False)
    assert [(a["state"], a["failure_reason"]) for a in queue.attempts(work_id)] == [("lost", "lease_expired")]
    alive = queue.claim(make_worker())
    assert (alive.work_id, alive.attempt_no) == (work_id, 2)
    assert alive.attempt_id != dead.attempt_id
    assert alive.authority.execution_token != dead.authority.execution_token


def test_a_live_lease_is_not_reclaimed(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    assert _reclaim(queue, sessions) == 0
    assert queue.work(work_id)["state"] == "running"
    assert queue.attempts(work_id)[0]["state"] == "running"
    with sessions() as session:
        item.require_current(session)
        session.rollback()


def test_a_lease_that_really_runs_out_is_reclaimed(sessions, project, kind_name, worker_id) -> None:
    short = ComparisonWorkRepository(lease_seconds=0.4)
    with sessions() as session:
        short.enqueue(session, project_uid=project, module="versions", kind=kind_name)
        session.commit()
    with sessions() as session:
        item = short.claim(session, worker_id=worker_id, modules=frozenset({"versions"}), kinds=frozenset({kind_name}))
        session.commit()
    assert item is not None
    with sessions() as session:
        assert short.heartbeat(session, item.authority) is True, "within its lease the holder can extend it"
        session.commit()
    time.sleep(0.7)
    with sessions() as session:
        assert short.reclaim_expired(session) == 1
        session.commit()


def test_the_holder_that_lost_its_lease_is_fenced_everywhere(queue, sessions, make_worker) -> None:
    work_id = queue.enqueue()
    old = queue.claim(make_worker())
    queue.expire_lease(old.attempt_id)
    _reclaim(queue, sessions)
    new = queue.claim(make_worker())
    with sessions() as session:
        assert queue.repository.heartbeat(session, old.authority) is False
        session.rollback()
    for call in (lambda s: old.require_current(s), lambda s: queue.repository.finish(s, old.authority, Completed())):
        with sessions() as session, pytest.raises(DomainError) as refused:
            call(session)
        assert refused.value.code is ErrorCode.STALE_ATTEMPT
    assert queue.work(work_id)["state"] == "running", "the fenced holder wrote nothing"
    with sessions() as session:
        assert queue.repository.finish(session, new.authority, Completed()) == "succeeded"
        session.commit()
    assert [a["state"] for a in queue.attempts(work_id)] == ["lost", "succeeded"]


def test_an_item_whose_attempt_budget_is_spent_fails_instead_of_returning_to_the_queue(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue(max_attempts=2)
    for _ in range(2):
        item = queue.claim(worker_id)
        queue.expire_lease(item.attempt_id)
        assert _reclaim(queue, sessions) == 1
    row = queue.work(work_id)
    assert (row["state"], row["failure_reason"], row["attempt_count"]) == ("failed", "attempt_budget_exhausted", 2)
    assert queue.claim(worker_id) is None


def test_a_cancel_requested_before_the_holder_died_cancels_instead_of_requeueing(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as session:
        queue.repository.cancel(session, work_id)
        session.commit()
    queue.expire_lease(item.attempt_id)
    _reclaim(queue, sessions)
    assert queue.work(work_id)["state"] == "cancelled"
    assert queue.attempts(work_id)[0]["state"] == "lost"


def test_an_attempt_a_settler_calls_ambiguous_ends_the_item_spend_unknown_and_an_explicit_retry_clears_it(
    queue, sessions, worker_id
) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    queue.expire_lease(item.attempt_id)
    asked: list[str] = []

    def settle(session, attempt_id: str) -> bool:  # type: ignore[no-untyped-def]
        asked.append(attempt_id)
        return True

    assert _reclaim(queue, sessions, spend_settlers=(settle,)) == 1
    assert asked == [item.attempt_id]
    assert queue.work(work_id)["state"] == "spend_unknown"
    assert queue.claim(worker_id) is None, "a possibly-spent item is never re-sent by itself"
    with sessions() as session:
        assert queue.repository.retry_spend_unknown(session, work_id) == "queued"
        session.commit()
    assert queue.claim(worker_id).attempt_no == 2


def test_a_settler_that_finds_nothing_ambiguous_leaves_the_item_to_be_requeued(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    queue.expire_lease(item.attempt_id)
    _reclaim(queue, sessions, spend_settlers=(lambda session, attempt_id: False,))
    assert queue.work(work_id)["state"] == "queued"


def test_a_live_lease_never_reaches_the_settlers(queue, sessions, worker_id) -> None:
    queue.enqueue()
    queue.claim(worker_id)
    asked: list[str] = []
    _reclaim(queue, sessions, spend_settlers=(lambda session, attempt_id: asked.append(attempt_id) or True,))
    assert asked == []


def test_the_watchdog_can_fence_its_own_attempt_before_the_lease_runs_out(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    assert _reclaim(queue, sessions) == 0
    assert _reclaim(queue, sessions, force_attempt_id=item.attempt_id, reason="item_watchdog") == 1
    assert queue.attempts(work_id)[0]["failure_reason"] == "item_watchdog"
    assert queue.work(work_id)["state"] == "queued"
    with sessions() as session, pytest.raises(DomainError):
        item.require_current(session)


def test_a_reclaim_reason_is_a_code(queue, sessions) -> None:
    with sessions() as session, pytest.raises(ValueError):
        queue.repository.reclaim_expired(session, reason="Not a code")
    with sessions() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
