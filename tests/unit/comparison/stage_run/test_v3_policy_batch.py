"""A batch freezes the V3 plan once and every child run starts under it (D-530).

Rules from `stage_run/batch.py` and docs/program/SPRINT3-STAGE-1030.md: a new V3 batch selects the plan once
(`fresh_policy()`) and freezes it in its command outcome as `stage_v3_policy`; the worker then starts every child run with
exactly that stored plan -- an absent plan too, which means legacy and must not be turned into "ask the switch again" --
so a switch changed after the batch began never reaches a child. A classic batch has no plan. Stub sessions only.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.stage_ai.validation import StageAiValidationError
from auditmanager.comparison.stage_run import batch as batch_module
from auditmanager.comparison.stage_run.batch import StageBatchHandler, StageBatchService
from auditmanager.comparison.stage_run.service import BATCH_WORK_KIND
from auditmanager.comparison.stage_v3 import consolidation as c, windowed as w
from auditmanager.comparison.stage_v3.mode import ENGINE
from auditmanager.comparison.stage_v3.policy import GLOBAL_LIMITS, GLOBAL_VERSION, LIMITS, VERSION
from auditmanager.comparison.work.model import Yielded
from auditmanager.shared.identity import StageChainBatchId, StageLinkRevisionId, StagePairId

SWITCH = "AUDITMANAGER_STAGE_V3_PLAN"
WINDOWED = {"plan_version": VERSION, "bundle": w.BUNDLE, "limits": LIMITS}
GLOBAL = {"plan_version": GLOBAL_VERSION, "bundle": c.BUNDLE, "limits": GLOBAL_LIMITS}
BATCH, PAIR, REVISION = str(StageChainBatchId.new()), str(StagePairId.new()), str(StageLinkRevisionId.new())
PROJECT, ACTOR = "prj_00000000000000000000000001", "usr_00000000000000000000000001"


class _Result:
    def __init__(self, value: Any = None) -> None:
        self._value = value

    def first(self) -> Any:
        return self._value

    def scalar_one(self) -> Any:
        return self._value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def all(self) -> list[Any]:
        return []


class _WorkerSession:
    """The statements the batch worker makes for one queued item of a batch whose command outcome is stored."""

    def __init__(self, *, engine: str | None, policy: Any, item: str) -> None:
        self.engine, self.policy, self.item = engine, policy, item
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = " ".join(str(statement).split())
        self.statements.append((sql, dict(params or {})))
        if "c.outcome->>'engine' FROM stage_chain_batch b" in sql:
            return _Result(self.engine)
        if "c.outcome->'stage_v3_policy' FROM stage_chain_batch b" in sql:
            return _Result(self.policy)
        if "FOR NO KEY UPDATE" in sql:
            return _Result("running")
        if sql.startswith("SELECT state, project_uid, actor_user_uid, with_ai FROM stage_chain_batch"):
            return _Result(("queued", PROJECT, ACTOR, True))
        if "FROM stage_chain_batch_item" in sql and "state IN ('queued','running')" in sql:
            return _Result((self.item, PAIR, REVISION, "queued", None, {}))
        return _Result()


def _run_children(monkeypatch: pytest.MonkeyPatch, *, engine: str | None, policy: Any, switch: str | None,
                  items: int = 2) -> list[dict[str, Any]]:
    """Run the batch worker once per queued item; return the arguments each child `start` received."""
    started: list[dict[str, Any]] = []
    session = _WorkerSession(engine=engine, policy=policy, item="bit_0")

    @contextmanager
    def scope(_factory: Any) -> Any:
        yield session

    def start(**kwargs: Any) -> Any:
        started.append(kwargs)
        return SimpleNamespace(run_id=f"crn_{len(started):026d}")

    monkeypatch.setattr(batch_module, "session_scope", scope)
    monkeypatch.setattr(batch_module, "AccountRepository", lambda: SimpleNamespace(roles_of=lambda *_a: frozenset({"expert"})))
    if switch is None:
        monkeypatch.delenv(SWITCH, raising=False)
    else:
        monkeypatch.setenv(SWITCH, switch)
    handler = StageBatchHandler(SimpleNamespace(session_factory=object()))  # type: ignore[arg-type]
    handler.chains = SimpleNamespace(start=start)  # type: ignore[assignment]
    work = SimpleNamespace(kind=BATCH_WORK_KIND, module="stages", payload={"batch_id": BATCH},
                           project_uid=PROJECT, require_current=lambda _session: None)
    for number in range(items):
        session.item = f"bit_{number}"
        assert isinstance(handler.run(work), Yielded)  # type: ignore[arg-type]
    return started


# --- the worker starts every child under the plan the batch froze ------------------------------------------------------------

@pytest.mark.parametrize("stored,switch_now", [(WINDOWED, "windowed-global-v1"), (GLOBAL, "windowed-v1"), (GLOBAL, "legacy"),
                                               (WINDOWED, None)])
def test_every_child_of_a_v3_batch_starts_under_the_stored_stage_v3_policy_whatever_the_switch_says_now(monkeypatch, stored, switch_now):
    started = _run_children(monkeypatch, engine=ENGINE, policy=stored, switch=switch_now, items=3)
    assert len(started) == 3
    assert all(call["engine"] == ENGINE and call["stage_v3_policy"] == stored for call in started)
    assert [call["idempotency_key"] for call in started] == [f"stage-batch:{BATCH}:bit_{n}" for n in range(3)]
    assert all(call["batch_id"] == BATCH for call in started)


@pytest.mark.parametrize("switch_now", ["windowed-v1", "windowed-global-v1", None])
def test_a_v3_batch_without_a_stored_plan_starts_its_children_as_legacy_not_under_the_switch(monkeypatch, switch_now):
    started = _run_children(monkeypatch, engine=ENGINE, policy=None, switch=switch_now)
    assert len(started) == 2
    for call in started:
        assert call["engine"] == ENGINE
        assert "stage_v3_policy" in call and call["stage_v3_policy"] is None      # passed explicitly: None is not "select a fresh plan"


def test_a_classic_batch_starts_classic_children_with_no_plan(monkeypatch):
    started = _run_children(monkeypatch, engine=None, policy=None, switch="windowed-v1")
    assert [call["engine"] for call in started] == ["classic", "classic"]
    assert all("stage_v3_policy" in call and call["stage_v3_policy"] is None for call in started)


# --- a new batch freezes the plan the switch selects ----------------------------------------------------------------------

class _Commands:
    def __init__(self) -> None:
        self.outcomes: list[dict[str, Any]] = []

    def begin(self, _session: Any, **_kw: Any) -> Any:
        return SimpleNamespace(command_id="cmd_00000000000000000000000001")

    def succeed(self, _session: Any, _command_id: Any, outcome: dict[str, Any]) -> None:
        self.outcomes.append(outcome)


class _StartSession:
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        self.statements.append((" ".join(str(statement).split()), dict(params or {})))
        return _Result()

    def inserted_batches(self) -> list[dict[str, Any]]:
        return [params for sql, params in self.statements if sql.startswith("INSERT INTO stage_chain_batch ")]


def _start_batch(monkeypatch: pytest.MonkeyPatch, *, switch: str | None, engine: str,
                 session: _StartSession | None = None) -> tuple[_Commands, _StartSession]:
    session = session or _StartSession()

    @contextmanager
    def scope(_factory: Any) -> Any:
        yield session

    commands = _Commands()
    chains = SimpleNamespace(
        _enabled=lambda: None, sessions=object(), commands=commands,
        _pair=lambda _s, pair_id: {"project_uid": PROJECT, "state": "confirmed"},
        _latest=lambda _s, pair_id: REVISION, work=SimpleNamespace(enqueue=lambda *_a, **_k: None))
    monkeypatch.setattr(batch_module, "session_scope", scope)
    if switch is None:
        monkeypatch.delenv(SWITCH, raising=False)
    else:
        monkeypatch.setenv(SWITCH, switch)
    service = StageBatchService(chains)  # type: ignore[arg-type]
    service.record = lambda _s, batch_id: {"batch_id": batch_id}  # type: ignore[method-assign]
    service._event = lambda *_a, **_k: None  # type: ignore[method-assign]
    service.start(project_uid=PROJECT, selections=[{"pair_id": PAIR, "link_revision_id": REVISION, "consent": {"accepted": True}}],
                  user_uid=ACTOR, actor_roles=frozenset({"expert"}), idempotency_key="stage-batch-00000000000001",
                  with_ai=True, engine=engine)
    return commands, session


@pytest.mark.parametrize("switch,expected", [("windowed-v1", WINDOWED), ("windowed-global-v1", GLOBAL), (None, GLOBAL)])
def test_a_new_v3_batch_freezes_the_selected_stage_v3_policy_in_its_command_outcome(monkeypatch, switch, expected):
    commands, session = _start_batch(monkeypatch, switch=switch, engine=ENGINE)
    (outcome,) = commands.outcomes
    assert outcome["engine"] == ENGINE and outcome["stage_v3_policy"] == expected
    assert len(session.inserted_batches()) == 1


def test_the_legacy_switch_freezes_no_plan_on_a_v3_batch(monkeypatch):
    commands, _session = _start_batch(monkeypatch, switch="legacy", engine=ENGINE)
    (outcome,) = commands.outcomes
    assert outcome["engine"] == ENGINE and "stage_v3_policy" not in outcome


def test_a_classic_batch_freezes_no_plan_and_never_reads_the_switch(monkeypatch):
    commands, _session = _start_batch(monkeypatch, switch="no-such-plan", engine="classic")    # would refuse a V3 batch
    (outcome,) = commands.outcomes
    assert outcome == {"batch_id": outcome["batch_id"], "engine": "classic"}


def test_an_unsupported_switch_refuses_a_new_v3_batch_before_anything_is_created(monkeypatch):
    session = _StartSession()
    with pytest.raises(StageAiValidationError, match="^v3_plan_configuration_unsupported$"):
        _start_batch(monkeypatch, switch="windowed-v2", engine=ENGINE, session=session)
    assert session.inserted_batches() == []
