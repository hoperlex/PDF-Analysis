"""Actual distant-window source comparison, with exact quotations from both packs."""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .core import ModelRequest, canonical, digest
from .coverage import validate_cross_window_policy
from .review import _document, _validate
from .workflow import review_bundle_digest

VERSION = "cross-window-comprehensive-v1"


def _text(maximum):
    return {"type": "string", "minLength": 1, "maxLength": maximum}


def response_schema():
    evidence = {"type": "object", "additionalProperties": False,
        "required": ["source_id", "quote"], "properties": {"source_id": _text(160), "quote": _text(2000)}}
    observation = {"type": "object", "additionalProperties": False,
        "required": ["title", "description", "source_ids", "norm_queries", "source_evidence"],
        "properties": {"title": _text(200), "description": _text(3000),
            "source_ids": {"type": "array", "minItems": 2, "maxItems": 16, "items": _text(160)},
            "norm_queries": {"type": "array", "maxItems": 2, "items": _text(160)},
            "source_evidence": {"type": "array", "minItems": 2, "maxItems": 8, "items": evidence}}}
    return {"type": "object", "additionalProperties": False, "required": ["observations"],
        "properties": {"observations": {"type": "array", "maxItems": 20, "items": observation}}}


def _sources(batch):
    if not isinstance(batch, dict) or not isinstance(batch.get("sources"), list) or not 2 <= len(batch["sources"]) <= 8:
        raise ValueError("global_cross_window_sources_invalid")
    indexed = {}
    for source in batch["sources"]:
        if (not isinstance(source, dict) or source.get("kind") != "text"
                or not isinstance(source.get("source_id"), str) or not source["source_id"]
                or len(source["source_id"]) > 160 or source["source_id"] in indexed
                or not isinstance(source.get("window_id"), str) or not source["window_id"]
                or type(source.get("page_number")) is not int or source["page_number"] < 1
                or not isinstance(source.get("quote"), str) or not 1 <= len(source["quote"]) <= 20_000
                or type(source.get("character_start")) is not int or source["character_start"] < 0
                or type(source.get("character_end")) is not int
                or source["character_end"] - source["character_start"] != len(source["quote"])
                or source.get("text_sha256") != hashlib.sha256(source["quote"].encode("utf-8")).hexdigest()
                or source.get("character_field") not in {"text", "recognised_context"}):
            raise ValueError("global_cross_window_source_binding_invalid")
        indexed[source["source_id"]] = source
    if len({source["window_id"] for source in indexed.values()}) < 2 or sum(len(source["quote"]) for source in indexed.values()) > 40_000:
        raise ValueError("global_cross_window_distinct_windows_required")
    return indexed


def build_global_cross_window_request(*, model_id, run_id, section, batch, source_sha256, policy):
    from .section_rules import section_instructions
    if not validate_cross_window_policy(policy): raise ValueError("global_cross_window_policy_required")
    indexed = _sources(batch)
    if any(source.get("source_sha256") != source_sha256 for source in indexed.values()):
        raise ValueError("global_cross_window_frozen_source_mismatch")
    payload = {"workflow_version": "extended-review-v3", "procedure": "global_cross_window",
        "global_cross_window_policy": deepcopy(policy), "source_sha256": source_sha256,
        "rules_sha256": review_bundle_digest(section), "batch_key": batch["batch_key"],
        "batch_sha256": batch["batch_sha256"], "relation": deepcopy(batch.get("relation", {})),
        "sources": [{key: deepcopy(value) for key, value in source.items() if key not in {"quote", "context"}}
                    for source in indexed.values()],
        "source_packs": [{"source_id": source["source_id"], "window_id": source["window_id"],
            "page_number": source["page_number"], "version_uid": source["version_uid"],
            "character_field": source["character_field"], "character_start": source["character_start"],
            "character_end": source["character_end"], "text": source["quote"]} for source in indexed.values()],
        "coverage": {"all_document_semantics_compared": False, "both_source_windows_provided": True,
                     "raw_images_attached": False, "full_original_sources_retained": True}}
    instruction = (f"Выполни реальную межоконную комплексную сверку раздела {section}. "
        "source_packs содержат фактический текст разных удалённых окон одного PDF, а не свод готовых замечаний. "
        "Сверь объекты, марки, количества, единицы, размеры, арифметику таблиц/перечней, требования общего текста "
        "и частные сведения, которые действительно присутствуют в этих пакетах. Ищи конкретное расхождение между ними. "
        "Не объявляй отсутствие по неполному охвату. Обе стороны могут быть корректны в разных условиях; "
        "если источник не позволяет установить расхождение, не изобретай наблюдение. Никаких новых нормативных "
        "утверждений, внешних файлов, OCR, графики или экспертных решений. "
        "Для КАЖДОГО наблюдения source_evidence содержит ДОСЛОВНЫЕ quote из фактически предоставленных пакетов "
        "МИНИМУМ ДВУХ разных window_id; source_ids точно равны множеству процитированных source_id. "
        "Пустой observations допустим; это не доказывает отсутствие остальных расхождений. "
        "norm_queries — только поисковые запросы, не подтверждение нормы. Ответ по закрытой схеме, по-русски.\n\n" +
        section_instructions(section, "comprehensive_analysis"))
    body = {"model": model_id, "max_tokens": 6000, "system": instruction,
        "messages": [{"role": "user", "content": canonical(payload)}], "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": response_schema()}}}
    if len(canonical(body).encode("utf-8")) > 900_000: raise ValueError("global_cross_window_request_budget")
    return ModelRequest(model_id, body,
        idempotency_scope=f"{run_id}:v3:global-cross-window:{batch['batch_key']}:{digest(body)}")


def parse_global_cross_window_reply(text, *, batch):
    indexed = _sources(batch); answer = _document(text); _validate(answer, response_schema())
    output = []
    for observation in answer["observations"]:
        refs = observation["source_ids"]
        if len(refs) != len(set(refs)) or not set(refs) <= set(indexed):
            raise ValueError("global_cross_window_reply_sources_invalid")
        cited, windows, evidence_rows = set(), set(), []
        for evidence in observation["source_evidence"]:
            source = indexed.get(evidence["source_id"])
            if source is None or evidence["quote"] not in source["quote"]:
                raise ValueError("global_cross_window_quote_not_in_source")
            relative = source["quote"].find(evidence["quote"])
            evidence_rows.append({**deepcopy(evidence), "page_number": source["page_number"],
                "window_id": source["window_id"], "character_field": source["character_field"],
                "character_start": source["character_start"] + relative,
                "character_end": source["character_start"] + relative + len(evidence["quote"]),
                "quote_occurrence": "first_exact_match_in_provided_piece"})
            cited.add(evidence["source_id"]); windows.add(source["window_id"])
        if cited != set(refs) or len(windows) < 2:
            raise ValueError("global_cross_window_both_windows_must_be_cited")
        output.append({**deepcopy(observation), "source_evidence": evidence_rows,
            "origin_scope": "global_cross_window", "cross_window_batch_key": batch["batch_key"],
            "window_ids": sorted(windows), "global_batch_sha256": batch["batch_sha256"]})
    return output
