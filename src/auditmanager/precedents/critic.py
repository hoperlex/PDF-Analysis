"""The critic's records for a finding: was it reviewed, and did the critic veto a cancel (`plan-v5` 2.4, V3).

A text finding is linked to the candidates whose sources include its ``primary_text_<key>``; a candidate-finding is linked through its
``extended_observation_ref``. A finding is *reviewed* when at least one linked candidate carries a critic record. The critic *vetoes* when
any linked candidate was given ``accept`` or ``needs_human``. A finding with no linked record was not reviewed, and V3 says it never gets
the cancel queue: its rejection labels are shown neutrally.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from auditmanager.precedents.models import CRITIC_VETO_DECISIONS, CONTEXT_PRECEDENTS, CriticCandidate, FindingContext


@dataclass(frozen=True, slots=True)
class CriticReview:
    """What the critic did about one finding. ``linked`` keeps every linked candidate, reviewed or not."""

    linked: tuple[CriticCandidate, ...]
    reviewed: bool
    veto: bool
    context_kinds: frozenset[str]

    @property
    def saw_precedents(self) -> bool:
        """True when a linked record was made with precedents in its context (never, while the critic gets norms only: V1)."""
        return CONTEXT_PRECEDENTS in self.context_kinds


def link_candidates(finding: FindingContext, candidates: Sequence[CriticCandidate]) -> tuple[CriticCandidate, ...]:
    """The candidates this finding stands on, in the given order, each once."""
    linked: list[CriticCandidate] = []
    for candidate in candidates:
        by_source = finding.primary_source_id is not None and finding.primary_source_id in candidate.source_ids
        by_reference = finding.extended_observation_ref is not None and finding.extended_observation_ref == candidate.candidate_id
        if by_source or by_reference:
            linked.append(candidate)
    return tuple(linked)


def review_of(finding: FindingContext, candidates: Sequence[CriticCandidate]) -> CriticReview:
    linked = link_candidates(finding, candidates)
    recorded = tuple(candidate for candidate in linked if candidate.decision is not None)
    kinds: frozenset[str] = frozenset().union(*(candidate.context_kinds for candidate in recorded))
    return CriticReview(
        linked=linked,
        reviewed=bool(recorded),
        veto=any(candidate.decision in CRITIC_VETO_DECISIONS for candidate in recorded),
        context_kinds=kinds,
    )
