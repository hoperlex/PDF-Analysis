"""`EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12 to 16) -- the claim binds a Run admitted on a group to one of its members, exactly
once, on real PostgreSQL.

Real PostgreSQL, no object store, **committing** sessions (a second process only sees what is committed). Everything is made by the
shipped ``JobRepository``, the executors context's own commands (a ``pull`` connection needs no secret) and the rows around them
written directly. These tests are written and **not run** in EXEC-2 (`R-149d`, D-292); each would pass against PostgreSQL at head
``0048``. B3 section 11 is not in the repository, so the numbers are the task file's reading of it (the integrator re-maps them):

* **4 -- the binding is written once, in the claim.** The connection revision goes NULL -> a member's snapshot revision with
  ``binding_state`` ``pending`` -> ``bound``; the wait is cleared; one ``executor.run_dispatched`` event; the rotation moves on; the
  Job is running (``test_a_pending_run_is_bound...``). A claim that is refused writes nothing -- not even the rotation
  (``test_a_refused_claim_writes_nothing``);
* **lock order** -- worker intake, the group's row, the member connections in ascending ``connection_id``, the control row, the Run, the
  Job, read off the statements the claim sends (``test_the_claim_takes_its_locks_in_the_documented_order``);
* **5 -- least loaded; equal members take turns** by the persisted rotation;
* **6 -- every member busy: the Run waits** (``executor_at_capacity``), visibly and for ever, and is offered again the moment a unit
  is free; **7 -- every member offline: ``runner_offline``**; **8 -- and after the configured time it ends ``no_executor_online``**;
* **9, 10 -- a member whose current revision is no longer the group's snapshot, or that is archived or not probed, is never chosen
  and never adopted;**
* **11 -- two claimants for the last unit: one binding** -- between two threads, between two processes queued on the group's lock,
  and two claims of one Run;
* **12 -- a consent that no longer holds binds nothing** (``needs_reconsent``), and the hint does not keep offering the Run;
* **14 -- lease loss after binding: the retry stays on the bound member** even with another member free; **an ``outcome_unknown``
  is never redispatched**;
* **18 -- a Run whose executor was frozen at start, the ``environment`` source included, claims as before**, and a pending Run's NULL
  connection is never read as "unlimited".
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import model_rate_sha256
from auditmanager.executors.public import (
    GroupSettings,
    MemberRequest,
    RevisionSettings,
    archive_connection,
    create_connection,
    create_group,
    issue_runner_token,
    pinned_models,
    record_probe_result,
    record_probe_started,
    request_probe,
    revise_connection,
)
from auditmanager.ingest.public import CommandRepository, payload_fingerprint
from auditmanager.jobs.events import _SAFE_KEYS
from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.jobs.repository import GroupDispatchWaiting
from auditmanager.runs import RunRepository
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    IdempotencyKey,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from auditmanager.workers.public import WorkerRegistry

pytestmark = pytest.mark.usefixtures("quiet_queue")

_SUPPORT_NAME = "exec2_cap_connection_capacity_support"
if _SUPPORT_NAME in sys.modules:
    support: ModuleType = sys.modules[_SUPPORT_NAME]
else:
    _spec = importlib.util.spec_from_file_location(
        _SUPPORT_NAME, Path(__file__).resolve().parent / "connection_capacity_support.py"
    )
    assert _spec is not None and _spec.loader is not None
    support = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT_NAME] = support
    _spec.loader.exec_module(support)

WAIT_SECONDS = 30.0
ACTOR = support.ACTOR
ROLES = frozenset({"admin"})
PINS = pinned_models()
PIN_IDS = {pin.model_id for pin in PINS}
SONNET = next(pin for pin in PINS if pin.model_id == "claude-sonnet-5")
PULL = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", allow_client_documents=False,
    timeout_seconds=600, pull_client="claude_code_session", answer_deadline_seconds=600, max_claimed_tasks=1,
    max_active_runs=1,
)
GROUP_SETTINGS = GroupSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", strategy="least_loaded")
PRIORITY = support.PRIORITY


def key() -> str:
    return f"grp-{uuid4().hex}"


# --- rows --------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Member:
    connection_id: str
    revision_id: str
    token_id: str | None = None


def member(sessions: sessionmaker[Session], *, capacity: int = 1, online: bool = True, probed: bool = True) -> Member:
    """A ``pull`` connection dispatch would choose: served, probed ``ok`` on its current revision, a runner seen just now."""
    settings = replace(PULL, max_claimed_tasks=capacity, max_active_runs=capacity)
    with sessions() as session:
        connection_id = create_connection(
            session, kind="pull", display_name=f"member-{uuid4().hex[:10]}", roles=ROLES, idempotency_key=key(),
            actor_uid=ACTOR).connection_id
        revision_id = revise_connection(
            session, connection_id=connection_id, settings=settings, pinned_model_ids=PIN_IDS, roles=ROLES,
            idempotency_key=key(), actor_uid=ACTOR).revision_id
        session.commit()
    if probed:
        with sessions() as session:
            probe = request_probe(
                session, connection_id=connection_id, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
            assert record_probe_started(session, probe.probe_id)
            assert record_probe_result(
                session, probe.probe_id, outcome="ok", reported_model="claude-sonnet-5", identity_basis="declared",
                rate_check="not_metered")
            session.commit()
    token = None
    if online:
        with sessions() as session:
            token = issue_runner_token(
                session, connection_id=connection_id, expires_in_days=None, roles=ROLES, idempotency_key=key(),
                actor_uid=ACTOR).record.token_id
            session.commit()
        seen(sessions, token, seconds_ago=5)
    return Member(connection_id, revision_id, token)


def seen(sessions: sessionmaker[Session], token_id: str | None, *, seconds_ago: int) -> None:
    """Move when a runner was last seen: a few seconds ago is online, an hour ago is offline."""
    with sessions() as session:
        session.execute(text(
            "UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - make_interval(secs => :s) "
            "WHERE token_id = :id"), {"s": seconds_ago, "id": token_id})
        session.commit()


def group(sessions: sessionmaker[Session], *members: Member) -> tuple[str, str]:
    """A group of the members' current revisions: ``(group_id, group_revision_id)``."""
    with sessions() as session:
        created = create_group(
            session, display_name=f"Pool {uuid4().hex[:10]}", settings=GROUP_SETTINGS,
            members=[MemberRequest(item.connection_id, item.revision_id, None) for item in members], pins=PINS,
            roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
        session.commit()
    return created.group.group_id, created.current_revision.group_revision_id


def consent_for(sessions: sessionmaker[Session], group_revision_id: str, **changes: Any) -> str:
    """An accepted ``start_audit_run`` command whose outcome holds the group consent; returns its command id."""
    consent = {
        "estimate_digest": "a" * 64, "ceiling_micros": 0, "billing": "unmetered", "model_id": "claude-sonnet-5",
        "rate_sha256": model_rate_sha256(SONNET), "connection_revision_id": None,
        "executor_group_revision_id": group_revision_id,
    }
    consent.update(changes)
    with sessions() as session:
        commands = CommandRepository()
        started = commands.begin(
            session, command_type="start_audit_run", idempotency_key=IdempotencyKey(key()),
            fingerprint=payload_fingerprint({"group_revision_id": group_revision_id, "n": uuid4().hex}))
        commands.succeed(session, started.command_id, {"run_id": "run_pending", "cost_consent": consent})
        session.commit()
    return str(started.command_id)


def pending_run(
    sessions: sessionmaker[Session], group_revision_id: str, *, command_id: str | None = None,
    rule_revision_id: str | None = None, priority: int = PRIORITY,
) -> str:
    """A committed ``queued`` Run admitted on a group -- ``pending``, no connection -- with its queued Job."""
    ids = {
        "project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()), "run": str(RunId.new()),
    }
    with sessions() as session:
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'group')"), ids)
        session.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'group')"
        ), ids)
        session.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, "
            "page_count) VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"), {**ids, "sha": "a" * 64})
        session.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
            "provider_mode, frozen_input_digest, command_id, binding_state, executor_group_revision_id, "
            "routing_rule_revision_id) VALUES (:run, :project, :version, :profile, :bundle, 'live', :digest, "
            ":command, 'pending', :group_revision, :rule)"),
            {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()), "digest": "b" * 64,
             "command": command_id, "group_revision": group_revision_id, "rule": rule_revision_id})
        RunRepository().advance(session, run_id=ids["run"], from_state="created", to_state="queued")
        jobs = JobRepository()
        job_id = jobs.enqueue(session, run_id=ids["run"])
        jobs.set_priority(session, job_id=job_id, priority=priority)
        session.commit()
    return ids["run"]


def busy(sessions: sessionmaker[Session], on: Member) -> tuple[str, Any]:
    """A Run frozen to the member's revision and claimed, so that one of its units is in use: ``(run_id, authority)``."""
    run_id = support.queue_run(sessions, on.revision_id)
    return run_id, support.claim(sessions, run_id)


def row(sessions: sessionmaker[Session], run_id: str) -> dict[str, Any]:
    with sessions() as session:
        found = session.execute(text(
            "SELECT state, binding_state, connection_revision_id, executor_group_revision_id, wait_reason, "
            "waiting_since, terminal_reason, terminal_detail FROM audit_run WHERE run_id = :r"), {"r": run_id}).mappings().one()
        return dict(found)


def rotation(sessions: sessionmaker[Session], group_id: str) -> int:
    with sessions() as session:
        return int(session.execute(text(
            "SELECT rotation_cursor FROM executor_group WHERE group_id = :g"), {"g": group_id}).scalar_one())


def events(sessions: sessionmaker[Session], run_id: str, prefix: str) -> list[dict[str, Any]]:
    with sessions() as session:
        return [dict(payload) for payload in session.execute(text(
            "SELECT payload FROM audit_event WHERE event_type LIKE :p AND payload ->> 'run_id' = :r ORDER BY sequence_no"),
            {"p": prefix + "%", "r": run_id}).scalars().all()]


def hint(sessions: sessionmaker[Session], **kwargs: Any) -> str | None:
    with sessions() as session:
        return JobRepository().next_queued_run(session, **kwargs)


def refuse(sessions: sessionmaker[Session], run_id: str) -> GroupDispatchWaiting:
    with pytest.raises(GroupDispatchWaiting) as refused:
        support.claim(sessions, run_id)
    return refused.value


def sweep(sessions: sessionmaker[Session], *, offline_wait_seconds: float = 1800) -> Any:
    with sessions() as session:
        report = JobRepository().refresh_group_waits(session, offline_wait_seconds=offline_wait_seconds)
        session.commit()
    return report


def snapshot(sessions: sessionmaker[Session], run_id: str, group_id: str) -> tuple[Any, ...]:
    """Everything a refused claim must leave as it found it."""
    with sessions() as session:
        return tuple(session.execute(text(
            "SELECT (SELECT to_jsonb(j) - 'updated_at' FROM job j WHERE j.run_id = :r), "
            "(SELECT to_jsonb(r) - 'updated_at' FROM audit_run r WHERE r.run_id = :r), "
            "(SELECT count(*) FROM attempt t JOIN job j ON j.job_id = t.job_id WHERE j.run_id = :r), "
            "(SELECT count(*) FROM audit_event WHERE payload ->> 'run_id' = :r), "
            "(SELECT rotation_cursor FROM executor_group WHERE group_id = :g)"), {"r": run_id, "g": group_id}).one())


def end(sessions: sessionmaker[Session], *run_ids: str) -> None:
    for run_id in run_ids:
        support.cancel(sessions, run_id)


# --- 4: the binding is written once, in the claim ---------------------------------------------------------------------------


def test_a_pending_run_is_bound_once_to_a_member_at_the_claim(sessions: sessionmaker[Session]) -> None:
    one, two = member(sessions), member(sessions)
    group_id, group_revision = group(sessions, one, two)
    run_id = pending_run(sessions, group_revision)
    before = row(sessions, run_id)
    assert (before["binding_state"], before["connection_revision_id"]) == ("pending", None)
    cursor = rotation(sessions, group_id)
    try:
        authority = support.claim(sessions, run_id)
        after = row(sessions, run_id)
        assert after["binding_state"] == "bound" and after["executor_group_revision_id"] == group_revision
        assert after["connection_revision_id"] in {one.revision_id, two.revision_id}, "a member's snapshot revision"
        assert after["wait_reason"] is None and after["waiting_since"] is None
        assert support.job_state(sessions, run_id) == "running" and support.attempts(sessions, run_id) == 1
        assert rotation(sessions, group_id) == cursor + 1, "the rotation moves on with the binding"
        (dispatched,) = events(sessions, run_id, "executor.")
        chosen = one if after["connection_revision_id"] == one.revision_id else two
        assert dispatched == {
            "run_id": run_id, "connection_id": chosen.connection_id, "revision_id": chosen.revision_id,
            "work_kind": "text_analysis", "from_state": "pending", "to_state": "bound", "reason": "least_loaded"}
        assert set(dispatched) - {"run_id"} <= _SAFE_KEYS
        assert support.active_runs(sessions, chosen.connection_id) == [run_id], "the Run holds the member's unit"
        support.finish(sessions, authority)
    finally:
        end(sessions, run_id)


def test_the_database_binds_a_run_once_and_only_to_a_member_of_its_group_revision(sessions: sessionmaker[Session]) -> None:
    one, two = member(sessions), member(sessions)
    outsider = member(sessions)
    _group_id, group_revision = group(sessions, one, two)
    run_id = pending_run(sessions, group_revision)
    try:
        with sessions() as session:
            with pytest.raises(Exception, match="not a member of group revision"):
                session.execute(text(
                    "UPDATE audit_run SET connection_revision_id = :c, binding_state = 'bound' WHERE run_id = :r"),
                    {"c": outsider.revision_id, "r": run_id})
        support.claim(sessions, run_id)
        bound = row(sessions, run_id)["connection_revision_id"]
        with sessions() as session:
            with pytest.raises(Exception):
                session.execute(text("UPDATE audit_run SET connection_revision_id = :c WHERE run_id = :r"),
                                {"c": one.revision_id if bound != one.revision_id else two.revision_id, "r": run_id})
    finally:
        end(sessions, run_id)


# --- the lock order ---------------------------------------------------------------------------------------------------------


def test_the_claim_takes_its_locks_in_the_documented_order(engine: Engine, sessions: sessionmaker[Session]) -> None:
    """Worker intake, the group's row, the member connections in ascending ``connection_id``, the control row, the Run, the Job."""
    members = sorted([member(sessions), member(sessions), member(sessions)], key=lambda item: item.connection_id,
                     reverse=True)                                      # listed out of order on purpose
    _group_id, group_revision = group(sessions, *members)
    run_id = pending_run(sessions, group_revision)
    with sessions() as session:
        worker_id = WorkerRegistry().register(session, version="group-dispatch-test", slots=1)
        session.commit()
    sent: list[tuple[str, Any]] = []

    def record(connection: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool) -> None:
        sent.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", record)
    try:
        with sessions() as session:
            JobRepository(worker_id=worker_id).start_execution(session, run_id=run_id)
            session.commit()
    finally:
        event.remove(engine, "before_cursor_execute", record)
        end(sessions, run_id)

    def index(*needles: str) -> int:
        return next(i for i, (statement, _) in enumerate(sent) if all(needle in statement for needle in needles))

    intake = index("FROM worker", "FOR SHARE")
    group_lock = index("FROM executor_group WHERE group_id", "FOR UPDATE")
    locks = [i for i, (statement, _) in enumerate(sent) if "pg_advisory_xact_lock" in statement]
    control = index("FROM execution_control", "FOR UPDATE")
    run_lock = index("FROM audit_run WHERE run_id", "FOR UPDATE")
    job_lock = index("FROM job WHERE run_id", "FOR UPDATE")
    assert len(locks) == 3
    assert intake < group_lock < locks[0] < locks[1] < locks[2] < control < run_lock < job_lock
    asked = [sent[i][1] for i in locks]
    assert [p["connection_id"] if isinstance(p, dict) else p[0] for p in asked] == sorted(
        item.connection_id for item in members), "ascending connection_id"
    bind = index("UPDATE audit_run SET connection_revision_id")
    assert job_lock < bind < index("INSERT INTO attempt"), "the binding is written under every lock and before the Attempt"


# --- 5: least loaded; equal members take turns ----------------------------------------------------------------------------


def test_the_emptier_member_is_chosen_and_an_equal_pair_takes_turns(sessions: sessionmaker[Session]) -> None:
    big, small = member(sessions, capacity=3), member(sessions, capacity=3)
    group_id, group_revision = group(sessions, big, small)
    held = [busy(sessions, big)[0], busy(sessions, big)[0]]             # big: 2 of 3 used; small: 0 of 3
    run_id = pending_run(sessions, group_revision)
    try:
        support.claim(sessions, run_id)
        assert row(sessions, run_id)["connection_revision_id"] == small.revision_id, "0/3 is less loaded than 2/3"
    finally:
        end(sessions, run_id, *held)

    a, b = member(sessions), member(sessions)
    group_id, group_revision = group(sessions, a, b)
    picked = []
    for _ in range(4):
        run = pending_run(sessions, group_revision)
        try:
            authority = support.claim(sessions, run)
            picked.append(row(sessions, run)["connection_revision_id"])
            support.finish(sessions, authority)                         # the unit is free again: the loads tie again
        finally:
            end(sessions, run)
    first, second = sorted([a, b], key=lambda item: item.connection_id)
    start = int(picked[0] == second.revision_id)                        # the persisted cursor decides where it starts
    assert picked == [(first, second)[(start + n) % 2].revision_id for n in range(4)], picked


# --- 6: every member busy -- the Run waits, and is offered when a unit is free --------------------------------------------------


def test_a_run_waits_when_every_member_is_full_and_binds_when_a_unit_is_free(sessions: sessionmaker[Session]) -> None:
    one, two = member(sessions), member(sessions)
    group_id, group_revision = group(sessions, one, two)
    (held_one, authority_one), (held_two, authority_two) = busy(sessions, one), busy(sessions, two)
    run_id = pending_run(sessions, group_revision)
    try:
        assert hint(sessions) is None, "no member has a free unit: the hint does not offer the Run"
        before = snapshot(sessions, run_id, group_id)
        refused = refuse(sessions, run_id)
        assert refused.wait_reason == "executor_at_capacity" and refused.code is ErrorCode.CONFLICT
        assert snapshot(sessions, run_id, group_id) == before, "a refused claim writes nothing, not even the rotation"

        sweep(sessions)
        waiting = row(sessions, run_id)
        assert (waiting["wait_reason"], waiting["binding_state"]) == ("executor_at_capacity", "pending")
        assert waiting["waiting_since"] is not None
        sweep(sessions)
        assert row(sessions, run_id)["waiting_since"] == waiting["waiting_since"], "the same reason keeps its clock"

        support.finish(sessions, authority_two)                         # one unit of `two` frees
        assert hint(sessions) == run_id, "a Run waiting only for capacity is offered when a member has a free unit"
        support.claim(sessions, run_id)
        bound = row(sessions, run_id)
        assert bound["connection_revision_id"] == two.revision_id and bound["wait_reason"] is None
    finally:
        end(sessions, run_id, held_one, held_two)


def test_waiting_for_a_busy_member_never_expires(sessions: sessionmaker[Session]) -> None:
    one = member(sessions)
    _group_id, group_revision = group(sessions, one)
    held, _ = busy(sessions, one)
    run_id = pending_run(sessions, group_revision)
    try:
        sweep(sessions, offline_wait_seconds=1)
        with sessions() as session:
            session.execute(text("UPDATE audit_run SET waiting_since = clock_timestamp() - interval '1 day' WHERE run_id = :r"),
                            {"r": run_id})
            session.commit()
        report = sweep(sessions, offline_wait_seconds=1)
        assert report.expired == 0 and row(sessions, run_id)["state"] == "queued"
    finally:
        end(sessions, run_id, held)


def test_the_carrier_stores_why_a_refused_claim_waits_in_a_transaction_of_its_own(sessions: sessionmaker[Session]) -> None:
    from auditmanager.runs.carrier import _record_group_wait

    one = member(sessions)
    _group_id, group_revision = group(sessions, one)
    held, _ = busy(sessions, one)
    run_id = pending_run(sessions, group_revision)
    try:
        refused = refuse(sessions, run_id)
        assert row(sessions, run_id)["wait_reason"] is None, "the refused claim's transaction was rolled back"
        _record_group_wait(sessions, run_id, refused)
        first = row(sessions, run_id)
        assert first["wait_reason"] == "executor_at_capacity" and first["waiting_since"] is not None
        _record_group_wait(sessions, run_id, refused)
        assert row(sessions, run_id)["waiting_since"] == first["waiting_since"]
        _record_group_wait(sessions, run_id, ExecutionNotClaimed(ErrorCode.CONFLICT))  # an ordinary refusal stores nothing
        assert row(sessions, run_id)["wait_reason"] == "executor_at_capacity"
    finally:
        end(sessions, run_id, held)


def test_the_hint_offers_a_pending_run_only_for_a_member_with_a_free_unit_and_leaves_every_other_run_alone(
    sessions: sessionmaker[Session],
) -> None:
    one, two = member(sessions), member(sessions)
    _group_id, group_revision = group(sessions, one, two)
    _plain_connection, plain_revision = support.new_connection(sessions, capacity=1)
    held_one, _ = busy(sessions, one)
    held_two, _ = busy(sessions, two)
    pending = pending_run(sessions, group_revision)                     # the oldest queued Run
    environment = support.queue_run(sessions, None)                     # frozen at start, no connection: never limited
    frozen = support.queue_run(sessions, plain_revision)
    try:
        assert hint(sessions) == environment, "the pending Run is the oldest, and is not offered: both members are full"
        assert hint(sessions, submitted=[environment]) == frozen
        assert hint(sessions, submitted=[environment, frozen]) is None
        end(sessions, held_one)                                         # one unit of `one` is free
        assert hint(sessions) == pending, "now the oldest Run has a member with a free unit"
        assert hint(sessions, submitted=[pending]) == environment
    finally:
        end(sessions, pending, environment, frozen, held_one, held_two)


# --- 7, 8: offline members ------------------------------------------------------------------------------------------------------


def test_an_offline_member_is_skipped_and_a_group_with_every_member_offline_waits_as_runner_offline(
    sessions: sessionmaker[Session],
) -> None:
    online, offline = member(sessions), member(sessions, online=False)
    group_id, group_revision = group(sessions, online, offline)
    run_id = pending_run(sessions, group_revision)
    second = pending_run(sessions, group_revision)
    try:
        support.claim(sessions, run_id)
        assert row(sessions, run_id)["connection_revision_id"] == online.revision_id, "the offline member is never chosen"
        seen(sessions, online.token_id, seconds_ago=3600)               # now nobody is online
        before = snapshot(sessions, second, group_id)
        assert refuse(sessions, second).wait_reason == "runner_offline"
        assert snapshot(sessions, second, group_id) == before
        sweep(sessions)
        assert row(sessions, second)["wait_reason"] == "runner_offline"
        assert hint(sessions) is None, "a Run waiting for a runner is not offered every poll"
        seen(sessions, online.token_id, seconds_ago=2)                  # the runner comes back ...
        end(sessions, run_id)                                           # ... and its unit is free
        sweep(sessions)
        assert row(sessions, second)["wait_reason"] is None and hint(sessions) == second
    finally:
        end(sessions, run_id, second)


def test_after_the_configured_time_every_member_offline_ends_no_executor_online(sessions: sessionmaker[Session]) -> None:
    gone = member(sessions, online=False)
    _group_id, group_revision = group(sessions, gone)
    run_id = pending_run(sessions, group_revision)
    try:
        assert sweep(sessions, offline_wait_seconds=1).expired == 0
        assert row(sessions, run_id)["wait_reason"] == "runner_offline"
        assert sweep(sessions, offline_wait_seconds=1800).expired == 0, "not yet"
        with sessions() as session:
            session.execute(text("UPDATE audit_run SET waiting_since = clock_timestamp() - interval '10 seconds' WHERE run_id = :r"),
                            {"r": run_id})
            session.commit()
        assert sweep(sessions, offline_wait_seconds=5).expired == 1
        ended = row(sessions, run_id)
        assert ended["state"] == "failed" and ended["terminal_reason"] == "dependency_unavailable"
        assert dict(ended["terminal_detail"]) == {"dependency": "no_executor_online"}
        assert ended["wait_reason"] is None and ended["waiting_since"] is None, "a finished Run waits for nothing"
        assert ended["binding_state"] == "pending" and ended["connection_revision_id"] is None, "no connection was ever chosen"
        assert support.job_state(sessions, run_id) == "cancelled" and support.attempts(sessions, run_id) == 0
        (expired,) = events(sessions, run_id, "executor.group_wait_expired")
        assert expired["reason"] == "no_executor_online"
        assert sweep(sessions, offline_wait_seconds=5).expired == 0, "ended once"
    finally:
        end(sessions, run_id)


# --- 9, 10: a member that is not what the group snapshotted -------------------------------------------------------------------


def test_a_member_revised_after_admission_is_ineligible_and_never_adopted(sessions: sessionmaker[Session]) -> None:
    one, two = member(sessions), member(sessions)
    group_id, group_revision = group(sessions, one, two)
    with sessions() as session:
        newer = revise_connection(
            session, connection_id=one.connection_id, settings=replace(PULL, timeout_seconds=601),
            pinned_model_ids=PIN_IDS, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR).revision_id
        session.commit()
    first, second = pending_run(sessions, group_revision), pending_run(sessions, group_revision)
    try:
        support.claim(sessions, first)
        assert row(sessions, first)["connection_revision_id"] == two.revision_id, "`one` now differs from the snapshot"
        before = snapshot(sessions, second, group_id)
        refused = refuse(sessions, second)                              # `two` is full, `one` is not what the group holds
        assert refused.wait_reason == "executor_at_capacity"
        assert snapshot(sessions, second, group_id) == before
        with sessions() as session:
            assert session.execute(text("SELECT count(*) FROM audit_run WHERE connection_revision_id = :n"),
                                   {"n": newer}).scalar_one() == 0, "the new revision is never adopted"
    finally:
        end(sessions, first, second)


def test_an_archived_unprobed_or_offline_member_is_never_chosen(sessions: sessionmaker[Session]) -> None:
    good, archived, failed, offline = (member(sessions) for _ in range(4))
    _group_id, group_revision = group(sessions, good, archived, failed, offline)
    with sessions() as session:
        archive_connection(session, connection_id=archived.connection_id, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
        probe = request_probe(
            session, connection_id=failed.connection_id, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
        assert record_probe_started(session, probe.probe_id)
        assert record_probe_result(session, probe.probe_id, outcome="timeout")     # the latest probe of `failed` is not ok
        session.commit()
    seen(sessions, offline.token_id, seconds_ago=3600)
    runs = [pending_run(sessions, group_revision) for _ in range(2)]
    try:
        support.claim(sessions, runs[0])
        assert row(sessions, runs[0])["connection_revision_id"] == good.revision_id
        # `good` is full now; the three others are each ineligible for a different reason, and none is adopted.
        assert refuse(sessions, runs[1]).wait_reason == "executor_at_capacity"
        for other in (archived, failed, offline):
            assert support.active_runs(sessions, other.connection_id) == []
    finally:
        end(sessions, *runs)


# --- 11: two claimants, one binding ---------------------------------------------------------------------------------------------


def test_two_claims_for_the_last_unit_of_a_two_member_group_bind_exactly_one_run(sessions: sessionmaker[Session]) -> None:
    one, two = member(sessions), member(sessions)
    _group_id, group_revision = group(sessions, one, two)
    held, _ = busy(sessions, one)                                       # `one` is full: one free unit left, on `two`
    first, second = pending_run(sessions, group_revision), pending_run(sessions, group_revision)
    start = threading.Barrier(2)
    results: dict[str, Any] = {}

    def claim(run_id: str) -> None:
        start.wait(timeout=WAIT_SECONDS)
        try:
            support.claim(sessions, run_id)
            results[run_id] = "claimed"
        except GroupDispatchWaiting as refusal:
            results[run_id] = refusal.wait_reason
        except BaseException as failure:
            results[run_id] = failure

    threads = [threading.Thread(target=claim, args=(run_id,)) for run_id in (first, second)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(WAIT_SECONDS)
        assert sorted(map(str, results.values())) == sorted(["claimed", "executor_at_capacity"]), results
        assert len(support.active_runs(sessions, two.connection_id)) == 1
        assert sum(row(sessions, run)["binding_state"] == "bound" for run in (first, second)) == 1
    finally:
        end(sessions, first, second, held)


def test_two_claims_of_one_pending_run_bind_it_once(sessions: sessionmaker[Session]) -> None:
    one, two = member(sessions), member(sessions)
    group_id, group_revision = group(sessions, one, two)
    run_id = pending_run(sessions, group_revision)
    start = threading.Barrier(2)
    results: list[Any] = []

    def claim() -> None:
        start.wait(timeout=WAIT_SECONDS)
        try:
            support.claim(sessions, run_id)
            results.append("claimed")
        except ExecutionNotClaimed as refusal:
            results.append(refusal.code)
        except BaseException as failure:
            results.append(failure)

    threads = [threading.Thread(target=claim) for _ in range(2)]
    cursor = rotation(sessions, group_id)
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(WAIT_SECONDS)
        assert results.count("claimed") == 1 and len(results) == 2, results
        assert support.attempts(sessions, run_id) == 1 and rotation(sessions, group_id) == cursor + 1
        assert len(events(sessions, run_id, "executor.run_dispatched")) == 1
    finally:
        end(sessions, run_id)


def test_the_last_unit_goes_to_one_of_two_processes_queued_on_the_groups_lock(
    engine: Engine, sessions: sessionmaker[Session],
) -> None:
    """The first claim takes the group's row and the members' locks and does not commit. A second **process** claims another
    Run of the group and must queue on the group's lock, not read around it: when the first commits, the member it bound
    holds its unit and the second is refused. Without the group lock the child would count the unit free and bind too."""
    one, two = member(sessions), member(sessions)
    group_id, group_revision = group(sessions, one, two)
    held, _ = busy(sessions, one)
    mine, theirs = pending_run(sessions, group_revision), pending_run(sessions, group_revision)
    holder = sessions()
    child = None
    try:
        JobRepository().start_execution(holder, run_id=mine)            # locks taken, nothing committed
        child = support.claim_in_a_second_process(theirs)
        _wait_until(lambda: _a_backend_waits_on_a_lock(engine), what="the other process to queue on the group's lock")
        assert child.poll() is None, "the other process did not wait for the first claim"
        holder.commit()
        answer = support.child_result(child)
        assert answer == {"result": "refused", "code": ErrorCode.CONFLICT.value}, answer
        assert row(sessions, mine)["connection_revision_id"] == two.revision_id
        assert row(sessions, theirs)["binding_state"] == "pending" and support.attempts(sessions, theirs) == 0
        assert len(support.active_runs(sessions, two.connection_id)) == 1
    finally:
        holder.close()
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate()
        end(sessions, mine, theirs, held)


def test_a_claim_that_rolls_back_leaves_the_member_to_the_process_waiting_behind_it(
    engine: Engine, sessions: sessionmaker[Session],
) -> None:
    one, two = member(sessions), member(sessions)
    group_id, group_revision = group(sessions, one, two)
    held, _ = busy(sessions, one)
    mine, theirs = pending_run(sessions, group_revision), pending_run(sessions, group_revision)
    cursor = rotation(sessions, group_id)
    holder = sessions()
    child = None
    try:
        JobRepository().start_execution(holder, run_id=mine)
        child = support.claim_in_a_second_process(theirs)
        _wait_until(lambda: _a_backend_waits_on_a_lock(engine), what="the other process to queue on the group's lock")
        holder.rollback()
        assert support.child_result(child) == {"result": "claimed"}
        assert row(sessions, theirs)["connection_revision_id"] == two.revision_id
        assert row(sessions, mine)["binding_state"] == "pending"
        assert rotation(sessions, group_id) == cursor + 1, "the rolled-back claim did not move the rotation"
    finally:
        holder.close()
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate()
        end(sessions, mine, theirs, held)


# --- 12: the consent --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("changes", [
    {"rate_sha256": "0" * 64},
    {"model_id": "claude-opus-5"},
    {"billing": "metered"},
    {"executor_group_revision_id": "exgr_01M2545JSD15ETSNNV904X999R"},
])
def test_a_consent_that_no_longer_holds_binds_nothing_and_the_hint_stops_offering_the_run(
    sessions: sessionmaker[Session], changes: dict[str, str],
) -> None:
    one = member(sessions)
    group_id, group_revision = group(sessions, one)
    run_id = pending_run(sessions, group_revision, command_id=consent_for(sessions, group_revision, **changes))
    other = pending_run(sessions, group_revision, command_id=consent_for(sessions, group_revision))
    try:
        before = snapshot(sessions, run_id, group_id)
        assert refuse(sessions, run_id).wait_reason == "needs_reconsent"
        assert snapshot(sessions, run_id, group_id) == before, "nothing is bound, nothing is written"
        sweep(sessions)
        assert row(sessions, run_id)["wait_reason"] == "needs_reconsent"
        assert hint(sessions) == other, "the Run that needs a new consent is not offered again and again"
        support.claim(sessions, other)                                  # a Run whose consent holds is not held back by it
        assert row(sessions, other)["binding_state"] == "bound"
    finally:
        end(sessions, run_id, other)


# --- 14: no re-routing after binding --------------------------------------------------------------------------------------------


def test_a_lease_lost_after_binding_retries_on_the_bound_member_even_with_the_other_free(
    sessions: sessionmaker[Session],
) -> None:
    one, two = member(sessions), member(sessions)
    _group_id, group_revision = group(sessions, one, two)
    run_id = pending_run(sessions, group_revision)
    try:
        authority = support.claim(sessions, run_id)
        bound = row(sessions, run_id)["connection_revision_id"]
        other = two if bound == one.revision_id else one
        with sessions() as session:
            session.execute(text("UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' WHERE lease_id = :l"),
                            {"l": authority.lease_id})
            session.commit()
        with sessions() as session:
            assert JobRepository().reclaim_expired(session) >= 1
            session.commit()
        assert support.job_state(sessions, run_id) == "queued"
        assert row(sessions, run_id)["binding_state"] == "bound", "recovery does not unbind"
        support.claim(sessions, run_id)
        again = row(sessions, run_id)
        assert again["connection_revision_id"] == bound != other.revision_id, "the retry stayed on its member"
        assert support.attempts(sessions, run_id) == 2
        assert len(events(sessions, run_id, "executor.run_dispatched")) == 1, "one dispatch, not two"
    finally:
        end(sessions, run_id)


def test_a_retry_whose_bound_member_is_full_waits_for_it_and_is_not_moved_to_the_free_one(
    sessions: sessionmaker[Session],
) -> None:
    one, two = member(sessions), member(sessions)
    _group_id, group_revision = group(sessions, one, two)
    run_id = pending_run(sessions, group_revision)
    try:
        authority = support.claim(sessions, run_id)
        bound = row(sessions, run_id)["connection_revision_id"]
        mine, other = (one, two) if bound == one.revision_id else (two, one)
        with sessions() as session:
            session.execute(text("UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' WHERE lease_id = :l"),
                            {"l": authority.lease_id})
            session.commit()
        with sessions() as session:
            JobRepository().reclaim_expired(session)
            session.commit()
        rival, _ = busy(sessions, mine)                                 # someone takes the bound member's freed unit
        try:
            assert hint(sessions) is None, "the bound Run is limited by its own member, like any frozen Run"
            with pytest.raises(ExecutionNotClaimed) as refused:
                support.claim(sessions, run_id)
            assert not isinstance(refused.value, GroupDispatchWaiting) and refused.value.code is ErrorCode.CONFLICT
            assert row(sessions, run_id)["connection_revision_id"] == mine.revision_id
            assert support.active_runs(sessions, other.connection_id) == [], "the other member stayed free"
        finally:
            end(sessions, rival)
    finally:
        end(sessions, run_id)


def test_an_outcome_unknown_is_never_redispatched(sessions: sessionmaker[Session]) -> None:
    one, two = member(sessions), member(sessions)
    _group_id, group_revision = group(sessions, one, two)
    run_id = pending_run(sessions, group_revision)
    try:
        authority = support.claim(sessions, run_id)
        bound = row(sessions, run_id)["connection_revision_id"]
        with sessions() as session:
            JobRepository().prepare_provider_call(
                session, authority, provider="claude_code_session", model_identity="claude-sonnet-5",
                provider_mode="live", parameters={}, request_sha256="d" * 64, connection_revision_id=bound,
                identity_basis="declared")
            session.commit()
        with sessions() as session:
            session.execute(text("UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' WHERE lease_id = :l"),
                            {"l": authority.lease_id})
            session.commit()
        with sessions() as session:
            JobRepository().reclaim_expired(session)
            session.commit()
        ended = row(sessions, run_id)
        assert ended["state"] == "failed", "the call may have been sent: the Run ends, it is not sent to another member"
        assert support.job_state(sessions, run_id) != "queued" and support.attempts(sessions, run_id) == 1
        assert (ended["binding_state"], ended["connection_revision_id"]) == ("bound", bound)
        assert len(events(sessions, run_id, "executor.run_dispatched")) == 1
    finally:
        end(sessions, run_id)


# --- 18: everything else claims as it did --------------------------------------------------------------------------------------


def test_a_run_frozen_at_start_claims_as_before_beside_a_group_that_is_full(sessions: sessionmaker[Session]) -> None:
    one = member(sessions)
    group_id, group_revision = group(sessions, one)
    held, _ = busy(sessions, one)
    pending = pending_run(sessions, group_revision)
    environment = support.queue_run(sessions, None)
    cursor = rotation(sessions, group_id)
    try:
        assert refuse(sessions, pending).wait_reason == "executor_at_capacity", (
            "the pending Run's NULL connection is not read as 'never limited'")
        support.claim(sessions, environment)
        assert row(sessions, environment)["binding_state"] == "frozen_at_start"
        assert events(sessions, environment, "executor.") == []
        assert rotation(sessions, group_id) == cursor, "neither the refusal nor the environment Run touched the group"
    finally:
        end(sessions, pending, environment, held)


# --- helpers for the process tests ----------------------------------------------------------------------------------------------


def _wait_until(predicate: Any, *, what: str) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out after {WAIT_SECONDS:.0f} s waiting for {what}")


def _a_backend_waits_on_a_lock(engine: Engine) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname = current_database() "
            "AND pid <> pg_backend_pid() AND state = 'active' AND wait_event_type = 'Lock')"
        )).scalar_one())
