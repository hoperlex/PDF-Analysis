"""The worker registry (`worker`, migration ``0019``; owner ruling R-105).

This module is the only writer of the ``worker`` table. A worker process registers once
when it starts, under a fresh ``wrk`` identity (a restarted process is a new worker), and
then only two columns ever change: ``heartbeat_at`` and ``intake_enabled``. The trigger
``trg_worker_frozen_guard`` refuses every other update, so the registry cannot be edited
into describing a different process.

**State is derived on read and never stored.** ``online`` while the last heartbeat is
younger than :data:`STALE_AFTER_SECONDS`, ``stale`` until :data:`OFFLINE_AFTER_SECONDS`,
``offline`` afterwards -- measured on database time, like the lease, so a reader on
another clock cannot disagree with the writer.

**Paging is by the immutable start.** ``listWorkers`` orders by ``started_at`` and the
identity, newest first. A restart is a new row, so the newest rows are the live ones and
the history of stopped processes collapses behind them. Ordering by the derived state
would put a moving value into the cursor; the frontend groups online and stale above
offline itself (plan section 3.7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import WorkerId

#: R-105: a worker heartbeats every 20 s; stale after 90 s, offline after 600 s.
HEARTBEAT_SECONDS: Final[float] = 20.0
STALE_AFTER_SECONDS: Final[int] = 90
OFFLINE_AFTER_SECONDS: Final[int] = 600

_STATE = (
    "CASE WHEN w.heartbeat_at > clock_timestamp() - make_interval(secs => :stale) "
    "THEN 'online' "
    "WHEN w.heartbeat_at > clock_timestamp() - make_interval(secs => :offline) "
    "THEN 'stale' ELSE 'offline' END"
)
_COLUMNS = (
    "w.worker_id, w.version, w.started_at, w.heartbeat_at, w.slots, w.intake_enabled, "
    + _STATE + " AS state"
)
_REGISTER = text(
    "INSERT INTO worker (worker_id, version, slots) VALUES (:worker_id, :version, :slots)"
)
_HEARTBEAT = text(
    "UPDATE worker SET heartbeat_at = clock_timestamp() WHERE worker_id = :worker_id"
)
_INTAKE = text("SELECT intake_enabled FROM worker WHERE worker_id = :worker_id")
_GET = text(f"SELECT {_COLUMNS} FROM worker w WHERE w.worker_id = :worker_id")
_LOCK = text("SELECT worker_id FROM worker WHERE worker_id = :worker_id FOR UPDATE")
_SET_INTAKE = text(
    "UPDATE worker SET intake_enabled = :enabled WHERE worker_id = :worker_id"
)
_PAGE = text(
    f"SELECT {_COLUMNS} FROM worker w "
    "WHERE CAST(:cursor_started_at AS timestamptz) IS NULL "
    "OR (w.started_at, w.worker_id) < (CAST(:cursor_started_at AS timestamptz), :cursor_worker_id) "
    "ORDER BY w.started_at DESC, w.worker_id DESC LIMIT :fetch"
)
_ANY_ONLINE = text(
    "SELECT EXISTS (SELECT 1 FROM worker w "
    "WHERE w.heartbeat_at > clock_timestamp() - make_interval(secs => :stale))"
)


@dataclass(frozen=True, slots=True)
class WorkerRecord:
    """One registry row, with its state derived at the moment it was read."""

    worker_id: str
    version: str
    started_at: datetime
    heartbeat_at: datetime
    slots: int
    intake_enabled: bool
    state: str


@dataclass(frozen=True, slots=True)
class WorkerCursor:
    """The immutable sort coordinates of the last row a page emitted."""

    started_at: datetime
    worker_id: str


def _thresholds() -> dict[str, float]:
    return {"stale": float(STALE_AFTER_SECONDS), "offline": float(OFFLINE_AFTER_SECONDS)}


class WorkerRegistry:
    """Register, heartbeat and read the worker processes of this deployment."""

    def register(self, session: Session, *, version: str, slots: int) -> str:
        """Insert a new registry row under a fresh identity and return the identity."""
        worker_id = str(WorkerId.new())
        session.execute(_REGISTER, {"worker_id": worker_id, "version": version, "slots": slots})
        return worker_id

    def heartbeat(self, session: Session, worker_id: str) -> bool:
        """``False`` when the row is gone -- the schema was reset under the process."""
        return session.execute(_HEARTBEAT, {"worker_id": worker_id}).rowcount == 1

    def intake_enabled(self, session: Session, worker_id: str) -> bool | None:
        value = session.execute(_INTAKE, {"worker_id": worker_id}).scalar_one_or_none()
        return None if value is None else bool(value)

    def get(self, session: Session, worker_id: str) -> WorkerRecord | None:
        row = session.execute(
            _GET, {"worker_id": worker_id, **_thresholds()}
        ).mappings().first()
        return None if row is None else WorkerRecord(**dict(row))

    def set_intake(self, session: Session, *, worker_id: str, enabled: bool) -> bool:
        """Lock the row and switch intake; ``False`` when no such worker exists.

        The row lock conflicts with the claim's ``FOR SHARE`` on the same row
        (``jobs``), so a claim in flight either committed before the switch or sees it.
        """
        if session.execute(_LOCK, {"worker_id": worker_id}).scalar_one_or_none() is None:
            return False
        session.execute(_SET_INTAKE, {"worker_id": worker_id, "enabled": enabled})
        return True

    def page(
        self, session: Session, *, cursor: WorkerCursor | None, limit: int
    ) -> tuple[WorkerRecord, ...]:
        rows = session.execute(_PAGE, {
            "cursor_started_at": None if cursor is None else cursor.started_at,
            "cursor_worker_id": None if cursor is None else cursor.worker_id,
            "fetch": limit,
            **_thresholds(),
        }).mappings().all()
        return tuple(WorkerRecord(**dict(row)) for row in rows)

    def any_online(self, session: Session) -> bool:
        return bool(session.execute(_ANY_ONLINE, {"stale": float(STALE_AFTER_SECONDS)}).scalar_one())


__all__ = [
    "HEARTBEAT_SECONDS",
    "OFFLINE_AFTER_SECONDS",
    "STALE_AFTER_SECONDS",
    "WorkerCursor",
    "WorkerRecord",
    "WorkerRegistry",
]
