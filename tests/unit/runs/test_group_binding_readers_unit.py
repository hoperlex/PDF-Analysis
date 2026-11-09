"""`EXEC2-GROUP-RUN-01`, premise P-01: every reader of a Run's frozen connection revision tells *pending* from *environment*.

A Run admitted on a group has no connection revision until the claim binds one -- which is also what a Run of the
``environment`` source has. The readers below are the ones with logic worth proving without a database (the file-by-file
inventory is in the lane report):

* **the cost policy** (``runs.cost_policy``): a group consent names the group revision and no connection; the Run must have
  frozen the same revision; the policy carries ``None`` while pending and the bound revision afterwards; an old-shape consent
  is compared exactly as it always was; a group Run whose consent names no group (or the reverse) is a changed binding;
* **the dispatcher's re-check** (``group_consent_holds``): the consent still holds for the group revision's model, billing and
  the provider lock's rate; a deployment with no consent has nothing to break;
* **the call-time guard** (``analysis.text.cost.require_approved_model``): a group Run with no bound member is refused before any
  call; a bound one is held to the member; the ``environment`` source is held to model and rate only, as before;
* **the provider sources** (``bootstrap.providers``): neither serves a ``pending`` Run -- the ``environment`` one because it
  would run group work on its own adapter, the ``database`` one because no connection exists to bind;
* **the status** (``bootstrap.adapters._run_status_view`` and ``api.schemas.runs``): ``binding_state``, ``planned``, ``binding``,
  ``wait_reason`` and ``waiting_since`` are rendered for a Run admitted on a group and for no other, so every other body is byte
  for byte what it was; the execution queue's items follow the same rule.

B3 section 11 numbers (the task file's reading): **17** -- the ``environment`` source never runs a pending Run; **18** -- every
other Run reads as it did; **3** -- what admission froze is visible. Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

import auditmanager.executors.public as executors_public
import auditmanager.runs as runs_package
import auditmanager.runs.cost_policy as cost_policy
from auditmanager.analysis.public import model_rate_sha256, pinned_models
from auditmanager.analysis.text.cost import require_approved_model
from auditmanager.api.schemas.runs import RunBindingView, RunGroupPlanView, RunStatusView, run_status_body
from auditmanager.bootstrap import adapters, providers
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X993K"
PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
COMMAND = "cmd_01M2545JSD15ETSNNV904X991C"
GROUP = "exg_01M2545JSD15ETSNNV904X991G"
GROUP_REVISION = "exgr_01M2545JSD15ETSNNV904X991R"
OTHER_REVISION = "exgr_01M2545JSD15ETSNNV904X992R"
RULE_REVISION = "exrr_01M2545JSD15ETSNNV904X991U"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991N"
MEMBER = "excr_01M2545JSD15ETSNNV904X991A"
PIN = next(pin for pin in pinned_models() if pin.model_id == "claude-sonnet-5")
NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def _consent(**changes: Any) -> dict[str, Any]:
    consent = {
        "estimate_digest": "a" * 64, "ceiling_micros": 0, "billing": "unmetered", "model_id": PIN.model_id,
        "rate_sha256": model_rate_sha256(PIN), "connection_revision_id": None,
        "executor_group_revision_id": GROUP_REVISION, "window_characters": 1000, "max_windows": 12,
    }
    consent.update(changes)
    return {key: value for key, value in consent.items() if value is not ...}


def _run(**changes: Any) -> Any:
    row = dict(
        run_id=RUN, command_id=COMMAND, state="queued", binding_state="pending",
        executor_group_revision_id=GROUP_REVISION, routing_rule_revision_id=None,
        connection_revision_id=None, wait_reason=None, waiting_since=None, preset_revision_id=None,
    )
    row.update(changes)
    return SimpleNamespace(**row)


class _Runs:
    def __init__(self, run: Any) -> None:
        self._run = run

    def get(self, session: Any, run_id: str) -> Any:
        return self._run


@pytest.fixture
def command(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The accepted command of the Run: its outcome is what a test sets."""
    state = SimpleNamespace(outcome={}, state="succeeded")

    class _Commands:
        def get(self, session: Any, command_id: Any) -> Any:
            return SimpleNamespace(state=state.state, outcome=state.outcome)

    monkeypatch.setattr(cost_policy, "CommandRepository", _Commands)
    return state


def _policy(run: Any) -> Any:
    return cost_policy.read_run_cost_policy(None, run_id=RUN, default_ceiling_usd=1.0, runs=_Runs(run))


# --- the worker's cost policy -----------------------------------------------------------------------------------------


def test_a_pending_group_run_has_a_policy_with_the_group_and_no_connection(command: SimpleNamespace) -> None:
    command.outcome = {"run_id": RUN, "cost_consent": _consent()}
    policy = _policy(_run())
    assert policy.approved and policy.executor_group_revision_id == GROUP_REVISION
    assert policy.connection_revision_id is None, "pending, not environment: nothing may be called yet"


def test_a_bound_group_run_carries_the_member_dispatch_wrote(command: SimpleNamespace) -> None:
    command.outcome = {"run_id": RUN, "cost_consent": _consent()}
    policy = _policy(_run(binding_state="bound", connection_revision_id=MEMBER))
    assert (policy.executor_group_revision_id, policy.connection_revision_id) == (GROUP_REVISION, MEMBER)


@pytest.mark.parametrize(("consent", "run"), [
    (_consent(executor_group_revision_id=OTHER_REVISION), _run()),                 # a different group revision
    (_consent(executor_group_revision_id=...), _run()),                            # a group Run, a consent with no group
    (_consent(), _run(binding_state="frozen_at_start", executor_group_revision_id=None)),   # a group consent, a frozen Run
    (_consent(connection_revision_id=MEMBER), _run()),                             # a group consent that names a connection
])
def test_a_consent_and_a_run_that_disagree_about_the_group_are_a_changed_binding(
    command: SimpleNamespace, consent: dict[str, Any], run: Any,
) -> None:
    command.outcome = {"run_id": RUN, "cost_consent": consent}
    with pytest.raises(DomainError) as caught:
        _policy(run)
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert dict(caught.value.detail_fields)["reason"] == "cost_estimate_binding_changed"


def test_a_frozen_run_is_compared_with_its_connection_exactly_as_before(command: SimpleNamespace) -> None:
    frozen = _run(binding_state="frozen_at_start", executor_group_revision_id=None, connection_revision_id=MEMBER)
    command.outcome = {"run_id": RUN, "cost_consent": _consent(
        executor_group_revision_id=..., connection_revision_id=MEMBER)}
    assert _policy(frozen).connection_revision_id == MEMBER
    command.outcome = {"run_id": RUN, "cost_consent": _consent(
        executor_group_revision_id=..., connection_revision_id="excr_OTHER")}
    with pytest.raises(DomainError):
        _policy(frozen)


def test_an_environment_run_with_an_environment_consent_still_has_no_connection(command: SimpleNamespace) -> None:
    environment = _run(binding_state="frozen_at_start", executor_group_revision_id=None)
    command.outcome = {"run_id": RUN, "cost_consent": _consent(executor_group_revision_id=...)}
    policy = _policy(environment)
    assert policy.connection_revision_id is None and policy.executor_group_revision_id is None


# --- the dispatcher's re-check --------------------------------------------------------------------------------------------


def _holds(**keywords: Any) -> bool:
    return cost_policy.group_consent_holds(
        None, run_id=RUN, group_revision_id=GROUP_REVISION, pin_id=PIN.model_id, billing="unmetered",
        runs=_Runs(_run()), **keywords)


def test_a_consent_that_names_this_revision_model_billing_and_the_current_rate_holds(command: SimpleNamespace) -> None:
    command.outcome = {"run_id": RUN, "cost_consent": _consent()}
    assert _holds() is True


@pytest.mark.parametrize("changes", [
    {"executor_group_revision_id": OTHER_REVISION},
    {"model_id": "claude-opus-5"},
    {"billing": "metered"},
    {"rate_sha256": "0" * 64},
    {"executor_group_revision_id": ...},
])
def test_a_consent_that_no_longer_matches_does_not_hold(command: SimpleNamespace, changes: dict[str, Any]) -> None:
    command.outcome = {"run_id": RUN, "cost_consent": _consent(**changes)}
    assert _holds() is False


def test_a_run_accepted_with_no_consent_has_nothing_to_break_and_one_whose_command_never_succeeded_holds_nothing(
    command: SimpleNamespace,
) -> None:
    command.outcome = {"run_id": RUN}
    assert _holds() is True
    command.state = "in_progress"
    assert _holds() is False


def test_a_pin_the_lock_no_longer_publishes_cannot_hold(command: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    command.outcome = {"run_id": RUN, "cost_consent": _consent()}
    monkeypatch.setattr(cost_policy, "pinned_models", lambda: ())
    assert _holds() is False


# --- the call-time guard ----------------------------------------------------------------------------------------------------


def _config(**changes: Any) -> Any:
    values = dict(
        approved_cost_ceiling=True, approved_model_id=PIN.model_id, approved_rate_sha256=model_rate_sha256(PIN),
        approved_connection_revision_id=None, approved_group_revision_id=None,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def test_a_group_run_with_no_bound_member_is_refused_before_any_call() -> None:
    with pytest.raises(DomainError) as caught:
        require_approved_model(_config(approved_group_revision_id=GROUP_REVISION), PIN, SimpleNamespace(
            connection_revision_id=None))
    assert dict(caught.value.detail_fields)["reason"] == "cost_estimate_binding_changed"


def test_a_bound_group_run_is_held_to_its_member() -> None:
    config = _config(approved_group_revision_id=GROUP_REVISION, approved_connection_revision_id=MEMBER)
    require_approved_model(config, PIN, SimpleNamespace(connection_revision_id=MEMBER))
    with pytest.raises(DomainError):
        require_approved_model(config, PIN, SimpleNamespace(connection_revision_id="excr_OTHER"))


def test_the_environment_source_is_held_to_model_and_rate_only_as_before() -> None:
    require_approved_model(_config(), PIN, None)
    require_approved_model(_config(), PIN, SimpleNamespace(connection_revision_id=None))
    with pytest.raises(DomainError):
        require_approved_model(_config(approved_rate_sha256="0" * 64), PIN, None)


# --- the provider sources ----------------------------------------------------------------------------------------------------


def test_the_environment_source_serves_neither_a_pending_nor_a_bound_run_and_still_serves_its_own() -> None:
    source = providers.EnvironmentProviders(SimpleNamespace(provider_mode=None), SimpleNamespace(model_id="x"))
    for run in (_run(), _run(binding_state="bound", connection_revision_id=MEMBER)):
        with pytest.raises(DomainError) as caught:
            source.resolve(None, run, None)  # type: ignore[arg-type]
        assert dict(caught.value.detail_fields) == {"dependency": "executor_route_missing"}
    own = _run(binding_state="frozen_at_start", executor_group_revision_id=None)
    assert source.resolve(None, own, None).adapter is not None  # type: ignore[arg-type]


def test_the_database_source_refuses_a_run_with_no_connection_pending_or_environment() -> None:
    source = providers.DatabaseProviders(
        ring=None, policy=None, base_config=SimpleNamespace(), ceiling_usd=1.0)  # type: ignore[arg-type]
    for run in (_run(), _run(binding_state="frozen_at_start", executor_group_revision_id=None)):
        with pytest.raises(DomainError) as caught:
            source.resolve(None, run, None)  # type: ignore[arg-type]
        assert dict(caught.value.detail_fields) == {"dependency": "executor_route_missing"}


# --- the status ----------------------------------------------------------------------------------------------------------------


def _view(monkeypatch: pytest.MonkeyPatch, run: Any, *, executor: Any = None) -> Any:
    import auditmanager.findings as findings

    row = SimpleNamespace(
        project_uid=PROJECT, version_uid=VERSION, provider_mode="live", created_at=NOW, analysis_profile_id="ap_X",
        prompt_bundle_id="pb_X", degradation_set=(), terminal_reason=None, terminal_detail=None,
        interrupted_reason=None, terminal_at=None, reaudit_of_run_id=None, norms_snapshot_id=None, **vars(run),
    )

    class _Repository:
        def get(self, session: Any, run_id: str) -> Any:
            return row

        def stage_results(self, session: Any, run_id: str) -> tuple[()]:
            return ()

        def cost(self, session: Any, run_id: str) -> None:
            return None

    revision = SimpleNamespace(
        group_id=GROUP, group_revision_id=GROUP_REVISION, pin_id=PIN.model_id, gateway_model="claude-sonnet-5",
        billing="not_metered")
    monkeypatch.setattr(runs_package, "RunRepository", _Repository)
    # Contract 1.40.0 (`UI-B-45`): the view reads an active run's estimated finish from the database; these cases stub
    # the session, so the estimate is stubbed too (its own cases are tests/unit/execution/test_eta.py).
    import auditmanager.execution.eta as eta
    monkeypatch.setattr(eta, "run_estimated_finish", lambda session, run_id: None)
    monkeypatch.setattr(findings, "published_finding_count", lambda session, run_id: 0)
    monkeypatch.setattr(findings, "diagnostics", lambda session, run_id: ())
    monkeypatch.setattr(executors_public, "executor_of_revision", lambda session, revision_id: executor)
    monkeypatch.setattr(executors_public, "run_queue_reason", lambda session, run_id: None)
    monkeypatch.setattr(executors_public, "group_revision_of", lambda session, revision_id: revision)
    return adapters._run_status_view(None, RUN)  # type: ignore[arg-type]


def test_a_pending_run_reports_its_plan_and_why_it_waits_and_no_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    view = _view(monkeypatch, _run(wait_reason="executor_at_capacity", waiting_since=NOW, routing_rule_revision_id=RULE_REVISION))
    body = run_status_body(view)
    assert body["binding_state"] == "pending"
    assert body["planned"] == {
        "executor_group_id": GROUP, "executor_group_revision_id": GROUP_REVISION,
        "routing_rule_revision_id": RULE_REVISION, "pin_id": PIN.model_id, "gateway_model": "claude-sonnet-5",
        "billing": "not_metered"}
    assert body["wait_reason"] == "executor_at_capacity" and body["waiting_since"].startswith("2026-11-03T12:00:00")
    assert "binding" not in body and "executor" not in body and "queue_reason" not in body


def test_a_group_named_without_a_rule_has_no_rule_revision_in_its_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    body = run_status_body(_view(monkeypatch, _run()))
    assert "routing_rule_revision_id" not in body["planned"]
    assert "wait_reason" not in body and "waiting_since" not in body, "a Run that is not waiting reports no wait"


def test_a_bound_run_reports_the_member_and_executor_names_the_same_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = SimpleNamespace(connection_id=CONNECTION, display_name="Сервер 1", pin_id=PIN.model_id)
    view = _view(monkeypatch, _run(binding_state="bound", connection_revision_id=MEMBER, state="running"), executor=executor)
    body = run_status_body(view)
    assert body["binding_state"] == "bound"
    assert body["binding"] == {
        "connection_id": CONNECTION, "connection_revision_id": MEMBER, "display_name": "Сервер 1",
        "pin_id": PIN.model_id, "gateway_model": "claude-sonnet-5"}
    assert body["executor"]["connection_id"] == body["binding"]["connection_id"]
    assert "wait_reason" not in body


def test_a_pending_run_that_has_ended_waits_for_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    body = run_status_body(_view(monkeypatch, _run(state="failed", wait_reason="runner_offline", waiting_since=NOW)))
    assert "wait_reason" not in body and "waiting_since" not in body


def test_a_run_whose_executor_was_frozen_at_start_reads_exactly_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    frozen = _run(binding_state="frozen_at_start", executor_group_revision_id=None)
    body = run_status_body(_view(monkeypatch, frozen))
    assert not {"binding_state", "planned", "binding", "wait_reason", "waiting_since"} & set(body)


def test_a_row_without_the_columns_is_read_as_frozen_at_start() -> None:
    """The contract's own reading of an absent ``binding_state`` -- the stubs of the older suites rely on it."""
    assert adapters._group_status_fields(None, SimpleNamespace(), None) == {}  # type: ignore[arg-type]


def test_the_body_renders_a_plan_with_no_rule_and_a_wait_with_its_clock() -> None:
    view = RunStatusView(
        run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="queued", provider_mode="live", created_at=NOW,
        binding_state="pending",
        planned=RunGroupPlanView(group_id=GROUP, group_revision_id=GROUP_REVISION, pin_id="p", gateway_model="m", billing="metered"),
        binding=RunBindingView(connection_id=CONNECTION, connection_revision_id=MEMBER, display_name="n", pin_id="p", gateway_model="m"),
        wait_reason="needs_reconsent", waiting_since=NOW,
    )
    body = run_status_body(view)
    assert set(body["planned"]) == {
        "executor_group_id", "executor_group_revision_id", "pin_id", "gateway_model", "billing"}
    assert (body["wait_reason"], body["binding_state"]) == ("needs_reconsent", "pending")


def test_a_wait_reason_without_its_clock_renders_the_reason_only_never_a_clock_of_none() -> None:
    view = RunStatusView(
        run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="queued", provider_mode="live", created_at=NOW,
        wait_reason="runner_offline")
    body = run_status_body(view)
    assert body["wait_reason"] == "runner_offline" and "waiting_since" not in body


# --- the execution queue -----------------------------------------------------------------------------------------------------


def test_a_queue_item_of_a_group_run_carries_binding_state_and_the_wait_and_an_ordinary_one_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Repository:
        def binding_facts(self, session: Any, run_ids: Any) -> dict[str, tuple[str, str | None]]:
            return {"run_a": ("pending", "executor_at_capacity"), "run_b": ("bound", None), "run_c": ("pending", None)}

    monkeypatch.setattr(runs_package, "RunRepository", _Repository)
    # Contract 1.40.0 (`UI-B-45`): the view reads an active run's estimated finish from the database; these cases stub
    # the session, so the estimate is stubbed too (its own cases are tests/unit/execution/test_eta.py).
    import auditmanager.execution.eta as eta
    monkeypatch.setattr(eta, "run_estimated_finish", lambda session, run_id: None)
    facts = adapters._queue_binding_facts(None, ["run_a", "run_b", "run_c", "run_d"])  # type: ignore[arg-type]
    assert facts == {
        "run_a": {"binding_state": "pending", "wait_reason": "executor_at_capacity"},
        "run_b": {"binding_state": "bound"},
        "run_c": {"binding_state": "pending"},
    }
    assert "run_d" not in facts, "an ordinary Run's queue item is exactly what it was"
