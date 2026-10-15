"""Rejected AR v2 proposals cannot enter the deterministic merge artifact."""

from __future__ import annotations

import pytest

from auditmanager.analysis.profiles.ar_v2.merge_input import prepare_merge
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
    GroundedProposal,
    ProposalGroundingResult,
    ground_proposals,
)
from auditmanager.analysis.profiles.ar_v2.response import (
    ParsedResponse,
    ProposedEvidence,
    ProposedObservation,
)
from auditmanager.analysis.text.textlayer import Page, TextLayer


def _proposal(*evidence: tuple[int, str]) -> ProposedObservation:
    return ProposedObservation(
        category="dimensions",
        finding_text="Сверить указанные размеры",
        recommendation_text="Уточнить размер в проекте",
        proposed_severity="operational",
        evidence=tuple(ProposedEvidence(page, quote) for page, quote in evidence),
    )


def _layer() -> TextLayer:
    text = "Стена А имеет толщину 200 мм. Окно Б имеет ширину 1200 мм."
    return TextLayer(
        version_uid="ver_merge_input",
        normalization_id="NFC",
        pages=(Page(1, 0, len(text), text),),
        document_text=text,
    )


def test_rejected_quote_never_becomes_a_merge_member() -> None:
    parsed = ParsedResponse(
        observations=(
            _proposal((1, "Стена А имеет толщину 200 мм")),
            _proposal((1, "Стена А имеет толщину 200 мм"), (1, "нет в PDF")),
            _proposal((1, "Стена А имеет толщину 200 мм")),
            _proposal((1, "Окно Б имеет ширину 1200 мм")),
        ),
        salvaged=True,
        malformed_count=1,
    )
    grounding = ground_proposals(parsed, _layer())
    assert [item.proposal_ordinal for item in grounding.rejected] == [1]

    result = prepare_merge(grounding)
    assert result.source_proposal_ordinals == (0, 2, 3)
    assert result.artifact == {
        "artifact_role": "findings.merged",
        "artifact_version": "1.0.0",
        "groups": [
            {
                "observation_ordinals": [0, 1],
                "canonical_ordinal": 0,
                "merge_rule_version": "1.0.0",
            },
            {
                "observation_ordinals": [2],
                "canonical_ordinal": 2,
                "merge_rule_version": "1.0.0",
            },
        ],
    }


def test_all_rejected_yields_an_empty_merge_artifact() -> None:
    grounding = ground_proposals(
        ParsedResponse((_proposal((1, "нет в PDF")),), False, 0), _layer()
    )
    result = prepare_merge(grounding)
    assert result.source_proposal_ordinals == ()
    assert result.artifact["groups"] == []


def test_hand_built_incomplete_grounding_is_refused() -> None:
    grounding = ground_proposals(
        ParsedResponse((_proposal((1, "Стена А имеет толщину 200 мм")),), False, 0),
        _layer(),
    )
    accepted = grounding.accepted[0]
    with pytest.raises(ValueError, match="incomplete_evidence"):
        prepare_merge(
            ProposalGroundingResult(
                accepted=(GroundedProposal(0, accepted.proposal, ()),),
                rejected=(),
                malformed_count=0,
                salvaged=False,
            )
        )
    with pytest.raises(ValueError, match="not_partitioned"):
        prepare_merge(
            ProposalGroundingResult(
                accepted=(accepted, accepted),
                rejected=(),
                malformed_count=0,
                salvaged=False,
            )
        )
