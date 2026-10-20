"""CSV: the encoding, then the delimiter, then the records. Standard library only.

**Encoding.** A UTF-8 byte-order mark means UTF-8 (``utf-8-sig``, as Excel's «CSV UTF-8»
writes it); a UTF-16 mark means UTF-16 (Excel's «Unicode text»); otherwise strict UTF-8, and
when that fails strict Windows-1251 (a Russian Excel's plain «CSV»). A file that is none of
these, or holds a NUL character, is refused.

**Delimiter.** ``;``, then tab, then ``,``: the first one under which the first
:data:`~.limits.HEADER_SCAN_ROWS` non-blank records contain a header row
(:func:`.headers.match_header`) is the file's delimiter. A Russian Excel writes ``;``
because ``,`` is its decimal separator; a value with a decimal comma in a ``,``-delimited
file is quoted and the standard reader honours the quotes.

**Row numbers** are 1-based record numbers -- the row a spreadsheet program shows when it
opens the file.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Final

from .headers import match_header
from .limits import HEADER_SCAN_ROWS, MAX_COLUMNS
from .refusals import CONSTRAINT_ENCODING, CONSTRAINT_HEADER, CONSTRAINT_UNREADABLE, refuse
from .values import Cell, cell_text

__all__ = ["CsvSource", "open_csv"]

DELIMITERS: Final[tuple[str, ...]] = (";", "\t", ",")
_UTF8_BOM: Final[bytes] = b"\xef\xbb\xbf"
_UTF16_BOMS: Final[tuple[bytes, ...]] = (b"\xff\xfe", b"\xfe\xff")


@dataclass(frozen=True, slots=True)
class CsvSource:
    """A decoded CSV and the delimiter its header was found under."""

    text: str
    encoding: str
    delimiter: str

    def rows(self) -> Iterator[tuple[int, list[Cell | None]]]:
        yield from _records(self.text, self.delimiter)


def _decode(data: bytes) -> tuple[str, str]:
    try:
        if data.startswith(_UTF8_BOM):
            return data[len(_UTF8_BOM):].decode("utf-8"), "utf-8-sig"
        if data.startswith(_UTF16_BOMS):
            return data.decode("utf-16"), "utf-16"
    except UnicodeDecodeError:
        raise refuse(
            CONSTRAINT_ENCODING,
            "The file declares a Unicode encoding its bytes do not follow.",
        ) from None
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1251"), "cp1251"
    except UnicodeDecodeError:
        raise refuse(
            CONSTRAINT_ENCODING,
            "The file is neither UTF-8 nor Windows-1251 text; save it as CSV UTF-8 and "
            "upload it again.",
        ) from None


def _records(text: str, delimiter: str) -> Iterator[tuple[int, list[Cell | None]]]:
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        for number, record in enumerate(reader, start=1):
            yield number, list(record[:MAX_COLUMNS])
    except csv.Error:
        raise refuse(
            CONSTRAINT_UNREADABLE,
            "The CSV file cannot be read: a record is malformed or a field is too long.",
        ) from None


def _finds_header(text: str, delimiter: str) -> bool:
    scanned = 0
    for _number, cells in _records(text, delimiter):
        if not any(cell_text(cell) for cell in cells):
            continue
        if match_header(cells) is not None:
            return True
        scanned += 1
        if scanned >= HEADER_SCAN_ROWS:
            return False
    return False


def open_csv(data: bytes) -> CsvSource:
    """Decode the bytes and pick the delimiter; refuse what cannot be a price-list CSV."""
    text, encoding = _decode(data)
    if "\x00" in text:
        raise refuse(
            CONSTRAINT_UNREADABLE,
            "The file holds binary content; upload a CSV or an XLSX price list.",
        )
    for delimiter in DELIMITERS:
        if _finds_header(text, delimiter):
            return CsvSource(text=text, encoding=encoding, delimiter=delimiter)
    raise refuse(
        CONSTRAINT_HEADER,
        f"No header row with the name, unit and price columns was found in the first "
        f"{HEADER_SCAN_ROWS} non-blank rows.",
    )
