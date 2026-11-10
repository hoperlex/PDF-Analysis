"""`HOSTS-CMP-01` (ADR-0028 decision 19) on PostgreSQL at head ``0062``: a comparison job started under the stage layout, end to end.

Real rows, real triggers, real locks; no model is called (a scripted adapter answers). One rolled-back connection per test, the sessions of the commands
joined to it by savepoint, as ``test_group_binding.py`` does. The hosts are made by the executors' own public commands (enrollment, redemption, a health
report), so the system connections and the system group of a (model, access) pair are the shipped ones; the layout by the layout store.

What each shows:

1. a start with the layout on is admitted by the **system group** of the cell's model -- a job ``pending`` with that group revision, no connection and no
   rule -- and **freezes the cell**: the estimate, its digest, the stored job and the consent all carry it, and the estimate counts the answer at the cell's
   limit; the job is valid against the generated models;
2. its first dispatched call binds a **server's system connection** (a member with no probe and no runner token of its own is eligible by the server's facts),
   and the request that goes out carries the cell's effort and the cell's limit as a ceiling over the module's own; the journal holds the request that was sent;
3. a subscription serves the kind before an API key; an API key serves it when no subscription does, priced at the group's rates and the cell's limit;
4. a kind whose model no server serves is refused at the estimate and at the start with ``executor_route_missing`` and **creates nothing**, though a legacy
   connection is routed for it and a rule would name a group: it is not routed anywhere else;
5. with the switch off the job is what it always was (``frozen_at_start``, the routed connection, no cell); a kind the layout has no cell of is read as before;
6. a job keeps **its own cell** when the layout is revised afterwards, in a re-estimate of what it has left;
7. the layout the **real service** revises (``StagePlanService`` over the real store, the servers' ``HostModelAvailability``) is the layout the route reads: the cells
   it returns are the cells a start freezes, the cells no server serves are named in ``unavailable_cell_keys``, and the access the availability port reports for
   a model is the access the route is made with.

Break-it-once (the lane's mutation script, in a scratch copy of ``src``): without the third branch of ``estimate.read_route`` tests 1, 2, 3 and 6 fail
(the route is the legacy connection's or ``executor_route_missing``); without the host-aware reading of a system member (``dispatch.member_facts_of``)
test 2 fails (no member is eligible: the call waits ``runner_offline``).
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import CellSettings, ModelRequest
from auditmanager.api.schemas import models
from auditmanager.comparison.ai_jobs.model import AiCallGroup, AiCounts, AiMode
from auditmanager.comparison.ai_jobs.repository import AiJobRepository
from auditmanager.comparison.public import (
    AiConsentInput,
    AiJobCommand,
    AiScope,
    CallEstimate,
    CallRoute,
    ComparisonAiJobService,
    ComparisonModelCaller,
    ComparisonWorkRepository,
    GroupRoutes,
)
from auditmanager.executors import public as ex
from auditmanager.executors.agent_package import AgentPackage
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.stage_layout_store import SqlStageLayoutStore
from auditmanager.shared.errors import DomainError, ErrorCode


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
ai = _load("cmp_ai_jobs_01_support", HERE / "ai_jobs" / "ai_jobs_support.py")

ACTOR = ai.ACTOR
EXPERT = frozenset({"expert"})
ROLES = ("admin",)
ORIGIN = "https://stand.example"
PACKAGE = AgentPackage(version="0.9.0", sha256="a" * 64, size_bytes=1, path=None)  # type: ignore[arg-type]
ASTRA, LUNA, SONNET = "gpt-6-astra", "gpt-6-luna", "claude-sonnet-5-5"
KIND = "comparison_pair_check"
_RUN = uuid.uuid4().hex[:10]
_counter = iter(range(1, 100_000))


def key() -> str:
    return f"cmplr-{_RUN}-{next(_counter):06d}"


@dataclass
class Db:
    connection: Connection
    sessions: "sessionmaker[Session]"
    work: ComparisonWorkRepository

    def one(self, sql: str, **values: Any) -> Any:
        return self.connection.execute(text(sql), values).scalar_one()

    def job(self, job_id: str) -> dict[str, Any]:
        return dict(self.connection.execute(text(
            "SELECT state, binding_state, connection_revision_id, executor_group_revision_id, routing_rule_revision_id, pinned_model, "
            "estimate, estimate_micros, estimate_digest, consent_no FROM comparison_ai_job WHERE comparison_ai_job_id = :j"),
            {"j": job_id}).mappings().one())


@pytest.fixture
def db(comparison_engine: Engine) -> Iterator[Db]:
    connection = comparison_engine.connect()
    outer = connection.begin()
    sessions = sessionmaker(bind=connection, expire_on_commit=False, future=True, join_transaction_mode="create_savepoint")
    try:
        yield Db(connection=connection, sessions=sessions, work=ComparisonWorkRepository())
    finally:
        outer.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def database_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDITMANAGER_PROVIDER_SOURCE", "database")


# -- a server with a verified model, and the layout -----------------------------------------------------------------------------


def report(provider: str, access: str, model: str, *, auth: str = "valid") -> dict[str, Any]:
    slots = 2 if access == "api" else 1
    return {
        "agent_version": "0.21.0", "clis": [{"cli": "codex", "installed": True, "auth_state": auth, "version": "1.0.0"}],
        "concurrency": slots, "execution_profile": "command", "features": [],
        "providers": [{"provider": provider, "access": access, "auth_state": auth, "models": [
            {"model_id": model, "state": "verified", "checked_at": "2026-11-10T12:00:00Z"}]}],
        "slots": {provider: slots},
    }


def server(db: Db, name: str, body: dict[str, Any]) -> str:
    """A server enrolled, redeemed and reported: ``host_id``. Its system connection and the system group of each of its pairs exist afterwards."""
    with db.sessions() as s:
        issued = ex.issue_host_enrollment(
            s, display_name=name, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR, configured_origin=ORIGIN, package_source=lambda: PACKAGE)
        s.commit()
        host_id = str(issued.record.host_id)
        principal = ex.authenticate_enrollment(s, issued.secret)
        assert principal is not None and principal.host_id == host_id
        redeemed = ex.redeem_enrollment(s, principal, runner_instance_id="agent-instance-0001")
        s.commit()
        token, token_id = redeemed.value, redeemed.record.token_id
    with db.sessions() as s:
        runner = ex.authenticate_runner(s, token, address=None)
        assert runner is not None and runner.host_id == host_id
        ex.report_host_runner_health(s, token_id=token_id, host_id=host_id, **body)
        s.commit()
    return host_id


def group_revision_of_pair(db: Db, model: str, access: str) -> str:
    return db.one(
        "SELECT v.group_revision_id FROM executor_group g JOIN executor_group_revision v ON v.group_id = g.group_id "
        "WHERE g.system_managed AND g.archived_at IS NULL AND g.display_name = :n ORDER BY v.revision_no DESC LIMIT 1",
        n=f"{model} · {access}")


def cells(kit: str = "codex_only", **edit: dict[str, Any]) -> tuple[CellSettings, ...]:
    from dataclasses import replace

    return tuple(replace(cell, **edit[cell.row]) if cell.row in edit else cell for cell in layout.comparison_preset_cells(kit))


def layout_on(db: Db, kit: str = "codex_only", comparison: tuple[CellSettings, ...] | None = None, *, on: bool = True) -> Any:
    store = SqlStageLayoutStore()
    with db.sessions() as s:
        store.lock(s)
        row = store.append_revision(
            s, kit=kit, cells=layout.preset_cells(kit), created_by=ACTOR, **({} if comparison is None else {"comparison_cells": comparison}))
        if on:
            store.append_switch(s, enabled=True, set_by=ACTOR)
        s.commit()
    return row


# -- the service and the call ---------------------------------------------------------------------------------------------------


def big_counts() -> AiCounts:
    """Ten calls that the module would let answer 8192 tokens: the cell's limit is what is counted."""
    return AiCounts(groups=(AiCallGroup(calls=10, prompt_chars=4_000, output_tokens=8_192, images=2, image_bytes=200_000),), units=10)


@dataclass
class Scene:
    db: Db
    world: dict[str, Any]
    scope: AiScope
    service: ComparisonAiJobService
    worker_id: str

    def command(self) -> AiJobCommand:
        return AiJobCommand(command_type="start_comparison_ai_pair_check", idempotency_key=ai.new_id("k")[:32], user_uid=ACTOR, actor_roles=EXPERT)

    def start(self) -> Any:
        digest = self.service.estimate(self.scope).estimate_digest
        return self.service.start(
            scope=self.scope, consent=AiConsentInput(estimate_digest=digest, confirmed=True), command=self.command())

    def claim(self) -> Any:
        with self.db.sessions() as session:
            item = self.db.work.claim(session, worker_id=self.worker_id, modules=frozenset({"versions"}), kinds=frozenset({KIND}))
            session.commit()
        assert item is not None, "the job queued no item"
        return item


def scene(db: Db) -> Scene:
    from auditmanager.workers.public import WorkerRegistry

    world = ai.new_world(db.connection)
    method = ai.FakeMethod(method="pair_check", counts_default=big_counts())
    service = ComparisonAiJobService(db.sessions, methods=[method], work=db.work, comparison_modules="versions", provider_mode="live")
    with db.sessions() as session:
        worker_id = WorkerRegistry().register(session, version="cmp-layout-route-test", slots=1)
        session.commit()
    return Scene(
        db=db, world=world, service=service, worker_id=worker_id,
        scope=AiScope(method="pair_check", project_uid=world["project"], document_uid=world["document"], matrix_id=world["build"]))


class Adapter(ai.ScriptedLiveAdapter):
    pass


class Members:
    """The composition root's binder, as a test: the route of the member the job is bound to, over a scripted adapter that remembers its requests."""

    def __init__(self, adapter: Adapter, *, unmetered: bool) -> None:
        self.adapter, self.unmetered = adapter, unmetered
        self.pin = next(pin for pin in ex.pinned_models() if pin.model_id == ASTRA)

    def route(self, session: Any, job: Any) -> CallRoute:
        return CallRoute(
            adapter=self.adapter, model_identity=job.pinned_model, connection_revision_id=job.connection_revision_id,
            expected_model=ASTRA, check_identity=True, unmetered=self.unmetered, pin=self.pin)

    route_for = route


def module_request() -> ModelRequest:
    """What a method builds: its own effort and its own limit, which the cell then holds to."""
    return ModelRequest(model_id=ASTRA, body={
        "model": ASTRA, "max_tokens": 8_192, "messages": [{"role": "user", "content": "q"}],
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": {"type": "object"}}}})


def a_call(s: Scene, item: Any, adapter: Adapter, *, unmetered: bool) -> Any:
    """What a handler does for one call: the job, its consent and its route in one unit of work, then the call through the wrapper."""
    from auditmanager.comparison.ai_jobs.repository import AiJobRepository as Jobs

    routes = GroupRoutes(Members(adapter, unmetered=unmetered), jobs=Jobs())
    job_id = item.payload["ai_job_id"]
    with s.db.sessions() as session:
        s.service.mark_running(session, job_id)
        job = s.service.job(session, job_id)
        consent = s.service.consent_for_calls(session, job_id)
        route = routes.route(session, job)
        session.commit()
    return ComparisonModelCaller(s.db.sessions, offline_wait_seconds=1800).call(
        item, route, module_request(), estimate=CallEstimate(input_tokens=4_800, output_tokens=8_192), consent=consent)


# -- 1. admission ---------------------------------------------------------------------------------------------------------------


def test_a_start_with_the_layout_on_is_admitted_by_the_system_group_and_freezes_the_cell(db: Db) -> None:
    server(db, "layout-1", report("codex", "api", ASTRA))
    cell = CellSettings(f"{KIND}:main", ASTRA, "medium", 900, 600)
    layout_on(db, "codex_only", cells(comparison_pair_check={"effort": "medium", "max_output_tokens": 900, "timeout_seconds": 600}))
    s = scene(db)
    group_revision = group_revision_of_pair(db, ASTRA, "api")

    estimate = s.service.estimate(s.scope)
    route = estimate.route
    assert route.executor_group_revision_id == group_revision and route.connection_id is None and route.routing_rule_revision_id is None
    assert (route.pinned_model, route.billing, route.cell) == (ASTRA, "metered", cell)
    assert estimate.totals.output_tokens == 10 * 900, "the estimate counts the answer at the cell's limit, not the module's 8192"
    assert estimate.estimate_micros > 0
    shown = models.ComparisonAiEstimate.model_validate(estimate.as_dict())
    assert shown.route.cell is not None and shown.route.cell.work_kind.value == KIND and shown.route.cell.max_output_tokens == 900

    view = s.start()
    stored = db.job(view.record.job_id)
    assert (stored["state"], stored["binding_state"], stored["connection_revision_id"]) == ("queued", "pending", None)
    assert (stored["executor_group_revision_id"], stored["routing_rule_revision_id"], stored["pinned_model"]) == (group_revision, None, ASTRA)
    assert stored["estimate"]["route"]["cell"] == {
        "work_kind": KIND, "model_id": ASTRA, "effort": "medium", "max_output_tokens": 900, "timeout_seconds": 600}
    assert stored["estimate_digest"] == estimate.estimate_digest and stored["estimate_micros"] == estimate.estimate_micros
    assert view.record.cell == cell

    with db.sessions() as session:
        consent = s.service.consent_for_calls(session, view.record.job_id)
    assert (consent.executor_group_revision_id, consent.connection_revision_id, consent.pinned_model) == (group_revision, None, ASTRA)
    assert consent.cell == cell and consent.estimate_digest == estimate.estimate_digest, "the consent names the group revision and the cell"
    job = models.ComparisonAiJob.model_validate(view.as_dict())
    assert job.binding_state.value == "pending" and str(job.planned.executor_group_revision_id) == group_revision
    assert job.estimate.route.cell is not None and job.estimate.route.cell.effort.value == "medium"


# -- 2. the first call ---------------------------------------------------------------------------------------------------------


def test_the_first_call_binds_a_servers_system_connection_and_sends_the_cells_effort_and_limit(db: Db) -> None:
    host = server(db, "layout-2", report("codex", "subscription", ASTRA))
    layout_on(db, "codex_only", cells(comparison_pair_check={"effort": "medium", "max_output_tokens": 900, "timeout_seconds": 600}))
    s = scene(db)
    job_id = s.start().record.job_id
    adapter = Adapter(reply=ai.live_reply(cost=None, tokens=(1_000, 200), model=ASTRA))

    result = a_call(s, s.claim(), adapter, unmetered=True)

    assert result.call_id and len(adapter.requests) == 1
    sent = adapter.requests[0]
    assert sent.body["max_tokens"] == 900, "the cell's limit is a ceiling over the module's 8192"
    assert sent.body["output_config"]["effort"] == "medium" and sent.body["output_config"]["format"]["type"] == "json_schema"
    bound = db.job(job_id)
    assert bound["binding_state"] == "bound" and bound["connection_revision_id"] is not None
    pool = db.one(
        "SELECT c.capacity_pool FROM executor_connection c JOIN executor_connection_revision r ON r.connection_id = c.connection_id "
        "WHERE r.revision_id = :r", r=bound["connection_revision_id"])
    assert pool == f"{host}:codex", "a member with no probe and no runner token of its own was eligible by the server's facts"
    journal = db.connection.execute(text(
        "SELECT c.request_sha256, c.state FROM comparison_model_call c JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id "
        "WHERE w.comparison_ai_job_id = :j"), {"j": job_id}).all()
    assert [(row[0], row[1]) for row in journal] == [(sent.request_sha256, "completed")], "the journal holds the request that went out"


# -- 3. the access --------------------------------------------------------------------------------------------------------------


def test_a_subscription_serves_the_kind_before_an_api_key_and_an_api_key_when_no_subscription_does(db: Db) -> None:
    server(db, "layout-3a", report("codex", "api", ASTRA))
    layout_on(db, "codex_only", cells())
    s = scene(db)
    api_only = s.service.estimate(s.scope).route
    assert (api_only.billing, api_only.executor_group_revision_id) == ("metered", group_revision_of_pair(db, ASTRA, "api"))
    server(db, "layout-3b", report("codex", "subscription", ASTRA))
    both = s.service.estimate(s.scope).route
    assert (both.billing, both.executor_group_revision_id) == ("not_metered", group_revision_of_pair(db, ASTRA, "subscription"))
    unmetered = s.service.estimate(s.scope)
    assert unmetered.estimate_micros == 0, "a subscription is counted and never charged"


# -- 4. nothing serves the model -----------------------------------------------------------------------------------------------


def test_a_kind_whose_model_no_server_serves_is_refused_and_creates_nothing_and_is_not_routed_elsewhere(db: Db) -> None:
    layout_on(db, "codex_only", cells())
    route = ai.recorded_route(db.connection, KIND, billing="metered")  # the legacy connection that would have served it
    s = scene(db)
    before = db.one("SELECT count(*) FROM comparison_ai_job")
    for refuse in (lambda: s.service.estimate(s.scope),
                   lambda: s.service.start(scope=s.scope, consent=AiConsentInput(estimate_digest="ab" * 32, confirmed=True), command=s.command())):
        with pytest.raises(DomainError) as refused:
            refuse()
        assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and refused.value.detail_fields["dependency"] == "executor_route_missing"
    assert db.one("SELECT count(*) FROM comparison_ai_job") == before, "a refused start writes nothing"
    assert route.revision_id, "the legacy route exists, and was not used"


# -- 5. the switch off ---------------------------------------------------------------------------------------------------------


def test_with_the_switch_off_the_job_is_what_it_always_was(db: Db) -> None:
    layout_on(db, "codex_only", cells(), on=False)  # a revision exists, the switch was never turned on
    server(db, "layout-5", report("codex", "api", ASTRA))
    route = ai.recorded_route(db.connection, KIND, billing="metered")
    s = scene(db)
    view = s.start()
    stored = db.job(view.record.job_id)
    assert (stored["binding_state"], stored["connection_revision_id"], stored["executor_group_revision_id"]) == ("frozen_at_start", route.revision_id, None)
    assert "cell" not in stored["estimate"]["route"] and view.record.cell is None
    with db.sessions() as session:
        assert s.service.consent_for_calls(session, view.record.job_id).cell is None


# -- 6. a job keeps its own cell -----------------------------------------------------------------------------------------------


def test_a_job_keeps_its_own_cell_when_the_layout_is_revised_afterwards(db: Db) -> None:
    server(db, "layout-6", report("codex", "api", ASTRA))
    layout_on(db, "codex_only", cells(comparison_pair_check={"effort": "medium", "max_output_tokens": 900}))
    s = scene(db)
    started = s.start().record
    layout_on(db, "codex_only", cells(comparison_pair_check={"effort": "low", "max_output_tokens": 300}), on=False)  # the layout moves on
    assert s.service.estimate(AiScope(method="pair_check", project_uid=s.world["project"], document_uid=s.world["document"],
                                      matrix_id=s.world["build"])).route.cell.effort == "low", "a new start reads the layout in force"
    with db.sessions() as session:
        again = s.service.estimate_in(session, s.scope, AiMode.LEFT, job=s.service.job(session, started.job_id))
    assert again.route.cell == started.cell and again.route.cell.effort == "medium" and again.totals.output_tokens == 10 * 900
    assert again.route.executor_group_revision_id == started.executor_group_revision_id


# -- 7. the real service writes what the route reads ---------------------------------------------------------------------------


def test_the_layout_the_real_service_revises_is_the_layout_the_route_reads_and_the_availability_agrees_with_the_route(db: Db) -> None:
    from auditmanager.access.public import AccountRepository, UserRepository
    from auditmanager.bootstrap.hosts_dispatch import HostModelAvailability
    from auditmanager.bootstrap.stage_plan_service import StagePlanService

    with db.sessions() as session:
        admin = str(UserRepository().create_user(session, "cmp-layout-" + uuid.uuid4().hex, "layout-test-password").user_uid)
        AccountRepository().grant_role(session, user_uid=admin, role="admin", granted_by=None)
        session.commit()
    server(db, "layout-7", report("codex", "api", LUNA))
    service = StagePlanService(session_factory=db.sessions, availability=HostModelAvailability(), provider_source="database")
    wire = layout.comparison_cells_to_wire(cells(comparison_pair_check={"effort": "medium", "max_output_tokens": 900}))
    # « Свой набор »: a named set must keep its table's models and efforts, and the medium effort of the pair check is the owner's own choice
    body = models.ReviseStageModelLayoutRequest.model_validate({
        "kit": "custom", "cells": layout.cells_to_wire(layout.preset_cells("codex_only")), "comparison_cells": wire})
    service.revise_layout(body=body, user_uid=admin, idempotency_key=key())
    view = service.set_layout_enabled(enabled=True, user_uid=admin, idempotency_key=key())

    shown = models.StageModelLayout.model_validate(view)
    assert shown.enabled and [item.work_kind.value for item in shown.current.comparison_cells] == list(layout.COMPARISON_KINDS)
    assert shown.current.comparison_cells[0].effort.value == "medium" and shown.current.comparison_cells[0].max_output_tokens == 900
    unserved = set(view["unavailable_cell_keys"])
    assert "comparison_pair_check:main" not in unserved and "comparison_spec:main" not in unserved, "gpt-6-luna is on the server: the pair check and the specification of « Только Codex » name it (R-153m)"
    assert {"comparison_sheet_changes:main", "comparison_report:main"} <= unserved, "gpt-6.1-sol is on no server: named, as the rows' cells are"

    s = scene(db)
    with db.sessions() as session:
        port = HostModelAvailability().availability(session, [LUNA])[LUNA]
    assert (port.subscription, port.api, port.access) == (False, True, "api")
    route = s.service.estimate(s.scope).route
    assert (route.billing, route.cell.effort, route.cell.max_output_tokens) == ("metered", "medium", 900), "the access of the port, the cell of the revision"
    server(db, "layout-7b", report("codex", "subscription", LUNA))
    with db.sessions() as session:
        port = HostModelAvailability().availability(session, [LUNA])[LUNA]
    assert (port.subscription, port.access) == (True, "subscription")
    assert s.service.estimate(s.scope).route.billing == "not_metered", "a subscription, once one serves the model, for the route as for the port"
    # the kind whose model no server serves is refused through the same layout
    sheet_scope = AiScope(method="sheet_changes", project_uid=s.world["project"], document_uid=s.world["document"], series_id=s.world["series"])
    sheets = ComparisonAiJobService(
        db.sessions, methods=[ai.FakeMethod(method="sheet_changes")], work=db.work, comparison_modules="versions", provider_mode="live")
    with pytest.raises(DomainError) as refused:
        sheets.estimate(sheet_scope)
    assert refused.value.detail_fields["dependency"] == "executor_route_missing"
