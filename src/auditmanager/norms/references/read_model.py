"""The per-request read model of the norms a project's text cites (`NORM-REFS-RUN-01`).

Pure. Given the saved page text of one Run and the catalogue of the norms snapshot the Run
pinned, this composes the *existing* W57b chain -- :func:`extract_references`, then
:func:`resolve_references` -- and reshapes its report for a reader: each distinct cited
designation with one of five outcomes, the pages it occurs on, the norm document it was
matched to, counts, the pages that have no text layer, and the catalogue slugs the family
parser cannot read. No rule lives here: the outcomes (a newer edition wins over the same one,
an amendment is never an edition, both word orders of a federal law, at most ten retained
occurrences) are the resolver's, unchanged.

The five outcomes are the resolver's (`W57-PLAN.md` B3.3, owner answer I-6), given stable
codes for the wire: ``in_corpus``, ``newer_edition``, ``older_edition_only`` (the corpus
holds only an earlier edition than the one cited), ``not_in_corpus`` and ``not_recognised``
(the citation could not be read as a designation). Nothing here publishes a finding, assigns a
severity or calls a model; the screen it feeds is information only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from auditmanager.norms.references.resolution import (
    ABSENT,
    MAX_EVIDENCE_OCCURRENCES,
    NEWER,
    OLDER,
    OUTCOMES,
    PRESENT,
    UNPARSED,
    PinnedCatalogue,
    ReferenceRefused,
    TextPage,
    extract_references,
    resolve_references,
)
from auditmanager.norms.search.display import display_name, reader_designation

__all__ = [
    "IN_CORPUS",
    "MAX_CITATION_CHARACTERS",
    "MAX_CITED_NORMS",
    "NEWER_EDITION",
    "NOT_IN_CORPUS",
    "NOT_RECOGNISED",
    "OLDER_EDITION_ONLY",
    "OUTCOME_CODES",
    "OUTCOME_ORDER",
    "TooManyCitations",
    "CitationAnchor",
    "CitedNorm",
    "ReferenceReadModel",
    "UnrecognisedSlug",
    "build_reference_read_model",
]

IN_CORPUS: Final[str] = "in_corpus"
NEWER_EDITION: Final[str] = "newer_edition"
OLDER_EDITION_ONLY: Final[str] = "older_edition_only"
NOT_IN_CORPUS: Final[str] = "not_in_corpus"
NOT_RECOGNISED: Final[str] = "not_recognised"

#: The resolver's outcome texts mapped to wire codes. Exactly the resolver's own set.
OUTCOME_CODES: Final[Mapping[str, str]] = MappingProxyType({
    PRESENT: IN_CORPUS,
    NEWER: NEWER_EDITION,
    OLDER: OLDER_EDITION_ONLY,
    ABSENT: NOT_IN_CORPUS,
    UNPARSED: NOT_RECOGNISED,
})
#: The wire codes in the order a reader is shown them (the resolver's order).
OUTCOME_ORDER: Final[tuple[str, ...]] = tuple(OUTCOME_CODES[outcome] for outcome in OUTCOMES)
if set(OUTCOME_CODES) != set(OUTCOMES):  # pragma: no cover - import-time totality guard
    raise RuntimeError("the read model's outcome codes differ from the resolver's outcomes")

#: Most distinct cited designations one answer carries. A text citing more is refused with
#: :class:`TooManyCitations`, never cut: a real project cites tens to a few hundred norms.
MAX_CITED_NORMS: Final[int] = 1000
#: Longest cited text one answer carries. A designation is tens of characters; the extractor's
#: pattern would also match a run of hundreds of digit groups in a damaged text layer, and an
#: answer must have a bound the contract can state. Longer is :class:`TooManyCitations` too.
MAX_CITATION_CHARACTERS: Final[int] = 300

_NOT_MATCHED = frozenset({ABSENT, UNPARSED})


class TooManyCitations(ReferenceRefused):
    """The text cites more than one answer carries: too many distinct designations, or one
    cited text longer than :data:`MAX_CITATION_CHARACTERS`."""


@dataclass(frozen=True, slots=True)
class CitationAnchor:
    """One occurrence: the page, the offsets inside that page's text and the cited text."""

    page_number: int
    char_start: int
    char_end: int
    quote: str


@dataclass(frozen=True, slots=True)
class CitedNorm:
    """One distinct cited designation and what the pinned snapshot holds for it.

    ``anchors`` keeps at most :data:`MAX_EVIDENCE_OCCURRENCES` occurrences in reading order;
    ``occurrence_count`` is the true number. ``matched_*`` name the corpus document the
    outcome points at (the same, the newer or the newest earlier edition) and are ``None``
    exactly for ``not_in_corpus`` and ``not_recognised``.
    """

    cited: str
    outcome: str
    occurrence_count: int
    anchors: tuple[CitationAnchor, ...]
    matched_document_id: str | None
    matched_designation: str | None
    matched_title: str | None


@dataclass(frozen=True, slots=True)
class UnrecognisedSlug:
    """A catalogue document whose slug the family parser cannot read (never matchable)."""

    document_id: str
    slug: str
    designation: str
    title: str | None


@dataclass(frozen=True, slots=True)
class ReferenceReadModel:
    norms_snapshot_id: str
    snapshot_document_count: int
    page_count: int
    #: Pages with no text layer, ascending. A citation on such a page cannot be found.
    unread_pages: tuple[int, ...]
    #: Distinct cited designations per outcome code; every code present, zeros written.
    counts: Mapping[str, int]
    #: Occurrences of every cited designation together (not capped at ten).
    occurrence_count: int
    #: In reading order of each designation's first occurrence.
    items: tuple[CitedNorm, ...]
    #: The catalogue's own unparsed slugs, in catalogue order.
    unrecognised: tuple[UnrecognisedSlug, ...]


def _checked_pages(pages: Mapping[int, str]) -> tuple[TextPage, ...]:
    if (
        not isinstance(pages, Mapping)
        or not pages
        or any(type(number) is not int for number in pages)
        or sorted(pages) != list(range(1, len(pages) + 1))
        or any(not isinstance(value, str) for value in pages.values())
    ):
        raise ReferenceRefused("page text must be numbered 1..N with text on every page")
    # An empty page is a page with no text layer: unread, never "read and empty".
    return tuple(TextPage(str(number), pages[number] or None) for number in sorted(pages))


def build_reference_read_model(
    *, pages: Mapping[int, str], catalogue: PinnedCatalogue, pinned_snapshot_id: str
) -> ReferenceReadModel:
    """Extract, resolve and reshape. Raises :class:`ReferenceRefused` on inconsistent input.

    ``pinned_snapshot_id`` is the id the Run pins; the catalogue must be that snapshot's
    (the resolver refuses a different one, a duplicated identity, tokens that differ from
    the Python twin and an unparsed slug that is not listed).
    """
    text_pages = _checked_pages(pages)
    report = resolve_references(
        extraction=extract_references(text_pages),
        catalogue=catalogue,
        pinned_snapshot_id=pinned_snapshot_id,
    )
    slugs = {document.document_id: document.slug for document in catalogue.documents}
    if len(report.references) > MAX_CITED_NORMS:
        raise TooManyCitations("the text cites more distinct designations than one answer carries")

    items: list[CitedNorm] = []
    counts = {code: 0 for code in OUTCOME_ORDER}
    for reference in report.references:
        code = OUTCOME_CODES.get(reference.outcome)
        if code is None:
            raise ReferenceRefused("the resolver answered an unknown outcome")
        occurrences = reference.occurrences
        if len(reference.cited) > MAX_CITATION_CHARACTERS or any(
            len(occurrence.raw_text) > MAX_CITATION_CHARACTERS for occurrence in occurrences
        ):
            raise TooManyCitations("a cited text is longer than one answer carries")
        if (
            not occurrences
            or len(occurrences) > MAX_EVIDENCE_OCCURRENCES
            or reference.total_occurrences < len(occurrences)
        ):
            raise ReferenceRefused("invalid reference occurrence count")
        matched = reference.matched_document_id
        if (matched is None) != (reference.outcome in _NOT_MATCHED) or (
            matched is not None and (matched not in slugs or not reference.matched_designation)
        ):
            raise ReferenceRefused("reference match differs from its outcome")
        counts[code] += 1
        items.append(
            CitedNorm(
                cited=reference.cited,
                outcome=code,
                occurrence_count=reference.total_occurrences,
                anchors=tuple(
                    CitationAnchor(int(o.page_label), o.start, o.end, o.raw_text)
                    for o in occurrences
                ),
                matched_document_id=matched,
                matched_designation=None if matched is None else reader_designation(slugs[matched]),
                matched_title=None if matched is None else display_name(slugs[matched]).title,
            )
        )

    unparsed = set(catalogue.listed_unparsed_slugs)
    return ReferenceReadModel(
        norms_snapshot_id=catalogue.snapshot_id,
        snapshot_document_count=len(catalogue.documents),
        page_count=len(text_pages),
        unread_pages=tuple(int(label) for label in report.unread_pages),
        counts=MappingProxyType(counts),
        occurrence_count=sum(item.occurrence_count for item in items),
        items=tuple(items),
        unrecognised=tuple(
            UnrecognisedSlug(
                doc.document_id, doc.slug, reader_designation(doc.slug), display_name(doc.slug).title
            )
            for doc in catalogue.documents
            if doc.slug in unparsed
        ),
    )
