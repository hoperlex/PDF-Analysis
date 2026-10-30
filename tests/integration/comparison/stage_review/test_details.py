"""Importance/materiality are actual matched immutable classifier labels, never category guesses."""

import json

import pytest
from sqlalchemy import text

from auditmanager.api.schemas.models import StageChangeCard
from tests.integration.comparison.stage_text.test_store import _id
from tests.integration.comparison.stage_review.test_service import _fixture


@pytest.mark.parametrize("metadata,expected", [
    ({"materiality": "material", "importance": "high", "detail_increased": True}, ("material", "high", True, 1, 0)),
    ({"materiality": "non_material", "importance": "normal", "detail_increased": False}, ("non_material", "normal", False, 0, 0)),
    ({}, ("unknown", "unknown", False, 0, 1)),
    ({"materiality": "made_up", "importance": "critical", "detail_increased": "yes"}, ("unknown", "unknown", False, 0, 1)),
])
def test_actual_metadata_and_counts_are_source_bound_with_safe_old_defaults(comparison_session, metadata, expected):
    service, _, _, revision, _, run, item = _fixture(comparison_session, with_ai=True)
    source = comparison_session.execute(text("SELECT stage_text_difference_id FROM stage_text_difference WHERE stage_link_revision_id=:revision"),
                                        {"revision": revision}).scalar_one()
    unit, classification = _id("saunit"), _id("sacls")
    comparison_session.execute(text("INSERT INTO stage_ai_unit(stage_ai_unit_id,stage_chain_run_id,kind,group_id,source_sha256,state) "
        "VALUES(:id,:run,'classify','test',:sha,'completed')"), {"id": unit, "run": run, "sha": "a" * 64})
    card = {"class_name": "PROJECT_CHANGE", "category": "electrical_load", "system": "electrical",
            "title": "Нагрузка изменилась", "evidence_ids": [source]} | metadata
    comparison_session.execute(text("INSERT INTO stage_ai_classification(stage_ai_classification_id,stage_chain_run_id,stage_ai_unit_id,"
        "content_key,group_id,source_sha256,cards) VALUES(:id,:run,:unit,:sha,'test',:sha,CAST(:cards AS jsonb))"),
        {"id": classification, "run": run, "unit": unit, "sha": "b" * 64, "cards": json.dumps([card])})
    counts = service.advance(item, run)
    projected = service.page(run)[0][0]
    StageChangeCard.model_validate(projected)
    assert (projected["materiality"], projected["importance"], projected["detail_increased"],
            counts["high_importance"], counts["importance_unknown"]) == expected
    assert service.get(projected["card_id"])["importance"] == expected[1]
    assert "classification_id" not in projected


def test_raw_card_has_unknown_metadata_even_for_electrical_load(comparison_session):
    service, _, _, _, _, run, item = _fixture(comparison_session)
    counts = service.advance(item, run)
    card = service.page(run)[0][0]
    assert card["materiality"] == card["importance"] == "unknown" and not card["detail_increased"]
    assert counts["high_importance"] == 0 and counts["importance_unknown"] == 1
