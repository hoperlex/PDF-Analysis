"""`NORM-ALL-FINDINGS-01` (B1): the norm stage model formulates search queries for findings that have none.

A flow observation whose plan is ``requires_query`` (``runs/norm_queries.plan_flow_norm_queries``) is not a finding without a normative
question: block legs return an empty ``norm_queries``, and the literal planner cannot invent one. This module is the one model call that
asks for it -- one batched request per up to :data:`MAX_PLAN_INPUTS` such observations, on the norms cell, before any word or semantic
lookup.

Per observation the model returns one record: either ``decision=search`` with one to three short Russian search queries, or
``decision=no_normative_question`` with a short reason. The record is **search text and nothing else**: it never names a paragraph, a
quote or an edition, and a query that carries a corpus identifier is refused. The reply is read per record (like
``parse_norm_review``): one bad record costs only itself, the caller accounts for an input the reply did not carry, and a reply that is
invalid as a whole raises ``ValueError``.

Pure: no I/O, no clock, no model. The caller (``runs/extended_review._plan_norm_queries_with_model``) owns the call, the one semantic repair
and the stored receipts. Hashed by ``flow_repair.flow_policy()``, so changing it needs a fresh consent.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .core import ModelRequest, _reply_document, canonical, digest, effort_of, limit_of

#: One request carries at most this many observations (the same "forty per call" the cost estimate prices).
MAX_PLAN_INPUTS = 40
MAX_QUERIES = 3
MAX_QUERY_CHARACTERS = 160
MAX_REASON_CHARACTERS = 300
DECISION_SEARCH = "search"
DECISION_NONE = "no_normative_question"

#: A corpus or request-local identifier is never search text: the model must not name a paragraph it was never given.
_IDENTIFIER = re.compile(r"(?<![\w])(?:npar|ndoc|ns|xnv|xni|xnq|xnr)_[0-9A-Za-z]+")


def plan_schema(input_ids) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["plans"],
        "properties": {"plans": {"type": "array", "maxItems": MAX_PLAN_INPUTS,
            "items": {"type": "object", "additionalProperties": False,
                "required": ["input_id", "decision", "queries", "reason"],
                "properties": {"input_id": {"type": "string", "enum": list(input_ids)},
                    "decision": {"type": "string", "enum": [DECISION_SEARCH, DECISION_NONE]},
                    "queries": {"type": "array", "maxItems": MAX_QUERIES,
                        "items": {"type": "string", "maxLength": MAX_QUERY_CHARACTERS}},
                    "reason": {"type": "string", "maxLength": MAX_REASON_CHARACTERS}}}}}}


def build_norm_query_request(*, model_id, run_id, section, payload, settings=None) -> ModelRequest:
    """One batched question for the findings that have no norm query: ``payload["observations"]`` rows carry ``input_id``, ``title``,
    ``description`` and ``source_ids``."""
    rows = payload.get("observations") if isinstance(payload, dict) else None
    if (not isinstance(rows, list) or not 1 <= len(rows) <= MAX_PLAN_INPUTS
            or any(not isinstance(row, dict) or not isinstance(row.get("input_id"), str) for row in rows)
            or len({row["input_id"] for row in rows}) != len(rows)):
        raise ValueError("norm_query_planning_window_invalid")
    system = (f"Ты выполняешь отдельный шаг нормативной сверки раздела {section}: для каждого замечания из observations "
        "определи, есть ли в нём нормативный вопрос, то есть требование нормы, стандарта или свода правил, по которому "
        "замечание можно проверить. Если есть, верни decision=search и от 1 до 3 коротких поисковых запросов по-русски для "
        "поиска в корпусе нормативных документов: назови предмет требования словами нормы, а не словами проекта; когда "
        "документ очевиден, назови его обозначением в форме «СП 16.13330» или «ГОСТ 5264-80» в начале запроса. Запросы — "
        "только текст для поиска: не придумывай номера пунктов, цитаты, редакции и идентификаторы абзацев и не выдавай "
        "запрос за найденную норму. Если замечание — внутреннее несоответствие проектных данных или вопрос без "
        "нормативной основы, верни decision=no_normative_question, пустой queries и короткую причину в reason. "
        "Верни ровно одну запись на каждый input_id, input_id копируй без изменений. Не меняй и не переписывай замечания. "
        "Ответ — объект plans по схеме, по-русски; результат предварительный, решение принимает эксперт.")
    body = {"model": model_id, "max_tokens": limit_of(settings, 12_000), "system": system,
        "messages": [{"role": "user", "content": canonical(payload)}], "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort_of(settings), "format": {"type": "json_schema",
            "schema": plan_schema(row["input_id"] for row in rows)}}}
    return ModelRequest(model_id, body, idempotency_scope=f"{run_id}:norm-queries:{digest(payload)}")


def _record(row, inputs: dict) -> dict:
    keys = {"input_id", "decision", "queries", "reason"}
    if not isinstance(row, dict) or set(row) != keys:
        raise ValueError("norm_query_record_shape_invalid")
    if not isinstance(row["input_id"], str) or row["input_id"] not in inputs:
        raise ValueError("norm_query_input_binding_invalid")
    if row["decision"] not in {DECISION_SEARCH, DECISION_NONE}:
        raise ValueError("norm_query_decision_invalid")
    reason = row["reason"]
    if not isinstance(reason, str) or len(reason) > MAX_REASON_CHARACTERS:
        raise ValueError("norm_query_reason_invalid")
    reason = " ".join(reason.split())
    queries = row["queries"]
    if not isinstance(queries, list) or any(not isinstance(query, str) for query in queries):
        raise ValueError("norm_query_queries_invalid")
    if row["decision"] == DECISION_NONE:
        if queries or not reason:
            raise ValueError("norm_query_no_question_invalid")
        return {"input_id": row["input_id"], "decision": DECISION_NONE, "queries": [], "reason": reason}
    cleaned = []
    for query in queries:
        text = " ".join(query.split())
        if not text or len(text) > MAX_QUERY_CHARACTERS or any(ord(character) < 32 for character in text):
            raise ValueError("norm_query_queries_invalid")
        if _IDENTIFIER.search(text):
            raise ValueError("norm_query_identifier_invented")
        if text.casefold() not in {kept.casefold() for kept in cleaned}:
            cleaned.append(text)
    if not 1 <= len(cleaned) <= MAX_QUERIES or len(queries) > MAX_QUERIES:
        raise ValueError("norm_query_queries_invalid")
    return {"input_id": row["input_id"], "decision": DECISION_SEARCH, "queries": cleaned, "reason": reason}


def parse_norm_queries(text, *, inputs, rejected=None) -> list[dict]:
    """The accepted records of a reply, one per input, in reply order.

    With ``rejected`` (a list) every record is judged alone: the refused ones are appended there (``reply_ordinal``, ``reason``,
    ``record``) and dropped; without it the first bad record raises. A reply that is not an object with exactly a ``plans`` list of at most
    :data:`MAX_PLAN_INPUTS` rows raises ``ValueError`` either way. A repeated ``input_id`` keeps its first record."""
    if not isinstance(inputs, dict) or not 1 <= len(inputs) <= MAX_PLAN_INPUTS:
        raise ValueError("norm_query_planning_window_invalid")
    document = _reply_document(text)
    if (not isinstance(document, dict) or set(document) != {"plans"} or not isinstance(document["plans"], list)
            or len(document["plans"]) > MAX_PLAN_INPUTS):
        raise ValueError("norm_query_reply_shape_invalid")
    accepted, seen = [], set()
    for ordinal, row in enumerate(document["plans"]):
        try:
            record = _record(row, inputs)
            if record["input_id"] in seen:
                raise ValueError("norm_query_input_binding_invalid")
        except ValueError as error:
            if rejected is None:
                raise
            rejected.append({"reply_ordinal": ordinal, "reason": str(error), "record": deepcopy(row)})
            continue
        seen.add(record["input_id"])
        accepted.append(record)
    return accepted
