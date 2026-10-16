"""Pure AR v3 PDF-first and norm-second proposal grounding.

An accepted value is only a candidate. This module cannot prove that supplied
paragraphs and prompt labels came from a verified pinned retrieval-set Blob;
the later CITE caller must establish that custody before using the result.
No finding, stage result or certified citation partition is written here.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.profiles.ar_v2.grounding import resolve_v2_anchor
from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.response import ParsedResponse, ProposedObservation
from auditmanager.analysis.profiles.ar_v3.response_schema import (
    NONNORMATIVE_CATEGORIES,
    NORMATIVE_CATEGORIES,
)
from auditmanager.analysis.text.anchors import BlockIndex, ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.textlayer import TextLayer
from auditmanager.norms.public import (
    GroundedNormCitation,
    NormCitation,
    NormLabelBinding,
    NormParagraph,
    ground_norm_observation,
)


@dataclass(frozen=True, slots=True)
class GroundedV3Candidate:
    proposal_ordinal: int
    proposal: ProposedObservation
    evidence: tuple[ResolvedAnchor, ...]
    norm_citations: tuple[GroundedNormCitation, ...]


@dataclass(frozen=True, slots=True)
class RejectedV3Proposal:
    proposal_ordinal: int
    reason: str


@dataclass(frozen=True, slots=True)
class V3GroundingResult:
    accepted: tuple[GroundedV3Candidate, ...]
    rejected: tuple[RejectedV3Proposal, ...]
    malformed_count: int
    salvaged: bool


def _validate_proposal_shape(proposal: ProposedObservation) -> bool:
    """Recheck the category partition before running either pure gate."""
    if not isinstance(proposal, ProposedObservation) or not proposal.evidence:
        raise ValueError("v3_parsed_proposal_required")
    normative = proposal.category in NORMATIVE_CATEGORIES
    if normative:
        if (not proposal.norm_citations or not 1 <= len(proposal.norm_citations) <= 5
                or proposal.required_value is None or proposal.stated_value is None):
            raise ValueError("v3_normative_proposal_shape_invalid")
    elif proposal.category in NONNORMATIVE_CATEGORIES:
        if (proposal.norm_citations is not None or proposal.required_value is not None
                or proposal.stated_value is not None):
            raise ValueError("v3_nonnormative_proposal_shape_invalid")
    else:
        raise ValueError("v3_proposal_category_invalid")
    return normative


def ground_v3_proposals(
    parsed: ParsedResponse,
    text_layer: TextLayer,
    *,
    paragraphs: tuple[NormParagraph, ...],
    label_bindings: tuple[NormLabelBinding, ...],
    recognised_context: tuple[RecognisedContext, ...] = (),
    block_index: BlockIndex | None = None,
) -> V3GroundingResult:
    """Withhold any proposal whose PDF evidence or normative claim fails.

    Paragraphs and labels must be derived from the exact pinned set by a later
    custody-aware caller; accepting synthetic input here grants no authority.
    """
    if not isinstance(parsed, ParsedResponse):
        raise ValueError("v3_parsed_response_required")
    page_numbers = set(text_layer.page_numbers)
    if any(item.page_number not in page_numbers for item in recognised_context):
        raise ValueError("recognised_page_absent_from_text_layer")
    accepted: list[GroundedV3Candidate] = []
    rejected: list[RejectedV3Proposal] = []
    for ordinal, proposal in enumerate(parsed.observations):
        normative = _validate_proposal_shape(proposal)
        anchors: list[ResolvedAnchor] = []
        first_failure: str | None = None
        for evidence in proposal.evidence:
            resolved = resolve_v2_anchor(
                text_layer, page_number=evidence.page_number, quote=evidence.quote,
                recognised_context=recognised_context, block_index=block_index,
            )
            if isinstance(resolved, UnresolvedAnchor):
                if first_failure is None:
                    first_failure = resolved.reason
            else:
                anchors.append(resolved)
        if first_failure is not None:
            rejected.append(RejectedV3Proposal(ordinal, first_failure))
            continue
        grounded: tuple[GroundedNormCitation, ...] = ()
        if normative:
            assert proposal.norm_citations is not None
            assert proposal.required_value is not None
            assert proposal.stated_value is not None
            result = ground_norm_observation(
                paragraphs,
                tuple(NormCitation(item.label, item.quote) for item in proposal.norm_citations),
                proposal.required_value,
                proposal.stated_value,
                tuple(anchor.quote for anchor in anchors),
                label_bindings=label_bindings,
            )
            if not result.accepted:
                assert result.reason is not None
                rejected.append(RejectedV3Proposal(ordinal, result.reason))
                continue
            grounded = result.citations
        accepted.append(GroundedV3Candidate(ordinal, proposal, tuple(anchors), grounded))
    return V3GroundingResult(
        tuple(accepted), tuple(rejected), parsed.malformed_count, parsed.salvaged,
    )
