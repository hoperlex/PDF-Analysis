"""`W54-WORKER-01` -- `listWorkers` and `setWorkerIntake` over the shipped adapter and command.

HEAVY: real PostgreSQL, one rolled-back transaction per test. `W54-SEAL-01` sealed both
operations as ``503 dependency_unavailable`` stubs; these are their bodies (R-105, R-80).

Registry rows are written with explicit timestamps so that each derived state -- online
under 90 s since the last heartbeat, stale under 600 s, offline beyond -- is a literal
here rather than a race with the clock.
"""

from __future__ import annotations

from contextlib import nullcontext
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.jobs.public import JobRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId, WorkerId
from auditmanager.workers.public import WorkerRegistry, set_worker_intake

ACTOR = "usr_01M2545JSD15ETSNNV904X991K"


def _insert_worker(session, *, heartbeat_age_seconds: int, started_age_seconds: int) -> str:
    worker_id = str(WorkerId.new())
    session.execute(text(
        "INSERT INTO worker (worker_id, version, started_at, heartbeat_at, slots) VALUES "
        "(:worker_id, 'registry-suite', "
        "statement_timestamp() - make_interval(secs => :started), "
        "statement_timestamp() - make_interval(secs => :heartbeat), 1)"
    ), {"worker_id": worker_id, "started": float(started_age_seconds),
        "heartbeat": float(heartbeat_age_seconds)})
    return worker_id


def _adapter(session) -> ExecutionAdapter:
    return ExecutionAdapter(lambda: nullcontext(session), runs=None)  # type: ignore[arg-type]


def _all_items(adapter: ExecutionAdapter):
    items, cursor = [], None
    while True:
        page = adapter.list_workers(cursor=cursor, limit=50)
        items.extend(page.items)
        cursor = page.page.next_cursor
        if cursor is None:
            return items


def test_each_worker_reports_its_derived_state(session) -> None:
    online = _insert_worker(session, heartbeat_age_seconds=5, started_age_seconds=10_000)
    stale = _insert_worker(session, heartbeat_age_seconds=120, started_age_seconds=10_001)
    offline = _insert_worker(session, heartbeat_age_seconds=700, started_age_seconds=10_002)
    states = {
        item.worker_id: item.state.value for item in _all_items(_adapter(session))
        if item.worker_id in {online, stale, offline}
    }
    assert states == {online: "online", stale: "stale", offline: "offline"}


def test_pages_follow_the_immutable_start_newest_first(session) -> None:
    # Both start "now", so they are newer than any committed residue and the first page
    # starts with them; the registered one is the later of the two.
    older = _insert_worker(session, heartbeat_age_seconds=0, started_age_seconds=0)
    newest = WorkerRegistry().register(session, version="registry-suite", slots=1)
    adapter = _adapter(session)
    first = adapter.list_workers(cursor=None, limit=1)
    assert [item.worker_id for item in first.items] == [newest]
    assert first.page.next_cursor is not None
    second = adapter.list_workers(cursor=first.page.next_cursor, limit=1)
    assert [item.worker_id for item in second.items] == [older]


def test_a_foreign_cursor_is_refused(session) -> None:
    with pytest.raises(DomainError) as refused:
        _adapter(session).list_workers(cursor="bm90LWEtY3Vyc29y", limit=10)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED


def test_current_runs_are_the_runs_its_unreleased_leases_hold(
    session, blob_store, helpers,
) -> None:
    seeded = helpers.seed_version(session, blob_store)
    worker_id = WorkerRegistry().register(session, version="registry-suite", slots=1)
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
        frozen_input_digest="a" * 64, command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    JobRepository().enqueue(session, run_id=run_id)
    runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    JobRepository(worker_id=worker_id).start_execution(session, run_id=run_id)

    item = next(i for i in _all_items(_adapter(session)) if i.worker_id == worker_id)
    assert item.current_run_ids == [run_id]
    assert item.state.value == "online" and item.intake_enabled is True and item.slots == 1


# --- setWorkerIntake ---------------------------------------------------------------------------


def test_intake_is_an_administrators_switch(session) -> None:
    worker_id = WorkerRegistry().register(session, version="registry-suite", slots=1)
    with pytest.raises(DomainError) as refused:
        set_worker_intake(
            session, worker_id=worker_id, enabled=False, roles=frozenset({"expert"}),
            idempotency_key=f"w54-intake-{uuid4().hex}", actor_uid=ACTOR,
        )
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    assert WorkerRegistry().intake_enabled(session, worker_id) is True


def test_an_unknown_worker_is_not_found(session) -> None:
    with pytest.raises(DomainError) as refused:
        set_worker_intake(
            session, worker_id=str(WorkerId.new()), enabled=False,
            roles=frozenset({"admin"}), idempotency_key=f"w54-intake-{uuid4().hex}",
            actor_uid=ACTOR,
        )
    assert refused.value.code is ErrorCode.NOT_FOUND


def test_the_switch_is_journalled_once_and_a_replay_changes_nothing(session) -> None:
    worker_id = WorkerRegistry().register(session, version="registry-suite", slots=1)
    key = f"w54-intake-{uuid4().hex}"
    for _ in range(2):
        record = set_worker_intake(
            session, worker_id=worker_id, enabled=False, roles=frozenset({"admin"}),
            idempotency_key=key, actor_uid=ACTOR,
        )
        assert record.intake_enabled is False
    events = session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'execution.worker_intake_changed' "
        "AND aggregate_type = 'Worker' AND aggregate_id = :worker_id"
    ), {"worker_id": worker_id}).scalars().all()
    assert events == [{"worker_id": worker_id, "intake_enabled": False, "actor_uid": ACTOR}]

    set_worker_intake(
        session, worker_id=worker_id, enabled=True, roles=frozenset({"admin"}),
        idempotency_key=f"w54-intake-{uuid4().hex}", actor_uid=ACTOR,
    )
    assert WorkerRegistry().intake_enabled(session, worker_id) is True
