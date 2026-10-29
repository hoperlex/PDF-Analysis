"""The program's check of a model's reading of a whole specification (pure Python; `CMP-VC-SPEC-01`, part B).

A port of ``specification_source.validate_extraction`` (PDF-proverka at ``23f379fd``, ``version_comparison/specification_source.py``;
``:N`` below are that file's lines). The model is trusted with nothing it can fabricate: a value is **confirmed** only if the
lines it cites, quoted exactly, contain it; a line of the text is **accounted for** only if some position cites it or it is ignored
for a reason the text bears out; and **one unconfirmed value, one lost line or one malformed answer makes the whole side
incomplete** (``docs/whole_specification_comparison.md`` lines 33-35: «Неподтверждённое значение или потерянная строка делает
сторону неполной»). An incomplete side yields no row at all (``:609``), so nothing of it can ever be compared, added or removed.

What is checked, each as an issue that stops the side:

* the answer has exactly the assigned blocks, each once, in the closed shape (``:341-358``, ``:422-435``);
* every position has a section, a parent, the nine fields as strings, and at least one evidence line whose **quote is an exact
  substring** of that line (``:452-471``) -- a quote the text does not contain is never confirmed;
* every non-empty value is found in its own quotes, whole (a number is not found inside a longer number: ``numeric_safe`` for
  ``pos``, ``code``, ``quantity``, ``mass``), or, for a continued cell, in the cells of the cited table rows (``:472-484``); a
  section or parent named by a position must appear in the text (``:485-490``);
* a line is claimed by one position at most and is not both evidence and ignored (``:549-556``); a duplicate position is refused
  (``:491-494``);
* an ignored line is a header, a separator or a section title that the text bears out; a data-like line, a substantive note, an
  unrecognised header and a blank are refused (``:497-521``, ``:564-567``);
* every data row of a table is extracted as a position and each of its cells appears in it (``:569-582``);
* every non-blank line of every block is accounted for (``:584-597``).

What it adds: the **coverage** the contract carries (blocks, rows, rows unresolved) and the **reason** (an engine-style code) of an
incomplete side.

Imports the standard library only.
"""

from __future__ import annotations

import re
from typing import Any, Final

from .prompt import FIELDS, IGNORE_REASONS

__all__ = ["REASON_ANSWER", "REASON_SOURCE", "check_extraction", "coverage_of"]

#: The reasons of an incomplete side (the contract's ``^[A-Z][A-Z0-9_]{2,63}$``).
REASON_SOURCE: Final[str] = "SPEC_SOURCE_INCOMPLETE"
REASON_ANSWER: Final[str] = "SPEC_ANSWER_UNCONFIRMED"

_NUMERIC_FIELDS: Final[tuple[str, ...]] = ("pos", "code", "quantity", "mass")
_TITLE_HEADER_RE: Final[re.Pattern[str]] = re.compile(r"^(?:спецификация|ведомость|перечень)(?:\s|№|$)", re.IGNORECASE)
#: ``:21-31``.
_HEADER_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "pos": ("поз", "позиция", "поз позиция", "п п", "номер позиции"),
    "name": ("наименование",),
    "mark": ("тип", "марка", "обозначение", "тип марка обозначение"),
    "code": ("код",),
    "supplier": ("поставщик", "завод изготовитель", "завод изготовитель поставщик", "поставщик завод изготовитель"),
    "unit": ("ед изм", "единица измерения", "единица изм"),
    "quantity": ("количество", "кол", "кол во", "колво", "количество кол"),
    "mass": ("масса",),
    "note": ("примечание",),
}


def _norm(value: str) -> str:
    return " ".join(value.split())


def _header_norm(value: str) -> str:
    value = value.lower().replace("ё", "е")
    return _norm(re.sub(r"[^\w]+", " ", value, flags=re.UNICODE))


def _pipe_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _table_header(cells: list[str] | None) -> dict[int, str] | None:
    """``:267-283``: a header maps every non-empty column to exactly one field, and names a position, a name or a quantity."""
    if not cells:
        return None
    columns: dict[int, str] = {}
    for index, cell in enumerate(cells):
        normalized = _header_norm(cell)
        for field, aliases in _HEADER_ALIASES.items():
            if normalized in aliases:
                columns[index] = field
                break
    mapped = set(columns.values())
    nonempty = {i for i, cell in enumerate(cells) if cell.strip()}
    if len(columns) == len(nonempty) and len(mapped) == len(columns) and len(columns) >= 2 and mapped & {"pos", "name", "quantity"}:
        return columns
    return None


def _separator_row(cells: list[str] | None) -> bool:
    return bool(cells) and all(re.fullmatch(r"[:\- =]+", cell or " ") for cell in cells or [])


def _plain_separator(line: str) -> bool:
    return bool(re.fullmatch(r"(?:[-=*_]\s*){3,}", line.strip()))


def _section_norm(value: str) -> str:
    return _norm(re.sub(r"^[#>*`\s]+|[#>*`\s]+$", "", value))


def _contains_cell(value: str, cell: str, *, numeric_safe: bool = False) -> bool:
    """``:299-316``: ``cell`` is in ``value``; for a number, not inside a longer number or word."""
    value_n, cell_n = _norm(value), _norm(cell)
    if not cell_n:
        return True
    start = 0
    while True:
        found = value_n.find(cell_n, start)
        if found < 0:
            return False
        end = found + len(cell_n)
        neighbours = "0123456789.,/"
        left_char = value_n[found - 1] if found else ""
        right_char = value_n[end] if end < len(value_n) else ""
        left_ok = found == 0 or not (left_char.isalnum() or left_char == "_" or (numeric_safe and left_char in neighbours))
        right_ok = end == len(value_n) or not (right_char.isalnum() or right_char == "_" or (numeric_safe and right_char in neighbours))
        if not numeric_safe or (left_ok and right_ok):
            return True
        start = found + 1


def _has_pipe_row(line: str) -> bool:
    """``:319-326``: a guard against hiding data rows as headers."""
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    if len(parts) < 3:
        return False
    has_number = any(re.search(r"\d", part) for part in parts)
    separator = all(re.fullmatch(r"[:\- =]+", part or " ") for part in parts)
    return has_number and not separator


def _table_lines(line_map: dict[int, tuple[dict[str, Any], str]], issues: list[str]) -> tuple[dict[int, dict[str, str]], set[int], set[int]]:
    cells_by_line: dict[int, dict[str, str]] = {}
    headers: set[int] = set()
    separators: set[int] = set()
    table_header: dict[int, str] | None = None
    width = 0
    ordered = list(line_map.items())
    for position, (number, (_, text)) in enumerate(ordered):
        cells = _pipe_cells(text)
        recognized = _table_header(cells)
        if recognized is not None:
            table_header, width = recognized, len(cells or [])
            headers.add(number)
            continue
        next_cells = _pipe_cells(ordered[position + 1][1][1]) if position + 1 < len(ordered) else None
        if cells and _separator_row(next_cells):
            issues.append(f"Unrecognized Markdown table header at line {number}")
            table_header, width = None, 0
            continue
        if table_header and cells:
            if len(cells) != width:
                issues.append(f"Markdown table row width differs from its header at line {number}")
                continue
            if _separator_row(cells):
                separators.add(number)
                continue
            if any(cell.strip() for cell in cells):
                cells_by_line[number] = {field: cells[index] for index, field in table_header.items() if index < len(cells)}
    return cells_by_line, headers, separators


def check_extraction(source: dict[str, Any], payload: Any) -> dict[str, Any]:
    """Check a model's answer against the packet it was given: see the module. Returns ``{"complete", "issues", "rows",
    "source_coverage", "coverage", "reason"}``; ``rows`` is empty unless the side is complete."""
    issues: list[str] = list(source.get("issues") or []) if isinstance(source.get("issues"), list) else []
    source_issues = len(issues)
    src_blocks = source.get("blocks") if isinstance(source.get("blocks"), list) else []
    payload_blocks: list[Any] = []
    if not isinstance(payload, dict) or not isinstance(payload.get("blocks"), list):
        issues.append("Extraction payload must contain a blocks array")
    else:
        payload_blocks = payload["blocks"]
        if set(payload) != {"blocks"}:
            issues.append("Extraction payload has unexpected top-level keys")
    expected_ids = [b.get("block_id") for b in src_blocks if isinstance(b, dict)]
    got_ids = [b.get("block_id") if isinstance(b, dict) else None for b in payload_blocks]
    valid_got = [value for value in got_ids if isinstance(value, str)]
    if len(valid_got) != len(got_ids):
        issues.append("Extraction block ids must be strings")
    if len(valid_got) != len(set(valid_got)):
        issues.append("Extraction contains duplicate block ids")
    if set(valid_got) != set(expected_ids) or len(valid_got) != len(expected_ids):
        issues.append("Extraction block ids do not exactly match the assigned source blocks")
    payload_by_id = {b.get("block_id"): b for b in payload_blocks if isinstance(b, dict) and isinstance(b.get("block_id"), str)}

    line_map: dict[int, tuple[dict[str, Any], str]] = {}
    for src_block in src_blocks:
        for line in src_block.get("lines", []):
            if not isinstance(line, dict) or not isinstance(line.get("line"), int) or not isinstance(line.get("text"), str):
                issues.append(f"Malformed source line in {src_block.get('block_id', '?')}")
                continue
            if line["line"] in line_map:
                issues.append(f"Duplicate absolute source line number: {line['line']}")
            line_map[line["line"]] = (src_block, line["text"])
    table_cells_by_line, table_header_lines, table_separator_lines = _table_lines(line_map, issues)

    all_text = " ".join(_norm(text) for _, text in line_map.values())
    classified: set[int] = set()
    evidence_claims: dict[int, set[str]] = {}
    ignored_claims: dict[int, list[tuple[str, str]]] = {}
    section_ignored_lines: set[int] = set()
    rows_out: list[dict[str, Any]] = []
    for src_block in src_blocks:
        block_id = src_block.get("block_id")
        model_block = payload_by_id.get(block_id)
        if not isinstance(model_block, dict):
            continue
        if set(model_block) != {"block_id", "rows", "ignored", "issues"}:
            issues.append(f"Malformed extraction block shape: {block_id}")
        if not isinstance(model_block.get("issues"), list) or any(not isinstance(x, str) for x in model_block.get("issues", [])):
            issues.append(f"Malformed block issues: {block_id}")
        elif model_block["issues"]:
            issues.extend(f"{block_id}: {x}" for x in model_block["issues"])
        rows, ignored = model_block.get("rows"), model_block.get("ignored")
        if not isinstance(rows, list) or not isinstance(ignored, list):
            issues.append(f"Malformed rows/ignored arrays: {block_id}")
            continue
        local_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        signatures: set[tuple[Any, ...]] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != {"section", "parent", "fields", "evidence"}:
                issues.append(f"Malformed row {index + 1} in {block_id}")
                continue
            fields, evidence = row.get("fields"), row.get("evidence")
            if not isinstance(fields, dict) or set(fields) != set(FIELDS) or any(not isinstance(fields.get(f), str) for f in FIELDS):
                issues.append(f"Malformed fields in row {index + 1} of {block_id}")
                continue
            if not any(fields.values()):
                issues.append(f"Empty extracted row in {block_id}, row {index + 1}")
            if not isinstance(evidence, list) or not evidence:
                issues.append(f"Row {index + 1} in {block_id} has no evidence")
                continue
            cites: list[dict[str, Any]] = []
            seen_lines: set[int] = set()
            for citation in evidence:
                if not isinstance(citation, dict) or set(citation) != {"line", "quote"}:
                    issues.append(f"Malformed evidence in row {index + 1} of {block_id}")
                    continue
                line_no, quote = citation.get("line"), citation.get("quote")
                if not isinstance(line_no, int) or not isinstance(quote, str) or not quote.strip() or line_no not in line_map:
                    issues.append(f"Evidence references an invalid source line in {block_id}")
                    continue
                if not quote or quote not in line_map[line_no][1]:
                    issues.append(f"Evidence quote is not an exact source substring in {block_id}, line {line_no}")
                    continue
                if line_no in seen_lines:
                    issues.append(f"Repeated evidence line in a row of {block_id}: {line_no}")
                    continue
                seen_lines.add(line_no)
                classified.add(line_no)
                evidence_claims.setdefault(line_no, set()).add(f"{block_id}:{index + 1}")
                if not cites and line_map[line_no][0].get("block_id") != block_id:
                    issues.append(f"Row in {block_id} begins with evidence from another block (continuation ownership mismatch)")
                cites.append({"line": line_no, "quote": quote})
            combined = _norm(" ".join(c["quote"] for c in cites))
            for field in FIELDS:
                value = fields[field]
                numeric_safe = field in _NUMERIC_FIELDS
                if value and not _contains_cell(combined, value, numeric_safe=numeric_safe):
                    # A continued cell may sit in a later row: ground it against the corresponding cells in evidence order.
                    parts = [table_cells_by_line[c["line"]].get(field, "") for c in cites if c["line"] in table_cells_by_line]
                    grounding = _norm(" ".join(part for part in parts if part))
                    if not grounding or not _contains_cell(grounding, value, numeric_safe=numeric_safe):
                        issues.append(f"Fabricated or ungrounded {field} in {block_id}, row {index + 1}")
            for context_key in ("section", "parent"):
                value = row.get(context_key)
                if not isinstance(value, str):
                    issues.append(f"Malformed {context_key} in {block_id}, row {index + 1}")
                elif value and _norm(value) not in all_text:
                    issues.append(f"Ungrounded {context_key} in {block_id}, row {index + 1}")
            signature = (tuple((f, _norm(fields[f])) for f in FIELDS), tuple(sorted(seen_lines)))
            if signature in signatures:
                issues.append(f"Duplicate extraction in {block_id}, row {index + 1}")
            signatures.add(signature)
            local_rows.append((row, cites))

        for item in ignored:
            if not isinstance(item, dict) or set(item) != {"line", "reason"}:
                issues.append(f"Malformed ignored-line entry in {block_id}")
                continue
            line_no, reason = item.get("line"), item.get("reason")
            if not isinstance(line_no, int) or line_no not in line_map or reason not in IGNORE_REASONS:
                issues.append(f"Invalid ignored-line entry in {block_id}")
                continue
            if line_map[line_no][0].get("block_id") != block_id:
                issues.append(f"Ignored line assigned to the wrong block in {block_id}: {line_no}")
            if reason == "empty":
                issues.append(f"A nonblank source line cannot be ignored as empty in {block_id}, line {line_no}")
            ignored_claims.setdefault(line_no, []).append((block_id, reason))
            classified.add(line_no)
            if reason == "note":
                issues.append(f"Substantive note may not be discarded in {block_id}, line {line_no}")
            if reason in ("header", "separator", "section") and _has_pipe_row(line_map[line_no][1]):
                issues.append(f"Data-like line hidden as {reason} in {block_id}, line {line_no}")
            ignored_text = line_map[line_no][1]
            if reason == "header" and line_no not in table_header_lines and not _TITLE_HEADER_RE.match(_section_norm(ignored_text).lower()):
                issues.append(f"Unrecognized line hidden as header in {block_id}, line {line_no}")
            if reason == "separator" and line_no not in table_separator_lines and not _plain_separator(ignored_text):
                issues.append(f"Non-separator line hidden as separator in {block_id}, line {line_no}")
            if reason == "section":
                section_ignored_lines.add(line_no)

        for index, (row, cites) in enumerate(local_rows, 1):
            sources = []
            for cite in cites:
                cited = line_map[cite["line"]][0]
                sources.append({
                    "page": cited.get("page"), "sheet": cited.get("sheet") or "", "block_id": cited["block_id"],
                    "line_start": cite["line"], "line_end": cite["line"], "quote": cite["quote"],
                })
            rows_out.append({
                "id": f"{block_id}:{index}", "section": row.get("section", ""), "parent": row.get("parent", ""),
                "fields": row.get("fields", {}), "sources": sources,
            })

    for line_no, claims in evidence_claims.items():
        if len(claims) > 1:
            issues.append(f"Source line claimed by multiple rows: {line_no}")
        if line_no in ignored_claims:
            issues.append(f"Source line classified as both evidence and ignored: {line_no}")
    for line_no, claims in ignored_claims.items():
        if len(claims) > 1:
            issues.append(f"Source line ignored more than once: {line_no}")
    row_context = {
        _section_norm(value).casefold()
        for row in rows_out for value in (row.get("section", ""), row.get("parent", ""))
        if isinstance(value, str) and _section_norm(value)
    }
    for line_no in section_ignored_lines:
        normalized = _section_norm(line_map[line_no][1]).casefold()
        if not normalized or normalized not in row_context:
            issues.append(f"Unconfirmed section line hidden as section at line {line_no}")
    unextracted: set[int] = set()
    for line_no, expected_cells in table_cells_by_line.items():
        if line_no not in evidence_claims:
            issues.append(f"Markdown table data line is not extracted as a row: {line_no}")
            unextracted.add(line_no)
            continue
        matching = [r for r in rows_out if any(s["line_start"] == line_no for s in r["sources"])]
        for field, cell in expected_cells.items():
            if not cell:
                continue
            numeric_safe = field in _NUMERIC_FIELDS
            if not any(_contains_cell(r["fields"].get(field, ""), cell, numeric_safe=numeric_safe) for r in matching):
                issues.append(f"Markdown table cell is missing or altered in {field}, line {line_no}")
    missing = set(line_map) - classified
    if missing:
        issues.append(f"Unclassified source lines: {', '.join(map(str, sorted(missing)))}")
    source_coverage = []
    for src_block in src_blocks:
        block_lines = {ln["line"] for ln in src_block.get("lines", []) if isinstance(ln, dict) and isinstance(ln.get("line"), int)}
        missing_here = sorted(block_lines - classified)
        source_coverage.append({
            "block_id": src_block.get("block_id"), "source_nonblank_lines": len(block_lines),
            "classified_lines": len(block_lines - set(missing_here)), "unclassified_lines": missing_here,
        })
    complete = bool(source.get("complete", False)) and not issues
    reason = None
    if not complete:
        reason = REASON_SOURCE if (source_issues or not source.get("complete", False)) else REASON_ANSWER
    return {
        "complete": complete, "issues": issues, "rows": rows_out if complete else [], "source_coverage": source_coverage,
        "coverage": coverage_of(source_coverage, table_cells_by_line, unextracted, answered=len(payload_by_id)), "reason": reason,
    }


def coverage_of(
    source_coverage: list[dict[str, Any]], table_cells_by_line: dict[int, dict[str, str]], unextracted: set[int], *, answered: int
) -> dict[str, int]:
    """The contract's «покрыто»: the blocks the answer accounts for completely, and the table rows it could not settle."""
    return {
        "blocks_total": len(source_coverage),
        "blocks_covered": sum(1 for b in source_coverage if not b["unclassified_lines"]) if answered else 0,
        "rows_total": len(table_cells_by_line),
        "rows_unresolved": len(unextracted),
    }
