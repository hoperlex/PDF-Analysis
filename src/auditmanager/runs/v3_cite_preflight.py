"""Rebuild saved AR v3 evidence before a later CITE publication transaction.

This read-only bridge never dispatches a provider or decides a finding. The
caller owns the transaction and must recheck authority when writing a stage.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ArtifactRef, RecognisedContext, V3GenerationSettings,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository, V3CompletedCall
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_citations import (
    V3BetaCitationReview, plan_v3_beta_citation_review,
)
from auditmanager.runs.v3_execution_request import (
    V3PreparedExecutionRequest, fence_v3_execution_request,
    prepare_v3_execution_request,
)
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.runs.v3_provider_call import REPLY_ARTIFACT_ROLE
from auditmanager.runs.v3_reply_custody import (
    V3RecoveredReply, V3ReplyExpectation, read_v3_reply,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore


@dataclass(frozen=True, slots=True)
class V3CitePreflight:
    prepared: V3PreparedExecutionRequest
    completed_call: V3CompletedCall
    recovered_reply: V3RecoveredReply
    review: V3BetaCitationReview


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved AR v3 request and provider evidence do not agree",
        stage_id="text_analysis", reason=reason,
    )


def prepare_v3_cite_preflight(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    blob_store: BlobStore,
    max_text_bytes: int,
    recognised_context: tuple[RecognisedContext, ...] = (),
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
) -> V3CitePreflight:
    """Pair one saved call and reply with the current Run's exact text and set.

    The generation settings come from the completed effect/call pair. Their
    rebuilt provider-body digest must match the saved call after a restart.
    Early call and request reads are provisional. Only after both external
    Blobs and grounding does one final transaction lock and compare their
    saved DB witnesses before the caller may publish a stage.
    """
    job_repo = jobs or JobRepository()
    call = job_repo.completed_v3_call(
        session, authority, lock_authority=False,
    )
    if call.run_id != authority.run_id or call.job_id != authority.job_id:
        raise _refuse("completed_call_owner_mismatch")
    settings = V3GenerationSettings(
        call.max_output_tokens, call.effort, {"type": "adaptive"},
    )
    prepared = prepare_v3_execution_request(
        session, authority=authority, registry=registry, blob_store=blob_store,
        max_text_bytes=max_text_bytes, expected_provider_mode=call.provider_mode,
        model_identity=call.model_id, settings=settings,
        idempotency_scope=authority.run_id, recognised_context=recognised_context,
        jobs=job_repo, runs=runs, documents=documents,
        defer_final_fence=True,
    )
    binding = prepared.binding
    if (binding.run_id != call.run_id
            or binding.scope_id != call.scope_id
            or binding.set_sha256 != call.set_sha256
            or binding.provider_mode != call.provider_mode
            or prepared.candidate_sha256 != call.candidate_sha256
            or prepared.provider_body_sha256 != call.request_sha256):
        raise _refuse("saved_request_call_mismatch")

    reference = ArtifactRef(
        role=REPLY_ARTIFACT_ROLE, blob_id=call.reply_blob_id,
        sha256=call.reply_blob_sha256, size_bytes=call.reply_blob_size,
        media_type="application/json",
    )
    reply = read_v3_reply(
        blob_store, reference=reference,
        expected=V3ReplyExpectation(
            run_id=authority.run_id, model_call_id=call.model_call_id,
            provider=call.provider, candidate_sha256=call.candidate_sha256,
            request_sha256=call.request_sha256,
            response_sha256=call.response_sha256,
        ),
    )
    response = reply.model_response
    if (call.status != "succeeded" or response.truncated):
        raise _refuse("saved_reply_incomplete")
    if (response.input_tokens != call.input_tokens
            or response.output_tokens != call.output_tokens
            or response.latency_ms != call.latency_ms
            or (call.provider_mode == "live" and (
                not isinstance(response.model, str) or not response.model.strip()
            ))
            or (call.cost_basis == "measured" and (
                response.reported_cost_usd is None
                or int(round(response.reported_cost_usd * 1_000_000))
                != call.cost_micros
            ))
            or (call.cost_basis == "estimated"
                and response.reported_cost_usd is not None)):
        raise _refuse("saved_reply_call_facts_mismatch")
    review = plan_v3_beta_citation_review(
        prepared.pinned_corpus, reply.supplied_response,
        prepared.saved_text.text_layer,
    )
    fence_v3_execution_request(
        session, authority=authority, registry=registry, prepared=prepared,
        jobs=job_repo, runs=runs, documents=documents,
    )
    if job_repo.completed_v3_call(session, authority) != call:
        raise _refuse("saved_evidence_changed_during_review")
    return V3CitePreflight(prepared, call, reply, review)


__all__ = ["V3CitePreflight", "prepare_v3_cite_preflight"]
