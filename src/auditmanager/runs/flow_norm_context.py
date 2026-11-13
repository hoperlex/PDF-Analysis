"""Fresh V2 adapter of the existing bounded, identity-bound norm context reader.

Request-local fragment aliases never replace corpus identities. Each claim gets
its own context sufficiency receipt; an unrelated missing paragraph cannot lower
its neighbour. The old norm-context policy and builders remain unchanged.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json

from auditmanager.analysis.public import extended_digest
from .norm_context import attach, policy


def attach_flow_norm_context(session, request, *, originals, indexed, snapshot_id, checkpoint):
    prepared, receipt = attach(session, request, observations=originals, snapshot_id=snapshot_id,
        accepted=policy(), checkpoint=checkpoint or (lambda _: None))
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
