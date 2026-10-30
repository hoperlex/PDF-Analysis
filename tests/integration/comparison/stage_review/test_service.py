"""Real 0042 rows, current work lease, bulk verdict rollback and accepted journal."""

from dataclasses import replace
import json

import pytest
from sqlalchemy import text

from auditmanager.api.schemas.models import StageChangeCard, StageChangeJournal
from auditmanager.comparison.stage_review import StageReviewService
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.stage_text.test_store import _seed, _batch, _command, _id, _fragment


def _run(session, store, pair, revision, actor, *, with_ai=False):
    run = _id("crn")
    pins = session.execute(text("SELECT version_uid FROM document_version WHERE document_uid IN "
        "(SELECT left_document_uid FROM stage_pair WHERE stage_pair_id=:pair UNION "
        "SELECT right_document_uid FROM stage_pair WHERE stage_pair_id=:pair) ORDER BY version_uid"),
        {"pair": pair}).scalars().all()
    session.execute(text(
        "INSERT INTO stage_chain_run(stage_chain_run_id,stage_pair_id,stage_link_revision_id,input_sha256,"
        "pinned_version_uids,state,actor_user_uid,command_id,kind,with_ai) VALUES(:id,:pair,:revision,:sha,"
        "CAST(:pins AS jsonb),'running',:actor,:command,'full',:ai)"
    ), {"id": run, "pair": pair, "revision": revision, "sha": "c" * 64,
        "pins": json.dumps(pins), "actor": actor, "command": _command(session, "start_stage_chain_run"), "ai": with_ai})
    work = ComparisonWorkRepository()
    with session_scope(store._sessions) as opened:
        project = opened.execute(text("SELECT project_uid FROM stage_pair WHERE stage_pair_id=:pair"), {"pair": pair}).scalar_one()
        work.enqueue(opened, project_uid=project, module="stages", kind="stage_chain",
                     payload={"run_id": run})
        worker = WorkerRegistry().register(opened, version="stage-review-test", slots=1)
        item = work.claim(opened, worker_id=worker, modules={"stages"}, kinds={"stage_chain"})
    assert item is not None
    return run, item


def _fixture(session, *, with_ai=False):
    store, pair, revision, actor, left, right = _seed(session)
    fragments, manifest, raw = _batch(left, right)
    store.write(pair_id=pair, revision_id=revision, fragments=fragments,
                expected_keys=manifest, raw=raw, hints=())
    run, item = _run(session, store, pair, revision, actor, with_ai=with_ai)
    return StageReviewService(store._sessions), store, pair, revision, actor, run, item


def _complete(session, run):
    session.execute(text("UPDATE stage_chain_run SET state='completed' WHERE stage_chain_run_id=:run"), {"run": run})


def _update(card, decision="accepted", revision=0, reason=""):
    return {"card_id": card["card_id"], "expected_revision": revision, "decision": decision, "reason": reason}


def test_fenced_deterministic_cards_replay_and_accepted_exports(comparison_session):
    service, _, _, _, actor, run, item = _fixture(comparison_session)
    counts = service.advance(item, run)
    assert counts == {"total": 1, "review": 1, "project_changes": 0, "conflicts": 0, "high_importance": 0, "importance_unknown": 1}
    assert service.advance(item, run) == counts
    cards, after, _ = service.page(run, limit=1)
    assert after is None and len(cards) == 1
    card = cards[0]
    StageChangeCard.model_validate(card)
    assert card["class_name"] == "REVIEW" and card["carryover"] == "none"
    assert card["before"] == "нагрузка 10 квт" and card["after"] == "нагрузка 20 квт"
    assert {e["side"] for e in card["evidence"]} == {"left", "right"}
    assert not any(e["absence_proven"] for e in card["evidence"])
    assert service.journal(run)["accepted_count"] == 0
    _complete(comparison_session, run)
    request = dict(run_id=run, updates=[_update(card)], user_uid=actor,
                   actor_roles=frozenset({"expert"}), idempotency_key=f"review-{new_ulid()}")
    first = service.apply_verdicts(**request)
    assert service.apply_verdicts(**request) == first
    history, after = service.verdicts(card["card_id"], limit=1)
    assert history == first and after is None
    journal = service.journal(run, "section")
    StageChangeJournal.model_validate(journal)
    assert journal["accepted_count"] == 1 and set(journal["groups"][0]) == {"key", "label", "rows"}
    assert service.export(run, "xlsx").startswith(b"PK")
    assert service.export(run, "pdf").startswith(b"%PDF")
    assert b"<!doctype html>" in service.export(run, "html")


def test_lost_or_foreign_work_cannot_publish(comparison_session):
    service, _, _, _, _, run, item = _fixture(comparison_session)
    with pytest.raises(DomainError):
        service.advance(replace(item, project_uid=_id("prj")), run)
    comparison_session.execute(text("UPDATE comparison_work_attempt SET lease_expires_at=clock_timestamp()-interval '1 second' "
        "WHERE comparison_work_attempt_id=:attempt"), {"attempt": item.authority.attempt_id})
    with pytest.raises(DomainError):
        service.advance(item, run)
    assert comparison_session.execute(text("SELECT count(*) FROM stage_change_card WHERE stage_chain_run_id=:run"), {"run": run}).scalar_one() == 0


def test_verdict_refusals_and_batch_atomicity(comparison_session):
    service, _, _, _, actor, run, item = _fixture(comparison_session)
    service.advance(item, run)
    card = service.page(run)[0][0]
    _complete(comparison_session, run)
    base = dict(run_id=run, user_uid=actor, actor_roles=frozenset({"expert"}))
    for updates in ([_update(card, "rejected", reason="  ")],
                    [_update(card), _update(card)],
                    [_update(card, revision=2)]):
        with pytest.raises(DomainError):
            service.apply_verdicts(**base, updates=updates, idempotency_key=f"review-{new_ulid()}")
    with pytest.raises(DomainError):
        service.apply_verdicts(**base, updates=[_update(card), _update({"card_id": _id("ccd")})],
                              idempotency_key=f"review-{new_ulid()}")
    assert service.verdicts(card["card_id"])[0] == ()
    key = f"review-{new_ulid()}"
    service.apply_verdicts(**base, updates=[_update(card)], idempotency_key=key)
    with pytest.raises(DomainError) as reused:
        service.apply_verdicts(**base, updates=[_update(card, "rejected", reason="Нет")], idempotency_key=key)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    with pytest.raises(DomainError):
        service.apply_verdicts(**base, updates=[_update(card)], idempotency_key=f"review-{new_ulid()}")
    assert len(service.verdicts(card["card_id"])[0]) == 1


def test_exact_evidence_carries_verdict_across_run_and_keeps_lineage(comparison_session):
    service, store, pair, revision, actor, run, item = _fixture(comparison_session)
    service.advance(item, run)
    card = service.page(run)[0][0]
    _complete(comparison_session, run)
    original = service.apply_verdicts(run, [_update(card)], user_uid=actor,
        actor_roles=frozenset({"expert"}), idempotency_key=f"review-{new_ulid()}")[0]
    # End the first work so the next claim belongs to this next run.
    from auditmanager.comparison.work.model import Completed
    with session_scope(store._sessions) as opened:
        ComparisonWorkRepository().finish(opened, item.authority, Completed())
    next_run, next_item = _run(comparison_session, store, pair, revision, actor)
    service.advance(next_item, next_run)
    carried = service.page(next_run)[0][0]
    assert carried["carryover"] == "full"
    assert carried["carried_verdict_ids"] == [original["verdict_id"]]
    assert carried["verdict"]["card_id"] == carried["card_id"] != card["card_id"]
    assert carried["verdict"]["verdict_id"] != original["verdict_id"]
    assert service.journal(next_run)["accepted_count"] == 1


def test_ai_labels_have_coverage_service_cards_refuse_verdicts_and_same_retains_raw(comparison_session):
    service, _, _, _, actor, run, item = _fixture(comparison_session, with_ai=True)
    evidence_id = comparison_session.execute(text("SELECT stage_text_difference_id FROM stage_text_difference "
        "WHERE stage_link_revision_id=(SELECT stage_link_revision_id FROM stage_chain_run WHERE stage_chain_run_id=:run)"), {"run": run}).scalar_one()
    review_unit, classify_unit = _id("saunit"), _id("saunit")
    for unit, phase in ((review_unit, "review"), (classify_unit, "classify")):
        comparison_session.execute(text("INSERT INTO stage_ai_unit(stage_ai_unit_id,stage_chain_run_id,kind,group_id,source_sha256,state) "
            "VALUES(:unit,:run,:phase,'test',:sha,'completed')"), {"unit": unit, "run": run, "phase": phase, "sha": "f" * 64})
    comparison_session.execute(text("INSERT INTO stage_ai_review(stage_ai_review_id,stage_chain_run_id,stage_ai_unit_id,content_key,group_id,source_sha256,decisions) "
        "VALUES(:id,:run,:unit,:sha,'test',:sha,CAST(:decisions AS jsonb))"),
        {"id": _id("sarev"), "run": run, "unit": review_unit, "sha": "e" * 64,
         "decisions": json.dumps([{"status": "SAME", "left_fragment_ids": [], "right_fragment_ids": []}])})
    card = {"evidence_ids": [evidence_id], "class_name": "SERVICE_STRUCTURE", "category": "formatting",
            "system": "unknown", "title": "Изменение оформления"}
    comparison_session.execute(text("INSERT INTO stage_ai_classification(stage_ai_classification_id,stage_chain_run_id,stage_ai_unit_id,content_key,group_id,source_sha256,cards) "
        "VALUES(:id,:run,:unit,:sha,'test',:sha,CAST(:cards AS jsonb))"),
        {"id": _id("sacls"), "run": run, "unit": classify_unit, "sha": "d" * 64, "cards": json.dumps([card])})
    service.advance(item, run)
    cards, _, counts = service.page(run)
    assert counts["total"] == 1 and cards[0]["class_name"] == "SERVICE_STRUCTURE"
    assert len(cards[0]["evidence"]) == 2
    assert service.journal(run)["ai_hidden_same_count"] == 1
    assert service.journal(run)["ai_service_count"] == 1
    _complete(comparison_session, run)
    with pytest.raises(DomainError):
        service.apply_verdicts(run, [_update(cards[0])], user_uid=actor,
            actor_roles=frozenset({"expert"}), idempotency_key=f"review-{new_ulid()}")


def test_empty_materialization_replay_publishes_once(comparison_session):
    store, pair, revision, actor, _, _ = _seed(comparison_session)
    run, item = _run(comparison_session, store, pair, revision, actor)
    service = StageReviewService(store._sessions)
    assert service.advance(item, run)["total"] == 0
    assert service.advance(item, run)["total"] == 0
    assert comparison_session.execute(text("SELECT count(*) FROM audit_event WHERE aggregate_id=:run "
        "AND event_type='stage.cards_materialized'"), {"run": run}).scalar_one() == 1


def test_changed_evidence_in_new_revision_is_stale_and_never_accepted_automatically(comparison_session):
    service, store, pair, revision, actor, run, item = _fixture(comparison_session)
    service.advance(item, run)
    card = service.page(run)[0][0]
    _complete(comparison_session, run)
    old_verdict = service.apply_verdicts(run, [_update(card)], user_uid=actor,
        actor_roles=frozenset({"expert"}), idempotency_key=f"review-{new_ulid()}")[0]
    from auditmanager.comparison.work.model import Completed
    with session_scope(store._sessions) as opened:
        ComparisonWorkRepository().finish(opened, item.authority, Completed())
    next_revision = _id("slk")
    comparison_session.execute(text("INSERT INTO stage_link_revision(stage_link_revision_id,stage_pair_id,revision_no,"
        "base_revision_id,source,input_sha256,actor_user_uid,command_id) "
        "VALUES(:id,:pair,2,:base,'expert',:sha,:actor,:command)"),
        {"id": next_revision, "pair": pair, "base": revision, "sha": "a" * 64,
         "actor": actor, "command": _command(comparison_session, "apply_stage_sheet_map")})
    left, right = comparison_session.execute(text("SELECT left_profile_id,right_profile_id FROM stage_link_item "
        "WHERE stage_link_revision_id=:revision"), {"revision": revision}).one()
    comparison_session.execute(text("INSERT INTO stage_link_item(stage_link_item_id,stage_link_revision_id,row_no,"
        "left_profile_id,right_profile_id,relation,confidence) VALUES(:id,:revision,1,:left,:right,'paired','manual')"),
        {"id": _id("sli"), "revision": next_revision, "left": left, "right": right})
    from auditmanager.comparison.stage_text import SheetLink, build_raw_differences
    fragments = (_fragment(left, "left", "Нагрузка 10 кВт", 2),
                 _fragment(right, "right", "Нагрузка 30 кВт", 2))
    manifest = {profile: frozenset(f.content_key for f in fragments if f.profile_id == profile) for profile in (left, right)}
    raw = build_raw_differences([SheetLink(left, right)], fragments,
                               {left: (100, 100), right: (100, 100)}, manifest)
    store.write(pair_id=pair, revision_id=next_revision, fragments=fragments, expected_keys=manifest, raw=raw, hints=())
    next_run, next_item = _run(comparison_session, store, pair, next_revision, actor)
    service.advance(next_item, next_run)
    new_card = service.page(next_run)[0][0]
    assert new_card["carryover"] == "stale" and "verdict" not in new_card
    assert new_card["carried_verdict_ids"] == [old_verdict["verdict_id"]]
    assert not new_card["stale"] and service.get(card["card_id"])["stale"]
    assert service.journal(next_run)["accepted_count"] == 0
