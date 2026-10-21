"""Prepare the pure merge artifact from complete, PDF-grounded AR v2 proposals.

The merge rule numbers observations in the filtered run artifact. Parser
ordinals remain available for diagnostics, but rejected proposals must never
occupy a merge ordinal or become a group member.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.profiles.ar_v2.proposal_grounding import ProposalGroundingResult
from auditmanager.analysis.stages.finding_merge import (
    MergeEvidence,
    MergeObservation,
    merge_grounded,
)


@dataclass(frozen=True, slots=True)
class MergePreparation:
    """Merge artifact and its dense-ordinal to source-proposal correspondence."""

    source_proposal_ordinals: tuple[int, ...]
    artifact: dict[str, object]


def prepare_merge(grounding: ProposalGroundingResult) -> MergePreparation:
    """Number only accepted proposals, then apply the deterministic merge rule.

    A malformed hand-built grounding result is refused. The normal caller is
    ``ground_proposals``, which supplies the complete accepted/rejected
    partition and already verifies PDF text-layer offsets.
    """
    accepted_ordinals = [item.proposal_ordinal for item in grounding.accepted]
    rejected_ordinals = [item.proposal_ordinal for item in grounding.rejected]
    all_ordinals = accepted_ordinals + rejected_ordinals
    if sorted(all_ordinals) != list(range(len(all_ordinals))):
        raise ValueError("grounding_proposal_ordinals_not_partitioned")
    if accepted_ordinals != sorted(accepted_ordinals):
        raise ValueError("accepted_proposals_out_of_order")

    observations: list[MergeObservation] = []
    for observation_ordinal, item in enumerate(grounding.accepted):
        if not item.evidence or len(item.evidence) != len(item.proposal.evidence):
            raise ValueError("accepted_proposal_has_incomplete_evidence")
        observations.append(
            MergeObservation(
                observation_ordinal=observation_ordinal,
                category=item.proposal.category,
                evidence=tuple(
                    MergeEvidence(
                        page_number=anchor.page_number,
                        char_start=anchor.char_start,
                        char_end=anchor.char_end,
                        quote=anchor.quote,
                    )
                    for anchor in item.evidence
                ),
            )
        )
    return MergePreparation(
        source_proposal_ordinals=tuple(accepted_ordinals),
        artifact=merge_grounded(observations),
    )
