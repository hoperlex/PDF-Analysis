"""The intake of an MD summary: header, transitions, sheets and items with the line numbers of the file (`CMP-VC-REPORT-01`).

A port of the original's ``md_report/parse.py`` at commit ``23f379fd`` of ``SU10KAZ/PDF-proverka`` (``backend/app/services/
version_comparison_ai/md_report/parse.py``, 266 lines). The format is the one ``summary.py`` (our ``build_summary``) writes -- the same
as the original's ``sheet_changes/series_summary.py`` -- but the parse does not trust the counters of the header: the structure is
inventoried again. The line number is the ordinal of the line in the file counted from 1 by ``\\n``; a BOM and ``\\r`` are stripped only in
the working copy and never shift a reference. What is not recognised is never read as «no changes»: it lands in ``issues`` and in the
blocks of the analysis.

Regular expressions are the original's, line for line: ``H1`` ``parse.py:16``, ``TRANSITION`` ``:18``, ``H3`` ``:19``, ``PAGES`` ``:20``,
``SINGLE`` ``:23``, ``SHEET_LABEL`` ``:24``, ``FILES`` ``:26``, ``ITALIC`` ``:27``, ``NO_CONTENT`` ``:28``, ``INCOMPLETE_MARKERS``
``:30-32``, ``UNCLEAR`` ``:33``, ``REGISTRY_*`` ``:35-37``.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Final

__all__ = [
    "INCOMPLETE_MARKERS",
    "NO_CONTENT",
    "REGISTRY_TITLE",
    "decode",
    "locate",
    "parse",
    "split_lines",
]

H1 = re.compile(r"^#\s+(.+?)\s*$")
TRANSITION = re.compile(r"^##\s+(\d+)\.\s+(?:(.+?):\s+)?(.+?)\s+→\s+(.+?)\s*$")
H3 = re.compile(r"^###\s+(.+?)\s*$")
PAGES = re.compile(r"\s*\(((?:A стр\. PDF \d+)?(?:\s*→\s*)?(?:B стр\. PDF \d+)?)\)\s*$")
PAGE_A = re.compile(r"A стр\. PDF (\d+)")
PAGE_B = re.compile(r"B стр\. PDF (\d+)")
SINGLE = re.compile(r"^(Лист добавлен|Лист удалён):\s*(.+)$")
SHEET_LABEL = re.compile(r"^((?:СО\s+)?л\.\s*[^\s·]+)\s+·\s+")
DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
FILES = re.compile(r"^A:\s.*файл «(.*?)»\.\s+B:\s.*файл «(.*?)»\.?\s*$")
ITALIC = re.compile(r"^-?\s*_(.+?)_\s*$")
NO_CONTENT: Final[str] = "изменений содержания нет"
#: Marks of the summary that there is no description: a gap in the source, not an absence of changes.
INCOMPLETE_MARKERS: Final[tuple[str, ...]] = (
    "не досчитано", "ошибка ИИ", "не отправлен", "ещё не описан", "описывается", "не описан (отменено)",
    "ИИ-описание не запускалось", "не запускалось", "Спецификация не описана",
)
UNCLEAR = re.compile(r"Требует уточнения:\s*(\d+)")
#: The coverage registry at the end of the summary: not a transition, not sent to the analysis, read apart.
REGISTRY_TITLE: Final[str] = "## Реестр покрытия"
REGISTRY_ROW = re.compile(r"^-\s+(\S+?→\S+?):\s+листов\s+(\d+)\s+—\s+(.+?)\.?\s*$")
REGISTRY_SUB = re.compile(r"^\s+-\s+(не обработано|неоднозначно|отметка документа):\s*(.+)$")


def decode(raw: bytes) -> str:
    """UTF-8 text (a BOM is allowed). Another encoding is a refusal: a silent re-encoding would distort the quotes (``parse.py:40-45``)."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"the file is not UTF-8 (byte {exc.start})") from exc


def split_lines(text: str) -> list[str]:
    """The lines of the original split by ``\\n``; a closing newline gives no empty last line (``parse.py:48-53``)."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def _iso(label: str) -> str | None:
    found = DATE.findall(label or "")
    if not found:
        return None
    day, month, year = found[-1]
    return f"{year}-{month}-{day}"


def _version(label: str) -> str:
    """The short name of a version: the first word of its label («V3», «(1)»); the whole label otherwise (``parse.py:64-67``)."""
    head = (label or "").split()
    return head[0] if head else (label or "")


def _sha(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _sheet(title_line: str, number: int) -> dict[str, Any]:
    text = H3.match(title_line).group(1)  # type: ignore[union-attr]
    kind = "pair"
    single = SINGLE.match(text)
    if single:
        kind = "added" if single.group(1) == "Лист добавлен" else "removed"
        text = single.group(2)
    page_a = page_b = None
    pages = PAGES.search(text)
    if pages:
        inner = pages.group(1)
        found_a, found_b = PAGE_A.search(inner), PAGE_B.search(inner)
        page_a = int(found_a.group(1)) if found_a else None
        page_b = int(found_b.group(1)) if found_b else None
        text = text[:pages.start()]
    labels: list[str] = []
    rest = text
    while True:
        label = SHEET_LABEL.match(rest)
        if not label:
            break
        labels.append(re.sub(r"\s+", " ", label.group(1)))
        rest = rest[label.end():]
    return {
        "heading": title_line.strip(), "kind": kind, "sheet": " · ".join(labels) or None, "title": rest.strip(),
        "a_page": page_a, "b_page": page_b, "line_start": number, "line_end": number, "items": 0, "unclear": 0,
        "not_described": [],
    }


def _registry_line(section: dict[str, Any], line: str, number: int) -> None:
    row = REGISTRY_ROW.match(line)
    if row:
        counts: dict[str, int] = {}
        for part in row.group(3).split(";"):
            count = re.match(r"^\s*(.+?)\s+(\d+)\s*$", part)
            if count:
                counts[count.group(1)] = int(count.group(2))
        section["rows"].append({
            "label": row.group(1), "sheets_total": int(row.group(2)), "counts": counts, "line": number, "details": [],
        })
        return
    sub = REGISTRY_SUB.match(line)
    if sub and section["rows"]:
        section["rows"][-1]["details"].append({"kind": sub.group(1), "text": sub.group(2).strip(), "line": number})


def parse(raw: bytes, filename: str = "") -> dict[str, Any]:
    """The manifest of an MD summary (``parse.py:117-257``): ``transitions`` (each with ``transition_id`` ``T01``…, ``label`` ``V1→V2``,
    ``sheets``, ``items``, ``chars``, ``sha256``), ``registry``, ``issues`` and the ``inventory``. ``ValueError`` for a file that is not UTF-8."""
    text = decode(raw)
    lines = split_lines(text)
    count = len(lines)
    issues: list[dict[str, Any]] = []
    title = code = None
    sections: list[dict[str, Any]] = []
    first_h2 = None
    for number, line in enumerate(lines, 1):
        if line.startswith("## ") or line == "##":
            first_h2 = first_h2 or number
            if line.strip() == REGISTRY_TITLE:
                sections.append({
                    "kind": "registry", "heading": line.strip(), "line_start": number, "line_end": number,
                    "rows": [], "sheets": [], "notes": [], "items": 0,
                })
                continue
            match = TRANSITION.match(line)
            if match:
                a_label, b_label = match.group(3).strip(), match.group(4).strip()
                sections.append({
                    "kind": "transition", "number": int(match.group(1)), "code": (match.group(2) or "").strip() or None,
                    "heading": line.strip(), "a_label": a_label, "b_label": b_label,
                    "from_version": _version(a_label), "to_version": _version(b_label),
                    "from_date": _iso(a_label), "to_date": _iso(b_label), "a_file": None, "b_file": None,
                    "line_start": number, "line_end": number, "sheets": [], "notes": [],
                    "explicit_no_content_changes": False, "source_incomplete": [], "items": 0, "unclear": 0,
                })
            else:
                sections.append({
                    "kind": "unknown", "heading": line.strip(), "line_start": number, "line_end": number,
                    "sheets": [], "notes": [], "items": 0,
                })
                issues.append({
                    "code": "UNRECOGNIZED_SECTION", "line": number,
                    "text": f"a section is not recognised as a transition A → B: «{line.strip()[:120]}»",
                })
            continue
        if not sections:
            heading = H1.match(line)
            if heading and title is None:
                title = heading.group(1)
                named = re.match(r"^Сводка изменений\s+(.+)$", title)
                code = named.group(1).strip() if named else None
            continue
        section = sections[-1]
        section["line_end"] = number
        if section["kind"] == "registry":
            _registry_line(section, line, number)
            continue
        if H3.match(line):
            section["sheets"].append(_sheet(line, number))
            continue
        current = section["sheets"][-1] if section["sheets"] else None
        if current:
            current["line_end"] = number
        stripped = line.strip()
        if not stripped:
            continue
        if section["kind"] == "transition" and not current:
            files = FILES.match(stripped)
            if files:
                section["a_file"], section["b_file"] = files.group(1), files.group(2)
                continue
        italic = ITALIC.match(stripped)
        note = italic.group(1) if italic else None
        if note:
            if current:
                unclear = UNCLEAR.search(note)
                if unclear:
                    current["unclear"] += int(unclear.group(1))
                    section["unclear"] = section.get("unclear", 0) + int(unclear.group(1))
                    continue
            if any(mark in note for mark in INCOMPLETE_MARKERS):
                where = {"line": number, "text": note, "sheet": current["heading"] if current else None}
                (current["not_described"] if current else section["notes"]).append(where)
                if section["kind"] == "transition":
                    section["source_incomplete"].append(where)
                continue
            if not current:
                section["notes"].append({"line": number, "text": note})
                if NO_CONTENT in note and section["kind"] == "transition":
                    section["explicit_no_content_changes"] = True
                continue
        if stripped.startswith("- "):
            section["items"] += 1
            if current:
                current["items"] += 1
            continue
        if not current:
            section["notes"].append({"line": number, "text": stripped[:200]})
    header_end = (first_h2 - 1) if first_h2 else count
    transitions = [s for s in sections if s["kind"] == "transition"]
    for position, transition in enumerate(transitions, 1):
        transition["transition_id"] = f"T{position:02d}"
        transition["label"] = f"{transition['from_version']}→{transition['to_version']}"
        for index, sheet in enumerate(transition["sheets"], 1):
            sheet["sheet_id"] = f"{transition['transition_id']}-S{index:03d}"
        transition["chars"] = sum(
            len(lines[x - 1]) + 1 for x in range(transition["line_start"], transition["line_end"] + 1)
        )
        transition["sha256"] = _sha(lines[transition["line_start"] - 1:transition["line_end"]])
        if transition["explicit_no_content_changes"] and (transition["sheets"] or transition["items"]):
            issues.append({
                "code": "NO_CHANGES_WITH_CONTENT", "line": transition["line_start"],
                "text": f"{transition['label']}: marked «no changes» but has sheets or items",
            })
        if (not transition["explicit_no_content_changes"] and not transition["sheets"] and not transition["items"]
                and not transition["source_incomplete"]):
            issues.append({
                "code": "EMPTY_TRANSITION", "line": transition["line_start"],
                "text": f"{transition['label']}: neither sheets nor a mark of no changes",
            })
        for sheet in transition["sheets"]:
            # A sheet with questions only («Требует уточнения: N») is not empty: it holds an uncertainty.
            if not sheet["items"] and not sheet["not_described"] and not sheet["unclear"]:
                issues.append({
                    "code": "EMPTY_SHEET", "line": sheet["line_start"],
                    "text": f"{transition['label']}: a sheet without items — «{sheet['heading'][:100]}»",
                })
    for unknown in (s for s in sections if s["kind"] == "unknown"):
        unknown["section_id"] = f"U{unknown['line_start']:05d}"
    # The order of versions is the document's. A gap in the chain and a repeated pair are reported; pairs are not completed.
    seen: dict[tuple[str, str], str] = {}
    for previous, following in zip(transitions, transitions[1:]):
        if previous["b_label"] != following["a_label"]:
            issues.append({
                "code": "CHAIN_GAP", "line": following["line_start"],
                "text": f"after {previous['label']} comes {following['label']}: B of the previous «{previous['b_label']}» "
                        f"is not A of the next «{following['a_label']}»",
            })
    for transition in transitions:
        key = (transition["a_label"], transition["b_label"])
        if key in seen:
            issues.append({
                "code": "DUPLICATE_PAIR", "line": transition["line_start"],
                "text": f"the pair {transition['label']} repeats (it was in {seen[key]})",
            })
        seen.setdefault(key, transition["transition_id"])
        if transition["source_incomplete"]:
            issues.append({
                "code": "SOURCE_INCOMPLETE", "line": transition["line_start"],
                "text": f"{transition['label']}: the summary has places with no description "
                        f"({len(transition['source_incomplete'])})",
            })
    codes = {t["code"] for t in transitions if t.get("code")}
    if not code and len(codes) == 1:
        code = next(iter(codes))
    if not transitions:
        issues.append({"code": "NO_TRANSITIONS", "line": 1, "text": "the file holds no transition A → B"})
    return {
        "filename": filename, "title": title, "project_code": code, "lines_total": count,
        "chars_total": sum(len(x) + 1 for x in lines),
        "header": {"line_start": 1, "line_end": header_end, "text": "\n".join(lines[:header_end])},
        "transitions": transitions, "unknown_sections": [s for s in sections if s["kind"] == "unknown"],
        "registry": next(
            ({k: s[k] for k in ("heading", "line_start", "line_end", "rows")} for s in sections if s["kind"] == "registry"),
            None,
        ),
        "issues": issues,
        "inventory": {
            "transitions": len(transitions), "sheets": sum(len(t["sheets"]) for t in transitions),
            "items": sum(t["items"] for t in transitions), "unclear": sum(t.get("unclear", 0) for t in transitions),
            "explicit_no_content_changes": sum(1 for t in transitions if t["explicit_no_content_changes"]),
            "with_source_gaps": sum(1 for t in transitions if t["source_incomplete"]),
        },
    }


def locate(manifest: dict[str, Any], line: int) -> dict[str, Any]:
    """The transition and the sheet a line of the original belongs to (``parse.py:260-266``)."""
    for transition in manifest["transitions"]:
        if transition["line_start"] <= line <= transition["line_end"]:
            sheet = next((s for s in transition["sheets"] if s["line_start"] <= line <= s["line_end"]), None)
            return {"transition": transition, "sheet": sheet}
    return {"transition": None, "sheet": None}
