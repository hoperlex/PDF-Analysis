"""Pure, fail-closed preparation for confirmed version decision carryover.

The comparison service must obtain approved finding matches, current decision
projections and actor roles from authoritative state. This module cannot prove
those inputs or append an event. It only makes an offer's exact content stable
and refuses a selection that no longer appears in a freshly loaded snapshot.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Sequence

from auditmanager.access.public import ROLE_EXPERT, ROLES, UserUid
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import (
    ComparisonId,
    DecisionId,
    FindingUid,
    IdentityError,
    VersionUid,
)

ALGORITHM = "confirmed-decision-carryover-offer-v1"
# One-to-one matches originate from at most 200 findings per Run in W59.
MAX_CARRYOVER_MATCHES = 200
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class DecisionCarryoverRefused(ValueError):
    """No attributable, current and explicitly selected plan can be produced."""


@dataclass(frozen=True, slots=True)
class MatchedDecision:
    """One authoritative match plus the two findings' current event snapshots.

    ``matching_evidence_sha256`` names immutable matching evidence, never a
    finding identity. The caller must prove that the source decision is the
    latest verdict-bearing event and both findings belong to the named
    versions. A target with any event is conservatively ineligible.
    """

    comparison_id: str
    source_version_uid: str
    target_version_uid: str
    source_finding_uid: str
    target_finding_uid: str
    source_decision_id: str
    source_current_verdict: str
    source_event_count: int
    target_event_count: int
    matching_revision: int
    matching_evidence_sha256: str


@dataclass(frozen=True, slots=True)
class DecisionCarryoverOffer:
    match: MatchedDecision
    offer_sha256: str


@dataclass(frozen=True, slots=True)
class ConfirmedCarryoverPlan:
    """Selected instruction for a future transactional append, not an event."""

    offer: DecisionCarryoverOffer
    expert_user_uid: str


def _identity(value: str, kind: type, field: str) -> None:
    try:
        kind.parse(value)
    except (IdentityError, TypeError):
        raise DecisionCarryoverRefused(f"{field}_invalid") from None


def _positive(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DecisionCarryoverRefused(f"{field}_invalid")


def _validate_match(match: MatchedDecision) -> None:
    if not isinstance(match, MatchedDecision):
        raise DecisionCarryoverRefused("match_invalid")
    for field, kind in (
        ("comparison_id", ComparisonId),
        ("source_version_uid", VersionUid),
        ("target_version_uid", VersionUid),
        ("source_finding_uid", FindingUid),
        ("target_finding_uid", FindingUid),
        ("source_decision_id", DecisionId),
    ):
        _identity(getattr(match, field), kind, field)
    if match.source_version_uid == match.target_version_uid:
        raise DecisionCarryoverRefused("same_version")
    if match.source_finding_uid == match.target_finding_uid:
        raise DecisionCarryoverRefused("same_finding")
    if match.source_current_verdict not in ("accepted", "rejected"):
        raise DecisionCarryoverRefused("source_verdict_not_decided")
    _positive(match.source_event_count, "source_event_count")
    if (
        isinstance(match.target_event_count, bool)
        or not isinstance(match.target_event_count, int)
        or match.target_event_count != 0
    ):
        raise DecisionCarryoverRefused("target_already_has_events")
    _positive(match.matching_revision, "matching_revision")
    if (
        not isinstance(match.matching_evidence_sha256, str)
        or _SHA256.fullmatch(match.matching_evidence_sha256) is None
    ):
        raise DecisionCarryoverRefused("matching_evidence_sha256_invalid")


def _offer_digest(match: MatchedDecision) -> str:
    body = {"algorithm": ALGORITHM, "match": asdict(match)}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def offer_decision_carryover(
    matches: Sequence[MatchedDecision],
) -> tuple[DecisionCarryoverOffer, ...]:
    """Offer current previous verdicts for explicit one-to-one finding matches.

    An empty authoritative match set yields no offer. No result contains an
    inferred match, copied event or automatic verdict. Order is independent of
    the caller's sequence order.
    """
    if not isinstance(matches, (tuple, list)):
        raise DecisionCarryoverRefused("matches_invalid")
    if len(matches) > MAX_CARRYOVER_MATCHES:
        raise DecisionCarryoverRefused("matches_too_large")
    if not matches:
        return ()
    seen_source: set[str] = set()
    seen_target: set[str] = set()
    comparison_key: tuple[str, str, str, int] | None = None
    offers: list[DecisionCarryoverOffer] = []
    for match in matches:
        _validate_match(match)
        key = (
            match.comparison_id,
            match.source_version_uid,
            match.target_version_uid,
            match.matching_revision,
        )
        if comparison_key is None:
            comparison_key = key
        elif key != comparison_key:
            raise DecisionCarryoverRefused("comparison_revision_mismatch")
        if match.source_finding_uid in seen_source or match.target_finding_uid in seen_target:
            raise DecisionCarryoverRefused("match_not_one_to_one")
        seen_source.add(match.source_finding_uid)
        seen_target.add(match.target_finding_uid)
        offers.append(DecisionCarryoverOffer(match, _offer_digest(match)))
    return tuple(sorted(offers, key=lambda item: item.match.target_finding_uid))


def confirm_decision_carryover(
    *,
    current_matches: Sequence[MatchedDecision],
    selected_offer_sha256s: Sequence[str],
    expert_user_uid: str,
    actor_roles: frozenset[str],
) -> tuple[ConfirmedCarryoverPlan, ...]:
    """Confirm exact displayed offers against a freshly loaded match snapshot.

    ``current_matches`` must be re-read in the same transaction that will append
    the resulting events. The future service must authenticate the role and
    persist each event with source provenance and an idempotency key. This pure
    result is never itself an authority to write a verdict.
    """
    try:
        UserUid.parse(expert_user_uid)
    except (DomainError, TypeError):
        raise DecisionCarryoverRefused("expert_identity_invalid") from None
    if (
        not isinstance(actor_roles, frozenset)
        or not actor_roles.issubset(ROLES)
        or ROLE_EXPERT not in actor_roles
    ):
        raise DecisionCarryoverRefused("expert_role_required")
    if not isinstance(selected_offer_sha256s, (tuple, list)) or not selected_offer_sha256s:
        raise DecisionCarryoverRefused("selection_empty_or_invalid")
    if len(selected_offer_sha256s) > MAX_CARRYOVER_MATCHES:
        raise DecisionCarryoverRefused("selection_too_large")
    if any(
        not isinstance(value, str) or _SHA256.fullmatch(value) is None
        for value in selected_offer_sha256s
    ):
        raise DecisionCarryoverRefused("selection_digest_invalid")
    if len(set(selected_offer_sha256s)) != len(selected_offer_sha256s):
        raise DecisionCarryoverRefused("selection_duplicate")
    offers = offer_decision_carryover(current_matches)
    selected = set(selected_offer_sha256s)
    if not selected.issubset({offer.offer_sha256 for offer in offers}):
        raise DecisionCarryoverRefused("selection_stale_or_unknown")
    return tuple(
        ConfirmedCarryoverPlan(offer, expert_user_uid)
        for offer in offers
        if offer.offer_sha256 in selected
    )
