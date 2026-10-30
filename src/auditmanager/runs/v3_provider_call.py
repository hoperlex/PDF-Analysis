"""One AR v3 provider effect, journaled under a current group-member Attempt.

The active executor still guards v3. This operation is the dispatch boundary for
its later CITE stage: only saved Run text and a verified set can create the body,
and a completed or uncertain call cannot be silently repeated.
"""

from __future__ import annotations

import math
import hashlib
import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ArtifactRef,
    ModelResponse,
    ProviderMode,
    ProxyDispatchError,
    V3GenerationSettings,
    CostMeter,
    pinned_models,
    request_cost_upper_usd,
    require_approved_model,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.executor import _publication_store
from auditmanager.runs.provider import ProviderBinding
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.cost_policy import RunCostPolicy
from auditmanager.runs.v3_execution_binding import resolve_v3_execution_binding
from auditmanager.runs.v3_execution_request import (
    V3PreparedExecutionRequest,
    prepare_v3_execution_request,
)
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import (
    BlobMetadataRepository, BlobStore, parse_blob_id, parse_blob_role,
)


REPLY_FORMAT = "ar-v3-provider-reply/1"
REPLY_ARTIFACT_ROLE = "analysis.v3_provider_reply"
REPLY_BLOB_ROLE = "analysis_v3_provider_reply"
MAX_REPLY_BYTES = 2_097_152


@dataclass(frozen=True, slots=True)
class V3ProviderCallReceipt:
    """Untrusted answer and durable call identity for the following CITE step."""

    prepared: V3PreparedExecutionRequest
    response: ModelResponse
    model_call_id: str
    provider: str
    cost_usd: float | None
    cost_basis: str
    reply_ref: ArtifactRef


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


def _publish_reply(
    session: Session, *, authority: AttemptAuthority, jobs: JobRepository,
    blobs: BlobMetadataRepository, blob_store: BlobStore,
    response: ModelResponse, model_call_id: object, provider: str,
    candidate_sha256: str, request_sha256: str,
) -> ArtifactRef:
    """Preserve the adapter's parsed answer with a committed upload breadcrumb."""
    payload = json.dumps({
        "format": REPLY_FORMAT,
        "run_id": authority.run_id,
        "model_call_id": str(model_call_id),
        "provider": provider,
        "candidate_sha256": candidate_sha256,
        "request_sha256": request_sha256,
        "response_sha256": response.response_sha256,
        "output_text": response.output_text,
        "stop_reason": response.stop_reason,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
        "reported_cost_usd": response.reported_cost_usd,
        "reported_model": response.model,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(payload) > MAX_REPLY_BYTES:
        raise _failed("the provider answer exceeds the v3 custody limit")
    digest = hashlib.sha256(payload).hexdigest()
    store = _publication_store(
        session, store=blob_store, jobs=jobs, blobs=blobs,
        authority=authority, stage_id="text_analysis",
    )
    published = store.put_blob(
        payload, declared_sha256=digest, declared_size=len(payload),
        role=parse_blob_role(REPLY_BLOB_ROLE), media_type="application/json",
    )
    if (published.sha256 != digest or published.size != len(payload)
            or store.read(parse_blob_id(str(published.blob_id)), verify=True) != payload):
        raise DomainError(
            ErrorCode.STORAGE_INTEGRITY_ERROR,
            message="v3 provider reply Blob readback differed from received answer",
            blob_id=str(published.blob_id), role=REPLY_ARTIFACT_ROLE,
        )
    return ArtifactRef(
        role=REPLY_ARTIFACT_ROLE, blob_id=str(published.blob_id),
        sha256=digest, size_bytes=len(payload), media_type="application/json",
    )


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
    blobs: BlobMetadataRepository | None = None,
    cost_policy: RunCostPolicy | None = None,
) -> V3ProviderCallReceipt:
    """Commit intent, send the exact v3 body once, then journal the received answer.

    The caller must have committed the running Run and current Job/Attempt. There
    is no retry here. A process lost after intent leaves a recoverable uncertain
    effect; it must never cause the caller to dispatch the same Run again.
    """
    job_repo = jobs or JobRepository()
    run_repo = runs or RunRepository()
    blob_repo = blobs or BlobMetadataRepository()
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
    if cost_policy is not None and cost_policy.approved:
        from dataclasses import replace
        approved_config = replace(config, approved_cost_ceiling=True,
            approved_model_id=cost_policy.model_id, approved_rate_sha256=cost_policy.rate_sha256,
            approved_connection_revision_id=cost_policy.connection_revision_id)
        pin = next((row for row in pinned_models() if row.model_id == request.model_id), None)
        if pin is None:
            raise _refuse("cost_model_price_unavailable")
        require_approved_model(approved_config, pin, call)
        prior = run_repo.cost(session, authority.run_id)
        CostMeter(ceiling_usd=cost_policy.ceiling_usd,
            spent_usd=0 if prior is None else prior.cost_micros / 1_000_000,
            enforce_ceiling=cost_policy.enforce_ceiling).check_before_call(
                pending_cost_usd=request_cost_upper_usd(pin, request))
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
            lock_authority=False,
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

    if (type(response.input_tokens) is not int or response.input_tokens < 0
            or type(response.output_tokens) is not int or response.output_tokens < 0
            or type(response.latency_ms) is not int or response.latency_ms < 0
            or not isinstance(response.output_text, str)
            or not isinstance(response.stop_reason, str)):
        raise _failed("the provider returned invalid usage counters")
    reported = response.reported_cost_usd
    if reported is not None and (
        isinstance(reported, bool) or not isinstance(reported, (int, float))
        or not math.isfinite(reported) or reported < 0
    ):
        raise _failed("the provider returned an invalid cost amount")
    reply_ref = _publish_reply(
        session, authority=authority, jobs=job_repo, blobs=blob_repo,
        blob_store=blob_store, response=response, model_call_id=model_call_id,
        provider=provider_label, candidate_sha256=prepared.candidate_sha256,
        request_sha256=prepared.provider_body_sha256,
    )
    if resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    ) != prepared.binding:
        raise _refuse("group_binding_changed_after_response")
    if mode is ProviderMode.LIVE and response.model != call.expected_model:
        raise DomainError(
            ErrorCode.MODEL_IDENTITY_MISMATCH,
            message="the provider reply did not name the pinned model",
        )
    unmetered = call is not None and call.unmetered
    cost_usd = 0.0 if unmetered else reported
    basis = "unmetered" if unmetered else "measured" if reported is not None else "estimated"
    status = "truncated" if response.truncated else "succeeded"
    job_repo.complete_provider_call(session, authority, call={
        "model_call_id": str(model_call_id),
        "provider": provider_label,
        "model_id": request.model_id,
        "provider_mode": mode.value,
        "parameters": {
            **parameters,
            "ar_v3_reply_blob_id": reply_ref.blob_id,
            "ar_v3_reply_blob_sha256": reply_ref.sha256,
            "ar_v3_reply_blob_size": reply_ref.size_bytes,
        },
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
        reply_ref=reply_ref,
    )


__all__ = ["V3ProviderCallReceipt", "dispatch_v3_provider_call"]
