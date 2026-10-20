"""The proposals slice's commands: start an optimisation pass, decide a proposal.

Each takes the caller's session and the actor's role set **read in the same transaction**
(the composition root reads it through ``access``, as for the vendor-list commands) and owns
no transaction: the caller commits or rolls back the whole unit of work, so a refusal raised
after the idempotency key is claimed leaves no claim, no pass and no decision behind.

:func:`start_optimisation_pass` -- ``expert``. In order: the role; the identifiers and the
key (``validation_failed``); the key -- a key already claimed with the same payload answers
the stored pass, with another payload ``idempotency_key_reuse``; the specification read
(:func:`~auditmanager.optimisation.project_match.read_specification_prices`) must be
``ready``, else ``conflict`` with its state as ``conflict_reason`` (an unknown project or a
set of another project is ``not_found``); the effective AR vendor list must exist, else
``conflict`` (``vendor_list_missing``); then, under the version's advisory lock, a pass with
exactly these inputs (version, run, price list, vendor list, the three algorithm versions)
is answered as it is stored -- an exact repeat under a new key creates nothing -- or the
generator runs and the pass and every proposal are inserted in this transaction.

:func:`decide_optimisation_proposal` -- ``expert`` (``admin`` alone is
``permission_denied``). The verdict and comment are validated (``revise`` requires a
comment); the key is claimed (same payload answers the stored decision); the proposal must
exist (``not_found`` ``OptimisationProposal``); under the proposal's advisory lock the next
``seq`` is appended. Every call under a new key appends a new event -- the history is the
record, the latest event is the current decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey, IdentityError, ProjectUid

from ..matching import MATCH_ALGORITHM
from ..policy import SOURCE_NONE
from ..project_match import (
    MAX_ROW_PAGE,
    SECTION_AR,
    STATE_READY,
    SavedTextReader,
    read_specification_prices,
)
from ..queries import get_effective_vendor_lists
from ..repository import (
    OptimisationRepository,
    PriceListPositionRecord,
    PriceListRevisionRecord,
)
from ..specification import EXTRACTION_ALGORITHM
from .generator import GENERATOR_VERSION, generate_cheaper_analogs
from .identity import OptimisationPassId, OptimisationProposalId, ProposalDecisionId
from .policy import (
    AGGREGATE_OPTIMISATION_PASS,
    AGGREGATE_OPTIMISATION_PROPOSAL,
    COMMAND_TYPE_DECIDE_PROPOSAL,
    COMMAND_TYPE_START_PASS,
    REFUSAL_VENDOR_LIST_MISSING,
    normalize_comment,
    parse_verdict,
    require_expert,
)
from .repository import (
    OptimisationPassRecord,
    OptimisationProposalRecord,
    ProposalDecisionRecord,
    ProposalRepository,
)

__all__ = [
    "PassStart",
    "ProposalDecision",
    "decide_optimisation_proposal",
    "start_optimisation_pass",
]

_POSITION_CHUNK: Final[int] = 5000


@dataclass(frozen=True, slots=True)
class PassStart:
    """The pass in force for the request, and how it was reached.

    ``created``: this call wrote it. ``replayed``: the idempotency key had already answered
    it. Neither: an earlier pass with exactly these inputs exists and is the answer.
    """

    optimisation_pass: OptimisationPassRecord
    created: bool
    replayed: bool


@dataclass(frozen=True, slots=True)
class ProposalDecision:
    """The appended (or replayed) decision and the proposal as it now stands."""

    decision: ProposalDecisionRecord
    proposal: OptimisationProposalRecord
    replayed: bool


def _pattern(field: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="pattern")


def _key(value: str) -> IdempotencyKey:
    try:
        return IdempotencyKey(value)
    except (IdentityError, TypeError):
        raise _pattern("idempotency_key") from None


def _refused(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.CONFLICT,
        message=f"the optimisation pass cannot start: {reason}",
        aggregate_type=AGGREGATE_OPTIMISATION_PASS,
        conflict_reason=reason,
    )


def _stale(command_type: str) -> DomainError:
    return DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=command_type)


def _replayed_pass(
    session: Session, repository: ProposalRepository, claim: CommandReplay
) -> OptimisationPassRecord:
    raw = claim.outcome.get("optimisation_pass_id")
    stored = repository.get_pass(session, raw) if isinstance(raw, str) else None
    if stored is None:
        raise _stale(COMMAND_TYPE_START_PASS)
    return stored


def start_optimisation_pass(
    session: Session,
    *,
    project_uid: str,
    document_uid: str,
    idempotency_key: str,
    actor_uid: str,
    actor_roles: frozenset[str],
    reader: SavedTextReader,
    documents: DocumentRepository | None = None,
    price_lists: OptimisationRepository | None = None,
    repository: ProposalRepository | None = None,
    commands: CommandRepository | None = None,
) -> PassStart:
    """Start (or answer) the optimisation pass of a document set's current AR version."""
    roles = frozenset(actor_roles)
    require_expert(roles, aggregate_type=AGGREGATE_OPTIMISATION_PASS, act="start an optimisation pass")
    try:
        project = ProjectUid.parse(project_uid)
    except (IdentityError, TypeError):
        raise _pattern("project_uid") from None
    try:
        document = DocumentUid.parse(document_uid)
    except (IdentityError, TypeError):
        raise _pattern("document_uid") from None
    key = _key(idempotency_key)
    documents = documents or DocumentRepository()
    price_lists = price_lists or OptimisationRepository()
    repository = repository or ProposalRepository()
    commands = commands or CommandRepository()

    claim = commands.begin(
        session,
        command_type=COMMAND_TYPE_START_PASS,
        idempotency_key=key,
        fingerprint=payload_fingerprint(
            {
                "command": "start_optimisation_pass.v1",
                "project_uid": str(project),
                "document_uid": str(document),
                "actor_uid": actor_uid,
            }
        ),
    )
    if isinstance(claim, CommandReplay):
        return PassStart(_replayed_pass(session, repository, claim), created=False, replayed=True)
    assert isinstance(claim, CommandStarted)

    prices = read_specification_prices(
        session,
        project_uid=str(project),
        document_uid=str(document),
        actor_roles=roles,
        reader=reader,
        limit=MAX_ROW_PAGE,
        documents=documents,
        repository=price_lists,
    )
    if prices.state != STATE_READY:
        raise _refused(prices.state)
    assert (
        prices.price_list is not None
        and prices.run_id is not None
        and prices.text_layer_sha256 is not None
        and prices.extraction is not None
        and prices.matching is not None
    )
    effective = next(
        entry
        for entry in get_effective_vendor_lists(
            session,
            project_uid=str(project),
            actor_roles=roles,
            documents=documents,
            repository=price_lists,
        )
        if entry.section_code == SECTION_AR
    )
    if effective.source == SOURCE_NONE or effective.effective is None:
        raise _refused(REFUSAL_VENDOR_LIST_MISSING)
    vendor_list = effective.effective

    repository.lock_version(session, prices.version_uid)
    inputs = {
        "version_uid": prices.version_uid,
        "run_id": prices.run_id,
        "price_list_id": prices.price_list.price_list_id,
        "vendor_list_id": vendor_list.vendor_list_id,
        "extraction_algorithm": EXTRACTION_ALGORITHM,
        "match_algorithm": MATCH_ALGORITHM,
        "generator_version": GENERATOR_VERSION,
    }
    existing = repository.find_pass(session, **inputs)
    if existing is not None:
        commands.succeed(
            session, claim.command_id, {"optimisation_pass_id": existing.optimisation_pass_id}
        )
        return PassStart(existing, created=False, replayed=False)

    outcome = generate_cheaper_analogs(
        prices.matching.matches,
        _positions_of(session, price_lists, prices.price_list),
        (entry.vendor for entry in vendor_list.entries),
    )
    pass_id = OptimisationPassId.new()
    repository.insert_pass(
        session,
        pass_id=pass_id,
        project_uid=str(project),
        document_uid=str(document),
        version_uid=prices.version_uid,
        run_id=prices.run_id,
        text_layer_sha256=prices.text_layer_sha256,
        price_list_id=prices.price_list.price_list_id,
        vendor_list_id=vendor_list.vendor_list_id,
        vendor_list_source=effective.source,
        extraction_algorithm=EXTRACTION_ALGORITHM,
        match_algorithm=MATCH_ALGORITHM,
        generator_version=GENERATOR_VERSION,
        specification_row_count=len(prices.extraction.rows),
        matched_row_count=outcome.rows_matched,
        proposed_row_count=outcome.rows_with_proposals,
        drafts=outcome.proposals,
        started_by_user_uid=actor_uid,
    )
    commands.succeed(session, claim.command_id, {"optimisation_pass_id": str(pass_id)})
    stored = repository.get_pass(session, str(pass_id))
    if stored is None:  # pragma: no cover - inserted above in this transaction
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="the new pass is not readable")
    return PassStart(stored, created=True, replayed=False)


def _positions_of(
    session: Session, price_lists: OptimisationRepository, revision: PriceListRevisionRecord
) -> tuple[PriceListPositionRecord, ...]:
    """Every position of the revision, in source-row order, read in bounded pages."""
    expected = revision.accepted_row_count
    collected: list[PriceListPositionRecord] = []
    while len(collected) < expected:
        page = price_lists.position_page(
            session, revision.price_list_id, offset=len(collected), limit=_POSITION_CHUNK
        )
        if not page:
            break
        collected.extend(page)
    if len(collected) != expected:
        raise DomainError(
            ErrorCode.INTERNAL_ERROR,
            message="the price list's stored positions disagree with its accepted row count",
        )
    return tuple(collected)


def decide_optimisation_proposal(
    session: Session,
    *,
    proposal_id: str,
    verdict: str,
    comment: str | None,
    idempotency_key: str,
    actor_uid: str,
    actor_roles: frozenset[str],
    repository: ProposalRepository | None = None,
    commands: CommandRepository | None = None,
) -> ProposalDecision:
    """Append one expert decision to a proposal, or answer the one stored under the key."""
    require_expert(
        frozenset(actor_roles),
        aggregate_type=AGGREGATE_OPTIMISATION_PROPOSAL,
        act="decide an optimisation proposal",
    )
    try:
        proposal = str(OptimisationProposalId.parse(proposal_id))
    except (DomainError, TypeError):
        raise _pattern("optimisation_proposal_id") from None
    chosen = parse_verdict(verdict)
    cleaned = normalize_comment(comment, verdict=chosen)
    key = _key(idempotency_key)
    repository = repository or ProposalRepository()
    commands = commands or CommandRepository()

    claim = commands.begin(
        session,
        command_type=COMMAND_TYPE_DECIDE_PROPOSAL,
        idempotency_key=key,
        fingerprint=payload_fingerprint(
            {
                "command": "decide_optimisation_proposal.v1",
                "optimisation_proposal_id": proposal,
                "verdict": chosen,
                "comment": cleaned,
                "actor_uid": actor_uid,
            }
        ),
    )
    if isinstance(claim, CommandReplay):
        stored = repository.decision_by_command(session, str(claim.command_id))
        current = repository.get_proposal(session, proposal)
        if stored is None or current is None:
            raise _stale(COMMAND_TYPE_DECIDE_PROPOSAL)
        return ProposalDecision(stored, current, replayed=True)
    assert isinstance(claim, CommandStarted)

    if repository.get_proposal(session, proposal) is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_OPTIMISATION_PROPOSAL)
    repository.lock_proposal(session, proposal)
    decision = repository.insert_decision(
        session,
        decision_id=ProposalDecisionId.new(),
        proposal_id=proposal,
        seq=repository.next_seq(session, proposal),
        verdict=chosen,
        comment=cleaned,
        actor_user_uid=actor_uid,
        command_id=str(claim.command_id),
    )
    commands.succeed(
        session, claim.command_id, {"proposal_decision_id": decision.proposal_decision_id}
    )
    current = repository.get_proposal(session, proposal)
    assert current is not None
    return ProposalDecision(decision, current, replayed=False)
