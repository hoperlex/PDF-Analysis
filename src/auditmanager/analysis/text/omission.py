"""A same-document omission that code can check: the pair of places and the absence of a term.

`SECTION-CATEGORY-OCR-01` (`R-146ao`), hardened by `SECTION-JUDGE-FIXES-01`. Lane G1 refused the omission
topic («named on a scheme, absent from the specification») because **an absence has no quote**: the grounding
gate checks that every quote exists, so it would have published «X does not exist» as grounded without being
able to check it. The owner allowed the existing category ``documentation`` for it. This module is the honest
anchor.

What the product publishes is not «the item does not exist» (code cannot know that) but «this term is named
here and does not occur in the saved text of these pages». The second half is a fact about the saved text
layer, and :func:`decide` checks it, without the model, after the existing path has resolved the quotes of the
place that **names** the item and of the **heading** of the range where it should appear:

* the claim is well formed (term of 3 to 60 characters and at most five words after folding, pages inside the
  document, ``first_page <= last_page``);
* in a windowed run the range lies inside the window that produced the proposal (the model only claims about
  pages it was shown), and does not end on the last page of a window that is not the last one (the schedule may
  go on in a window the model never saw);
* the heading lies inside the range;
* every quote resolved (all-or-nothing: a pair with one place missing is not a pair);
* the term occurs in a naming quote (the naming place really names it);
* the finding text the model wrote does not say more than the check proves (no «нет в проекте», no
  «обязательно»: the check proves a term absent from a text layer, not an item absent from a project);
* every page of the range has usable text (a scan proves nothing about absence), by the text layer **and** by
  the version's own list of text-less pages;
* the term does **not** occur in the text of the range, **nor on any other page the model was shown** except
  the pages of the naming quote (a schedule goes on after the page the model thought was its last), **nor in
  the recognised text** of those pages. «Occurs» is deliberately wide so that a refusal errs towards
  dropping: see :func:`fold` and :func:`occurs`.

A proposal that passes is published as ``documentation`` with the naming quote(s) and the heading quote as its
evidence (a pair of places; every item an ordinary resolved anchor, so the unchanged gate accepts it) and a
sentence the stage appends to the model's text saying exactly which pages code searched (:func:`note_for`). A
proposal that fails is not written; the reason is counted (:class:`OmissionTally`) in a closed vocabulary.
Nothing here knows whether the item is meant to be in the schedule, whether the schedule lists it under another
name, or what a drawing shows: that is the expert's call, as for every finding.

**Limits of the spelling fold, said once** (the tests state the same): a mark split across table cells with the
text of other cells between the halves is not found; ``О`` (letter) and ``0`` (digit), ``З`` and ``3``, and the
Roman numerals above one are not folded (``II`` reads as ``11``, which contains ``1``: a presence, by the rule
that a refusal errs towards dropping); Greek capitals that look like Latin or Cyrillic ones are not folded
(only ``φ`` for the diameter sign); a term is a substring test, so ``Д-5`` is present in ``Д-50``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Collection, Final, Sequence

from auditmanager.analysis.text.anchors import ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.prompt import OMISSION_CATEGORY
from auditmanager.analysis.text.recognised_input import RecognisedPage
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
#: `SECTION-JUDGE-FIXES-01`: the claim ends on the last page of a window that is not the last window. The
#: schedule may go on in a window the model never saw, so «not found on pages a to b» would be true and
#: misleading; the pair is refused.
REASON_RANGE_REACHES_WINDOW_END: Final[str] = "range_reaches_window_end"
REASON_HEADING_OUTSIDE_RANGE: Final[str] = "heading_outside_range"
REASON_EVIDENCE_UNRESOLVED: Final[str] = "evidence_unresolved"
REASON_TERM_NOT_IN_NAMING_QUOTE: Final[str] = "term_not_in_naming_quote"
#: `SECTION-JUDGE-FIXES-01`: the model's sentence says the item is absent from the project or required. The
#: check proves a term absent from a text layer, not an item absent from a project.
REASON_FINDING_TEXT_OVERCLAIMS: Final[str] = "finding_text_overclaims"
#: `SECTION-JUDGE-FIXES-01`: a page of the range is in the version's own list of text-less pages.
REASON_RANGE_PAGE_TEXTLESS: Final[str] = "range_page_textless"
REASON_RANGE_PAGE_WITHOUT_TEXT: Final[str] = "range_page_without_text"
REASON_TERM_PRESENT_IN_RANGE: Final[str] = "term_present_in_range"
#: `SECTION-JUDGE-FIXES-01`: the term occurs on a page the model was shown that is neither in the range nor a
#: page of the naming quote (the schedule continues, or the term is listed elsewhere).
REASON_TERM_ON_OTHER_VISIBLE_PAGE: Final[str] = "term_on_other_visible_page"
#: `SECTION-JUDGE-FIXES-01`: the term occurs in the recognised (OCR) text of a searched page.
REASON_TERM_IN_RECOGNISED_TEXT: Final[str] = "term_in_recognised_text"

#: The closed vocabulary, in the order the checks run. Each is a stage metric ``omissions_dropped_<reason>``.
OMISSION_REASONS: Final[tuple[str, ...]] = (
    REASON_CLAIM_INVALID,
    REASON_RANGE_OUTSIDE_WINDOW,
    REASON_RANGE_REACHES_WINDOW_END,
    REASON_HEADING_OUTSIDE_RANGE,
    REASON_EVIDENCE_UNRESOLVED,
    REASON_TERM_NOT_IN_NAMING_QUOTE,
    REASON_FINDING_TEXT_OVERCLAIMS,
    REASON_RANGE_PAGE_TEXTLESS,
    REASON_RANGE_PAGE_WITHOUT_TEXT,
    REASON_TERM_PRESENT_IN_RANGE,
    REASON_TERM_ON_OTHER_VISIBLE_PAGE,
    REASON_TERM_IN_RECOGNISED_TEXT,
)

#: What the model's sentence must not say (`SECTION-JUDGE-FIXES-01`, finding 6). The prompt already tells it not
#: to; this is the check that does not rely on it. Matched on the case-folded text; a stem, so «обязательна»,
#: «обязательно» and «не обязательной» all match (a refusal errs towards dropping).
_OVERCLAIM = re.compile(r"нет\s+в\s+проекте|не\s+предусмотрен|обязательн")

#: Every dash the text layers contain, read as the hyphen. (The soft hyphen is a format character and is dropped
#: with the others, below.)
_DASHES: Final[str] = "‐‑‒–—―−"
#: Latin letters that look like Cyrillic ones, after case folding: ``ВК-1`` and ``BK-1`` are one mark.
_LOOKALIKES: Final[dict[str, str]] = {
    "a": "а", "b": "в", "c": "с", "e": "е", "h": "н", "k": "к",
    "m": "м", "o": "о", "p": "р", "t": "т", "x": "х", "y": "у",
}
#: The multiplication sign and the asterisk read as the letter in ``3х2,5``.
_TIMES: Final[str] = "×*"
#: The diameter sign and its look-alikes read as ``ф`` (``Ø20`` and ``Ф20``).
_DIAMETER: Final[str] = "ø⌀∅φϕɸ"
#: «1», the Roman numeral one and the letters that stand for it in a mark: ``ЩО-1``, ``ЩО-I``, ``ЩО-l``,
#: ``ЩО-І`` (Cyrillic) and ``ЩО-Ⅰ`` all read as ``що-1``. Decided (`SECTION-JUDGE-FIXES-01`): a mark's «1» is
#: written with an «I» or an «l» in the wild, and folding is free here, since it can only add presences. The
#: price is that every Latin ``i`` and ``l`` in the text reads as ``1``, on both sides of the comparison.
_ONE: Final[str] = "ilіӏı"
_FOLD_TABLE: Final[dict[int, str]] = {
    **{ord(ch): "-" for ch in _DASHES},
    **{ord(latin): cyrillic for latin, cyrillic in _LOOKALIKES.items()},
    **{ord(ch): "х" for ch in _TIMES},
    **{ord(ch): "ф" for ch in _DIAMETER},
    **{ord(ch): "1" for ch in _ONE},
}
_DROPPED_CATEGORIES: Final[frozenset[str]] = frozenset({"Mn", "Cf"})  # combining marks, zero-width and soft hyphen
_SPACE = re.compile(r"\s+")
_DECIMAL_COMMA = re.compile(r"(?<=\d),(?=\d)")
_HYPHENATION = re.compile(r"(?<=\w)-\s+(?=\w)")
#: Whitespace and the separators of a mark (hyphen, point, comma, slash, underscore, bar, middle dot): the
#: loosest view, in which ``Г-3``, ``Г.3``, ``Г 3``, ``Г/3`` and a mark broken over two table cells are one string.
_LOOSE = re.compile(r"[\s\-.,/_|·]+")


def fold(text: str) -> str:
    """The text as the absence check compares it.

    Case folded; Unicode compatibility forms (non-breaking space, ligatures, full-width forms, superscripts,
    Roman numeral signs) decomposed; combining marks, zero-width and soft hyphens dropped (so ``ё`` reads as
    ``е`` and ``й`` as ``и``); every dash one hyphen; Latin letters that look like Cyrillic ones written as the
    Cyrillic letter; the multiplication sign and ``*`` as ``х``; the diameter sign as ``ф``; the Latin ``i`` and
    ``l`` and their Cyrillic look-alikes as ``1``; the decimal comma between digits as a point; runs of
    whitespace one space. Folding only ever makes two strings more alike, so it can only turn a would-be
    absence into a presence, never the reverse.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    kept = "".join(ch for ch in decomposed if unicodedata.category(ch) not in _DROPPED_CATEGORIES)
    translated = kept.translate(_FOLD_TABLE)
    return _SPACE.sub(" ", _DECIMAL_COMMA.sub(".", translated)).strip()


def _dehyphenated(folded: str) -> str:
    """A line-break hyphenation joined: ``светиль- ник`` reads as ``светильник``."""
    return _HYPHENATION.sub("", folded)


def _loose(folded: str) -> str:
    """Spaces and the separators of a mark removed: ``Г - 3``, ``Г-3``, ``Г.3`` and ``Г3`` are one string."""
    return _LOOSE.sub("", folded)


def occurs(term: str, texts: Sequence[str]) -> bool:
    """Whether ``term`` occurs in any of ``texts`` in any of the ways a record can hide.

    Three views of both sides are tried (the folded text, the text with hyphenation joined, and the text
    with spaces and the separators of a mark removed), and the texts are tried one by one, joined with a
    space and joined with nothing (a name broken across a page break). A hit in any is a presence.
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


def _pages_phrase(pages: Sequence[int]) -> str:
    """``2, 4–6, 9``: sorted, runs of consecutive pages as a range."""
    ordered = sorted(set(pages))
    parts: list[str] = []
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1] == ordered[end] + 1:
            end += 1
        parts.append(str(ordered[index]) if end == index else f"{ordered[index]}–{ordered[end]}")
        index = end + 1
    return ", ".join(parts)


def _pages_word(pages: Sequence[int], one: str, many: str) -> str:
    return f"{one if len(set(pages)) == 1 else many} {_pages_phrase(pages)}"


def note_for(
    term: str,
    first_page: int,
    last_page: int,
    *,
    others: Sequence[int] = (),
    naming_pages: Sequence[int] = (),
    recognised_pages: Sequence[int] = (),
) -> str:
    """The sentence the stage appends: exactly which pages code searched and, in the same breath, what it did not.

    ``first_page``..``last_page`` is the range the model claimed; ``others`` are the other pages the model was
    shown that were searched as well (everything it saw except the range and the pages of the naming quote);
    ``naming_pages`` are the pages of the naming quote, which are not searched; ``recognised_pages`` are the
    searched pages whose recognised (OCR) text was searched too (`SECTION-JUDGE-FIXES-01`).
    """
    where = f"на странице {first_page}" if first_page == last_page else f"на страницах {first_page}–{last_page}"
    parts = [f"Проверка программой: запись «{term}» не найдена в текстовом слое {where}"]
    if others:
        parts[0] += (
            f" и на остальных {_pages_word(others, 'странице', 'страницах')}, которые видела модель "
            f"(кроме {_pages_word(naming_pages, 'страницы', 'страниц')}, где запись названа)"
        )
    if recognised_pages:
        parts.append(
            f"распознанный текст {_pages_word(recognised_pages, 'страницы', 'страниц')} тоже проверен"
        )
    parts.append("сравнение без учёта регистра, тире, пробелов и сходных по начертанию букв")
    parts.append("другие написания не проверялись.")
    return "; ".join(parts)


def decide(
    text_layer: TextLayer,
    proposal: ProposedObservation,
    anchors: Sequence[ResolvedAnchor | UnresolvedAnchor],
    visible: tuple[int, int] | None,
    *,
    textless_pages: Collection[int] | None = None,
    recognised: Sequence[RecognisedPage] = (),
) -> OmissionOutcome:
    """Check an omission proposal against the saved text layer. Pure; the model is not consulted.

    ``anchors`` are the resolutions of :func:`quotes_of` in the same order. ``visible`` is the first and last
    page the model was shown (``None``: the whole document). ``textless_pages`` is the version's own list of
    text-less pages (``None``: not known, only the text layer's own count of a page's characters applies) and
    ``recognised`` the recognised (OCR) text of those pages (`SECTION-JUDGE-FIXES-01`).

    The absence is proved over **every page the model was shown** except the pages of the naming quote, not
    only over the range it chose. A window that is not the last one is never trusted to its last page.
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
    if visible is not None:
        if not (visible[0] <= claim.first_page and claim.last_page <= visible[1]):
            return OmissionOutcome(REASON_RANGE_OUTSIDE_WINDOW)
        if claim.last_page == visible[1] and visible[1] < max(known):
            return OmissionOutcome(REASON_RANGE_REACHES_WINDOW_END)
    if not claim.first_page <= claim.heading.page_number <= claim.last_page:
        return OmissionOutcome(REASON_HEADING_OUTSIDE_RANGE)
    if not all(isinstance(anchor, ResolvedAnchor) for anchor in anchors):
        return OmissionOutcome(REASON_EVIDENCE_UNRESOLVED)
    resolved = tuple(anchor for anchor in anchors if isinstance(anchor, ResolvedAnchor))
    naming = resolved[:-1]
    if not occurs(claim.term, [anchor.quote for anchor in naming]):
        return OmissionOutcome(REASON_TERM_NOT_IN_NAMING_QUOTE)
    if _OVERCLAIM.search(proposal.finding_text.casefold()):
        return OmissionOutcome(REASON_FINDING_TEXT_OVERCLAIMS)

    first, last = claim.first_page, claim.last_page
    in_range = [page for page in text_layer.pages if first <= page.page_number <= last]
    if textless_pages is not None and any(page.page_number in textless_pages for page in in_range):
        return OmissionOutcome(REASON_RANGE_PAGE_TEXTLESS)
    if any(len(page.text.strip()) < USABLE_PAGE_CHARACTERS for page in in_range):
        return OmissionOutcome(REASON_RANGE_PAGE_WITHOUT_TEXT)
    if occurs(claim.term, [page.text for page in in_range]):
        return OmissionOutcome(REASON_TERM_PRESENT_IN_RANGE)

    naming_pages = {anchor.page_number for anchor in naming}
    shown = [
        page
        for page in text_layer.pages
        if visible is None or visible[0] <= page.page_number <= visible[1]
    ]
    searched = [page for page in shown if page.page_number not in naming_pages]
    others = tuple(page.page_number for page in searched if not first <= page.page_number <= last)
    # The searched pages in order, the range among them: a term broken between the range and the page after
    # it (a schedule that goes on) is found as well.
    if occurs(claim.term, [page.text for page in searched]):
        return OmissionOutcome(REASON_TERM_ON_OTHER_VISIBLE_PAGE)
    searched_numbers = {page.page_number for page in searched}
    scans = [page for page in recognised if page.page_number in searched_numbers]
    if occurs(claim.term, [page.text for page in scans]):
        return OmissionOutcome(REASON_TERM_IN_RECOGNISED_TEXT)
    return OmissionOutcome(
        None,
        evidence=resolved,
        finding_text=(
            f"{proposal.finding_text.rstrip()} "
            f"{note_for(claim.term, first, last, others=others, naming_pages=tuple(sorted(naming_pages)), recognised_pages=tuple(page.page_number for page in scans))}"
        ),
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
