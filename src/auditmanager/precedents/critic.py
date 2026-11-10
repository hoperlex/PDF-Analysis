"""The critic's records for a finding: was it reviewed, and did the critic veto a cancel (`plan-v5` 2.4, V3).

A text finding is linked to the candidates whose sources include its ``primary_text_<key>``; a candidate-finding is linked through its
``extended_observation_ref``. A finding is *reviewed* when the critic took part in the run's plan **and** at least one linked candidate
carries a critic record: :func:`critic_reviewed` is the only place that decides it, so V3 and the owner's ruling (a run whose plan has no
critic counts as «not reviewed») can change in one place. The critic *vetoes* when a reviewed finding has a linked candidate given ``accept`` or
``needs_human``. A finding that was not reviewed never gets the cancel queue: its rejection labels are shown neutrally.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from auditmanager.precedents.models import CONTEXT_PRECEDENTS, CRITIC_VETO_DECISIONS, CriticCandidate, FindingContext


def critic_reviewed(review: CriticReview) -> bool:
    """The single check of V3: the critic is in the run's plan, and a linked candidate carries its record.

    A run whose plan has no critic counts as not reviewed for every one of its findings, even if some record were linked by mistake: the
    caller says whether a critic took part, and nothing here ties that to a plan version. What counts as a critic record, and as a veto,
    is decided by whoever builds the :class:`CriticCandidate` values.
    """
    return review.critic_in_plan and bool(review.recorded)


@dataclass(frozen=True, slots=True)
class CriticReview:
    """What the critic did about one finding. ``linked`` keeps every linked candidate, recorded or not."""

    critic_in_plan: bool
    linked: tuple[CriticCandidate, ...]

    @property
    def recorded(self) -> tuple[CriticCandidate, ...]:
        return tuple(candidate for candidate in self.linked if candidate.decision is not None)

    @property
    def reviewed(self) -> bool:
        return critic_reviewed(self)

    @property
    def veto(self) -> bool:
        return self.reviewed and any(candidate.decision in CRITIC_VETO_DECISIONS for candidate in self.recorded)

    @property
    def context_kinds(self) -> frozenset[str]:
        if not self.reviewed:
            return frozenset()
        return frozenset().union(*(candidate.context_kinds for candidate in self.recorded))

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


def review_of(finding: FindingContext, candidates: Sequence[CriticCandidate], *, critic_in_plan: bool) -> CriticReview:
    return CriticReview(critic_in_plan=critic_in_plan, linked=link_candidates(finding, candidates))
