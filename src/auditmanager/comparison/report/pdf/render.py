"""The PDF of a report, written by a program (reportlab, A4 portrait) from structured data (`CMP-VC-REPORT-01`, `Q-CMP-9`, ADR-0025 decisions 8 and 24).

A port of the original's ``md_report/pdf.py`` at commit ``23f379fd`` (681 lines): ``render`` (``pdf.py:106-340``) is the analytic report from
``report_v2``, ``render_client`` (``:426-554``) the report for the customer from the client view. The generator is reportlab: it lays out
tables with a repeated header on a new page and embeds a TrueType font with Cyrillic (here DejaVu Sans under ``../fonts/``; the original looked
for the same font in the host's font directories, ``:18``, ``:30-44``). **No model writes the PDF**: the text comes from the fields of the
report, is escaped, and the markup of the source never reaches it (``:1-7``).

This module is run by the **child** (``program.py``) and loaded by path under a private name, so it imports the standard library and
reportlab only -- nothing of the product. It does not decide anything about the report: the distribution of the transitions, the assessments
and the sources are in the data it is given. The data are the ``document`` of :func:`render`:

``{"kind": "client" | "analytic", "label": str, "recall": str, "recorded_label": str | None, "code": str, "view" | "report": {…},
"distribution": {…}, "analysed_at": str, "sha256": str}``.

What this port adds to the original's pages: **every page carries the label that the text is model output not confirmed by an engineer
and the recall line** («изменённых листов N, описано K, отброшено проверкой D»; ADR-0025 decision 20), and, for a report made of recorded
(test) answers, the recorded mark. The original's client footer held the cipher and the page only (``:459-469``, ``:645-647``); this one holds
those two lines as well. The file is written with reportlab's ``invariant`` mode (no clock, no random document id), so the same data give the
same bytes and «Пересобрать PDF» returns the same file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

__all__ = ["FONT", "FONT_BOLD", "render"]

FONT = "CmpSans"
FONT_BOLD = "CmpSans-Bold"
INK = "#1d2b3a"
MUTED = "#5d6b78"
ACCENT = "#8f2d2d"
RULE = "#c9d1d8"
FILL = "#eef2f5"
HEAD_FILL = "#1d2b3a"
CLIENT_KICKER = "#1f6f5c"
MARGIN_MM = 16
BOTTOM_MM = 24


def _register_fonts(font_dir: str) -> None:
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    regular, bold = Path(font_dir) / "DejaVuSans.ttf", Path(font_dir) / "DejaVuSans-Bold.ttf"
    if not regular.is_file() or not bold.is_file():
        raise FileNotFoundError("the report font is not where the program was told")
    pdfmetrics.registerFont(TTFont(FONT, str(regular)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold)))
    addMapping(FONT, 0, 0, FONT)
    addMapping(FONT, 1, 0, FONT_BOLD)


def _t(text: Any) -> str:
    return escape(re.sub(r"\s+", " ", str(text or "")).strip())


def _date(iso: str | None) -> str:
    if not iso:
        return ""
    year, month, day = iso.split("-")
    return f"{day}.{month}.{year}"


def _pages(pages: list[int] | None) -> str:
    return ", ".join(map(str, pages)) if pages else "—"


def _styles() -> dict[str, Any]:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle

    base = ParagraphStyle("base", fontName=FONT, fontSize=10, leading=13.4, textColor=HexColor(INK))
    return {
        "kicker": ParagraphStyle("kicker", base, fontName=FONT_BOLD, fontSize=8, leading=10, textColor=HexColor(MUTED)),
        "h1": ParagraphStyle("h1", base, fontName=FONT_BOLD, fontSize=20, leading=24, spaceAfter=2),
        "sub": ParagraphStyle("sub", base, fontSize=9, leading=12, textColor=HexColor(MUTED), spaceAfter=8),
        "h2": ParagraphStyle("h2", base, fontName=FONT_BOLD, fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=6),
        "body": base,
        "small": ParagraphStyle("small", base, fontSize=8, leading=10.4, textColor=HexColor(MUTED)),
        "cell": ParagraphStyle("cell", base, fontSize=9.2, leading=12),
        "cell_b": ParagraphStyle("cell_b", base, fontName=FONT_BOLD, fontSize=9.2, leading=12),
        "cell_muted": ParagraphStyle("cell_muted", base, fontSize=8.8, leading=11.6, textColor=HexColor(MUTED)),
        "head": ParagraphStyle("head", base, fontName=FONT_BOLD, fontSize=8.8, leading=11, textColor=HexColor("#ffffff")),
        "tile_n": ParagraphStyle("tile_n", base, fontName=FONT_BOLD, fontSize=19, leading=22),
        "tile_l": ParagraphStyle("tile_l", base, fontSize=8.4, leading=10.4, textColor=HexColor(MUTED)),
        "card_t": ParagraphStyle("card_t", base, fontName=FONT_BOLD, fontSize=10.6, leading=13.6, spaceAfter=3),
        "warn": ParagraphStyle("warn", base, fontName=FONT_BOLD, fontSize=10, leading=13, textColor=HexColor(ACCENT)),
    }


def _footer(document: dict[str, Any], left: str):
    """The footer of every page: the unconfirmed label, the recall line, the cipher and the page «стр. N из M»."""
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    label = document["label"] + (f". {document['recorded_label']}" if document.get("recorded_label") else "")

    def draw(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        width, _ = A4
        canvas.setStrokeColor(HexColor(RULE))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_MM * mm, 18.5 * mm, width - MARGIN_MM * mm, 18.5 * mm)
        canvas.setFillColor(HexColor(ACCENT))
        canvas.setFont(FONT_BOLD, 7.3)
        canvas.drawString(MARGIN_MM * mm, 14.8 * mm, _fit(canvas, label, FONT_BOLD, 7.3, width - 2 * MARGIN_MM * mm))
        canvas.setFillColor(HexColor(MUTED))
        canvas.setFont(FONT, 7.3)
        canvas.drawString(MARGIN_MM * mm, 11.3 * mm, _fit(canvas, document["recall"], FONT, 7.3, width - 2 * MARGIN_MM * mm))
        canvas.setFont(FONT, 7.5)
        canvas.drawString(MARGIN_MM * mm, 7.8 * mm, _fit(canvas, left, FONT, 7.5, width - 2 * MARGIN_MM * mm - 70))
        canvas.drawRightString(width - MARGIN_MM * mm, 7.8 * mm, f"стр. {doc.page} из {doc._cmp_pages}")
        canvas.restoreState()

    return draw


def _fit(canvas: Any, text: str, font: str, size: float, width: float) -> str:
    if canvas.stringWidth(text, font, size) <= width:
        return text
    while canvas.stringWidth(text + "…", font, size) > width and len(text) > 1:
        text = text[:-1]
    return text + "…"


def _two_pass(path: Path, build: Any) -> None:
    """The page count «из N» is known after a pass: build once with 0, then with the count (a third pass only if it moved)."""
    pages = build(0)
    if build(pages) != pages:
        build(build(pages))


def render(document: dict[str, Any], out: str | Path, *, font_dir: str) -> int:
    """Write the PDF of ``document`` to ``out`` (atomically: a temporary file, then a rename). Returns the number of pages."""
    _register_fonts(font_dir)
    out = Path(out)
    tmp = out.with_name(out.name + ".tmp")
    result: list[int] = []

    def build(pages: int) -> int:
        count = _build_client(document, tmp, pages) if document["kind"] == "client" else _build_analytic(document, tmp, pages)
        result[:] = [count]
        return count

    _two_pass(out, build)
    tmp.replace(out)
    return result[0]


# ------------------------------------------------------------------ the analytic report (pdf.py:106-340)

def _build_analytic(document: dict[str, Any], tmp: Path, pages: int) -> int:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import CondPageBreak, KeepTogether, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    st = _styles()
    report = document["report"]
    code = report["project_code"]
    transitions = report["transitions"]
    dist = document["distribution"]
    analysed_at = document["analysed_at"]
    sha256 = document.get("sha256") or ""
    width = A4[0] - 2 * MARGIN_MM * mm

    def sources_line(ids: list[str]) -> str:
        return ", ".join(ids)

    def story() -> list[Any]:
        s: list[Any] = [Paragraph(_t(f"{code} / короткий отчёт").upper(), st["kicker"]), Paragraph("Как менялась документация", st["h1"])]
        first, last = transitions[0], transitions[-1]
        span = " – ".join(x for x in (_date(first.get("from_date")), _date(last.get("to_date"))) if x)
        s.append(Paragraph(_t(
            f"Выдачи {first['from_version']} – {last['to_version']}" + (f" · {span}" if span else "")
            + " · оценка последствий для закупки и монтажа · по MD-сводке, исходные PDF не проверялись"), st["sub"]))
        if document.get("incomplete"):
            s.append(Paragraph(_t("НЕПОЛНЫЙ РЕЗУЛЬТАТ: " + "; ".join(document["incomplete"])), st["warn"]))
            s.append(Spacer(1, 4))
        tiles = [
            (dist["technical"], "с техническими изменениями"), (dist["no_content_change"], "без изменений содержания"),
            (dist["formatting_only"], "только оформление"),
        ]
        if dist["unknown"]:
            tiles.append((dist["unknown"], "оценить не удалось"))
        cells = [[Paragraph(str(n), st["tile_n"]), Paragraph(_t(lbl), st["tile_l"])] for n, lbl in tiles]
        tile_w = width / len(tiles)
        tile_table = Table([[Table([[c[0]], [c[1]]], colWidths=[tile_w - 10]) for c in cells]], colWidths=[tile_w] * len(tiles))
        tile_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor(FILL)), ("LINEBEFORE", (1, 0), (-1, -1), 2, HexColor("#ffffff")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        s.append(tile_table)
        s.append(Paragraph(_t(
            f"Переходов между выдачами: {dist['total']}. Масштаб оценён качественно по содержанию сводки, а не по числу листов или пунктов."),
            st["small"]))
        s.append(Spacer(1, 6))
        s.append(Paragraph(_t(" ".join(report["summary"])), st["body"]))
        if report.get("summary_sources"):
            s.append(Spacer(1, 2))
            s.append(Paragraph(_t("Основание: " + sources_line(report["summary_sources"])), st["small"]))
        s.append(Paragraph(_t(
            "Ссылки вида «Ф0123» — факты сводки; паспорт каждого (переход, лист, страницы PDF A → B, строка MD, исходная запись, "
            "подтверждение) — в приложении «Реестр источников»."), st["small"]))
        s.append(Paragraph("Оценка по каждой паре версий", st["h2"]))
        rows = [[Paragraph("Переход", st["head"]), Paragraph("Масштаб и значимость", st["head"]),
                 Paragraph("Изменения и последствия для работ по предыдущей выдаче", st["head"])]]
        for t in transitions:
            label = f"{t['from_version']}→{t['to_version']}"
            dates = "<br/>".join(_t(x) for x in (_date(t.get("from_date")), _date(t.get("to_date"))) if x)
            left = [Paragraph(_t(label), st["cell_b"])]
            if dates:
                left.append(Paragraph(dates, st["small"]))
            mid = [Paragraph(_t(t["change_scope"]), st["cell_b"])]
            if t["significance"] != "Нет новых технических изменений":
                mid.append(Paragraph(_t(f"Значимость: {t['significance'].lower()}"), st["cell_muted"]))
            right = [Paragraph(_t(t["main_changes"]), st["cell"])]
            for change in t.get("changes") or []:
                note = " (связь значений между версиями не подтверждена)" if change.get("chain_unconfirmed") else ""
                right.append(Paragraph(
                    f"• <font name='{FONT_BOLD}'>{_t(change['object'])}</font> — {_t(change['before'])} → {_t(change['after'])}{_t(note)} "
                    f"<font size='7.6' color='{MUTED}'>[{_t(sources_line(change['sources']))}]</font>", st["cell"]))
            impact = _t(t["construction_impact"])
            if t.get("impact_sources"):
                impact += f" <font size='7.6'>[{_t(sources_line(t['impact_sources']))}]</font>"
            right.append(Paragraph(impact, st["cell_muted"]))
            for mark in t.get("document_marks") or []:
                right.append(Paragraph(_t("Отметка документа: " + mark), st["small"]))
            completeness = (t.get("completeness") or {}).get("text")
            if completeness:
                right.append(Paragraph(_t("Полнота: " + completeness), st["small"]))
            rows.append([left, mid, right])

        def word_w(texts: list[str], size: float) -> float:
            return max((stringWidth(w, FONT_BOLD, size) for x in texts for w in x.split()), default=0)

        pad = 12
        c1 = max(21 * mm, word_w([f"{t['from_version']}→{t['to_version']}" for t in transitions], 9.2) + pad)
        c2 = max(31 * mm, word_w([t["change_scope"] for t in transitions], 9.2) + pad)
        table = LongTable(rows, colWidths=[c1, c2, width - c1 - c2], repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(HEAD_FILL)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, HexColor(RULE)), ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]
        for k in range(1, len(rows)):
            if k % 2 == 0:
                style.append(("BACKGROUND", (0, k), (-1, k), HexColor("#f7f9fa")))
        table.setStyle(TableStyle(style))
        s.append(table)
        significant = report.get("significant_changes") or []
        s.append(CondPageBreak(60 * mm))
        s.append(Paragraph("Что выделить отдельно", st["h2"]))
        if significant:
            s.append(Paragraph(_t("Наиболее значимые связанные изменения для согласования и проверки. Приоритет означает внимание, а не доказанное нарушение."), st["small"]))
            s.append(Spacer(1, 4))
            for k, c in enumerate(significant, 1):
                body = [
                    Paragraph(f"<font color='{ACCENT}'>{k:02d}</font>&nbsp;&nbsp;{_t(c['title'])} "
                              f"<font size='8' color='{MUTED}'>({_t(c['priority'])}, {_t(c['version_range'])})</font>", st["card_t"]),
                    Paragraph(f"<font name='{FONT_BOLD}'>Было → стало.</font> {_t(c['before_after'])}"
                              + (_t(" (связь значений между версиями не подтверждена — изменения по отдельным фактам)")
                                 if c.get("chain_unconfirmed") else ""), st["cell"]),
                    Spacer(1, 2),
                    Paragraph(f"<font name='{FONT_BOLD}'>Последствие.</font> {_t(c['consequence'])}", st["cell"]),
                    Spacer(1, 2),
                    Paragraph(_t("Источники: " + sources_line(c.get("sources") or [])), st["small"]),
                ]
                card = Table([[body]], colWidths=[width])
                card.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor(FILL)), ("LINEBEFORE", (0, 0), (0, -1), 2.2, HexColor(ACCENT)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                s.append(KeepTogether([card, Spacer(1, 5)]))
        else:
            s.append(Paragraph(_t("Серьёзных изменений, требующих отдельного внимания, по проверенным результатам сводки не выявлено."), st["body"]))
        s.append(Paragraph("Основание и границы вывода", st["h2"]))
        for line in report.get("limitations") or []:
            s.append(Paragraph("• " + _t(line), st["small"]))
        if report.get("reference_warnings"):
            s.append(Paragraph("• " + _t(
                f"Отброшено ссылок на факты, которых нет в реестре или которые относятся к другому переходу: {len(report['reference_warnings'])}."),
                st["small"]))
        basis = report.get("analysis_basis") or {}
        checked = "Исходные PDF проверялись." if basis.get("source_pdf_checked") else \
            "Исходные PDF не проверялись: номера листов и страниц PDF приведены по заголовкам сводки."
        s.append(Spacer(1, 3))
        s.append(Paragraph(_t(
            f"Источник: {report['input_filename']}" + (f" (SHA-256 {sha256[:16]}…)" if sha256 else "") + f". {checked} Анализ выполнен {analysed_at}."),
            st["small"]))
        s += _coverage_table(report, st, width)
        s += _registry_table(report, st, width)
        return s

    def _coverage_table(report_: dict[str, Any], st_: dict[str, Any], width_: float) -> list[Any]:
        coverage = report_.get("coverage") or []
        if not coverage:
            return []
        out: list[Any] = [CondPageBreak(50 * mm), Paragraph("Реестр покрытия", st_["h2"])]
        if not any(c.get("registry") for c in coverage):
            return out + [Paragraph(_t("Реестр покрытия в сводке не передан: полнота по набору обработанных листов не подтверждена."), st_["small"])]
        out.append(Paragraph(_t(
            "Каждый лист перехода — в одной категории (по сохранённым данным сравнения). Снятая отметка документа — изменение отметки, "
            "не оборудования, и не доказательство согласования."), st_["small"]))
        out.append(Spacer(1, 3))
        columns = ["совпадает по движку", "только служебное", "описано ИИ", "СО целиком", "неоднозначно", "не обработано"]
        heads = ["Переход", "Листов", "Совп.", "Служ.", "ИИ", "СО", "Неодн.", "Не обр."]
        rows = [[Paragraph(h, st_["head"]) for h in heads]]
        for c in coverage:
            counts = c.get("counts") or {}
            rows.append([Paragraph(_t(c["label"]), st_["cell_b"]), Paragraph(str(c.get("sheets_total") or "—"), st_["cell"])]
                        + [Paragraph(str(counts.get(k, "—")), st_["cell"]) for k in columns])
        w0 = 24 * mm
        rest = (width_ - w0) / 7
        table = LongTable(rows, colWidths=[w0] + [rest] * 7, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(HEAD_FILL)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, HexColor(RULE)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        out.append(table)
        for c in coverage:
            for kind, items in (("не обработано", c.get("not_processed")), ("неоднозначно", c.get("ambiguous"))):
                for x in items or []:
                    out.append(Paragraph(_t(f"{c['label']}, {kind}: {x}"), st_["small"]))
        return out

    def _registry_table(report_: dict[str, Any], st_: dict[str, Any], width_: float) -> list[Any]:
        facts = report_.get("facts") or []
        out: list[Any] = [
            PageBreak(), Paragraph("Приложение. Реестр источников", st_["h2"]),
            Paragraph(_t(f"Все факты, на которые ссылается отчёт: {len(facts)} из {report_.get('facts_total', len(facts))} пунктов сводки. "
                         "ID — порядковый номер пункта в исходном MD; строка MD — номер строки исходного файла."), st_["small"]),
            Spacer(1, 3),
        ]
        if not facts:
            return out + [Paragraph(_t("Ссылок на факты нет."), st_["small"])]
        rows = [[Paragraph(h, st_["head"]) for h in ("ID", "Переход, лист, стр. PDF A → B", "MD", "Подтверждение", "Пункт сводки")]]
        for f in facts:
            title = f.get("sheet_title") or ""
            where = f["transition"] + (f", {f['sheet']}" if f.get("sheet") else f", {title[:60]}{'…' if len(title) > 60 else ''}" if title else "")
            where += f"; стр. {_pages(f.get('pages_a'))} → {_pages(f.get('pages_b'))}"
            record = f.get("record") or {}
            confirmation = f.get("confirmation") or ""
            if record.get("change_id") or record.get("entry_id"):
                confirmation += f" (запись {record.get('change_id') or record.get('entry_id')})"
            rows.append([Paragraph(_t(f["fact_id"]), st_["cell_b"]), Paragraph(_t(where), st_["cell_muted"]),
                         Paragraph(str(f["md_line"]), st_["cell_muted"]), Paragraph(_t(confirmation), st_["cell_muted"]),
                         Paragraph(_t(f.get("text")), st_["cell_muted"])])
        widths = [15 * mm, 40 * mm, 11 * mm, 34 * mm]
        table = LongTable(rows, colWidths=widths + [width_ - sum(widths)], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(HEAD_FILL)), ("LINEBELOW", (0, 1), (-1, -1), 0.3, HexColor(RULE)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        return out + [table]

    footer = _footer(document, f"{code} | {report['input_filename']} | анализ {analysed_at}")
    doc = SimpleDocTemplate(
        str(tmp), pagesize=A4, leftMargin=MARGIN_MM * mm, rightMargin=MARGIN_MM * mm, topMargin=14 * mm,
        bottomMargin=BOTTOM_MM * mm, title=f"{code} — оценка изменений версий", author="AuditManager",
        subject="Анализ сводки изменений версий", invariant=1,
    )
    doc._cmp_pages = pages
    doc.build(story(), onFirstPage=footer, onLaterPages=footer)
    return doc.page


# ------------------------------------------------------------------ the report for the customer (pdf.py:426-590)

def _uncap(question: str) -> str:
    """«Уточнить: …» without a repeat of the verb («Уточнить марку…» → «марку…») -- pdf.py:587-590."""
    question = re.sub(r"^(Уточнить|Требуется уточнить|Необходимо уточнить)\s*[:,]?\s*", "", question.strip())
    return question[:1].lower() + question[1:] if question[:2] != question[:2].upper() else question


def _cont_table_class() -> Any:
    from reportlab.platypus import LongTable

    class ContTable(LongTable):  # type: ignore[misc]
        """A table that, when it breaks across pages, puts the transition, the dates and «продолжение» into the first columns of the
        continuation (pdf.py:557-580)."""

        _group_start: list[int] = []
        _cont: dict[int, Any] = {}

        def split(self, availWidth: float, availHeight: float) -> Any:
            parts = LongTable.split(self, availWidth, availHeight)
            if len(parts) != 2 or not self._group_start:
                return parts
            head, tail = parts
            n = len(head._cellvalues)  # the first row of the continuation in the original numbering
            header = len(tail._cellvalues) - (len(self._cellvalues) - n)
            if n < len(self._group_start) and self._group_start[n] < n and n in self._cont:
                left, scale = self._cont[n]
                tail._cellvalues[header][0], tail._cellvalues[header][1] = left, scale
                tail._argH = list(tail._argH)
                tail._argH[header] = None  # the row height is recomputed for the inserted columns
            tail._group_start = [0] * header + [g - n + header if g >= n else header for g in self._group_start[n:]]
            tail._cont = {k - n + header: v for k, v in self._cont.items() if k >= n}
            return parts

    return ContTable


def _build_client(document: dict[str, Any], tmp: Path, pages: int) -> int:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, TableStyle

    view = document["view"]
    st = _styles()
    base = st["cell"]
    sty = {
        "kicker": ParagraphStyle("c_kicker", base, fontName=FONT_BOLD, fontSize=8.6, leading=11, textColor=HexColor(CLIENT_KICKER)),
        "h1": ParagraphStyle("c_h1", base, fontName=FONT_BOLD, fontSize=19, leading=23, spaceBefore=4, spaceAfter=6),
        "sub": ParagraphStyle("c_sub", base, fontSize=9.4, leading=12.4, textColor=HexColor(MUTED)),
        "head": ParagraphStyle("c_head", base, fontName=FONT_BOLD, fontSize=8.4, leading=10.6, textColor=HexColor("#ffffff")),
        "tr": ParagraphStyle("c_tr", base, fontName=FONT_BOLD, fontSize=9.4, leading=12),
        "date": ParagraphStyle("c_date", base, fontSize=7.8, leading=10, textColor=HexColor(MUTED)),
        "scale": ParagraphStyle("c_scale", base, fontName=FONT_BOLD, fontSize=7.8, leading=10),
        "lead": ParagraphStyle("c_lead", base, fontName=FONT_BOLD, fontSize=9.4, leading=12.2, spaceAfter=3),
        "pt": ParagraphStyle("c_pt", base, fontSize=8.5, leading=10.9, spaceAfter=2),
        "cont": ParagraphStyle("c_cont", base, fontSize=7.4, leading=9.4, textColor=HexColor(MUTED)),
        "imp": ParagraphStyle("c_imp", base, fontSize=8.4, leading=10.8, spaceBefore=1, textColor=HexColor("#33414e")),
        "warn": ParagraphStyle("c_warn", base, fontName=FONT_BOLD, fontSize=8.6, leading=11, textColor=HexColor(ACCENT)),
    }
    code = view["code"]
    ContTable = _cont_table_class()

    def story() -> list[Any]:
        width = A4[0] - 2 * MARGIN_MM * mm
        kicker = " / ".join(x for x in (view.get("object"), code) if x).upper()
        s: list[Any] = [Paragraph(_t(kicker), sty["kicker"]), Paragraph(_t(view["title"]), sty["h1"])]
        if view.get("section"):
            s.append(Paragraph(_t(view["section"]), sty["sub"]))
        s.append(Paragraph(_t(f"Выдачи {view['versions']} · {view['period']}"), sty["sub"]))
        if document.get("incomplete"):
            s.append(Paragraph(_t("НЕПОЛНЫЙ РЕЗУЛЬТАТ: " + "; ".join(document["incomplete"])), sty["warn"]))
        s.append(Spacer(1, 5 * mm))
        rows: list[list[Any]] = [[Paragraph("Переход и даты выдач", sty["head"]), Paragraph("Масштаб изменений", sty["head"]),
                                  Paragraph("Изменения и последствия для работ по предыдущей выдаче", sty["head"])]]
        # A transition is a group of sub-rows (essence, points, questions, consequence): the table breaks between them instead of cutting
        # a row. A short transition is held whole (NOSPLIT); a long one breaks, and on the new page the first columns repeat the transition,
        # the dates and «продолжение» (pdf.py:481-483).
        pad = 10.5
        w_tr = max([stringWidth(r["label"], FONT_BOLD, sty["tr"].fontSize) for r in view["rows"]]
                   + [stringWidth(d, FONT, sty["date"].fontSize) for r in view["rows"] for d in r["dates"] if d]
                   + [stringWidth("продолжение", FONT, sty["date"].fontSize)]) + pad
        w_sc = max(stringWidth(w, FONT_BOLD, sty["scale"].fontSize) for r in view["rows"] for w in r["scale"].split()) + pad
        w_tr, w_sc = max(w_tr, 19 * mm), max(w_sc, 22 * mm)
        w_tx = width - w_tr - w_sc
        style: list[tuple[Any, ...]] = [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(HEAD_FILL)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, 0), 5), ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]
        group_start: list[int] = [0]
        cont: dict[int, Any] = {}
        frame_h = A4[1] - 38 * mm
        for r in view["rows"]:
            left = [Paragraph(_t(r["label"]), sty["tr"])] + [Paragraph(_t(d), sty["date"]) for d in r["dates"] if d]
            cont_left = [Paragraph(_t(r["label"]), sty["tr"]), Paragraph("продолжение", sty["cont"])] + [
                Paragraph(_t(d), sty["date"]) for d in r["dates"] if d]
            parts: list[Any] = [Paragraph(_t(r["lead"]), sty["lead"])]
            for p in r["points"]:
                obj = f"<font name='{FONT_BOLD}'>{_t(p['object'])}:</font> " if p.get("object") else ""
                parts.append(Paragraph(obj + _t(p["text"]), sty["pt"]))
            for q in r.get("questions") or []:
                parts.append(Paragraph(f"<font name='{FONT_BOLD}'>Уточнить:</font> {_t(_uncap(q))}", sty["pt"]))
            if r.get("impact"):
                parts.append(Paragraph(_t(r["impact"]), sty["imp"]))
            # Sub-rows not lower than the left cell of the «continuation»: short points are glued, so that a break leaves no empty space.
            heights = [x.wrap(w_tx - 10, 1e6)[1] + 4 for x in parts]
            min_h = sum(x.wrap(w_tr - 10, 1e6)[1] for x in cont_left) + 2
            chunks: list[list[Any]] = []
            current: list[Any] = []
            current_h = 0.0
            for x, h in zip(parts, heights):
                current.append(x)
                current_h += h
                if current_h >= min_h:
                    chunks.append(current)
                    current, current_h = [], 0.0
            if current:
                if chunks and current_h < min_h:
                    chunks[-1] += current
                else:
                    chunks.append(current)
            first, last = len(rows), len(rows) + len(chunks) - 1
            for k, chunk in enumerate(chunks):
                rows.append([left if k == 0 else "", Paragraph(_t(r["scale"]), sty["scale"]) if k == 0 else "", chunk])
                group_start.append(first)
                cont[len(rows) - 1] = (cont_left, Paragraph(_t(r["scale"]), sty["scale"]))
            style += [("TOPPADDING", (0, first), (-1, first), 6), ("BOTTOMPADDING", (0, last), (-1, last), 7),
                      ("LINEBELOW", (0, last), (-1, last), 0.4, HexColor(RULE))]
            if sum(heights) + 13 < 0.25 * frame_h:
                style.append(("NOSPLIT", (0, first), (-1, last)))
            if r["points"]:
                style.append(("BACKGROUND", (0, first), (-1, last), HexColor(FILL)))
        table = ContTable(rows, colWidths=[w_tr, w_sc, w_tx], repeatRows=1)
        table._group_start, table._cont = group_start, cont
        table.setStyle(TableStyle(style))
        return s + [table]

    footer = _footer(document, code)
    doc = SimpleDocTemplate(
        str(tmp), pagesize=A4, leftMargin=MARGIN_MM * mm, rightMargin=MARGIN_MM * mm, topMargin=14 * mm,
        bottomMargin=BOTTOM_MM * mm, title=f"{code} — {view['title']}", author="", subject=view.get("section") or "",
        invariant=1,
    )
    doc._cmp_pages = pages
    doc.build(story(), onFirstPage=footer, onLaterPages=footer)
    return doc.page
