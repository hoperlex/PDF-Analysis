"""Finish a sealed AR v3 Run: publish its grounded provisional findings, then close it.

``R-146as``: a proposal that passed both pure gates (every PDF quote resolves; the norm labels,
quotes and values hold) and cites only provisional topics is published as a finding through the
transaction-scoped writer ``findings.citation_publication``, so an expert can record a verdict on
it. A withheld (context-only or mixed) proposal, a rejected one and a non-normative one stay in
the sealed review and get no row. The model's text is never a decision: the finding is
``pending`` until an expert's ``appendDecision``.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import ArtifactRef, StageResult, StageStatus
from auditmanager.documents.public import DocumentRepository
from auditmanager.findings.public import (
    CitationPublicationRefused, PublishedV3CitationFinding, TerminalSelection,
    V3PublicationCandidate, publication_rows_exist, publish_grounded_v3_finding,
    select_terminal,
)
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.runs.v3_cite_preflight import prepare_v3_cite_preflight
from auditmanager.runs.v3_cite_stage_contract import (
    load_v3_cite_stage_contract, require_v3_cite_stage_result,
)
from auditmanager.runs.v3_citations import provisional_publication_candidates
from auditmanager.runs.v3_execution_binding import resolve_v3_execution_binding
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.runs.v3_review_artifact import build_v3_beta_review_artifact
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore


_REQUIRED = (
    "source_preparation", "page_geometry_extraction",
    "document_context_build", "ar_v3_citation_review",
)


CITE_STAGE_ID = "ar_v3_citation_review"
#: The bound on the saved text layer the rebuild may read; the worker passes its own.
MAX_PUBLICATION_TEXT_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class V3ReviewTerminal:
    selection: TerminalSelection
    stage_statuses: dict[str, str]
    #: The findings this terminal wrote, in proposal order; empty when nothing was provisional.
    published_findings: tuple[PublishedV3CitationFinding, ...] = ()


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved AR v3 review cannot be published",
        stage_id="ar_v3_citation_review", reason=reason,
    )


def _checked_review(row: StageResultRow) -> StageResult:
    contract = load_v3_cite_stage_contract()
    try:
        result = StageResult(
            stage_id=row.stage_id, stage_version=row.stage_version,
            status=StageStatus(row.status),
            artifacts=tuple(ArtifactRef(**dict(raw)) for raw in row.artifacts),
            metrics=row.metrics, started_at=row.started_at, finished_at=row.finished_at,
        )
        require_v3_cite_stage_result(result, contract=contract)
    except (TypeError, ValueError) as exc:
        raise _refuse("saved_citation_stage_invalid") from exc
    return result


def _rebuild_candidates(
    session: Session, *, review: StageResult, authority: AttemptAuthority,
    registry: TrustedPackRegistry, blob_store: BlobStore | None, max_text_bytes: int,
    jobs: JobRepository, runs: RunRepository, documents: DocumentRepository | None,
) -> tuple[tuple[V3PublicationCandidate, ...], bytes]:
    """Rebuild the provisional publication candidates from the saved inputs of the CITE stage.

    The sealed artifact keeps the evidence anchors and the citations of a provisional proposal
    but not the model's sentences, its category or its values, by design. The candidates are
    therefore rebuilt from the same saved inputs the CITE writer used (text layer, custody-checked
    retrieval set, saved reply), and the rebuilt artifact must be **byte-equal** to the sealed
    one: a finding is a view of exactly the review that was sealed, never of another computation.
    This does external Blob I/O, so it runs before the Run leaves ``running``.
    """
    if blob_store is None:
        raise _refuse("publication_inputs_missing")
    try:
        preflight = prepare_v3_cite_preflight(
            session, authority=authority, registry=registry, blob_store=blob_store,
            max_text_bytes=max_text_bytes, jobs=jobs, runs=runs, documents=documents,
        )
        artifact = build_v3_beta_review_artifact(preflight)
        candidates = provisional_publication_candidates(preflight.review)
    except ValueError as exc:  # V3CorpusCitationRefused and the pure gates' refusals
        raise _refuse(f"publication_rebuild_refused:{exc}") from exc
    sealed = review.artifacts[0]
    if artifact.sha256 != sealed.sha256 or artifact.size_bytes != sealed.size_bytes:
        raise _refuse("rebuilt_review_differs_from_sealed")
    if len(candidates) != review.metrics["provisional_citation_count"]:
        raise _refuse("provisional_count_differs_from_sealed")
    return candidates, preflight.prepared.pinned_corpus.verified_set.data


def _publish_candidates(
    session: Session, *, authority: AttemptAuthority, model_call_id: str, set_bytes: bytes,
    candidates: tuple[V3PublicationCandidate, ...],
) -> tuple[PublishedV3CitationFinding, ...]:
    """Write one finding per candidate in the caller's transaction (no commit here)."""
    try:
        return tuple(publish_grounded_v3_finding(
            session, run_id=authority.run_id, job_id=authority.job_id,
            attempt_id=authority.attempt_id, execution_token=authority.execution_token,
            model_call_id=model_call_id, set_bytes=set_bytes, candidate=candidate,
            cite_stage_id=CITE_STAGE_ID,
        ) for candidate in candidates)
    except CitationPublicationRefused as exc:
        raise _refuse(f"publication_refused:{exc}") from exc


def finish_v3_review_run(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
    blob_store: BlobStore | None = None,
    documents: DocumentRepository | None = None,
    max_text_bytes: int = MAX_PUBLICATION_TEXT_BYTES,
) -> V3ReviewTerminal:
    """Select a terminal from saved stages, publish the provisional findings, close Run/Job.

    A publishable terminal first rebuilds the candidates of the sealed review (external Blob
    reads, before the Run transition) when the review holds any provisional proposal, moves the
    Run to ``validating``, writes one finding per candidate through the grounded writer, and
    only then terminates the Run and finishes the Job, all in the caller's transaction: every
    finding and the terminal state, or none. The caller commits or rolls back.
    """
    job_repo = jobs or JobRepository()
    run_repo = runs or RunRepository()
    binding = resolve_v3_execution_binding(
        session, authority=authority, registry=registry, jobs=job_repo,
    )
    before = run_repo.stage_results(session, authority.run_id)
    stages: dict[str, StageResultRow] = {}
    for row in before:
        if row.stage_id not in _REQUIRED:
            raise _refuse("unexpected_stage_result")
        if row.stage_id in stages:
            raise _refuse("duplicate_stage_result")
        stages[row.stage_id] = row
    if publication_rows_exist(session, authority.run_id):
        raise _refuse("canonical_finding_already_published")
    statuses = {key: value.status for key, value in stages.items()}
    missing = tuple(stage for stage in _REQUIRED if stage not in stages)
    if missing:
        selection = TerminalSelection(
            state="failed", degradation_set=missing,
            terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        )
    else:
        selection = select_terminal(
            statuses, required_stages=_REQUIRED,
            stage_errors={key: (value.error or {}).get("code") for key, value in stages.items()},
            stage_details={key: (value.error or {}).get("details") for key, value in stages.items()},
        )
    candidates: tuple[V3PublicationCandidate, ...] = ()
    set_bytes = b""
    call = None
    if selection.is_publishable:
        review = _checked_review(stages["ar_v3_citation_review"])
        call = job_repo.completed_v3_call(session, authority)
        metrics = review.metrics
        if (call.run_id != binding.run_id
                or call.scope_id != binding.scope_id
                or call.set_sha256 != binding.set_sha256
                or call.status != "succeeded"
                or metrics["model_call_id"] != call.model_call_id
                or metrics["candidate_sha256"] != call.candidate_sha256
                or metrics["provider_body_sha256"] != call.request_sha256
                or metrics["provider_response_sha256"] != call.response_sha256
                or metrics["set_sha256"] != call.set_sha256
                or metrics["reply_blob_sha256"] != call.reply_blob_sha256):
            raise _refuse("review_call_binding_changed")
        if metrics["provisional_citation_count"] > 0:
            candidates, set_bytes = _rebuild_candidates(
                session, review=review, authority=authority, registry=registry,
                blob_store=blob_store, max_text_bytes=max_text_bytes,
                jobs=job_repo, runs=run_repo, documents=documents,
            )
    run_repo.advance(
        session, run_id=authority.run_id, from_state="running", to_state="validating",
    )
    if (run_repo.stage_results(session, authority.run_id) != before
            or publication_rows_exist(session, authority.run_id)):
        raise _refuse("review_inputs_changed_before_terminal")
    published = ()
    if candidates:
        assert call is not None
        published = _publish_candidates(
            session, authority=authority, model_call_id=call.model_call_id,
            set_bytes=set_bytes, candidates=candidates,
        )
    run_repo.terminate(
        session, run_id=authority.run_id, from_state="validating",
        to_state=selection.state, degradation_set=selection.degradation_set,
        terminal_reason=selection.terminal_reason,
        terminal_detail=selection.terminal_detail,
    )
    job_repo.finish_execution(
        session, authority, publishes_result=selection.is_publishable,
    )
    return V3ReviewTerminal(selection, statuses, published)


__all__ = ["V3ReviewTerminal", "finish_v3_review_run"]
