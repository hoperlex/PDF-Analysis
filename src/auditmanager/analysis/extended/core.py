"""Bounded preliminary multimodal review, separate from canonical text findings.

Source method: PDF-proverka3c994817 block_analysis/context/merge workflow;
implemented against local immutable artifacts, without importing its runner.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from auditmanager.analysis.geometry.crop_cohort import prepare_image_crop_cohort
from auditmanager.analysis.text.adapter import ModelRequest

PLAN_VERSION = "extended-review-v1"
PLAN_VERSION_V2 = "extended-review-v2"
PLAN_VERSION_V3 = "extended-review-v3"
RESULT_ROLE = "analysis.extended_review"
REPLY_ROLE = "analysis.extended_reply"
MAX_BLOCKS = 16
FULL_DOCUMENT = "all"
BATCH_SIZE = 8
MAX_ITEMS = 40


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def enabled(policy: object) -> bool:
    if not isinstance(policy, dict) or policy.get("enabled") is not True:
        return False
    if policy.get("plan_version") == PLAN_VERSION_V3:
        from .coverage import validate_coverage_policy, validate_cross_window_policy
        try:
            validate_coverage_policy(policy)
            if "global_cross_window_policy" in policy:
                if (not validate_cross_window_policy(policy["global_cross_window_policy"])
                        or policy.get("coverage_version") != "batched-v1"
                        or type(policy.get("text_page_limit")) is not int or policy["text_page_limit"] <= 16):
                    return False
        except ValueError:
            return False
        maximum=policy.get("max_blocks");windows=policy.get("max_windows");rules=policy.get("rules_sha256")
        text_pages=policy.get("text_page_limit")
        return (type(maximum) is int and 1 <= maximum <= 2**31 - 1 and policy.get("window_size") == 16
            and type(policy.get("window_size")) is int and type(windows) is int and windows >= 1
            and type(text_pages) is int and 1 <= text_pages <= 2**31 - 1
            and windows == max((maximum+15)//16,(text_pages+15)//16) and policy.get("review") is True
            and isinstance(policy.get("section_code"),str) and bool(policy["section_code"].strip())
            and isinstance(rules,str) and len(rules)==64 and all(c in "0123456789abcdef" for c in rules))
    if "global_cross_window_policy" in policy:
        return False
    if policy.get("plan_version") == PLAN_VERSION:
        return type(policy.get("max_blocks")) is int and policy["max_blocks"] == MAX_BLOCKS
    return (policy.get("plan_version") == PLAN_VERSION_V2
            and (type(policy.get("max_blocks")) is int and policy["max_blocks"] == MAX_BLOCKS
                 or policy.get("max_blocks") == FULL_DOCUMENT))


def plan_inputs(*, version_uid: str, section: str, portal: Mapping[str, Any], manifest: Mapping[str, Any],
                text_layer: Mapping[str, Any], graph: Mapping[str, Any], observations: Mapping[str, Any] | None,
                recognised: Mapping[str, Any] | None = None,
                native_sources: Mapping[str, Any] | None = None, plan_version: str = PLAN_VERSION,
                source_offset: int = 0, source_limit: int = 16, max_sources: int = 16,
                full_document: bool = False, coverage_version: str | None = None) -> dict:
    if plan_version not in {PLAN_VERSION, PLAN_VERSION_V2, PLAN_VERSION_V3}:
        raise ValueError("extended_plan_version_invalid")
    if type(full_document) is not bool or full_document and plan_version != PLAN_VERSION_V2:
        raise ValueError("extended_full_document_policy_invalid")
    if coverage_version is not None and (coverage_version != "batched-v1" or plan_version != PLAN_VERSION_V3):
        raise ValueError("extended_coverage_version_invalid")
    complete_text = full_document or coverage_version == "batched-v1"
    if plan_version == PLAN_VERSION_V3 and (type(source_offset) is not int or source_offset < 0
            or type(source_limit) is not int or not 1 <= source_limit <= 16
            or type(max_sources) is not int or max_sources < 1 or source_offset >= max_sources):
        raise ValueError("extended_source_window_invalid")
    if native_sources is not None and plan_version not in {PLAN_VERSION_V2, PLAN_VERSION_V3}:
        raise ValueError("native_sources_require_v2")
    if native_sources is None:
        cohort = prepare_image_crop_cohort(version_uid=version_uid,
            portal_blocks_document=portal, crop_manifest_document=manifest)
        ordered = sorted(cohort.crops, key=lambda c: (c.page_number, c.portal_block_id))
        selected = (ordered[source_offset:min(source_offset+source_limit,max_sources)]
            if plan_version == PLAN_VERSION_V3 else ordered if full_document else ordered[:MAX_BLOCKS])
    else:
        selected = list(native_sources["sources"])
        if (not full_document and len(selected) > MAX_BLOCKS
                or any(source.get("kind") != "image" for source in selected)):
            raise ValueError("native_sources_window_invalid")
    pages = {p["page_number"]: p.get("text", "") for p in text_layer.get("pages", [])}
    ocr: dict[int, list[str]] = {}
    for item in (recognised or {}).get("entries", []):
        if item.get("kind") == "recognised_text":
            ocr.setdefault(item["page_number"], []).append(str(item.get("text", "")))
    sources = []
    for crop in selected:
        number = crop.page_number if native_sources is None else crop["page_number"]
        neighbors = [{"page_number": n, "text": str(pages[n])[:6000],
                      "recognised_context": "\n".join(ocr.get(n, []))[:4000],
                      "context_truncated": len(str(pages[n])) > 6000 or len("\n".join(ocr.get(n, []))) > 4000}
                     for n in (number-1, number, number+1) if n in pages]
        if native_sources is not None:
            sources.append(dict(deepcopy(crop), context=neighbors))
            continue
        sources.append({"source_id": crop.portal_block_id, "kind": "image", "page_number": number,
            "bbox_norm": list(crop.bbox_norm), "crop_sha256": crop.blob.sha256,
            "blob_id": crop.blob.blob_id, "size_bytes": crop.blob.size_bytes,
            "context": neighbors})
    text_items = []
    text_observations = (observations or {}).get("observations", [])
    for i, item in enumerate(text_observations if complete_text else text_observations[:MAX_ITEMS]):
        evidence = item.get("evidence", [])
        if not evidence:
            continue
        primary_key=(digest({"index":item.get("_extended_primary_index",i),
            "observation":{k:v for k,v in item.items() if k!="_extended_primary_index"}})[:24]
            if plan_version==PLAN_VERSION_V3 else None)
        source_id = "primary_text_"+primary_key if plan_version==PLAN_VERSION_V3 else f"text:{i}"
        proposed_quote=str(evidence[0].get("quote", ""))[:2000]
        page_number=evidence[0]["page_number"]
        verified_quote=(proposed_quote if proposed_quote and proposed_quote in str(pages.get(page_number,"")) else "")
        sources.append({"source_id": source_id, "kind": "text",
            "page_number":page_number,"quote":verified_quote if plan_version==PLAN_VERSION_V3 else proposed_quote,
            **({"source_type":"primary_text_proposal","quote_source":"native" if verified_quote else "unverified_proposal"}
                if plan_version==PLAN_VERSION_V3 else {})})
        text_items.append({"title": str(item.get("category", "Текстовое наблюдение"))[:200],
            "description": str(item.get("finding_text", ""))[:3000], "source_ids": [source_id], "norm_queries": [],
            **({"primary_observation_key":primary_key,
                "original_primary_observation":{k:v for k,v in item.items() if k!="_extended_primary_index"}}
                if plan_version==PLAN_VERSION_V3 else {})})
    if native_sources is None:
        skipped = [{"block_id": c.portal_block_id, "page_number": c.page_number, "reason": c.reason} for c in cohort.skipped]
        if not full_document:
            skipped.extend({"block_id": c.portal_block_id, "page_number": c.page_number, "reason": "outside_approved_window"}
                           for c in ordered[max_sources if plan_version == PLAN_VERSION_V3 else MAX_BLOCKS:])
        total = len(ordered) + len(cohort.skipped)
    else:
        skipped = deepcopy(native_sources.get("coverage", {}).get("skipped", []))
        total = native_sources.get("coverage", {}).get("blocks_total", len(selected))
        if type(total) is not int or total < len(selected):
            raise ValueError("native_sources_coverage_invalid")
    result = {"format": plan_version, "preliminary": True, "version_uid": version_uid, "section": section,
        "sources": sources, "observations": [], "warnings": [],
        "coverage": {"blocks_total": total, "blocks_selected": len(selected),
            "blocks_processed": 0, "blocks_remaining": total, "skipped": skipped},
        "context_sections": [{"title": str(s.get("title", ""))[:160]} for s in graph.get("sections", [])[:30]],
        "text_items": text_items}
    if full_document:
        result["review_scope"] = "full_document"
    result["source_sha256"] = digest({"version_uid": version_uid, "section": section,
        "portal": portal, "manifest": manifest, "text_layer": text_layer, "graph": graph, "text_observations": observations,
        "recognised": recognised})
    if plan_version == PLAN_VERSION_V2:
        from .workflow import workflow_procedures
        result.update(workflow_version=PLAN_VERSION_V2, procedures=workflow_procedures())
        result["source_sha256"] = digest({"base": result["source_sha256"], "workflow_version": plan_version,
            "native_sources_sha256": None if native_sources is None else native_sources["source_sha256"],
            "native_source_facts": None if native_sources is None else
                {"sources": native_sources["sources"], "coverage": native_sources.get("coverage", {})}} |
            ({"full_document": True} if full_document else {}))
    if plan_version == PLAN_VERSION_V3:
        result["workflow_version"] = PLAN_VERSION_V3
        result["review_scope"] = "full_document"
        result["source_window"] = {"offset":source_offset,"limit":source_limit,"max_sources":max_sources,
            "source_total":total,"source_selected_total":min(max_sources,len(ordered)) if native_sources is None else min(max_sources,total)}
        result["source_sha256"] = digest({"base":result["source_sha256"],"workflow_version":plan_version,
            "native_sources_sha256":None if native_sources is None else native_sources["source_sha256"],
            "window":result["source_window"],"sources":sources})
    if (native_sources is None and not full_document and len(ordered) > (max_sources if plan_version==PLAN_VERSION_V3 else MAX_BLOCKS)
            or native_sources is not None and total > (max_sources if plan_version==PLAN_VERSION_V3 else len(selected))):
        result["warnings"].append("remaining_blocks_not_reviewed")
    if native_sources is None and cohort.skipped:
        result["warnings"].append("geometry_blocks_not_available")
    if native_sources is not None:
        result["warnings"].extend(native_sources.get("warnings", []))
    if not complete_text and len(text_observations) > MAX_ITEMS:
        result["warnings"].append("text_observations_outside_merge_window")
    if any(n["context_truncated"] for s in sources for n in s.get("context", [])):
        result["warnings"].append("page_context_truncated")
    return result


def response_schema(*, merge: bool = False) -> dict:
    schema = {"type": "object", "additionalProperties": False, "required": ["observations"],
        "properties": {"observations": {"type": "array", "maxItems": MAX_ITEMS,
            "items": {"type": "object", "additionalProperties": False,
                "required": ["title", "description", "source_ids", "norm_queries"],
                "properties": {"title": {"type": "string", "maxLength": 200},
                    "description": {"type": "string", "maxLength": 3000},
                    "source_ids": {"type": "array", "minItems": 1, "maxItems": 16, "items": {"type": "string"}},
                    "norm_queries": {"type": "array", "maxItems": 2, "items": {"type": "string", "maxLength": 160}}}}}}}
    if merge:
        item = schema["properties"]["observations"]["items"]
        item["required"].extend(["input_ids", "norm_assessment"])
        item["properties"]["input_ids"] = {"type": "array", "minItems": 1, "maxItems": 120, "items": {"type": "string"}}
        item["properties"]["norm_assessment"] = {"anyOf": [{"type": "null"}, {
            "type": "object", "additionalProperties": False,
            "required": ["relation", "explanation", "citations"], "properties": {
                "relation": {"type": "string", "enum": ["supports", "contradicts", "insufficient"]},
                "explanation": {"type": "string", "minLength": 1, "maxLength": 1000},
                "citations": {"type": "array", "minItems": 1, "maxItems": 6, "items": {
                    "type": "object", "additionalProperties": False, "required": ["paragraph_id", "quote"],
                    "properties": {"paragraph_id": {"type": "string"},
                        "quote": {"type": "string", "minLength": 1, "maxLength": 2000}}}}}}]}
    return schema


def build_request(*, model_id: str, run_id: str, phase: str, section: str, payload: dict) -> ModelRequest:
    instruction = ("Исследуй приложенные изображения блоков чертежей вместе с текстом их страниц и соседей. "
        "Найди конкретные внутренние расхождения, технические неясности и позиции для экспертной сверки. "
        "Картинка является источником: не выдумывай native цитату или текстовые координаты. "
        if phase == "blocks" else
        "Выполни семантический свод текстовых и визуальных наблюдений: объединяй только одну и ту же проблему, "
        "сохраняй все её source_ids и перечисляй input_ids исходных наблюдений. Каждое исходное input_id должно "
        "войти хотя бы в одно выходное наблюдение. Не объединяй разные объекты и не добавляй новых фактов. "
        "Сверь каждое наблюдение с переданными norm_candidate_ids именно его input_ids и цитатами из norm_context. norm_assessment.relation "
        "означает: supports — цитата предварительно поддерживает описанное замечание; contradicts — цитата "
        "противоречит замечанию; insufficient — цитаты недостаточно для вывода. Дай короткое объяснение и "
        "citations с реальными paragraph_id и ДОСЛОВНО ПОЛНОЙ переданной quote, без исправлений. "
        "При отсутствии кандидатов norm_assessment=null. Это модельная сверка по цитате, а не правовой вывод, "
        "не проверка действующей редакции и не подтверждение применимости нормы. ")
    norm_instruction = ("Ссылки на норму предложи лишь как поисковые norm_queries. " if phase == "blocks" else
        "Используй только реальные абзацы norm_context; новых norm_queries не предлагай, верни пустой список. ")
    system = (f"Ты инженер предварительного обзора раздела {section}. " + instruction +
        "Это предварительные наблюдения, не экспертный вердикт и не доказанное нарушение нормы. "
        "Используй только перечисленные source_id. " + norm_instruction +
        "Не утверждай актуальность или обязательность. Ответ по-русски, объект observations по схеме. "
        "Если источник не позволяет проверить вопрос, опиши неопределённость; не объявляй отсутствие детали по одному фрагменту.")
    body = {"model": model_id, "max_tokens": 6000, "system": system,
        "messages": [{"role": "user", "content": canonical(payload)}],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": response_schema(merge=phase == "merge")}}}
    return ModelRequest(model_id, body, idempotency_scope=f"{run_id}:{phase}:{digest(payload)}")


def parse_reply(text: str, *, allowed_sources: set[str], expected_inputs: dict[str, dict] | None = None) -> list[dict]:
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("duplicate_key")
            result[k] = v
        return result
    value = json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    if not isinstance(value, dict) or set(value) != {"observations"} or not isinstance(value["observations"], list) or len(value["observations"]) > MAX_ITEMS:
        raise ValueError("reply_shape_invalid")
    items = []
    for item in value["observations"]:
        keys = {"title", "description", "source_ids", "norm_queries"}
        if expected_inputs is not None:
            keys.update({"input_ids", "norm_assessment"})
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("observation_shape_invalid")
        if (not isinstance(item["title"], str) or not 1 <= len(item["title"].strip()) <= 200
                or not isinstance(item["description"], str) or not 1 <= len(item["description"].strip()) <= 3000
                or not isinstance(item["source_ids"], list) or not 1 <= len(item["source_ids"]) <= 16
                or any(not isinstance(x, str) or x not in allowed_sources for x in item["source_ids"])
                or len(set(item["source_ids"])) != len(item["source_ids"])
                or not isinstance(item["norm_queries"], list) or len(item["norm_queries"]) > 2
                or any(not isinstance(x, str) or not 1 <= len(x.strip()) <= 160 for x in item["norm_queries"])):
            raise ValueError("observation_sources_or_limits_invalid")
        if expected_inputs is not None:
            ids = item["input_ids"]
            if (not isinstance(ids, list) or not 1 <= len(ids) <= 120
                    or any(not isinstance(k, str) or k not in expected_inputs for k in ids)
                    or len(set(ids)) != len(ids)
                    or set(item["source_ids"]) != {s for k in ids for s in expected_inputs[k]["source_ids"]}):
                raise ValueError("merge_input_binding_invalid")
            candidates = {c["paragraph_id"]: c for key in ids for c in expected_inputs[key].get("norm_candidates", [])}
            assessment = item["norm_assessment"]
            if not candidates:
                if assessment is not None:
                    raise ValueError("norm_assessment_without_corpus")
            else:
                if (not isinstance(assessment, dict) or set(assessment) != {"relation", "explanation", "citations"}
                        or not isinstance(assessment["relation"], str)
                        or assessment["relation"] not in {"supports", "contradicts", "insufficient"}
                        or not isinstance(assessment["explanation"], str)
                        or not 1 <= len(assessment["explanation"].strip()) <= 1000
                        or not isinstance(assessment["citations"], list) or not 1 <= len(assessment["citations"]) <= 6):
                    raise ValueError("norm_assessment_invalid")
                seen = set()
                for citation in assessment["citations"]:
                    if (not isinstance(citation, dict) or set(citation) != {"paragraph_id", "quote"}
                            or not isinstance(citation["paragraph_id"], str)
                            or citation["paragraph_id"] not in candidates or citation["paragraph_id"] in seen
                            or citation["quote"] != candidates[citation["paragraph_id"]]["quote"]):
                        raise ValueError("norm_citation_not_in_context")
                    seen.add(citation["paragraph_id"])
        items.append(dict(item))
    return items


def finalize_items(items: list[dict], sources: list[dict]) -> list[dict]:
    by_id = {s["source_id"]: s for s in sources}
    output = []
    for item in items:
        kinds = {by_id[s]["kind"] for s in item["source_ids"]}
        output.append({**item, "observation_id": "xobs_"+digest(item)[:24],
            "source_kind": next(iter(kinds)) if len(kinds) == 1 else "mixed",
            "status": "requires_expert_review", "norm_status": item.get("norm_status", "unavailable"),
            "norm_candidates": item.get("norm_candidates", [])})
    return output


def block_payload(*, section: str, batch: list[dict], sections: list[dict], coverage: dict) -> tuple[dict, bool]:
    """One shared page context per batch, at most24k characters, with missing context explicit."""
    pages = {}
    for source in batch:
        for page in source.get("context", []):
            pages[page["page_number"]] = page
    targets = {source["page_number"] for source in batch}
    remaining = 24_000
    contexts = []
    truncated = False
    for number in sorted(pages, key=lambda n: (n not in targets, n)):
        page = pages[number]
        native = page["text"][:remaining]
        remaining -= len(native)
        recognised = page["recognised_context"][:remaining]
        remaining -= len(recognised)
        cut = bool(page["context_truncated"] or len(native) < len(page["text"]) or len(recognised) < len(page["recognised_context"]))
        truncated |= cut
        contexts.append({"page_number": number, "native_text": native,
            "recognised_context": recognised, "context_truncated": cut})
    return {"section": section, "sources": [{k:v for k,v in source.items() if k != "context"} for source in batch],
        "page_contexts": contexts, "context_sections": sections, "coverage": coverage}, truncated


def build_request_v3(*, model_id, run_id, phase, section, payload, window_id):
    """Fresh-consent visual request with the frozen section rubric; legacy requests stay byte-stable."""
    from .section_rules import section_instructions
    from .workflow import review_bundle_digest
    rubric = section_instructions(section, "block_analysis" if phase == "blocks" else phase)
    bound = {**payload,"workflow_version":PLAN_VERSION_V3,"window_id":window_id,
        "rules_sha256":review_bundle_digest(section)}
    request=build_request(model_id=model_id,run_id=run_id,phase=phase,section=section,payload=bound)
    body={**request.body,"system":request.body["system"]+"\n\n"+rubric}
    return ModelRequest(model_id,body,idempotency_scope=f"{run_id}:v3:{window_id}:{phase}:{digest(bound)}")
