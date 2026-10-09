"""Independent cross-lane checks for mutable queue pages and provider effect history."""

from __future__ import annotations

from contextlib import nullcontext
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.execution.public import ExecutionRepository
from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.commands import cancel_audit_run
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import RunId


def _queued_run(session, seeded) -> str:
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64,
        command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    return run_id


def test_priority_edit_does_not_hide_an_unseen_queue_job(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    jobs = JobRepository()
    first = jobs.enqueue(session, run_id=_queued_run(session, seeded))
    unseen = jobs.enqueue(session, run_id=_queued_run(session, seeded))
    jobs.set_priority(session, job_id=first, priority=100)
    jobs.set_priority(session, job_id=unseen, priority=90)
    queue = ExecutionAdapter(lambda: nullcontext(session), runs=None)
    cursor = None
    seen = set()
    while True:
        page_one = queue.list_queue(cursor=cursor, limit=1)
        assert len(page_one.items) == 1, "the A anchor was not reachable"
        current = page_one.items[0].job_id
        assert current not in seen, "queue continuation repeated a Job before A"
        if current == first:
            break
        seen.add(current)
        cursor = page_one.page.next_cursor
        assert cursor is not None, "the A anchor was not reachable"
    assert [item.job_id for item in page_one.items] == [first]
    cursor = page_one.page.next_cursor
    assert isinstance(cursor, str)
    baseline_page_two = queue.list_queue(cursor=cursor, limit=1000)
    assert unseen in [item.job_id for item in baseline_page_two.items]

    # Another administrator edits the already-seen anchor before the user opens page 2.
    jobs.set_priority(session, job_id=first, priority=50)
    page_two = queue.list_queue(cursor=cursor, limit=1000)
    assert unseen in [item.job_id for item in page_two.items]
    assert first not in [item.job_id for item in page_two.items]


def test_pause_between_hint_and_claim_refuses_new_authority(engine, blob_store, helpers) -> None:
    jobs = JobRepository()
    with Session(engine) as seed:
        jobs.set_paused(seed, paused=False)
        seeded = helpers.seed_version(seed, blob_store)
        competing_run_id = _queued_run(seed, seeded)
        competing_job_id = jobs.enqueue(seed, run_id=competing_run_id)
        jobs.set_priority(seed, job_id=competing_job_id, priority=100)
        run_id = _queued_run(seed, seeded)
        job_id = jobs.enqueue(seed, run_id=run_id)
        jobs.set_priority(seed, job_id=job_id, priority=99)
        seed.commit()

    try:
        with Session(engine) as dispatcher:
            assert jobs.next_queued_run(dispatcher) != run_id

        # The hint has no run_id argument. Lock every other runnable Run on a
        # separate connection so SKIP LOCKED reaches this Job even when earlier
        # tests left queued Jobs behind. This remains a real dispatcher hint.
        with Session(engine) as competing_claims:
            locked = competing_claims.execute(text(
                "SELECT r.run_id FROM audit_run r JOIN job j ON j.run_id = r.run_id "
                "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
                "AND j.available_at <= statement_timestamp() AND r.run_id <> :run_id "
                "FOR UPDATE OF r"
            ), {"run_id": run_id}).scalars().all()
            assert competing_run_id in locked
            with Session(engine) as dispatcher:
                assert jobs.next_queued_run(dispatcher) == run_id
                dispatcher.commit()

        with Session(engine) as administrator:
            jobs.set_paused(administrator, paused=True)
            administrator.commit()

        with Session(engine) as claimant:
            assert ExecutionRepository().dispatch_status(claimant).paused is True
            try:
                authority = jobs.start_execution(claimant, run_id=run_id)
            except DomainError:
                authority = None
            row = claimant.execute(text(
                "SELECT j.state, (SELECT count(*) FROM attempt a WHERE a.job_id = j.job_id) "
                "FROM job j WHERE j.job_id = :job_id"
            ), {"job_id": job_id}).one()
            assert authority is None and tuple(row) == ("queued", 0), (
                "paused dispatch acquired authority after an earlier hint", authority, row,
            )
    finally:
        with Session(engine) as administrator:
            jobs.set_paused(administrator, paused=False)
            administrator.commit()
        with Session(engine) as cleanup:
            for owned_run_id in (run_id, competing_run_id):
                cancel_audit_run(
                    cleanup, run_id=owned_run_id, roles=frozenset({"expert"}),
                    idempotency_key="w53-qa-cleanup-" + uuid4().hex,
                )
            cleanup.commit()


def test_lease_reclaim_journals_the_effect_outcome(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    jobs = JobRepository()
    jobs.enqueue(session, run_id=run_id)
    authority = jobs.start_execution(session, run_id=run_id)
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
    effect = jobs.prepare_provider_call(
        session, authority, provider="synthetic", model_identity="synthetic",
        provider_mode="recorded", parameters={}, request_sha256="a" * 64,
    )
    session.execute(text(
        "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
        "WHERE lease_id = :lease_id"
    ), {"lease_id": authority.lease_id})
    assert jobs.reclaim_expired(session) >= 1
    assert session.execute(text(
        "SELECT state FROM provider_call_effect WHERE model_call_id = :effect"
    ), {"effect": str(effect)}).scalar_one() == "outcome_unknown"
    events = ExecutionRepository().list_journal(session, run_id=run_id, cursor=None, limit=100)
    assert any(
        item.aggregate_id == authority.attempt_id
        and item.payload.get("dispatch_class") == "outcome_unknown"
        for item in events
    )


def test_terminal_effect_settlement_journals_abandonment(session, blob_store, helpers) -> None:
    seeded = helpers.seed_version(session, blob_store)
    run_id = _queued_run(session, seeded)
    jobs = JobRepository()
    jobs.enqueue(session, run_id=run_id)
    authority = jobs.start_execution(session, run_id=run_id)
    RunRepository().advance(session, run_id=run_id, from_state="queued", to_state="running")
    effect = jobs.prepare_provider_call(
        session, authority, provider="synthetic", model_identity="synthetic",
        provider_mode="recorded", parameters={}, request_sha256="b" * 64,
    )
    cancel_audit_run(
        session, run_id=run_id, roles=frozenset({"expert"}),
        idempotency_key="w53-qa-" + uuid4().hex,
    )
    settled = jobs.settle_terminal_provider_effects(
        session, older_than="0 seconds", batch_size=1000,
    )
    assert any(item.model_call_id == str(effect) and item.state == "abandoned" for item in settled)
    events = ExecutionRepository().list_journal(session, run_id=run_id, cursor=None, limit=100)
    assert any(
        item.aggregate_id == authority.attempt_id
        and item.payload.get("state") == "abandoned"
        for item in events
    )
