"""Pure PDF-text anchors for W57b's newer-edition rule observations.

The resolver decides the catalogue outcome. This module only converts its
page-local occurrence spans into document-global evidence offsets, without
reading a PDF, adding severity or publishing findings.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.norms.references.resolution import (
    MAX_EVIDENCE_OCCURRENCES,
    NEWER,
    NEWER_TEMPLATE,
    RULE_ID,
    ReferenceRefused,
    ReferenceReport,
)


@dataclass(frozen=True, slots=True)
class ReferencePage:
    page_label: str
    page_number: int
    char_start: int
    text: str | None


@dataclass(frozen=True, slots=True)
class RuleEvidence:
    page_number: int
    quote: str
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class NewerEditionCandidate:
    cited: str
    matched_document_id: str
    matched_designation: str
    finding_text: str
    rule_id: str
    evidence: tuple[RuleEvidence, ...]


def plan_newer_observations(
    *, report: ReferenceReport, pages: tuple[ReferencePage, ...]
) -> tuple[NewerEditionCandidate, ...]:
    """Produce one candidate per newer citation, with exact PDF text offsets.

    Page labels bind resolver occurrences to the original extraction pages;
    page numbers and starts bind them to the prepared text layer. Both must
    come from the same artifact in the future deterministic stage.
    """
    by_label: dict[str, ReferencePage] = {}
    page_numbers: set[int] = set()
    expected_start = 0
    previous_number: int | None = None
    unread: list[str] = []
    for page in pages:
        if not page.page_label or page.page_label in by_label:
            raise ReferenceRefused("duplicate or empty reference page label")
        if (
            isinstance(page.page_number, bool)
            or not isinstance(page.page_number, int)
            or page.page_number < 1
            or page.page_number in page_numbers
            or (previous_number is not None and page.page_number <= previous_number)
        ):
            raise ReferenceRefused("invalid or unordered reference page number")
        if isinstance(page.char_start, bool) or not isinstance(page.char_start, int) or page.char_start != expected_start:
            raise ReferenceRefused("reference page offsets are not contiguous")
        if page.text is None:
            unread.append(page.page_label)
        elif not isinstance(page.text, str):
            raise ReferenceRefused("reference page text must be text or absent")
        else:
            expected_start += len(page.text)
        by_label[page.page_label] = page
        page_numbers.add(page.page_number)
        previous_number = page.page_number
    if not pages or report.unread_pages != tuple(unread):
        raise ReferenceRefused("reference report unread pages differ from PDF text pages")

    candidates: list[NewerEditionCandidate] = []
    cited_seen: set[str] = set()
    for reference in report.references:
        if reference.cited in cited_seen:
            raise ReferenceRefused("duplicate resolved reference")
        cited_seen.add(reference.cited)
        if (
            not reference.occurrences
            or len(reference.occurrences) > MAX_EVIDENCE_OCCURRENCES
            or reference.total_occurrences < len(reference.occurrences)
        ):
            raise ReferenceRefused("invalid reference occurrence count")
        evidence: list[RuleEvidence] = []
        for occurrence in reference.occurrences:
            page = by_label.get(occurrence.page_label)
            if page is None or page.text is None:
                raise ReferenceRefused("reference occurrence has no readable PDF text page")
            if (
                isinstance(occurrence.start, bool)
                or isinstance(occurrence.end, bool)
                or not isinstance(occurrence.start, int)
                or not isinstance(occurrence.end, int)
                or occurrence.start < 0
                or occurrence.end <= occurrence.start
                or occurrence.end > len(page.text)
                or page.text[occurrence.start:occurrence.end] != occurrence.raw_text
            ):
                raise ReferenceRefused("reference occurrence does not match PDF text")
            if reference.outcome == NEWER:
                evidence.append(
                    RuleEvidence(
                        page_number=page.page_number,
                        quote=occurrence.raw_text,
                        char_start=page.char_start + occurrence.start,
                        char_end=page.char_start + occurrence.end,
                    )
                )
        if reference.outcome != NEWER:
            if reference.observation_text is not None:
                raise ReferenceRefused("report-only reference carries observation text")
            continue
        if (
            not reference.matched_document_id
            or not reference.matched_document_id.startswith("ndoc_")
            or not reference.matched_designation
            or reference.observation_text != NEWER_TEMPLATE.format(
                cited=reference.cited, newest=reference.matched_designation
            )
        ):
            raise ReferenceRefused("newer-edition observation has invalid catalogue provenance")
        candidates.append(
            NewerEditionCandidate(
                cited=reference.cited,
                matched_document_id=reference.matched_document_id,
                matched_designation=reference.matched_designation,
                finding_text=reference.observation_text,
                rule_id=RULE_ID,
                evidence=tuple(evidence),
            )
        )
    return tuple(candidates)
