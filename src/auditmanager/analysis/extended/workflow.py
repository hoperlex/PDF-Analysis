"""Four genuine preliminary procedures inside the existing durable extended artifact.

Engineering task adaptation from PDF-proverka3c994817, not its filesystem runner.
"""
from __future__ import annotations
from copy import deepcopy

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


def deterministic_lossless_merge(items):
    """Collapse exact duplicate content only; keep every original and source binding."""
    if not isinstance(items, list) or len(items) > MAX_MERGED_INPUTS:
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
