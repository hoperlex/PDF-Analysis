"""Finding the header row and mapping its columns to position fields, by fixed rules.

Each header cell is normalised (:func:`.values.normalise_header`: lower case, ``ё`` as ``е``,
punctuation as spaces) and given to the first rule below that accepts it; a rule belongs to a
field and a tier. ``Цена, руб.`` is ``unit_price``; ``Ед. изм.`` is ``unit``; ``Наименование``
is ``name`` (tier 1) and ``Описание`` is ``name`` too, but tier 2, so a sheet with both keeps
``Наименование``. ``Сумма`` and ``Стоимость`` are deliberately **not** a unit price: either can
be a row total, and a total read as a unit price would be a guessed price.

A row is the header when it maps ``name``, ``unit`` and ``unit_price``. Within the best tier a
field must name exactly one column: two candidate columns for a **required** field refuse the
file (``price_list_header_ambiguous`` -- e.g. «Цена без НДС» and «Цена с НДС»: which one is
the unit price is the expert's decision, not this parser's); two for an **optional** field map
neither and the report lists them.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from .limits import MAX_COLUMNS, MAX_HEADER_TEXT
from .refusals import CONSTRAINT_HEADER_AMBIGUOUS, refuse
from .values import Cell, cell_text, normalise_header

__all__ = [
    "FIELDS",
    "OPTIONAL_FIELDS",
    "REQUIRED_FIELDS",
    "HeaderMatch",
    "MappedColumn",
    "field_of",
    "match_header",
]

REQUIRED_FIELDS: Final[tuple[str, ...]] = ("name", "unit", "unit_price")
OPTIONAL_FIELDS: Final[tuple[str, ...]] = ("code", "mark", "currency", "vendor", "section")
FIELDS: Final[tuple[str, ...]] = (*REQUIRED_FIELDS, *OPTIONAL_FIELDS)

_VENDOR_STEMS: Final[tuple[str, ...]] = (
    "поставщик",
    "производител",
    "изготовител",
    "vendor",
    "manufacturer",
    "supplier",
)

Rule = Callable[[str, tuple[str, ...]], bool]


def _first(*words: str) -> Rule:
    return lambda _normalised, tokens: tokens[0] in words


def _exact(*phrases: str) -> Rule:
    return lambda normalised, _tokens: normalised in phrases


def _prefix(*phrases: str) -> Rule:
    return lambda normalised, _tokens: any(
        normalised == phrase or normalised.startswith(phrase + " ") for phrase in phrases
    )


def _contains_stem(*stems: str) -> Rule:
    return lambda _normalised, tokens: any(
        token.startswith(stem) for token in tokens for stem in stems
    )


def _any(*rules: Rule) -> Rule:
    return lambda normalised, tokens: any(rule(normalised, tokens) for rule in rules)


#: ``(field, tier, rule)``, tried in this order; the first accepting rule decides a cell.
#: ``unit_price`` comes before ``unit`` (``Unit price`` is a price), ``code`` before ``vendor``
#: (``Код поставщика`` is a code), ``vendor`` before ``name`` (``Наименование поставщика`` is a
#: vendor).
RULES: Final[tuple[tuple[str, int, Rule], ...]] = (
    ("unit_price", 1, _any(_first("цена", "price"), _prefix("unit price"))),
    ("code", 1, _any(_first("код"), _exact("code", "item code", "product code"))),
    ("vendor", 1, _contains_stem(*_VENDOR_STEMS)),
    ("vendor", 2, _any(_first("бренд", "brand"), _prefix("торговая марка", "trade mark"))),
    ("name", 1, _any(_first("наименование"), _exact("name", "item name", "product name"))),
    (
        "name",
        2,
        _any(
            _first("название", "номенклатура", "товар", "описание"),
            _exact("item", "product", "description"),
        ),
    ),
    (
        "unit",
        1,
        _any(
            _prefix("ед изм", "единица измерения", "единицы измерения"),
            _exact("unit", "uom", "unit of measure", "unit of measurement"),
        ),
    ),
    ("unit", 2, _exact("ед", "единица", "units")),
    ("currency", 1, _first("валюта", "currency", "вал")),
    ("code", 2, _any(_first("артикул", "sku", "article"), _exact("part number", "p n"))),
    ("mark", 1, _first("марка", "тип", "обозначение", "model", "type", "mark")),
    ("section", 1, _first("раздел", "section", "дисциплина")),
)


def field_of(header: str) -> tuple[str, int] | None:
    """The ``(field, tier)`` one header cell maps to, or ``None``."""
    normalised = normalise_header(header)
    tokens = tuple(normalised.split())
    if not tokens:
        return None
    for field, tier, rule in RULES:
        if rule(normalised, tokens):
            return field, tier
    return None


@dataclass(frozen=True, slots=True)
class MappedColumn:
    """One mapped column: its 0-based index and its header text (display only)."""

    index: int
    header: str


@dataclass(frozen=True, slots=True)
class HeaderMatch:
    """The header row's mapping. ``columns`` has every required field."""

    columns: Mapping[str, MappedColumn]
    ambiguous: Mapping[str, tuple[str, ...]]
    ignored: tuple[str, ...]


def _clip(text: str) -> str:
    return text[:MAX_HEADER_TEXT]


def match_header(cells: Sequence[Cell | None]) -> HeaderMatch | None:
    """The row's mapping when it is a header, ``None`` when it is not; refuses ambiguity."""
    candidates: dict[str, dict[int, list[MappedColumn]]] = {}
    ignored: list[str] = []
    for index, cell in enumerate(cells[:MAX_COLUMNS]):
        text = cell_text(cell)
        if not text:
            continue
        mapped = field_of(text)
        if mapped is None:
            ignored.append(_clip(text))
            continue
        field, tier = mapped
        candidates.setdefault(field, {}).setdefault(tier, []).append(
            MappedColumn(index, _clip(text))
        )
    if any(field not in candidates for field in REQUIRED_FIELDS):
        return None

    columns: dict[str, MappedColumn] = {}
    ambiguous: dict[str, tuple[str, ...]] = {}
    for field in FIELDS:
        tiers = candidates.get(field)
        if not tiers:
            continue
        best = tiers[min(tiers)]
        for tier in sorted(tiers)[1:]:
            # A weaker-tier candidate (``Описание`` beside ``Наименование``) is not read;
            # the report names it so nothing is dropped without a trace.
            ignored.extend(column.header for column in tiers[tier])
        if len(best) == 1:
            columns[field] = best[0]
            continue
        if field in REQUIRED_FIELDS:
            raise refuse(
                CONSTRAINT_HEADER_AMBIGUOUS,
                f"More than one column of the header row can be read as the {field} "
                "column; keep exactly one such column and upload the file again.",
            )
        ambiguous[field] = tuple(column.header for column in best)
    return HeaderMatch(columns=columns, ambiguous=ambiguous, ignored=tuple(ignored))
