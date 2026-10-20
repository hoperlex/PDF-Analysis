"""Expert-confirmed decision carryover over the served comparison (`W59-DECISION-CARRYOVER-01`).

The served comparison (:class:`~auditmanager.comparison.service.VersionComparisonService`)
proposes finding matches and writes nothing. This module adds the one write it leads to: an
expert who sees an ``unchanged`` proposal whose source finding carries a decision confirms
«Перенести решение», and the target finding receives a new decision event recording where
it came from (:func:`auditmanager.decisions.public.carry_over_decision`).

* **Nothing is carried without that confirmation.** :func:`carryover_candidates` only lists
  what *could* be carried; it never appends.
* **The pair is proved at confirmation time.** :meth:`DecisionCarryoverService.carry_over`
  recomputes the comparison for the named versions, mode and runs in the confirming
  transaction, and refuses ``conflict`` / ``carryover_pair_not_proposed`` unless it still
  proposes exactly these two findings as ``unchanged``. A foreign, swapped or crossed pair,
  a finding of another version, a refused comparison, a run over the finding limit and a
  pair a newer published run no longer proposes are all that one refusal.
* **Only ``unchanged`` is carried.** A ``probably_fixed`` source has no target finding, so
  there is nothing to carry a verdict to and nothing here marks it resolved: that takes an
  expert's own decision. ``undetermined`` and ``new`` are never carried either.
* **Expert only** (`R-60`): the account's role set, read in the transaction, must hold
  ``expert``; ``admin`` alone is ``permission_denied``.
* **The decision is the expert's.** The appended event's author is the confirming account;
  no AI layer proposes or edits it, and the source finding, its decisions and the raw
  comparison evidence are only read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.comparison.decision_carryover import (
    MAX_CARRYOVER_MATCHES,
    DecisionCarryoverRefused,
    require_carryover_expert,
)
from auditmanager.comparison.read_model import (
    FINDINGS_COMPARED,
    MODES,
    OUTCOME_COMPARED,
    PROPOSAL_UNCHANGED,
    SIDE_TARGET,
    FindingProposal,
    FindingRef,
    VersionComparison,
)
from auditmanager.comparison.service import (
    ComparisonIntegrityError,
    ComparisonRequest,
    VersionComparisonService,
)
from auditmanager.decisions.public import (
    CARRIED_EVENT_FOR_VERDICT,
    CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED,
    CarryoverProvenance,
    DecisionEvent,
    carry_over_decision,
    current_verdict,
    current_verdicts,
    decision_events_by_id,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    DecisionId,
    DocumentUid,
    FindingUid,
    IdentityError,
    ProjectUid,
    RunId,
    VersionUid,
)

__all__ = [
    "CarriedSourceDecision",
    "CarryoverCandidate",
    "CarryoverOutcome",
    "CarryoverRequest",
    "DecisionCarryoverService",
    "carryover_candidates",
]

#: ``permission_denied`` detail of a carryover by an account without the expert role.
REQUIRED_CAPABILITY: Final[str] = "role:expert"


@dataclass(frozen=True, slots=True)
class CarryoverRequest:
    """One confirmation: the comparison it was shown in, the pair and the decision.

    ``source_decision_id`` is the decision the expert saw on the source finding; if the
    source's current verdict has moved on since, the carryover is refused rather than
    carrying a decision nobody confirmed.
    """

    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    source_finding_uid: str
    target_finding_uid: str
    source_decision_id: str
    mode: str = "version"
    source_run_id: str | None = None
    target_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class CarriedSourceDecision:
    """The source finding's current verdict-bearing event, as the expert is shown it."""

    decision_id: str
    verdict: str
    severity: str | None
    comment: str | None
    author_label: str
    recorded_at: datetime | None


@dataclass(frozen=True, slots=True)
class CarryoverCandidate:
    """An ``unchanged`` proposal whose source is decided and whose target has no event."""

    proposal_sha256: str
    source_finding: FindingRef
    target_finding: FindingRef
    source_decision: CarriedSourceDecision


@dataclass(frozen=True, slots=True)
class CarryoverOutcome:
    """The carried event on the target finding, its provenance and the verdict now standing.

    ``replayed`` is ``True`` when the target already carried exactly this event and nothing
    was appended (an exact repeat answers the first confirmation, its expert and time).
    """

    event: DecisionEvent
    replayed: bool
    target_current_verdict: str
    source_decision: CarriedSourceDecision
    source_finding_uid: str
    source_version_uid: str
    source_version_ordinal: int
    target_version_uid: str
    mode: str


def _source_decision(event: DecisionEvent) -> CarriedSourceDecision:
    if event.verdict not in CARRIED_EVENT_FOR_VERDICT:
        raise ComparisonIntegrityError("source_decision_not_verdict_bearing")
    return CarriedSourceDecision(
        event.decision_id, event.verdict, event.severity, event.comment,
        event.author_label, event.recorded_at,  # type: ignore[arg-type]
    )


def _unchanged_pairs(comparison: VersionComparison) -> tuple[FindingProposal, ...]:
    if (
        comparison.outcome != OUTCOME_COMPARED
        or comparison.findings is None
        or comparison.findings.status != FINDINGS_COMPARED
    ):
        return ()
    pairs = tuple(
        proposal for proposal in comparison.findings.proposals
        if proposal.kind == PROPOSAL_UNCHANGED
    )
    for proposal in pairs:
        if (
            proposal.source_finding is None
            or proposal.target_finding is None
            or proposal.proposal_sha256 is None
        ):
            raise ComparisonIntegrityError("unchanged_proposal_incomplete")
    if len(pairs) > MAX_CARRYOVER_MATCHES:
        raise ComparisonIntegrityError("unchanged_proposals_over_limit")
    return pairs


def carryover_candidates(
    session: Session, comparison: VersionComparison,
) -> tuple[CarryoverCandidate, ...]:
    """What an expert could carry in ``comparison``, in the proposals' order. Read-only.

    A pair is a candidate when it is proposed ``unchanged``, its source finding's current
    verdict is ``accepted`` or ``rejected``, and its target finding has no decision event at
    all. A refused comparison, or findings over the limit, has none. Two batched reads of the
    decision projection and ledger, at most 200 pairs (one per finding of a run).
    """
    pairs = _unchanged_pairs(comparison)
    if not pairs:
        return ()
    uids = [
        uid for proposal in pairs
        for uid in (proposal.source_finding.finding_uid, proposal.target_finding.finding_uid)  # type: ignore[union-attr]
    ]
    verdicts = current_verdicts(session, uids)
    if set(verdicts) != set(uids):
        raise ComparisonIntegrityError("decision_projection_missing")
    eligible: list[tuple[FindingProposal, str]] = []
    for proposal in pairs:
        source = verdicts[proposal.source_finding.finding_uid]  # type: ignore[union-attr]
        target = verdicts[proposal.target_finding.finding_uid]  # type: ignore[union-attr]
        if (
            source.current_verdict in CARRIED_EVENT_FOR_VERDICT
            and source.latest_verdict_decision_id is not None
            and target.decision_event_count == 0
        ):
            eligible.append((proposal, source.latest_verdict_decision_id))
    events = decision_events_by_id(session, [decision_id for _, decision_id in eligible])
    if set(events) != {decision_id for _, decision_id in eligible}:
        raise ComparisonIntegrityError("decision_event_missing")
    return tuple(
        CarryoverCandidate(
            proposal.proposal_sha256,  # type: ignore[arg-type]
            proposal.source_finding,  # type: ignore[arg-type]
            proposal.target_finding,  # type: ignore[arg-type]
            _source_decision(events[decision_id]),
        )
        for proposal, decision_id in eligible
    )


def _check_request(request: CarryoverRequest) -> None:
    if not isinstance(request, CarryoverRequest):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="request", constraint="format")
    for field, kind in (
        ("project_uid", ProjectUid),
        ("document_uid", DocumentUid),
        ("source_version_uid", VersionUid),
        ("target_version_uid", VersionUid),
        ("source_finding_uid", FindingUid),
        ("target_finding_uid", FindingUid),
        ("source_decision_id", DecisionId),
    ):
        try:
            kind.parse(getattr(request, field))
        except (IdentityError, TypeError):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field=field, constraint="format",
            ) from None
    for field in ("source_run_id", "target_run_id"):
        value = getattr(request, field)
        if value is None:
            continue
        try:
            RunId.parse(value)
        except (IdentityError, TypeError):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field=field, constraint="format",
            ) from None
    if request.mode not in MODES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="mode", constraint="enum")


class DecisionCarryoverService:
    """The confirmed carryover command over a freshly recomputed comparison."""

    def __init__(self, *, comparisons: VersionComparisonService) -> None:
        if not isinstance(comparisons, VersionComparisonService):
            raise TypeError("comparisons must be the served VersionComparisonService")
        self._comparisons = comparisons

    def carry_over(
        self,
        session: Session,
        request: CarryoverRequest,
        *,
        actor_uid: str,
        actor_label: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> CarryoverOutcome:
        """Carry the confirmed source decision to the target finding, or refuse.

        The caller owns the (write) transaction and reads ``actor_roles`` from the account
        inside it. Order: request shape (``validation_failed``), the expert role
        (``permission_denied``), the path (``not_found``), the recomputed pair
        (``conflict`` / ``carryover_pair_not_proposed``), then the ledger's own rules under
        row locks (:func:`auditmanager.decisions.public.carry_over_decision`).
        """
        _check_request(request)
        try:
            require_carryover_expert(actor_uid, actor_roles)
        except DecisionCarryoverRefused:
            raise DomainError(
                ErrorCode.PERMISSION_DENIED, required_capability=REQUIRED_CAPABILITY,
            ) from None
        DocumentRepository().get_version_in(
            session,
            project_uid=ProjectUid.parse(request.project_uid),
            document_uid=DocumentUid.parse(request.document_uid),
            version_uid=VersionUid.parse(request.source_version_uid),
        )
        current = self._comparisons.current_finding_proposals(session, ComparisonRequest(
            project_uid=request.project_uid,
            document_uid=request.document_uid,
            source_version_uid=request.source_version_uid,
            target_version_uid=request.target_version_uid,
            source_run_id=request.source_run_id,
            target_run_id=request.target_run_id,
            mode=request.mode,
        ))
        comparison = current.comparison
        proposal = next(
            (
                item for item in _unchanged_pairs(comparison)
                if item.source_finding.finding_uid == request.source_finding_uid  # type: ignore[union-attr]
                and item.target_finding.finding_uid == request.target_finding_uid  # type: ignore[union-attr]
            ),
            None,
        )
        if proposal is None:
            raise DomainError(
                ErrorCode.CONFLICT,
                aggregate_type="ExpertDecision",
                conflict_reason=CONFLICT_CARRYOVER_PAIR_NOT_PROPOSED,
            )
        observation = current.observations[SIDE_TARGET].get(request.target_finding_uid)
        if observation is None or comparison.source is None:
            raise ComparisonIntegrityError("proposed_finding_without_observation")
        provenance = CarryoverProvenance(
            source_finding_uid=request.source_finding_uid,
            source_decision_id=request.source_decision_id,
            source_version_uid=request.source_version_uid,
            source_version_ordinal=comparison.source.version_ordinal,
            target_version_uid=request.target_version_uid,
            mode=request.mode,
        )
        carried = carry_over_decision(
            session,
            provenance=provenance,
            target_finding_uid=request.target_finding_uid,
            target_finding_observation_id=observation,
            idempotency_key=idempotency_key,
            author_label=actor_label,
            author_user_uid=actor_uid,
        )
        standing = current_verdict(session, request.target_finding_uid)
        if standing is None:  # pragma: no cover - the finding row was locked above
            raise ComparisonIntegrityError("target_finding_vanished")
        return CarryoverOutcome(
            carried.event,
            carried.replayed,
            standing.current_verdict,
            _source_decision(carried.source_event),
            provenance.source_finding_uid,
            provenance.source_version_uid,
            provenance.source_version_ordinal,
            provenance.target_version_uid,
            provenance.mode,
        )
