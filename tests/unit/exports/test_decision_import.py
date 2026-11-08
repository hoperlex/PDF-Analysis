"""Loading decisions back from our own run workbook (`R-151d`, contract 1.27.0).

The reader is exercised on the bytes our writer produces and on the shape a spreadsheet program saves
(shared strings, renamed parts, moved columns); the importer's row rules on a stand-in session whose
ledger appends are captured. The ledger itself, the command claim and the HTTP surface are the
integration suite's.
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Any

import pytest

from auditmanager.exports.xlsx import FindingMember, FindingRow, WorkbookInput, render_xlsx
from auditmanager.exports.xlsx import decision_import
from auditmanager.exports.xlsx.reader import SheetRow, read_findings_sheet
from auditmanager.shared.errors import DomainError

RUN = "run_01M5B0000000000000000000R1"
F1 = "fnd_01M5B0000000000000000000F1"
F2 = "fnd_01M5B0000000000000000000F2"
F3 = "fnd_01M5B0000000000000000000F3"


def _workbook() -> bytes:
    return render_xlsx(WorkbookInput(
        project_uid="prj_01M5B0000000000000000000P1", version_uid="ver_01M5B0000000000000000000V1", run_id=RUN,
        profile_id="ar_v2", snapshot_key="ns_1", attribution="тест",
        findings=(
            FindingRow(finding_uid=F1, sheet_page="АР-1", category="roof", finding_text="Кровля",
                       expert_decision="pending"),
            FindingRow(finding_uid=F2, sheet_page="АР-2", category="facade", finding_text="Фасад",
                       expert_decision="accepted", comment="верно", members=(FindingMember("АР-3"),)),
        ),
    )).content


def _replace_sheet(content: bytes, edit: Any) -> bytes:
    """The workbook with «Замечания» (``sheet2.xml``) rewritten by ``edit``."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(out, "w") as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "xl/worksheets/sheet2.xml":
                data = edit(data.decode("utf-8")).encode("utf-8")
            target.writestr(info, data)
    return out.getvalue()


def _set_cell(sheet: str, address: str, value: str) -> str:
    return re.sub(
        rf'(<c r="{address}"[^>]*><is><t xml:space="preserve">)[^<]*(</t></is></c>)', rf"\g<1>{value}\g<2>", sheet,
    )


class TestTheReader:
    def test_reads_our_export_by_the_id_column(self) -> None:
        rows = read_findings_sheet(_workbook())
        assert rows == (
            SheetRow(row=2, finding_uid=F1, decision="не решено", comment=""),
            SheetRow(row=3, finding_uid=F2, decision="принято", comment="верно"),
            SheetRow(row=4, finding_uid="", decision="", comment=""),  # «также найдено»
        )

    def test_reads_an_edited_cell(self) -> None:
        edited = _replace_sheet(_workbook(), lambda sheet: _set_cell(sheet, "J2", "Отклонено"))
        assert read_findings_sheet(edited)[0].decision == "Отклонено"

    def test_reads_shared_strings_and_moved_columns_as_a_spreadsheet_program_saves_them(self) -> None:
        sheet = (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="s"><v>1</v></c><c r="D1" t="s"><v>2</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="C2" t="s"><v>4</v></c><c r="D2"><v>5</v></c></row>'
            '</sheetData></worksheet>'
        )
        strings = "".join(f"<si><t>{text}</t></si>" for text in (
            "Комментарий", "ID замечания", "Решение эксперта", "нужно поправить", F1, "принято",
        ))
        shared = f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{strings}</sst>'
        content = _package({"xl/worksheets/data.xml": sheet, "xl/sharedStrings.xml": shared}, shared=True)
        assert read_findings_sheet(content) == (SheetRow(row=2, finding_uid=F1, decision="5", comment="нужно поправить"),)

    @pytest.mark.parametrize(("content", "constraint"), [
        (b"not a zip", "unreadable"),
        (b"PK" + b"\0" * (10 * 1024 * 1024), "too_large"),
    ], ids=["not-a-zip", "over-10-mib"])
    def test_refuses_what_is_not_an_xlsx(self, content: bytes, constraint: str) -> None:
        with pytest.raises(DomainError) as refused:
            read_findings_sheet(content)
        assert refused.value.detail_fields["constraint"] == constraint

    def test_refuses_a_foreign_workbook_whole(self) -> None:
        sheet = (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            '<row r="1"><c r="A1" t="inlineStr"><is><t>ID замечания</t></is></c></row></sheetData></worksheet>'
        )
        foreign = _package({"xl/worksheets/data.xml": sheet}, shared=False, sheet_name="Лист1")
        with pytest.raises(DomainError) as refused:
            read_findings_sheet(foreign)
        assert refused.value.detail_fields["constraint"] == "not_our_export"

    def test_refuses_an_export_without_the_id_column(self) -> None:
        without = _replace_sheet(_workbook(), lambda sheet: _set_cell(sheet, "L1", "Код"))
        with pytest.raises(DomainError) as refused:
            read_findings_sheet(without)
        assert refused.value.detail_fields["constraint"] == "not_our_export"

    def test_refuses_an_entity_declaration_before_parsing(self) -> None:
        hostile = _replace_sheet(_workbook(), lambda sheet: sheet.replace(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]>',
        ))
        with pytest.raises(DomainError) as refused:
            read_findings_sheet(hostile)
        assert refused.value.detail_fields["constraint"] == "unreadable"


def _package(parts: dict[str, str], *, shared: bool, sheet_name: str = "Замечания") -> bytes:
    """A minimal workbook whose «Замечания» lives in a part named unlike ours."""
    relationships = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/data.xml"/>'
        + ('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
           'sharedStrings" Target="sharedStrings.xml"/>' if shared else "")
        + "</Relationships>"
    )
    files = {
        "_rels/.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": relationships,
        **parts,
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text.encode("utf-8"))
    return out.getvalue()


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


class _Session:
    def __init__(self, findings: list[dict[str, Any]]) -> None:
        self._findings = findings

    def execute(self, _statement: Any, parameters: dict[str, Any]) -> _Result:
        return _Result([row for row in self._findings if row["finding_uid"] in parameters["finding_uids"]])


def _finding(uid: str, verdict: str = "pending", comment: str | None = None, run: str = RUN) -> dict[str, Any]:
    return {"finding_uid": uid, "allocated_by_run_id": run, "observation_id": f"obs_{uid[-2:]}",
            "current_verdict": verdict, "latest_comment": comment}


@pytest.fixture
def appended(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(decision_import, "record_decision", lambda _session, **event: events.append(event))
    return events


def _run(rows: list[SheetRow], findings: list[dict[str, Any]]) -> list[tuple[int, str, str | None, str | None]]:
    report = decision_import._import(_Session(findings), RUN, rows, "Эксперт", "usr_01M5B0000000000000000000U1")
    return [(row.row, row.outcome, row.finding_uid, row.reason) for row in report]


class TestTheRowRules:
    def test_a_changed_decision_is_an_event_by_the_importer_with_the_row_comment(self, appended: list) -> None:
        assert _run([SheetRow(2, F1, "Отклонено", "не по норме")], [_finding(F1)]) == [(2, "recorded", F1, None)]
        assert appended == [{
            "finding_uid": F1, "finding_observation_id": "obs_F1", "event_type": "reject", "comment": "не по норме",
            "author_label": "Эксперт", "author_user_uid": "usr_01M5B0000000000000000000U1",
            "origin_kind": "imported",
        }]

    def test_the_same_decision_and_comment_record_nothing(self, appended: list) -> None:
        rows = [SheetRow(2, F1, "принято", "верно"), SheetRow(3, F2, "не решено", "")]
        assert _run(rows, [_finding(F1, "accepted", "верно"), _finding(F2)]) == [
            (2, "unchanged", F1, None), (3, "unchanged", F2, None),
        ]
        assert appended == []

    def test_a_new_comment_alone_is_a_comment_event(self, appended: list) -> None:
        assert _run([SheetRow(2, F1, "принято", "уточнить узел")], [_finding(F1, "accepted", "верно")]) == [
            (2, "recorded", F1, None),
        ]
        assert appended[0]["event_type"] == "comment"

    def test_each_refusal_names_its_row_and_reason(self, appended: list) -> None:
        rows = [
            SheetRow(2, "", "принято", ""),
            SheetRow(3, "fnd_unknown", "принято", ""),
            SheetRow(4, F1, "может быть", ""),
            SheetRow(5, F1, "принято", ""),
            SheetRow(6, F2, "не решено", ""),
            SheetRow(7, F3, "принято", ""),
            SheetRow(8, "", "", "также найдено — не строка решения"),
        ]
        findings = [_finding(F1), _finding(F2, "accepted"), _finding(F3, run="run_01M5B0000000000000000000R2")]
        assert _run(rows, findings) == [
            (2, "refused", None, "no_finding_uid"),
            (3, "refused", None, "unknown_finding"),
            (4, "refused", F1, "unknown_decision"),
            (5, "refused", F1, "duplicate_finding"),
            (6, "refused", F2, "not_importable"),
            (7, "refused", F3, "finding_not_in_run"),
        ]
        assert appended == []

    def test_the_display_number_is_never_a_key(self, appended: list) -> None:
        assert _run([SheetRow(2, "1", "принято", "")], [_finding(F1)]) == [(2, "refused", None, "unknown_finding")]

    def test_the_report_survives_its_replay(self) -> None:
        report = decision_import.DecisionImport(RUN, (
            decision_import.ImportedRow(2, "recorded", F1), decision_import.ImportedRow(3, "refused", reason="no_finding_uid"),
        ))
        assert decision_import._replayed(decision_import._stored(report)) == report
