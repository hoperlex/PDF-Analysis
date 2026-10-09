"""W53 execution projections and command invariants on frozen 0017."""

from __future__ import annotations

import json
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.execution.public import ExecutionRepository
from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.api.schemas.common import encode_cursor
from auditmanager.analysis.text import ProviderMode
from auditmanager.jobs.public import JobRepository, set_execution_paused
from auditmanager.runs.commands import cancel_audit_run, reaudit_run
from auditmanager.runs import execute_run
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, ModelCallId, NormsSnapshotId, RunId


def _run(session, seeded, *, snapshot=None, terminal=False):
    run_id = str(RunId.new())
    repo = RunRepository()
    repo.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64,
        command_id=None, norms_snapshot_id=snapshot,
    )
    repo.advance(session, run_id=run_id, from_state="created", to_state="queued")
    if terminal:
        repo.advance(session, run_id=run_id, from_state="queued", to_state="running")
        repo.terminate(
            session, run_id=run_id, from_state="running", to_state="failed",
            terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        )
    return run_id


def _key() -> str:
    return "w53-exec-" + uuid4().hex


def test_reaudit_copies_nonnull_frozen_snapshot_and_replays_once(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    snapshot = str(NormsSnapshotId.new())
    content_key = _key()
    session.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, segmentation_profile) "
        "VALUES (:snapshot, :content_key, :content_key, :digest, 1, 1, 'w53-test')"
    ), {"snapshot": snapshot, "content_key": content_key, "digest": "b" * 64})
    source_id = _run(session, seeded, snapshot=snapshot, terminal=True)
    key = _key()
    first = reaudit_run(
        session, source_run_id=source_id, roles=frozenset({"expert"}),
        idempotency_key=key,
    )
    replay = reaudit_run(
        session, source_run_id=source_id, roles=frozenset({"expert"}),
        idempotency_key=key,
    )
    assert replay.replayed is True and replay.run_id == first.run_id
    child = RunRepository().get(session, first.run_id)
    assert child.norms_snapshot_id == snapshot
    assert child.frozen_input_digest == "a" * 64
    assert child.state == "queued"
    assert session.execute(text(
        "SELECT reaudit_of_run_id FROM audit_run WHERE run_id = :run_id"
    ), {"run_id": first.run_id}).scalar_one() == source_id
    with pytest.raises(DomainError) as busy:
        reaudit_run(
            session, source_run_id=source_id, roles=frozenset({"expert"}),
            idempotency_key=_key(),
        )
    assert busy.value.code is ErrorCode.CONFLICT


def test_pause_actor_event_is_atomic_and_idempotent(session):
    actor = "usr_" + str(RunId.new()).split("_", 1)[1]
    key = _key()
    set_execution_paused(
        session, paused=True, roles=frozenset({"admin"}),
        actor_uid=actor, idempotency_key=key,
    )
    set_execution_paused(
        session, paused=True, roles=frozenset({"admin"}),
        actor_uid=actor, idempotency_key=key,
    )
    events = session.execute(text(
        "SELECT aggregate_type, aggregate_id, payload FROM audit_event "
        "WHERE event_type = 'execution.dispatch_paused_changed' "
        "AND payload->>'actor_uid' = :actor"
    ), {"actor": actor}).mappings().all()
    assert len(events) == 1
    assert events[0]["aggregate_type"] == "CommandRecord"
    assert events[0]["aggregate_id"].startswith("cmd_")
    assert events[0]["payload"] == {"paused": True, "actor_uid": actor}
    savepoint = session.begin_nested()
    set_execution_paused(
        session, paused=False, roles=frozenset({"admin"}),
        actor_uid=actor, idempotency_key=_key(),
    )
    savepoint.rollback()
    assert ExecutionRepository().dispatch_status(session).paused is True
    assert session.execute(text(
        "SELECT count(*) FROM audit_event WHERE event_type = "
        "'execution.dispatch_paused_changed' AND payload->>'actor_uid' = :actor"
    ), {"actor": actor}).scalar_one() == 1


def test_journal_cursor_handles_equal_timestamps_and_newer_insert(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    instant = datetime(2099, 1, 1, tzinfo=timezone.utc)
    def append(at):
        event_id = str(AuditEventId.new())
        session.execute(text(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, "
            "aggregate_id, payload, occurred_at) VALUES (:event_id, 'test.cursor', "
            "'AuditRun', :run_id, CAST(:payload AS jsonb), :occurred_at)"
        ), {"event_id": event_id, "run_id": run_id,
            "payload": json.dumps({"run_id": run_id}), "occurred_at": at})
        return event_id
    first, second, third = (append(instant) for _ in range(3))
    repo = ExecutionRepository()
    page1 = repo.list_journal(session, run_id=run_id, cursor=None, limit=2)
    assert [item.event_id for item in page1] == [third, second]
    newest = append(instant + timedelta(seconds=1))
    page2 = repo.list_journal(session, run_id=run_id, cursor=second, limit=2)
    assert page2[0].event_id == first
    assert newest not in {item.event_id for item in page2}
    assert all(item.run_id == run_id for item in (*page1, *page2))


def test_generic_audit_event_without_run_payload_is_projected_from_identity(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    event_id = str(AuditEventId.new())
    session.execute(text(
        "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, "
        "aggregate_id, payload, occurred_at) VALUES (:id, 'test.generic', "
        "'AuditRun', :run_id, '{}'::jsonb, timestamptz '2099-02-01')"
    ), {"id": event_id, "run_id": run_id})
    repository = ExecutionRepository()
    for filtered in (None, run_id):
        page = repository.list_journal(session, run_id=filtered, cursor=None, limit=1)
        assert page[0].event_id == event_id
        assert page[0].run_id == run_id
        assert page[0].payload == {}


def _queue_page_at_job(queue, job_id):
    """Read actual one-item pages until this test's anchor is emitted."""
    cursor = None
    seen = set()
    while True:
        page = queue.list_queue(cursor=cursor, limit=1)
        assert len(page.items) == 1, f"own anchor {job_id} was not reachable"
        current = page.items[0].job_id
        assert current not in seen, "queue continuation repeated an earlier Job"
        if current == job_id:
            assert page.page.next_cursor is not None
            return page
        seen.add(current)
        cursor = page.page.next_cursor
        assert cursor is not None, f"own anchor {job_id} was not reachable"


def test_queue_cursor_follows_priority_order_after_new_insert(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    jobs = JobRepository()
    first = jobs.enqueue(session, run_id=_run(session, seeded))
    second = jobs.enqueue(session, run_id=_run(session, seeded))
    jobs.set_priority(session, job_id=first, priority=100)
    jobs.set_priority(session, job_id=second, priority=98)
    queue = ExecutionAdapter(lambda: nullcontext(session), runs=None)
    page1 = _queue_page_at_job(queue, first)
    later = jobs.enqueue(session, run_id=_run(session, seeded))
    jobs.set_priority(session, job_id=later, priority=99)
    page2 = queue.list_queue(cursor=page1.page.next_cursor, limit=1000)
    identities = [item.job_id for item in page2.items]
    assert first not in identities
    assert identities.index(later) < identities.index(second)


def test_queue_emitted_cursor_survives_anchor_state_edit_and_refuses_bad_fields(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    jobs = JobRepository()
    first = jobs.enqueue(session, run_id=_run(session, seeded))
    unseen = jobs.enqueue(session, run_id=_run(session, seeded))
    jobs.set_priority(session, job_id=first, priority=100)
    jobs.set_priority(session, job_id=unseen, priority=90)
    queue = ExecutionAdapter(lambda: nullcontext(session), runs=None)
    first_page = _queue_page_at_job(queue, first)
    assert [item.job_id for item in first_page.items] == [first]
    cursor = first_page.page.next_cursor
    assert cursor is not None
    assert unseen in [item.job_id for item in queue.list_queue(cursor=cursor, limit=1000).items]

    # Only the anchor row moves; the emitted token keeps the old boundary.
    session.execute(text("UPDATE job SET state = 'leased' WHERE job_id = :job_id"),
                    {"job_id": first})
    second_page = queue.list_queue(cursor=cursor, limit=1000)
    assert unseen in [item.job_id for item in second_page.items]
    assert first not in [item.job_id for item in second_page.items]

    for parts in (
        ("q1", "5", "100", first_page.items[0].created_at.isoformat(), first),
        ("q1", "0", "101", first_page.items[0].created_at.isoformat(), first),
        ("q1", "0", "100", "not-a-time", first),
        ("q1", "0", "100", first_page.items[0].created_at.isoformat(), "not-a-job"),
        (first,),
    ):
        with pytest.raises(DomainError) as error:
            queue.list_queue(cursor=encode_cursor(parts), limit=20)
        assert error.value.code is ErrorCode.VALIDATION_FAILED


def test_queued_tie_order_matches_dispatcher(session, blob_store, helpers):
    seeded = helpers.seed_version(session, blob_store)
    jobs = JobRepository()
    run_ids = [_run(session, seeded) for _ in range(3)]
    job_ids = [jobs.enqueue(session, run_id=run_id) for run_id in run_ids]
    for job_id in job_ids:
        jobs.set_priority(session, job_id=job_id, priority=70)
    eligible = session.execute(text(
        "SELECT j.job_id, j.run_id FROM job j JOIN audit_run r ON r.run_id = j.run_id "
        "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
        "AND j.available_at <= statement_timestamp() "
        "AND NOT EXISTS (SELECT 1 FROM execution_control WHERE singleton AND paused) "
        "ORDER BY j.priority DESC, j.created_at, j.job_id"
    )).mappings().all()
    assert eligible
    expected = [row["job_id"] for row in eligible]
    own_expected = [job_id for job_id in expected if job_id in job_ids]
    assert set(own_expected) == set(job_ids)
    assert jobs.next_queued_run(session) == eligible[0]["run_id"]
    queue = ExecutionAdapter(lambda: nullcontext(session), runs=None)
    observed = []
    cursor = None
    while True:
        page = queue.list_queue(cursor=cursor, limit=1)
        assert len(page.items) == 1
        assert page.items[0].job_id not in observed
        observed.extend(item.job_id for item in page.items)
        cursor = page.page.next_cursor
        if cursor is None:
            break
    assert [job_id for job_id in observed if job_id in expected] == expected
    assert [job_id for job_id in observed if job_id in job_ids] == own_expected


def _claim(session, run_id):
    repository = RunRepository()
    if repository.get(session, run_id).state == "queued":
        repository.advance(session, run_id=run_id, from_state="queued", to_state="running")
    return JobRepository().start_execution(session, run_id=run_id)


def _expire(session, authority):
    session.execute(text(
        "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
        "WHERE lease_id = :lease_id"
    ), {"lease_id": authority.lease_id})
    assert JobRepository().heartbeat(session, authority) is False
    assert JobRepository().reclaim_expired(session) >= 1


def test_only_not_processed_attempt_resumes_and_third_loss_dead_letters(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    jobs = JobRepository()
    jobs.enqueue(session, run_id=run_id)
    first = _claim(session, run_id)
    effect = jobs.prepare_provider_call(
        session, first, provider="anthropic", model_identity="claude-opus-5",
        provider_mode="recorded", parameters={}, request_sha256="c" * 64,
    )
    jobs.record_provider_not_processed(
        session, first, model_call_id=effect,
        error_code=ErrorCode.DEPENDENCY_UNAVAILABLE.value,
        dispatch_class="not_sent",
    )
    _expire(session, first)
    second = _claim(session, run_id)
    assert second.attempt_id != first.attempt_id
    _expire(session, second)
    third = _claim(session, run_id)
    _expire(session, third)
    row = session.execute(text(
        "SELECT r.state, j.state FROM audit_run r JOIN job j ON j.run_id = r.run_id "
        "WHERE r.run_id = :run_id"
    ), {"run_id": run_id}).one()
    assert tuple(row) == ("failed", "dead_letter")
    assert session.execute(text(
        "SELECT state FROM provider_call_effect WHERE model_call_id = :effect"
    ), {"effect": str(effect)}).scalar_one() == "not_processed"


def test_prepared_provider_effect_fails_closed_on_lease_loss(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    jobs = JobRepository()
    jobs.enqueue(session, run_id=run_id)
    first = _claim(session, run_id)
    effect = jobs.prepare_provider_call(
        session, first, provider="anthropic", model_identity="claude-opus-5",
        provider_mode="live", parameters={}, request_sha256="d" * 64,
    )
    second_effect = jobs.prepare_provider_call(
        session, first, provider="anthropic", model_identity="claude-opus-5",
        provider_mode="live", parameters={}, request_sha256="e" * 64,
    )
    _expire(session, first)
    row = session.execute(text(
        "SELECT r.state, j.state FROM audit_run r JOIN job j ON j.run_id = r.run_id "
        "WHERE r.run_id = :run_id"
    ), {"run_id": run_id}).one()
    assert tuple(row) == ("failed", "failed")
    states = dict(session.execute(text(
        "SELECT model_call_id, state FROM provider_call_effect WHERE run_id = :run_id"
    ), {"run_id": run_id}).all())
    assert states == {str(effect): "outcome_unknown", str(second_effect): "outcome_unknown"}
    events = text(
        "SELECT count(*) FROM audit_event WHERE event_type = 'provider.outcome_unknown' "
        "AND aggregate_id = :attempt_id AND payload->>'run_id' = :run_id"
    )
    assert session.execute(events, {
        "attempt_id": first.attempt_id, "run_id": run_id,
    }).scalar_one() == 2
    assert jobs.reclaim_expired(session) == 0
    assert session.execute(events, {
        "attempt_id": first.attempt_id, "run_id": run_id,
    }).scalar_one() == 2
    with pytest.raises(DomainError):
        _claim(session, run_id)


def test_validating_cancel_refuses_without_changing_run_job_or_attempt(
    session, blob_store, helpers
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    JobRepository().enqueue(session, run_id=run_id)
    authority = _claim(session, run_id)
    RunRepository().advance(session, run_id=run_id,
                            from_state="running", to_state="validating")
    savepoint = session.begin_nested()
    with pytest.raises(DomainError) as refusal:
        cancel_audit_run(
            session, run_id=run_id, roles=frozenset({"expert"}),
            idempotency_key=_key(),
        )
    savepoint.rollback()
    assert refusal.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    states = session.execute(text(
        "SELECT r.state, j.state, a.state FROM audit_run r JOIN job j "
        "ON j.run_id = r.run_id JOIN attempt a ON a.attempt_id = j.current_attempt_id "
        "WHERE r.run_id = :run_id"
    ), {"run_id": run_id}).one()
    assert tuple(states) == ("validating", "running", "running")


class _PricedRecordedAdapter:
    provider_mode = ProviderMode.RECORDED

    def __init__(self, inner):
        self.inner = inner
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        return replace(self.inner.complete(request), reported_cost_usd=0.5)


def test_running_run_without_job_refuses_before_new_authority_or_provider(
    session, blob_store, helpers, recorded_adapter, provider_config
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    RunRepository().advance(
        session, run_id=run_id, from_state="queued", to_state="running"
    )
    _prior_call(session, run_id, cost_micros=500_000, basis="measured")
    adapter = _PricedRecordedAdapter(recorded_adapter)
    with pytest.raises(DomainError) as refusal:
        execute_run(
            session, run_id, blob_store=blob_store, adapter=adapter,
            provider_config=provider_config,
        )
    assert refusal.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert refusal.value.detail_fields == {
        "machine": "audit_run", "current_state": "running", "requested_state": "queued"
    }
    assert adapter.calls == 0
    assert RunRepository().get(session, run_id).state == "running"
    assert session.execute(text(
        "SELECT count(*) FROM job WHERE run_id = :run_id"
    ), {"run_id": run_id}).scalar_one() == 0
    assert session.execute(text(
        "SELECT count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id "
        "WHERE j.run_id = :run_id"
    ), {"run_id": run_id}).scalar_one() == 0
    assert session.execute(text(
        "SELECT count(*) FROM lease l JOIN attempt a ON a.attempt_id = l.attempt_id "
        "JOIN job j ON j.job_id = a.job_id WHERE j.run_id = :run_id"
    ), {"run_id": run_id}).scalar_one() == 0
    assert session.execute(text(
        "SELECT count(*) FROM audit_event WHERE aggregate_type = 'AuditRun' "
        "AND aggregate_id = :run_id AND event_type LIKE 'stage.%'"
    ), {"run_id": run_id}).scalar_one() == 0
    assert session.execute(text(
        "SELECT count(*) FROM model_call WHERE run_id = :run_id"
    ), {"run_id": run_id}).scalar_one() == 1


def _prior_call(session, run_id, *, cost_micros, basis):
    call_id = str(ModelCallId.new())
    session.execute(text(
        "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
        "model_identity, provider_mode, request_sha256, response_sha256, "
        "cost_micros, cost_basis, status) VALUES (:id, :run_id, 'text_analysis', "
        "'anthropic', 'claude-opus-5', 'recorded', :hash, :hash, :cost, :basis, 'succeeded')"
    ), {"id": call_id, "run_id": run_id, "hash": "e" * 64,
        "cost": cost_micros, "basis": basis})


def test_persisted_zero_cost_unmeasured_call_keeps_resumed_basis_estimated(
    session, blob_store, helpers, recorded_adapter, provider_config
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    _prior_call(session, run_id, cost_micros=0, basis="estimated")
    adapter = _PricedRecordedAdapter(recorded_adapter)
    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=adapter,
        provider_config=provider_config,
    )
    assert result.terminal_state == "published" and adapter.calls == 1
    stage = next(row for row in RunRepository().stage_results(session, run_id)
                 if row.stage_id == "text_analysis")
    assert stage.metrics["cost_basis"] == "estimated"
    assert RunRepository().cost(session, run_id).basis == "estimated"


def test_persisted_prior_spend_exhausts_run_ceiling_before_another_call(
    session, blob_store, helpers, recorded_adapter, provider_config
):
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded)
    _prior_call(session, run_id, cost_micros=1_000_000, basis="measured")
    adapter = _PricedRecordedAdapter(recorded_adapter)
    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=adapter,
        provider_config=provider_config,
    )
    assert result.terminal_state == "failed" and adapter.calls == 0
    stage = next(row for row in RunRepository().stage_results(session, run_id)
                 if row.stage_id == "text_analysis")
    assert stage.error["code"] == ErrorCode.COST_BUDGET_EXCEEDED.value
