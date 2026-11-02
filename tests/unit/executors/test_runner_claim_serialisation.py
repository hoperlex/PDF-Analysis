"""`EXEC2-PULL-01` (ADR-0026 decision 3): the claims of one token run one after the other.

The count of a token's held claims and the claim that follows it were two statements with nothing
between them, so two claims of one token could both count below the limit and both claim. The claim now
takes the token's row ``FOR UPDATE`` as the first statement of its transaction.

What is proved here is the **order** of ``claim_task``'s steps and that the order is what keeps the limit,
over a model of the rows that behaves the way the lock does: a claim that locks waits for the claim that
holds the lock until that claim's transaction ends. The statements themselves (the lock on PostgreSQL, the
race between two real connections) are proved in ``tests/integration/executors/test_runner_concurrency.py``,
which needs a database and was not run in EXEC-2 (`R-149d`).

Each guard is shown able to fail: the model without the lock lets two claims past a limit of one.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.executors.runner import RunnerPrincipal, claim_task
from auditmanager.executors.runner_repository import ClaimedRow
from auditmanager.shared.errors import DomainError, ErrorCode

PRINCIPAL = RunnerPrincipal("ern_TOKEN", "exc_CONN")
A, B = "agent-instance-aaaa", "agent-instance-bbbb"


def _row(task_id: str) -> ClaimedRow:
    now = datetime.now(UTC)
    return ClaimedRow(
        task_id=task_id, claim_expires_at=now + timedelta(seconds=120),
        deadline_at=now + timedelta(seconds=600), expected_model="m",
        payload={"system": "s", "user_text": "u", "output_schema": {}})


class _Session:
    """What ``claim_task`` opens: its transaction ends at ``commit`` or when the block is left, and the
    row lock the token's claim took is released then, as PostgreSQL releases it."""

    def __init__(self, rows: _Rows) -> None:
        self._rows = rows

    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *exc: object) -> bool:
        self._rows.release(self)
        return False

    def commit(self) -> None:
        self._rows.release(self)


class _Executors:
    def __init__(self, limit: int | None) -> None:
        self._limit = limit

    def current_revisions(self, session: Any, connection_ids: Any) -> dict[str, Any]:
        return {connection_ids[0]: SimpleNamespace(settings=SimpleNamespace(max_claimed_tasks=self._limit))}


class _Rows:
    """One token's rows, in memory: the open tasks, the tasks it holds (with the instance that took each)
    and the token's row lock. ``serialise=False`` is the repository without ``lock_token``'s lock."""

    def __init__(
        self, open_tasks: list[str], *, serialise: bool = True, exists: bool = True, pause: float = 0.0,
        rendezvous: threading.Barrier | None = None,
    ) -> None:
        self.open = list(open_tasks)
        self.held: dict[str, str | None] = {}
        self.log: list[str] = []
        self._serialise, self._exists, self._pause, self._rendezvous = serialise, exists, pause, rendezvous
        self._data = threading.Lock()
        self._token_row = threading.Lock()
        self._holder: _Session | None = None

    # -- the token's row lock -------------------------------------------------------------
    def lock_token(self, session: _Session, token_id: str) -> bool:
        self.log.append("lock_token")
        if not self._exists:
            return False
        if self._serialise:
            self._token_row.acquire()
            self._holder = session
        return True

    def release(self, session: _Session) -> None:
        if self._holder is session:
            self._holder = None
            self._token_row.release()

    # -- the statements ---------------------------------------------------------------------
    def sweep(self, session: Any, connection_id: str) -> None:
        self.log.append("sweep")

    def clear_terminal_payloads(self, session: Any, **kwargs: Any) -> None:
        self.log.append("clear_terminal_payloads")

    def redeliver(self, session: Any, *, token_id: str, lease_seconds: int, max_images: int,
                  runner_instance_id: str | None = None) -> ClaimedRow | None:
        self.log.append("redeliver")
        with self._data:
            for task_id, instance in self.held.items():
                if runner_instance_id is None or instance == runner_instance_id:
                    self.held[task_id] = runner_instance_id
                    return _row(task_id)
        return None

    def held_claims(self, session: Any, token_id: str) -> int:
        self.log.append("held_claims")
        with self._data:
            count = len(self.held)
        if self._pause:
            time.sleep(self._pause)  # widen the window between the count and the claim
        if self._rendezvous is not None:
            self._rendezvous.wait(timeout=10)  # both claims have counted before either claims
        return count

    def claim_next(self, session: Any, *, connection_id: str, token_id: str, lease_seconds: int,
                   max_images: int, runner_instance_id: str | None = None) -> ClaimedRow | None:
        self.log.append("claim_next")
        with self._data:
            if not self.open:
                return None
            task_id = self.open.pop(0)
            self.held[task_id] = runner_instance_id
        return _row(task_id)


def _claim(rows: _Rows, limit: int | None, instance: str | None = None) -> Any:
    return claim_task(
        lambda: _Session(rows), PRINCIPAL, wait_seconds=0, executors=_Executors(limit),  # type: ignore[arg-type]
        repository=rows, runner_instance_id=instance)  # type: ignore[arg-type]


def _race(rows: _Rows, limit: int, instances: list[str], polls: int = 1) -> dict[str, list[str]]:
    start = threading.Barrier(len(instances))
    got: dict[str, list[str]] = {instance: [] for instance in instances}
    errors: list[BaseException] = []

    def run(instance: str) -> None:
        try:
            start.wait(timeout=10)
            for _ in range(polls):
                task = _claim(rows, limit, instance)
                if task is not None:
                    got[instance].append(task.task_id)
        except BaseException as error:  # noqa: BLE001 - reported by the test thread
            errors.append(error)

    threads = [threading.Thread(target=run, args=(instance,)) for instance in instances]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert not errors, errors
    assert not any(thread.is_alive() for thread in threads), "a claim never finished"
    return got


# -- the order of the steps ------------------------------------------------------------------------


def test_the_token_is_locked_before_anything_is_counted_or_claimed_at_a_limit_of_one() -> None:
    rows = _Rows(["ext_1"])
    assert _claim(rows, 1).task_id == "ext_1"
    assert rows.log == ["lock_token", "sweep", "clear_terminal_payloads", "redeliver", "held_claims", "claim_next"]


def test_the_token_is_locked_first_above_a_limit_of_one_too_and_nothing_is_redelivered() -> None:
    rows = _Rows(["ext_1"])
    assert _claim(rows, 3).task_id == "ext_1"
    assert rows.log == ["lock_token", "sweep", "clear_terminal_payloads", "held_claims", "claim_next"]


def test_a_connection_with_no_revision_limit_is_a_limit_of_one_and_still_locks_first() -> None:
    rows = _Rows(["ext_1"])
    _claim(rows, None)
    assert rows.log[:2] == ["lock_token", "sweep"] and "redeliver" in rows.log


def test_a_token_that_has_no_row_is_refused_as_unauthenticated_and_nothing_else_runs() -> None:
    rows = _Rows(["ext_1"], exists=False)
    with pytest.raises(DomainError) as refused:
        _claim(rows, 1)
    assert refused.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    assert rows.log == ["lock_token"] and rows.open == ["ext_1"] and rows.held == {}


def test_the_lock_is_released_when_the_transaction_ends_so_the_next_claim_can_take_it() -> None:
    rows = _Rows(["ext_1", "ext_2"])
    _claim(rows, 3)
    _claim(rows, 3)  # a lock that outlived the first transaction would block here for ever
    assert sorted(rows.held) == ["ext_1", "ext_2"]


# -- the race --------------------------------------------------------------------------------------


@pytest.mark.parametrize("round_", range(5))
def test_two_claims_of_one_token_at_a_limit_of_one_take_exactly_one_task(round_: int) -> None:
    rows = _Rows(["ext_1", "ext_2"], pause=0.05)
    got = _race(rows, 1, [A, B])
    assert sum(len(tasks) for tasks in got.values()) == 1, got
    assert len(rows.held) == 1 and len(rows.open) == 1


def test_four_claims_of_one_token_at_a_limit_of_three_take_exactly_three_distinct_tasks() -> None:
    rows = _Rows([f"ext_{n}" for n in range(6)], pause=0.02)
    got = _race(rows, 3, [A, B, "agent-instance-cccc", "agent-instance-dddd"], polls=3)
    taken = [task for tasks in got.values() for task in tasks]
    assert len(taken) == 3 and len(set(taken)) == 3, got
    assert len(rows.held) == 3 and len(rows.open) == 3


def test_without_the_lock_two_claims_both_pass_a_limit_of_one() -> None:
    """The guard shown able to fail. The same two claims over the model without ``lock_token``'s lock both
    count zero held claims, because neither has claimed yet, and both claim: the limit is exceeded. This
    is the defect the lock closes (the barrier makes both counts happen before either claim, so the
    outcome does not depend on timing)."""
    rows = _Rows(["ext_1", "ext_2"], serialise=False, rendezvous=threading.Barrier(2))
    got = _race(rows, 1, [A, B])
    assert sum(len(tasks) for tasks in got.values()) == 2, got
    assert len(rows.held) == 2


def test_a_held_task_is_never_handed_to_the_other_instance_however_often_it_asks() -> None:
    """Two processes presenting one token never work on the same task: at a limit of one the instance that
    holds the claim is given it again, the other is given nothing, and no second task is taken."""
    rows = _Rows(["ext_1", "ext_2"], pause=0.005)
    assert _claim(rows, 1, A).task_id == "ext_1"
    got = _race(rows, 1, [A, B], polls=8)
    assert got[A] == ["ext_1"] * 8, "the holder is redelivered its task every time"
    assert got[B] == [], "the other instance is never handed it"
    assert rows.held == {"ext_1": A} and rows.open == ["ext_2"]
