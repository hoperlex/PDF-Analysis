"""«Спецификация и цены»: one document set's specification priced from the project's list.

`W60-OPT-MATCH-01`; opened to every section by `OPT-PROJECT-ALL-SECTIONS-01`. One read, in the
caller's session, composes:

1. the **document set's current version**, addressed through its project (an unknown project
   is ``not_found`` ``Project``; a set of another project, or none, ``not_found``
   ``Document``);
2. its **persisted classification** (``documents``, `W59-SECTION-SEAL-01`): the version must
   be confirmed by an expert in one of the fifteen sections -- never inferred from a file
   name, a suggestion or the set's legacy section. The section is carried on the answer and
   changes nothing in how the rows are read or priced (the extraction, the matcher and the
   price list know no section); ``section_not_ar`` is no longer produced -- the member stays
   in :data:`STATES` because the wire enum keeps it (removing a value is a breaking change);
3. the project's **current price-list revision** (the highest ``revision_number``) and all
   of its positions;
4. the version's **newest published run** and that run's verified saved
   ``prepared.text_layer`` through :class:`SavedTextReader`, a port the composition root
   implements over the runs context and the object store (as for the version comparison);
5. :func:`~auditmanager.optimisation.specification.extract_specification` and
   :func:`~auditmanager.optimisation.matching.match_specification`.

A failed precondition is an explicit :data:`STATES` value with the facts read so far --
never an empty table, never another version, section, run or price list. A port answer
that contradicts its own constraints is ``internal_error``. Nothing is written.

**Bounds.** At most :data:`~auditmanager.optimisation.specification.MAX_SPECIFICATION_ROWS`
rows per version (more is ``specification_too_large``, not a cut table); rows are served
:data:`MAX_ROW_PAGE` at a time while the counts and totals always cover every row; the
skipped-line and table listings are capped by the extractor and their counts are complete;
a price list has at most 20 000 positions (``0026``), read in pages of
:data:`_POSITION_CHUNK`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final, Protocol, runtime_checkable

from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository, DocumentVersionRecord
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdentityError, ProjectUid, RunId

from .matching import CurrencyTotal, MatchOutcome, RowMatch, match_specification
from .policy import AGGREGATE_PRICE_LIST, require_reader
from .repository import OptimisationRepository, PriceListPositionRecord, PriceListRevisionRecord
from .specification import SpecificationExtraction, extract_specification

__all__ = [
    "DEFAULT_ROW_PAGE",
    "MAX_ROW_PAGE",
    "RUN_STATE_PUBLISHED",
    "STATES",
    "STATE_ANALYSIS_MISSING",
    "STATE_PRICE_LIST_MISSING",
    "STATE_READY",
    "STATE_SECTION_NOT_AR",
    "STATE_SPECIFICATION_TOO_LARGE",
    "STATE_TEXT_UNAVAILABLE",
    "STATE_VERSION_UNCLASSIFIED",
    "RowPage",
    "RunCandidate",
    "SavedPageText",
    "SavedTextReader",
    "SpecificationPrices",
    "read_specification_prices",
]

#: The success terminal of ``audit_run`` (there is no ``succeeded`` run state).
RUN_STATE_PUBLISHED: Final[str] = "published"

STATE_READY: Final[str] = "ready"
STATE_VERSION_UNCLASSIFIED: Final[str] = "version_unclassified"
#: No longer produced by any read: a version confirmed in any section is read. The member stays
#: because the wire enum (``SpecificationPrices.state``) and the pass refusal reasons keep it.
STATE_SECTION_NOT_AR: Final[str] = "section_not_ar"
STATE_PRICE_LIST_MISSING: Final[str] = "price_list_missing"
STATE_ANALYSIS_MISSING: Final[str] = "analysis_missing"
STATE_TEXT_UNAVAILABLE: Final[str] = "text_unavailable"
STATE_SPECIFICATION_TOO_LARGE: Final[str] = "specification_too_large"
#: In the order the preconditions are checked (``section_not_ar`` is never reached any more).
STATES: Final[tuple[str, ...]] = (
    STATE_READY,
    STATE_VERSION_UNCLASSIFIED,
    STATE_SECTION_NOT_AR,
    STATE_PRICE_LIST_MISSING,
    STATE_ANALYSIS_MISSING,
    STATE_TEXT_UNAVAILABLE,
    STATE_SPECIFICATION_TOO_LARGE,
)

DEFAULT_ROW_PAGE: Final[int] = 50
MAX_ROW_PAGE: Final[int] = 200
_POSITION_CHUNK: Final[int] = 5000


@dataclass(frozen=True, slots=True)
class RunCandidate:
    run_id: str
    state: str


@dataclass(frozen=True, slots=True)
class SavedPageText:
    """The verified ``prepared.text_layer`` of one run, as page number to text."""

    run_id: str
    text_layer_sha256: str
    pages: Mapping[int, str]


@runtime_checkable
class SavedTextReader(Protocol):
    """Runs and saved page text of one version (implemented by the composition root)."""

    def runs_newest_first(self, session: Session, *, version_uid: str) -> Sequence[RunCandidate]:
        """Every run of the version, newest first."""

    def saved_page_text(
        self, session: Session, *, run_id: str, version_uid: str, page_count: int
    ) -> SavedPageText | None:
        """The run's verified text layer for every page, or ``None`` when it has none.

        A layer that exists but fails its recorded digest or shape must raise, never
        answer ``None``.
        """


@dataclass(frozen=True, slots=True)
class RowPage:
    offset: int
    limit: int
    total: int
    next_offset: int | None
    items: tuple[RowMatch, ...]


@dataclass(frozen=True, slots=True)
class SpecificationPrices:
    """The read model. Fields after ``state`` are filled as far as the preconditions held."""

    project_uid: str
    document_uid: str
    version_uid: str
    version_ordinal: int
    page_count: int
    state: str
    project_stage: str | None
    section_code: str | None
    price_list: PriceListRevisionRecord | None
    position_count: int | None
    run_id: str | None
    text_layer_sha256: str | None
    extraction: SpecificationExtraction | None
    matching: MatchOutcome | None
    rows: RowPage | None

    @property
    def totals(self) -> tuple[CurrencyTotal, ...]:
        return () if self.matching is None else self.matching.totals


def _bounded(value: object, *, field: str, minimum: int, maximum: int | None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="type")
    if value < minimum or (maximum is not None and value > maximum):
        constraint = f">= {minimum}" if maximum is None else f"{minimum}..{maximum}"
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)
    return value


def _pattern_refusal(field: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="pattern")


def _integrity(message: str) -> DomainError:
    return DomainError(ErrorCode.INTERNAL_ERROR, message=message)


def _current_version(
    session: Session, documents: DocumentRepository, project: ProjectUid, document: DocumentUid
) -> DocumentVersionRecord:
    documents.get_project(session, project)
    if documents.require_document(session, document) != project:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
    for version in documents.list_documents(session, project):
        if version.document_uid == document:
            return version
    raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")


def _positions(
    session: Session, repository: OptimisationRepository, revision: PriceListRevisionRecord
) -> tuple[PriceListPositionRecord, ...]:
    collected: list[PriceListPositionRecord] = []
    while len(collected) < revision.accepted_row_count:
        page = repository.position_page(
            session, revision.price_list_id, offset=len(collected), limit=_POSITION_CHUNK
        )
        if not page:
            break
        collected.extend(page)
    if len(collected) != revision.accepted_row_count:
        raise _integrity("the price list's stored positions disagree with its accepted row count")
    return tuple(collected)


def _newest_published(reader: SavedTextReader, session: Session, version_uid: str) -> str | None:
    runs = tuple(reader.runs_newest_first(session, version_uid=version_uid))
    for run in runs:
        if not isinstance(run, RunCandidate) or not isinstance(run.state, str):
            raise _integrity("a run candidate is malformed")
        try:
            RunId.parse(run.run_id)
        except (IdentityError, TypeError):
            raise _integrity("a run candidate is malformed") from None
    return next((run.run_id for run in runs if run.state == RUN_STATE_PUBLISHED), None)


def _checked_text(text: object, *, run_id: str, page_count: int) -> SavedPageText:
    if (
        not isinstance(text, SavedPageText)
        or text.run_id != run_id
        or not isinstance(text.text_layer_sha256, str)
        or len(text.text_layer_sha256) != 64
        or not isinstance(text.pages, Mapping)
        or set(text.pages) != set(range(1, page_count + 1))
        or any(not isinstance(value, str) for value in text.pages.values())
    ):
        raise _integrity("the saved page text does not match its run and version")
    return text


def read_specification_prices(
    session: Session,
    *,
    project_uid: str,
    document_uid: str,
    actor_roles: frozenset[str],
    reader: SavedTextReader,
    offset: int = 0,
    limit: int = DEFAULT_ROW_PAGE,
    documents: DocumentRepository | None = None,
    repository: OptimisationRepository | None = None,
) -> SpecificationPrices:
    """The specification of the set's current version, priced; or its explicit state."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_PRICE_LIST)
    try:
        project = ProjectUid.parse(project_uid)
    except (IdentityError, TypeError):
        raise _pattern_refusal("project_uid") from None
    try:
        document = DocumentUid.parse(document_uid)
    except (IdentityError, TypeError):
        raise _pattern_refusal("document_uid") from None
    start = _bounded(offset, field="offset", minimum=0, maximum=None)
    size = _bounded(limit, field="limit", minimum=1, maximum=MAX_ROW_PAGE)
    documents = documents or DocumentRepository()
    repository = repository or OptimisationRepository()

    version = _current_version(session, documents, project, document)
    classification = version.classification
    answer = SpecificationPrices(
        project_uid=str(project),
        document_uid=str(document),
        version_uid=str(version.version_uid),
        version_ordinal=version.version_ordinal,
        page_count=version.page_count,
        state=STATE_READY,
        project_stage=None if classification is None else classification.project_stage,
        section_code=None if classification is None else classification.section_code,
        price_list=None,
        position_count=None,
        run_id=None,
        text_layer_sha256=None,
        extraction=None,
        matching=None,
        rows=None,
    )
    if classification is None:
        return replace(answer, state=STATE_VERSION_UNCLASSIFIED)

    revisions = repository.list_price_lists(session, str(project))
    if not revisions:
        return replace(answer, state=STATE_PRICE_LIST_MISSING)
    current = revisions[0]
    if not current.is_current:  # pragma: no cover - the statement orders by revision
        raise _integrity("the newest price-list revision is not marked current")
    positions = _positions(session, repository, current)
    answer = replace(answer, price_list=current, position_count=len(positions))

    run_id = _newest_published(reader, session, str(version.version_uid))
    if run_id is None:
        return replace(answer, state=STATE_ANALYSIS_MISSING)
    answer = replace(answer, run_id=run_id)
    supplied = reader.saved_page_text(
        session, run_id=run_id, version_uid=str(version.version_uid), page_count=version.page_count
    )
    if supplied is None:
        return replace(answer, state=STATE_TEXT_UNAVAILABLE)
    text = _checked_text(supplied, run_id=run_id, page_count=version.page_count)
    answer = replace(answer, text_layer_sha256=text.text_layer_sha256)

    extraction = extract_specification(version_uid=str(version.version_uid), pages=text.pages)
    answer = replace(answer, extraction=extraction)
    if extraction.over_limit:
        return replace(answer, state=STATE_SPECIFICATION_TOO_LARGE)
    outcome = match_specification(extraction.rows, positions)
    total = len(outcome.matches)
    items = outcome.matches[start : start + size]
    following = start + len(items)
    page = RowPage(
        offset=start,
        limit=size,
        total=total,
        next_offset=following if following < total else None,
        items=items,
    )
    return replace(answer, matching=outcome, rows=page)
