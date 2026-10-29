"""The deterministic MD summary of a series: «Сводка изменений (MD)» (`CMP-VC-REPORT-01`, plan 1.1, `streamComparisonSeriesSummary`).

The original's ``sheet_changes/series_summary.py`` at commit ``23f379fd`` (399 lines, ``SU10KAZ/PDF-proverka``) is the model: one Markdown
file, from the first transition to the last, **no model call**; per transition the cipher, the versions A and B and their files
(``series_summary.py:243-246``), per sheet the number, the title and the PDF pages of both versions (``_sheet_head``, ``:44-52``), from a change
the main thing -- the object and the essence «было → стало» (``:305``) -- while «Неясно», the fields and the questions stay in the portal, in
the summary only the **count** of questions of a sheet (``:306-307``); the «Реестр покрытия» at the end in six categories (``:34-36``,
``_registry_lines`` ``:170-190``), after the transitions so that the line numbers of the transitions do not depend on it.

The file is **reproducible**: the same stored data give the same bytes -- the time in the header is the time of the last data, never the time
of the making (``:9-13``), here in UTC so that it does not depend on the host's zone. Besides the text :func:`build_summary` returns the
**passport of the lines** (``records``: line number → the stored record with its fields, members and questions) and the coverage of the
transitions (``coverage``), the two things the fact registry and the PDF need.

What the new data adds to the original's: the engine's own verdict of the transition (``series/verdict.py``), a line for every listed sheet
with the engine's status, the tiers of the values of a change («с изображения», «не подтверждено») and the mark that the text of an AI
description is not confirmed by an engineer, a mark on a transition that rests on an accepted AI link of two sheets, and the
recorded-answer mark. A sheet with no stored description reads «ИИ-описание не запускалось» (one of the parse's incomplete marks), never
«no changes». Not ported: the permit-stamp notes of ``_doc_marks`` (``:79-86``), because the stored description carries them in ``declared``
and this lane does not read the permit; the category «СО целиком» counts only the specification sheets that the whole comparison names.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final

__all__ = [
    "AiChange",
    "COVERAGE",
    "MARK_UNCONFIRMED",
    "REGISTRY_TITLE",
    "SheetDescription",
    "SheetInfo",
    "SpecChangeInfo",
    "SpecInfo",
    "Summary",
    "SummaryData",
    "TransitionInfo",
    "VersionInfo",
    "build_summary",
    "verdict_text",
]

REGISTRY_TITLE: Final[str] = "## Реестр покрытия"
#: The categories of the coverage of the sheets of a transition; every sheet is in exactly one (series_summary.py:34-36).
COVERAGE: Final[tuple[tuple[str, str], ...]] = (
    ("engine_same", "совпадает по движку"), ("service_only", "только служебное"), ("ai_described", "описано ИИ"),
    ("spec_whole", "СО целиком"), ("ambiguous", "неоднозначно"), ("not_processed", "не обработано"),
)
MARK_UNCONFIRMED: Final[str] = "не подтверждено инженером"
NOT_DESCRIBED: Final[str] = "ИИ-описание не запускалось"
#: Statuses of a sheet pair that are listed in the summary: the others (``same``, ``same_zones_changed``) are not described (SC_SKIP_STATUSES).
LISTED_STATUSES: Final[frozenset[str]] = frozenset({"different", "needs_review", "added", "removed", "unmatched"})
_STATUS_TEXT: Final[Mapping[str, str]] = {
    "different": "есть отличия по сравнению движка", "needs_review": "нужна проверка (результат сравнения неоднозначен)",
    "unmatched": "лист не сопоставлен", "added": "лист добавлен", "removed": "лист удалён",
    "same": "совпадает по движку", "same_zones_changed": "основное содержание совпадает, изменены служебные зоны",
}
_TIER_TEXT: Final[Mapping[str, str]] = {"from_text": "", "from_image": "с изображения", "unverified": "не подтверждено"}
#: The confirmation code of a record (facts.CONFIRMATION): the tier of the weaker value of a change.
_TIER_CODE: Final[Mapping[str, str]] = {"from_text": "text", "from_image": "image", "unverified": "unverified"}
_FIELD_LABELS: Final[Mapping[str, str]] = {
    "pos": "Поз.", "name": "Наименование", "mark": "Марка", "code": "Код", "supplier": "Поставщик", "unit": "Ед. изм.",
    "quantity": "Количество", "mass": "Масса", "note": "Примечание",
}


def _one_line(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ------------------------------------------------------------------ the input (plain data, no database)

@dataclass(frozen=True, slots=True)
class VersionInfo:
    ordinal: int
    file_name: str | None = None

    @property
    def label(self) -> str:
        """The label of a version: its first word is the short name the parse reads («V3»), the file is apart (parse.py:64-67)."""
        return f"V{self.ordinal}"


@dataclass(frozen=True, slots=True)
class AiChange:
    """One change of a sheet description (``ComparisonAiChange``)."""

    change_id: str
    object_name: str
    certainty: str = "confirmed"
    kind: str | None = None
    place: str | None = None
    was: str | None = None
    now: str | None = None
    was_tier: str | None = None
    now_tier: str | None = None
    limitation: str | None = None


@dataclass(frozen=True, slots=True)
class SheetDescription:
    """The stored AI description of a sheet pair (or of an added or removed page): a state, the changes and the questions."""

    state: str
    changes: tuple[AiChange, ...] = ()
    unresolved: tuple[str, ...] = ()
    recorded: bool = False
    model: str | None = None
    created_at: datetime | None = None
    #: the one-sentence essence of an added or removed page, when the description holds one
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class SheetInfo:
    pair_no: int
    state: str
    status: str | None
    a_page: int | None
    b_page: int | None
    a_sheet: str | None = None
    b_sheet: str | None = None
    a_title: str | None = None
    b_title: str | None = None
    ai_dependent: bool = False
    description: SheetDescription | None = None
    #: this sheet is a specification sheet of the whole comparison of the transition
    in_whole_specification: bool = False


@dataclass(frozen=True, slots=True)
class SpecChangeInfo:
    change_id: str
    kind: str
    text: str | None = None
    fields: tuple[tuple[str, str, str], ...] = ()  # (field, was, now)
    old: Mapping[str, Any] | None = None
    new: Mapping[str, Any] | None = None
    old_page: int | None = None
    new_page: int | None = None
    #: the sheet numbers of the pages (the stamp of the page profile), when known
    old_sheet: str | None = None
    new_sheet: str | None = None


@dataclass(frozen=True, slots=True)
class SpecInfo:
    state: str
    changes: tuple[SpecChangeInfo, ...] = ()
    model: str | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TransitionInfo:
    number: int
    state: str
    source: VersionInfo
    target: VersionInfo
    summary: Mapping[str, int] = field(default_factory=dict)
    verdict: tuple[str, ...] = ()
    sheets: tuple[SheetInfo, ...] = ()
    spec: SpecInfo | None = None


@dataclass(frozen=True, slots=True)
class SummaryData:
    code: str
    transitions: tuple[TransitionInfo, ...]
    data_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Summary:
    filename: str
    text: str
    #: line number (as text, from 1) → the stored record of the line
    records: Mapping[str, Mapping[str, Any]]
    coverage: tuple[Mapping[str, Any], ...]
    data_at: str | None
    sheets: int
    changes: int


# ------------------------------------------------------------------ the text of the engine's verdict (series/verdict.py table)

def verdict_text(summary: Mapping[str, int], verdict: Sequence[str]) -> str:
    """The sentence of the transition's deterministic verdict (the original's ``series.py:38-64``): the words are the client's in the
    contract; the summary prints them as the original did."""
    parts: list[str] = []
    for code in verdict:
        if code == "incomplete":
            parts.append("переход досчитан не полностью")
        elif code == "content_same":
            parts.append("основное содержание совпадает")
        elif code == "zones_only":
            parts[-1:] = [f"{parts[-1]}, изменены только служебные зоны"] if parts else ["изменены только служебные зоны"]
        elif code == "different":
            style = summary.get("style_only", 0)
            parts.append(f"есть отличия на {summary.get('different', 0)} л." + (f", из них только оформление линий — {style}" if style else ""))
        elif code == "composition_changed":
            parts.append(f"изменён состав (+{summary.get('added', 0)} / −{summary.get('removed', 0)} л.)")
        elif code == "needs_review":
            parts.append(f"нужна проверка: {summary.get('needs_review', 0)}")
        elif code == "calculation_failed":
            parts.append(f"ошибка расчёта: {summary.get('failed', 0)}")
    return "; ".join(parts)


# ------------------------------------------------------------------ the sheets

def _sheet_title(sheet: SheetInfo) -> str:
    number = sheet.b_sheet or sheet.a_sheet
    title = _one_line(sheet.b_title or sheet.a_title) or f"лист {sheet.pair_no}"
    if number and not re.match(rf"^\s*л\.\s*{re.escape(str(number))}\b", title):
        title = f"л.{number} · {title}"
    return title


def _pages(sheet: SheetInfo) -> str:
    return " → ".join(x for x in (
        f"A стр. PDF {sheet.a_page}" if sheet.a_page else "", f"B стр. PDF {sheet.b_page}" if sheet.b_page else "") if x)


def _sheet_order(sheet: SheetInfo) -> tuple[int, int]:
    return (sheet.b_page or sheet.a_page or 0, sheet.pair_no)


def _listed(sheet: SheetInfo) -> bool:
    return sheet.state != "done" or (sheet.status or "") in LISTED_STATUSES


def _change_record(sheet: SheetInfo, change: AiChange, transition: TransitionInfo) -> dict[str, Any]:
    tiers = [t for t in (change.was_tier, change.now_tier) if t]
    weakest = "unverified" if "unverified" in tiers else "from_image" if "from_image" in tiers else "from_text"
    fields = [{
        "name": change.kind or "значение", "before": change.was or "", "after": change.now or "", "unit": "",
        "certainty": change.certainty, "confirmation": _TIER_CODE[weakest],
    }]
    return {
        "kind": "ai_change", "pair_no": sheet.pair_no, "change_id": change.change_id, "object": _one_line(change.object_name),
        "place": _one_line(change.place), "change_kind": change.kind, "fields": fields, "members": [], "mapping": None,
        "confirmation": _TIER_CODE[weakest], "unclear": change.certainty != "confirmed", "limitation": _one_line(change.limitation),
        "flags": [], "a_page": sheet.a_page, "b_page": sheet.b_page,
    }


def _change_line(change: AiChange) -> str:
    was, now = _one_line(change.was), _one_line(change.now)
    essence = f"{was or 'нет'} → {now or 'нет'}"
    if change.place:
        essence = f"{_one_line(change.place)}: {essence}"
    marks = []
    tiers = {change.was_tier, change.now_tier}
    if "from_image" in tiers:
        marks.append(_TIER_TEXT["from_image"])
    if "unverified" in tiers:
        marks.append(_TIER_TEXT["unverified"])
    if change.certainty != "confirmed":
        marks.append("неясно")
    return f"- **{_one_line(change.object_name)}** — {essence}" + (f" ({', '.join(marks)})" if marks else "")


def _spec_position(position: Mapping[str, Any] | None, keys: Sequence[str] = ("name", "mark", "section", "quantity")) -> str:
    if not position:
        return ""
    parts = []
    for key in keys:
        value = _one_line(str(position.get(key) or ""))
        if not value:
            continue
        label = {"name": "Наименование", "mark": "Марка", "section": "раздел", "quantity": "Количество"}[key]
        parts.append(f"{label} {value}" if key != "quantity" else f"{label}: {value}")
    return "; ".join(parts)


def _spec_line(change: SpecChangeInfo) -> tuple[str, dict[str, Any]]:
    old_pages = [change.old_page] if change.old_page else []
    new_pages = [change.new_page] if change.new_page else []

    def location(page: int | None, sheet: str | None) -> str:
        """``л.5 (стр. PDF 13)`` -- the grammar of the original's location (facts.py:17-20); ``л.?`` when the sheet number is not known."""
        return f"л.{sheet or '?'} (стр. PDF {page})" if page else "—"

    locs_old, locs_new = location(change.old_page, change.old_sheet), location(change.new_page, change.new_sheet)
    if change.old or change.new:
        if change.kind == "added":
            body = "Добавлено: не было → " + _spec_position(change.new)
        elif change.kind == "removed":
            body = "Удалено: " + _spec_position(change.old)
        else:
            # the changed fields follow as «поле: было → стало», so the position itself does not repeat them
            body = _spec_position(change.new or change.old, ("name", "mark", "section"))
            body += "".join(
                f"; {_FIELD_LABELS.get(name, name)}: {_one_line(was) or '—'} → {_one_line(now) or '—'}"
                for name, was, now in change.fields
            )
        text = f"Старая: {locs_old}; новая: {locs_new}. {body}"
    else:
        text = _one_line(change.text) or f"позиция спецификации: {change.kind}"
    kind = {"unclear": "unresolved"}.get(change.kind, change.kind)
    record = {
        "kind": "spec_entry", "entry_id": change.change_id, "change_kind": kind,
        "old_locations": [{"sheet": change.old_sheet}] if change.old_sheet else [],
        "new_locations": [{"sheet": change.new_sheet}] if change.new_sheet else [], "old_pages": old_pages, "new_pages": new_pages,
        "fields": [{"name": n, "before": w, "after": v} for n, w, v in change.fields], "confirmation": "spec_text",
    }
    return f"- {text}", record


# ------------------------------------------------------------------ the builder

def build_summary(data: SummaryData) -> Summary:
    """The summary of a series from plain data. Pure: no database, no clock, no model; the same data give the same bytes."""
    body: list[str] = []
    records: dict[int, dict[str, Any]] = {}  # index in ``body`` (0-based) → record
    coverage: list[dict[str, Any]] = []
    models: set[str] = set()
    totals = {"sheets": 0, "changes": 0}
    code = _one_line(data.code) or "серия"
    for transition in data.transitions:
        a, b = transition.source, transition.target
        body += ["", f"## {transition.number}. {code}: {a.label} → {b.label}", ""]
        if a.file_name or b.file_name:
            body += [f"A: {a.label}, файл «{a.file_name or '—'}». B: {b.label}, файл «{b.file_name or '—'}».", ""]
        verdict = verdict_text(transition.summary, transition.verdict)
        if verdict:
            body += [f"Сравнение движка: {verdict}" + ("" if verdict.endswith(".") else "."), ""]
        if transition.summary.get("ai_dependent"):
            body += [
                f"_Часть пар листов ({transition.summary['ai_dependent']}) опирается на связь, принятую по ответу ИИ: "
                "проверьте сопоставление листов._", "",
            ]
        lines: list[str] = []
        line_records: dict[int, dict[str, Any]] = {}
        described = recorded = False

        def add(line: str, record: dict[str, Any] | None = None) -> None:
            if record is not None:
                line_records[len(lines)] = record
            lines.append(line)

        categories: dict[str, list[SheetInfo]] = {key: [] for key, _ in COVERAGE}
        for sheet in sorted(transition.sheets, key=_sheet_order):
            description = sheet.description
            if sheet.status == "same":
                categories["engine_same"].append(sheet)
            elif sheet.status == "same_zones_changed":
                categories["service_only"].append(sheet)
            elif sheet.in_whole_specification:
                categories["spec_whole"].append(sheet)
            elif description is None:
                categories["not_processed"].append(sheet)
            elif description.state in ("needs_clarification", "partial") or description.unresolved:
                categories["ambiguous"].append(sheet)
            elif description.state == "no_construction_changes" or not description.changes and not description.summary:
                categories["service_only"].append(sheet)
            else:
                categories["ai_described"].append(sheet)
            if not _listed(sheet):
                continue
            if sheet.in_whole_specification:
                continue  # the whole-specification comparison owns all specification output (series_summary.py:258-261)
            single = sheet.status in ("added", "removed")
            if description is not None:
                described = True
                recorded = recorded or description.recorded
                if description.model:
                    models.add(description.model)
            if single:
                kind = "added" if sheet.status == "added" else "removed"
                side, page = ("B", sheet.b_page) if kind == "added" else ("A", sheet.a_page)
                title = _one_line(sheet.b_title if kind == "added" else sheet.a_title) or f"лист {sheet.pair_no}"
                add(f"### {'Лист добавлен' if kind == 'added' else 'Лист удалён'}: {title}" + (f" ({side} стр. PDF {page})" if page else ""))
                add("")
                if description is not None and (description.summary or description.changes):
                    essence = description.summary or "; ".join(_one_line(c.object_name) for c in description.changes)
                    add(f"- лист — {_one_line(essence)}", {
                        "kind": "ai_single", "pair_no": sheet.pair_no, "single": kind, "sheet_kind": None,
                        "summary": _one_line(essence), "a_page": sheet.a_page if kind == "removed" else None,
                        "b_page": sheet.b_page if kind == "added" else None,
                    })
                    totals["sheets"] += 1
                else:
                    add(f"- _{NOT_DESCRIBED}_")
                add("")
                continue
            add(f"### {_sheet_title(sheet)}" + (f" ({_pages(sheet)})" if _pages(sheet) else ""))
            add("")
            engine = _STATUS_TEXT.get(sheet.status or "", "сравнение не завершено")
            add(f"- Сравнение: {engine}.")
            if description is None:
                add(f"- _{NOT_DESCRIBED}_")
            else:
                if description.state == "no_construction_changes" or (not description.changes and not description.unresolved):
                    add("- ИИ: строительных изменений не выявлено.")
                for change in description.changes:
                    add(_change_line(change), _change_record(sheet, change, transition))
                    totals["changes"] += 1
                if description.unresolved:
                    add(
                        f"- _Требует уточнения: {len(description.unresolved)} (вопросы — в портале по этому листу)._",
                        {"kind": "ai_questions", "pair_no": sheet.pair_no, "questions": [
                            {"id": None, "object": "", "place": "", "question": _one_line(q)} for q in description.unresolved
                        ], "a_page": sheet.a_page, "b_page": sheet.b_page},
                    )
                if description.changes or description.unresolved:
                    totals["sheets"] += 1
            add("")
        spec_lines: list[tuple[str, dict[str, Any]]] = []
        spec = transition.spec
        if spec is not None:
            if spec.model:
                models.add(spec.model)
            spec_lines = [_spec_line(c) for c in spec.changes if c.kind in ("changed", "added", "removed", "unclear")]
        if spec_lines:
            add("### Спецификация целиком")
            add("")
            for line, record in spec_lines:
                add(line, record)
            add("")
            totals["changes"] += len(spec_lines)
        if spec is not None and spec.state == "incomplete":
            add("_Спецификация сравнена не полностью: добавления, удаления и отсутствие изменений не опубликованы._")
            add("")
        if not lines:
            # Nothing is listed: either the engine found nothing that changed (the original's «изменений содержания нет», series_summary.py:376-377)
            # or the transition is not finished -- never the first for the second.
            lines = [
                "_По данным сравнения изменений содержания нет._" if "content_same" in transition.verdict
                else "_Сравнение не досчитано: описанных изменений нет._"
            ]
        if described:
            add(f"_Описания листов подготовлены моделью: {MARK_UNCONFIRMED}._")
            if recorded:
                add("_Часть описаний — записанные (тестовые) ответы, не ответы рабочей модели._")
        base = len(body)
        for index, record in line_records.items():
            records[base + index] = record
        body += lines
        coverage.append({
            "index": transition.number - 1, "label": f"{a.label} → {b.label}", "sheets_total": len(transition.sheets),
            "categories": {key: [{"pair_no": s.pair_no, "title": _sheet_title(s)} for s in value] for key, value in categories.items()},
            "complete": not categories["not_processed"],
        })
    when = data.data_at.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC") if data.data_at else None
    head = [
        f"# Сводка изменений {code}", "",
        f"Переходы от первой версии к последней, {len(data.transitions)} шт." + (f" Данные на {when}." if when else "")
        + f" Модель: {', '.join(sorted(models)) or '—'}.",
        f"Описано листов: {totals['sheets']}, изменений: {totals['changes']}.", "",
        "Спецификации приведены по сравнению целиком; остальные листы — по ИИ-описаниям и по сравнению движка. "
        "Каждое изменение проверяйте по указанному листу и страницам PDF. "
        "Подробности (поля «было/стало», «Неясно», вопросы) — в портале, раздел «Сравнение версий». "
        f"Тексты, написанные моделью: {MARK_UNCONFIRMED}.",
    ]
    while body and body[-1] == "":
        body.pop()
    tail = _registry_lines(coverage) if coverage else []
    lines_all = head + body + tail
    shifted = {str(len(head) + index + 1): record for index, record in records.items()}
    safe = re.sub(r"[^0-9A-Za-zА-Яа-яЁё._-]+", "_", code).strip("_") or "серия"
    return Summary(
        filename=f"Сводка_изменений_{safe}.md", text="\n".join(lines_all).rstrip() + "\n", records=shifted,
        coverage=tuple(coverage), data_at=when, sheets=totals["sheets"], changes=totals["changes"],
    )


def _registry_lines(coverage: Sequence[Mapping[str, Any]]) -> list[str]:
    """The «Реестр покрытия» (series_summary.py:170-190): every sheet of a transition in one category, with the reason."""
    out = [
        "", REGISTRY_TITLE, "",
        "Каждый лист перехода — в одной категории: совпадает по движку; только служебное (служебные зоны, отметки, оформление); "
        "описано ИИ; СО целиком (полное сравнение спецификации); неоднозначно (вопросы, частичный разбор); не обработано.", "",
    ]
    for item in coverage:
        a, b = item["label"].split(" → ", 1)
        counts = "; ".join(f"{label} {len(item['categories'][key])}" for key, label in COVERAGE)
        out.append(f"- {a}→{b}: листов {item['sheets_total']} — {counts}.")
        if item["categories"]["not_processed"]:
            out.append("  - не обработано: " + "; ".join(f"{r['title']} ({NOT_DESCRIBED})" for r in item["categories"]["not_processed"]))
        if item["categories"]["ambiguous"]:
            out.append("  - неоднозначно: " + "; ".join(r["title"] for r in item["categories"]["ambiguous"]))
    return out
