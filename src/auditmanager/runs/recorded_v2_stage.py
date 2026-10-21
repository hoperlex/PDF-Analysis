"""Unactivated, durable recorded-only AR v2 text stage port.

The executor owns terminal selection and recovery. This port owns one successful
text-stage path under an already committed Job/Attempt: journal the exact replay,
publish and read back its observation Blob, then bind the StageResult. A failed
later step may leave a truthful call or publication intent; it never creates a
success stage result from missing evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ArtifactRef,
    ProviderConfig,
    ProviderMode,
    RecordedAdapter,
    RecordedGenerationSettings,
    StageResult,
    blob_role_for,
    build_recorded_call_facts,
    build_recorded_observation_artifact,
    replay_recorded_response,
    seal_recorded_v2_stage_result,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.executor import (
    _DurableCallJournal,
    _persist_and_bind,
    _publication_store,
)
from auditmanager.runs.recorded_v2_sources import load_recorded_v2_input
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import (
    BlobMetadataRepository,
    BlobStore,
    parse_blob_id,
)


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_recorded_v2_stage(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    adapter: RecordedAdapter,
    provider_config: ProviderConfig,
    fixture_model_id: str,
    settings: RecordedGenerationSettings,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
    documents: DocumentRepository | None = None,
    blobs: BlobMetadataRepository | None = None,
    clock: Clock = _utc_now,
) -> StageResult:
    """Persist one complete recorded replay under the caller's current Attempt.

    The caller already committed the running Run and Job/Attempt/Lease and keeps
    its lease heartbeat alive. This method commits the call intent before the
    fixture read; response and canonical call each have a durable boundary.
    Blob publication uses the existing outbox/reconciliation breadcrumbs.
    The final stage row and Blob binding commit together, after exact readback.
    Exceptions must be followed by the caller's rollback/recovery policy.
    """
    if type(adapter) is not RecordedAdapter or adapter.provider_mode is not ProviderMode.RECORDED:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the AR v2 stage requires the concrete offline recorded adapter",
            stage_id="text_analysis",
            reason="recorded_adapter_required",
        )
    if provider_config.mode is not ProviderMode.RECORDED:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the AR v2 stage requires recorded provider configuration",
            stage_id="text_analysis",
            reason="provider_mode_invalid",
        )
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    blob_repo = blobs or BlobMetadataRepository()
    run_id = authority.run_id
    # Read source Blobs before taking the Attempt's row locks. The loader
    # rechecks the saved run, source stage and version against those bytes.
    prepared = load_recorded_v2_input(
        session,
        run_id=run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
        fixture_model_id=fixture_model_id,
        settings=settings,
        runs=run_repo,
        documents=documents,
    )
    job_repo.require_current(session, authority)
    run = run_repo.get(session, run_id)
    if run.state != "running" or any(
        row.stage_id == "text_analysis" for row in run_repo.stage_results(session, run_id)
    ):
        raise DomainError(
            ErrorCode.CONFLICT,
            message="a recorded text stage requires an unfinished running run",
            aggregate_type="AuditRun",
        )
    job_repo.require_recorded_stage_call_available(session, authority)
    started_at = clock()
    run_repo.stage_started(session, run_id=run_id, stage_id="text_analysis")
    session.commit()

    journal = _DurableCallJournal(session, job_repo, authority)
    model_call_id = journal.prepare(prepared.request, mode=ProviderMode.RECORDED)
    replay = replay_recorded_response(
        prepared=prepared,
        adapter=adapter,
        expected_request_sha256=prepared.request_sha256,
        expected_model_id=fixture_model_id,
        expected_source_binding_sha256=prepared.source_binding_sha256,
    )
    facts = build_recorded_call_facts(
        prepared=prepared, replay=replay, model_call_id=str(model_call_id),
    )
    journal.response_received(model_call_id, replay.response)
    # W56a has no verified model/price pin. NULL is the database's explicit
    # unknown-cost value; the run summary counts it as unmeasured. Inserting a
    # synthetic zero or a guessed v1 model rate would falsify immutable evidence.
    job_repo.complete_provider_call(session, authority, call={
        "model_call_id": facts.model_call_id,
        "provider": "anthropic",
        "model_id": facts.model_id,
        "provider_mode": facts.provider_mode.value,
        "parameters": facts.parameters,
        "request_sha256": facts.request_sha256,
        "response_sha256": facts.response_sha256,
        "input_tokens": facts.input_tokens,
        "output_tokens": facts.output_tokens,
        "latency_ms": facts.latency_ms,
        "status": facts.status,
        "cost_usd": None,
        "cost_basis": "estimated",
    })
    session.commit()

    if replay.finished.truncated or replay.finished.grounding.salvaged:
        raise DomainError(
            ErrorCode.ANALYSIS_FAILED,
            message="an incomplete recorded reply needs a separate partial coverage policy",
            stage_id="text_analysis",
        )

    artifact = build_recorded_observation_artifact(
        prepared=prepared,
        replay=replay,
        run_id=run_id,
        model_call_id=facts.model_call_id,
        analysis_profile_id=run.analysis_profile_id,
        prompt_bundle_id=run.prompt_bundle_id,
    )
    publication_store = _publication_store(
        session,
        store=blob_store,
        jobs=job_repo,
        blobs=blob_repo,
        authority=authority,
        stage_id="text_analysis",
    )
    published = publication_store.put_blob(
        artifact.payload,
        declared_sha256=artifact.sha256,
        declared_size=artifact.size_bytes,
        role=blob_role_for(artifact.role),
        media_type=artifact.media_type,
    )
    reference = ArtifactRef(
        role=artifact.role,
        blob_id=str(published.blob_id),
        sha256=published.sha256,
        size_bytes=published.size,
        media_type=published.media_type,
    )
    readback = publication_store.read(parse_blob_id(reference.blob_id), verify=True)
    if readback != artifact.payload:
        raise DomainError(
            ErrorCode.STORAGE_INTEGRITY_ERROR,
            message="recorded observation Blob readback differed from published bytes",
            blob_id=reference.blob_id,
            role=reference.role,
        )
    result = seal_recorded_v2_stage_result(
        artifact=artifact,
        published_ref=reference,
        call=facts,
        prepared=prepared,
        run_id=run_id,
        version_uid=run.version_uid,
        started_at=started_at,
        finished_at=clock(),
    )
    _persist_and_bind(
        session,
        runs=run_repo,
        jobs=job_repo,
        blobs=blob_repo,
        authority=authority,
        run_id=run_id,
        result=result,
    )
    session.commit()
    return result


__all__ = ["run_recorded_v2_stage"]
