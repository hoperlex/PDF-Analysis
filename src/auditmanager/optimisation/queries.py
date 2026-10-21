"""The optimisation boundary's reads: price-list revisions, positions, vendor lists.

Every read takes the caller's session and the actor's role set; an account with no role is
``permission_denied`` (`R-80`). A price list that does not exist -- or that belongs to another
project than the one the caller named -- is ``not_found`` (``PriceList``): a response never
confirms a resource outside the scope it was asked in. An unknown project is ``not_found``
(``Project``).

The current price list of a project is its highest ``revision_number``; every earlier revision
stays readable. Positions are served in source-row order, one page at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, ProjectUid

from .identity import PriceListId
from .policy import (
    AGGREGATE_PRICE_LIST,
    AGGREGATE_VENDOR_LIST,
    MODE_LIST,
    SECTION_ORDER,
    effective_source,
    parse_section_code,
    require_reader,
)
from .repository import (
    OptimisationRepository,
    PriceListPositionRecord,
    PriceListRevisionRecord,
    VendorListRevisionRecord,
)

__all__ = [
    "DEFAULT_POSITION_PAGE",
    "MAX_POSITION_PAGE",
    "MAX_VENDOR_HISTORY",
    "EffectiveVendorList",
    "PositionPage",
    "get_effective_vendor_lists",
    "get_price_list_revision",
    "list_global_vendor_lists",
    "list_price_list_positions",
    "list_price_list_revisions",
    "list_vendor_list_history",
]

DEFAULT_POSITION_PAGE: Final[int] = 100
MAX_POSITION_PAGE: Final[int] = 500
MAX_VENDOR_HISTORY: Final[int] = 50


@dataclass(frozen=True, slots=True)
class PositionPage:
    """One page of a revision's positions; ``next_offset`` is ``None`` on the last page."""

    revision: PriceListRevisionRecord
    positions: tuple[PriceListPositionRecord, ...]
    offset: int
    limit: int
    total: int
    next_offset: int | None


@dataclass(frozen=True, slots=True)
class EffectiveVendorList:
    """One section's vendor list as it applies to a project.

    ``source`` names where ``effective`` comes from: the project's own list, the global one,
    or none. ``global_revision`` and ``project_revision`` are the latest of each scope (the
    project one may be an ``inherit`` revision), for showing both side by side.
    """

    section_code: str
    source: str
    effective: VendorListRevisionRecord | None
    global_revision: VendorListRevisionRecord | None
    project_revision: VendorListRevisionRecord | None


def _project(session: Session, value: str, documents: DocumentRepository) -> str:
    try:
        project = ProjectUid.parse(value)
    except IdentityError:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="project_uid", constraint="pattern"
        ) from None
    documents.get_project(session, project)
    return str(project)


def _bounded(value: int, *, field: str, minimum: int, maximum: int | None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="type")
    if value < minimum or (maximum is not None and value > maximum):
        constraint = f">= {minimum}" if maximum is None else f"{minimum}..{maximum}"
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)
    return value


def list_price_list_revisions(
    session: Session,
    *,
    project_uid: str,
    actor_roles: frozenset[str],
    documents: DocumentRepository | None = None,
    repository: OptimisationRepository | None = None,
) -> tuple[PriceListRevisionRecord, ...]:
    """Every price-list revision of a project, newest first; the first one is current."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_PRICE_LIST)
    project = _project(session, project_uid, documents or DocumentRepository())
    return (repository or OptimisationRepository()).list_price_lists(session, project)


def get_price_list_revision(
    session: Session,
    *,
    price_list_id: str,
    actor_roles: frozenset[str],
    project_uid: str | None = None,
    repository: OptimisationRepository | None = None,
) -> PriceListRevisionRecord:
    """One revision with its parse report. With ``project_uid``, another project's is unseen."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_PRICE_LIST)
    identity = PriceListId.parse(price_list_id)
    record = (repository or OptimisationRepository()).get_price_list(session, str(identity))
    if record is None or (project_uid is not None and record.project_uid != project_uid):
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_PRICE_LIST)
    return record


def list_price_list_positions(
    session: Session,
    *,
    price_list_id: str,
    actor_roles: frozenset[str],
    offset: int = 0,
    limit: int = DEFAULT_POSITION_PAGE,
    project_uid: str | None = None,
    repository: OptimisationRepository | None = None,
) -> PositionPage:
    """One page of a revision's positions in source-row order."""
    repository = repository or OptimisationRepository()
    record = get_price_list_revision(
        session,
        price_list_id=price_list_id,
        actor_roles=actor_roles,
        project_uid=project_uid,
        repository=repository,
    )
    start = _bounded(offset, field="offset", minimum=0, maximum=None)
    size = _bounded(limit, field="limit", minimum=1, maximum=MAX_POSITION_PAGE)
    positions = repository.position_page(session, record.price_list_id, offset=start, limit=size)
    total = record.accepted_row_count
    following = start + len(positions)
    return PositionPage(
        revision=record,
        positions=positions,
        offset=start,
        limit=size,
        total=total,
        next_offset=following if following < total else None,
    )


def get_effective_vendor_lists(
    session: Session,
    *,
    project_uid: str,
    actor_roles: frozenset[str],
    documents: DocumentRepository | None = None,
    repository: OptimisationRepository | None = None,
) -> tuple[EffectiveVendorList, ...]:
    """All fifteen sections' vendor lists as they apply to one project, in section order."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_VENDOR_LIST)
    project = _project(session, project_uid, documents or DocumentRepository())
    repository = repository or OptimisationRepository()
    global_lists = repository.latest_vendor_lists(session, project_uid=None)
    project_lists = repository.latest_vendor_lists(session, project_uid=project)
    answer: list[EffectiveVendorList] = []
    for section in SECTION_ORDER:
        global_revision = global_lists.get(section)
        project_revision = project_lists.get(section)
        source = effective_source(
            project_mode=None if project_revision is None else project_revision.mode,
            has_global=global_revision is not None,
        )
        effective = {"project": project_revision, "global": global_revision}.get(source)
        if effective is not None and effective.mode != MODE_LIST:  # pragma: no cover
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="an inherit revision applied")
        answer.append(
            EffectiveVendorList(
                section_code=section,
                source=source,
                effective=effective,
                global_revision=global_revision,
                project_revision=project_revision,
            )
        )
    return tuple(answer)


def list_global_vendor_lists(
    session: Session,
    *,
    actor_roles: frozenset[str],
    repository: OptimisationRepository | None = None,
) -> tuple[tuple[str, VendorListRevisionRecord | None], ...]:
    """The latest global revision of every section, in section order (``None``: never set)."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_VENDOR_LIST)
    latest = (repository or OptimisationRepository()).latest_vendor_lists(session, project_uid=None)
    return tuple((section, latest.get(section)) for section in SECTION_ORDER)


def list_vendor_list_history(
    session: Session,
    *,
    section_code: str,
    actor_roles: frozenset[str],
    project_uid: str | None = None,
    limit: int = MAX_VENDOR_HISTORY,
    documents: DocumentRepository | None = None,
    repository: OptimisationRepository | None = None,
) -> tuple[VendorListRevisionRecord, ...]:
    """A section's revisions in one scope (global, or one project), newest first."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_VENDOR_LIST)
    section = parse_section_code(section_code)
    size = _bounded(limit, field="limit", minimum=1, maximum=MAX_VENDOR_HISTORY)
    project = (
        None
        if project_uid is None
        else _project(session, project_uid, documents or DocumentRepository())
    )
    return (repository or OptimisationRepository()).vendor_list_history(
        session, project_uid=project, section=section, limit=size
    )
