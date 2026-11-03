"""`EXEC2-GROUP-CMP-01` (ADR-0026 decisions 12 to 16): comparison AI jobs admitted by a rule or a group, over real PostgreSQL at head
``0048``.

Written and **not run** in EXEC-2 (`R-149d`, D-292); every test needs PostgreSQL (the ``comparison_engine`` fixture of this directory fails,
it never skips, without ``DATABASE_URL``). Two kinds:

* the first block works on one connection inside an outer transaction that is rolled back, with the session factory joining it by savepoint
  (the harness of ``ai_jobs/conftest.py``): a command runs as production runs it -- its own unit of work, its own commit -- and nothing stays
  in the lane's database. The groups, members, rules and routing-mode events are made by the executors' own public commands, so the
  group machinery under test is the shipped one;
* the last test commits (two threads need two connections) and cleans up after itself like ``spend/``: it fakes the *group's rows* (a group row
  cannot be deleted) and keeps the journal, the day lock and the advisory locks real.

What each shows (ADR-0026 decision in brackets):

1.  a start under mode ``rules`` stores the job ``pending`` with the rule and group revision and no connection, priced at the group's
    model and rates, the plan in the response (13); a work kind without a rule is the typed refusal and creates nothing (17, 18); mode
    ``legacy`` is untouched, a rule that exists is not read (17);
2.  the first dispatched call binds the job to an eligible member -- the binding, its event and the journal row of the call in one
    transaction -- and later calls stay (14, 16); the member's unit is counted for the call and for no other member (14);
3.  waiting is durable and visible: for capacity without end, for an executor until the offline wait is over, then the job ends
    ``failed`` / ``no_executor_online`` through its own failure path (15);
4.  a consent that does not hold calls nothing, records ``needs_reconsent`` and pauses for a new consent, which then goes on (14);
5.  a resume after ``overrun`` keeps the bound member, and the database refuses every other write of the revision (12, 16);
6.  ``not_metered`` is shown as such: an estimate of 0 and a journal row ``unmetered``, never a price of zero (14);
7.  two dispatches decided at once under the USD 50 day ceiling: room for one (14).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas import models
from auditmanager.comparison.ai_jobs.model import AiJobRecord
from auditmanager.comparison.ai_jobs.repository import AiJobRepository
from auditmanager.comparison.public import (
    AiConsentInput,
    AiJobCommand,
    AiScope,
    CallEstimate,
    CallRefused,
    CallRoute,
    ComparisonAiJobService,
    ComparisonModelCaller,
    ComparisonSpendRepository,
    ComparisonWorkRepository,
    Consent,
    GroupRoutes,
    OutcomeUnknown,
)
from auditmanager.comparison.spend import dispatch
from auditmanager.executors.public import (
    GroupSettings,
    MemberFacts,
    MemberRequest,
    RevisionSettings,
    create_connection,
    create_group,
    issue_runner_token,
    pinned_models,
    record_probe_result,
    record_probe_started,
    request_probe,
    revise_connection,
    set_routing_rule,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorRoutingModeEventId, new_ulid


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
spend = _load("cmp_spend_01_spend_support", HERE / "spend" / "spend_support.py")
limits = _load("exec_par_queue_connection_limit_support", HERE.parent / "jobs" / "connection_limit_support.py")

ACTOR = ai.ACTOR
ADMIN_ROLES = frozenset({"admin"})
EXPERT = frozenset({"expert"})
WORK_KIND = "comparison_pair_check"
SONNET = "claude-sonnet-5"
PIN_IDS = {pin.model_id for pin in pinned_models()}
SONNET_PIN = next(pin for pin in pinned_models() if pin.model_id == SONNET)
USD = 1_000_000


def key() -> str:
    return f"cmpgb-{uuid.uuid4().hex}"


# --- the harness: one rolled-back connection, sessions joined by savepoint -----------------------------------------------------


@dataclass
class Db:
    connection: Connection
    sessions: "sessionmaker[Session]"
    work: ComparisonWorkRepository

    def one(self, sql: str, **values: Any) -> Any:
        return self.connection.execute(text(sql), values).scalar_one()

    def row(self, sql: str, **values: Any) -> dict[str, Any]:
        return dict(self.connection.execute(text(sql), values).mappings().one())

    def job(self, job_id: str) -> dict[str, Any]:
        return self.row(
            "SELECT state, pause_reason, failure_reason, binding_state, connection_revision_id, executor_group_revision_id, "
            "routing_rule_revision_id, wait_reason, waiting_since, consent_no, estimate_micros, ceiling_micros, pinned_model, estimate "
            "FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job_id)

    def seed(self, run: Callable[[Session], Any]) -> Any:
        with self.sessions() as session:
            found = run(session)
            session.commit()
        return found


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


def settings(*, billing: str = "metered", capacity: int = 2) -> RevisionSettings:
    return RevisionSettings(
        pin_id=SONNET, gateway_model=SONNET, billing=billing, allow_client_documents=False, timeout_seconds=600,
        pull_client="claude_code_session", answer_deadline_seconds=600, max_claimed_tasks=capacity, max_active_runs=capacity,
    )


def member(db: Db, name: str, *, online: bool = True, billing: str = "metered", capacity: int = 2) -> tuple[str, str]:
    """A ``pull`` connection that dispatch would choose: probed ``ok`` on its current revision and, when ``online``, a runner seen
    a few seconds ago. ``(connection_id, revision_id)``."""

    def run(session: Session) -> tuple[str, str]:
        connection_id = create_connection(
            session, kind="pull", display_name=name, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ACTOR).connection_id
        revision = revise_connection(
            session, connection_id=connection_id, settings=settings(billing=billing, capacity=capacity),
            pinned_model_ids=PIN_IDS, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ACTOR)
        probe = request_probe(session, connection_id=connection_id, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ACTOR)
        assert record_probe_started(session, probe.probe_id)
        assert record_probe_result(
            session, probe.probe_id, outcome="ok", reported_model=SONNET, identity_basis="declared",
            rate_check="not_metered" if billing == "not_metered" else "checked")
        if online:
            token = issue_runner_token(
                session, connection_id=connection_id, expires_in_days=None, roles=ADMIN_ROLES, idempotency_key=key(),
                actor_uid=ACTOR).record.token_id
            session.execute(text(
                "UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - make_interval(secs => 5) WHERE token_id = :id"),
                {"id": token})
        return connection_id, revision.revision_id

    return db.seed(run)


def group_of(db: Db, name: str, *members: tuple[str, str], billing: str = "metered") -> tuple[str, str]:
    """A group of ``members`` and its first revision: ``(group_id, group_revision_id)``."""

    def run(session: Session) -> tuple[str, str]:
        made = create_group(
            session, display_name=name, settings=GroupSettings(pin_id=SONNET, gateway_model=SONNET, billing=billing, strategy="least_loaded"),
            members=[MemberRequest(connection_id, revision_id) for connection_id, revision_id in members], pins=pinned_models(),
            roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ACTOR)
        return made.group.group_id, made.current_revision.group_revision_id

    return db.seed(run)


def rule_for(db: Db, group_revision_id: str, work_kind: str = WORK_KIND) -> str:
    def run(session: Session) -> str:
        return set_routing_rule(
            session, work_kind=work_kind, group_revision_id=group_revision_id, roles=ADMIN_ROLES, idempotency_key=key(),
            actor_uid=ACTOR).rule_revision_id

    return db.seed(run)


def rules_mode(db: Db) -> None:
    """The cut-over, as the journal records it (the command that makes this event is `EXEC2-CUTOVER-01`'s)."""
    db.connection.execute(text(
        "INSERT INTO executor_routing_mode_event (mode_event_id, event_no, mode, preview_digest, mapping, changed_by) "
        "SELECT CAST(:id AS text), COALESCE(MAX(event_no), 0) + 1, 'rules', CAST(:digest AS text), CAST(:mapping AS jsonb), "
        "CAST(:actor AS text) FROM executor_routing_mode_event"
    ), {"id": str(ExecutorRoutingModeEventId.new()), "digest": "cd" * 32, "mapping": json.dumps([{"work_kind": WORK_KIND}]), "actor": ACTOR})


@dataclass
class Scene:
    db: Db
    world: dict[str, Any]
    scope: AiScope
    service: ComparisonAiJobService
    method: Any
    members: list[tuple[str, str]]
    group_id: str
    group_revision_id: str
    rule_revision_id: str
    worker_id: str

    def command(self, kind: str = "start_comparison_ai_pair_check") -> AiJobCommand:
        return AiJobCommand(command_type=kind, idempotency_key=ai.new_id("k")[:32], user_uid=ACTOR, actor_roles=EXPERT)

    def start(self) -> Any:
        digest = self.service.estimate(self.scope).estimate_digest
        return self.service.start(
            scope=self.scope, consent=AiConsentInput(estimate_digest=digest, confirmed=True), command=self.command())

    def claim(self) -> Any:
        with self.db.sessions() as session:
            item = self.db.work.claim(
                session, worker_id=self.worker_id, modules=frozenset({"versions"}), kinds=frozenset({WORK_KIND}))
            session.commit()
        assert item is not None, "the job queued no item"
        return item

    def resume_consent(self) -> AiConsentInput:
        return AiConsentInput(estimate_digest=self.service.estimate(self.scope).estimate_digest, confirmed=True)


def scene(db: Db, *, members: int = 2, online: bool = True, billing: str = "metered", capacity: int = 2, mode: bool = True) -> Scene:
    from auditmanager.workers.public import WorkerRegistry

    world = ai.new_world(db.connection)
    made = [member(db, f"member-{index}", online=online, billing=billing, capacity=capacity) for index in range(members)]
    group_id, group_revision_id = group_of(db, f"pool-{uuid.uuid4().hex[:8]}", *made, billing=billing)
    rule_revision_id = rule_for(db, group_revision_id)
    if mode:
        rules_mode(db)
    method = ai.FakeMethod(method="pair_check")
    service = ComparisonAiJobService(
        db.sessions, methods=[method], work=db.work, comparison_modules="versions", provider_mode="live")
    with db.sessions() as session:
        worker_id = WorkerRegistry().register(session, version="cmp-group-binding-test", slots=1)
        session.commit()
    return Scene(
        db=db, world=world,
        scope=AiScope(method="pair_check", project_uid=world["project"], document_uid=world["document"], matrix_id=world["build"]),
        service=service, method=method, members=made, group_id=group_id, group_revision_id=group_revision_id,
        rule_revision_id=rule_revision_id, worker_id=worker_id)


class Adapter(ai.ScriptedLiveAdapter):
    """A scripted live adapter that can look at the database from inside the call (what a crash at that instant leaves)."""

    def __init__(self, reply: Any, inside: Callable[[], None] | None = None) -> None:
        super().__init__(reply=reply)
        self.inside = inside

    def complete(self, request: Any) -> Any:
        if self.inside is not None:
            self.inside()
        return super().complete(request)


class Members:
    """The composition root's binder, as a test: the route of the member the job is bound to, over a scripted adapter."""

    def __init__(self, adapter: Adapter, *, unmetered: bool = False) -> None:
        self.adapter, self.unmetered, self.opened = adapter, unmetered, []

    def route(self, session: Any, job: AiJobRecord) -> CallRoute:
        self.opened.append((job.binding_state, job.connection_revision_id))
        return CallRoute(
            adapter=self.adapter, model_identity=job.pinned_model, connection_revision_id=job.connection_revision_id,
            expected_model=SONNET, check_identity=True, unmetered=self.unmetered, pin=SONNET_PIN)

    route_for = route


def reply(*, cost: float | None = None) -> Any:
    return ai.live_reply(cost=cost, tokens=(1000, 200), model=SONNET)


def first_call(s: Scene, item: Any, routes: GroupRoutes, *, caller: ComparisonModelCaller | None = None, label: str = "q") -> Any:
    """What a handler does for one call: the job, its consent and its route in one unit of work, then the call through the wrapper."""
    job_id = item.payload["ai_job_id"]
    with s.db.sessions() as session:
        s.service.mark_running(session, job_id)
        job = s.service.job(session, job_id)
        consent = s.service.consent_for_calls(session, job_id)
        route = routes.route(session, job)
        session.commit()
    return (caller or ComparisonModelCaller(s.db.sessions, offline_wait_seconds=1800)).call(
        item, route, ai.request_for(label), estimate=CallEstimate(input_tokens=4800, output_tokens=1000), consent=consent)


def refuse(s: Scene, item: Any, routes: GroupRoutes, **kw: Any) -> CallRefused:
    """A call that must be refused; what the handler does about it is the job layer's answer to the refusal."""
    with pytest.raises(CallRefused) as refused:
        first_call(s, item, routes, **kw)
    if refused.value.pauses_job:
        with s.db.sessions() as session:
            s.service.pause_for_spend(session, item.payload["ai_job_id"], refused.value.reason)
            session.commit()
    return refused.value


def routes_over(adapter: Adapter, **kw: Any) -> tuple[GroupRoutes, Members]:
    members = Members(adapter, **kw)
    return GroupRoutes(members, jobs=AiJobRepository()), members


# --- 1. admission: the estimate and the consent (decisions 13, 17 and 18) ------------------------------------------------------


def test_a_start_under_rules_stores_the_job_pending_with_the_group_and_no_connection(db: Db) -> None:
    s = scene(db)
    estimate = s.service.estimate(s.scope)
    assert estimate.route.executor_group_revision_id == s.group_revision_id and estimate.route.routing_rule_revision_id == s.rule_revision_id
    assert (estimate.route.pinned_model, estimate.route.billing, estimate.route.connection_id) == (SONNET, "metered", None)
    assert estimate.estimate_micros > 0 and estimate.ceiling_micros == 10 * USD, "a metered group is priced at its pin's rates"
    shown = models.ComparisonAiEstimate.model_validate(estimate.as_dict())
    assert str(shown.route.executor_group_id) == s.group_id and shown.route.connection_id is None and shown.route.revision_id is None

    view = s.start()
    job = db.job(view.record.job_id)
    assert (job["binding_state"], job["connection_revision_id"], job["wait_reason"], job["waiting_since"]) == ("pending", None, None, None)
    assert (job["executor_group_revision_id"], job["routing_rule_revision_id"], job["pinned_model"]) == (
        s.group_revision_id, s.rule_revision_id, SONNET)
    assert (job["estimate_micros"], job["consent_no"], job["state"]) == (estimate.estimate_micros, 1, "queued")
    assert job["estimate"]["route"]["executor_group_revision_id"] == s.group_revision_id and "connection_id" not in job["estimate"]["route"]
    assert db.one("SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id = :j", j=view.record.job_id) == 3

    shown_job = models.ComparisonAiJob.model_validate(view.as_dict())
    assert shown_job.binding_state.value == "pending" and shown_job.binding is None
    assert str(shown_job.planned.executor_group_revision_id) == s.group_revision_id
    assert (shown_job.planned.pin_id, shown_job.planned.billing.value) == (SONNET, "metered")
    assert shown_job.wait_reason is None
    queued = models.ComparisonAiQueueItem.model_validate(view.as_queue_item())
    assert queued.binding_state.value == "pending"


def test_a_work_kind_without_a_rule_under_rules_is_a_typed_refusal_and_creates_nothing(db: Db) -> None:
    s = scene(db, mode=False)
    rules_mode(db)  # the rule of one kind exists (pair_check); the kind asked about below has none
    other = ai.FakeMethod(method="spec")
    spec_scope = AiScope(method="spec", project_uid=s.world["project"], document_uid=s.world["document"], transition_id=s.world["transition"])
    service = ComparisonAiJobService(db.sessions, methods=[other], work=db.work, comparison_modules="versions", provider_mode="live")
    before = db.one("SELECT count(*) FROM comparison_ai_job")
    with pytest.raises(DomainError) as refused:
        service.estimate(spec_scope)
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE and refused.value.detail_fields["dependency"] == "no_rule_for_work_kind"
    with pytest.raises(DomainError) as started:
        service.start(scope=spec_scope, consent=AiConsentInput(estimate_digest="ab" * 32, confirmed=True), command=s.command("start_comparison_specification"))
    assert started.value.detail_fields["dependency"] == "no_rule_for_work_kind"
    assert db.one("SELECT count(*) FROM comparison_ai_job") == before, "a refused start writes nothing"


def test_mode_legacy_is_the_primary_route_frozen_at_start_and_a_rule_that_exists_is_not_read(db: Db) -> None:
    s = scene(db, mode=False)  # a group and a rule exist; the journal says nothing: legacy
    route = ai.recorded_route(db.connection, WORK_KIND, billing="metered")
    view = s.start()
    job = db.job(view.record.job_id)
    assert job["binding_state"] == "frozen_at_start" and job["connection_revision_id"] == route.revision_id
    assert (job["executor_group_revision_id"], job["routing_rule_revision_id"]) == (None, None)
    document = view.as_dict()
    assert "binding_state" not in document and "planned" not in document and "binding" not in document
    assert document["estimate"]["route"]["connection_id"] == route.connection_id and "executor_group_id" not in document["estimate"]["route"]


# --- 2. the first dispatched call binds (decisions 14 and 16) ---------------------------------------------------------------------


def test_the_first_call_binds_the_job_to_an_eligible_member_and_its_later_calls_stay(db: Db) -> None:
    s = scene(db)
    job_id = s.start().record.job_id
    db.connection.execute(text("UPDATE executor_group SET rotation_cursor = 1 WHERE group_id = :g"), {"g": s.group_id})
    first, second = s.claim(), s.claim()
    seen: dict[str, Any] = {}

    def inside() -> None:
        with db.sessions() as session:
            from auditmanager.executors.public import occupancies

            seen["used"] = {cid: o.used for cid, o in occupancies(session, [m[0] for m in s.members]).items()}

    adapter = Adapter(reply(), inside)
    routes, opened = routes_over(adapter)
    result = first_call(s, first, routes)
    assert result.cost_basis in ("measured", "estimated") and adapter.requests

    bound = db.job(job_id)
    chosen = next(m for m in s.members if m[1] == bound["connection_revision_id"])
    assert bound["binding_state"] == "bound" and bound["wait_reason"] is None and bound["consent_no"] == 1
    assert bound["connection_revision_id"] in {revision for _, revision in s.members}
    assert db.one("SELECT rotation_cursor FROM executor_group WHERE group_id = :g", g=s.group_id) == 2, "the dispatch advanced the persisted rotation"
    assert db.one("SELECT connection_revision_id FROM comparison_model_call WHERE comparison_work_id = :w", w=first.work_id) == chosen[1]
    assert seen["used"] == {chosen[0]: 1, **{cid: 0 for cid, _ in s.members if cid != chosen[0]}}, (
        "the call is one unit of the member it was sent to and of no other")
    events = db.connection.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'executor.comparison_job_bound' AND aggregate_id = :j"), {"j": job_id}).all()
    assert len(events) == 1 and dict(events[0][0]) == {
        "job_id": job_id, "connection_id": chosen[0], "revision_id": chosen[1], "work_kind": WORK_KIND, "from_state": "pending",
        "to_state": "bound"}
    assert opened.opened == [("bound", chosen[1])], "the member's route is opened for the job as it will be once bound"

    again = first_call(s, second, routes, label="r")
    assert db.job(job_id)["connection_revision_id"] == chosen[1] and again.call_id
    assert db.one("SELECT count(*) FROM audit_event WHERE event_type = 'executor.comparison_job_bound' AND aggregate_id = :j", j=job_id) == 1
    assert {row[0] for row in db.connection.execute(text(
        "SELECT c.connection_revision_id FROM comparison_model_call c JOIN comparison_work w "
        "ON w.comparison_work_id = c.comparison_work_id WHERE w.comparison_ai_job_id = :j"), {"j": job_id})} == {chosen[1]}

    view = s.service.view(job_id)
    shown = models.ComparisonAiJob.model_validate(view.as_dict())
    assert shown.binding_state.value == "bound" and shown.binding.display_name.startswith("member-")
    assert (str(shown.binding.connection_id), str(shown.binding.connection_revision_id), shown.binding.pin_id) == (chosen[0], chosen[1], SONNET)
    assert shown.planned is not None and shown.wait_reason is None


def test_the_least_loaded_member_is_the_one_that_binds(db: Db) -> None:
    s = scene(db)
    job_id = s.start().record.job_id
    busy = s.claim()
    ai.insert_call(db.connection, busy, state="sent", revision_id=s.members[0][1])  # one of the first member's two units is in use
    mine = s.claim()
    first_call(s, mine, routes_over(Adapter(reply()))[0])
    assert db.job(job_id)["connection_revision_id"] == s.members[1][1]


def test_the_database_writes_the_connection_revision_once_and_to_a_member_only(db: Db) -> None:
    s = scene(db)
    job_id = s.start().record.job_id
    stranger = limits.new_connection(db.sessions)  # a connection that is not a member of the job's group
    repository = AiJobRepository()
    with db.sessions() as session:
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                repository.bind(session, job_id, connection_revision_id=stranger[1])
        assert repository.bind(session, job_id, connection_revision_id=s.members[0][1]) is True
        assert repository.bind(session, job_id, connection_revision_id=s.members[1][1]) is False, "a bound job is not bound again"
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("UPDATE comparison_ai_job SET connection_revision_id = :r WHERE comparison_ai_job_id = :j"),
                                {"r": s.members[1][1], "j": job_id})
        session.commit()
    assert db.job(job_id)["connection_revision_id"] == s.members[0][1]


# --- 3. waiting is durable and visible (decision 15) ---------------------------------------------------------------------------------


def test_a_job_with_no_member_online_waits_visibly_and_ends_no_executor_online_after_the_wait(db: Db) -> None:
    s = scene(db, online=False)
    job_id = s.start().record.job_id
    item = s.claim()
    routes, _ = routes_over(Adapter(reply()))
    waiting = refuse(s, item, routes)
    assert (waiting.reason, waiting.pauses_job) == ("connection_busy", False)
    job = db.job(job_id)
    assert (job["wait_reason"], job["state"], job["binding_state"]) == ("runner_offline", "running", "pending")
    assert job["waiting_since"] is not None
    shown = models.ComparisonAiJob.model_validate(s.service.view(job_id).as_dict())
    assert shown.wait_reason.value == "runner_offline" and shown.waiting_since is not None

    refuse(s, item, routes)
    assert db.job(job_id)["waiting_since"] == job["waiting_since"], "the clock runs on while the reason stays"

    db.connection.execute(text(
        "UPDATE comparison_ai_job SET waiting_since = waiting_since - interval '29 minutes' WHERE comparison_ai_job_id = :j"), {"j": job_id})
    assert refuse(s, item, routes).reason == "connection_busy", "29 minutes is not longer than 30"

    db.connection.execute(text(
        "UPDATE comparison_ai_job SET waiting_since = waiting_since - interval '2 minutes' WHERE comparison_ai_job_id = :j"), {"j": job_id})
    ended = refuse(s, item, routes)
    assert (ended.reason, ended.pauses_job) == ("no_executor_online", True)
    job = db.job(job_id)
    assert (job["state"], job["failure_reason"], job["wait_reason"], job["waiting_since"]) == ("failed", "no_executor_online", None, None)
    assert db.one(
        "SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id = :j AND terminal_at IS NULL AND comparison_work_id <> :w",
        j=job_id, w=item.work_id) == 0, "the job's own failure path cancels what is left"
    assert db.one("SELECT cancel_requested_at IS NOT NULL FROM comparison_work WHERE comparison_work_id = :w", w=item.work_id), (
        "and asks the item in hand to stop")


def test_a_job_whose_members_are_full_waits_for_capacity_without_end(db: Db) -> None:
    s = scene(db, members=1, capacity=1)
    job_id = s.start().record.job_id
    occupier, mine = s.claim(), s.claim()
    ai.insert_call(db.connection, occupier, state="sent", revision_id=s.members[0][1])
    routes, _ = routes_over(Adapter(reply()))
    assert refuse(s, mine, routes).reason == "connection_busy"
    assert db.job(job_id)["wait_reason"] == "executor_at_capacity"
    db.connection.execute(text(
        "UPDATE comparison_ai_job SET waiting_since = waiting_since - interval '10 days' WHERE comparison_ai_job_id = :j"), {"j": job_id})
    aged = db.job(job_id)["waiting_since"]
    assert refuse(s, mine, routes).reason == "connection_busy"
    after = db.job(job_id)
    assert (after["state"], after["wait_reason"], after["waiting_since"]) == ("running", "executor_at_capacity", aged), "no end, and the clock is not restarted"
    assert not db.one("SELECT count(*) FROM comparison_model_call WHERE comparison_work_id = :w", w=mine.work_id)


# --- 4. a consent that does not hold (decision 14) -----------------------------------------------------------------------------------


def test_a_consent_that_does_not_hold_calls_nothing_records_needs_reconsent_and_pauses_for_a_new_one(db: Db) -> None:
    s = scene(db)
    job_id = s.start().record.job_id
    item = s.claim()
    # The stored figure is no longer what the group's rate snapshot prices the stored estimate at (a new consent number, as the trigger wants).
    db.connection.execute(text(
        "UPDATE comparison_ai_job SET estimate_micros = estimate_micros + 1, consent_no = consent_no + 1 WHERE comparison_ai_job_id = :j"), {"j": job_id})
    adapter = Adapter(reply())
    routes, _ = routes_over(adapter)
    refused = refuse(s, item, routes)
    assert (refused.reason, refused.pauses_job) == ("consent_stale", True)
    job = db.job(job_id)
    assert (job["state"], job["pause_reason"], job["wait_reason"], job["binding_state"]) == ("paused", "route_changed", "needs_reconsent", "pending")
    assert adapter.requests == [] and not db.one("SELECT count(*) FROM comparison_model_call WHERE comparison_work_id = :w", w=item.work_id)
    assert db.one("SELECT rotation_cursor FROM executor_group WHERE group_id = :g", g=s.group_id) == 0, "nothing was dispatched"
    shown = models.ComparisonAiJob.model_validate(s.service.view(job_id).as_dict())
    assert shown.wait_reason.value == "needs_reconsent"

    resumed = s.service.resume(
        job_id=job_id, method="pair_check", command=s.command("resume_comparison_ai_pair_check"), consent=s.resume_consent())
    job = db.job(job_id)
    assert (resumed.record.state, job["wait_reason"], job["waiting_since"], job["consent_no"]) == ("queued", None, None, 3)
    assert job["connection_revision_id"] is None and job["binding_state"] == "pending"

    again = s.claim()
    first_call(s, again, routes)
    assert db.job(job_id)["binding_state"] == "bound", "the job goes on under the new consent"


# --- 5. no re-routing (decision 16) ----------------------------------------------------------------------------------------------------


def test_a_resume_after_overrun_keeps_the_bound_member_and_the_database_refuses_another(db: Db) -> None:
    s = scene(db)
    job_id = s.start().record.job_id
    routes, _ = routes_over(Adapter(reply()))
    first_call(s, s.claim(), routes)
    bound = db.job(job_id)["connection_revision_id"]
    other = next(revision for _, revision in s.members if revision != bound)

    with db.sessions() as session:
        assert s.service.pause_for_spend(session, job_id, "overrun") is True
        session.commit()
    resumed = s.service.resume(
        job_id=job_id, method="pair_check", command=s.command("resume_comparison_ai_pair_check"), consent=s.resume_consent())
    job = db.job(job_id)
    assert (resumed.record.state, job["consent_no"], job["binding_state"], job["connection_revision_id"]) == ("queued", 2, "bound", bound)
    assert job["executor_group_revision_id"] == s.group_revision_id, "re-estimated on the job's own group revision"

    with db.sessions() as session:
        for column, value in (("connection_revision_id", other), ("pinned_model", "claude-opus-5")):
            with pytest.raises(DBAPIError):
                with session.begin_nested():
                    session.execute(text(f"UPDATE comparison_ai_job SET {column} = :v, consent_no = consent_no + 1 "
                                         "WHERE comparison_ai_job_id = :j"), {"v": value, "j": job_id})
        session.commit()
    assert db.job(job_id)["connection_revision_id"] == bound


def test_an_unknown_outcome_is_never_sent_to_another_member(db: Db) -> None:
    s = scene(db)
    job_id = s.start().record.job_id
    first, second = s.claim(), s.claim()

    def boom() -> None:
        raise RuntimeError("the connection dropped")

    routes, _ = routes_over(Adapter(reply(), boom))
    with pytest.raises(OutcomeUnknown):
        first_call(s, first, routes)
    bound = db.job(job_id)["connection_revision_id"]
    assert bound is not None and db.one("SELECT state FROM comparison_model_call WHERE comparison_work_id = :w", w=first.work_id) == "unknown"
    # the next call of the job goes to the same member, although the other is idle
    working, _ = routes_over(Adapter(reply()))
    first_call(s, second, working, label="r")
    assert db.one("SELECT connection_revision_id FROM comparison_model_call WHERE comparison_work_id = :w", w=second.work_id) == bound


# --- 6. not_metered is shown as such (decision 14) -----------------------------------------------------------------------------------


def test_a_not_metered_group_shows_no_price_and_its_call_is_journalled_unmetered(db: Db) -> None:
    s = scene(db, billing="not_metered")
    view = s.start()
    job_id = view.record.job_id
    document = view.as_dict()
    assert document["estimate"]["estimate_micros"] == 0 and document["estimate"]["ceiling_micros"] == 0
    assert document["planned"]["billing"] == "not_metered"
    item = s.claim()
    routes, _ = routes_over(Adapter(reply()), unmetered=True)
    result = first_call(s, item, routes)
    assert (result.cost_basis, result.cost_micros) == ("unmetered", 0) and result.pause is None
    row = db.row("SELECT estimate_micros, cost_basis, cost_micros, connection_revision_id FROM comparison_model_call WHERE comparison_work_id = :w", w=item.work_id)
    assert (row["estimate_micros"], row["cost_basis"], row["cost_micros"]) == (0, "unmetered", 0) and row["connection_revision_id"] is not None
    assert db.job(job_id)["binding_state"] == "bound"


# --- 7. two dispatches decided at once under the day ceiling (decision 14) ---------------------------------------------------------------


@pytest.fixture
def committed(comparison_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=comparison_engine, expire_on_commit=False, future=True)


@pytest.fixture
def worker(committed: sessionmaker[Session]) -> Iterator[str]:
    from auditmanager.workers.public import WorkerRegistry

    with committed() as session:
        made = WorkerRegistry().register(session, version="cmp-group-binding-race", slots=1)
        session.commit()
    yield made
    with committed() as session:
        session.execute(text("DELETE FROM worker WHERE worker_id = :w"), {"w": made})
        session.commit()


@pytest.fixture
def project(committed: sessionmaker[Session], worker: str) -> Iterator[str]:
    project_uid = f"prj_{new_ulid()}"
    with committed() as session:
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'cmp-group-binding test')"), {"p": project_uid})
        session.commit()
    try:
        yield project_uid
    finally:
        with committed() as session:
            session.execute(text(
                "DELETE FROM comparison_model_call WHERE comparison_work_id IN "
                "(SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p)"), {"p": project_uid})
            session.execute(text(
                "DELETE FROM executor_task WHERE comparison_attempt_id IN "
                "(SELECT a.comparison_work_attempt_id FROM comparison_work_attempt a JOIN comparison_work w "
                "ON w.comparison_work_id = a.comparison_work_id WHERE w.project_uid = :p)"), {"p": project_uid})
            session.execute(text(
                "DELETE FROM comparison_work_attempt WHERE comparison_work_id IN "
                "(SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p)"), {"p": project_uid})
            session.execute(text("DELETE FROM comparison_work WHERE project_uid = :p"), {"p": project_uid})
            session.execute(text("DELETE FROM project WHERE project_uid = :p"), {"p": project_uid})
            session.commit()


def test_two_dispatches_decided_at_once_cannot_both_fit_the_one_call_that_fits_under_the_day_ceiling(
    committed: sessionmaker[Session], worker: str, project: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two jobs, each admitted by a group of its own, are dispatched at the same instant with room under USD 50 for one 6.00 call.
    Each group has its own member, so the members' locks do not meet: the day lock does. The second reads the day after the first has
    committed its ``prepared`` row and is refused ``day_ceiling`` -- before its job is bound. The groups' rows are stood in for (a group
    cannot be deleted); the journal, the day lock, the advisory locks and the transaction are the database's."""
    from auditmanager.executors import public
    from auditmanager.jobs import public as jobs_public

    queue = spend.Queue(committed, project, f"gb_{uuid.uuid4().hex[:16]}", worker)
    journal = spend.Journal(committed)
    with committed() as session:
        others = session.execute(text(
            "SELECT count(*) FROM comparison_model_call c JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id "
            "WHERE w.project_uid <> :p AND c.prepared_at >= (date_trunc('day', clock_timestamp() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')"
        ), {"p": project}).scalar_one()
    assert others == 0, "another project has journalled calls today; the day ceiling needs an empty day"

    connections = [limits.new_connection(committed) for _ in range(2)]
    for number in range(4):                                         # 4 x 10.00 = 40.00 spent today
        other = queue.claimed(ai_job_id=f"job-fill-{number}")
        journal.insert(other.work_id, other.attempt_id, connection_revision_id=connections[0][1], cost_micros=10 * USD)

    groups = {f"exgr_{name}": (f"exg_{name}", connection) for name, connection in zip("AB", connections)}
    revisions = {
        revision_id: SimpleNamespace(
            group_revision_id=revision_id, group_id=group_id, revision_no=1, pin_id=spend.MODEL, gateway_model=spend.GATEWAY,
            billing="metered", input_per_mtok_usd=Decimal("1.0"), output_per_mtok_usd=Decimal("5.0"), strategy="least_loaded",
            members=(SimpleNamespace(connection_id=connection[0], connection_revision_id=connection[1], tie_break_order=None),))
        for revision_id, (group_id, connection) in groups.items()
    }
    monkeypatch.setattr(public, "group_revision_of", lambda session, revision_id, groups=None: revisions.get(revision_id))
    monkeypatch.setattr(public, "member_facts", lambda session, revision, repository=None: [
        MemberFacts(connection_id=m.connection_id, tie_break_order=None, revision_is_snapshot=True, archived=False, served=True,
                    probed_ok=True, runner_online=True, capacity=2, used=0) for m in revision.members])
    monkeypatch.setattr(public, "current_revision", lambda session, connection_id, repository=None: next(
        SimpleNamespace(revision_id=c[1], connection_id=c[0], settings=SimpleNamespace(
            pin_id=spend.MODEL, gateway_model=spend.GATEWAY, billing="metered")) for c in connections if c[0] == connection_id))
    monkeypatch.setattr(public, "advance_group_rotation", lambda session, group_id, groups=None: 1)
    monkeypatch.setattr(jobs_public, "append_execution_event", lambda session, **kw: None)

    class FakeJobs:
        """The job rows, in memory: the binding is the wrapper's to ask for; a bind that is asked for is a bind that was decided."""

        def __init__(self) -> None:
            self.records = {
                name: AiJobRecord(
                    job_id=f"job-{name}", project_uid=project, document_uid="doc_x", method="pair_check", state="running",
                    pause_reason=None, failure_reason=None, matrix_id="cmx_x", series_id=None, transition_id=None,
                    sheet_pair_id=None, restart=False, connection_revision_id=None, pinned_model=spend.MODEL, provider_mode="live",
                    estimate={"input_tokens": 1_000_000, "output_tokens": 1_000_000, "route": {
                        "pinned_model": spend.MODEL, "billing": "metered", "provider_mode": "live",
                        "executor_group_id": f"exg_{name}", "executor_group_revision_id": f"exgr_{name}"}},
                    estimate_digest=spend.DIGEST, estimate_micros=6 * USD, ceiling_micros=10 * USD, consent_no=1,
                    consented_by_user_uid=ACTOR, consented_at=None, command_id="cmd_x", created_at=None, updated_at=None,
                    finished_at=None, binding_state="pending", executor_group_revision_id=f"exgr_{name}")
                for name in "AB"}
            self.binds: list[str] = []

        def get(self, session: Any, job_id: str, *, lock: bool = False) -> AiJobRecord:
            return self.records[job_id.removeprefix("job-")]

        def bind(self, session: Any, job_id: str, *, connection_revision_id: str) -> bool:
            name = job_id.removeprefix("job-")
            self.binds.append(name)
            self.records[name] = replace(self.records[name], binding_state="bound", connection_revision_id=connection_revision_id)
            return True

        def set_wait(self, session: Any, job_id: str, reason: str) -> float | None:  # pragma: no cover - nothing waits here
            raise AssertionError("neither job waits")

    fake_jobs = FakeJobs()

    class Slow(ComparisonSpendRepository):
        """The group rows are not there to lock; the day is read and then dawdled over: without the lock both read 40.00."""

        def lock_group(self, session: Any, group_id: str) -> int:
            return 0

        def day_spend(self, session: Any) -> Any:
            found = super().day_spend(session)
            time.sleep(0.6)
            return found

    caller = ComparisonModelCaller(committed, repository=Slow(), offline_wait_seconds=1800)
    items = {name: queue.claimed(ai_job_id=f"job-{name}") for name in "AB"}
    adapters = {name: spend.ScriptedAdapter(reply=spend.reply(cost=0.01)) for name in "AB"}
    outcomes: list[str] = []
    barrier = threading.Barrier(2)

    def run(name: str) -> None:
        job = fake_jobs.records[name]
        route = dispatch.pending_route(
            None, job, jobs=fake_jobs,  # type: ignore[arg-type]
            member_route=lambda session, bound: spend.route(adapters[name], bound.connection_revision_id))
        barrier.wait()
        try:
            # Each call is estimated at 6.00: 40 + 6 fits, 40 + 6 + 6 does not.
            caller.call(
                items[name], route, spend.request(name), estimate=CallEstimate(1_000_000, 1_000_000),
                consent=Consent(
                    estimate_digest=spend.DIGEST, estimate_usd=9.0, ceiling_usd=10.0, connection_revision_id=None,
                    pinned_model=spend.MODEL, executor_group_revision_id=f"exgr_{name}"))
            outcomes.append(f"sent:{name}")
        except CallRefused as refusal:
            outcomes.append(f"{refusal.reason}:{name}")

    threads = [threading.Thread(target=run, args=(name,)) for name in "AB"]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcome.split(":")[0] for outcome in outcomes) == ["day_ceiling", "sent"], outcomes
    sent = next(outcome.split(":")[1] for outcome in outcomes if outcome.startswith("sent"))
    refused = "A" if sent == "B" else "B"
    assert sum(a.calls for a in adapters.values()) == 1 and adapters[refused].calls == 0
    assert fake_jobs.binds == [sent], "only the dispatch that fitted bound its job; the other job is still pending"
    assert fake_jobs.records[refused].binding_state == "pending"
    rows = journal.rows(items[sent].work_id)
    assert len(rows) == 1 and rows[0]["connection_revision_id"] == connections["AB".index(sent)][1]
    assert journal.rows(items[refused].work_id) == [], "a refused dispatch leaves no row"
