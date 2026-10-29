"""The stored description of a sheet and its readers (`CMP-VC-AISHEET-01`; pure, no database, no model).

``build_description`` makes the document that ``comparison_sheet_description.description`` holds from the packet and the checked answer: the
items with their tiers, the questions, what was left out, the coverage, the diagnostics. It is **the AI layer** and it names raw evidence by
reference only (candidate and pointer ids, the boxes the program took from the engine's rows); it never rewrites the raw rows
(ADR-0025 decision 3, AGENTS.md section 4). It says in its data that no engineer has confirmed it (``engineer_confirmed`` false,
``disclaimer``) and whether it is a recorded answer.

The readers turn it into the contract's shapes (``ComparisonAiChange`` ...), into the «Проверить» reason (``view.py:154-168``) and into
the Markdown of a sheet (``report.py:367-388``): **the same description gives the same bytes** -- nothing in the Markdown is a time, an
identity of a row or an order a dictionary happens to have.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.ai_sheets import geometry as geo
from auditmanager.comparison.ai_sheets.candidates import REASONS as PROGRAM_REASONS
from auditmanager.comparison.ai_sheets.check import norm, weakest
from auditmanager.comparison.ai_sheets.model import (
    DISCLAIMER,
    KIND_SINGLE,
    LABEL_ADDED,
    LABEL_REMOVED,
    RECORDED_NOTICE,
    SINGLE_DISCLAIMER,
    STATE_LABELS,
    TIER_IMAGE,
    TIER_TEXT,
    TIER_UNVERIFIED,
)
from auditmanager.comparison.ai_sheets.schema import EXCLUDE_LABELS

__all__ = [
    "DESCRIPTION_SCHEMA",
    "build_description",
    "build_single_description",
    "check_single",
    "contract_changes",
    "contract_coverage",
    "contract_diagnostics",
    "contract_excluded",
    "contract_unresolved",
    "review_reason",
    "sheet_markdown",
]

DESCRIPTION_SCHEMA: Final[str] = "cmp-sheet-description/1"
_ISSUE: Final = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
#: The program's reasons for leaving a pointer out, as the contract's ``ComparisonAiExcludeReason``.
_PROGRAM_EXCLUDE: Final[Mapping[str, str]] = {
    "service": "service", "revision_tag": "revision_mark", "whitespace": "formatting", "label_move": "label_move",
    "line_style": "formatting", "shift_speck": "formatting", "engine_noise": "formatting",
}


def build_description(
    packet: Mapping[str, Any], checked: Mapping[str, Any], state: str, *, calls: Sequence[Mapping[str, Any]], launches: int,
    recorded: bool, context: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """The document of a described sheet pair (``report.py:329-356``). ``checked`` is the output of :func:`.check.check` (``ok`` true)."""
    excluded_by_program: dict[str, int] = {}
    for entry in (packet.get("ledger") or {}).values():
        if entry["status"] == "excluded":
            reason = entry.get("reason") or "?"
            excluded_by_program[reason] = excluded_by_program.get(reason, 0) + 1
    return {
        "schema": DESCRIPTION_SCHEMA, "kind": "pair", "packet_id": packet["packet_id"], "state": state,
        "engine": {k: packet["engine"].get(k) for k in ("status", "status_label", "notes")},
        "changes": checked["changes"], "unresolved": checked["unresolved"], "excluded": checked["excluded"],
        "coverage": checked["coverage"],
        "diagnostics": {
            "issues": checked["issues"], "pointer_ledger_counts": dict(packet.get("counts") or {}),
            "excluded_by_program": excluded_by_program,
            "candidates": [{"id": c["id"], "kind": c["kind"]} for c in packet["candidates"]],
            "calls": list(calls), "launches": launches, "context": list(context), "budget": dict(packet.get("budget") or {}),
        },
        "transform": packet.get("transform"), "canvas": packet.get("canvas"),
        "disclaimer": DISCLAIMER, "engineer_confirmed": False, "recorded": recorded,
    }


def check_single(answer: Mapping[str, Any], sheet_text: str) -> dict[str, Any]:
    """The check of a single sheet's answer against its own text layer (``single.py:112-114`` ``_check``, and this lane's tiers).

    The answer must be a summary, a list of objects and a list of marks. A mark that is not in the text of the sheet is dropped (and said
    in ``issues``): a designation is a claim about a place the raw evidence must contain."""
    issues: list[dict[str, Any]] = []
    text = norm(sheet_text)
    marks = []
    for mark in dict.fromkeys(m for m in answer["marks"] if isinstance(m, str) and m.strip()):
        if norm(mark) in text:
            marks.append(mark.strip())
        else:
            issues.append({"code": "MARK_UNVERIFIED", "text": mark, "ref": "marks"})
    objects = []
    for item in answer["objects"][:15]:
        name, detail = str(item.get("name", "")).strip(), str(item.get("detail", "")).strip()
        tier = TIER_TEXT if (not detail or norm(detail) in text) else TIER_UNVERIFIED
        if tier == TIER_UNVERIFIED:
            issues.append({"code": "VALUE_UNVERIFIED", "text": f"{name}: {detail}", "ref": "objects"})
        objects.append({"name": name, "detail": detail, "tier": tier})
    summary = str(answer["summary"]).strip()
    numbers = [t for t in re.findall(r"\d+(?:[.,]\d+)?", summary) if norm(t) not in text]
    summary_tier = TIER_UNVERIFIED if numbers else TIER_TEXT
    if numbers:
        issues.append({"code": "SUMMARY_UNSUPPORTED", "text": ", ".join(numbers), "ref": "summary"})
    return {
        "sheet_kind": str(answer["sheet_kind"]).strip(), "summary": summary, "summary_tier": summary_tier, "objects": objects,
        "marks": marks[:40], "limitation": str(answer.get("limitation") or "").strip(), "issues": issues,
    }


def build_single_description(
    kind: str, checked: Mapping[str, Any], *, packet_id: str, side: str, page: int, calls: Sequence[Mapping[str, Any]],
    launches: int, recorded: bool,
) -> dict[str, Any]:
    """The document of a sheet that is in one version only (``single.py:181-196``): no changes -- what is on the sheet."""
    return {
        "schema": DESCRIPTION_SCHEMA, "kind": KIND_SINGLE, "packet_id": packet_id, "state": "done",
        "single": {
            "kind": kind, "label": LABEL_ADDED if kind == "added" else LABEL_REMOVED, "side": side, "page": page,
            "sheet_kind": checked["sheet_kind"], "summary": checked["summary"], "summary_tier": checked["summary_tier"],
            "objects": checked["objects"], "marks": checked["marks"], "limitation": checked["limitation"],
        },
        "changes": [], "unresolved": [], "excluded": [], "coverage": {"candidates": 1, "in_changes": 0, "in_unresolved": 0, "excluded": 0,
                                                                      "not_reviewed": []},
        "diagnostics": {"issues": list(checked["issues"]), "pointer_ledger_counts": {}, "excluded_by_program": {},
                        "candidates": [], "calls": list(calls), "launches": launches, "context": [], "budget": {}},
        "disclaimer": SINGLE_DISCLAIMER, "engineer_confirmed": False, "recorded": recorded,
    }


# -- the contract's shapes ----------------------------------------------------------------------------------------------------


def _cut(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _values(change: Mapping[str, Any], key: str) -> str:
    fields = list(change.get("fields") or [])
    if not [f for f in fields if f.get(key)]:
        fields = [f for m in change.get("members") or [] for f in m.get("fields") or []]
    fields = [f for f in fields if f.get(key)]
    if len(fields) == 1:
        return str(fields[0][key])
    return "; ".join(f"{f['name']}: {f[key]}" for f in fields)


def _where(evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not evidence:
        return {}
    first = evidence[0]
    box = first.get("box")
    if not box:
        return {}
    return {"side": str(first["side"]).lower(), "box": geo.box_to_dict(box)}


def contract_changes(description: Mapping[str, Any]) -> list[dict[str, Any]]:
    """``ComparisonAiChange`` for each item. A single sheet's objects are its changes: ``added`` with a ``now``, ``removed`` with a ``was``."""
    single = description.get("single")
    if single:
        return _single_changes(single)
    out: list[dict[str, Any]] = []
    for change in description.get("changes") or []:
        item: dict[str, Any] = {
            "change_id": str(change["id"]).lower(), "object_name": _cut(change["object"] or change["place"] or "объект", 300),
            "certainty": "unclear" if change.get("unclear") else "confirmed", "kind": change["kind"],
        }
        if change.get("place"):
            item["place"] = _cut(change["place"], 300)
        was, now = _values(change, "before"), _values(change, "after")
        if was:
            item["was"], item["was_tier"] = _cut(was, 500), change.get("tier_was", TIER_UNVERIFIED)
        if now:
            item["now"], item["now_tier"] = _cut(now, 500), change.get("tier_now", TIER_UNVERIFIED)
        notes = [change["limitation"].strip()] if (change.get("limitation") or "").strip() else []
        unsupported = change.get("unsupported") or {}
        if unsupported.get("summary"):
            notes.append("числа или обозначения текста пункта не найдены в данных листа: " + ", ".join(unsupported["summary"]))
        if unsupported.get("place"):
            notes.append("место не подтверждено данными листа: " + ", ".join(unsupported["place"]))
        if "no_candidate" in (change.get("flags") or []):
            notes.append("пункт не опирается на кандидата программы")
        if notes:
            item["limitation"] = _cut(" ".join(notes), 300)
        item.update(_where(change.get("evidence") or []))
        out.append(item)
    return out


def _single_changes(single: Mapping[str, Any]) -> list[dict[str, Any]]:
    kind, key, tier_key = single["kind"], ("now" if single["kind"] == "added" else "was"), ("now_tier" if single["kind"] == "added" else "was_tier")
    unclear = bool(single.get("limitation"))
    items: list[dict[str, Any]] = [{
        "change_id": "s0", "object_name": _cut(single["sheet_kind"] or single["label"], 300),
        "certainty": "unclear" if (unclear or single["summary_tier"] == TIER_UNVERIFIED) else "confirmed", "kind": kind,
        key: _cut(single["summary"], 500), tier_key: single["summary_tier"],
        **({"limitation": _cut(single["limitation"], 300)} if single.get("limitation") else {}),
    }]
    for number, obj in enumerate(single["objects"], 1):
        if not obj["name"]:
            continue
        item: dict[str, Any] = {
            "change_id": f"s{number}", "object_name": _cut(obj["name"], 300), "certainty": "confirmed" if obj["tier"] != TIER_UNVERIFIED else "unclear",
            "kind": kind,
        }
        if obj["detail"]:
            item[key], item[tier_key] = _cut(obj["detail"], 500), obj["tier"]
        items.append(item)
    return items[:300]


def contract_unresolved(description: Mapping[str, Any]) -> list[dict[str, Any]]:
    out = []
    for item in description.get("unresolved") or []:
        entry: dict[str, Any] = {"question": _cut(item["question"] or "—", 500)}
        entry.update(_where(item.get("evidence") or []))
        out.append(entry)
    return out


def contract_excluded(description: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in description.get("excluded") or []:
        entry: dict[str, Any] = {"reason": item["reason"]}
        text = _cut(item.get("note") or "", 300)
        if text:
            entry["text"] = text
        out.append(entry)
    counts: dict[str, int] = {}
    for reason, n in sorted(((description.get("diagnostics") or {}).get("excluded_by_program") or {}).items()):
        counts[reason] = n
    for reason, n in counts.items():
        out.append({
            "reason": _PROGRAM_EXCLUDE.get(reason, "not_construction"),
            "text": _cut(f"{PROGRAM_REASONS.get(reason, reason)}: {n}", 300),
        })
    return out[:300]


def contract_coverage(description: Mapping[str, Any]) -> dict[str, int]:
    coverage = description.get("coverage") or {}
    return {
        "candidates": int(coverage.get("candidates", 0)), "in_changes": int(coverage.get("in_changes", 0)),
        "not_reviewed": len(coverage.get("not_reviewed") or []),
    }


def contract_diagnostics(description: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = description.get("diagnostics") or {}
    codes = list(dict.fromkeys(i["code"] for i in diagnostics.get("issues") or [] if _ISSUE.match(str(i.get("code", "")))))
    return {
        "issues": codes[:64], "excluded_by_program": int(sum((diagnostics.get("excluded_by_program") or {}).values())),
        "candidates": len(diagnostics.get("candidates") or []),
    }


def review_reason(description: Mapping[str, Any]) -> str | None:
    """Why a sheet is «частично» and what the engineer is to check; ``None`` when there is nothing to check (``view.py:154-168``)."""
    if description.get("state") != "partial":
        return None
    left = (description.get("coverage") or {}).get("not_reviewed") or []
    if left:
        return (f"ИИ разобрал не все отличия листа: не разобрано {len(left)}. "
                "Посмотрите их сами в списке «Отличия» или опишите лист заново.")
    notes = list((description.get("engine") or {}).get("notes") or [])
    if any("низкой уверенностью" in n for n in notes):
        head = "ИИ строительных изменений не нашёл, но пара листов сопоставлена неуверенно — проверьте, что в A и B один и тот же лист."
    else:
        head = "ИИ строительных изменений не нашёл, но алгоритм сравнения оставил по листу пометки — проверьте отличия сами."
    rest = [n for n in notes if "низкой уверенностью" not in n]
    return head + (" Ещё: " + "; ".join(rest) + "." if rest else "")


# -- the Markdown of a sheet --------------------------------------------------------------------------------------------------

_TIER_MARK: Final[Mapping[str, str]] = {TIER_TEXT: "", TIER_IMAGE: " (с изображения)", TIER_UNVERIFIED: " (не подтверждено)"}


def _fields(fields: Sequence[Mapping[str, Any]]) -> str:
    parts = []
    for f in fields:
        unit = f" {f['unit']}" if f.get("unit") else ""
        parts.append(
            f"{f['name']}: {f['before'] or '—'}{_TIER_MARK[f.get('was_tier', TIER_TEXT)] if f['before'] else ''} → "
            f"{f['after'] or '—'}{_TIER_MARK[f.get('now_tier', TIER_TEXT)] if f['after'] else ''}{unit}"
        )
    return "; ".join(parts)


def sheet_markdown(
    header: Mapping[str, Any], description: Mapping[str, Any], *, declared: Sequence[Mapping[str, Any]] = (), state: str | None = None,
) -> str:
    """The Markdown of one sheet (``report.py:367-388``). ``header`` is ``{title, page_a, page_b, label_a, label_b}``. Deterministic: the
    same description and header give the same bytes."""
    shown = state or description["state"]
    lines = [
        f"### {header.get('title') or header.get('sheet_pair_id')} · A стр. PDF {header.get('page_a')} → B стр. PDF {header.get('page_b')}", "",
        f"A: {header.get('label_a')}. B: {header.get('label_b')}.", f"Состояние: {STATE_LABELS[shown]}.", "",
    ]
    single = description.get("single")
    if single:
        lines += [f"**{single['label']}.** {single['sheet_kind']}", "", f"{single['summary']}{_TIER_MARK[single['summary_tier']]}", ""]
        for obj in single["objects"]:
            detail = f": {obj['detail']}{_TIER_MARK[obj['tier']]}" if obj["detail"] else ""
            lines.append(f"- {obj['name']}{detail}")
        if single["marks"]:
            lines += ["", "Марки: " + ", ".join(single["marks"])]
        if single["limitation"]:
            lines += ["", f"Неясно: {single['limitation']}"]
    for number, change in enumerate(description.get("changes") or [], 1):
        lines.append(f"{number}. **{change['object']}** — {change['summary']}")
        for member in change.get("members") or []:
            place = f" ({member['place']})" if member.get("place") else ""
            lines.append(f"   - {member['object']}{place}: {_fields(member['fields'])}")
        if change.get("fields") and not change.get("members"):
            lines.append(f"   - {_fields(change['fields'])}")
        if change.get("limitation"):
            lines.append(f"   - Неясно: {change['limitation']}")
        unsupported = change.get("unsupported") or {}
        if unsupported.get("summary"):
            lines.append("   - Не подтверждено данными листа: " + ", ".join(unsupported["summary"]))
        if unsupported.get("place"):
            lines.append("   - Место не подтверждено данными листа: " + ", ".join(unsupported["place"]))
    if description.get("unresolved"):
        lines += ["", "**Требует уточнения**", ""]
        for item in description["unresolved"]:
            place = f" ({item['place']})" if item.get("place") else ""
            lines.append(f"- {item['object']}{place}: {item['question']}")
    if not description.get("changes") and not description.get("unresolved") and not single:
        lines.append(f"_{STATE_LABELS[shown]}._")
    if declared:
        lines += ["", "Заявлено проектировщиком в разрешении: " + "; ".join(str(d["text"]) for d in declared)]
    lines += ["", f"_{description.get('disclaimer') or DISCLAIMER}_"]
    if description.get("recorded"):
        lines.append(f"_{RECORDED_NOTICE}_")
    lines.append("")
    return "\n".join(lines)


def weakest_tier(description: Mapping[str, Any]) -> str:
    """The weakest tier among the values of a description (``from_text`` when it holds none)."""
    return weakest([c.get("confirmation", TIER_TEXT) for c in description.get("changes") or []])
