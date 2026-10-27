"""A same-document omission that code can check: the pair of places and the absence of a term.

`SECTION-CATEGORY-OCR-01` (`R-146ao`). Lane G1 refused the omission topic («named on a scheme, absent from
the specification») because **an absence has no quote**: the grounding gate checks that every quote exists,
so it would have published «X does not exist» as grounded without being able to check it. The owner allowed
the existing category ``documentation`` for it. This module is the honest anchor.

What the product publishes is not «the item does not exist» (code cannot know that) but «this term is named
here and does not occur, letter for letter, in the saved text of these pages». The second half is a fact about
the saved text layer, and :func:`decide` checks it, without the model, after the existing path has resolved the
quotes of the place that **names** the item and of the **heading** of the range where it should appear:

* the claim is well formed (term of 3 to 60 characters and at most five words after folding, pages inside the
  document, ``first_page <= last_page``);
* in a windowed run the range lies inside the window that produced the proposal (the model only claims about
  pages it was shown);
* the heading lies inside the range;
* every quote resolved (all-or-nothing: a pair with one place missing is not a pair);
* the term occurs in a naming quote (the naming place really names it);
* every page of the range has usable text (a scan proves nothing about absence);
* the term does **not** occur in the text of the range. «Occurs» is deliberately wide so that a refusal errs
  towards dropping: see :func:`fold` and :func:`occurs`.

A proposal that passes is published as ``documentation`` with the naming quote(s) and the heading quote as its
evidence (a pair of places; every item an ordinary resolved anchor, so the unchanged gate accepts it) and a
sentence the stage appends to the model's text saying exactly what code verified. A proposal that fails is not
written; the reason is counted (:class:`OmissionTally`) in a closed vocabulary. Nothing here knows whether the
item is meant to be in the schedule, whether the schedule lists it under another name, or what a drawing shows:
that is the expert's call, as for every finding.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Final, Sequence

from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.prompt import OMISSION_CATEGORY
from auditmanager.analysis.text.response import ProposedEvidence, ProposedObservation
from auditmanager.analysis.text.textlayer import TextLayer

#: Restated from ``auditmanager.ingest.envelope.TEXTLESS_PAGE_CHARACTERS`` (``analysis`` does not import
#: ``ingest``; ``tests/unit/analysis/test_omission_check.py`` holds the two equal). A range page with fewer
#: non-blank characters than this has no usable text: the absence of a term from it means nothing.
USABLE_PAGE_CHARACTERS: Final[int] = 50
TERM_MIN_CHARACTERS: Final[int] = 3
TERM_MAX_CHARACTERS: Final[int] = 60
TERM_MAX_WORDS: Final[int] = 5

REASON_CLAIM_INVALID: Final[str] = "claim_invalid"
REASON_RANGE_OUTSIDE_WINDOW: Final[str] = "range_outside_window"
REASON_HEADING_OUTSIDE_RANGE: Final[str] = "heading_outside_range"
REASON_EVIDENCE_UNRESOLVED: Final[str] = "evidence_unresolved"
REASON_TERM_NOT_IN_NAMING_QUOTE: Final[str] = "term_not_in_naming_quote"
REASON_RANGE_PAGE_WITHOUT_TEXT: Final[str] = "range_page_without_text"
REASON_TERM_PRESENT_IN_RANGE: Final[str] = "term_present_in_range"

#: The closed vocabulary, in the order the checks run. Each is a stage metric ``omissions_dropped_<reason>``.
OMISSION_REASONS: Final[tuple[str, ...]] = (
    REASON_CLAIM_INVALID,
    REASON_RANGE_OUTSIDE_WINDOW,
    REASON_HEADING_OUTSIDE_RANGE,
    REASON_EVIDENCE_UNRESOLVED,
    REASON_TERM_NOT_IN_NAMING_QUOTE,
    REASON_RANGE_PAGE_WITHOUT_TEXT,
    REASON_TERM_PRESENT_IN_RANGE,
)

_DASHES: Final[str] = "‐‑‒–—―−­"
_DASH_TABLE: Final[dict[int, str | None]] = {
    **{ord(ch): "-" for ch in _DASHES if ch != "­"},
    ord("­"): None,  # a soft hyphen is nothing
}
_SPACE = re.compile(r"\s+")
_HYPHENATION = re.compile(r"(?<=\w)-\s+(?=\w)")
_LOOSE = re.compile(r"[\s\-]+")


def fold(text: str) -> str:
    """The text as the absence check compares it.

    Unicode compatibility forms (non-breaking space, ligatures, full-width forms), case folded,
    ``ё`` read as ``е``, every dash one hyphen, soft hyphens removed, runs of whitespace one space.
    Folding only ever makes two strings more alike, so it can only turn a would-be absence into a
    presence, never the reverse.
    """
    folded = unicodedata.normalize("NFKC", text).translate(_DASH_TABLE).casefold().replace("ё", "е")
    return _SPACE.sub(" ", folded).strip()


def _dehyphenated(folded: str) -> str:
    """A line-break hyphenation joined: ``светиль- ник`` reads as ``светильник``."""
    return _HYPHENATION.sub("", folded)


def _loose(folded: str) -> str:
    """Spaces and hyphens removed: ``Г - 3``, ``Г-3`` and ``Г3`` are one string."""
    return _LOOSE.sub("", folded)


def occurs(term: str, texts: Sequence[str]) -> bool:
    """Whether ``term`` occurs in any of ``texts`` in any of the ways a record can hide.

    Three views of both sides are tried (the folded text, the text with hyphenation joined, and the text
    with spaces and hyphens removed), and the texts are tried one by one, joined with a space and joined
    with nothing (a name broken across a page break). A hit in any is a presence.
    """
    wanted = fold(term)
    if not wanted:
        return False
    pages = [fold(text) for text in texts]
    haystacks = [*pages, " ".join(pages), "".join(pages)]
    for transform in (str, _dehyphenated, _loose):
        needle = transform(wanted)
        if needle and any(needle in transform(haystack) for haystack in haystacks):
            return True
    return False


def quotes_of(proposal: ProposedObservation) -> tuple[ProposedEvidence, ...]:
    """The quotes an omission proposal asks the stage to resolve: the naming place(s), then the heading."""
    if proposal.omission is None:
        raise ValueError("not an omission proposal")
    return (*proposal.evidence, proposal.omission.heading)


@dataclass(frozen=True, slots=True)
class OmissionOutcome:
    """Published (``evidence`` and ``finding_text`` set) or dropped (``reason`` set). Never both."""

    reason: str | None
    evidence: tuple[ResolvedAnchor, ...] = ()
    finding_text: str = ""

    @property
    def published(self) -> bool:
        return self.reason is None


def note_for(term: str, first_page: int, last_page: int) -> str:
    """The sentence the stage appends: what code verified and, in the same breath, what it did not."""
    where = f"на странице {first_page}" if first_page == last_page else f"на страницах {first_page}–{last_page}"
    return (
        f"Проверка программой: запись «{term}» не найдена в текстовом слое {where} "
        "(буквальное совпадение без учёта регистра); другие написания не проверялись."
    )


def decide(
    text_layer: TextLayer,
    proposal: ProposedObservation,
    anchors: Sequence[ResolvedAnchor | UnresolvedAnchor],
    visible: tuple[int, int] | None,
) -> OmissionOutcome:
    """Check an omission proposal against the saved text layer. Pure; the model is not consulted.

    ``anchors`` are the resolutions of :func:`quotes_of` in the same order. ``visible`` is the first and last
    page the model was shown (``None``: the whole document).
    """
    claim = proposal.omission
    if claim is None or proposal.category != OMISSION_CATEGORY:
        raise ValueError("not an omission proposal")
    quotes = quotes_of(proposal)
    if len(anchors) != len(quotes):
        raise ValueError("one anchor per quote is required")

    wanted = fold(claim.term)
    known = set(text_layer.page_numbers)
    if (
        not TERM_MIN_CHARACTERS <= len(wanted) <= TERM_MAX_CHARACTERS
        or len(claim.term.split()) > TERM_MAX_WORDS
        or not any(ch.isalnum() for ch in wanted)
        or claim.first_page > claim.last_page
        or claim.first_page not in known
        or claim.last_page not in known
    ):
        return OmissionOutcome(REASON_CLAIM_INVALID)
    if visible is not None and not (visible[0] <= claim.first_page and claim.last_page <= visible[1]):
        return OmissionOutcome(REASON_RANGE_OUTSIDE_WINDOW)
    if not claim.first_page <= claim.heading.page_number <= claim.last_page:
        return OmissionOutcome(REASON_HEADING_OUTSIDE_RANGE)
    if not all(isinstance(anchor, ResolvedAnchor) for anchor in anchors):
        return OmissionOutcome(REASON_EVIDENCE_UNRESOLVED)
    resolved = tuple(anchor for anchor in anchors if isinstance(anchor, ResolvedAnchor))
    naming = resolved[:-1]
    if not occurs(claim.term, [anchor.quote for anchor in naming]):
        return OmissionOutcome(REASON_TERM_NOT_IN_NAMING_QUOTE)
    in_range = [
        page for page in text_layer.pages if claim.first_page <= page.page_number <= claim.last_page
    ]
    if any(len(page.text.strip()) < USABLE_PAGE_CHARACTERS for page in in_range):
        return OmissionOutcome(REASON_RANGE_PAGE_WITHOUT_TEXT)
    if occurs(claim.term, [page.text for page in in_range]):
        return OmissionOutcome(REASON_TERM_PRESENT_IN_RANGE)
    return OmissionOutcome(
        None,
        evidence=resolved,
        finding_text=f"{proposal.finding_text.rstrip()} {note_for(claim.term, claim.first_page, claim.last_page)}",
    )


@dataclass(slots=True)
class OmissionTally:
    """The omission counters of one stage run. ``enabled`` is whether the profile declares the category."""

    enabled: bool
    proposed: int = 0
    published: int = 0
    dropped: dict[str, int] = field(default_factory=dict)

    def record(self, outcome: OmissionOutcome) -> None:
        self.proposed += 1
        if outcome.reason is None:
            self.published += 1
        else:
            self.dropped[outcome.reason] = self.dropped.get(outcome.reason, 0) + 1

    def metrics(self) -> dict[str, int]:
        """Scalar stage metrics; none at all for a profile without the category (its metrics do not move)."""
        if not self.enabled:
            return {}
        out = {
            "omissions_proposed": self.proposed,
            "omissions_published": self.published,
            "omissions_dropped": sum(self.dropped.values()),
        }
        for reason in OMISSION_REASONS:
            out[f"omissions_dropped_{reason}"] = self.dropped.get(reason, 0)
        return out


__all__ = [
    "OMISSION_REASONS",
    "OmissionOutcome",
    "OmissionTally",
    "TERM_MAX_CHARACTERS",
    "TERM_MAX_WORDS",
    "TERM_MIN_CHARACTERS",
    "USABLE_PAGE_CHARACTERS",
    "decide",
    "fold",
    "note_for",
    "occurs",
    "quotes_of",
]
