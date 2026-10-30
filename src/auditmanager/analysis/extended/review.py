"""Bounded original-taxonomy machine critique and proposal-only correction.

Every selected input is accounted for. Neither a critic recommendation nor a
proposed rewrite is an expert act; original observations remain immutable.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import re
import unicodedata

from .core import ModelRequest, canonical, digest
from .original_review.normalize import normalize_finding
from .original_review.rule_filter import apply_rule_filter
from .original_review.scorer import score_finding
from .workflow import WORKFLOW_V3, review_bundle_digest

MAX_REVIEW_ITEMS = 40
MAX_SOURCE_REFS = 128
MAX_CONTEXT_CHARACTERS = 48_000
MAX_REQUEST_BYTES = 900_000
REVIEW_OUTPUT_TOKENS = 12_000
CORRECTION_OUTPUT_TOKENS = 12_000
_ASSETS = Path(__file__).parent / "original_review"
_DECISIONS = ("accept", "reject", "borderline", "needs_human", "rewrite")
_REASONS = (
    "visual_or_ocr_misread", "duplicate_or_already_covered", "wrong_norm_context",
    "acceptable_design_solution", "not_functionally_significant", "insufficient_source_context",
    "value_already_correct", "false_positive_due_to_missing_context", "requirement_not_mandatory",
    "already_resolved_by_project_note", "other",
)
_DEPENDENCIES = ("enough_source", "needs_more_context", "cross_section_required")
_ACTIONS = ("retain", "propose_revision", "needs_context")
_REJECTION_REASONS = {"value_already_correct", "already_resolved_by_project_note",
    "false_positive_due_to_missing_context", "requirement_not_mandatory",
    "visual_or_ocr_misread", "duplicate_or_already_covered", "wrong_norm_context"}
_NUMBER = re.compile(r"([+\-±−]?)\s*(\d+(?:[.,]\d+)*)")
_IDENTIFIER = re.compile(r"(?<!\w)(?=[\w./-]*\d)(?=[\w./-]*[A-Za-zА-Яа-яЁё])[\w]+(?:[./-][\w]+)*")


def _object(**properties):
    return {"type": "object", "additionalProperties": False,
            "required": list(properties), "properties": properties}


def _text(maximum, *, empty=False):
    return {"type": "string", "minLength": 0 if empty else 1, "maxLength": maximum}


def _array(schema, *, maximum=MAX_SOURCE_REFS, minimum=0):
    return {"type": "array", "items": schema, "maxItems": maximum, "minItems": minimum}


def _evidence_schema():
    return _array(_object(source_id=_text(160), quote=_text(2000)), maximum=16)


def critic_schema():
    return _object(reviews=_array(_object(
        input_id=_text(160), source_ids=_array(_text(160), minimum=1),
        llm_decision={"type": "string", "enum": list(_DECISIONS)},
        human_taxonomy_reason={"type": "string", "enum": list(_REASONS)},
        confidence={"type": "number", "minimum": 0, "maximum": 1},
        explanation=_text(800), evidence_checked={"type": "boolean"},
        source_dependency={"type": "string", "enum": list(_DEPENDENCIES)},
        needs_correction={"type": "boolean"}, suggested_fix=_text(800, empty=True),
        source_evidence=_evidence_schema()), maximum=MAX_REVIEW_ITEMS))


def corrector_schema():
    return _object(corrections=_array(_object(
        input_id=_text(160), action={"type": "string", "enum": list(_ACTIONS)},
        source_ids=_array(_text(160), minimum=1), proposed_title=_text(200),
        proposed_description=_text(3000), proposed_source_ids=_array(_text(160), minimum=1),
        source_evidence=_evidence_schema(), explanation=_text(800),
        required_context=_array(_text(300), maximum=8)), maximum=MAX_REVIEW_ITEMS))


def _document(raw):
    if isinstance(raw, bytes):
        if len(raw) > 2_097_152:
            raise ValueError("review_reply_too_large")
        raw = raw.decode("utf-8")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 2_097_152:
        raise ValueError("review_reply_invalid")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("review_duplicate_json_key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("review_nonfinite_number")))


def _validate(value, schema):
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict) or set(value) != set(schema["required"]):
            raise ValueError("review_object_schema_invalid")
        for key, specification in schema["properties"].items():
            _validate(value[key], specification)
    elif kind == "array":
        if not isinstance(value, list) or not schema.get("minItems", 0) <= len(value) <= schema["maxItems"]:
            raise ValueError("review_array_schema_invalid")
        for item in value:
            _validate(item, schema["items"])
    elif kind == "string":
        if not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 20_000):
            raise ValueError("review_string_schema_invalid")
        if schema.get("minLength", 0) and not value.strip():
            raise ValueError("review_empty_text")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("review_boolean_schema_invalid")
    elif kind == "number":
        if type(value) not in (int, float) or not math.isfinite(value) or not schema["minimum"] <= value <= schema["maximum"]:
            raise ValueError("review_number_schema_invalid")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("review_enum_schema_invalid")


def _input_items(observations):
    if not isinstance(observations, dict) or len(observations) > MAX_REVIEW_ITEMS:
        raise ValueError("review_input_window_exceeded")
    for key, item in observations.items():
        if (not isinstance(key, str) or not key or len(key) > 160 or not isinstance(item, dict)
                or not isinstance(item.get("title"), str) or not isinstance(item.get("description"), str)
                or not 1 <= len(item["title"].strip()) <= 200 or not 1 <= len(item["description"].strip()) <= 3000):
            raise ValueError("review_input_observation_invalid")
        _refs(item.get("source_ids"))
    return observations


def _refs(values):
    if (not isinstance(values, list) or not 1 <= len(values) <= MAX_SOURCE_REFS
            or any(not isinstance(value, str) or not value or len(value) > 160 for value in values)
            or len(set(values)) != len(values)):
        raise ValueError("review_source_refs_invalid")
    return set(values)


def _source_index(sources, context=None):
    if not isinstance(sources, list) or len(sources) > 512:
        raise ValueError("review_sources_invalid")
    indexed, texts = {}, {}
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            raise ValueError("review_source_shape_invalid")
        key = source["source_id"]
        if key in indexed and canonical(indexed[key]) != canonical(source):
            raise ValueError("review_source_identity_conflict")
        indexed[key] = source
        values = [source.get(field) for field in ("quote", "text", "native_text")]
        # Neighbor text is context, not a quotation from this page's source.
        for page in source.get("context", []):
            if isinstance(page, dict) and page.get("page_number") == source.get("page_number"):
                values.extend(page.get(field) for field in ("text", "native_text", "recognised_context"))
        texts[key] = [value for value in values if isinstance(value, str) and value]
    if context is not None:
        if not isinstance(context, dict):
            raise ValueError("review_context_invalid")
        for page in context.get("native_context", []):
            if not isinstance(page, dict) or page.get("source_id") not in indexed:
                raise ValueError("review_context_source_invalid")
            key = page["source_id"]
            if page.get("page_number") != indexed[key].get("page_number"):
                raise ValueError("review_context_page_mismatch")
            texts[key].extend(page[field] for field in ("text", "recognised_context")
                              if isinstance(page.get(field), str) and page[field])
    return indexed, texts


def _source_view(indexed, texts):
    budget = MAX_CONTEXT_CHARACTERS
    output, passages, shown = [], [], {}
    truncated = False
    for key in sorted(indexed):
        source = indexed[key]
        references = []
        for text in texts[key]:
            if text in shown:
                references.append(shown[text])
                continue
            fragment = text[:budget]
            budget -= len(fragment)
            cut = len(fragment) != len(text)
            truncated |= cut
            if fragment:
                identity = "review_text_" + digest({"text": fragment})[:24]
                passages.append({"text_id": identity, "text": fragment, "truncated": cut})
                shown[text] = identity
                references.append(identity)
        output.append({field: source[field] for field in
            ("source_id", "kind", "source_type", "page_number", "version_uid", "bbox_norm", "crop_sha256", "text_sha256")
            if field in source} | {"text_refs": list(dict.fromkeys(references))})
    return {"sources": output, "source_text": passages,
            "context_coverage": {"limit_characters": MAX_CONTEXT_CHARACTERS,
                "characters_provided": MAX_CONTEXT_CHARACTERS - budget, "truncated": truncated,
                "raw_images_reattached": False}}


def _original_signals(key, item, indexed):
    raw = {"id": key, "title": item["title"], "description": item["description"],
        "category": item.get("category", "unknown"), "severity": item.get("severity", "unknown"),
        "action_required": item.get("action_required"), "evidence": [
            {"block_id": source, "type": "text" if indexed[source].get("kind") == "text" else "image",
             "page": indexed[source].get("page_number")} for source in item["source_ids"]]}
    normalized = normalize_finding(raw, blocks_index=set(indexed))
    rule, explanation = apply_rule_filter(normalized)
    return {"original_offline_rule_reason": rule, "original_offline_rule_explanation": explanation,
            "original_usefulness_score": score_finding(normalized),
            "structural_evidence_quality": normalized.evidence_quality,
            "semantic_source_confirmation": False}


def _normative_view(observations):
    """Deduplicate real corpus excerpts without mutating saved observations."""
    candidates, priority, references = {}, [], {}
    for key, item in observations.items():
        rows = item.get("norm_candidates", [])
        references[key] = []
        for row in rows:
            paragraph = row["paragraph_id"]
            if paragraph in candidates and canonical(candidates[paragraph]) != canonical(row):
                raise ValueError("review_normative_identity_conflict")
            candidates[paragraph] = row
            references[key].append({field: row[field] for field in
                ("paragraph_id", "designation", "clause_number") if field in row})
        assessment = item.get("norm_assessment")
        if isinstance(assessment, dict):
            priority.extend(citation["paragraph_id"] for citation in assessment.get("citations", []))
    budget, supplied, omitted = MAX_CONTEXT_CHARACTERS, [], []
    for paragraph in dict.fromkeys([*priority, *candidates]):
        if paragraph not in candidates:
            raise ValueError("review_normative_citation_unavailable")
        row = candidates[paragraph]
        size = len(canonical(row))
        if size > budget:
            omitted.append(paragraph)
            continue
        supplied.append(deepcopy(row))
        budget -= size
    return references, supplied, {"limit_characters": MAX_CONTEXT_CHARACTERS,
        "characters_provided": MAX_CONTEXT_CHARACTERS - budget,
        "truncated": bool(omitted), "omitted_paragraph_ids": omitted}


def _request(*, model_id, run_id, section, observations, sources, window_id, context,
             phase, schema, instruction, critiques=None):
    from .section_rules import section_instructions
    selected = _input_items(observations)
    indexed, texts = _source_index(sources, context)
    if any(_refs(item["source_ids"]) - set(indexed) for item in selected.values()):
        raise ValueError("review_input_source_unavailable")
    if not isinstance(window_id, str) or not window_id or len(window_id) > 128:
        raise ValueError("review_window_identity_invalid")
    payload = _source_view(indexed, texts)
    norm_references, norm_context, norm_coverage = _normative_view(selected)
    payload.update(workflow_version=WORKFLOW_V3, window_id=window_id,
        rules_sha256=review_bundle_digest(section), procedure=phase,
        norm_context=norm_context, norm_context_coverage=norm_coverage,
        observations=[{"input_id": key, "observation_id": item.get("observation_id", key),
            "title": item["title"], "description": item["description"], "source_ids": list(item["source_ids"]),
            "norm_status": item.get("norm_status", "unavailable"), "norm_assessment": item.get("norm_assessment"),
            "norm_candidates": norm_references[key],
            "deterministic_signals": _original_signals(key, item, indexed)} for key, item in selected.items()])
    if critiques is not None:
        payload["critiques"] = deepcopy(critiques)
    taxonomy = (_ASSETS / "prompts/human_taxonomy.ru.md").read_text(encoding="utf-8")
    quality = (_ASSETS / "prompts/quality_criteria.md").read_text(encoding="utf-8")
    system = (taxonomy + "\n\n" + quality + "\n\n" + section_instructions(section, phase) +
        "\n\nАДАПТАЦИЯ ТЕКУЩЕГО ЭТАПА. Следующие правила и закрытая JSON-схема определяют ответ. "
        "Это машинное предварительное мнение, НЕ решение эксперта. Нельзя удалять или скрывать исходные наблюдения, "
        "менять экспертные решения либо утверждать доказанное нарушение/актуальность нормы. "
        "Исходные файлы, инструменты и внешние каталоги недоступны. Структурная оценка исходного Python-критика "
        "не подтверждает инженерный факт. Изображения здесь повторно не приложены: оценивай только реально "
        "переданные текстовые контексты, нормативную сверку и результат предыдущего визуального прохода. "
        "Полные нормативные кандидаты переданы один раз в norm_context; ссылки наблюдений сами по себе "
        "не являются текстом нормы. Учитывай norm_context_coverage и пропущенные параграфы. "
        "Не выдумывай прочитанные пиксели или цитаты. При недостатке данных отметь потребность в контексте. " + instruction)
    body = {"model": model_id, "max_tokens": REVIEW_OUTPUT_TOKENS if phase == "finding_review" else CORRECTION_OUTPUT_TOKENS,
        "system": system, "messages": [{"role": "user", "content": canonical(payload)}],
        "thinking": {"type": "adaptive"}, "output_config": {"effort": "high",
            "format": {"type": "json_schema", "schema": schema}}}
    if len(canonical(body).encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ValueError("review_request_window_too_large")
    return ModelRequest(model_id, body,
        idempotency_scope=f"{run_id}:v3:{window_id}:{phase}:{digest(body)}")


def build_critic_request(*, model_id, run_id, section, observations, sources, window_id, context=None):
    if not _input_items(observations):
        return None
    return _request(model_id=model_id, run_id=run_id, section=section, observations=observations,
        sources=sources, window_id=window_id, context=context, phase="finding_review", schema=critic_schema(),
        instruction=("Верни объект reviews: ровно одна запись для КАЖДОГО input_id, без добавлений и пропусков. "
            "source_ids повторяют полный исходный набор. llm_decision — только совет модели. Для reject нужны "
            "confidence>=0.75, enough_source, evidence_checked=true и конкретные source_evidence с ДОСЛОВНЫМИ "
            "цитатами именно указанного source_id. Без достаточного источника только needs_human/borderline. "
            "source_evidence не цитируют чужую страницу через контекст соседа. wrong_norm_context или "
            "requirement_not_mandatory допустимы как уверенная причина лишь при реально переданной нормативной "
            "сверке; иначе needs_human. Для нужного уточнения поставь needs_correction=true и заполни "
            "suggested_fix. rewrite требует needs_correction=true; accept не требует исправления. "
            "Не пиши исправленное наблюдение сейчас: оно относится к отдельному targeted corrector."))


def _quote_refs(values, *, allowed, texts):
    _validate(values, _evidence_schema())
    seen = set()
    for value in values:
        key, quote = value["source_id"], value["quote"]
        if key not in allowed or key not in texts or not any(quote in text for text in texts[key]):
            raise ValueError("review_quote_not_in_source")
        if (key, quote) in seen:
            raise ValueError("review_duplicate_evidence")
        seen.add((key, quote))


def parse_critic_reply(text, *, observations, sources, allowed_sources=None, context=None):
    expected = _input_items(observations)
    indexed, texts = _source_index(sources, context)
    allowed = set(indexed) if allowed_sources is None else set(allowed_sources) & set(indexed)
    value = _document(text)
    _validate(value, critic_schema())
    result, seen = [], set()
    for row in value["reviews"]:
        key = row["input_id"]
        if key not in expected or key in seen:
            raise ValueError("critic_input_partition_invalid")
        original = expected[key]
        refs = _refs(row["source_ids"])
        if refs != _refs(original["source_ids"]) or not refs <= allowed:
            raise ValueError("critic_source_binding_invalid")
        _quote_refs(row["source_evidence"], allowed=refs, texts=texts)
        decision, dependency = row["llm_decision"], row["source_dependency"]
        if dependency != "enough_source" and decision not in {"borderline", "needs_human"}:
            raise ValueError("critic_insufficient_source_decision")
        if decision == "reject" and (row["confidence"] < .75 or not row["evidence_checked"] or not row["source_evidence"]):
            raise ValueError("critic_rejection_without_evidence")
        if (dependency == "enough_source" and row["human_taxonomy_reason"] in _REJECTION_REASONS
                and decision != "reject"):
            raise ValueError("critic_reason_decision_inconsistent")
        if row["human_taxonomy_reason"] == "insufficient_source_context" and decision != "needs_human":
            raise ValueError("critic_context_reason_inconsistent")
        if (row["human_taxonomy_reason"] == "not_functionally_significant" and decision == "reject"
                and row["confidence"] < .80):
            raise ValueError("critic_significance_confidence_insufficient")
        if row["human_taxonomy_reason"] in {"wrong_norm_context", "requirement_not_mandatory"} and decision == "reject":
            if not original.get("norm_candidates") or not original.get("norm_assessment"):
                raise ValueError("critic_normative_context_unavailable")
        if ((decision == "rewrite" and not row["needs_correction"])
                or decision == "accept" and row["needs_correction"]
                or row["needs_correction"] and not row["suggested_fix"].strip()):
            raise ValueError("critic_correction_intent_invalid")
        result.append(deepcopy(row) | {"observation_id": original.get("observation_id", key),
            "status": "requires_expert_review", "expert_decision": False})
        seen.add(key)
    if seen != set(expected):
        raise ValueError("critic_input_partition_invalid")
    return result


def _targets(observations, critiques):
    expected = _input_items(observations)
    if not isinstance(critiques, list):
        raise ValueError("corrector_reviews_invalid")
    found, targets = set(), {}
    for row in critiques:
        if not isinstance(row, dict) or row.get("input_id") not in expected or row["input_id"] in found:
            raise ValueError("corrector_review_partition_invalid")
        key = row["input_id"]
        if _refs(row.get("source_ids")) != _refs(expected[key]["source_ids"]):
            raise ValueError("corrector_review_source_binding_invalid")
        if type(row.get("needs_correction")) is not bool:
            raise ValueError("corrector_review_intent_invalid")
        if row["needs_correction"]:
            targets[key] = expected[key]
        found.add(key)
    if found != set(expected):
        raise ValueError("corrector_review_partition_invalid")
    return targets


def build_corrector_request(*, model_id, run_id, section, observations, critiques, sources, window_id, context=None):
    targets = _targets(observations, critiques)
    if not targets:
        return None
    selected = [row for row in critiques if row["input_id"] in targets]
    return _request(model_id=model_id, run_id=run_id, section=section, observations=targets,
        sources=sources, window_id=window_id, context=context, phase="finding_correction",
        schema=corrector_schema(), critiques=selected,
        instruction=("Верни объект corrections: ровно одна запись для каждого переданного input_id, без новых наблюдений. "
            "Следуй консервативному corrector исходного проекта: НИЧЕГО НЕ УДАЛЯТЬ, исходные данные сохранить. "
            "source_ids повторяют исходный набор. action=retain или needs_context сохраняют proposed_title/description "
            "и proposed_source_ids точно равными исходным; укажи недостающие источники в required_context. "
            "action=propose_revision предлагает отдельный новый вариант, не применяя его: только реально известные "
            "proposed_source_ids и ДОСЛОВНЫЕ source_evidence этих источников. Не добавляй чисел, марок и нормативных "
            "утверждений, которых нет в переданных источниках; не выводи физическую замену объекта из одной смены подписи. "
            "Если доказательств для безопасного исправления нет, выбери needs_context, не выдумывай исправление. "
            "Никакого одобрения/отклонения эксперта, изменения важности или подтверждения действующей нормы."))


def _numbers(value):
    normalized = unicodedata.normalize("NFKC", value)
    # Keep complete decimals and their sign, including signs next to words or
    # range endpoints. These are conservative lexical guards, not arithmetic.
    return {sign + number for sign, number in _NUMBER.findall(normalized)}


def _identifiers(value):
    return set(_IDENTIFIER.findall(unicodedata.normalize("NFKC", value).casefold()))


def parse_corrector_reply(text, *, observations, critiques, sources, allowed_sources=None, context=None):
    targets = _targets(observations, critiques)
    indexed, texts = _source_index(sources, context)
    allowed = set(indexed) if allowed_sources is None else set(allowed_sources) & set(indexed)
    value = _document(text)
    _validate(value, corrector_schema())
    result, seen = [], set()
    for row in value["corrections"]:
        key = row["input_id"]
        if key not in targets or key in seen:
            raise ValueError("corrector_input_partition_invalid")
        original = targets[key]
        if _refs(row["source_ids"]) != _refs(original["source_ids"]):
            raise ValueError("corrector_original_binding_invalid")
        proposed_refs = _refs(row["proposed_source_ids"])
        if not proposed_refs <= allowed:
            raise ValueError("corrector_proposed_source_unavailable")
        _quote_refs(row["source_evidence"], allowed=proposed_refs, texts=texts)
        candidate = None
        if row["action"] == "propose_revision":
            if not row["source_evidence"]:
                raise ValueError("corrector_proposal_without_evidence")
            supplied = "\n".join(entry["quote"] for entry in row["source_evidence"])
            normative = []
            assessment = original.get("norm_assessment")
            candidates = {entry["paragraph_id"]: entry for entry in original.get("norm_candidates", [])}
            if isinstance(assessment, dict):
                for citation in assessment.get("citations", []):
                    actual = candidates.get(citation.get("paragraph_id"))
                    if actual is None or citation.get("quote") != actual.get("quote"):
                        raise ValueError("corrector_original_norm_binding_invalid")
                    normative.append(deepcopy(citation))
                    supplied += "\n" + " ".join(str(actual.get(field, "")) for field in
                        ("designation", "clause_number", "quote"))
            proposed_text = row["proposed_title"] + "\n" + row["proposed_description"]
            if not _numbers(proposed_text) <= _numbers(supplied):
                raise ValueError("corrector_proposal_invents_number")
            if not _identifiers(proposed_text) <= _identifiers(supplied):
                raise ValueError("corrector_proposal_invents_identifier")
            candidate = {"title": row["proposed_title"], "description": row["proposed_description"],
                "source_ids": list(row["proposed_source_ids"]), "source_evidence": deepcopy(row["source_evidence"]),
                "norm_evidence": normative,
                "status": "proposed_requires_expert_review"}
        elif (row["proposed_title"] != original["title"] or row["proposed_description"] != original["description"]
                or proposed_refs != _refs(original["source_ids"])):
            raise ValueError("corrector_nonproposal_changed_original")
        result.append({"input_id": key, "observation_id": original.get("observation_id", key),
            "original": deepcopy(original), "candidate": candidate, "action": row["action"],
            "source_ids": list(original["source_ids"]), "reason": row["explanation"],
            "required_context": list(row["required_context"]), "status": "requires_expert_review",
            "expert_decision": False})
        seen.add(key)
    if seen != set(targets):
        raise ValueError("corrector_input_partition_invalid")
    return result
