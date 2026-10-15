"""Validate an AR v2 merge before any finding identity is allocated.

The plan is a pure input to a later transactional publisher. It retains every
accepted member, the original proposal ordinals and rejected diagnostics;
neither a model response nor an artifact can allocate a finding or a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.public import (
    MERGE_ARTIFACT_ROLE,
    MERGE_ARTIFACT_VERSION,
    MERGE_RULE_VERSION,
    MergePreparation,
    ProposalGroundingResult,
    ProposedObservation,
    RejectedProposal,
    ResolvedAnchor,
    prepare_merge,
)


@dataclass(frozen=True, slots=True)
class PlannedObservation:
    observation_ordinal: int
    source_proposal_ordinal: int
    proposal: ProposedObservation
    evidence: tuple[ResolvedAnchor, ...]


@dataclass(frozen=True, slots=True)
class PlannedFinding:
    category: str
    canonical: PlannedObservation
    members: tuple[PlannedObservation, ...]


@dataclass(frozen=True, slots=True)
class MergePublicationPlan:
    groups: tuple[PlannedFinding, ...]
    rejected: tuple[RejectedProposal, ...]
    malformed_count: int
    salvaged: bool

    @property
    def finding_count(self) -> int:
        return len(self.groups)

    @property
    def observation_count(self) -> int:
        return sum(len(group.members) for group in self.groups)


def plan_v2_merge_publication(
    grounding: ProposalGroundingResult, merge: MergePreparation
) -> MergePublicationPlan:
    """Require a total, rule-consistent partition of the accepted proposals.

    The publisher can insert one finding per group, insert all its members with
    that finding UID, then set the canonical observation ID in one savepoint.
    Rejected proposals stay diagnostic records, without a group or finding UID.
    """
    if not isinstance(grounding, ProposalGroundingResult) or not isinstance(merge, MergePreparation):
        raise ValueError("v2_merge_inputs_required")

    accepted = grounding.accepted
    rejected = grounding.rejected
    source_ordinals = tuple(item.proposal_ordinal for item in accepted)
    all_ordinals = (*source_ordinals, *(item.proposal_ordinal for item in rejected))
    if any(type(ordinal) is not int for ordinal in all_ordinals) or sorted(all_ordinals) != list(range(len(all_ordinals))):
        raise ValueError("proposal_ordinals_not_partitioned")
    if source_ordinals != tuple(sorted(source_ordinals)):
        raise ValueError("accepted_proposals_out_of_order")
    if merge.source_proposal_ordinals != source_ordinals:
        raise ValueError("merge_source_ordinals_mismatch")
    if any(not item.failures for item in rejected):
        raise ValueError("rejected_proposal_without_diagnostic")

    observations: list[PlannedObservation] = []
    for ordinal, item in enumerate(accepted):
        if not item.evidence or len(item.evidence) != len(item.proposal.evidence):
            raise ValueError("accepted_proposal_has_incomplete_evidence")
        observations.append(
            PlannedObservation(ordinal, item.proposal_ordinal, item.proposal, item.evidence)
        )

    artifact = merge.artifact
    if not isinstance(artifact, dict) or set(artifact) != {"artifact_role", "artifact_version", "groups"}:
        raise ValueError("merge_artifact_shape_invalid")
    if artifact["artifact_role"] != MERGE_ARTIFACT_ROLE or artifact["artifact_version"] != MERGE_ARTIFACT_VERSION:
        raise ValueError("merge_artifact_version_mismatch")
    raw_groups = artifact["groups"]
    if not isinstance(raw_groups, list):
        raise ValueError("merge_groups_invalid")

    seen: set[int] = set()
    groups: list[PlannedFinding] = []
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict) or set(raw_group) != {
            "observation_ordinals", "canonical_ordinal", "merge_rule_version"
        }:
            raise ValueError("merge_group_shape_invalid")
        if raw_group["merge_rule_version"] != MERGE_RULE_VERSION:
            raise ValueError("merge_rule_version_mismatch")
        ordinals = raw_group["observation_ordinals"]
        if (not isinstance(ordinals, list) or not ordinals
                or any(type(ordinal) is not int or ordinal < 0 or ordinal >= len(observations)
                       for ordinal in ordinals)):
            raise ValueError("merge_group_member_invalid")
        if ordinals != sorted(set(ordinals)) or seen.intersection(ordinals):
            raise ValueError("merge_group_member_duplicate")
        seen.update(ordinals)
        canonical_ordinal = raw_group["canonical_ordinal"]
        if type(canonical_ordinal) is not int or canonical_ordinal not in ordinals:
            raise ValueError("merge_canonical_not_in_group")
        members = tuple(observations[ordinal] for ordinal in ordinals)
        category = members[0].proposal.category
        if any(member.proposal.category != category for member in members):
            raise ValueError("merge_group_category_mismatch")

        def canonical_key(member: PlannedObservation) -> tuple[int, int, int]:
            first = min((item.page_number, item.char_start) for item in member.evidence)
            return (*first, member.observation_ordinal)

        canonical = observations[canonical_ordinal]
        if canonical != min(members, key=canonical_key):
            raise ValueError("merge_canonical_rule_mismatch")
        groups.append(PlannedFinding(category, canonical, members))

    if seen != set(range(len(observations))):
        raise ValueError("merge_members_not_total")
    # A well-shaped but forged grouping must not merge unrelated observations.
    if artifact != prepare_merge(grounding).artifact:
        raise ValueError("merge_artifact_rule_mismatch")
    return MergePublicationPlan(tuple(groups), rejected, grounding.malformed_count, grounding.salvaged)
