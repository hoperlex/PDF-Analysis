"""`HOSTS-BACKEND-01` on PostgreSQL: the host lifecycle, the system objects, the pool lock, the cell binding, the wait and the host token's claim.

Real rows, real triggers, real locks. Each test makes its own hosts and its own (model, access) pair, so the system group of a pair is the test's alone:

* **lifecycle** -- enroll, redeem, report: the system connections and the group of the pair appear, an identical report writes nothing, a changed one clears the
  cooldowns, «Использовать» appends an event and sets the mark, slots are an event, the system objects cannot be revised, listed or routed by hand, a used
  single-model agent's name blocks a host enrollment;
* **binding** -- a planned run is bound by cell in the claim transaction (one unit per pool however many cells), the second binding row of a cell is refused by
  the database, a second run on the full subscription waits for capacity and spends **no attempt**, and is offered again by the hint once the first run ends;
* **the wait** -- a run whose model is on no server waits ``model_unavailable`` and ends ``no_executor_online`` after the limit, with no attempt ever made;
* **the lock** -- two concurrent binds on one subscription: the second blocks until the first commits and then finds the pool full; the claim, the cell binding
  and the comparison mirror take one lock (a lock held by the mirror blocks the pool's);
* **the host token** -- it claims only tasks of its own host that carry the seven members, extends, answers with the exact reported model, and a refusal about
  access starts the cooldown that ends the model's availability until a changed report.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.spend.repository import ComparisonSpendRepository
from auditmanager.executors import public as ex
from auditmanager.executors.agent_package import AgentPackage
from auditmanager.executors.runner import RunnerPrincipal, claim_task, extend_claim, fail_task, submit_answer
from auditmanager.executors.runner_repository import RunnerRepository
from auditmanager.jobs.repository import GroupDispatchWaiting, JobRepository
from auditmanager.runs import RunRepository
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import AnalysisProfileId, DocumentUid, ProjectUid, PromptBundleId, RunId, VersionUid

ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
ROLES = ("admin",)
ORIGIN = "https://stand.example"
PACKAGE = AgentPackage(version="0.9.0", sha256="a" * 64, size_bytes=1, path=None)  # type: ignore[arg-type]
OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
GPT_SOL, GPT_ASTRA, GPT_6 = "gpt-6.1-sol", "gpt-6-astra", "gpt-6-sol"
_counter = iter(range(1, 10_000))
_RUN = uuid.uuid4().hex[:10]  # idempotency keys outlive the process in the database: a second run in the same database must not reuse one


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture(autouse=True)
def _isolated(sessions: sessionmaker[Session]) -> Iterator[None]:
    """Every test starts and ends with no live job and no live host, so the system group of a (model, access) pair is the test's alone."""
    def clean() -> None:
        with sessions() as s:
            for (run_id,) in s.execute(text("SELECT run_id FROM job WHERE state NOT IN ('succeeded', 'failed', 'cancelled', 'dead_letter')")).all():
                JobRepository().cancel_for_run(s, run_id=run_id)
            s.commit()
        with sessions() as s:
            for host in ex.read_hosts(s):
                ex.archive_host(s, host_id=host.record.host_id, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN)
            s.commit()

    clean()
    yield
    clean()


def _key() -> str:
    return f"hosts-backend-{_RUN}-{next(_counter):06d}"


def _report(provider: str = "codex", access: str = "subscription", *models: tuple[str, str], auth: str = "valid",
            slots: int | None = None, version: str = "0.21.0") -> dict[str, Any]:
    return {
        "agent_version": version, "clis": [{"cli": "claude" if provider == "claude_code" else "codex", "installed": True,
                                            "auth_state": auth, "version": "1.0.0"}],
        "concurrency": slots or (2 if access == "api" else 1), "execution_profile": "command", "features": [],
        "providers": [{"provider": provider, "access": access, "auth_state": auth, "models": [
            {"model_id": model, "state": state, "checked_at": "2026-11-10T12:00:00Z",
             **({"failure_code": "quota_exceeded"} if state == "failed" else {})} for model, state in models]}],
        "slots": {provider: slots or (2 if access == "api" else 1)},
    }


class World:
    """A host enrolled, redeemed and reported: its id, its token and a way to make it report again."""

    def __init__(self, sessions: sessionmaker[Session], name: str, report: dict[str, Any]) -> None:
        self.sessions, self.name = sessions, name
        with sessions() as s:
            issued = ex.issue_host_enrollment(s, display_name=name, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN,
                                              configured_origin=ORIGIN, package_source=lambda: PACKAGE)
            s.commit()
            self.host_id = str(issued.record.host_id)
            principal = ex.authenticate_enrollment(s, issued.secret)
            assert principal is not None and principal.host_id == self.host_id
            redeemed = ex.redeem_enrollment(s, principal, runner_instance_id="agent-instance-0001")
            s.commit()
            self.token, self.token_id = redeemed.value, redeemed.record.token_id
        self.report(report)

    def report(self, body: dict[str, Any]) -> Any:
        with self.sessions() as s:
            runner = ex.authenticate_runner(s, self.token, address=None)  # touches the token: the pulse
            assert runner is not None and runner.host_id == self.host_id and runner.connection_id is None
            ack = ex.report_host_runner_health(s, token_id=self.token_id, host_id=self.host_id, **body)
            s.commit()
            return ack

    def principal(self) -> RunnerPrincipal:
        return RunnerPrincipal(token_id=self.token_id, connection_id=None, host_id=self.host_id)

    def facts(self) -> Any:
        with self.sessions() as s:
            (facts,) = ex.read_hosts(s, [self.host_id])
            return facts


def _plan(*cells: tuple[str, str], access: str = "subscription") -> str:
    import json

    return json.dumps({"cells": [{"cell_key": key, "model_id": model, "effort": "medium", "max_output_tokens": 16000,
                                  "timeout_seconds": 600, "access": access} for key, model in cells]})


def _planned_run(sessions: sessionmaker[Session], plan: str) -> str:
    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "version": str(VersionUid.new()), "run": str(RunId.new())}
    with sessions() as s:
        s.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'hosts')"), ids)
        s.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'D')"), ids)
        s.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
                       "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
        s.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, "
            "frozen_input_digest, binding_state, stage_plan) VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, "
            "'pending', CAST(:plan AS jsonb))"),
            {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()), "digest": "b" * 64, "plan": plan})
        RunRepository().advance(s, run_id=ids["run"], from_state="created", to_state="queued")
        JobRepository().enqueue(s, run_id=ids["run"])
        s.commit()
    return ids["run"]


def _scalar(sessions: sessionmaker[Session], sql: str, **params: Any) -> Any:
    with sessions() as s:
        return s.execute(text(sql), params).scalar_one()


def _attempts(sessions: sessionmaker[Session], run_id: str) -> int:
    return int(_scalar(sessions, "SELECT count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id WHERE j.run_id = :r", r=run_id))


def _claim(sessions: sessionmaker[Session], run_id: str, repo: JobRepository | None = None) -> Any:
    with sessions() as s:
        authority = (repo or JobRepository()).start_execution(s, run_id=run_id)
        s.commit()
        return authority


def _wait_reason(sessions: sessionmaker[Session], run_id: str) -> Any:
    with sessions() as s:
        return s.execute(text("SELECT wait_reason, binding_state, state FROM audit_run WHERE run_id = :r"), {"r": run_id}).one()


def _claim_refused(sessions: sessionmaker[Session], run_id: str) -> str:
    """Claim as the carrier does: a refusal that names a wait is stored in a transaction of its own."""
    with pytest.raises(GroupDispatchWaiting) as waited:
        with sessions() as s:
            JobRepository().start_execution(s, run_id=run_id)
    with sessions() as s:
        JobRepository().record_group_wait(s, run_id=run_id, reason=waited.value.wait_reason)
        s.commit()
    return str(waited.value.wait_reason)


def _offered(sessions: sessionmaker[Session], run_id: str) -> bool:
    seen: list[str] = []
    with sessions() as s:
        while True:
            found = JobRepository().next_queued_run(s, submitted=seen)
            if found is None:
                return False
            if found == run_id:
                return True
            seen.append(found)


# --- lifecycle ------------------------------------------------------------------------------------------------------------


def test_a_host_enrolled_and_reported_makes_its_system_objects_once(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "lifecycle-1", _report("claude_code", "subscription", (OPUS, "verified"), (SONNET, "not_verified")))
    with sessions() as s:
        rows = s.execute(text(
            "SELECT c.connection_id, c.system_managed, c.capacity_pool, c.integration_authorised_at IS NOT NULL AS marked, r.pin_id, r.billing "
            "FROM executor_connection c JOIN executor_connection_revision r ON r.connection_id = c.connection_id WHERE c.host_id = :h "
            "ORDER BY r.pin_id"), {"h": world.host_id}).all()
        assert [(r[1], r[2], r[3], r[4], r[5]) for r in rows] == [
            (True, f"{world.host_id}:claude_code", True, OPUS, "not_metered"), (True, f"{world.host_id}:claude_code", True, SONNET, "not_metered")]
        groups = s.execute(text(
            "SELECT g.display_name, g.system_managed, count(m.connection_id) FROM executor_group g JOIN executor_group_revision v ON v.group_id = g.group_id "
            "JOIN executor_group_member m ON m.group_revision_id = v.group_revision_id WHERE m.connection_id = ANY(:ids) "
            "GROUP BY g.display_name, g.system_managed ORDER BY g.display_name"), {"ids": [r[0] for r in rows]}).all()
        assert [(g[0], g[1], g[2]) for g in groups] == [(f"{OPUS} · subscription", True, 1), (f"{SONNET} · subscription", True, 1)]
    facts = world.facts()
    assert facts.enabled and facts.state == "online"
    states = {m.model_id: (m.state, m.reasons) for m in ex.model_availability(facts)}
    assert states[OPUS] == ("available", ()) and states[SONNET] == ("unavailable", ("model_not_verified",))


def test_an_identical_report_writes_nothing_and_a_changed_one_clears_the_cooldowns(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "lifecycle-2", _report("claude_code", "api", (OPUS, "verified")))
    sha = _scalar(sessions, "SELECT report_sha256 FROM executor_host_report WHERE host_id = :h", h=world.host_id)
    at = _scalar(sessions, "SELECT reported_at FROM executor_host_report WHERE host_id = :h", h=world.host_id)
    events = _scalar(sessions, "SELECT count(*) FROM audit_event WHERE event_type = 'executor.host_report_changed' AND aggregate_id = :h", h=world.host_id)
    ack = world.report(_report("claude_code", "api", (OPUS, "verified")))
    assert ack.enabled is True and {entry["model_id"] for entry in ack.catalogue} >= {OPUS, SONNET} and ack.changed is False
    assert _scalar(sessions, "SELECT reported_at FROM executor_host_report WHERE host_id = :h", h=world.host_id) == at, "the snapshot is not rewritten"
    assert _scalar(sessions, "SELECT count(*) FROM audit_event WHERE event_type = 'executor.host_report_changed' AND aggregate_id = :h", h=world.host_id) == events
    with sessions() as s:
        ex.HostRepository().set_cooldown(s, host_id=world.host_id, provider="claude_code", model_id=OPUS, seconds=900, reason="quota_exceeded")
        s.commit()
    assert [m.reasons for m in ex.model_availability(world.facts())] == [("model_cooling_down",)]
    assert world.report(_report("claude_code", "api", (OPUS, "failed"))).changed is True
    assert _scalar(sessions, "SELECT report_sha256 FROM executor_host_report WHERE host_id = :h", h=world.host_id) != sha
    assert _scalar(sessions, "SELECT count(*) FROM executor_model_cooldown WHERE host_id = :h", h=world.host_id) == 0, "the agent has said what is true"


def test_use_and_slots_are_journalled_events_with_their_author(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "lifecycle-3", _report("codex", "subscription", (GPT_SOL, "verified")))
    with sessions() as s:
        ex.set_host_enabled(s, host_id=world.host_id, enabled=False, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN)
        ex.set_host_slots(s, host_id=world.host_id, slots={"codex": 3}, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN)
        s.commit()
        assert s.execute(text("SELECT enabled, set_by FROM executor_host_use_event WHERE host_id = :h ORDER BY event_no"), {"h": world.host_id}).all() == [
            (True, ADMIN), (False, ADMIN)]
        assert s.execute(text("SELECT count(*) FROM executor_connection WHERE host_id = :h AND integration_authorised_at IS NOT NULL"),
                         {"h": world.host_id}).scalar_one() == 0, "switching off clears the mark of its system connections"
    facts = world.facts()
    assert facts.enabled is False and facts.slots_total == 3
    assert [m.reasons for m in ex.model_availability(facts)] == [("host_disabled",)]
    assert ex.host_claim_limit(sessions(), world.host_id) == 3, "a host token holds at most the sum of its slots"


def test_a_system_object_is_not_revised_listed_or_routed_by_hand(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "lifecycle-4", _report("codex", "subscription", (GPT_ASTRA, "verified")))
    with sessions() as s:
        (connection_id,) = s.execute(text("SELECT connection_id FROM executor_connection WHERE host_id = :h"), {"h": world.host_id}).first()
        (group_id,) = s.execute(text("SELECT g.group_id FROM executor_group g WHERE g.system_managed AND g.display_name = :n"),
                                {"n": f"{GPT_ASTRA} · subscription"}).first()
        for call in (
            lambda: ex.archive_connection(s, connection_id=connection_id, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN),
            lambda: ex.archive_group(s, group_id=group_id, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN),
        ):
            with pytest.raises(DomainError) as refused:
                call()
            assert refused.value.detail_fields["conflict_reason"] == "system_managed"
        assert connection_id not in {item.connection.connection_id for item in ex.list_connection_summaries(s)}
        assert group_id not in {item.group.group_id for item in ex.list_group_summaries(s)}
        assert ex.routing_mode(s).mode == "legacy"


def test_the_name_of_a_used_single_model_agent_blocks_a_host_enrollment(sessions: sessionmaker[Session]) -> None:
    with sessions() as s:
        cid = "exc_" + "01M2545JSD15ETSNNV904X99" + "AB"
        s.execute(text("INSERT INTO executor_connection (connection_id, kind, display_name, created_by) VALUES (:c, 'pull', 'kzSonnet-guard', :a)"),
                  {"c": cid, "a": ADMIN})
        s.execute(text("INSERT INTO executor_connection (connection_id, kind, display_name, created_by) VALUES (:c, 'pull', 'idle-guard', :a)"),
                  {"c": cid[:-2] + "AC", "a": ADMIN})
        s.execute(text("INSERT INTO executor_route_event (route_event_id, work_kind, route_no, primary_connection_id, set_by) "
                       "VALUES ('ert_01M2545JSD15ETSNNV904X99AB', 'text_analysis', (SELECT COALESCE(max(route_no), 0) + 1 FROM executor_route_event "
                       "WHERE work_kind = 'text_analysis'), :c, :a)"), {"c": cid, "a": ADMIN})
        s.commit()
        with pytest.raises(DomainError) as refused:
            ex.issue_host_enrollment(s, display_name="KZSONNET-GUARD", roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN,
                                     configured_origin=ORIGIN, package_source=lambda: PACKAGE)
        assert refused.value.detail_fields["conflict_reason"] == "upgrade_blocked_by_use"
        s.rollback()
        issued = ex.issue_host_enrollment(s, display_name="idle-guard", roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN,
                                          configured_origin=ORIGIN, package_source=lambda: PACKAGE)
        assert issued.record.host_id is not None and "AUDITMANAGER_AGENT_MODEL" not in issued.command, "a host command asks for no model"
        s.rollback()


# --- binding --------------------------------------------------------------------------------------------------------------


def test_a_planned_run_is_bound_by_cell_in_the_claim_and_a_second_run_waits_without_spending_an_attempt(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "binding-1", _report("codex", "subscription", (GPT_SOL, "verified")))
    first = _planned_run(sessions, _plan(("text:main", GPT_SOL), ("norms:main", GPT_SOL)))
    second = _planned_run(sessions, _plan(("text:main", GPT_SOL)))
    assert _offered(sessions, first), "a pending planned run is offered once, while nothing holds it back"

    authority = _claim(sessions, first)
    assert _wait_reason(sessions, first)[:2] == (None, "bound")
    with sessions() as s:
        bound = [ex.cell_binding_of(s, first, key) for key in ("text:main", "norms:main")]
        assert all(item is not None and item.host_id == world.host_id and item.access == "subscription" for item in bound)
        assert {item.pool for item in bound if item} == {f"{world.host_id}:codex"}
        assert ex.HostRepository().pool_units(s, f"{world.host_id}:codex") == 1, "one unit for the run however many cells share the pool"
    assert _attempts(sessions, first) == 1 and authority.run_id == first

    assert _claim_refused(sessions, second) == "executor_at_capacity"
    assert _wait_reason(sessions, second)[:2] == ("executor_at_capacity", "pending")
    assert _attempts(sessions, second) == 0, "waiting spent no attempt"
    assert _scalar(sessions, "SELECT count(*) FROM audit_run_cell_binding WHERE run_id = :r", r=second) == 0, "nothing was bound"
    assert not _offered(sessions, second), "a run the claim refused is not offered again until the sweep clears its wait"

    with sessions() as s:
        JobRepository().cancel_for_run(s, run_id=first)
        s.commit()
        assert JobRepository().refresh_group_waits(s).updated >= 1
        s.commit()
    assert _wait_reason(sessions, second)[0] is None, "the pool is free: the wait is cleared"
    assert _offered(sessions, second)
    _claim(sessions, second)
    assert _wait_reason(sessions, second)[1] == "bound" and _attempts(sessions, second) == 1


def test_a_cell_binding_is_written_once(sessions: sessionmaker[Session]) -> None:
    World(sessions, "binding-2", _report("codex", "api", (GPT_6, "verified")))
    run = _planned_run(sessions, _plan(("text:main", GPT_6), access="api"))
    _claim(sessions, run)
    with sessions() as s:
        bound = ex.cell_binding_of(s, run, "text:main")
        assert bound is not None
        with pytest.raises(DBAPIError) as refused:
            ex.write_bindings(s, run_id=run, bound=[bound])
        assert getattr(refused.value.orig, "sqlstate", None) in ("AM001", "23505", "AM003"), refused.value
        s.rollback()
        with pytest.raises(DBAPIError):
            s.execute(text("UPDATE audit_run_cell_binding SET cell_key = 'text:judge' WHERE run_id = :r"), {"r": run})
        s.rollback()


def test_the_journal_of_a_call_names_the_member_the_cell_was_bound_to(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "binding-3", _report("codex", "subscription", (GPT_SOL, "verified")))
    run = _planned_run(sessions, _plan(("review:main", GPT_SOL)))
    authority = _claim(sessions, run)
    with sessions() as s:
        call = JobRepository().prepare_provider_call(
            s, authority, provider="openai", model_identity=GPT_SOL, provider_mode="live", parameters={}, request_sha256="c" * 64,
            stage_key="review", cell_key="review:main")
        s.commit()
        row = s.execute(text("SELECT host_id, access, stage_key, connection_revision_id IS NOT NULL, identity_basis FROM provider_call_effect "
                             "WHERE model_call_id = :c"), {"c": str(call)}).one()
    assert tuple(row) == (world.host_id, "subscription", "review", True, "declared")


# --- the wait -----------------------------------------------------------------------------------------------------------------


def test_a_model_on_no_server_waits_and_the_run_ends_no_executor_online_after_the_limit_with_no_attempt(sessions: sessionmaker[Session]) -> None:
    run = _planned_run(sessions, _plan(("text:main", "claude-sonnet-5-5"), access="api"))  # no host serves Sonnet by API in this database
    assert _claim_refused(sessions, run) == "model_unavailable"
    assert _wait_reason(sessions, run)[:2] == ("model_unavailable", "pending")
    with sessions() as s:
        outcome = ex.evaluate_wait(s, run_id=run, cells=ex.cell_requests({"cells": [{"cell_key": "text:main", "model_id": "claude-sonnet-5-5",
                                                                                      "access": "api"}]}))
        assert [(w.cell_key, w.cause) for w in outcome.waits] == [("text:main", "not_on_any_server")], "the cell and the cause are named"
        assert JobRepository().refresh_group_waits(s, offline_wait_seconds=1800).expired == 0, "inside the limit"
        s.commit()
    with sessions() as s:
        s.execute(text("UPDATE audit_run SET waiting_since = clock_timestamp() - interval '31 minutes' WHERE run_id = :r"), {"r": run})
        assert JobRepository().refresh_group_waits(s, offline_wait_seconds=1800).expired >= 1
        s.commit()
    state = _wait_reason(sessions, run)
    assert state[0] is None and state[2] == "failed"
    assert _attempts(sessions, run) == 0, "the budget was never touched"


def test_a_capacity_wait_never_expires(sessions: sessionmaker[Session]) -> None:
    World(sessions, "wait-2", _report("codex", "subscription", (GPT_ASTRA, "verified")))
    holder, waiter = _planned_run(sessions, _plan(("text:main", GPT_ASTRA))), _planned_run(sessions, _plan(("text:main", GPT_ASTRA)))
    _claim(sessions, holder)
    assert _claim_refused(sessions, waiter) == "executor_at_capacity"
    with sessions() as s:
        s.execute(text("UPDATE audit_run SET waiting_since = clock_timestamp() - interval '5 hours' WHERE run_id = :r"), {"r": waiter})
        assert JobRepository().refresh_group_waits(s, offline_wait_seconds=1800).expired == 0
        s.commit()
    assert _wait_reason(sessions, waiter)[:3] == ("executor_at_capacity", "pending", "queued")


# --- the lock -------------------------------------------------------------------------------------------------------------------


def test_two_binds_on_one_subscription_cannot_both_pass(sessions: sessionmaker[Session]) -> None:
    World(sessions, "lock-1", _report("claude_code", "subscription", (OPUS, "verified")))
    one, two = (_planned_run(sessions, _plan(("text:main", OPUS))) for _ in range(2))
    held, release = threading.Event(), threading.Event()
    outcome: dict[str, Any] = {}

    def first() -> None:
        with sessions() as s:
            JobRepository().start_execution(s, run_id=one)  # takes the pool lock and binds; the transaction stays open
            held.set()
            release.wait(30)
            s.commit()
        outcome["first"] = "bound"

    def second() -> None:
        held.wait(30)
        try:
            with sessions() as s:
                JobRepository().start_execution(s, run_id=two)
                s.commit()
            outcome["second"] = "bound"
        except GroupDispatchWaiting as waited:
            outcome["second"] = waited.wait_reason

    a, b = threading.Thread(target=first), threading.Thread(target=second)
    a.start()
    b.start()
    held.wait(30)
    time.sleep(1.5)
    assert b.is_alive() and "second" not in outcome, "the second bind waits on the pool's lock while the first holds it"
    release.set()
    a.join(30)
    b.join(30)
    assert outcome == {"first": "bound", "second": "executor_at_capacity"}, "it then reads the first's committed unit"
    assert _attempts(sessions, two) == 0


def test_the_claim_the_binding_and_the_comparison_call_take_one_lock(sessions: sessionmaker[Session], engine: Engine) -> None:
    world = World(sessions, "lock-2", _report("codex", "subscription", (GPT_SOL, "verified")))
    with sessions() as s:
        (connection_id,) = s.execute(text("SELECT connection_id FROM executor_connection WHERE host_id = :h"), {"h": world.host_id}).first()
    pool = f"{world.host_id}:codex"
    probe = text("SELECT pg_try_advisory_xact_lock(hashtextextended('auditmanager.executor_connection|' || :key, 0))")
    mirror = ComparisonSpendRepository()
    with sessions() as holder:
        mirror.lock_connection(holder, connection_id)  # the comparison call's lock, taken from the connection
        with engine.connect() as other:
            assert other.execute(probe, {"key": pool}).scalar_one() is False, "the pool's lock is the same lock"
            assert other.execute(probe, {"key": connection_id}).scalar_one() is True, "and the connection's own key is not the key"
        holder.rollback()
    with sessions() as holder:
        ex.HostRepository().lock_pool(holder, pool)  # the cell binding's lock, taken from the pool
        with engine.connect() as other:
            other.execute(text("SET LOCAL lock_timeout = '300ms'"))
            with pytest.raises(DBAPIError):
                other.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('auditmanager.executor_connection|' || :key, 0))"), {"key": pool})
        holder.rollback()


def test_the_comparison_mirror_counts_in_the_pool(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "lock-3", _report("codex", "subscription", (GPT_6, "verified")))
    with sessions() as s:
        (connection_id,) = s.execute(text("SELECT connection_id FROM executor_connection WHERE host_id = :h"), {"h": world.host_id}).first()
        assert ComparisonSpendRepository().connection_has_free_unit(s, connection_id) is True
    _claim(sessions, _planned_run(sessions, _plan(("text:main", GPT_6))))
    with sessions() as s:
        assert ComparisonSpendRepository().connection_has_free_unit(s, connection_id) is False, "the run holds the subscription's one unit"
        ex.set_host_slots(s, host_id=world.host_id, slots={"codex": 2}, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN)
        s.commit()
        assert ComparisonSpendRepository().connection_has_free_unit(s, connection_id) is True, "a second slot is a second unit"


# --- the host token -------------------------------------------------------------------------------------------------------------------


def _write_task(sessions: sessionmaker[Session], run: str, authority: Any, bound: Any, *, cell: str = "text:main", provider: str = "codex",
                access: str = "subscription", model: str = GPT_SOL) -> str:
    from auditmanager.executors.pull import HostCall

    schema = {"type": "object", "properties": {"observations": {"type": "array"}}, "required": ["observations"], "additionalProperties": False}
    call = HostCall(provider=provider, access=access, model_id=model, effort="medium", max_output_tokens=16000, timeout_seconds=600, cell_key=cell)
    with sessions() as s:
        task = RunnerRepository().insert_task(
            s, connection_id=bound.connection_id, revision_id=bound.connection_revision_id, origin="run_call", run_id=run,
            attempt_id=authority.attempt_id, model_call_id=None, probe_id=None, expected_model=model,
            payload={"system": "s", "user_text": "u", "output_schema": schema, "host": call.members(600)}, deadline_seconds=600)
        s.commit()
        return task.task_id


def test_a_host_token_claims_extends_answers_and_fails_its_hosts_tasks_only(sessions: sessionmaker[Session]) -> None:
    mine = World(sessions, "token-1", _report("codex", "subscription", (GPT_SOL, "verified")))
    other = World(sessions, "token-2", _report("claude_code", "subscription", (SONNET, "verified")))
    run = _planned_run(sessions, _plan(("text:main", GPT_SOL)))
    authority = _claim(sessions, run)
    with sessions() as s:
        bound = ex.cell_binding_of(s, run, "text:main")
        assert bound is not None and bound.host_id == mine.host_id
    task_id = _write_task(sessions, run, authority, bound)

    assert claim_task(sessions, other.principal(), wait_seconds=0) is None, "another host's token never sees it"
    claimed = claim_task(sessions, mine.principal(), wait_seconds=0, runner_instance_id="agent-instance-0001")
    assert claimed is not None and claimed.task_id == task_id
    assert (claimed.provider, claimed.access, claimed.model_id, claimed.effort, claimed.max_output_tokens, claimed.cell_key) == (
        "codex", "subscription", GPT_SOL, "medium", 16000, "text:main")
    assert claimed.model == claimed.model_id
    with sessions() as s:
        assert extend_claim(s, mine.principal(), task_id) >= claimed.claim_expires_at
        s.commit()
        with pytest.raises(DomainError):
            extend_claim(s, other.principal(), task_id)
        s.rollback()

    def refuse() -> Exception:
        return RuntimeError("model_not_the_tasks")

    with sessions() as s:
        with pytest.raises(RuntimeError):
            submit_answer(s, mine.principal(), task_id, output_text='{"observations": []}', model=GPT_SOL, input_tokens=None, output_tokens=None,
                          on_mismatch=refuse, provider="codex", access="subscription", reported_model="gpt-6.1-sol-20261101")
        s.rollback()
        ack = submit_answer(s, mine.principal(), task_id, output_text='{"observations": []}', model=GPT_SOL, input_tokens=None,
                            output_tokens=None, on_mismatch=refuse, provider="codex", access="subscription", reported_model=GPT_SOL,
                            usage={"input_tokens": 10, "output_tokens": 5})
        s.commit()
        assert ack.state == "answered"
        row = s.execute(text("SELECT declared_model, declared_input_tokens, declared_output_tokens FROM executor_task WHERE task_id = :t"),
                        {"t": task_id}).one()
        assert tuple(row) == (GPT_SOL, 10, 5)


def test_a_refusal_about_access_starts_the_cooldown_and_a_changed_report_ends_it(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "token-3", _report("claude_code", "subscription", (OPUS, "verified")))
    run = _planned_run(sessions, _plan(("text:main", OPUS)))
    authority = _claim(sessions, run)
    with sessions() as s:
        bound = ex.cell_binding_of(s, run, "text:main")
    task_id = _write_task(sessions, run, authority, bound, provider="claude_code", model=OPUS)
    assert claim_task(sessions, world.principal(), wait_seconds=0) is not None
    with sessions() as s:
        fail_task(s, world.principal(), task_id, reason="timeout: the CLI stopped")
        s.commit()
    assert _scalar(sessions, "SELECT count(*) FROM executor_model_cooldown WHERE host_id = :h", h=world.host_id) == 0, "a timeout is not about access"
    second = _write_task(sessions, run, authority, bound, provider="claude_code", model=OPUS)
    assert claim_task(sessions, world.principal(), wait_seconds=0) is not None
    with sessions() as s:
        fail_task(s, world.principal(), second, reason="quota_exceeded: monthly cap reached")
        s.commit()
    row = _scalar(sessions, "SELECT reason || ':' || (until > clock_timestamp() + interval '14 minutes')::text || ':' || "
                  "(until < clock_timestamp() + interval '16 minutes')::text FROM executor_model_cooldown WHERE host_id = :h", h=world.host_id)
    assert row == "quota_exceeded:true:true", "fifteen minutes"
    assert [m.reasons for m in ex.model_availability(world.facts())] == [("model_cooling_down",)]
    world.report(_report("claude_code", "subscription", (OPUS, "failed")))
    assert _scalar(sessions, "SELECT count(*) FROM executor_model_cooldown WHERE host_id = :h", h=world.host_id) == 0
    assert [m.reasons for m in ex.model_availability(world.facts())] == [("model_not_verified",)]


def test_a_stale_pulse_makes_a_host_unavailable_without_any_write(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "stale-1", _report("codex", "subscription", (GPT_SOL, "verified")))
    with sessions() as s:
        s.execute(text("UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - interval '3 minutes' WHERE token_id = :t"),
                  {"t": world.token_id})
        s.commit()
    before = _scalar(sessions, "SELECT count(*) FROM audit_event")
    facts = world.facts()
    assert facts.state == "offline" and [m.reasons for m in ex.model_availability(facts)] == [("host_offline",)]
    assert _scalar(sessions, "SELECT count(*) FROM audit_event") == before, "reading it wrote nothing"


def test_an_archived_host_leaves_its_group_and_its_token_stops_working(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "archive-1", _report("codex", "subscription", (GPT_ASTRA, "verified")))
    with sessions() as s:
        ex.archive_host(s, host_id=world.host_id, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN)
        s.commit()
        assert s.execute(text("SELECT archived_at IS NOT NULL FROM executor_host WHERE host_id = :h"), {"h": world.host_id}).scalar_one()
        assert ex.authenticate_runner(s, world.token, address=None) is None
        assert s.execute(text("SELECT count(*) FROM executor_connection WHERE host_id = :h AND archived_at IS NULL"), {"h": world.host_id}).scalar_one() == 0
    assert world.host_id not in {h.record.host_id for h in ex.read_hosts(sessions())}, "an archived server is not listed"


def test_the_one_unit_of_a_pool_blocks_an_archive_until_the_run_ends(sessions: sessionmaker[Session]) -> None:
    world = World(sessions, "archive-2", _report("codex", "subscription", (GPT_ASTRA, "verified")))
    run = _planned_run(sessions, _plan(("text:main", GPT_ASTRA)))
    _claim(sessions, run)
    with sessions() as s:
        with pytest.raises(DomainError) as refused:
            ex.archive_host(s, host_id=world.host_id, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN)
        assert refused.value.detail_fields["conflict_reason"] == "host_in_use"
        s.rollback()
        JobRepository().cancel_for_run(s, run_id=run)
        ex.archive_host(s, host_id=world.host_id, roles=ROLES, idempotency_key=_key(), actor_uid=ADMIN)
        s.commit()

