"""`XLSX-RU-LABELS-01`: the writer prints the screens' Russian words for enum cells.

Pure checks on the deterministic writer: no database, no storage, no spreadsheet application.
The expected words are written out here as literals on purpose. ``labels.py`` is held equal to
the web tables by ``test_xlsx_labels_lockstep.py``; these literals hold the *workbook* to the
words, so a table edited on both sides still has to be edited here, on purpose.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from xml.etree import ElementTree as ET

import pytest

from auditmanager.exports.xlsx import Citation, FindingMember, FindingRow, WorkbookInput, render_xlsx
from auditmanager.exports.xlsx import writer
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


def _corpus() -> WorkbookInput:
    """Every category x verdict, all severities, citations, members, formula-like text."""
    findings = []
    for index, category in enumerate(CATEGORIES):
        for step, verdict in enumerate(VERDICT_WORDS):
            number = index * 4 + step
            findings.append(_finding(
                f"f_{number:03d}", category=category, expert_decision=verdict,
                decided_severity=list(SEVERITY_WORDS)[number % 5] if verdict == "accepted" else None,
                proposed_severity=list(SEVERITY_WORDS)[(number * 3) % 5] if number % 7 else None,
                recommendation="+SUM(1,2)" if number % 3 == 0 else "",
                citations=(Citation("СП 1", "п. 2", f"Цитата {number}"),) if number % 2 else (),
                members=(FindingMember(f"АР-{number} / 9", "повтор"),) if number % 4 == 0 else (),
            ))
    return _source(*findings)


def _skeleton(part: bytes) -> bytes:
    """A sheet part with every cell's text blanked: structure, order, styles, widths remain."""
    return re.sub(rb'(<t xml:space="preserve">)[^<]*(</t>)', rb"\1\2", part)


def test_only_the_enum_cells_differ_from_the_raw_value_rendering(monkeypatch) -> None:
    """The layout, styles and every non-enum cell are what the raw-value writer produced.

    The previous writer printed the contract value in these cells, which is what the identity
    tables below do again. Comparing the two ZIPs part by part shows the change is exactly the
    enum cells, each moved by its table and nothing else: same parts, same bytes outside the two
    sheets, same cell addresses, styles and widths.
    """
    source = _corpus()
    labelled = render_xlsx(source).content
    identity = {name: {key: key for key in table} for name, table in (
        ("SEVERITY_LABELS", writer.SEVERITY_LABELS),
        ("CATEGORY_LABELS", writer.CATEGORY_LABELS),
        ("VERDICT_LABELS", writer.VERDICT_LABELS),
    )}
    for name, table in identity.items():
        monkeypatch.setattr(writer, name, table)
    raw = render_xlsx(source).content
    monkeypatch.undo()

    with zipfile.ZipFile(io.BytesIO(raw)) as before, zipfile.ZipFile(io.BytesIO(labelled)) as after:
        assert before.namelist() == after.namelist()
        changed = [name for name in before.namelist() if before.read(name) != after.read(name)]
        assert changed == ["xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"]
        moved_total = 0
        words = {**SEVERITY_WORDS, **CATEGORIES, **VERDICT_WORDS}
        for name in changed:
            assert _skeleton(before.read(name)) == _skeleton(after.read(name)), name
            old = {c.attrib["r"]: "".join(t.text or "" for t in c.iter(f"{MAIN}t"))
                   for c in ET.fromstring(before.read(name)).iter(f"{MAIN}c")}
            new = {c.attrib["r"]: "".join(t.text or "" for t in c.iter(f"{MAIN}t"))
                   for c in ET.fromstring(after.read(name)).iter(f"{MAIN}c")}
            assert list(old) == list(new)
            moved = {address for address in old if old[address] != new[address]}
            assert moved, name
            assert all(new[address] == words[old[address]] for address in moved), name
            allowed = set("CFGJ") if name.endswith("sheet2.xml") else {"A"}
            assert {re.match("[A-Z]+", address).group(0) for address in moved} <= allowed
            moved_total += len(moved)
    # 17 summary rows (5 severities + 12 categories) and, on the sheet, one category and one
    # verdict per finding plus the severity cells that are set.
    assert moved_total > 17 + 2 * 48


#: SHA-256 of each part of ``_corpus()``'s workbook, the two sheets with their cell text
#: blanked (``_skeleton``). **Captured from the writer of base commit ``59f976fc``, which printed
#: the contract values**, and equal to this writer's: the labels moved text and nothing else. A
#: deliberate layout change (a column, a width, a style, a sheet name, the cell order) changes a
#: digest and must re-pin it here, in the same change, on purpose.
LAYOUT_DIGESTS = {
    "[Content_Types].xml": "de7b6ad03ba57780707e68a38d9b57cb5c95f8cde27469d3aed927a03aa5b93e",
    "_rels/.rels": "f2f3948a1b6f661f2a5169a86b7029166acd4b79d7abfd37fa2b646fe302bfd6",
    "xl/workbook.xml": "6cc215ecd3183af404a50d46f80668ca5955fb55f2c12bc990115801b7e86ead",
    "xl/_rels/workbook.xml.rels": "2372344717cc04fdf4983d6b5a2a815515cb851c5fcca40de351ff35dfdd63a2",
    "xl/styles.xml": "58fd2aaf6abb52a2eefbea4eedbb452a62cef186b3301c201c69fec7ac6eb126",
    "xl/worksheets/sheet1.xml": "10e015b0e0d9fd99e3f16ebbcec27aaf3373c7a66a839c58525ced6ac08f0ee6",
    "xl/worksheets/sheet2.xml": "e5ef8607bf2ee9f5e1dcdcd096179c7f653699269dd6fd7c5febcfd4e28acd45",
}


def _is_enum_cell(sheet: str, address: str) -> bool:
    """The cells this change moved: sheet column C/F/G/J below the header; summary label rows."""
    column, row = re.fullmatch(r"([A-Z]+)([0-9]+)", address).groups()  # type: ignore[union-attr]
    if sheet.endswith("sheet2.xml"):
        return column in "CFGJ" and int(row) >= 2
    return column == "A" and (9 <= int(row) <= 13 or int(row) >= 16)


def _text_digest(archive: zipfile.ZipFile, sheet: str) -> str:
    """SHA-256 of every cell's address and text, the enum cells' text masked."""
    lines = []
    for cell in ET.fromstring(archive.read(sheet)).iter(f"{MAIN}c"):
        address = cell.attrib["r"]
        text = "".join(t.text or "" for t in cell.iter(f"{MAIN}t")) or "".join(
            v.text or "" for v in cell.iter(f"{MAIN}v")
        )
        lines.append(f"{address}={'<enum>' if _is_enum_cell(sheet, address) else text}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


#: SHA-256 of every cell's text outside the enum cells (identifiers, headers, counts, free text,
#: page labels, citations, "также найдено"), captured from the base writer like the digests above.
TEXT_DIGESTS = {
    "xl/worksheets/sheet1.xml": "e25dac707e13425f7849d89d23d2954eade3b7e99f0ec29651ae9e9652b6b5b6",
    "xl/worksheets/sheet2.xml": "17c4156f0fe83e9fdd8ce520714ebbd5f815bd03fef103bfe7fddcba4c75a47e",
}


def test_the_text_outside_the_enum_cells_is_the_one_the_raw_value_writer_produced() -> None:
    with zipfile.ZipFile(io.BytesIO(render_xlsx(_corpus()).content)) as archive:
        shown = {name: _text_digest(archive, name) for name in TEXT_DIGESTS}
    assert shown == TEXT_DIGESTS


def test_the_layout_is_the_one_the_raw_value_writer_produced() -> None:
    content = render_xlsx(_corpus()).content
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        shown = {}
        for name in archive.namelist():
            part = archive.read(name)
            shown[name] = hashlib.sha256(
                _skeleton(part) if name.startswith("xl/worksheets/") else part
            ).hexdigest()
    assert shown == LAYOUT_DIGESTS
