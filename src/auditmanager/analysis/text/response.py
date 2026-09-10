"""Reading the model's reply, including a reply the provider cut short.

The reply is schema-constrained JSON. When the provider stops at the output ceiling
the JSON is syntactically incomplete, and the run is *not* thrown away: complete array
elements are salvaged and the incomplete tail is discarded. That discard is the point.
An element that did not finish serializing is an element whose evidence list may be
missing its second quotation, and a half-written contradiction reads exactly like a
whole one - so it is never salvaged by patching the JSON, only by requiring each
element to parse on its own.

Nothing here interprets the prose. Categories are checked against the closed set, and
a proposal that does not satisfy the declared shape is dropped and counted rather than
repaired: this stage does not improve the model's answer, it records it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.text.prompt import CATEGORIES

_OBSERVATIONS_KEY: Final[str] = '"observations"'
_SKIPPABLE: Final[str] = " \t\r\n,"


@dataclass(frozen=True, slots=True)
class ProposedEvidence:
    """One page-and-quotation claim, before any anchor exists."""

    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class ProposedObservation:
    """One model proposal, structurally valid but not yet grounded."""

    category: str
    finding_text: str
    recommendation_text: str
    evidence: tuple[ProposedEvidence, ...]


@dataclass(frozen=True, slots=True)
class ParsedResponse:
    """What could be read out of the reply, and what could not."""

    observations: tuple[ProposedObservation, ...]
    salvaged: bool
    malformed_count: int


def _salvage_array(text: str) -> list[Any]:
    """Read as many complete elements of the observations array as the text holds."""
    key_at = text.find(_OBSERVATIONS_KEY)
    if key_at < 0:
        return []
    open_at = text.find("[", key_at)
    if open_at < 0:
        return []
    decoder = json.JSONDecoder()
    items: list[Any] = []
    position = open_at + 1
    length = len(text)
    while True:
        while position < length and text[position] in _SKIPPABLE:
            position += 1
        if position >= length or text[position] == "]":
            return items
        try:
            element, position = decoder.raw_decode(text, position)
        except ValueError:
            return items  # the tail did not finish; it is not guessed at
        items.append(element)


def _coerce(raw: Any) -> ProposedObservation | None:
    """One proposal, or ``None`` when it does not satisfy the declared shape."""
    if not isinstance(raw, dict):
        return None
    category = raw.get("category")
    finding = raw.get("finding_text")
    recommendation = raw.get("recommendation_text")
    evidence_raw = raw.get("evidence")
    if category not in CATEGORIES:
        return None
    if not isinstance(finding, str) or not finding.strip():
        return None
    if not isinstance(recommendation, str) or not recommendation.strip():
        return None
    if not isinstance(evidence_raw, list) or not evidence_raw:
        # Section 4.7: an observation with no evidence is malformed, not "ungrounded".
        return None
    evidence: list[ProposedEvidence] = []
    for item in evidence_raw:
        if not isinstance(item, dict):
            return None
        page = item.get("page_number")
        quote = item.get("quote")
        if not isinstance(page, int) or isinstance(page, bool):
            return None
        if not isinstance(quote, str) or not quote:
            return None
        evidence.append(ProposedEvidence(page_number=page, quote=quote))
    return ProposedObservation(
        category=category,
        finding_text=finding,
        recommendation_text=recommendation,
        evidence=tuple(evidence),
    )


def parse_response(output_text: str, *, truncated: bool) -> ParsedResponse:
    """Read the reply. ``truncated`` says the provider stopped at the output ceiling."""
    raw_items: list[Any]
    salvaged: bool
    try:
        document = json.loads(output_text)
    except ValueError:
        raw_items = _salvage_array(output_text)
        salvaged = True
    else:
        if isinstance(document, dict) and isinstance(document.get("observations"), list):
            raw_items = document["observations"]
            # A reply can be complete JSON and still have been cut short in the sense
            # that matters, so the provider's own stop reason is authoritative here.
            salvaged = truncated
        else:
            raw_items = _salvage_array(output_text)
            salvaged = True

    observations: list[ProposedObservation] = []
    malformed = 0
    for raw in raw_items:
        coerced = _coerce(raw)
        if coerced is None:
            malformed += 1
        else:
            observations.append(coerced)
    return ParsedResponse(
        observations=tuple(observations), salvaged=salvaged, malformed_count=malformed
    )
