"""`F8-COUNT-XLSX`: the Excel export of a ``one_list`` run, over the rows the real publisher wrote (PostgreSQL and S3).

A candidate finding of a ``one_list`` run has no ``finding_evidence`` row: it stands on blocks (``finding_block_evidence``). The workbook reads
such a run by the statement that takes a block's page as the finding's location, and gives the sheet the column «Источник»
(«Текст» / «Чертёж» / «Сверка»). What this suite pins, over the use case ``export_run_xlsx`` with the version's real portal companion:

* a ``one_list`` workbook has the thirteen columns, a block finding has a row with «Источник» = «Чертёж», its members a «также найдено» row, a
  cross-check «Сверка», a text finding «Текст»; two exports are byte-identical; the import still reads the IDs;
* a ``text_only`` run of the same version, with the same text finding, is exported with the twelve columns of before and no «Источник»;
* the control that shows the marker is what selects the read: a block finding written under a ``text_only`` run is refused, not exported with
  an empty location, while the same finding under ``one_list`` is a row.

The harness seeds the PDF and the S3 object; the run rows are inserted by ``one_list_seed`` (and the findings by the real publisher). Every
transaction is rolled back by the harness.
"""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx.reader import read_findings_sheet
from auditmanager.exports.xlsx.writer import FINDING_COLUMNS
from tests.integration.dashboard.one_list_seed import BLK_A, BLK_B, BLK_C, block_finding, insert_run, text_finding
from tests.integration.exports.test_xlsx_run_export import _add_companion, _export

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

ONE_LIST_COLUMNS = (
    "№", "Лист/стр.", "Категория", "Источник", "Замечание", "Рекомендация", "Серьёзность (решение эксперта)",
    "Серьёзность (предложение модели)", "Норма (документ, пункт)", "Цитата нормы", "Решение эксперта", "Комментарий",
    "ID замечания",
)


def _cells(content: bytes, part: str = "xl/worksheets/sheet2.xml") -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read(part))
    cells: dict[str, str] = {}
    for cell in root.findall(f".//{MAIN}c"):
        node = cell.find(f"{MAIN}is/{MAIN}t")
        if node is None:
            node = cell.find(f"{MAIN}v")
        cells[cell.attrib["r"]] = (node.text or "") if node is not None else ""
    return cells


def _row_of(cells: dict[str, str], finding_uid: str, last_column: str) -> int:
    (row,) = [int(address[1:]) for address, value in cells.items() if address[0] == last_column and value == finding_uid]
    return row


def test_a_one_list_run_exports_a_row_for_a_block_finding_with_its_source(session, seeded, blob_store) -> None:  # type: ignore[no-untyped-def]
    run = insert_run(session, seeded.project_uid, seeded.version_uid, mode="one_list")
    written = text_finding(session, seeded.project_uid, seeded.version_uid, run, "pending")
    drawing = block_finding(session, seeded.project_uid, seeded.version_uid, run, "pending", members=((BLK_A,), (BLK_C,)), group_id="xgrp_1")
    cross = block_finding(
        session, seeded.project_uid, seeded.version_uid, run, "pending", members=((BLK_B,),), group_id="xgrp_2", other_source_count=1
    )
    _add_companion(session, blob_store, seeded.version_uid)

    export = _export(session, blob_store, run)
    assert export.run_state == "published" and export.content == _export(session, blob_store, run).content

    sheet = _cells(export.content)
    assert tuple(sheet[f"{column}1"] for column in "ABCDEFGHIJKLM") == ONE_LIST_COLUMNS
    assert "N1" not in sheet

    # a text finding: the text of the document, located by its span (page 1, labelled 101 by the companion)
    text_row = _row_of(sheet, written, "M")
    assert (sheet[f"B{text_row}"], sheet[f"C{text_row}"], sheet[f"D{text_row}"]) == ("101", "Планировочные решения", "Текст")

    # a block finding: a row, its place is the page of its canonical observation's block (page 2 -> 102), «Чертёж»
    drawing_row = _row_of(sheet, drawing.finding_uid, "M")
    assert (sheet[f"B{drawing_row}"], sheet[f"C{drawing_row}"], sheet[f"D{drawing_row}"]) == ("102", "Расхождение на чертеже", "Чертёж")
    assert sheet[f"E{drawing_row}"] == "Размер не совпадает с планом (xgrp_1_0)."
    assert sheet[f"F{drawing_row}"] == "Требуется проверка эксперта по источнику" and sheet[f"K{drawing_row}"] == "не решено"
    # ... and its second candidate is a «также найдено» row under it: block on page 3 -> 103, no ID of its own
    member = drawing_row + 1
    assert (sheet[f"B{member}"], sheet[f"D{member}"], sheet[f"E{member}"], sheet[f"L{member}"], sheet[f"M{member}"]) == (
        "103", "", "также найдено", "Размер не совпадает с планом (xgrp_1_1).", "",
    )

    # a group that stands on a block and on another source is a cross-check
    cross_row = _row_of(sheet, cross.finding_uid, "M")
    assert (sheet[f"C{cross_row}"], sheet[f"D{cross_row}"]) == ("Расхождение источников", "Сверка")

    # «Сводка» counts the two new categories by their words
    summary = _cells(export.content, "xl/worksheets/sheet1.xml")
    counted = {summary[f"A{row}"]: summary[f"B{row}"] for row in range(1, 40) if f"A{row}" in summary}
    assert counted["Расхождение на чертеже"] == "1" and counted["Расхождение источников"] == "1" and counted["Планировочные решения"] == "1"

    # the import by «ID замечания» reads the same workbook: the three findings by their IDs, no row for a member
    assert sorted(row.finding_uid for row in read_findings_sheet(export.content) if row.finding_uid) == sorted(
        [written, drawing.finding_uid, cross.finding_uid]
    )


def test_a_one_list_run_with_no_finding_still_has_the_column(session, seeded, blob_store) -> None:  # type: ignore[no-untyped-def]
    run = insert_run(session, seeded.project_uid, seeded.version_uid, mode="one_list")
    _add_companion(session, blob_store, seeded.version_uid)
    sheet = _cells(_export(session, blob_store, run).content)
    assert tuple(sheet[f"{column}1"] for column in "ABCDEFGHIJKLM") == ONE_LIST_COLUMNS
    assert {address for address in sheet if address[1:] != "1"} == set()


def test_a_text_only_run_of_the_same_version_is_exported_as_before(session, seeded, blob_store) -> None:  # type: ignore[no-untyped-def]
    run = insert_run(session, seeded.project_uid, seeded.version_uid, mode="text_only")
    written = text_finding(session, seeded.project_uid, seeded.version_uid, run, "accepted")
    _add_companion(session, blob_store, seeded.version_uid)
    export = _export(session, blob_store, run)
    sheet = _cells(export.content)
    assert tuple(sheet[f"{column}1"] for column in "ABCDEFGHIJKL") == FINDING_COLUMNS and "M1" not in sheet
    assert "Источник" not in set(sheet.values())
    # the same text finding as in the one-list workbook above, in the columns it always had
    row = _row_of(sheet, written, "L")
    assert (sheet[f"B{row}"], sheet[f"C{row}"], sheet[f"D{row}"], sheet[f"J{row}"]) == (
        "101", "Планировочные решения", "Текстовое замечание", "принято",
    )


def test_the_control_the_marker_selects_the_read_a_block_finding_under_text_only_is_refused(session, seeded, blob_store) -> None:  # type: ignore[no-untyped-def]
    """The publisher takes any run id; only a ``one_list`` run is read by the statement that knows a block's page."""
    refused = insert_run(session, seeded.project_uid, seeded.version_uid, mode="text_only")
    block_finding(session, seeded.project_uid, seeded.version_uid, refused, "pending")
    allowed = insert_run(session, seeded.project_uid, seeded.version_uid, mode="one_list")
    block_finding(session, seeded.project_uid, seeded.version_uid, allowed, "pending")
    _add_companion(session, blob_store, seeded.version_uid)

    with pytest.raises(ValueError, match="xlsx_read_incomplete_finding"):
        _export(session, blob_store, refused)
    assert tuple(_cells(_export(session, blob_store, allowed).content)[f"{column}1"] for column in "ABCDEFGHIJKLM") == ONE_LIST_COLUMNS
