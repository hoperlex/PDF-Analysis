"""Reading the model's reply, including a reply the provider cut short.

The reply is schema-constrained JSON. When the provider stops at the output ceiling
the JSON is syntactically incomplete, and the run is *not* thrown away: complete array
elements are salvaged and the incomplete tail is discarded. That discard is the point.
An element that did not finish serializing is an element whose evidence list may be
missing its second quotation, and a half-written contradiction reads exactly like a
whole one - so it is never salvaged by patching the JSON, only by requiring each
element to parse on its own.

Nothing here interprets the prose. Categories are checked against the set the **profile**
declares (the two v1 categories unless its package says more, `SECTION-CATEGORY-OCR-01`), and a
proposal that does not satisfy the declared shape is dropped and counted rather than repaired: this
stage does not improve the model's answer, it records it.

The one extra shape is the omission claim of the category ``documentation``: an ``omission`` object
(``term``, ``first_page``, ``last_page``, ``heading``) that must be present for that category and
absent for every other. It is a claim the stage checks (:mod:`~auditmanager.analysis.text.omission`),
not something this module believes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.text.prompt import CATEGORIES, OMISSION_CATEGORY

_OBSERVATIONS_KEY: Final[str] = '"observations"'
_SKIPPABLE: Final[str] = " \t\r\n,"


@dataclass(frozen=True, slots=True)
class ProposedEvidence:
    """One page-and-quotation claim, before any anchor exists."""

    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class OmissionClaim:
    """The model's claim that a term named in the evidence is not in the text of a page range.

    ``heading`` is the quote of the heading of the schedule, specification or list that spans
    ``first_page`` to ``last_page``. Nothing here is verified yet.
    """

    term: str
    first_page: int
    last_page: int
    heading: ProposedEvidence


@dataclass(frozen=True, slots=True)
class ProposedObservation:
    """One model proposal, structurally valid but not yet grounded."""

    category: str
    finding_text: str
    recommendation_text: str
    evidence: tuple[ProposedEvidence, ...]
    #: Present exactly when ``category`` is :data:`~auditmanager.analysis.text.prompt.OMISSION_CATEGORY`.
    omission: OmissionClaim | None = None


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


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _coerce_omission(raw: Any) -> OmissionClaim | None:
    """The ``omission`` object, or ``None`` when it is not exactly the declared shape."""
    if not isinstance(raw, dict) or set(raw) != {"term", "first_page", "last_page", "heading"}:
        return None
    heading = raw["heading"]
    if (
        not isinstance(raw["term"], str)
        or not raw["term"].strip()
        or not _int(raw["first_page"])
        or not _int(raw["last_page"])
        or not isinstance(heading, dict)
        or set(heading) != {"page_number", "quote"}
        or not _int(heading["page_number"])
        or not isinstance(heading["quote"], str)
        or not heading["quote"]
    ):
        return None
    return OmissionClaim(
        term=raw["term"],
        first_page=raw["first_page"],
        last_page=raw["last_page"],
        heading=ProposedEvidence(page_number=heading["page_number"], quote=heading["quote"]),
    )


def _coerce(raw: Any, categories: tuple[str, ...]) -> ProposedObservation | None:
    """One proposal, or ``None`` when it does not satisfy the declared shape."""
    if not isinstance(raw, dict):
        return None
    category = raw.get("category")
    finding = raw.get("finding_text")
    recommendation = raw.get("recommendation_text")
    evidence_raw = raw.get("evidence")
    if category not in categories:
        return None
    omission: OmissionClaim | None = None
    if category == OMISSION_CATEGORY:
        # The category's claim is part of the proposal; without a well-formed one there is nothing to check.
        omission = _coerce_omission(raw.get("omission"))
        if omission is None:
            return None
    elif "omission" in raw:
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
        omission=omission,
    )


def parse_response(
    output_text: str, *, truncated: bool, categories: tuple[str, ...] = CATEGORIES
) -> ParsedResponse:
    """Read the reply. ``truncated`` says the provider stopped at the output ceiling.

    ``categories`` are the profile's declared categories; the default is the v1 pair, so a caller that
    names none reads what it always read. A category outside them makes the proposal malformed.
    """
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
        coerced = _coerce(raw, tuple(categories))
        if coerced is None:
            malformed += 1
        else:
            observations.append(coerced)
    return ParsedResponse(
        observations=tuple(observations), salvaged=salvaged, malformed_count=malformed
    )
