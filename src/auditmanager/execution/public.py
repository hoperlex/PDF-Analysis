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
    #: `UI-PARITY-P0M` (contract 1.28.0): a queued job's place in the dispatcher's order among every queued job
    #: (priority, then the oldest first), as the original numbers its queue; ``None`` for a job not queued.
    queue_position: int | None = None
    #: How many attempts the job has had.
    attempt_count: int = 0

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

#: `D-370` (contract 1.43.0): the queue's three groups of states, as the original's «Активные / Завершённые / Ошибки»
#: sub-tabs list them. ``listExecutionQueue`` takes a group by name (``state_group``) and lists every job in any of its
#: states, so the group is one filtered, paged, counted list and not a client-side merge of several single-state pages.
#: A cancelled job ended without a failure, so it stands with the completed ones (a choice, `D-370`). Every job state is in
#: exactly one group.
QUEUE_STATE_GROUPS: Mapping[str, tuple[str, ...]] = {
    "active": ("queued", "leased", "running", "retry_wait"),
    "completed": ("succeeded", "cancelled"),
    "errors": ("failed", "dead_letter"),
}


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
       r.analysis_profile_id, dv.page_count, qp.queue_position,
       (SELECT count(*) FROM attempt a WHERE a.job_id = page.job_id) AS attempt_count"""
#: `UI-PARITY-P0M`: a queued job's place in the dispatcher's order (priority, then the oldest first), numbered once per
#: statement over the queued jobs (``ix_job_dispatch`` leads with ``state``) rather than counted again for every row.
_ITEM_JOINS = """
  JOIN audit_run r ON r.run_id = page.run_id
  JOIN project p ON p.project_uid = r.project_uid
  JOIN document_version dv ON dv.version_uid = r.version_uid
  JOIN document d ON d.document_uid = dv.document_uid
  LEFT JOIN (
      SELECT q.job_id, row_number() OVER (ORDER BY q.priority DESC, q.created_at, q.job_id) AS queue_position
        FROM job q
       WHERE q.state = 'queued'
  ) qp ON qp.job_id = page.job_id"""
#: The page of jobs is cut from ``job`` alone, sorted and limited first; only those rows are then joined to the run,
#: the project and the document, so the cost of a read is the sort it always was plus one lookup per listed row.
#: The optional filters bind as ``CAST(:name AS type) IS NULL OR ...``: a set of states (one state, or a group's), and the half-open period
#: ``[created_from, created_to)`` over ``job.created_at`` (the ``created_at`` the item reports).
_QUEUE = text(f"""
    SELECT {_ITEM_COLUMNS}
      FROM (
        SELECT j.job_id, j.run_id, j.state, j.priority, j.created_at, j.available_at, j.terminal_at
          FROM job j
         WHERE (CAST(:states AS text[]) IS NULL OR j.state = ANY(CAST(:states AS text[])))
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
#: `UI-PARITY-P0M`: how many jobs stand in each state, over the queue's period filter and not its state filter, so the
#: counts are what each state of the filter would list.
_OVERVIEW = text("""
    SELECT j.state, count(*) AS count
      FROM job j
     WHERE (CAST(:created_from AS timestamptz) IS NULL OR j.created_at >= CAST(:created_from AS timestamptz))
       AND (CAST(:created_to AS timestamptz) IS NULL OR j.created_at < CAST(:created_to AS timestamptz))
     GROUP BY j.state
""")


def _state_set(state: str | None, states: tuple[str, ...] | None) -> list[str] | None:
    """The states a listing keeps, or ``None`` for every state: ``state`` and ``states`` narrow each other."""
    if states is None:
        return None if state is None else [state]
    return [item for item in states if state is None or item == state]


class ExecutionRepository:
    def list_queue(
        self, session: Session, *, cursor: QueuePosition | None, limit: int,
        state: str | None = None, created_from: datetime | None = None,
        created_to: datetime | None = None, states: tuple[str, ...] | None = None,
    ) -> tuple[QueueItem, ...]:
        """One page of the queue in its fixed order. ``state`` keeps the jobs in that state, ``states`` (`D-370`) the jobs
        in any of those states, and ``[created_from, created_to)`` the jobs created in that period; each is ``None`` for no
        filter. ``state`` and ``states`` together keep the jobs that satisfy both."""
        rows = session.execute(_QUEUE, {
            "states": _state_set(state, states), "created_from": created_from, "created_to": created_to,
            "cursor_rank": None if cursor is None else cursor.rank,
            "cursor_priority": None if cursor is None else cursor.priority,
            "cursor_created_at": None if cursor is None else cursor.created_at,
            "cursor_job_id": None if cursor is None else cursor.job_id,
            "fetch": limit,
        }).mappings()
        return tuple(QueueItem(**dict(row)) for row in rows)

    def queue_overview(
        self, session: Session, *, created_from: datetime | None = None, created_to: datetime | None = None,
    ) -> dict[str, int]:
        """``{state: count}`` of the jobs created in ``[created_from, created_to)``; a state with none is absent."""
        rows = session.execute(_OVERVIEW, {"created_from": created_from, "created_to": created_to}).all()
        return {str(row[0]): int(row[1]) for row in rows}

    def live_failure_count(self, session: Session) -> int:
        """`D-395` (contract 1.43.0): the failed jobs that are still the last word on their document version.

        A job in ``failed`` or ``dead_letter`` counts unless a **later job exists for a run of the same version**:
        someone re-audited it, started from a stage, or simply ran it again, and the failure has been answered --
        whatever became of that later job. If the later job failed too, it is the one that counts. Every run has
        exactly one job (``uq_job_run_id``) and a re-audit makes a new run, so "a later job for the same run" -- the
        original's "retried" -- is read as a later job of the same version, which is what a retry is here. Over all
        history, with no window: a failure ages out only by being answered.
        """
        count = session.execute(text("""
            SELECT count(*)
              FROM job j
              JOIN audit_run r ON r.run_id = j.run_id
             WHERE j.state IN ('failed', 'dead_letter')
               AND NOT EXISTS (
                   SELECT 1
                     FROM job n
                     JOIN audit_run nr ON nr.run_id = n.run_id
                    WHERE nr.version_uid = r.version_uid
                      AND (n.created_at, n.job_id) > (j.created_at, j.job_id)
               )
        """)).scalar_one()
        return int(count)

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
