"""Finish a sealed AR v3 Run with only its grounded review artifact."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.analysis.public import ArtifactRef, StageResult, StageStatus
from auditmanager.findings.public import TerminalSelection, publication_rows_exist, select_terminal
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.runs.v3_cite_stage_contract import (
    load_v3_cite_stage_contract, require_v3_cite_stage_result,
)
from auditmanager.runs.v3_execution_binding import resolve_v3_execution_binding
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.shared.errors import DomainError, ErrorCode


_REQUIRED = (
    "source_preparation", "page_geometry_extraction",
    "document_context_build", "ar_v3_citation_review",
)


@dataclass(frozen=True, slots=True)
class V3ReviewTerminal:
    selection: TerminalSelection
    stage_statuses: dict[str, str]


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


def finish_v3_review_run(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    jobs: JobRepository | None = None,
    runs: RunRepository | None = None,
) -> V3ReviewTerminal:
    """Select a terminal from saved stages and close Run/Job in one transaction.

    No external Blob I/O follows the Run transition. A successful terminal
    publishes only the already verified CITE review; no finding row is written.
    The caller commits or rolls back this final transaction.
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
    run_repo.advance(
        session, run_id=authority.run_id, from_state="running", to_state="validating",
    )
    if (run_repo.stage_results(session, authority.run_id) != before
            or publication_rows_exist(session, authority.run_id)):
        raise _refuse("review_inputs_changed_before_terminal")
    run_repo.terminate(
        session, run_id=authority.run_id, from_state="validating",
        to_state=selection.state, degradation_set=selection.degradation_set,
        terminal_reason=selection.terminal_reason,
        terminal_detail=selection.terminal_detail,
    )
    job_repo.finish_execution(
        session, authority, publishes_result=selection.is_publishable,
    )
    return V3ReviewTerminal(selection, statuses)


__all__ = ["V3ReviewTerminal", "finish_v3_review_run"]
