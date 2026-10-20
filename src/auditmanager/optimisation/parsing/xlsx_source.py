"""XLSX: the first sheet's cells, read with ``zipfile`` and ``xml.etree`` only.

The workbook is located through the package relationships (``_rels/.rels`` names the office
document), the **first** ``<sheet>`` of the workbook through the workbook's relationships, and
the shared-string table the same way. Nothing is assumed from a member's name.

Cells: a shared string (``t="s"``), an inline string (``t="inlineStr"``, rich runs joined), a
formula's cached string (``t="str"``), a boolean or an error as its text, and a number (no
``t`` or ``t="n"``) as a :class:`.values.NumericCell` holding the stored value. Phonetic runs
(``rPh``) are not text. Formulas are never evaluated: a cell is its cached value.

Bounds and hostile input. The archive has at most :data:`~.limits.MAX_XLSX_MEMBERS` members;
every part is decompressed through a counting reader that refuses more than
:data:`~.limits.MAX_XLSX_PART_BYTES` (small parts: :data:`~.limits.MAX_XLSX_SMALL_PART_BYTES`)
whatever the archive's headers claim; any part holding a document type declaration or an
entity declaration is refused before it is parsed, so no entity is ever expanded or fetched.
The sheet and the shared strings are parsed incrementally and released as they are read.
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

from .limits import (
    MAX_COLUMNS,
    MAX_XLSX_MEMBERS,
    MAX_XLSX_PART_BYTES,
    MAX_XLSX_SMALL_PART_BYTES,
)
from .refusals import CONSTRAINT_UNREADABLE, CONSTRAINT_XLSX_PART_SIZE, refuse
from .values import Cell, NumericCell

__all__ = ["XlsxSource", "open_xlsx"]

_OFFICE_DOCUMENT: Final[str] = "/officeDocument"
_SHARED_STRINGS: Final[str] = "/sharedStrings"
_CELL_REFERENCE: Final[re.Pattern[str]] = re.compile(r"([A-Z]{1,3})(\d+)$")
_FORBIDDEN_MARKUP: Final[tuple[bytes, ...]] = (b"<!DOCTYPE", b"<!ENTITY")


def _unreadable(detail: str) -> Exception:
    return refuse(CONSTRAINT_UNREADABLE, f"The XLSX file cannot be read: {detail}.")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class _BoundedPart(io.RawIOBase):
    """A decompressing read that counts bytes and refuses DTDs, whatever the headers say."""

    def __init__(self, stream: IO[bytes], limit: int) -> None:
        self._stream = stream
        self._limit = limit
        self._read = 0
        self._tail = b""

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray | memoryview) -> int:  # type: ignore[override]
        chunk = self._stream.read(len(buffer))
        self._read += len(chunk)
        if self._read > self._limit:
            raise refuse(
                CONSTRAINT_XLSX_PART_SIZE,
                "A part of the XLSX file is larger than the accepted decompressed size.",
            )
        window = self._tail + chunk
        if any(marker in window for marker in _FORBIDDEN_MARKUP):
            raise _unreadable("it declares a document type or an entity")
        self._tail = window[-16:]
        buffer[: len(chunk)] = chunk
        return len(chunk)


@dataclass(frozen=True, slots=True)
class XlsxSource:
    """An opened workbook: the first sheet's name and part, and the shared strings."""

    archive: zipfile.ZipFile
    sheet_name: str
    sheet_part: str
    shared_strings: tuple[str, ...]

    def rows(self) -> Iterator[tuple[int, list[Cell | None]]]:
        yield from _sheet_rows(self.archive, self.sheet_part, self.shared_strings)


def _open_part(archive: zipfile.ZipFile, name: str, limit: int) -> io.BufferedReader:
    try:
        stream = archive.open(name)
    except KeyError:
        raise _unreadable("a part the workbook names is missing") from None
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError):
        raise _unreadable("a part is damaged or encrypted") from None
    return io.BufferedReader(_BoundedPart(stream, limit))


def _parse_small(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    with _open_part(archive, name, MAX_XLSX_SMALL_PART_BYTES) as handle:
        try:
            data = handle.read()
        except (zipfile.BadZipFile, OSError, EOFError):
            raise _unreadable("a part is damaged") from None
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError:
        raise _unreadable("a part is not well-formed XML") from None


def _relationships(archive: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    """``Id -> (Type, absolute member name)`` for one part's relationships."""
    directory, base = posixpath.split(part)
    rels_name = posixpath.join(directory, "_rels", f"{base}.rels")
    if rels_name not in archive.NameToInfo:
        return {}
    root = _parse_small(archive, rels_name)
    found: dict[str, tuple[str, str]] = {}
    for element in root:
        if _local(element.tag) != "Relationship":
            continue
        if element.get("TargetMode") == "External":
            continue
        identifier, kind, target = element.get("Id"), element.get("Type"), element.get("Target")
        if not identifier or not kind or not target:
            continue
        absolute = target.lstrip("/") if target.startswith("/") else posixpath.normpath(
            posixpath.join(directory, target)
        )
        found[identifier] = (kind, absolute)
    return found


def _read_shared_strings(archive: zipfile.ZipFile, part: str | None) -> tuple[str, ...]:
    if part is None:
        return ()
    strings: list[str] = []
    with _open_part(archive, part, MAX_XLSX_PART_BYTES) as handle:
        try:
            context = ElementTree.iterparse(handle, events=("start", "end"))
            root: ElementTree.Element | None = None
            for event, element in context:
                if event == "start":
                    if root is None:
                        root = element
                    continue
                if _local(element.tag) == "si":
                    strings.append(_string_item_text(element))
                    if root is not None:
                        root.clear()
        except ElementTree.ParseError:
            raise _unreadable("the shared strings are not well-formed XML") from None
        except (zipfile.BadZipFile, OSError, EOFError):
            raise _unreadable("the shared strings are damaged") from None
    return tuple(strings)


def _string_item_text(item: ElementTree.Element) -> str:
    """The text of an ``<si>`` or ``<is>``: its ``<t>`` and each run's ``<t>``, not ``rPh``."""
    parts: list[str] = []
    for child in item:
        name = _local(child.tag)
        if name == "t":
            parts.append(child.text or "")
        elif name == "r":
            for run_child in child:
                if _local(run_child.tag) == "t":
                    parts.append(run_child.text or "")
    return "".join(parts)


def _column_index(reference: str | None, fallback: int) -> int:
    if not reference:
        return fallback
    match = _CELL_REFERENCE.match(reference)
    if match is None:
        return fallback
    index = 0
    for letter in match.group(1):
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def _cell_value(cell: ElementTree.Element, shared: tuple[str, ...]) -> Cell | None:
    kind = cell.get("t") or "n"
    value_text: str | None = None
    inline: ElementTree.Element | None = None
    for child in cell:
        name = _local(child.tag)
        if name == "v":
            value_text = child.text
        elif name == "is":
            inline = child
    if kind == "inlineStr":
        return None if inline is None else _string_item_text(inline)
    if value_text is None:
        return None
    if kind == "s":
        try:
            return shared[int(value_text.strip())]
        except (ValueError, IndexError):
            raise _unreadable("a cell names a shared string that does not exist") from None
    if kind == "n":
        return NumericCell(value_text)
    if kind == "b":
        return "TRUE" if value_text.strip() == "1" else "FALSE"
    return value_text  # "str" (a formula's cached text), "e" (an error), "d" (an ISO date)


def _sheet_rows(
    archive: zipfile.ZipFile, part: str, shared: tuple[str, ...]
) -> Iterator[tuple[int, list[Cell | None]]]:
    with _open_part(archive, part, MAX_XLSX_PART_BYTES) as handle:
        try:
            context = ElementTree.iterparse(handle, events=("start", "end"))
            sheet_data: ElementTree.Element | None = None
            previous_row = 0
            for event, element in context:
                name = _local(element.tag)
                if event == "start":
                    if name == "sheetData":
                        sheet_data = element
                    continue
                if name != "row":
                    continue
                raw_number = element.get("r")
                number = int(raw_number) if raw_number and raw_number.isdigit() else previous_row + 1
                if number <= previous_row:
                    raise _unreadable("its rows are out of order")
                previous_row = number
                cells: dict[int, Cell | None] = {}
                position = 0
                for cell in element:
                    if _local(cell.tag) != "c":
                        continue
                    index = _column_index(cell.get("r"), position)
                    position = index + 1
                    if index < MAX_COLUMNS:
                        cells[index] = _cell_value(cell, shared)
                width = max(cells) + 1 if cells else 0
                yield number, [cells.get(index) for index in range(width)]
                if sheet_data is not None:
                    sheet_data.clear()
        except ElementTree.ParseError:
            raise _unreadable("the sheet is not well-formed XML") from None
        except (zipfile.BadZipFile, OSError, EOFError):
            raise _unreadable("the sheet is damaged") from None


def open_xlsx(data: bytes) -> XlsxSource:
    """Open the workbook and locate its first sheet; refuse what is not a readable XLSX."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError):
        raise _unreadable("it is not a valid ZIP package") from None
    if len(archive.infolist()) > MAX_XLSX_MEMBERS:
        raise _unreadable("the package has too many members")
    package = _relationships(archive, "")
    workbook = next(
        (target for kind, target in package.values() if kind.endswith(_OFFICE_DOCUMENT)),
        None,
    )
    if workbook is None or workbook not in archive.NameToInfo:
        raise _unreadable("it holds no workbook")
    root = _parse_small(archive, workbook)
    sheets = next((child for child in root if _local(child.tag) == "sheets"), None)
    first = None if sheets is None else next(
        (child for child in sheets if _local(child.tag) == "sheet"), None
    )
    if first is None:
        raise _unreadable("the workbook has no sheet")
    relation = next(
        (value for key, value in first.attrib.items() if _local(key) == "id" and key != "id"),
        None,
    )
    workbook_rels = _relationships(archive, workbook)
    if relation is None or relation not in workbook_rels:
        raise _unreadable("the first sheet's part is not named")
    sheet_part = workbook_rels[relation][1]
    if sheet_part not in archive.NameToInfo:
        raise _unreadable("the first sheet's part is missing")
    shared_part = next(
        (target for kind, target in workbook_rels.values() if kind.endswith(_SHARED_STRINGS)),
        None,
    )
    if shared_part is not None and shared_part not in archive.NameToInfo:
        raise _unreadable("the shared strings part is missing")
    return XlsxSource(
        archive=archive,
        sheet_name=(first.get("name") or "")[:200],
        sheet_part=sheet_part,
        shared_strings=_read_shared_strings(archive, shared_part),
    )
