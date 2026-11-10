"""`HOSTS-INT-WIRE-01`: the integrator's wiring of `HOSTS-BACKEND-01` and `HOSTS-LAYOUT-01` into the served application.

No database and no network. What is proved, each by a test that fails without the line it names:

* the runner seam carries the host: ``RunnerIdentity`` and ``EnrollmentIdentity`` name a host, the principal handed to the executors carries it, a claimed
  task carries its six members (all or none) and a host agent's answer reaches ``submit_answer`` with provider, access, reported model and usage;
* the enrollment adapter takes a host grant through the host adapter, a host token's health report likewise, and refuses a connection token that sends the
  host's members before anything is written;
* the three start commands and the cost preflight read the stage layout through **one** object, and the composition root builds it once (read as syntax);
* the provider sources: the ``environment`` source refuses a planned run with a typed error; the ``database`` source resolves it per cell and never falls
  back to the single binding of a connection;
* the availability port reads the servers: subscription and API apart, busy as available, and the one reason of the host closest to serving a model.
"""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.api.routers.runner import ModelNotTheTasks
from auditmanager.api.schemas import models
from auditmanager.api.security import EnrollmentIdentity, RunnerIdentity
from auditmanager.bootstrap import adapters, composition
from auditmanager.bootstrap.adapters import ExecutionAdapter, ExecutorEnrollmentAdapter, RunAdapter, _enrollment_view
from auditmanager.bootstrap.hosts_dispatch import HostModelAvailability
from auditmanager.bootstrap.providers import DatabaseProviders, EnvironmentProviders
from auditmanager.bootstrap.runner import RunnerAdapter, runner_token_view
from auditmanager.bootstrap.stage_plan_service import StagePlanService
from auditmanager.executors import public as executors_public
from auditmanager.executors.runtime import DestinationPolicy
from auditmanager.runs import public as runs_public
from auditmanager.shared.errors import DomainError, ErrorCode

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
HOST = "exh_01M2545JSD15ETSNNV904X991M"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
TOKEN = "ern_01M2545JSD15ETSNNV904X991K"
TASK = "ext_01M2545JSD15ETSNNV904X991K"
ENROLLMENT = "exe_01M2545JSD15ETSNNV904X991K"
USER = "usr_01M2545JSD15ETSNNV904X991K"
OPUS = "claude-opus-5-5"
SIX = {"provider": "claude_code", "access": "subscription", "model_id": OPUS, "effort": "medium",
       "timeout_seconds": 600, "cell_key": "text:main"}
COMPOSITION = Path(composition.__file__).resolve()


class FakeSession:
    def commit(self) -> None:
        pass

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False


def fake_sessions() -> FakeSession:
    return FakeSession()


HOST_IDENTITY = RunnerIdentity(token_id=TOKEN, connection_id=None, host_id=HOST)
CONNECTION_IDENTITY = RunnerIdentity(token_id=TOKEN, connection_id=CONNECTION)


# --- A, B: the runner seam --------------------------------------------------------------------------------------------------


def test_the_two_identities_name_a_host_and_default_to_none() -> None:
    assert HOST_IDENTITY.host_id == HOST and HOST_IDENTITY.connection_id is None
    assert CONNECTION_IDENTITY.host_id is None and CONNECTION_IDENTITY.connection_id == CONNECTION
    grant = EnrollmentIdentity(enrollment_id=ENROLLMENT, connection_id=None, exchange_key=b"k", host_id=HOST)
    assert grant.host_id == HOST and "k" not in repr(grant), "the exchange key stays out of every repr"
    assert EnrollmentIdentity(enrollment_id=ENROLLMENT, connection_id=CONNECTION, exchange_key=b"k").host_id is None


def test_authenticate_runner_fills_the_host(monkeypatch: pytest.MonkeyPatch) -> None:
    principal = executors_public.RunnerPrincipal(token_id=TOKEN, connection_id=None, host_id=HOST)
    monkeypatch.setattr(executors_public, "authenticate_runner", lambda session, presented, *, address: principal)
    identity = RunnerAdapter(fake_sessions).authenticate_runner("amr_x", address=None)  # type: ignore[arg-type]
    assert identity == HOST_IDENTITY
    legacy = executors_public.RunnerPrincipal(token_id=TOKEN, connection_id=CONNECTION)
    monkeypatch.setattr(executors_public, "authenticate_runner", lambda session, presented, *, address: legacy)
    assert RunnerAdapter(fake_sessions).authenticate_runner("amr_x", address=None) == CONNECTION_IDENTITY  # type: ignore[arg-type]


def test_the_principal_handed_to_the_executors_carries_the_host() -> None:
    principal = RunnerAdapter._principal(HOST_IDENTITY)
    assert (principal.token_id, principal.connection_id, principal.host_id) == (TOKEN, None, HOST)
    legacy = RunnerAdapter._principal(CONNECTION_IDENTITY)
    assert (legacy.connection_id, legacy.host_id) == (CONNECTION, None)


def _record(**more: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "token_id": TOKEN, "connection_id": None, "host_id": HOST, "token_prefix": "amr_abcd1234", "created_at": T0, "created_by": USER,
        "expires_at": T0, "revoked_at": None, "revoked_by": None, "last_seen_at": None, "last_seen_address": None}
    fields.update(more)
    return SimpleNamespace(**fields)


def test_a_token_view_names_exactly_one_of_connection_and_host() -> None:
    host = runner_token_view(_record())
    assert host["host_id"] == HOST and "connection_id" not in host, "the one without a value is absent, never null"
    connection = runner_token_view(_record(connection_id=CONNECTION, host_id=None))
    assert connection["connection_id"] == CONNECTION and "host_id" not in connection
    models.RunnerTokenMetadata.model_validate(host)
    models.RunnerTokenMetadata.model_validate(connection)


def _claimed(**members: Any) -> executors_public.ClaimedTask:
    return executors_public.ClaimedTask(
        task_id=TASK, claim_expires_at=T0, deadline_at=T0, model=OPUS, system="s", user_text="u", output_schema={"type": "object"}, **members)


def test_a_claimed_host_task_reaches_the_wire_with_its_six_members_and_no_answer_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    def claim(factory: Any, principal: Any, **kwargs: Any) -> Any:
        seen.append(principal)
        return _claimed(**SIX)

    monkeypatch.setattr(executors_public, "claim_task", claim)
    task = RunnerAdapter(fake_sessions).claim_task(runner=HOST_IDENTITY, wait_seconds=0)  # type: ignore[arg-type]
    assert task is not None and seen[0].host_id == HOST and seen[0].connection_id is None
    wire = task.model_dump(mode="json", exclude_unset=True)
    for name, value in SIX.items():
        assert wire[name] == value
    assert wire["model"] == wire["model_id"]
    assert "max_output_tokens" not in wire, "`R-153n`: no answer cap on the wire"


def test_a_claimed_legacy_task_carries_none_of_the_members(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(executors_public, "claim_task", lambda *a, **k: _claimed())
    task = RunnerAdapter(fake_sessions).claim_task(runner=CONNECTION_IDENTITY, wait_seconds=0)  # type: ignore[arg-type]
    assert task is not None
    wire = task.model_dump(mode="json", exclude_unset=True)
    assert not set(SIX) & set(wire) - {"model"}, "the earlier wire is unchanged: no host member is sent"


@pytest.mark.parametrize("missing", list(SIX))
def test_a_half_made_host_task_is_never_sent(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    half = {name: value for name, value in SIX.items() if name != missing}
    monkeypatch.setattr(executors_public, "claim_task", lambda *a, **k: _claimed(**half))
    with pytest.raises(DomainError) as refused:
        RunnerAdapter(fake_sessions).claim_task(runner=HOST_IDENTITY, wait_seconds=0)  # type: ignore[arg-type]
    assert refused.value.code is ErrorCode.INTERNAL_ERROR


def test_a_host_answer_reaches_submit_answer_with_its_host_members(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, dict[str, Any]]] = []

    def submit(session: Any, principal: Any, task_id: str, **kwargs: Any) -> Any:
        calls.append((principal, kwargs))
        return SimpleNamespace(task_id=TASK, state="answered")

    monkeypatch.setattr(executors_public, "submit_answer", submit)
    body = models.SubmitExecutorTaskAnswerRequest.model_validate({
        "output_text": "{}", "model": OPUS, "provider": "claude_code", "access": "subscription",
        "reported_model": "claude-opus-5-5-20261001", "usage": {"input_tokens": 12, "output_tokens": 3}})
    ack = RunnerAdapter(fake_sessions).submit_answer(runner=HOST_IDENTITY, task_id=TASK, body=body)  # type: ignore[arg-type]
    assert ack.state.value == "answered"
    principal, kwargs = calls[0]
    assert principal.host_id == HOST
    assert (kwargs["provider"], kwargs["access"], kwargs["reported_model"], kwargs["usage"]) == (
        "claude_code", "subscription", "claude-opus-5-5-20261001", {"input_tokens": 12, "output_tokens": 3})
    assert kwargs["on_mismatch"] is ModelNotTheTasks, "a model that is not the task's keeps the runner's own refusal"


def test_a_legacy_answer_passes_no_host_member(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(executors_public, "submit_answer",
                        lambda session, principal, task_id, **kwargs: calls.append(kwargs) or SimpleNamespace(task_id=TASK, state="answered"))
    body = models.SubmitExecutorTaskAnswerRequest.model_validate({"output_text": "{}", "model": OPUS, "input_tokens": 5, "output_tokens": 2})
    RunnerAdapter(fake_sessions).submit_answer(runner=CONNECTION_IDENTITY, task_id=TASK, body=body)  # type: ignore[arg-type]
    assert calls[0]["provider"] is None and calls[0]["access"] is None and calls[0]["reported_model"] is None and calls[0]["usage"] is None
    assert (calls[0]["input_tokens"], calls[0]["output_tokens"]) == (5, 2)


# --- C: the enrollment adapter ------------------------------------------------------------------------------------------------


class RecordingHosts:
    """The host adapter's two calls a host token makes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def redeem_host_enrollment(self, **kwargs: Any) -> str:
        self.calls.append(("redeem", kwargs))
        return "host-document"

    def report_host_health(self, **kwargs: Any) -> str:
        self.calls.append(("health", kwargs))
        return "host-ack"


def _enrollment(host_id: str | None, connection_id: str | None) -> EnrollmentIdentity:
    return EnrollmentIdentity(enrollment_id=ENROLLMENT, connection_id=connection_id, exchange_key=b"k", host_id=host_id)


def test_a_host_grant_is_redeemed_through_the_host_adapter() -> None:
    hosts = RecordingHosts()
    adapter = ExecutorEnrollmentAdapter(fake_sessions, hosts=hosts)  # type: ignore[arg-type]
    grant = _enrollment(HOST, None)
    assert adapter.redeem_enrollment(enrollment=grant, runner_instance_id="agent-instance-0001") == "host-document"
    assert hosts.calls == [("redeem", {"enrollment": grant, "runner_instance_id": "agent-instance-0001"})]


def test_a_connection_grant_keeps_todays_path_and_adds_the_host_to_its_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    hosts = RecordingHosts()
    principals: list[Any] = []
    redeemed = SimpleNamespace(value="amr_" + "x" * 52, record=_record(connection_id=CONNECTION, host_id=None))

    def redeem(session: Any, principal: Any, *, runner_instance_id: str) -> Any:
        principals.append(principal)
        return redeemed

    monkeypatch.setattr(executors_public, "redeem_enrollment", redeem)
    monkeypatch.setattr(adapters, "_with_runner_health", lambda session, views: views)
    adapter = ExecutorEnrollmentAdapter(fake_sessions, hosts=hosts)  # type: ignore[arg-type]
    adapter.redeem_enrollment(enrollment=_enrollment(None, CONNECTION), runner_instance_id="agent-instance-0001")
    assert hosts.calls == [], "a connection grant never reaches the host adapter"
    assert (principals[0].connection_id, principals[0].host_id) == (CONNECTION, None)


def _health(**more: Any) -> models.ReportRunnerHealthRequest:
    body: dict[str, Any] = {"agent_version": "0.21.0", "clis": [], "concurrency": 1, "execution_profile": "command", "features": []}
    body.update(more)
    return models.ReportRunnerHealthRequest.model_validate(body)


def test_a_host_tokens_report_goes_through_the_host_adapter() -> None:
    hosts = RecordingHosts()
    body = _health()
    adapter = ExecutorEnrollmentAdapter(fake_sessions, hosts=hosts)  # type: ignore[arg-type]
    assert adapter.report_health(runner=HOST_IDENTITY, body=body) == "host-ack"
    assert hosts.calls == [("health", {"runner": HOST_IDENTITY, "body": body})]


@pytest.mark.parametrize(("name", "value"), [
    ("providers", []), ("slots", {"claude_code": 1}),
    ("key_file", {"state": "absent"}),
])
def test_a_connection_token_that_sends_a_host_member_is_refused_before_anything_is_written(name: str, value: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[Any] = []
    monkeypatch.setattr(executors_public, "report_runner_health", lambda *a, **k: written.append(a))
    adapter = ExecutorEnrollmentAdapter(fake_sessions, hosts=RecordingHosts())  # type: ignore[arg-type]
    try:
        body = _health(**{name: value})
    except Exception:  # noqa: BLE001 - a shape the model itself already refuses is not this test's subject
        pytest.skip("the wire model refuses this shape before the adapter does")
    with pytest.raises(DomainError) as refused:
        adapter.report_health(runner=CONNECTION_IDENTITY, body=body)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert refused.value.detail_fields["constraint"] == "host_token_only" and refused.value.detail_fields["field"] == name
    assert written == []


def test_a_host_token_is_refused_typed_when_no_host_adapter_is_wired() -> None:
    adapter = ExecutorEnrollmentAdapter(fake_sessions)  # type: ignore[arg-type]
    with pytest.raises(DomainError) as refused:
        adapter.report_health(runner=HOST_IDENTITY, body=_health())
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and refused.value.detail_fields["dependency"] == "executor_hosts"
    with pytest.raises(DomainError):
        adapter.redeem_enrollment(enrollment=_enrollment(HOST, None), runner_instance_id="agent-instance-0001")


def test_an_enrollment_view_names_exactly_one_of_connection_and_host() -> None:
    base = {"enrollment_id": ENROLLMENT, "secret_prefix": "ame_abcd1234", "state": "pending", "created_at": T0, "created_by": USER,
            "expires_at": T0, "redeemed_at": None, "runner_token_id": None, "revoked_at": None, "revoked_by": None}
    host = _enrollment_view(SimpleNamespace(connection_id=None, host_id=HOST, **base))
    assert host["host_id"] == HOST and "connection_id" not in host
    connection = _enrollment_view(SimpleNamespace(connection_id=CONNECTION, host_id=None, **base))
    assert connection["connection_id"] == CONNECTION and "host_id" not in connection


# --- C: the three start commands and the cost preflight read one layout --------------------------------------------------------------


def _run_adapter(stage_plans: Any) -> RunAdapter:
    return RunAdapter(
        fake_sessions, blob_store=None, adapter=None, provider_config=SimpleNamespace(model_id="m"), provider_mode="live",
        carrier=None, section_profiles={"АР": ("p", "b")}, text_profiles=lambda *a, **k: None,
        stage_plans=stage_plans)  # type: ignore[arg-type]


def test_the_cost_preflight_and_the_adapter_hold_the_same_layout_reader() -> None:
    reader = object()
    adapter = _run_adapter(reader)
    assert adapter.stage_plans is reader
    assert adapter.cost_preflight.stage_plans is reader, "the estimate, the consent and the plan a run freezes are one reading"
    assert _run_adapter(None).cost_preflight.stage_plans is None, "a bare adapter keeps the legacy route"


@pytest.mark.parametrize("method", ["reaudit_run", "start_run_from_stage"])
def test_a_reaudit_and_a_start_from_a_stage_take_the_layout_through_the_run_adapter(method: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.runs import commands

    seen: list[dict[str, Any]] = []

    def command(session: Any, **kwargs: Any) -> Any:
        seen.append(kwargs)
        return SimpleNamespace(run_id="run_X", replayed=True)

    monkeypatch.setattr(commands, method, command)
    monkeypatch.setattr(adapters, "_run_status_view", lambda session, run_id: "view")
    monkeypatch.setattr(ExecutionAdapter, "_roles", staticmethod(lambda session, uid: frozenset({"admin"})))
    reader = object()
    runs = _run_adapter(reader)
    execution = ExecutionAdapter(fake_sessions, runs=runs)  # type: ignore[arg-type]
    arguments = {"run_id": "run_S", "user_uid": USER, "idempotency_key": "k"}
    if method == "start_run_from_stage":
        arguments["stage_id"] = "text_analysis"
    getattr(execution, method)(**arguments)
    assert seen[0]["stage_plans"] is reader


def test_the_composition_root_builds_the_layout_once_and_hands_it_to_the_starts_the_preflight_and_the_adapters() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_application")

    def calls(name: str) -> list[ast.Call]:
        return [node for node in ast.walk(build) if isinstance(node, ast.Call) and ast.unparse(node.func).rsplit(".", 1)[-1] == name]

    def keyword(call: ast.Call, name: str) -> str | None:
        found = [ast.unparse(item.value) for item in call.keywords if item.arg == name]
        return found[0] if found else None

    (service,) = calls("StagePlanService")
    assert keyword(service, "provider_source") == "resolved.provider_source", "the process's own source, never a fresh read of the environment"
    assert keyword(service, "availability") == "HostModelAvailability()"
    (run_adapter,) = calls("RunAdapter")
    assert keyword(run_adapter, "stage_plans") == "stage_plans.freezer"
    (readiness,) = calls("StageModelAdapter")
    assert keyword(readiness, "service") == "stage_plans"
    assert [ast.unparse(node.func) for node in ast.walk(build) if isinstance(node, ast.Call)
            and ast.unparse(node.func) == "stage_plans.attach_cost_preflight"], "the readiness read prices with the preflight the starts bind to"
    (hosts,) = calls("ExecutorHostAdapter")
    assert keyword(hosts, "ring") == "resolved.secrets_public_ring" and keyword(hosts, "public_origin") == "env.get(PUBLIC_ORIGIN_ENV) or None"
    (enrollment,) = calls("ExecutorEnrollmentAdapter")
    assert keyword(enrollment, "hosts") == "host_adapter"
    router = next(node for node in ast.walk(build) if isinstance(node, ast.Call) and ast.unparse(node.func) == "build_router")
    assert keyword(router, "executor_hosts") == "host_adapter", "one host adapter serves the router and the enrollment adapter"


# --- E: the two provider sources ----------------------------------------------------------------------------------------------


def _planned_run() -> SimpleNamespace:
    return SimpleNamespace(run_id="run_P", stage_plan={"cells": []}, connection_revision_id=None, binding_state="bound")


def test_the_environment_source_refuses_a_planned_run_typed_and_never_serves_it_with_its_one_adapter() -> None:
    source = EnvironmentProviders(object(), object(), None)
    for state in ("bound", "pending"):
        run = _planned_run()
        run.binding_state = state
        with pytest.raises(DomainError) as refused:
            source.resolve(None, run, None)  # type: ignore[arg-type]
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert refused.value.detail_fields["dependency"] == "executor_route_missing"
    plain = SimpleNamespace(run_id="run_L", stage_plan=None, connection_revision_id=None, binding_state="frozen_at_start")
    assert source.resolve(None, plain, None) is not None, "a run with no plan is served exactly as before"  # type: ignore[arg-type]


def test_the_database_source_resolves_a_planned_run_per_cell_and_never_by_the_connection_path(monkeypatch: pytest.MonkeyPatch) -> None:
    source = DatabaseProviders(
        ring=None, policy=DestinationPolicy.from_environment({}), base_config=SimpleNamespace(), ceiling_usd=1.0,
        runtime=SimpleNamespace(session_factory=fake_sessions, engine=None))  # type: ignore[arg-type]
    answered = object()
    asked: list[Any] = []
    monkeypatch.setattr(source._planned, "resolve", lambda session, run, context: asked.append((run, context)) or answered)
    run = _planned_run()
    assert source.resolve("session", run, "context") is answered  # type: ignore[arg-type]
    assert asked == [(run, "context")]
    # a run with no plan and no connection is still refused by the connection path, which this branch must not have changed
    with pytest.raises(DomainError):
        source.resolve("session", SimpleNamespace(run_id="run_L", stage_plan=None, connection_revision_id=None), None)  # type: ignore[arg-type]


# --- D: the stage plan service and the availability port ----------------------------------------------------------------------


def test_the_service_takes_its_cost_preflight_once_and_refuses_another() -> None:
    service = StagePlanService(session_factory=fake_sessions, provider_source="database")  # type: ignore[arg-type]
    preflight = object()
    service.attach_cost_preflight(preflight)
    service.attach_cost_preflight(preflight)
    with pytest.raises(ValueError):
        service.attach_cost_preflight(object())


def _layout_fakes() -> Any:
    """LAYOUT's in-memory store, command ledger and availability (a test directory is no package, so by path)."""
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "runs" / "stage_layout_fakes.py"
    spec = importlib.util.spec_from_file_location("hosts_int_wire_stage_layout_fakes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_switch_is_journalled_under_an_identity_the_database_accepts(monkeypatch: pytest.MonkeyPatch) -> None:
    """``audit_event.aggregate_id`` must be an identity (``ck_audit_event_aggregate_id``): the literal ``default`` the service wrote made the database refuse
    **every change of the switch** -- found on a real database by this lane's end-to-end test, invisible to the unit cases that stubbed the journal."""
    import re

    from auditmanager.bootstrap import stage_plan_service as service_module

    fakes = _layout_fakes()
    store = fakes.MemoryStore()
    revision = store.append_revision(None, kit="claude_only", cells=(), created_by=fakes.ADMIN)
    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(service_module, "append_execution_event", lambda session, **kwargs: seen.append(kwargs))
    monkeypatch.setattr(service_module, "_roles", lambda session, uid: fakes.ROLES[uid])
    service = StagePlanService(
        session_factory=fakes.FakeSessions(), store=store, commands=fakes.MemoryCommands(), provider_source="database",
        availability=fakes.everything())
    service.set_layout_enabled(enabled=True, user_uid=fakes.ADMIN, idempotency_key="k-on")
    service.set_layout_enabled(enabled=False, user_uid=fakes.ADMIN, idempotency_key="k-off")
    switched = [item for item in seen if item["event_type"] == "stage_layout.switched"]
    assert [item["payload"]["state"] for item in switched] == ["on", "off"]
    for item in switched:
        assert re.fullmatch(r"[a-z][a-z0-9]{1,7}_[0-9A-HJKMNP-TV-Z]{26}", item["aggregate_id"]), item["aggregate_id"]
        assert item["aggregate_id"] == revision.layout_revision_id, "the switch concerns the revision in force"
        assert re.fullmatch(r"[A-Za-z][A-Za-z0-9]{2,63}", item["aggregate_type"])


def _availability(state: str, access: str, model: str, *reasons: str) -> Any:
    return SimpleNamespace(provider="claude_code", access=access, model_id=model, state=state, reasons=tuple(reasons))


def _read(monkeypatch: pytest.MonkeyPatch, hosts: list[list[Any]]) -> HostModelAvailability:
    monkeypatch.setattr(executors_public, "read_hosts", lambda session: [SimpleNamespace(items=items) for items in hosts])
    monkeypatch.setattr(executors_public, "model_availability", lambda facts: facts.items)
    return HostModelAvailability()


def test_the_availability_port_reads_the_servers(monkeypatch: pytest.MonkeyPatch) -> None:
    port = _read(monkeypatch, [
        [_availability("available", "subscription", "m-a"), _availability("busy", "api", "m-a"),
         _availability("unavailable", "subscription", "m-b", "host_offline", "model_not_verified"),
         _availability("unavailable", "api", "m-c", "host_disabled")],
        [_availability("unavailable", "subscription", "m-b", "model_cooling_down"),
         _availability("available", "api", "m-other")],
    ])
    answer = port.availability(None, ["m-a", "m-b", "m-c", "m-gone"])  # type: ignore[arg-type]
    assert (answer["m-a"].subscription, answer["m-a"].api, answer["m-a"].reasons) == (True, True, ()), "busy is available with every slot taken"
    assert answer["m-b"].access is None and answer["m-b"].reasons == ("model_cooling_down",), "the host closest to serving it speaks"
    assert answer["m-c"].reasons == ("host_disabled",)
    assert "m-gone" not in answer and "m-other" not in answer, "a model no host reports is left out: the port reads it as not on any server"
    assert isinstance(answer["m-a"], runs_public.ModelAvailability)


def test_a_model_served_by_api_only_is_not_a_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    port = _read(monkeypatch, [[_availability("available", "api", "m-a")]])
    found = port.availability(None, ["m-a"])["m-a"]  # type: ignore[arg-type]
    assert (found.subscription, found.api, found.access) == (False, True, "api")
