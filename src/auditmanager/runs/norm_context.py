"""Fresh authority for bounded genuine corpus context, separate from paid builders."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path

from auditmanager.analysis.public import extended_digest
from auditmanager.norms.public import norm_paragraph_context_digest, read_norm_paragraph_context
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "source-bound-norm-paragraph-context-v1"

#: `NORM-ALL-FINDINGS-01` (B4). The per-call budget of the paragraph context was 12 paragraphs / 18 000 characters: on prod run
#: ``run_01M7HH1MPV5W1FEZMX5ZK29PTA`` it delivered 7 of 52 contexts, and 14 assessments ran on a context cut by the budget. The flow now packs
#: its norm review calls so that every candidate's context is delivered (``runs/flow_norm_context.pack_norm_batches``), and this is the room one
#: call has for it: what is left of ``input_tokens_per_call`` once the observation batch (``OBSERVATION_CHARACTERS_PER_CALL``, the flow's own cap on
#: titles, descriptions and candidate quotes) is in. At the estimate's 5/7 token per character that is 140 000 characters for the call, so
#: 140 000 - 80 000 = 60 000 for the paragraph contexts; 40 paragraphs keeps the old ratio of one per 1 500 characters. A single input that
#: still does not fit one call is a technical gap with a reason, never a silent cut.
INPUT_TOKENS_PER_CALL = 100_000
OBSERVATION_CHARACTERS_PER_CALL = 80_000
_CHARACTERS_PER_CALL = INPUT_TOKENS_PER_CALL * 7 // 5
MAX_PARAGRAPHS = 40
MAX_CHARACTERS = _CHARACTERS_PER_CALL - OBSERVATION_CHARACTERS_PER_CALL

#: The cost estimate's assumptions for the packing (``runs/preflight.py``): up to six candidates for an input (the semantic lookup's
#: ``limit`` of a full-document run), and 2 600 characters for the encoded context of one candidate (measured: 7 contexts filled the 18 000
#: characters of the old budget on the prod run above). An estimate is a bound the meter checks, not a promise.
ESTIMATE_INPUTS_PER_CALL = 40
ESTIMATE_CANDIDATES_PER_INPUT = 6
ESTIMATE_CONTEXT_CHARACTERS = 2_600


def estimated_calls_per_review_call():
    """How many norm review calls a "forty inputs" call of the estimate becomes once every candidate's context is delivered."""
    budget = policy()
    contexts = ESTIMATE_INPUTS_PER_CALL * ESTIMATE_CANDIDATES_PER_INPUT
    return max(1, math.ceil(contexts * ESTIMATE_CONTEXT_CHARACTERS / budget["max_characters"]),
               math.ceil(contexts / budget["max_paragraphs"]))


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def encoded_characters(value):
    """The size the budget measures: the characters of a ``norm_paragraph_context`` as it is encoded into the request."""
    return len(_encoded(value))


def policy():
    return {"version": VERSION, "bundle_sha256": extended_digest({
        "application": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reader": norm_paragraph_context_digest()}),
        "max_paragraphs": MAX_PARAGRAPHS, "max_characters": MAX_CHARACTERS, "paragraph_characters": 6000,
        "neighbor_characters": 1000, "input_tokens_per_call": INPUT_TOKENS_PER_CALL}


def identity_of(candidate):
    """The identity of a context: the exact search fragment of a paragraph, never the paragraph alone."""
    return (candidate["snapshot_id"], candidate["document_id"], candidate["paragraph_id"], candidate["quote"])


#: What a prefetched context is when the corpus could not give it (a missing paragraph, an unavailable corpus).
UNAVAILABLE = None


def read_context(session, identity, accepted):
    """One candidate's context as :func:`attach` carries it, or :data:`UNAVAILABLE` when the corpus cannot give it.

    Any other failure propagates: only the three corpus codes below are an absent context, everything else is a defect.
    """
    try:
        actual = read_norm_paragraph_context(session, snapshot_id=identity[0], document_id=identity[1],
            paragraph_id=identity[2], quote=identity[3], paragraph_characters=accepted["paragraph_characters"],
            neighbor_characters=accepted["neighbor_characters"])
    except DomainError as error:
        if error.code not in {ErrorCode.REQUIRED_NORM_UNAVAILABLE, ErrorCode.NOT_FOUND, ErrorCode.DEPENDENCY_UNAVAILABLE}:
            raise
        return UNAVAILABLE
    actual["search_quote_sha256"] = hashlib.sha256(identity[3].encode("utf-8")).hexdigest()
    return actual


def context_of(snapshot_id, wanted, paragraphs):
    """The ``norm_paragraph_context`` of a call: ``wanted`` contexts asked for, ``paragraphs`` of them provided."""
    return {"version": VERSION, "snapshot_id": snapshot_id, "paragraphs": list(paragraphs),
        "candidate_quote_contexts": wanted, "contexts_provided": len(paragraphs),
        "contexts_not_provided": wanted - len(paragraphs), "complete_corpus_claim": False,
        "edition_applicability_verified": False, "neighbor_citations_allowed": False}


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


def attach(session, request, *, observations, snapshot_id, accepted, checkpoint, prefetched=None):
    """``prefetched`` maps an :func:`identity_of` to what :func:`read_context` returned for it (the packer already read every context of the
    flow once); an identity it does not hold is read here, exactly as before."""
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
            identity = identity_of(candidate)
            if candidate["snapshot_id"] != snapshot_id:
                raise ValueError("norm_paragraph_context_snapshot_conflict")
            if identity not in seen:
                seen.add(identity); wanted.append((identity, candidate))
    context = context_of(snapshot_id, len(wanted), [])
    omitted = []
    attempted = 0
    for identity, candidate in wanted:
        if attempted >= accepted["max_paragraphs"]:
            omitted.append({"paragraph_id": candidate["paragraph_id"], "reason": "paragraph_context_selection_limit"})
            continue
        attempted += 1
        checkpoint("extended_norm_paragraph_context")
        actual = deepcopy(prefetched[identity]) if prefetched is not None and identity in prefetched \
            else read_context(session, identity, accepted)
        if actual is UNAVAILABLE or actual is None:
            omitted.append({"paragraph_id": candidate["paragraph_id"], "reason": "paragraph_context_unavailable"})
            continue
        proposed = context_of(snapshot_id, len(wanted), [*context["paragraphs"], actual])
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
