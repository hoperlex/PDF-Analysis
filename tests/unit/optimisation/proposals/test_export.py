"""`W60-OPT-PROPOSALS-01` phase A: the proposals CSV bytes, container-free.

Every cell a spreadsheet would read as a formula is escaped; the file conventions are the
findings export's (BOM, CRLF, RFC 4180 quoting, empty for absent); an absent saving is an
empty cell, never ``0``; the header stands alone for a pass with no proposals.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from auditmanager.optimisation.proposals.export import (
    BOM,
    COLUMNS,
    escape_formula,
    render_proposals_csv,
)
from auditmanager.optimisation.proposals.repository import (
    OptimisationPassRecord,
    OptimisationProposalRecord,
    PositionSummary,
    ProposalDecisionRecord,
)

PASS = OptimisationPassRecord(
    optimisation_pass_id="opp_01M2545JSD15ETSNNV904XA001",
    project_uid="prj_01M2545JSD15ETSNNV904XA001",
    document_uid="doc_01M2545JSD15ETSNNV904XA001",
    version_uid="ver_01M2545JSD15ETSNNV904XA001",
    run_id="run_01M2545JSD15ETSNNV904XA001",
    text_layer_sha256="e" * 64,
    price_list_id="prl_01M2545JSD15ETSNNV904XA001",
    vendor_list_id="vnl_01M2545JSD15ETSNNV904XA001",
    vendor_list_source="global",
    extraction_algorithm="specification-text-v1",
    match_algorithm="price-match-v1",
    generator_version="cheaper-analog-v1",
    specification_row_count=3,
    matched_row_count=2,
    proposed_row_count=1,
    proposal_count=1,
    started_by_user_uid="usr_01M2545JSD15ETSNNV904XA001",
    started_at=datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc),
    decision_counts={"pending": 1, "accept": 0, "reject": 0, "revise": 0},
    version_ordinal=1,
)


def _proposal(**overrides: object) -> OptimisationProposalRecord:
    values: dict[str, object] = {
        "optimisation_proposal_id": "opr_01M2545JSD15ETSNNV904XA001",
        "optimisation_pass_id": PASS.optimisation_pass_id,
        "ordinal": 1,
        "proposal_type": "cheaper_analog",
        "spec_row_key": "sr-" + "0" * 32,
        "page_number": 2,
        "sheet_label": "10",
        "line_start": 4,
        "line_end": 5,
        "table_ordinal": 1,
        "row_position": "1",
        "row_text": "Дверь противопожарная ДПМ-01/60",
        "matched_basis": "mark",
        "analog_basis": "name_similarity",
        "name_similarity": Decimal("0.6666"),
        "proposed_vendor": "Кнауф Гипс",
        "unit": "шт",
        "quantity": Decimal("4"),
        "quantity_text": "4",
        "current_unit_price": Decimal("25000"),
        "proposed_unit_price": Decimal("19500.50"),
        "currency": "RUB",
        "saving": Decimal("21998.00"),
        "rationale": "Более дешёвый аналог, «в кавычках», с запятой",
        "matched_position": PositionSummary(
            "prp_01M2545JSD15ETSNNV904XA001", 3, None, "Дверь противопожарная", "ДПМ-01/60", "Другой"
        ),
        "proposed_position": PositionSummary(
            "prp_01M2545JSD15ETSNNV904XA002", 4, "К-1", "Дверь металлическая", None, "Кнауф Гипс"
        ),
        "current_decision": None,
    }
    values.update(overrides)
    return OptimisationProposalRecord(**values)  # type: ignore[arg-type]


def _parsed(content: bytes) -> list[dict[str, str]]:
    assert content.startswith(BOM)
    assert content.count(BOM) == 1
    text = content[len(BOM):].decode("utf-8")
    assert text.endswith("\r\n")
    return list(csv.DictReader(io.StringIO(text, newline="")))


@pytest.mark.parametrize(
    ("value", "escaped"),
    [
        ("=HYPERLINK(\"http://x\")", "'=HYPERLINK(\"http://x\")"),
        ("+1+1", "'+1+1"),
        ("-2+3", "'-2+3"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\tTAB", "'\tTAB"),
        ("\rCR", "'\rCR"),
        ("  =1+1", "'  =1+1"),
        ("Дверь", "Дверь"),
        ("1 250", "1 250"),
        ("", ""),
    ],
)
def test_formula_triggers_are_escaped(value: str, escaped: str) -> None:
    assert escape_formula(value) == escaped


def test_a_row_carries_every_column_with_exact_numbers_and_escaped_text() -> None:
    hostile = _proposal(row_text="=cmd|' /C calc'!A0", proposed_vendor="@vendor")
    rows = _parsed(render_proposals_csv(PASS, (hostile,)))
    assert len(rows) == 1
    (row,) = rows
    assert tuple(row) == COLUMNS
    assert row["row_text"] == "'=cmd|' /C calc'!A0"
    assert row["proposed_vendor"] == "'@vendor"
    assert (row["current_unit_price"], row["proposed_unit_price"], row["saving"]) == (
        "25000", "19500.5", "21998",
    )
    assert row["name_similarity"] == "0.6666"
    assert row["current_decision"] == "pending" and row["decided_at"] == ""
    assert row["rationale"] == "Более дешёвый аналог, «в кавычках», с запятой"
    assert row["matched_mark"] == "ДПМ-01/60" and row["matched_code"] == ""


def test_an_absent_saving_is_an_empty_cell_never_zero() -> None:
    rows = _parsed(render_proposals_csv(PASS, (_proposal(quantity=None, quantity_text="-", saving=None),)))
    assert rows[0]["saving"] == "" and rows[0]["quantity"] == ""
    assert rows[0]["quantity_text"] == "'-"


def test_the_current_decision_is_exported() -> None:
    decision = ProposalDecisionRecord(
        "opd_01M2545JSD15ETSNNV904XA001",
        "opr_01M2545JSD15ETSNNV904XA001",
        2,
        "revise",
        "-уточнить марку",
        "usr_01M2545JSD15ETSNNV904XA002",
        datetime(2026, 10, 20, 9, 30, tzinfo=timezone.utc),
    )
    rows = _parsed(render_proposals_csv(PASS, (_proposal(current_decision=decision),)))
    assert rows[0]["current_decision"] == "revise"
    assert rows[0]["decision_comment"] == "'-уточнить марку"
    assert rows[0]["decided_at"] == "2026-10-20T09:30:00Z"


def test_a_pass_without_proposals_is_the_header_alone_and_rendering_is_deterministic() -> None:
    empty = render_proposals_csv(PASS, ())
    assert empty == BOM + (",".join(COLUMNS) + "\r\n").encode("utf-8")
    one = render_proposals_csv(PASS, (_proposal(),))
    assert one == render_proposals_csv(PASS, (_proposal(),))


# -- `D-346` (contract 1.43.0): the percent of the price, in the CSV and in the workbook -----------------------------------


def test_the_percent_is_the_last_csv_column_so_no_column_before_it_moves() -> None:
    """`D-346`: the file is read by position by whoever scripts against it, so the new column takes the end."""
    assert COLUMNS[-1] == "saving_percent"
    # Every column that was there keeps its place: the percent is appended after the decision's four, not set beside `saving`.
    assert COLUMNS.index("saving") == 36 and COLUMNS[-5:-1] == (
        "current_decision", "decision_comment", "decided_by_user_uid", "decided_at",
    )
    assert len(COLUMNS) == 43


def test_a_row_states_the_server_percent_exactly_and_without_a_trailing_zero() -> None:
    # 25000 -> 19500.50 saves 21.998 %, which is 22 to the hundredth: the cell says `22`, not `22.00` and not a float.
    (row,) = _parsed(render_proposals_csv(PASS, (_proposal(),)))
    assert row["saving_percent"] == "22"
    (third,) = _parsed(render_proposals_csv(PASS, (_proposal(current_unit_price=Decimal("450"), proposed_unit_price=Decimal("300")),)))
    assert third["saving_percent"] == "33.33"


def test_the_percent_stands_where_the_saving_is_absent_and_is_empty_only_without_a_base() -> None:
    # The quantity is not a number: there is no saving, and there is still a price difference.
    (tape,) = _parsed(render_proposals_csv(PASS, (_proposal(quantity=None, quantity_text="-", saving=None),)))
    assert tape["saving"] == "" and tape["saving_percent"] == "22"
    # A zero current price has no base to be a share of: an empty cell, never `0`.
    (free,) = _parsed(render_proposals_csv(
        PASS, (_proposal(quantity=None, quantity_text="-", saving=None, current_unit_price=Decimal("0"), proposed_unit_price=Decimal("0")),),
    ))
    assert free["saving_percent"] == ""


def _workbook_rows(content: bytes) -> list[list[str]]:
    from auditmanager.exports.xlsx import proposals as workbook
    from auditmanager.exports.xlsx.reader import _findings_part, _rows, _shared_strings
    import zipfile

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        part, shared = _findings_part(archive, workbook.PROPOSALS_SHEET)
        found = [cells for _number, cells in _rows(archive, part, _shared_strings(archive, shared))]
    width = len(workbook.PROPOSAL_COLUMNS)
    return [[cells.get(column, "") for column in range(width)] for cells in found]


def test_the_workbook_has_the_percent_beside_the_saving_and_is_still_read_back_by_its_headers() -> None:
    from auditmanager.exports.xlsx import proposals as workbook
    from auditmanager.exports.xlsx.reader import read_decision_sheet

    columns = workbook.PROPOSAL_COLUMNS
    assert columns[columns.index("Экономия") + 1] == "Экономия, %"
    assert len(columns) == 16 and len(workbook._WIDTHS) == len(columns)
    content = workbook.render_proposals_xlsx((_proposal(), _proposal(quantity=None, quantity_text="-", saving=None)))
    header, with_amount, without_amount = _workbook_rows(content)
    assert header == list(columns)
    saving, percent = columns.index("Экономия"), columns.index("Экономия, %")
    assert (with_amount[saving], with_amount[percent]) == ("21998", "22")
    # No amount, and still the price difference.
    assert (without_amount[saving], without_amount[percent]) == ("", "22")
    # The way back finds its three columns by their headers, wherever the new one stands.
    read = read_decision_sheet(
        content, sheet=workbook.PROPOSALS_SHEET, id_column=workbook.ID_COLUMN,
        decision_column=workbook.DECISION_COLUMN, comment_column=workbook.COMMENT_COLUMN,
    )
    assert [row.key for row in read] == ["opr_01M2545JSD15ETSNNV904XA001"] * 2
    assert [row.decision for row in read] == ["не решено", "не решено"]
