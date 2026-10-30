"""The only writer of ``comparison_ai_job`` (`CMP-AI-JOBS-01`) and the reads over a job's work items and journal rows.

Statements only, as ``comparison.work`` and ``comparison.spend`` do: every method takes the caller's session and **never
commits**; the service owns the transactions. Each state change names the states it expects (``WHERE state = ANY(...)``), so a
lost race is an answer of ``False``, never a quiet overwrite; the database's own trigger (``am_guard_comparison_ai_state_edges``)
refuses an edge it does not declare.

Reads of ``comparison_work`` and ``comparison_model_call`` are here because the queue's ``counts`` has no job filter and the
spend wrapper's ``job_spend`` is keyed by an item's payload: the job's progress and spend are read through
``comparison_work.comparison_ai_job_id`` (the column the seal added), so there is one money truth -- the journal.
The one write to ``comparison_work`` is :meth:`AiJobRepository.insert_item`: a job's item is written with its job (the column is
frozen at creation, so ``ComparisonWorkRepository.enqueue``, which has no such argument, cannot make it).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.model import (
    METHOD_PAIR_CHECK,
    METHOD_REPORT,
    METHOD_SHEET_CHANGES,
    METHOD_SPEC,
    METHOD_STAGE_REVIEW,
    AiEstimate,
    AiScope,
    AiJobRecord,
    AiJobSpend,
    AiProgress,
)
from auditmanager.comparison.spend.model import JOB_KEY
from auditmanager.comparison.work.model import KIND_PATTERN
from auditmanager.shared.identity import ComparisonAiJobId, ComparisonWorkId

__all__ = ["AiJobRepository", "LIVE_SCOPE_INDEXES", "WorkItemRow"]

#: The partial unique indexes of the database that hold "one live job per scope" (migration ``0040``). A unique violation of
#: one of them is the race the service's own look-before-insert lost.
LIVE_SCOPE_INDEXES: Final[tuple[str, ...]] = (
    "uq_comparison_ai_job_live_pair_check", "uq_comparison_ai_job_live_series", "uq_comparison_ai_job_live_sheet",
    "uq_comparison_ai_job_live_spec", "uq_comparison_ai_job_live_stage",
)
_COLUMNS = (
    "comparison_ai_job_id AS job_id, project_uid, document_uid, method, state, pause_reason, failure_reason, "
    "comparison_matrix_id AS matrix_id, comparison_series_id AS series_id, comparison_transition_id AS transition_id, "
    "comparison_sheet_pair_id AS sheet_pair_id, restart, connection_revision_id, pinned_model, provider_mode, estimate, "
    "estimate_digest, estimate_micros, ceiling_micros, consent_no, consented_by_user_uid, consented_at, command_id, "
    "created_at, updated_at, finished_at, stage_chain_run_id, "
    "(SELECT coalesce(r.effective_link_revision_id,r.stage_link_revision_id) FROM stage_chain_run r "
    "WHERE r.stage_chain_run_id = comparison_ai_job.stage_chain_run_id) AS stage_link_revision_id"
)
_INSERT = text(
    "INSERT INTO comparison_ai_job (comparison_ai_job_id, project_uid, document_uid, method, comparison_matrix_id, "
    "comparison_series_id, comparison_transition_id, comparison_sheet_pair_id, restart, connection_revision_id, "
    "pinned_model, provider_mode, estimate, estimate_digest, estimate_micros, ceiling_micros, consent_no, "
    "consented_by_user_uid, command_id, stage_chain_run_id) VALUES (:job_id, :project_uid, :document_uid, :method, :matrix_id, :series_id, "
    ":transition_id, :sheet_pair_id, :restart, :revision_id, :pinned_model, :provider_mode, CAST(:estimate AS jsonb), "
    ":digest, :estimate_micros, :ceiling_micros, 1, :user_uid, :command_id, :stage_chain_run_id)"
)
_GET = text(f"SELECT {_COLUMNS} FROM comparison_ai_job WHERE comparison_ai_job_id = :job_id")
_GET_LOCKED = text(f"SELECT {_COLUMNS} FROM comparison_ai_job WHERE comparison_ai_job_id = :job_id FOR UPDATE")
#: One live job per scope, per method (the shape of the four partial unique indexes): a pair check holds its document, a sheet
#: run its series or its sheet pair, a specification its transition. A report has no live-scope index (a series has several
#: reports), so it never holds a scope.
_LIVE_ON_SCOPE = {
    METHOD_PAIR_CHECK: "method = 'pair_check' AND document_uid = :document_uid",
    METHOD_SPEC: "method = 'spec' AND comparison_transition_id = :transition_id",
    METHOD_STAGE_REVIEW: "method = 'stage_review' AND stage_chain_run_id = :stage_chain_run_id",
}
_LIVE = "state IN ('queued', 'running', 'paused')"
_LATEST_ON_SCOPE = {
    METHOD_PAIR_CHECK: "method = 'pair_check' AND document_uid = :document_uid",
    METHOD_SPEC: "method = 'spec' AND comparison_transition_id = :transition_id",
    METHOD_STAGE_REVIEW: "method = 'stage_review' AND stage_chain_run_id = :stage_chain_run_id",
    METHOD_REPORT: "method = 'report' AND comparison_series_id = :series_id",
}
_MOVE = text(
    "UPDATE comparison_ai_job SET state = :to_state, pause_reason = :pause_reason, failure_reason = :failure_reason, "
    "updated_at = clock_timestamp(), "
    "finished_at = CASE WHEN :terminal THEN clock_timestamp() ELSE NULL END "
    "WHERE comparison_ai_job_id = :job_id AND state = ANY (CAST(:from_states AS text[]))"
)
_RENEW_CONSENT = text(
    "UPDATE comparison_ai_job SET estimate = CAST(:estimate AS jsonb), estimate_digest = :digest, "
    "estimate_micros = :estimate_micros, ceiling_micros = :ceiling_micros, connection_revision_id = :revision_id, "
    "pinned_model = :pinned_model, provider_mode = :provider_mode, consented_by_user_uid = :user_uid, "
    "consented_at = clock_timestamp(), consent_no = consent_no + 1, updated_at = clock_timestamp() "
    "WHERE comparison_ai_job_id = :job_id AND state = ANY (CAST(:from_states AS text[])) AND consent_no = :consent_no"
)
#: The items of a job with the facts the steering needs; ``attempt_count`` tells whether any was ever claimed.
_ITEMS = text(
    "SELECT comparison_work_id AS work_id, state, attempt_count, terminal_at IS NOT NULL AS terminal "
    "FROM comparison_work WHERE comparison_ai_job_id = :job_id ORDER BY created_at, comparison_work_id"
)
#: A work item of a job is written **with** its job: the column is frozen at creation (migration ``0040``: no later UPDATE may
#: set it) and the table's CHECK pairs it with the payload's ``ai_job_id``. ``ComparisonWorkRepository.enqueue`` has no such
#: argument, so the one statement is here; it is that method's statement with the column added, including the dedupe rule (a
#: live item with the same project, kind and key is returned instead of a second one).
_INSERT_ITEM = text(
    "INSERT INTO comparison_work (comparison_work_id, project_uid, module, kind, payload, dedupe_key, priority, not_before, "
    "max_attempts, created_by_user_uid, comparison_ai_job_id) "
    "VALUES (:work_id, :project_uid, :module, :kind, CAST(:payload AS jsonb), :dedupe_key, :priority, "
    "clock_timestamp() + make_interval(secs => :delay), :max_attempts, :created_by, :job_id) "
    "ON CONFLICT (project_uid, kind, dedupe_key) WHERE dedupe_key IS NOT NULL AND terminal_at IS NULL DO NOTHING "
    "RETURNING comparison_work_id"
)
#: A unit is counted once, by its latest work item: a finish or a retry queues a new item for the same unit key (the
#: dedupe key is the job and the unit), and the old, ended one must not count again.
_PROGRESS = text(
    "SELECT state, count(*) AS n FROM ("
    "SELECT DISTINCT ON (coalesce(dedupe_key, comparison_work_id)) state FROM comparison_work "
    "WHERE comparison_ai_job_id = :job_id "
    "ORDER BY coalesce(dedupe_key, comparison_work_id), created_at DESC, comparison_work_id DESC) latest GROUP BY state"
)
_LIVE_ITEMS = text(
    "SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id = :job_id AND terminal_at IS NULL "
    "AND (CAST(:excluding_work_id AS text) IS NULL OR comparison_work_id <> :excluding_work_id)"
)
_SPEND_COLUMNS = (
    "coalesce(sum(c.cost_micros) FILTER (WHERE c.state IN ('completed', 'failed')), 0) AS spent, "
    "coalesce(sum(c.estimate_micros) FILTER (WHERE c.state IN ('prepared', 'sent', 'unknown')), 0) AS reserved, "
    "count(c.comparison_model_call_id) AS calls, "
    "count(c.comparison_model_call_id) FILTER (WHERE c.state = 'unknown') AS unknown_calls, "
    "coalesce(sum(c.input_tokens), 0) AS input_tokens, coalesce(sum(c.output_tokens), 0) AS output_tokens"
)
_SPEND = text(
    f"SELECT {_SPEND_COLUMNS} FROM comparison_model_call c "
    "JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id WHERE w.comparison_ai_job_id = :job_id"
)
_SPENT_BEFORE = text(
    "SELECT coalesce(sum(c.cost_micros) FILTER (WHERE c.state IN ('completed', 'failed')), 0) "
    "FROM comparison_model_call c JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id "
    "WHERE w.comparison_ai_job_id = :job_id AND c.prepared_at < :before"
)
_WAITING = text(
    f"SELECT {_COLUMNS}, "
    "CASE WHEN state = 'queued' THEN row_number() OVER (PARTITION BY state ORDER BY created_at, comparison_ai_job_id) "
    "END AS queue_position FROM comparison_ai_job WHERE state IN ('queued', 'running', 'paused') "
    "ORDER BY CASE state WHEN 'running' THEN 0 WHEN 'queued' THEN 1 ELSE 2 END, created_at, comparison_ai_job_id "
    "LIMIT :limit"
)
_WAITING_TOTALS = text("SELECT state, count(*) AS n FROM comparison_ai_job WHERE state IN ('queued', 'running', 'paused') GROUP BY state")
_QUEUE_POSITION = text(
    "SELECT position FROM (SELECT comparison_ai_job_id, row_number() OVER (ORDER BY created_at, comparison_ai_job_id) "
    "AS position FROM comparison_ai_job WHERE state = 'queued') q WHERE comparison_ai_job_id = :job_id"
)


def _record(row: Any) -> AiJobRecord:
    values = {name: row[name] for name in AiJobRecord.__dataclass_fields__ if name != "estimate"}
    return AiJobRecord(estimate=dict(row["estimate"]), **values)


class WorkItemRow:
    """One work item of a job as the steering sees it (plain attributes: ``work_id``, ``state``, ``attempt_count``,
    ``terminal``)."""

    __slots__ = ("work_id", "state", "attempt_count", "terminal")

    def __init__(self, work_id: str, state: str, attempt_count: int, terminal: bool) -> None:
        self.work_id, self.state, self.attempt_count, self.terminal = work_id, state, attempt_count, terminal


class AiJobRepository:
    """Stateless; every method takes the caller's session and never commits."""

    __slots__ = ()

    # -- writes -----------------------------------------------------------------------------------
    def insert(
        self, session: Session, *, estimate: AiEstimate, user_uid: str, command_id: str,
    ) -> str:
        """Write the job row ``queued`` with its consented estimate and ``consent_no`` 1. A unique violation of a live-scope
        index propagates (the service maps it to ``comparison_ai_job_active``)."""
        scope = estimate.scope
        job_id = str(ComparisonAiJobId.new())
        session.execute(_INSERT, {
            "job_id": job_id, "project_uid": scope.project_uid, "document_uid": scope.document_uid,
            "method": scope.method, "matrix_id": scope.matrix_id, "series_id": scope.series_id,
            "transition_id": scope.transition_id, "sheet_pair_id": scope.sheet_pair_id, "restart": scope.restart,
            "stage_chain_run_id": scope.stage_chain_run_id,
            "revision_id": estimate.route.revision_id, "pinned_model": estimate.route.pinned_model,
            "provider_mode": estimate.route.provider_mode,
            "estimate": json.dumps(estimate.as_dict(with_state=False), sort_keys=True),
            "digest": estimate.estimate_digest, "estimate_micros": estimate.estimate_micros,
            "ceiling_micros": estimate.ceiling_micros, "user_uid": user_uid, "command_id": command_id,
        })
        return job_id

    def move(
        self, session: Session, job_id: str, *, from_states: Sequence[str], to_state: str,
        pause_reason: str | None = None, failure_reason: str | None = None,
    ) -> bool:
        """One state edge, guarded by the states it is taken from. ``False`` when the job is not in one of them (a lost race
        or a wrong state); the database refuses an edge it does not declare."""
        return session.execute(_MOVE, {
            "job_id": job_id, "to_state": to_state, "pause_reason": pause_reason, "failure_reason": failure_reason,
            "terminal": to_state in ("completed", "failed", "cancelled"), "from_states": list(from_states),
        }).rowcount == 1

    def renew_consent(
        self, session: Session, job_id: str, *, estimate: AiEstimate, user_uid: str, consent_no: int,
        from_states: Sequence[str],
    ) -> bool:
        """A new consent: the estimate, its digest, the figures, the route and the consenting user change together and
        ``consent_no`` rises by one (the table's trigger refuses a change of the estimate under the same number)."""
        return session.execute(_RENEW_CONSENT, {
            "job_id": job_id, "estimate": json.dumps(estimate.as_dict(with_state=False), sort_keys=True),
            "digest": estimate.estimate_digest, "estimate_micros": estimate.estimate_micros,
            "ceiling_micros": estimate.ceiling_micros, "revision_id": estimate.route.revision_id,
            "pinned_model": estimate.route.pinned_model, "provider_mode": estimate.route.provider_mode,
            "user_uid": user_uid, "consent_no": consent_no, "from_states": list(from_states),
        }).rowcount == 1

    def insert_item(
        self, session: Session, *, job: JobRecord, kind: str, payload: Mapping[str, Any], dedupe_key: str,
        priority: int, delay_seconds: float, max_attempts: int, user_uid: str,
    ) -> str | None:
        """Write one work item of ``job`` ``queued``, linked to it (``comparison_work.comparison_ai_job_id``, the column the
        progress and the spend read through) and carrying ``ai_job_id`` in its payload (the key the spend wrapper's ceilings
        sum). Answers its identity, or ``None`` when a live item with the same project, kind and dedupe key exists."""
        if payload.get(JOB_KEY) != job.job_id:
            raise ValueError("the payload of a job's item names the job")
        if not KIND_PATTERN.match(kind):
            raise ValueError("a work kind is a lower-case code")
        if not -100 <= priority <= 100 or not 1 <= max_attempts <= 10 or delay_seconds < 0:
            raise ValueError("a priority is -100 to 100, attempts 1 to 10 and a delay is not negative")
        inserted = session.execute(_INSERT_ITEM, {
            "work_id": str(ComparisonWorkId.new()), "project_uid": job.project_uid, "kind": kind,
            "module": "stages" if job.method == METHOD_STAGE_REVIEW else "versions",
            "payload": json.dumps(dict(payload), sort_keys=True), "dedupe_key": dedupe_key, "priority": priority,
            "delay": float(delay_seconds), "max_attempts": max_attempts, "created_by": user_uid, "job_id": job.job_id,
        }).scalar_one_or_none()
        return None if inserted is None else str(inserted)

    @staticmethod
    def wake_workers(session: Session) -> None:
        """Hint every listening worker that there is queued work (delivered only if the caller's transaction commits). One
        channel serves runs and comparison work; a notification is a hint, the queue in PostgreSQL is the authority."""
        from auditmanager.jobs.public import JobRepository

        JobRepository.wake_workers(session)

    # -- reads of a job ---------------------------------------------------------------------------
    def get(self, session: Session, job_id: str, *, lock: bool = False) -> AiJobRecord | None:
        row = session.execute(_GET_LOCKED if lock else _GET, {"job_id": job_id}).mappings().first()
        return None if row is None else _record(row)

    def live_on_scope(self, session: Session, scope: AiScope) -> AiJobRecord | None:
        """The live job that holds ``scope``, if the method has a live-scope rule (a report has none)."""
        if scope.method == METHOD_REPORT:
            return None
        if scope.method == METHOD_SHEET_CHANGES:
            clause = (
                "method = 'sheet_changes' AND comparison_series_id = :series_id" if scope.series_id is not None
                else "method = 'sheet_changes' AND comparison_sheet_pair_id = :sheet_pair_id"
            )
        else:
            clause = _LIVE_ON_SCOPE[scope.method]
        row = session.execute(
            text(f"SELECT {_COLUMNS} FROM comparison_ai_job WHERE {clause} AND {_LIVE} ORDER BY created_at LIMIT 1"),
            self._scope_parameters(scope),
        ).mappings().first()
        return None if row is None else _record(row)

    def latest_on_scope(self, session: Session, scope: AiScope) -> AiJobRecord | None:
        """The newest job of ``scope`` in any state (the read of «the latest job» a lane's GET shows)."""
        if scope.method == METHOD_SHEET_CHANGES:
            clause = (
                "method = 'sheet_changes' AND comparison_series_id = :series_id" if scope.series_id is not None
                else "method = 'sheet_changes' AND comparison_sheet_pair_id = :sheet_pair_id"
            )
        else:
            clause = _LATEST_ON_SCOPE[scope.method]
        row = session.execute(
            text(f"SELECT {_COLUMNS} FROM comparison_ai_job WHERE {clause} ORDER BY created_at DESC, comparison_ai_job_id DESC LIMIT 1"),
            self._scope_parameters(scope),
        ).mappings().first()
        return None if row is None else _record(row)

    @staticmethod
    def _scope_parameters(scope: AiScope) -> dict[str, Any]:
        return {
            "document_uid": scope.document_uid, "series_id": scope.series_id, "transition_id": scope.transition_id,
            "sheet_pair_id": scope.sheet_pair_id, "stage_chain_run_id": scope.stage_chain_run_id,
        }

    def queue_position(self, session: Session, job_id: str) -> int | None:
        """The place of a ``queued`` job among the installation's queued jobs (1 starts first), else ``None``."""
        value = session.execute(_QUEUE_POSITION, {"job_id": job_id}).scalar_one_or_none()
        return None if value is None else int(value)

    def waiting(self, session: Session, *, limit: int) -> tuple[list[tuple[AiJobRecord, int | None]], dict[str, int]]:
        """The installation's live jobs (running first, then queued in start order, then paused) with the queue position of
        each queued one, and the count of each state."""
        rows = session.execute(_WAITING, {"limit": limit}).mappings().all()
        totals = {str(state): int(n) for state, n in session.execute(_WAITING_TOTALS).all()}
        return [(_record(row), None if row["queue_position"] is None else int(row["queue_position"])) for row in rows], totals

    # -- reads through the job's work items and the journal ---------------------------------------
    def items(self, session: Session, job_id: str) -> list[WorkItemRow]:
        return [
            WorkItemRow(str(row["work_id"]), str(row["state"]), int(row["attempt_count"]), bool(row["terminal"]))
            for row in session.execute(_ITEMS, {"job_id": job_id}).mappings()
        ]

    def live_item_count(self, session: Session, job_id: str, *, excluding_work_id: str | None = None) -> int:
        return int(session.execute(_LIVE_ITEMS, {"job_id": job_id, "excluding_work_id": excluding_work_id}).scalar_one())

    def progress(self, session: Session, job_id: str) -> AiProgress:
        by_state = {str(state): int(n) for state, n in session.execute(_PROGRESS, {"job_id": job_id}).all()}
        return AiProgress(
            total=sum(by_state.values()), done=by_state.get("succeeded", 0), failed=by_state.get("failed", 0),
            unknown=by_state.get("spend_unknown", 0), by_state=by_state,
        )

    def spend(self, session: Session, job_id: str) -> AiJobSpend:
        row = session.execute(_SPEND, {"job_id": job_id}).one()
        return AiJobSpend(
            spent_micros=int(row.spent), reserved_micros=int(row.reserved), calls=int(row.calls),
            unknown_calls=int(row.unknown_calls), input_tokens=int(row.input_tokens), output_tokens=int(row.output_tokens),
        )

    def spent_before(self, session: Session, job_id: str, before: datetime) -> int:
        """What the job's calls prepared before ``before`` actually cost (the baseline of a later consent)."""
        return int(session.execute(_SPENT_BEFORE, {"job_id": job_id, "before": before}).scalar_one())
