"""The registry of facts of a summary: every item «- …» of a sheet or of a transition has an ID and a passport (`CMP-VC-REPORT-01`).

A port of the original's ``md_report/facts.py`` at ``23f379fd`` (223 lines). A fact is the item line of a sheet or of a transition; its ID is
the ordinal of the item in the file («Ф0001»), so parsing one file twice gives the same IDs. For a summary made by the program from stored
data the passport is completed from the **record** of the line (the fields «было/стало», members, questions, the confirmation tier);
for an uploaded MD the passport comes from the structure of the file alone. The model never writes a source: it names IDs, and the
program fills the sheet, the pages and the line from the passport.
"""

from __future__ import annotations

import re
from typing import Any, Final

__all__ = [
    "CONFIRMATION",
    "EXTRA_CHARS",
    "FACT_ID",
    "TEXT_CHARS",
    "build",
    "in_ranges",
    "index",
    "model_line",
    "normalize_id",
    "passport",
]

FACT_ID = re.compile(r"[ФF]\d{4}")  # facts.py:16
# «Старая: л.1 (стр. PDF 50), л.2 (стр. PDF 51); новая: л.1 (стр. PDF 52). …» -- a position of the whole specification (facts.py:17-20).
_LOC_TOKEN = r"(?:л\.[^\s(,;]+(?: \(стр\. PDF \d+\))?|стр\. PDF \d+|—)"
_LOC_LIST = rf"{_LOC_TOKEN}(?:, {_LOC_TOKEN})*"
SPEC_LOC = re.compile(rf"^Старая: ({_LOC_LIST}); новая: ({_LOC_LIST})\.(?:\s|$)")
LOC = re.compile(r"(?:л\.([^\s(,]+))?\s*(?:\(?стр\. PDF (\d+)\)?)?")
DESIGNATION = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё.\-/]*-?\d[\w.\-/]*")
#: How firmly a fact stands (facts.py:23-35). The Russian labels are shown in the PDF of the analytic kind.
CONFIRMATION: Final[dict[str, str]] = {
    "spec_text": "сравнение текста спецификации (программа)",
    "text": "ИИ-описание листа; значения есть в текстовом слое листа",
    "image": "ИИ-описание листа; значения прочитаны по изображению",
    "unverified": "ИИ-описание листа; значение не подтверждено",
    "question": "вопрос ИИ — не установлено",
    "ai_questions": "вопрос ИИ — не установлено",
    "single": "ИИ-описание добавленного/удалённого листа",
    "summary": "по тексту сводки (исходная запись не передана)",
    "gap": "описания нет",
}
SHORT_CONF: Final[dict[str, str]] = {
    "spec_text": "СО-текст", "text": "текст", "image": "изобр.", "unverified": "не подтв.", "question": "вопрос",
    "ai_questions": "вопрос", "single": "лист", "summary": "сводка", "gap": "нет описания",
}
TEXT_CHARS: Final[int] = 160  # facts.py:182 -- the text of an item in the composer's task: for recognition, the meaning is in the checked wordings
EXTRA_CHARS: Final[int] = 220  # facts.py:183 -- the stored values of a record that the text lacks, one line per kind


def normalize_id(value: str) -> str:
    """The Latin F for «Ф» is the same ID (facts.py:36-39)."""
    value = (value or "").strip()
    return "Ф" + value[1:] if value[:1] in ("F", "f") else value


def _locs(text: str) -> tuple[list[str], list[int]]:
    sheets: list[str] = []
    pages: list[int] = []
    for part in text.split(","):
        match = LOC.search(part.strip())
        if not match:
            continue
        if match.group(1):
            sheets.append(f"л.{match.group(1)}")
        if match.group(2):
            pages.append(int(match.group(2)))
    return sheets, pages


def _plain(line: str) -> str:
    text = re.sub(r"^\s*-\s+", "", line)
    return re.sub(r"\*\*|__|`+", "", text).strip()


def _identity(record: dict[str, Any] | None, text: str) -> str | None:
    """The designation of one line or apparatus for the chains «was → became → became» (facts.py:60-71): only with a letter-and-digit
    designation (ЩР-1.2, гр.3, ВРУ-1). Without one, the sameness of the object is not confirmed."""
    if record and record.get("kind") == "ai_change":
        name = f"{record.get('object') or ''}"
    elif record:
        return None
    else:
        match = re.match(r"^\*\*(.+?)\*\*", re.sub(r"^\s*-\s+", "", text))
        name = match.group(1) if match else ""
    found = DESIGNATION.findall(name)
    return re.sub(r"\s+", " ", name).strip().casefold() if found else None


def build(manifest: dict[str, Any], lines: list[str], records: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """The facts in the order of the file and the pointer «line → ID» (facts.py:74-127)."""
    records = records or {}
    facts: list[dict[str, Any]] = []
    for transition in manifest["transitions"]:
        sheets = transition["sheets"]
        for number in range(transition["line_start"], transition["line_end"] + 1):
            raw = lines[number - 1]
            if not raw.strip().startswith("- "):
                continue
            sheet = next((x for x in sheets if x["line_start"] <= number <= x["line_end"]), None)
            text = _plain(raw)
            record = records.get(str(number))
            kind = (record or {}).get("kind") or (
                "question" if text.startswith("_Требует уточнения") else "gap" if re.match(r"^_.*_$", text) else "summary"
            )
            # An item of the summary's own form «**объект** — суть» with no record (an uploaded file, or data that moved since the summary was
            # made) is read as a described change whose values are its text: the client report can then write about it, and the check holds every
            # value it cites to that text. `[own design]`: the original's uploaded file reached the client kind only through its own records.
            inferred = None
            if not record and kind == "summary":
                shaped = re.match(r"^\*\*(.+?)\*\*\s+[—-]\s+(.+)$", re.sub(r"^\s*-\s+", "", raw.strip()))
                if shaped:
                    kind, inferred = "ai_change", {"object": shaped.group(1).strip()}
            pages_a = [p for p in [(sheet or {}).get("a_page")] if p]
            pages_b = [p for p in [(sheet or {}).get("b_page")] if p]
            sheet_a = sheet_b = [sheet["sheet"]] if sheet and sheet.get("sheet") else []
            spec = SPEC_LOC.match(text)
            if kind == "spec_entry" or spec:
                if record and kind == "spec_entry":
                    sheet_a = [f"л.{x['sheet']}" for x in record.get("old_locations") or [] if x.get("sheet")]
                    sheet_b = [f"л.{x['sheet']}" for x in record.get("new_locations") or [] if x.get("sheet")]
                    pages_a, pages_b = list(record.get("old_pages") or []), list(record.get("new_pages") or [])
                elif spec:
                    sheet_a, pages_a = _locs(spec.group(1))
                    sheet_b, pages_b = _locs(spec.group(2))
                    kind = "spec_entry"
                text_conf = "spec_text" if record else "summary"
            elif kind == "ai_change":
                text_conf = (record or {}).get("confirmation") or ("summary" if inferred else "text")
            elif kind == "ai_questions":
                text_conf = "question"
            elif kind == "ai_single":
                text_conf = "single"
            else:
                text_conf = kind if kind in CONFIRMATION else "summary"
            if record and kind in ("ai_change", "ai_single", "ai_questions"):
                pages_a = [record["a_page"]] if record.get("a_page") else pages_a
                pages_b = [record["b_page"]] if record.get("b_page") else pages_b
            confirmation = CONFIRMATION.get(text_conf, text_conf)
            if (record or {}).get("unclear"):
                confirmation += "; есть неясность"
            facts.append({
                "fact_id": f"Ф{len(facts) + 1:04d}", "md_line": number, "transition_id": transition["transition_id"],
                "transition": transition["label"], "sheet_id": (sheet or {}).get("sheet_id"),
                "sheet": " · ".join(dict.fromkeys(sheet_a + sheet_b)) or ((sheet or {}).get("sheet") or None),
                "sheet_title": (sheet or {}).get("title") or ((sheet or {}).get("heading") or "").lstrip("# ").strip() or None,
                "pages_a": pages_a, "pages_b": pages_b, "kind": kind, "confirmation_code": text_conf,
                "confirmation": confirmation, "text": text, "identity": _identity(record, raw),
                "record": _record_ref(record), "details": _details(record) or inferred,
            })
    by_line = {f["md_line"]: f["fact_id"] for f in facts}
    return {"facts": facts, "by_line": by_line, "with_records": bool(records), "total": len(facts)}


def _record_ref(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """The address of the source record (for the passport and the export), without values."""
    if not record:
        return None
    keys = ("kind", "run_id", "job_id", "spid", "change_id", "entry_id")
    return {k: record[k] for k in keys if record.get(k)}


def _details(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """The stored values of a record: the fields «было/стало», members, questions, limitations."""
    if not record:
        return None
    keys = ("object", "place", "change_kind", "fields", "members", "mapping", "limitation", "questions", "summary",
            "sheet_kind", "single")
    out = {k: record[k] for k in keys if record.get(k)}
    return out or None


def index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f["fact_id"]: f for f in registry["facts"]}


def in_ranges(registry: dict[str, Any], refs: list[dict[str, int]]) -> list[str]:
    """IDs of the facts whose lines fall into the ranges ``md_from``–``md_to`` (facts.py:151-157)."""
    out: list[str] = []
    for fact in registry["facts"]:
        if any(r["md_from"] <= fact["md_line"] <= r["md_to"] for r in refs) and fact["fact_id"] not in out:
            out.append(fact["fact_id"])
    return out


def _norm(value: str) -> str:
    return re.sub(r"[\s«»\"']+", "", (value or "").casefold()).replace("x", "×").replace("х", "×")


def _fmt_fields(fields: list[dict[str, Any]], text: str) -> str:
    """Fields «было → стало» that are not in the item's text (a repeat of the text's values is not passed on) -- facts.py:168-179."""
    seen = _norm(text)
    out = []
    for field in fields or []:
        before, after = field.get("before") or "", field.get("after") or ""
        unclear = field.get("certainty", "confirmed") != "confirmed"
        if not unclear and _norm(before) in seen and _norm(after) in seen:
            continue
        unit = f" {field['unit']}" if field.get("unit") else ""
        out.append(f"{field.get('name') or 'значение'}: {before or '—'} → {after or '—'}{unit}" + (" (неясно)" if unclear else ""))
    return "; ".join(out)


def _cut(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def model_line(fact: dict[str, Any]) -> str:
    """The line of a fact for the composer's task (facts.py:191-217): ID, transition, sheet, pages A→B, confirmation, the start of the
    text and the stored values the text lacks. «обозн.» -- the object has a letter-and-digit designation, the ground of a chain."""
    where = fact["transition"] + (f" {fact['sheet']}" if fact.get("sheet") else "")
    pages = "/".join(map(str, fact["pages_a"])) or "—", "/".join(map(str, fact["pages_b"])) or "—"
    conf = SHORT_CONF.get(fact.get("confirmation_code"), fact.get("confirmation_code") or "")
    if "неясность" in (fact.get("confirmation") or ""):
        conf += ", неясно"
    if fact.get("identity"):
        conf += ", обозн."
    shown = _cut(fact["text"], TEXT_CHARS)
    row = f"{fact['fact_id']} [{where}; стр. {pages[0]}→{pages[1]}; {conf}] {shown}"
    details = fact.get("details") or {}
    extra = []
    fields = _fmt_fields(details.get("fields"), shown)
    if fields:
        extra.append("поля: " + fields)
    members = "; ".join(
        f"{m.get('object')}: {mf}" for m in details.get("members") or [] for mf in [_fmt_fields(m.get("fields"), shown)] if mf
    )
    if members:
        extra.append("члены: " + members)
    if details.get("questions"):
        extra.append("вопросы: " + " | ".join(f"{q.get('object')}: {q.get('question')}" for q in details["questions"]))
    if details.get("limitation"):
        extra.append("ограничение: " + details["limitation"])
    return row + "".join(f"\n  {_cut(x, EXTRA_CHARS)}" for x in extra)


def passport(fact: dict[str, Any]) -> dict[str, Any]:
    """The passport of a fact for the report and the PDF (facts.py:220-223)."""
    return {k: fact.get(k) for k in (
        "fact_id", "md_line", "transition", "sheet", "sheet_title", "pages_a", "pages_b", "confirmation", "text", "record",
    )}
