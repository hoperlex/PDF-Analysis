"""Ground parsed AR v2 proposals without allowing partial evidence through.

This is a pure bridge between the response parser and the PDF quote resolver.
It creates no artifact, model identity, finding or expert verdict. In
particular, a proposal with one unresolved item is wholly absent from
``accepted`` even when its other items resolved.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.profiles.ar_shared.grounding import resolve_v2_anchor
from auditmanager.analysis.profiles.ar_shared.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v2.response import ParsedResponse, ProposedObservation
from auditmanager.analysis.text.anchors import BlockIndex, ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.textlayer import TextLayer


@dataclass(frozen=True, slots=True)
class GroundedProposal:
    """A complete proposal whose every quote has a PDF text-layer interval."""

    proposal_ordinal: int
    proposal: ProposedObservation
    evidence: tuple[ResolvedAnchor, ...]


@dataclass(frozen=True, slots=True)
class UnresolvedEvidence:
    """One failed proposed quote, ordered as it appeared in the response."""

    evidence_ordinal: int
    page_number: int
    quote: str
    reason: str


@dataclass(frozen=True, slots=True)
class RejectedProposal:
    """A whole proposal rejected because one or more quotes failed."""

    proposal_ordinal: int
    failures: tuple[UnresolvedEvidence, ...]


@dataclass(frozen=True, slots=True)
class ProposalGroundingResult:
    accepted: tuple[GroundedProposal, ...]
    rejected: tuple[RejectedProposal, ...]
    malformed_count: int
    salvaged: bool


def ground_proposals(
    parsed: ParsedResponse,
    text_layer: TextLayer,
    *,
    recognised_context: tuple[RecognisedContext, ...] = (),
    block_index: BlockIndex | None = None,
) -> ProposalGroundingResult:
    """Resolve every quote and discard all anchors of a rejected proposal.

    The parser's ordinals name positions among structurally accepted
    proposals, not positions in the raw model array. Runtime artifact
    ordinals must be assigned after this filter. All evidence is attempted,
    so a later failure is visible even when an earlier item already failed.
    """
    page_numbers = set(text_layer.page_numbers)
    if any(item.page_number not in page_numbers for item in recognised_context):
        raise ValueError("recognised_page_absent_from_text_layer")
    accepted: list[GroundedProposal] = []
    rejected: list[RejectedProposal] = []
    for proposal_ordinal, proposal in enumerate(parsed.observations):
        anchors: list[ResolvedAnchor] = []
        failures: list[UnresolvedEvidence] = []
        for evidence_ordinal, evidence in enumerate(proposal.evidence):
            result = resolve_v2_anchor(
                text_layer,
                page_number=evidence.page_number,
                quote=evidence.quote,
                recognised_context=recognised_context,
                block_index=block_index,
            )
            if isinstance(result, UnresolvedAnchor):
                failures.append(
                    UnresolvedEvidence(
                        evidence_ordinal=evidence_ordinal,
                        page_number=result.page_number,
                        quote=result.quote,
                        reason=result.reason,
                    )
                )
            else:
                anchors.append(result)
        if failures:
            rejected.append(RejectedProposal(proposal_ordinal, tuple(failures)))
        else:
            accepted.append(GroundedProposal(proposal_ordinal, proposal, tuple(anchors)))
    return ProposalGroundingResult(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        malformed_count=parsed.malformed_count,
        salvaged=parsed.salvaged,
    )
