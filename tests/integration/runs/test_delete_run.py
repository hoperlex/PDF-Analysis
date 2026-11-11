"""`RUN-DELETE-01` on real PostgreSQL: ``deleteRun`` takes a partial, failed or cancelled run out of the run lists and nothing else.

Owner hotfix 2026-11-11: «удалять частичные и непрошедшие прогоны в UI — они необъективны, это шум». The shipped ``ExecutionAdapter`` (the port the
route calls), the shipped ``RunAdapter`` for the reads, on the suite's rolled-back session (every row a test writes is its own; the lane database
holds other suites' rows, so a count over it would be an assertion about someone else's data -- each test counts a **difference**).

* the three deletable states get one immutable tombstone (the actor, the command receipt) and the run leaves ``listRuns``, while the run row is
  byte for byte what it was, ``getRunStatus`` still answers it, and its findings stay stored;
* every other state is ``state_transition_not_allowed`` (``machine``, ``current_state``, ``requested_state``) and writes neither a tombstone nor a receipt;
* an unknown run and a run already deleted are ``not_found``; a repeat of the same keyed call replays the first answer; the same key on another run is
  ``idempotency_key_reuse``; a caller with neither ``expert`` nor ``admin`` is ``permission_denied``;
* the readers: the dashboard's runs by state, a document's audit state (a deleted partial run gives way to the published run before it), the
  execution queue with its counts and its live-failure count (the failed job leaves them; ``getQueueItem`` by identity still answers), and the walk of a
  version's runs (the block index, the portal source, the comparison's pick) which never lands on a deleted run;
* the tombstone is immutable (no update, no delete) and a project's runs cannot be removed from under it.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from auditmanager.access.accounts import AccountRepository as AccountAccessRepository
from auditmanager.access.repository import UserRepository as UserAccessRepository
from auditmanager.analysis.public import ProviderConfig, ProviderMode
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.bootstrap.adapters import ExecutionAdapter, RunAdapter
from auditmanager.dashboard import AuditCountsRecord, DashboardRepository, DocumentAuditReadModel, tally
from auditmanager.execution.public import ExecutionRepository
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DecisionId,
    FindingObservationId,
    FindingUid,
    PromptBundleId,
    RunId,
)

RECORDED_CONFIG = ProviderConfig(ProviderMode.RECORDED, "claude-opus-5", 1.0, None, True)
REGISTRY = load_text_profile_registry()
DELETABLE = ("partial", "failed", "cancelled")
REFUSED = ("created", "queued", "running", "validating", "published")


class _Carrier:
    def submit(self, job: object) -> None:  # pragma: no cover - nothing here starts a run
        raise AssertionError("deleteRun starts nothing")

    def shutdown(self) -> None:
        return None


def _adapters(session: Any) -> tuple[ExecutionAdapter, RunAdapter]:
    """The shipped adapters on the suite's own connection. Every ``with factory()`` they open is a **savepoint** of the suite's rolled-back
    transaction: a clean call is committed into it, and a refused call (an exception out of the ``with``) is rolled back to it, exactly what a
    refusal does to a served request -- so "a refused call leaves no receipt" is proved and not assumed."""
    holder = sessionmaker(bind=session.get_bind(), expire_on_commit=False, future=True, join_transaction_mode="create_savepoint")
    runs = RunAdapter(
        holder, blob_store=None, adapter=None, provider_config=RECORDED_CONFIG, provider_mode="recorded", carrier=_Carrier(),  # type: ignore[arg-type]
        section_profiles=REGISTRY.section_profiles(), text_profiles=REGISTRY.resolve,
    )
    return ExecutionAdapter(holder, runs=runs), runs  # type: ignore[arg-type]


def _account(session: Any, *roles: str) -> str:
    """A complete account holding exactly ``roles`` (a login unique to this call)."""
    login = f"rd01-{uuid.uuid4().hex[:10]}@suite.invalid"
    users, accounts = UserAccessRepository(), AccountAccessRepository()
    created = users.create_user(session, login, "rd01-suite-password")
    accounts.complete_profile(session, user_uid=str(created.user_uid), email=None, last_name="Тестов", first_name="Тест")
    for role in roles:
        accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
    return str(created.user_uid)


def _key(label: str) -> str:
    return f"rd01-{label}-{uuid.uuid4().hex[:12]}"


def _run(session: Any, seeded: Any, state: str, *, age: int = 0) -> str:
    """One run of the seeded version, created ``age`` seconds ago and walked along the declared edges to ``state``.

    The row is inserted with its own ``created_at`` (``now()`` is one value for the whole rolled-back transaction, and ``listRuns`` orders by
    it), then moved by the repository's own transitions, so the state machine's trigger and CHECKs see every step."""
    run_id = str(RunId.new())
    repo = RunRepository()
    session.execute(
        text("INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
             "frozen_input_digest, created_at) VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :d, "
             "now() - make_interval(secs => CAST(:age AS double precision)))"),
        {"r": run_id, "p": seeded.project_uid, "v": seeded.version_uid, "ap": seeded.analysis_profile_id,
         "pb": seeded.prompt_bundle_id, "d": "c" * 64, "age": age},
    )
    if state == "cancelled":
        repo.terminate(session, run_id=run_id, from_state="created", to_state="cancelled")
        return run_id
    if state == "created":
        return run_id
    repo.advance(session, run_id=run_id, from_state="created", to_state="queued")
    if state == "queued":
        return run_id
    repo.advance(session, run_id=run_id, from_state="queued", to_state="running")
    if state == "running":
        return run_id
    if state == "failed":
        repo.terminate(session, run_id=run_id, from_state="running", to_state="failed", terminal_reason=ErrorCode.ANALYSIS_FAILED.value)
        return run_id
    repo.advance(session, run_id=run_id, from_state="running", to_state="validating")
    if state == "validating":
        return run_id
    if state == "partial":
        repo.terminate(session, run_id=run_id, from_state="validating", to_state="partial", degradation_set=("block_analysis",))
        return run_id
    assert state == "published", state
    repo.terminate(session, run_id=run_id, from_state="validating", to_state="published")
    return run_id


def _finding(session: Any, seeded: Any, run_id: str, *, verdict: str | None) -> str:
    """One finding allocated by ``run_id`` with its grounded observation, and an ``accept`` event when ``verdict`` is ``accepted``."""
    finding_uid, observation_id = str(FindingUid.new()), str(FindingObservationId.new())
    session.execute(
        text("INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
             "VALUES (:f, :p, :v, :r, 'internal_contradiction')"),
        {"f": finding_uid, "p": seeded.project_uid, "v": seeded.version_uid, "r": run_id},
    )
    session.execute(
        text("INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
             "recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
             "VALUES (:o, :r, :f, 'text_analysis', 'internal_contradiction', 'text', 'recommendation', true, :ap, :pb, 'recorded')"),
        {"o": observation_id, "r": run_id, "f": finding_uid, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new())},
    )
    if verdict == "accepted":
        session.execute(
            text("INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, verdict, comment, "
                 "author_label) VALUES (:d, :f, :o, 'accept', 'accepted', NULL, 'rd01 suite')"),
            {"d": str(DecisionId.new()), "f": finding_uid, "o": observation_id},
        )
    return finding_uid


def _count(session: Any, sql: str, **params: Any) -> int:
    return int(session.execute(text(sql), params).scalar_one())


def _tombstones(session: Any, run_id: str) -> list[Any]:
    return list(session.execute(
        text("SELECT run_id, deleted_by_user_uid, command_id FROM audit_run_deletion WHERE run_id = :r"), {"r": run_id}
    ).all())


def _listed(runs: RunAdapter, seeded: Any) -> list[str]:
    return [str(view.run_id) for view in runs.list_runs(version_uid=seeded.version_uid)]


def _row(session: Any, run_id: str) -> dict[str, Any]:
    return dict(session.execute(text("SELECT * FROM audit_run WHERE run_id = :r"), {"r": run_id}).mappings().one())


# --- the command ------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("state", DELETABLE)
def test_a_deletable_run_leaves_the_run_list_and_stays_stored(session, blob_store, helpers, state) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, runs = _adapters(session)
    expert = _account(session, "expert")
    kept_published = _run(session, seeded, "published", age=300)
    target = _run(session, seeded, state, age=200)
    kept_running = _run(session, seeded, "running", age=100)
    finding = _finding(session, seeded, target, verdict="accepted")
    assert _listed(runs, seeded) == [kept_running, target, kept_published]
    before = _row(session, target)

    key = _key("delete")
    view = execution.delete_run(run_id=target, user_uid=expert, idempotency_key=key)

    assert (str(view.run_id), view.state) == (target, state), "the answer is the run, in the state it ended in"
    rows = _tombstones(session, target)
    assert len(rows) == 1 and rows[0].deleted_by_user_uid == expert
    receipt = session.execute(
        text("SELECT command_type, state FROM command_record WHERE command_id = :c"), {"c": rows[0].command_id}
    ).one()
    assert tuple(receipt) == ("delete_audit_run", "succeeded")
    assert _listed(runs, seeded) == [kept_running, kept_published], "the run left the list; the others keep their order"
    assert runs.get_run_status(run_id=target).state == state, "getRunStatus still answers a deleted run by its identity"
    assert _row(session, target) == before, "the run row is byte for byte what it was"
    assert _count(session, "SELECT count(*) FROM finding WHERE finding_uid = :f AND allocated_by_run_id = :r", f=finding, r=target) == 1
    assert _count(session, "SELECT count(*) FROM expert_decision_event WHERE finding_uid = :f", f=finding) == 1, "an expert's decision stays"


@pytest.mark.parametrize("state", REFUSED)
def test_any_other_state_is_refused_and_writes_nothing(session, blob_store, helpers, state) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, runs = _adapters(session)
    expert = _account(session, "expert")
    target = _run(session, seeded, state)
    key = _key("refused")
    with pytest.raises(DomainError) as refused:
        execution.delete_run(run_id=target, user_uid=expert, idempotency_key=key)
    assert refused.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert dict(refused.value.detail_fields) == {"machine": "audit_run", "current_state": state, "requested_state": "delete"}
    assert _tombstones(session, target) == []
    assert _count(session, "SELECT count(*) FROM command_record WHERE command_type = 'delete_audit_run' AND idempotency_key = :k", k=key) == 0
    assert target in _listed(runs, seeded)


def test_an_unknown_run_is_not_found(session, blob_store, helpers) -> None:
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    with pytest.raises(DomainError) as refused:
        execution.delete_run(run_id=str(RunId.new()), user_uid=expert, idempotency_key=_key("unknown"))
    assert refused.value.code is ErrorCode.NOT_FOUND


def test_a_run_already_deleted_is_not_found_and_a_repeat_of_the_same_call_replays(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    target = _run(session, seeded, "failed")
    key = _key("twice")
    first = execution.delete_run(run_id=target, user_uid=expert, idempotency_key=key)

    replay = execution.delete_run(run_id=target, user_uid=expert, idempotency_key=key)
    assert replay == first and len(_tombstones(session, target)) == 1, "the same keyed call answers the first outcome and writes no second row"

    with pytest.raises(DomainError) as again:
        execution.delete_run(run_id=target, user_uid=expert, idempotency_key=_key("again"))
    assert again.value.code is ErrorCode.NOT_FOUND, "a new call on a deleted run: the run is no longer there"
    assert len(_tombstones(session, target)) == 1


def test_one_key_cannot_delete_two_runs(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, runs = _adapters(session)
    expert = _account(session, "expert")
    first, second = _run(session, seeded, "failed"), _run(session, seeded, "cancelled")
    key = _key("shared")
    execution.delete_run(run_id=first, user_uid=expert, idempotency_key=key)
    with pytest.raises(DomainError) as reused:
        execution.delete_run(run_id=second, user_uid=expert, idempotency_key=key)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert _tombstones(session, second) == [] and second in _listed(runs, seeded)


@pytest.mark.parametrize(("roles", "allowed"), [
    (("expert",), True), (("admin",), True), (("expert", "admin"), True),
    (("viewer",), False), ((), False),
])
def test_only_an_expert_or_an_administrator_deletes(session, blob_store, helpers, roles, allowed) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    actor = _account(session, *roles)
    target = _run(session, seeded, "partial")
    if allowed:
        execution.delete_run(run_id=target, user_uid=actor, idempotency_key=_key("role"))
        assert len(_tombstones(session, target)) == 1
        return
    with pytest.raises(DomainError) as denied:
        execution.delete_run(run_id=target, user_uid=actor, idempotency_key=_key("role"))
    assert denied.value.code is ErrorCode.PERMISSION_DENIED and _tombstones(session, target) == []


# --- what the readers answer after a delete ---------------------------------------------------------------------------------


def test_the_dashboard_counts_the_runs_the_lists_show(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    failed, partial = _run(session, seeded, "failed"), _run(session, seeded, "partial")
    _run(session, seeded, "published")

    def activity() -> dict[str, int]:
        summary = DashboardRepository().summary(session, project_uid=seeded.project_uid)
        return {row.state: row.count for row in summary.run_activity}

    assert activity()["failed"] == 1 and activity()["partial"] == 1 and activity()["published"] == 1
    execution.delete_run(run_id=failed, user_uid=expert, idempotency_key=_key("dash"))
    execution.delete_run(run_id=partial, user_uid=expert, idempotency_key=_key("dash"))
    after = activity()
    assert (after["failed"], after["partial"], after["published"]) == (0, 0, 1)


def test_a_deleted_partial_run_gives_way_to_the_published_run_before_it(session, blob_store, helpers) -> None:
    """The document's audit state reads the newest published or partial run as the result; a deleted one is not that run."""
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    published = _run(session, seeded, "published", age=100)
    _finding(session, seeded, published, verdict="accepted")
    partial = _run(session, seeded, "partial", age=10)
    _finding(session, seeded, partial, verdict=None)
    model = DocumentAuditReadModel()

    def counts() -> AuditCountsRecord:
        return tally(model.groups(session, project_uid=seeded.project_uid))

    assert counts() == AuditCountsRecord(document_count=1, not_run=0, clean=0, awaiting_decision=1, checked=0, partial=1), \
        "before: the newer partial run is the result and it is undecided"
    execution.delete_run(run_id=partial, user_uid=expert, idempotency_key=_key("audit"))
    assert counts() == AuditCountsRecord(document_count=1, not_run=0, clean=0, awaiting_decision=0, checked=1, partial=0), \
        "after: the published run before it is the result, and it is decided"


def test_a_document_whose_only_result_was_deleted_is_not_run(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    partial = _run(session, seeded, "partial")
    _finding(session, seeded, partial, verdict="accepted")
    model = DocumentAuditReadModel()
    assert tally(model.groups(session, project_uid=seeded.project_uid)).checked == 1
    execution.delete_run(run_id=partial, user_uid=expert, idempotency_key=_key("only"))
    counts = tally(model.groups(session, project_uid=seeded.project_uid))
    assert (counts.not_run, counts.checked, counts.partial) == (1, 0, 0)


def test_the_job_of_a_deleted_failed_run_leaves_the_queue_and_its_counts_but_the_item_still_answers(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    run_id = str(RunId.new())
    repo, jobs = RunRepository(), JobRepository()
    repo.create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="d" * 64, command_id=None,
    )
    repo.advance(session, run_id=run_id, from_state="created", to_state="queued")
    job_id = jobs.enqueue(session, run_id=run_id)
    authority = jobs.start_execution(session, run_id=run_id)
    jobs.finish_execution(session, authority, publishes_result=False)
    repo.advance(session, run_id=run_id, from_state="queued", to_state="running")
    repo.terminate(session, run_id=run_id, from_state="running", to_state="failed", terminal_reason=ErrorCode.ANALYSIS_FAILED.value)
    queue = ExecutionRepository()

    def listed() -> list[str]:
        return [item.job_id for item in queue.list_queue(session, cursor=None, limit=500, state="failed")]

    failed_jobs = queue.queue_overview(session).get("failed", 0)
    live_failures = queue.live_failure_count(session)
    assert job_id in listed(), "before: the failed job is in the queue"

    execution.delete_run(run_id=run_id, user_uid=expert, idempotency_key=_key("queue"))

    assert job_id not in listed()
    assert queue.queue_overview(session).get("failed", 0) == failed_jobs - 1
    assert queue.live_failure_count(session) == live_failures - 1
    item = queue.get_queue_item(session, job_id)
    assert item is not None and item.run_id == run_id, "the job is read by its identity, as the run is"


def test_the_walk_of_a_versions_runs_never_lands_on_a_deleted_run_and_the_operator_reading_sees_it(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    older, newer = _run(session, seeded, "published", age=50), _run(session, seeded, "partial", age=5)
    repo = RunRepository()
    assert [row.run_id for row in repo.list_for_version(session, seeded.version_uid)] == [newer, older]
    execution.delete_run(run_id=newer, user_uid=expert, idempotency_key=_key("walk"))
    assert [row.run_id for row in repo.list_for_version(session, seeded.version_uid)] == [older]
    assert [row.run_id for row in repo.list_for_version(session, seeded.version_uid, include_deleted=True)] == [newer, older]


# --- the table ---------------------------------------------------------------------------------------------------------------


def test_a_tombstone_is_immutable_and_its_run_cannot_be_removed_from_under_it(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    target = _run(session, seeded, "failed")
    execution.delete_run(run_id=target, user_uid=expert, idempotency_key=_key("immutable"))
    for statement in (
        "UPDATE audit_run_deletion SET deleted_at = now() WHERE run_id = :r",
        "DELETE FROM audit_run_deletion WHERE run_id = :r",
        "DELETE FROM audit_run WHERE run_id = :r",
    ):
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(text(statement), {"r": target})
    assert len(_tombstones(session, target)) == 1


def test_a_run_has_at_most_one_tombstone_and_its_identities_are_well_formed(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    execution, _ = _adapters(session)
    expert = _account(session, "expert")
    target, other = _run(session, seeded, "failed"), _run(session, seeded, "cancelled")
    execution.delete_run(run_id=target, user_uid=expert, idempotency_key=_key("once"))
    row = _tombstones(session, target)[0]
    insert = ("INSERT INTO audit_run_deletion (run_id, deleted_by_user_uid, command_id) VALUES (:r, :u, :c)")
    for params in (
        {"r": target, "u": expert, "c": row.command_id},                  # the primary key: one tombstone per run
        {"r": other, "u": expert, "c": row.command_id},                   # the receipt is one command's
        {"r": other, "u": "usr_not-an-identity", "c": row.command_id},    # the identity format of the actor
        {"r": "run_not-an-identity", "u": expert, "c": row.command_id},   # the identity format of the run
    ):
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(text(insert), params)
    assert _tombstones(session, other) == []
