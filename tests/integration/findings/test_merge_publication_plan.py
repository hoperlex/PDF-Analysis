"""The v2 publication boundary accepts only complete, consistent merge groups."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from auditmanager.analysis.profiles.ar_v2.merge_input import prepare_merge
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
    GroundedProposal,
    ProposalGroundingResult,
    RejectedProposal,
    UnresolvedEvidence,
)
from auditmanager.analysis.profiles.ar_v2.response import ProposedEvidence, ProposedObservation
from auditmanager.analysis.text.anchors import ResolvedAnchor
from auditmanager.findings.grounding import GateResult
from auditmanager.findings.merge_publication_plan import plan_v2_merge_publication


def _accepted(source_ordinal: int, start: int, *, category: str = "dimensions") -> GroundedProposal:
    quote = "Указан размер помещения"
    proposal = ProposedObservation(
        category=category,
        finding_text=f"Проверить размер {source_ordinal}",
        recommendation_text="Сверить чертёж",
        proposed_severity="operational",
        evidence=(ProposedEvidence(1, quote),),
    )
    return GroundedProposal(
        source_ordinal, proposal, (ResolvedAnchor(1, quote, start, start + len(quote)),)
    )


def _inputs() -> tuple[ProposalGroundingResult, object]:
    grounding = ProposalGroundingResult(
        accepted=(
            _accepted(0, 10),
            _accepted(2, 15),
            _accepted(3, 80, category="layout"),
        ),
        rejected=(RejectedProposal(1, (UnresolvedEvidence(0, 1, "нет в PDF", "quotation_absent"),)),),
        malformed_count=2,
        salvaged=True,
    )
    return grounding, prepare_merge(grounding)


def _changed_groups(merge: object, change) -> object:
    artifact = deepcopy(merge.artifact)
    change(artifact["groups"])
    return replace(merge, artifact=artifact)


def test_plan_preserves_all_members_canonical_and_rejected_diagnostics() -> None:
    grounding, merge = _inputs()
    plan = plan_v2_merge_publication(grounding, merge)

    assert plan.finding_count == 2
    assert plan.observation_count == 3
    assert [(group.category, group.canonical.observation_ordinal,
             tuple(member.observation_ordinal for member in group.members))
            for group in plan.groups] == [
        ("dimensions", 0, (0, 1)), ("layout", 2, (2,)),
    ]
    assert tuple(member.source_proposal_ordinal for group in plan.groups
                 for member in group.members) == (0, 2, 3)
    assert plan.rejected == grounding.rejected
    assert plan.rejected[0].proposal_ordinal == 1
    assert plan.rejected[0].failures[0].reason == "quotation_absent"
    assert (plan.malformed_count, plan.salvaged) == (2, True)


@pytest.mark.parametrize("change,reason", [
    (lambda groups: groups[0]["observation_ordinals"].remove(1), "not_total"),
    (lambda groups: groups[1]["observation_ordinals"].append(1), "duplicate"),
    (lambda groups: groups[0].update(canonical_ordinal=2), "not_in_group"),
    (lambda groups: groups[0].update(canonical_ordinal=1), "canonical_rule_mismatch"),
    (lambda groups: groups[0]["observation_ordinals"].append(2), "category_mismatch"),
])
def test_malformed_partition_or_canonical_is_refused(change, reason: str) -> None:
    grounding, merge = _inputs()
    with pytest.raises(ValueError, match=reason):
        plan_v2_merge_publication(grounding, _changed_groups(merge, change))


def test_rejected_source_ordinal_cannot_be_relabelled_as_accepted() -> None:
    grounding, merge = _inputs()
    with pytest.raises(ValueError, match="merge_source_ordinals_mismatch"):
        plan_v2_merge_publication(grounding, replace(merge, source_proposal_ordinals=(0, 1, 3)))
    with pytest.raises(ValueError, match="merge_group_member_invalid"):
        plan_v2_merge_publication(
            grounding,
            _changed_groups(merge, lambda groups: groups[1].update(observation_ordinals=[3])),
        )


def test_linked_members_cannot_be_forged_into_separate_findings() -> None:
    grounding, merge = _inputs()
    artifact = deepcopy(merge.artifact)
    artifact["groups"] = [
        {"observation_ordinals": [0], "canonical_ordinal": 0, "merge_rule_version": "1.0.0"},
        {"observation_ordinals": [1], "canonical_ordinal": 1, "merge_rule_version": "1.0.0"},
        artifact["groups"][1],
    ]
    with pytest.raises(ValueError, match="merge_artifact_rule_mismatch"):
        plan_v2_merge_publication(grounding, replace(merge, artifact=artifact))


def test_v1_gate_result_cannot_enter_v2_planner() -> None:
    grounding, merge = _inputs()
    with pytest.raises(ValueError, match="v2_merge_inputs_required"):
        plan_v2_merge_publication(GateResult((), "NFC"), merge)
    with pytest.raises(ValueError, match="v2_merge_inputs_required"):
        plan_v2_merge_publication(grounding, GateResult((), "NFC"))


def test_empty_and_all_rejected_have_no_findings() -> None:
    empty = ProposalGroundingResult((), (), 0, False)
    rejected = ProposalGroundingResult(
        (), (RejectedProposal(0, _inputs()[0].rejected[0].failures),), 0, False
    )
    for grounding in (empty, rejected):
        plan = plan_v2_merge_publication(grounding, prepare_merge(grounding))
        assert plan.groups == ()
        assert plan.finding_count == 0
        assert plan.rejected == grounding.rejected
