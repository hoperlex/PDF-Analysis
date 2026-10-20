"""The projection must reject partial joins before XLSX bytes are emitted."""

from __future__ import annotations

import io
import zipfile
from dataclasses import replace
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx.projection import (
    CitationRead,
    EvidenceLocationRead,
    FindingRead,
    ObservationRead,
    RunRead,
    VerdictRead,
    project_workbook,
)
from auditmanager.exports.xlsx.writer import render_xlsx


MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _run() -> RunRead:
    return RunRead("prj_1", "ver_1", "run_1", "ar_v3", "ns_1", "recorded")


def _observation(observation_id: str, *, page: int, label: str, text: str) -> ObservationRead:
    return ObservationRead(
        finding_observation_id=observation_id,
        finding_uid="f_1",
        category="fire_safety",
        finding_text=text,
        recommendation="Исправить",
        proposed_severity="operational",
        evidence=(EvidenceLocationRead(0, page, label),),
    )


def _finding() -> FindingRead:
    return FindingRead(
        finding_uid="f_1",
        run_id="run_1",
        category="fire_safety",
        canonical_observation_id="o_2",
        member_observation_ids=("o_3", "o_1"),
        observations=(
            _observation("o_1", page=4, label="АР-4 / стр. 4", text="Повтор 1"),
            _observation("o_2", page=2, label="АР-2 / стр. 2", text="Главное"),
            _observation("o_3", page=3, label="АР-3 / стр. 3", text="Повтор 3"),
        ),
        verdict=VerdictRead("f_1", "accepted", "critical", "Проверено"),
        citations=(CitationRead("СП 1", "п. 2", "Норма 1"),),
    )


def _sheet_cells(content: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    cells: dict[str, str] = {}
    for cell in root.findall(f".//{MAIN}c"):
        value = cell.find(f"{MAIN}is/{MAIN}t")
        if value is None:
            value = cell.find(f"{MAIN}v")
        cells[cell.attrib["r"]] = value.text or "" if value is not None else ""
    return cells


def test_canonical_member_order_verdict_citations_and_rendered_rows() -> None:
    workbook = project_workbook(_run(), (_finding(),))
    row = workbook.findings[0]
    assert row.finding_text == "Главное"
    assert row.sheet_page == "АР-2 / стр. 2"
    assert row.decided_severity == "critical"
    assert row.proposed_severity == "operational"
    assert [(item.sheet_page, item.note) for item in row.members] == [
        ("АР-3 / стр. 3", "Повтор 3"),
        ("АР-4 / стр. 4", "Повтор 1"),
    ]
    assert [(item.document, item.clause, item.quote) for item in row.citations] == [
        ("СП 1", "п. 2", "Норма 1")
    ]
    cells = _sheet_cells(render_xlsx(workbook).content)
    assert [cells[f"A{number}"] for number in (2, 3, 4)] == ["1", "", ""]
    assert [cells[f"B{number}"] for number in (2, 3, 4)] == [
        "АР-2 / стр. 2", "АР-3 / стр. 3", "АР-4 / стр. 4",
    ]
    assert cells["D2"] == "Главное"
    assert cells["C2"] == "Пожарная безопасность"
    assert cells["F2"] == "Критическое"
    assert cells["G2"] == "Эксплуатационное"
    assert cells["H2"] == "СП 1, п. 2"
    assert cells["I2"] == "Норма 1"
    assert cells["J2"] == "принято"
    assert cells["K2"] == "Проверено"


def test_rejected_verdict_carries_no_decided_severity_and_preserves_proposal() -> None:
    finding = replace(_finding(), verdict=VerdictRead("f_1", "rejected", None, None))
    row = project_workbook(_run(), (finding,)).findings[0]
    assert row.decided_severity is None
    assert row.proposed_severity == "operational"
    cells = _sheet_cells(render_xlsx(project_workbook(_run(), (finding,))).content)
    assert cells["F2"] == ""
    assert cells["G2"] == "Эксплуатационное"
    assert cells["J2"] == "отклонено"


def test_all_evidence_labels_are_explicit_and_keep_evidence_order() -> None:
    finding = _finding()
    canonical = replace(
        finding.observations[1],
        evidence=(
            EvidenceLocationRead(0, 2, "АР-2 / стр. 2"),
            EvidenceLocationRead(1, 5, "АР-5 / стр. 5"),
        ),
    )
    finding = replace(finding, observations=(finding.observations[0], canonical, finding.observations[2]))
    row = project_workbook(_run(), (finding,)).findings[0]
    assert row.sheet_page == "АР-2 / стр. 2\nАР-5 / стр. 5"


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (lambda f: replace(f, canonical_observation_id="o_missing"), "canonical_missing"),
        (lambda f: replace(f, member_observation_ids=("o_3",)), "member_partition_invalid"),
        (lambda f: replace(f, member_observation_ids=("o_1", "o_1")), "member_partition_invalid"),
        (
            lambda f: replace(f, observations=(replace(f.observations[0], finding_uid="f_other"), *f.observations[1:])),
            "observation_invalid",
        ),
        (
            lambda f: replace(f, observations=(f.observations[0], replace(f.observations[1], evidence=()), f.observations[2])),
            "evidence_missing",
        ),
        (
            lambda f: replace(f, observations=(f.observations[0], replace(f.observations[1], evidence=(EvidenceLocationRead(0, 2, ""),)), f.observations[2])),
            "evidence_invalid",
        ),
        (
            lambda f: replace(f, observations=(f.observations[0], replace(f.observations[1], evidence=(EvidenceLocationRead(2, 2, "АР-2"),)), f.observations[2])),
            "evidence_invalid",
        ),
        (lambda f: replace(f, verdict=VerdictRead("f_1", "rejected", "critical", None)), "verdict_invalid"),
        (lambda f: replace(f, verdict=VerdictRead("f_other", "accepted", "critical", None)), "verdict_invalid"),
    ],
)
def test_partial_or_inconsistent_reads_fail_closed(change, error: str) -> None:
    with pytest.raises(ValueError, match=f"xlsx_projection_{error}"):
        project_workbook(_run(), (change(_finding()),))


def test_duplicate_findings_fail_and_empty_run_is_explicit() -> None:
    with pytest.raises(ValueError, match="xlsx_projection_finding_duplicate"):
        project_workbook(_run(), (_finding(), _finding()))
    assert project_workbook(_run(), ()).findings == ()


def test_cross_run_finding_fails_before_rendering() -> None:
    with pytest.raises(ValueError, match="xlsx_projection_finding_invalid"):
        project_workbook(_run(), (replace(_finding(), run_id="run_other"),))
