"""Pure W57a normative quote and value grounding; no corpus or provider I/O.

The caller must first ground project-document evidence by the existing W56a
gate. These rules apply only to normative quotations from a pinned retrieval
set; they do not decide whether a norm applies to the project.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal


NORM_QUOTE_VERSION = "norm-quote-v1"
NORM_VALUE_VERSION = "norm-value-v1"
_WHITE_SPACE = frozenset(
    "\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008"
    "\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
)
_DELETED = frozenset("\u00ad\u200b\ufeff")
_NUMBER = re.compile(r"[0-9]{1,3}(?: [0-9]{3})+(?:[,.][0-9]+)*|[0-9]+(?:[,.][0-9]+)*")


@dataclass(frozen=True, slots=True)
class NormalizedParagraph:
    text: str
    raw_offsets: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class NormParagraph:
    paragraph_id: str
    document_id: str
    text: str
    label: str | None = None
    reliable: bool = True


@dataclass(frozen=True, slots=True)
class NormCitation:
    label: str
    quote: str


@dataclass(frozen=True, slots=True)
class NormLabelBinding:
    """One prompt label pointing at a unique canonical paragraph.

    Distinct map items may select the same paragraph under different labels.
    The binding is only local input; a caller must prove its set/custody pin.
    """

    label: str
    paragraph_id: str


@dataclass(frozen=True, slots=True)
class GroundedNormCitation:
    label: str
    document_id: str
    paragraph_id: str
    raw_offset: int
    raw_quote: str
    state: str  # verified | rebound


@dataclass(frozen=True, slots=True)
class NormGrounding:
    citations: tuple[GroundedNormCitation, ...]
    reason: str | None
    skipped_non_nfc: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.reason is None


class _RawSpanTooLong(Exception):
    """A normalized match exists but its canonical raw span is not storable."""


def normalize_paragraph(raw: str) -> NormalizedParagraph:
    """Apply N(s) and retain the first raw index of each collapsed space."""
    if unicodedata.normalize("NFC", raw) != raw:
        raise ValueError("norm_paragraph_not_nfc")
    chars: list[str] = []
    offsets: list[int] = []
    pending_space: int | None = None
    index = 0
    while index < len(raw):
        char = raw[index]
        if char in _DELETED:
            index += 1
            continue
        if raw.startswith("**", index):
            index += 2
            continue
        if char in _WHITE_SPACE:
            if pending_space is None:
                pending_space = index
            index += 1
            continue
        if pending_space is not None and chars:
            chars.append(" ")
            offsets.append(pending_space)
        pending_space = None
        chars.append(char)
        offsets.append(index)
        index += 1
    return NormalizedParagraph("".join(chars), tuple(offsets))


def normalize_quote(model_quote: str) -> str:
    """N(s) after the model-only NFC conversion declared by W57a."""
    return normalize_paragraph(unicodedata.normalize("NFC", model_quote)).text


def _raw_match(
    paragraph: NormParagraph, normalized: NormalizedParagraph, quote: str
) -> tuple[int, str] | None:
    start = normalized.text.find(quote)
    if start < 0:
        return None
    raw_start = normalized.raw_offsets[start]
    raw_end = normalized.raw_offsets[start + len(quote) - 1] + 1
    if raw_end - raw_start > 4000:
        raise _RawSpanTooLong
    raw_quote = paragraph.text[raw_start:raw_end]
    assert normalize_quote(raw_quote) == quote
    return raw_start, raw_quote


def value_tokens(value: str) -> tuple[Decimal, ...]:
    """Extract T(s) numbers with Decimal equality and W57a sign rules."""
    normalized = normalize_quote(value).replace("{,}", ",")
    tokens: list[Decimal] = []
    previous_end: int | None = None
    for match in _NUMBER.finditer(normalized):
        start, end = match.span()
        before = normalized[start - 1] if start else ""
        if before and (before.isalpha() or before in "^_"):
            continue
        if before == "{" and start >= 2 and normalized[start - 2] in "^_":
            continue
        if start and (
            before.isdigit()
            or (before in ",." and start >= 2 and normalized[start - 2].isdigit())
        ):
            continue
        if (
            end + 1 < len(normalized)
            and normalized[end] in ",."
            and normalized[end + 1].isdigit()
        ):
            continue
        literal = match.group()
        if literal.count(",") + literal.count(".") > 1:
            continue
        number = Decimal(literal.replace(" ", "").replace(",", "."))
        sign_index = start - 1
        if sign_index >= 0 and normalized[sign_index] in "-−+":
            sign_before = normalized[sign_index - 1] if sign_index else ""
            valid_position = not sign_before or sign_before in " ("
            follows_number = (
                previous_end is not None
                and normalized[previous_end:sign_index].strip(" ") == ""
            )
            if valid_position and not follows_number and normalized[sign_index] != "+":
                number = -number
        tokens.append(number)
        previous_end = end
    return tuple(tokens)


def value_in_quotes(value: str, quotes: tuple[str, ...]) -> bool:
    """Every numeric token must occur in the quotes; text values use N(s)."""
    wanted = value_tokens(value)
    if wanted:
        present = frozenset(token for quote in quotes for token in value_tokens(quote))
        return all(token in present for token in wanted)
    normalized = normalize_quote(value)
    return len(normalized) >= 3 and any(normalized in normalize_quote(quote) for quote in quotes)


def ground_norm_observation(
    paragraphs: tuple[NormParagraph, ...],
    citations: tuple[NormCitation, ...],
    required_value: str,
    stated_value: str,
    evidence_quotes: tuple[str, ...],
    *,
    label_bindings: tuple[NormLabelBinding, ...] | None = None,
) -> NormGrounding:
    """Ground all citations and values, withholding the whole item on failure.

    `evidence_quotes` must already have passed document-evidence grounding.
    Non-NFC and unreliable paragraphs are excluded from both labels and
    rebinding. A caller persists citations only when `accepted` is true.
    """
    paragraph_ids = [item.paragraph_id for item in paragraphs]
    paragraph_id_set = set(paragraph_ids)
    if len(paragraph_id_set) != len(paragraph_ids):
        raise ValueError("duplicate_norm_paragraph_id")
    if label_bindings is None:
        bindings = tuple(
            NormLabelBinding(item.label, item.paragraph_id)
            for item in paragraphs if item.label is not None
        )
    else:
        if (not isinstance(label_bindings, tuple)
                or any(not isinstance(item, NormLabelBinding) for item in label_bindings)
                or any(item.label is not None for item in paragraphs)):
            raise ValueError("mixed_or_invalid_norm_label_sources")
        bindings = label_bindings
    labels = [item.label for item in bindings]
    if len(set(labels)) != len(labels):
        raise ValueError("duplicate_norm_label")
    if any(
        not isinstance(item.label, str)
        or re.fullmatch(r"N[1-9][0-9]*", item.label) is None
        or item.paragraph_id not in paragraph_id_set
        for item in bindings
    ):
        raise ValueError("invalid_norm_label_binding")
    skipped = tuple(
        item.paragraph_id
        for item in paragraphs
        if unicodedata.normalize("NFC", item.text) != item.text
    )
    reliable = tuple(
        item for item in paragraphs if item.reliable and item.paragraph_id not in skipped
    )
    by_id = {item.paragraph_id: item for item in reliable}
    by_label = {
        binding.label: by_id[binding.paragraph_id]
        for binding in bindings if binding.paragraph_id in by_id
    }
    prepared = {item.paragraph_id: normalize_paragraph(item.text) for item in reliable}

    def withheld(reason: str) -> NormGrounding:
        return NormGrounding((), reason, skipped)

    grounded: list[GroundedNormCitation] = []
    for citation in citations:
        labelled = by_label.get(citation.label)
        if labelled is None:
            return withheld("norm_label_unknown")
        quote = normalize_quote(citation.quote)
        if len(quote) < 20:
            return withheld("norm_quote_too_short")
        try:
            match = _raw_match(labelled, prepared[labelled.paragraph_id], quote)
        except _RawSpanTooLong:
            return withheld("norm_quote_absent")
        state = "verified"
        target = labelled
        if match is None:
            alternatives: list[tuple[NormParagraph, tuple[int, str]]] = []
            for item in reliable:
                if (
                    item.document_id != labelled.document_id
                    or item.paragraph_id == labelled.paragraph_id
                ):
                    continue
                try:
                    found = _raw_match(item, prepared[item.paragraph_id], quote)
                except _RawSpanTooLong:
                    continue
                if found is not None:
                    alternatives.append((item, found))
                    if len(alternatives) > 1:
                        break
            if len(alternatives) > 1:
                return withheld("norm_quote_ambiguous")
            if not alternatives:
                return withheld("norm_quote_absent")
            target, match = alternatives[0]
            state = "rebound"
        assert match is not None
        grounded.append(
            GroundedNormCitation(
                label=citation.label,
                document_id=target.document_id,
                paragraph_id=target.paragraph_id,
                raw_offset=match[0],
                raw_quote=match[1],
                state=state,
            )
        )
    norm_quotes = tuple(item.raw_quote for item in grounded)
    if not value_in_quotes(required_value, norm_quotes):
        return withheld("norm_value_not_in_quote")
    if not value_in_quotes(stated_value, evidence_quotes):
        return withheld("stated_value_not_in_evidence")
    return NormGrounding(tuple(grounded), None, skipped)
