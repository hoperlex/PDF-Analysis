"""Keep the stored state of a report in step with its job (`CMP-VC-REPORT-01`).

The job (``comparison_ai_job``, owned by the shared core) is the one source of truth for whether a report is queued, running, paused, failed or
cancelled; the report row keeps a copy of it so that the table says what a reader sees. The copy is brought up to date at the three places a job
moves: the command that steered it (the service), the item that finished (the handler) and the item that was reclaimed. Each is a
**walk along the table's own edges** (:func:`~auditmanager.comparison.report.model.path_between`): a report whose job ran and ended between two
syncs passes ``running`` on its way to ``completed``, and a target the table cannot reach is not written (a reader derives the state from the job
anyway: :func:`~auditmanager.comparison.report.views.derived_state`).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.model import AiJobRecord
from auditmanager.comparison.report.model import ARTIFACT_PDF, path_between
from auditmanager.comparison.report.repository import ReportRepository

__all__ = ["sync_report"]


def sync_report(session: Session, repository: ReportRepository, report_id: str, job: AiJobRecord | None, *, stage: str | None = None) -> str | None:
    """Move the report row to the state its job implies; answer the state it ends in (``None`` for an unknown or unstarted report).

    ``stage`` replaces the stored stage when given. A job that completed reads ``completed`` only when a PDF was written, else ``partial``."""
    row = repository.get(session, report_id, lock=True)
    if row is None or row.job_id is None or job is None:
        return None if row is None else row.state
    if job.state == "completed":
        has_pdf = ReportRepository.latest(repository.artifacts(session, report_id), ARTIFACT_PDF) is not None
        target = "completed" if has_pdf else "partial"
    else:
        target = job.state
    keep = stage if stage is not None else row.stage
    try:
        path = path_between(row.state, target)
    except ValueError:
        return row.state
    current = row.state
    for step in path:
        reason = (job.failure_reason or "report_failed") if step == "failed" else None
        if not repository.move(session, report_id, from_states=(current,), to_state=step, stage=keep, failure_reason=reason):
            return current
        current = step
    if not path and stage is not None and stage != row.stage:
        repository.set_stage(session, report_id, stage)
    return current
