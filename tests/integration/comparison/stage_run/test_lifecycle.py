"""Seven durable receipts, child text work, cancellation and batch controls."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.stage_run.batch import StageBatchHandler, StageBatchService
from auditmanager.comparison.stage_run.handler import StageChainHandler
from auditmanager.comparison.stage_run.service import BATCH_WORK_KIND, WORK_KIND, StageChainService
from auditmanager.comparison.stage_text.handler import StageTextRecomputeHandler
from auditmanager.comparison.stage_text.recompute import WORK_KIND as TEXT_KIND
from auditmanager.comparison.work.model import Completed, WorkDependencies, Yielded
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.stage_text.test_recompute import _profiles
from tests.integration.comparison.stage_text.test_store import _seed
from tests.support.accounts import complete_expert_account


class _Action:
    def advance(self, item, *, run_id):
        return {"cards": 0}


def _scene(database: Session):
    store, pair, revision, _actor, left, right = _seed(database)
    actor = str(complete_expert_account(database, f"stage-chain-{new_ulid().lower()}").user_uid)
    service = StageChainService(store._sessions, comparison_modules="versions,stages")
    work = ComparisonWorkRepository()
    with session_scope(store._sessions) as session:
        worker = WorkerRegistry().register(session, version="stage-chain-test", slots=1)
    return store, service, work, worker, pair, revision, actor, left, right


def _claim(sessions, work, worker, kind):
    with session_scope(sessions) as session:
        item = work.claim(session, worker_id=worker, modules={"stages"}, kinds={kind})
    assert item is not None
    return item


def test_full_chain_yields_for_text_and_completes_seven_receipts(comparison_session: Session) -> None:
    store, service, work, worker, pair, revision, actor, left, right = _scene(comparison_session)
    request = dict(pair_id=pair, revision_id=revision, user_uid=actor,
                   actor_roles=frozenset({"expert"}), with_ai=False,
                   idempotency_key=f"stage-chain-{new_ulid()}")
    started = service.start(**request)
    assert len(started.steps) == 7 and started.state == "queued"
    assert service.start(**request).run_id == started.run_id
    full = _claim(store._sessions, work, worker, WORK_KIND)
    deps = WorkDependencies(None, store._sessions, None, work)  # type: ignore[arg-type]
    handler = StageChainHandler(deps, repair=_Action(), review=_Action())
    assert isinstance(handler.run(full), Yielded)  # links
    assert isinstance(handler.run(full), Yielded)  # enqueue text child
    child = _claim(store._sessions, work, worker, TEXT_KIND)
    text_handler = StageTextRecomputeHandler(deps, profile_reader=_profiles(
        comparison_session, left, right, empty=False,
    ))
    assert isinstance(text_handler.run(child), Completed)
    with session_scope(store._sessions) as session:
        work.finish(session, child.authority, Completed())
    for _ in range(8):
        outcome = handler.run(full)
        if isinstance(outcome, Completed):
            break
    else:
        pytest.fail("chain did not finish its seven steps")
    finished = service.get(started.run_id)
    assert finished.state == "completed"
    assert all(step.state == "completed" for step in finished.steps)
    assert finished.steps[3].counts == {"skipped": 1}
    page, _next = service.page(pair_id=pair, after=None, limit=10)
    assert {run.kind for run in page} == {"full", "deterministic"}


def test_cancel_and_resume_keep_completed_receipts(comparison_session: Session) -> None:
    store, service, work, worker, pair, revision, actor, _left, _right = _scene(comparison_session)
    started = service.start(pair_id=pair, revision_id=revision, user_uid=actor,
                            actor_roles=frozenset({"expert"}), with_ai=False,
                            idempotency_key=f"stage-chain-{new_ulid()}")
    item = _claim(store._sessions, work, worker, WORK_KIND)
    handler = StageChainHandler(WorkDependencies(None, store._sessions, None, work))  # type: ignore[arg-type]
    assert isinstance(handler.run(item), Yielded)
    cancelled = service.cancel(run_id=started.run_id, user_uid=actor,
                               actor_roles=frozenset({"expert"}),
                               idempotency_key=f"stage-cancel-{new_ulid()}")
    assert cancelled.state == "cancelled" and cancelled.steps[0].state == "completed"
    with session_scope(store._sessions) as session:
        assert work.finish(session, item.authority, Yielded()) == "cancelled"
    resumed = service.resume(run_id=started.run_id, user_uid=actor,
                             actor_roles=frozenset({"expert"}),
                             idempotency_key=f"stage-resume-{new_ulid()}")
    assert resumed.state == "queued" and resumed.steps[0].state == "completed"
    assert all(step.state == "queued" for step in resumed.steps[1:])


def test_batch_pause_resume_and_cancel_are_durable(comparison_session: Session) -> None:
    store, service, work, worker, pair, revision, actor, _left, _right = _scene(comparison_session)
    batches = StageBatchService(service)
    batch = batches.start(project_uid=str(comparison_session.execute(text(
        "SELECT project_uid FROM stage_pair WHERE stage_pair_id = :pair"
    ), {"pair": pair}).scalar_one()), selections=[{"pair_id": pair, "link_revision_id": revision}],
        user_uid=actor, actor_roles=frozenset({"expert"}), with_ai=False,
        idempotency_key=f"stage-batch-{new_ulid()}")
    batch_id = batch["batch_id"]
    command = dict(batch_id=batch_id, user_uid=actor, actor_roles=frozenset({"expert"}))
    paused = batches.control(**command, action="pause", idempotency_key=f"pause-{new_ulid()}")
    assert paused["state"] == "paused"
    item = _claim(store._sessions, work, worker, BATCH_WORK_KIND)
    handler = StageBatchHandler(WorkDependencies(None, store._sessions, None, work))  # type: ignore[arg-type]
    assert isinstance(handler.run(item), Yielded)
    assert batches.get(batch_id)["items"][0].get("run_id") is None
    batches.control(**command, action="resume", idempotency_key=f"resume-{new_ulid()}")
    assert isinstance(handler.run(item), Yielded)
    assert batches.get(batch_id)["items"][0]["state"] == "running"
    cancelled = batches.control(**command, action="cancel", idempotency_key=f"cancel-{new_ulid()}")
    assert cancelled["state"] == "cancelled" and cancelled["counts"]["cancelled"] == 1


def test_ai_start_requires_explicit_consent(comparison_session: Session) -> None:
    _store, service, _work, _worker, pair, revision, actor, _left, _right = _scene(comparison_session)
    with pytest.raises(DomainError) as error:
        service.start(pair_id=pair, revision_id=revision, user_uid=actor,
                      actor_roles=frozenset({"expert"}), with_ai=True,
                      idempotency_key=f"stage-chain-{new_ulid()}")
    assert error.value.code is ErrorCode.CONFLICT


def test_graphic_failure_finishes_run_in_failed_state(comparison_session: Session) -> None:
    from auditmanager.comparison.work.model import Failed

    class RefusedGraphics:
        def advance(self, item, *, run_id):
            return Failed('stage_graphic_evidence_unavailable')

    store, service, work, worker, pair, revision, actor, left, right = _scene(comparison_session)
    run = service.start(pair_id=pair, revision_id=revision, user_uid=actor,
        actor_roles=frozenset({'expert'}), with_ai=False, idempotency_key='graphic-failure-'+new_ulid())
    item = _claim(store._sessions, work, worker, WORK_KIND)
    deps = WorkDependencies(None, store._sessions, None, work)
    handler = StageChainHandler(deps, graphics=RefusedGraphics())
    handler.run(item)
    handler.run(item)
    child = _claim(store._sessions, work, worker, TEXT_KIND)
    assert isinstance(StageTextRecomputeHandler(deps, profile_reader=_profiles(
        comparison_session, left, right, empty=False)).run(child), Completed)
    with session_scope(store._sessions) as session:
        work.finish(session, child.authority, Completed())
    outcome = handler.run(item)
    assert isinstance(outcome, Failed)
    final = service.get(run.run_id)
    assert final.state == 'failed' and final.steps[2].state == 'failed'
