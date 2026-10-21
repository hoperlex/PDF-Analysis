"""Finish a typed AR v2 model response without provider or persistence I/O.

The response may come from an authorized recorded adapter later. This pure
step parses proposals, requires complete PDF evidence and then numbers only
accepted proposals for deterministic merge. It never creates expert verdicts.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.analysis.profiles.ar_v2.merge_input import MergePreparation, prepare_merge
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
    ProposalGroundingResult,
    ground_proposals,
)
from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v2.response import parse_response
from auditmanager.analysis.text.adapter import ModelResponse
from auditmanager.analysis.text.anchors import BlockIndex
from auditmanager.analysis.text.textlayer import TextLayer


@dataclass(frozen=True, slots=True)
class FinishedV2Response:
    response_sha256: str
    truncated: bool
    grounding: ProposalGroundingResult
    merge: MergePreparation


def finish_response(
    response: ModelResponse,
    text_layer: TextLayer,
    *,
    recognised_context: tuple[RecognisedContext, ...] = (),
    block_index: BlockIndex | None = None,
) -> FinishedV2Response:
    """Connect the declared parser, PDF grounding gate and merge preparation.

    `ModelResponse.truncated` is the provider's explicit max-token signal.
    Invalid untruncated JSON is refused; no caller can turn a malformed body
    into a partial success by guessing from the text. The full diagnostic
    partition remains available to the later runtime report.
    """
    parsed = parse_response(response.output_text, truncated=response.truncated)
    grounding = ground_proposals(
        parsed,
        text_layer,
        recognised_context=recognised_context,
        block_index=block_index,
    )
    return FinishedV2Response(
        response_sha256=response.response_sha256,
        truncated=response.truncated,
        grounding=grounding,
        merge=prepare_merge(grounding),
    )
