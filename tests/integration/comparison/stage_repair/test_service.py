"""HIGH swaps commit as one revision and undo is a new expert act."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.stage_links.map import LinkInput
from auditmanager.comparison.stage_repair.service import StageRepairService
from auditmanager.comparison.stage_run.service import StageChainService, WORK_KIND
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.stage_links.test_map import seed
from tests.support.accounts import complete_expert_account


def _scene(session: Session):
    maps, pair, actor, left_one, left_two, right_one = seed(session)
    right_two = str(session.execute(text(
        "SELECT p2.comparison_page_profile_id FROM comparison_page_profile p1 "
        "JOIN comparison_page_profile p2 ON p2.version_uid = p1.version_uid AND p2.page_number = 2 "
        "WHERE p1.comparison_page_profile_id = :right"
    ), {"right": right_one}).scalar_one())
    expert = str(complete_expert_account(session, f"repair-{new_ulid().lower()}").user_uid)
    before = maps.apply(pair_id=pair, base_revision_id=None, items=(
        LinkInput("paired", left_one, right_two), LinkInput("paired", left_two, right_one),
    ), user_uid=actor, actor_roles=frozenset({"expert"}), idempotency_key=f"map-{new_ulid()}")
    chains = StageChainService(maps._sessions, comparison_modules="versions,stages")
    run = chains.start(pair_id=pair, revision_id=before.revision_id, user_uid=expert,
                       actor_roles=frozenset({"expert"}), with_ai=False,
                       idempotency_key=f"chain-{new_ulid()}")
    work = ComparisonWorkRepository()
    with session_scope(maps._sessions) as inner:
        worker = WorkerRegistry().register(inner, version="repair-service-test", slots=1)
        item = work.claim(inner, worker_id=worker, modules={"stages"}, kinds={WORK_KIND})
    assert item is not None
    return maps, StageRepairService(maps._sessions), chains, run, item, expert, left_one, left_two, right_one, right_two


def test_atomic_swap_and_keyed_undo_recompute(comparison_session: Session) -> None:
    maps, repairs, chains, run, item, expert, left_one, left_two, right_one, right_two = _scene(comparison_session)
    result = repairs.advance(item, run_id=run.run_id)
    assert result == {"repair_cycles": 1, "repairs": 1, "recompute": 1}
    current = maps.current(pair_id=run.pair_id)
    assert current.source == "automatic"
    assert {(row.left_profile_id, row.right_profile_id) for row in current.items} == {
        (left_one, right_one), (left_two, right_two),
    }
    assert all(row.confidence == "automatic_repair" for row in current.items)
    assert chains.get(run.run_id).effective_revision_id == current.revision_id
    rows, _ = repairs.page(run_id=run.run_id, after=None, limit=10)
    assert len(rows) == 1 and rows[0]["state"] == "applied"
    request = dict(repair_id=rows[0]["repair_id"], base_revision_id=current.revision_id,
                   user_uid=expert, actor_roles=frozenset({"expert"}),
                   idempotency_key=f"undo-{new_ulid()}")
    undone = repairs.undo(**request)
    assert undone["state"] == "undone" and repairs.undo(**request) == undone
    restored = maps.current(pair_id=run.pair_id)
    assert restored.source == "expert"
    assert {(row.left_profile_id, row.right_profile_id) for row in restored.items} == {
        (left_one, right_two), (left_two, right_one),
    }
    event = comparison_session.execute(text(
        "SELECT recompute_run_id FROM stage_link_repair_event "
        "WHERE stage_link_repair_id = :repair AND action = 'undone'"
    ), {"repair": rows[0]["repair_id"]}).scalar_one()
    assert event is not None
    assert repairs.advance(item, run_id=run.run_id)["repair_cycles"] == 1


def test_later_manual_revision_supersedes_undo(comparison_session: Session) -> None:
    maps, repairs, _chains, run, item, expert, left_one, left_two, right_one, right_two = _scene(comparison_session)
    repairs.advance(item, run_id=run.run_id)
    repaired = maps.current(pair_id=run.pair_id)
    rows, _ = repairs.page(run_id=run.run_id, after=None, limit=10)
    maps.apply(pair_id=run.pair_id, base_revision_id=repaired.revision_id, items=(
        LinkInput("paired", left_one, right_one), LinkInput("paired", left_two, right_two),
    ), user_uid=expert, actor_roles=frozenset({"expert"}), idempotency_key=f"manual-{new_ulid()}")
    superseded, _ = repairs.page(run_id=run.run_id, after=None, limit=10)
    assert superseded[0]["state"] == "superseded"
    with pytest.raises(DomainError) as error:
        repairs.undo(repair_id=rows[0]["repair_id"], base_revision_id=repaired.revision_id,
                     user_uid=expert, actor_roles=frozenset({"expert"}),
                     idempotency_key=f"undo-{new_ulid()}")
    assert error.value.code is ErrorCode.CONFLICT
