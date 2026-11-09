"""The only writer of ``comparison_model_call`` (`CMP-SPEND-01`, ADR-0025 decision 5).

The journal of every model call the comparison modules make, with the life ``prepared -> sent ->
completed | failed | unknown`` that migration ``0038`` enforces: a row can only be **inserted**
``prepared`` (a trigger), only move along the declared edges, and a terminal row never moves. Each
statement here names the state it expects, so a lost race (the reclaim settled the row first) is an
answer of ``False``, never a quiet overwrite.

Statements only, as ``jobs`` and ``executors.runner_repository`` do: every method takes the caller's
session and **never commits**. The wrapper (:mod:`.caller`) owns the transactions, because the
``prepared`` row must be committed on its own, before the adapter is called.

The reads that decide a call -- what a job and a day have cost, whether the connection has a unit left --
live here too, beside the writes they must agree with. Three of them restate a fact of the ``jobs``
context: the advisory-lock key of a connection, the Job states that make a Run *active* and the unit
count against ``max_active_runs`` of the connection's current revision (`EXEC2-CAP-01`). All three are
pinned to their original by a test (this context may not import ``jobs`` internals).

`EXEC2-GROUP-CMP-01` (ADR-0026 decisions 12 and 14). A job admitted by a rule or a group has no connection until its first
call binds it, and a Run admitted the same way has none until its claim does. Both counts below join ``audit_run`` and
``comparison_model_call`` to ``executor_connection_revision`` on the **row's own** revision with an inner join, so a ``pending``
Run (``connection_revision_id`` NULL) holds no unit of any connection, and a call is journalled with the member's revision in
the very transaction that binds the job, so it is never counted against a connection it was not sent to. The first-call
binding takes the group's row lock with :meth:`ComparisonSpendRepository.lock_group`, then the members' connection locks with
:meth:`~ComparisonSpendRepository.lock_connection` in ascending ``connection_id``, then the day lock -- the order of decision 14.
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
#: lock, so a Run's claim and a comparison call cannot both pass their check at once. `HOSTS-BACKEND-01` (ADR-0028 decision 4): the key
#: is the connection's ``capacity_pool`` when it has one (a system connection of a host: ``<host_id>:<provider>``), its own id otherwise,
#: so a call on a pooled connection and a planned Run's claim or cell binding in that pool take one lock.
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
    f"SELECT pg_advisory_xact_lock(hashtextextended('{CONNECTION_LOCK_KEY}' || "
    "COALESCE((SELECT capacity_pool FROM executor_connection WHERE connection_id = :connection_id), :connection_id), 0))"
)
#: The same lock taken from a pool, spelled as ``jobs.repository._LOCK_POOL`` spells it (a test holds the two equal).
_LOCK_POOL = text(f"SELECT pg_advisory_xact_lock(hashtextextended('{CONNECTION_LOCK_KEY}' || :pool, 0))")
_POOL_OF = text("SELECT capacity_pool FROM executor_connection WHERE connection_id = :connection_id")
_LOCK_DAY = text(f"SELECT pg_advisory_xact_lock(hashtextextended('{DAY_LOCK_KEY}', 0))")
#: `EXEC2-GROUP-CMP-01`. The group's row lock (the first lock of decision 14's order, the one a Run's claim takes before it
#: and an administrator's revision takes) and, read under it, the persisted tie-break rotation of ``least_loaded``.
_LOCK_GROUP = text("SELECT rotation_cursor FROM executor_group WHERE group_id = :group_id FOR UPDATE")
_ACTIVE_STATES_SQL = "(" + ", ".join(f"'{s}'" for s in ACTIVE_JOB_STATES) + ")"
#: The rows of the Runs active on a connection, and of its **active comparison calls**. A call is *active*
#: while it is open **and** its attempt still holds the item: a killed worker's call stays active until the
#: reclaim ends its attempt (the Run rule: an expired lease keeps the connection busy), and a row left open
#: by an attempt that is over blocks nothing. The two ``FROM`` clauses are shared by the existence form
#: (a capacity of one: "is anyone using it") and the count form (`EXEC2-CAP-01`: "how many units").
_ACTIVE_RUN_ROWS = (
    "FROM job j JOIN audit_run r ON r.run_id = j.run_id "
    "JOIN executor_connection_revision rev ON rev.revision_id = r.connection_revision_id "
    f"WHERE rev.connection_id = :connection_id AND j.state IN {_ACTIVE_STATES_SQL}"
)
_ACTIVE_CALL_ROWS = (
    "FROM comparison_model_call c "
    "JOIN comparison_work_attempt a ON a.comparison_work_attempt_id = c.comparison_work_attempt_id "
    "JOIN executor_connection_revision rev ON rev.revision_id = c.connection_revision_id "
    "WHERE rev.connection_id = :connection_id AND c.state IN ('prepared', 'sent') "
    "AND a.state IN ('created', 'leased', 'running')"
)
_CONNECTION_HAS_ACTIVE_RUN = text(f"SELECT EXISTS (SELECT 1 {_ACTIVE_RUN_ROWS})")
_CONNECTION_HAS_ACTIVE_CALL = text(f"SELECT EXISTS (SELECT 1 {_ACTIVE_CALL_ROWS})")
#: `EXEC2-CAP-01` (ADR-0026 decision 1). Does the connection have a unit left: its active Runs plus its
#: active comparison calls, each one unit, **below** ``max_active_runs`` of its current (highest-numbered)
#: revision, one when that is NULL or there is no revision. Decided under the connection's lock, which the
#: caller takes first, so with one unit left exactly one of a Run's claim and a call passes. The mirror of
#: ``jobs.repository._CONNECTION_UNITS``; a test holds the two equal.
_CONNECTION_HAS_FREE_UNIT = text(
    f"SELECT ((SELECT count(*) {_ACTIVE_RUN_ROWS}) + (SELECT count(*) {_ACTIVE_CALL_ROWS})) < "
    "COALESCE((SELECT current_revision.max_active_runs FROM executor_connection_revision current_revision "
    "WHERE current_revision.connection_id = :connection_id "
    "ORDER BY current_revision.revision_no DESC LIMIT 1), 1)"
)
#: `HOSTS-BACKEND-01` (ADR-0028 decision 4). The same question for a **pooled** connection: the units in use in its pool -- the active Runs bound
#: in it (by cell, or by the revision they froze) and the active comparison calls of every connection of the pool, each Run once however many cells
#: it has there -- below the pool's slots. The mirror of ``executors.host_repository.POOL_UNITS`` and ``POOL_SLOTS`` and of the planned branch
#: of ``jobs.repository._NEXT_JOB``; a test holds the three equal.
_POOL_HAS_FREE_UNIT = text(
    "WITH active AS (SELECT j.run_id, r.connection_revision_id FROM job j JOIN audit_run r ON r.run_id = j.run_id "
    f"WHERE j.state IN {_ACTIVE_STATES_SQL}) "
    "SELECT ((SELECT count(*) FROM ("
    "SELECT a.run_id FROM active a JOIN audit_run_cell_binding b ON b.run_id = a.run_id "
    "JOIN executor_connection_revision rev ON rev.revision_id = b.connection_revision_id "
    "JOIN executor_connection c ON c.connection_id = rev.connection_id WHERE c.capacity_pool = :pool "
    "UNION "
    "SELECT a.run_id FROM active a JOIN executor_connection_revision rev ON rev.revision_id = a.connection_revision_id "
    "JOIN executor_connection c ON c.connection_id = rev.connection_id WHERE c.capacity_pool = :pool) units) "
    "+ (SELECT count(*) FROM comparison_model_call active_call "
    "JOIN comparison_work_attempt active_attempt "
    "ON active_attempt.comparison_work_attempt_id = active_call.comparison_work_attempt_id "
    "JOIN executor_connection_revision call_peer ON call_peer.revision_id = active_call.connection_revision_id "
    "JOIN executor_connection call_connection ON call_connection.connection_id = call_peer.connection_id "
    "WHERE call_connection.capacity_pool = :pool AND active_call.state IN ('prepared', 'sent') "
    "AND active_attempt.state IN ('created', 'leased', 'running'))) < "
    "COALESCE((SELECT slot_event.slots FROM executor_host_slot_event slot_event "
    "WHERE slot_event.host_id = split_part(:pool, ':', 1) AND slot_event.provider = split_part(:pool, ':', 2) "
    "ORDER BY slot_event.event_no DESC LIMIT 1), "
    "(SELECT CASE reported.provider_item ->> 'access' WHEN 'api' THEN 2 ELSE 1 END "
    "FROM (SELECT jsonb_array_elements(host_report.providers) AS provider_item "
    "FROM executor_host_report host_report WHERE host_report.host_id = split_part(:pool, ':', 1)) reported "
    "WHERE reported.provider_item ->> 'provider' = split_part(:pool, ':', 2) LIMIT 1), 1)"
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
        """Take the connection's advisory lock to the end of the transaction (the Run claim's key): the lock of its capacity pool when it has
        one, so every connection of a host's provider takes the same lock."""
        session.execute(_LOCK_CONNECTION, {"connection_id": connection_id})

    def lock_pool(self, session: Session, pool: str) -> None:
        """Take a pool's advisory lock to the end of the transaction: the lock of every connection of the pool (`HOSTS-BACKEND-01`)."""
        session.execute(_LOCK_POOL, {"pool": pool})

    def lock_day(self, session: Session) -> None:
        """Take the installation's spend lock to the end of the transaction."""
        session.execute(_LOCK_DAY)

    def lock_group(self, session: Session, group_id: str) -> int | None:
        """`EXEC2-GROUP-CMP-01`. Take the group's row lock to the end of the transaction (``FOR UPDATE``: the lock a Run's
        claim and an administrator's revision take) and answer its rotation cursor as it stands under the lock, or ``None``
        when there is no such group. Taken **before** any connection lock and the day lock."""
        found = session.execute(_LOCK_GROUP, {"group_id": group_id}).scalar_one_or_none()
        return None if found is None else int(found)

    def connection_has_active_run(self, session: Session, connection_id: str) -> bool:
        return bool(session.execute(_CONNECTION_HAS_ACTIVE_RUN, {"connection_id": connection_id}).scalar_one())

    def connection_has_active_call(self, session: Session, connection_id: str) -> bool:
        return bool(session.execute(_CONNECTION_HAS_ACTIVE_CALL, {"connection_id": connection_id}).scalar_one())

    def connection_has_free_unit(self, session: Session, connection_id: str) -> bool:
        """`EXEC2-CAP-01`. Is the connection's use (active Runs plus active calls) below its capacity?

        Asked after :meth:`lock_connection`. With the default capacity of one it answers ``False`` exactly
        when :meth:`connection_has_active_run` or :meth:`connection_has_active_call` answers ``True``.

        A connection with a capacity pool (`HOSTS-BACKEND-01`, ADR-0028 decision 4) is counted in its **pool**: the active Runs bound in it, each
        once, and the active calls of every connection of it, below the slots of the provider on the host."""
        pool = session.execute(_POOL_OF, {"connection_id": connection_id}).scalar_one_or_none()
        if pool is not None:
            return bool(session.execute(_POOL_HAS_FREE_UNIT, {"pool": pool}).scalar_one())
        return bool(session.execute(_CONNECTION_HAS_FREE_UNIT, {"connection_id": connection_id}).scalar_one())

    def open_calls_of_other_attempts(self, session: Session, *, work_id: str, attempt_id: str) -> int:
        """Calls of the item's *earlier* attempts that are still ``prepared`` or ``sent``: nothing may be
        sent for the item while one exists."""
        return int(session.execute(
            _OPEN_OF_OTHER_ATTEMPTS, {"work_id": work_id, "attempt_id": attempt_id}
        ).scalar_one())
