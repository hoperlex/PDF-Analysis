"""The score of a pair of pages (``lineage.py:190-287``): what the assignment maximises.

`CMP-MATRIX-01`. A pair's score is the weighted mean of the parts that are *known* for both pages: a part that
cannot be computed (no text, no stamp, no mask) is left out of the mean and does not count against the pair
(``_score_rules``, the ``text`` rule). Page order is no part of the score under rule ``order``: it only orders
close candidates. A pair with no part at all scores zero. Parts and weights are the original's:

========== ====== ===========================================================================
part       weight what
========== ====== ===========================================================================
text       0.30   weighted Jaccard of the words outside the service zones
layout     0.15   share of the (word, 15 pt cell) pairs the two pages have in common
title      0.25   1.0 for an equal title, else 0.6 x the similarity of the two titles
identity   0.10   1.0 same designation and sheet number, 0.5 same designation, else 0.0
image      0.15   overlap of the ink masks (each dilated by 3 x 3); only with comparable text
========== ====== ===========================================================================

``containment`` (the shared share of the smaller page's text, with 40 words or more on both), ``title_prefix`` and
``order`` are parts of the record that decide *candidacy*, not the value. A pair of different kinds is multiplied by
0.6 unless both kinds are known and they are the drawing/text pair.
"""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from auditmanager.comparison.matrix.features import PageFeatures

__all__ = ["has_content_evidence", "mask_iou", "score", "weighted_jaccard"]


def weighted_jaccard(a: Counter[str], b: Counter[str]) -> float:
    """``lineage.py:175-180``: the multiset Jaccard index; two empty pages score zero."""
    if not a and not b:
        return 0.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


def mask_iou(a: PageFeatures, b: PageFeatures) -> float:
    """``lineage.py:183-187``: how much of each page's ink lies within a pixel of the other's; 1.0 for two blank pages."""
    mask_a, mask_b = a.mask, b.mask
    dil_a, dil_b = a.dilated(), b.dilated()
    assert mask_a is not None and mask_b is not None and dil_a is not None and dil_b is not None
    inter = int((mask_a & dil_b).sum()) + int((mask_b & dil_a).sum())
    total = a.half_ink + b.half_ink
    return inter / total if total else 1.0


def score(
    a: PageFeatures, b: PageFeatures, rel_a: float, rel_b: float, rules: frozenset[str]
) -> tuple[float, dict[str, float]]:
    """``_score_rules`` (``lineage.py:234-282``) for the rule set ``v1.2``. Returns ``(value, parts)``."""
    parts: dict[str, float] = {}
    weights: dict[str, float] = {}
    text_known = (a.has_text and b.has_text) if "text" in rules else bool(a.token_total or b.token_total)
    shared = 0
    if a.token_total or b.token_total:
        shared = sum((a.tokens & b.tokens).values())
    if text_known:
        union_tokens = a.token_total + b.token_total - shared
        parts["text"] = shared / union_tokens if (a.tokens or b.tokens) and union_tokens else 0.0
        weights["text"] = 0.30
        union = len(a.pos | b.pos)
        parts["layout"] = len(a.pos & b.pos) / union if union else 0.0
        weights["layout"] = 0.15
    elif "text" in rules and (a.token_total or b.token_total):
        parts["text_unknown"] = 1.0
    if a.title and b.title:
        parts["title"] = 1.0 if a.title == b.title else 0.6 * SequenceMatcher(None, a.title, b.title).ratio()
        weights["title"] = 0.25
    if a.designation and b.designation:
        same_designation = a.designation == b.designation
        same_number = bool(a.sheet_no) and a.sheet_no == b.sheet_no
        parts["identity"] = 1.0 if (same_designation and same_number) else (0.5 if same_designation else 0.0)
        weights["identity"] = 0.10
    both_text = a.has_text and b.has_text if "text" in rules else bool(a.token_total and b.token_total)
    if (
        a.has_mask
        and b.has_mask
        and a.mask_shape() == b.mask_shape()
        and (parts.get("text", 1.0) >= 0.15 or not both_text)
    ):
        parts["image"] = mask_iou(a, b)
        weights["image"] = 0.15
    if min(a.token_total, b.token_total) >= 40:
        parts["containment"] = shared / min(a.token_total, b.token_total)
    if a.title and b.title and a.title != b.title and (a.title.startswith(b.title) or b.title.startswith(a.title)):
        parts["title_prefix"] = 1.0
    parts["order"] = max(0.0, 1.0 - abs(rel_a - rel_b) * 4)
    if "order" not in rules:
        weights["order"] = 0.05
    elif not weights:
        return 0.0, parts | {"no_content_evidence": 1.0}
    total_weight = sum(weights.values())
    value = sum(parts[k] * weights[k] for k in weights) / total_weight if total_weight else 0.0
    kinds_known = "kind" not in rules or "unknown" not in (a.kind, b.kind)
    if kinds_known and a.kind != b.kind and {a.kind, b.kind} != {"drawing", "text"}:
        value *= 0.6
        parts["kind_mismatch"] = 1.0
    return value, parts


def has_content_evidence(parts: dict[str, float]) -> bool:
    """``lineage.py:284-287``: a candidate needs shared content, not only a sheet number."""
    return bool(
        parts.get("text", 0) >= 0.15
        or parts.get("layout", 0) >= 0.15
        or parts.get("image", 0) >= 0.4
        or parts.get("title", 0) >= 0.6
        or parts.get("containment", 0) >= 0.25
        or parts.get("title_prefix", 0) > 0
    )
