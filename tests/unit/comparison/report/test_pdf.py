"""`CMP-VC-REPORT-01`: the PDF of a report (container-free): written by a program in a child under the ceilings of ADR-0025 decision 8; every
page carries the unconfirmed label and the recall line; the Cyrillic font is embedded; the same data give the same bytes; an end without a
result is a typed failure and never a half-written file; the font and its licence are in the package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from auditmanager.comparison.profile.limits import MIB, ChildLimits
from auditmanager.comparison.profile.runner import ChildResult
from auditmanager.comparison.report import analytic, client
from auditmanager.comparison.report.model import RECORDED_LABEL, UNCONFIRMED_LABEL
from auditmanager.comparison.report.pdf import runner as pdf_runner
from auditmanager.comparison.report.pdf.check import check_pdf
from auditmanager.comparison.report.pdf.runner import PDF_LIMITS, PdfFailed, write_pdf

RECALL = "изменённых листов 3, описано 1, отброшено проверкой 2"
CODE = "133/23-ГК-ЭМ2"


def client_document(rows: int = 2, *, recorded: bool = False) -> dict[str, Any]:
    transition = {"from_version": "V1", "to_version": "V2", "from_date": "2026-01-01", "to_date": "2026-02-01"}
    stored = {
        "answer": {"change_scope": "Локальные изменения", "lead": "Заменён кабель и автомат питания.", "impact": "Потребуется закупка.",
                   "questions": [{"text": "Уточнить марку щита"}]},
        "kept": [{"point": {"object": "Кабель ВВГнг(А)-LS", "text": "3×2,5 → 3×4 мм²"}}, {"point": {"object": "Автомат QF1", "text": "16 А → 25 А"}}],
        "impact": "Потребуется закупка.",
    }
    view_rows = [client.row_of(transition, stored)]
    for k in range(2, rows + 1):
        view_rows.append(client.row_of({"from_version": f"V{k}", "to_version": f"V{k + 1}", "from_date": None, "to_date": None}, None))
    view = {"title": "Изменения проектных решений", "object": "Объект", "code": CODE, "section": "", "versions": f"V1–V{rows + 1}",
            "period": "01.01.2026–", "rows": view_rows}
    return {"kind": "client", "label": UNCONFIRMED_LABEL, "recall": RECALL, "recorded_label": RECORDED_LABEL if recorded else None,
            "code": CODE, "view": view}


@pytest.fixture(scope="module")
def written() -> Any:
    return write_pdf(client_document(2))


def test_the_package_holds_the_font_and_its_licence() -> None:
    fonts = Path(pdf_runner.FONT_DIR)
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        assert (fonts / name).stat().st_size > 400_000
    licence = (fonts / "LICENSE-DejaVu.txt").read_text(encoding="utf-8")
    assert "Bitstream" in licence and "Permission is hereby granted" in licence
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):  # the licence names the exact files it covers
        assert hashlib.sha256((fonts / name).read_bytes()).hexdigest() in licence


def test_the_pdf_has_the_label_and_the_recall_line_on_every_page_and_the_font_embedded(written) -> None:
    result = check_pdf(written.content, label=UNCONFIRMED_LABEL, recall=RECALL, transitions=["V1→V2", "V2→V3"], client=True, code=CODE)
    assert result == {"ok": True, "problems": [], "pages": written.pages}
    many = write_pdf(client_document(60))
    assert many.pages >= 2
    verdict = check_pdf(many.content, label=UNCONFIRMED_LABEL, recall=RECALL, transitions=[f"V{k}→V{k + 1}" for k in range(1, 61)], client=True, code=CODE)
    assert verdict["ok"] is True and verdict["pages"] == many.pages  # the label and the recall line are checked page by page


def test_a_pdf_without_the_label_or_with_service_words_is_not_fit(written) -> None:
    other = check_pdf(written.content, label="Совсем другая подпись", recall=RECALL, transitions=["V1→V2"], client=True, code=CODE)
    assert not other["ok"] and any("label is missing" in p for p in other["problems"])
    wrong = check_pdf(written.content, label=UNCONFIRMED_LABEL, recall="изменённых листов 9", transitions=["V1→V2", "V7→V8"], client=True, code=CODE)
    assert any("recall line is missing" in p for p in wrong["problems"]) and any("V7→V8" in p for p in wrong["problems"])


def test_the_same_data_give_the_same_bytes_and_other_data_do_not(written) -> None:
    assert write_pdf(client_document(2)).content == written.content
    assert write_pdf(client_document(3)).content != written.content


def test_a_recorded_answer_is_marked_on_the_page() -> None:
    result = write_pdf(client_document(2, recorded=True))
    assert check_pdf(result.content, label=UNCONFIRMED_LABEL + ". " + RECORDED_LABEL, recall=RECALL, transitions=["V1→V2"], client=True, code=CODE)["ok"]
    assert not check_pdf(write_pdf(client_document(2)).content, label=UNCONFIRMED_LABEL + ". " + RECORDED_LABEL, recall=RECALL, transitions=["V1→V2"], client=True, code=CODE)["ok"]


class Recording:
    """A runner that ends with the status the test chose and records the limits it was given."""

    def __init__(self, status: str, **facts: Any) -> None:
        self.status, self.facts, self.seen = status, facts, []

    def run(self, settings: Any, limits: ChildLimits) -> ChildResult:
        self.seen.append((dict(settings), limits))
        return ChildResult(self.status, facts=self.facts)


def test_the_child_runs_under_the_ceilings_of_decision_8() -> None:
    assert PDF_LIMITS == ChildLimits(768 * MIB, 300, 600.0)
    recording = Recording("overrun")
    with pytest.raises(PdfFailed):
        write_pdf(client_document(1), runner=recording)
    settings, limits = recording.seen[0]
    assert limits == PDF_LIMITS and settings["file_bytes"] == pdf_runner.OUTPUT_LIMIT_BYTES == 64 * MIB


@pytest.mark.parametrize("end", ["overrun", "cpu", "wall", "signal:SIGKILL", "error:MemoryError", "exit:3"])
def test_an_end_without_a_result_is_a_typed_failure_and_no_file_is_returned(end: str) -> None:
    with pytest.raises(PdfFailed) as failure:
        write_pdf(client_document(1), runner=Recording(end))
    assert failure.value.end == ChildResult(end).end


def test_the_real_child_is_stopped_by_the_kernel_ceiling_and_by_the_wall_clock() -> None:
    with pytest.raises(PdfFailed) as memory:
        write_pdf(client_document(1), limits=ChildLimits(24 * MIB, 300, 600.0))  # python and reportlab do not fit in 24 MiB of address space
    assert memory.value.end != "ok"
    with pytest.raises(PdfFailed) as wall:
        write_pdf(client_document(1), limits=ChildLimits(768 * MIB, 300, 0.05))
    assert wall.value.end == "wall"


def test_a_child_that_says_ok_without_a_pdf_is_not_believed() -> None:
    with pytest.raises(PdfFailed) as failure:
        write_pdf(client_document(1), runner=Recording("ok", pages=1))
    assert failure.value.end == "error:NoOutput"


def analytic_document() -> dict[str, Any]:
    transitions = [
        {"transition_id": "T01", "from_version": "V1", "to_version": "V2", "from_date": "2026-01-01", "to_date": "2026-02-01",
         "change_scope": "Локальные изменения", "significance": "Средняя", "main_changes": "Заменены кабель и автомат.",
         "changes": [{"object": "Кабель ВВГнг(А)-LS", "before": "3×2,5", "after": "3×4", "sources": ["Ф0002"], "chain_unconfirmed": False}],
         "construction_impact": "При выполнении по предыдущей версии потребовалась бы проверка.", "impact_sources": ["Ф0002"],
         "completeness": {"text": "обработаны все 1 листов", "registry": True, "counts": {"описано ИИ": 1}, "sheets_total": 1, "not_processed": [], "ambiguous": []},
         "document_marks": [], "sources": ["Ф0002"]},
        {"transition_id": "T02", "from_version": "V2", "to_version": "V3", "from_date": None, "to_date": None,
         "change_scope": "Нет изменений содержания", "significance": "Нет новых технических изменений", "main_changes": "Изменений нет.",
         "changes": [], "construction_impact": "Дополнительных технических последствий не выявлено.", "impact_sources": [],
         "completeness": {"text": "обработаны все 0 листов"}, "document_marks": [], "sources": []},
    ]
    report = {
        "schema_version": "report_v2", "project_code": CODE, "title": "Оценка изменений версий документации", "input_filename": "x.md",
        "analysis_basis": {"type": "ai_change_summary", "description": "d", "source_pdf_checked": False},
        "summary": ["Раздел переработан локально."], "summary_sources": ["Ф0002"], "transitions": transitions,
        "significant_changes": [{"priority": "P2", "title": "Замена кабеля", "version_range": "V1→V2", "before_after": "3×2,5 → 3×4",
                                 "consequence": "Потребуется проверка.", "claim_ids": ["G01.T01.F1"], "sources": ["Ф0002"], "chain_unconfirmed": False}],
        "limitations": ["Исходные PDF не проверялись."],
        "facts": [{"fact_id": "Ф0002", "md_line": 10, "transition": "V1→V2", "sheet": "л.1", "sheet_title": "План", "pages_a": [1], "pages_b": [1],
                   "confirmation": "ИИ-описание листа", "text": "Кабель ВВГнг(А)-LS — 3×2,5 → 3×4", "record": None}],
        "facts_total": 6, "coverage": [{"label": "V1→V2", "registry": True, "sheets_total": 1, "counts": {"описано ИИ": 1}}],
        "reference_warnings": [],
    }
    return {"kind": "analytic", "label": UNCONFIRMED_LABEL, "recall": RECALL, "recorded_label": None, "code": CODE, "report": report,
            "distribution": analytic.distribution(report), "analysed_at": "29.10.2026 05:00", "sha256": "ab" * 32}


def test_the_analytic_report_renders_with_its_registry_and_the_same_footer() -> None:
    document = analytic_document()
    result = write_pdf(document)
    verdict = check_pdf(result.content, label=UNCONFIRMED_LABEL, recall=RECALL, transitions=["V1→V2", "V2→V3"], client=False, code=CODE)
    assert verdict["ok"] is True, verdict
    assert write_pdf(document).content == result.content
