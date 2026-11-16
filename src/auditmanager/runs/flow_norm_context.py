"""Fresh V2 adapter of the existing bounded, identity-bound norm context reader.

Request-local fragment aliases never replace corpus identities. Each claim gets
its own context sufficiency receipt; an unrelated missing paragraph cannot lower
its neighbour. The old norm-context builders remain unchanged; `NORM-ALL-FINDINGS-01`
adds the packing of the calls, so that no candidate's context is left out of a call.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json

from auditmanager.analysis.public import extended_digest
from .norm_context import (OBSERVATION_CHARACTERS_PER_CALL, UNAVAILABLE, attach, context_of, encoded_characters,
    identity_of, policy, read_context)

#: One norm review call carries at most this many observations (the flow's own limit; the cost estimate prices the same figure).
OBSERVATIONS_PER_CALL = 40
#: The reason of an input whose own candidates do not fit one call's paragraph-context budget: a technical gap, never a silent cut.
CONTEXT_OVER_BUDGET = "norm_paragraph_context_over_budget"


def _fits(snapshot_id, identities, contexts, accepted):
    """Whether one call can carry the contexts of ``identities``: their count (an unavailable context was still attempted) and the encoded
    size of the ``norm_paragraph_context`` they make, each within the call's budget."""
    if len(identities) > accepted["max_paragraphs"]:
        return False
    provided = [contexts[identity] for identity in identities if contexts[identity] is not UNAVAILABLE]
    return encoded_characters(context_of(snapshot_id, len(identities), provided)) <= accepted["max_characters"]


def pack_norm_batches(session, items, *, snapshot_id, checkpoint):
    """`NORM-ALL-FINDINGS-01` (B4): split the candidate-bearing ``items`` into norm review calls so that **every** candidate's paragraph context
    is delivered. A call is closed when the next item would take it past the observation limit, past the character cap of the observation
    part, or past the paragraph-context budget (the contexts the call's items share are carried once); a new call starts instead of omitting.

    Every distinct context is read once, here, and handed to :func:`attach` through the returned ``prefetched`` mapping. An item whose own
    candidates cannot fit one empty call is returned in ``over_budget`` and is in no batch: the caller marks it a technical gap with
    :data:`CONTEXT_OVER_BUDGET`. Order is the order of ``items``, so the same inputs make the same calls (a paid reply is found again).

    Returns ``(batches, prefetched, over_budget)``; ``batches`` is a list of lists of items.
    """
    accepted, check = policy(), checkpoint or (lambda _: None)
    prefetched: dict[tuple, dict | None] = {}
    batches, over_budget = [], []
    current, identities, characters = [], [], 0
    for item in items:
        own = []
        for candidate in item["norm_candidates"]:
            if candidate["snapshot_id"] != snapshot_id:
                raise ValueError("norm_paragraph_context_snapshot_conflict")
            identity = identity_of(candidate)
            if identity not in prefetched:
                check("extended_norm_paragraph_context")
                prefetched[identity] = read_context(session, identity, accepted)
            if identity not in own:
                own.append(identity)
        if not _fits(snapshot_id, own, prefetched, accepted):
            over_budget.append(item)
            continue
        size = len(item["title"]) + len(item["description"]) + sum(len(c["quote"]) for c in item["norm_candidates"])
        joined = [*identities, *(identity for identity in own if identity not in identities)]
        if current and (len(current) >= OBSERVATIONS_PER_CALL or characters + size > OBSERVATION_CHARACTERS_PER_CALL
                        or not _fits(snapshot_id, joined, prefetched, accepted)):
            batches.append(current)
            current, identities, characters, joined = [], [], 0, list(own)
        current.append(item)
        identities, characters = joined, characters + size
    if current:
        batches.append(current)
    return batches, prefetched, over_budget


def attach_flow_norm_context(session, request, *, originals, indexed, snapshot_id, checkpoint, prefetched=None):
    prepared, receipt = attach(session, request, observations=originals, snapshot_id=snapshot_id,
        accepted=policy(), checkpoint=checkpoint or (lambda _: None), prefetched=prefetched)
    body = deepcopy(dict(prepared.body))
    payload = json.loads(body["messages"][0]["content"])
    payload["norm_context_by_input"] = [{"input_id": key, "norm_candidates": deepcopy(item["norm_candidates"])}
        for key, item in indexed.items()]
    payload["candidate_identity_policy"] = "exact-fragment-alias-v1"
    body["messages"][0]["content"] = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["system"] += (" Идентификаторы xnv_ — временные имена точных фрагментов соответствующего входа. "
        "actual_paragraph_id связывает их с настоящим абзацем norm_paragraph_context. "
        "В ответе используй только временные paragraph_id своих norm_candidates; сервер восстановит настоящие IDs.")
    if len(json.dumps(body, ensure_ascii=False).encode()) > 900_000:
        raise ValueError("flow_norm_context_request_too_large")
    receipt["context_sha256"] = extended_digest({"by_input": payload["norm_context_by_input"],
        "paragraph_context": receipt["context"]})
    receipt["norm_context_by_input"] = deepcopy(payload["norm_context_by_input"])
    available = {(row["snapshot_id"], row["document_id"], row["paragraph_id"], row["search_quote_sha256"]): row
        for row in receipt["context"]["paragraphs"]}
    receipt["by_input"] = {}
    for key, item in originals.items():
        incomplete = []
        for candidate in item["norm_candidates"]:
            identity = (candidate["snapshot_id"], candidate["document_id"], candidate["paragraph_id"],
                hashlib.sha256(candidate["quote"].encode()).hexdigest())
            context = available.get(identity)
            if (context is None or context.get("search_quote_literal_in_paragraph") is not True
                    or context["primary"].get("truncated") is not False):
                incomplete.append(candidate["paragraph_id"])
        item["normative_context"] = {"complete": not incomplete,
            "reason": "provided" if not incomplete else "norm_paragraph_context_incomplete",
            "incomplete_paragraph_ids": list(dict.fromkeys(incomplete)),
            "context_sha256": receipt["context_sha256"], "edition_applicability_verified": False}
        receipt["by_input"][key] = deepcopy(item["normative_context"])
    return replace(prepared, body=body,
        idempotency_scope=f"{request.idempotency_scope}:flow-norm-context:{extended_digest(body)}"), receipt
