"""Parse AR v2 model proposals without grounding or publishing them.

An incomplete trailing element is never repaired: it may lack one side of a
contradiction or its evidence. Salvage is permitted only when the caller has
the provider's explicit truncation signal.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES, SEVERITIES


class V2ResponseError(ValueError):
    """A response could not be interpreted as the declared v2 envelope."""


@dataclass(frozen=True, slots=True)
class ProposedEvidence:
    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class ProposedObservation:
    category: str
    finding_text: str
    recommendation_text: str
    proposed_severity: str
    evidence: tuple[ProposedEvidence, ...]


@dataclass(frozen=True, slots=True)
class ParsedResponse:
    observations: tuple[ProposedObservation, ...]
    salvaged: bool
    malformed_count: int


_PREFIX: Final[re.Pattern[str]] = re.compile(r'\A\s*\{\s*"observations"\s*:\s*\[')
_OBS_KEYS: Final[frozenset[str]] = frozenset({
    "category", "finding_text", "recommendation_text", "proposed_severity", "evidence"
})
_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset({"page_number", "quote"})


def _complete_array_elements(text: str) -> list[Any]:
    """Read only independently complete elements at the start of a cut array."""
    match = _PREFIX.match(text)
    if match is None:
        return []
    decoder = json.JSONDecoder()
    position = match.end()
    elements: list[Any] = []
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text) or text[position] == "]":
            break
        try:
            value, position = decoder.raw_decode(text, position)
        except ValueError:
            break
        elements.append(value)
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text) or text[position] == "]":
            break
        if text[position] != ",":
            break
        position += 1
    return elements


def _proposal(raw: Any) -> ProposedObservation | None:
    if not isinstance(raw, dict) or set(raw) != _OBS_KEYS:
        return None
    category = raw["category"]
    severity = raw["proposed_severity"]
    finding = raw["finding_text"]
    recommendation = raw["recommendation_text"]
    evidence_raw = raw["evidence"]
    if category not in CATEGORIES or severity not in SEVERITIES:
        return None
    if not isinstance(finding, str) or not 1 <= len(finding) <= 4000 or not finding.strip():
        return None
    if (not isinstance(recommendation, str) or
            not 1 <= len(recommendation) <= 4000 or not recommendation.strip()):
        return None
    if not isinstance(evidence_raw, list) or not evidence_raw:
        return None
    evidence: list[ProposedEvidence] = []
    for item in evidence_raw:
        if not isinstance(item, dict) or set(item) != _EVIDENCE_KEYS:
            return None
        page, quote = item["page_number"], item["quote"]
        if type(page) is not int or page < 1:
            return None
        if not isinstance(quote, str) or not quote.strip():
            return None
        evidence.append(ProposedEvidence(page_number=page, quote=quote))
    return ProposedObservation(
        category=category,
        finding_text=finding,
        recommendation_text=recommendation,
        proposed_severity=severity,
        evidence=tuple(evidence),
    )


def parse_response(output_text: str, *, truncated: bool) -> ParsedResponse:
    """Return valid complete proposals and a count of malformed elements.

    Grounding is separate: a structurally valid quote here may still be
    absent from the page and must be rejected before publication.
    """
    if not isinstance(output_text, str) or type(truncated) is not bool:
        raise V2ResponseError("invalid_response_input")
    try:
        document = json.loads(output_text)
    except ValueError:
        if not truncated:
            raise V2ResponseError("malformed_untruncated_response") from None
        raw_items = _complete_array_elements(output_text)
        salvaged = True
    else:
        if not isinstance(document, dict) or set(document) != {"observations"}:
            raise V2ResponseError("invalid_response_envelope")
        raw_items = document["observations"]
        if not isinstance(raw_items, list):
            raise V2ResponseError("invalid_response_envelope")
        salvaged = truncated

    accepted: list[ProposedObservation] = []
    malformed_count = 0
    for item in raw_items:
        proposal = _proposal(item)
        if proposal is None:
            malformed_count += 1
        else:
            accepted.append(proposal)
    return ParsedResponse(tuple(accepted), salvaged, malformed_count)
