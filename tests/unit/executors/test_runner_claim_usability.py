"""`EXEC2-INT-1` review: the claim re-checks the token under its own lock.

A claim long-polls for up to 25 s and a token is authenticated once, before the first poll, so a token
revoked or expired -- or of a connection archived -- after authentication could still claim a task. The
token's row is locked as the first statement of every poll (`EXEC2-PULL-01`); that same statement now says
whether the token is **still usable**, and an unusable token is refused as ``authentication_required``,
exactly as a missing one, before anything is swept, counted or claimed.

What is shown here needs no database: the text and the reading of the statement, and that ``claim_task``
refuses before any further statement. The behaviour on PostgreSQL (a claim that waited for the row lock of
a token revoked in the meantime, and the three ways a token stops being usable) is in
``tests/integration/executors/test_runner_concurrency.py`` and was not run in EXEC-2 (`R-149d`).

The guard is shown able to fail: over the repository that reports only that the row exists (the
`lock_token` before this change), the same revoked token claims a task.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.executors.runner import RunnerPrincipal, claim_task
from auditmanager.executors.runner_repository import ClaimedRow, RunnerRepository
from auditmanager.shared.errors import DomainError, ErrorCode

STORE = RunnerRepository()
PRINCIPAL = RunnerPrincipal("ern_TOKEN", "exc_CONN")


class _Result:
    def __init__(self, row: Any) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class _Recording:
    """A session that remembers every statement and its parameters and answers with one fixed row."""

    def __init__(self, row: Any = None) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []
        self._row = row

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        self.statements.append((" ".join(str(statement).split()), dict(params or {})))
        return _Result(self._row)


# -- the statement ----------------------------------------------------------------------------------


def test_the_lock_locks_the_tokens_own_row_and_reads_its_usability_from_that_row() -> None:
    session = _Recording(row=(True,))
    assert STORE.lock_token(session, "ern_T") is True  # type: ignore[arg-type]
    (sql, params), = session.statements
    assert params == {"t": "ern_T"}
    assert sql.endswith("WHERE t.token_id = :t FOR UPDATE OF t"), "the token's row, and only that row, is locked"
    # `HOSTS-BACKEND-01`: the token of a host is usable while its host is not archived, as a connection's while the connection is not.
    for part in ("t.revoked_at IS NULL", "t.expires_at > clock_timestamp()", "COALESCE(c.archived_at, h.archived_at) IS NULL",
                 "LEFT JOIN executor_connection c ON c.connection_id = t.connection_id",
                 "LEFT JOIN executor_host h ON h.host_id = t.host_id"):
        assert part in sql, part
    assert "FOR UPDATE OF c" not in sql and "FOR SHARE" not in sql, (
        "the connection is read and not locked: the administrator's writes take it before the token")


@pytest.mark.parametrize(("row", "usable"), [
    ((True,), True),
    ((False,), False),   # revoked, expired or its connection archived
    ((None,), False),    # the join produced no verdict: never usable
    (None, False),       # no such token
])
def test_only_a_row_that_says_usable_is_usable(row: Any, usable: bool) -> None:
    assert STORE.lock_token(_Recording(row=row), "ern_T") is usable  # type: ignore[arg-type]


# -- the claim ----------------------------------------------------------------------------------------


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def commit(self) -> None:
        pass


class _Executors:
    def current_revisions(self, session: Any, connection_ids: Any) -> dict[str, Any]:
        from types import SimpleNamespace

        return {connection_ids[0]: SimpleNamespace(settings=SimpleNamespace(max_claimed_tasks=1))}


class _Rows:
    """The statements of a claim over one token, in memory. ``revoked`` is the token's state in the database;
    ``reports_usability`` is whether ``lock_token`` says so (this change) or says only that the row is there
    (the lock before it)."""

    def __init__(self, *, revoked: bool, reports_usability: bool = True) -> None:
        self.revoked, self.reports_usability = revoked, reports_usability
        self.log: list[str] = []
        self.open = ["ext_1"]

    def lock_token(self, session: Any, token_id: str) -> bool:
        self.log.append("lock_token")
        return not (self.revoked and self.reports_usability)

    def sweep(self, session: Any, connection_id: str) -> None:
        self.log.append("sweep")

    def clear_terminal_payloads(self, session: Any, **kwargs: Any) -> None:
        self.log.append("clear_terminal_payloads")

    def redeliver(self, session: Any, **kwargs: Any) -> ClaimedRow | None:
        self.log.append("redeliver")
        return None

    def held_claims(self, session: Any, token_id: str) -> int:
        self.log.append("held_claims")
        return 0

    def claim_next(self, session: Any, **kwargs: Any) -> ClaimedRow | None:
        self.log.append("claim_next")
        if not self.open:
            return None
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        return ClaimedRow(
            task_id=self.open.pop(0), claim_expires_at=now + timedelta(seconds=120),
            deadline_at=now + timedelta(seconds=600), expected_model="m",
            payload={"system": "s", "user_text": "u", "output_schema": {}})


def _claim(rows: _Rows) -> Any:
    return claim_task(
        lambda: _Session(), PRINCIPAL, wait_seconds=0, executors=_Executors(),  # type: ignore[arg-type]
        repository=rows)  # type: ignore[arg-type]


def test_a_token_that_is_no_longer_usable_is_refused_as_unauthenticated_before_anything_else_runs() -> None:
    rows = _Rows(revoked=True)
    with pytest.raises(DomainError) as refused:
        _claim(rows)
    assert refused.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    assert rows.log == ["lock_token"] and rows.open == ["ext_1"], "nothing swept, counted or claimed"


def test_a_usable_token_claims_as_before() -> None:
    rows = _Rows(revoked=False)
    assert _claim(rows).task_id == "ext_1"
    assert rows.log[0] == "lock_token" and rows.log[-1] == "claim_next"


def test_over_a_lock_that_reports_only_that_the_row_exists_the_same_revoked_token_claims() -> None:
    """The guard shown able to fail. This is the defect: the revoked token's row is there, the lock is
    taken, and the claim goes on to hand the token a task."""
    rows = _Rows(revoked=True, reports_usability=False)
    assert _claim(rows).task_id == "ext_1"
    assert rows.open == []
