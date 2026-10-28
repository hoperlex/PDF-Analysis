"""The heartbeat of one running item: its own thread, its own short transactions.

Same shape as ``jobs/lease.py`` (`LeaseHeartbeat`): the lease is extended on database time by a
thread that does not share the handler's transaction, three heartbeats fit in one lease, and a
transient fault is logged and retried on the next tick -- the lease expiry is the durable fence if
heartbeats cannot commit. After the watchdog interval the thread stops extending and fences its own
attempt, because an item that is still running after that long has lost its handler or its child.
The thread also carries two facts to the handler: the lease is gone, and a cancel was requested.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from time import monotonic

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.work.model import WorkItem
from auditmanager.comparison.work.repository import ComparisonWorkRepository

__all__ = ["ItemHeartbeat"]

_log = logging.getLogger(__name__)


class ItemHeartbeat:
    def __init__(
        self, sessions: "sessionmaker[Session]", repository: ComparisonWorkRepository,
        item: WorkItem, *, interval_seconds: float, watchdog_seconds: float,
        fence: Callable[[Session, str], object],
    ) -> None:
        self._sessions = sessions
        self._repository = repository
        self._item = item
        self._interval = interval_seconds
        self._watchdog = watchdog_seconds
        #: ``fence(session, attempt_id)``: force the reclaim of this attempt (the watchdog).
        self._fence = fence
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="auditmanager-comparison-heartbeat", daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        started = monotonic()
        item = self._item
        while not self._stop.wait(self._interval):
            try:
                with self._sessions() as session:
                    if monotonic() - started >= self._watchdog:
                        self._fence(session, item.attempt_id)
                        session.commit()
                        item.lease_lost.set()
                        return
                    current = self._repository.heartbeat(session, item.authority)
                    cancel = current and self._repository.cancel_requested(session, item.work_id)
                    session.commit()
                if not current:
                    item.lease_lost.set()
                    return
                if cancel:
                    item.cancelled.set()
            except Exception:
                _log.exception(
                    "comparison work %s (attempt %d): heartbeat failed; retried next tick",
                    item.work_id, item.attempt_no,
                )
