"""The estimated finish of a running audit (`UI-PARITY-P0K`, ruling `R-151u`).

The owner ruled «По похожим прошлым прогонам»: the median duration of recent completed runs of the same analysis
profile and a similar page count, shown as «≈ до ЧЧ:ММ»; without enough history there is no estimate, never an
invented one. A run's duration is from its first attempt to its terminal time (queue waiting excluded); "similar" is a
page count within a quarter of the running one; "recent" is the latest completed runs, at most ``HISTORY``; at least
``MINIMUM_SAMPLES`` similar ones are needed. An estimate is a deterministic statistic of stored times, nothing else.
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
     ORDER BY r.terminal_at DESC
     LIMIT :limit
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
