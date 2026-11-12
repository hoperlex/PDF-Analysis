"""Actual distant-window source comparison, with exact quotations from both packs."""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .core import ModelRequest, canonical, digest, effort_of, limit_of
from .coverage import validate_cross_window_policy
from .cross_window import FULL_BIN_SOURCES, FULL_COVERAGE_MODE, FULL_VERSION
from .review import _document, _validate
from .workflow import review_bundle_digest

VERSION = "cross-window-comprehensive-v1"


def _text(maximum):
    return {"type": "string", "minLength": 1, "maxLength": maximum}


def response_schema(*, source_ids=None):
    identity = _text(160)
    if source_ids is not None:
        identity["enum"] = sorted(source_ids)
    evidence = {"type": "object", "additionalProperties": False,
        "required": ["source_id", "quote"], "properties": {"source_id": identity, "quote": _text(2000)}}
    observation = {"type": "object", "additionalProperties": False,
        "required": ["title", "description", "source_ids", "norm_queries", "source_evidence"],
        "properties": {"title": _text(200), "description": _text(3000),
            "source_ids": {"type": "array", "minItems": 2, "maxItems": 16, "items": identity},
            "norm_queries": {"type": "array", "items": _text(160)},
            "source_evidence": {"type": "array", "minItems": 2, "maxItems": 8, "items": evidence}}}
    return {"type": "object", "additionalProperties": False, "required": ["observations"],
        "properties": {"observations": {"type": "array", "maxItems": 20, "items": observation}}}


def _sources(batch):
    full = isinstance(batch, dict) and batch.get("coverage_mode") == FULL_COVERAGE_MODE
    maximum = 2 * FULL_BIN_SOURCES if full else 8
    if not isinstance(batch, dict) or not isinstance(batch.get("sources"), list) or not 2 <= len(batch["sources"]) <= maximum:
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
                or full and (not isinstance(source.get("source_sha256"), str)
                    or len(source["source_sha256"]) != 64
                    or any(char not in "0123456789abcdef" for char in source["source_sha256"]))
                or source.get("character_field") not in {"text", "recognised_context"}):
            raise ValueError("global_cross_window_source_binding_invalid")
        indexed[source["source_id"]] = source
    if len({source["window_id"] for source in indexed.values()}) < 2 or sum(len(source["quote"]) for source in indexed.values()) > 40_000:
        raise ValueError("global_cross_window_distinct_windows_required")
    if full:
        groups = batch.get("pair_source_groups")
        if (not isinstance(groups, list) or len(groups) != 2
                or any(not isinstance(group, list) or not group or len(group) > FULL_BIN_SOURCES
                    or any(not isinstance(key, str) for key in group) for group in groups)):
            raise ValueError("global_cross_window_pair_groups_invalid")
        left, right = map(set, groups)
        if (any(len(group) != len(set(group)) for group in groups) or left & right
                or left | right != set(indexed)
                or type(batch.get("pair_count")) is not int
                or batch["pair_count"] != len(left) * len(right)):
            raise ValueError("global_cross_window_pair_partition_invalid")
        window_groups = [{indexed[key]["window_id"] for key in group} for group in groups]
        if (any(len(group) != 1 for group in window_groups) or window_groups[0] == window_groups[1]
                or any(sum(len(indexed[key]["quote"]) for key in group) > 20_000 for group in groups)):
            raise ValueError("global_cross_window_pair_groups_invalid")
        sha = digest({"version": FULL_VERSION, "source_sha256": indexed[groups[0][0]]["source_sha256"],
            "pair_source_groups": groups, "sources": batch["sources"]})
        if batch.get("batch_sha256") != sha or batch.get("batch_key") != "gcwb_" + sha[:32]:
            raise ValueError("global_cross_window_batch_binding_invalid")
    return indexed


def build_global_cross_window_request(*, model_id, run_id, section, batch, source_sha256, policy, settings=None):
    from .section_rules import section_instructions
    if not validate_cross_window_policy(policy): raise ValueError("global_cross_window_policy_required")
    indexed = _sources(batch)
    if batch.get("coverage_mode") == FULL_COVERAGE_MODE and policy.get("coverage_mode") != FULL_COVERAGE_MODE:
        raise ValueError("global_cross_window_full_coverage_authority_required")
    if any(source.get("source_sha256") != source_sha256 for source in indexed.values()):
        raise ValueError("global_cross_window_frozen_source_mismatch")
    payload = {"workflow_version": "extended-review-v3", "procedure": "global_cross_window",
        "global_cross_window_policy": deepcopy(policy), "source_sha256": source_sha256,
        "rules_sha256": review_bundle_digest(section), "batch_key": batch["batch_key"],
        "batch_sha256": batch["batch_sha256"], "relation": deepcopy(batch.get("relation", {})),
        "pair_source_groups": deepcopy(batch.get("pair_source_groups")),
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
        "Если заданы pair_source_groups, последовательно сравни КАЖДЫЙ источник первой группы с КАЖДЫМ "
        "источником второй группы; несколько источников могут принадлежать одному окну. "
        "Сверь объекты, марки, количества, единицы, размеры, арифметику таблиц/перечней, требования общего текста "
        "и частные сведения, которые действительно присутствуют в этих пакетах. Ищи конкретное расхождение между ними. "
        "Не объявляй отсутствие по неполному охвату. Обе стороны могут быть корректны в разных условиях; "
        "если источник не позволяет установить расхождение, не изобретай наблюдение. Никаких новых нормативных "
        "утверждений, внешних файлов, OCR, графики или экспертных решений. "
        "Для КАЖДОГО наблюдения source_evidence содержит ДОСЛОВНЫЕ quote из фактически предоставленных пакетов "
        "МИНИМУМ ДВУХ разных window_id; source_ids точно равны множеству процитированных source_id. "
        "Пустой observations допустим; это не доказывает отсутствие остальных расхождений. "
        "source_id бери только из переданных пакетов и не подменяй номером страницы или ID другого этапа. "
        "norm_queries — только поисковые запросы, не подтверждение нормы. Ответ по закрытой схеме, по-русски.\n\n" +
        section_instructions(section, "comprehensive_analysis"))
    # `HOSTS-LAYOUT-01`: the cell's answer limit and effort when the run has a stage plan; the constants otherwise.
    body = {"model": model_id, "max_tokens": limit_of(settings, 6000), "system": instruction,
        "messages": [{"role": "user", "content": canonical(payload)}], "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort_of(settings), "format": {"type": "json_schema", "schema": response_schema(source_ids=indexed)}}}
    if len(canonical(body).encode("utf-8")) > 900_000: raise ValueError("global_cross_window_request_budget")
    return ModelRequest(model_id, body,
        idempotency_scope=f"{run_id}:v3:global-cross-window:{batch['batch_key']}:{digest(body)}")


def parse_global_cross_window_reply(text, *, batch, rejected=None):
    """Keep refusals separate; a collector never makes their coverage complete."""
    indexed = _sources(batch); answer = _document(text)
    schema = response_schema()
    envelope = deepcopy(schema)
    if rejected is not None:
        envelope["properties"]["observations"]["items"] = {}
    _validate(answer, envelope)
    output = []
    for ordinal, observation in enumerate(answer["observations"]):
        try:
            _validate(observation, schema["properties"]["observations"]["items"])
            output.append(_parse_observation(observation, indexed=indexed, batch=batch))
        except ValueError as error:
            if rejected is None:
                raise
            reason = str(error)
            if not reason.startswith("global_cross_window_") or not reason.isidentifier():
                reason = "global_cross_window_record_schema_invalid"
            rejected.append({"reply_ordinal": ordinal, "reason": reason,
                "record": deepcopy(observation)})
    return output


def _parse_observation(observation, *, indexed, batch):
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
    return {**deepcopy(observation), "source_evidence": evidence_rows,
        "origin_scope": "global_cross_window", "cross_window_batch_key": batch["batch_key"],
        "window_ids": sorted(windows), "global_batch_sha256": batch["batch_sha256"]}
