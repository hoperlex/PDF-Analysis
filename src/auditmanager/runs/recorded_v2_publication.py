"""Unactivated final transaction for a saved recorded AR v2 Run.

The caller commits once after this function returns. Blob reads finish before
``running -> validating`` locks the Run; the Lease is locked only by the final
Job/Attempt finish, so its heartbeat can continue during finding publication.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    ArtifactRef, StageResult, StageStatus, canonical_bytes, default_registry,
    resolve_recorded_profile, sha256_hex,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.findings.public import (
    TerminalSelection, V2PublicationContext, plan_recorded_saved_publication,
    publication_rows_exist, publish_v2_merge_plan, select_terminal,
)
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.recorded_v2_merge import _source_references
from auditmanager.runs.repository import RunRepository, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import BlobStore


@dataclass(frozen=True, slots=True)
class RecordedPublicationGateResult:
    run_id: str
    selection: TerminalSelection
    finding_count: int
    observation_count: int
    rejected_count: int


def _refuse(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="saved recorded AR v2 publication evidence is invalid",
        stage_id="finding_merge", reason=reason,
    )


def _stages(rows: tuple[StageResultRow, ...], plan: tuple[str, ...]) -> dict[str, StageResultRow]:
    found: dict[str, StageResultRow] = {}
    for row in rows:
        if row.stage_id not in plan or row.stage_id in found:
            raise _refuse("unexpected_or_duplicate_stage")
        if row.stage_version != default_registry().stage(row.stage_id).stage_version:
            raise _refuse("stage_version_mismatch")
        if row.status not in {status.value for status in StageStatus}:
            raise _refuse("stage_status_invalid")
        found[row.stage_id] = row
    return found


def _successful_stage(row: StageResultRow) -> StageResult:
    if row.status != StageStatus.SUCCEEDED.value or row.error is not None:
        raise _refuse("saved_stage_not_succeeded")
    try:
        result = StageResult(
            stage_id=row.stage_id, stage_version=row.stage_version,
            status=StageStatus.SUCCEEDED,
            artifacts=tuple(ArtifactRef(**dict(raw)) for raw in row.artifacts),
            metrics=row.metrics, started_at=row.started_at, finished_at=row.finished_at,
        )
        result.to_document()
    except (TypeError, ValueError) as exc:
        raise _refuse("saved_stage_result_invalid") from exc
    return result


def _terminal_without_plan(
    stages: dict[str, StageResultRow], plan: tuple[str, ...],
) -> TerminalSelection | None:
    missing = tuple(stage for stage in plan if stage not in stages)
    if missing:
        return TerminalSelection(
            state="failed", degradation_set=missing,
            terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        )
    statuses = {stage: row.status for stage, row in stages.items()}
    if any(statuses[stage] in {"failed", "skipped"} for stage in plan):
        return select_terminal(
            statuses, required_stages=plan, gate_ran=False,
            stage_errors={stage: (row.error or {}).get("code") for stage, row in stages.items()},
            stage_details={
                stage: (row.error or {}).get("details") for stage, row in stages.items()
            },
        )
    # A partial source/text/merge stage cannot supply the strict saved plan.
    if any(stages[stage].status != "succeeded" for stage in (
        "source_preparation", "text_analysis", "finding_merge",
    )):
        return TerminalSelection(
            state="failed",
            degradation_set=tuple(stage for stage in plan if statuses[stage] == "partial"),
            terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        )
    return None


def publish_recorded_v2_run(
    session: Session,
    *,
    authority: AttemptAuthority,
    blob_store: BlobStore,
    runs: RunRepository | None = None,
    jobs: JobRepository | None = None,
    documents: DocumentRepository | None = None,
) -> RecordedPublicationGateResult:
    """Publish one saved plan, terminal Run and finish current Attempt atomically.

    The caller owns the outer transaction and must commit or roll it back. A
    stale Attempt is discovered by the final ``finish_execution`` and rolls
    back every finding and Run transition in that transaction.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    document_repo = documents or DocumentRepository()
    run_id = authority.run_id
    run = run_repo.get(session, run_id)
    if run.state != "running" or run.provider_mode != "recorded":
        raise _refuse("recorded_running_run_required")
    try:
        profile = resolve_recorded_profile(run.analysis_profile_id, run.prompt_bundle_id)
    except ValueError as exc:
        raise _refuse("registered_profile_mismatch") from exc
    stage_plan = profile.stage_plan
    before = run_repo.stage_results(session, run_id)
    stages = _stages(before, stage_plan)
    failed_selection = _terminal_without_plan(stages, stage_plan)
    saved = None
    call = None
    if failed_selection is None:
        version = document_repo.get_version(session, VersionUid.parse(run.version_uid))
        if str(version.project_uid) != run.project_uid:
            raise _refuse("run_version_mismatch")
        text_ref, recognised_ref = _source_references(before)
        call = job_repo.completed_recorded_call(
            session, run_id=run_id, job_id=authority.job_id,
        )
        source_binding = sha256_hex(canonical_bytes({
            "version_uid": run.version_uid,
            "text_layer_ref": text_ref.to_document(),
            "recognised_ref": None if recognised_ref is None else recognised_ref.to_document(),
            "textless_pages": version.textless_pages,
            "request_sha256": call.request_sha256,
        }))
        try:
            saved = plan_recorded_saved_publication(
                blob_store,
                text_result=_successful_stage(stages["text_analysis"]),
                merge_result=_successful_stage(stages["finding_merge"]),
                run_id=run_id, version_uid=run.version_uid,
                analysis_profile_id=run.analysis_profile_id,
                prompt_bundle_id=run.prompt_bundle_id,
                model_id=call.model_id, model_call_id=call.model_call_id,
                request_sha256=call.request_sha256,
                response_sha256=call.response_sha256,
                source_binding_sha256=source_binding,
                text_layer_ref=text_ref, recognised_ref=recognised_ref,
            )
        except ValueError as exc:
            raise _refuse("saved_publication_plan_invalid") from exc

    # The CAS acquires the Run lock before publication. StageResult UPSERT itself
    # need not take that lock: its writer must bind artifacts/check authority in
    # the same rollback-on-error transaction. A late bind after this terminal
    # transaction commits will fail, rolling back the writer's earlier UPSERT.
    # No external read or intermediate commit follows this point.
    run_repo.advance(session, run_id=run_id, from_state="running", to_state="validating")
    if (run_repo.get(session, run_id) != replace(run, state="validating")
            or run_repo.stage_results(session, run_id) != before
            or publication_rows_exist(session, run_id)):
        raise DomainError(ErrorCode.CONFLICT, message="recorded publication inputs changed")
    if call is not None and job_repo.completed_recorded_call(
        session, run_id=run_id, job_id=authority.job_id,
    ) != call:
        raise DomainError(ErrorCode.CONFLICT, message="recorded call changed during read")

    if failed_selection is None:
        assert saved is not None and call is not None
        statuses = {stage: stages[stage].status for stage in stage_plan}
        selection = select_terminal(statuses, required_stages=stage_plan, gate_ran=True)
        if not selection.is_publishable:
            raise _refuse("saved_plan_not_publishable")
        published = publish_v2_merge_plan(
            session, plan=saved.plan,
            context=V2PublicationContext(
                run_id=run_id, project_uid=run.project_uid,
                version_uid=run.version_uid,
                analysis_profile_id=run.analysis_profile_id,
                prompt_bundle_id=run.prompt_bundle_id,
                provider_mode="recorded", model_call_id=call.model_call_id,
            ),
        )
        finding_count = published.finding_count
        observation_count = published.observation_count
        rejected_count = len(published.rejected)
    else:
        selection = failed_selection
        finding_count = observation_count = rejected_count = 0

    run_repo.terminate(
        session, run_id=run_id, from_state="validating", to_state=selection.state,
        degradation_set=selection.degradation_set,
        terminal_reason=selection.terminal_reason,
        terminal_detail=selection.terminal_detail,
    )
    job_repo.finish_execution(
        session, authority, publishes_result=selection.is_publishable,
    )
    return RecordedPublicationGateResult(
        run_id, selection, finding_count, observation_count, rejected_count,
    )


__all__ = ["RecordedPublicationGateResult", "publish_recorded_v2_run"]
