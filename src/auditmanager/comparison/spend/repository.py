"""The only writer of ``comparison_model_call`` (`CMP-SPEND-01`, ADR-0025 decision 5).

The journal of every model call the comparison modules make, with the life ``prepared -> sent ->
completed | failed | unknown`` that migration ``0038`` enforces: a row can only be **inserted**
``prepared`` (a trigger), only move along the declared edges, and a terminal row never moves. Each
statement here names the state it expects, so a lost race (the reclaim settled the row first) is an
answer of ``False``, never a quiet overwrite.

Statements only, as ``jobs`` and ``executors.runner_repository`` do: every method takes the caller's
session and **never commits**. The wrapper (:mod:`.caller`) owns the transactions, because the
``prepared`` row must be committed on its own, before the adapter is called.

The reads that decide a call -- what a job and a day have cost, who else is using a connection --
live here too, beside the writes they must agree with. Two of them restate a fact of the ``jobs``
context: the advisory-lock key of a connection and the Job states that make a Run *active*. Both are
pinned to their original by a test (this context may not import ``jobs`` internals).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.spend.model import JOB_KEY, CallRecord, Spend
from auditmanager.shared.identity import ComparisonModelCallId

__all__ = ["ACTIVE_JOB_STATES", "ComparisonSpendRepository", "CONNECTION_LOCK_KEY", "DAY_LOCK_KEY"]

#: The key of the advisory lock a connection's single user is decided under: the one ``jobs``
#: takes for a Run's claim (``jobs.repository._LOCK_CONNECTION``). A comparison call takes the same
#: lock, so a Run's claim and a comparison call cannot both pass their check at once.
CONNECTION_LOCK_KEY: Final[str] = "auditmanager.executor_connection|"
#: The installation-wide lock the ceilings are decided under, so two workers cannot both fit one more
#: call under a ceiling that only one of them fits.
DAY_LOCK_KEY: Final[str] = "auditmanager.comparison_spend|day"
#: The Job states in which a Run is active on its connection (``jobs.repository._ACTIVE_JOB_STATES``).
ACTIVE_JOB_STATES: Final[tuple[str, ...]] = ("leased", "running", "retry_wait")

_COLUMNS = (
    "comparison_model_call_id AS call_id, comparison_work_id AS work_id, "
    "comparison_work_attempt_id AS attempt_id, work_kind, state, provider_mode, model_identity, "
    "connection_revision_id, request_sha256, estimate_micros, executor_task_id, response_sha256, "
    "input_tokens, output_tokens, latency_ms, cost_basis, cost_micros, error_code, prepared_at, "
    "sent_at, terminal_at"
)
_INSERT = text(
    "INSERT INTO comparison_model_call (comparison_model_call_id, comparison_work_id, "
    "comparison_work_attempt_id, work_kind, provider_mode, model_identity, connection_revision_id, "
    "request_sha256, estimate_micros) VALUES (:call_id, :work_id, :attempt_id, :work_kind, "
    ":provider_mode, :model_identity, :revision_id, :request_sha256, :estimate_micros)"
)
_MARK_SENT = text(
    "UPDATE comparison_model_call SET state = 'sent', sent_at = clock_timestamp() "
    "WHERE comparison_model_call_id = :call_id AND state = 'prepared'"
)
_COMPLETE = text(
    "UPDATE comparison_model_call SET state = 'completed', response_sha256 = :response_sha256, "
    "input_tokens = :input_tokens, output_tokens = :output_tokens, latency_ms = :latency_ms, "
    "cost_basis = :cost_basis, cost_micros = :cost_micros, terminal_at = clock_timestamp() "
    "WHERE comparison_model_call_id = :call_id AND state = 'sent'"
)
_FAIL = text(
    "UPDATE comparison_model_call SET state = 'failed', error_code = :error_code, "
    "response_sha256 = :response_sha256, input_tokens = :input_tokens, "
    "output_tokens = :output_tokens, latency_ms = :latency_ms, cost_basis = :cost_basis, "
    "cost_micros = :cost_micros, terminal_at = clock_timestamp() "
    "WHERE comparison_model_call_id = :call_id AND state IN ('prepared', 'sent')"
)
_UNKNOWN = text(
    "UPDATE comparison_model_call SET state = 'unknown', error_code = :error_code, "
    "terminal_at = clock_timestamp() "
    "WHERE comparison_model_call_id = :call_id AND state IN ('prepared', 'sent')"
)
#: The settler's statement: every call of a lost attempt that is not ended may have spent.
_SETTLE_ATTEMPT = text(
    "UPDATE comparison_model_call SET state = 'unknown', error_code = :error_code, "
    "terminal_at = clock_timestamp() "
    "WHERE comparison_work_attempt_id = :attempt_id AND state IN ('prepared', 'sent') "
    "RETURNING comparison_model_call_id"
)
#: The same for an attempt that ended some other way (the queue settles only a lost one, and not at all
#: when a cancel was requested): housekeeping, so that no row stays open for an attempt that is over.
_SETTLE_ABANDONED = text(
    "UPDATE comparison_model_call c SET state = 'unknown', error_code = :error_code, "
    "terminal_at = clock_timestamp() FROM comparison_work_attempt a "
    "WHERE a.comparison_work_attempt_id = c.comparison_work_attempt_id "
    "AND c.state IN ('prepared', 'sent') "
    "AND a.state IN ('succeeded', 'failed', 'superseded', 'lost', 'cancelled')"
)
_GET = text(f"SELECT {_COLUMNS} FROM comparison_model_call WHERE comparison_model_call_id = :call_id")
_OF_WORK = text(
    f"SELECT {_COLUMNS} FROM comparison_model_call WHERE comparison_work_id = :work_id "
    "ORDER BY prepared_at, comparison_model_call_id"
)
_ATTACH_TASK = text(
    "UPDATE comparison_model_call SET executor_task_id = :task_id "
    "WHERE comparison_model_call_id = :call_id AND executor_task_id IS NULL "
    "AND state IN ('prepared', 'sent')"
)
#: The cost and the reservations of one scope. ``actual`` is what is known to have been charged;
#: ``reserved`` is the estimate of a call that is open or ended ``unknown``. An unmetered call has an
#: estimate of zero (it is journalled so), so no filter on the basis is needed here.
_SPEND_COLUMNS = (
    "coalesce(sum(c.cost_micros) FILTER (WHERE c.state IN ('completed', 'failed')), 0) AS actual, "
    "coalesce(sum(c.estimate_micros) FILTER (WHERE c.state IN ('prepared', 'sent', 'unknown')), 0) "
    "AS reserved"
)
_JOB_SPEND = text(
    f"SELECT {_SPEND_COLUMNS} FROM comparison_model_call c "
    "JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id "
    "WHERE (CAST(:job_id AS text) IS NOT NULL AND w.project_uid = :project_uid "
    f"AND w.payload ->> '{JOB_KEY}' = :job_id) "
    "OR (CAST(:job_id AS text) IS NULL AND c.comparison_work_id = :work_id)"
)
#: The day is the UTC day of the database clock.
_DAY_SPEND = text(
    f"SELECT {_SPEND_COLUMNS} FROM comparison_model_call c "
    "WHERE c.prepared_at >= (date_trunc('day', clock_timestamp() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')"
)
_CONNECTION_OF = text(
    "SELECT connection_id FROM executor_connection_revision WHERE revision_id = :revision_id"
)
_LOCK_CONNECTION = text(
    f"SELECT pg_advisory_xact_lock(hashtextextended('{CONNECTION_LOCK_KEY}' || :connection_id, 0))"
)
_LOCK_DAY = text(f"SELECT pg_advisory_xact_lock(hashtextextended('{DAY_LOCK_KEY}', 0))")
_ACTIVE_STATES_SQL = "(" + ", ".join(f"'{s}'" for s in ACTIVE_JOB_STATES) + ")"
_CONNECTION_HAS_ACTIVE_RUN = text(
    "SELECT EXISTS (SELECT 1 FROM job j JOIN audit_run r ON r.run_id = j.run_id "
    "JOIN executor_connection_revision rev ON rev.revision_id = r.connection_revision_id "
    f"WHERE rev.connection_id = :connection_id AND j.state IN {_ACTIVE_STATES_SQL})"
)
#: A call is *active* on a connection while it is open **and** its attempt still holds the item: a
#: killed worker's call stays active until the reclaim ends its attempt (the Run rule: an expired
#: lease keeps the connection busy), and a row left open by an attempt that is over blocks nothing.
_CONNECTION_HAS_ACTIVE_CALL = text(
    "SELECT EXISTS (SELECT 1 FROM comparison_model_call c "
    "JOIN comparison_work_attempt a ON a.comparison_work_attempt_id = c.comparison_work_attempt_id "
    "JOIN executor_connection_revision rev ON rev.revision_id = c.connection_revision_id "
    "WHERE rev.connection_id = :connection_id AND c.state IN ('prepared', 'sent') "
    "AND a.state IN ('created', 'leased', 'running'))"
)
_OPEN_OF_OTHER_ATTEMPTS = text(
    "SELECT count(*) FROM comparison_model_call WHERE comparison_work_id = :work_id "
    "AND comparison_work_attempt_id <> :attempt_id AND state IN ('prepared', 'sent')"
)


def _record(row: Any) -> CallRecord:
    return CallRecord(**{name: row[name] for name in CallRecord.__dataclass_fields__})


class ComparisonSpendRepository:
    """Stateless; every method takes the caller's session and never commits."""

    __slots__ = ()

    # -- the life of a call -----------------------------------------------------------------------
    def prepare(
        self, session: Session, *, work_id: str, attempt_id: str, work_kind: str, provider_mode: str,
        model_identity: str, connection_revision_id: str | None, request_sha256: str,
        estimate_micros: int,
    ) -> str:
        """Insert the ``prepared`` row (the pre-call breadcrumb) and answer its identity. The caller
        commits it **before** the adapter is called."""
        call_id = str(ComparisonModelCallId.new())
        session.execute(_INSERT, {
            "call_id": call_id, "work_id": work_id, "attempt_id": attempt_id,
            "work_kind": work_kind, "provider_mode": provider_mode, "model_identity": model_identity,
            "revision_id": connection_revision_id, "request_sha256": request_sha256,
            "estimate_micros": int(estimate_micros),
        })
        return call_id

    def mark_sent(self, session: Session, call_id: str) -> bool:
        """``prepared -> sent``: the adapter is about to be called. ``False`` when the row is not
        ``prepared`` any more (the reclaim settled it)."""
        return session.execute(_MARK_SENT, {"call_id": call_id}).rowcount == 1

    def complete(
        self, session: Session, call_id: str, *, response_sha256: str, input_tokens: int,
        output_tokens: int, latency_ms: int, cost_basis: str, cost_micros: int,
    ) -> bool:
        """``sent -> completed`` with the reply's checksum, usage and cost."""
        return session.execute(_COMPLETE, {
            "call_id": call_id, "response_sha256": response_sha256, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "latency_ms": latency_ms, "cost_basis": cost_basis,
            "cost_micros": cost_micros,
        }).rowcount == 1

    def fail(
        self, session: Session, call_id: str, *, error_code: str, response_sha256: str | None = None,
        input_tokens: int | None = None, output_tokens: int | None = None,
        latency_ms: int | None = None, cost_basis: str | None = None, cost_micros: int | None = None,
    ) -> bool:
        """``prepared | sent -> failed``. A failure that carries usage (the provider answered, the
        answer was unusable) records the cost it may have charged; a proven pre-dispatch refusal
        records none."""
        return session.execute(_FAIL, {
            "call_id": call_id, "error_code": error_code, "response_sha256": response_sha256,
            "input_tokens": input_tokens, "output_tokens": output_tokens, "latency_ms": latency_ms,
            "cost_basis": cost_basis, "cost_micros": cost_micros,
        }).rowcount == 1

    def mark_unknown(self, session: Session, call_id: str, *, error_code: str) -> bool:
        """``prepared | sent -> unknown``: nothing proves whether the provider did billable work."""
        return session.execute(_UNKNOWN, {"call_id": call_id, "error_code": error_code}).rowcount == 1

    def settle_attempt(self, session: Session, attempt_id: str, *, error_code: str = "attempt_lost") -> bool:
        """Every call of a lost attempt that is ``prepared`` or ``sent`` becomes ``unknown``. ``True``
        when there was one: the queue then ends the item ``spend_unknown`` instead of re-queueing it."""
        return bool(session.execute(
            _SETTLE_ATTEMPT, {"attempt_id": attempt_id, "error_code": error_code}
        ).all())

    def settle_abandoned(self, session: Session, *, error_code: str = "attempt_ended") -> int:
        """Settle ``unknown`` the open calls of attempts that are over without the queue having done
        it. Answers how many."""
        return int(session.execute(_SETTLE_ABANDONED, {"error_code": error_code}).rowcount or 0)

    def attach_task(self, session: Session, call_id: str, task_id: str) -> bool:
        """Link the pull channel's ``executor_task`` to the journal row, once."""
        return session.execute(_ATTACH_TASK, {"call_id": call_id, "task_id": task_id}).rowcount == 1

    # -- reads ------------------------------------------------------------------------------------
    def get(self, session: Session, call_id: str) -> CallRecord | None:
        row = session.execute(_GET, {"call_id": call_id}).mappings().first()
        return None if row is None else _record(row)

    def calls_of_work(self, session: Session, work_id: str) -> Sequence[CallRecord]:
        return [_record(row) for row in session.execute(_OF_WORK, {"work_id": work_id}).mappings()]

    def job_spend(
        self, session: Session, *, project_uid: str, work_id: str, job_id: str | None
    ) -> Spend:
        """The cost of one AI job: every call of the items that carry ``job_id`` in their payload (of
        one project), or of the item itself when it carries none."""
        row = session.execute(_JOB_SPEND, {
            "project_uid": project_uid, "work_id": work_id, "job_id": job_id,
        }).one()
        return Spend(actual_micros=int(row.actual), reserved_micros=int(row.reserved))

    def day_spend(self, session: Session) -> Spend:
        """The cost of the installation since 00:00 UTC."""
        row = session.execute(_DAY_SPEND).one()
        return Spend(actual_micros=int(row.actual), reserved_micros=int(row.reserved))

    # -- the connection's single user ---------------------------------------------------------------
    def connection_of(self, session: Session, revision_id: str) -> str | None:
        return session.execute(_CONNECTION_OF, {"revision_id": revision_id}).scalar_one_or_none()

    def lock_connection(self, session: Session, connection_id: str) -> None:
        """Take the connection's advisory lock to the end of the transaction (the Run claim's key)."""
        session.execute(_LOCK_CONNECTION, {"connection_id": connection_id})

    def lock_day(self, session: Session) -> None:
        """Take the installation's spend lock to the end of the transaction."""
        session.execute(_LOCK_DAY)

    def connection_has_active_run(self, session: Session, connection_id: str) -> bool:
        return bool(session.execute(_CONNECTION_HAS_ACTIVE_RUN, {"connection_id": connection_id}).scalar_one())

    def connection_has_active_call(self, session: Session, connection_id: str) -> bool:
        return bool(session.execute(_CONNECTION_HAS_ACTIVE_CALL, {"connection_id": connection_id}).scalar_one())

    def open_calls_of_other_attempts(self, session: Session, *, work_id: str, attempt_id: str) -> int:
        """Calls of the item's *earlier* attempts that are still ``prepared`` or ``sent``: nothing may be
        sent for the item while one exists."""
        return int(session.execute(
            _OPEN_OF_OTHER_ATTEMPTS, {"work_id": work_id, "attempt_id": attempt_id}
        ).scalar_one())
