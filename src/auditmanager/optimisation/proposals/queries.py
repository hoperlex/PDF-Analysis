"""The proposals slice's reads: passes of a project, one pass, its proposals page by page.

Every read takes the caller's session and the actor's role set; an account with no role is
``permission_denied`` (`R-80`). A pass or a proposal that does not exist is ``not_found``
(``OptimisationPass`` / ``OptimisationProposal``); an unknown project is ``not_found``
(``Project``); a document set of another project is ``not_found`` (``Document``).

Counts by decision cover **every** proposal of a pass -- ``pending`` (no decision yet) and
each verdict -- whatever page or filter is asked for. They are the proposals' own counts,
never mixed with finding counts.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdentityError, ProjectUid

from .identity import OptimisationPassId, OptimisationProposalId
from .policy import (
    AGGREGATE_OPTIMISATION_PASS,
    AGGREGATE_OPTIMISATION_PROPOSAL,
    DEFAULT_PROPOSAL_PAGE,
    MAX_PASS_PAGE,
    MAX_PROPOSAL_PAGE,
    parse_decision_filter,
    require_reader,
)
from .repository import (
    OptimisationPassRecord,
    OptimisationProposalRecord,
    ProposalDecisionRecord,
    ProposalRepository,
)

__all__ = [
    "ProposalPage",
    "get_optimisation_pass",
    "list_optimisation_passes",
    "list_optimisation_proposals",
    "list_proposal_decisions",
]


@dataclass(frozen=True, slots=True)
class ProposalPage:
    """One page of a pass's proposals; ``next_offset`` is ``None`` on the last page.

    ``total`` counts the proposals the ``decision`` filter admits; the pass's
    ``decision_counts`` count all of them.
    """

    optimisation_pass: OptimisationPassRecord
    decision: str | None
    offset: int
    limit: int
    total: int
    next_offset: int | None
    items: tuple[OptimisationProposalRecord, ...]


def _bounded(value: object, *, field: str, minimum: int, maximum: int | None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="type")
    if value < minimum or (maximum is not None and value > maximum):
        constraint = f">= {minimum}" if maximum is None else f"{minimum}..{maximum}"
        raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)
    return value


def _pattern(field: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="pattern")


def _pass_id(value: str) -> str:
    try:
        return str(OptimisationPassId.parse(value))
    except (DomainError, TypeError):
        raise _pattern("optimisation_pass_id") from None


def list_optimisation_passes(
    session: Session,
    *,
    project_uid: str,
    actor_roles: frozenset[str],
    document_uid: str | None = None,
    limit: int = MAX_PASS_PAGE,
    documents: DocumentRepository | None = None,
    repository: ProposalRepository | None = None,
) -> tuple[OptimisationPassRecord, ...]:
    """A project's passes, newest first, each with its counts by decision."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_OPTIMISATION_PASS)
    try:
        project = ProjectUid.parse(project_uid)
    except (IdentityError, TypeError):
        raise _pattern("project_uid") from None
    document: DocumentUid | None = None
    if document_uid is not None:
        try:
            document = DocumentUid.parse(document_uid)
        except (IdentityError, TypeError):
            raise _pattern("document_uid") from None
    size = _bounded(limit, field="limit", minimum=1, maximum=MAX_PASS_PAGE)
    documents = documents or DocumentRepository()
    documents.get_project(session, project)
    if document is not None and documents.require_document(session, document) != project:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
    return (repository or ProposalRepository()).list_passes(
        session,
        project_uid=str(project),
        document_uid=None if document is None else str(document),
        limit=size,
    )


def get_optimisation_pass(
    session: Session,
    *,
    optimisation_pass_id: str,
    actor_roles: frozenset[str],
    repository: ProposalRepository | None = None,
) -> OptimisationPassRecord:
    """One pass with its counts by decision."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_OPTIMISATION_PASS)
    identity = _pass_id(optimisation_pass_id)
    stored = (repository or ProposalRepository()).get_pass(session, identity)
    if stored is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_OPTIMISATION_PASS)
    return stored


def list_optimisation_proposals(
    session: Session,
    *,
    optimisation_pass_id: str,
    actor_roles: frozenset[str],
    decision: str | None = None,
    offset: int = 0,
    limit: int = DEFAULT_PROPOSAL_PAGE,
    repository: ProposalRepository | None = None,
) -> ProposalPage:
    """A page of a pass's proposals in ordinal order, each with its current decision."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_OPTIMISATION_PROPOSAL)
    identity = _pass_id(optimisation_pass_id)
    chosen = parse_decision_filter(decision)
    start = _bounded(offset, field="offset", minimum=0, maximum=None)
    size = _bounded(limit, field="limit", minimum=1, maximum=MAX_PROPOSAL_PAGE)
    repository = repository or ProposalRepository()
    stored = repository.get_pass(session, identity)
    if stored is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_OPTIMISATION_PASS)
    items, total = repository.proposal_page(
        session, pass_id=identity, decision=chosen, offset=start, limit=size
    )
    following = start + len(items)
    return ProposalPage(
        optimisation_pass=stored,
        decision=chosen,
        offset=start,
        limit=size,
        total=total,
        next_offset=following if following < total else None,
        items=items,
    )


def list_proposal_decisions(
    session: Session,
    *,
    optimisation_proposal_id: str,
    actor_roles: frozenset[str],
    repository: ProposalRepository | None = None,
) -> tuple[ProposalDecisionRecord, ...]:
    """Every decision of one proposal, oldest first; the last one is current."""
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_OPTIMISATION_PROPOSAL)
    try:
        identity = str(OptimisationProposalId.parse(optimisation_proposal_id))
    except (DomainError, TypeError):
        raise _pattern("optimisation_proposal_id") from None
    repository = repository or ProposalRepository()
    if repository.get_proposal(session, identity) is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_OPTIMISATION_PROPOSAL)
    return repository.decision_history(session, identity)
