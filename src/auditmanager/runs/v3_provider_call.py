"""One AR v3 provider effect, journaled under a current group-member Attempt.

The active executor still guards v3. This operation is the dispatch boundary for
its later CITE stage: only saved Run text and a verified set can create the body,
and a completed or uncertain call cannot be silently repeated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ModelResponse,
    ProviderMode,
    ProxyDispatchError,
    V3GenerationSettings,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.provider import ProviderBinding
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_execution_binding import resolve_v3_execution_binding
from auditmanager.runs.v3_execution_request import (
    V3PreparedExecutionRequest,
    prepare_v3_execution_request,
)
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore


@dataclass(frozen=True, slots=True)
class V3ProviderCallReceipt:
    """Untrusted answer and durable call identity for the following CITE step."""

    prepared: V3PreparedExecutionRequest
    response: ModelResponse
    model_call_id: str
    provider: str
    cost_usd: float | None
    cost_basis: str


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.REQUIRED_NORM_UNAVAILABLE,
        reference_kind="norm_retrieval_set",
        reason=reason,
    )


def _failed(message: str) -> DomainError:
    return DomainError(ErrorCode.ANALYSIS_FAILED, message=message, stage_id="text_analysis")


def _record_failure(
    session: Session, jobs: JobRepository, authority: AttemptAuthority,
    model_call_id: object, error: Exception, mode: ProviderMode,
) -> None:
    code = error.code.value if isinstance(error, DomainError) else ErrorCode.ANALYSIS_FAILED.value
    if mode is ProviderMode.RECORDED:
        jobs.record_provider_not_processed(
            session, authority, model_call_id=model_call_id,
            error_code=code, dispatch_class="not_sent",
        )
    elif isinstance(error, ProxyDispatchError) and error.received is not None:
        jobs.record_provider_response(
            session, authority, model_call_id=model_call_id,
            response_sha256=error.received.response_sha256,
            input_tokens=error.received.input_tokens,
            output_tokens=error.received.output_tokens,
            latency_ms=error.received.latency_ms,
        )
    elif (isinstance(error, ProxyDispatchError)
          and error.dispatch_class in {
              "not_sent", "rate_limited", "proxy_unavailable", "definite_refusal",
          }):
        jobs.record_provider_not_processed(
            session, authority, model_call_id=model_call_id,
            error_code=code, dispatch_class=error.dispatch_class,
        )
    else:
        jobs.record_provider_unknown(
            session, authority, model_call_id=model_call_id, error_code=code,
        )
    session.commit()


def dispatch_v3_provider_call(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    blob_store: BlobStore,
    max_text_bytes: int,
    provider: ProviderBinding,
    settings: V3GenerationSettings,
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
) -> V3ProviderCallReceipt:
    """Commit intent, send the exact v3 body once, then journal the received answer.

    The caller must have committed the running Run and current Job/Attempt. There
    is no retry here. A process lost after intent leaves a recoverable uncertain
    effect; it must never cause the caller to dispatch the same Run again.
    """
    job_repo = jobs or JobRepository()
    run_repo = runs or RunRepository()
    adapter, config, call = provider.adapter, provider.config, provider.call
    mode = adapter.provider_mode
    if (mode not in {ProviderMode.LIVE, ProviderMode.RECORDED}
            or config.mode is not mode
            or not isinstance(config.model_id, str)
            or not config.model_id
            or config.model_id.lower() in {"proxy", "default", "auto", "unknown", "stub"}):
        raise _refuse("provider_binding_invalid")
    if mode is ProviderMode.LIVE and (
        call is None or not call.check_identity
        or not isinstance(call.expected_model, str) or not call.expected_model.strip()
        or call.expected_model.lower() in {"proxy", "default", "auto", "unknown"}
    ):
        raise _refuse("model_identity_unpinned")
    provider_label = "anthropic" if call is None else call.provider_label
    if not isinstance(provider_label, str) or not provider_label:
        raise _refuse("provider_label_invalid")

    prepared = prepare_v3_execution_request(
        session, authority=authority, registry=registry, blob_store=blob_store,
        max_text_bytes=max_text_bytes, expected_provider_mode=mode.value,
        model_identity=config.model_id, settings=settings,
        idempotency_scope=authority.run_id, jobs=job_repo, runs=run_repo,
        documents=documents,
    )
    job_repo.require_current(session, authority)
    job_repo.require_recorded_stage_call_available(session, authority)
    if resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    ) != prepared.binding:
        raise _refuse("group_binding_changed_before_intent")

    request = prepared.model_request
    parameters = {
        **request.parameters,
        "ar_v3_candidate_sha256": prepared.candidate_sha256,
        "ar_v3_scope_id": prepared.binding.scope_id,
        "ar_v3_set_sha256": prepared.binding.set_sha256,
    }
    model_call_id = job_repo.prepare_provider_call(
        session, authority, provider=provider_label,
        model_identity=request.model_id, provider_mode=mode.value,
        parameters=parameters, request_sha256=prepared.provider_body_sha256,
        connection_revision_id=None if call is None else call.connection_revision_id,
        identity_basis=None if call is None else call.identity_basis,
    )
    session.commit()  # intent is durable before the first provider effect

    try:
        if resolve_v3_execution_binding(
            session, authority=authority, registry=registry, jobs=job_repo,
        ) != prepared.binding:
            raise _refuse("group_binding_changed_before_dispatch")
    except Exception as error:
        job_repo.record_provider_not_processed(
            session, authority, model_call_id=model_call_id,
            error_code=(error.code.value if isinstance(error, DomainError)
                        else ErrorCode.ANALYSIS_FAILED.value),
            dispatch_class="not_sent",
        )
        session.commit()
        raise

    try:
        response = adapter.complete(request)
    except Exception as error:
        _record_failure(session, job_repo, authority, model_call_id, error, mode)
        raise
    if not isinstance(response, ModelResponse):
        error = _failed("the provider returned an invalid response shape")
        _record_failure(session, job_repo, authority, model_call_id, error, mode)
        raise error
    job_repo.record_provider_response(
        session, authority, model_call_id=model_call_id,
        response_sha256=response.response_sha256,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
    )
    session.commit()  # answer evidence survives a later identity/CITE refusal

    if resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    ) != prepared.binding:
        raise _refuse("group_binding_changed_after_response")
    if mode is ProviderMode.LIVE and response.model != call.expected_model:
        raise DomainError(
            ErrorCode.MODEL_IDENTITY_MISMATCH,
            message="the provider reply did not name the pinned model",
        )
    if (type(response.input_tokens) is not int or response.input_tokens < 0
            or type(response.output_tokens) is not int or response.output_tokens < 0
            or type(response.latency_ms) is not int or response.latency_ms < 0):
        raise _failed("the provider returned invalid usage counters")
    reported = response.reported_cost_usd
    if reported is not None and (
        isinstance(reported, bool) or not isinstance(reported, (int, float))
        or not math.isfinite(reported) or reported < 0
    ):
        raise _failed("the provider returned an invalid cost amount")
    unmetered = call is not None and call.unmetered
    cost_usd = 0.0 if unmetered else reported
    basis = "unmetered" if unmetered else "measured" if reported is not None else "estimated"
    status = "truncated" if response.truncated else "succeeded"
    job_repo.complete_provider_call(session, authority, call={
        "model_call_id": str(model_call_id),
        "provider": provider_label,
        "model_id": request.model_id,
        "provider_mode": mode.value,
        "parameters": parameters,
        "request_sha256": prepared.provider_body_sha256,
        "response_sha256": response.response_sha256,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
        "status": status,
        "cost_usd": cost_usd,
        "cost_basis": basis,
    })
    session.commit()
    return V3ProviderCallReceipt(
        prepared=prepared, response=response, model_call_id=str(model_call_id),
        provider=provider_label, cost_usd=cost_usd, cost_basis=basis,
    )


__all__ = ["V3ProviderCallReceipt", "dispatch_v3_provider_call"]
