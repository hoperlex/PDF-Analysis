"""Specification rows matched to the positions of one price-list revision (`W60-OPT-MATCH-01`).

**The money rule** (``ROADMAP-TO-BETA.md`` §10 A-4/A-5): a price and an amount exist only
for a row matched to exactly one position, in the same unit, with a numeric quantity; the
amount is ``quantity × unit_price``, exact; a total is a sum of such amounts **per
currency** and states how many rows it leaves out and why. No price is guessed, no
currency converted, no amount rounded. Absent is absent, never ``0``.

Matching, per row, deterministic and exact on normalised text -- never fuzzy:

1. **Code / mark.** A position's ``code`` or ``mark`` that occurs, as whole tokens, in the
   row's description (a text layer runs the Form-7 name, type/mark, code and manufacturer
   cells together, ``specification``). Only specific keys take part: at least
   :data:`MIN_CODE_LENGTH` characters with a digit and either a letter or six digits, and
   not a bare standard reference (``ГОСТ``, ``ТУ``, ``СП``…), which many products share.
2. **Name**, only when step 1 finds nothing: the row's description equals, after
   normalisation, the position's name -- or its name followed by its mark, code and vendor
   in the Form-7 order (each combination of the ones present). Only when that finds nothing
   either, a vendor's **legal form** is optional on one side: a row whose manufacturer (the
   extractor's ``manufacturer``) opens with ``ООО``/``АО``… is compared without it against
   the positions whose vendor has none, and a row without one against the positions whose
   vendor has one dropped. Two different legal forms (``ООО`` and ``ЗАО``) are never equal.
3. Of the candidates, those **in the row's unit**: exactly one → ``matched``; two or more
   → ``ambiguous``; none → ``unmatched`` (``unit_mismatch``). A row without a unit is
   ``unmatched`` (``row_unit_missing``); no candidate at all is ``no_position``.

Normalisation (both sides alike): case, ``ё``/``е``, Latin letters that look like Cyrillic
ones (``x``/``х``, ``M``/``М``…), a decimal comma between digits, punctuation and
whitespace (the name key drops spaces altogether, so the extractor's glued words compare
equal), and a closed set of abbreviations (``мет.``/``металлический``,
``оцинк.``/``оцинкованный``, ``ж/б``/``железобетонный``…). Units compare by
:func:`unit_key`: the canonical unit when the spelling is known, else the compact text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from typing import Final

from .repository import PriceListPositionRecord
from .specification import SpecificationRow, canonical_unit, strip_legal_form

__all__ = [
    "BASIS_CODE",
    "BASIS_MARK",
    "BASIS_NAME",
    "BASES",
    "EXCLUDED_AMBIGUOUS",
    "EXCLUDED_QUANTITY_NOT_NUMERIC",
    "EXCLUSION_REASONS",
    "MATCH_ALGORITHM",
    "MAX_LISTED_CANDIDATES",
    "MIN_CODE_LENGTH",
    "REASON_NO_POSITION",
    "REASON_ROW_UNIT_MISSING",
    "REASON_SEVERAL_POSITIONS",
    "REASON_UNIT_MISMATCH",
    "STATUSES",
    "STATUS_AMBIGUOUS",
    "STATUS_MATCHED",
    "STATUS_UNMATCHED",
    "CurrencyTotal",
    "MatchOutcome",
    "RowMatch",
    "canonical_amount",
    "match_specification",
    "name_key",
    "unit_key",
]

MATCH_ALGORITHM: Final[str] = "price-match-v2"

STATUS_MATCHED: Final[str] = "matched"
STATUS_AMBIGUOUS: Final[str] = "ambiguous"
STATUS_UNMATCHED: Final[str] = "unmatched"
STATUSES: Final[tuple[str, ...]] = (STATUS_MATCHED, STATUS_AMBIGUOUS, STATUS_UNMATCHED)

BASIS_CODE: Final[str] = "code"
BASIS_MARK: Final[str] = "mark"
BASIS_NAME: Final[str] = "name"
BASES: Final[tuple[str, ...]] = (BASIS_CODE, BASIS_MARK, BASIS_NAME)

REASON_NO_POSITION: Final[str] = "no_position"
REASON_UNIT_MISMATCH: Final[str] = "unit_mismatch"
REASON_ROW_UNIT_MISSING: Final[str] = "row_unit_missing"
REASON_SEVERAL_POSITIONS: Final[str] = "several_positions"

EXCLUDED_AMBIGUOUS: Final[str] = "ambiguous"
EXCLUDED_QUANTITY_NOT_NUMERIC: Final[str] = "quantity_not_numeric"
#: Why a row adds nothing to a total; every row without an amount has exactly one.
EXCLUSION_REASONS: Final[tuple[str, ...]] = (
    REASON_NO_POSITION,
    REASON_UNIT_MISMATCH,
    REASON_ROW_UNIT_MISSING,
    EXCLUDED_AMBIGUOUS,
    EXCLUDED_QUANTITY_NOT_NUMERIC,
)

MAX_LISTED_CANDIDATES: Final[int] = 5
MIN_CODE_LENGTH: Final[int] = 5
_MIN_DIGIT_ONLY_CODE: Final[int] = 6


# --- normalisation ----------------------------------------------------------------------

#: Latin letters (after lower-casing) that print like Cyrillic ones.
_HOMOGLYPHS: Final[Mapping[int, str]] = str.maketrans({
    "a": "а", "b": "в", "c": "с", "e": "е", "h": "н", "k": "к", "m": "м", "o": "о",
    "p": "р", "t": "т", "x": "х", "y": "у", "ё": "е",
})
_DECIMAL_COMMA: Final[re.Pattern[str]] = re.compile(r"(?<=\d),(?=\d)")
_EDGE_PUNCTUATION: Final[str] = ".,;:()[]{}\"'«»„“”!?*"

#: Abbreviations written as a whole token (after punctuation is dropped).
_ABBREVIATIONS: Final[Mapping[str, str]] = {
    "мет": "мет", "металлич": "мет",
    "оцинк": "оцинк", "оц": "оцинк",
    "нерж": "нерж",
    "толщ": "толщ",
    "диам": "диам", "ø": "диам", "∅": "диам",
    "жб": "жб",
}
#: Full words that the abbreviations stand for, with their endings.
_FULL_WORDS: Final[tuple[tuple[re.Pattern[str], str], ...]] = tuple(
    (re.compile(rf"{stem}(?:ий|ый|ая|ое|ие|ые|ого|ой|их|ых|ую|им|ым|ими|ыми|ом|ем)"), short)
    for stem, short in (
        ("металлическ", "мет"),
        ("оцинкованн", "оцинк"),
        ("нержавеющ", "нерж"),
        ("железобетонн", "жб"),
    )
) + (
    (re.compile(r"толщин(?:а|ы|ой|у)"), "толщ"),
    (re.compile(r"диаметр(?:а|ом)?"), "диам"),
)
_STANDARD_PREFIXES: Final[frozenset[str]] = frozenset(
    "гост ост ту сто сп снип din en iso гостр".translate(_HOMOGLYPHS).split()
)


def _base(text: str) -> str:
    lowered = text.lower().translate(_HOMOGLYPHS)
    return _DECIMAL_COMMA.sub(".", lowered.replace("ж/б", "жб"))


def _code_tokens(text: str) -> tuple[str, ...]:
    """Whitespace tokens with edge punctuation removed; inner punctuation is kept."""
    tokens = (token.strip(_EDGE_PUNCTUATION) for token in _base(text).split())
    return tuple(token for token in tokens if token)


def _word(token: str) -> str:
    if token in _ABBREVIATIONS:
        return _ABBREVIATIONS[token]
    for pattern, short in _FULL_WORDS:
        if pattern.fullmatch(token):
            return short
    return token


def name_key(text: str) -> str:
    """The comparison key of a name: normalised words, abbreviations folded, no spaces."""
    base = _base(text)
    spaced = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", base)
    spaced = re.sub(r"[^0-9a-zа-я.ø∅]+", " ", spaced)
    return "".join(_word(token) for token in spaced.split())


def unit_key(text: str | None) -> str | None:
    """Pricing identity; owner2026-10-30 equates running metres and metres at factor1."""
    if text is None or not text.strip():
        return None
    canonical = canonical_unit(text)
    if canonical is not None:
        return "м" if canonical == "п.м" else canonical
    compact = re.sub(r"[\s.]", "", text.lower().replace("ё", "е"))
    return compact or None


def _specific_code(text: str | None) -> tuple[str, ...] | None:
    """The token sequence of a code or mark specific enough to identify a product."""
    if not text:
        return None
    tokens = _code_tokens(text)
    joined = "".join(tokens)
    digits = sum(character.isdigit() for character in joined)
    letters = sum(character.isalpha() for character in joined)
    if (
        not tokens
        or len(joined) < MIN_CODE_LENGTH
        or digits == 0
        or (letters == 0 and digits < _MIN_DIGIT_ONLY_CODE)
        or tokens[0] in _STANDARD_PREFIXES
        or any(joined.startswith(prefix) and joined[len(prefix) : len(prefix) + 1].isdigit()
               for prefix in _STANDARD_PREFIXES)
    ):
        return None
    return tokens


def canonical_amount(value: Decimal) -> str:
    """An exact decimal as plain text: no exponent, no trailing zeros, never rounded."""
    text = format(value.normalize(), "f")
    return "0" if text in ("-0", "") else text


# --- records --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RowMatch:
    """One row's match. ``amount`` is set only when the row counts in its currency's total.

    ``candidate_ids`` lists at most :data:`MAX_LISTED_CANDIDATES` positions in source-row
    order (the ambiguous tie, or the positions in another unit); ``candidate_count`` is
    complete. ``excluded_reason`` is one of :data:`EXCLUSION_REASONS` when ``amount`` is
    ``None``.
    """

    row: SpecificationRow
    status: str
    reason: str | None
    basis: str | None
    position: PriceListPositionRecord | None
    candidate_ids: tuple[str, ...]
    candidate_count: int
    amount: Decimal | None
    excluded_reason: str | None


@dataclass(frozen=True, slots=True)
class CurrencyTotal:
    currency: str
    amount: Decimal
    row_count: int


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    algorithm: str
    matches: tuple[RowMatch, ...]
    status_counts: Mapping[str, int]
    totals: tuple[CurrencyTotal, ...]
    excluded_by_reason: Mapping[str, int]


# --- index ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Keyed:
    tokens: tuple[str, ...]
    position: PriceListPositionRecord
    basis: str


class _PriceIndex:
    """Positions indexed by their code/mark tokens and by every name key.

    A code is looked up by its whole token sequence, under its first token: a row that names
    a token shared by thousands of codes (``ПК`` in ``ПК 60-12-8``) asks one dictionary per
    distinct length of those codes, not each of the thousands (`D-185`: the pass runs inside
    the request).
    """

    def __init__(self, positions: Sequence[PriceListPositionRecord]) -> None:
        self.codes: dict[str, dict[tuple[str, ...], list[_Keyed]]] = {}
        #: The distinct token counts of the codes that open with a token, ascending.
        self.code_lengths: dict[str, tuple[int, ...]] = {}
        self.names: dict[str, list[PriceListPositionRecord]] = {}
        #: Name keys with the vendor's legal form dropped, for positions whose vendor has one.
        self.loose_names: dict[str, list[PriceListPositionRecord]] = {}
        for position in sorted(positions, key=lambda item: item.row_number):
            for basis, value in ((BASIS_CODE, position.code), (BASIS_MARK, position.mark)):
                tokens = _specific_code(value)
                if tokens is not None:
                    self.codes.setdefault(tokens[0], {}).setdefault(tokens, []).append(
                        _Keyed(tokens, position, basis)
                    )
            for key in _name_keys(position):
                bucket = self.names.setdefault(key, [])
                if not bucket or bucket[-1] is not position:
                    bucket.append(position)
            for key in _loose_name_keys(position):
                bucket = self.loose_names.setdefault(key, [])
                if not bucket or bucket[-1] is not position:
                    bucket.append(position)
        self.code_lengths = {
            first: tuple(sorted({len(tokens) for tokens in table}))
            for first, table in self.codes.items()
        }

    def by_code(self, text: str) -> list[tuple[PriceListPositionRecord, str]]:
        tokens = _code_tokens(text)
        found: dict[str, tuple[PriceListPositionRecord, str]] = {}
        for start, token in enumerate(tokens):
            table = self.codes.get(token)
            if table is None:
                continue
            for length in self.code_lengths[token]:
                window = tokens[start : start + length]
                if len(window) < length:
                    break
                for keyed in table.get(window, ()):
                    identity = keyed.position.price_list_position_id
                    if identity not in found or keyed.basis == BASIS_CODE:
                        found[identity] = (keyed.position, keyed.basis)
        return sorted(found.values(), key=lambda pair: pair[0].row_number)

    def by_name(self, row: SpecificationRow) -> list[PriceListPositionRecord]:
        key = name_key(row.name)
        if not key:
            return []
        exact = list(self.names.get(key, ()))
        if exact:
            return exact
        # Nothing equal as written: a legal form is optional on one side (module note).
        if row.manufacturer is not None and strip_legal_form(row.manufacturer) != row.manufacturer:
            dropped = name_key(row.name.replace(row.manufacturer, strip_legal_form(row.manufacturer), 1))
            return list(self.names.get(dropped, ())) if dropped else []
        return list(self.loose_names.get(key, ()))


def _name_keys(position: PriceListPositionRecord) -> list[str]:
    """The name alone, then followed by each combination of mark, code and vendor in order."""
    extras = [value for value in (position.mark, position.code, position.vendor) if value]
    keys: list[str] = []
    for size in range(len(extras) + 1):
        for chosen in combinations(extras, size):
            key = name_key(" ".join((position.name, *chosen)))
            if key and key not in keys:
                keys.append(key)
    return keys


def _loose_name_keys(position: PriceListPositionRecord) -> list[str]:
    """The name keys that name the vendor without its legal form (none: it has no legal form)."""
    if not position.vendor or strip_legal_form(position.vendor) == position.vendor:
        return []
    others = [value for value in (position.mark, position.code) if value]
    vendor = strip_legal_form(position.vendor)
    keys: list[str] = []
    for size in range(len(others) + 1):
        for chosen in combinations(others, size):
            key = name_key(" ".join((position.name, *chosen, vendor)))
            if key and key not in keys:
                keys.append(key)
    return keys


# --- matching -------------------------------------------------------------------------


def _listed(positions: Iterable[PriceListPositionRecord]) -> tuple[tuple[str, ...], int]:
    ordered = sorted(positions, key=lambda item: item.row_number)
    return tuple(item.price_list_position_id for item in ordered[:MAX_LISTED_CANDIDATES]), len(ordered)


def _contributes(row: SpecificationRow, position: PriceListPositionRecord | None) -> bool:
    """The money rule, held at the point of computing an amount."""
    return (
        position is not None
        and row.quantity is not None
        and row.unit is not None
        and unit_key(row.unit) == unit_key(position.unit)
        and bool(position.currency)
    )


def _match_row(row: SpecificationRow, index: _PriceIndex) -> RowMatch:
    coded = index.by_code(row.name)
    if coded:
        candidates = [position for position, _ in coded]
        bases = {position.price_list_position_id: basis for position, basis in coded}
    else:
        candidates = index.by_name(row)
        bases = {position.price_list_position_id: BASIS_NAME for position in candidates}
    if not candidates:
        return RowMatch(row, STATUS_UNMATCHED, REASON_NO_POSITION, None, None, (), 0, None,
                        REASON_NO_POSITION)
    row_unit = unit_key(row.unit)
    if row_unit is None:
        listed, count = _listed(candidates)
        return RowMatch(row, STATUS_UNMATCHED, REASON_ROW_UNIT_MISSING, None, None, listed,
                        count, None, REASON_ROW_UNIT_MISSING)
    same_unit = [position for position in candidates if unit_key(position.unit) == row_unit]
    if not same_unit:
        listed, count = _listed(candidates)
        return RowMatch(row, STATUS_UNMATCHED, REASON_UNIT_MISMATCH, None, None, listed, count,
                        None, REASON_UNIT_MISMATCH)
    if len(same_unit) > 1:
        listed, count = _listed(same_unit)
        return RowMatch(row, STATUS_AMBIGUOUS, REASON_SEVERAL_POSITIONS, None, None, listed,
                        count, None, EXCLUDED_AMBIGUOUS)
    position = same_unit[0]
    basis = bases[position.price_list_position_id]
    quantity = row.quantity
    if quantity is None or not _contributes(row, position):
        return RowMatch(row, STATUS_MATCHED, None, basis, position,
                        (position.price_list_position_id,), 1, None,
                        EXCLUDED_QUANTITY_NOT_NUMERIC)
    amount = quantity * position.unit_price
    return RowMatch(row, STATUS_MATCHED, None, basis, position,
                    (position.price_list_position_id,), 1, amount, None)


def match_specification(
    rows: Sequence[SpecificationRow], positions: Sequence[PriceListPositionRecord]
) -> MatchOutcome:
    """Every row matched against the positions; totals per currency over amounts only."""
    index = _PriceIndex(positions)
    matches = tuple(_match_row(row, index) for row in rows)
    status_counts = {status: 0 for status in STATUSES}
    sums: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    excluded: dict[str, int] = {}
    for match in matches:
        status_counts[match.status] += 1
        if match.amount is not None and match.position is not None:
            currency = match.position.currency
            sums[currency] = sums.get(currency, Decimal(0)) + match.amount
            counts[currency] = counts.get(currency, 0) + 1
        else:
            reason = match.excluded_reason or REASON_NO_POSITION
            excluded[reason] = excluded.get(reason, 0) + 1
    return MatchOutcome(
        algorithm=MATCH_ALGORITHM,
        matches=matches,
        status_counts=status_counts,
        totals=tuple(
            CurrencyTotal(currency, sums[currency], counts[currency]) for currency in sorted(sums)
        ),
        excluded_by_reason={
            reason: excluded[reason] for reason in EXCLUSION_REASONS if reason in excluded
        },
    )
