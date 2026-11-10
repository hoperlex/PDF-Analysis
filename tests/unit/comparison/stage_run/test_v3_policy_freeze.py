"""The V3 plan a run starts under is frozen with its start command (D-530).

Rules from `stage_run/service.py` and docs/program/SPRINT3-STAGE-1030.md: a genuinely new V3 command selects the plan once
(`fresh_policy()`, or the parent batch's explicit `stage_v3_policy`), freezes it in the command outcome and in the run's
input hash, and hands it to the AI preparation; an identical retry replays and never reads the switch again; an active
run is reused only when its stored plan agrees with the one this command selects; a classic run knows no policy.
Stub repositories only: no database.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.stage_ai.validation import StageAiValidationError
from auditmanager.comparison.stage_run import service as service_module
from auditmanager.comparison.stage_run.service import StageChainService
from auditmanager.comparison.stage_v3 import consolidation as c, windowed as w
from auditmanager.comparison.stage_v3.mode import ENGINE
from auditmanager.comparison.stage_v3.policy import GLOBAL_LIMITS, GLOBAL_VERSION, LIMITS, VERSION
from auditmanager.ingest.public import CommandReplay
from auditmanager.shared.errors import DomainError

SWITCH = "AUDITMANAGER_STAGE_V3_PLAN"
WINDOWED = {"plan_version": VERSION, "bundle": w.BUNDLE, "limits": LIMITS}
GLOBAL = {"plan_version": GLOBAL_VERSION, "bundle": c.BUNDLE, "limits": GLOBAL_LIMITS}
PAIR, REVISION, USER = "spr_00000000000000000000000001", "slr_00000000000000000000000001", "usr_00000000000000000000000001"
LIVE = "crn_00000000000000000000000001"
CONSENT = {"estimate_digest": "d" * 64, "accepted": True}


class _Result:
    def __init__(self, value: Any = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalar_one(self) -> Any:
        return self._value

    def all(self) -> list[Any]:
        return []


class _Session:
    """Answers the statements `start` makes, from what the test stored; records every one."""

    def __init__(self, *, live: str | None = None, stored: Any = None) -> None:
        self.live, self.stored = live, stored
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = " ".join(str(statement).split())
        self.statements.append((sql, dict(params or {})))
        if sql.startswith("SELECT stage_chain_run_id FROM stage_chain_run WHERE stage_pair_id"):
            return _Result(self.live)
        if "c.outcome->'stage_v3_policy' FROM stage_chain_run r" in sql:
            return _Result(self.stored)
        return _Result()

    def inserted_runs(self) -> list[dict[str, Any]]:
        return [params for sql, params in self.statements if sql.startswith("INSERT INTO stage_chain_run ")]


class _Commands:
    def __init__(self, replay: CommandReplay | None) -> None:
        self.replay, self.outcomes = replay, []

    def begin(self, _session: Any, **_kw: Any) -> Any:
        return self.replay if self.replay is not None else SimpleNamespace(command_id="cmd_00000000000000000000000001")

    def succeed(self, _session: Any, _command_id: Any, outcome: dict[str, Any]) -> None:
        self.outcomes.append(outcome)


class _Ai:
    def __init__(self) -> None:
        self.prepared: list[dict[str, Any]] = []

    def prepare(self, _session: Any, **kwargs: Any) -> str:
        self.prepared.append(kwargs)
        return "job_00000000000000000000000001"


def _existing(engine: str, *, with_ai: bool = True, stale: bool = False) -> SimpleNamespace:
    return SimpleNamespace(run_id=LIVE, engine=engine, with_ai=with_ai, stale=stale)


def _start(monkeypatch: pytest.MonkeyPatch, session: _Session, *, switch: str | None = None,
           existing: SimpleNamespace | None = None, replay: CommandReplay | None = None,
           **start_args: Any) -> tuple[Any, _Commands, _Ai]:
    @contextmanager
    def scope(_factory: Any) -> Any:
        yield session

    monkeypatch.setattr(service_module, "session_scope", scope)
    if switch is None:
        monkeypatch.delenv(SWITCH, raising=False)
    else:
        monkeypatch.setenv(SWITCH, switch)
    ai = _Ai()
    service = StageChainService(object(), comparison_modules="versions,stages", ai=ai)  # type: ignore[arg-type]
    service.commands = _Commands(replay)  # type: ignore[assignment]
    service.sheets = SimpleNamespace(passports=lambda pair_id: [  # type: ignore[assignment]
        SimpleNamespace(version_uid="ver_a", profile_id="pp_a"), SimpleNamespace(version_uid="ver_b", profile_id="pp_b")])
    service.work = SimpleNamespace(enqueue=lambda *_a, **_k: None)  # type: ignore[assignment]
    service._pair = lambda _s, pair_id: {"project_uid": "prj_00000000000000000000000001", "state": "confirmed"}  # type: ignore[method-assign]
    service._latest = lambda _s, pair_id: REVISION  # type: ignore[method-assign]
    service._event = lambda *_a, **_k: None  # type: ignore[method-assign]
    service.record = lambda _s, run_id: (  # type: ignore[method-assign]
        existing if existing is not None and run_id == LIVE else SimpleNamespace(run_id=run_id))
    args = dict(pair_id=PAIR, revision_id=REVISION, user_uid=USER, actor_roles=frozenset({"expert"}),
                idempotency_key="stage-start-0000000000000001", with_ai=True, consent=CONSENT)
    result = service.start(**{**args, **start_args})
    return result, service.commands, ai  # type: ignore[return-value]


def _outcome(commands: _Commands) -> dict[str, Any]:
    assert len(commands.outcomes) == 1
    return commands.outcomes[0]


def _input_hash(session: _Session) -> str:
    (run,) = session.inserted_runs()
    return run["sha"]


# --- a new V3 command freezes the plan the switch selects ----------------------------------------------------------------

@pytest.mark.parametrize("switch,expected", [("windowed-v1", WINDOWED), ("windowed-global-v1", GLOBAL), (None, GLOBAL)])
def test_a_new_v3_run_freezes_the_selected_plan_in_its_command_outcome_and_hands_it_to_the_ai(monkeypatch, switch, expected):
    session = _Session()
    run, commands, ai = _start(monkeypatch, session, switch=switch, engine=ENGINE)
    assert _outcome(commands) == {"run_id": run.run_id, "engine": ENGINE, "original_source": service_module.ORIGINAL_SHA,
                                  "stage_v3_policy": expected}
    assert len(ai.prepared) == 1 and ai.prepared[0]["engine"] == ENGINE and ai.prepared[0]["v3_policy"] == expected


def test_the_legacy_switch_freezes_no_plan_and_still_runs_the_v3_engine(monkeypatch):
    session = _Session()
    _run, commands, ai = _start(monkeypatch, session, switch="legacy", engine=ENGINE)
    assert "stage_v3_policy" not in _outcome(commands) and _outcome(commands)["engine"] == ENGINE
    assert ai.prepared[0]["engine"] == ENGINE and ai.prepared[0]["v3_policy"] is None


def test_a_classic_run_knows_no_plan_and_never_reads_the_switch(monkeypatch):
    session = _Session()
    run, commands, ai = _start(monkeypatch, session, switch="no-such-plan")   # a switch value that would refuse a V3 start
    assert _outcome(commands) == {"run_id": run.run_id, "engine": "classic"}
    assert "engine" not in ai.prepared[0] and "v3_policy" not in ai.prepared[0]


def test_an_unsupported_switch_refuses_a_new_v3_start_before_any_run_is_created(monkeypatch):
    session = _Session()
    with pytest.raises(StageAiValidationError, match="^v3_plan_configuration_unsupported$"):
        _start(monkeypatch, session, switch="windowed-v2", engine=ENGINE)
    assert session.inserted_runs() == []


# --- the plan is part of the run's input identity ---------------------------------------------------------------------------

def test_the_input_hash_differs_per_plan_and_is_stable_for_one_plan(monkeypatch):
    hashes = {}
    for switch in ("legacy", "windowed-v1", "windowed-global-v1"):
        first, second = _Session(), _Session()
        _start(monkeypatch, first, switch=switch, engine=ENGINE)
        _start(monkeypatch, second, switch=switch, engine=ENGINE)
        assert _input_hash(first) == _input_hash(second)
        hashes[switch] = _input_hash(first)
    classic = _Session()
    _start(monkeypatch, classic)
    hashes["classic"] = _input_hash(classic)
    assert len(set(hashes.values())) == 4


def test_the_input_hash_binds_the_whole_frozen_policy_not_only_its_name_and_bundle(monkeypatch):
    # Same plan name and bundle, a different limit: another run input.
    from auditmanager.comparison.stage_v3 import policy as policy_module
    base, widened = _Session(), _Session()
    _start(monkeypatch, base, switch="windowed-v1", engine=ENGINE)
    monkeypatch.setattr(policy_module, "fresh_policy", lambda: WINDOWED | {"limits": dict(LIMITS, pages=65)})
    _start(monkeypatch, widened, switch="windowed-v1", engine=ENGINE)
    assert _input_hash(base) != _input_hash(widened)


# --- an explicit plan (a parent batch's) beats the switch ------------------------------------------------------------------

def test_an_explicit_plan_from_a_batch_is_frozen_whatever_the_switch_says_now(monkeypatch):
    session = _Session()
    _run, commands, ai = _start(monkeypatch, session, switch="windowed-v1", engine=ENGINE, stage_v3_policy=GLOBAL)
    assert _outcome(commands)["stage_v3_policy"] == GLOBAL and ai.prepared[0]["v3_policy"] == GLOBAL


def test_an_explicit_absent_plan_means_legacy_not_the_switch(monkeypatch):
    session = _Session()
    _run, commands, ai = _start(monkeypatch, session, switch="windowed-global-v1", engine=ENGINE, stage_v3_policy=None)
    assert "stage_v3_policy" not in _outcome(commands) and ai.prepared[0]["v3_policy"] is None


def test_an_explicit_plan_that_no_longer_matches_the_code_refuses_the_start_and_creates_nothing(monkeypatch):
    session = _Session()
    with pytest.raises(StageAiValidationError, match="^v3_windowed_policy_changed_requires_fresh_run$"):
        _start(monkeypatch, session, engine=ENGINE, stage_v3_policy=dict(WINDOWED, bundle="0" * 64))
    assert session.inserted_runs() == []


# --- an identical retry replays; it never reads the switch again ------------------------------------------------------------

def test_a_replayed_start_returns_its_run_without_consulting_the_switch(monkeypatch):
    replay = CommandReplay(command_id="cmd_00000000000000000000000001", outcome={"run_id": LIVE, "engine": ENGINE})  # type: ignore[arg-type]
    session = _Session()
    run, commands, ai = _start(monkeypatch, session, switch="windowed-v2", engine=ENGINE, replay=replay,
                               existing=_existing(ENGINE))    # the switch is garbage now: a new command would refuse it
    assert run.run_id == LIVE and commands.outcomes == [] and ai.prepared == [] and session.inserted_runs() == []


# --- an active run is reused only when its plan agrees ----------------------------------------------------------------------------

@pytest.mark.parametrize("stored,switch", [(WINDOWED, "windowed-v1"), (GLOBAL, "windowed-global-v1"), (GLOBAL, None), (None, "legacy")])
def test_an_active_v3_run_is_reused_when_the_selected_plan_is_the_one_it_runs_under(monkeypatch, stored, switch):
    session = _Session(live=LIVE, stored=stored)
    run, commands, ai = _start(monkeypatch, session, switch=switch, engine=ENGINE, existing=_existing(ENGINE))
    assert run.run_id == LIVE and session.inserted_runs() == [] and ai.prepared == []
    expected = {"run_id": LIVE, "engine": ENGINE}
    assert _outcome(commands) == expected | ({"stage_v3_policy": stored} if stored is not None else {})   # the retry replays the run's own plan


@pytest.mark.parametrize("stored,switch", [(WINDOWED, "windowed-global-v1"), (GLOBAL, "windowed-v1"), (WINDOWED, "legacy"),
                                           (None, "windowed-v1"), (None, "windowed-global-v1")])
def test_an_active_v3_run_under_another_plan_is_not_reused_it_is_a_conflict(monkeypatch, stored, switch):
    session = _Session(live=LIVE, stored=stored)
    with pytest.raises(DomainError) as refused:
        _start(monkeypatch, session, switch=switch, engine=ENGINE, existing=_existing(ENGINE))
    assert refused.value.detail_fields["conflict_reason"] == "stage_chain_run_active"
    assert session.inserted_runs() == []


def test_an_active_run_is_compared_with_the_explicit_plan_of_the_command_not_the_switch(monkeypatch):
    session = _Session(live=LIVE, stored=GLOBAL)
    run, _commands, _ai = _start(monkeypatch, session, switch="windowed-v1", engine=ENGINE, existing=_existing(ENGINE),
                                 stage_v3_policy=GLOBAL)
    assert run.run_id == LIVE
    with pytest.raises(DomainError):
        _start(monkeypatch, _Session(live=LIVE, stored=GLOBAL), switch="windowed-global-v1", engine=ENGINE,
               existing=_existing(ENGINE), stage_v3_policy=WINDOWED)


def test_an_active_classic_run_is_reused_by_a_classic_start_and_refused_to_a_v3_start(monkeypatch):
    session = _Session(live=LIVE)
    run, commands, _ai = _start(monkeypatch, session, existing=_existing("classic"))
    assert run.run_id == LIVE and _outcome(commands) == {"run_id": LIVE, "engine": "classic"}
    with pytest.raises(DomainError) as refused:
        _start(monkeypatch, _Session(live=LIVE), switch="windowed-v1", engine=ENGINE, existing=_existing("classic"))
    assert refused.value.detail_fields["conflict_reason"] == "stage_chain_run_active"
