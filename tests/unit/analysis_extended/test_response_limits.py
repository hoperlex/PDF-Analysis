"""Valid engineering observations must survive additional queries and longer explanations."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from auditmanager.analysis.extended import block_ensemble, core, cross_window_review, workflow
from auditmanager.analysis.extended.review import _validate


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


def cross_window_example(count):
    sources = []
    for index, quote in enumerate(["Щит Щ-1: ток 10 А.", "Щит Щ-1: ток 20 А."], start=1):
        sources.append({"source_id": f"s{index}", "kind": "text", "window_id": f"w{index}",
            "page_number": index, "quote": quote, "text_sha256": hashlib.sha256(quote.encode()).hexdigest(),
            "character_start": 0, "character_end": len(quote), "character_field": "text"})
    batch = {"sources": sources, "batch_key": "gcwb_test", "batch_sha256": "a" * 64}
    queries = [f"Запрос {i}" for i in range(count)]
    row = observation(*queries) | {"source_ids": ["s1", "s2"], "source_evidence": [
        {"source_id": source["source_id"], "quote": source["quote"]} for source in sources]}
    return batch, row


@pytest.mark.parametrize("count", [0, 3, 20])
@pytest.mark.parametrize("collect_refusals", [False, True])
def test_real_cross_window_reply_retains_all_queries(count, collect_refusals):
    batch, row = cross_window_example(count)
    rejected = [] if collect_refusals else None
    parsed = cross_window_review.parse_global_cross_window_reply(
        json.dumps({"observations": [row]}), batch=batch, rejected=rejected)
    assert len(parsed) == 1
    assert parsed[0]["norm_queries"] == row["norm_queries"]
    assert parsed[0]["window_ids"] == ["w1", "w2"]
    assert [evidence["quote"] for evidence in parsed[0]["source_evidence"]] == [source["quote"] for source in batch["sources"]]
    assert rejected in (None, [])


@pytest.mark.parametrize("fault,reason", [("source", "global_cross_window_reply_sources_invalid"),
                                         ("quote", "global_cross_window_quote_not_in_source")])
@pytest.mark.parametrize("collect_refusals", [False, True])
def test_cross_window_source_and_quote_binding_still_refuse_invalid_records(fault, reason, collect_refusals):
    batch, row = cross_window_example(3)
    if fault == "source":
        row["source_ids"][1] = "foreign"
    else:
        row["source_evidence"][1]["quote"] = "Цитата отсутствует в источнике."
    reply = json.dumps({"observations": [row]})
    if collect_refusals:
        rejected = []
        assert cross_window_review.parse_global_cross_window_reply(reply, batch=batch, rejected=rejected) == []
        assert [record["reason"] for record in rejected] == [reason]
    else:
        with pytest.raises(ValueError, match=reason):
            cross_window_review.parse_global_cross_window_reply(reply, batch=batch)


@pytest.mark.parametrize("value", [[], "not an array", [1], [""]])
def test_unbounded_arrays_keep_their_type_minimum_and_item_checks(value):
    schema = {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}
    with pytest.raises(ValueError):
        _validate(value, schema)


def test_array_limits_still_apply_when_explicitly_declared():
    schema = {"type": "array", "maxItems": 1, "items": {"type": "string"}}
    _validate(["a"], schema)
    with pytest.raises(ValueError, match="review_array_schema_invalid"):
        _validate(["a", "b"], schema)
