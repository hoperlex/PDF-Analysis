"""The worker service: the one process that claims runs on the stand (R-105, F-8).

``python -m auditmanager.workers serve`` runs this from the API's image with
``EXECUTION_ROLE=worker``. The API then runs ``EXECUTION_ROLE=api`` and claims nothing;
both processes fence expired leases. The authority boundary is unchanged from W53 and is
the database: a claim is a Job, a current Attempt and a Lease with the execution token,
taken under the run-first lock order by ``jobs``. This module decides only *when* to ask.

What it does, in five threads
-----------------------------
* **registry** -- at start a new ``wrk`` identity is registered in ``worker`` and written
  to the state directory (a tmpfs on the stand, so a restarted container is a new worker);
  every :data:`~auditmanager.workers.registry.HEARTBEAT_SECONDS` its ``heartbeat_at`` moves
  and the state directory's ``heartbeat`` file is touched for the container's health check.
  A heartbeat that finds no row (the schema was reset underneath) stops intake and marks
  the service failed, so the process exits and restarts under a new identity.
* **dispatch** -- ``LISTEN`` on :data:`~auditmanager.jobs.public.JOB_WAKEUP_CHANNEL` over a
  dedicated connection outside the pool. A notification, a finished run or the
  :data:`POLL_SECONDS` poll each lead to one hint (``next_queued_run``) while a slot is free
  and the worker's intake is on. A lost ``LISTEN`` connection is logged as a warning and
  the poll carries on alone until the connection is re-established -- the stated
  fallback, never a silent one.
* **reclaim** -- inside the dispatch loop, every :data:`RECLAIM_SECONDS`.
* **slots** -- a pool of ``slots`` threads, each running one claimed run to a terminal.
* **probes** -- when a probe runner is given (`EXEC-HTTP-01`), a thread that takes the
  ``requested`` connection probes and runs them on this worker's network path. A draining worker
  takes no new probe.
* **temporaries** -- every :data:`TEMPORARIES_SWEEP_SECONDS`, the stage temporaries a killed
  process left in this container's ``/tmp`` (`DEBT-TEMP-SWEEP-01`, D-170; see below).

Temporaries
-----------
A stage's temporary PDF is removed by a context manager, which a ``SIGKILL`` never reaches. The
sweep at process start (``__main__``) takes what is older than the attempt watchdog plus a
minute, and the files of the kill that *caused* the restart are younger than that, so they stay
until a later start -- never, in a worker that is not restarted again. This thread repeats the
sweep while the worker runs, with a margin of :data:`TEMPORARIES_LIVE_MARGIN_SECONDS` over the
watchdog because this process's own attempts may be live. Housekeeping: a sweep that fails is
logged at error and tried again; it never stops the worker.

Drain
-----
:meth:`WorkerService.drain` stops claiming and waits for the runs in flight. ``SIGTERM``
drains (``__main__``); the compose stop grace period bounds it. A run still in flight when
the process is killed keeps its Lease until it expires, and the reclaim of either process
fences it -- resumed when no provider effect can have spent, failed otherwise.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from pathlib import Path
from time import monotonic
from typing import Any, Final

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.jobs.public import (
    ATTEMPT_WATCHDOG_SECONDS,
    JOB_WAKEUP_CHANNEL,
    JobRepository,
    SweepReport,
    sweep_stale_temporaries,
)
from auditmanager.workers.registry import HEARTBEAT_SECONDS, WorkerRegistry

_log = logging.getLogger(__name__)

#: The stated fallback when no notification arrives (R-105).
POLL_SECONDS: Final[float] = 5.0
#: W53's reclaim cadence, shared with the API process.
RECLAIM_SECONDS: Final[float] = 30.0
#: The longest the dispatch loop blocks before it looks at its stop and drain flags.
_TICK_SECONDS: Final[float] = 1.0
#: How often the probe loop looks for a ``requested`` probe when the last look found none
#: (`EXEC-HTTP-01`). A poll rather than a ``LISTEN``: a probe is a person pressing a button.
PROBE_POLL_SECONDS: Final[float] = 2.0
#: How often a running worker looks for the temporaries a killed process left
#: (`DEBT-TEMP-SWEEP-01`). A pass lists one directory and removes nothing unless something
#: stale is there.
TEMPORARIES_SWEEP_SECONDS: Final[float] = 300.0
#: What a running worker adds to the attempt watchdog before it calls a temporary stale. The sweep
#: at process start runs before any attempt exists and adds a minute; here this process's own
#: attempts may hold a file, so the margin is five minutes. The file is made after the claim and
#: the watchdog fences the attempt at its limit, so an older file belongs to an attempt that no
#: longer holds authority.
TEMPORARIES_LIVE_MARGIN_SECONDS: Final[float] = 300.0

#: Files in the state directory. The identity is written once; the heartbeat file's
#: modification time is what ``python -m auditmanager.workers health`` reads.
IDENTITY_FILE: Final[str] = "worker-id"
HEARTBEAT_FILE: Final[str] = "heartbeat"


def sweep_running_temporaries() -> SweepReport:
    """The sweep of a worker that is running: the start sweep's rules, a longer margin."""
    return sweep_stale_temporaries(
        older_than=float(ATTEMPT_WATCHDOG_SECONDS) + TEMPORARIES_LIVE_MARGIN_SECONDS,
    )


class JobWakeup:
    """``LISTEN`` on a dedicated connection, with its loss logged and survived.

    The connection is taken from the engine and **detached** from its pool, so it is a
    connection of its own (autocommit, never returned to another caller) rather than a
    pooled one held forever.
    """

    def __init__(
        self, engine: Engine, *, channel: str = JOB_WAKEUP_CHANNEL,
        poll_seconds: float = POLL_SECONDS,
    ) -> None:
        self._engine = engine
        self._channel = channel
        self._poll_seconds = poll_seconds
        self._connection: Any = None
        self._lost = False

    @property
    def listening(self) -> bool:
        return self._connection is not None

    @property
    def backend_pid(self) -> int | None:
        """The server process of the ``LISTEN`` connection, for an operator or a test."""
        return None if self._connection is None else int(self._connection.info.backend_pid)

    def connect(self) -> bool:
        try:
            pooled = self._engine.raw_connection()
            # Read the driver connection *before* detaching: SQLAlchemy 2.0's
            # ``_ConnectionFairy.driver_connection`` answers ``None`` once the fairy has
            # no pool record, which made every LISTEN fail with AttributeError and left
            # the worker on its poll alone (W55A-FIX-DB).
            connection = pooled.driver_connection
            pooled.detach()
            connection.rollback()
            connection.autocommit = True
            connection.execute(f"LISTEN {self._channel}")
        except Exception as failure:  # the database may be down; the poll still runs
            if not self._lost:
                _log.warning(
                    "worker LISTEN on %s could not be established (%s); polling every "
                    "%g s until it is", self._channel, type(failure).__name__,
                    self._poll_seconds,
                )
                self._lost = True
            return False
        self._connection = connection
        if self._lost:
            _log.info("worker LISTEN on %s re-established", self._channel)
        self._lost = False
        return True

    def wait(self, timeout: float, *, stop: threading.Event) -> bool:
        """``True`` when a notification arrived within ``timeout`` seconds."""
        if self._connection is None and not self.connect():
            stop.wait(timeout)
            return False
        try:
            # Consumed to the end so the generator releases the connection's lock here,
            # not whenever it happens to be collected.
            received = list(self._connection.notifies(timeout=timeout, stop_after=1))
            return bool(received)
        except Exception as failure:
            _log.warning(
                "worker LISTEN connection on %s was lost (%s: %s); falling back to a "
                "%g s poll until it is re-established",
                self._channel, type(failure).__name__, failure, self._poll_seconds,
            )
            self._lost = True
            self.close()
            return False

    def close(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.close()
            except Exception:  # pragma: no cover - closing a dead socket
                pass


class WorkerService:
    """Register, listen, claim, run and drain. One instance per worker process."""

    def __init__(
        self,
        *,
        engine: Engine,
        session_factory: sessionmaker[Session],
        execute: Callable[[str, str], None],
        version: str,
        slots: int = 1,
        state_dir: Path | None = None,
        poll_seconds: float = POLL_SECONDS,
        heartbeat_seconds: float = HEARTBEAT_SECONDS,
        reclaim_seconds: float = RECLAIM_SECONDS,
        registry: WorkerRegistry | None = None,
        probe_runner: Callable[[], int] | None = None,
        probe_poll_seconds: float = PROBE_POLL_SECONDS,
        temporaries_sweep: Callable[[], SweepReport] = sweep_running_temporaries,
        temporaries_sweep_seconds: float = TEMPORARIES_SWEEP_SECONDS,
    ) -> None:
        if slots < 1:
            raise ValueError("a worker needs at least one slot")
        if temporaries_sweep_seconds <= 0:
            raise ValueError("the temporaries sweep needs a positive interval")
        self._engine = engine
        self._sessions = session_factory
        self._execute = execute
        self._version = version
        self._slots = slots
        self._state_dir = state_dir
        self._poll_seconds = poll_seconds
        self._heartbeat_seconds = heartbeat_seconds
        self._reclaim_seconds = reclaim_seconds
        self._registry = registry or WorkerRegistry()
        self._probe_runner = probe_runner
        self._probe_poll_seconds = probe_poll_seconds
        self._temporaries_sweep = temporaries_sweep
        self._temporaries_sweep_seconds = temporaries_sweep_seconds
        self._worker_id: str | None = None
        self._stopped = threading.Event()
        self._draining = threading.Event()
        self._failed = threading.Event()
        self._poll_now = threading.Event()
        self._lock = threading.Lock()
        self._in_flight: set[Future[None]] = set()
        self._pool = ThreadPoolExecutor(max_workers=slots, thread_name_prefix="auditmanager-worker-run")
        self._threads: list[threading.Thread] = []
        self.wakeup = JobWakeup(engine, poll_seconds=poll_seconds)

    # -- identity -----------------------------------------------------------------
    @property
    def worker_id(self) -> str:
        if self._worker_id is None:
            raise RuntimeError("the worker has not registered yet")
        return self._worker_id

    @property
    def failed(self) -> bool:
        """The registry row disappeared under the process; it must restart."""
        return self._failed.is_set()

    @property
    def busy(self) -> int:
        with self._lock:
            return len(self._in_flight)

    def start(self) -> str:
        """Register a new identity and start listening, claiming and heartbeating."""
        with self._sessions() as session:
            self._worker_id = self._registry.register(
                session, version=self._version, slots=self._slots,
            )
            session.commit()
        self._write_state(IDENTITY_FILE, self._worker_id + "\n")
        self._touch_heartbeat()
        _log.info(
            "worker %s registered (version %s, %d slot(s))",
            self._worker_id, self._version, self._slots,
        )
        loops = [
            (self._heartbeat_loop, "auditmanager-worker-heartbeat"),
            (self._dispatch_loop, "auditmanager-worker-dispatch"),
            (self._temporaries_loop, "auditmanager-worker-temporaries"),
        ]
        if self._probe_runner is not None:
            loops.append((self._probe_loop, "auditmanager-worker-probes"))
        for target, name in loops:
            thread = threading.Thread(target=target, name=name, daemon=True)
            thread.start()
            self._threads.append(thread)
        return self._worker_id

    # -- drain and stop -------------------------------------------------------------
    def drain(self, timeout: float | None = None) -> bool:
        """Stop claiming new runs and wait for those in flight. ``True`` when none remain."""
        self._draining.set()
        deadline = None if timeout is None else monotonic() + timeout
        while True:
            with self._lock:
                pending = set(self._in_flight)
            if not pending:
                return True
            remaining = None if deadline is None else deadline - monotonic()
            if remaining is not None and remaining <= 0:
                return False
            wait(pending, timeout=remaining)

    def stop(self) -> None:
        """Stop every thread this service started. Does not wait for runs; see drain."""
        self._draining.set()
        self._stopped.set()
        for thread in self._threads:
            thread.join(timeout=_TICK_SECONDS * 5)
        self._pool.shutdown(wait=False, cancel_futures=True)

    # -- the loops ------------------------------------------------------------------
    def _heartbeat_loop(self) -> None:
        while not self._stopped.wait(self._heartbeat_seconds):
            try:
                with self._sessions() as session:
                    present = self._registry.heartbeat(session, self.worker_id)
                    session.commit()
            except Exception:
                _log.exception("worker %s heartbeat failed; retried next tick", self._worker_id)
                continue
            if not present:
                _log.error(
                    "worker %s is no longer in the registry (was the schema reset?); it "
                    "stops claiming and exits so that it restarts under a new identity",
                    self._worker_id,
                )
                self._draining.set()
                self._failed.set()
                return
            self._touch_heartbeat()

    def _dispatch_loop(self) -> None:
        next_poll = 0.0
        next_reclaim = 0.0
        woken = False
        try:
            while not self._stopped.is_set():
                now = monotonic()
                if now >= next_reclaim:
                    self._reclaim()
                    next_reclaim = monotonic() + self._reclaim_seconds
                if self._poll_now.is_set():
                    self._poll_now.clear()
                    woken = True
                can_claim = not self._draining.is_set() and self.busy < self._slots
                if can_claim and (woken or now >= next_poll):
                    woken = False
                    claimed = self._claim_next()
                    next_poll = monotonic() + self._poll_seconds
                    if claimed:
                        continue
                # Busy or draining: nothing to claim until a slot frees (`_poll_now`), so
                # wait a whole tick instead of spinning on an overdue poll.
                tick = (
                    min(_TICK_SECONDS, max(0.01, next_poll - monotonic())) if can_claim
                    else _TICK_SECONDS
                )
                woken = self.wakeup.wait(tick, stop=self._stopped) or woken
        finally:
            self.wakeup.close()

    def _probe_loop(self) -> None:
        """Take ``requested`` connection probes while this worker is not draining."""
        assert self._probe_runner is not None
        while not self._stopped.is_set():
            handled = 0
            if not self._draining.is_set():
                try:
                    handled = self._probe_runner()
                except Exception:
                    _log.exception("worker %s probe pass failed; retried", self._worker_id)
            self._stopped.wait(0.1 if handled else self._probe_poll_seconds)

    def _temporaries_loop(self) -> None:
        """Reclaim the temporaries of killed processes while the service runs (D-170).

        Housekeeping, so the one place a failure is logged and the worker carries on; the sweep
        itself logs what it removed and what it could not.
        """
        while not self._stopped.wait(self._temporaries_sweep_seconds):
            try:
                self._temporaries_sweep()
            except Exception:
                _log.exception(
                    "worker %s temporaries sweep failed; retried in %g s",
                    self._worker_id, self._temporaries_sweep_seconds,
                )

    def _reclaim(self) -> None:
        try:
            with self._sessions() as session:
                JobRepository().reclaim_expired(session)
                session.commit()
        except Exception:
            _log.exception("worker %s lease reclaim pass failed", self._worker_id)

    def _claim_next(self) -> bool:
        """Hand one runnable Job to a free slot. The claim itself happens in the slot."""
        try:
            with self._sessions() as session:
                if not self._registry.intake_enabled(session, self.worker_id):
                    return False
                run_id = JobRepository().next_queued_run(session)
        except Exception:
            _log.exception("worker %s could not read the queue", self._worker_id)
            return False
        if run_id is None:
            return False
        future = self._pool.submit(self._run_one, str(run_id))
        with self._lock:
            self._in_flight.add(future)
        future.add_done_callback(self._finished)
        return True

    def _run_one(self, run_id: str) -> None:
        try:
            self._execute(run_id, self.worker_id)
        except Exception as failure:
            # `run_to_terminal` has already written the outcome to the run row, or left
            # the run untouched when the claim was refused; this is the log line only.
            _log.info("worker %s: run %s ended here with %s", self._worker_id, run_id,
                      type(failure).__name__)

    def _finished(self, future: Future[None]) -> None:
        with self._lock:
            self._in_flight.discard(future)
        self._poll_now.set()

    # -- the state directory ------------------------------------------------------------
    def _write_state(self, name: str, content: str) -> None:
        if self._state_dir is None:
            return
        target = self._state_dir / name
        temporary = target.with_name(f".{name}.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, target)

    def _touch_heartbeat(self) -> None:
        if self._state_dir is None:
            return
        try:
            (self._state_dir / HEARTBEAT_FILE).touch()
        except OSError:
            _log.exception("worker %s could not touch its heartbeat file", self._worker_id)


def healthy(state_dir: Path, *, max_age_seconds: float, now: float) -> bool:
    """The container health check: a registered identity and a recent heartbeat."""
    try:
        identity = (state_dir / IDENTITY_FILE).read_text(encoding="utf-8").strip()
        age = now - (state_dir / HEARTBEAT_FILE).stat().st_mtime
    except OSError:
        return False
    return identity.startswith("wrk_") and age <= max_age_seconds


__all__ = [
    "HEARTBEAT_FILE",
    "IDENTITY_FILE",
    "POLL_SECONDS",
    "PROBE_POLL_SECONDS",
    "RECLAIM_SECONDS",
    "TEMPORARIES_LIVE_MARGIN_SECONDS",
    "TEMPORARIES_SWEEP_SECONDS",
    "JobWakeup",
    "WorkerService",
    "healthy",
    "sweep_running_temporaries",
]
