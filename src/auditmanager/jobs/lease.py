"""Independent database heartbeat and watchdog for one execution Attempt."""

from __future__ import annotations

import logging
import math
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Final

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
#: The age ceiling of a **live** Attempt: there is none (`R-155c`, owner 2026-11-17, «Без потолка»). Two hours used to be the ceiling
#: (owner 2026-10-29) and ended the production run ``run_01M7MAMZTTDEQTT8VWNG63J7BB`` while its critic was still working. It is
#: ``math.inf``, never ``None``, so every limit that is *derived* from it (:meth:`AttemptContext.remaining_seconds`,
#: :meth:`AttemptContext.fence_remaining_seconds`) stays a finite, well-defined number -- the smaller of the infinity and a finite
#: window. What bounds an Attempt is the window of each model call (:meth:`AttemptContext.call_budget_seconds`), the lease, and the
#: silence watchdog below.
ATTEMPT_HARD_CAP_SECONDS = math.inf
#: The silence window of a live Attempt's model call, as the heartbeat of a command that prints one reads it (the SSH adapter's
#: ``live_stall_s``; the host agent keeps the same 600 s on its side, `R-153p`). It does not cut a call's window any more
#: (`R-155h`): a call's window is its stage row's, see :meth:`AttemptContext.call_budget_seconds`.
ATTEMPT_STALL_SECONDS = 600
#: `R-155c`. How long a **live** Attempt may show no sign of life **outside a model call** before the heartbeat fences it and the run ends
#: ``failed`` with ``interrupted_reason = attempt_stalled`` -- not re-queued. The stand's own work between two calls (pages, artifacts,
#: batches, the evidence gate) is local work that signals through :meth:`AttemptContext.progress`; a worker that signals nothing for this
#: long is hung, and resuming it would only hang again.
ATTEMPT_LOCAL_SILENCE_SECONDS = 1800
#: What a model call may outlive its **own** window by before the heartbeat takes it for a hung adapter and fences the Attempt the same
#: way. Every adapter ends its call by its window (a runner's task expires, a socket times out, an SSH command is cut); this is the
#: backstop for one that does not.
ATTEMPT_CALL_GRACE_SECONDS = 300
#: The window assumed for a call whose adapter did not name one (:meth:`AttemptContext.call_started` without ``window_seconds``): the
#: longest call the contract admits for a host (``payload.host.timeout_seconds`` 1..7200).
ATTEMPT_CALL_DEFAULT_WINDOW_SECONDS = 7200
#: `R-155c`, slot recovery. How long the work thread of an Attempt whose authority was **revoked** (the stall fence, ``cancelRun``, a
#: reclaim by another process, a lost lease) may keep running before the worker is told its slot is lost
#: (:func:`install_slot_recovery`). The fence takes the authority away, not the thread, and a worker has as many slots as threads
#: (``AUDITMANAGER_WORKER_SLOTS``, one by default), so one hung thread would hold the slot -- and with one slot, every run behind it --
#: for ever. A thread that is merely finishing returns well within this: its next write to the database is refused as stale.
ATTEMPT_RETURN_GRACE_SECONDS = 120

#: Why :meth:`AttemptContext.fence_reason` says the Attempt is to be fenced. The first two end the Attempt as before (the lost Attempt is
#: re-queued unless a provider effect is ambiguous or its budget is spent); the last two are a stall and end the run.
FENCE_WATCHDOG: Final[str] = "watchdog"
FENCE_HARD_CAP: Final[str] = "hard_cap"
FENCE_STALLED: Final[str] = "stalled"
FENCE_CALL_OVERRAN: Final[str] = "call_overran"
#: The ``interrupted_reason`` of a run whose Attempt was fenced as stalled.
INTERRUPTED_ATTEMPT_STALLED: Final[str] = "attempt_stalled"

_log = logging.getLogger(__name__)
_current = threading.local()


class RevokedAttempt:
    """What the slot-recovery hook is told (:func:`install_slot_recovery`): the Attempt whose authority was taken away and whose work
    thread was still running ``grace_seconds`` later, and why the authority went (``reason``)."""

    __slots__ = ("attempt_id", "grace_seconds", "reason", "run_id")

    def __init__(self, *, run_id: str, attempt_id: str, reason: str, grace_seconds: float) -> None:
        self.run_id = run_id
        self.attempt_id = attempt_id
        self.reason = reason
        self.grace_seconds = grace_seconds

    def __repr__(self) -> str:
        return (f"RevokedAttempt(run_id={self.run_id!r}, attempt_id={self.attempt_id!r}, "
                f"reason={self.reason!r}, grace_seconds={self.grace_seconds:g})")


SlotRecovery = Callable[[RevokedAttempt], None]
_slot_recovery: SlotRecovery | None = None


def install_slot_recovery(hook: SlotRecovery | None) -> None:
    """Name the process's answer to a lost slot: ``hook`` is called, once per Attempt and from that Attempt's heartbeat thread, when
    the work thread of an Attempt whose authority was revoked has not returned within :data:`ATTEMPT_RETURN_GRACE_SECONDS`.

    The worker service installs one (it exits the process so the container restart policy brings a fresh worker, `R-155c`); a process
    that holds no slot of its own -- the API, a test -- installs none, and the heartbeat then says so in its log. ``None`` removes it."""
    global _slot_recovery
    _slot_recovery = hook


def current_slot_recovery() -> SlotRecovery | None:
    """The installed hook, so a caller that replaces it can put it back."""
    return _slot_recovery


@dataclass(slots=True)
class AttemptContext:
    """What a provider adapter factory may know about the Attempt it serves (`EXEC-HTTP-01`).

    Built where the lease heartbeat starts, so ``started_monotonic`` is the instant the
    watchdog counts from (:data:`ATTEMPT_WATCHDOG_SECONDS`), and handed to the factory that
    builds the adapter. ``EXEC-PULL-01`` reads the deadline and the task's references from it;
    nothing in the run path changes for a new kind. ``call_id`` is the call journal's current
    model call, set when its intent is committed, so an adapter can name the call it is
    serving; it is ``None`` before the first call.

    **Signs of life.** An Attempt that never signals is fenced
    ``watchdog_seconds`` after the claim, exactly as before (and, as before, re-queued by the
    reclaim). A sign of life -- :meth:`progress`, the start and the end of a model call -- makes the
    Attempt *live*, and the watchdog no longer applies to it: a model that is thinking is not a
    model that hangs.

    **A live Attempt has no age ceiling** (`R-155c`): ``hard_cap_seconds`` is :data:`math.inf`
    unless a test says otherwise. What ends a live Attempt that has stopped is a silence, not an
    age:

    * **outside a model call**, the worker's own work (rendering pages, reading artifacts, planning
      batches, the evidence gate) must show a sign of life at least every ``local_silence_seconds``
      (:data:`ATTEMPT_LOCAL_SILENCE_SECONDS`, 30 minutes); the end of a call is itself one;
    * **inside a model call** (:meth:`call_started` ... :meth:`call_finished`), no silence is
      counted at all -- the call has its own window, up to an hour -- and the Attempt is fenced only
      when the call outlives that window by ``call_grace_seconds`` (a hung adapter).

    Both fences are *stalls* (:data:`FENCE_STALLED`, :data:`FENCE_CALL_OVERRAN`): the heartbeat ends
    the run ``failed`` with ``interrupted_reason = attempt_stalled`` and does not re-queue it.

    **A model call's window is its stage row's** (`R-155h`), not what the silence window leaves: an
    adapter asks :meth:`call_budget_seconds`, which for a live Attempt is the absolute ceiling alone
    (infinite with none), and cuts its own window (the row's ``ROW_TIMEOUT_SECONDS``) to it. Silence
    *inside* a call stays bounded by the party that makes it: the host agent's activity window and
    the runner's claim lease, or the SSH command's heartbeat (``stall_seconds``).

    Thread-safety: :meth:`progress`, :meth:`call_started` and :meth:`call_finished` are called by
    the thread that works and makes the model calls and :meth:`fence_remaining_seconds` /
    :meth:`fence_reason` by the lease-heartbeat thread. The state they share -- the last sign of
    life and the calls in flight -- is written under ``_progress_lock`` and read as one snapshot
    under it, so the heartbeat never pairs "no call in flight" with a sign of life older than the
    call that just ended. :meth:`remaining_seconds` and :meth:`call_budget_seconds` take no lock
    and read the sign of life **once** into a local, which is atomic in CPython.
    """

    run_id: str
    attempt_id: str
    started_monotonic: float
    watchdog_seconds: float = float(ATTEMPT_WATCHDOG_SECONDS)
    call_id: str | None = field(default=None)
    hard_cap_seconds: float = float(ATTEMPT_HARD_CAP_SECONDS)
    stall_seconds: float = float(ATTEMPT_STALL_SECONDS)
    local_silence_seconds: float = float(ATTEMPT_LOCAL_SILENCE_SECONDS)
    call_grace_seconds: float = float(ATTEMPT_CALL_GRACE_SECONDS)
    _last_progress: float | None = field(default=None, init=False, repr=False, compare=False)
    #: Model calls in flight (a count, so overlapping calls never end each other's tracking) and the instant after which the
    #: latest-deadline one is taken for hung; ``None`` while no call is in flight.
    _calls_in_flight: int = field(default=0, init=False, repr=False, compare=False)
    _call_deadline: float | None = field(default=None, init=False, repr=False, compare=False)
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

    @property
    def in_call(self) -> bool:
        """``True`` while a model call is in flight (between :meth:`call_started` and :meth:`call_finished`)."""
        return self._calls_in_flight > 0

    def call_started(self, now: float | None = None, *, window_seconds: float | None = None) -> None:
        """A model call is starting, with ``window_seconds`` of its own (the adapter's cut window).

        For a live Attempt this is a sign of life. For every Attempt it marks a call in flight until
        :meth:`call_finished`, so the silence watchdog leaves the Attempt alone for that call's window
        plus ``call_grace_seconds`` (the call's own window, :data:`ATTEMPT_CALL_DEFAULT_WINDOW_SECONDS`
        when none is named). An Attempt that is not live is otherwise left as it is: it keeps the
        watchdog's fixed deadline.
        """
        instant = monotonic() if now is None else now
        window = float(ATTEMPT_CALL_DEFAULT_WINDOW_SECONDS if window_seconds is None else window_seconds)
        deadline = instant + max(0.0, window) + self.call_grace_seconds
        with self._progress_lock:
            self._calls_in_flight += 1
            current = self._call_deadline
            self._call_deadline = deadline if current is None else max(current, deadline)
            last = self._last_progress
            if last is not None and instant > last:
                self._last_progress = instant

    def call_finished(self, now: float | None = None) -> None:
        """The model call ended, however it ended: for a live Attempt a sign of life, so the silence of the worker's own work
        that follows is counted from here. Called by the adapter in a ``finally``; one that is called without a matching
        :meth:`call_started` changes nothing but the sign of life."""
        instant = monotonic() if now is None else now
        with self._progress_lock:
            if self._calls_in_flight > 0:
                self._calls_in_flight -= 1
            if self._calls_in_flight == 0:
                self._call_deadline = None
            last = self._last_progress
            if last is not None and instant > last:
                self._last_progress = instant

    def remaining_seconds(self, now: float | None = None) -> float:
        """Seconds of silence a live call may still keep, never negative; always finite.

        Not live: ``watchdog_seconds`` less the time since the claim (the fixed deadline of
        before). Live: the smaller of the ceiling that is left (infinite with none) and the silence
        window that is left. It is **not** what a model call's window is cut to any more
        (:meth:`call_budget_seconds`).
        """
        current = monotonic() if now is None else now
        elapsed = current - self.started_monotonic
        last = self._last_progress  # read once: see the class docstring
        if last is None:
            return max(0.0, self.watchdog_seconds - elapsed)
        return max(0.0, min(self.hard_cap_seconds - elapsed, self.stall_seconds - (current - last)))

    def hard_remaining_seconds(self, now: float | None = None) -> float:
        """Seconds left to the absolute ceiling, never negative (``math.inf`` while there is none)."""
        current = monotonic() if now is None else now
        return max(0.0, self.hard_cap_seconds - (current - self.started_monotonic))

    def call_budget_seconds(self, now: float | None = None) -> float:
        """What the Attempt's own limits leave a model call that starts now, never negative (`R-155h`).

        Not live: the watchdog's fixed deadline, exactly :meth:`remaining_seconds` -- an Attempt that has
        shown no life yet is held to its 900 s. Live: the absolute ceiling alone, which with none is
        ``math.inf``; the silence window does not cut a call. The adapter takes the smaller of this (less its
        margin) and its own window, so with no ceiling a call's window is its stage row's.
        """
        if self._last_progress is None:  # read once: see the class docstring
            return self.remaining_seconds(now)
        return self.hard_remaining_seconds(now)

    def fence_remaining_seconds(self, now: float | None = None) -> float:
        """Seconds before the heartbeat fences this Attempt, never negative; always finite while a silence limit applies.

        Not live: the watchdog's fixed deadline, exactly as :meth:`remaining_seconds`. Live and between calls: the smaller
        of the ceiling and the local silence window that is left. Live and inside a call: the smaller of the ceiling and what
        is left of the call's own window plus its grace.
        """
        return self._fence(now)[0]

    def fence_reason(self, now: float | None = None) -> str | None:
        """Why the heartbeat fences this Attempt now -- :data:`FENCE_WATCHDOG`, :data:`FENCE_HARD_CAP`,
        :data:`FENCE_STALLED` or :data:`FENCE_CALL_OVERRAN` -- or ``None`` while it may go on."""
        remaining, reason = self._fence(now)
        return reason if remaining <= 0 else None

    def _fence(self, now: float | None) -> tuple[float, str]:
        current = monotonic() if now is None else now
        with self._progress_lock:
            last, deadline = self._last_progress, self._call_deadline
        elapsed = current - self.started_monotonic
        if last is None:
            return max(0.0, self.watchdog_seconds - elapsed), FENCE_WATCHDOG
        if deadline is not None:
            silence, reason = deadline - current, FENCE_CALL_OVERRAN
        else:
            silence, reason = self.local_silence_seconds - (current - last), FENCE_STALLED
        ceiling = self.hard_cap_seconds - elapsed
        if ceiling < silence:
            return max(0.0, ceiling), FENCE_HARD_CAP
        return max(0.0, silence), reason

    def bind_call(self, call_id: str) -> None:
        self.call_id = call_id


def model_call_budget_seconds(context: Any) -> float:
    """What the Attempt's limits leave a model call starting now, read from whatever context an adapter was given.

    An :class:`AttemptContext` answers :meth:`~AttemptContext.call_budget_seconds`; the comparison work's call context
    (``comparison.spend.pull_images.ComparisonCallContext``) has only ``remaining_seconds()``, which is its own, queue-bound
    number, and keeps meaning exactly what it meant."""
    budget = getattr(context, "call_budget_seconds", None)
    return float(budget() if callable(budget) else context.remaining_seconds())


def model_call_started(context: Any | None, window_seconds: float) -> None:
    """An adapter is about to make a model call of ``window_seconds``: tell the Attempt (:meth:`AttemptContext.call_started`).
    A context that has no such method (``None``, the comparison work's) is left alone."""
    starting = getattr(context, "call_started", None)
    if callable(starting):
        starting(window_seconds=window_seconds)


def model_call_finished(context: Any | None) -> None:
    """The call ended, however it ended; the adapter calls this in a ``finally`` (:meth:`AttemptContext.call_finished`)."""
    finished = getattr(context, "call_finished", None)
    if callable(finished):
        finished()


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
            local_silence_seconds=float(ATTEMPT_LOCAL_SILENCE_SECONDS),
            call_grace_seconds=float(ATTEMPT_CALL_GRACE_SECONDS),
        )
        self._return_grace_seconds = float(ATTEMPT_RETURN_GRACE_SECONDS)
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
        revoked: str | None = None
        while revoked is None and not self._stop.wait(HEARTBEAT_SECONDS):
            try:
                with self._sessions() as session:
                    # An Attempt that never signalled has the watchdog; a live one is fenced by a silence
                    # (`AttemptContext.fence_reason`), not by its age (`R-155c`).
                    reason = self.context.fence_reason()
                    if reason is not None:
                        revoked = self._fence(session, reason)
                        session.commit()
                    elif not JobRepository().heartbeat(session, self._authority):
                        revoked = self._why_not_current(session)
                        session.commit()
                        if revoked is None:
                            return  # the Attempt ended itself (`finish_execution`): nothing was taken away
                    else:
                        session.commit()
            except Exception:
                # A transient DB fault is visible and retried on the next tick. The
                # lease expiry is the durable fence if heartbeats cannot commit.
                _log.exception("lease heartbeat failed for run %s", self._authority.run_id)
        if revoked is not None:
            self._await_return(revoked)

    def _fence(self, session: Session, reason: str) -> str:
        """Fence the Attempt for ``reason``. The watchdog and the ceiling end it as before (re-queued by the reclaim unless a
        provider effect is ambiguous or the budget is spent); a stall ends the run, ``attempt_stalled``, and re-queues nothing."""
        stalled = reason in (FENCE_STALLED, FENCE_CALL_OVERRAN)
        _log.warning(
            "attempt %s of run %s is fenced (%s, live=%s, in_call=%s)",
            self._authority.attempt_id, self._authority.run_id, reason, self.context.live, self.context.in_call,
        )
        JobRepository().reclaim_expired(
            session, force_attempt_id=self._authority.attempt_id,
            **({"fail_reason": INTERRUPTED_ATTEMPT_STALLED} if stalled else {}),
        )
        return f"fenced:{reason}"

    def _why_not_current(self, session: Session) -> str | None:
        """The lease could not be extended: the authority is gone. ``None`` when the Attempt ended itself (it ran to its end
        and released the lease), otherwise what was done to it -- ``cancelRun``, another process's reclaim, a lease that lapsed."""
        state = JobRepository().attempt_state(session, self._authority.attempt_id)
        if state in ("succeeded", "failed"):
            return None
        return f"revoked:{state}"

    def _await_return(self, reason: str) -> None:
        """The authority of this Attempt is gone. Its work thread is still running until it stops this heartbeat (it does,
        in ``execute_run``'s ``finally``, within moments of its next refused write); if it has not within the grace, the
        slot is lost and the process is told (:func:`install_slot_recovery`)."""
        if self._stop.wait(self._return_grace_seconds):
            return
        notice = RevokedAttempt(
            run_id=self._authority.run_id, attempt_id=self._authority.attempt_id, reason=reason,
            grace_seconds=self._return_grace_seconds,
        )
        hook = _slot_recovery
        if hook is None:
            _log.error(
                "attempt %s of run %s: the work thread has not returned %g s after its authority was revoked (%s); "
                "this process has no slot recovery installed, so the slot stays held",
                notice.attempt_id, notice.run_id, notice.grace_seconds, reason,
            )
            return
        try:
            hook(notice)
        except Exception:
            _log.exception("slot recovery failed for run %s", notice.run_id)


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
