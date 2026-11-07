"""Carrying the decisions of an earlier version's pass over to a later one (`UI-B-14`, «Перенести решения из V#»).

A new version of a document set gets a **new pass** with no decisions: a proposal belongs to one pass and a pass to one
version. An expert who has already worked through the previous version's proposals may confirm that the decisions in
force there are carried into the new pass. This is the proposals' counterpart of the findings' carryover
(:mod:`auditmanager.decisions.carryover`) and keeps its discipline:

* **A carried decision is an ordinary event.** It is appended on the target proposal through the same append-only table,
  authored by the expert who confirmed the carryover, and a later decision on the target supersedes it exactly as it
  would any other. Nothing in the source pass is read for writing: its proposals, its decisions and its counts stay as
  they were.
* **Provenance is a column, not a sentence.** ``carried_from_decision_id`` names the source decision by its opaque
  identity; the source's version ordinal travels with it for display ("V2") and is never read back as an identity.
* **Content decides, nothing else.** A source decision is carried only where exactly one proposal of the source pass
  and exactly one proposal of the target pass have the same content -- the type, the specification row's text, the unit
  and currency, both positions (code, mark, name, supplier) and both unit prices (:func:`content_key`). Position in the
  drawing, page, ordinal, the price-list revision's identities and the quantity are not content: a later version moves
  rows around and a quantity does not change what was decided about the replacement. The matcher never falls back to
  "the same number" or "the same name alone": two proposals with the same content on either side are ``ambiguous`` and
  nothing is carried for them.
* **Only into a proposal nobody has touched.** The target must have no event at all. A decision there is an expert's act
  and a withdrawal is one too; a carryover resurrects neither (``target_decided``).
* **Only decisions in force.** A source proposal whose decision in force is an acceptance, a rejection or a revision
  request is carried (a ``revise`` carries its comment, which it requires); a proposal nobody decided, or whose decision
  was withdrawn, carries nothing. An accepted decision is not the same as a trusted one: the confirming expert is the
  author of the carried event.

**The source** must be a pass of the *same document set* started over an *earlier version* than the target's; otherwise
``conflict`` with one of :data:`~auditmanager.optimisation.proposals.policy.CARRYOVER_REFUSAL_REASONS`.

**Concurrency.** A carried decision always goes to a proposal that has no event, so its ``seq`` is ``1``; it is inserted
``ON CONFLICT DO NOTHING`` on the ``(proposal, seq)`` key. A concurrent ordinary decision that won the race leaves the
carried one unwritten and counted as ``target_decided`` -- an expert's act is never overwritten -- and no advisory lock per
proposal is held (a long request would otherwise hold one lock-table entry per carried decision).

**Idempotency.** The request is one keyed command; each decision it appends is claimed under a key derived from the
request's key, the two passes and the two proposals, so a decision is carried once however the request is retried. An
exact repeat of the request answers the report it stored and appends nothing; a new key repeats the matching and, the
targets now being decided, carries nothing more.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey, IdentityError

from .identity import OptimisationPassId, ProposalDecisionId
from .policy import (
    AGGREGATE_OPTIMISATION_PASS,
    COMMAND_TYPE_CARRY_OVER,
    COMMAND_TYPE_CARRY_OVER_ONE,
    REFUSAL_CARRYOVER_SOURCE_IS_TARGET,
    REFUSAL_CARRYOVER_SOURCE_NOT_EARLIER,
    REFUSAL_CARRYOVER_SOURCE_OTHER_DOCUMENT,
    REFUSAL_CARRYOVER_SOURCE_UNKNOWN,
    VERDICTS,
    require_expert,
)
from .repository import OptimisationProposalRecord, PositionSummary, ProposalRepository

__all__ = [
    "CarryoverMatch",
    "ProposalDecisionCarryover",
    "carry_over_proposal_decisions",
    "content_key",
    "plan_carryover",
]

ContentKey = tuple[Any, ...]

_OUTCOME_CARRIED: Final[str] = "carried"
_OUTCOME_TARGET_DECIDED: Final[str] = "target_decided"
_OUTCOME_AMBIGUOUS: Final[str] = "ambiguous"
_OUTCOME_UNMATCHED: Final[str] = "unmatched"


def _text(value: str | None) -> str | None:
    """A text as content: runs of whitespace are one space. Case and characters are kept exactly."""
    return None if value is None else " ".join(value.split())


def _position(position: PositionSummary) -> tuple[str | None, ...]:
    return (_text(position.code), _text(position.mark), _text(position.name), _text(position.vendor))


def content_key(proposal: OptimisationProposalRecord) -> ContentKey:
    """What a proposal says, apart from where it is and which pass or price-list revision it came from.

    The type, the specification row's text, the unit and the currency, the matched and the proposed position by their
    code, mark, name and supplier, and both unit prices (exact decimals: ``10.50`` is ``10.5``). Never an ordinal, a page,
    a position number, an identity or the quantity.
    """
    return (
        proposal.proposal_type,
        _text(proposal.row_text),
        _text(proposal.unit),
        proposal.currency,
        _position(proposal.matched_position),
        _position(proposal.proposed_position),
        Decimal(proposal.current_unit_price),
        Decimal(proposal.proposed_unit_price),
    )


@dataclass(frozen=True, slots=True)
class CarryoverMatch:
    """What one source decision comes to. ``target`` is set for ``carried`` and ``target_decided`` only."""

    source: OptimisationProposalRecord
    target: OptimisationProposalRecord | None
    outcome: str


def plan_carryover(
    source: Sequence[OptimisationProposalRecord], target: Sequence[OptimisationProposalRecord]
) -> tuple[CarryoverMatch, ...]:
    """Match the source pass's decisions in force to the target pass's proposals by content. No I/O, no writes.

    One entry for each source proposal whose decision is in force, in the source's order. A source decision is
    ``unmatched`` when no target proposal has its content, ``ambiguous`` when more than one proposal of either pass has
    it, ``target_decided`` when the one target proposal already carries any event, and ``carried`` otherwise.
    """
    source_by_content: dict[ContentKey, list[OptimisationProposalRecord]] = defaultdict(list)
    for proposal in source:
        source_by_content[content_key(proposal)].append(proposal)
    target_by_content: dict[ContentKey, list[OptimisationProposalRecord]] = defaultdict(list)
    for proposal in target:
        target_by_content[content_key(proposal)].append(proposal)

    matches: list[CarryoverMatch] = []
    for proposal in source:
        if proposal.current_verdict not in VERDICTS:
            continue
        key = content_key(proposal)
        candidates = target_by_content.get(key, [])
        if not candidates:
            matches.append(CarryoverMatch(proposal, None, _OUTCOME_UNMATCHED))
        elif len(candidates) > 1 or len(source_by_content[key]) > 1:
            matches.append(CarryoverMatch(proposal, None, _OUTCOME_AMBIGUOUS))
        elif candidates[0].current_decision is not None:
            matches.append(CarryoverMatch(proposal, candidates[0], _OUTCOME_TARGET_DECIDED))
        else:
            matches.append(CarryoverMatch(proposal, candidates[0], _OUTCOME_CARRIED))
    return tuple(matches)


@dataclass(frozen=True, slots=True)
class ProposalDecisionCarryover:
    """What the request did: every decision in force of the source is counted in exactly one of the four outcomes."""

    optimisation_pass_id: str
    source_optimisation_pass_id: str
    #: The source version's display ordinal ("V2"); never an identity.
    source_version_ordinal: int
    carried: int
    target_decided: int
    ambiguous: int
    unmatched: int

    @property
    def source_decided(self) -> int:
        return self.carried + self.target_decided + self.ambiguous + self.unmatched

    def stored(self) -> dict[str, Any]:
        return {
            "optimisation_pass_id": self.optimisation_pass_id,
            "source_optimisation_pass_id": self.source_optimisation_pass_id,
            "source_version_ordinal": self.source_version_ordinal,
            "carried": self.carried,
            "target_decided": self.target_decided,
            "ambiguous": self.ambiguous,
            "unmatched": self.unmatched,
        }


def _replayed(outcome: Mapping[str, Any]) -> ProposalDecisionCarryover:
    return ProposalDecisionCarryover(
        optimisation_pass_id=str(outcome["optimisation_pass_id"]),
        source_optimisation_pass_id=str(outcome["source_optimisation_pass_id"]),
        source_version_ordinal=int(outcome["source_version_ordinal"]),
        carried=int(outcome["carried"]),
        target_decided=int(outcome["target_decided"]),
        ambiguous=int(outcome["ambiguous"]),
        unmatched=int(outcome["unmatched"]),
    )


def _pattern(field: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="pattern")


def _pass_id(value: str, field: str) -> str:
    try:
        return str(OptimisationPassId.parse(value))
    except (DomainError, TypeError):
        raise _pattern(field) from None


def _refused(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.CONFLICT,
        message=f"the decisions cannot be carried over: {reason}",
        aggregate_type=AGGREGATE_OPTIMISATION_PASS,
        conflict_reason=reason,
    )


def _row_key(request_key: str, target_pass: str, source_pass: str, source_decision: str, target_proposal: str) -> str:
    """The key one carried decision is claimed under: derived, so it is carried once however the request is retried."""
    digest = hashlib.sha256(
        f"{request_key}|{target_pass}|{source_pass}|{source_decision}|{target_proposal}".encode()
    ).hexdigest()
    return f"cry-{digest[:48]}"


def carry_over_proposal_decisions(
    session: Session,
    *,
    optimisation_pass_id: str,
    source_optimisation_pass_id: str,
    idempotency_key: str,
    actor_uid: str,
    actor_roles: frozenset[str],
    repository: ProposalRepository | None = None,
    commands: CommandRepository | None = None,
) -> ProposalDecisionCarryover:
    """Carry the decisions in force of ``source_optimisation_pass_id`` into ``optimisation_pass_id``, or answer the stored report.

    ``expert`` only. The caller owns the transaction: a refusal raised after the key is claimed leaves no claim and no
    decision behind. See the module docstring for the rules.
    """
    require_expert(
        frozenset(actor_roles),
        aggregate_type=AGGREGATE_OPTIMISATION_PASS,
        act="carry over proposal decisions",
    )
    target_id = _pass_id(optimisation_pass_id, "optimisation_pass_id")
    source_id = _pass_id(source_optimisation_pass_id, "source_optimisation_pass_id")
    try:
        key = IdempotencyKey(idempotency_key)
    except (IdentityError, TypeError):
        raise _pattern("idempotency_key") from None
    repository = repository or ProposalRepository()
    commands = commands or CommandRepository()

    claim = commands.begin(
        session,
        command_type=COMMAND_TYPE_CARRY_OVER,
        idempotency_key=key,
        fingerprint=payload_fingerprint(
            {
                "command": "carry_over_proposal_decisions.v1",
                "optimisation_pass_id": target_id,
                "source_optimisation_pass_id": source_id,
                "actor_uid": actor_uid,
            }
        ),
    )
    if isinstance(claim, CommandReplay):
        try:
            return _replayed(claim.outcome)
        except (KeyError, TypeError, ValueError):
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE_CARRY_OVER) from None
    assert isinstance(claim, CommandStarted)

    target_pass = repository.get_pass(session, target_id)
    if target_pass is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_OPTIMISATION_PASS)
    source_pass = repository.get_pass(session, source_id)
    if source_pass is None:
        raise _refused(REFUSAL_CARRYOVER_SOURCE_UNKNOWN)
    if source_id == target_id:
        raise _refused(REFUSAL_CARRYOVER_SOURCE_IS_TARGET)
    if source_pass.document_uid != target_pass.document_uid:
        raise _refused(REFUSAL_CARRYOVER_SOURCE_OTHER_DOCUMENT)
    source_ordinal = source_pass.version_ordinal
    if source_ordinal >= target_pass.version_ordinal:
        raise _refused(REFUSAL_CARRYOVER_SOURCE_NOT_EARLIER)

    plan = plan_carryover(
        repository.every_proposal(session, source_id), repository.every_proposal(session, target_id)
    )
    counts = {_OUTCOME_CARRIED: 0, _OUTCOME_TARGET_DECIDED: 0, _OUTCOME_AMBIGUOUS: 0, _OUTCOME_UNMATCHED: 0}
    for match in plan:
        if match.outcome != _OUTCOME_CARRIED:
            counts[match.outcome] += 1
            continue
        assert match.target is not None and match.source.current_decision is not None
        source_decision = match.source.current_decision
        row_claim = commands.begin(
            session,
            command_type=COMMAND_TYPE_CARRY_OVER_ONE,
            idempotency_key=IdempotencyKey(
                _row_key(
                    idempotency_key,
                    target_id,
                    source_id,
                    source_decision.proposal_decision_id,
                    match.target.optimisation_proposal_id,
                )
            ),
            fingerprint=payload_fingerprint(
                {
                    "command": "carry_over_proposal_decision.v1",
                    "optimisation_proposal_id": match.target.optimisation_proposal_id,
                    "source_proposal_decision_id": source_decision.proposal_decision_id,
                    "actor_uid": actor_uid,
                }
            ),
        )
        if not isinstance(row_claim, CommandStarted):
            # A derived key is claimed in this transaction only, after the request's own key: a replay here means the
            # request was somehow run twice. Fail closed rather than count a decision nobody appended.
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE_CARRY_OVER_ONE)
        appended = repository.insert_carried_decision(
            session,
            decision_id=ProposalDecisionId.new(),
            proposal_id=match.target.optimisation_proposal_id,
            verdict=source_decision.verdict,
            comment=source_decision.comment,
            actor_user_uid=actor_uid,
            command_id=str(row_claim.command_id),
            carried_from_decision_id=source_decision.proposal_decision_id,
        )
        if appended is None:
            # An ordinary decision reached the target between the read and the insert: the expert's act stands.
            counts[_OUTCOME_TARGET_DECIDED] += 1
            commands.succeed(session, row_claim.command_id, {"proposal_decision_id": None})
            continue
        counts[_OUTCOME_CARRIED] += 1
        commands.succeed(session, row_claim.command_id, {"proposal_decision_id": appended.proposal_decision_id})

    report = ProposalDecisionCarryover(
        optimisation_pass_id=target_id,
        source_optimisation_pass_id=source_id,
        source_version_ordinal=source_ordinal,
        carried=counts[_OUTCOME_CARRIED],
        target_decided=counts[_OUTCOME_TARGET_DECIDED],
        ambiguous=counts[_OUTCOME_AMBIGUOUS],
        unmatched=counts[_OUTCOME_UNMATCHED],
    )
    commands.succeed(session, claim.command_id, report.stored())
    return report
