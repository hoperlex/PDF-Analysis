"""One durable work item drives one project queue, one selected step at a time."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from auditmanager.access.public import AccountRepository
from auditmanager.comparison.ai_jobs.model import AiConsentInput
from auditmanager.comparison.ai_jobs.service import AiJobCommand, ComparisonAiJobService
from auditmanager.comparison.ai_pairs.service import ComparisonAiPairService
from auditmanager.comparison.ai_sheets.method import SheetChangesMethod
from auditmanager.comparison.ai_sheets.service import ComparisonAiSheetService
from auditmanager.comparison.matrix.service import ComparisonMatrixService
from auditmanager.comparison.overview.service import ComparisonOverviewService
from auditmanager.comparison.profile_queue.enqueue import enqueue_version_page_profiles
from auditmanager.comparison.queue.model import LAUNCH_KIND
from auditmanager.comparison.queue.repository import LaunchQueueRepository
from auditmanager.comparison.report.service import ComparisonReportService
from auditmanager.comparison.series.service import ComparisonSeriesService
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid

_LOG = logging.getLogger(__name__)
POLL_SECONDS = 5.0
PAUSED_POLL_SECONDS = 30.0


def _reason(error: DomainError) -> str:
    if error.code is ErrorCode.CONFLICT:
        reason = error.detail_fields.get("conflict_reason")
        if reason == "comparison_estimate_stale":
            return "comparison_estimate_stale"
    return "comparison_launch_step_failed"


class ComparisonLaunchHandler:
    kind = LAUNCH_KIND

    def __init__(self, dependencies: WorkDependencies) -> None:
        self._deps = dependencies
        self._repo = LaunchQueueRepository()
        self._factory = dependencies.session_factory
        self._matrix = ComparisonMatrixService(session_factory=self._factory, blob_store=dependencies.blob_store)
        self._series = ComparisonSeriesService(session_factory=self._factory, blob_store=dependencies.blob_store)
        self._pairs = ComparisonAiPairService(self._factory, blob_store=dependencies.blob_store,
                                               comparison_modules="versions")
        method = SheetChangesMethod()
        jobs = ComparisonAiJobService(self._factory, methods=[method], comparison_modules="versions")
        self._sheets = ComparisonAiSheetService(self._factory, jobs=jobs, method=method)
        self._reports = ComparisonReportService(self._factory, blob_store=dependencies.blob_store,
                                                comparison_modules="versions")
        self._jobs = ComparisonAiJobService(self._factory, methods=[], comparison_modules="versions")
        self._overview = ComparisonOverviewService(session_factory=self._factory)

    def run(self, item: WorkItem) -> Outcome:
        if item.kind != self.kind or item.payload != {"project_uid": item.project_uid}:
            return Failed("comparison_launch_payload_invalid")
        try:
            return self._run(item)
        except DomainError as error:
            _LOG.warning("comparison launch %s failed: %s", item.project_uid, error.code.value)
            return self._fail(item, _reason(error))

    def _run(self, item: WorkItem) -> Outcome:
        with session_scope(self._factory) as session:
            item.require_current(session)
            queue = self._repo.queue(session, item.project_uid, lock=True)
            if queue is None:
                return Completed()
            entries = self._repo.entries(session, item.project_uid, lock=True)
            running = next((row for row in entries if row["state"] == "running"), None)
            if running is not None:
                entry = running
                phase = "poll"
            elif queue["paused"]:
                return Yielded(PAUSED_POLL_SECONDS)
            elif queue["failure_reason"] is not None:
                return Completed()
            else:
                entry = next((row for row in entries if row["state"] == "waiting"), None)
                if entry is None:
                    return Completed()
                phase = "start"
        if phase == "start":
            if entry["step"] in ("ai_pairs", "ai_changes", "report"):
                try:
                    estimate = self._estimate(entry)
                except DomainError as error:
                    if error.code is ErrorCode.CONFLICT and error.detail_fields.get("conflict_reason") == "comparison_ai_nothing_to_do":
                        with session_scope(self._factory) as session:
                            item.require_current(session)
                            self._repo.move(session, entry["comparison_launch_entry_id"], from_state="waiting", to_state="skipped")
                        return Yielded()
                    raise
                if entry["consent_digest"] is None or entry["consent_digest"] != estimate["estimate_digest"]:
                    with session_scope(self._factory) as session:
                        item.require_current(session)
                        self._repo.move(session, entry["comparison_launch_entry_id"], from_state="waiting",
                                        to_state="needs_consent", reason="comparison_consent_required")
                    return Yielded()
            with session_scope(self._factory) as session:
                item.require_current(session)
                queue = self._repo.queue(session, item.project_uid, lock=True)
                if queue is None or queue["paused"] or queue["failure_reason"] is not None:
                    return Yielded(PAUSED_POLL_SECONDS)
                rows = self._repo.entries(session, item.project_uid, lock=True)
                if any(row["state"] == "running" for row in rows):
                    return Yielded()
                if not self._repo.move(session, entry["comparison_launch_entry_id"], from_state="waiting", to_state="running"):
                    return Yielded()
        if entry["step"] in ("profile", "matrix", "series"):
            result = self._deterministic(item, entry)
        else:
            try:
                result = self._ai(item, entry)
            except DomainError as error:
                if error.code is ErrorCode.CONFLICT and error.detail_fields.get("conflict_reason") == "comparison_ai_nothing_to_do":
                    result = "skipped"
                else:
                    raise
        if result == "working":
            return Yielded(POLL_SECONDS)
        with session_scope(self._factory) as session:
            item.require_current(session)
            self._repo.move(session, entry["comparison_launch_entry_id"], from_state="running",
                            to_state=result,
                            reason=None if result in ("done", "skipped") else "comparison_launch_step_failed")
            if result == "failed":
                self._repo.set_queue(session, item.project_uid, paused=False, failure_reason="comparison_launch_step_failed")
        return Yielded() if result in ("done", "skipped") else Completed()

    def _roles(self, user_uid: str) -> frozenset[str]:
        with session_scope(self._factory) as session:
            return AccountRepository().roles_of(session, user_uid)

    def _latest_series(self, entry: Mapping[str, Any]) -> str:
        page = self._series.list_series(project_uid=entry["project_uid"], document_uid=entry["document_uid"],
                                        after=None, limit=1)
        if not page.items:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="comparison_series_state")
        return str(page.items[0]["series_id"])

    def _overview_state(self, entry: Mapping[str, Any]) -> str:
        overview = self._overview.get_overview(project_uid=entry["project_uid"])
        document = next((row for row in overview["sets"] if row["document_uid"] == entry["document_uid"]), None)
        if document is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
        return next(row["state"] for row in document["steps"] if row["step"] == entry["step"])

    def _deterministic(self, item: WorkItem, entry: Mapping[str, Any]) -> str:
        step = entry["step"]
        initial_state = self._overview_state(entry)
        if initial_state == "not_applicable":
            return "skipped"
        if initial_state in ("done", "attention") and not entry["restart"]:
            return "skipped"
        key = f"launch-{entry['comparison_launch_entry_id']}"
        if step == "profile":
            if initial_state != "done":
                with session_scope(self._factory) as session:
                    item.require_current(session)
                    versions = DocumentRepository().list_versions(session, DocumentUid.parse(entry["document_uid"]))
                    for version in versions:
                        enqueue_version_page_profiles(session, project_uid=entry["project_uid"],
                                                      version_uid=str(version.version_uid),
                                                      created_by_user_uid=entry["actor_user_uid"],
                                                      retry_failed=initial_state == "failed")
        elif step == "matrix":
            self._matrix.prepare_matrix(project_uid=entry["project_uid"], document_uid=entry["document_uid"],
                                        user_uid=entry["actor_user_uid"], actor_roles=self._roles(entry["actor_user_uid"]),
                                        idempotency_key=key)
        else:
            if entry["comparison_series_id"] is None:
                view = self._series.start_series(
                    project_uid=entry["project_uid"], document_uid=entry["document_uid"],
                    restart=entry["restart"], base_order_revision_no=None, user_uid=entry["actor_user_uid"],
                    actor_label=entry["actor_label"], actor_roles=self._roles(entry["actor_user_uid"]),
                    idempotency_key=key,
                )
                with session_scope(self._factory) as session:
                    item.require_current(session)
                    self._repo.attach(session, entry["comparison_launch_entry_id"], series_id=view["series_id"])
                entry = {**entry, "comparison_series_id": view["series_id"]}
            state = self._series.get_series(series_id=entry["comparison_series_id"])["state"]
            return "done" if state == "completed" else "failed" if state in ("failed", "cancelled") else "working"
        state = self._overview_state(entry)
        return "done" if state in ("done", "attention") else "failed" if state == "failed" else "working"

    def _estimate(self, entry: Mapping[str, Any]) -> Mapping[str, Any]:
        step = entry["step"]
        if step == "ai_pairs":
            return self._pairs.estimate(project_uid=entry["project_uid"], document_uid=entry["document_uid"])
        series_id = self._latest_series(entry)
        if step == "ai_changes":
            return self._sheets.estimate_series(series_id=series_id, only_failed=False)
        report = self._reports.create_report(
            series_id=series_id, kind="client", reuse=True, user_uid=entry["actor_user_uid"],
            actor_label=entry["actor_label"], actor_roles=self._roles(entry["actor_user_uid"]),
            idempotency_key=f"launch-{entry['comparison_launch_entry_id']}-draft",
        )
        return report["estimate"]

    def _ai(self, item: WorkItem, entry: Mapping[str, Any]) -> str:
        step = entry["step"]
        job_id = entry["comparison_ai_job_id"]
        if job_id is None:
            consent = AiConsentInput(estimate_digest=entry["consent_digest"], confirmed=True)
            key = f"launch-{entry['comparison_launch_entry_id']}-start"
            roles = self._roles(entry["actor_user_uid"])
            if step == "ai_pairs":
                view = self._pairs.start(project_uid=entry["project_uid"], document_uid=entry["document_uid"],
                                         consent=consent, user_uid=entry["actor_user_uid"], actor_roles=roles,
                                         idempotency_key=key)
                job_id = view["job_id"]
            elif step == "ai_changes":
                series_id = self._latest_series(entry)
                view = self._sheets.start_series(
                    series_id=series_id, consent=consent, restart=entry["restart"],
                    command=AiJobCommand("start_comparison_ai_sheet_changes", key, entry["actor_user_uid"], roles),
                )
                job_id = view["job_id"]
            else:
                report = self._reports.create_report(
                    series_id=self._latest_series(entry), kind="client", reuse=True,
                    user_uid=entry["actor_user_uid"], actor_label=entry["actor_label"], actor_roles=roles,
                    idempotency_key=f"launch-{entry['comparison_launch_entry_id']}-draft",
                )
                view = self._reports.start_report(report_id=report["report_id"], consent=consent,
                                                  user_uid=entry["actor_user_uid"], actor_roles=roles,
                                                  idempotency_key=key)
                job_id = view["job"]["job_id"]
            with session_scope(self._factory) as session:
                item.require_current(session)
                self._repo.attach(session, entry["comparison_launch_entry_id"], job_id=job_id)
        state = self._jobs.view(job_id).record.state
        return "done" if state == "completed" else "failed" if state in ("failed", "cancelled") else "working"

    def _fail(self, item: WorkItem, reason: str) -> Outcome:
        with session_scope(self._factory) as session:
            item.require_current(session)
            queue = self._repo.queue(session, item.project_uid, lock=True)
            if queue is None:
                return Failed(reason)
            running = next((row for row in self._repo.entries(session, item.project_uid, lock=True)
                            if row["state"] == "running"), None)
            if running is not None:
                self._repo.move(session, running["comparison_launch_entry_id"], from_state="running",
                                to_state="failed", reason=reason)
            self._repo.set_queue(session, item.project_uid, paused=False, failure_reason=reason)
        return Failed(reason)


def comparison_launch_handler(dependencies: WorkDependencies) -> ComparisonLaunchHandler:
    return ComparisonLaunchHandler(dependencies)
