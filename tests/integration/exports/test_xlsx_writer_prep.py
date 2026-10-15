"""Focused W57b XLSX package and review-layout checks, without a DB or soffice."""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx import (
    Citation,
    FindingMember,
    FindingRow,
    WorkbookInput,
    render_xlsx,
)
from auditmanager.exports.xlsx.writer import CONTENT_TYPE, FINDING_COLUMNS, SEVERITIES

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _source(*findings: FindingRow) -> WorkbookInput:
    return WorkbookInput(
        project_uid="prj_1",
        version_uid="ver_1",
        run_id="run_1",
        profile_id="ar_v3",
        snapshot_key="ns_1",
        attribution="recorded",
        findings=tuple(findings),
    )


def _finding(**changes: object) -> FindingRow:
    values = dict(
        finding_uid="f_1",
        sheet_page="АР-1 / 3",
        category="fire_safety",
        finding_text="Замечание",
        recommendation="Исправить",
        proposed_severity="economic",
    )
    values.update(changes)
    return FindingRow(**values)


def _parts(source: WorkbookInput) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(render_xlsx(source).content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _cells(sheet: bytes) -> dict[str, tuple[str, str]]:
    root = ET.fromstring(sheet)
    result = {}
    for cell in root.findall(f".//{MAIN}c"):
        text = cell.find(f"{MAIN}is/{MAIN}t")
        number = cell.find(f"{MAIN}v")
        result[cell.attrib["r"]] = (
            text.text or "" if text is not None else number.text if number is not None else "",
            cell.attrib["s"],
        )
    return result


def test_repeat_bytes_stored_parts_order_timestamps_and_two_sheet_names():
    source = _source(_finding())
    first = render_xlsx(source)
    assert first.content == render_xlsx(source).content
    assert first.content_type == CONTENT_TYPE
    with zipfile.ZipFile(io.BytesIO(first.content)) as archive:
        infos = archive.infolist()
        assert [info.filename for info in infos] == [
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/styles.xml",
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
        ]
        assert all(info.compress_type == zipfile.ZIP_STORED for info in infos)
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in infos)
        assert archive.testzip() is None
        for info in infos:
            ET.fromstring(archive.read(info.filename))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        assert [sheet.attrib["name"] for sheet in workbook.findall(f".//{MAIN}sheet")] == [
            "Сводка",
            "Замечания",
        ]


def test_summary_totals_use_decided_then_proposed_and_categories():
    source = _source(
        _finding(decided_severity="critical", members=(FindingMember("АР-2 / 4"),)),
        _finding(
            finding_uid="f_2", category="accessibility", proposed_severity="operational"
        ),
        _finding(finding_uid="f_3", category="fire_safety", proposed_severity=None),
    )
    summary = _cells(_parts(source)["xl/worksheets/sheet1.xml"])
    assert [summary[f"B{row}"][0] for row in range(2, 8)] == [
        "prj_1", "ver_1", "run_1", "ar_v3", "ns_1", "recorded"
    ]
    assert [(summary[f"A{row}"][0], summary[f"B{row}"][0]) for row in range(9, 15)] == [
        ("critical", "1"),
        ("economic", "0"),
        ("operational", "1"),
        ("recommendation", "0"),
        ("check_adjacent", "0"),
        ("Без серьёзности", "1"),
    ]
    assert [(summary[f"A{row}"][0], summary[f"B{row}"][0]) for row in (16, 17)] == [
        ("accessibility", "1"), ("fire_safety", "2")
    ]
    assert len(SEVERITIES) == 5


def test_findings_columns_multicitation_member_rows_color_and_frozen_header():
    source = _source(
        _finding(
            citations=(
                Citation("СП 1", "п. 2", "Первая цитата"),
                Citation("СП 2", "табл. 3", "Вторая цитата"),
            ),
            members=(FindingMember("АР-2 / 4", "повтор"), FindingMember("АР-3 / 5")),
        )
    )
    sheet = _parts(source)["xl/worksheets/sheet2.xml"]
    cells = _cells(sheet)
    assert tuple(cells[f"{chr(65 + i)}1"][0] for i in range(11)) == FINDING_COLUMNS
    assert cells["A2"] == ("1", "3")  # economic row fill
    assert cells["H2"][0] == "СП 1, п. 2\nСП 2, табл. 3"
    assert cells["I2"][0] == "Первая цитата\nВторая цитата"
    assert cells["A3"][0] == ""
    assert cells["B3"][0] == "АР-2 / 4"
    assert cells["D3"] == ("также найдено", "3")
    assert cells["K3"][0] == "повтор"
    assert cells["D4"][0] == "также найдено"
    root = ET.fromstring(sheet)
    pane = root.find(f".//{MAIN}pane")
    assert pane is not None and pane.attrib["state"] == "frozen"
    assert len(root.findall(f".//{MAIN}col")) == 11


def test_formulas_are_literal_strings_xml_forbidden_replaced_and_counted():
    source = _source(
        _finding(
            finding_text="=1+1\x00\ud800",
            recommendation="+SUM(1,2)",
            comment="@cmd",
            citations=(Citation("СП", "", "-2 + 3\x01"),),
        )
    )
    rendered = render_xlsx(source)
    assert rendered.replacement_count == 3
    parts = _parts(source)
    assert all(b"<f>" not in part and b"<f " not in part for part in parts.values())
    cells = _cells(parts["xl/worksheets/sheet2.xml"])
    assert cells["D2"][0] == "=1+1\ufffd\ufffd"
    assert cells["E2"][0] == "+SUM(1,2)"
    assert cells["K2"][0] == "@cmd"
    assert cells["I2"][0] == "-2 + 3\ufffd"


def test_cell_limit_empty_workbook_and_invalid_inputs_fail_closed():
    empty = _cells(_parts(_source())["xl/worksheets/sheet2.xml"])
    assert len(empty) == 11
    render_xlsx(_source(_finding(finding_text="x" * 32_767)))
    with pytest.raises(ValueError, match="xlsx_cell_too_long"):
        render_xlsx(_source(_finding(finding_text="x" * 32_768)))
    with pytest.raises(ValueError, match="xlsx_severity_invalid"):
        render_xlsx(_source(_finding(proposed_severity="urgent")))
    with pytest.raises(ValueError, match="xlsx_finding_identity_invalid"):
        render_xlsx(_source(_finding(), _finding()))
