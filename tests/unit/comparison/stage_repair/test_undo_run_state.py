"""Undo recomputes the text evidence of every run, but only a live run goes back to work."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.stage_repair import service as repair_service
from auditmanager.comparison.stage_repair.service import StageRepairService, undo_reopens_run
from auditmanager.ingest.public import CommandStarted
from auditmanager.shared.identity import (
    CommandId, StageChainRunId, StageLinkRepairId, StageLinkRevisionId, StagePairId,
)

EXPERT = frozenset({"expert"})
RUN, REPAIR, PAIR = str(StageChainRunId.new()), str(StageLinkRepairId.new()), str(StagePairId.new())
REPAIRED = str(StageLinkRevisionId.new())
BEFORE = str(StageLinkRevisionId.new())
CHILD = str(StageChainRunId.new())
USER = "usr_00000000000000000000000001"


class _Result:
    def __init__(self, row: Any = None, scalar: Any = None) -> None:
        self._row, self._scalar = row, scalar

    def first(self) -> Any:
        return self._row

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def all(self) -> list[Any]:
        return []

    def scalars(self) -> "_Result":
        return self


class _Session:
    """Answers the SQL ``undo`` issues from canned rows and remembers every statement and its parameters."""

    def __init__(self, *, run_state: str, with_ai: bool) -> None:
        self.run_state, self.with_ai = run_state, with_ai
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = " ".join(str(statement).split())
        self.statements.append((sql, dict(params or {})))
        if "FOR UPDATE OF r" in sql:
            return _Result(row=(RUN, [], REPAIRED, PAIR, self.with_ai, ["ver_a", "ver_b"], "prj_x", self.run_state))
        if sql.startswith("SELECT stage_chain_run_id FROM stage_link_repair"):
            return _Result(scalar=RUN)
        if "FROM stage_link_revision WHERE stage_pair_id" in sql:
            return _Result(row=(REPAIRED, 2, "automatic"))
        if "FROM stage_link_repair x JOIN stage_chain_run r USING" in sql:
            return _Result(row=(REPAIR, RUN, BEFORE, REPAIRED, {}, "2026-11-02", PAIR))
        return _Result()

    def writes(self, table: str) -> list[dict[str, Any]]:
        return [params for sql, params in self.statements if sql.startswith(f"UPDATE {table} ")]


class _Commands:
    def begin(self, session: Any, **_kw: Any) -> CommandStarted:
        return CommandStarted(CommandId.new())

    def succeed(self, session: Any, command_id: Any, outcome: dict[str, Any]) -> None:
        self.outcome = outcome


class _Work:
    enqueued: list[dict[str, Any]] = []

    def enqueue(self, session: Any, **kwargs: Any) -> None:
        self.enqueued.append(kwargs)


class _Recompute:
    def __init__(self, sessions: Any) -> None: ...

    def start_in_session(self, session: Any, **_kw: Any) -> Any:
        return SimpleNamespace(run_id=CHILD)


def _undo(monkeypatch: pytest.MonkeyPatch, *, run_state: str, with_ai: bool) -> tuple[_Session, _Commands]:
    session, commands = _Session(run_state=run_state, with_ai=with_ai), _Commands()

    @contextmanager
    def scope(factory: Any) -> Any:
        yield session

    _Work.enqueued = []
    monkeypatch.setattr(repair_service, "session_scope", scope)
    monkeypatch.setattr(repair_service, "StageTextRecomputeService", _Recompute)
    monkeypatch.setattr(repair_service, "ComparisonWorkRepository", _Work)
    service = StageRepairService(lambda: session)  # type: ignore[arg-type]
    service.commands = commands  # type: ignore[assignment]
    service.undo(repair_id=REPAIR, base_revision_id=REPAIRED, user_uid=USER, actor_roles=EXPERT,
                 idempotency_key="undo-unit-key")
    return session, commands


def test_only_a_completed_run_is_left_alone() -> None:
    assert [undo_reopens_run(state) for state in ("queued", "running", "paused")] == [True, True, True]
    assert undo_reopens_run("completed") is False


@pytest.mark.parametrize("with_ai", [False, True])
def test_undo_of_a_completed_run_recomputes_text_and_leaves_the_run_and_its_cards(
    monkeypatch: pytest.MonkeyPatch, with_ai: bool,
) -> None:
    session, commands = _undo(monkeypatch, run_state="completed", with_ai=with_ai)
    inserted = [sql for sql, _params in session.statements if sql.startswith("INSERT INTO stage_link_revision ")]
    assert len(inserted) == 1  # the undo revision is still written
    assert any("INSERT INTO stage_link_repair_event" in sql for sql, _p in session.statements)
    assert commands.outcome["recompute_run_id"] == CHILD and commands.outcome["run_reopened"] is False
    # Neither the run nor its steps (and so the cards step 7 wrote) are reopened or queued again.
    assert session.writes("stage_chain_run") == [] and session.writes("stage_chain_step") == []
    assert _Work.enqueued == []


@pytest.mark.parametrize(("run_state", "with_ai"), [
    ("queued", False), ("running", False), ("paused", False), ("paused", True),
])
def test_undo_of_a_live_run_still_recomputes_steps_two_to_seven(
    monkeypatch: pytest.MonkeyPatch, run_state: str, with_ai: bool,
) -> None:
    session, commands = _undo(monkeypatch, run_state=run_state, with_ai=with_ai)
    (run_update,) = session.writes("stage_chain_run")
    assert run_update["state"] == ("paused" if with_ai else "queued")
    assert run_update["reason"] == ("comparison_consent_required" if with_ai else None)
    assert len(session.writes("stage_chain_step")) == 1
    assert len(_Work.enqueued) == (0 if with_ai else 1)
    assert commands.outcome["run_reopened"] is True
