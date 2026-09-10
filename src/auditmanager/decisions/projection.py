"""The current-verdict projection.

``finding_current_verdict`` is a **view**, defined once in the migration. ``B4``, ``B5``
and ``B6`` read it and none recomputes it, so "the current verdict is a rebuildable
projection over the event stream" is true by construction and not by anybody's
discipline. This module reads that view. It keeps no cache, and there is no Python copy
of the projection standing between a caller and the database — a cache would be a second
answer to the same question, and the whole point of a projection is that there is one.

:func:`rebuild_current_verdict` exists for one reason: to prove the claim. It folds the
raw event stream in the server's total order and returns what the view should say. A
test that compares the two cannot pass by comparing a cache with itself, because the
fold reads ``expert_decision_event`` and the view is computed by PostgreSQL. It is not a
read path — nothing in the API or the CSV calls it.

**PD-01**: a revocation moves the projection to ``pending`` and restores no earlier
verdict. That falls out of "the verdict of the most recent verdict-bearing event":
``revoke`` carries the verdict ``pending``, so it *is* the most recent verdict-bearing
event and there is no rule anywhere that walks further back. A verdict after a
revocation exists only where an authorized expert appended a new event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

_CURRENT_VERDICT = text(
    """
    SELECT finding_uid,
           current_verdict,
           latest_verdict_decision_id,
           latest_verdict_recorded_at,
           latest_comment,
           latest_comment_decision_id,
           latest_decision_id,
           decision_recorded_at,
           decision_event_count
    FROM finding_current_verdict
    WHERE finding_uid = :finding_uid
    """
)

_RAW_STREAM = text(
    """
    SELECT decision_id, event_type, verdict, comment, recorded_at
    FROM expert_decision_event
    WHERE finding_uid = :finding_uid
    ORDER BY sequence_no
    """
)

_FINDING_EXISTS = text("SELECT 1 FROM finding WHERE finding_uid = :finding_uid")


@dataclass(frozen=True, slots=True)
class CurrentVerdict:
    """One row of the projection, in the shape P02 §5.4 declares."""

    finding_uid: str
    current_verdict: str
    latest_verdict_decision_id: str | None
    latest_comment: str | None
    latest_comment_decision_id: str | None
    latest_decision_id: str | None
    decision_recorded_at: datetime | None
    decision_event_count: int

    def comparable(self) -> tuple:
        """The fields a rebuild can be compared on, without the timestamps that only
        the database can produce."""
        return (
            self.finding_uid,
            self.current_verdict,
            self.latest_verdict_decision_id,
            self.latest_comment,
            self.latest_comment_decision_id,
            self.latest_decision_id,
            self.decision_event_count,
        )


def current_verdict(session: Session, finding_uid: str) -> CurrentVerdict | None:
    """Read the projection. ``None`` when no finding carries that identity.

    A finding with no events at all still has a row: ``current_verdict`` is ``pending``
    and every decision field is null. ``pending`` is explicit, never inferred from a
    missing row.
    """
    row = session.execute(_CURRENT_VERDICT, {"finding_uid": finding_uid}).mappings().first()
    if row is None:
        return None
    return CurrentVerdict(
        finding_uid=row["finding_uid"],
        current_verdict=row["current_verdict"],
        latest_verdict_decision_id=row["latest_verdict_decision_id"],
        latest_comment=row["latest_comment"],
        latest_comment_decision_id=row["latest_comment_decision_id"],
        latest_decision_id=row["latest_decision_id"],
        decision_recorded_at=row["decision_recorded_at"],
        decision_event_count=row["decision_event_count"],
    )


def rebuild_current_verdict(session: Session, finding_uid: str) -> CurrentVerdict | None:
    """Fold the raw event stream into what the projection should say.

    Used to prove the view is a projection, never as a read path. The fold applies §5.4
    exactly:

    * ``current_verdict`` is the verdict of the most recent verdict-bearing event, and
      ``pending`` when there is none. It never walks back past a revocation to find an
      older verdict — PD-01.
    * ``latest_comment`` is the comment of the most recent event carrying one, whatever
      that event's type, so a comment attached to an accept still shows.
    * ``latest_decision_id`` and ``decision_recorded_at`` describe the most recent event
      of **any** type, so appending a comment moves them while leaving the verdict alone.
    """
    if session.execute(_FINDING_EXISTS, {"finding_uid": finding_uid}).first() is None:
        return None

    verdict = "pending"
    latest_verdict_decision_id: str | None = None
    latest_comment: str | None = None
    latest_comment_decision_id: str | None = None
    latest_decision_id: str | None = None
    decision_recorded_at: datetime | None = None
    count = 0

    for row in session.execute(_RAW_STREAM, {"finding_uid": finding_uid}).mappings():
        count += 1
        latest_decision_id = row["decision_id"]
        decision_recorded_at = row["recorded_at"]
        if row["verdict"] is not None:
            verdict = row["verdict"]
            latest_verdict_decision_id = row["decision_id"]
        if row["comment"] is not None:
            latest_comment = row["comment"]
            latest_comment_decision_id = row["decision_id"]

    return CurrentVerdict(
        finding_uid=finding_uid,
        current_verdict=verdict,
        latest_verdict_decision_id=latest_verdict_decision_id,
        latest_comment=latest_comment,
        latest_comment_decision_id=latest_comment_decision_id,
        latest_decision_id=latest_decision_id,
        decision_recorded_at=decision_recorded_at,
        decision_event_count=count,
    )
