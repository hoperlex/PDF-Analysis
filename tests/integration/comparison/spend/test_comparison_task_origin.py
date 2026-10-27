"""The ``comparison_call`` origin of an executor task in ``runner_repository`` (`CMP-SPEND-01`, ADR-0025 decision 4).

A task whose attempt is a comparison attempt is served only while that attempt is the live, current one of its
work item -- the rule a Run's task already has, with the comparison tables as the alternative: ``claim_next`` skips
it, ``live_claim_and_attempt`` says no, and ``sweep`` cancels it. A Run's task and a probe's are decided as they
were (``tests/integration/executors/test_runner_channel.py`` and the pull run path say so and are unmodified). The
tests write committed rows (the repository's statements are the code under test).

Mutations recorded in ``docs/program/CMP-SPEND-01.md``: the comparison branch missing from each of the three
statements.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import SPEND_SETTLERS
from auditmanager.executors.runner_repository import RunnerRepository
from auditmanager.shared.identity import ExecutorRunnerTokenId

REPOSITORY = RunnerRepository()
ACTOR = f"usr_{'0' * 26}"


def _token(sessions: Any, connection_id: str) -> str:
    with sessions() as session:
        token_id = str(ExecutorRunnerTokenId.new())
        session.execute(text(
            "INSERT INTO executor_runner_token (token_id, connection_id, token_prefix, token_hash, created_by, "
            "expires_at) VALUES (:t, :c, :p, :h, :a, clock_timestamp() + interval '1 day')"
        ), {"t": token_id, "c": connection_id, "p": "amr_" + token_id[-8:].lower(), "h": b"h" * 32, "a": ACTOR})
        session.commit()
    return token_id


def _task(sessions: Any, connection: tuple[str, str], attempt_id: str) -> str:
    with sessions() as session:
        task = REPOSITORY.insert_task(
            session, connection_id=connection[0], revision_id=connection[1], origin="comparison_call",
            run_id=None, attempt_id=None, model_call_id=None, probe_id=None,
            expected_model="anthropic/claude-opus-5", payload={"system": "S", "user_text": "U"},
            deadline_seconds=600, comparison_attempt_id=attempt_id,
        )
        session.commit()
    return task.task_id


def _state(sessions: Any, task_id: str) -> str:
    with sessions() as session:
        return str(session.execute(
            text("SELECT state FROM executor_task WHERE task_id = :t"), {"t": task_id}).scalar_one())


def _drop_tasks(sessions: Any, connection_id: str) -> None:
    with sessions() as session:
        session.execute(text("DELETE FROM executor_task WHERE connection_id = :c"), {"c": connection_id})
        session.execute(text("DELETE FROM executor_runner_token WHERE connection_id = :c"), {"c": connection_id})
        session.commit()


@pytest.fixture
def stand(sessions: Any, connection: tuple[str, str]) -> Any:
    token = _token(sessions, connection[0])
    yield connection, token
    _drop_tasks(sessions, connection[0])


def test_a_task_of_origin_comparison_call_carries_its_attempt_and_no_run(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    connection, _token_id = stand
    item = queue.claimed()
    with sessions() as session:
        task = REPOSITORY.insert_task(
            session, connection_id=connection[0], revision_id=connection[1], origin="comparison_call",
            run_id=None, attempt_id=None, model_call_id=None, probe_id=None, expected_model="m",
            payload={}, deadline_seconds=60, comparison_attempt_id=item.attempt_id)
        session.commit()
        assert (task.origin, task.run_id, task.attempt_id, task.model_call_id, task.probe_id) == (
            "comparison_call", None, None, None, None)
        assert task.comparison_attempt_id == item.attempt_id
        assert REPOSITORY.get_task(session, task.task_id).comparison_attempt_id == item.attempt_id  # type: ignore[union-attr]


def test_a_live_attempts_task_is_claimed_and_its_claim_is_live(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    connection, token = stand
    item = queue.claimed()
    task_id = _task(sessions, connection, item.attempt_id)
    with sessions() as session:
        claimed = REPOSITORY.claim_next(session, connection_id=connection[0], token_id=token, lease_seconds=30)
        session.commit()
        assert claimed is not None and claimed.task_id == task_id
        assert REPOSITORY.live_claim_and_attempt(session, task_id, token) is True


def test_the_task_of_an_attempt_the_queue_has_ended_is_never_claimed(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    connection, token = stand
    item = queue.claimed()
    task_id = _task(sessions, connection, item.attempt_id)
    queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS)           # the attempt is lost; no sweep has run yet
    with sessions() as session:
        assert REPOSITORY.claim_next(session, connection_id=connection[0], token_id=token, lease_seconds=30) is None
        session.rollback()
    assert _state(sessions, task_id) == "open", "claim_next skips it without having to sweep first"


def test_the_task_of_a_superseded_attempt_is_not_served_but_the_current_attempts_is(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    connection, token = stand
    first = queue.claimed()
    old_task = _task(sessions, connection, first.attempt_id)
    queue.expire_and_reclaim(first, settlers=())                       # back to the queue, attempt 1 lost
    queue.make_due(first.work_id)
    second = queue.reclaim_item()
    assert second is not None and second.attempt_no == 2
    new_task = _task(sessions, connection, second.attempt_id)
    with sessions() as session:
        claimed = REPOSITORY.claim_next(session, connection_id=connection[0], token_id=token, lease_seconds=30)
        session.commit()
    assert claimed is not None and claimed.task_id == new_task
    assert _state(sessions, old_task) == "open"


def test_a_task_whose_attempt_is_running_but_is_not_the_items_current_attempt_is_not_served(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    """The Run rule (``test_a_task_that_is_not_the_current_attempts_is_not_served``): the attempt must be the one the
    item names as current. A second attempt is written by hand here, because the queue never leaves two running."""
    from auditmanager.shared.identity import ComparisonWorkAttemptId

    connection, token = stand
    item = queue.claimed()
    task_id = _task(sessions, connection, item.attempt_id)
    with sessions() as session:
        newer = str(ComparisonWorkAttemptId.new())
        session.execute(text(
            "INSERT INTO comparison_work_attempt (comparison_work_attempt_id, comparison_work_id, attempt_no, "
            "execution_token) VALUES (:a, :w, 2, :t)"), {"a": newer, "w": item.work_id, "t": f"tok-{newer}"})
        session.execute(text(
            "UPDATE comparison_work SET current_work_attempt_id = :a WHERE comparison_work_id = :w"),
            {"a": newer, "w": item.work_id})
        session.commit()
        state = session.execute(text(
            "SELECT state FROM comparison_work_attempt WHERE comparison_work_attempt_id = :a"),
            {"a": item.attempt_id}).scalar_one()
    assert state == "running", "the first attempt is still running: only 'current' can say no"
    with sessions() as session:
        assert REPOSITORY.claim_next(session, connection_id=connection[0], token_id=token, lease_seconds=30) is None
        session.rollback()
    assert _state(sessions, task_id) == "open"


def test_a_claim_is_no_longer_live_once_its_attempt_has_ended(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    """The check a runner's image fetch makes before any egress (``live_claim_and_attempt``)."""
    connection, token = stand
    item = queue.claimed()
    task_id = _task(sessions, connection, item.attempt_id)
    with sessions() as session:
        assert REPOSITORY.claim_next(session, connection_id=connection[0], token_id=token, lease_seconds=300) is not None
        session.commit()
    queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS)
    with sessions() as session:
        assert REPOSITORY.live_claim_and_attempt(session, task_id, token) is False
        session.rollback()


def test_the_sweep_cancels_the_open_and_the_claimed_tasks_of_an_ended_attempt_and_only_those(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    connection, token = stand
    gone, alive = queue.claimed(), queue.claimed()
    open_task = _task(sessions, connection, gone.attempt_id)
    kept_task = _task(sessions, connection, alive.attempt_id)
    with sessions() as session:
        claimed = REPOSITORY.claim_next(session, connection_id=connection[0], token_id=token, lease_seconds=300)
        session.commit()
    assert claimed is not None
    held = claimed.task_id                                                 # the oldest task is claimed first
    queue.expire_and_reclaim(gone, settlers=SPEND_SETTLERS)
    with sessions() as session:
        REPOSITORY.sweep(session, connection[0])
        session.commit()
    assert _state(sessions, open_task) == "cancelled" and held == open_task
    assert _state(sessions, kept_task) == "open", "an attempt that still holds its item keeps its task"


def test_the_sweep_leaves_a_live_comparison_task_claimed(
    sessions: Any, queue: Any, stand: Any,
) -> None:
    connection, token = stand
    item = queue.claimed()
    task_id = _task(sessions, connection, item.attempt_id)
    with sessions() as session:
        REPOSITORY.claim_next(session, connection_id=connection[0], token_id=token, lease_seconds=300)
        REPOSITORY.sweep(session, connection[0])
        session.commit()
    assert _state(sessions, task_id) == "claimed"
