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
#: The deadline of an Attempt that never shows a sign of life, counted from the claim.
ATTEMPT_WATCHDOG_SECONDS = 900
#: The absolute ceiling of a **live** Attempt (`AR-V3-LIVENESS-01`, owner 2026-10-29): one whose
#: model call has shown a sign of life (:meth:`AttemptContext.progress`). Nothing else caps the
#: model's effort, thinking or turns.
ATTEMPT_HARD_CAP_SECONDS = 7200
#: How long a live Attempt may be silent before the watchdog fences it.
ATTEMPT_STALL_SECONDS = 600

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

    **Signs of life** (`AR-V3-LIVENESS-01`). An Attempt that never signals is fenced
    ``watchdog_seconds`` after the claim, exactly as before. An adapter whose remote session
    reports that it is alive calls :meth:`progress`; the first call makes the Attempt *live*, and
    from then on it is fenced after ``stall_seconds`` without a sign of life or at
    ``hard_cap_seconds`` after the claim, whichever comes first
    (:meth:`remaining_seconds`). The watchdog no longer applies to a live Attempt: a model that
    is thinking is not a model that hangs, and what is silent for ``stall_seconds`` is.

    Thread-safety: :meth:`progress` is called by the thread that makes the model call and
    :meth:`remaining_seconds` by the lease-heartbeat thread. The only state they share is one
    float, ``_last_progress`` (``None`` while the Attempt is not live). A writer takes
    ``_progress_lock`` to keep the value monotonic; a reader takes no lock and reads the
    attribute **once** into a local, which is atomic in CPython, so it never sees a torn value
    and never reads "live" and a stale instant from two different reads.
    """

    run_id: str
    attempt_id: str
    started_monotonic: float
    watchdog_seconds: float = float(ATTEMPT_WATCHDOG_SECONDS)
    call_id: str | None = field(default=None)
    hard_cap_seconds: float = float(ATTEMPT_HARD_CAP_SECONDS)
    stall_seconds: float = float(ATTEMPT_STALL_SECONDS)
    _last_progress: float | None = field(default=None, init=False, repr=False, compare=False)
    _progress_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False, compare=False,
    )

    def progress(self, now: float | None = None) -> None:
        """Record a sign of life at ``now`` (the monotonic clock unless given).

        The first call makes the Attempt live. A call with an instant older than the last one
        recorded changes nothing, so the sign of life never moves backwards.
        """
        instant = monotonic() if now is None else now
        with self._progress_lock:
            last = self._last_progress
            if last is None or instant > last:
                self._last_progress = instant

    @property
    def live(self) -> bool:
        """``True`` once the Attempt has shown a sign of life."""
        return self._last_progress is not None

    def remaining_seconds(self, now: float | None = None) -> float:
        """Seconds the watchdog leaves this Attempt, never negative.

        Not live: ``watchdog_seconds`` less the time since the claim (the fixed deadline of
        before). Live: the smaller of the ceiling that is left and the silence window that is
        left.
        """
        current = monotonic() if now is None else now
        elapsed = current - self.started_monotonic
        last = self._last_progress  # read once: see the class docstring
        if last is None:
            return max(0.0, self.watchdog_seconds - elapsed)
        return max(0.0, min(self.hard_cap_seconds - elapsed, self.stall_seconds - (current - last)))

    def hard_remaining_seconds(self, now: float | None = None) -> float:
        """Seconds left to the absolute ceiling, never negative."""
        current = monotonic() if now is None else now
        return max(0.0, self.hard_cap_seconds - (current - self.started_monotonic))

    def bind_call(self, call_id: str) -> None:
        self.call_id = call_id


class LeaseHeartbeat:
    def __init__(self, bind: Engine | Connection, authority: AttemptAuthority) -> None:
        engine = bind.engine if isinstance(bind, Connection) else bind
        self._sessions = sessionmaker(bind=engine)
        self._authority = authority
        # The limits are read here, not bound at import, so a test (or a later setting) that
        # changes the module constants governs the Attempts that start after it.
        self.context = AttemptContext(
            run_id=authority.run_id, attempt_id=authority.attempt_id,
            started_monotonic=monotonic(),
            watchdog_seconds=float(ATTEMPT_WATCHDOG_SECONDS),
            hard_cap_seconds=float(ATTEMPT_HARD_CAP_SECONDS),
            stall_seconds=float(ATTEMPT_STALL_SECONDS),
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
        while not self._stop.wait(HEARTBEAT_SECONDS):
            try:
                with self._sessions() as session:
                    # An Attempt that never signalled has the watchdog; a live one has its
                    # silence window and its ceiling (`AttemptContext.remaining_seconds`).
                    if self.context.remaining_seconds() <= 0:
                        _log.warning(
                            "attempt %s of run %s is fenced (live=%s)",
                            self._authority.attempt_id, self._authority.run_id, self.context.live,
                        )
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
