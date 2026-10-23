"""Unserved-to-served AR v3 worker chain for an installed reviewed pack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from auditmanager.analysis.public import V3GenerationSettings
from auditmanager.documents.public import DocumentRepository
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.provider import ProviderBinding
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_cite_stage import run_v3_cite_stage
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.runs.v3_provider_call import dispatch_v3_provider_call
from auditmanager.runs.v3_review_terminal import V3ReviewTerminal, finish_v3_review_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobMetadataRepository, BlobStore


MAX_V3_SAVED_TEXT_BYTES = 16 * 1024 * 1024
V3_BETA_SETTINGS = V3GenerationSettings(4096, "high", {"type": "adaptive"})


@dataclass(frozen=True, slots=True)
class V3WorkerOutcome:
    terminal: V3ReviewTerminal
    dispatched: bool


def _no_completed_call(error: DomainError) -> bool:
    return (
        error.code is ErrorCode.ANALYSIS_INPUT_INVALID
        and error.detail_fields.get("reason") == "v3_call_missing_or_duplicate"
    )


def run_v3_worker_chain(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    blob_store: BlobStore,
    provider_for_dispatch: Callable[[], ProviderBinding],
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
    blobs: BlobMetadataRepository | None = None,
) -> V3WorkerOutcome:
    """Dispatch at most once, ground saved evidence and select review-only terminal.

    The caller has committed the running Run and deterministic stages, and owns
    the final transaction. Completed call/effect evidence from a prior Attempt
    is replayed through CITE without an adapter call. An unresolved effect is
    still fenced by the provider journal's no-duplicate gate.
    """
    job_repo = jobs or JobRepository()
    run_repo = runs or RunRepository()
    before = run_repo.stage_results(session, authority.run_id)
    citation_rows = tuple(row for row in before if row.stage_id == "ar_v3_citation_review")
    if len(citation_rows) > 1:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="AR v3 Run has duplicate citation stages",
            stage_id="ar_v3_citation_review", reason="duplicate_citation_stage",
        )
    dispatched = False
    if not citation_rows:
        try:
            job_repo.completed_v3_call(
                session, authority, lock_authority=False,
            )
        except DomainError as error:
            if not _no_completed_call(error):
                raise
            dispatch_v3_provider_call(
                session, authority=authority, registry=registry,
                blob_store=blob_store, max_text_bytes=MAX_V3_SAVED_TEXT_BYTES,
                provider=provider_for_dispatch(), settings=V3_BETA_SETTINGS,
                jobs=job_repo, runs=run_repo, documents=documents, blobs=blobs,
            )
            dispatched = True
        run_v3_cite_stage(
            session, authority=authority, registry=registry, blob_store=blob_store,
            max_text_bytes=MAX_V3_SAVED_TEXT_BYTES,
            jobs=job_repo, runs=run_repo, documents=documents, blobs=blobs,
        )
    return V3WorkerOutcome(
        finish_v3_review_run(
            session, authority=authority, registry=registry,
            jobs=job_repo, runs=run_repo,
        ),
        dispatched,
    )


__all__ = ["MAX_V3_SAVED_TEXT_BYTES", "V3_BETA_SETTINGS", "V3WorkerOutcome", "run_v3_worker_chain"]
