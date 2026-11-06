"""Reading the «Замечания» sheet of our own run workbook back (`R-151d`).

The expert edits the exported workbook in a spreadsheet program and loads it back. Only our
export is read: the workbook must hold a sheet named «Замечания» whose header row names the
columns «ID замечания», «Решение эксперта» and «Комментарий» (:data:`.writer.FINDING_COLUMNS`);
anything else is a foreign file and is refused whole. The columns are found by their header,
as the original pdf-proverka finds «ID» and «Решение эксперта», so a column the expert added or
moved does not matter.

A spreadsheet program rewrites what it saves: inline strings become shared strings, a cell may
become a number, parts may be renamed. So the sheet is found by its name through the workbook's
relationships and never by a member name, both string forms are read, and a number cell is its
stored text. Formulas are never evaluated.

Bounds and hostile input: at most :data:`MAX_UPLOAD_BYTES` of file, :data:`_MAX_MEMBERS` members,
:data:`_MAX_PART_BYTES` per decompressed part whatever the archive's headers claim, and
:data:`MAX_ROWS` rows; a part declaring a document type or an entity is refused before it is
parsed, so no entity is ever expanded or fetched.
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from typing import IO, Final
from xml.etree import ElementTree

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "COMMENT_COLUMN",
    "DECISION_COLUMN",
    "FINDINGS_SHEET",
    "ID_COLUMN",
    "MAX_ROWS",
    "MAX_UPLOAD_BYTES",
    "DecisionSheetRow",
    "SheetRow",
    "read_decision_sheet",
    "read_findings_sheet",
]

FINDINGS_SHEET: Final[str] = "Замечания"
ID_COLUMN: Final[str] = "ID замечания"
DECISION_COLUMN: Final[str] = "Решение эксперта"
COMMENT_COLUMN: Final[str] = "Комментарий"
MAX_UPLOAD_BYTES: Final[int] = 10 * 1024 * 1024
MAX_ROWS: Final[int] = 20_000
_MAX_MEMBERS: Final[int] = 1_000
_MAX_PART_BYTES: Final[int] = 64 * 1024 * 1024
_FORBIDDEN_MARKUP: Final[tuple[bytes, ...]] = (b"<!DOCTYPE", b"<!ENTITY")
_CELL_REFERENCE: Final[re.Pattern[str]] = re.compile(r"([A-Z]{1,3})\d+$")


@dataclass(frozen=True, slots=True)
class SheetRow:
    """One data row of «Замечания»: its sheet row number and the three cells, stripped."""

    row: int
    finding_uid: str
    decision: str
    comment: str


@dataclass(frozen=True, slots=True)
class DecisionSheetRow:
    """One data row of any of our decision sheets: its sheet row number, the identity cell, the decision and the comment."""

    row: int
    key: str
    decision: str
    comment: str


def _refuse(constraint: str, message: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, message=message, field="file", constraint=constraint)


def _unreadable(detail: str) -> DomainError:
    return _refuse("unreadable", f"The file cannot be read as an XLSX workbook: {detail}.")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class _BoundedPart(io.RawIOBase):
    """A decompressing read that counts bytes and refuses DTDs, whatever the headers say."""

    def __init__(self, stream: IO[bytes]) -> None:
        self._stream = stream
        self._read = 0
        self._tail = b""

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray | memoryview) -> int:  # type: ignore[override]
        chunk = self._stream.read(len(buffer))
        self._read += len(chunk)
        if self._read > _MAX_PART_BYTES:
            raise _unreadable("a part is larger than the accepted decompressed size")
        window = self._tail + chunk
        if any(marker in window for marker in _FORBIDDEN_MARKUP):
            raise _unreadable("it declares a document type or an entity")
        self._tail = window[-16:]
        buffer[: len(chunk)] = chunk
        return len(chunk)


def _open_part(archive: zipfile.ZipFile, name: str) -> io.BufferedReader:
    try:
        return io.BufferedReader(_BoundedPart(archive.open(name)))
    except KeyError:
        raise _unreadable("a part the workbook names is missing") from None
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError):
        raise _unreadable("a part is damaged or encrypted") from None


def _parse(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    with _open_part(archive, name) as handle:
        try:
            return ElementTree.fromstring(handle.read())
        except ElementTree.ParseError:
            raise _unreadable("a part is not well-formed XML") from None
        except (zipfile.BadZipFile, OSError, EOFError):
            raise _unreadable("a part is damaged") from None


def _relationships(archive: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    """``Id -> (Type, absolute member name)`` of one part's internal relationships."""
    directory, base = posixpath.split(part)
    rels = posixpath.join(directory, "_rels", f"{base}.rels")
    if rels not in archive.NameToInfo:
        return {}
    found: dict[str, tuple[str, str]] = {}
    for element in _parse(archive, rels):
        identifier, kind, target = element.get("Id"), element.get("Type"), element.get("Target")
        if _local(element.tag) != "Relationship" or element.get("TargetMode") == "External":
            continue
        if identifier and kind and target:
            found[identifier] = (kind, target.lstrip("/") if target.startswith("/")
                                 else posixpath.normpath(posixpath.join(directory, target)))
    return found


def _text(item: ElementTree.Element) -> str:
    """The text of an ``<si>`` or ``<is>``: its ``<t>`` and each run's ``<t>``, not phonetic runs."""
    parts: list[str] = []
    for child in item:
        if _local(child.tag) == "t":
            parts.append(child.text or "")
        elif _local(child.tag) == "r":
            parts.extend(run.text or "" for run in child if _local(run.tag) == "t")
    return "".join(parts)


def _shared_strings(archive: zipfile.ZipFile, part: str | None) -> tuple[str, ...]:
    if part is None:
        return ()
    return tuple(_text(item) for item in _parse(archive, part) if _local(item.tag) == "si")


def _column(reference: str | None, fallback: int) -> int:
    match = _CELL_REFERENCE.match(reference or "")
    if match is None:
        return fallback
    index = 0
    for letter in match.group(1):
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def _value(cell: ElementTree.Element, shared: tuple[str, ...]) -> str:
    kind = cell.get("t") or "n"
    stored: str | None = None
    for child in cell:
        if _local(child.tag) == "is" and kind == "inlineStr":
            return _text(child)
        if _local(child.tag) == "v":
            stored = child.text
    if stored is None:
        return ""
    if kind == "s":
        try:
            return shared[int(stored.strip())]
        except (ValueError, IndexError):
            raise _unreadable("a cell names a shared string that does not exist") from None
    return stored


def _rows(archive: zipfile.ZipFile, part: str, shared: tuple[str, ...]) -> Iterator[tuple[int, dict[int, str]]]:
    with _open_part(archive, part) as handle:
        try:
            previous = 0
            for _event, element in ElementTree.iterparse(handle, events=("end",)):
                if _local(element.tag) != "row":
                    continue
                raw = element.get("r")
                number = int(raw) if raw and raw.isdigit() else previous + 1
                if number <= previous:
                    raise _unreadable("its rows are out of order")
                if number > MAX_ROWS + 1:
                    raise _refuse("too_many_rows", f"The sheet has more than {MAX_ROWS} rows.")
                previous = number
                cells: dict[int, str] = {}
                position = 0
                for cell in element:
                    if _local(cell.tag) == "c":
                        position = _column(cell.get("r"), position)
                        cells[position] = _value(cell, shared).strip()
                        position += 1
                element.clear()
                yield number, cells
        except ElementTree.ParseError:
            raise _unreadable("the sheet is not well-formed XML") from None
        except (zipfile.BadZipFile, OSError, EOFError):
            raise _unreadable("the sheet is damaged") from None


def _findings_part(archive: zipfile.ZipFile, sheet_name: str = FINDINGS_SHEET) -> tuple[str, str | None]:
    """The named sheet's part (the «Замечания» sheet by default) and the shared-strings part, located by relationships."""
    workbook = next((target for kind, target in _relationships(archive, "").values()
                     if kind.endswith("/officeDocument")), None)
    if workbook is None or workbook not in archive.NameToInfo:
        raise _unreadable("it holds no workbook")
    sheets = next((child for child in _parse(archive, workbook) if _local(child.tag) == "sheets"), None)
    sheet = None if sheets is None else next(
        (child for child in sheets if _local(child.tag) == "sheet" and child.get("name") == sheet_name), None
    )
    if sheet is None:
        raise _refuse("not_our_export", f"The workbook has no «{sheet_name}» sheet of our export.")
    relation = next((value for key, value in sheet.attrib.items() if _local(key) == "id" and key != "id"), None)
    rels = _relationships(archive, workbook)
    if relation is None or relation not in rels or rels[relation][1] not in archive.NameToInfo:
        raise _unreadable("the sheet's part is missing")
    shared = next((target for kind, target in rels.values() if kind.endswith("/sharedStrings")), None)
    if shared is not None and shared not in archive.NameToInfo:
        raise _unreadable("the shared strings part is missing")
    return rels[relation][1], shared


def read_decision_sheet(
    data: bytes, *, sheet: str, id_column: str, decision_column: str, comment_column: str
) -> tuple[DecisionSheetRow, ...]:
    """Every data row of the named sheet of one of our exports, or a refusal of the whole file.

    The three columns are found by their header, so a column the expert added or moved does not matter; a workbook with no
    such sheet or without those headers is a foreign file (``not_our_export``).
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise _refuse("too_large", "The file is larger than 10 MiB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError):
        raise _unreadable("it is not a ZIP package") from None
    with archive:
        if len(archive.infolist()) > _MAX_MEMBERS:
            raise _unreadable("the package has too many members")
        part, shared_part = _findings_part(archive, sheet)
        rows = _rows(archive, part, _shared_strings(archive, shared_part))
        where: dict[str, int] = {}
        for index, name in sorted(next(rows, (0, {}))[1].items()):
            where.setdefault(name, index)  # a repeated header: the leftmost column is the one read
        if not all(column in where for column in (id_column, decision_column, comment_column)):
            raise _refuse(
                "not_our_export",
                f"The «{sheet}» sheet does not name the columns «{id_column}», «{decision_column}» "
                f"and «{comment_column}» of our export.",
            )
        return tuple(
            DecisionSheetRow(
                row=number,
                key=cells.get(where[id_column], ""),
                decision=cells.get(where[decision_column], ""),
                comment=cells.get(where[comment_column], ""),
            )
            for number, cells in rows
        )


def read_findings_sheet(data: bytes) -> tuple[SheetRow, ...]:
    """Every data row of the «Замечания» sheet of our run export, or a refusal of the whole file."""
    return tuple(
        SheetRow(row=item.row, finding_uid=item.key, decision=item.decision, comment=item.comment)
        for item in read_decision_sheet(
            data, sheet=FINDINGS_SHEET, id_column=ID_COLUMN, decision_column=DECISION_COLUMN, comment_column=COMMENT_COLUMN
        )
    )
