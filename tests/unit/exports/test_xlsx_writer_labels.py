"""`XLSX-RU-LABELS-01`: the writer prints the screens' Russian words for enum cells.

Pure checks on the deterministic writer: no database, no storage, no spreadsheet application.
The expected words are written out here as literals on purpose. ``labels.py`` is held equal to
the web tables by ``test_xlsx_labels_lockstep.py``; these literals hold the *workbook* to the
words, so a table edited on both sides still has to be edited here, on purpose.
"""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx import Citation, FindingMember, FindingRow, WorkbookInput, render_xlsx
from auditmanager.exports.xlsx.writer import SEVERITIES

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

CATEGORIES = {
    "internal_contradiction": "Внутреннее противоречие",
    "explicit_placeholder": "Явный пропуск",
    "dimensions": "Размеры помещений",
    "layout": "Планировочные решения",
    "facade": "Фасадные решения",
    "roof": "Кровля",
    "documentation": "Документация",
    "evacuation": "Эвакуация",
    "fire_safety": "Пожарная безопасность",
    "accessibility": "Доступность",
    "insulation": "Теплоизоляция",
    "sound": "Звукоизоляция",
}
SEVERITY_WORDS = {
    "critical": "Критическое",
    "economic": "Экономическое",
    "operational": "Эксплуатационное",
    "recommendation": "Рекомендация",
    "check_adjacent": "Проверить смежный раздел",
}
VERDICT_WORDS = {
    "pending": "не решено",
    "accepted": "принято",
    "rejected": "отклонено",
    "needs_manual_review": "нужен ручной разбор",
}
RAW_VALUES = {*CATEGORIES, *SEVERITY_WORDS, *VERDICT_WORDS}


def _source(*findings: FindingRow) -> WorkbookInput:
    return WorkbookInput(
        project_uid="prj_01M5B0000000000000000000P1",
        version_uid="ver_01M5B0000000000000000000V1",
        run_id="run_01M5B0000000000000000000R1",
        profile_id="ar_v3",
        snapshot_key="ns_1",
        attribution="ответы модели воспроизведены из записи (recorded)",
        findings=tuple(findings),
    )


def _finding(uid: str = "f_1", **changes: object) -> FindingRow:
    values: dict[str, object] = dict(
        finding_uid=uid, sheet_page="АР-1 / 3", category="fire_safety",
        finding_text="Замечание", proposed_severity="economic",
    )
    values.update(changes)
    return FindingRow(**values)  # type: ignore[arg-type]


def _sheets(source: WorkbookInput) -> tuple[dict[str, str], dict[str, str], bytes]:
    content = render_xlsx(source).content
    out = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for part in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"):
            cells = {}
            for cell in ET.fromstring(archive.read(part)).iter(f"{MAIN}c"):
                node = cell.find(f"{MAIN}is/{MAIN}t")
                if node is None:
                    node = cell.find(f"{MAIN}v")
                cells[cell.attrib["r"]] = (node.text or "") if node is not None else ""
            out.append(cells)
    return out[0], out[1], content


def test_every_category_severity_and_verdict_is_printed_as_its_screen_word() -> None:
    categories = list(CATEGORIES)
    severities = list(SEVERITY_WORDS)
    verdicts = list(VERDICT_WORDS)
    findings = tuple(
        _finding(
            f"f_{index:02d}",
            category=category,
            decided_severity=severities[index % 5] if verdicts[index % 4] == "accepted" else None,
            proposed_severity=severities[(index + 1) % 5],
            expert_decision=verdicts[index % 4],
        )
        for index, category in enumerate(categories)
    )
    _, sheet, _ = _sheets(_source(*findings))
    for index, category in enumerate(categories):
        row = index + 2
        assert sheet[f"C{row}"] == CATEGORIES[category]
        verdict = verdicts[index % 4]
        assert sheet[f"J{row}"] == VERDICT_WORDS[verdict]
        decided = severities[index % 5] if verdict == "accepted" else None
        assert sheet[f"F{row}"] == (SEVERITY_WORDS[decided] if decided else "")
        assert sheet[f"G{row}"] == SEVERITY_WORDS[severities[(index + 1) % 5]]
    # All twelve categories, all five severities and all four verdicts really occurred.
    assert {sheet[f"C{index + 2}"] for index in range(12)} == set(CATEGORIES.values())
    assert {sheet[f"G{index + 2}"] for index in range(12)} == set(SEVERITY_WORDS.values())
    assert {sheet[f"J{index + 2}"] for index in range(12)} == set(VERDICT_WORDS.values())


def test_the_summary_counts_are_labelled_and_no_raw_value_survives_anywhere() -> None:
    findings = tuple(
        _finding(
            f"f_{index:02d}", category=category,
            decided_severity="critical" if index % 2 else None,
            proposed_severity=list(SEVERITY_WORDS)[index % 5],
            expert_decision="accepted" if index % 2 else "pending",
        )
        for index, category in enumerate(CATEGORIES)
    )
    summary, sheet, _ = _sheets(_source(*findings))
    assert [summary[f"A{row}"] for row in range(9, 15)] == [
        *SEVERITY_WORDS.values(), "Без серьёзности",
    ]
    # Categories keep the order of the contract value, and show the label.
    counted = [summary[f"A{row}"] for row in range(16, 28)]
    assert counted == [CATEGORIES[key] for key in sorted(CATEGORIES)]
    for sheet_cells in (summary, sheet):
        leaked = RAW_VALUES & set(sheet_cells.values())
        assert not leaked, leaked


def test_identifiers_and_free_text_are_written_verbatim_even_when_they_look_like_a_value() -> None:
    word = "critical"
    finding = _finding(
        sheet_page="fire_safety", finding_text="pending", recommendation=word,
        comment="accepted", members=(FindingMember("roof", "economic"),),
        citations=(Citation("sound", "layout", "check_adjacent"),),
        decided_severity="critical", expert_decision="accepted",
    )
    summary, sheet, _ = _sheets(_source(finding))
    assert (summary["B2"], summary["B3"], summary["B4"]) == (
        "prj_01M5B0000000000000000000P1", "ver_01M5B0000000000000000000V1",
        "run_01M5B0000000000000000000R1",
    )
    assert summary["B5"] == "ar_v3" and summary["B6"] == "ns_1"
    assert summary["B7"] == "ответы модели воспроизведены из записи (recorded)"
    assert [sheet[f"{column}2"] for column in "BDEHIK"] == [
        "fire_safety", "pending", word, "sound, layout", "check_adjacent", "accepted",
    ]
    assert (sheet["B3"], sheet["D3"], sheet["K3"]) == ("roof", "также найдено", "economic")
    # ... while the enum cells of the same row are the words.
    assert (sheet["C2"], sheet["F2"], sheet["G2"], sheet["J2"]) == (
        "Пожарная безопасность", "Критическое", "Экономическое", "принято",
    )


def test_no_formula_and_every_cell_is_inline_text_or_a_count() -> None:
    findings = tuple(
        _finding(f"f_{index}", category=category, decided_severity="critical",
                 expert_decision="accepted")
        for index, category in enumerate(CATEGORIES)
    )
    summary, sheet, content = _sheets(_source(*findings))
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            body = archive.read(name)
            assert b"<f>" not in body and b"<f " not in body, name
        for part in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"):
            for cell in ET.fromstring(archive.read(part)).iter(f"{MAIN}c"):
                assert cell.find(f"{MAIN}f") is None
                is_count = cell.find(f"{MAIN}v") is not None
                assert is_count == (cell.get("t") is None), cell.attrib["r"]
    # No label begins with a character a spreadsheet application reads as a formula.
    for value in (*CATEGORIES.values(), *SEVERITY_WORDS.values(), *VERDICT_WORDS.values()):
        assert value[0] not in "=+-@\t\r"
    assert summary and sheet


def test_the_severity_fill_still_follows_the_value_and_not_the_word() -> None:
    findings = tuple(
        _finding(f"f_{index}", proposed_severity=severity)
        for index, severity in enumerate(SEVERITIES)
    )
    content = render_xlsx(_source(*findings)).content
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    styles = {cell.attrib["r"]: cell.attrib["s"] for cell in sheet.iter(f"{MAIN}c")}
    assert [styles[f"A{row}"] for row in range(2, 7)] == ["2", "3", "4", "5", "6"]


def test_the_empty_verdict_and_missing_severity_stay_empty_cells() -> None:
    _, sheet, _ = _sheets(_source(_finding(proposed_severity=None)))
    assert (sheet["F2"], sheet["G2"], sheet["J2"]) == ("", "", "")


@pytest.mark.parametrize(
    ("change", "refusal"),
    [
        ({"category": "urgent"}, "xlsx_category_invalid"),
        ({"category": "Fire_Safety"}, "xlsx_category_invalid"),
        ({"category": " fire_safety"}, "xlsx_category_invalid"),
        # An already-translated word is not a contract value: no double translation.
        ({"category": "Пожарная безопасность"}, "xlsx_category_invalid"),
        ({"decided_severity": "Критическое"}, "xlsx_severity_invalid"),
        ({"proposed_severity": "urgent"}, "xlsx_severity_invalid"),
        ({"expert_decision": "accept"}, "xlsx_verdict_invalid"),  # a proposal verdict
        ({"expert_decision": "Accepted"}, "xlsx_verdict_invalid"),
        ({"expert_decision": "принято"}, "xlsx_verdict_invalid"),
        ({"expert_decision": " "}, "xlsx_verdict_invalid"),
        ({"expert_decision": 5}, "xlsx_verdict_invalid"),
    ],
)
def test_a_value_outside_the_closed_sets_is_refused_never_printed_raw(
    change: dict[str, object], refusal: str
) -> None:
    with pytest.raises(ValueError, match=refusal):
        render_xlsx(_source(_finding(**change)))
