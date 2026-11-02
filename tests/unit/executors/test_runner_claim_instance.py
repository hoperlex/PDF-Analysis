"""`EXEC2-PULL-01` (ADR-0026 decision 3): the statements that record, match and clear ``runner_instance_id``.

The behaviour on PostgreSQL (a held task redelivered to its own instance and to no other, the lapse that
clears the instance, the CHECK that ties the instance to a token) is in
``tests/integration/executors/test_runner_concurrency.py`` and was not run in EXEC-2 (`R-149d`). This file
holds what needs no database: the text and the parameters of the four statements, the refusal of a name
the wire would not accept before any statement runs, and that ``claim_task`` passes the name on to both
statements that hand out a task and passes ``None`` for a claim that named none.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.executors.runner import RunnerPrincipal, claim_task
from auditmanager.executors.runner_repository import RunnerRepository

STORE = RunnerRepository()
NAME = "agent-instance-aaaa"


class _Result:
    def __init__(self, row: Any = None) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class _Recording:
    """A session that remembers every statement and its parameters and answers with no row."""

    def __init__(self, row: Any = None) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []
        self._row = row

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        self.statements.append((str(statement), dict(params or {})))
        return _Result(self._row)


def _flat(sql: str) -> str:
    return " ".join(sql.split())


# -- claim_next ------------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", [NAME, None])
def test_a_fresh_claim_records_the_instance_it_names_and_null_when_it_names_none(instance: str | None) -> None:
    session = _Recording()
    STORE.claim_next(session, connection_id="exc_C", token_id="ern_T", lease_seconds=120,  # type: ignore[arg-type]
                     runner_instance_id=instance)
    (sql, params), = session.statements
    sql = _flat(sql)
    assert "claimed_by_instance_id = CAST(:instance AS text)" in sql
    assert sql.index("claimed_by_instance_id") < sql.index("WHERE"), "it is assigned, not tested"
    assert params["instance"] == instance and params["token"] == "ern_T"


def test_a_fresh_claim_that_names_nothing_binds_null_and_changes_nothing_else() -> None:
    """The old caller (`claim_next` without the argument, as `test_comparison_task_origin.py` calls it)."""
    session = _Recording()
    STORE.claim_next(session, connection_id="exc_C", token_id="ern_T", lease_seconds=120)  # type: ignore[arg-type]
    (_, params), = session.statements
    assert params == {"c": "exc_C", "token": "ern_T", "lease": 120, "max_images": 1, "instance": None}


# -- redeliver -------------------------------------------------------------------------------------


def test_a_redelivery_is_matched_on_the_instance_only_when_the_claim_names_one() -> None:
    session = _Recording()
    STORE.redeliver(session, token_id="ern_T", lease_seconds=120, runner_instance_id=NAME)  # type: ignore[arg-type]
    (sql, params), = session.statements
    sql = _flat(sql)
    assert ("AND (CAST(:instance AS text) IS NULL OR claimed_by_instance_id = CAST(:instance AS text)) "
            "ORDER BY created_at, task_id LIMIT 1 FOR UPDATE") in sql, "the match is in the row that is locked"
    assert "claimed_by_instance_id = CAST(:instance AS text) WHERE task_id = (SELECT" in sql, (
        "the redelivered task records the instance it is handed to")
    assert params["instance"] == NAME and params["t"] == "ern_T"


def test_a_redelivery_for_a_claim_that_names_none_binds_null_so_any_held_task_matches_as_before() -> None:
    session = _Recording()
    STORE.redeliver(session, token_id="ern_T", lease_seconds=120)  # type: ignore[arg-type]
    (_, params), = session.statements
    assert params["instance"] is None and params["max_images"] == 1


# -- sweep ------------------------------------------------------------------------------------------


def test_the_sweep_clears_the_instance_in_the_statement_that_returns_the_task_to_open() -> None:
    """``ck_executor_task_instance_with_token`` is checked at the end of each statement: a statement that
    cleared the token and left the instance would be refused by the database, and a later statement
    that cleared the instance would come too late."""
    session = _Recording()
    STORE.sweep(session, "exc_C")  # type: ignore[arg-type]
    reopening = [_flat(sql) for sql, _ in session.statements if "SET state = 'open'" in sql]
    assert len(reopening) == 1
    assert "claimed_by_token_id = NULL" in reopening[0] and "claimed_by_instance_id = NULL" in reopening[0]
    others = [_flat(sql) for sql, _ in session.statements if "SET state = 'open'" not in sql]
    assert len(others) == 2 and all("claimed_by_token_id" not in sql for sql in others), (
        "a cancelled or expired task keeps its token, so it keeps its instance")


# -- lock_token -------------------------------------------------------------------------------------


def test_the_token_lock_is_a_select_for_update_of_the_tokens_own_row() -> None:
    found, missing = _Recording(row=(1,)), _Recording(row=None)
    assert STORE.lock_token(found, "ern_T") is True  # type: ignore[arg-type]
    assert STORE.lock_token(missing, "ern_T") is False  # type: ignore[arg-type]
    (sql, params), = found.statements
    assert _flat(sql) == "SELECT 1 FROM executor_runner_token WHERE token_id = :t FOR UPDATE"
    assert params == {"t": "ern_T"}


# -- a name the wire would not accept is refused before any statement -----------------------------------


@pytest.mark.parametrize("bad", [
    "", "short", "x" * 65, "has space inside", "slash/in-name", "ключ-агента-1", "trailing-newline\n",
    "semi;colon-1", 12345678, b"agent-instance-aaaa", ["agent-instance-aaaa"],
])
def test_a_name_outside_the_wire_pattern_is_refused_before_any_statement(bad: Any) -> None:
    session = _Recording()
    with pytest.raises(ValueError):
        STORE.claim_next(session, connection_id="exc_C", token_id="ern_T", lease_seconds=1,  # type: ignore[arg-type]
                         runner_instance_id=bad)
    with pytest.raises(ValueError):
        STORE.redeliver(session, token_id="ern_T", lease_seconds=1, runner_instance_id=bad)  # type: ignore[arg-type]
    assert session.statements == []


@pytest.mark.parametrize("good", ["abcdefgh", "A" * 64, "a-b_C-1234", "q3Zr8k0vXw2mN5bTjA9cLg"])
def test_a_name_inside_the_wire_pattern_reaches_the_statement(good: str) -> None:
    session = _Recording()
    STORE.redeliver(session, token_id="ern_T", lease_seconds=1, runner_instance_id=good)  # type: ignore[arg-type]
    assert session.statements[0][1]["instance"] == good


# -- claim_task passes the name on ----------------------------------------------------------------


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def commit(self) -> None:
        return None


class _Executors:
    def current_revisions(self, session: Any, connection_ids: Any) -> dict[str, Any]:
        return {}


class _Asked:
    """A repository that hands out nothing and remembers the instance each statement was asked for."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, Any]] = []

    def lock_token(self, session: Any, token_id: str) -> bool:
        return True

    def sweep(self, session: Any, connection_id: str) -> None: ...

    def clear_terminal_payloads(self, session: Any, **kwargs: Any) -> None: ...

    def held_claims(self, session: Any, token_id: str) -> int:
        return 0

    def redeliver(self, session: Any, **kwargs: Any) -> None:
        self.asked.append(("redeliver", kwargs["runner_instance_id"]))

    def claim_next(self, session: Any, **kwargs: Any) -> None:
        self.asked.append(("claim_next", kwargs["runner_instance_id"]))


def _ask(**extra: Any) -> list[tuple[str, Any]]:
    rows = _Asked()
    claim_task(_Session, RunnerPrincipal("ern_T", "exc_C"), wait_seconds=0, executors=_Executors(),  # type: ignore[arg-type]
               repository=rows, **extra)  # type: ignore[arg-type]
    return rows.asked


def test_the_name_reaches_both_the_redelivery_and_the_fresh_claim() -> None:
    assert _ask(runner_instance_id=NAME) == [("redeliver", NAME), ("claim_next", NAME)]


def test_a_claim_that_names_none_asks_both_statements_for_none() -> None:
    assert _ask() == [("redeliver", None), ("claim_next", None)]
