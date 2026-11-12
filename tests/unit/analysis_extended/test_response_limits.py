"""Valid engineering observations must survive additional queries and longer explanations."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from auditmanager.analysis.extended import block_ensemble, core, cross_window_review, workflow


def observation(*queries: str) -> dict:
    return {"title": "Защита цепи", "description": "Проверить согласование защиты с кабелем и двигателем.",
            "source_ids": ["s1"], "norm_queries": list(queries)}


@pytest.mark.parametrize("count", [3, 20])
def test_a_leg_and_the_judges_gap_search_retain_every_norm_query(count):
    row = observation(*(f"Запрос {i}" for i in range(count)))
    rejected = []
    assert core.parse_reply(json.dumps({"observations": [row]}), allowed_sources={"s1"}, rejected=rejected) == [row]
    document = {"relationships": [], "gap_observations": [row], "gap_search": {
        "performed": True, "status": "gaps_found", "searched_categories": [], "summary": "Проверена защита."}}
    parsed = block_ensemble.parse_block_judge_reply(json.dumps(document), allowed_sources={"s1"},
        refs={"leg1": ["leg1:001"]}, rejected=rejected)
    assert next(record["item"] for record in parsed if record["kind"] == "gap") == row
    assert rejected == []


@pytest.mark.parametrize("length", [305, 315, 349, 2000])
def test_a_relationship_keeps_its_complete_explanation(length):
    row = {"left_ref": "leg1:001", "right_ref": "leg2:001", "relation": "extension", "extends": "both",
           "confidence": 0.98, "reason": "а" * length}
    document = {"relationships": [row], "gap_observations": [], "gap_search": {
        "performed": True, "status": "no_new_findings", "searched_categories": [], "summary": ""}}
    rejected = []
    parsed = block_ensemble.parse_block_judge_reply(json.dumps(document), allowed_sources={"s1"},
        refs={"leg1": ["leg1:001"], "leg2": ["leg2:001"]}, rejected=rejected)
    assert parsed[0] == {"kind": "relationship", **row}
    assert rejected == []


@pytest.mark.parametrize("full_document", [False, True])
def test_exact_duplicate_findings_merge_without_losing_their_distinct_queries(full_document):
    left = observation("Норма А", "Норма Б")
    right = observation("Норма В", "Норма Г")
    originals = deepcopy([left, right])
    merged = workflow.deterministic_lossless_merge([left, right], full_document=full_document)
    assert len(merged) == 1
    assert merged[0]["norm_queries"] == ["Норма А", "Норма Б", "Норма В", "Норма Г"]
    assert merged[0]["merged_observations"] == originals
    assert [left, right] == originals


def test_response_schemas_do_not_reintroduce_the_removed_limits():
    request = block_ensemble.build_block_judge_request(model_id="m", run_id="r", section="EOM",
        payload={"sources": [{"source_id": "s1"}]}, legs={"leg1": [observation()], "leg2": [observation()]})
    judge = request.body["output_config"]["format"]["schema"]["properties"]
    queries = [core.response_schema()["properties"]["observations"]["items"]["properties"]["norm_queries"],
               core.response_schema(merge=True)["properties"]["observations"]["items"]["properties"]["norm_queries"],
               cross_window_review.response_schema()["properties"]["observations"]["items"]["properties"]["norm_queries"],
               judge["gap_observations"]["items"]["properties"]["norm_queries"]]
    assert all("maxItems" not in schema for schema in queries)
    assert "maxLength" not in judge["relationships"]["items"]["properties"]["reason"]


@pytest.mark.parametrize("change", [{"source_ids": ["foreign"]}, {"source_ids": ["s1", "s1"]},
                                    {"norm_queries": [""]}, {"norm_queries": ["а" * 161]}])
def test_removing_the_count_limit_keeps_source_and_query_content_validation(change):
    row = observation("Норма А", "Норма Б", "Норма В") | change
    with pytest.raises(ValueError, match="observation_sources_or_limits_invalid"):
        core.parse_reply(json.dumps({"observations": [row]}), allowed_sources={"s1"})
