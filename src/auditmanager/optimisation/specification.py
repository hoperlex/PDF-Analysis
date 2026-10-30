"""Specification rows read deterministically from a version's saved text layer (`W60-OPT-MATCH-01`).

The input is the run's verified ``prepared.text_layer``: one string per page, the lines
pdfplumber produced joined by ``\\n``. **A line carries no column separators** -- the cells
of a table row are joined by single spaces -- so this module never pretends to split cells
it cannot see. It finds a specification table by its header and then reads each row by
anchors that are unambiguous in plain text:

* **Header.** One to three consecutive lines that name the ``Наименование`` column and a
  quantity column (``Кол.``, ``Кол-во``, ``Количество``) and at least one more Form-7 column
  (``Поз.``, ``Тип, марка``/``Обозначение``, ``Код``, ``Завод-изготовитель``/``Поставщик``,
  ``Ед. изм.``, ``Масса``, ``Примечание``). Words glued together by the extractor
  (``Наименованиеитехническаяхарактеристика``) are found; a header split over lines
  (``Ед.`` / ``изм.``) is read as one. A header that names two quantity or two name columns
  (``Кол-во, м3`` beside ``Кол-во, м2``) is **ambiguous**: its table is reported and not read.
  A drawing stamp (``Изм. Кол.уч. Лист №док. Подпись Дата``) is never a header.
* **Row, with a unit column.** The one place where a recognised unit (:data:`UNITS`) is
  directly followed by a plain number or a dash: everything before it (after an optional
  leading position number) is the description, the number is the quantity, a following
  plain number is the unit mass when the header has a mass column, the rest is the note.
  Two such places in one line make the row ambiguous; it is skipped, never guessed.
* **Row, with the unit in the quantity header** (``Кол-во, шт.``) or with no unit at all.
  The rightmost plain number followed only by non-numeric words is the quantity. When the
  header has a position column, a row must start with a position number.
* **Multi-line names.** A line without an anchor after a row continues that row's
  description (at most :data:`MAX_CONTINUATION_LINES`); a short group heading
  (``Оборудование``, ``Материалы``) labels the rows after it instead.
* **Cells that wrap above their anchor line** (`SPEC-TABLE-RECORDING-01`). A cell centred
  vertically puts its first lines *above* the line that carries the position, unit and
  quantity. Those lines would continue the row above (or be reported as text before the first
  row), so a row whose own fragment cannot open a name -- it does not begin with a capitalised
  word (a lower-case word, a mark, an abbreviation, a size) -- takes the lines directly above
  it back, up to and including the nearest line that opens a name (a capitalised word), at
  most :data:`MAX_CONTINUATION_LINES` up. With no such line, or a fragment that can open a
  name, nothing moves: the lines stay where they were.
* **A table continued onto the next page without a repeated header.** The next page continues
  the previous page's table when that table ran to the end of its page (its last row, then
  nothing but the stamp), the page opens with nothing but column numbers, a group heading or a
  «Продолжение» line before its first row, that row parses under the same header, and either
  the position numbering goes on (the next integer) or the page says «Продолжение». Its rows
  belong to the same table (same ordinal, ``DetectedTable.continued_on``). Anything else is
  today's behaviour: the table ends with its page.
* **Manufacturer.** When the header names a manufacturer column and the row's own fragment
  holds a legal form (``ООО``, ``АО``…) after at least one word, the text from the legal form
  to the end of the fragment is the row's ``manufacturer`` -- the last cell of the description,
  by the Form-7 order. The type/mark and the code are *not* split: nothing in plain text
  separates them from the name or from each other.
* **End of a table.** A stamp line, ``Примечание``/a numbered note, the next header, more
  than :data:`MAX_UNANCHORED_RUN` lines in a row without an anchor, or the end of the page.

In a text layer the description holds the name **and** whatever type/mark, code and
manufacturer cells the row has, in the Form-7 order -- they cannot be told apart without
column geometry, which the saved text does not keep. The matcher works on that text
(``matching``). Quantities are exact decimals (decimal comma or point); a quantity that is
not a plain number, or whose digit grouping cannot be told from the next column, is kept
as text with its issue and never becomes a number.

Every row keeps its page, the sheet label when the stamp shows one, and its line span; its
``row_id`` is a digest of the version, page and span -- a provenance key, not a stored
identity. Every line inside a detected table that becomes neither a row nor part of one is
reported with a reason (:data:`SKIP_REASONS`). Pure and deterministic: same pages, same
answer. Nothing here reads a database or a file.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Final

__all__ = [
    "EXTRACTION_ALGORITHM",
    "FORM7_COLUMNS",
    "LEGAL_FORMS",
    "MAX_CONTINUATION_LINES",
    "MAX_LISTED_SKIPS",
    "MAX_LISTED_TABLES",
    "MAX_SPECIFICATION_ROWS",
    "MAX_UNANCHORED_RUN",
    "QUANTITY_AMBIGUOUS",
    "QUANTITY_ISSUES",
    "QUANTITY_NOT_NUMERIC",
    "SKIP_REASONS",
    "TABLE_HEADER_AMBIGUOUS",
    "TABLE_PARSED",
    "UNITS",
    "UNIT_SOURCE_COLUMN",
    "UNIT_SOURCE_HEADER",
    "DetectedTable",
    "SkippedLine",
    "SpecificationExtraction",
    "SpecificationRow",
    "canonical_unit",
    "extract_specification",
    "strip_legal_form",
]

EXTRACTION_ALGORITHM: Final[str] = "specification-text-v1"

#: The nine Form-7 columns, in the form's order.
FORM7_COLUMNS: Final[tuple[str, ...]] = (
    "position", "name", "type_mark", "code", "manufacturer", "unit", "quantity", "mass", "note",
)

#: Source canonical units retain ``п.м`` for fidelity. Pricing unit_key equates it with ``м``
#: at factor1 under the owner’s2026-10-30 decision; source quantities stay unchanged.
UNITS: Final[tuple[str, ...]] = ("шт", "м", "м2", "м3", "кг", "т", "компл", "п.м")

#: Bounds. A version with more rows than this is reported too large, never cut.
MAX_SPECIFICATION_ROWS: Final[int] = 10_000
MAX_CONTINUATION_LINES: Final[int] = 3
MAX_UNANCHORED_RUN: Final[int] = 6
MAX_LISTED_SKIPS: Final[int] = 200
MAX_LISTED_TABLES: Final[int] = 200
_MAX_HEADER_LINES: Final[int] = 3
_MAX_HEADER_TOKENS: Final[int] = 40
_MAX_HEADER_NUMBERS: Final[int] = 3
_MAX_EXCERPT: Final[int] = 200

TABLE_PARSED: Final[str] = "parsed"
TABLE_HEADER_AMBIGUOUS: Final[str] = "header_ambiguous"

UNIT_SOURCE_COLUMN: Final[str] = "column"
UNIT_SOURCE_HEADER: Final[str] = "header"

QUANTITY_NOT_NUMERIC: Final[str] = "not_numeric"
QUANTITY_AMBIGUOUS: Final[str] = "ambiguous"
QUANTITY_ISSUES: Final[tuple[str, ...]] = (QUANTITY_NOT_NUMERIC, QUANTITY_AMBIGUOUS)

#: Why a line inside a detected table became neither a row nor part of one.
SKIP_REASONS: Final[tuple[str, ...]] = (
    "table_header_ambiguous",  # the table's header names two quantity or name columns
    "text_before_first_row",  # an unanchored line before the table's first row
    "continuation_limit",  # a row already has MAX_CONTINUATION_LINES continuation lines
    "anchor_ambiguous",  # two unit-and-quantity places in one line
    "position_missing",  # the header has a position column; the line has no position
    "name_missing",  # an anchored line with no description text
    "column_numbering",  # the «1 2 3 4 5 6 7 8 9» row under a header
    "rows_over_limit",  # beyond MAX_SPECIFICATION_ROWS
)

# --- units ----------------------------------------------------------------------------

_UNIT_SPELLINGS: Final[Mapping[str, str]] = {
    **dict.fromkeys(("шт", "штук", "штука", "штуки"), "шт"),
    **dict.fromkeys(("м", "метр"), "м"),
    **dict.fromkeys(("м2", "квм", "мкв"), "м2"),
    **dict.fromkeys(("м3", "кубм", "мкуб"), "м3"),
    "кг": "кг",
    **dict.fromkeys(("т", "тн", "тонн", "тонна", "тонны"), "т"),
    **dict.fromkeys(("компл", "комплект", "к-т", "кт"), "компл"),
    **dict.fromkeys(("пм", "погм", "мп"), "п.м"),
}
#: First halves of a unit written as two tokens: ``кв. м``, ``куб. м``, ``п. м``, ``пог. м``.
_UNIT_PREFIXES: Final[frozenset[str]] = frozenset({"кв", "куб", "п", "пог"})


def _unit_compact(text: str) -> str:
    lowered = text.lower().replace("ё", "е").replace("²", "2").replace("³", "3")
    return re.sub(r"[\s.]", "", lowered)


def canonical_unit(text: str | None) -> str | None:
    """The canonical unit of a spelling (``м²``, ``кв. м``, ``шт.``), or ``None``."""
    if not text:
        return None
    return _UNIT_SPELLINGS.get(_unit_compact(text))


# --- reading tokens -------------------------------------------------------------------

_NUMBER: Final[re.Pattern[str]] = re.compile(r"\d{1,12}(?:[.,]\d{1,6})?")
_GROUP_HEAD: Final[re.Pattern[str]] = re.compile(r"\d{1,3}")
_GROUP_TAIL: Final[re.Pattern[str]] = re.compile(r"\d{3}(?:[.,]\d{1,6})?")
_POSITION: Final[re.Pattern[str]] = re.compile(r"\d{1,3}(?:\.\d{1,3}){0,3}\.?")
_DASHES: Final[frozenset[str]] = frozenset({"-", "–", "—"})
_NOTE_START: Final[re.Pattern[str]] = re.compile(r"\d{1,2}\.\s*\S")
_NUMBERING_MIN: Final[int] = 3


def _is_number(token: str) -> bool:
    return _NUMBER.fullmatch(token) is not None


def _decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(" ", "").replace(",", "."))
    except InvalidOperation:  # pragma: no cover - guarded by _NUMBER
        return None


def _unit_at(tokens: Sequence[str], index: int) -> tuple[str, int] | None:
    """A unit starting at ``tokens[index]``: (canonical, token count), or ``None``."""
    token = tokens[index]
    if index + 1 < len(tokens) and _unit_compact(token) in _UNIT_PREFIXES:
        joined = canonical_unit(token + tokens[index + 1])
        if joined is not None and _unit_compact(tokens[index + 1]) == "м":
            return joined, 2
    unit = canonical_unit(token)
    return None if unit is None else (unit, 1)


def _words(text: str) -> str:
    return re.sub(r"[\s ]+", " ", text).strip()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.lower().replace("ё", "е"))


#: Legal forms that open a manufacturer's name in a Form-7 cell (a closed list; ``OOO`` is the
#: Latin spelling of the same letters).
LEGAL_FORMS: Final[frozenset[str]] = frozenset({
    "ООО", "OOO", "ОАО", "ЗАО", "ПАО", "АО", "ИП", "НПО", "НПП", "НПК", "НПФ", "ТОО", "ОДО",
    "ЧП", "ФГУП", "ГУП", "МУП",
})
_QUOTES: Final[str] = "«»\"'„“”(),;:."


def _is_legal_form(token: str) -> bool:
    return token.strip(_QUOTES).upper() in LEGAL_FORMS


def strip_legal_form(text: str) -> str:
    """``text`` without a leading legal form (``ООО «Промет»`` -> ``«Промет»``)."""
    tokens = text.split()
    if len(tokens) >= 2 and _is_legal_form(tokens[0]):
        return " ".join(tokens[1:])
    return text


def _manufacturer_of(fragment: str, header: _Header) -> str | None:
    """The manufacturer cell of a row's own fragment: from a legal form to the fragment's end.

    Only when the header names a manufacturer column, only after at least one word (the name
    must remain), and only with something after the legal form. Otherwise ``None``.
    """
    if "manufacturer" not in header.columns:
        return None
    tokens = fragment.split()
    for index in range(1, len(tokens) - 1):
        if _is_legal_form(tokens[index]):
            return " ".join(tokens[index:])
    return None


# --- headers and stamps -----------------------------------------------------------------

_STAMP_TOKENS: Final[frozenset[str]] = frozenset({
    "подпись", "разработал", "проверил", "гип", "гап", "нконтр", "утвердил",
})
_STAMP_FRAGMENTS: Final[tuple[str, ...]] = ("кол.уч", "№док", "стадиялистлистов")


def _is_stamp(line: str) -> bool:
    compact = _compact(line)
    if any(fragment in compact for fragment in _STAMP_FRAGMENTS):
        return True
    return any(
        re.sub(r"[^\wа-я]", "", token.lower().replace("ё", "е")) in _STAMP_TOKENS
        for token in line.split()
    )


#: Header fragments of tables that are not specifications: «Наименование помещения» and
#: «№ пом.» name rooms (экспликация помещений, ведомость отделки), not products.
_NOT_SPECIFICATION: Final[tuple[str, ...]] = ("наименованиепомещени", "№пом")
_QUANTITY_HEADER: Final[re.Pattern[str]] = re.compile(r"количеств|кол-во|кол\.|кол,")
_FAMILY_PATTERNS: Final[Mapping[str, re.Pattern[str]]] = {
    "position": re.compile(r"поз\.|позиция|поз,|№п/п"),
    "name": re.compile(r"наименовани"),
    "type_mark": re.compile(r"тип|марка|обозначени"),
    "code": re.compile(r"код"),
    "manufacturer": re.compile(r"изготовител|поставщик|производител"),
    "mass": re.compile(r"масса"),
    "note": re.compile(r"примечани"),
}
#: Words a split header's later lines carry (``характеристика Обозначение … изм. 1 ед.,``).
_HEADER_TAIL_WORDS: Final[tuple[str, ...]] = (
    "характеристик", "обозначени", "изм", "изготовител", "документ", "опросн", "листа",
    "материал", "оборудовани", "издели", "продукци", "ед.", "кг", "поставщик", "масса",
    "примечани", "марка", "код", "наименовани", "кол",
)
_IMPLICIT_UNIT: Final[re.Pattern[str]] = re.compile(
    r"(?:количество|кол-во|кол\.)\s*,?\s*(шт|м2|м²|м3|м³|кг|компл|п\.\s?м|м|т)(?![а-яa-z0-9])"
)


@dataclass(frozen=True, slots=True)
class _Header:
    columns: frozenset[str]
    implicit_unit: str | None
    ambiguous: bool


def _read_header(lines: Sequence[str]) -> _Header | None:
    """The header these lines form together, or ``None`` when they are not one."""
    if any(_is_stamp(line) for line in lines):
        return None
    if any(len(line.split()) > _MAX_HEADER_TOKENS for line in lines):
        return None
    text = " ".join(lines)
    if sum(1 for token in text.split() if _is_number(token)) > _MAX_HEADER_NUMBERS:
        return None
    compact = _compact(text)
    names = len(_FAMILY_PATTERNS["name"].findall(compact))
    quantities = len(_QUANTITY_HEADER.findall(compact))
    if names == 0 or quantities == 0:
        return None
    if any(fragment in compact for fragment in _NOT_SPECIFICATION):
        return None  # a room schedule or finishing schedule names rooms, not products
    columns = {"name", "quantity"}
    for family, pattern in _FAMILY_PATTERNS.items():
        if family != "name" and pattern.search(compact):
            columns.add(family)
    tokens = {re.sub(r"[,;:]", "", token.lower()) for token in text.split()}
    if (
        "ед.изм" in compact
        or "единицаизм" in compact
        or ("ед." in tokens and any(token.startswith("изм") for token in tokens))
    ):
        columns.add("unit")
    if len(columns) < 3:
        return None
    implicit = None
    if "unit" not in columns:
        found = _IMPLICIT_UNIT.search(text.lower().replace("ё", "е"))
        implicit = None if found is None else canonical_unit(found.group(1))
    return _Header(frozenset(columns), implicit, names > 1 or quantities > 1)


def _is_header_tail(line: str) -> bool:
    """A later line of a split header: header words, no data (only ``1`` of ``1 ед.``)."""
    tokens = line.split()
    compact = _compact(line)
    return (
        len(tokens) <= 12
        and any(word in compact for word in _HEADER_TAIL_WORDS)
        and not any(_is_number(token) and token != "1" for token in tokens)
        and not _has_unit_anchor(tokens)
    )


def _has_unit_anchor(tokens: Sequence[str]) -> bool:
    return bool(_unit_anchors(tokens, start=0))


def _is_numbering(tokens: Sequence[str]) -> bool:
    if len(tokens) < _NUMBERING_MIN or not all(token.isdigit() for token in tokens):
        return False
    return [int(token) for token in tokens] == list(range(1, len(tokens) + 1))


_GROUP_WORDS: Final[tuple[str, ...]] = (
    "оборудование", "материалы", "изделия", "конструкции", "трубопроводы", "арматура",
    "кабельнаяпродукция", "прочие", "элементы",
)


def _is_group_heading(line: str) -> bool:
    tokens = line.split()
    compact = _compact(line).rstrip(":")
    return (
        0 < len(tokens) <= 6
        and not any(character.isdigit() for character in line)
        and any(compact.startswith(word) for word in _GROUP_WORDS)
    )


# --- sheet label ------------------------------------------------------------------------

_SHEET_ALONE: Final[re.Pattern[str]] = re.compile(r"\d{1,3}")
_SHEET_AFTER_STAGE: Final[re.Pattern[str]] = re.compile(r"(?:^|\s)[ПРСИ]\s+(\d{1,3})(?:\s+\d{1,3})?$")


def _sheet_label(lines: Sequence[str]) -> str | None:
    """The sheet number the stamp's «Стадия Лист Листов» cell shows, when it is legible."""
    for index, line in enumerate(lines):
        if "стадиялистлистов" not in _compact(line):
            continue
        for following in lines[index + 1 : index + 4]:
            text = following.strip()
            if _SHEET_ALONE.fullmatch(text):
                return text
            found = _SHEET_AFTER_STAGE.search(text)
            if found is not None:
                return found.group(1)
        return None
    return None


# --- records --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SpecificationRow:
    """One row of a specification table, as the text layer shows it.

    ``name`` is the description run: the name and, when the row fills them, the type/mark,
    code and manufacturer cells, in that order (a text layer does not separate them).
    ``unit`` is canonical (:data:`UNITS`) or ``None``; ``unit_text`` is what the page shows
    (or the quantity header's unit, ``unit_source == "header"``). ``quantity`` is set only
    when ``quantity_text`` is one plain number; otherwise ``quantity_issue`` says why not.
    Lines are 1-based within the page, ``line_start``..``line_end`` inclusive.
    ``manufacturer`` is the tail of the row's own fragment from a legal form on, when the
    header has a manufacturer column and the text shows one (module note); ``name`` still
    holds it, so nothing that reads ``name`` changes.
    """

    row_id: str
    page_number: int
    sheet_label: str | None
    line_start: int
    line_end: int
    table_ordinal: int
    group: str | None
    position: str | None
    name: str
    unit_text: str | None
    unit: str | None
    unit_source: str | None
    quantity_text: str | None
    quantity: Decimal | None
    quantity_issue: str | None
    mass_text: str | None
    note: str | None
    manufacturer: str | None = None


@dataclass(frozen=True, slots=True)
class SkippedLine:
    page_number: int
    line: int
    reason: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class DetectedTable:
    """One detected specification table: where its header is and what it names."""

    ordinal: int
    page_number: int
    header_line_start: int
    header_line_end: int
    columns: tuple[str, ...]
    implicit_unit: str | None
    status: str
    row_count: int
    #: Pages after ``page_number`` on which the table's rows continue without a repeated
    #: header (``row_count`` includes them). Empty for a table that ends with its page.
    continued_on: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class SpecificationExtraction:
    """Every row found, the tables, and what was skipped (listing capped, counts complete)."""

    algorithm: str
    version_uid: str
    page_count: int
    rows: tuple[SpecificationRow, ...]
    tables: tuple[DetectedTable, ...]
    table_count: int
    skipped: tuple[SkippedLine, ...]
    skipped_by_reason: Mapping[str, int]
    over_limit: bool

    @property
    def skipped_count(self) -> int:
        return sum(self.skipped_by_reason.values())


# --- extraction -------------------------------------------------------------------------


@dataclass(slots=True)
class _TableRecord:
    """A listed table while its rows are still being read (a continuation adds to it)."""

    ordinal: int
    page_number: int
    header_line_start: int
    header_line_end: int
    columns: tuple[str, ...]
    implicit_unit: str | None
    status: str
    row_count: int
    continued_on: list[int] = field(default_factory=list)

    def freeze(self) -> DetectedTable:
        return DetectedTable(
            ordinal=self.ordinal,
            page_number=self.page_number,
            header_line_start=self.header_line_start,
            header_line_end=self.header_line_end,
            columns=self.columns,
            implicit_unit=self.implicit_unit,
            status=self.status,
            row_count=self.row_count,
            continued_on=tuple(self.continued_on),
        )


@dataclass(frozen=True, slots=True)
class _OpenTable:
    """A table that ran to the end of its page: what a following page may continue."""

    header: _Header
    ordinal: int
    page: int
    last_position: str | None


class _Collector:
    def __init__(self, version_uid: str) -> None:
        self.version_uid = version_uid
        self.rows: list[SpecificationRow] = []
        self.tables: list[_TableRecord] = []
        self.records: dict[int, _TableRecord] = {}
        self.table_count = 0
        self.skipped: list[SkippedLine] = []
        self.by_reason: dict[str, int] = {}
        self.over_limit = False

    def skip(self, page: int, line: int, reason: str, text: str) -> None:
        self.by_reason[reason] = self.by_reason.get(reason, 0) + 1
        if len(self.skipped) < MAX_LISTED_SKIPS:
            self.skipped.append(SkippedLine(page, line, reason, _words(text)[:_MAX_EXCERPT]))

    def row_id(self, page: int, start: int, end: int) -> str:
        material = f"{EXTRACTION_ALGORITHM}|{self.version_uid}|{page}|{start}|{end}"
        return "sr-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


@dataclass(slots=True)
class _Draft:
    line_start: int
    line_end: int
    group: str | None
    position: str | None
    name_parts: list[str]
    unit_text: str | None
    unit: str | None
    unit_source: str | None
    quantity_text: str | None
    quantity: Decimal | None
    quantity_issue: str | None
    mass_text: str | None
    note: str | None
    manufacturer: str | None = None
    #: The line that carries the unit and quantity (``line_start`` is earlier when the name
    #: wraps above it).
    anchor_line: int = 0
    #: Line numbers (1-based) of the unanchored lines appended to ``name_parts[1:]``.
    continuation_lines: list[int] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _Anchor:
    unit_index: int
    unit_width: int
    unit: str


def _unit_anchors(tokens: Sequence[str], *, start: int) -> list[_Anchor]:
    anchors: list[_Anchor] = []
    index = start
    while index < len(tokens):
        found = _unit_at(tokens, index)
        if found is None:
            index += 1
            continue
        unit, width = found
        following = index + width
        if following < len(tokens) and (
            _is_number(tokens[following]) or tokens[following] in _DASHES
        ):
            anchors.append(_Anchor(index, width, unit))
        index += width  # «п. м 120»: the «м» belongs to the two-token unit
    return anchors


def _leading_position(tokens: Sequence[str]) -> str | None:
    if len(tokens) >= 2 and _POSITION.fullmatch(tokens[0]) and not _is_number(tokens[1]):
        return tokens[0].rstrip(".")
    return None


def _quantity_after_unit(
    tokens: Sequence[str], index: int, header: _Header
) -> tuple[str, Decimal | None, str | None, int]:
    """Quantity text, value, issue and the index after it, for a unit-column row."""
    first = tokens[index]
    if first in _DASHES:
        return first, None, QUANTITY_NOT_NUMERIC, index + 1
    following = tokens[index + 1] if index + 1 < len(tokens) else None
    if (
        following is not None
        and _GROUP_HEAD.fullmatch(first)
        and _GROUP_TAIL.fullmatch(following)
    ):
        if header.columns & {"mass", "note"}:
            return f"{first} {following}", None, QUANTITY_AMBIGUOUS, index + 2
        return f"{first} {following}", _decimal(first + following), None, index + 2
    return first, _decimal(first), None, index + 1


def _row_with_unit_column(
    tokens: Sequence[str], header: _Header
) -> tuple[_Draft | None, str | None]:
    position = _leading_position(tokens) if "position" in header.columns else None
    start = 1 if position is not None else 0
    anchors = [anchor for anchor in _unit_anchors(tokens, start=start) if anchor.unit_index > start]
    if not anchors:
        return None, None
    if len(anchors) > 1:
        return None, "anchor_ambiguous"
    anchor = anchors[0]
    name = " ".join(tokens[start : anchor.unit_index])
    if not any(character.isalpha() for character in name):
        return None, "name_missing"
    quantity_text, quantity, issue, after = _quantity_after_unit(
        tokens, anchor.unit_index + anchor.unit_width, header
    )
    mass_text = None
    if "mass" in header.columns and after < len(tokens) and _is_number(tokens[after]):
        mass_text = tokens[after]
        after += 1
    note = " ".join(tokens[after:]) or None
    unit_text = " ".join(tokens[anchor.unit_index : anchor.unit_index + anchor.unit_width])
    return _Draft(
        0, 0, None, position, [name], unit_text, anchor.unit, UNIT_SOURCE_COLUMN,
        quantity_text, quantity, issue, mass_text, note,
    ), None


def _row_with_implicit_unit(
    tokens: Sequence[str], header: _Header
) -> tuple[_Draft | None, str | None]:
    numbers = [index for index, token in enumerate(tokens) if _is_number(token)]
    if not numbers:
        return None, None
    last = numbers[-1]
    if any(character.isdigit() for token in tokens[last + 1 :] for character in token):
        return None, None  # «см. л. 17 и18»: digits after the number, so it is no quantity
    position = _leading_position(tokens) if "position" in header.columns else None
    start = 1 if position is not None else 0
    if last < start + 1:
        return None, None
    if "position" in header.columns and position is None:
        return None, "position_missing"
    issue: str | None = None
    quantity_index, mass_text = last, None
    if "mass" in header.columns:
        if last - 1 >= start + 1 and _is_number(tokens[last - 1]):
            quantity_index, mass_text = last - 1, tokens[last]
        else:
            issue = QUANTITY_AMBIGUOUS
    quantity_text = tokens[quantity_index]
    if issue is None and quantity_index - 1 >= start + 1:
        before = tokens[quantity_index - 1]
        if _GROUP_HEAD.fullmatch(before) and _GROUP_TAIL.fullmatch(quantity_text):
            issue = QUANTITY_AMBIGUOUS
    name = " ".join(tokens[start:quantity_index])
    if not any(character.isalpha() for character in name):
        return None, "name_missing"
    note = " ".join(tokens[last + 1 :]) or None
    quantity = None if issue is not None else _decimal(quantity_text)
    unit = header.implicit_unit
    return _Draft(
        0, 0, None, position, [name], unit, unit,
        UNIT_SOURCE_HEADER if unit is not None else None,
        quantity_text, quantity, issue, mass_text, note,
    ), None


def _parse_row(tokens: Sequence[str], header: _Header) -> tuple[_Draft | None, str | None]:
    if "unit" in header.columns:
        return _row_with_unit_column(tokens, header)
    return _row_with_implicit_unit(tokens, header)


def _find_header(lines: Sequence[str], index: int) -> tuple[_Header, int] | None:
    """A header starting at ``lines[index]`` and the index after it, or ``None``."""
    for width in range(1, _MAX_HEADER_LINES + 1):
        window = lines[index : index + width]
        if len(window) < width:
            return None
        if width > 1 and not all(_is_header_tail(line) for line in window):
            return None
        header = _read_header(window)
        if header is not None:
            if width > 1 and _read_header(window[1:]) is not None:
                return None  # a title line above the header: the header starts below it
            end = index + width
            while end < len(lines) and end - index < _MAX_HEADER_LINES and _is_header_tail(lines[end]):
                extended = _read_header(lines[index : end + 1])
                if extended is None:
                    break
                header, end = extended, end + 1
            return header, end
    return None


def _emit(collector: _Collector, page: int, sheet: str | None, ordinal: int, draft: _Draft) -> bool:
    if len(collector.rows) >= MAX_SPECIFICATION_ROWS:
        collector.over_limit = True
        collector.skip(page, draft.line_start, "rows_over_limit", " ".join(draft.name_parts))
        return False
    collector.rows.append(
        SpecificationRow(
            row_id=collector.row_id(page, draft.line_start, draft.line_end),
            page_number=page,
            sheet_label=sheet,
            line_start=draft.line_start,
            line_end=draft.line_end,
            table_ordinal=ordinal,
            group=draft.group,
            position=draft.position,
            name=_words(" ".join(draft.name_parts)),
            unit_text=draft.unit_text,
            unit=draft.unit,
            unit_source=draft.unit_source,
            quantity_text=draft.quantity_text,
            quantity=draft.quantity,
            quantity_issue=draft.quantity_issue,
            mass_text=draft.mass_text,
            note=draft.note,
            manufacturer=draft.manufacturer,
        )
    )
    return True


# --- cells that wrap above their anchor line ---------------------------------------------

#: Opening punctuation in front of a name's first word.
_OPENING: Final[str] = "«\"'(["
#: A name opens with a capitalised word: a capital and at least two lower-case letters.
_NAME_OPENER: Final[re.Pattern[str]] = re.compile(r"[А-ЯЁA-Z][а-яёa-z]{2,}")


def _starts_a_name(line: str) -> bool:
    return _NAME_OPENER.match(line.strip().lstrip(_OPENING)) is not None


def _cannot_start_name(fragment: str) -> bool:
    """A row fragment (the text before its unit) that no name cell opens with.

    A name cell opens with a capitalised word. A fragment that begins with anything else -- a
    lower-case word, a mark (``ДПМ-01/60``, ``HIT-HY``), an abbreviation, a size -- is the
    middle of a cell whose beginning is on an earlier line, or a name this rule cannot tell
    from one; the lines above must then show where a cell begins (:func:`_above_count`).
    """
    return bool(fragment.strip()) and not _starts_a_name(fragment)


def _above_count(texts: Sequence[str]) -> int:
    """How many trailing lines of an unanchored run open the next row's name cell (0: none).

    Scanning upward from the anchor line, the cell begins at the nearest line that opens a
    name, at most :data:`MAX_CONTINUATION_LINES` lines up. Without such a line there is no
    evidence where the cell begins, and nothing moves.
    """
    for count in range(1, min(len(texts), MAX_CONTINUATION_LINES) + 1):
        if _starts_a_name(texts[-count]):
            return count
    return 0


# --- a table continued onto the next page --------------------------------------------------

_END_PAGE: Final[str] = "page"
_END_STAMP: Final[str] = "stamp"
_END_OTHER: Final[str] = "other"
_MAX_LEAD_IN_LINES: Final[int] = 3
_INTEGER_POSITION: Final[re.Pattern[str]] = re.compile(r"\d{1,3}")


def _is_continuation_marker(line: str) -> bool:
    return len(line.split()) <= 12 and "продолжение" in _compact(line)


def _continues(carried: _OpenTable, position: str | None, marker: bool) -> bool:
    """Whether a page's first row continues the carried table: a marker, or the next integer."""
    if marker:
        return True
    last = carried.last_position
    if "position" not in carried.header.columns or last is None or position is None:
        return False
    if _INTEGER_POSITION.fullmatch(last) is None or _INTEGER_POSITION.fullmatch(position) is None:
        return False
    return int(position) == int(last) + 1


def _continuation_start(lines: Sequence[str], carried: _OpenTable) -> int | None:
    """The index of the first row of a page that continues ``carried``, or ``None``.

    Before that row the page may hold only column numbers, a group heading and a
    «Продолжение» line (at most :data:`_MAX_LEAD_IN_LINES` of the last two). Any other text, a
    stamp or a header of its own before the first row means this is not a plain continuation.
    """
    marker = False
    seen = 0
    for index, line in enumerate(lines):
        tokens = line.split()
        if not tokens:
            continue
        if _is_stamp(line):
            return None
        if _is_numbering(tokens):
            continue
        draft, _ = _parse_row(tokens, carried.header)
        if draft is not None:
            return index if _continues(carried, draft.position, marker) else None
        seen += 1
        if seen > _MAX_LEAD_IN_LINES:
            return None
        if _is_continuation_marker(line):
            marker = True
        elif not _is_group_heading(line):
            return None
    return None


def _read_table(
    collector: _Collector,
    page: int,
    sheet: str | None,
    lines: Sequence[str],
    header: _Header,
    header_start: int,
    body_start: int,
    *,
    resume: _OpenTable | None = None,
) -> tuple[int, _OpenTable | None]:
    """Read one table's rows; returns the index after the table and what the next page may continue.

    ``resume`` is the table of the previous page this page continues: the rows join it (same
    ordinal) and the header is the carried one.
    """
    if resume is None:
        collector.table_count += 1
        ordinal = collector.table_count
    else:
        ordinal = resume.ordinal
    rows_before = len(collector.rows)
    index = body_start
    current: _Draft | None = None
    group: str | None = None
    unanchored = 0
    run_len = 0  # trailing continuation lines of ``current`` that touch the line being read
    orphans: list[tuple[int, str]] = []  # unanchored lines before any row, not yet reported
    ended = _END_PAGE

    def flush() -> None:
        nonlocal current
        if current is not None:
            _emit(collector, page, sheet, ordinal, current)
            current = None

    def drain() -> None:
        for orphan_line, orphan_text in orphans:
            collector.skip(page, orphan_line, "text_before_first_row", orphan_text)
        orphans.clear()

    while index < len(lines):
        line = lines[index]
        number = index + 1
        tokens = line.split()
        if not tokens:
            index += 1
            continue
        if _is_stamp(line):
            ended = _END_STAMP
            break
        if _compact(line).startswith("примечани") or _find_header(lines, index) is not None:
            ended = _END_OTHER
            break
        if header.ambiguous:
            collector.skip(page, number, "table_header_ambiguous", line)
            index += 1
            unanchored += 1
            if unanchored > MAX_UNANCHORED_RUN:
                ended = _END_OTHER
                break
            continue
        if _is_numbering(tokens):
            drain()
            run_len = 0
            collector.skip(page, number, "column_numbering", line)
            index += 1
            continue
        draft, refusal = _parse_row(tokens, header)
        if draft is not None:
            fragment = draft.name_parts[0]
            draft.manufacturer = _manufacturer_of(fragment, header)
            draft.line_start = draft.line_end = draft.anchor_line = number
            if _cannot_start_name(fragment):
                if current is not None:
                    count = _above_count(current.name_parts[len(current.name_parts) - run_len :])
                    if count:
                        draft.name_parts = [*current.name_parts[-count:], fragment]
                        draft.line_start = current.continuation_lines[-count]
                        del current.name_parts[-count:]
                        del current.continuation_lines[-count:]
                        current.line_end = (
                            current.continuation_lines[-1]
                            if current.continuation_lines else current.anchor_line
                        )
                else:
                    count = _above_count([text for _, text in orphans])
                    if count:
                        draft.name_parts = [*(text for _, text in orphans[-count:]), fragment]
                        draft.line_start = orphans[-count][0]
                        del orphans[-count:]
            drain()
            flush()
            draft.group = group
            current = draft
            unanchored = 0
            run_len = 0
            index += 1
            continue
        if refusal == "position_missing":
            # A number at the end but no position: interleaved text or a wrapped name that
            # ends in a number. Reported; the open row stays open for its continuations.
            drain()
            run_len = 0
            collector.skip(page, number, refusal, line)
            unanchored += 1
            if unanchored > MAX_UNANCHORED_RUN:
                ended = _END_OTHER
                break
            index += 1
            continue
        if refusal is not None:
            drain()
            flush()
            run_len = 0
            collector.skip(page, number, refusal, line)
            unanchored = 0
            index += 1
            continue
        # A line without an anchor: a note, a group heading, or a wrapped description.
        unanchored += 1
        if unanchored > MAX_UNANCHORED_RUN or _NOTE_START.match(line.strip()):
            ended = _END_OTHER
            break
        if _is_group_heading(line):
            drain()
            flush()
            run_len = 0
            group = _words(line).rstrip(":")
        elif current is None:
            orphans.append((number, line))
        elif len(current.continuation_lines) >= MAX_CONTINUATION_LINES:
            collector.skip(page, number, "continuation_limit", line)
            run_len = 0
        else:
            current.name_parts.append(line)
            current.continuation_lines.append(number)
            current.line_end = number
            run_len += 1
        index += 1
    drain()
    flush()
    read = len(collector.rows) - rows_before
    if resume is None:
        if len(collector.tables) < MAX_LISTED_TABLES:
            record = _TableRecord(
                ordinal=ordinal,
                page_number=page,
                header_line_start=header_start + 1,
                header_line_end=body_start,
                columns=tuple(column for column in FORM7_COLUMNS if column in header.columns),
                implicit_unit=header.implicit_unit,
                status=TABLE_HEADER_AMBIGUOUS if header.ambiguous else TABLE_PARSED,
                row_count=read,
            )
            collector.tables.append(record)
            collector.records[ordinal] = record
    else:
        record = collector.records.get(ordinal)
        if record is not None:
            record.row_count += read
            record.continued_on.append(page)
    return index, _open_after(collector, header, ordinal, page, lines, index, ended, resume, read)


def _open_after(
    collector: _Collector,
    header: _Header,
    ordinal: int,
    page: int,
    lines: Sequence[str],
    index: int,
    ended: str,
    resume: _OpenTable | None,
    read: int,
) -> _OpenTable | None:
    """The table a following page may continue, or ``None`` when this one ended for good.

    A table is open only when it ran to the end of its page -- to the page's last line, or to
    the stamp with nothing after it that reads as one of the table's own rows -- and has at
    least one row (a header-ambiguous table reads none, so it is never open). "Reads as one of
    its own rows" is asked only of a table with a position or a unit column: in a table with
    neither, any title-block line ending in a number (``Разработал Иванов 01.26``) would read as
    a row, so there the next page's «Продолжение» line is the only evidence (:func:`_continues`).
    """
    if ended not in (_END_PAGE, _END_STAMP):
        return None
    if (
        ended == _END_STAMP
        and header.columns & {"position", "unit"}
        and any(
            _parse_row(text.split(), header)[0] is not None
            for text in lines[index + 1 :]
            if text.split()
        )
    ):
        return None
    if read:
        last = collector.rows[-1].position
    elif resume is not None:
        last = resume.last_position
    else:
        return None
    return _OpenTable(header=header, ordinal=ordinal, page=page, last_position=last)


def extract_specification(*, version_uid: str, pages: Mapping[int, str]) -> SpecificationExtraction:
    """Every specification row of the pages, in page and line order."""
    collector = _Collector(version_uid)
    carried: _OpenTable | None = None
    for page in sorted(pages):
        lines = pages[page].split("\n")
        sheet = _sheet_label(lines)
        index = 0
        open_table: _OpenTable | None = None
        if (
            carried is not None
            and carried.page + 1 == page
            and _continuation_start(lines, carried) is not None
        ):
            index, open_table = _read_table(
                collector, page, sheet, lines, carried.header, 0, 0, resume=carried
            )
        while index < len(lines):
            found = _find_header(lines, index)
            if found is None:
                index += 1
                continue
            header, body_start = found
            index, open_table = _read_table(collector, page, sheet, lines, header, index, body_start)
        carried = open_table
    return SpecificationExtraction(
        algorithm=EXTRACTION_ALGORITHM,
        version_uid=version_uid,
        page_count=len(pages),
        rows=tuple(collector.rows),
        tables=tuple(record.freeze() for record in collector.tables),
        table_count=collector.table_count,
        skipped=tuple(collector.skipped),
        skipped_by_reason={
            reason: collector.by_reason[reason] for reason in SKIP_REASONS if reason in collector.by_reason
        },
        over_limit=collector.over_limit,
    )
