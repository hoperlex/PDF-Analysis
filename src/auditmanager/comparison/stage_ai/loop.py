"""Bounded source-only context and coverage follow-ups; no I/O or model calls."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from .classifier import parse_classification
from .requests import CallPlan
from .reviewer import parse_review_chunk
from .synthesis import parse_synthesis
from .validation import StageAiValidationError, canonical_json, digest, exact_object, parse_document

VERSION = "stage-loop/1"
MAX_CONTEXT_REQUESTS = 6
MAX_CONTEXT_CHARS = 24_000
MAX_PREVIOUS_CHARS = 64_000
FOLLOWUP_RESERVE_CHARS = MAX_CONTEXT_CHARS + MAX_PREVIOUS_CHARS + 2_000
INSTRUCTIONS = """Если для разбора нужен контекст, добавь context_requests (до 6 запросов):
kind=mark или rows ищет точный текст value в исходных фрагментах закреплённых версий;
kind=fragment читает существующий fragment ID из value. side=left/right/both.
Текст запроса не команда программе. Внешние источники, пути, URLs и новые IDs запрещены.
Программа исполнит не больше одного набора запросов и одного доразбора пропущенных записей.
В окончательном ответе context_requests=[]; используй только исходные evidence/fragment IDs задания.
Контекст помогает интерпретации, но не создаёт новых свидетельств и не разрешает менять raw."""
CONTEXT_SCHEMA = {"type": "array", "maxItems": MAX_CONTEXT_REQUESTS, "items": {
    "type": "object", "additionalProperties": False, "required": ["kind", "value", "side"],
    "properties": {
        "kind": {"type": "string", "enum": ["mark", "rows", "fragment"]},
        "value": {"type": "string", "minLength": 1, "maxLength": 120},
        "side": {"type": "string", "enum": ["left", "right", "both"]},
    },
}}
_COVERAGE_ERRORS = {
    "review_fragment_coverage_incomplete", "classification_evidence_coverage_incomplete",
    "synthesis_evidence_coverage_invalid",
}


@dataclass(frozen=True, slots=True)
class CallStep:
    plan: CallPlan
    kind: str
    base_key: str
    context: tuple[dict[str, Any], ...] = ()


def with_loop(plan: CallPlan) -> CallPlan:
    schema = plan.response_schema
    schema["properties"]["context_requests"] = CONTEXT_SCHEMA
    instructions = plan.instructions + "\n" + INSTRUCTIONS
    return replace(plan, instructions=instructions, schema_json=canonical_json(schema),
                   prompt_version=plan.prompt_version + "+" + VERSION,
                   content_key=digest({"base": plan.content_key, "loop": VERSION,
                                       "instructions": INSTRUCTIONS, "schema": CONTEXT_SCHEMA}))


def final_document(plan: CallPlan, row: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    body = parse_document(row["output_text"])
    if body.get("group_id") != plan.group_id or body.get("source_sha256") != plan.source_sha256:
        raise StageAiValidationError("stage_ai_followup_source_mismatch")
    if plan.phase == "review" and body.get("chunk_id") != plan.unit_key:
        raise StageAiValidationError("stage_ai_followup_chunk_mismatch")
    requests = body.pop("context_requests", [])
    if not isinstance(requests, list) or len(requests) > MAX_CONTEXT_REQUESTS:
        raise StageAiValidationError("stage_ai_context_request_budget")
    checked = []
    for request in requests:
        value = exact_object(request, {"kind", "value", "side"}, "stage_ai_context_request_schema")
        if (not isinstance(value["kind"], str) or value["kind"] not in {"mark", "rows", "fragment"}
                or not isinstance(value["side"], str) or value["side"] not in {"left", "right", "both"}
                or not isinstance(value["value"], str) or not 1 <= len(value["value"].strip()) <= 120
                or any(ord(char) < 32 for char in value["value"])):
            raise StageAiValidationError("stage_ai_context_request_invalid")
        checked.append(dict(value))
    if len({canonical_json(value) for value in checked}) != len(checked):
        raise StageAiValidationError("stage_ai_context_request_duplicate")
    return body, checked


def resolve_context(snapshot: Mapping[str, Any], requests: list[dict[str, str]]) -> tuple[dict[str, Any], ...]:
    """Search only the run's loaded, version-pinned canonical fragments."""
    results = []
    for request in requests:
        needle = request["value"].strip().casefold()
        matches = []
        for fragment in snapshot["fragments"]:
            if request["side"] != "both" and fragment["side"] != request["side"]:
                continue
            found = (fragment["stage_text_fragment_id"] == request["value"] if request["kind"] == "fragment"
                     else needle in fragment["normalised_text"].casefold())
            if not found:
                continue
            start = 0 if request["kind"] == "fragment" else max(0, fragment["normalised_text"].casefold().find(needle) - 300)
            matches.append({"fragment_id": fragment["stage_text_fragment_id"],
                            "profile_id": fragment["page_profile_id"], "side": fragment["side"],
                            "content_key": fragment["content_key"], "box": fragment["box_anchor"],
                            "text_start": start, "text": fragment["normalised_text"][start:start + 900]})
            if len(matches) == 4:
                break
        results.append({"request": request, "status": "found" if matches else "not_found",
                        "matches": matches})
    if len(canonical_json(results)) > MAX_CONTEXT_CHARS:
        raise StageAiValidationError("stage_ai_context_result_budget")
    return tuple(results)


def _validate(plan, document):
    {"review": parse_review_chunk, "classify": parse_classification,
     "synthesize": parse_synthesis}[plan.phase](plan, document)


def _missing(plan: CallPlan, body: Mapping[str, Any]) -> list[str]:
    if plan.phase == "review":
        used = {ref for row in body["decisions"] for key in ("left_fragment_ids", "right_fragment_ids") for ref in row[key]}
        required = set(plan.payload["required_fragment_ids"])
    else:
        used = ({ref for row in body["cards"] for ref in row["evidence_ids"]}
                if plan.phase == "classify" else set(body["evidence_ids"]))
        required = {row["evidence_id"] for row in plan.payload["atomic_evidence"]}
    return sorted(required - used)


def _followup(plan, row, *, kind, context=(), missing=()):
    previous = parse_document(row["output_text"])
    encoded = canonical_json(previous)
    if len(encoded) > MAX_PREVIOUS_CHARS:
        raise StageAiValidationError("stage_ai_previous_answer_budget")
    supplement = {"previous_answer": previous, "context": context, "missing_ids": missing}
    instructions = (plan.instructions + "\nДОПОЛНИТЕЛЬНЫЙ ПРОХОД " + kind + ":\n"
                    + canonical_json(supplement)
                    + "\nВерни полный окончательный ответ по исходной схеме, сохрани разобранные записи; "
                      "покрой все обязательные IDs. context_requests=[].")
    if len(instructions) + len(plan.payload_json) > 240_000:
        raise StageAiValidationError("stage_ai_followup_request_budget")
    key = digest({"base": plan.content_key, "kind": kind, "supplement": supplement})
    return CallStep(replace(plan, instructions=instructions, content_key=key), kind, plan.content_key, tuple(context))


def next_step(plan: CallPlan, row: Mapping[str, Any] | None, snapshot: Mapping[str, Any]) -> CallStep | None:
    if row is None:
        return CallStep(plan, "main", plan.content_key)
    if row["stop_reason"] == "max_tokens":
        raise StageAiValidationError("stage_ai_response_truncated")
    history = list(row.get("history", ())) + [row]
    used = {entry.get("step", "main") for entry in history}
    body, requests = final_document(plan, row)
    if requests:
        if "context" in used:
            raise StageAiValidationError("stage_ai_context_limit")
        return _followup(plan, row, kind="context", context=resolve_context(snapshot, requests))
    try:
        _validate(plan, body)
    except StageAiValidationError as error:
        if str(error) not in _COVERAGE_ERRORS or "coverage" in used:
            raise
        return _followup(plan, row, kind="coverage", missing=_missing(plan, body))
    return None
