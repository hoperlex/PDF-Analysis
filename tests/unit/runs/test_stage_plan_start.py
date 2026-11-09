"""`HOSTS-LAYOUT-01`: the three start commands freeze a stage plan while the layout is on, and are what they were while it is off.

Container-free, in the manner of ``test_group_admission_unit.py`` (whose ledger, repositories and session fakes this reuses). The
preflight is a fake that prices nothing: it returns the plan the draft freezes for the rows it was told, which is the contract the
commands rely on (the real preflight's consent v2 is held by ``test_stage_plan_consent.py``).
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.runs import commands as commands_module
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.commands import reaudit_run, start_audit_run, start_run_from_stage
from auditmanager.runs.stage_plan import ModelAvailability, StagePlanDraft
from auditmanager.runs.stage_reuse import PC01_STAGES, STARTABLE_STAGES
from auditmanager.shared.errors import DomainError, ErrorCode

from .test_group_admission_unit import (
    BASE_FINGERPRINT, BUNDLE, CONNECTION, GROUP, PRESET, PROFILE, SOURCE_RUN, VERSION, Admitter, Documents, Freezer, Jobs, Ledger,
    Runs, Session, _nothing_written, _source,
)

REVISION = "slr_01M2545JSD15ETSNNV904X991J"


def draft(subscription: bool = True) -> StagePlanDraft:
    cells = layout.preset_cells("claude_only")
    served = ModelAvailability(subscription=subscription, api=True)
    return StagePlanDraft(REVISION, "claude_only", cells, {c.model_id: served for c in cells})


class Estimate:
    def __init__(self, plan: Any) -> None:
        self.stage_plan, self.frozen_route, self.chosen_preset, self.admitted_group = plan, None, None, None

    def approve(self, consent: Any, *, actor_user_uid: Any = None) -> dict[str, Any]:
        return {"window_characters": 10**9, "estimate_digest": "e" * 64, "consent": consent, "actor": actor_user_uid}


class Preflight:
    """Records how each estimate was asked for and freezes the plan of the rows a v3 run calls."""

    def __init__(self, rows: tuple[str, ...] = layout.STAGE_ROWS) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._rows = rows

    def _estimate(self, kind: str, kwargs: dict[str, Any]) -> Estimate:
        self.calls.append((kind, kwargs))
        planned = kwargs.get("stage_plan")
        return Estimate(None if planned is None else planned.freeze(self._rows))

    def estimate_run(self, session: Any, **kwargs: Any) -> Estimate:
        return self._estimate("run", kwargs)

    def estimate_reaudit(self, session: Any, **kwargs: Any) -> Estimate:
        return self._estimate("reaudit", kwargs)

    def estimate_from_stage(self, session: Any, **kwargs: Any) -> Estimate:
        return self._estimate("from_stage", kwargs)


class Layout:
    """The ``stage_plans`` seam: ``None`` while off, the draft while on; counts how often the switch was read."""

    def __init__(self, on: bool = True, **kwargs: Any) -> None:
        self.on, self.reads, self._draft = on, 0, draft(**kwargs)

    def __call__(self, session: Any) -> StagePlanDraft | None:
        self.reads += 1
        return self._draft if self.on else None


def _start(ledger, runs, session, *, stage_plans, preflight, freezer=None, admitter=None, **named):
    return start_audit_run(
        session, version_uid=VERSION, analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE, provider_mode="recorded",
        idempotency_key="plan-1", commands=ledger, runs=runs, documents=Documents(), norms_snapshot=lambda s: None,
        connection_route=freezer, group_admitter=admitter, stage_plans=stage_plans, cost_preflight=preflight, **named,
    )


def _repeat(ledger, runs, session, *, stage_plans, preflight, freezer=None, admitter=None):
    return reaudit_run(
        session, source_run_id=SOURCE_RUN, roles=frozenset({"expert"}), idempotency_key="repeat-1", analysis_profile_id=PROFILE,
        prompt_bundle_id=BUNDLE, provider_mode="recorded", runs=runs, jobs=Jobs(), commands=ledger, documents=Documents(),
        norms_snapshot=lambda s: None, connection_route=freezer, group_admitter=admitter, input_budget_characters=10**9,
        stage_plans=stage_plans, cost_preflight=preflight,
    )


def _from_stage(ledger, runs, session, *, stage_plans, preflight, freezer=None, admitter=None):
    return start_run_from_stage(
        session, source_run_id=SOURCE_RUN, start_stage_id="text_analysis", roles=frozenset({"expert"}), idempotency_key="stage-1",
        analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE, provider_mode="recorded", runs=runs, jobs=Jobs(), commands=ledger,
        documents=Documents(), norms_snapshot=lambda s: None, connection_route=freezer, group_admitter=admitter,
        input_budget_characters=10**9, stage_plans=stage_plans, cost_preflight=preflight,
    )


@pytest.fixture(autouse=True)
def no_reuse_rule(monkeypatch):
    monkeypatch.setattr(commands_module, "plan_stage_reuse", lambda *a, **k: None)


def source(**more):
    return _source(binding_state="frozen_at_start", executor_group_revision_id=None, routing_rule_revision_id=None, **more)


# --- the plan is frozen ------------------------------------------------------------------------------------------------------


def test_a_start_with_the_layout_on_is_written_pending_with_the_plan_and_no_executor() -> None:
    ledger, runs, session, freezer, admitter, preflight, stage_plans = Ledger(), Runs(), Session(), Freezer(), Admitter(), Preflight(), Layout()
    started = _start(ledger, runs, session, stage_plans=stage_plans, preflight=preflight, freezer=freezer, admitter=admitter)
    (row,) = runs.created
    assert row["binding_state"] == "pending" and row["stage_plan"] == draft().freeze(layout.STAGE_ROWS).to_json()
    assert row.get("connection_revision_id") is None and row.get("preset_revision_id") is None
    assert "executor_group_revision_id" not in row and "routing_rule_revision_id" not in row
    assert freezer.calls == [] and admitter.calls == [], "the layout chooses the servers: no route, no group"
    assert stage_plans.reads == 1 and [kind for kind, _ in preflight.calls] == ["run"]
    assert preflight.calls[0][1]["stage_plan"] is stage_plans._draft, "the estimate is told of the layout, and the same draft"
    assert ledger.succeeded[0]["cost_consent"]["estimate_digest"] == "e" * 64
    (event,) = session.events
    assert event["event_type"] == "audit_run.stage_plan_frozen" and event["payload"] == {
        "run_id": started.run_id, "revision_id": REVISION, "state": "pending", "reason": "claude_only"}
    assert ledger.fingerprints == [BASE_FINGERPRINT], "the request is the payload: the plan is the server's"


def test_the_access_is_frozen_with_the_plan() -> None:
    runs = Runs()
    _start(Ledger(), runs, Session(), stage_plans=Layout(subscription=False), preflight=Preflight())
    cells = runs.created[0]["stage_plan"]["cells"]
    assert {cell["access"] for cell in cells} == {"api"}
    subscription = Runs()
    _start(Ledger(), subscription, Session(), stage_plans=Layout(subscription=True), preflight=Preflight())
    assert {cell["access"] for cell in subscription.created[0]["stage_plan"]["cells"]} == {"subscription"}


def test_a_run_freezes_only_the_cells_it_will_call() -> None:
    runs = Runs()
    _start(Ledger(), runs, Session(), stage_plans=Layout(), preflight=Preflight(rows=("text",)))
    assert [cell["cell_key"] for cell in runs.created[0]["stage_plan"]["cells"]] == ["text:main"]


def test_with_the_layout_off_the_start_is_exactly_what_it_was() -> None:
    ledger, runs, session, freezer, preflight = Ledger(), Runs(), Session(), Freezer(), Preflight()
    _start(ledger, runs, session, stage_plans=Layout(on=False), preflight=preflight, freezer=freezer)
    (row,) = runs.created
    assert "stage_plan" not in row and "binding_state" not in row and session.events == []
    assert "stage_plan" not in preflight.calls[0][1], "a preflight that predates the layout is called as before"
    assert ledger.fingerprints == [BASE_FINGERPRINT]
    plain, plain_runs = Ledger(), Runs()
    _start(plain, plain_runs, Session(), stage_plans=None, preflight=Preflight())
    assert "stage_plan" not in plain_runs.created[0]


@pytest.mark.parametrize(("named", "field"), [
    ({"executor_connection_id": CONNECTION}, "executor_connection_id"),
    ({"preset_id": PRESET}, "preset_id"),
    ({"executor_group_id": GROUP}, "executor_group_id"),
])
def test_an_explicit_selector_under_the_layout_is_validation_failed_and_writes_nothing(named: dict[str, str], field: str) -> None:
    ledger, runs, session, preflight = Ledger(), Runs(), Session(), Preflight()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, stage_plans=Layout(), preflight=preflight, **named)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(caught.value.detail_fields) == {"field": field, "constraint": "stage_layout_enabled"}
    _nothing_written(ledger, runs, session)
    assert preflight.calls == []


def test_the_same_selectors_are_allowed_while_the_layout_is_off() -> None:
    runs, freezer = Runs(), Freezer()
    _start(Ledger(), runs, Session(), stage_plans=Layout(on=False), preflight=None, freezer=freezer,
           executor_connection_id=CONNECTION)
    assert freezer.calls == [{"connection_id": CONNECTION}] and runs.created[0]["connection_revision_id"] is not None


def test_a_layout_with_no_cost_preflight_refuses_the_start_instead_of_running_unconsented() -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, stage_plans=Layout(), preflight=None)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(caught.value.detail_fields) == {"dependency": "analysis_cost_preflight"}
    _nothing_written(ledger, runs, session)


def test_an_estimate_that_froze_no_plan_under_the_layout_is_refused() -> None:
    class Blind(Preflight):
        def _estimate(self, kind: str, kwargs: dict[str, Any]) -> Estimate:
            return Estimate(None)

    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, stage_plans=Layout(), preflight=Blind())
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert runs.created == []


def test_a_replayed_key_reads_no_layout_and_writes_nothing() -> None:
    ledger, runs, session, stage_plans = Ledger(replay_run=SOURCE_RUN), Runs(), Session(), Layout()
    started = _start(ledger, runs, session, stage_plans=stage_plans, preflight=Preflight())
    assert started.replayed is True and stage_plans.reads == 0 and runs.created == [] and session.events == []


def test_a_cell_with_no_server_refuses_the_start_and_nothing_is_substituted() -> None:
    class Down(Layout):
        def __init__(self) -> None:
            super().__init__()
            self._draft = replace(self._draft, availability={})

    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, stage_plans=Down(), preflight=Preflight())
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    _nothing_written(ledger, runs, session)


# --- all three commands use the plan --------------------------------------------------------------------------------------


@pytest.mark.parametrize("command", [_repeat, _from_stage])
def test_a_repeat_and_a_start_from_a_stage_take_today_s_plan_and_ignore_the_source_s_executor(command) -> None:
    ledger, runs, session, freezer, admitter, preflight, stage_plans = (
        Ledger(), Runs(source(), CONNECTION), Session(), Freezer(), Admitter(mode="rules"), Preflight(), Layout())
    command(ledger, runs, session, stage_plans=stage_plans, preflight=preflight, freezer=freezer, admitter=admitter)
    (row,) = runs.created
    assert row["binding_state"] == "pending" and row["stage_plan"]["layout_revision_id"] == REVISION
    assert row.get("connection_revision_id") is None
    assert freezer.calls == [] and admitter.calls == [], "the source's named connection is not carried over"
    ((kind, kwargs),) = preflight.calls
    assert kind in {"reaudit", "from_stage"} and kwargs["stage_plan"] is stage_plans._draft
    (event,) = session.events
    assert event["event_type"] == "audit_run.stage_plan_frozen"


@pytest.mark.parametrize("command", [_repeat, _from_stage])
def test_a_repeat_and_a_start_from_a_stage_are_unchanged_with_the_layout_off(command) -> None:
    ledger, runs, session, freezer, preflight = Ledger(), Runs(source(), CONNECTION), Session(), Freezer(), Preflight()
    command(ledger, runs, session, stage_plans=Layout(on=False), preflight=preflight, freezer=freezer, admitter=Admitter())
    (row,) = runs.created
    assert "stage_plan" not in row and "binding_state" not in row
    assert "stage_plan" not in preflight.calls[0][1]


@pytest.mark.parametrize("command", [_repeat, _from_stage])
def test_a_repeat_and_a_start_from_a_stage_with_a_layout_and_no_preflight_are_refused(command) -> None:
    ledger, runs, session = Ledger(), Runs(source()), Session()
    with pytest.raises(DomainError) as caught:
        command(ledger, runs, session, stage_plans=Layout(), preflight=None)
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    _nothing_written(ledger, runs, session)


@pytest.mark.parametrize("command", [_repeat, _from_stage])
def test_a_replayed_repeat_reads_no_layout(command) -> None:
    ledger, stage_plans = Ledger(replay_run=SOURCE_RUN), Layout()
    command(ledger, Runs(source()), Session(), stage_plans=stage_plans, preflight=Preflight())
    assert stage_plans.reads == 0


def test_a_start_from_a_stage_reuses_only_stages_that_run_no_model() -> None:
    for stage in STARTABLE_STAGES:
        reused = PC01_STAGES[:PC01_STAGES.index(stage)]
        assert reused and all(layout.row_of_phase(name) is None for name in reused), (stage, reused)
    assert layout.row_of_phase("text_analysis") == "text", "the stage that calls a model is never in a reused prefix"
