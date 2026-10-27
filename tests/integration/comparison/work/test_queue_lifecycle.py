"""The lifecycle of one comparison work item against real PostgreSQL (`CMP-WORK-01`, ADR-0025 decision 4).

Enqueue with its live dedupe key, the claim and its order, the lease and the token, the three typed
outcomes, the retry budget, the fence that keeps a lost holder from ending or publishing anything.
Every check reads the rows back with the test's own SQL, not through the repository under test.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.comparison.public import (
    CANCEL_REQUESTED,
    Completed,
    ComparisonWorkRepository,
    Failed,
    Yielded,
)
from auditmanager.shared.errors import DomainError, ErrorCode


def test_an_enqueued_item_waits_in_the_queue_with_its_declared_shape(queue, sessions) -> None:
    work_id = queue.enqueue(payload={"page": 3}, priority=7, max_attempts=5)
    row = queue.work(work_id)
    assert (row["state"], row["attempt_count"], row["max_attempts"], row["terminal"]) == ("queued", 0, 5, False)
    with sessions() as session:
        record = queue.repository.get(session, work_id)
    assert record is not None
    assert (record.kind, record.module, record.priority, dict(record.payload)) == (
        queue.kind, "versions", 7, {"page": 3})


def test_a_live_dedupe_key_enqueues_the_work_once_and_frees_the_key_when_it_ends(queue, sessions, worker_id) -> None:
    first = queue.enqueue(dedupe_key="page:1")
    with sessions() as session:
        again = queue.repository.enqueue(
            session, project_uid=queue.project_uid, module="versions", kind=queue.kind, dedupe_key="page:1")
        session.commit()
    assert (again.work_id, again.created) == (first, False)
    with sessions() as session:
        assert queue.repository.cancel(session, first) == "cancelled"
        session.commit()
    second = queue.enqueue(dedupe_key="page:1")
    assert second != first, "a key is unique only among live items"


@pytest.mark.parametrize(("options", "field"), [
    ({"module": "nope"}, "module"), ({"kind": "Bad Kind"}, "kind"), ({"priority": 101}, "priority"),
    ({"max_attempts": 0}, "max_attempts"), ({"delay_seconds": -1.0}, "delay_seconds"),
    ({"dedupe_key": ""}, "dedupe_key"),
])
def test_an_enqueue_the_column_would_refuse_is_refused_in_the_vocabulary_of_the_context(
    queue, sessions, options, field
) -> None:
    arguments = {"project_uid": queue.project_uid, "module": "versions", "kind": queue.kind, **options}
    with sessions() as session, pytest.raises(DomainError) as refused:
        queue.repository.enqueue(session, **arguments)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert refused.value.detail_fields["field"] == field


def test_the_claim_takes_the_strongest_item_first_then_the_oldest(queue, worker_id) -> None:
    low = queue.enqueue(priority=0)
    high = queue.enqueue(priority=50)
    low_later = queue.enqueue(priority=0)
    order = [queue.claim(worker_id).work_id for _ in range(3)]
    assert order == [high, low, low_later]
    assert queue.claim(worker_id) is None


def test_the_claim_leaves_an_item_that_is_not_due_a_cancelled_one_and_another_module_or_kind(
    queue, sessions, worker_id
) -> None:
    delayed = queue.enqueue(delay_seconds=3600.0)
    other_module = queue.enqueue(module="stages")
    assert queue.claim(worker_id) is None, "not due, and the module is not asked for"
    assert queue.claim(worker_id, modules=("stages",)).work_id == other_module
    queue.make_due(delayed)
    with sessions() as session:
        assert queue.repository.claim(
            session, worker_id=worker_id, modules=frozenset({"versions"}), kinds=frozenset({"some_other_kind"}),
        ) is None, "a kind that was not asked for is never claimed"
        session.rollback()
    assert queue.claim(worker_id).work_id == delayed


def test_a_claim_leases_the_item_to_the_worker_and_keeps_the_token_out_of_every_repr(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue(payload={"pair": ["a", "b"]})
    item = queue.claim(worker_id)
    assert (item.work_id, item.attempt_no, item.kind, item.module, dict(item.payload)) == (
        work_id, 1, queue.kind, "versions", {"pair": ["a", "b"]})
    row = queue.work(work_id)
    assert (row["state"], row["attempt_count"], row["current_work_attempt_id"]) == ("running", 1, item.attempt_id)
    (attempt,) = queue.attempts(work_id)
    assert (attempt["state"], attempt["worker_id"], attempt["has_lease"], attempt["lease_current"]) == (
        "running", worker_id, True, True)
    with sessions() as session:
        token = session.execute(text(
            "SELECT execution_token FROM comparison_work_attempt WHERE comparison_work_attempt_id = :a"
        ), {"a": item.attempt_id}).scalar_one()
    assert item.authority.execution_token == token
    for shown in (repr(item), repr(item.authority), str(item.authority)):
        assert token not in shown, "the execution token is secret-class and never formatted"


def test_a_completed_item_succeeds_and_cannot_be_ended_again(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as session:
        assert queue.repository.finish(session, item.authority, Completed()) == "succeeded"
        session.commit()
    assert (queue.work(work_id)["state"], queue.work(work_id)["terminal"]) == ("succeeded", True)
    assert queue.attempts(work_id)[0]["state"] == "succeeded"
    with sessions() as session, pytest.raises(DomainError) as refused:
        queue.repository.finish(session, item.authority, Completed())
    assert refused.value.code is ErrorCode.STALE_ATTEMPT


def test_a_failure_without_retry_ends_the_item_with_its_reason(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as session:
        assert queue.repository.finish(session, item.authority, Failed("page_unreadable")) == "failed"
        session.commit()
    row = queue.work(work_id)
    assert (row["state"], row["failure_reason"]) == ("failed", "page_unreadable")
    assert queue.attempts(work_id)[0]["failure_reason"] == "page_unreadable"


def test_a_retryable_failure_waits_out_a_backoff_and_ends_when_the_budget_is_spent(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue(max_attempts=2)
    first = queue.claim(worker_id)
    with sessions() as session:
        assert queue.repository.finish(session, first.authority, Failed("busy", retry=True)) == "queued"
        session.commit()
    row = queue.work(work_id)
    assert (row["state"], row["attempt_count"], row["delayed"]) == ("queued", 1, True)
    assert queue.claim(worker_id) is None, "the backoff keeps it out of the claim"
    queue.make_due(work_id)
    second = queue.claim(worker_id)
    assert second.attempt_no == 2
    with sessions() as session:
        assert queue.repository.finish(session, second.authority, Failed("busy", retry=True)) == "failed"
        session.commit()
    row = queue.work(work_id)
    assert (row["state"], row["failure_reason"], row["attempt_count"]) == ("failed", "busy", 2)
    assert [a["state"] for a in queue.attempts(work_id)] == ["failed", "failed"]


def test_a_yield_returns_the_item_to_the_queue_and_spends_none_of_the_budget(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue(max_attempts=1)
    for turn in range(1, 4):
        item = queue.claim(worker_id)
        assert item is not None and item.attempt_no == turn
        with sessions() as session:
            assert queue.repository.finish(session, item.authority, Yielded(delay_seconds=0.0)) == "queued"
            session.commit()
        row = queue.work(work_id)
        assert (row["state"], row["attempt_count"]) == ("queued", 0)
    assert [a["state"] for a in queue.attempts(work_id)] == ["superseded"] * 3
    last = queue.claim(worker_id)
    with sessions() as session:
        queue.repository.finish(session, last.authority, Completed())
        session.commit()
    assert queue.work(work_id)["state"] == "succeeded"


def test_a_yield_with_a_delay_is_not_claimable_until_it_is_due(queue, sessions, worker_id) -> None:
    queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as session:
        queue.repository.finish(session, item.authority, Yielded(delay_seconds=600.0))
        session.commit()
    assert queue.claim(worker_id) is None


def test_a_cancel_requested_while_the_item_runs_wins_over_a_yield_and_a_failure(queue, sessions, worker_id) -> None:
    for outcome in (Yielded(), Failed("busy", retry=True)):
        work_id = queue.enqueue()
        item = queue.claim(worker_id)
        with sessions() as session:
            assert queue.repository.cancel(session, work_id) == CANCEL_REQUESTED
            session.commit()
        with sessions() as session:
            assert queue.repository.finish(session, item.authority, outcome) == "cancelled"
            session.commit()
        assert queue.work(work_id)["state"] == "cancelled"
        assert queue.attempts(work_id)[-1]["state"] == "cancelled"


def test_an_item_that_completed_ends_succeeded_even_if_a_cancel_arrived_late(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as session:
        queue.repository.cancel(session, work_id)
        session.commit()
    with sessions() as session:
        assert queue.repository.finish(session, item.authority, Completed()) == "succeeded"
        session.commit()


def test_a_token_that_is_not_the_attempts_is_refused_and_nothing_is_written(queue, sessions, worker_id) -> None:
    from dataclasses import replace

    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    forged = replace(item.authority, execution_token="forged-token")
    with sessions() as session, pytest.raises(DomainError) as refused:
        queue.repository.require_current(session, forged)
    assert refused.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
    with sessions() as session, pytest.raises(DomainError) as early:
        queue.repository.check_current(session, forged)
    assert early.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
    assert queue.work(work_id)["state"] == "running"


def test_an_item_can_check_and_require_that_it_still_holds_its_lease(queue, sessions, worker_id) -> None:
    queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as session:
        item.check_current(session)
        item.require_current(session)
        session.rollback()
    queue.expire_lease(item.attempt_id)
    for call in ("check_current", "require_current"):
        with sessions() as session, pytest.raises(DomainError) as refused:
            getattr(item, call)(session)
        assert refused.value.code is ErrorCode.STALE_ATTEMPT


def test_a_heartbeat_extends_a_live_lease_and_is_refused_for_an_expired_one(queue, sessions, worker_id) -> None:
    queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as session:
        before = session.execute(text(
            "SELECT lease_expires_at FROM comparison_work_attempt WHERE comparison_work_attempt_id = :a"
        ), {"a": item.attempt_id}).scalar_one()
        assert queue.repository.heartbeat(session, item.authority) is True
        after = session.execute(text(
            "SELECT lease_expires_at FROM comparison_work_attempt WHERE comparison_work_attempt_id = :a"
        ), {"a": item.attempt_id}).scalar_one()
        session.commit()
    assert after > before
    queue.expire_lease(item.attempt_id)
    with sessions() as session:
        assert queue.repository.heartbeat(session, item.authority) is False, "an expired lease is never revived"
        session.rollback()


def test_the_database_refuses_a_state_move_the_declared_edges_do_not_allow(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    with sessions() as session, pytest.raises(DBAPIError) as refused:
        session.execute(text(
            "UPDATE comparison_work SET state = 'succeeded', terminal_at = clock_timestamp() "
            "WHERE comparison_work_id = :w"), {"w": work_id})
    assert "state_transition_not_allowed" in str(refused.value)


def test_a_lease_is_positive(sessions) -> None:
    with pytest.raises(ValueError):
        ComparisonWorkRepository(lease_seconds=0)


def test_the_publishing_transaction_keeps_the_item_locked_so_a_project_erase_cannot_get_past_it(
    queue, sessions, worker_id, project
) -> None:
    """ADR-0025 decision 7: between ``require_current`` and the commit the project cannot be removed.
    An erase must delete the item's row first (``ON DELETE RESTRICT`` keeps the project while any row
    exists), and that row is locked by the publishing transaction; the project itself is refused
    outright while the item exists."""
    work_id = queue.enqueue()
    item = queue.claim(worker_id)
    with sessions() as holder, sessions() as erase:
        item.require_current(holder)
        erase.execute(text("SET LOCAL lock_timeout = '300ms'"))
        with pytest.raises(DBAPIError) as blocked:
            erase.execute(text("DELETE FROM comparison_work WHERE comparison_work_id = :w"), {"w": work_id})
        assert "lock timeout" in str(blocked.value).lower() or "could not obtain lock" in str(blocked.value).lower()
        erase.rollback()
        erase.execute(text("SET LOCAL lock_timeout = '300ms'"))  # the foreign-key check waits for the held row too
        with pytest.raises(DBAPIError) as restricted:
            erase.execute(text("DELETE FROM project WHERE project_uid = :p"), {"p": project})
        assert any(word in str(restricted.value).lower() for word in ("foreign key", "violates", "lock timeout", "could not obtain lock"))
        erase.rollback()
        holder.rollback()
