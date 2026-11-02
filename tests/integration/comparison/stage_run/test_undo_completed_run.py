"""Undoing a repair on a finished run is a recompute and a fresh run, never a failed reopening."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import new_ulid
from tests.integration.comparison.stage_repair.test_service import _scene

EXPERT = frozenset({"expert"})


def _work_rows(session: Session, run_id: str) -> int:
    return int(session.execute(text(
        "SELECT count(*) FROM comparison_work WHERE kind = 'stage_chain' AND payload->>'run_id' = :run"
    ), {"run": run_id}).scalar_one())


def test_undo_on_a_completed_run_leaves_it_completed_and_a_fresh_run_can_start(comparison_session: Session) -> None:
    maps, repairs, chains, run, item, expert, _l1, _l2, _r1, _r2 = _scene(comparison_session)
    assert repairs.advance(item, run_id=run.run_id)["repairs"] == 1
    repaired = maps.current(pair_id=run.pair_id)
    (applied,), _ = repairs.page(run_id=run.run_id, after=None, limit=10)
    # The run finishes as step 7 leaves it: every receipt completed, the repaired map effective.
    with session_scope(maps._sessions) as session:
        session.execute(text(
            "UPDATE stage_chain_step SET state = 'completed', finished_at = clock_timestamp() "
            "WHERE stage_chain_run_id = :run"
        ), {"run": run.run_id})
        session.execute(text("UPDATE stage_chain_run SET state = 'completed' WHERE stage_chain_run_id = :run"),
                        {"run": run.run_id})
    work_before = _work_rows(comparison_session, run.run_id)

    undone = repairs.undo(repair_id=applied["repair_id"], base_revision_id=repaired.revision_id,
                          user_uid=expert, actor_roles=EXPERT, idempotency_key=f"undo-{new_ulid()}")

    assert undone["state"] == "undone"
    restored = maps.current(pair_id=run.pair_id)
    assert restored.source == "expert" and restored.revision_id != repaired.revision_id
    finished = chains.get(run.run_id)
    assert finished.state == "completed" and finished.failure_reason is None
    assert all(step.state == "completed" for step in finished.steps)
    assert finished.effective_revision_id == repaired.revision_id and finished.stale
    assert _work_rows(comparison_session, run.run_id) == work_before  # nothing queued for the finished run
    recompute = comparison_session.execute(text(
        "SELECT recompute_run_id FROM stage_link_repair_event "
        "WHERE stage_link_repair_id = :repair AND action = 'undone'"
    ), {"repair": applied["repair_id"]}).scalar_one()
    assert recompute is not None and recompute != run.run_id

    fresh = chains.start(pair_id=run.pair_id, revision_id=restored.revision_id, user_uid=expert,
                         actor_roles=EXPERT, with_ai=False, idempotency_key=f"chain-{new_ulid()}")
    assert fresh.run_id != run.run_id and fresh.state == "queued"
