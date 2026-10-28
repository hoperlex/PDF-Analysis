"""The contract-shaped dictionaries of the series, its transitions and its sheet pairs (`CMP-SERIES-01`).

Pure: no database. The adapter in the composition root validates them with the generated models. Raw deterministic
evidence is **copied, never rebuilt**: the members of the stored result ``jsonb`` that the contract names
(``canvas``, ``differences``, ``text_changes``, ``service_notes``, ``how_compared``) and the result's own ``channels`` and
``reasons`` are passed through as they were stored (wave brief section 4 item 3; AGENTS.md section 4: an AI layer, or a view,
never rewrites raw evidence). What the series adds -- the pair's status after a forced review, the forcing reason, the
parts coverage, the permit -- is the series' own and sits beside them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.series.repository import SeriesRow, TransitionRow

__all__ = ["EVIDENCE_MEMBERS", "contract_reason", "pair_dict", "series_dict", "transition_dict"]

#: The members of the stored result that ``getComparisonSheetPair`` copies verbatim.
EVIDENCE_MEMBERS: Final[tuple[str, ...]] = ("canvas", "differences", "text_changes", "service_notes", "how_compared")

#: A reason of ``ComparisonSheetPair.reasons`` (the contract's pattern).
_REASON: Final = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


def contract_reason(reason: str) -> str:
    """A stored reason as the contract can carry it. A reason that fits the pattern is passed as it is. The engine also writes
    ``UNCHECKED_CHANNEL:<channel>`` (a colon and lower case), which the pattern refuses; it becomes ``UNCHECKED_CHANNEL_<CHANNEL>``
    -- the same words, no information lost (the channel's own state and reason stay in ``channels``). The stored row is untouched."""
    if _REASON.match(reason):
        return reason
    mapped = re.sub(r"[^A-Z0-9_]", "_", reason.upper())[:64]
    return mapped if _REASON.match(mapped) else "REASON_" + re.sub(r"[^A-Z0-9_]", "_", reason.upper())[:57]


def series_dict(
    row: SeriesRow, *, transitions_total: int, transitions_done: int, stale_reasons: Sequence[str],
    transitions: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "series_id": row.series_id,
        "project_uid": row.project_uid,
        "document_uid": row.document_uid,
        "state": row.state,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "transitions_total": transitions_total,
        "transitions_done": transitions_done,
        "matrix_revision": {"matrix_id": row.matrix_id, "edit_no": row.edit_no},
    }
    if row.order_id is not None:
        out["order_id"] = row.order_id
    if row.restarted_from is not None:
        out["restarted_from"] = row.restarted_from
    if stale_reasons:
        out["stale_reasons"] = list(stale_reasons)
    if row.failure_reason is not None:
        out["failure_reason"] = row.failure_reason
    if transitions is not None:
        out["transitions"] = list(transitions)
    return out


def transition_dict(row: TransitionRow, *, items_total: int, items_done: int, summary: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "transition_id": row.transition_id,
        "series_id": row.series_id,
        "source_version_uid": row.source_version_uid,
        "target_version_uid": row.target_version_uid,
        "state": row.state,
        "items_total": items_total,
        "items_done": items_done,
        "summary": dict(summary),
    }
    if row.verdict:
        out["verdict"] = list(row.verdict)
    if row.failure_reason is not None:
        out["failure_reason"] = row.failure_reason
    return out


def _page(row: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    profile_id = row["page_a_profile_id" if side == "a" else "page_b_profile_id"]
    if profile_id is None:
        return None
    ref: dict[str, Any] = {
        "version_uid": row[f"{side}_version"], "page_number": int(row[f"{side}_number"]), "page_profile_id": profile_id,
    }
    page: dict[str, Any] = {"page": ref}
    if row[f"{side}_sheet"]:
        page["sheet_number"] = row[f"{side}_sheet"]
    if row[f"{side}_title"]:
        page["title"] = row[f"{side}_title"]
    if row[f"{side}_scan"] is not None:
        page["scan"] = bool(row[f"{side}_scan"])
    return page


def _public_parts(parts: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """``ComparisonPartsCoverage`` from the stored record (which also keeps the series' own working members)."""
    if not parts or "role" not in parts:
        return None
    return {
        "role": parts["role"], "covered_percent": float(parts.get("covered_percent", 0.0)),
        "parts": list(parts.get("parts", ())),
    }


def pair_dict(row: Mapping[str, Any], *, with_evidence: bool) -> dict[str, Any]:
    """One sheet pair. ``row`` is the joined row of :meth:`SeriesRepository.pair_view` / ``pair_page``."""
    out: dict[str, Any] = {
        "sheet_pair_id": row["comparison_sheet_pair_id"],
        "transition_id": row["comparison_transition_id"],
        "state": row["state"],
    }
    for side in ("a", "b"):
        page = _page(row, side)
        if page is not None:
            out[f"page_{side}"] = page
    if row["status"] is not None:
        out["status"] = row["status"]
    if row["confidence"] is not None:
        out["confidence"] = row["confidence"]
    flags = list(row["flags"] or [])
    if flags:
        out["flags"] = flags
    parts = row["parts"]
    raw_reasons = list(dict.fromkeys(contract_reason(r) for r in (row["r_reasons"] or [])))
    series_reasons = [r for r in (parts or {}).get("series_reasons", ()) if r not in raw_reasons]
    if row["r_reasons"] is not None or series_reasons:  # a pair with a result always shows the result's reasons, even none
        out["reasons"] = raw_reasons + series_reasons
    if row["r_channels"]:
        out["channels"] = row["r_channels"]
    if row["permit"] is not None:
        out["permit"] = row["permit"]
    public_parts = _public_parts(parts)
    if public_parts is not None:
        out["parts"] = public_parts
    if row["result_id"] is not None:
        out["result_id"] = row["result_id"]
    out["ai_dependent"] = bool(row["ai_dependent"])
    if row["failure_reason"] is not None:
        out["failure_reason"] = row["failure_reason"]
    if with_evidence and row.get("r_result"):
        result = row["r_result"]
        for member in EVIDENCE_MEMBERS:
            if member in result:
                out[member] = result[member]
    return out

