"""Deterministic, standard-library XLSX writer for the W57b review layout.

This module knows only supplied values. It does not read a run, grant a role,
assign a download name, decide a finding or infer a norm citation.
"""

from __future__ import annotations

import io
import zipfile
from collections import Counter
from dataclasses import dataclass
from typing import Final
from xml.sax.saxutils import escape


CONTENT_TYPE: Final[str] = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
MAX_CELL_CHARACTERS: Final[int] = 32_767
SEVERITIES: Final[tuple[str, ...]] = (
    "critical",
    "economic",
    "operational",
    "recommendation",
    "check_adjacent",
)
FINDING_COLUMNS: Final[tuple[str, ...]] = (
    "№",
    "Лист/стр.",
    "Категория",
    "Замечание",
    "Рекомендация",
    "Серьёзность (решение эксперта)",
    "Серьёзность (предложение модели)",
    "Норма (документ, пункт)",
    "Цитата нормы",
    "Решение эксперта",
    "Комментарий",
)

_PARTS: Final[tuple[str, ...]] = (
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
    "xl/worksheets/sheet1.xml",
    "xl/worksheets/sheet2.xml",
)
_FIXED_ZIP_TIME: Final[tuple[int, int, int, int, int, int]] = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class Citation:
    document: str
    clause: str
    quote: str


@dataclass(frozen=True, slots=True)
class FindingMember:
    sheet_page: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class FindingRow:
    finding_uid: str
    sheet_page: str
    category: str
    finding_text: str
    recommendation: str = ""
    decided_severity: str | None = None
    proposed_severity: str | None = None
    citations: tuple[Citation, ...] = ()
    expert_decision: str = ""
    comment: str = ""
    members: tuple[FindingMember, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkbookInput:
    project_uid: str
    version_uid: str
    run_id: str
    profile_id: str
    snapshot_key: str
    attribution: str
    findings: tuple[FindingRow, ...]


@dataclass(frozen=True, slots=True)
class RenderedWorkbook:
    content: bytes
    replacement_count: int
    content_type: str = CONTENT_TYPE


class _Cells:
    def __init__(self) -> None:
        self.replacement_count = 0

    def text(self, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("xlsx_cell_requires_text")
        cleaned = []
        for character in value:
            code = ord(character)
            if code in (9, 10, 13) or 32 <= code <= 0xD7FF or 0xE000 <= code <= 0xFFFD or 0x10000 <= code <= 0x10FFFF:
                cleaned.append(character)
            else:
                cleaned.append("\ufffd")
                self.replacement_count += 1
        result = "".join(cleaned)
        if len(result) > MAX_CELL_CHARACTERS:
            raise ValueError("xlsx_cell_too_long")
        return escape(result)


def _column(number: int) -> str:
    result = ""
    while number:
        number, digit = divmod(number - 1, 26)
        result = chr(65 + digit) + result
    return result


def _string_cell(address: str, value: str, style: int, cells: _Cells) -> str:
    # Inline strings are text even when their first character is =, +, - or @.
    return (
        f'<c r="{address}" s="{style}" t="inlineStr"><is>'
        f'<t xml:space="preserve">{cells.text(value)}</t></is></c>'
    )


def _number_cell(address: str, value: int, style: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("xlsx_count_invalid")
    return f'<c r="{address}" s="{style}"><v>{value}</v></c>'


def _row(index: int, values: tuple[str | int, ...], style: int, cells: _Cells) -> str:
    if index < 1 or index > 1_048_576:
        raise ValueError("xlsx_row_limit")
    parts = []
    for column, value in enumerate(values, start=1):
        address = f"{_column(column)}{index}"
        parts.append(
            _number_cell(address, value, style)
            if isinstance(value, int) else _string_cell(address, value, style, cells)
        )
    return f'<row r="{index}">{"".join(parts)}</row>'


def _sheet(rows: list[str], widths: tuple[int, ...]) -> bytes:
    columns = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        f'<cols>{columns}</cols><sheetData>{"".join(rows)}</sheetData></worksheet>'
    ).encode("utf-8")


def _validate(source: WorkbookInput) -> None:
    if not isinstance(source, WorkbookInput) or not isinstance(source.findings, tuple):
        raise ValueError("xlsx_input_invalid")
    for identity in (source.project_uid, source.version_uid, source.run_id, source.profile_id):
        if not isinstance(identity, str) or not identity:
            raise ValueError("xlsx_identity_invalid")
    if not isinstance(source.snapshot_key, str) or not isinstance(source.attribution, str):
        raise ValueError("xlsx_identity_invalid")
    seen: set[str] = set()
    for finding in source.findings:
        if not isinstance(finding, FindingRow):
            raise ValueError("xlsx_finding_invalid")
        if not finding.finding_uid or not isinstance(finding.finding_uid, str) or finding.finding_uid in seen:
            raise ValueError("xlsx_finding_identity_invalid")
        seen.add(finding.finding_uid)
        for value in (finding.sheet_page, finding.category, finding.finding_text):
            if not isinstance(value, str) or not value:
                raise ValueError("xlsx_finding_invalid")
        for severity in (finding.decided_severity, finding.proposed_severity):
            if severity is not None and severity not in SEVERITIES:
                raise ValueError("xlsx_severity_invalid")
        if not isinstance(finding.citations, tuple) or not isinstance(finding.members, tuple):
            raise ValueError("xlsx_finding_invalid")
        for citation in finding.citations:
            if not isinstance(citation, Citation) or not citation.document or not citation.quote:
                raise ValueError("xlsx_citation_invalid")
            if not isinstance(citation.document, str) or not isinstance(citation.clause, str) or not isinstance(citation.quote, str):
                raise ValueError("xlsx_citation_invalid")
        for member in finding.members:
            if not isinstance(member, FindingMember) or not isinstance(member.sheet_page, str) or not member.sheet_page or not isinstance(member.note, str):
                raise ValueError("xlsx_member_invalid")


def _summary(source: WorkbookInput, cells: _Cells) -> bytes:
    rows = [_row(1, ("Параметр", "Значение"), 1, cells)]
    identity = (
        ("Проект", source.project_uid),
        ("Версия", source.version_uid),
        ("Прогон", source.run_id),
        ("Профиль", source.profile_id),
        ("Ключ снимка", source.snapshot_key),
        ("Атрибуция", source.attribution),
    )
    for label, value in identity:
        rows.append(_row(len(rows) + 1, (label, value), 0, cells))
    rows.append(_row(len(rows) + 1, ("Серьёзность", "Количество"), 1, cells))
    by_severity = Counter(
        finding.decided_severity or finding.proposed_severity
        for finding in source.findings
    )
    for severity in SEVERITIES:
        rows.append(_row(len(rows) + 1, (severity, by_severity[severity]), 0, cells))
    rows.append(_row(len(rows) + 1, ("Без серьёзности", by_severity[None]), 0, cells))
    rows.append(_row(len(rows) + 1, ("Категория", "Количество"), 1, cells))
    by_category = Counter(finding.category for finding in source.findings)
    for category in sorted(by_category):
        rows.append(_row(len(rows) + 1, (category, by_category[category]), 0, cells))
    return _sheet(rows, (30, 72))


def _findings(source: WorkbookInput, cells: _Cells) -> bytes:
    rows = [_row(1, FINDING_COLUMNS, 1, cells)]
    for ordinal, finding in enumerate(source.findings, start=1):
        severity = finding.decided_severity or finding.proposed_severity
        style = SEVERITIES.index(severity) + 2 if severity is not None else 0
        norm_labels = "\n".join(
            f"{citation.document}, {citation.clause}" if citation.clause else citation.document
            for citation in finding.citations
        )
        norm_quotes = "\n".join(citation.quote for citation in finding.citations)
        rows.append(
            _row(
                len(rows) + 1,
                (
                    ordinal,
                    finding.sheet_page,
                    finding.category,
                    finding.finding_text,
                    finding.recommendation,
                    finding.decided_severity or "",
                    finding.proposed_severity or "",
                    norm_labels,
                    norm_quotes,
                    finding.expert_decision,
                    finding.comment,
                ),
                style,
                cells,
            )
        )
        for member in finding.members:
            rows.append(
                _row(
                    len(rows) + 1,
                    ("", member.sheet_page, "", "также найдено", "", "", "", "", "", "", member.note),
                    style,
                    cells,
                )
            )
    return _sheet(rows, (7, 21, 23, 54, 54, 28, 28, 45, 68, 27, 48))


def _static_parts() -> dict[str, bytes]:
    return {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ).encode("utf-8"),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ).encode("utf-8"),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Сводка" sheetId="1" r:id="rId1"/>'
            '<sheet name="Замечания" sheetId="2" r:id="rId2"/></sheets></workbook>'
        ).encode("utf-8"),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        ).encode("utf-8"),
        "xl/styles.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="8"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFD9E2F3"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFF4CCCC"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFFCE5CD"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFD9EAD3"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFEADCF8"/><bgColor indexed="64"/></patternFill></fill>'
            '</fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="7"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyFill="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="6" borderId="0" xfId="0" applyFill="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="7" borderId="0" xfId="0" applyFill="1"/>'
            '</cellXfs></styleSheet>'
        ).encode("utf-8"),
    }


def render_xlsx(source: WorkbookInput) -> RenderedWorkbook:
    """Return byte-identical XLSX bytes and the count of replaced XML characters."""
    _validate(source)
    cells = _Cells()
    parts = _static_parts()
    parts["xl/worksheets/sheet1.xml"] = _summary(source, cells)
    parts["xl/worksheets/sheet2.xml"] = _findings(source, cells)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in _PARTS:
            info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0
            info.external_attr = 0
            archive.writestr(info, parts[name])
    return RenderedWorkbook(output.getvalue(), cells.replacement_count)


__all__ = [
    "CONTENT_TYPE",
    "FINDING_COLUMNS",
    "SEVERITIES",
    "Citation",
    "FindingMember",
    "FindingRow",
    "RenderedWorkbook",
    "WorkbookInput",
    "render_xlsx",
]
