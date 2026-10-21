"""Reading one cell: text, a unit price, a currency, a section. Pure and deterministic.

**A price is read, never guessed.** A text cell is a price only when it is a plain number:
digits with at most one decimal separator (a comma or a point -- the Russian decimal comma is
the default reading of ``1,234``), optionally grouped in thousands by spaces, or by points when
the decimal separator is a comma, or by commas when it is a point. ``по запросу``,
``от 100``, ``500 руб.``, ``1-2 тыс.`` and anything else are not prices and the row is
skipped with a reason. A numeric XLSX cell is the stored number, read back at Excel's own
display precision (fifteen significant digits) so that a binary artefact such as
``12.300000000000001`` reads as ``12.3`` -- the value the spreadsheet shows. A price that is
not positive, has more than six decimals or is not below 10^14 is refused, never rounded.

**A currency** is an ISO 4217 code (any three Latin letters, upper-cased) or one of the
spelled forms in :data:`CURRENCY_WORDS`; anything else is unrecognised.

**A section** is one of the fifteen sections, by its code in Latin (``EOM``) or as its Cyrillic abbreviation
(``ЭОМ``), or the section's catalogue name; anything else is unrecognised (a warning: the
position keeps its price and has no section).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation
from typing import Final

from .limits import MAX_PRICE_DECIMALS, MAX_PRICE_EXCLUSIVE, XLSX_SIGNIFICANT_DIGITS

__all__ = [
    "CURRENCY_WORDS",
    "SECTION_ABBREVIATIONS",
    "NumericCell",
    "Cell",
    "PriceReading",
    "canonical_price",
    "cell_text",
    "header_tokens",
    "normalise_header",
    "read_currency",
    "read_price",
    "read_section",
]


@dataclass(frozen=True, slots=True)
class NumericCell:
    """A numeric XLSX cell: the number exactly as the sheet stores it (``<v>`` text)."""

    raw: str


#: A cell is text (CSV, a string XLSX cell) or a stored XLSX number.
Cell = str | NumericCell

_XLSX_CONTEXT: Final[Context] = Context(prec=XLSX_SIGNIFICANT_DIGITS, rounding=ROUND_HALF_EVEN)
_OOXML_ESCAPE: Final[re.Pattern[str]] = re.compile(r"_x([0-9A-Fa-f]{4})_")
_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")
_SPACES: Final[re.Pattern[str]] = re.compile(r"[\s    ]+")

#: Plain numbers, tried in this order on the space-normalised text.
_PLAIN: Final[re.Pattern[str]] = re.compile(r"[+-]?\d+(?:[.,]\d+)?")
_SPACE_GROUPED: Final[re.Pattern[str]] = re.compile(r"[+-]?\d{1,3}(?: \d{3})+(?:[.,]\d+)?")
#: Point-grouped thousands need a decimal comma or at least two groups (``1.234.567``): one
#: group alone (``1.234``) is a plain decimal. The same rule for comma groups.
_POINT_GROUPED: Final[re.Pattern[str]] = re.compile(
    r"[+-]?\d{1,3}(?:(?:\.\d{3})+,\d+|(?:\.\d{3}){2,})"
)
_COMMA_GROUPED: Final[re.Pattern[str]] = re.compile(
    r"[+-]?\d{1,3}(?:(?:,\d{3})+\.\d+|(?:,\d{3}){2,})"
)

#: Spelled currencies (lower case, after :func:`normalise_header`). Three Latin letters are
#: read as an ISO 4217 code without this table.
CURRENCY_WORDS: Final[Mapping[str, str]] = {
    "р": "RUB",
    "руб": "RUB",
    "рубль": "RUB",
    "рубли": "RUB",
    "рублей": "RUB",
    "рубля": "RUB",
    "₽": "RUB",
    "rur": "RUB",
    "$": "USD",
    "долл": "USD",
    "доллар": "USD",
    "доллары": "USD",
    "долларов": "USD",
    "доллар сша": "USD",
    "€": "EUR",
    "евро": "EUR",
    "юань": "CNY",
    "юани": "CNY",
    "юаней": "CNY",
}
_ISO_CODE: Final[re.Pattern[str]] = re.compile(r"[a-z]{3}")

#: The fifteen section codes' Cyrillic abbreviations (``tests/unit/optimisation`` holds the
#: key set equal to the section vocabulary). Upper case; ``ОВИК`` is the common spelling of
#: «ОВиК».
SECTION_ABBREVIATIONS: Final[Mapping[str, str]] = {
    "AR": "АР",
    "AI": "АИ",
    "KM": "КМ",
    "KJ": "КЖ",
    "OV": "ОВ",
    "EOM": "ЭОМ",
    "VK": "ВК",
    "PT": "ПТ",
    "PB": "ПБ",
    "SS": "СС",
    "ITP": "ИТП",
    "GP": "ГП",
    "TX": "ТХ",
    "POS": "ПОС",
    "PS": "ПЗ",
}
_SECTION_ALIASES: Final[Mapping[str, str]] = {"ОВИК": "OV"}

_HEADER_PUNCTUATION: Final[re.Pattern[str]] = re.compile(
    r"[.,:;()\[\]{}/\\|\-–—_\"'«»*#№]+"
)


def _clean(text: str) -> str:
    """Undo OOXML ``_xHHHH_`` escapes and collapse every whitespace run to one space."""
    unescaped = _OOXML_ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), text)
    return _WHITESPACE.sub(" ", unescaped).strip()


def _xlsx_decimal(raw: str) -> Decimal | None:
    try:
        value = _XLSX_CONTEXT.create_decimal(raw.strip())
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite():
        return None
    return value


def canonical_price(value: Decimal) -> str:
    """The exact plain-decimal text stored and served: no exponent, no trailing zeros."""
    normalised = value.normalize()
    text = format(normalised, "f")
    return "0" if text in ("-0", "") else text


def cell_text(cell: Cell | None) -> str:
    """A cell as display text: whitespace collapsed, a stored number as its plain decimal."""
    if cell is None:
        return ""
    if isinstance(cell, NumericCell):
        value = _xlsx_decimal(cell.raw)
        return cell.raw.strip() if value is None else canonical_price(value)
    return _clean(cell)


def normalise_header(text: str) -> str:
    """Lower case, ``ё`` as ``е``, punctuation as spaces, one space between words."""
    lowered = _clean(text).replace("ё", "е").replace("Ё", "Е").lower()
    return " ".join(_HEADER_PUNCTUATION.sub(" ", lowered).split())


def header_tokens(text: str) -> tuple[str, ...]:
    return tuple(normalise_header(text).split())


@dataclass(frozen=True, slots=True)
class PriceReading:
    """A unit price, or the reason a cell is not one."""

    value: Decimal | None
    reason: str | None


def _bounded(value: Decimal) -> PriceReading:
    if value <= 0:
        return PriceReading(None, "price_not_positive")
    normalised = value.normalize()
    exponent = normalised.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -MAX_PRICE_DECIMALS:
        return PriceReading(None, "price_precision")
    if normalised >= MAX_PRICE_EXCLUSIVE:
        return PriceReading(None, "price_too_large")
    return PriceReading(normalised, None)


def read_price(cell: Cell | None) -> PriceReading:
    """A unit price from one cell, or ``price_missing`` / ``price_not_a_number`` / a bound."""
    if cell is None:
        return PriceReading(None, "price_missing")
    if isinstance(cell, NumericCell):
        value = _xlsx_decimal(cell.raw)
        if value is None:
            return PriceReading(None, "price_not_a_number")
        return _bounded(value)
    text = _SPACES.sub(" ", _OOXML_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), cell)).strip()
    if not text:
        return PriceReading(None, "price_missing")
    if _PLAIN.fullmatch(text):
        literal = text.replace(",", ".")
    elif _SPACE_GROUPED.fullmatch(text):
        literal = text.replace(" ", "").replace(",", ".")
    elif _POINT_GROUPED.fullmatch(text):
        literal = text.replace(".", "").replace(",", ".")
    elif _COMMA_GROUPED.fullmatch(text):
        literal = text.replace(",", "")
    else:
        return PriceReading(None, "price_not_a_number")
    try:
        value = Decimal(literal)
    except InvalidOperation:  # pragma: no cover - the patterns admit only decimal literals
        return PriceReading(None, "price_not_a_number")
    return _bounded(value)


def _currency_word(normalised: str) -> str | None:
    if _ISO_CODE.fullmatch(normalised):
        return normalised.upper()
    return CURRENCY_WORDS.get(normalised)


def read_currency(cell: Cell | None) -> tuple[str | None, bool]:
    """``(code, recognised)``: ``(None, True)`` for an empty cell, ``(None, False)`` unread."""
    text = cell_text(cell)
    if not text:
        return None, True
    code = _currency_word(normalise_header(text))
    return code, code is not None


def currency_in_header(header: str) -> str | None:
    """The one currency a price column's header names (``Цена, руб.``), if exactly one."""
    words = normalise_header(header).split()
    found = {code for code in (CURRENCY_WORDS.get(word) for word in words) if code}
    found |= {
        word.upper()
        for word in words
        if word in ("rub", "usd", "eur", "cny")
    }
    for symbol, code in (("₽", "RUB"), ("$", "USD"), ("€", "EUR")):
        if symbol in header:
            found.add(code)
    return found.pop() if len(found) == 1 else None


def read_section(cell: Cell | None, names: Mapping[str, str]) -> tuple[str | None, bool]:
    """``(code, recognised)`` for a section cell; ``names`` maps code to catalogue name."""
    text = cell_text(cell)
    if not text:
        return None, True
    upper = text.upper().replace("Ё", "Е")
    if upper in SECTION_ABBREVIATIONS:
        return upper, True
    for code, abbreviation in SECTION_ABBREVIATIONS.items():
        if upper == abbreviation:
            return code, True
    if upper in _SECTION_ALIASES:
        return _SECTION_ALIASES[upper], True
    folded = normalise_header(text)
    for code, name in names.items():
        if folded == normalise_header(name):
            return code, True
    return None, False
