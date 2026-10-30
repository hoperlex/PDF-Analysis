"""Experts may expose masked/service evidence without modifying or accepting raw/model rows."""

import json

import pytest
from sqlalchemy import text

from auditmanager.api.schemas.models import StageChangeCard
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from tests.integration.comparison.stage_text.test_store import _id
from tests.integration.comparison.stage_review.test_service import _fixture, _complete


def _masked(session, run):
    return list(session.execute(text("SELECT left_fragment_id,right_fragment_id FROM stage_text_exclusion "
        "WHERE stage_link_revision_id=(SELECT stage_link_revision_id FROM stage_chain_run WHERE stage_chain_run_id=:run)"),
        {"run": run}).one())


def test_masked_fragments_create_keyed_anchored_review_without_removing_exclusion(comparison_session):
    service, _, _, _, actor, run, item = _fixture(comparison_session)
    service.advance(item, run)
    ids = _masked(comparison_session, run)
    _complete(comparison_session, run)
    key = f"promote-{new_ulid()}"
    request = dict(run_id=run, source_ids=ids, reason="  Эксперт просит проверить контекст  ",
                   user_uid=actor, actor_roles=frozenset({"expert"}), idempotency_key=key)
    card = service.promote(**request)
    assert service.promote(**request) == card
    StageChangeCard.model_validate(card)
    assert card["class_name"] == "REVIEW" and set(card["evidence_ids"]) == set(ids) and "verdict" not in card
    assert len(card["evidence"]) == 2 and all(e["box_anchor"] and not e["absence_proven"] for e in card["evidence"])
    assert service.page(run)[2]["total"] == 2 and service.journal(run)["accepted_count"] == 0
    assert comparison_session.execute(text("SELECT count(*) FROM stage_text_exclusion WHERE "
        "stage_link_revision_id=(SELECT stage_link_revision_id FROM stage_chain_run WHERE stage_chain_run_id=:run)"),
        {"run": run}).scalar_one() == 1
    events = comparison_session.execute(text("SELECT payload FROM audit_event WHERE aggregate_id=:run "
        "AND event_type='stage.review_card_created'"), {"run": run}).scalars().all()
    assert len(events) == 1 and events[0]["reason"] == "Эксперт просит проверить контекст"
    assert set(events[0]) == {"source_ids", "card_id", "actor_uid", "command_id", "reason"}
    assert "кабель" not in json.dumps(events[0], ensure_ascii=False).lower()
    with pytest.raises(DomainError) as reused:
        service.promote(**(request | {"reason": "Иной комментарий"}))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_service_evidence_gets_new_review_card_and_original_class_is_immutable(comparison_session):
    service, _, _, revision, actor, run, item = _fixture(comparison_session, with_ai=True)
    source_id = comparison_session.execute(text("SELECT stage_text_difference_id FROM stage_text_difference "
        "WHERE stage_link_revision_id=:revision"), {"revision": revision}).scalar_one()
    unit, classification = _id("saunit"), _id("sacls")
    comparison_session.execute(text("INSERT INTO stage_ai_unit(stage_ai_unit_id,stage_chain_run_id,kind,group_id,source_sha256,state) "
        "VALUES(:id,:run,'classify','test',:sha,'completed')"), {"id": unit, "run": run, "sha": "e" * 64})
    comparison_session.execute(text("INSERT INTO stage_ai_classification(stage_ai_classification_id,stage_chain_run_id,stage_ai_unit_id,"
        "content_key,group_id,source_sha256,cards) VALUES(:id,:run,:unit,:sha,'test',:sha,CAST(:cards AS jsonb))"),
        {"id": classification, "run": run, "unit": unit, "sha": "f" * 64, "cards": json.dumps([{
            "class_name": "SERVICE_STRUCTURE", "category": "formatting", "system": "unknown",
            "title": "Служебное различие", "evidence_ids": [source_id]}])})
    service.advance(item, run)
    old = service.page(run)[0][0]
    assert old["class_name"] == "SERVICE_STRUCTURE"
    _complete(comparison_session, run)
    created = service.promote(run, [source_id], "Существенно по мнению эксперта", user_uid=actor,
        actor_roles=frozenset({"expert"}), idempotency_key=f"promote-{new_ulid()}")
    assert created["class_name"] == "REVIEW" and created["card_id"] != old["card_id"]
    assert service.get(old["card_id"])["class_name"] == "SERVICE_STRUCTURE"
    assert "verdict" not in created and service.journal(run)["accepted_count"] == 0


def test_promote_refuses_missing_role_invalid_foreign_or_incomplete_sources_atomically(comparison_session):
    service, _, _, _, actor, run, _ = _fixture(comparison_session)
    ids = _masked(comparison_session, run)
    base = dict(run_id=run, source_ids=ids, reason="Проверить", user_uid=actor,
                actor_roles=frozenset({"expert"}))
    with pytest.raises(DomainError):
        service.promote(**base, idempotency_key=f"promote-{new_ulid()}")
    _complete(comparison_session, run)
    for changes in ({"actor_roles": frozenset()}, {"source_ids": [_id("stf")]},
                    {"source_ids": [ids[0], ids[0]]}, {"source_ids": []}, {"reason": "  "}):
        with pytest.raises(DomainError):
            service.promote(**(base | changes), idempotency_key=f"promote-{new_ulid()}")
    assert comparison_session.execute(text("SELECT count(*) FROM stage_change_card WHERE stage_chain_run_id=:run"),
                                      {"run": run}).scalar_one() == 0
