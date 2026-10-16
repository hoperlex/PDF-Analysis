"""Parse untrusted AR v3 proposals before any grounding or publication.

This module has no corpus access and creates no citation verdict. Provider
truncation may salvage only complete initial observations, never a partly
written normative citation or an inferred missing value.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.profiles.ar_v3.response_schema import (
    CATEGORIES,
    NONNORMATIVE_CATEGORIES,
    NORMATIVE_CATEGORIES,
    SEVERITIES,
)


class V3ResponseError(ValueError):
    """The response is not a valid v3 envelope or JSON input."""


@dataclass(frozen=True, slots=True)
class ProposedEvidence:
    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class ProposedNormCitation:
    label: str
    quote: str


@dataclass(frozen=True, slots=True)
class ProposedObservation:
    category: str
    finding_text: str
    recommendation_text: str
    proposed_severity: str
    evidence: tuple[ProposedEvidence, ...]
    norm_citations: tuple[ProposedNormCitation, ...] | None
    required_value: str | None
    stated_value: str | None


@dataclass(frozen=True, slots=True)
class ParsedResponse:
    observations: tuple[ProposedObservation, ...]
    salvaged: bool
    malformed_count: int


_PREFIX: Final[re.Pattern[str]] = re.compile(r'\A\s*\{\s*"observations"\s*:\s*\[')
_LABEL: Final[re.Pattern[str]] = re.compile(r"N[1-9][0-9]*\Z")
_BASE_KEYS: Final[frozenset[str]] = frozenset({
    "category", "finding_text", "recommendation_text", "proposed_severity", "evidence",
})
_NORM_KEYS: Final[frozenset[str]] = frozenset({
    "norm_citations", "required_value", "stated_value",
})


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


def _complete_array_elements(output_text: str) -> list[Any]:
    """Read initial complete array elements only after the exact v3 envelope prefix."""
    match = _PREFIX.match(output_text)
    if match is None:
        return []
    decoder = json.JSONDecoder(object_pairs_hook=_unique_object)
    position = match.end()
    elements: list[Any] = []
    while position < len(output_text):
        while position < len(output_text) and output_text[position].isspace():
            position += 1
        if position >= len(output_text) or output_text[position] == "]":
            break
        try:
            value, position = decoder.raw_decode(output_text, position)
        except ValueError:
            break
        elements.append(value)
        while position < len(output_text) and output_text[position].isspace():
            position += 1
        if position >= len(output_text) or output_text[position] == "]":
            break
        if output_text[position] != ",":
            break
        position += 1
    return elements


def _bounded_text(value: Any, maximum: int) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= maximum and bool(value.strip())


def _proposal(raw: Any) -> ProposedObservation | None:
    if not isinstance(raw, dict):
        return None
    category = raw.get("category")
    if category not in CATEGORIES:
        return None
    normative = category in NORMATIVE_CATEGORIES
    if set(raw) != (_BASE_KEYS | _NORM_KEYS if normative else _BASE_KEYS):
        return None
    if (raw["proposed_severity"] not in SEVERITIES
            or not _bounded_text(raw["finding_text"], 4000)
            or not _bounded_text(raw["recommendation_text"], 4000)):
        return None
    evidence_raw = raw["evidence"]
    if not isinstance(evidence_raw, list) or not evidence_raw:
        return None
    evidence: list[ProposedEvidence] = []
    for item in evidence_raw:
        if not isinstance(item, dict) or set(item) != {"page_number", "quote"}:
            return None
        page = item["page_number"]
        if type(page) is not int or page < 1 or not _bounded_text(item["quote"], 2000):
            return None
        evidence.append(ProposedEvidence(page, item["quote"]))
    citations: tuple[ProposedNormCitation, ...] | None = None
    required_value: str | None = None
    stated_value: str | None = None
    if normative:
        raw_citations = raw["norm_citations"]
        if not isinstance(raw_citations, list) or not 1 <= len(raw_citations) <= 5:
            return None
        parsed_citations: list[ProposedNormCitation] = []
        for item in raw_citations:
            if not isinstance(item, dict) or set(item) != {"label", "quote"}:
                return None
            label, quote = item["label"], item["quote"]
            if (not isinstance(label, str) or _LABEL.fullmatch(label) is None
                    or not _bounded_text(quote, 1000) or len(quote) < 20):
                return None
            parsed_citations.append(ProposedNormCitation(label, quote))
        required_value = raw["required_value"]
        stated_value = raw["stated_value"]
        if (not _bounded_text(required_value, 200)
                or not _bounded_text(stated_value, 200)):
            return None
        citations = tuple(parsed_citations)
    else:
        assert category in NONNORMATIVE_CATEGORIES
    return ProposedObservation(
        category=category,
        finding_text=raw["finding_text"],
        recommendation_text=raw["recommendation_text"],
        proposed_severity=raw["proposed_severity"],
        evidence=tuple(evidence),
        norm_citations=citations,
        required_value=required_value,
        stated_value=stated_value,
    )


def parse_response(output_text: str, *, truncated: bool) -> ParsedResponse:
    """Drop malformed proposals; never infer a missing field from nearby JSON."""
    if not isinstance(output_text, str) or type(truncated) is not bool:
        raise V3ResponseError("invalid_response_input")
    try:
        document = json.loads(output_text, object_pairs_hook=_unique_object)
    except ValueError:
        if not truncated:
            raise V3ResponseError("malformed_untruncated_response") from None
        raw_items = _complete_array_elements(output_text)
        salvaged = True
    else:
        if not isinstance(document, dict) or set(document) != {"observations"}:
            raise V3ResponseError("invalid_response_envelope")
        raw_items = document["observations"]
        if not isinstance(raw_items, list):
            raise V3ResponseError("invalid_response_envelope")
        salvaged = truncated
    observations: list[ProposedObservation] = []
    malformed_count = 0
    for item in raw_items:
        proposal = _proposal(item)
        if proposal is None:
            malformed_count += 1
        else:
            observations.append(proposal)
    return ParsedResponse(tuple(observations), salvaged, malformed_count)
