"""Unserved AR v3 CITE writer with a durable review artifact publication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ArtifactRef, StageError, StageResult, StageStatus, V3GenerationSettings,
    blob_role_for,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.executor import _persist_and_bind, _publication_store
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.runs.v3_cite_preflight import prepare_v3_cite_preflight
from auditmanager.runs.v3_cite_stage_contract import (
    load_v3_cite_stage_contract, require_v3_cite_stage_result,
)
from auditmanager.runs.v3_execution_binding import resolve_v3_execution_binding
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.runs.v3_review_artifact import build_v3_beta_review_artifact
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import (
    BlobMetadataRepository, BlobStore, parse_blob_id,
)


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="AR v3 citation review cannot bind its saved evidence",
        stage_id="ar_v3_citation_review", reason=reason,
    )


def _prior_rows(
    rows: tuple[StageResultRow, ...], *, stage_id: str,
) -> tuple[StageResultRow, ...]:
    if any(row.stage_id == stage_id for row in rows):
        raise _refuse("citation_stage_already_recorded")
    return rows


def _failed_stage(
    session: Session, *, authority: AttemptAuthority, error: DomainError,
    started_at: datetime, clock: Clock, before: tuple[StageResultRow, ...],
    binding: object, registry: TrustedPackRegistry,
    jobs: JobRepository, runs: RunRepository,
) -> StageResult:
    jobs.require_current(session, authority)
    if (resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=jobs,
    ) != binding or runs.stage_results(session, authority.run_id) != before):
        raise _refuse("citation_inputs_changed_before_failure")
    contract = load_v3_cite_stage_contract()
    result = StageResult(
        stage_id=contract.stage_id, stage_version=contract.stage_version,
        status=StageStatus.FAILED, error=StageError.from_domain_error(error),
        started_at=started_at, finished_at=clock(),
    )
    require_v3_cite_stage_result(result, contract=contract)
    runs.record_stage_result(
        session, run_id=authority.run_id, document=result.to_document(),
    )
    session.commit()
    return result


def run_v3_cite_stage(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    blob_store: BlobStore,
    max_text_bytes: int,
    settings: V3GenerationSettings,
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
    blobs: BlobMetadataRepository | None = None,
    clock: Clock = _utc_now,
) -> StageResult:
    """Commit one review-only CITE stage under the current Attempt.

    The caller begins with a committed running Run and keeps an independent
    lease heartbeat alive. A later owner selects the Run terminal state.
    """
    contract = load_v3_cite_stage_contract()
    job_repo = jobs or JobRepository()
    run_repo = runs or RunRepository()
    blob_repo = blobs or BlobMetadataRepository()
    binding = resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    )
    before = _prior_rows(
        run_repo.stage_results(session, authority.run_id),
        stage_id=contract.stage_id,
    )
    started_at = clock()
    run_repo.stage_started(
        session, run_id=authority.run_id, stage_id=contract.stage_id,
    )
    session.commit()  # the start event survives a worker loss during CITE

    try:
        preflight = prepare_v3_cite_preflight(
            session, authority=authority, registry=registry,
            blob_store=blob_store, max_text_bytes=max_text_bytes,
            settings=settings, jobs=job_repo, runs=run_repo,
            documents=documents,
        )
        if preflight.prepared.binding != binding:
            raise _refuse("citation_group_changed_during_preflight")
        artifact = build_v3_beta_review_artifact(preflight)
    except DomainError as exc:
        if exc.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
            raise
        return _failed_stage(
            session, authority=authority, error=exc, started_at=started_at,
            clock=clock, before=before, binding=binding, registry=registry,
            jobs=job_repo, runs=run_repo,
        )
    except ValueError:
        return _failed_stage(
            session, authority=authority, error=_refuse("citation_input_invalid"),
            started_at=started_at, clock=clock, before=before, binding=binding,
            registry=registry, jobs=job_repo, runs=run_repo,
        )

    if run_repo.stage_results(session, authority.run_id) != before:
        raise _refuse("citation_inputs_changed_before_publication")

    publication = _publication_store(
        session, store=blob_store, jobs=job_repo, blobs=blob_repo,
        authority=authority, stage_id=contract.stage_id,
    )
    published = publication.put_blob(
        artifact.payload, declared_sha256=artifact.sha256,
        declared_size=artifact.size_bytes, role=blob_role_for(artifact.role),
        media_type=artifact.media_type,
    )
    if (published.sha256 != artifact.sha256
            or published.size != artifact.size_bytes
            or published.media_type != artifact.media_type):
        raise DomainError(
            ErrorCode.STORAGE_INTEGRITY_ERROR,
            message="AR v3 review Blob metadata differed from sealed bytes",
            blob_id=str(published.blob_id), role=artifact.role,
        )
    reference = ArtifactRef(
        role=artifact.role, blob_id=str(published.blob_id),
        sha256=published.sha256, size_bytes=published.size,
        media_type=published.media_type,
    )
    if publication.read(parse_blob_id(reference.blob_id), verify=True) != artifact.payload:
        raise DomainError(
            ErrorCode.STORAGE_INTEGRITY_ERROR,
            message="AR v3 review Blob readback differed from sealed bytes",
            blob_id=reference.blob_id, role=reference.role,
        )

    call = preflight.completed_call
    if (resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    ) != binding
            or job_repo.completed_v3_call(session, authority) != call
            or run_repo.stage_results(session, authority.run_id) != before):
        raise _refuse("citation_inputs_changed_before_bind")
    review = preflight.review
    result = StageResult(
        stage_id=contract.stage_id, stage_version=contract.stage_version,
        status=StageStatus.SUCCEEDED, artifacts=(reference,),
        metrics={
            "model_call_id": call.model_call_id,
            "candidate_sha256": call.candidate_sha256,
            "provider_body_sha256": call.request_sha256,
            "provider_response_sha256": call.response_sha256,
            "set_sha256": call.set_sha256,
            "reply_blob_sha256": call.reply_blob_sha256,
            "provisional_citation_count": len(review.provisional_proposal_ordinals),
            "withheld_proposal_count": len(review.withheld_proposal_ordinals),
            "rejected_proposal_count": len(review.evaluation.grounding.rejected),
        },
        started_at=started_at, finished_at=clock(),
    )
    require_v3_cite_stage_result(result, contract=contract)
    _persist_and_bind(
        session, runs=run_repo, jobs=job_repo, blobs=blob_repo,
        authority=authority, run_id=authority.run_id, result=result,
    )
    session.commit()
    return result


__all__ = ["run_v3_cite_stage"]
