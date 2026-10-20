"""Reading a price list (CSV, or the first sheet of an XLSX) into positions and a report.

:func:`parse_price_list` is pure: the same bytes and the same ``default_currency`` give the
same positions and the same report, byte for byte, on every run. It uses the standard library
only (``csv``, ``zipfile``, ``xml.etree``, ``decimal``) -- no new dependency.

The format is recognised by the bytes, never by the file name: a ZIP package is an XLSX, an
OLE2 compound file (Excel 97-2003 ``.xls``) is refused with ``price_list_format``, anything
else is read as CSV text.

**What becomes a position.** After the header row (:mod:`.headers`), every non-blank row is a
data row. A data row is accepted when it has a name, a unit, a unit price (:mod:`.values`) and
a currency, every value within its length bound; otherwise it is **skipped with one reason**,
the first that applies in the order ``name_missing``, ``unit_missing``, ``price_*``,
``currency_*``, ``value_too_long``. Nothing is guessed: a row whose price is not a plain
number is skipped, never repaired.

**Currency** of a row: its currency cell, else the currency the price column's header names
(``Цена, руб.``), else the uploader's declared ``default_currency``; with none of the three
the row is skipped (``currency_missing``). The report counts rows by source.

**Section** of a row: its section cell when that is one of the fifteen section codes in Latin, a Cyrillic
abbreviation or a catalogue name; an unrecognised value leaves the position without a section
and is a **warning** (``section_unrecognised``), not a skip -- the price itself is sound.

**Whole-file refusals** (:mod:`.refusals`): empty, over 10 MiB, an unsupported format, an
unreadable package or text, no header row, an ambiguous required column, more than 20 000
data rows, or not one accepted row.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Final

from .csv_source import open_csv
from .headers import FIELDS, HeaderMatch, match_header
from .limits import (
    HEADER_SCAN_ROWS,
    MAX_BYTES,
    MAX_CODE_LENGTH,
    MAX_DATA_ROWS,
    MAX_LISTED_ROWS,
    MAX_MARK_LENGTH,
    MAX_NAME_LENGTH,
    MAX_UNIT_LENGTH,
    MAX_VENDOR_LENGTH,
)
from .refusals import (
    CONSTRAINT_EMPTY,
    CONSTRAINT_FORMAT,
    CONSTRAINT_HEADER,
    CONSTRAINT_NO_POSITIONS,
    CONSTRAINT_ROWS,
    CONSTRAINT_SIZE,
    FILE_CONSTRAINTS,
    refuse,
)
from .values import (
    Cell,
    canonical_price,
    cell_text,
    currency_in_header,
    read_currency,
    read_price,
    read_section,
)
from .xlsx_source import open_xlsx

__all__ = [
    "CURRENCY_SOURCES",
    "FIELD_ORDER",
    "FILE_CONSTRAINTS",
    "FORMAT_CSV",
    "FORMAT_XLSX",
    "MEDIA_TYPES",
    "REPORT_VERSION",
    "SKIP_REASONS",
    "WARNING_REASONS",
    "ParseOutcome",
    "ParsedPosition",
    "parse_price_list",
]

FORMAT_CSV: Final[str] = "csv"
FORMAT_XLSX: Final[str] = "xlsx"
#: The media type recorded for each format (migration ``0026`` restates the pairs).
MEDIA_TYPES: Final[Mapping[str, str]] = {
    FORMAT_CSV: "text/csv",
    FORMAT_XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
#: Bumped whenever a rule here changes what a file parses to.
REPORT_VERSION: Final[int] = 1

#: Why a data row is skipped, in the order the checks run.
SKIP_REASONS: Final[tuple[str, ...]] = (
    "name_missing",
    "unit_missing",
    "price_missing",
    "price_not_a_number",
    "price_not_positive",
    "price_precision",
    "price_too_large",
    "currency_missing",
    "currency_unrecognised",
    "value_too_long",
)
WARNING_REASONS: Final[tuple[str, ...]] = ("section_unrecognised",)

CURRENCY_SOURCES: Final[tuple[str, ...]] = ("column", "price_header", "default")
#: The position fields in the order a report lists its mapped columns.
FIELD_ORDER: Final[tuple[str, ...]] = FIELDS

_ZIP_MAGIC: Final[bytes] = b"PK\x03\x04"
_OLE2_MAGIC: Final[bytes] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_LENGTHS: Final[Mapping[str, int]] = {
    "name": MAX_NAME_LENGTH,
    "code": MAX_CODE_LENGTH,
    "mark": MAX_MARK_LENGTH,
    "unit": MAX_UNIT_LENGTH,
    "vendor": MAX_VENDOR_LENGTH,
}


@dataclass(frozen=True, slots=True)
class ParsedPosition:
    """One accepted data row. ``row_number`` is the source row, never an identity."""

    row_number: int
    name: str
    unit: str
    unit_price: Decimal
    currency: str
    code: str | None
    mark: str | None
    vendor: str | None
    section_code: str | None


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    """The format, the accepted positions and the deterministic report."""

    source_format: str
    media_type: str
    positions: tuple[ParsedPosition, ...]
    report: Mapping[str, Any]
    data_row_count: int
    skipped_row_count: int

    @property
    def accepted_row_count(self) -> int:
        return len(self.positions)


def _detect_format(data: bytes) -> str:
    if data.startswith(_ZIP_MAGIC):
        return FORMAT_XLSX
    if data.startswith(_OLE2_MAGIC):
        raise refuse(
            CONSTRAINT_FORMAT,
            "Excel 97-2003 workbooks (XLS) are not read; save the price list as XLSX or CSV "
            "and upload it again.",
        )
    return FORMAT_CSV


def _cell(cells: list[Cell | None], header: HeaderMatch, field: str) -> Cell | None:
    column = header.columns.get(field)
    if column is None or column.index >= len(cells):
        return None
    return cells[column.index]


@dataclass(slots=True)
class _Tally:
    """What the walk counted; the lists stop at :data:`~.limits.MAX_LISTED_ROWS`."""

    data_rows: int = 0
    preamble_rows: int = 0
    blank_rows: int = 0
    skipped: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    skipped_by_reason: Counter[str] = field(default_factory=Counter)
    warnings_by_reason: Counter[str] = field(default_factory=Counter)
    currency_sources: Counter[str] = field(default_factory=Counter)

    def skip(self, row: int, reason: str) -> None:
        self.skipped_by_reason[reason] += 1
        if len(self.skipped) < MAX_LISTED_ROWS:
            self.skipped.append({"row": row, "reason": reason})

    def warn(self, row: int, reason: str) -> None:
        self.warnings_by_reason[reason] += 1
        if len(self.warnings) < MAX_LISTED_ROWS:
            self.warnings.append({"row": row, "reason": reason})


def _read_row(
    number: int,
    cells: list[Cell | None],
    header: HeaderMatch,
    *,
    header_currency: str | None,
    default_currency: str | None,
    section_names: Mapping[str, str],
    tally: _Tally,
) -> ParsedPosition | None:
    texts = {name: cell_text(_cell(cells, header, name)) for name in FIELDS if name != "unit_price"}
    if not texts["name"]:
        tally.skip(number, "name_missing")
        return None
    if not texts["unit"]:
        tally.skip(number, "unit_missing")
        return None
    price = read_price(_cell(cells, header, "unit_price"))
    if price.value is None:
        assert price.reason is not None
        tally.skip(number, price.reason)
        return None

    currency, recognised = read_currency(_cell(cells, header, "currency"))
    if not recognised:
        tally.skip(number, "currency_unrecognised")
        return None
    source = "column"
    if currency is None and header_currency is not None:
        currency, source = header_currency, "price_header"
    if currency is None and default_currency is not None:
        currency, source = default_currency, "default"
    if currency is None:
        tally.skip(number, "currency_missing")
        return None

    if any(len(texts[name]) > limit for name, limit in _LENGTHS.items()):
        tally.skip(number, "value_too_long")
        return None

    section, section_known = read_section(_cell(cells, header, "section"), section_names)
    if not section_known:
        tally.warn(number, "section_unrecognised")

    tally.currency_sources[source] += 1
    return ParsedPosition(
        row_number=number,
        name=texts["name"],
        unit=texts["unit"],
        unit_price=price.value,
        currency=currency,
        code=texts["code"] or None,
        mark=texts["mark"] or None,
        vendor=texts["vendor"] or None,
        section_code=section,
    )


def _header_report(header: HeaderMatch, header_currency: str | None) -> dict[str, Any]:
    return {
        "columns": {
            name: {"column": column.index + 1, "header": column.header}
            for name, column in sorted(header.columns.items())
        },
        "ambiguous_columns": {
            name: list(headers) for name, headers in sorted(header.ambiguous.items())
        },
        "ignored_columns": list(header.ignored[:50]),
        "price_header_currency": header_currency,
    }


def _walk(
    rows: Iterable[tuple[int, list[Cell | None]]],
    *,
    default_currency: str | None,
    section_names: Mapping[str, str],
) -> tuple[HeaderMatch, int, str | None, list[ParsedPosition], _Tally]:
    tally = _Tally()
    header: HeaderMatch | None = None
    header_row = 0
    header_currency: str | None = None
    scanned = 0
    positions: list[ParsedPosition] = []
    for number, cells in rows:
        if not any(cell_text(cell) for cell in cells):
            if header is not None:
                tally.blank_rows += 1
            continue
        if header is None:
            matched = match_header(cells)
            if matched is not None:
                header, header_row = matched, number
                header_currency = currency_in_header(matched.columns["unit_price"].header)
                continue
            scanned += 1
            tally.preamble_rows += 1
            if scanned >= HEADER_SCAN_ROWS:
                break
            continue
        tally.data_rows += 1
        if tally.data_rows > MAX_DATA_ROWS:
            raise refuse(
                CONSTRAINT_ROWS,
                f"The price list has more than {MAX_DATA_ROWS} data rows; split it and "
                "upload the parts as separate revisions.",
            )
        position = _read_row(
            number,
            cells,
            header,
            header_currency=header_currency,
            default_currency=default_currency,
            section_names=section_names,
            tally=tally,
        )
        if position is not None:
            positions.append(position)
    if header is None:
        raise refuse(
            CONSTRAINT_HEADER,
            f"No header row with the name, unit and price columns was found in the first "
            f"{HEADER_SCAN_ROWS} non-blank rows.",
        )
    return header, header_row, header_currency, positions, tally


def parse_price_list(
    data: bytes,
    *,
    default_currency: str | None,
    section_names: Mapping[str, str],
) -> ParseOutcome:
    """Parse one uploaded price list, or refuse the whole file with ``validation_failed``.

    ``default_currency`` is an already validated ISO 4217 code or ``None``;
    ``section_names`` maps each of the fifteen section codes to its catalogue name.
    """
    if not data:
        raise refuse(CONSTRAINT_EMPTY, "The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise refuse(
            CONSTRAINT_SIZE,
            f"The price list is larger than {MAX_BYTES // (1024 * 1024)} MiB.",
        )
    source_format = _detect_format(data)
    source_report: dict[str, Any]
    if source_format == FORMAT_XLSX:
        xlsx = open_xlsx(data)
        rows = xlsx.rows()
        source_report = {"sheet": xlsx.sheet_name, "encoding": None, "delimiter": None}
    else:
        csv_source = open_csv(data)
        rows = csv_source.rows()
        source_report = {
            "sheet": None,
            "encoding": csv_source.encoding,
            "delimiter": csv_source.delimiter,
        }

    header, header_row, header_currency, positions, tally = _walk(
        rows, default_currency=default_currency, section_names=section_names
    )
    skipped_count = sum(tally.skipped_by_reason.values())
    if not positions:
        reasons = ", ".join(
            f"{reason} {tally.skipped_by_reason[reason]}"
            for reason in SKIP_REASONS
            if tally.skipped_by_reason[reason]
        )
        raise refuse(
            CONSTRAINT_NO_POSITIONS,
            f"No row could be read as a price position: {tally.data_rows} data row(s)"
            + (f", skipped: {reasons}." if reasons else "."),
        )

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "format": source_format,
        **source_report,
        "header_row": header_row,
        **_header_report(header, header_currency),
        "default_currency": default_currency,
        "preamble_rows": tally.preamble_rows,
        "blank_rows": tally.blank_rows,
        "data_rows": tally.data_rows,
        "accepted_rows": len(positions),
        "skipped_rows": skipped_count,
        "skipped_by_reason": {
            reason: tally.skipped_by_reason[reason]
            for reason in SKIP_REASONS
            if tally.skipped_by_reason[reason]
        },
        "skipped": list(tally.skipped),
        "skipped_listed_in_full": skipped_count <= MAX_LISTED_ROWS,
        "warnings_by_reason": {
            reason: tally.warnings_by_reason[reason]
            for reason in WARNING_REASONS
            if tally.warnings_by_reason[reason]
        },
        "warnings": list(tally.warnings),
        "currency_sources": {
            source: tally.currency_sources[source]
            for source in CURRENCY_SOURCES
            if tally.currency_sources[source]
        },
    }
    return ParseOutcome(
        source_format=source_format,
        media_type=MEDIA_TYPES[source_format],
        positions=tuple(positions),
        report=report,
        data_row_count=tally.data_rows,
        skipped_row_count=skipped_count,
    )


def price_text(position: ParsedPosition) -> str:
    """The exact unit price as the stored plain decimal text."""
    return canonical_price(position.unit_price)
