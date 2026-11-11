"""The estimated finish of a running audit (`UI-PARITY-P0K`, ruling `R-151u`).

The owner ruled «По похожим прошлым прогонам»: the median duration of recent completed runs of the same analysis
profile and a similar page count, shown as «≈ до ЧЧ:ММ»; without enough history there is no estimate, never an
invented one. A run's duration is from its first attempt to its terminal time (queue waiting excluded); "similar" is a
page count within a quarter of the running one; "recent" is the latest completed runs, at most ``HISTORY``; at least
``MINIMUM_SAMPLES`` similar ones are needed. An estimate is a deterministic statistic of stored times, nothing else.

**One rule, two readers.** The execution queue (``ExecutionQueueItem.estimated_finish_at``) and the run's own status
(``RunStatus.estimated_finish_at``, `UI-A-65` / `UI-B-45`, contract 1.40.0) both answer through
:func:`job_estimated_finish`: the same job states, the same history, the same statistic. The queue hands it the facts of
a row it already read; :func:`run_estimated_finish` reads the same four facts for one run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import text
from sqlalchemy.orm import Session

HISTORY = 200
MINIMUM_SAMPLES = 3
SIMILAR_PAGES = 0.25

#: The job states in which a run is being worked on, and so has an estimate. A ``queued`` job has not started and a
#: ``retry_wait`` one is between attempts; neither is estimated.
RUNNING_JOB_STATES = ("leased", "running")

#: `RUN-DELETE-01`: the durations of the runs the estimate is made from leave out a run an expert deleted from the run lists (it was
#: deleted as not objective); `_RUN_FACTS` below reads one run by identity and keeps no such condition.
_HISTORY = text(
    """
    SELECT r.analysis_profile_id, dv.page_count,
           EXTRACT(EPOCH FROM (r.terminal_at - first_attempt.started_at)) AS seconds
      FROM audit_run r
      JOIN document_version dv ON dv.version_uid = r.version_uid
      JOIN LATERAL (
        SELECT min(a.created_at) AS started_at
          FROM job j JOIN attempt a ON a.job_id = j.job_id
         WHERE j.run_id = r.run_id
      ) first_attempt ON first_attempt.started_at IS NOT NULL
     WHERE r.state IN ('published', 'partial') AND r.terminal_at IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM audit_run_deletion deleted WHERE deleted.run_id = r.run_id)
     ORDER BY r.terminal_at DESC
     LIMIT :limit
    """
)


#: The four facts the estimate is made of, for one run: its job's state, the creation of the job's first attempt, the
#: run's analysis profile and its version's page count. The same expressions as the queue's ``_ITEM_COLUMNS`` and as
#: ``_HISTORY`` above (``job.run_id`` is unique, so at most one row).
_RUN_FACTS = text(
    """
    SELECT j.state,
           (SELECT min(a.created_at) FROM attempt a WHERE a.job_id = j.job_id) AS started_at,
           r.analysis_profile_id, dv.page_count
      FROM job j
      JOIN audit_run r ON r.run_id = j.run_id
      JOIN document_version dv ON dv.version_uid = r.version_uid
     WHERE j.run_id = :run_id
    """
)


@dataclass(frozen=True, slots=True)
class Sample:
    analysis_profile_id: str | None
    page_count: int
    seconds: float


def history(session: Session) -> tuple[Sample, ...]:
    rows = session.execute(_HISTORY, {"limit": HISTORY}).all()
    return tuple(Sample(row[0], int(row[1]), float(row[2])) for row in rows if row[2] is not None and float(row[2]) > 0)


def expected_seconds(samples: Sequence[Sample], *, analysis_profile_id: str | None, page_count: int | None) -> float | None:
    """The median duration of the similar samples, or ``None`` when there are fewer than ``MINIMUM_SAMPLES``."""
    if page_count is None or page_count <= 0:
        return None
    low, high = page_count * (1 - SIMILAR_PAGES), page_count * (1 + SIMILAR_PAGES)
    similar = [
        sample.seconds for sample in samples
        if sample.analysis_profile_id == analysis_profile_id and low <= sample.page_count <= high
    ]
    return median(similar) if len(similar) >= MINIMUM_SAMPLES else None


def estimated_finish(
    samples: Sequence[Sample], *, started_at: datetime | None, analysis_profile_id: str | None, page_count: int | None,
) -> datetime | None:
    """``started_at`` plus the expected duration; ``None`` without a start or without enough history."""
    if started_at is None:
        return None
    seconds = expected_seconds(samples, analysis_profile_id=analysis_profile_id, page_count=page_count)
    return None if seconds is None else started_at + timedelta(seconds=seconds)


def job_estimated_finish(
    samples: Sequence[Sample], *, job_state: str | None, started_at: datetime | None,
    analysis_profile_id: str | None, page_count: int | None,
) -> datetime | None:
    """**The** estimate of a job's run: ``None`` unless the job is in :data:`RUNNING_JOB_STATES`, has started and has
    enough similar history (:func:`estimated_finish`). Both the queue item and the run status call this."""
    if job_state not in RUNNING_JOB_STATES or not samples:
        return None
    return estimated_finish(
        samples, started_at=started_at, analysis_profile_id=analysis_profile_id, page_count=page_count,
    )


def run_estimated_finish(session: Session, run_id: str) -> datetime | None:
    """The estimated finish of one run, from the same facts and the same rule as its queue item (`UI-A-65`).

    The recent history (up to ``HISTORY`` rows) is read only when the run's job is running and has started: a queued,
    waiting or finished run costs the one lean statement and no history read.
    """
    row = session.execute(_RUN_FACTS, {"run_id": run_id}).first()
    if row is None or row[0] not in RUNNING_JOB_STATES or row[1] is None:
        return None
    return job_estimated_finish(
        history(session), job_state=row[0], started_at=row[1],
        analysis_profile_id=row[2], page_count=None if row[3] is None else int(row[3]),
    )
