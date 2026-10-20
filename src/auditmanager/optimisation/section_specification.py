"""«Оптимизация разделов»: one section's combined Form-7 specification across projects.

`W63-SECTION-FORM7-01`. One read, in the caller's session, composes for a **section code**:

1. **membership** from the documents projection (``documents.public``,
   `W59-SECTION-SEAL-01`, `SECTION-READ-MODEL-01`): every document set whose **current**
   version is confirmed by an expert in that section is a *source*. A current version
   confirmed in another section is not part of the answer at all; a current version nobody
   has classified is listed in :attr:`SectionSpecification.excluded` with its reason and
   contributes nothing. An older version's classification, a file name, a suggestion or the
   set's legacy ``section`` never makes a set a member. Members and unclassified sets are
   two keyset-paged documents queries over the whole deployment -- not one ``listDocuments``
   per project;
2. per project, its **current price-list revision** (highest ``revision_number``) and its
   positions -- or the explicit price state ``price_list_missing``;
3. per source, the version's **newest published run** and that run's verified saved
   ``prepared.text_layer`` through the same port as «Спецификация и цены»
   (:class:`~auditmanager.optimisation.project_match.SavedTextReader`) -- or the explicit
   source state ``analysis_missing`` / ``text_unavailable`` / ``specification_too_large``;
4. :func:`~auditmanager.optimisation.specification.extract_specification` over that text and
   :func:`~auditmanager.optimisation.matching.match_specification` of the rows against **the
   row's own project's** positions only.

**The section code is a filter, not an identity** (`W59-SECTION-IDENTITY-DECISION-01`): every
row is addressed by its exact project, document set, version, page, sheet and line span, and
rows are **never merged across projects** -- two projects listing the same product keep two
rows, each priced from its own project's list. **Totals exist only per project and per
currency** (:attr:`SectionProject.totals`); there is no section total and nothing is converted.
A price and an amount appear only where the matcher's money rule gave one (``matching``): a
project without a price list serves its rows with no match at all, never a figure.

**Filters.** ``project_uid`` narrows the projects, sources, exclusions and rows to one project
(an unknown project is ``not_found`` ``Project``; a known one with no member set answers an
empty section). ``query`` keeps the rows whose own Form-7 text -- position, description,
group heading, unit as printed, note -- contains it after case folding, ``ё``/``е`` and
whitespace runs are folded; it never narrows the projects, their states or their totals.

**Bounds** (documented caps; an answer over one is the explicit state
``section_too_large`` with :attr:`SectionSpecification.limit_reason`, never a cut list):

* a deployment of more than :data:`MAX_SCANNED_PROJECTS` projects is answered
  ``limit_reason: projects`` and no project is listed, unless one project is named. The bound
  was set when membership cost one documents read per project; membership is now a handful of
  paged queries, and the bound is kept as the documented cap it was (retiring it is a wire
  decision: ``projects`` is a frozen ``limit_reason`` value);
* at most :data:`MAX_SECTION_SOURCES` member sets are read (one run lookup, one text layer
  and one extraction each) -- more is ``limit_reason: sources``;
* at most :data:`MAX_SECTION_ROWS` rows in all (each version is also held to the
  extractor's :data:`~auditmanager.optimisation.specification.MAX_SPECIFICATION_ROWS`) --
  more is ``limit_reason: rows``.

  Over the sources or rows bound the membership (projects, sets, versions, exclusions) is
  still served, every source in state ``not_read`` and every price state ``not_read``, and
  no row or total: narrowing to one project is the way in.
* rows are served :data:`MAX_ROW_PAGE` at a time; counts and totals always cover every row
  in scope;
* at most :data:`MAX_LISTED_EXCLUDED` exclusions are listed, their count is complete;
* the query is at most :data:`MAX_QUERY_LENGTH` characters.

Any one role reads (`R-80`). A port answer that contradicts its own constraints is
``internal_error``. Nothing is written, nothing persisted, no LLM.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from itertools import groupby
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.documents.public import CurrentVersionPlacementRecord, DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdentityError, ProjectUid

from .matching import (
    EXCLUSION_REASONS,
    MATCH_ALGORITHM,
    STATUSES,
    CurrencyTotal,
    RowMatch,
    match_specification,
)
from .policy import parse_section_code, require_reader
from .project_match import (
    DEFAULT_ROW_PAGE,
    MAX_ROW_PAGE,
    STATE_ANALYSIS_MISSING,
    STATE_PRICE_LIST_MISSING,
    STATE_READY,
    STATE_SPECIFICATION_TOO_LARGE,
    STATE_TEXT_UNAVAILABLE,
    STATE_VERSION_UNCLASSIFIED,
    SavedTextReader,
    _checked_text,
    _newest_published,
    _positions,
)
from .repository import OptimisationRepository, PriceListPositionRecord, PriceListRevisionRecord
from .specification import EXTRACTION_ALGORITHM, SpecificationRow, extract_specification

__all__ = [
    "AGGREGATE_SECTION_SPECIFICATION",
    "DEFAULT_ROW_PAGE",
    "EXCLUSION_VERSION_UNCLASSIFIED",
    "LIMIT_PROJECTS",
    "LIMIT_REASONS",
    "LIMIT_ROWS",
    "LIMIT_SOURCES",
    "MAX_LISTED_EXCLUDED",
    "MAX_QUERY_LENGTH",
    "MAX_ROW_PAGE",
    "MAX_SCANNED_PROJECTS",
    "MAX_SECTION_ROWS",
    "MAX_SECTION_SOURCES",
    "PRICE_STATES",
    "PRICE_STATE_NOT_READ",
    "PRICE_STATE_PRICED",
    "PRICE_STATE_PRICE_LIST_MISSING",
    "ROW_PRICE_LIST_MISSING",
    "SECTION_STATES",
    "SECTION_STATE_READY",
    "SECTION_STATE_TOO_LARGE",
    "SOURCE_STATES",
    "SOURCE_STATE_ANALYSIS_MISSING",
    "SOURCE_STATE_NOT_READ",
    "SOURCE_STATE_READY",
    "SOURCE_STATE_SPECIFICATION_TOO_LARGE",
    "SOURCE_STATE_TEXT_UNAVAILABLE",
    "ExcludedVersion",
    "SectionProject",
    "SectionRow",
    "SectionRowPage",
    "SectionSource",
    "SectionSpecification",
    "read_section_specification",
]

AGGREGATE_SECTION_SPECIFICATION: Final[str] = "SectionSpecification"

SECTION_STATE_READY: Final[str] = "ready"
SECTION_STATE_TOO_LARGE: Final[str] = "section_too_large"
SECTION_STATES: Final[tuple[str, ...]] = (SECTION_STATE_READY, SECTION_STATE_TOO_LARGE)

LIMIT_PROJECTS: Final[str] = "projects"
LIMIT_SOURCES: Final[str] = "sources"
LIMIT_ROWS: Final[str] = "rows"
LIMIT_REASONS: Final[tuple[str, ...]] = (LIMIT_PROJECTS, LIMIT_SOURCES, LIMIT_ROWS)

#: A member set's state, in the order its preconditions are checked; ``not_read`` only in a
#: ``section_too_large`` answer. The spellings are «Спецификация и цены»'s own.
SOURCE_STATE_READY: Final[str] = STATE_READY
SOURCE_STATE_ANALYSIS_MISSING: Final[str] = STATE_ANALYSIS_MISSING
SOURCE_STATE_TEXT_UNAVAILABLE: Final[str] = STATE_TEXT_UNAVAILABLE
SOURCE_STATE_SPECIFICATION_TOO_LARGE: Final[str] = STATE_SPECIFICATION_TOO_LARGE
SOURCE_STATE_NOT_READ: Final[str] = "not_read"
SOURCE_STATES: Final[tuple[str, ...]] = (
    SOURCE_STATE_READY,
    SOURCE_STATE_ANALYSIS_MISSING,
    SOURCE_STATE_TEXT_UNAVAILABLE,
    SOURCE_STATE_SPECIFICATION_TOO_LARGE,
    SOURCE_STATE_NOT_READ,
)

#: A project's price state: its current revision read, none uploaded, or not read (over a bound).
PRICE_STATE_PRICED: Final[str] = "priced"
PRICE_STATE_PRICE_LIST_MISSING: Final[str] = STATE_PRICE_LIST_MISSING
PRICE_STATE_NOT_READ: Final[str] = "not_read"
PRICE_STATES: Final[tuple[str, ...]] = (
    PRICE_STATE_PRICED,
    PRICE_STATE_PRICE_LIST_MISSING,
    PRICE_STATE_NOT_READ,
)

#: Why a current version of a project is listed but contributes nothing.
EXCLUSION_VERSION_UNCLASSIFIED: Final[str] = STATE_VERSION_UNCLASSIFIED
#: A row's price status when its project has no price list (the matcher's are ``STATUSES``).
ROW_PRICE_LIST_MISSING: Final[str] = STATE_PRICE_LIST_MISSING

MAX_SCANNED_PROJECTS: Final[int] = 1000
MAX_SECTION_SOURCES: Final[int] = 20
MAX_SECTION_ROWS: Final[int] = 20_000
MAX_LISTED_EXCLUDED: Final[int] = 200
MAX_QUERY_LENGTH: Final[int] = 200

#: Placements asked of the documents projection per query. Membership is read page by page
#: (keyset on the set's identity), so no single read is unbounded; the total is not capped
#: here -- the source and row caps above are what bound the work done *with* the members.
_MEMBERSHIP_PAGE: Final[int] = 500


# --- records ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SectionSource:
    """One document set whose current version is confirmed in the section.

    ``run_id`` onwards are filled as far as the source's preconditions held; ``row_count``,
    ``table_count`` and ``skipped_by_reason`` come from the extraction (``None``/empty
    before it).
    """

    project_uid: str
    document_uid: str
    display_title: str
    version_uid: str
    version_ordinal: int
    page_count: int
    project_stage: str
    state: str
    run_id: str | None
    text_layer_sha256: str | None
    row_count: int | None
    table_count: int | None
    skipped_by_reason: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class SectionProject:
    """One project with at least one member set; its price state and its own totals.

    ``status_counts``, ``excluded_by_reason`` and ``totals`` cover the rows of this project's
    ``ready`` sources and nothing else; they are empty without a price list or over a bound.
    ``totals`` are per currency, never converted and never summed with another project's.
    """

    project_uid: str
    project_name: str
    price_state: str
    price_list: PriceListRevisionRecord | None
    position_count: int | None
    sources: tuple[SectionSource, ...]
    row_count: int
    status_counts: Mapping[str, int]
    excluded_by_reason: Mapping[str, int]
    totals: tuple[CurrencyTotal, ...]


@dataclass(frozen=True, slots=True)
class ExcludedVersion:
    """A current version listed because it cannot be placed in any section yet."""

    project_uid: str
    project_name: str
    document_uid: str
    display_title: str
    version_uid: str
    version_ordinal: int
    reason: str


@dataclass(frozen=True, slots=True)
class SectionRow:
    """One specification row with its full address; ``match`` is ``None`` without a price list."""

    project_uid: str
    document_uid: str
    version_uid: str
    row: SpecificationRow
    match: RowMatch | None

    @property
    def price_status(self) -> str:
        return ROW_PRICE_LIST_MISSING if self.match is None else self.match.status


@dataclass(frozen=True, slots=True)
class SectionRowPage:
    offset: int
    limit: int
    total: int
    next_offset: int | None
    items: tuple[SectionRow, ...]


@dataclass(frozen=True, slots=True)
class SectionSpecification:
    """The read model. ``rows`` is ``None`` exactly when the answer is ``section_too_large``.

    ``row_count`` counts every row in scope (the project filter applied, the text query
    not); ``rows.total`` counts the rows the query keeps.
    """

    section_code: str
    state: str
    limit_reason: str | None
    project_filter: str | None
    query: str | None
    extraction_algorithm: str
    match_algorithm: str
    projects: tuple[SectionProject, ...]
    excluded: tuple[ExcludedVersion, ...]
    excluded_count: int
    source_count: int
    row_count: int
    rows: SectionRowPage | None


# --- request values ---------------------------------------------------------------------


def _bounded(value: object, *, field: str, minimum: int, maximum: int | None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="type")
    if value < minimum or (maximum is not None and value > maximum):
        constraint = f">= {minimum}" if maximum is None else f"{minimum}..{maximum}"
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)
    return value


_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")


def _fold(text: str) -> str:
    """The search key: case folded, ``ё`` as ``е``, whitespace runs as one space."""
    return _WHITESPACE.sub(" ", text.casefold().replace("ё", "е")).strip()


def _query(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="query", constraint="type")
    cleaned = _WHITESPACE.sub(" ", value).strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"query is longer than {MAX_QUERY_LENGTH} characters",
            field="query",
            constraint="max_length",
        )
    return cleaned


def _project_filter(value: object) -> ProjectUid | None:
    if value is None:
        return None
    try:
        return ProjectUid.parse(value)  # type: ignore[arg-type]
    except (IdentityError, TypeError):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="project_uid", constraint="pattern"
        ) from None


def _integrity(message: str) -> DomainError:
    return DomainError(ErrorCode.INTERNAL_ERROR, message=message)


# --- membership -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Member:
    project_uid: str
    project_name: str
    versions: tuple[CurrentVersionPlacementRecord, ...]


def _title_order(version: CurrentVersionPlacementRecord) -> tuple[str, str]:
    return (version.display_title.casefold(), str(version.document_uid))


def _listing_order(version: CurrentVersionPlacementRecord) -> tuple[str, str, str, str]:
    """Projects by name (case folded) then identity, a project's sets by title then identity."""
    return (version.project_name.casefold(), str(version.project_uid), *_title_order(version))


def _walk(
    fetch: Callable[[DocumentUid | None], Sequence[CurrentVersionPlacementRecord]],
) -> Iterator[Sequence[CurrentVersionPlacementRecord]]:
    """The pages of a keyset-ordered documents query, until one is empty or short.

    A page that does not start after the key it was asked to follow would repeat the same
    rows for ever; the projection contradicting its own paging is ``internal_error``.
    """
    after: DocumentUid | None = None
    while True:
        page = fetch(after)
        if not page:
            return
        if after is not None and str(page[0].document_uid) <= str(after):
            raise _integrity("the documents projection did not advance its page")
        yield page
        if len(page) < _MEMBERSHIP_PAGE:
            return
        after = page[-1].document_uid


def _checked_member(
    item: CurrentVersionPlacementRecord, *, section: str, project: str | None
) -> CurrentVersionPlacementRecord:
    if item.section_code != section or item.project_stage is None:
        raise _integrity("a listed set is not confirmed in the requested section")
    if project is not None and str(item.project_uid) != project:
        raise _integrity("a listed current version belongs to another project")
    return item


def _checked_unclassified(
    item: CurrentVersionPlacementRecord, *, project: str | None
) -> CurrentVersionPlacementRecord:
    if item.section_code is not None or item.project_stage is not None:
        raise _integrity("a listed unclassified set carries a classification")
    if project is not None and str(item.project_uid) != project:
        raise _integrity("a listed current version belongs to another project")
    return item


def _membership(
    session: Session,
    documents: DocumentRepository,
    *,
    section: str,
    project_uid: ProjectUid | None,
) -> tuple[list[_Member], list[ExcludedVersion], int]:
    """Member sets, and the first unclassified current versions with their full count.

    Two paged documents queries over the whole deployment (or the one project named): the
    sets whose current version is confirmed in ``section``, and the sets whose current version
    is not classified at all. Both come back in the answer's order. The exclusion listing keeps
    only the first :data:`MAX_LISTED_EXCLUDED` while it counts them all, so the memory held is
    bounded however many sets are unclassified.
    """
    project = None if project_uid is None else str(project_uid)

    listed: list[CurrentVersionPlacementRecord] = []
    for page in _walk(
        lambda after: documents.list_current_versions_in_section(
            session,
            section_code=section,
            project_uid=project_uid,
            after=after,
            limit=_MEMBERSHIP_PAGE,
        )
    ):
        listed.extend(_checked_member(item, section=section, project=project) for item in page)
    members: list[_Member] = []
    for owner, items in groupby(
        sorted(listed, key=_listing_order), key=lambda item: str(item.project_uid)
    ):
        sets = tuple(items)
        members.append(_Member(owner, sets[0].project_name, sets))

    unclassified_count = 0
    first: list[CurrentVersionPlacementRecord] = []
    for page in _walk(
        lambda after: documents.list_unclassified_current_versions(
            session, project_uid=project_uid, after=after, limit=_MEMBERSHIP_PAGE
        )
    ):
        unclassified_count += len(page)
        first = sorted(
            [*first, *(_checked_unclassified(item, project=project) for item in page)],
            key=_listing_order,
        )[:MAX_LISTED_EXCLUDED]
    excluded = [
        ExcludedVersion(
            project_uid=str(item.project_uid),
            project_name=item.project_name,
            document_uid=str(item.document_uid),
            display_title=item.display_title,
            version_uid=str(item.version_uid),
            version_ordinal=item.version_ordinal,
            reason=EXCLUSION_VERSION_UNCLASSIFIED,
        )
        for item in first
    ]
    return members, excluded, unclassified_count


def _source(version: CurrentVersionPlacementRecord, state: str) -> SectionSource:
    assert version.project_stage is not None  # members are classified by construction
    return SectionSource(
        project_uid=str(version.project_uid),
        document_uid=str(version.document_uid),
        display_title=version.display_title,
        version_uid=str(version.version_uid),
        version_ordinal=version.version_ordinal,
        page_count=version.page_count,
        project_stage=version.project_stage,
        state=state,
        run_id=None,
        text_layer_sha256=None,
        row_count=None,
        table_count=None,
        skipped_by_reason={},
    )


def _unread(member: _Member) -> SectionProject:
    return SectionProject(
        project_uid=member.project_uid,
        project_name=member.project_name,
        price_state=PRICE_STATE_NOT_READ,
        price_list=None,
        position_count=None,
        sources=tuple(_source(version, SOURCE_STATE_NOT_READ) for version in member.versions),
        row_count=0,
        status_counts={},
        excluded_by_reason={},
        totals=(),
    )


# --- one project ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _ReadProject:
    project: SectionProject
    rows: tuple[SectionRow, ...]


def _read_source(
    session: Session,
    reader: SavedTextReader,
    version: CurrentVersionPlacementRecord,
    positions: tuple[PriceListPositionRecord, ...] | None,
) -> tuple[SectionSource, tuple[SectionRow, ...], tuple[RowMatch, ...]]:
    source = _source(version, SOURCE_STATE_READY)
    version_uid = str(version.version_uid)
    run_id = _newest_published(reader, session, version_uid)
    if run_id is None:
        return replace(source, state=SOURCE_STATE_ANALYSIS_MISSING), (), ()
    source = replace(source, run_id=run_id)
    supplied = reader.saved_page_text(
        session, run_id=run_id, version_uid=version_uid, page_count=version.page_count
    )
    if supplied is None:
        return replace(source, state=SOURCE_STATE_TEXT_UNAVAILABLE), (), ()
    text = _checked_text(supplied, run_id=run_id, page_count=version.page_count)
    extraction = extract_specification(version_uid=version_uid, pages=text.pages)
    source = replace(
        source,
        text_layer_sha256=text.text_layer_sha256,
        table_count=extraction.table_count,
        skipped_by_reason=dict(extraction.skipped_by_reason),
    )
    if extraction.over_limit:
        return replace(source, state=SOURCE_STATE_SPECIFICATION_TOO_LARGE), (), ()
    source = replace(source, row_count=len(extraction.rows))
    if positions is None:
        rows = tuple(
            SectionRow(source.project_uid, source.document_uid, version_uid, row, None)
            for row in extraction.rows
        )
        return source, rows, ()
    # The row's own project's positions -- never another project's list.
    outcome = match_specification(extraction.rows, positions)
    rows = tuple(
        SectionRow(source.project_uid, source.document_uid, version_uid, match.row, match)
        for match in outcome.matches
    )
    return source, rows, outcome.matches


def _project_totals(
    matches: Sequence[RowMatch],
) -> tuple[dict[str, int], dict[str, int], tuple[CurrencyTotal, ...]]:
    """One project's counts and per-currency totals over its own matches only."""
    status_counts = {status: 0 for status in STATUSES}
    excluded: dict[str, int] = {}
    sums: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    for match in matches:
        status_counts[match.status] += 1
        if match.amount is not None and match.position is not None:
            currency = match.position.currency
            sums[currency] = sums.get(currency, Decimal(0)) + match.amount
            counts[currency] = counts.get(currency, 0) + 1
        else:
            reason = match.excluded_reason
            if reason not in EXCLUSION_REASONS:
                raise _integrity("a row without an amount carries no exclusion reason")
            excluded[reason] = excluded.get(reason, 0) + 1
    ordered = {reason: excluded[reason] for reason in EXCLUSION_REASONS if reason in excluded}
    totals = tuple(
        CurrencyTotal(currency, sums[currency], counts[currency]) for currency in sorted(sums)
    )
    return status_counts, ordered, totals


def _read_project(
    session: Session,
    reader: SavedTextReader,
    repository: OptimisationRepository,
    member: _Member,
) -> _ReadProject:
    revisions = repository.list_price_lists(session, member.project_uid)
    price_list: PriceListRevisionRecord | None = None
    positions: tuple[PriceListPositionRecord, ...] | None = None
    if revisions:
        price_list = revisions[0]
        if not price_list.is_current or price_list.project_uid != member.project_uid:
            raise _integrity("the project's newest price-list revision is not its current one")
        positions = _positions(session, repository, price_list)

    sources: list[SectionSource] = []
    rows: list[SectionRow] = []
    matches: list[RowMatch] = []
    for version in member.versions:
        source, source_rows, source_matches = _read_source(session, reader, version, positions)
        sources.append(source)
        rows.extend(source_rows)
        matches.extend(source_matches)

    if positions is None:
        status_counts: Mapping[str, int] = {}
        excluded: Mapping[str, int] = {}
        totals: tuple[CurrencyTotal, ...] = ()
    else:
        status_counts, excluded, totals = _project_totals(matches)
    project = SectionProject(
        project_uid=member.project_uid,
        project_name=member.project_name,
        price_state=PRICE_STATE_PRICE_LIST_MISSING if price_list is None else PRICE_STATE_PRICED,
        price_list=price_list,
        position_count=None if positions is None else len(positions),
        sources=tuple(sources),
        row_count=len(rows),
        status_counts=status_counts,
        excluded_by_reason=excluded,
        totals=totals,
    )
    return _ReadProject(project, tuple(rows))


# --- search and paging ------------------------------------------------------------------


def _row_text(row: SpecificationRow) -> str:
    parts = (row.position, row.name, row.group, row.unit_text, row.note)
    return _fold(" ".join(part for part in parts if part))


def _page(rows: Sequence[SectionRow], *, offset: int, limit: int) -> SectionRowPage:
    items = tuple(rows[offset : offset + limit])
    following = offset + len(items)
    return SectionRowPage(
        offset=offset,
        limit=limit,
        total=len(rows),
        next_offset=following if following < len(rows) else None,
        items=items,
    )


# --- the read ---------------------------------------------------------------------------


def read_section_specification(
    session: Session,
    *,
    section_code: str,
    actor_roles: frozenset[str],
    reader: SavedTextReader,
    project_uid: str | None = None,
    query: str | None = None,
    offset: int = 0,
    limit: int = DEFAULT_ROW_PAGE,
    documents: DocumentRepository | None = None,
    repository: OptimisationRepository | None = None,
) -> SectionSpecification:
    """The section's combined specification of current versions, priced per project."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_SECTION_SPECIFICATION)
    section = parse_section_code(section_code)
    project_filter = _project_filter(project_uid)
    search = _query(query)
    start = _bounded(offset, field="offset", minimum=0, maximum=None)
    size = _bounded(limit, field="limit", minimum=1, maximum=MAX_ROW_PAGE)
    documents = documents or DocumentRepository()
    repository = repository or OptimisationRepository()

    answer = SectionSpecification(
        section_code=section,
        state=SECTION_STATE_READY,
        limit_reason=None,
        project_filter=None if project_filter is None else str(project_filter),
        query=search,
        extraction_algorithm=EXTRACTION_ALGORITHM,
        match_algorithm=MATCH_ALGORITHM,
        projects=(),
        excluded=(),
        excluded_count=0,
        source_count=0,
        row_count=0,
        rows=None,
    )

    if project_filter is not None:
        documents.get_project(session, project_filter)  # an unknown project is not_found
    elif documents.count_projects(session) > MAX_SCANNED_PROJECTS:
        return replace(answer, state=SECTION_STATE_TOO_LARGE, limit_reason=LIMIT_PROJECTS)

    members, excluded, excluded_count = _membership(
        session, documents, section=section, project_uid=project_filter
    )
    source_count = sum(len(member.versions) for member in members)
    answer = replace(
        answer,
        excluded=tuple(excluded),
        excluded_count=excluded_count,
        source_count=source_count,
    )
    unread = tuple(_unread(member) for member in members)
    if source_count > MAX_SECTION_SOURCES:
        return replace(
            answer, state=SECTION_STATE_TOO_LARGE, limit_reason=LIMIT_SOURCES, projects=unread
        )

    projects: list[SectionProject] = []
    rows: list[SectionRow] = []
    for member in members:
        read = _read_project(session, reader, repository, member)
        projects.append(read.project)
        rows.extend(read.rows)
        if len(rows) > MAX_SECTION_ROWS:
            return replace(
                answer, state=SECTION_STATE_TOO_LARGE, limit_reason=LIMIT_ROWS, projects=unread
            )

    if search is None:
        kept: Sequence[SectionRow] = rows
    else:
        needle = _fold(search)
        kept = [row for row in rows if needle in _row_text(row.row)]
    return replace(
        answer,
        projects=tuple(projects),
        row_count=len(rows),
        rows=_page(kept, offset=start, limit=size),
    )
