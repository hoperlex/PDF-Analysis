"""Fresh authority for bounded genuine corpus context, separate from paid builders."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from auditmanager.analysis.public import extended_digest
from auditmanager.norms.public import norm_paragraph_context_digest, read_norm_paragraph_context
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "source-bound-norm-paragraph-context-v1"


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def policy():
    return {"version": VERSION, "bundle_sha256": extended_digest({
        "application": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reader": norm_paragraph_context_digest()}),
        "max_paragraphs": 12, "max_characters": 18_000, "paragraph_characters": 6000,
        "neighbor_characters": 1000, "input_tokens_per_call": 100_000}


def validate_policy(value, *, compare_bundle=True):
    if value is None:
        return False
    expected = policy()
    if not compare_bundle and isinstance(value, dict):
        expected["bundle_sha256"] = value.get("bundle_sha256")
    if (not isinstance(value, dict) or set(value) != set(expected) or value != expected
            or not isinstance(value.get("bundle_sha256"), str) or len(value["bundle_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in value["bundle_sha256"])
            or any(type(value[key]) is not int for key in expected if key not in {"version", "bundle_sha256"})):
        raise ValueError("norm_paragraph_context_changed_requires_consent")
    return True


def attach(session, request, *, observations, snapshot_id, accepted, checkpoint):
    if not validate_policy(accepted):
        raise ValueError("norm_paragraph_context_policy_required")
    body = deepcopy(dict(request.body))
    payload = json.loads(body["messages"][0]["content"])
    by_input = [{"input_id": key, "norm_candidates": deepcopy(item.get("norm_candidates", []))}
        for key, item in observations.items()]
    wanted = []
    seen = set()
    for entry in by_input:
        for candidate in entry["norm_candidates"]:
            identity = (candidate["snapshot_id"], candidate["document_id"], candidate["paragraph_id"], candidate["quote"])
            if candidate["snapshot_id"] != snapshot_id:
                raise ValueError("norm_paragraph_context_snapshot_conflict")
            if identity not in seen:
                seen.add(identity); wanted.append((identity, candidate))
    context = {"version": VERSION, "snapshot_id": snapshot_id, "paragraphs": [],
        "candidate_quote_contexts": len(wanted), "contexts_provided": 0,
        "contexts_not_provided": len(wanted), "complete_corpus_claim": False,
        "edition_applicability_verified": False, "neighbor_citations_allowed": False}
    omitted = []
    attempted = 0
    for identity, candidate in wanted:
        if attempted >= accepted["max_paragraphs"]:
            omitted.append({"paragraph_id": candidate["paragraph_id"], "reason": "paragraph_context_selection_limit"})
            continue
        attempted += 1
        checkpoint("extended_norm_paragraph_context")
        try:
            actual = read_norm_paragraph_context(session, snapshot_id=identity[0], document_id=identity[1],
                paragraph_id=identity[2], quote=identity[3], paragraph_characters=accepted["paragraph_characters"],
                neighbor_characters=accepted["neighbor_characters"])
        except DomainError as error:
            if error.code not in {ErrorCode.REQUIRED_NORM_UNAVAILABLE, ErrorCode.NOT_FOUND, ErrorCode.DEPENDENCY_UNAVAILABLE}:
                raise
            omitted.append({"paragraph_id": candidate["paragraph_id"], "reason": "paragraph_context_unavailable"})
            continue
        actual["search_quote_sha256"] = hashlib.sha256(identity[3].encode("utf-8")).hexdigest()
        proposed = {**context, "paragraphs": [*context["paragraphs"], actual],
            "contexts_provided": len(context["paragraphs"]) + 1,
            "contexts_not_provided": len(wanted) - len(context["paragraphs"]) - 1}
        if len(_encoded(proposed)) > accepted["max_characters"]:
            omitted.append({"paragraph_id": candidate["paragraph_id"], "reason": "paragraph_context_character_limit"})
            continue
        context = proposed
    if len(_encoded(context)) > accepted["max_characters"]:
        raise ValueError("norm_paragraph_context_character_limit")
    # Each original input keeps its own real search excerpt even when another
    # query hit the same paragraph at another position. No global quote wins.
    payload["norm_context"] = []
    payload["norm_context_by_input"] = by_input
    payload["norm_paragraph_context"] = context
    body["messages"][0]["content"] = _encoded(payload)
    body["system"] += ("\nНовая независимая политика контекста: цитаты norm_candidates задаются отдельно "
        "для каждого input_id в norm_context_by_input; глобальный norm_context пуст намеренно. "
        "Для citations разрешены ТОЛЬКО paragraph_id и дословная quote кандидатов соответствующего входа. "
        "norm_paragraph_context содержит настоящий ограниченный текст того же абзаца и соседей; используй "
        "для проверки оговорок, условий и применимости. Соседние абзацы и более длинный текст не создают "
        "новых разрешённых цитат. Ненадёжный текст, неполное окно, отсутствие контекста или несовпадение "
        "поисковой цитаты с абзацем требуют осторожности; при недостатке данных relation=insufficient. "
        "Дата корпуса не доказывает актуальность редакции. Это предварительная сверка, решение за экспертом.")
    context_sha = extended_digest({"by_input": by_input, "paragraph_context": context})
    receipt = {"version": VERSION, "context_sha256": context_sha, "context": context,
        "norm_context_by_input": by_input, "omitted": omitted,
        "encoded_context_characters": len(_encoded(context)), "lookup_attempts": attempted,
        "candidate_quote_contexts": len(wanted), "contexts_provided": len(context["paragraphs"]),
        "contexts_not_provided": len(wanted) - len(context["paragraphs"]),
        "provided_only": True, "edition_applicability_verified": False}
    return replace(request, body=body,
        idempotency_scope=f"{request.idempotency_scope}:norm-paragraph-context:{context_sha}"), receipt
