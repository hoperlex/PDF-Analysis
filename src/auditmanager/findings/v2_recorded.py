"""Recorded-only AR v2 response to transactional finding publication.

The caller supplies a response, the exact PDF text layer and a transaction.
This is an opt-in development seam; it does not select a provider, start a run,
commit the outer transaction or turn a proposal into an expert decision.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    BlockIndex,
    FinishedV2Response,
    ModelResponse,
    RecognisedContext,
    TextLayer,
    finish_response,
)
from auditmanager.findings.merge_publication_plan import plan_v2_merge_publication
from auditmanager.findings.v2_publication import (
    V2PublicationContext,
    V2PublicationResult,
    publish_v2_merge_plan,
)


@dataclass(frozen=True, slots=True)
class RecordedV2Result:
    finished: FinishedV2Response
    publication: V2PublicationResult


def publish_recorded_v2_response(
    session: Session,
    *,
    response: ModelResponse,
    text_layer: TextLayer,
    context: V2PublicationContext,
    recognised_context: tuple[RecognisedContext, ...] = (),
    block_index: BlockIndex | None = None,
) -> RecordedV2Result:
    """Ground, merge and write one recorded response in the caller's unit of work.

    A valid but truncated response may contain complete salvageable proposals;
    ``finish_response`` decides that partition. No ID is allocated until its
    deterministic merge has been checked by ``plan_v2_merge_publication``.
    """
    if not isinstance(context, V2PublicationContext) or context.provider_mode != "recorded":
        raise ValueError("recorded_v2_context_required")
    finished = finish_response(
        response,
        text_layer,
        recognised_context=recognised_context,
        block_index=block_index,
    )
    plan = plan_v2_merge_publication(finished.grounding, finished.merge)
    publication = publish_v2_merge_plan(session, plan=plan, context=context)
    return RecordedV2Result(finished, publication)


__all__ = ["RecordedV2Result", "publish_recorded_v2_response"]
