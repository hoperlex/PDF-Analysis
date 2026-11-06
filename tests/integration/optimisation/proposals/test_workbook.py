"""`UI-B-15` (contract 1.35.0): the pass's proposals as a workbook, and the experts' decisions loaded back from it.

The first column of the sheet «Предложения» is the proposal's own identity, never the display number: a row is matched by
it, and only to a proposal of the pass the file is loaded into. A row that changes the decision in force appends one
ordinary event authored by the importer (a withdrawal for «не решено»); every row that names an ID or a decision is
reported; one keyed command covers the file.
"""

from __future__ import annotations

import io
import zipfile
from typing import Any

import pytest

from auditmanager.exports import export_proposals_xlsx, import_proposal_decisions
from auditmanager.exports.xlsx import proposals as workbook
from auditmanager.exports.xlsx.writer import _Cells, _row, _sheet
from auditmanager.optimisation.proposals.public import (
    decide_optimisation_proposal,
    list_optimisation_proposals,
    list_proposal_decisions,
    start_optimisation_pass,
)
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import HOSTILE_VENDOR, World, published_reader


@pytest.fixture
def started(unit, cast, ready: World) -> dict[str, Any]:
    record = unit(
        start_optimisation_pass,
        project_uid=ready.project,
        document_uid=ready.document,
        idempotency_key="pass-1",
        actor_uid=cast.expert,
        reader=published_reader(ready),
    ).optimisation_pass
    page = unit(
        list_optimisation_proposals,
        optimisation_pass_id=record.optimisation_pass_id,
        actor_roles=frozenset({"expert"}),
    )
    return {"pass": record.optimisation_pass_id, "proposals": [item.optimisation_proposal_id for item in page.items]}


def _decide(unit, cast, proposal: str, verdict: str, key: str, comment: str | None = None):
    return unit(
        decide_optimisation_proposal,
        proposal_id=proposal,
        verdict=verdict,
        comment=comment,
        idempotency_key=key,
        actor_uid=cast.expert,
    )


def _workbook(rows: list[tuple[str, str, str]], *, sheet: str = workbook.PROPOSALS_SHEET) -> bytes:
    """An edited workbook: our header, and for each row the identity, the decision and the comment cells."""
    cells = _Cells()
    columns = workbook.PROPOSAL_COLUMNS
    width = len(columns)
    body = [_row(1, columns, 1, cells)]
    for index, (identity, decision, comment) in enumerate(rows, start=2):
        values: list[str | int] = [""] * width
        values[0] = identity
        values[columns.index(workbook.DECISION_COLUMN)] = decision
        values[columns.index(workbook.COMMENT_COLUMN)] = comment
        body.append(_row(index, tuple(values), 0, cells))
    parts = workbook._single_sheet_parts(_sheet(body, workbook._WIDTHS))
    parts["xl/workbook.xml"] = parts["xl/workbook.xml"].replace(
        workbook.PROPOSALS_SHEET.encode(), sheet.encode()
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name in workbook._PARTS:
            archive.writestr(name, parts[name])
    return output.getvalue()


def _import(unit, cast, started, content: bytes, key: str, **extra: Any):
    arguments: dict[str, Any] = {
        "optimisation_pass_id": started["pass"],
        "content": content,
        "idempotency_key": key,
        "actor_uid": cast.expert,
    }
    arguments.update(extra)
    return unit(import_proposal_decisions, **arguments)


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


def _history(unit, proposal: str):
    return unit(list_proposal_decisions, optimisation_proposal_id=proposal, actor_roles=frozenset({"admin"}))


# -- the export ------------------------------------------------------------------------------------------------------


def test_the_export_names_the_proposal_first_says_the_decision_in_force_and_keeps_text_as_text(
    unit, cast, started
) -> None:
    door, window, anchor, tape = started["proposals"]
    _decide(unit, cast, door, "accept", "w-1", "берём")
    _decide(unit, cast, window, "accept", "w-2")
    _decide(unit, cast, window, "revoke", "w-3", "снимаю")
    content = unit(export_proposals_xlsx, optimisation_pass_id=started["pass"], actor_roles=frozenset({"admin"}))
    assert content == unit(export_proposals_xlsx, optimisation_pass_id=started["pass"], actor_roles=frozenset({"viewer"}))
    rows = workbook_rows(content)
    assert rows[0] == list(workbook.PROPOSAL_COLUMNS) and rows[0][0] == "ID предложения"
    assert [row[0] for row in rows[1:]] == started["proposals"]
    decision, comment = (workbook.PROPOSAL_COLUMNS.index(name) for name in (workbook.DECISION_COLUMN, workbook.COMMENT_COLUMN))
    by_id = {row[0]: row for row in rows[1:]}
    assert (by_id[door][decision], by_id[door][comment]) == ("принято", "берём")
    # A withdrawn decision is no decision in force: the cells are those of an undecided proposal.
    assert (by_id[window][decision], by_id[window][comment]) == ("не решено", "")
    assert (by_id[tape][decision], by_id[tape][comment]) == ("не решено", "")
    assert by_id[anchor][workbook.PROPOSAL_COLUMNS.index("Поставщик аналога")] == HOSTILE_VENDOR
    # Text, never a formula: the cell is an inline string whatever it begins with.
    sheet = zipfile.ZipFile(io.BytesIO(content)).read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "HYPERLINK" in sheet and sheet.count('t="inlineStr"') > 0
    assert "<f>" not in sheet
    # The tape's quantity is not a number: its text, and no saving -- never a zero.
    assert by_id[tape][workbook.PROPOSAL_COLUMNS.index("Количество")] == "-"
    assert by_id[tape][workbook.PROPOSAL_COLUMNS.index("Экономия")] == ""


def workbook_rows(content: bytes) -> list[list[str]]:
    """The sheet's rows as the reader sees them: the header, then one list per row."""
    from auditmanager.exports.xlsx.reader import _findings_part, _rows, _shared_strings

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        part, shared = _findings_part(archive, workbook.PROPOSALS_SHEET)
        found = [(number, cells) for number, cells in _rows(archive, part, _shared_strings(archive, shared))]
    width = len(workbook.PROPOSAL_COLUMNS)
    return [[cells.get(column, "") for column in range(width)] for _number, cells in found]


def test_reading_the_export_needs_a_role_and_an_existing_pass(unit, started) -> None:
    _refused(ErrorCode.PERMISSION_DENIED, unit, export_proposals_xlsx, optimisation_pass_id=started["pass"],
             actor_roles=frozenset())
    _refused(ErrorCode.NOT_FOUND, unit, export_proposals_xlsx,
             optimisation_pass_id="opp_01M2545JSD15ETSNNV904XA001", actor_roles=frozenset({"admin"}))


# -- the way back ----------------------------------------------------------------------------------------------------


def test_the_edited_workbook_appends_one_event_per_changed_row_authored_by_the_importer(unit, cast, started) -> None:
    door, window, anchor, tape = started["proposals"]
    _decide(unit, cast, tape, "accept", "i-0", "ранее")
    report = _import(unit, cast, started, _workbook([
        (door, "принято", "подходит"),
        (window, "Отклонено", "хуже по теплотехнике"),
        (anchor, "на доработку", "уточнить поставщика"),
        (tape, "", ""),
    ]), "import-1")
    assert [(row.row, row.outcome, row.optimisation_proposal_id) for row in report.rows] == [
        (2, "recorded", door), (3, "recorded", window), (4, "recorded", anchor), (5, "unchanged", tape),
    ]
    assert (report.count("recorded"), report.count("unchanged"), report.count("refused")) == (3, 1, 0)
    for proposal, verdict, comment in ((door, "accept", "подходит"), (window, "reject", "хуже по теплотехнике"),
                                       (anchor, "revise", "уточнить поставщика")):
        (event,) = _history(unit, proposal)
        assert (event.verdict, event.comment, event.actor_user_uid) == (verdict, comment, cast.expert)
    assert [event.verdict for event in _history(unit, tape)] == ["accept"]  # a blank cell keeps the decision in force


def test_not_decided_withdraws_a_decision_in_force_and_is_nothing_over_an_undecided_proposal(unit, cast, started) -> None:
    door, window, *_ = started["proposals"]
    _decide(unit, cast, door, "reject", "n-1", "дороже монтаж")
    report = _import(unit, cast, started, _workbook([(door, "не решено", "ошибся"), (window, "не решено", "")]), "import-n")
    assert [(row.outcome, row.reason) for row in report.rows] == [("recorded", None), ("unchanged", None)]
    assert [(event.verdict, event.comment) for event in _history(unit, door)] == [
        ("reject", "дороже монтаж"), ("revoke", "ошибся"),
    ]
    assert _history(unit, window) == ()


def test_the_same_decision_is_unchanged_and_a_new_comment_on_it_is_a_new_event(unit, cast, started) -> None:
    door = started["proposals"][0]
    _decide(unit, cast, door, "accept", "c-1", "берём")
    same = _import(unit, cast, started, _workbook([(door, "принято", "берём"), (door, "принято", "")]), "import-c1")
    assert [(row.outcome, row.reason) for row in same.rows] == [("unchanged", None), ("refused", "duplicate_proposal")]
    assert len(_history(unit, door)) == 1
    renewed = _import(unit, cast, started, _workbook([(door, "принято", "берём, но проверить марку")]), "import-c2")
    assert renewed.rows[0].outcome == "recorded"
    assert [(event.verdict, event.comment) for event in _history(unit, door)] == [
        ("accept", "берём"), ("accept", "берём, но проверить марку"),
    ]


def test_every_refusal_names_its_reason_and_echoes_an_identity_only_for_a_proposal_of_the_pass(unit, cast, started) -> None:
    door, window, anchor, _tape = started["proposals"]
    strange = "opr_01M2545JSD15ETSNNV904XA001"
    report = _import(unit, cast, started, _workbook([
        ("", "принято", ""),
        ("", "", ""),  # neither an ID nor a decision: not a row about a decision
        (strange, "принято", ""),
        (door, "почти принято", ""),
        (window, "на доработку", ""),
        (anchor, "принято", "я" * 2001),
        (door, "принято", ""),
    ]), "import-r")
    assert [(row.row, row.outcome, row.optimisation_proposal_id, row.reason) for row in report.rows] == [
        (2, "refused", None, "no_proposal_id"),
        (4, "refused", None, "unknown_proposal"),
        (5, "refused", door, "unknown_decision"),
        (6, "refused", window, "comment_required"),
        (7, "refused", anchor, "comment_too_long"),
        (8, "refused", door, "duplicate_proposal"),  # a refused row has still met its ID: the later row is the repeat
    ]
    assert all(_history(unit, proposal) == () for proposal in (door, window, anchor))


def test_a_key_replays_its_report_and_another_file_under_it_is_refused(unit, cast, started) -> None:
    door = started["proposals"][0]
    content = _workbook([(door, "принято", "")])
    first = _import(unit, cast, started, content, "import-k")
    replay = _import(unit, cast, started, content, "import-k")
    assert replay == first and len(_history(unit, door)) == 1
    reused = _refused(ErrorCode.IDEMPOTENCY_KEY_REUSE, _import, unit, cast, started,
                      _workbook([(door, "отклонено", "")]), "import-k")
    assert reused.detail_fields["command_type"] == "import_optimisation_proposal_decisions"
    assert len(_history(unit, door)) == 1


def test_only_an_expert_loads_decisions_and_a_foreign_file_is_refused_whole(unit, cast, started) -> None:
    door = started["proposals"][0]
    content = _workbook([(door, "принято", "")])
    for actor in (cast.admin, cast.nobody):
        denied = _refused(ErrorCode.PERMISSION_DENIED, _import, unit, cast, started, content, "import-x", actor_uid=actor)
        assert denied.detail_fields["required_capability"] == "role:expert"
    _refused(ErrorCode.NOT_FOUND, _import, unit, cast, started, content, "import-y",
             optimisation_pass_id="opp_01M2545JSD15ETSNNV904XA001")
    foreign = _refused(ErrorCode.VALIDATION_FAILED, _import, unit, cast, started,
                       _workbook([(door, "принято", "")], sheet="Замечания"), "import-z")
    assert (foreign.detail_fields["field"], foreign.detail_fields["constraint"]) == ("file", "not_our_export")
    unreadable = _refused(ErrorCode.VALIDATION_FAILED, _import, unit, cast, started, b"not a workbook", "import-u")
    assert unreadable.detail_fields["constraint"] == "unreadable"
    assert _history(unit, door) == ()
