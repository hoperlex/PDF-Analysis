"""`EXEC2-PULL-01` (ADR-0026 decision 3): one agent with ``concurrency = 3``, claims serialised per token,
and a task redelivered only to the agent instance that claimed it.

Real PostgreSQL (the suite's ``engine`` and ``session``, the first from the harness the other executor
suites bind) and the served application. **Not run in EXEC-2 (`R-149d`).** The suite has no database marker:
a test here needs PostgreSQL because it takes ``engine``, ``session`` or ``surface``; the unit twins that
need none are ``tests/unit/executors/test_runner_claim_*.py``.

Two kinds of test:

* the **HTTP** tests drive the runner operations through ``build_router(runner=RunnerAdapter(...))`` on the
  rolled-back ``session``, exactly as ``test_runner_channel.py`` does, to show what a runner is told;
* the **race** tests use committed rows and real connections (threads, one ``Session`` per poll) to show
  what the lock on the token's row does. They write a connection, a revision, tokens, a live Attempt and tasks,
  and remove the tasks and tokens afterwards (a revision and a run are immutable and stay, as in
  ``tests/integration/jobs/connection_limit_support.py``).

The numbering of the acceptance list this file answers (B1 section 6 items 7 to 12 and 14, B2 section 11
item 11) is the design documents', which are not in the repository; each test says in words what it shows.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.executors.public import RunnerPrincipal, claim_task
from auditmanager.executors.runner_repository import RunnerRepository
from auditmanager.shared.identity import (
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ExecutorRunnerTokenId,
)
from tests.integration.executors.test_runner_channel import (  # noqa: F401 - the fixtures
    GOOD,
    MODEL,
    PULL_SETTINGS,
    SCHEMA,
    adapter_for,
    issue,
    live_attempt,
    make_connection,
    runner_call,
    surface,
    task_row,
)

A, B = "agent-instance-aaaa", "agent-instance-bbbb"
ACTOR = f"usr_{'0' * 26}"
PAYLOAD = {"system": "s", "user_text": "u", "output_schema": SCHEMA}
LIMIT_THREE = {**PULL_SETTINGS, "max_claimed_tasks": 3}


# -- the HTTP side ---------------------------------------------------------------------------------------


def claim_as(surface: Any, token: str, instance: str | None = None, **extra: Any):
    body: dict[str, Any] = {"wait_seconds": 0, **extra}
    if instance is not None:
        body["runner_instance_id"] = instance
    return runner_call(surface, token, "/runner/tasks/claim", body)


def write_tasks(session: Session, connection_id: str, count: int) -> list[str]:
    """``count`` open tasks of the connection, oldest first, on one live Attempt."""
    adapter = adapter_for(session, connection_id, live_attempt(session))
    return [adapter._write_task(PAYLOAD, 600).task_id for _ in range(count)]


def answer(surface: Any, token: str, task_id: str):
    return runner_call(surface, token, f"/runner/tasks/{task_id}/answer", {"output_text": GOOD, "model": MODEL})


def lapse(session: Session, task_id: str) -> None:
    session.execute(text("UPDATE executor_task SET claim_expires_at = clock_timestamp() - interval '1 second' "
                         "WHERE task_id = :id"), {"id": task_id})


def test_one_agent_with_a_limit_of_three_takes_three_tasks_and_answers_each_exactly_once(session, surface) -> None:
    """The outcome of the task: one agent, concurrency 3, a matching server limit and open tasks. Each
    task is claimed once (``claim_count`` 1), answered once, and the fourth waits for a free unit."""
    connection_id = make_connection(surface, settings=LIMIT_THREE)
    token, _ = issue(surface, connection_id)
    ids = write_tasks(session, connection_id, 4)
    taken = []
    for _ in range(3):
        claimed = claim_as(surface, token, A)
        assert claimed.status == 200, claimed.body
        taken.append(claimed.json()["task_id"])
    assert taken == ids[:3], "three different tasks, the oldest first"
    assert claim_as(surface, token, A).status == 204, "the limit is three"
    for task_id in taken:
        row = task_row(session, task_id)
        assert (row["state"], row["claim_count"], row["claimed_by_instance_id"]) == ("claimed", 1, A)
    assert task_row(session, ids[3])["state"] == "open"

    for task_id in taken:
        done = answer(surface, token, task_id)
        assert done.status == 200 and done.json() == {"task_id": task_id, "state": "answered"}
    assert answer(surface, token, taken[0]).json()["state"] == "answered", "the same answer again is not a second answer"
    rows = [task_row(session, task_id) for task_id in taken]
    assert [(r["state"], r["claim_count"]) for r in rows] == [("answered", 1)] * 3

    fourth = claim_as(surface, token, A)
    assert fourth.status == 200 and fourth.json()["task_id"] == ids[3], "an answered task frees its unit"


def test_at_a_limit_of_one_a_held_task_goes_back_only_to_the_instance_that_claimed_it(session, surface) -> None:
    connection_id = make_connection(surface)  # max_claimed_tasks 1
    token, _ = issue(surface, connection_id)
    first, second = write_tasks(session, connection_id, 2)
    assert claim_as(surface, token, A).json()["task_id"] == first
    again = claim_as(surface, token, A)
    assert again.status == 200 and again.json()["task_id"] == first, "a lost response is recovered by the same instance"
    assert task_row(session, first)["claim_count"] == 1, "a redelivery is not a second claim"

    other = claim_as(surface, token, B)
    assert other.status == 204, "another instance of the same token is not handed the held task, nor a second one"
    held = task_row(session, first)
    assert (held["state"], held["claimed_by_instance_id"]) == ("claimed", A)
    assert task_row(session, second)["state"] == "open"
    assert claim_as(surface, token, A).json()["task_id"] == first, "and the holder still has it"


def test_a_claim_that_names_no_instance_is_redelivered_as_before_and_the_recorded_instance_is_cleared(
    session, surface,
) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    (task,) = write_tasks(session, connection_id, 1)
    assert claim_as(surface, token, A).json()["task_id"] == task
    handed = claim_as(surface, token)  # an agent or bridge built before the field
    assert handed.status == 200 and handed.json()["task_id"] == task, "today's behaviour: any caller of the token"
    row = task_row(session, task)
    assert row["claimed_by_instance_id"] is None and row["claim_count"] == 1
    assert claim_as(surface, token, A).status == 204, "the task is no longer A's: the latest redelivery owns it"
    assert claim_as(surface, token).json()["task_id"] == task


def test_an_old_sequential_agent_that_sends_no_instance_works_unchanged(session, surface) -> None:
    """The pull regression: an agent with concurrency 1 (or a Claude Code session behind the bridge) claims,
    may claim again after a lost response and is handed the same task, answers, and claims the next. Nothing
    it sends or is told differs from before, and no instance is ever recorded."""
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    first, second = write_tasks(session, connection_id, 2)
    for expected in (first, second):
        got = claim_as(surface, token, max_images=1)  # the old wire, with and without max_images
        assert got.status == 200 and got.json()["task_id"] == expected
        assert claim_as(surface, token).json()["task_id"] == expected, "redelivered after a lost response"
        row = task_row(session, expected)
        assert (row["claimed_by_instance_id"], row["claim_count"]) == (None, 1)
        assert answer(surface, token, expected).status == 200
    assert claim_as(surface, token).status == 204

    wide = make_connection(surface, settings={**PULL_SETTINGS, "max_claimed_tasks": 2})
    wide_token, _ = issue(surface, wide)
    one, two, three = write_tasks(session, wide, 3)
    assert [claim_as(surface, wide_token).json()["task_id"] for _ in range(2)] == [one, two]
    assert claim_as(surface, wide_token).status == 204, "above a limit of one nothing is redelivered, as before"
    assert task_row(session, three)["state"] == "open"
    assert task_row(session, one)["claimed_by_instance_id"] is None


def test_a_restarted_agent_does_not_receive_its_predecessors_claim_until_the_lease_lapses(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    (task,) = write_tasks(session, connection_id, 1)
    assert claim_as(surface, token, A).json()["task_id"] == task
    assert claim_as(surface, token, B).status == 204, "a new instance is not handed the old instance's claim"
    assert task_row(session, task)["claimed_by_instance_id"] == A

    lapse(session, task)
    taken = claim_as(surface, token, B)
    assert taken.status == 200 and taken.json()["task_id"] == task, "the lease lapsed and the task follows the re-open rule"
    row = task_row(session, task)
    assert (row["claimed_by_instance_id"], row["claim_count"]) == (B, 2)
    assert claim_as(surface, token, A).status == 204, "the old instance, if it were alive, is not handed it back"


def test_a_lapsed_claim_returns_the_task_to_open_with_no_token_and_no_instance(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    (task,) = write_tasks(session, connection_id, 1)
    assert claim_as(surface, token, A).status == 200
    lapse(session, task)
    RunnerRepository().sweep(session, connection_id)
    row = task_row(session, task)
    assert (row["state"], row["claimed_by_token_id"], row["claimed_by_instance_id"], row["claim_expires_at"]) == (
        "open", None, None, None)


def test_the_database_refuses_an_instance_that_outlives_its_token(session, surface) -> None:
    """Why the sweep clears the instance in the same statement: with the token gone a recorded instance
    breaks ``ck_executor_task_instance_with_token``. The sweep of the code before this task, which did not
    clear it, would be refused here."""
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    (task,) = write_tasks(session, connection_id, 1)
    assert claim_as(surface, token, A).status == 200
    lapse(session, task)
    with pytest.raises(DBAPIError) as refused:
        with session.begin_nested():
            session.execute(text("UPDATE executor_task SET state = 'open', claimed_by_token_id = NULL, "
                                 "claim_expires_at = NULL WHERE task_id = :id"), {"id": task})
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"
    assert "ck_executor_task_instance_with_token" in str(refused.value)
    assert task_row(session, task)["state"] == "claimed", "the refused statement changed nothing"


def test_a_stale_extend_or_answer_after_the_lease_moved_is_claim_lost(session, surface) -> None:
    connection_id = make_connection(surface)
    first, _ = issue(surface, connection_id)
    second, _ = issue(surface, connection_id)
    (task,) = write_tasks(session, connection_id, 1)
    assert claim_as(surface, first, A).json()["task_id"] == task
    lapse(session, task)
    assert claim_as(surface, second, B).json()["task_id"] == task
    stale = answer(surface, first, task)
    assert stale.status == 409 and stale.json()["details"]["conflict_reason"] == "claim_lost"
    assert runner_call(surface, first, f"/runner/tasks/{task}/extend").status == 409
    assert task_row(session, task)["claimed_by_instance_id"] == B
    assert answer(surface, second, task).status == 200


def test_a_cancelled_tasks_late_answer_is_refused_and_its_instance_may_stay(session, surface) -> None:
    connection_id = make_connection(surface)
    token, _ = issue(surface, connection_id)
    (task,) = write_tasks(session, connection_id, 1)
    assert claim_as(surface, token, A).status == 200
    session.execute(text("UPDATE executor_task SET state = 'cancelled', terminal_at = clock_timestamp() "
                         "WHERE task_id = :id"), {"id": task})
    late = answer(surface, token, task)
    assert late.status == 409 and late.json()["details"]["conflict_reason"] == "task_terminal"
    assert runner_call(surface, token, f"/runner/tasks/{task}/extend").status == 409
    row = task_row(session, task)
    assert (row["state"], row["answer_text"]) == ("cancelled", None)


# -- the race: committed rows, real connections ---------------------------------------------------------


@dataclass(frozen=True)
class Committed:
    connection_id: str
    token_ids: tuple[str, ...]
    task_ids: tuple[str, ...]


@pytest.fixture
def sessions(engine: Any) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _commit_stand(sessions: sessionmaker[Session], *, limit: int, tokens: int, tasks: int) -> Committed:
    connection_id, revision_id = str(ExecutorConnectionId.new()), str(ExecutorConnectionRevisionId.new())
    with sessions() as s:
        s.execute(text("INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
                       "VALUES (:c, 'pull', 'concurrency', :a)"), {"c": connection_id, "a": ACTOR})
        s.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, "
            "pin_id, gateway_model, billing, allow_client_documents, timeout_seconds, pull_client, "
            "answer_deadline_seconds, max_claimed_tasks) VALUES (:r, :c, 1, :a, :m, :m, 'not_metered', false, "
            "60, 'agent', 600, :limit)"), {"r": revision_id, "c": connection_id, "a": ACTOR, "m": MODEL,
                                          "limit": limit})
        token_ids = []
        for _ in range(tokens):
            token_id = str(ExecutorRunnerTokenId.new())
            s.execute(text(
                "INSERT INTO executor_runner_token (token_id, connection_id, token_prefix, token_hash, "
                "created_by, expires_at) VALUES (:t, :c, :p, :h, :a, clock_timestamp() + interval '1 day')"),
                {"t": token_id, "c": connection_id, "p": "amr_" + token_id[-8:].lower(), "h": b"h" * 32,
                 "a": ACTOR})
            token_ids.append(token_id)
        attempt = live_attempt(s)
        store = RunnerRepository()
        task_ids = [store.insert_task(
            s, connection_id=connection_id, revision_id=revision_id, origin="run_call",
            run_id=attempt["run_id"], attempt_id=attempt["attempt_id"], model_call_id=None, probe_id=None,
            expected_model=MODEL, payload=PAYLOAD, deadline_seconds=600).task_id for _ in range(tasks)]
        s.commit()
    return Committed(connection_id, tuple(token_ids), tuple(task_ids))


@pytest.fixture
def committed(sessions: sessionmaker[Session]):
    made: list[str] = []

    def make(*, limit: int, tokens: int = 1, tasks: int) -> Committed:
        stand = _commit_stand(sessions, limit=limit, tokens=tokens, tasks=tasks)
        made.append(stand.connection_id)
        return stand

    yield make
    for connection_id in made:
        with sessions() as s:
            s.execute(text("DELETE FROM executor_task WHERE connection_id = :c"), {"c": connection_id})
            s.execute(text("DELETE FROM executor_runner_token WHERE connection_id = :c"), {"c": connection_id})
            s.commit()


def _poll(sessions: sessionmaker[Session], stand: Committed, token_id: str, instance: str | None):
    """One claim of the shipped ``claim_task``, each poll in a transaction (and a connection) of its own."""
    principal = RunnerPrincipal(token_id=token_id, connection_id=stand.connection_id)
    return claim_task(sessions, principal, wait_seconds=0, runner_instance_id=instance)  # type: ignore[arg-type]


def _claimed(sessions: sessionmaker[Session], stand: Committed) -> list[tuple[str, str | None]]:
    with sessions() as s:
        return [(r[0], r[1]) for r in s.execute(text(
            "SELECT task_id, claimed_by_instance_id FROM executor_task "
            "WHERE connection_id = :c AND state = 'claimed' ORDER BY task_id"), {"c": stand.connection_id})]


def _reopen(sessions: sessionmaker[Session], stand: Committed) -> None:
    with sessions() as s:
        s.execute(text("UPDATE executor_task SET state = 'open', claimed_by_token_id = NULL, "
                       "claimed_by_instance_id = NULL, claim_expires_at = NULL "
                       "WHERE connection_id = :c AND state = 'claimed'"), {"c": stand.connection_id})
        s.commit()


def _race(sessions: sessionmaker[Session], stand: Committed, token_id: str, instances: list[str],
          polls: int = 1) -> dict[str, list[str]]:
    start = threading.Barrier(len(instances))
    got: dict[str, list[str]] = {instance: [] for instance in instances}
    errors: list[BaseException] = []

    def run(instance: str) -> None:
        try:
            start.wait(timeout=30)
            for _ in range(polls):
                task = _poll(sessions, stand, token_id, instance)
                if task is not None:
                    got[instance].append(task.task_id)
        except BaseException as error:  # noqa: BLE001 - reported by the test thread
            errors.append(error)

    threads = [threading.Thread(target=run, args=(instance,)) for instance in instances]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    assert not errors, errors
    assert not any(thread.is_alive() for thread in threads), "a claim never finished"
    return got


def test_two_processes_with_one_token_never_pass_a_limit_of_one(sessions, committed) -> None:
    """Two claims of one token at the same moment, twenty times. Without the lock on the token's row both
    count no held claim and both claim; with it exactly one claim succeeds and the other is told nothing."""
    stand = committed(limit=1, tasks=2)
    for round_ in range(20):
        got = _race(sessions, stand, stand.token_ids[0], [A, B])
        taken = [task for tasks in got.values() for task in tasks]
        held = _claimed(sessions, stand)
        assert len(taken) == 1 and len(held) == 1, (round_, got, held)
        assert held[0][0] == taken[0]
        _reopen(sessions, stand)


def test_four_processes_with_one_token_never_pass_a_limit_of_three(sessions, committed) -> None:
    stand = committed(limit=3, tasks=6)
    names = [A, B, "agent-instance-cccc", "agent-instance-dddd"]
    for round_ in range(10):
        got = _race(sessions, stand, stand.token_ids[0], names, polls=3)
        taken = [task for tasks in got.values() for task in tasks]
        held = _claimed(sessions, stand)
        assert len(taken) == 3 and len(set(taken)) == 3, (round_, got)
        assert sorted(task for task, _ in held) == sorted(taken), (round_, held)
        _reopen(sessions, stand)


def test_two_processes_with_one_token_never_work_on_the_same_task(sessions, committed) -> None:
    """At a limit of one the instance that holds the claim is handed it again however often it asks,
    and the other instance of the token is handed nothing, at any interleaving."""
    stand = committed(limit=1, tasks=2)
    token = stand.token_ids[0]
    first = _poll(sessions, stand, token, A)
    assert first is not None and first.task_id == stand.task_ids[0]
    got = _race(sessions, stand, token, [A, B], polls=15)
    assert got[A] == [first.task_id] * 15, "the holder is redelivered its task every time"
    assert got[B] == [], "the other instance is never handed it"
    assert _claimed(sessions, stand) == [(first.task_id, A)], "and no second task was taken"


def test_a_claim_waits_for_its_tokens_row_lock_and_a_claim_of_another_token_does_not(sessions, committed) -> None:
    """The lock is on the token's row: a claim of that token queues behind whoever holds the row, a claim
    of another token of the same connection goes straight through. Failure mode of a claim that does not lock:
    the first claim below would finish while the row is held."""
    stand = committed(limit=3, tokens=2, tasks=3)
    locked, free = stand.token_ids
    holder = sessions()
    holder.execute(text("SELECT 1 FROM executor_runner_token WHERE token_id = :t FOR UPDATE"), {"t": locked})
    result: dict[str, Any] = {}
    blocked = threading.Thread(
        target=lambda: result.update(task=_poll(sessions, stand, locked, A)), daemon=True)
    try:
        blocked.start()
        other = _poll(sessions, stand, free, B)
        assert other is not None, "a claim of another token is not held up by the first token's row"
        blocked.join(1.0)
        assert blocked.is_alive() and "task" not in result, "the claim did not wait for the token's row"
    finally:
        holder.commit()
        holder.close()
    blocked.join(30)
    assert not blocked.is_alive() and result["task"] is not None
    assert result["task"].task_id != other.task_id
