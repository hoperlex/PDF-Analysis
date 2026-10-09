"""Bounded reads of durable Jobs and append-only execution events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class QueueItem:
    job_id: str
    run_id: str
    state: str
    priority: int
    created_at: datetime
    available_at: datetime

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


_QUEUE = text("""
    SELECT j.job_id, j.run_id, j.state, j.priority, j.created_at, j.available_at
      FROM job j
     WHERE (CAST(:cursor_job_id AS text) IS NULL OR j.job_id <> :cursor_job_id)
       AND (CAST(:cursor_rank AS integer) IS NULL OR (
            CASE j.state WHEN 'queued' THEN 0 WHEN 'leased' THEN 1
                 WHEN 'running' THEN 2 WHEN 'retry_wait' THEN 3 ELSE 4 END > :cursor_rank
            OR (CASE j.state WHEN 'queued' THEN 0 WHEN 'leased' THEN 1
                 WHEN 'running' THEN 2 WHEN 'retry_wait' THEN 3 ELSE 4 END = :cursor_rank
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
     ORDER BY CASE j.state WHEN 'queued' THEN 0 WHEN 'leased' THEN 1
                   WHEN 'running' THEN 2 WHEN 'retry_wait' THEN 3 ELSE 4 END,
              j.priority DESC,
              CASE WHEN j.state = 'queued' THEN j.created_at END,
              CASE WHEN j.state <> 'queued' THEN j.created_at END DESC,
              CASE WHEN j.state = 'queued' THEN j.job_id END,
              CASE WHEN j.state <> 'queued' THEN j.job_id END DESC
     LIMIT :fetch
""")
_QUEUE_ITEM = text(
    "SELECT job_id, run_id, state, priority, created_at, available_at "
    "FROM job WHERE job_id = :job_id"
)

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
        self, session: Session, *, cursor: QueuePosition | None, limit: int
    ) -> tuple[QueueItem, ...]:
        rows = session.execute(_QUEUE, {
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
