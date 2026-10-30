"""Run-local sge receipts must preserve verdict identity by stable engine raw evidence."""

import json

from sqlalchemy import text

from auditmanager.comparison.engine import ENGINE_ALGO_VERSION, PairResultRepository
from auditmanager.comparison.stage_graphic.evidence import project_result
from auditmanager.comparison.stage_review.cards import digest
from auditmanager.comparison.work.model import Completed
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import new_ulid
from tests.integration.comparison.stage_text.test_store import _id
from tests.integration.comparison.stage_review.test_service import _fixture, _run, _complete, _update


def _graphic(session, run, left, right, *, changed=False):
    row = session.execute(text("SELECT r.stage_link_revision_id,p.project_uid FROM stage_chain_run r "
        "JOIN stage_pair p ON p.stage_pair_id=r.stage_pair_id WHERE r.stage_chain_run_id=:run"), {"run": run}).one()
    engine_key = digest(["engine-content", changed])
    repo = PairResultRepository()
    stored = repo.find(session, row[1], engine_key)
    if stored is None:
        identity = repo.insert(session, project_uid=row[1], content_key=engine_key, algo_version=ENGINE_ALGO_VERSION,
            status="different", reasons=[], channels={"geometry": {"state": "checked", "diffs": 1},
                "color": {"state": "checked", "diffs": 0}}, page_a_profile_id=left, page_b_profile_id=right,
            mask_blob_id=None, result={"how_compared": {"transform": [1, 0, 0, 1, 0, 0], "dpi": 200},
                "differences": [{"region_class": "graphic_changed", "layer": "main", "box": {
                    "x": 10, "y": 20, "width": 30, "height": 40}, "before_text": "old", "after_text": "new" if changed else "same"}]})
        stored = repo.get(session, identity)
    status, reason, regions = project_result(stored, left_size=(200, 200), right_size=(200, 200))
    link = session.execute(text("SELECT stage_link_item_id FROM stage_link_item WHERE stage_link_revision_id=:revision"),
                           {"revision": row[0]}).scalar_one()
    graphic = _id("sge")
    session.execute(text("INSERT INTO stage_graphic_evidence(stage_graphic_evidence_id,stage_chain_run_id,stage_link_item_id,"
        "left_profile_id,right_profile_id,comparison_sheet_pair_result_id,status,reason,regions,content_key) "
        "VALUES(:id,:run,:link,:left,:right,:result,:status,:reason,CAST(:regions AS jsonb),:key)"),
        {"id": graphic, "run": run, "link": link, "left": left, "right": right, "result": stored.result_id,
         "status": status, "reason": reason, "regions": json.dumps(regions), "key": digest([run, stored.content_key])})
    return graphic


def test_graphic_same_evidence_carries_across_runs_changed_region_does_not(comparison_session):
    service, store, pair, revision, actor, run, item = _fixture(comparison_session)
    left, right = comparison_session.execute(text("SELECT left_profile_id,right_profile_id FROM stage_link_item "
        "WHERE stage_link_revision_id=:revision"), {"revision": revision}).one()
    first_graphic = _graphic(comparison_session, run, left, right)
    service.advance(item, run)
    card = next(card for card in service.page(run)[0] if first_graphic in card["evidence_ids"])
    assert len(card["evidence"]) == 2
    assert {tuple(sorted(e["box_anchor"].items())) for e in card["evidence"]} == {
        tuple(sorted({"x0": 10, "top": 20, "x1": 40, "bottom": 60}.items()))}
    _complete(comparison_session, run)
    original = service.apply_verdicts(run, [_update(card)], user_uid=actor,
        actor_roles=frozenset({"expert"}), idempotency_key=f"graphic-{new_ulid()}")[0]
    with session_scope(store._sessions) as opened:
        ComparisonWorkRepository().finish(opened, item.authority, Completed())
    same_run, same_item = _run(comparison_session, store, pair, revision, actor)
    same_graphic = _graphic(comparison_session, same_run, left, right)
    service.advance(same_item, same_run)
    carried = next(c for c in service.page(same_run)[0] if same_graphic in c["evidence_ids"])
    assert carried["evidence_digest"] == card["evidence_digest"]
    assert carried["carryover"] == "full" and carried["carried_verdict_ids"] == [original["verdict_id"]]
    assert carried["verdict"]["decision"] == "accepted" and same_graphic != first_graphic
    _complete(comparison_session, same_run)
    with session_scope(store._sessions) as opened:
        ComparisonWorkRepository().finish(opened, same_item.authority, Completed())
    changed_run, changed_item = _run(comparison_session, store, pair, revision, actor)
    changed_graphic = _graphic(comparison_session, changed_run, left, right, changed=True)
    service.advance(changed_item, changed_run)
    stale = next(c for c in service.page(changed_run)[0] if changed_graphic in c["evidence_ids"])
    assert stale["evidence_digest"] != card["evidence_digest"]
    assert stale["carryover"] == "stale" and "verdict" not in stale
    assert service.journal(changed_run)["accepted_count"] == 0
