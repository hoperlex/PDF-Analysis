"""Pure W57b extraction and five-outcome pinned-catalogue resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass

from auditmanager.norms.embedding.profile import require_snapshot_id
from auditmanager.norms.references.families import Designation, detection_shadow, parse_designation
from auditmanager.norms.references.tokens import sql_designation_tokens


RULE_ID = "normative_refs.newer_edition/1"
NEWER_TEMPLATE = "Проект ссылается на {cited}; в корпусе есть более новая редакция: {newest}"
PRESENT = "есть в корпусе"
NEWER = "в корпусе есть более новая редакция"
OLDER = "в корпусе только более ранняя редакция"
ABSENT = "нет в корпусе"
UNPARSED = "не сопоставлено"
MAX_EVIDENCE_OCCURRENCES = 10

_STANDARD = r"(?:гост(?:[ _]+р)?|сп|снип|санпин|всн)[ _]+\d+(?:[._-]\d+)*"
_AMENDMENT = rf"изменени[ея][ _]*(?:n|№)[ _]*\d+[ _]*к[ _]*{_STANDARD}"
_LAW_FULL = r"федеральный[ _]+закон[ _]*(?:№|n)[ _]*\d+[ _-]*фз"
_LAW_SHORT = r"(?:\d+[ _-]*фз|фз[ _-]*\d+)"
_ACT = r"(?:пп[ _]+рф|постановление[ _]+правительства[ _]+рф)[ _]*(?:№|n)[ _]*\d+"
_CANDIDATE = re.compile(
    rf"(?<![а-яёa-z0-9])(?:{_AMENDMENT}|{_LAW_FULL}|{_ACT}|{_STANDARD}|{_LAW_SHORT})(?![а-яёa-z0-9])"
)


class ReferenceRefused(ValueError):
    """The supplied page or pinned-catalogue evidence is inconsistent."""


@dataclass(frozen=True, slots=True)
class TextPage:
    page_label: str
    text: str | None


@dataclass(frozen=True, slots=True)
class Occurrence:
    page_label: str
    start: int
    end: int
    raw_text: str


@dataclass(frozen=True, slots=True)
class Extraction:
    occurrences: tuple[Occurrence, ...]
    unread_pages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    document_id: str
    slug: str
    designation_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PinnedCatalogue:
    snapshot_id: str
    documents: tuple[CatalogueEntry, ...]
    listed_unparsed_slugs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    cited: str
    outcome: str
    occurrences: tuple[Occurrence, ...]
    total_occurrences: int
    matched_document_id: str | None
    matched_designation: str | None
    observation_text: str | None


@dataclass(frozen=True, slots=True)
class ReferenceReport:
    references: tuple[ResolvedReference, ...]
    unread_pages: tuple[str, ...]


def extract_references(pages: tuple[TextPage, ...]) -> Extraction:
    """Find every candidate span on pages with a text layer; retain raw offsets."""
    seen_pages: set[str] = set()
    occurrences: list[Occurrence] = []
    unread: list[str] = []
    for page in pages:
        if not isinstance(page.page_label, str) or not page.page_label or page.page_label in seen_pages:
            raise ReferenceRefused("duplicate or invalid page label")
        seen_pages.add(page.page_label)
        if page.text is None:
            unread.append(page.page_label)
            continue
        if not isinstance(page.text, str):
            raise ReferenceRefused("page text must be text or absent")
        shadow = detection_shadow(page.text)
        if len(shadow) != len(page.text):
            raise ReferenceRefused("designation normalization changed offsets")
        for match in _CANDIDATE.finditer(shadow):
            occurrences.append(
                Occurrence(page.page_label, match.start(), match.end(), page.text[match.start():match.end()])
            )
    return Extraction(tuple(occurrences), tuple(unread))


def _catalogue_index(catalogue: PinnedCatalogue) -> dict[tuple[str, tuple[str, ...]], list[tuple[Designation, CatalogueEntry]]]:
    ids: set[str] = set()
    slugs: set[str] = set()
    listed = set(catalogue.listed_unparsed_slugs)
    if len(listed) != len(catalogue.listed_unparsed_slugs):
        raise ReferenceRefused("duplicate listed unparsed slug")
    index: dict[tuple[str, tuple[str, ...]], list[tuple[Designation, CatalogueEntry]]] = {}
    for doc in catalogue.documents:
        if not doc.document_id.startswith("ndoc_") or doc.document_id in ids or not doc.slug or doc.slug in slugs:
            raise ReferenceRefused("duplicate or invalid catalogue identity")
        ids.add(doc.document_id)
        slugs.add(doc.slug)
        if doc.designation_tokens != sql_designation_tokens(doc.slug):
            raise ReferenceRefused("catalogue SQL designation tokens mismatch")
        parsed = parse_designation(doc.slug)
        if parsed is None:
            if doc.slug not in listed:
                raise ReferenceRefused("unlisted unparsed catalogue slug")
            continue
        if doc.slug in listed:
            raise ReferenceRefused("stale unparsed catalogue listing")
        index.setdefault(parsed.family_base, []).append((parsed, doc))
    if listed - slugs:
        raise ReferenceRefused("unparsed listing names absent catalogue slug")
    return index


def _group_key(occurrence: Occurrence) -> tuple[object, ...]:
    parsed = parse_designation(occurrence.raw_text)
    return ("parsed", *parsed.cited_key) if parsed else ("unparsed", detection_shadow(occurrence.raw_text))


def _choose(
    cited: Designation, index: dict[tuple[str, tuple[str, ...]], list[tuple[Designation, CatalogueEntry]]]
) -> tuple[str, CatalogueEntry | None, Designation | None]:
    candidates = [
        (designation, doc)
        for designation, doc in index.get(cited.family_base, ())
        if designation.amendment_number is None or cited.amendment_number is not None
    ]
    if cited.amendment_number is not None:
        newer_base = [
            (designation, doc) for designation, doc in candidates
            if designation.amendment_number is None
            and designation.edition is not None
            and cited.edition is not None
            and designation.edition > cited.edition
        ]
        if newer_base:
            selected = min(newer_base, key=lambda pair: (-pair[0].edition, pair[1].document_id))
            return NEWER, selected[1], selected[0]
        exact = [
            (designation, doc) for designation, doc in candidates
            if designation.edition == cited.edition
            and designation.amendment_number == cited.amendment_number
        ]
        if not exact:
            return ABSENT, None, None
        selected = min(exact, key=lambda pair: pair[1].document_id)
        return PRESENT, selected[1], selected[0]
    candidates = [(designation, doc) for designation, doc in candidates if designation.amendment_number is None]
    if not candidates:
        return ABSENT, None, None
    if cited.edition is None:
        selected = min(candidates, key=lambda pair: pair[1].document_id)
        return PRESENT, selected[1], selected[0]
    newer = [(designation, doc) for designation, doc in candidates if designation.edition is not None and designation.edition > cited.edition]
    if newer:
        selected = min(newer, key=lambda pair: (-pair[0].edition, pair[1].document_id))
        return NEWER, selected[1], selected[0]
    same = [(designation, doc) for designation, doc in candidates if designation.edition == cited.edition]
    if same:
        selected = min(same, key=lambda pair: pair[1].document_id)
        return PRESENT, selected[1], selected[0]
    older = [(designation, doc) for designation, doc in candidates if designation.edition is not None and designation.edition < cited.edition]
    if older:
        selected = min(older, key=lambda pair: (-pair[0].edition, pair[1].document_id))
        return OLDER, selected[1], selected[0]
    return ABSENT, None, None


def resolve_references(
    *, extraction: Extraction, catalogue: PinnedCatalogue, pinned_snapshot_id: str
) -> ReferenceReport:
    """Group cited designations and resolve each against exactly one pinned catalogue."""
    try:
        require_snapshot_id(pinned_snapshot_id)
    except (TypeError, ValueError) as exc:
        raise ReferenceRefused("invalid pinned snapshot id") from exc
    if catalogue.snapshot_id != pinned_snapshot_id:
        raise ReferenceRefused("catalogue snapshot differs from pinned snapshot")
    index = _catalogue_index(catalogue)
    grouped: dict[tuple[object, ...], list[Occurrence]] = {}
    for occurrence in extraction.occurrences:
        grouped.setdefault(_group_key(occurrence), []).append(occurrence)
    resolved: list[ResolvedReference] = []
    for occurrences in grouped.values():
        cited = occurrences[0].raw_text
        parsed = parse_designation(cited)
        outcome, match, designation = (UNPARSED, None, None) if parsed is None else _choose(parsed, index)
        matched_name = designation.display if designation is not None else None
        resolved.append(
            ResolvedReference(
                cited=cited,
                outcome=outcome,
                occurrences=tuple(occurrences[:MAX_EVIDENCE_OCCURRENCES]),
                total_occurrences=len(occurrences),
                matched_document_id=match.document_id if match is not None else None,
                matched_designation=matched_name,
                observation_text=NEWER_TEMPLATE.format(cited=cited, newest=matched_name) if outcome == NEWER else None,
            )
        )
    return ReferenceReport(tuple(resolved), extraction.unread_pages)
