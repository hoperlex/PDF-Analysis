"""The reads of the sheet descriptions: the eleven states, the description of a pair, the progress of a transition, the «Проверить» list
(`CMP-VC-AISHEET-01`). Pure over the rows of :mod:`.repository`; reading starts nothing and calls no model.

**The state of a sheet pair** (the contract's ``ComparisonAiSheetState``, ``view.py:99-142`` of the original) is derived on every read
and never stored, so there is no second copy to drift:

1. an item of a live job that is waiting is ``queued`` and one that is being described is ``running`` (a job that is paused still waits);
2. else a stored description of the pair's subject gives its own state -- ``done``, ``needs_clarification``, ``partial``,
   ``no_construction_changes`` -- or ``stale`` when it was made by another version of the prompt (``view.py:65-77``: «Описание устарело»);
3. else the newest item decides: a failed one is ``failed``, a cancelled one (or one of a cancelled job) ``cancelled``;
4. else a pair whose comparison is ``same`` or ``same_zones_changed`` is ``engine_same`` («По данным сравнения изменений нет») -- which is
   not the same as no changes found by the AI -- and anything else is ``not_processed`` («Не обработано»: not the same as no changes).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.ai_sheets.description import (
    contract_changes,
    contract_coverage,
    contract_diagnostics,
    contract_excluded,
    contract_unresolved,
    review_reason,
)
from auditmanager.comparison.ai_sheets.model import DESCRIPTION_STATES, ELIGIBLE_STATUSES, SINGLE_STATUSES
from auditmanager.comparison.ai_sheets.repository import DescriptionRow, PairFacts, PairState

__all__ = [
    "ENGINE_SAME",
    "current_prompt_of",
    "derive_state",
    "description_view",
    "eligible",
    "history_item",
    "page_ref",
    "review_item",
    "state_eligible",
    "transition_progress",
]

ENGINE_SAME: Final[tuple[str, ...]] = ("same", "same_zones_changed")
_LIVE_JOB: Final[tuple[str, ...]] = ("queued", "running", "paused")
_WAITING_NOW: Final[tuple[str, ...]] = ("queued", "paused")


def eligible(pair: PairFacts) -> bool:
    """A pair that is described: the engine found a difference of content or could not decide (a result exists), or the sheet is in one
    version only. A pair that is not finished, that failed, that is ``unmatched`` or that is ``same`` is not."""
    if pair.pair_state != "done":
        return False
    if pair.status in SINGLE_STATUSES:
        return pair.subject_page_profile is not None
    return pair.status in ELIGIBLE_STATUSES and pair.result_id is not None


def state_eligible(ps: PairState) -> bool:
    """:func:`eligible` for a row of the state query (the pair's own columns only)."""
    if ps.pair_state != "done":
        return False
    if ps.status in SINGLE_STATUSES:
        return True
    return ps.status in ELIGIBLE_STATUSES and ps.result_id is not None


def current_prompt_of(ps: PairState) -> str:
    """The ``prompt_version`` a description of this pair would be made with now."""
    from auditmanager.comparison.ai_sheets.method import prompt_for
    from auditmanager.comparison.ai_sheets.model import KIND_PAIR, KIND_SINGLE

    return prompt_for(KIND_SINGLE if ps.status in SINGLE_STATUSES else KIND_PAIR)


def derive_state(ps: PairState, *, current_prompt: str) -> str:
    """The state of a pair now (see the module note)."""
    if ps.item_state in ("queued", "running") and ps.job_state in _LIVE_JOB:
        return "running" if (ps.item_state == "running" and ps.job_state == "running") else "queued"
    if ps.description_id is not None:
        return "stale" if ps.description_prompt != current_prompt else str(ps.description_state)
    if ps.item_state == "failed" or (ps.item_state in ("queued", "running") and ps.job_state == "failed"):
        return "failed"
    if ps.item_state == "cancelled" or (ps.item_state in ("queued", "running") and ps.job_state in ("cancelled", "completed")):
        return "cancelled"  # a sheet still waiting in a job that is over was never described: it was cancelled
    if ps.status in ENGINE_SAME:
        return "engine_same"
    return "not_processed"


def description_view(
    pair: PairFacts, state: str, *, latest: DescriptionRow | None, history_count: int, job_id: str | None,
) -> dict[str, Any]:
    """The contract's ``ComparisonSheetDescription``. The members after ``source`` are absent while the state says nothing was
    described (``not_processed``, ``queued``, ``running``, ``engine_same``, and ``failed`` / ``cancelled`` with no description)."""
    view: dict[str, Any] = {"sheet_pair_id": pair.pair_id, "state": state, "history_count": history_count}
    if job_id is not None and state in ("queued", "running"):
        view["job_id"] = job_id
    if latest is None or state in ("not_processed", "queued", "running", "engine_same"):
        return view
    description = latest.description
    declared = declared_of(pair)
    view.update({
        "description_id": latest.description_id, "source": latest.source,
        "changes": contract_changes(description), "unresolved": contract_unresolved(description), "declared": declared,
        "excluded": contract_excluded(description), "coverage": contract_coverage(description),
        "diagnostics": contract_diagnostics(description), "model": latest.model_identity[:128],
        "prompt_version": latest.prompt_version[:64], "recorded": latest.recorded, "created_at": latest.created_at,
    })
    return view


def declared_of(pair: PairFacts) -> list[dict[str, Any]]:
    """«Заявлено проектировщиком в разрешении»: the items the series' permit reconciliation attached to this pair (the table's text is
    the designer's, taken literally, and is no input of the model)."""
    permit = pair.permit or {}
    out = []
    for item in permit.get("items") or []:
        text = " ".join(str(item.get("text", "")).split())
        if text:
            entry: dict[str, Any] = {"text": text[:500]}
            if item.get("state"):
                entry["reference"] = str(item["state"])[:120]
            out.append(entry)
    return out[:100]


def history_item(row: DescriptionRow) -> dict[str, Any]:
    """The contract's ``ComparisonSheetDescriptionRevision`` (one entry of «История (N)»)."""
    description = row.description
    single = description.get("single")
    return {
        "description_id": row.description_id, "state": row.state,
        "changes_count": len(contract_changes(description)) if single else len(description.get("changes") or []),
        "unresolved_count": len(description.get("unresolved") or []), "recorded": row.recorded, "created_at": row.created_at,
        "model": row.model_identity[:128], "prompt_version": row.prompt_version[:64],
    }


def page_ref(row: Mapping[str, Any], side: str, profile_id: str | None) -> dict[str, Any] | None:
    """The contract's ``ComparisonPairPage`` of one side of a pair, or ``None`` for a side that has no page."""
    if profile_id is None:
        return None
    page: dict[str, Any] = {"page": {
        "version_uid": row[f"{side}_version"], "page_number": int(row[f"{side}_number"]), "page_profile_id": profile_id,
    }}
    if row[f"{side}_sheet"]:
        page["sheet_number"] = row[f"{side}_sheet"]
    if row[f"{side}_title"]:
        page["title"] = row[f"{side}_title"]
    if row[f"{side}_scan"] is not None:
        page["scan"] = bool(row[f"{side}_scan"])
    return page


def review_item(ps: PairState, state: str) -> dict[str, Any] | None:
    """A row of «Проверить»: a one-sided sheet (``added`` / ``removed``), or a sheet the AI left ``partial``; ``None`` for any other."""
    if ps.status in SINGLE_STATUSES:
        kind = str(ps.status)
    elif state == "partial":
        kind = "to_check"
    else:
        return None
    item: dict[str, Any] = {"sheet_pair_id": ps.pair_id, "kind": kind, "state": state}
    for side in ("a", "b"):
        page = page_ref(ps.row, side, ps.row[f"page_{side}_profile_id"])
        if page is not None:
            item[f"page_{side}"] = page
    return item


def transition_progress(
    transition_id: str, states: Sequence[tuple[PairState, str]], spend: Mapping[str, int] | None,
) -> dict[str, Any]:
    """One row of «ИИ-описание изменений» (``ComparisonAiTransitionProgress``): «Листов» the sheets to describe, «Изм.» those with a change,
    «Вопр.» the open questions, «Ошибок» the failed ones, «Проверить» the ``partial`` ones, then the calls, tokens and seconds of the
    latest job (``series_ai.py:_progress_status``)."""
    spend = spend or {}
    sheets = done = changed = questions = errors = to_review = 0
    for ps, state in states:
        sheets += 1
        if state in DESCRIPTION_STATES:
            done += 1
            if ps.changes_count > 0:
                changed += 1
            questions += ps.unresolved_count
            if state == "partial":
                to_review += 1
        elif state == "failed":
            errors += 1
    return {
        "transition_id": transition_id, "sheets": sheets, "done": done, "changed": changed, "questions": questions, "errors": errors,
        "to_review": to_review, "calls": int(spend.get("calls", 0)), "input_tokens": int(spend.get("input_tokens", 0)),
        "output_tokens": int(spend.get("output_tokens", 0)), "seconds": int(spend.get("elapsed_ms", 0)) // 1000,
    }


def review_text(row: DescriptionRow) -> str | None:
    return review_reason(row.description)
