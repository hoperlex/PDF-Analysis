"""Bounded reads of durable Jobs and append-only execution events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class QueueItem:
    """One job of the queue with what it executes, joined at read time (`UI-PARITY-QUEUE-A`).

    Every job belongs to exactly one audit run (``job.run_id`` is not null and unique), and a run
    to one version of one document of one project, all by not-null foreign keys. So the six identity
    and name members are never absent. ``started_at`` (the first attempt's creation), ``finished_at``
    (the job's terminal time), ``error_code`` (the run's ``terminal_reason``) and ``interrupted_reason``
    are ``None`` while the database holds none: nothing is guessed in their place.
    """

    job_id: str
    run_id: str
    state: str
    priority: int
    created_at: datetime
    available_at: datetime
    project_uid: str
    project_name: str
    document_uid: str
    document_name: str
    version_uid: str
    version_ordinal: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    interrupted_reason: str | None = None
    #: `R-151v` (migration 0051): the account that started the job's run; ``None`` before 0051.
    started_by_user_uid: str | None = None
    #: `R-151u`: what the ETA compares a running job with -- its run's analysis profile and its version's page count.
    analysis_profile_id: str | None = None
    page_count: int | None = None

    @property
    def position(self) -> QueuePosition:
        return QueuePosition(
            rank=_QUEUE_RANK.get(self.state, 4), priority=self.priority,
            created_at=self.created_at, job_id=self.job_id,
        )


@dataclass(frozen=True, slots=True)
class QueuePosition:
    """The sort coordinates captured when a queue page was emitted."""

    rank: int
    priority: int
    created_at: datetime
    job_id: str


_QUEUE_RANK = {"queued": 0, "leased": 1, "running": 2, "retry_wait": 3}


@dataclass(frozen=True, slots=True)
class JournalEntry:
    event_id: str
    run_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    occurred_at: datetime
    payload: Mapping[str, str | int | float | bool | None]


@dataclass(frozen=True, slots=True)
class DispatchStatus:
    paused: bool
    changed_at: datetime


#: The queue's order, once: state rank (active work first), priority, then the oldest queued job first and the newest
#: finished job first. ``{a}`` is the alias of the row source it orders. The page is cut by the inner statement and
#: put in the same order by the outer one, so the two cannot disagree: they are this one expression.
_RANK = (
    "CASE {a}.state WHEN 'queued' THEN 0 WHEN 'leased' THEN 1 "
    "WHEN 'running' THEN 2 WHEN 'retry_wait' THEN 3 ELSE 4 END"
)
_ORDER = (
    "ORDER BY " + _RANK + ", {a}.priority DESC, "
    "CASE WHEN {a}.state = 'queued' THEN {a}.created_at END, "
    "CASE WHEN {a}.state <> 'queued' THEN {a}.created_at END DESC, "
    "CASE WHEN {a}.state = 'queued' THEN {a}.job_id END, "
    "CASE WHEN {a}.state <> 'queued' THEN {a}.job_id END DESC"
)
#: What a queue row says about the work, joined onto the page of jobs. ``started_at`` is the creation of the job's
#: first attempt (``ix_attempt_job_id``), absent while no attempt exists; ``finished_at`` is the job's own
#: ``terminal_at``, read in the same statement as its state so the two cannot be torn apart.
_ITEM_COLUMNS = """
       page.job_id, page.run_id, page.state, page.priority, page.created_at, page.available_at,
       page.terminal_at AS finished_at,
       r.project_uid, p.name AS project_name,
       dv.document_uid, d.display_title AS document_name,
       r.version_uid, dv.version_ordinal,
       (SELECT min(a.created_at) FROM attempt a WHERE a.job_id = page.job_id) AS started_at,
       r.terminal_reason AS error_code, r.interrupted_reason, r.started_by_user_uid,
       r.analysis_profile_id, dv.page_count"""
_ITEM_JOINS = """
  JOIN audit_run r ON r.run_id = page.run_id
  JOIN project p ON p.project_uid = r.project_uid
  JOIN document_version dv ON dv.version_uid = r.version_uid
  JOIN document d ON d.document_uid = dv.document_uid"""
#: The page of jobs is cut from ``job`` alone, sorted and limited first; only those rows are then joined to the run,
#: the project and the document, so the cost of a read is the sort it always was plus one lookup per listed row.
#: The three optional filters bind as ``CAST(:name AS type) IS NULL OR ...``: a state, and the half-open period
#: ``[created_from, created_to)`` over ``job.created_at`` (the ``created_at`` the item reports).
_QUEUE = text(f"""
    SELECT {_ITEM_COLUMNS}
      FROM (
        SELECT j.job_id, j.run_id, j.state, j.priority, j.created_at, j.available_at, j.terminal_at
          FROM job j
         WHERE (CAST(:state AS text) IS NULL OR j.state = :state)
           AND (CAST(:created_from AS timestamptz) IS NULL OR j.created_at >= CAST(:created_from AS timestamptz))
           AND (CAST(:created_to AS timestamptz) IS NULL OR j.created_at < CAST(:created_to AS timestamptz))
           AND (CAST(:cursor_job_id AS text) IS NULL OR j.job_id <> :cursor_job_id)
           AND (CAST(:cursor_rank AS integer) IS NULL OR (
                {_RANK.format(a="j")} > :cursor_rank
                OR ({_RANK.format(a="j")} = :cursor_rank
                    AND (j.priority < :cursor_priority
                        OR (j.priority = :cursor_priority
                            AND ((:cursor_rank = 0 AND (
                                      j.created_at > CAST(:cursor_created_at AS timestamptz)
                                      OR (j.created_at = CAST(:cursor_created_at AS timestamptz)
                                          AND j.job_id > :cursor_job_id)))
                                 OR (:cursor_rank <> 0 AND (
                                      j.created_at < CAST(:cursor_created_at AS timestamptz)
                                      OR (j.created_at = CAST(:cursor_created_at AS timestamptz)
                                          AND j.job_id < :cursor_job_id))))))
         )))
         {_ORDER.format(a="j")}
         LIMIT :fetch
      ) page{_ITEM_JOINS}
     {_ORDER.format(a="page")}
""")
_QUEUE_ITEM = text(f"""
    SELECT {_ITEM_COLUMNS}
      FROM (
        SELECT j.job_id, j.run_id, j.state, j.priority, j.created_at, j.available_at, j.terminal_at
          FROM job j WHERE j.job_id = :job_id
      ) page{_ITEM_JOINS}
""")

# Cursor holds only an event ID. The DB resolves its ordering coordinates;
# sequence_no is never sent to a client. Run filtering joins indexed aggregate
# identities rather than scanning the unindexed payload run_id field.
_JOURNAL_ALL = text("""
    WITH anchor AS (
        SELECT e.occurred_at, e.sequence_no FROM audit_event e
         WHERE e.audit_event_id = :cursor AND (
             (e.aggregate_type = 'AuditRun' AND EXISTS (
                 SELECT 1 FROM audit_run r WHERE r.run_id = e.aggregate_id))
             OR (e.aggregate_type = 'Job' AND EXISTS (
                 SELECT 1 FROM job j WHERE j.job_id = e.aggregate_id))
             OR (e.aggregate_type = 'Attempt' AND EXISTS (
                 SELECT 1 FROM attempt a WHERE a.attempt_id = e.aggregate_id))
           )
    )
    SELECT e.audit_event_id, e.aggregate_type, e.aggregate_id, e.event_type,
           e.occurred_at, e.payload,
           COALESCE(r.run_id, j.run_id, aj.run_id) AS run_id
      FROM audit_event e
      LEFT JOIN audit_run r ON e.aggregate_type = 'AuditRun'
                           AND r.run_id = e.aggregate_id
      LEFT JOIN job j ON e.aggregate_type = 'Job'
                     AND j.job_id = e.aggregate_id
      LEFT JOIN attempt a ON e.aggregate_type = 'Attempt'
                          AND a.attempt_id = e.aggregate_id
      LEFT JOIN job aj ON aj.job_id = a.job_id
     WHERE e.aggregate_type IN ('AuditRun', 'Job', 'Attempt')
       AND COALESCE(r.run_id, j.run_id, aj.run_id) IS NOT NULL
       AND (CAST(:cursor AS text) IS NULL OR (e.occurred_at, e.sequence_no) <
           (SELECT occurred_at, sequence_no FROM anchor))
     ORDER BY e.occurred_at DESC, e.sequence_no DESC
     LIMIT :fetch
""")
_JOURNAL_RUN = text("""
    WITH aggregate_ids AS (
        SELECT 'AuditRun'::text AS aggregate_type, CAST(:run_id AS text) AS aggregate_id
        UNION ALL
        SELECT 'Job'::text, j.job_id FROM job j WHERE j.run_id = :run_id
        UNION ALL
        SELECT 'Attempt'::text, a.attempt_id FROM job j
          JOIN attempt a ON a.job_id = j.job_id WHERE j.run_id = :run_id
    ), anchor AS (
        SELECT e.occurred_at, e.sequence_no FROM audit_event e
          JOIN aggregate_ids ids ON ids.aggregate_type = e.aggregate_type
                                AND ids.aggregate_id = e.aggregate_id
         WHERE e.audit_event_id = :cursor
    )
    SELECT e.audit_event_id, e.aggregate_type, e.aggregate_id, e.event_type,
           e.occurred_at, e.payload, CAST(:run_id AS text) AS run_id
      FROM aggregate_ids ids
      JOIN audit_event e ON e.aggregate_type = ids.aggregate_type
                        AND e.aggregate_id = ids.aggregate_id
     WHERE CAST(:cursor AS text) IS NULL OR (e.occurred_at, e.sequence_no) <
           (SELECT occurred_at, sequence_no FROM anchor)
     ORDER BY e.occurred_at DESC, e.sequence_no DESC
     LIMIT :fetch
""")
_CONTROL = text("SELECT paused, changed_at FROM execution_control WHERE singleton = true")


class ExecutionRepository:
    def list_queue(
        self, session: Session, *, cursor: QueuePosition | None, limit: int,
        state: str | None = None, created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[QueueItem, ...]:
        """One page of the queue in its fixed order. ``state`` keeps the jobs in that state, and
        ``[created_from, created_to)`` the jobs created in that period; each is ``None`` for no filter."""
        rows = session.execute(_QUEUE, {
            "state": state, "created_from": created_from, "created_to": created_to,
            "cursor_rank": None if cursor is None else cursor.rank,
            "cursor_priority": None if cursor is None else cursor.priority,
            "cursor_created_at": None if cursor is None else cursor.created_at,
            "cursor_job_id": None if cursor is None else cursor.job_id,
            "fetch": limit,
        }).mappings()
        return tuple(QueueItem(**dict(row)) for row in rows)

    def get_queue_item(self, session: Session, job_id: str) -> QueueItem | None:
        row = session.execute(_QUEUE_ITEM, {"job_id": job_id}).mappings().first()
        return None if row is None else QueueItem(**dict(row))

    def list_journal(
        self, session: Session, *, run_id: str | None, cursor: str | None,
        limit: int,
    ) -> tuple[JournalEntry, ...]:
        query = _JOURNAL_ALL if run_id is None else _JOURNAL_RUN
        rows = session.execute(query, {
            "run_id": run_id, "cursor": cursor, "fetch": limit,
        }).mappings()
        return tuple(JournalEntry(
            event_id=row["audit_event_id"],
            run_id=row["run_id"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            event_type=row["event_type"],
            occurred_at=row["occurred_at"],
            payload=dict(row["payload"]),
        ) for row in rows)

    def dispatch_status(self, session: Session) -> DispatchStatus:
        row = session.execute(_CONTROL).mappings().first()
        if row is not None:
            return DispatchStatus(**dict(row))
        now = session.execute(text("SELECT statement_timestamp()")).scalar_one()
        return DispatchStatus(paused=False, changed_at=now)
