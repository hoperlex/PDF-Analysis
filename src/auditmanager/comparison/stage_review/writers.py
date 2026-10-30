"""Local synchronous stage-journal writers (ADR-0025 §22), with no export resource."""

from __future__ import annotations

import html
import io
import threading
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from auditmanager.shared.errors import DomainError, ErrorCode

_FONT_LOCK = threading.Lock()
_NOTE = ("Журнал содержит принятые экспертные карточки. SAME/MOVED — оценка AI; "
         "исходные детерминированные доказательства сохранены. Отсутствие строки "
         "само по себе не доказывает исчезновение объекта. Оценки существенности "
         "и важности ИИ требуют экспертной проверки.")
_HEADERS = ("Группа", "Класс", "Категория", "Система", "Изменение", "Было", "Стало",
            "Решение эксперта", "Основание", "Доказательства")


def _rows(journal: dict[str, Any]) -> list[list[str]]:
    rows = []
    for group in journal["groups"]:
        for card in group["rows"]:
            verdict = card.get("verdict", {})
            rows.append([str(group["label"]), card["class_name"], card["category"],
                         card["system"], card["title"], card["before"], card["after"],
                         verdict.get("decision", ""), verdict.get("reason", ""),
                         ", ".join(card["evidence_ids"])])
    if len(rows) > 5_000 or sum(len(v) for row in rows for v in row) > 8_000_000:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_chain_run_id",
                          constraint="stage_journal_export_budget")
    return rows


def _summary(journal: dict[str, Any]) -> str:
    return (f"Принято: {journal['accepted_count']}; AI SAME/MOVED: {journal['ai_hidden_same_count']}; "
            f"служебных карточек AI: {journal['ai_service_count']}; "
            f"состояние источника: {'устарело' if journal['stale'] else 'актуально'}.")


def render_html(journal: dict[str, Any]) -> bytes:
    rows = _rows(journal)
    head = "".join(f"<th>{html.escape(value)}</th>" for value in _HEADERS)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row)
                   + "</tr>" for row in rows)
    return ("<!doctype html><html lang=\"ru\"><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width\"><title>Журнал изменений</title>"
            "<style>body{font:14px sans-serif;margin:24px}table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #777;padding:6px;text-align:left;vertical-align:top;"
            "white-space:pre-wrap;overflow-wrap:anywhere}thead{display:table-header-group}"
            "@media print{body{margin:0}tr{break-inside:avoid}}</style><body>"
            f"<h1>Журнал изменений</h1><p>{html.escape(_summary(journal))}</p>"
            f"<p>{html.escape(_NOTE)}</p><table><thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table></body></html>").encode("utf-8")


def _xml_text(value: str) -> str:
    # XML 1.0 excludes control characters and isolated surrogates. This is encoding
    # hygiene; cells remain literal strings, including initial = + - @ characters.
    return escape("".join(c if c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF
                          or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF
                          else "\ufffd" for c in value))


def render_xlsx(journal: dict[str, Any]) -> bytes:
    rows = [["Журнал изменений"], [_summary(journal)], [_NOTE], list(_HEADERS), *_rows(journal)]
    xml_rows = []
    for row_no, row in enumerate(rows, 1):
        cells = []
        for column, value in enumerate(row):
            # Ten fixed columns, all inlineStr: spreadsheet formula execution is
            # impossible without changing the quoted evidence or inserting apostrophes.
            ref = f"{chr(65 + column)}{row_no}"
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                         f'{_xml_text(value)}</t></is></c>')
        xml_rows.append(f'<row r="{row_no}">{"".join(cells)}</row>')
    sheet = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" '
             'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
             '<sheetData>' + ''.join(xml_rows) + '</sheetData></worksheet>')
    parts = {
        '[Content_Types].xml': '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Журнал изменений" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': sheet,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(parts.items()):
            metadata = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            metadata.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(metadata, value.encode('utf-8'))
    return output.getvalue()


def render_pdf(journal: dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    rows = _rows(journal)
    with _FONT_LOCK:
        if "StageJournal" not in pdfmetrics.getRegisteredFontNames():
            fonts = Path(__file__).resolve().parents[1] / "report" / "fonts"
            pdfmetrics.registerFont(TTFont("StageJournal", str(fonts / "DejaVuSans.ttf")))
    normal = ParagraphStyle("stage-journal", fontName="StageJournal", fontSize=9,
                            leading=13, textColor=colors.black, splitLongWords=True)
    title = ParagraphStyle("stage-title", parent=normal, fontSize=15, leading=20, spaceAfter=12)
    def paragraph(value: str, style: Any = normal) -> Any:
        return Paragraph(html.escape(value).replace("\n", "<br/>"), style)
    story = [paragraph("Журнал изменений", title), paragraph(_summary(journal)),
             paragraph(_NOTE), Spacer(1, 12)]
    for row in rows:
        story.extend([paragraph(f"{row[0]} — {row[4]}", title),
                      paragraph(f"{row[1]} · {row[2]} · {row[3]}"),
                      paragraph("Было: " + row[5]), paragraph("Стало: " + row[6]),
                      paragraph("Решение: " + row[7] + "; " + row[8]),
                      paragraph("Доказательства: " + row[9]), Spacer(1, 12)])
    output = io.BytesIO()
    SimpleDocTemplate(output, pagesize=A4, title="Журнал изменений", author="AuditManager",
                      invariant=1, pageCompression=1).build(story)
    return output.getvalue()
