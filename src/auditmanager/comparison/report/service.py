"""The thirteen report operations (`CMP-VC-REPORT-01`; `CMP-SEAL-C2` section 3, plan 1.1 «Сводка MD и отчёт для заказчика»).

Every operation checks the **module flag first**, before any read or write (ADR-0025 decision 23, ``A-12``), and every write is an **expert's act**
(ADR-0025 decision 16, ``R-60``) claimed by an ``Idempotency-Key`` in the transaction that acts: a repeat of the key replays the recorded outcome and
a refused command writes nothing. A report is made in two steps so that an estimate always precedes a spend: ``createComparisonReport`` and
``uploadComparisonReportSource`` make a **draft** with its estimate and call no model; ``startComparisonReport`` consents to that estimate through
the shared AI-job core (``ComparisonAiJobService``), which writes the job and the first work items in one transaction. The steering of a started
report -- cancel, continue («Продолжить»: a resume or «Досчитать») -- is the core's too; **«Пересобрать PDF» is not a job at all**: it reads the stored
text and writes the PDF again in a child under its ceilings, and no model is called. «Удалить» is a tombstone: no published blob is deleted.

The service never calls a model and never opens a transaction for one: that is the worker's handler (``handler.py``).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.estimate import RouteReader, read_route
from auditmanager.comparison.ai_jobs.model import CONSENT_PAUSES, AiConsentInput, AiMode, AiScope
from auditmanager.comparison.ai_jobs.service import AiJobCommand, ComparisonAiJobService
from auditmanager.comparison.modules import MODULE_VERSIONS, enabled_modules, parse_modules
from auditmanager.comparison.profile.publish import ProfileBlobPublisher
from auditmanager.comparison.profile.runner import ChildRunner
from auditmanager.comparison.report.method import ReportAiMethod, ReportSpec
from auditmanager.comparison.report.model import (
    ARTIFACT_PDF,
    ARTIFACT_SOURCE_MD,
    ARTIFACT_TEXT,
    CONFLICT_REPORT_STATE,
    CONFLICT_SUMMARY_UNAVAILABLE,
    KIND_ANALYTIC,
    KIND_CLIENT,
    KINDS,
    LIVE_STATES,
    MAX_SOURCE_BYTES,
    METHOD,
    SOURCE_SERIES_SUMMARY,
    SOURCE_UPLOADED_MD,
    WORK_KIND,
    conflict,
    source_invalid,
)
from auditmanager.comparison.report.pdf.runner import ChildStartError, PdfFailed, write_pdf
from auditmanager.comparison.report.plan import SourceDoc, load_source
from auditmanager.comparison.report.repository import ReportRepository, ReportRow
from auditmanager.comparison.report.summary import build_summary
from auditmanager.comparison.report.summary_source import SeriesRow, SummaryReader
from auditmanager.comparison.report.sync import sync_report
from auditmanager.comparison.report.views import derived_state, report_dict
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage.public import BlobNotFoundError, StorageError, parse_blob_id

__all__ = ["ComparisonReportService", "ReportPage", "ROLE_PDF", "ROLE_SOURCE", "ROLE_TEXT"]

#: Roles of the report's blobs in the blob journal (``^[a-z][a-z0-9_]{2,63}$``).
ROLE_SOURCE: Final[str] = "comparison_report_source"
ROLE_TEXT: Final[str] = "comparison_report_text"
ROLE_PDF: Final[str] = "comparison_report_pdf"
_MEDIA: Final[Mapping[str, str]] = {ARTIFACT_SOURCE_MD: "text/markdown", ARTIFACT_TEXT: "application/json", ARTIFACT_PDF: "application/pdf"}


@dataclass(frozen=True, slots=True)
class ReportPage:
    items: list[dict[str, Any]]
    next_after: tuple[datetime, str] | None


def _not_found(what: str = "ComparisonReport") -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=what)


def _require_expert(roles: frozenset[str]) -> None:
    """Every write of a report is an expert's act: an administrator alone is refused (the edge refuses it too; this is the command's own check)."""
    if "expert" not in roles:
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")


class ComparisonReportService:
    """The thirteen operations over the report tables, the shared AI-job core and the blob store. Stateless between calls apart from a small cache
    of parsed sources (keyed by the sha-256 of the MD, so a stale entry is impossible)."""

    def __init__(
        self, session_factory: "sessionmaker[Session]", *, blob_store: Any, comparison_modules: str = "none", provider_mode: str = "live",
        route_reader: RouteReader = read_route, pdf_runner: ChildRunner | None = None, repository: ReportRepository | None = None,
        commands: CommandRepository | None = None, summaries: SummaryReader | None = None,
    ) -> None:
        if provider_mode not in ("live", "recorded"):
            raise ValueError("the provider mode is live or recorded")
        self._factory = session_factory
        self._store = blob_store
        self._modules = parse_modules(comparison_modules)
        self._versions_module_on = MODULE_VERSIONS in enabled_modules(self._modules)
        self._provider_mode = provider_mode
        self._route_reader = route_reader
        self._runner = pdf_runner
        self._repo = repository or ReportRepository()
        self._commands = commands or CommandRepository()
        self._summaries = summaries or SummaryReader()
        self._sources: dict[tuple[str, bool], SourceDoc] = {}

    @property
    def repository(self) -> ReportRepository:
        return self._repo

    # -- the module flag -----------------------------------------------------------------------------
    def _require_versions_module(self) -> None:
        """``503 dependency_unavailable`` (``comparison_modules``) unless «Сравнение версий» is on: the first statement of every operation."""
        if not self._versions_module_on:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_modules")

    def _core(self, method: ReportAiMethod | None = None) -> ComparisonAiJobService:
        return ComparisonAiJobService(
            self._factory, methods=[] if method is None else [method], comparison_modules=self._modules,
            provider_mode=self._provider_mode, route_reader=self._route_reader,
        )

    # -- blobs ---------------------------------------------------------------------------------------
    def publish(self, content: bytes, role: str, media_type: str) -> str:
        return ProfileBlobPublisher(self._factory, self._store).publish(content, role=role, media_type=media_type)

    def read_blob(self, blob_id: str) -> bytes:
        try:
            return self._store.read(parse_blob_id(blob_id), verify=True)
        except BlobNotFoundError:
            raise _not_found() from None
        except StorageError as failure:
            from auditmanager.shared.errors import from_internal

            code = from_internal(getattr(failure, "code", "") or "")
            raise DomainError(code) from None

    def artifact_bytes(self, session: Session, report_id: str, kind: str) -> bytes | None:
        artifact = ReportRepository.latest(self._repo.artifacts(session, report_id), kind)
        return None if artifact is None else self.read_blob(artifact.blob_id)

    # -- the source of a report ----------------------------------------------------------------------
    def source_doc(self, session: Session, row: ReportRow) -> SourceDoc:
        raw = self.artifact_bytes(session, row.report_id, ARTIFACT_SOURCE_MD)
        if raw is None:
            raise _not_found()
        return self._doc_for(session, raw=raw, source=row.source, series_id=row.series_id, name=row.source_name or "summary.md")

    def _doc_for(
        self, session: Session, *, raw: bytes, source: str, series_id: str, name: str, records: Mapping[str, Any] | None = None,
    ) -> SourceDoc:
        """The MD parsed. A summary made by the program keeps its records (the stored values of each line) **only while the summary of the
        series still reads as it did**: the records are rebuilt from the data and trusted when their text is the report's source. The same
        path serves the draft's estimate and every later reading, so the estimate a client consented to is the one a start computes."""
        digest = hashlib.sha256(raw).hexdigest()
        if records is None and source == SOURCE_SERIES_SUMMARY:
            series = self._summaries.series(session, series_id)
            if series is not None:
                rebuilt = build_summary(self._summaries.data(session, series))
                if hashlib.sha256(rebuilt.text.encode("utf-8")).hexdigest() == digest:
                    records = rebuilt.records
        key = (digest, records is not None)
        if key not in self._sources:
            if len(self._sources) >= 4:
                self._sources.pop(next(iter(self._sources)))
            self._sources[key] = load_source(raw, name, records)
        return self._sources[key]

    def unchanged_from(self, session: Session, row: ReportRow, doc: SourceDoc | None = None) -> frozenset[str]:
        """The transitions an analytic report found to be the confirmed absence of changes (for a client report prepared from it): the
        identities of the MD's transitions (``T01`` …) whose verified scale is «Нет изменений содержания» and whose coverage is complete."""
        if row.prepared_from_id is None:
            return frozenset()
        text = self.artifact_bytes(session, row.prepared_from_id, ARTIFACT_TEXT)
        if text is None:
            return frozenset()
        report = json.loads(text).get("report") or {}
        found = {
            t["transition_id"] for t in report.get("transitions", [])
            if t.get("change_scope") == "Нет изменений содержания" and (t.get("completeness") or {}).get("complete") is not False
        }
        return frozenset(found)

    def _method(self, session: Session, row: ReportRow, *, doc: SourceDoc | None = None) -> ReportAiMethod:
        spec = ReportSpec(
            kind=row.kind, reuse=row.reuse, project_uid=row.project_uid, series_id=row.series_id, report_id=row.report_id,
            transitions=self._repo.transition_numbers(session, row.series_id), unchanged=self.unchanged_from(session, row),
        )
        return ReportAiMethod(
            spec, load_source=(lambda s: doc) if doc is not None else (lambda s: self.source_doc(s, row)),
            pinned_model=lambda s: self._route_reader(s, WORK_KIND, self._provider_mode).pinned_model, repository=self._repo,
        )

    @staticmethod
    def _scope(row: ReportRow) -> AiScope:
        return AiScope(method=METHOD, project_uid=row.project_uid, document_uid=row.document_uid, series_id=row.series_id)

    # -- the views -----------------------------------------------------------------------------------
    def _view_in(self, session: Session, report_id: str) -> dict[str, Any]:
        row = self._repo.get(session, report_id)
        if row is None:
            raise _not_found()
        job = None if row.job_id is None else self._core().view_in(session, row.job_id).as_dict()
        view = report_dict(row, self._repo.parts(session, report_id), self._repo.artifacts(session, report_id), job)
        if row.state == "draft" and row.deleted_at is None:
            view["estimate"] = self._draft_estimate(session, row)
        elif job is not None and job.get("state") == "paused" and job.get("pause_reason") in CONSENT_PAUSES:
            left = self._left_estimate(session, row, job["job_id"])
            if left is not None:
                view["estimate"] = left
        return view

    def _left_estimate(self, session: Session, row: ReportRow, job_id: str) -> dict[str, Any] | None:
        """The estimate of what a report **has left**, for the consent a resume carries after a pause for ``overrun`` or ``route_changed``: the
        report shows it beside the job's consented one, so the client has the digest to consent to (a report that is paused for another reason
        needs none). ``None`` when it cannot be computed now (no route)."""
        core = self._core(self._method(session, row))
        try:
            return core.estimate_in(session, self._scope(row), AiMode.LEFT, job=core.job(session, job_id)).as_dict()
        except DomainError:
            return None

    def _draft_estimate(self, session: Session, row: ReportRow) -> dict[str, Any]:
        """The estimate of a draft **now**: the digest a client consents to is the one a start will compute. The stored estimate (and its frozen
        digest) is what the draft showed when it was made; the route, the model or the earlier reports may have moved since, and a stale digest
        is refused at the start, so a read that showed the old one would leave the client with no way to a digest that is accepted. A route that
        is gone (``dependency_unavailable``) leaves the stored estimate: the start refuses by its own reason."""
        try:
            return self._core(self._method(session, row)).estimate_in(session, self._scope(row), AiMode.START).as_dict()
        except DomainError as error:
            if error.code is ErrorCode.DEPENDENCY_UNAVAILABLE:
                return dict(row.estimate)
            raise

    def _live_row(self, session: Session, report_id: str) -> ReportRow:
        row = self._repo.get(session, report_id)
        if row is None or row.deleted_at is not None:
            raise _not_found()
        return row

    def _state_of(self, session: Session, row: ReportRow) -> str:
        job = None if row.job_id is None else {"state": self._core().job(session, row.job_id).state}
        return derived_state(row, job, self._repo.artifacts(session, row.report_id))

    def _after(self, report_id: str, *, stage: str | None = None) -> dict[str, Any]:
        """Bring the stored state in step with the job after a command of the core committed, and answer the report."""
        with session_scope(self._factory) as session:
            row = self._repo.get(session, report_id)
            if row is None:
                raise _not_found()
            if row.job_id is not None:
                sync_report(session, self._repo, report_id, self._core().job(session, row.job_id), stage=stage)
            return self._view_in(session, report_id)

    # -- (1) the MD summary --------------------------------------------------------------------------
    def read_series_summary(self, *, series_id: str) -> bytes:
        self._require_versions_module()
        with session_scope(self._factory) as session:
            series = self._summaries.series(session, series_id)
            if series is None:
                raise _not_found("ComparisonSeries")
            data = self._summaries.data(session, series)
            if not self._summaries.available(data):
                raise conflict(CONFLICT_SUMMARY_UNAVAILABLE)
            return build_summary(data).text.encode("utf-8")

    # -- (2) a draft ---------------------------------------------------------------------------------
    def create_report(
        self, *, series_id: str, kind: str, reuse: bool, user_uid: str, actor_label: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        """«Сформировать PDF-отчёт…», source «сводка проекта»: a ``draft`` with its estimate; no model is called, nothing is spent."""
        self._require_versions_module()
        _require_expert(actor_roles)
        kind = self._kind(kind)
        fingerprint = payload_fingerprint({
            "command": "create_comparison_report.v1", "series_id": series_id, "kind": kind, "reuse": bool(reuse),
        })
        with session_scope(self._factory) as session:
            claim = self._commands.begin(
                session, command_type="create_comparison_report", idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._view_in(session, str(claim.outcome["report_id"]))
            series = self._summaries.series(session, series_id)
            if series is None:
                raise _not_found("ComparisonSeries")
            data = self._summaries.data(session, series)
            if not self._summaries.available(data):
                raise conflict(CONFLICT_SUMMARY_UNAVAILABLE)
            summary = build_summary(data)
            report_id = self._draft(
                session, series=series, kind=kind, source=SOURCE_SERIES_SUMMARY, raw=summary.text.encode("utf-8"),
                filename=summary.filename, source_name=summary.filename, reuse=bool(reuse), prepared_from=None, records=summary.records,
                unchanged=frozenset(), user_uid=user_uid, actor_label=actor_label, command_id=str(claim.command_id),
            )
            self._commands.succeed(session, claim.command_id, {"report_id": report_id})
            return self._view_in(session, report_id)

    def upload_report_source(
        self, *, series_id: str, kind: str, reuse: bool, content: bytes, source_name: str | None, user_uid: str, actor_label: str,
        actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        """«загрузить MD-файл»: the body is the file. Empty, over 20 MiB, not UTF-8, without a transition ``## N. … A → B`` or naming a
        transition the series does not have is ``422 validation_failed`` (``comparison_report_source_invalid``) and nothing is written."""
        self._require_versions_module()
        _require_expert(actor_roles)
        kind = self._kind(kind)
        digest = hashlib.sha256(content).hexdigest()
        fingerprint = payload_fingerprint({
            "command": "upload_comparison_report_source.v1", "series_id": series_id, "kind": kind, "reuse": bool(reuse),
            "source_sha256": digest, "source_name": source_name,
        })
        with session_scope(self._factory) as session:
            claim = self._commands.begin(
                session, command_type="upload_comparison_report_source", idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._view_in(session, str(claim.outcome["report_id"]))
            series = self._summaries.series(session, series_id)
            if series is None:
                raise _not_found("ComparisonSeries")
            doc = self._validated_upload(session, series, content, source_name)
            report_id = self._draft(
                session, series=series, kind=kind, source=SOURCE_UPLOADED_MD, raw=content, filename=doc.filename,
                source_name=source_name, reuse=bool(reuse), prepared_from=None, records=None, unchanged=frozenset(), user_uid=user_uid,
                actor_label=actor_label, command_id=str(claim.command_id), doc=doc,
            )
            self._commands.succeed(session, claim.command_id, {"report_id": report_id})
            return self._view_in(session, report_id)

    def _validated_upload(self, session: Session, series: SeriesRow, content: bytes, source_name: str | None) -> SourceDoc:
        if not content or len(content) > MAX_SOURCE_BYTES:
            raise source_invalid()
        filename = re.sub(r"[\x00-\x1f]+", " ", source_name or "upload.md").strip()[:200] or "upload.md"
        try:
            doc = load_source(content, filename)
        except ValueError:  # not UTF-8
            raise source_invalid() from None
        numbers = [t["number"] for t in doc.manifest["transitions"]]
        if not numbers or len(set(numbers)) != len(numbers):
            raise source_invalid()
        series_numbers = self._repo.transition_numbers(session, series.series_id)
        if any(n not in series_numbers for n in numbers):
            raise source_invalid()
        return doc

    def _draft(
        self, session: Session, *, series: SeriesRow, kind: str, source: str, raw: bytes, filename: str, source_name: str | None,
        reuse: bool, prepared_from: str | None, records: Mapping[str, Any] | None, unchanged: frozenset[str], user_uid: str,
        actor_label: str, command_id: str, doc: SourceDoc | None = None,
    ) -> str:
        """The draft and its estimate, and the exact MD it is built from (a blob first, then the rows)."""
        doc = doc or self._doc_for(session, raw=raw, source=source, series_id=series.series_id, name=filename, records=records)
        spec = ReportSpec(
            kind=kind, reuse=reuse, project_uid=series.project_uid, series_id=series.series_id, report_id=None,
            transitions=self._repo.transition_numbers(session, series.series_id), unchanged=unchanged,
        )
        method = ReportAiMethod(
            spec, load_source=lambda s: doc, pinned_model=lambda s: self._route_reader(s, WORK_KIND, self._provider_mode).pinned_model,
            repository=self._repo,
        )
        scope = AiScope(method=METHOD, project_uid=series.project_uid, document_uid=series.document_uid, series_id=series.series_id)
        estimate = self._core(method).estimate_in(session, scope, AiMode.START).as_dict()
        blob_id = self.publish(raw, ROLE_SOURCE, _MEDIA[ARTIFACT_SOURCE_MD])
        report_id = self._repo.insert(
            session, project_uid=series.project_uid, document_uid=series.document_uid, series_id=series.series_id, kind=kind,
            source=source, estimate=estimate, reuse=reuse, source_name=source_name, source_sha256=doc.sha256, prepared_from_id=prepared_from,
            actor_user_uid=user_uid, actor_label=actor_label, command_id=command_id,
        )
        self._repo.add_artifact(session, report_id, kind=ARTIFACT_SOURCE_MD, blob_id=blob_id, sha256=doc.sha256, size_bytes=len(raw))
        return report_id

    @staticmethod
    def _kind(kind: str) -> str:
        if kind not in KINDS:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="kind", constraint="enum")
        return kind

    # -- reads ---------------------------------------------------------------------------------------
    def get_report(self, *, report_id: str) -> dict[str, Any]:
        self._require_versions_module()
        with session_scope(self._factory) as session:
            self._live_row(session, report_id)
            return self._view_in(session, report_id)

    def list_reports(self, *, series_id: str, after: tuple[datetime, str] | None, limit: int) -> ReportPage:
        self._require_versions_module()
        with session_scope(self._factory) as session:
            if self._summaries.series(session, series_id) is None:
                raise _not_found("ComparisonSeries")
            rows = self._repo.list_for_series(session, series_id, after=after, limit=limit + 1)
            page = rows[:limit]
            items = [self._view_in(session, r.report_id) for r in page]
            more = len(rows) > limit
            return ReportPage(items, (page[-1].created_at, page[-1].report_id) if more and page else None)

    def read_report_pdf(self, *, report_id: str) -> bytes:
        self._require_versions_module()
        with session_scope(self._factory) as session:
            self._live_row(session, report_id)
            content = self.artifact_bytes(session, report_id, ARTIFACT_PDF)
            if content is None:
                raise conflict(CONFLICT_REPORT_STATE)
            return content

    def read_report_source_md(self, *, report_id: str) -> bytes:
        self._require_versions_module()
        with session_scope(self._factory) as session:
            self._live_row(session, report_id)
            content = self.artifact_bytes(session, report_id, ARTIFACT_SOURCE_MD)
            if content is None:
                raise conflict(CONFLICT_REPORT_STATE)
            return content

    # -- (3) start with consent, cancel, continue ----------------------------------------------------
    def start_report(
        self, *, report_id: str, consent: AiConsentInput, user_uid: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        """«Начать»: consent to the draft's estimate. The shared core writes the job and the first items in one transaction (a stale digest, a
        ceiling, nothing to do, an unconfirmed consent and a missing route refuse and write nothing); the report is linked to its job in that
        same transaction, so a report has **one live job** and a second start finds it no longer a draft (``comparison_report_state``)."""
        self._require_versions_module()
        _require_expert(actor_roles)
        # The core's key is derived from the report too: the core's fingerprint has no report in it, so one client key can never start two.
        derived = hashlib.sha256(f"{report_id}:{idempotency_key}".encode("utf-8")).hexdigest()
        with session_scope(self._factory) as session:
            row = self._live_row(session, report_id)
            if row.state != "draft" and not self._claimed(session, "start_comparison_report", derived):
                raise conflict(CONFLICT_REPORT_STATE)
            method = self._method(session, row)
        command = AiJobCommand(
            command_type="start_comparison_report", idempotency_key=derived, user_uid=user_uid, actor_roles=actor_roles,
        )
        self._core(method).start(scope=self._scope(row), consent=consent, command=command)
        return self._after(report_id)

    def _claimed(self, session: Session, command_type: str, key: str) -> bool:
        """Whether the core already holds this key: a repeat replays, so the state the first call left behind is no reason to refuse it."""
        return self._commands.find(session, command_type=command_type, idempotency_key=IdempotencyKey(key)) is not None

    def cancel_report(self, *, report_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        """«Отменить»: a queued, running or paused report stops; its finished parts are kept."""
        self._require_versions_module()
        _require_expert(actor_roles)
        with session_scope(self._factory) as session:
            row = self._live_row(session, report_id)
            if row.job_id is None or (
                self._state_of(session, row) not in LIVE_STATES and not self._claimed(session, "cancel_comparison_report", idempotency_key)
            ):
                raise conflict(CONFLICT_REPORT_STATE)
            method, job_id = self._method(session, row), row.job_id
        command = AiJobCommand("cancel_comparison_report", idempotency_key, user_uid, actor_roles)
        self._core(method).cancel(job_id=job_id, method=METHOD, command=command)
        return self._after(report_id)

    def continue_report(
        self, *, report_id: str, consent: AiConsentInput | None, user_uid: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        """«Продолжить»: a paused report resumes (after ``overrun`` or ``route_changed`` under a new consent); a partial, failed or cancelled one is
        finished under the consent it already holds («Досчитать»). The finished parts are reused; a queued, running, completed or draft report is
        ``comparison_report_state``."""
        self._require_versions_module()
        _require_expert(actor_roles)
        with session_scope(self._factory) as session:
            row = self._live_row(session, report_id)
            state = self._state_of(session, row) if row.job_id is not None else row.state
            replay = self._claimed(session, "continue_comparison_report", idempotency_key)
            if row.job_id is None or (state not in ("paused", "partial", "failed", "cancelled") and not replay):
                raise conflict(CONFLICT_REPORT_STATE)
            method, job_id = self._method(session, row), row.job_id
        command = AiJobCommand("continue_comparison_report", idempotency_key, user_uid, actor_roles)
        core = self._core(method)
        if state == "paused":
            core.resume(job_id=job_id, method=METHOD, command=command, consent=consent)
        else:
            core.finish(job_id=job_id, method=METHOD, command=command)
        return self._after(report_id)

    # -- (4) «Пересобрать PDF», delete, prepare the client report ------------------------------------
    def rebuild_report_pdf(self, *, report_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        """«Пересобрать PDF»: the PDF is written again from the stored text; **no model is called and nothing is spent**. A report whose text is
        not complete is ``comparison_report_state``. A child that ends without a PDF leaves the earlier PDF where it was."""
        self._require_versions_module()
        _require_expert(actor_roles)
        fingerprint = payload_fingerprint({"command": "rebuild_comparison_report_pdf.v1", "report_id": report_id})
        with session_scope(self._factory) as session:
            row = self._live_row(session, report_id)
            claim = self._commands.begin(
                session, command_type="rebuild_comparison_report_pdf", idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._view_in(session, report_id)
            text = self.artifact_bytes(session, row.report_id, ARTIFACT_TEXT)
            if text is None:
                raise conflict(CONFLICT_REPORT_STATE)
            document = json.loads(text)
            try:
                written = write_pdf(document, runner=self._runner)
            except (PdfFailed, ChildStartError):
                raise DomainError(ErrorCode.INTERNAL_ERROR, message="the PDF could not be written; the earlier PDF stays") from None
            if written.problems:
                raise DomainError(ErrorCode.INTERNAL_ERROR, message="the PDF did not pass its check; the earlier PDF stays")
            blob_id = self.publish(written.content, ROLE_PDF, _MEDIA[ARTIFACT_PDF])
            self._repo.add_artifact(
                session, report_id, kind=ARTIFACT_PDF, blob_id=blob_id, sha256=hashlib.sha256(written.content).hexdigest(),
                size_bytes=len(written.content),
            )
            self._commands.succeed(session, claim.command_id, {"report_id": report_id})
            return self._view_in(session, report_id)

    def delete_report(self, *, report_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        """«Удалить»: a tombstone (``deleted_at``); the report leaves the history and **no published blob is deleted** (ADR-0025 decision 9). A
        report that is queued, running or paused is ``comparison_report_state`` (a paused job would stay in the installation's queue)."""
        self._require_versions_module()
        _require_expert(actor_roles)
        fingerprint = payload_fingerprint({"command": "delete_comparison_report.v1", "report_id": report_id})
        with session_scope(self._factory) as session:
            row = self._repo.get(session, report_id)
            if row is None:
                raise _not_found()
            claim = self._commands.begin(
                session, command_type="delete_comparison_report", idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._view_in(session, report_id)
            if row.deleted_at is not None:
                raise _not_found()
            if self._state_of(session, row) in LIVE_STATES:
                raise conflict(CONFLICT_REPORT_STATE)
            self._repo.tombstone(session, report_id)
            self._commands.succeed(session, claim.command_id, {"report_id": report_id})
            return self._view_in(session, report_id)

    def prepare_client_report(
        self, *, report_id: str, reuse: bool, user_uid: str, actor_label: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        """«Подготовить отчёт для заказчика»: a new ``client`` draft with its estimate that reads a finished analytic report: it is built from the
        same MD, and a transition the analytic report verified as the absence of changes is not asked again. No model is called."""
        self._require_versions_module()
        _require_expert(actor_roles)
        fingerprint = payload_fingerprint({"command": "prepare_comparison_client_report.v1", "report_id": report_id, "reuse": bool(reuse)})
        with session_scope(self._factory) as session:
            parent = self._live_row(session, report_id)
            claim = self._commands.begin(
                session, command_type="prepare_comparison_client_report", idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._view_in(session, str(claim.outcome["report_id"]))
            if parent.kind != KIND_ANALYTIC or self._state_of(session, parent) != "completed":
                raise conflict(CONFLICT_REPORT_STATE)
            raw = self.artifact_bytes(session, parent.report_id, ARTIFACT_SOURCE_MD)
            if raw is None:
                raise conflict(CONFLICT_REPORT_STATE)
            series = self._summaries.series(session, parent.series_id)
            if series is None:
                raise _not_found("ComparisonSeries")
            unchanged = self.unchanged_from(session, _as_child(parent))
            created = self._draft(
                session, series=series, kind=KIND_CLIENT, source=parent.source, raw=raw, filename=parent.source_name or "summary.md",
                source_name=parent.source_name, reuse=bool(reuse), prepared_from=parent.report_id, records=None, unchanged=unchanged,
                user_uid=user_uid, actor_label=actor_label, command_id=str(claim.command_id),
            )
            self._commands.succeed(session, claim.command_id, {"report_id": created})
            return self._view_in(session, created)


def _as_child(parent: ReportRow) -> ReportRow:
    """``parent`` as the ``prepared_from`` view of a not yet existing child: ``_unchanged_from`` reads its ``prepared_from_id``."""
    from dataclasses import replace

    return replace(parent, prepared_from_id=parent.report_id)
