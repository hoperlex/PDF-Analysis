"""`HOSTS-INT-WIRE-01` on PostgreSQL: a run on the stage layout, end to end through the wiring the integrator added.

One throwaway database, committed rows (the claim, the binding, the pull task and the answer are each their own transaction, as in service). The path:

1. **a server is connected through the adapters** -- the host grant authenticates as an enrollment that names a host (``EnrollmentIdentity.host_id``), is
   redeemed through ``ExecutorEnrollmentAdapter`` -> ``ExecutorHostAdapter`` (the host token, its host and the catalogue), the token authenticates as a
   ``RunnerIdentity`` that names the host, and a health report with ``providers[]`` and ``slots`` goes through ``report_health`` to the host adapter: the
   host has two members (Opus and Sonnet by subscription);
2. **the layout is on** -- an administrator revises it and switches it on through ``StagePlanService`` (its journal is the database's: the event's identity
   is held to ``ck_audit_event_aggregate_id``, which is how this test found the literal the service used to write there); the freezer reads the servers
   through ``HostModelAvailability`` and freezes a plan, every cell on a subscription. The layout's **store** is the in-memory one of
   ``tests/unit/runs/stage_layout_fakes.py`` on purpose: revisions are immutable rows, and ``tests/integration/runs/test_stage_plan_db.py`` (the SQL store's
   own cases) starts from an empty store -- a committed revision of this test would break it whenever it runs after;
3. **the run is bound** -- the claim binds every cell to a member of the host, once;
4. **each cell is called by its own model** -- ``DatabaseProviders.resolve`` of the planned run answers one adapter and one ``CallBinding`` per cell;
   the call is written as a task carrying the seven members of *its* cell, claimed through the host token, and journaled on the member that serves it;
5. **the identity check holds** -- an answer whose reported model is an alias of the catalogue's list is accepted, one that names another model is refused
   (and the task keeps its claim), a declared model that is not the task's is refused.

The same suite proves the sources: with the switch off a start reads no plan (the legacy route), and the ``environment`` source refuses a planned run.
"""

from __future__ import annotations

import importlib.util
import json
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.analysis.public import ModelRequest, ProviderConfig, ProviderMode, accepted_reported
from auditmanager.api.routers.runner import ModelNotTheTasks
from auditmanager.api.schemas import models
from auditmanager.bootstrap.hosts_adapter import ExecutorHostAdapter
from auditmanager.bootstrap.hosts_dispatch import HostModelAvailability
from auditmanager.bootstrap.providers import DatabaseProviders, EnvironmentProviders
from auditmanager.bootstrap.runner import RunnerAdapter
from auditmanager.bootstrap.stage_plan_service import StagePlanService
from auditmanager.bootstrap.adapters import ExecutorEnrollmentAdapter
from auditmanager.executors import public as ex
from auditmanager.executors.agent_package import AgentPackage
from auditmanager.executors.runner import RunnerPrincipal, claim_task
from auditmanager.executors.runtime import DestinationPolicy, KindRuntime
from auditmanager.jobs.repository import JobRepository
from auditmanager.runs import RunRepository
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.public import call_journal_columns
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AnalysisProfileId, DocumentUid, ProjectUid, PromptBundleId, RunId, VersionUid

ORIGIN = "https://stand.example"
PACKAGE = AgentPackage(version="0.9.0", sha256="a" * 64, size_bytes=1, path=None)  # type: ignore[arg-type]
OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
_counter = iter(range(1, 10_000))
_RUN = uuid.uuid4().hex[:10]
SCHEMA = {"type": "object", "properties": {"observations": {"type": "array"}}, "required": ["observations"], "additionalProperties": False}


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _key() -> str:
    return f"hosts-int-wire-{_RUN}-{next(_counter):06d}"


@pytest.fixture
def admin(sessions: sessionmaker[Session]) -> str:
    with sessions() as s:
        uid = str(UserRepository().create_user(s, "wire-" + uuid.uuid4().hex, "wire-test-password").user_uid)
        AccountRepository().grant_role(s, user_uid=uid, role="admin", granted_by=None)
        s.commit()
    return uid


@pytest.fixture(autouse=True)
def _isolated(sessions: sessionmaker[Session], admin: str) -> Iterator[None]:
    """No live job and no live host before and after, so the system group of a (model, access) pair is the test's alone."""
    def clean() -> None:
        with sessions() as s:
            for (run_id,) in s.execute(text("SELECT run_id FROM job WHERE state NOT IN ('succeeded', 'failed', 'cancelled', 'dead_letter')")).all():
                JobRepository().cancel_for_run(s, run_id=run_id)
            s.commit()
        with sessions() as s:
            for host in ex.read_hosts(s):
                ex.archive_host(s, host_id=host.record.host_id, roles=("admin",), idempotency_key=_key(), actor_uid=admin)
            s.commit()

    clean()
    yield
    clean()


def _report(*models_: tuple[str, str]) -> dict[str, Any]:
    return {
        "agent_version": "0.21.0",
        "clis": [{"cli": "claude", "installed": True, "auth_state": "valid", "version": "1.0.0"}],
        "concurrency": 1, "execution_profile": "command", "features": [],
        "providers": [{"provider": "claude_code", "access": "subscription", "auth_state": "valid", "cli_version": "1.0.0", "models": [
            {"model_id": model, "state": state, "checked_at": "2026-11-10T12:00:00Z"} for model, state in models_]}],
        "slots": {"claude_code": 1},
    }


class Server:
    """A host connected the way an agent connects: through the adapters the router calls."""

    def __init__(self, sessions: sessionmaker[Session], admin: str, name: str, report: dict[str, Any]) -> None:
        self.sessions = sessions
        self.hosts = ExecutorHostAdapter(sessions, public_origin=ORIGIN)
        self.enrollment = ExecutorEnrollmentAdapter(sessions, public_origin=ORIGIN, hosts=self.hosts)
        self.runner = RunnerAdapter(sessions)
        with sessions() as s:
            issued = ex.issue_host_enrollment(s, display_name=name, roles=("admin",), idempotency_key=_key(), actor_uid=admin,
                                              configured_origin=ORIGIN, package_source=lambda: PACKAGE)
            s.commit()
            self.host_id = str(issued.record.host_id)
        grant = self.enrollment.authenticate_enrollment(issued.secret)
        assert grant is not None and grant.host_id == self.host_id and grant.connection_id is None, "the grant names the host"
        document = self.enrollment.redeem_enrollment(enrollment=grant, runner_instance_id="agent-instance-0001")
        assert document.host_id is not None and str(document.host_id) == self.host_id and document.catalogue, "the host token, its host and the catalogue"
        self.token = document.token
        self.identity = self.runner.authenticate_runner(self.token, address=None)
        assert self.identity is not None and self.identity.host_id == self.host_id and self.identity.connection_id is None
        self.report(report)

    def report(self, body: dict[str, Any]) -> models.RunnerHealthAck:
        ack = self.enrollment.report_health(runner=self.identity, body=models.ReportRunnerHealthRequest.model_validate(body))
        assert ack.enabled is True and ack.catalogue, "a host token's report is answered with the catalogue and the switch"
        return ack

    def principal(self) -> RunnerPrincipal:
        return RunnerPrincipal(token_id=self.identity.token_id, connection_id=None, host_id=self.host_id)


def _layout_fakes() -> Any:
    path = Path(__file__).resolve().parents[2] / "unit" / "runs" / "stage_layout_fakes.py"
    spec = importlib.util.spec_from_file_location("hosts_int_wire_stage_layout_fakes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enable_layout(sessions: sessionmaker[Session], admin: str) -> StagePlanService:
    fakes = _layout_fakes()
    service = StagePlanService(
        session_factory=sessions, store=fakes.MemoryStore(), commands=fakes.MemoryCommands(), availability=HostModelAvailability(),
        provider_source="database")
    body = models.ReviseStageModelLayoutRequest.model_validate({"kit": "claude_only", "cells": layout.cells_to_wire(layout.preset_cells("claude_only"))})
    service.revise_layout(body=body, user_uid=admin, idempotency_key=_key())
    assert service.set_layout_enabled(enabled=True, user_uid=admin, idempotency_key=_key())["enabled"] is True
    return service


def _planned_run(sessions: sessionmaker[Session], plan: dict[str, Any]) -> str:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "version": str(VersionUid.new()), "run": str(RunId.new())}
    with sessions() as s:
        s.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'wire')"), ids)
        s.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'D')"), ids)
        s.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
                       "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
        s.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, "
            "frozen_input_digest, binding_state, stage_plan) VALUES (:run, :project, :version, :profile, :bundle, 'live', :digest, "
            "'pending', CAST(:plan AS jsonb))"),
            {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()), "digest": "b" * 64, "plan": json.dumps(plan)})
        RunRepository().advance(s, run_id=ids["run"], from_state="created", to_state="queued")
        JobRepository().enqueue(s, run_id=ids["run"])
        s.commit()
    return ids["run"]


class Call:
    """One model call in a daemon thread: a failing test must not wait out the call's deadline (half an hour) when the interpreter exits."""

    def __init__(self, adapter: Any, request: ModelRequest) -> None:
        self.response: Any = None
        self.error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, args=(adapter, request), daemon=True)
        self._thread.start()

    def _run(self, adapter: Any, request: ModelRequest) -> None:
        try:
            self.response = adapter.complete(request)
        except BaseException as failure:  # noqa: BLE001 - handed to the test thread
            self.error = failure

    def done(self) -> bool:
        return not self._thread.is_alive()

    def result(self, timeout: float) -> Any:
        self._thread.join(timeout)
        assert self.done(), "the call is still waiting for its answer"
        if self.error is not None:
            raise self.error
        return self.response


def _request(cell_model: str) -> ModelRequest:
    return ModelRequest(model_id=cell_model, body={
        "system": "you answer with one JSON document", "messages": [{"role": "user", "content": "an observation, please"}],
        "output_config": {"format": {"schema": SCHEMA}}, "max_tokens": 1000})


def _claim_one(sessions: sessionmaker[Session], server: Server, seconds: float = 20.0) -> Any:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        claimed = claim_task(sessions, server.principal(), wait_seconds=0, runner_instance_id="agent-instance-0001")
        if claimed is not None:
            return claimed
        time.sleep(0.2)
    raise AssertionError("the host token claimed nothing: the cell's call never became a task of this host")


def _answer(server: Server, task_id: str, *, model: str, reported: str, usage: tuple[int, int] = (120, 30)) -> Any:
    body = models.SubmitExecutorTaskAnswerRequest.model_validate({
        "output_text": json.dumps({"observations": []}), "model": model, "provider": "claude_code", "access": "subscription",
        "reported_model": reported, "usage": {"input_tokens": usage[0], "output_tokens": usage[1]}})
    return server.runner.submit_answer(runner=server.identity, task_id=task_id, body=body)


def test_a_run_on_the_stage_layout_is_bound_called_by_each_cells_model_and_held_to_the_exact_reported_model(
    sessions: sessionmaker[Session], engine: Engine, admin: str,
) -> None:
    server = Server(sessions, admin, "wire-1", _report((OPUS, "verified"), (SONNET, "verified")))
    service = _enable_layout(sessions, admin)

    # 2. the layout is on: the freezer reads the servers and freezes every cell on a subscription
    with sessions() as s:
        draft = service.freezer(s)
        assert draft is not None, "with the switch on a start reads the layout"
        plan = draft.freeze(layout.STAGE_ROWS)
    assert {cell.access for cell in plan.cells} == {"subscription"} and {cell.model_id for cell in plan.cells} == {OPUS, SONNET}
    run = _planned_run(sessions, plan.to_json())

    # 3. the claim binds every cell to a member of the host, once
    with sessions() as s:
        authority = JobRepository().start_execution(s, run_id=run)
        s.commit()
    with sessions() as s:
        bound = {cell.cell_key: ex.cell_binding_of(s, run, cell.cell_key) for cell in plan.cells}
    assert all(item is not None and item.host_id == server.host_id and item.access == "subscription" for item in bound.values())
    assert {key: item.model_id for key, item in bound.items()} == {cell.cell_key: cell.model_id for cell in plan.cells}, "each cell's own member"
    assert len({item.connection_revision_id for item in bound.values()}) == 2, "two members: one per model"

    # 4. each cell is called by its own model
    providers = DatabaseProviders(
        ring=None, policy=DestinationPolicy.from_environment({}), ceiling_usd=1.0, runtime=KindRuntime(session_factory=sessions, engine=engine),
        base_config=ProviderConfig(mode=ProviderMode.LIVE, model_id=SONNET, run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=True))
    context = SimpleNamespace(run_id=run, attempt_id=authority.attempt_id, call_id=None, remaining_seconds=lambda: 3000.0, progress=lambda: None,
                              bind_call=lambda call_id: None)
    with sessions() as s:
        binding = providers.resolve(s, RunRepository().get(s, run), context)
        by_cell = {cell.cell_key: binding.cells(cell.cell_key) for cell in plan.cells}
    for cell in plan.cells:
        one = by_cell[cell.cell_key]
        assert (one.call.expected_model, one.call.cell_key, one.call.access, one.call.host_id, one.call.unmetered, one.call.check_identity) == (
            cell.model_id, cell.cell_key, "subscription", server.host_id, True, True)
        assert one.call.connection_revision_id == bound[cell.cell_key].connection_revision_id and one.call.identity_basis == "declared"
        assert one.config.model_id == cell.model_id and one.config.cell_settings == cell
    assert by_cell["text:main"].call.expected_model == SONNET and by_cell["blocks:leg1"].call.expected_model == OPUS, "not one model for the run"

    for cell_key, model in (("text:main", SONNET), ("blocks:leg1", OPUS)):
        cell = next(item for item in plan.cells if item.cell_key == cell_key)
        one = by_cell[cell_key]
        with sessions() as s:  # the journal, as the runs layer writes it: the columns the call binding names
            call_id = JobRepository().prepare_provider_call(
                s, authority, provider=one.call.provider_label, model_identity=model, provider_mode="live", parameters={},
                request_sha256=uuid.uuid4().hex + uuid.uuid4().hex, connection_revision_id=one.call.connection_revision_id,
                identity_basis=one.call.identity_basis, **call_journal_columns(one.call))
            s.commit()
            row = s.execute(text("SELECT host_id, access, stage_key, connection_revision_id, identity_basis FROM provider_call_effect "
                                 "WHERE model_call_id = :c"), {"c": str(call_id)}).one()
        assert tuple(row) == (server.host_id, "subscription", cell_key.partition(":")[0], bound[cell_key].connection_revision_id, "declared")

        waiting = Call(one.adapter, _request(model))
        claimed = _claim_one(sessions, server)
        assert (claimed.provider, claimed.access, claimed.model_id, claimed.effort, claimed.max_output_tokens, claimed.cell_key) == (
            "claude_code", "subscription", model, cell.effort, cell.max_output_tokens, cell_key), "the task carries the cell's own settings"
        assert claimed.model == model and claimed.timeout_seconds == cell.timeout_seconds

        # 5. the identity check: another model is refused and the task keeps its claim; a declared model that is not the task's is refused
        other = SONNET if model == OPUS else OPUS
        with pytest.raises(ModelNotTheTasks):
            _answer(server, claimed.task_id, model=model, reported=other)
        with pytest.raises(ModelNotTheTasks):
            _answer(server, claimed.task_id, model=other, reported=model)
        with sessions() as s:
            assert s.execute(text("SELECT state FROM executor_task WHERE task_id = :t"), {"t": claimed.task_id}).scalar_one() == "claimed"
        assert not waiting.done(), "a refused answer ends nothing: the call still waits for the member's answer"

        alias = f"{model}[1m]"
        assert accepted_reported(model, alias), "the alias is on the catalogue's list for this model"
        assert _answer(server, claimed.task_id, model=model, reported=alias).state.value == "answered"
        response = waiting.result(timeout=30)
        assert response.model == alias and accepted_reported(one.call.expected_model, response.model)
        assert (response.input_tokens, response.output_tokens) == (120, 30)


def test_with_the_switch_off_a_start_reads_no_plan_and_the_environment_source_refuses_a_planned_run(
    sessions: sessionmaker[Session], admin: str,
) -> None:
    service = StagePlanService(session_factory=sessions, availability=HostModelAvailability(), provider_source="database")
    with sessions() as s:
        assert service.freezer(s) is None, "the legacy route: no plan is read, none is frozen"
    # a planned run reaching a process of the environment source is refused, typed, never served by its one adapter
    with sessions() as s:
        planned = SimpleNamespace(run_id="run_P", stage_plan={"cells": []}, connection_revision_id=None, binding_state="bound")
        with pytest.raises(DomainError) as refused:
            EnvironmentProviders(object(), object(), None).resolve(s, planned, None)
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_a_model_no_host_serves_refuses_the_freeze_and_names_no_substitute(sessions: sessionmaker[Session], admin: str) -> None:
    Server(sessions, admin, "wire-2", _report((SONNET, "verified"), (OPUS, "not_verified")))
    service = _enable_layout(sessions, admin)
    with sessions() as s:
        draft = service.freezer(s)
        assert draft is not None
        assert draft.availability_of(SONNET).access == "subscription"
        assert draft.availability_of(OPUS).access is None and draft.availability_of(OPUS).reasons == ("model_not_verified",)
        with pytest.raises(DomainError) as refused:
            draft.freeze(layout.STAGE_ROWS)
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE, "no cell is dropped and no other model is put in its place"


def test_a_host_tokens_report_needs_its_providers(sessions: sessionmaker[Session], admin: str) -> None:
    """The host adapter takes the host token's report, and a host token that sends none of the host's members is refused (``required``)."""
    server = Server(sessions, admin, "wire-3", _report((SONNET, "verified")))
    body = _report((SONNET, "verified"))
    del body["providers"], body["slots"]
    with pytest.raises(DomainError) as refused:
        server.enrollment.report_health(runner=server.identity, body=models.ReportRunnerHealthRequest.model_validate(body))
    assert refused.value.code is ErrorCode.VALIDATION_FAILED and refused.value.detail_fields["field"] == "providers"
    assert refused.value.detail_fields["constraint"] == "required"
