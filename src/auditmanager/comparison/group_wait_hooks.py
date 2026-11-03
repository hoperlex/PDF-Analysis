"""The sweep of comparison jobs that wait on a group, with what each method does when its job ends without an executor
(`EXEC2-FOLLOWUP-01`, ADR-0026 decision 15).

``ai_jobs/group_waits.py`` ends a job whose group has had no eligible member for longer than the offline wait, and says in its module doc
what the in-call expiry does for every method. The core cannot import the methods (they import the core), so the three that do something
beyond ``pause_for_spend`` are written here, where the methods are known, and handed to the sweep:

``sheet_changes``
    ``ai_sheets/handler.py`` (``_interrupted``) moves the sheet pair the call was at ``running -> queued`` right after ``pause_for_spend``.
    The sweep moves every pair of the job that is ``running`` (a pair never goes ``running`` for a job that has made no call, so it finds
    one only where a handler was in the middle of one), in the same transaction, once the job has ended.
``report``
    ``report/handler.py`` (``_ask``) calls ``sync_report`` right after ``pause_for_spend``, so the report row says what its job implies
    (``failed``, with the job's failure reason). The sweep finds the report by the job it was started with and does the same.
``stage_review``
    ``stage_ai/runtime.py`` (``_failed``) fails the unit it was advancing, fails the run and its step and cancels the pending units, **and then**
    ends the job. The sweep does the same through ``StageAiRepository.end_without_executor``, **before** the job ends, in that order.

``pair_check`` and ``spec`` have no hook: their handlers call ``pause_for_spend`` and nothing else
(:data:`~auditmanager.comparison.ai_jobs.group_waits.ENDED_BY_PAUSE_ONLY`).
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.group_waits import EndedWithoutExecutor, ComparisonGroupWaitSweep
from auditmanager.comparison.ai_jobs.model import AiJobRecord
from auditmanager.comparison.ai_jobs.repository import AiJobRepository
from auditmanager.comparison.ai_sheets.repository import AiSheetRepository
from auditmanager.comparison.report.repository import ReportRepository
from auditmanager.comparison.report.sync import sync_report
from auditmanager.comparison.spend.errors import REASON_NO_EXECUTOR_ONLINE
from auditmanager.comparison.stage_ai.repository import StageAiRepository

__all__ = ["build_group_wait_sweep", "end_hooks"]


def end_hooks(
    *, jobs: AiJobRepository | None = None, sheets: AiSheetRepository | None = None, reports: ReportRepository | None = None,
    stages: StageAiRepository | None = None,
) -> dict[str, EndedWithoutExecutor]:
    """The per-method hooks, over the given repositories (the defaults are the stateless ones)."""
    job_rows = jobs or AiJobRepository()
    sheet_rows = sheets or AiSheetRepository()
    report_rows = reports or ReportRepository()
    stage_rows = stages or StageAiRepository()

    def sheets_after(session: Session, job: AiJobRecord) -> None:
        for item in sheet_rows.items_of_job(session, job.job_id):
            if item.state == "running":
                sheet_rows.move_item(
                    session, job_id=job.job_id, pair_id=item.pair_id, from_states=("running",), to_state="queued",
                )

    def report_after(session: Session, job: AiJobRecord) -> None:
        report = report_rows.by_job(session, job.job_id)
        if report is not None:
            sync_report(session, report_rows, report.report_id, job_rows.get(session, job.job_id))

    def stage_before(session: Session, job: AiJobRecord) -> None:
        if job.stage_chain_run_id is not None:
            stage_rows.end_without_executor(
                session, run_id=job.stage_chain_run_id, job_id=job.job_id, reason=REASON_NO_EXECUTOR_ONLINE,
            )

    return {
        "sheet_changes": EndedWithoutExecutor(after=sheets_after),
        "report": EndedWithoutExecutor(after=report_after),
        "stage_review": EndedWithoutExecutor(before=stage_before),
    }


def build_group_wait_sweep(
    session_factory: "sessionmaker[Session]", *, batch_size: int | None = None,
) -> ComparisonGroupWaitSweep:
    """The sweep the worker runs: every method of the comparison AI jobs, each ended the way its own handler ends it."""
    options = {} if batch_size is None else {"batch_size": batch_size}
    return ComparisonGroupWaitSweep(session_factory, hooks=end_hooks(), **options)
