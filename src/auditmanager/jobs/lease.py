"""Independent database heartbeat and watchdog for one execution Attempt."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from time import monotonic

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.repository import AttemptAuthority, JobRepository

# The lease is measured on database time: PostgreSQL stamps ``lease.expires_at`` at the
# claim and at every extension as ``statement_timestamp()`` plus
# ``JobRepository.lease_seconds`` (60 seconds, the 0017 default). Three heartbeats fit
# inside one lease. `W54-WORKER-01` (D-141): the final run transaction no longer holds the
# lease row while the evidence gate runs, so these extensions are not blocked there.
HEARTBEAT_SECONDS = 20
ATTEMPT_WATCHDOG_SECONDS = 900

_log = logging.getLogger(__name__)
_current = threading.local()


@dataclass(slots=True)
class AttemptContext:
    """What a provider adapter factory may know about the Attempt it serves (`EXEC-HTTP-01`).

    Built where the lease heartbeat starts, so ``started_monotonic`` is the instant the
    watchdog counts from (:data:`ATTEMPT_WATCHDOG_SECONDS`), and handed to the factory that
    builds the adapter. ``EXEC-PULL-01`` reads the deadline and the task's references from it;
    nothing in the run path changes for a new kind. ``call_id`` is the call journal's current
    model call, set when its intent is committed, so an adapter can name the call it is
    serving; it is ``None`` before the first call.
    """

    run_id: str
    attempt_id: str
    started_monotonic: float
    watchdog_seconds: float = float(ATTEMPT_WATCHDOG_SECONDS)
    call_id: str | None = field(default=None)

    def remaining_seconds(self, now: float | None = None) -> float:
        """Seconds the watchdog leaves this Attempt, never negative."""
        elapsed = (monotonic() if now is None else now) - self.started_monotonic
        return max(0.0, self.watchdog_seconds - elapsed)

    def bind_call(self, call_id: str) -> None:
        self.call_id = call_id


class LeaseHeartbeat:
    def __init__(self, bind: Engine | Connection, authority: AttemptAuthority) -> None:
        engine = bind.engine if isinstance(bind, Connection) else bind
        self._sessions = sessionmaker(bind=engine)
        self._authority = authority
        self.context = AttemptContext(
            run_id=authority.run_id, attempt_id=authority.attempt_id,
            started_monotonic=monotonic(),
        )
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
        started = self.context.started_monotonic
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


def start_for_current_thread(session: Session, authority: AttemptAuthority) -> AttemptContext:
    if getattr(_current, "heartbeat", None) is not None:
        raise RuntimeError("one execution thread cannot own two live lease heartbeats")
    heartbeat = LeaseHeartbeat(session.get_bind(), authority)
    _current.heartbeat = heartbeat
    heartbeat.start()
    return heartbeat.context


def stop_for_current_thread() -> None:
    heartbeat = getattr(_current, "heartbeat", None)
    if heartbeat is not None:
        del _current.heartbeat
        heartbeat.stop()
