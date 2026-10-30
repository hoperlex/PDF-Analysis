"""Pure card preparation over immutable raw evidence. No model call or raw rewrite."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from auditmanager.comparison.stage_ai.model import CATEGORIES, CLASSES, SYSTEMS
from auditmanager.shared.errors import DomainError, ErrorCode


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def invalid(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


def source_signature(source: Mapping[str, Any]) -> dict[str, Any]:
    """Revision/classification changes cannot alter the content a verdict judged.

    Profiles pin document versions and page coordinates; fragment content keys pin
    normalised text and its source. Raw difference IDs are revision-local and are
    deliberately outside this signature.
    """
    return {"kind": source["kind"], "parts": sorted(
        ({"side": p["side"], "profile_id": p["profile_id"],
          "content_key": p["content_key"], "box_anchor": p["box_anchor"]}
         for p in source["parts"]), key=lambda p: (p["side"], p["content_key"])),
        "graphic_key": source.get("graphic_key")}


def anchor_key(part: Mapping[str, Any]) -> str:
    """A location relates changed evidence only for stale/partial labels, never acceptance."""
    return digest({"document_uid": part.get("document_uid"), "page": part.get("page_number"),
                   "side": part["side"], "box": part["box_anchor"]})


def prepare_cards(sources: Mapping[str, dict[str, Any]],
                  classifications: Sequence[dict[str, Any]], *, include_uncovered: bool = True) -> tuple[dict[str, Any], ...]:
    """Validated AI labels decorate evidence; every uncovered raw row remains REVIEW.

    SAME/MOVED judgments never remove the underlying deterministic difference.
    A whole invalid stored classification is refused rather than partially applied.
    """
    proposed: list[dict[str, Any]] = []
    used: set[str] = set()
    for answer in classifications:
        for card in answer["cards"]:
            ids = card.get("evidence_ids", [])
            if (not isinstance(ids, list) or not ids or len(ids) != len(set(ids))
                    or any(i not in sources for i in ids) or used.intersection(ids)):
                raise invalid("stage_card_classification_evidence_invalid")
            if (card.get("class_name") not in CLASSES or card.get("category") not in CATEGORIES
                    or card.get("system") not in SYSTEMS or not isinstance(card.get("title"), str)
                    or not 1 <= len(card["title"].strip()) <= 260):
                raise invalid("stage_card_classification_invalid")
            used.update(ids)
            proposed.append(dict(card) | {"classification_id": answer["classification_id"]})
    for evidence_id in sorted(set(sources) - used) if include_uncovered else ():
        source = sources[evidence_id]
        title = ("Графическое различие требует проверки" if source["kind"] == "GRAPHIC"
                 else "Текстовое различие требует проверки")
        proposed.append({"class_name": "REVIEW", "category": "uncertain", "title": title,
                         "system": "unknown", "evidence_ids": [evidence_id],
                         "classification_id": None})
    result = []
    for card in proposed:
        ids = sorted(card["evidence_ids"])
        selected = [sources[i] for i in ids]
        before = "\n\n".join(dict.fromkeys(s["before"] for s in selected if s["before"]))
        after = "\n\n".join(dict.fromkeys(s["after"] for s in selected if s["after"]))
        if max(len(before), len(after)) > 20_000:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_chain_run_id",
                              constraint="stage_card_text_budget")
        signature = sorted((source_signature(s) for s in selected), key=digest)
        result.append(card | {"evidence_ids": ids, "before": before, "after": after,
                              "evidence_digest": digest({"evidence": signature}),
                              "anchor_keys": sorted({anchor_key(p) for s in selected for p in s["parts"]
                                                     if p.get("document_uid")}),
                              "card_key": digest({"class": card["class_name"], "evidence_ids": ids})})
    return tuple(sorted(result, key=lambda c: c["card_key"]))


def carryover_match(current: Mapping[str, Any], previous: Sequence[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Only unanimous exact content matches may carry an expert act forward."""
    exact = [p for p in previous if p["evidence_digest"] == current["evidence_digest"]]
    if exact:
        if len({p["decision"] for p in exact}) == 1:
            return "full", exact
        return "stale", exact
    ids = set(current["evidence_ids"])
    related = [p for p in previous if ids.intersection(p["evidence_ids"])]
    if related:
        return ("partial" if any(ids != set(p["evidence_ids"]) for p in related) else "stale"), related
    anchors = set(current.get("anchor_keys", []))
    related = [p for p in previous if anchors.intersection(p.get("anchor_keys", []))]
    if related:
        return ("partial" if any(anchors != set(p.get("anchor_keys", [])) for p in related) else "stale"), related
    return "none", []
