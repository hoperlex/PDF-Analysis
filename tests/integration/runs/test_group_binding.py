"""`EXEC2-GROUP-RUN-01`, premise P-01 and decisions 12, 14 and 15 on real PostgreSQL -- the readers of a Run's frozen revision, the
claim inside ``execute_run``, and what the status and the queue say.

Real PostgreSQL and S3 (the baseline corpus PDF), the recorded adapter, one rolled-back transaction per test. A Run admitted on a
group is made with ``RunRepository.create`` exactly as ``start_audit_run`` makes it (``binding_state = 'pending'``, the group
revision, no connection); the members are ``pull`` connections made by the executors context's own commands, probed ``ok`` and with
a runner seen a moment ago. Written and **not run** in EXEC-2 (`R-149d`, D-292). B3 section 11 numbers are the task file's reading of
it (the integrator re-maps them):

* **4 -- ``execute_run`` binds before any stage.** The claim writes the member into the Run; the executor re-reads the row, so the
  provider resolver is handed the *bound* Run and calls the recorded adapter once; the Run publishes; the row says ``bound``, the
  status names the plan and the binding, ``executor`` names the same connection;
* **6, 7 -- a Run no member can take is not run:** ``execute_run`` raises the claim's refusal, calls no provider and leaves the Run and
  its Job queued and unchanged;
* **17 -- the ``environment`` source never runs a pending Run:** it serves neither a Run with no connection nor one bound to a
  connection, so the stage fails with ``executor_route_missing`` and the adapter is not called;
* **18 -- every other Run reads as it did:** the row, the status body and the queue item of a Run whose executor was frozen at start
  carry none of the new fields;
* **15 -- waiting is visible:** ``wait_reason`` and ``waiting_since`` reach the status and the queue item of a pending Run, and only
  of a pending one that has not ended.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.api.schemas.runs import run_status_body
from auditmanager.bootstrap.adapters import ExecutionAdapter, _run_status_view
from auditmanager.bootstrap.providers import EnvironmentProviders
from auditmanager.executors.public import (
    GroupSettings,
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
)
from auditmanager.jobs.public import JobRepository
from auditmanager.jobs.repository import GroupDispatchWaiting
from auditmanager.runs import ProviderBinding, RunRepository, execute_run
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import RunId
from tests.support.v1_reference_profile import resolve_reference_profile

ACTOR = f"usr_{'0' * 26}"
ROLES = frozenset({"admin"})
PINS = pinned_models()
PIN_IDS = {pin.model_id for pin in PINS}
PULL = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", allow_client_documents=False,
    timeout_seconds=600, pull_client="claude_code_session", answer_deadline_seconds=600, max_claimed_tasks=1,
    max_active_runs=1,
)
SETTINGS = GroupSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered", strategy="least_loaded")


def key() -> str:
    return f"bnd-{uuid4().hex}"


@dataclass(frozen=True)
class Member:
    connection_id: str
    revision_id: str


def ready_member(session, *, online: bool = True) -> Member:  # type: ignore[no-untyped-def]
    """A ``pull`` connection dispatch would choose: probed ``ok`` on its current revision and a runner seen a moment ago."""
    connection_id = create_connection(
        session, kind="pull", display_name=f"member-{uuid4().hex[:8]}", roles=ROLES, idempotency_key=key(),
        actor_uid=ACTOR).connection_id
    revision_id = revise_connection(
        session, connection_id=connection_id, settings=PULL, pinned_model_ids=PIN_IDS, roles=ROLES,
        idempotency_key=key(), actor_uid=ACTOR).revision_id
    probe = request_probe(session, connection_id=connection_id, roles=ROLES, idempotency_key=key(), actor_uid=ACTOR)
    assert record_probe_started(session, probe.probe_id)
    assert record_probe_result(
        session, probe.probe_id, outcome="ok", reported_model="claude-sonnet-5", identity_basis="declared",
        rate_check="not_metered")
    if online:
        token = issue_runner_token(
            session, connection_id=connection_id, expires_in_days=None, roles=ROLES, idempotency_key=key(),
            actor_uid=ACTOR).record.token_id
        session.execute(text(
            "UPDATE executor_runner_token SET last_seen_at = clock_timestamp() - make_interval(secs => 5) "
            "WHERE token_id = :id"), {"id": token})
    return Member(connection_id, revision_id)


def make_group(session, *members: Member) -> str:  # type: ignore[no-untyped-def]
    """The first group revision of a group over the members' current revisions."""
    return create_group(
        session, display_name=f"Pool {uuid4().hex[:8]}", settings=SETTINGS,
        members=[MemberRequest(member.connection_id, member.revision_id, None) for member in members], pins=PINS,
        roles=ROLES, idempotency_key=key(), actor_uid=ACTOR).current_revision.group_revision_id


def make_run(session, seeded, *, group_revision_id: str | None = None, queued: bool = True) -> str:  # type: ignore[no-untyped-def]
    """A Run as ``start_audit_run`` leaves it: pending on a group revision, or frozen at start with no connection."""
    run_id = str(RunId.new())
    repository = RunRepository()
    repository.create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
        **({} if group_revision_id is None else {
            "binding_state": "pending", "executor_group_revision_id": group_revision_id}))
    if queued:
        repository.advance(session, run_id=run_id, from_state="created", to_state="queued")
        JobRepository().enqueue(session, run_id=run_id)
    return run_id


class Resolver:
    """The composition root's provider resolver, recording the Run it was handed and answering the recorded adapter."""

    def __init__(self, adapter: Any, config: Any) -> None:
        self.seen: list[tuple[str, str | None]] = []
        self._adapter, self._config = adapter, config

    def __call__(self, session: Any, run: Any, context: Any) -> ProviderBinding:
        self.seen.append((run.binding_state, run.connection_revision_id))
        return ProviderBinding(adapter=self._adapter, config=self._config, call=None)


class Counting:
    """An adapter that counts how often it is asked, for the source that must never ask it."""

    def __init__(self, inner: Any) -> None:
        self._inner, self.calls = inner, 0

    @property
    def provider_mode(self) -> Any:
        return self._inner.provider_mode

    def complete(self, request: Any) -> Any:
        self.calls += 1
        return self._inner.complete(request)


def run_row(session, run_id: str) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return dict(session.execute(text(
        "SELECT state, binding_state, executor_group_revision_id, connection_revision_id, wait_reason, waiting_since "
        "FROM audit_run WHERE run_id = :r"), {"r": run_id}).mappings().one())


def job_state(session, run_id: str) -> str | None:  # type: ignore[no-untyped-def]
    return session.execute(text("SELECT state FROM job WHERE run_id = :r"), {"r": run_id}).scalar_one_or_none()


# --- the row and its readers ------------------------------------------------------------------------------------------------------


def test_a_pending_run_is_read_back_as_pending_and_an_environment_run_as_frozen_at_start(session, seeded) -> None:  # type: ignore[no-untyped-def]
    group_revision = make_group(session, ready_member(session))
    pending = make_run(session, seeded, group_revision_id=group_revision, queued=False)
    environment = make_run(session, seeded, queued=False)
    repository = RunRepository()
    one, two = repository.get(session, pending), repository.get(session, environment)
    assert (one.binding_state, one.executor_group_revision_id, one.connection_revision_id) == ("pending", group_revision, None)
    assert (two.binding_state, two.executor_group_revision_id, two.connection_revision_id) == ("frozen_at_start", None, None)
    assert one.connection_revision_id is None and two.connection_revision_id is None, (
        "both have no connection; the binding state is what tells them apart")
    assert one.routing_rule_revision_id is None and one.wait_reason is None and one.waiting_since is None


def test_the_binding_facts_name_only_the_runs_admitted_on_a_group_and_a_wait_only_while_it_lasts(session, seeded) -> None:  # type: ignore[no-untyped-def]
    group_revision = make_group(session, ready_member(session))
    waiting = make_run(session, seeded, group_revision_id=group_revision)
    ended = make_run(session, seeded, group_revision_id=group_revision)
    ordinary = make_run(session, seeded)
    JobRepository().record_group_wait(session, run_id=waiting, reason="runner_offline")
    JobRepository().record_group_wait(session, run_id=ended, reason="executor_at_capacity")
    repository = RunRepository()
    repository.terminate(session, run_id=ended, from_state="queued", to_state="failed",
                         terminal_reason=ErrorCode.ANALYSIS_FAILED.value)
    facts = repository.binding_facts(session, [waiting, ended, ordinary])
    assert facts == {waiting: ("pending", "runner_offline"), ended: ("pending", None)}, "an ordinary Run is absent"
    repository.clear_wait(session, run_id=ended)
    assert run_row(session, ended)["wait_reason"] is None and run_row(session, ended)["waiting_since"] is None


# --- 4: execute_run binds before any stage -------------------------------------------------------------------------------------------


def test_execute_run_binds_a_member_before_any_stage_and_the_provider_is_handed_the_bound_run(
    session, blob_store, seeded, recorded_adapter, provider_config,
) -> None:  # type: ignore[no-untyped-def]
    member = ready_member(session)
    group_revision = make_group(session, member)
    run_id = make_run(session, seeded, group_revision_id=group_revision)
    adapter = Counting(recorded_adapter)
    resolver = Resolver(adapter, provider_config)

    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=adapter, provider_config=provider_config,
        providers=resolver, text_profiles=resolve_reference_profile)

    assert result.terminal_state == "published" and adapter.calls == 1
    assert resolver.seen == [("bound", member.revision_id)], "the Run the stage is bound for is the bound one"
    row = run_row(session, run_id)
    assert (row["binding_state"], row["connection_revision_id"], row["executor_group_revision_id"]) == (
        "bound", member.revision_id, group_revision)
    assert row["wait_reason"] is None
    (dispatched,) = session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'executor.run_dispatched' AND aggregate_id = :r"),
        {"r": run_id}).scalars().all()
    assert dispatched["connection_id"] == member.connection_id and dispatched["revision_id"] == member.revision_id

    body = run_status_body(_run_status_view(session, run_id))
    assert body["binding_state"] == "bound" and body["binding"]["connection_id"] == member.connection_id
    assert body["binding"]["connection_revision_id"] == member.revision_id
    assert body["executor"]["connection_id"] == member.connection_id, "`executor` names the same connection"
    assert body["planned"]["executor_group_revision_id"] == group_revision
    assert "wait_reason" not in body and "queue_reason" not in body


# --- 6, 7: a Run no member can take is not run -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("how", ["full", "offline"])
def test_execute_run_of_a_pending_run_no_member_can_take_calls_nothing_and_leaves_it_queued(
    session, blob_store, seeded, recorded_adapter, provider_config, how: str,
) -> None:  # type: ignore[no-untyped-def]
    member = ready_member(session, online=how == "full")
    group_revision = make_group(session, member)
    if how == "full":
        occupant = make_run(session, seeded, group_revision_id=group_revision)
        JobRepository().start_execution(session, run_id=occupant)        # the member's only unit
    run_id = make_run(session, seeded, group_revision_id=group_revision)
    adapter = Counting(recorded_adapter)
    resolver = Resolver(adapter, provider_config)
    before = run_row(session, run_id)

    with pytest.raises(GroupDispatchWaiting) as refused:
        execute_run(
            session, run_id, blob_store=blob_store, adapter=adapter, provider_config=provider_config,
            providers=resolver, text_profiles=resolve_reference_profile)

    assert refused.value.wait_reason == ("executor_at_capacity" if how == "full" else "runner_offline")
    assert adapter.calls == 0 and resolver.seen == []
    assert run_row(session, run_id) == before and job_state(session, run_id) == "queued"


# --- 17: the environment source never runs a pending Run ------------------------------------------------------------------------------------


def test_the_environment_source_never_runs_group_work_even_when_the_claim_bound_it(
    session, blob_store, seeded, recorded_adapter, provider_config,
) -> None:  # type: ignore[no-untyped-def]
    member = ready_member(session)
    run_id = make_run(session, seeded, group_revision_id=make_group(session, member))
    adapter = Counting(recorded_adapter)
    source = EnvironmentProviders(adapter, provider_config)

    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=adapter, provider_config=provider_config,
        providers=source.resolve, text_profiles=resolve_reference_profile)

    assert adapter.calls == 0, "the environment adapter was never asked to run group work"
    assert result.terminal_state != "published"
    stage = next(row for row in RunRepository().stage_results(session, run_id) if row.stage_id == "text_analysis")
    assert stage.error["code"] == "dependency_unavailable"
    assert stage.error["details"]["dependency"] == "executor_route_missing"


# --- 15, 18: the status and the queue ---------------------------------------------------------------------------------------------------


def test_the_status_of_a_waiting_pending_run_says_why_and_since_when_and_an_ended_one_waits_for_nothing(
    session, seeded,
) -> None:  # type: ignore[no-untyped-def]
    group_revision = make_group(session, ready_member(session))
    run_id = make_run(session, seeded, group_revision_id=group_revision)
    JobRepository().record_group_wait(session, run_id=run_id, reason="executor_at_capacity")
    body = run_status_body(_run_status_view(session, run_id))
    assert body["binding_state"] == "pending" and body["wait_reason"] == "executor_at_capacity"
    assert "waiting_since" in body and "binding" not in body and "executor" not in body
    assert "queue_reason" not in body, "a pending Run reports its stored wait, not a derived queue reason"
    assert body["planned"]["executor_group_revision_id"] == group_revision
    assert body["planned"]["pin_id"] == "claude-sonnet-5" and body["planned"]["billing"] == "not_metered"

    RunRepository().terminate(session, run_id=run_id, from_state="queued", to_state="failed",
                              terminal_reason=ErrorCode.DEPENDENCY_UNAVAILABLE.value,
                              terminal_detail={"dependency": "no_executor_online"})
    ended = run_status_body(_run_status_view(session, run_id))
    assert "wait_reason" not in ended and "waiting_since" not in ended
    assert ended["terminal_reason"] == "dependency_unavailable"
    assert ended["terminal_detail"] == {"dependency": "no_executor_online"}


def test_a_run_whose_executor_was_frozen_at_start_reads_exactly_as_before(session, seeded) -> None:  # type: ignore[no-untyped-def]
    body = run_status_body(_run_status_view(session, make_run(session, seeded)))
    assert not {"binding_state", "planned", "binding", "wait_reason", "waiting_since"} & set(body)


def test_the_queue_item_of_a_group_run_carries_its_binding_state_and_wait_and_an_ordinary_one_does_not(
    session, seeded,
) -> None:  # type: ignore[no-untyped-def]
    group_revision = make_group(session, ready_member(session))
    pending = make_run(session, seeded, group_revision_id=group_revision)
    ordinary = make_run(session, seeded)
    JobRepository().record_group_wait(session, run_id=pending, reason="runner_offline")
    queue = ExecutionAdapter(lambda: nullcontext(session), runs=None)  # type: ignore[arg-type]
    items = {item.run_id: item for item in queue.list_queue(cursor=None, limit=1000).items}
    assert items[pending].binding_state.value == "pending" and items[pending].wait_reason.value == "runner_offline"
    assert items[ordinary].binding_state is None and items[ordinary].wait_reason is None
    assert "binding_state" not in items[ordinary].model_dump(exclude_unset=True)
