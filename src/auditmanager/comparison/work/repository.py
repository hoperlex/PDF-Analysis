"""The only writer of ``comparison_work`` and ``comparison_work_attempt`` (`CMP-WORK-01`).

The Lease pattern of ``jobs`` (ADR-0025 decision 4) over the comparison-local queue, without a Run:
an item is claimed under a row lock and a lease, kept alive by a heartbeat on database time,
fenced by an execution token, reclaimed when the lease expires, paused, cancelled and ended with a
typed outcome. Every state change goes along an edge of migration ``0038`` (the trigger refuses any
other); the SQL here names the expected source state, so a lost race is a refusal, never a quiet
overwrite.

The execution token is secret-class: it is carried only by :class:`ItemAuthority`, compared for
equality while the item is locked, and never formatted into a message.

Attempt accounting. ``attempt_count`` is the number of attempts *charged* against ``max_attempts``:
a claim charges one, a lost lease keeps the charge, a retryable failure keeps the charge, and a
yield gives it back (so an item that waits for something never exhausts its budget). Attempt rows
are numbered ``max(attempt_no) + 1`` and are the audit trail; none is ever deleted.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.modules import MODULE_STAGES, MODULE_VERSIONS
from auditmanager.comparison.work.model import (
    KIND_PATTERN,
    LEASE_SECONDS,
    REASON_ATTEMPT_BUDGET,
    REASON_LEASE_EXPIRED,
    REASON_PATTERN,
    TERMINAL_STATES,
    Completed,
    Failed,
    ItemAuthority,
    Outcome,
    SpendSettler,
    WorkItem,
    Yielded,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonWorkAttemptId, ComparisonWorkId

__all__ = [
    "CANCEL_REQUESTED",
    "CancelResult",
    "ComparisonWorkRepository",
    "Enqueued",
    "RETRY_BACKOFF_CAP_SECONDS",
    "WorkRecord",
    "retry_delay_seconds",
]

#: What :meth:`ComparisonWorkRepository.cancel` answers for an item that is leased or running: the
#: request is recorded and the holder ends the item at its next checkpoint, or the reclaim does.
CANCEL_REQUESTED: Final[str] = "cancel_requested"
RETRY_BACKOFF_CAP_SECONDS: Final[float] = 300.0
_MODULES: Final[frozenset[str]] = frozenset({MODULE_VERSIONS, MODULE_STAGES})
_LOCK_TIMEOUT = text("SET LOCAL lock_timeout = '2s'")

_INSERT = text(
    "INSERT INTO comparison_work (comparison_work_id, project_uid, module, kind, payload, "
    "dedupe_key, priority, not_before, max_attempts, comparison_upload_id, comparison_series_id, "
    "created_by_user_uid, comparison_ai_job_id) "
    "VALUES (:work_id, :project_uid, :module, :kind, CAST(:payload AS jsonb), :dedupe_key, "
    ":priority, clock_timestamp() + make_interval(secs => :delay), :max_attempts, "
    ":upload_id, :series_id, :created_by, :ai_job_id) "
    "ON CONFLICT (project_uid, kind, dedupe_key) "
    "WHERE dedupe_key IS NOT NULL AND terminal_at IS NULL DO NOTHING "
    "RETURNING comparison_work_id"
)
_LIVE_BY_DEDUPE = text(
    "SELECT comparison_work_id FROM comparison_work WHERE project_uid = :project_uid "
    "AND kind = :kind AND dedupe_key = :dedupe_key AND terminal_at IS NULL"
)
#: The claim's pick: the strongest queued item of a module that is on and a kind that has a handler.
#: ``SKIP LOCKED`` lets two claimants take two items instead of queueing on one, and the row lock
#: is what makes the second claimant's pick of the *same* item impossible.
_PICK = text(
    "SELECT w.comparison_work_id, w.project_uid, w.module, w.kind, w.payload, "
    "w.comparison_upload_id, w.comparison_series_id, w.created_by_user_uid, w.max_attempts "
    "FROM comparison_work w WHERE w.state = 'queued' "
    "AND w.module = ANY (CAST(:modules AS text[])) AND w.kind = ANY (CAST(:kinds AS text[])) "
    "AND w.not_before <= statement_timestamp() AND w.cancel_requested_at IS NULL "
    "ORDER BY w.priority DESC, w.not_before, w.created_at, w.comparison_work_id "
    "LIMIT 1 FOR UPDATE OF w SKIP LOCKED"
)
_INSERT_ATTEMPT = text(
    "INSERT INTO comparison_work_attempt (comparison_work_attempt_id, comparison_work_id, "
    "attempt_no, state, execution_token, worker_id) VALUES (:attempt_id, :work_id, "
    "(SELECT coalesce(max(attempt_no), 0) + 1 FROM comparison_work_attempt "
    "WHERE comparison_work_id = :work_id), 'created', gen_random_uuid()::text, :worker_id) "
    "RETURNING attempt_no, execution_token"
)
_SET_CURRENT = text(
    "UPDATE comparison_work SET current_work_attempt_id = :attempt_id, "
    "updated_at = statement_timestamp() "
    "WHERE comparison_work_id = :work_id AND state = 'queued'"
)
_LEASE_ATTEMPT = text(
    "UPDATE comparison_work_attempt SET state = 'leased', updated_at = statement_timestamp(), "
    "heartbeat_at = statement_timestamp(), "
    "lease_expires_at = statement_timestamp() + make_interval(secs => :lease_seconds) "
    "WHERE comparison_work_attempt_id = :attempt_id AND state = 'created'"
)
_ADVANCE_WORK = text(
    "UPDATE comparison_work SET state = :to_state, updated_at = statement_timestamp(), "
    "terminal_at = CASE WHEN :terminal THEN statement_timestamp() ELSE NULL END, "
    "failure_reason = :failure_reason, "
    "attempt_count = greatest(attempt_count + :attempt_delta, 0), "
    "not_before = CASE WHEN CAST(:delay AS double precision) IS NULL THEN not_before "
    "ELSE statement_timestamp() + make_interval(secs => CAST(:delay AS double precision)) END "
    "WHERE comparison_work_id = :work_id AND state = :from_state"
)
_ADVANCE_ATTEMPT = text(
    "UPDATE comparison_work_attempt SET state = :to_state, updated_at = statement_timestamp(), "
    "terminal_at = CASE WHEN :terminal THEN statement_timestamp() ELSE NULL END, "
    "failure_reason = :failure_reason "
    "WHERE comparison_work_attempt_id = :attempt_id AND state = :from_state"
)
_LOCK_WORK = text(
    "SELECT comparison_work_id, state, current_work_attempt_id, attempt_count, max_attempts, "
    "cancel_requested_at IS NOT NULL AS cancel_requested FROM comparison_work "
    "WHERE comparison_work_id = :work_id FOR UPDATE"
)
_LOCK_ATTEMPT = text(
    "SELECT state, execution_token, comparison_work_id, "
    "lease_expires_at IS NOT NULL AND lease_expires_at > statement_timestamp() AS lease_current "
    "FROM comparison_work_attempt WHERE comparison_work_attempt_id = :attempt_id FOR UPDATE"
)
_CHECK_UNLOCKED = text(
    "SELECT w.state AS work_state, w.current_work_attempt_id, a.state AS attempt_state, "
    "a.execution_token, "
    "a.lease_expires_at IS NOT NULL AND a.lease_expires_at > statement_timestamp() AS lease_current "
    "FROM comparison_work w LEFT JOIN comparison_work_attempt a "
    "ON a.comparison_work_attempt_id = :attempt_id AND a.comparison_work_id = w.comparison_work_id "
    "WHERE w.comparison_work_id = :work_id"
)
_HEARTBEAT = text(
    "UPDATE comparison_work_attempt SET heartbeat_at = statement_timestamp(), "
    "lease_expires_at = statement_timestamp() + make_interval(secs => :lease_seconds), "
    "updated_at = statement_timestamp() "
    "WHERE comparison_work_attempt_id = :attempt_id AND execution_token = :token "
    "AND state IN ('leased', 'running') AND lease_expires_at > statement_timestamp()"
)
_CANCEL_REQUESTED = text(
    "SELECT cancel_requested_at IS NOT NULL FROM comparison_work WHERE comparison_work_id = :work_id"
)
_EXPIRED = text(
    "SELECT a.comparison_work_attempt_id AS attempt_id, a.comparison_work_id AS work_id "
    "FROM comparison_work_attempt a WHERE a.state IN ('leased', 'running') "
    "AND ((CAST(:force_attempt_id AS text) IS NULL AND a.lease_expires_at <= statement_timestamp()) "
    "OR (CAST(:force_attempt_id AS text) IS NOT NULL "
    "AND a.comparison_work_attempt_id = :force_attempt_id)) "
    "ORDER BY a.comparison_work_id, a.comparison_work_attempt_id LIMIT 100"
)
_REQUEST_CANCEL = text(
    "UPDATE comparison_work SET cancel_requested_at = coalesce(cancel_requested_at, "
    "statement_timestamp()), updated_at = statement_timestamp() WHERE comparison_work_id = :work_id"
)
_PAUSE_UPLOAD = text(
    "UPDATE comparison_work SET state = 'paused', updated_at = statement_timestamp() "
    "WHERE comparison_upload_id = :upload_id AND state IN ('queued', 'retry_wait')"
)
_RESUME_UPLOAD = text(
    "UPDATE comparison_work SET state = 'queued', updated_at = statement_timestamp() "
    "WHERE comparison_upload_id = :upload_id AND state = 'paused'"
)
_CANCEL_UPLOAD_AT_REST = text(
    "UPDATE comparison_work SET state = 'cancelled', updated_at = statement_timestamp(), "
    "terminal_at = statement_timestamp() WHERE comparison_upload_id = :upload_id "
    "AND state IN ('queued', 'paused', 'retry_wait', 'spend_unknown')"
)
_CANCEL_UPLOAD_RUNNING = text(
    "UPDATE comparison_work SET cancel_requested_at = statement_timestamp(), "
    "updated_at = statement_timestamp() WHERE comparison_upload_id = :upload_id "
    "AND state IN ('leased', 'running') AND cancel_requested_at IS NULL"
)
_PAUSE_SERIES = text(
    "UPDATE comparison_work SET state = 'paused', updated_at = statement_timestamp() "
    "WHERE comparison_series_id = :series_id AND state IN ('queued', 'retry_wait')"
)
_RESUME_SERIES = text(
    "UPDATE comparison_work SET state = 'queued', updated_at = statement_timestamp() "
    "WHERE comparison_series_id = :series_id AND state = 'paused'"
)
_CANCEL_SERIES_AT_REST = text(
    "UPDATE comparison_work SET state = 'cancelled', updated_at = statement_timestamp(), "
    "terminal_at = statement_timestamp() WHERE comparison_series_id = :series_id "
    "AND state IN ('queued', 'paused', 'retry_wait', 'spend_unknown')"
)
_CANCEL_SERIES_RUNNING = text(
    "UPDATE comparison_work SET cancel_requested_at = statement_timestamp(), "
    "updated_at = statement_timestamp() WHERE comparison_series_id = :series_id "
    "AND state IN ('leased', 'running') AND cancel_requested_at IS NULL"
)
_COLUMNS = (
    "comparison_work_id, project_uid, module, kind, state, payload, priority, not_before, "
    "attempt_count, max_attempts, current_work_attempt_id, comparison_upload_id, comparison_series_id, "
    "cancel_requested_at IS NOT NULL AS cancel_requested, failure_reason, created_at, terminal_at"
)
_GET = text(f"SELECT {_COLUMNS} FROM comparison_work WHERE comparison_work_id = :work_id")
_LIVE_KINDS = text(
    "SELECT DISTINCT kind FROM comparison_work WHERE terminal_at IS NULL "
    "AND module = ANY (CAST(:modules AS text[]))"
)
_COUNTS = text(
    "SELECT state, count(*) AS n FROM comparison_work "
    "WHERE (CAST(:project_uid AS text) IS NULL OR project_uid = :project_uid) "
    "AND (CAST(:upload_id AS text) IS NULL OR comparison_upload_id = :upload_id) "
    "AND (CAST(:series_id AS text) IS NULL OR comparison_series_id = :series_id) GROUP BY state"
)


@dataclass(frozen=True, slots=True)
class Enqueued:
    """The item an enqueue answered with; ``created`` is ``False`` when a live item with the same
    ``(project, kind, dedupe key)`` already existed and was returned instead."""

    work_id: str
    created: bool


@dataclass(frozen=True, slots=True)
class CancelResult:
    """``cancelled`` items ended at rest; ``requested`` running items were asked to stop."""

    cancelled: int
    requested: int


@dataclass(frozen=True, slots=True)
class WorkRecord:
    """One row of ``comparison_work`` as a reader sees it (the token is never part of it)."""

    work_id: str
    project_uid: str
    module: str
    kind: str
    state: str
    payload: Mapping[str, Any]
    priority: int
    not_before: datetime
    attempt_count: int
    max_attempts: int
    current_attempt_id: str | None
    comparison_upload_id: str | None
    comparison_series_id: str | None
    cancel_requested: bool
    failure_reason: str | None
    created_at: datetime
    terminal_at: datetime | None


def retry_delay_seconds(charged_attempts: int) -> float:
    """The wait before a retryable failure is claimed again: 5, 10, 20 ... seconds, capped."""
    return min(RETRY_BACKOFF_CAP_SECONDS, 5.0 * 2.0 ** max(0, charged_attempts - 1))


def _refusal(machine: str, current: str, requested: str) -> DomainError:
    return DomainError(
        ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
        machine=machine, current_state=current, requested_state=requested,
    )


def _wake_workers(session: Session) -> None:
    """Hint every listening worker (delivered only if the caller's transaction commits).

    One channel serves runs and comparison work: a notification is a hint, the queue in PostgreSQL
    is the authority, and the worker's poll is the stated fallback.
    """
    from auditmanager.jobs.public import JobRepository

    JobRepository.wake_workers(session)


class ComparisonWorkRepository:
    """Enqueue, claim, fence, end and reclaim comparison work items."""

    def __init__(self, *, lease_seconds: float = LEASE_SECONDS) -> None:
        if lease_seconds <= 0:
            raise ValueError("a lease lasts a positive number of seconds")
        #: Stamped on database time at the claim and at every extension. An instance attribute so a
        #: test can shorten the claim and the extension together without a second code path.
        self.lease_seconds = lease_seconds

    # -- enqueue ------------------------------------------------------------------------------
    def enqueue(
        self, session: Session, *, project_uid: str, module: str, kind: str,
        payload: Mapping[str, Any] | None = None, dedupe_key: str | None = None,
        priority: int = 0, delay_seconds: float = 0.0, max_attempts: int = 3,
        comparison_upload_id: str | None = None, comparison_series_id: str | None = None,
        created_by_user_uid: str | None = None, comparison_ai_job_id: str | None = None,
    ) -> Enqueued:
        """Create an item in the caller's transaction and hint the workers.

        A live item (not yet terminal) with the same project, kind and dedupe key is returned
        instead of a second one: a double click, a retried command and a re-run enqueue the same
        work once. The kind need not have a handler in this process (the API holds none): the
        worker claims only kinds it has a handler for, and refuses to start for a module that
        has live items of an unhandled kind (:meth:`live_kinds`).
        """
        if module not in _MODULES:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="module", constraint="enum")
        if not KIND_PATTERN.match(kind):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="kind", constraint="pattern")
        if not -100 <= priority <= 100:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="priority", constraint="range")
        if not 1 <= max_attempts <= 10:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="max_attempts", constraint="range")
        if delay_seconds < 0:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="delay_seconds", constraint="range")
        if dedupe_key is not None and not 1 <= len(dedupe_key) <= 256:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="dedupe_key", constraint="length")
        body = {} if payload is None else dict(payload)
        if comparison_ai_job_id is not None:
            if body.get("ai_job_id", comparison_ai_job_id) != comparison_ai_job_id:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="ai_job_id", constraint="scope")
            job = session.execute(text(
                "SELECT project_uid, method FROM comparison_ai_job WHERE comparison_ai_job_id = :job"
            ), {"job": comparison_ai_job_id}).first()
            if job is None or job[0] != project_uid or module != ("stages" if job[1] == "stage_review" else "versions"):
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonAiJob")
            body["ai_job_id"] = comparison_ai_job_id
        for _ in range(3):
            work_id = str(ComparisonWorkId.new())
            inserted = session.execute(_INSERT, {
                "work_id": work_id, "project_uid": project_uid, "module": module, "kind": kind,
                "payload": json.dumps(body, sort_keys=True), "dedupe_key": dedupe_key,
                "priority": priority, "delay": float(delay_seconds), "max_attempts": max_attempts,
                "upload_id": comparison_upload_id, "series_id": comparison_series_id,
                "created_by": created_by_user_uid, "ai_job_id": comparison_ai_job_id,
            }).scalar_one_or_none()
            if inserted is not None:
                _wake_workers(session)
                return Enqueued(work_id=str(inserted), created=True)
            existing = session.execute(_LIVE_BY_DEDUPE, {
                "project_uid": project_uid, "kind": kind, "dedupe_key": dedupe_key,
            }).scalar_one_or_none()
            if existing is not None:
                return Enqueued(work_id=str(existing), created=False)
            # The live twin ended between the conflict and the read: the key is free again.
        raise DomainError(
            ErrorCode.CONFLICT, message="the dedupe key kept changing hands", aggregate_type="ComparisonWork",
        )

    # -- claim --------------------------------------------------------------------------------
    def claim(
        self, session: Session, *, worker_id: str, modules: frozenset[str] | Sequence[str],
        kinds: frozenset[str] | Sequence[str],
    ) -> WorkItem | None:
        """Take the strongest claimable item of ``modules`` and ``kinds``, or ``None``.

        The caller commits. Nothing here decides whether claiming is *allowed* (the pause, the
        module flag and the priority of Runs are the runner's gates): this is the lease. An empty
        ``modules`` or ``kinds`` claims nothing.
        """
        module_list, kind_list = sorted(modules), sorted(kinds)
        if not module_list or not kind_list:
            return None
        row = session.execute(
            _PICK, {"modules": module_list, "kinds": kind_list}
        ).mappings().first()
        if row is None:
            return None
        work_id = str(row["comparison_work_id"])
        attempt_id = str(ComparisonWorkAttemptId.new())
        attempt = session.execute(
            _INSERT_ATTEMPT, {"attempt_id": attempt_id, "work_id": work_id, "worker_id": worker_id},
        ).mappings().one()
        if session.execute(
            _SET_CURRENT, {"attempt_id": attempt_id, "work_id": work_id},
        ).rowcount != 1:
            raise _refusal("comparison_work", "queued", "leased")
        self._advance_work(session, work_id, "queued", "leased", attempt_delta=1)
        if session.execute(
            _LEASE_ATTEMPT, {"attempt_id": attempt_id, "lease_seconds": float(self.lease_seconds)},
        ).rowcount != 1:
            raise _refusal("comparison_work_attempt", "created", "leased")
        self._advance_work(session, work_id, "leased", "running")
        self._advance_attempt(session, attempt_id, "leased", "running")
        return WorkItem(
            work_id=work_id, attempt_id=attempt_id, attempt_no=int(attempt["attempt_no"]),
            project_uid=str(row["project_uid"]), module=str(row["module"]), kind=str(row["kind"]),
            payload=dict(row["payload"]), comparison_upload_id=row["comparison_upload_id"],
            comparison_series_id=row["comparison_series_id"],
            created_by_user_uid=row["created_by_user_uid"], max_attempts=int(row["max_attempts"]),
            authority=ItemAuthority(work_id, attempt_id, str(attempt["execution_token"])),
            _repository=self,
        )

    # -- lease --------------------------------------------------------------------------------
    def heartbeat(self, session: Session, authority: ItemAuthority) -> bool:
        """Extend only a live lease, on database time and with a bounded lock wait."""
        session.execute(_LOCK_TIMEOUT)
        return session.execute(_HEARTBEAT, {
            "attempt_id": authority.attempt_id, "token": authority.execution_token,
            "lease_seconds": float(self.lease_seconds),
        }).rowcount == 1

    def cancel_requested(self, session: Session, work_id: str) -> bool:
        """Whether a cancel was requested for the item (read by the holder's heartbeat)."""
        return bool(session.execute(_CANCEL_REQUESTED, {"work_id": work_id}).scalar_one_or_none())

    def check_current(self, session: Session, authority: ItemAuthority) -> None:
        """Lock-free early check before slow I/O; never an authority fence (see
        :meth:`require_current`)."""
        row = session.execute(
            _CHECK_UNLOCKED, {"work_id": authority.work_id, "attempt_id": authority.attempt_id},
        ).mappings().first()
        if (row is None or row["current_work_attempt_id"] != authority.attempt_id
                or row["attempt_state"] is None):
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="ComparisonWorkAttempt")
        if not secrets.compare_digest(str(row["execution_token"]), authority.execution_token):
            raise DomainError(
                ErrorCode.EXECUTION_TOKEN_INVALID, aggregate_type="ComparisonWorkAttempt",
            )
        if (row["work_state"] != "running" or row["attempt_state"] != "running"
                or row["lease_current"] is not True):
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="ComparisonWorkAttempt")

    def require_current(self, session: Session, authority: ItemAuthority) -> None:
        """Lock the item, then its attempt, and refuse unless this attempt still holds the item.

        The publishing transaction calls this before it writes, so a worker whose lease was
        reclaimed cannot publish: ``stale_attempt`` for a superseded or expired attempt,
        ``execution_token_invalid`` for a token that is not the attempt's. The locks are held to
        the caller's commit, which is what serialises a publication with a reclaim and with a
        project erase (ADR-0025 decision 7): the item's and the attempt's rows stay locked, the
        erase must delete them before it can delete the project (``fk_comparison_work_project`` is
        ``ON DELETE RESTRICT``), so the project cannot vanish between this check and the
        publication. A share lock on the ``project`` row itself is not taken: the table is
        append-only for the application role (``scripts/recovery/grant_classification.py``), and a
        row lock needs the ``UPDATE`` privilege it does not have.
        """
        self._lock_current(session, authority)

    def _lock_current(self, session: Session, authority: ItemAuthority) -> Mapping[str, Any]:
        work = session.execute(_LOCK_WORK, {"work_id": authority.work_id}).mappings().first()
        if work is None or work["current_work_attempt_id"] != authority.attempt_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="ComparisonWorkAttempt")
        attempt = session.execute(
            _LOCK_ATTEMPT, {"attempt_id": authority.attempt_id},
        ).mappings().first()
        if attempt is None or attempt["comparison_work_id"] != authority.work_id:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="ComparisonWorkAttempt")
        if not secrets.compare_digest(str(attempt["execution_token"]), authority.execution_token):
            raise DomainError(
                ErrorCode.EXECUTION_TOKEN_INVALID, aggregate_type="ComparisonWorkAttempt",
            )
        if (work["state"] != "running" or attempt["state"] != "running"
                or attempt["lease_current"] is not True):
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="ComparisonWorkAttempt")
        return work

    # -- end of an attempt ----------------------------------------------------------------------
    def finish(self, session: Session, authority: ItemAuthority, outcome: Outcome) -> str:
        """End the attempt with the handler's outcome and answer the item's new state.

        Refuses (``stale_attempt`` / ``execution_token_invalid``) unless the attempt still holds
        the item. A cancel that was requested while the item ran wins over a yield or a failure
        (the item ends ``cancelled``); an item whose work completed ends ``succeeded`` whatever
        arrived late.
        """
        work = self._lock_current(session, authority)
        work_id, attempt_id = authority.work_id, authority.attempt_id
        if isinstance(outcome, Completed):
            self._advance_attempt(session, attempt_id, "running", "succeeded")
            self._advance_work(session, work_id, "running", "succeeded")
            return "succeeded"
        if work["cancel_requested"]:
            self._advance_attempt(session, attempt_id, "running", "cancelled")
            self._advance_work(session, work_id, "running", "cancelled")
            return "cancelled"
        if isinstance(outcome, Yielded):
            self._advance_attempt(session, attempt_id, "running", "superseded")
            self._advance_work(
                session, work_id, "running", "queued",
                delay=outcome.delay_seconds, attempt_delta=-1,
            )
            _wake_workers(session)
            return "queued"
        if not isinstance(outcome, Failed):
            raise TypeError("a handler ends an item with Completed, Failed or Yielded")
        self._advance_attempt(
            session, attempt_id, "running", "failed", failure_reason=outcome.reason,
        )
        charged = int(work["attempt_count"])
        if outcome.retry and charged < int(work["max_attempts"]):
            self._advance_work(session, work_id, "running", "retry_wait")
            self._advance_work(
                session, work_id, "retry_wait", "queued", delay=retry_delay_seconds(charged),
            )
            _wake_workers(session)
            return "queued"
        self._advance_work(session, work_id, "running", "failed", failure_reason=outcome.reason)
        return "failed"

    # -- reclaim --------------------------------------------------------------------------------
    def reclaim_expired(
        self, session: Session, *, spend_settlers: Sequence[SpendSettler] = (),
        force_attempt_id: str | None = None, reason: str = REASON_LEASE_EXPIRED,
    ) -> int:
        """Fence the attempts whose lease expired and decide what happens to their items.

        An item whose cancel was requested ends ``cancelled`` (after every ``spend_settlers`` entry
        has been asked about the lost attempt, so a call it left open is settled ``unknown`` and not
        left ``sent``); one whose attempt left a model call
        that may have spent (a ``spend_settlers`` entry answers ``True``) ends ``spend_unknown``
        and is never re-sent by itself (ADR-0025 decision 5); one whose attempt budget is spent
        ends ``failed`` with ``attempt_budget_exhausted``; any other goes back to the queue. A
        watchdog passes ``force_attempt_id`` and ``reason`` to fence its own attempt before the
        lease has run out. Rows are locked item first, attempt second, in a stable order, so
        overlapping sweeps and a publishing handler cannot wait in a cycle.
        """
        if not REASON_PATTERN.match(reason):
            raise ValueError("a reason is a lower-case code")
        session.execute(_LOCK_TIMEOUT)
        recovered = 0
        candidates = session.execute(
            _EXPIRED, {"force_attempt_id": force_attempt_id},
        ).mappings().all()
        for candidate in candidates:
            work_id, attempt_id = str(candidate["work_id"]), str(candidate["attempt_id"])
            work = session.execute(_LOCK_WORK, {"work_id": work_id}).mappings().first()
            if work is None or work["current_work_attempt_id"] != attempt_id:
                continue
            attempt = session.execute(_LOCK_ATTEMPT, {"attempt_id": attempt_id}).mappings().first()
            if (attempt is None or attempt["state"] not in {"leased", "running"}
                    or (attempt["lease_current"] and attempt_id != force_attempt_id)):
                continue
            self._advance_attempt(
                session, attempt_id, str(attempt["state"]), "lost", failure_reason=reason,
            )
            recovered += 1
            state = str(work["state"])
            if state not in {"leased", "running"}:
                continue
            if work["cancel_requested"]:
                # The cancel wins, but the lost attempt may have left a model call open (``sent``):
                # every settler is asked first and, unlike ``any(...)`` below, each one is asked
                # (the answer is not needed: whatever it says, the item ends ``cancelled``), so no
                # call stays open behind a cancelled item (`CMP-C0-FIX-01`, `CMP-SPEND-01` item 2).
                for settle in spend_settlers:
                    settle(session, attempt_id)
                self._advance_work(session, work_id, state, "cancelled")
            elif any(settle(session, attempt_id) for settle in spend_settlers):
                self._advance_work(session, work_id, state, "spend_unknown")
            elif int(work["attempt_count"]) >= int(work["max_attempts"]):
                self._advance_work(
                    session, work_id, state, "failed", failure_reason=REASON_ATTEMPT_BUDGET,
                )
            else:
                if state == "running":
                    self._advance_work(session, work_id, "running", "retry_wait")
                    state = "retry_wait"
                self._advance_work(session, work_id, state, "queued", delay=0.0)
                _wake_workers(session)
        return recovered

    # -- pause, resume, cancel ---------------------------------------------------------------------
    def pause(self, session: Session, work_id: str) -> str:
        """Pause an item that is waiting (``queued`` or ``retry_wait``); ``paused`` is idempotent.

        An item that is leased or running is not paused: the holder finishes it (an item is one
        page or one pair), and what pauses is the *queue* behind it. Any other state is refused.
        """
        row = self._locked(session, work_id)
        state = str(row["state"])
        if state == "paused":
            return state
        if state not in {"queued", "retry_wait"}:
            raise _refusal("comparison_work", state, "paused")
        self._advance_work(session, work_id, state, "paused")
        return "paused"

    def resume(self, session: Session, work_id: str) -> str:
        """Return a paused item to the queue; ``queued`` is idempotent."""
        row = self._locked(session, work_id)
        state = str(row["state"])
        if state == "queued":
            return state
        if state != "paused":
            raise _refusal("comparison_work", state, "queued")
        self._advance_work(session, work_id, "paused", "queued")
        _wake_workers(session)
        return "queued"

    def retry_spend_unknown(self, session: Session, work_id: str) -> str:
        """The explicit «Повторить» that clears ``spend_unknown`` (decision 5): back to the queue."""
        row = self._locked(session, work_id)
        state = str(row["state"])
        if state != "spend_unknown":
            raise _refusal("comparison_work", state, "queued")
        self._advance_work(session, work_id, "spend_unknown", "queued", delay=0.0)
        _wake_workers(session)
        return "queued"

    def cancel(self, session: Session, work_id: str) -> str:
        """Cancel an item. An item at rest ends ``cancelled`` at once (answer ``cancelled``); one that
        is leased or running is asked to stop (answer :data:`CANCEL_REQUESTED`) and its holder, or
        the reclaim, ends it; a terminal item is left as it is and its state is answered."""
        row = self._locked(session, work_id)
        state = str(row["state"])
        if state in TERMINAL_STATES:
            return state
        if state in {"leased", "running"}:
            session.execute(_REQUEST_CANCEL, {"work_id": work_id})
            return CANCEL_REQUESTED
        self._advance_work(session, work_id, state, "cancelled")
        return "cancelled"

    def pause_for_upload(self, session: Session, upload_id: str) -> int:
        """Pause every waiting item of an upload (the batch's «пауза»); the item in flight finishes."""
        return int(session.execute(_PAUSE_UPLOAD, {"upload_id": upload_id}).rowcount)

    def resume_for_upload(self, session: Session, upload_id: str) -> int:
        resumed = int(session.execute(_RESUME_UPLOAD, {"upload_id": upload_id}).rowcount)
        if resumed:
            _wake_workers(session)
        return resumed

    def cancel_for_upload(self, session: Session, upload_id: str) -> CancelResult:
        """Cancel an upload's items: the ones at rest end, the ones in flight are asked to stop."""
        cancelled = int(session.execute(_CANCEL_UPLOAD_AT_REST, {"upload_id": upload_id}).rowcount)
        requested = int(session.execute(_CANCEL_UPLOAD_RUNNING, {"upload_id": upload_id}).rowcount)
        return CancelResult(cancelled=cancelled, requested=requested)

    def pause_for_series(self, session: Session, series_id: str) -> int:
        """Pause every waiting item of a series (its «Пауза»); an item in flight finishes (it is one pair)."""
        return int(session.execute(_PAUSE_SERIES, {"series_id": series_id}).rowcount)

    def resume_for_series(self, session: Session, series_id: str) -> int:
        resumed = int(session.execute(_RESUME_SERIES, {"series_id": series_id}).rowcount)
        if resumed:
            _wake_workers(session)
        return resumed

    def cancel_for_series(self, session: Session, series_id: str) -> CancelResult:
        """Cancel a series' items: the ones at rest end, the ones in flight are asked to stop."""
        cancelled = int(session.execute(_CANCEL_SERIES_AT_REST, {"series_id": series_id}).rowcount)
        requested = int(session.execute(_CANCEL_SERIES_RUNNING, {"series_id": series_id}).rowcount)
        return CancelResult(cancelled=cancelled, requested=requested)

    # -- reads ----------------------------------------------------------------------------------
    def get(self, session: Session, work_id: str) -> WorkRecord | None:
        row = session.execute(_GET, {"work_id": work_id}).mappings().first()
        if row is None:
            return None
        return WorkRecord(
            work_id=row["comparison_work_id"], project_uid=row["project_uid"],
            module=row["module"], kind=row["kind"], state=row["state"],
            payload=dict(row["payload"]), priority=int(row["priority"]),
            not_before=row["not_before"], attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]), current_attempt_id=row["current_work_attempt_id"],
            comparison_upload_id=row["comparison_upload_id"], comparison_series_id=row["comparison_series_id"],
            cancel_requested=bool(row["cancel_requested"]),
            failure_reason=row["failure_reason"], created_at=row["created_at"],
            terminal_at=row["terminal_at"],
        )

    def live_kinds(self, session: Session, *, modules: frozenset[str] | Sequence[str]) -> frozenset[str]:
        """The kinds of the items of ``modules`` that are not terminal (the worker's start check)."""
        module_list = sorted(modules)
        if not module_list:
            return frozenset()
        return frozenset(
            str(kind) for kind in session.execute(_LIVE_KINDS, {"modules": module_list}).scalars()
        )

    def counts(
        self, session: Session, *, project_uid: str | None = None, upload_id: str | None = None,
        series_id: str | None = None,
    ) -> dict[str, int]:
        """Items by state, for a project, an upload and/or a series (every state with none is absent)."""
        rows = session.execute(
            _COUNTS, {"project_uid": project_uid, "upload_id": upload_id, "series_id": series_id}
        ).all()
        return {str(state): int(n) for state, n in rows}

    # -- transitions ----------------------------------------------------------------------------
    @staticmethod
    def _locked(session: Session, work_id: str) -> Mapping[str, Any]:
        row = session.execute(_LOCK_WORK, {"work_id": work_id}).mappings().first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonWork")
        return row

    @staticmethod
    def _advance_work(
        session: Session, work_id: str, from_state: str, to_state: str, *,
        failure_reason: str | None = None, delay: float | None = None, attempt_delta: int = 0,
    ) -> None:
        if (to_state == "failed") != (failure_reason is not None):
            raise ValueError("a work item carries a failure reason exactly when it failed")
        changed = session.execute(_ADVANCE_WORK, {
            "work_id": work_id, "from_state": from_state, "to_state": to_state,
            "terminal": to_state in TERMINAL_STATES, "failure_reason": failure_reason,
            "delay": delay, "attempt_delta": attempt_delta,
        }).rowcount
        if changed != 1:
            raise _refusal("comparison_work", from_state, to_state)

    @staticmethod
    def _advance_attempt(
        session: Session, attempt_id: str, from_state: str, to_state: str, *,
        failure_reason: str | None = None,
    ) -> None:
        changed = session.execute(_ADVANCE_ATTEMPT, {
            "attempt_id": attempt_id, "from_state": from_state, "to_state": to_state,
            "terminal": to_state in {"succeeded", "failed", "superseded", "lost", "cancelled"},
            "failure_reason": failure_reason,
        }).rowcount
        if changed != 1:
            raise _refusal("comparison_work_attempt", from_state, to_state)
