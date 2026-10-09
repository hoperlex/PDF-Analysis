"""Independent database heartbeat and watchdog for one execution Attempt."""

from __future__ import annotations

import logging
import threading
from time import monotonic

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.repository import AttemptAuthority, JobRepository

LEASE_SECONDS = 60
HEARTBEAT_SECONDS = 20
ATTEMPT_WATCHDOG_SECONDS = 900

_log = logging.getLogger(__name__)
_current = threading.local()


class LeaseHeartbeat:
    def __init__(self, bind: Engine | Connection, authority: AttemptAuthority) -> None:
        engine = bind.engine if isinstance(bind, Connection) else bind
        self._sessions = sessionmaker(bind=engine)
        self._authority = authority
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="auditmanager-lease-heartbeat", daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        started = monotonic()
        while not self._stop.wait(HEARTBEAT_SECONDS):
            try:
                with self._sessions() as session:
                    if monotonic() - started >= ATTEMPT_WATCHDOG_SECONDS:
                        JobRepository().reclaim_expired(
                            session, force_attempt_id=self._authority.attempt_id,
                        )
                        session.commit()
                        return
                    current = JobRepository().heartbeat(session, self._authority)
                    session.commit()
                    if not current:
                        return
            except Exception:
                # A transient DB fault is visible and retried on the next tick. The
                # lease expiry is the durable fence if heartbeats cannot commit.
                _log.exception("lease heartbeat failed for run %s", self._authority.run_id)


def start_for_current_thread(session: Session, authority: AttemptAuthority) -> None:
    if getattr(_current, "heartbeat", None) is not None:
        raise RuntimeError("one execution thread cannot own two live lease heartbeats")
    heartbeat = LeaseHeartbeat(session.get_bind(), authority)
    _current.heartbeat = heartbeat
    heartbeat.start()


def stop_for_current_thread() -> None:
    heartbeat = getattr(_current, "heartbeat", None)
    if heartbeat is not None:
        del _current.heartbeat
        heartbeat.stop()
