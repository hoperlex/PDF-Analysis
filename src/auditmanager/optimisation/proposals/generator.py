"""The deterministic generator of «более дешёвый аналог» proposals (``cheaper-analog-v1``).

Pure: rows already matched by :func:`~auditmanager.optimisation.matching.match_specification`,
the positions of the **same** price-list revision and the vendors of the effective AR vendor
list go in; ordered proposal drafts come out. No clock, no randomness, no I/O, no model.

For each specification row whose match is ``matched`` (exactly one position, in the row's
unit -- the matcher's own rule), a position of the same revision is a **cheaper analog**
when all of the following hold:

1. it is another position than the matched one;
2. its unit is the matched position's unit under the matcher's :func:`unit_key` (so also the
   row's unit) -- ``п.м`` and ``м`` stay different units;
3. its currency is the matched position's currency -- nothing is converted;
4. its unit price is strictly lower than the matched position's;
5. its vendor is on the effective AR vendor list (:func:`vendor_key`: case, ``ё``, quotes
   and punctuation and the legal form -- ``ООО``, ``АО``… -- do not count); a position
   without a vendor never qualifies;
6. it is the **same kind of product**: both names start with the same head word (the first
   word with a letter, abbreviations folded as the matcher folds them), and either
   * ``code_family`` -- both carry a code (else a mark) whose leading letters, at least
     :data:`MIN_FAMILY_LETTERS` of them followed by a digit, are the same (``ПК 60-12-8`` and
     ``ПК 63-15-8``); or
   * ``name_similarity`` -- the share of shared words, ``|A ∩ B| / |A ∪ B|`` over the two
     names' normalised word sets, is at least :data:`NAME_SIMILARITY_THRESHOLD`.

   The matcher itself has no similarity threshold: its name tier is equality after
   normalisation (similarity 1), which identifies *the* product. An analog is by definition
   another product, so the generator's threshold is its own, fixed and documented here; an
   equal name from another vendor is the strongest analog there is (similarity 1).

The analogs of one row are ordered by unit price ascending (the largest saving per unit
first), then similarity descending, then source row, then position identity, and at most
:data:`MAX_PROPOSALS_PER_ROW` are kept. Rows keep the extraction order (page, line); the
pass-wide ``ordinal`` numbers the drafts in that order and is a display order, never an
identity.

**The money rule** (``ROADMAP-TO-BETA.md`` §10.1 A-4/A-5). Both prices come from price-list
positions of the pass's revision and nowhere else. The saving is
``(current − proposed) × quantity``, exact and never rounded, and **only** when the row's
quantity is a plain number; otherwise it is absent (``None``) -- never ``0``. A row that is
unmatched, ambiguous or unit-mismatched never yields a proposal and therefore never a
saving. Migration ``0027`` restates the rule as CHECKs and a trigger, so a writer that
bypassed this module would still be refused.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from fractions import Fraction
from typing import Final

from ..matching import BASES, STATUS_MATCHED, RowMatch, canonical_amount, name_key, unit_key
from ..repository import PriceListPositionRecord
from ..specification import SpecificationRow

__all__ = [
    "ANALOG_BASES",
    "BASIS_CODE_FAMILY",
    "BASIS_NAME_SIMILARITY",
    "GENERATOR_VERSION",
    "MAX_PROPOSALS_PER_PASS",
    "MAX_PROPOSALS_PER_ROW",
    "MAX_QUANTITY_TEXT",
    "MAX_RATIONALE",
    "MAX_ROW_POSITION",
    "MAX_ROW_TEXT",
    "MAX_SHEET_LABEL",
    "MIN_FAMILY_LETTERS",
    "NAME_SIMILARITY_THRESHOLD",
    "PROPOSAL_TYPE_CHEAPER_ANALOG",
    "PROPOSAL_TYPES",
    "GeneratorOutcome",
    "ProposalDraft",
    "code_family",
    "generate_cheaper_analogs",
    "head_word",
    "name_similarity",
    "saving_for",
    "vendor_key",
]

GENERATOR_VERSION: Final[str] = "cheaper-analog-v1"

PROPOSAL_TYPE_CHEAPER_ANALOG: Final[str] = "cheaper_analog"
#: The legacy vocabulary also names ``faster_install``, ``simpler_design`` and ``lifecycle``;
#: those need judgement and arrive with the LLM slice (``contracts/optimization/v1``).
#: Restated by migration ``0027`` (``ck_optimisation_proposal_proposal_type``).
PROPOSAL_TYPES: Final[tuple[str, ...]] = (PROPOSAL_TYPE_CHEAPER_ANALOG,)

BASIS_CODE_FAMILY: Final[str] = "code_family"
BASIS_NAME_SIMILARITY: Final[str] = "name_similarity"
ANALOG_BASES: Final[tuple[str, ...]] = (BASIS_CODE_FAMILY, BASIS_NAME_SIMILARITY)

MAX_PROPOSALS_PER_ROW: Final[int] = 3
NAME_SIMILARITY_THRESHOLD: Final[Fraction] = Fraction(1, 2)
MIN_FAMILY_LETTERS: Final[int] = 2

#: Storage bounds, restated by migration ``0027``. A matched row whose provenance exceeds one
#: is not proposed (counted as ``rows_out_of_bounds``) rather than stored cut.
MAX_ROW_TEXT: Final[int] = 8000
MAX_ROW_POSITION: Final[int] = 100
MAX_SHEET_LABEL: Final[int] = 100
MAX_QUANTITY_TEXT: Final[int] = 100
MAX_RATIONALE: Final[int] = 10_000
#: ``MAX_SPECIFICATION_ROWS`` (10 000) × :data:`MAX_PROPOSALS_PER_ROW`.
MAX_PROPOSALS_PER_PASS: Final[int] = 30_000

_SIMILARITY_PLACES: Final[Decimal] = Decimal("0.0001")
_WORD_SPLIT: Final[re.Pattern[str]] = re.compile(r"\s+")
_VENDOR_SPLIT: Final[re.Pattern[str]] = re.compile(r"[^0-9a-zа-я]+")
_LEGAL_FORMS: Final[frozenset[str]] = frozenset(
    {"ооо", "оао", "зао", "пао", "нао", "ао", "ип", "тоо", "llc", "ltd", "gmbh", "inc", "jsc"}
)
_FAMILY: Final[re.Pattern[str]] = re.compile(r"^([^\W\d_]+)\d")


# --- normalisation ----------------------------------------------------------------------


def _words(text: str) -> tuple[str, ...]:
    """The name's words, each normalised as the matcher's name key normalises it."""
    keys = (name_key(token) for token in _WORD_SPLIT.split(text.strip()))
    return tuple(key for key in keys if key)


def head_word(text: str) -> str | None:
    """The first normalised word that contains a letter (a leading number is not a kind)."""
    return next((word for word in _words(text) if any(ch.isalpha() for ch in word)), None)


def name_similarity(left: str, right: str) -> Fraction:
    """``|A ∩ B| / |A ∪ B|`` over the two names' normalised word sets (0 when both empty)."""
    first, second = set(_words(left)), set(_words(right))
    union = first | second
    return Fraction(len(first & second), len(union)) if union else Fraction(0)


def code_family(position: PriceListPositionRecord) -> str | None:
    """The leading letters of the position's code (else its mark), when followed by a digit."""
    for value in (position.code, position.mark):
        if not value:
            continue
        compact = name_key(value)
        found = _FAMILY.match(compact)
        if found is not None and len(found.group(1)) >= MIN_FAMILY_LETTERS:
            return found.group(1)
        return None
    return None


def vendor_key(text: str | None) -> str | None:
    """A vendor name compared regardless of case, ``ё``, quotes, punctuation and legal form."""
    if not text:
        return None
    lowered = text.lower().replace("ё", "е")
    words = [word for word in _VENDOR_SPLIT.split(lowered) if word and word not in _LEGAL_FORMS]
    keys = [name_key(word) for word in words]
    joined = " ".join(key for key in keys if key)
    return joined or None


# --- money --------------------------------------------------------------------------------


def saving_for(
    *, current_unit_price: Decimal, proposed_unit_price: Decimal, quantity: Decimal | None
) -> Decimal | None:
    """``(current − proposed) × quantity`` exactly, or ``None`` without a numeric quantity."""
    if quantity is None:
        return None
    return (current_unit_price - proposed_unit_price) * quantity


# --- records ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProposalDraft:
    """One proposal before it is stored. ``saving`` is ``None`` unless it is computable."""

    ordinal: int
    proposal_type: str
    row: SpecificationRow
    matched: PriceListPositionRecord
    matched_basis: str
    proposed: PriceListPositionRecord
    analog_basis: str
    similarity: Decimal
    unit: str
    quantity: Decimal | None
    current_unit_price: Decimal
    proposed_unit_price: Decimal
    currency: str
    saving: Decimal | None
    rationale: str


@dataclass(frozen=True, slots=True)
class GeneratorOutcome:
    """The drafts and how every specification row was accounted for.

    ``rows_matched`` = ``rows_with_proposals`` + ``rows_without_analog`` +
    ``rows_out_of_bounds``; ``rows_not_matched`` are the unmatched and ambiguous rows, which
    are never proposed.
    """

    generator_version: str
    proposals: tuple[ProposalDraft, ...]
    rows_total: int
    rows_matched: int
    rows_not_matched: int
    rows_with_proposals: int
    rows_without_analog: int
    rows_out_of_bounds: int


# --- generation ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Keyed:
    """One position with the keys the rules compare, computed once per pass."""

    position: PriceListPositionRecord
    unit: str | None
    vendor: str | None
    head: str | None
    words: frozenset[str]
    family: str | None


@dataclass(frozen=True, slots=True)
class _Candidate:
    position: PriceListPositionRecord
    basis: str
    similarity: Fraction


def _keyed(position: PriceListPositionRecord) -> _Keyed:
    words = _words(position.name)
    return _Keyed(
        position=position,
        unit=unit_key(position.unit),
        vendor=vendor_key(position.vendor),
        head=next((word for word in words if any(ch.isalpha() for ch in word)), None),
        words=frozenset(words),
        family=code_family(position),
    )


class _Index:
    """Positions bucketed by (unit, currency, head word): only a bucket can hold an analog."""

    def __init__(self, positions: Sequence[PriceListPositionRecord]) -> None:
        self.keyed: dict[str, _Keyed] = {}
        self.buckets: dict[tuple[str | None, str, str], list[_Keyed]] = {}
        for position in sorted(positions, key=lambda item: item.row_number):
            keyed = _keyed(position)
            self.keyed[position.price_list_position_id] = keyed
            if keyed.head is not None:
                bucket = (keyed.unit, position.currency, keyed.head)
                self.buckets.setdefault(bucket, []).append(keyed)

    def of(self, position: PriceListPositionRecord) -> _Keyed:
        return self.keyed.get(position.price_list_position_id) or _keyed(position)


def _similarity(left: frozenset[str], right: frozenset[str]) -> Fraction:
    union = left | right
    return Fraction(len(left & right), len(union)) if union else Fraction(0)


def _same_kind(matched: _Keyed, other: _Keyed) -> _Candidate | None:
    """Rule 6: the same head word (the bucket), then the code family or the name similarity."""
    if matched.head is None or matched.head != other.head:
        return None
    similarity = _similarity(matched.words, other.words)
    if matched.family is not None and matched.family == other.family:
        return _Candidate(other.position, BASIS_CODE_FAMILY, similarity)
    if similarity >= NAME_SIMILARITY_THRESHOLD:
        return _Candidate(other.position, BASIS_NAME_SIMILARITY, similarity)
    return None


def _analogs(matched: _Keyed, index: _Index, vendors: frozenset[str]) -> list[_Candidate]:
    """Rules 1-6 over the matched position's bucket, ordered, at most N."""
    current = matched.position
    if matched.head is None:
        return []
    found: list[_Candidate] = []
    for other in index.buckets.get((matched.unit, current.currency, matched.head), ()):
        position = other.position
        if (
            position.price_list_position_id == current.price_list_position_id
            or other.unit != matched.unit
            or position.currency != current.currency
            or not position.unit_price < current.unit_price
            or other.vendor is None
            or other.vendor not in vendors
        ):
            continue
        candidate = _same_kind(matched, other)
        if candidate is not None:
            found.append(candidate)
    found.sort(
        key=lambda item: (
            item.position.unit_price,
            -item.similarity,
            item.position.row_number,
            item.position.price_list_position_id,
        )
    )
    return found[:MAX_PROPOSALS_PER_ROW]


def _in_bounds(row: SpecificationRow) -> bool:
    return (
        0 < len(row.name) <= MAX_ROW_TEXT
        and (row.position is None or len(row.position) <= MAX_ROW_POSITION)
        and (row.sheet_label is None or len(row.sheet_label) <= MAX_SHEET_LABEL)
        and (row.quantity_text is None or len(row.quantity_text) <= MAX_QUANTITY_TEXT)
    )


def _priced_match(match: RowMatch) -> PriceListPositionRecord | None:
    """The matched position, only for a row the money rule lets carry a price at all."""
    position = match.position
    if match.status != STATUS_MATCHED or position is None or match.basis not in BASES:
        return None
    row_unit = unit_key(match.row.unit)
    if row_unit is None or row_unit != unit_key(position.unit):
        return None
    return position


def _similarity_value(value: Fraction) -> Decimal:
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    return exact.quantize(_SIMILARITY_PLACES, rounding=ROUND_DOWN)


def _label(position: PriceListPositionRecord) -> str:
    extras = [value for value in (position.mark, position.code) if value]
    return f"«{position.name}»" + (f" ({', '.join(extras)})" if extras else "")


def _rationale(matched: _Keyed, candidate: _Candidate) -> str:
    """The sentence an expert reads beside the two prices: which position, from whom, why.

    Words only -- no price, no currency code, no decimal: the figures are the proposal's own
    fields, shown exactly by whoever renders them, and a second copy of them in prose would be
    a second thing to keep equal.
    """
    current, proposed = matched.position, candidate.position
    basis = (
        f"одно семейство кода «{matched.family}»"
        if candidate.basis == BASIS_CODE_FAMILY
        else f"сходство наименований {canonical_amount(_similarity_value(candidate.similarity))}"
    )
    return (
        f"Более дешёвый аналог: {_label(proposed)}, поставщик {proposed.vendor}, "
        f"вместо {_label(current)}; основание: {basis}."
    )


def generate_cheaper_analogs(
    matches: Sequence[RowMatch],
    positions: Sequence[PriceListPositionRecord],
    vendors: Iterable[str],
) -> GeneratorOutcome:
    """Every cheaper analog of every matched row, ordered, at most N per row.

    ``positions`` are every position of the one revision the rows were matched against;
    a matched position that is not among them is a caller error (``ValueError``).
    """
    allowed = frozenset(key for key in (vendor_key(vendor) for vendor in vendors) if key)
    index = _Index(positions)
    drafts: list[ProposalDraft] = []
    matched_rows = with_proposals = without_analog = out_of_bounds = 0
    for match in matches:
        position = _priced_match(match)
        if position is None:
            continue
        matched_rows += 1
        if position.price_list_position_id not in index.keyed:
            raise ValueError("a matched position is not a position of the given revision")
        if not _in_bounds(match.row):
            out_of_bounds += 1
            continue
        matched = index.of(position)
        analogs = _analogs(matched, index, allowed) if allowed else []
        if not analogs:
            without_analog += 1
            continue
        with_proposals += 1
        unit = matched.unit
        assert unit is not None and match.basis is not None  # held by _priced_match
        for candidate in analogs:
            proposed = candidate.position
            drafts.append(
                ProposalDraft(
                    ordinal=len(drafts) + 1,
                    proposal_type=PROPOSAL_TYPE_CHEAPER_ANALOG,
                    row=match.row,
                    matched=position,
                    matched_basis=match.basis,
                    proposed=proposed,
                    analog_basis=candidate.basis,
                    similarity=_similarity_value(candidate.similarity),
                    unit=unit,
                    quantity=match.row.quantity,
                    current_unit_price=position.unit_price,
                    proposed_unit_price=proposed.unit_price,
                    currency=position.currency,
                    saving=saving_for(
                        current_unit_price=position.unit_price,
                        proposed_unit_price=proposed.unit_price,
                        quantity=match.row.quantity,
                    ),
                    rationale=_rationale(matched, candidate),
                )
            )
    return GeneratorOutcome(
        generator_version=GENERATOR_VERSION,
        proposals=tuple(drafts),
        rows_total=len(matches),
        rows_matched=matched_rows,
        rows_not_matched=len(matches) - matched_rows,
        rows_with_proposals=with_proposals,
        rows_without_analog=without_analog,
        rows_out_of_bounds=out_of_bounds,
    )
