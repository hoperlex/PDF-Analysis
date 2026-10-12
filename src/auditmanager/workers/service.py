"""The worker service: the one process that claims runs on the stand (R-105, F-8).

``python -m auditmanager.workers serve`` runs this from the API's image with
``EXECUTION_ROLE=worker``. The API then runs ``EXECUTION_ROLE=api`` and claims nothing;
both processes fence expired leases. The authority boundary is unchanged from W53 and is
the database: a claim is a Job, a current Attempt and a Lease with the execution token,
taken under the run-first lock order by ``jobs``. This module decides only *when* to ask.

What it does, in four threads
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

from auditmanager.jobs.public import JOB_WAKEUP_CHANNEL, JobRepository
from auditmanager.workers.registry import HEARTBEAT_SECONDS, WorkerRegistry

_log = logging.getLogger(__name__)

#: The stated fallback when no notification arrives (R-105).
POLL_SECONDS: Final[float] = 5.0
#: W53's reclaim cadence, shared with the API process.
RECLAIM_SECONDS: Final[float] = 30.0
#: The longest the dispatch loop blocks before it looks at its stop and drain flags.
_TICK_SECONDS: Final[float] = 1.0

#: Files in the state directory. The identity is written once; the heartbeat file's
#: modification time is what ``python -m auditmanager.workers health`` reads.
IDENTITY_FILE: Final[str] = "worker-id"
HEARTBEAT_FILE: Final[str] = "heartbeat"


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
            pooled.detach()
            connection = pooled.driver_connection
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
    ) -> None:
        if slots < 1:
            raise ValueError("a worker needs at least one slot")
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
        for target, name in (
            (self._heartbeat_loop, "auditmanager-worker-heartbeat"),
            (self._dispatch_loop, "auditmanager-worker-dispatch"),
        ):
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
    "RECLAIM_SECONDS",
    "JobWakeup",
    "WorkerService",
    "healthy",
]
