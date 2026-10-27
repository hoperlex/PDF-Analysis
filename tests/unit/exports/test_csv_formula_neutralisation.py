"""`SMALL-HARDENING-02` / `R-146ax`: the run CSV does not hand a spreadsheet a formula.

Pure checks on the deterministic serializer: no database, no storage, no spreadsheet
application. ``evidence_quote`` is a verbatim quotation from a client's document and the
two finding texts are model output, so a cell may begin with a character that Excel reads as
the start of a formula (`EXPOSURE-REVIEW-02.md` `F-11`). The owner's ruling: such a cell
gets one leading apostrophe and every other byte stays.

The expected values are written out as literals and the trigger set is spelled out here, **not**
imported from the module under test: an assertion phrased against the module's own constant
survives the constant being emptied (the lesson of ``BOM_BYTES`` in
``tests/integration/exports/test_csv_contract.py``).
"""

from __future__ import annotations

import csv
import io
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from auditmanager.exports.query import ExportRow
from auditmanager.exports.serializer import COLUMNS, render_csv, row_values

#: The six first characters of `R-146ax`, one per case so a mutation names the class it broke.
TRIGGERS = {
    "equals": "=",
    "plus": "+",
    "minus": "-",
    "at": "@",
    "tab": "\t",
    "carriage_return": "\r",
}

#: The text columns a third party or a model can write into, and every other text column.
FREE_TEXT_COLUMNS = ("finding_text", "recommendation_text", "evidence_quote", "latest_comment")
NUMBER_COLUMNS = ("evidence_page",)
DATETIME_COLUMNS = ("decision_recorded_at",)
TEXT_COLUMNS = tuple(
    column for column in COLUMNS if column not in NUMBER_COLUMNS + DATETIME_COLUMNS
)

BOM = b"\xef\xbb\xbf"


def _row(**changes: object) -> ExportRow:
    base = ExportRow(
        project_uid="prj_1",
        document_uid="doc_1",
        version_uid="ver_1",
        run_id="run_1",
        run_state="published",
        provider_mode="recorded",
        finding_uid="fnd_1",
        finding_observation_id="fobs_1",
        category="internal_contradiction",
        finding_text="Степень огнестойкости",
        recommendation_text="Согласовать",
        evidence_page=2,
        evidence_quote="цитата",
        current_verdict="accepted",
        latest_comment="комментарий",
        latest_decision_id="dec_1",
        decision_recorded_at=datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc),
        evidence_ordinal=0,
        severity="critical",
        severity_proposed="economic",
    )
    return replace(base, **changes)


def _parse(content: bytes) -> list[dict[str, str]]:
    assert content[:3] == BOM
    parsed = list(csv.reader(io.StringIO(content[3:].decode("utf-8"), newline="")))
    return [dict(zip(parsed[0], row, strict=True)) for row in parsed[1:]]


@pytest.mark.parametrize("trigger", TRIGGERS.values(), ids=TRIGGERS.keys())
@pytest.mark.parametrize("column", FREE_TEXT_COLUMNS)
def test_a_free_text_cell_that_starts_with_a_trigger_gets_one_leading_apostrophe(
    column: str, trigger: str
) -> None:
    value = f"{trigger}HYPERLINK(1)"
    cells = dict(zip(COLUMNS, row_values(_row(**{column: value}))))
    assert cells[column] == "'" + value
    # ... and through the writer, parsed as a conforming reader would (CR is quoted by it).
    assert _parse(render_csv((_row(**{column: value}),)))[0][column] == "'" + value


@pytest.mark.parametrize("column", TEXT_COLUMNS)
def test_every_text_column_is_neutralised_not_only_the_four_that_carry_free_text(
    column: str,
) -> None:
    """A column list kept by hand would lose the next column added; the rule is per cell."""
    cells = dict(zip(COLUMNS, row_values(_row(**{column: "=1+1"}))))
    assert cells[column] == "'=1+1"
    for other in COLUMNS:
        if other != column:
            assert cells[other] == dict(zip(COLUMNS, row_values(_row())))[other]


def test_the_neutralised_bytes_of_one_row_are_exactly_these() -> None:
    """The whole file, once, for a trigger in each class: quoting is unchanged around it."""
    row = _row(
        finding_text="=SUM(A1:A2)",
        recommendation_text="+1 выход",
        evidence_quote='@"x",y',
        latest_comment="\tотступ",
        severity="-",
    )
    header = ",".join(COLUMNS) + "\r\n"
    line = (
        "prj_1,doc_1,ver_1,run_1,published,recorded,fnd_1,fobs_1,internal_contradiction,"
        "'=SUM(A1:A2),'+1 выход,2,\"'@\"\"x\"\",y\",accepted,'\tотступ,dec_1,"
        "2026-10-27T09:30:00Z,'-,economic\r\n"
    )
    assert render_csv((row,)) == BOM + (header + line).encode("utf-8")


def test_a_cell_that_starts_with_a_carriage_return_is_quoted_and_neutralised() -> None:
    content = render_csv((_row(evidence_quote="\rx"),))
    assert b"\"'\rx\"" in content
    assert _parse(content)[0]["evidence_quote"] == "'\rx"


@pytest.mark.parametrize(
    "value",
    [
        "",  # the empty cell stays empty: no lone apostrophe
        "Степень огнестойкости",
        "a=b",
        "1+1",
        "x-",
        "e-mail@example.com",
        " =1+1",  # the ruling names the first character; a leading space is not one
        "\n=1",  # a line feed is not one of the six
        "'=1",  # already starts with an apostrophe: not doubled
        '"=1"',
        "5",
        ".5",
        "№ 5",
    ],
)
def test_a_cell_that_does_not_start_with_a_trigger_keeps_its_bytes(value: str) -> None:
    cells = dict(zip(COLUMNS, row_values(_row(evidence_quote=value))))
    assert cells["evidence_quote"] == value


def test_a_row_with_no_trigger_is_byte_for_byte_what_the_serializer_always_wrote() -> None:
    """The frozen `OD-11` bytes: BOM, CRLF, comma, minimal quoting, empty cells, `Z`."""
    row = _row(
        finding_text="Степень, огнестойкости",
        recommendation_text=None,
        latest_comment=None,
        latest_decision_id=None,
        decision_recorded_at=None,
        severity=None,
        severity_proposed=None,
    )
    expected = (
        ",".join(COLUMNS) + "\r\n"
        "prj_1,doc_1,ver_1,run_1,published,recorded,fnd_1,fobs_1,internal_contradiction,"
        '"Степень, огнестойкости",,2,цитата,accepted,,,,,\r\n'
    )
    assert render_csv((row,)) == BOM + expected.encode("utf-8")


def test_numbers_and_dates_are_not_text_cells() -> None:
    """The one integer column is a page number (``CHECK (page_number >= 1)``): digits, never
    prefixed. A negative one cannot come from the database; it is built by hand here to show
    the decision the module states, that a number stays a number."""
    assert dict(zip(COLUMNS, row_values(_row(evidence_page=7))))["evidence_page"] == "7"
    assert dict(zip(COLUMNS, row_values(_row(evidence_page=-5))))["evidence_page"] == "-5"
    cells = dict(zip(COLUMNS, row_values(_row())))
    assert cells["decision_recorded_at"] == "2026-10-27T09:30:00Z"


def test_a_negative_number_held_in_a_text_column_is_text_and_is_neutralised() -> None:
    cells = dict(zip(COLUMNS, row_values(_row(evidence_quote="-5", finding_text="-12,5 м"))))
    assert cells["evidence_quote"] == "'-5"
    assert cells["finding_text"] == "'-12,5 м"


def test_neutralising_twice_over_two_exports_changes_nothing() -> None:
    """Two exports of the same rows are byte-identical (`OD-11`); the rule keeps no state."""
    rows = (_row(evidence_quote="=1"), _row(evidence_quote="ok", evidence_ordinal=1))
    assert render_csv(rows) == render_csv(rows)
