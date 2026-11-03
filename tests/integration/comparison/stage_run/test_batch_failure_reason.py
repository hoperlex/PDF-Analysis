"""A batch item that cannot start leaves its reason in the audit trail."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.stage_run.batch import StageBatchHandler, StageBatchService
from auditmanager.comparison.stage_run.service import BATCH_WORK_KIND
from auditmanager.comparison.work.model import WorkDependencies, Yielded
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from tests.integration.comparison.stage_run.test_lifecycle import _claim, _scene

EXPERT = frozenset({"expert"})


def test_a_refused_item_is_failed_with_its_reason_recorded(comparison_session: Session) -> None:
    store, service, work, worker, pair, revision, actor, _left, _right = _scene(comparison_session)
    batches = StageBatchService(service)
    project = str(comparison_session.execute(text(
        "SELECT project_uid FROM stage_pair WHERE stage_pair_id = :pair"), {"pair": pair}).scalar_one())
    batch = batches.start(project_uid=project, selections=[{"pair_id": pair, "link_revision_id": revision}],
                          user_uid=actor, actor_roles=EXPERT, with_ai=False,
                          idempotency_key=f"stage-batch-{new_ulid()}")
    item = _claim(store._sessions, work, worker, BATCH_WORK_KIND)
    handler = StageBatchHandler(WorkDependencies(None, store._sessions, None, work))  # type: ignore[arg-type]

    def refuse(**_kwargs):
        raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_link_revision_stale")

    handler.chains.start = refuse  # type: ignore[method-assign]
    assert isinstance(handler.run(item), Yielded)

    stored = batches.get(batch["batch_id"])
    assert stored["items"][0]["state"] == "failed" and "run_id" not in stored["items"][0]
    payloads = comparison_session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'stage.batch_item_failed' "
        "AND aggregate_type = 'StageChainBatch' AND aggregate_id = :batch"
    ), {"batch": batch["batch_id"]}).scalars().all()
    assert len(payloads) == 1
    assert payloads[0]["error_code"] == "conflict" and payloads[0]["conflict_reason"] == "stage_link_revision_stale"
    assert payloads[0]["item_id"] == stored["items"][0]["item_id"] and payloads[0]["pair_id"] == pair
