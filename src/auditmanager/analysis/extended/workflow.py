"""Four genuine preliminary procedures inside the existing durable extended artifact.

Engineering task adaptation from PDF-proverka3c994817, not its filesystem runner.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .core import (PLAN_VERSION_V2, MAX_ITEMS, ModelRequest, canonical, digest,
                   response_schema, parse_reply)

WORKFLOW_V2 = PLAN_VERSION_V2
MAX_NATIVE_CONTEXT = 48_000
MAX_COMPREHENSIVE_INPUTS = 120
MAX_MERGED_INPUTS = 160
SOURCE_PROVENANCE = {
    "repository": "https://github.com/SU10KAZ/PDF-proverka",
    "commit": "3c99481719218b9cfa7560886529916646c61939",
    "path": "prompts/pipeline/ru/text_analysis_task.md",
    "sha256": "1d410a212f7fbe22910cabe5e300f4e1f31f2b77a660a98aeb83c7553735755e",
    "adaptation": "Arithmetic/cross-sheet/text-versus-visual checks over supplied bounded data; no file tools, absence claims or normative currency assertion.",
}


def workflow_procedures():
    return [{"id": identity, "title": title, "status": "queued"} for identity, title in (
        ("block_analysis", "Анализ блоков"),
        ("comprehensive_analysis", "Комплексная сверка"),
        ("finding_merge", "Свод наблюдений"),
        ("norm_verification", "Проверка нормативных ссылок"))]


def _native_context(payload):
    contexts = payload.get("native_context", [])
    if not isinstance(contexts, list):
        raise ValueError("comprehensive_native_context_invalid")
    budget, result, truncated = MAX_NATIVE_CONTEXT, [], False
    for context in contexts:
        if not isinstance(context, dict) or not isinstance(context.get("text"), str):
            raise ValueError("comprehensive_native_context_invalid")
        original, recognised = context["text"], context.get("recognised_context", "")
        if not isinstance(recognised, str):
            raise ValueError("comprehensive_native_context_invalid")
        text = original[:budget]
        budget -= len(text)
        ocr = recognised[:budget]
        budget -= len(ocr)
        cut = len(text) != len(original) or len(ocr) != len(recognised) or bool(context.get("context_truncated"))
        truncated |= cut
        result.append({k: v for k, v in context.items() if k not in {"text", "recognised_context"}} |
                      {"text": text, "recognised_context": ocr, "context_truncated": cut})
    return result, truncated


def build_comprehensive_request(*, model_id, run_id, section, payload):
    """Independent cross-source reasoning over actual visual results and native text."""
    if not isinstance(payload, dict):
        raise ValueError("comprehensive_payload_invalid")
    body = deepcopy(payload)
    sources = body.get("sources", [])
    if not isinstance(sources, list) or any(not isinstance(s, dict) or not s.get("source_id") for s in sources):
        raise ValueError("comprehensive_sources_invalid")
    contexts, cut = _native_context(body)
    for key in ("visual_observations", "text_observations"):
        values = body.get(key, [])
        if not isinstance(values, list) or len(values) > MAX_COMPREHENSIVE_INPUTS:
            raise ValueError("comprehensive_observation_window_exceeded")
    body["native_context"] = contexts
    body["sources"] = [{k: v for k, v in s.items() if k != "context"} for s in sources]
    body["context_coverage"] = {"characters_limit": MAX_NATIVE_CONTEXT,
        "characters_provided": sum(len(c["text"]) + len(c["recognised_context"]) for c in contexts),
        "truncated": cut, "complete_document_claim": False}
    body["workflow_version"] = WORKFLOW_V2
    body["procedure"] = "comprehensive_analysis"
    body["source_provenance"] = SOURCE_PROVENANCE
    instruction = (f"Ты выполняешь отдельную комплексную сверку раздела {section}. "
        "Вход содержит реальные visual_observations, text_observations и native_context, а не готовое экспертное решение. "
        "Выполни арифметическую сверку: пересчитай суммы строк и столбцов в переданных таблицах, "
        "проверь числа, единицы и порядки величин. Выполни перекрёстную сверку: ПЗ против таблиц, "
        "спецификация против текста, марки/количества/типоразмеры в разных местах документа. "
        "Сверь текстовые находки с конкретными результатами визуального анализа; совпадение формулировок "
        "не доказывает совпадение фактов. Для каждого нового наблюдения перечисли реальные source_ids. "
        "Используй только предоставленные данные, учитывай context_coverage и context_truncated. "
        "Это новый независимый поиск межисточниковых расхождений, а не пересказ или свод прежних замечаний. "
        "Не объявляй отсутствие элементов по неполному входу, не выдумывай цитаты, координаты, нормы "
        "или сведения каталогов. Нормативные вопросы предложи только как поисковые norm_queries. "
        "Ответ observations по схеме, по-русски; результат предварительный, решение принимает эксперт.")
    encoded = canonical(body)
    if len(encoded) > 480_000:
        raise ValueError("comprehensive_payload_too_large")
    return ModelRequest(model_id, {"model": model_id, "max_tokens": 6000, "system": instruction,
        "messages": [{"role": "user", "content": encoded}], "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": response_schema()}}},
        idempotency_scope=f"{run_id}:comprehensive:{digest(body)}")


def deterministic_lossless_merge(items, *, full_document=False):
    """Collapse exact duplicate content only; keep every original and source binding."""
    if not isinstance(items, list) or not full_document and len(items) > MAX_MERGED_INPUTS:
        raise ValueError("extended_merge_window_exceeded")
    ignored = {"source_ids", "norm_queries", "norm_candidates", "observation_id", "source_kind",
               "input_ids", "provenance", "merged_observations"}
    output, by_key = [], {}
    for original in items:
        if not isinstance(original, dict) or not isinstance(original.get("title"), str) or not isinstance(original.get("description"), str):
            raise ValueError("extended_merge_observation_invalid")
        key = canonical({k: v for k, v in original.items() if k not in ignored})
        if key not in by_key:
            item = deepcopy(original)
            output.append(item)
            by_key[key] = item
            continue
        target = by_key[key]
        if full_document and (len(set(target.get("source_ids", [])) | set(original.get("source_ids", []))) > 16
                or len(set(target.get("norm_queries", [])) | set(original.get("norm_queries", []))) > 2):
            item = deepcopy(original)
            output.append(item)
            by_key[key] = item
            continue
        target.setdefault("merged_observations", [deepcopy(target)]).append(deepcopy(original))
        for field in ("source_ids", "norm_queries", "norm_candidates", "input_ids"):
            if field not in original and field not in target:
                continue
            values = target.setdefault(field, [])
            for value in original.get(field, []):
                if value not in values:
                    values.append(deepcopy(value))
        if target.get("source_kind") != original.get("source_kind"):
            target["source_kind"] = "mixed"
    return output


def build_norm_review_request(*, model_id, run_id, section, payload):
    """Fourth bounded call: review actual corpus quotes for already merged observations."""
    from .core import build_request
    rows = payload.get("observations", [])
    if not isinstance(rows, list) or len(rows) > MAX_ITEMS:
        raise ValueError("norm_review_window_exceeded")
    request = build_request(model_id=model_id, run_id=run_id, section=section, phase="merge", payload=payload)
    body = deepcopy(request.body)
    body["max_tokens"] = 12_000
    body["system"] = (f"Ты выполняешь отдельную предварительную нормативную сверку раздела {section}. "
        "Отдельная процедура norm_verification: НЕ объединяй и НЕ переписывай наблюдения. "
        "Для каждого входного input_id верни ровно одно наблюдение с единственным соответствующим input_ids. "
        "Сохрани title, description, source_ids; оцени только реально переданные цитаты его norm_candidates. "
        "Используй norm_context и norm_candidate_ids соответствующих входов. norm_assessment.relation: "
        "supports — цитата предварительно поддерживает наблюдение; contradicts — противоречит ему; "
        "insufficient — цитата не позволяет сделать вывод. Объясни связь и приведи реальные paragraph_id "
        "и ДОСЛОВНО ПОЛНУЮ переданную quote в citations; новые нормы и цитаты запрещены. "
        "Верни пустые norm_queries. Без цитат norm_assessment=null, без подтверждения актуальности/применимости. "
        "Ответ observations по схеме по-русски. Это машинная сверка, решение принимает эксперт.")
    return ModelRequest(model_id, body, idempotency_scope=f"{run_id}:norm-review:{digest(payload)}")


def parse_norm_review(text, *, observations, allowed_sources=None):
    if not isinstance(observations, dict) or len(observations) > MAX_ITEMS:
        raise ValueError("norm_review_window_exceeded")
    allowed = {source for item in observations.values() for source in item["source_ids"]}
    parsed = parse_reply(text, allowed_sources=allowed if allowed_sources is None else allowed_sources,
                         expected_inputs=observations)
    seen = set()
    for item in parsed:
        if len(item["input_ids"]) != 1 or item["input_ids"][0] in seen or item["norm_queries"]:
            raise ValueError("norm_review_input_partition_invalid")
        key = item["input_ids"][0]
        if any(item[field] != observations[key][field] for field in ("title", "description")):
            raise ValueError("norm_review_observation_changed")
        seen.add(key)
    if seen != set(observations):
        raise ValueError("norm_review_input_partition_invalid")
    return parsed


# V3 has separate builders. Historical v1/v2 requests above retain their
# instructions, bounds, schemas and idempotency behavior.
WORKFLOW_V3 = "extended-review-v3"
REVIEW_BUNDLE_VERSION = "section-review-source-bound/1"
# Full-document v3 authority is frozen by the preflight/runtime owners. The
# admitted 1,000-image ceiling requires ceil(1,000 / 16) durable windows;
# individual comprehensive/review requests retain their existing window bounds.
MAX_WORKFLOW_WINDOWS = 2**31 - 1
MAX_GLOBAL_OBSERVATIONS = MAX_WORKFLOW_WINDOWS * MAX_MERGED_INPUTS
MAX_V3_REQUEST_BYTES = 2**63 - 1


def workflow_procedures_v3():
    return workflow_procedures() + [
        {"id": "finding_review", "title": "Критик наблюдений", "status": "queued"},
        {"id": "finding_correction", "title": "Предложения по уточнению", "status": "queued"},
        {"id": "report_generation", "title": "Формирование отчёта", "status": "queued"},
    ]


def review_bundle_digest(section):
    """Actual source/assets/rules identity frozen by fresh v3 cost consent."""
    from .section_rules import rules_digest
    root = Path(__file__).parent
    assets = {}
    for path in sorted((root / "original_review").rglob("*")):
        if path.is_file() and path.suffix in {".py", ".md", ".txt", ".json"}:
            assets[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ("core.py", "workflow.py", "review.py", "native_pages.py", "coverage.py",
                 "cross_window.py", "cross_window_review.py"):
        assets[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    return digest({"version": REVIEW_BUNDLE_VERSION, "workflow_version": WORKFLOW_V3,
                   "section": section, "section_rules": rules_digest(section), "assets": assets})


def _v3_request(request, *, run_id, section, phase, window_id=None):
    from .section_rules import section_instructions
    body = deepcopy(request.body)
    payload = json.loads(body["messages"][0]["content"])
    window = window_id or payload.get("window_id") or "window-1"
    if not isinstance(window, str) or not window or len(window) > 128:
        raise ValueError("extended_window_identity_invalid")
    payload.update(workflow_version=WORKFLOW_V3, window_id=window,
                   rules_sha256=review_bundle_digest(section))
    if payload.get("v3_input_coverage", {}).get("truncated"):
        payload.setdefault("context_coverage", {})["truncated"] = True
    body["messages"][0]["content"] = canonical(payload)
    body["system"] += "\n\n" + section_instructions(section, phase)
    if len(canonical(body).encode("utf-8")) > MAX_V3_REQUEST_BYTES:
        raise ValueError("extended_v3_request_window_too_large")
    return ModelRequest(request.model_id, body,
        idempotency_scope=f"{run_id}:v3:{window}:{phase}:{digest(body)}")


def build_comprehensive_request_v3(*, model_id, run_id, section, payload, window_id=None):
    summarized = deepcopy(payload)
    truncated_items, truncated_sources = [], []
    for field in ("visual_observations", "text_observations"):
        for ordinal, item in enumerate(summarized.get(field, [])):
            if not isinstance(item, dict):
                raise ValueError("comprehensive_observation_invalid")
            cuts = []
            for key, maximum in (("title", 200), ("description", 800)):
                value = item.get(key)
                if not isinstance(value, str):
                    raise ValueError("comprehensive_observation_invalid")
                if len(value) > maximum:
                    item[key] = value[:maximum]
                    cuts.append({"field": key, "original_characters": len(value), "provided_characters": maximum})
            if cuts:
                item["input_summary_truncated"] = True
                truncated_items.append({"field": field, "ordinal": ordinal, "cuts": cuts})
    for ordinal, source in enumerate(summarized.get("sources", [])):
        quote = source.get("quote") if isinstance(source, dict) else None
        if isinstance(quote, str) and len(quote) > 800:
            source["quote"] = quote[:800]
            source["quote_truncated"] = True
            truncated_sources.append({"source_id": source["source_id"], "original_characters": len(quote),
                                      "provided_characters": 800, "ordinal": ordinal})
    summarized["v3_input_coverage"] = {"truncated": bool(truncated_items or truncated_sources),
        "full_input_sha256": digest(payload), "truncated_observations": truncated_items,
        "truncated_source_quotes": truncated_sources, "originals_retained_by_runtime": True}
    return _v3_request(build_comprehensive_request(model_id=model_id, run_id=run_id,
        section=section, payload=summarized), run_id=run_id, section=section,
        phase="comprehensive_analysis", window_id=window_id)


def build_norm_review_request_v3(*, model_id, run_id, section, payload, window_id=None):
    return _v3_request(build_norm_review_request(model_id=model_id, run_id=run_id,
        section=section, payload=payload), run_id=run_id, section=section,
        phase="norm_verification", window_id=window_id)


def build_comprehensive_request_batched_v3(*, model_id, run_id, section, payload, window_id=None):
    """Fresh batched authority keeps complete observations and every supplied text piece."""
    if payload.get("coverage_version") != "batched-v1":
        raise ValueError("extended_batched_authority_required")
    return _v3_request(build_comprehensive_request(model_id=model_id, run_id=run_id,
        section=section, payload=payload), run_id=run_id, section=section,
        phase="comprehensive_analysis", window_id=window_id)


def deterministic_lossless_merge_v3(items, *, max_windows=MAX_WORKFLOW_WINDOWS):
    """Bounded global collection; no v2 overflow cap or hidden item dropping."""
    if type(max_windows) is not int or not 1 <= max_windows <= MAX_WORKFLOW_WINDOWS:
        raise ValueError("extended_global_window_limit_invalid")
    if not isinstance(items, list):
        raise ValueError("extended_global_observation_limit_exceeded")
    ignored = {"source_ids", "norm_queries", "norm_candidates", "observation_id", "source_kind",
               "input_ids", "provenance", "merged_observations"}
    output, by_key = [], {}
    for original in items:
        if not isinstance(original, dict) or not isinstance(original.get("title"), str) or not isinstance(original.get("description"), str):
            raise ValueError("extended_merge_observation_invalid")
        key = canonical({k: v for k, v in original.items() if k not in ignored})
        if key not in by_key:
            item = deepcopy(original)
            output.append(item)
            by_key[key] = item
            continue
        target = by_key[key]
        if "merged_observations" not in target:
            target["merged_observations"] = [deepcopy(target)]
        target["merged_observations"].append(deepcopy(original))
        for field in ("source_ids", "norm_queries", "norm_candidates", "input_ids"):
            if field not in original and field not in target:
                continue
            values = target.setdefault(field, [])
            for value in original.get(field, []):
                if value not in values:
                    values.append(deepcopy(value))
        if target.get("source_kind") != original.get("source_kind"):
            target["source_kind"] = "mixed"
    return output


def _batched_norm_schema():
    assessment = response_schema(merge=True)['properties']['observations']['items']['properties']['norm_assessment']
    return {'type': 'object', 'additionalProperties': False, 'required': ['assessments'],
        'properties': {'assessments': {'type': 'array', 'maxItems': 20, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['input_id', 'norm_assessment'],
            'properties': {'input_id': {'type': 'string', 'minLength': 1, 'maxLength': 160},
                'norm_assessment': assessment}}}}}


def build_norm_review_request_batched_v3(*, model_id, run_id, section, payload, window_id=None):
    """Fresh compact annotations avoid repeating the full original finding in every reply."""
    if payload.get('coverage_version') != 'batched-v1' or len(payload.get('observations', [])) > 20:
        raise ValueError('extended_batched_norm_authority_invalid')
    request = build_norm_review_request_v3(model_id=model_id, run_id=run_id, section=section,
        payload=payload, window_id=window_id)
    body = deepcopy(request.body)
    body['system'] += ('\nДля этой новой версии формат ответа заменён: объект assessments, ровно одна '
        'запись {input_id,norm_assessment} для каждого входа. Не возвращай title, description, source_ids '
        'или norm_queries. Исходные наблюдения остаются неизменными; только аннотация нормативной сверки. '
        'Цитируй дословно полную предоставленную quote соответствующего кандидата.')
    body['output_config']['format']['schema'] = _batched_norm_schema()
    return ModelRequest(model_id, body,
        idempotency_scope=f'{run_id}:v3:{window_id}:batched-norm:{digest(body)}')


def parse_norm_review_batched_v3(text, *, observations, allowed_sources=None):
    from .review import _document, _validate
    if not isinstance(observations, dict) or len(observations) > 20:
        raise ValueError('extended_batched_norm_window_invalid')
    result = _document(text)
    _validate(result, _batched_norm_schema())
    seen = set()
    for row in result['assessments']:
        key = row['input_id']
        if key not in observations or key in seen:
            raise ValueError('norm_review_input_partition_invalid')
        original = observations[key]
        if allowed_sources is not None and not set(original['source_ids']) <= set(allowed_sources):
            raise ValueError('norm_review_source_binding_invalid')
        candidates = {candidate['paragraph_id']: candidate for candidate in original.get('norm_candidates', [])}
        assessment = row['norm_assessment']
        if not candidates and assessment is not None or candidates and assessment is None:
            raise ValueError('norm_assessment_without_corpus')
        if assessment is not None:
            _validate(assessment, response_schema(merge=True)['properties']['observations']
                ['items']['properties']['norm_assessment']['anyOf'][1])
        citations = set()
        for citation in (assessment or {}).get('citations', []):
            paragraph = citation['paragraph_id']
            if (paragraph not in candidates or paragraph in citations
                    or citation['quote'] != candidates[paragraph]['quote']):
                raise ValueError('norm_citation_not_in_context')
            citations.add(paragraph)
        seen.add(key)
    if seen != set(observations):
        raise ValueError('norm_review_input_partition_invalid')
    return result['assessments']
