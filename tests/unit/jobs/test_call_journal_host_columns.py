"""`HOSTS-SEAL-1`: the call journal carries ``stage_key``, ``host_id`` and ``access`` (migration ``0062``) and nothing else moved.

No database: the repository is driven through a recording session. What is proved is the plumbing -- the keyword arguments of
``prepare_provider_call`` reach the INSERT of ``provider_call_effect``, an existing caller writes ``NULL`` for all three, and the INSERT of
``model_call`` and the read of the effect that feeds it name the same three columns. The columns' own rules (their CHECKs, the absence of a
foreign key on ``host_id``) are proved on a real PostgreSQL in ``tests/integration/db/test_hosts_stage_models_migration.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.jobs import repository as jobs_repository
from auditmanager.jobs.repository import JobRepository

HOST = "exh_01ARZ3NDEKTSV4RRFFQ69G5FAV"


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        self.calls.append((str(statement), dict(params or {})))
        return SimpleNamespace(rowcount=1)


@pytest.fixture
def repository(monkeypatch: pytest.MonkeyPatch) -> JobRepository:
    repo = JobRepository()
    monkeypatch.setattr(repo, "require_current", lambda session, authority: None)
    monkeypatch.setattr(jobs_repository, "append_execution_event", lambda *args, **kwargs: None)
    return repo


def _prepare(repo: JobRepository, session: _Recorder, **extra: Any) -> dict[str, Any]:
    authority = SimpleNamespace(run_id="run_x", job_id="job_x", attempt_id="att_x")
    repo.prepare_provider_call(
        session, authority, provider="anthropic", model_identity="claude-opus-5-5", provider_mode="live",
        parameters={}, request_sha256="a" * 64, **extra,
    )
    (sql, params), = session.calls
    assert "INSERT INTO provider_call_effect" in sql
    return params


def test_an_existing_caller_writes_null_for_the_three_columns(repository: JobRepository) -> None:
    params = _prepare(repository, _Recorder())
    assert (params["stage_key"], params["host_id"], params["access"]) == (None, None, None)


def test_the_three_values_reach_the_insert_of_the_effect(repository: JobRepository) -> None:
    params = _prepare(repository, _Recorder(), stage_key="blocks", host_id=HOST, access="subscription")
    assert (params["stage_key"], params["host_id"], params["access"]) == ("blocks", HOST, "subscription")


@pytest.mark.parametrize("statement", ["_INSERT_PROVIDER_EFFECT", "_INSERT_MODEL_CALL", "_PROVIDER_FOR_COMPLETION"])
def test_each_statement_of_the_journal_names_the_three_columns(statement: str) -> None:
    sql = str(getattr(jobs_repository, statement))
    for column in ("stage_key", "host_id", "access"):
        assert column in sql, f"{statement} lost {column}"


def test_the_model_call_takes_its_three_values_from_the_effect_that_was_prepared() -> None:
    sql_insert = str(jobs_repository._INSERT_MODEL_CALL)
    for placeholder in (":stage_key", ":host_id", ":access"):
        assert placeholder in sql_insert
