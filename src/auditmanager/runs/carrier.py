"""`D-20` — what carries a run off the request thread, and what it leaves behind.

Until this module existed, ``RunAdapter.start_run`` imported ``execute_run`` and called it
inline, inside the same ``_write(...)`` that created the run. Three consequences, all of
them measured rather than reasoned about:

* the ``202`` was already ``published``, so a poller made **one** request and stopped, and
  ``PA-01`` criterion 4's UI clause was *unreachable* rather than unimplemented;
* every state the executor wrote -- ``queued``, ``running``, ``validating`` -- was written
  and overwritten inside one uncommitted transaction, so no second connection could ever
  read one. The states were reachable in the code and unobservable from outside it, which
  is not the same defect and is why the row is an implementation change and not a reseal:
  ``contracts/domain/v1/state-machines.json`` already declares
  ``created -> queued -> running -> validating -> {published, partial, failed}``, and
  nothing here adds a state, an edge or a field;
* nginx's ``proxy_read_timeout 300s`` was the whole margin of a run, because the browser
  was holding the connection open for the duration of the analysis.

What carries it, and why not something bigger
---------------------------------------------
``PROTOTYPE_PROFILE.md`` section 7 defers "remote/distributed workers", and section 2 says
"One local execution process is sufficient. Run and stage state are persisted before
execution, but distributed-worker semantics are deferred." Both sentences are about
*distribution*. Neither says the work must happen on the thread that answered the request,
and the second one says the opposite of that: state is persisted *before* execution, which
only means anything if something other than the accepting call can read it in between.

So: **one bounded pool inside the serving process**, :data:`RUN_CONCURRENCY` wide, owned by
the composition root. It creates no ``Job``, no ``Attempt``, no lease, no heartbeat, no
fencing token and no outbox -- ``auditmanager.runs``'s own module note lists those as the
things PC-01 has no such thing as, and this module adds none of them. A queue that outlives
the process, a second machine, or work that can be handed from one process to another would
be the deferred thing; a thread that outlives one HTTP response is not.

:data:`RUN_CONCURRENCY` is **1**, so runs still execute one at a time exactly as they did
inline. That is the profile's "one local execution process is sufficient" taken literally,
and it buys something the inline version could not offer: a second run submitted while the
first is executing sits in ``queued`` and *says so*, which is the state the contract
declares for precisely that situation.

Two transactions, and the crash story that follows from where the boundary is
-----------------------------------------------------------------------------
:func:`run_to_terminal` executes a queued run in **two** transactions:

1. ``queued -> running``, committed. This is what makes ``running`` a reading rather than
   an internal step.
2. everything else -- all four stages, every ``stage_result`` row, the evidence gate, the
   published findings and the terminal -- committed once, at the end.

The boundary is deliberately not finer. A commit in the middle of the analysis would let a
reader see the stage rows of a run that then died, and PC-01 cannot resume, so those rows
would describe work no terminal ever accounts for. With one boundary there are exactly two
things a process death can leave: a run in ``running`` with no stage rows at all, or a run
that reached its terminal with all of them. Nothing in between.

That leaves ``running`` as *the* stranded state, which is what
:mod:`auditmanager.runs.reconciliation` was already written to resolve -- ``OD-10``, at
startup, into the declared terminal ``failed`` carrying an ``interrupted_reason``. Before
this module that reconciler had nothing to reconcile, because nothing ever committed a
``running`` row.

An exception is not a crash, and is not left to the reconciler
--------------------------------------------------------------
While execution was inline, an exception that escaped ``execute_run`` became a ``500``
envelope and the caller learned about it. Off the request thread there is no caller left to
tell, so the *only* reader is the run row -- and a run whose execution raised must reach a
terminal by itself rather than wait an unbounded time for the next process start.
:func:`run_to_terminal` therefore catches everything that escapes, in its own fresh
transaction (the failed one has been rolled back), and terminates the run ``failed`` with
``analysis_failed`` and a reason naming the exception type. ``run_stage`` only catches
``DomainError``, so this path is reachable by anything else a handler, a store or a driver
can raise.

The reconciler stays for the case this cannot cover: a process that is killed has no
``except`` clause to run.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from time import monotonic
from typing import Any, Final, Protocol

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.runs.executor import execute_run
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.scope import RECONCILIATION_TERMINAL
from auditmanager.shared.errors import ErrorCode

__all__ = [
    "CRASHED_REASON",
    "RUN_CONCURRENCY",
    "InlineCarrier",
    "RunCarrier",
    "ThreadCarrier",
    "run_to_terminal",
]

_log = logging.getLogger(__name__)

#: How many runs this process executes at once. One, because ``PROTOTYPE_PROFILE.md``
#: section 2 says one local execution process is sufficient -- so a second submitted run
#: waits in ``queued``, which is a declared state and now a visible one.
RUN_CONCURRENCY: Final[int] = 1

#: The ``interrupted_reason`` of a run whose execution raised. Deliberately a different
#: sentence from ``reconciliation.INTERRUPTED_REASON``: that one means "the process ended
#: before a terminal", this one means "the process is alive and the execution raised". A
#: reader that could not tell them apart would not know whether to look for a dead
#: container or for a stack trace.
CRASHED_REASON: Final[str] = "executor_raised_before_terminal"


class RunCarrier(Protocol):
    """Whatever takes a unit of run work off the thread that accepted the request.

    Narrow on purpose: it takes a nullary callable and knows nothing about runs, sessions
    or stages. The knowledge of what a run *is* stays in :func:`run_to_terminal`, so a
    different carrier is a scheduling decision and never a second implementation of
    execution.
    """

    def submit(self, job: Callable[[], None]) -> None:
        """Arrange for ``job`` to be called. Returns without waiting for it."""

    def drain(self, timeout: float | None = None) -> bool:
        """Block until everything submitted so far has finished.

        Returns ``True`` when it did. This is how a test waits for a run without
        sleeping on a guess, and how a caller that genuinely needs the whole result --
        the characterization journey, the acceptance suite -- gets it deterministically.
        """

    def shutdown(self) -> None:
        """Stop accepting work. Does not wait; see the module note on shutdown."""


class InlineCarrier:
    """Runs the job on the calling thread, before ``submit`` returns.

    This is the behaviour `D-20` is about, kept as a named object rather than deleted.
    Two reasons. It is the thing a mutation restores, so "execution went back on the
    request thread" is one constructor argument and the tests that redden are the point
    of the exercise. And an in-process caller that wants a finished run and has no
    server -- a migration check, a script -- can ask for one without a pool.
    """

    def submit(self, job: Callable[[], None]) -> None:
        job()

    def drain(self, timeout: float | None = None) -> bool:
        return True

    def shutdown(self) -> None:
        return None


class ThreadCarrier:
    """A bounded pool of daemon-ish worker threads inside the serving process.

    ``ThreadPoolExecutor`` threads are non-daemon and are joined by an ``atexit`` hook, so
    a clean interpreter exit waits for the run in flight -- which is the right thing when
    the process is shutting down normally and has a chance to finish. A kill does not
    reach that hook, which is exactly the case :mod:`auditmanager.runs.reconciliation`
    exists for.

    The futures are kept so :meth:`drain` can wait on the real completion of the real work
    rather than on a duration somebody guessed. They are discarded as they complete, so a
    long-lived process does not accumulate one per run.
    """

    __slots__ = ("_pending", "_pool", "_lock")

    def __init__(self, *, max_workers: int = RUN_CONCURRENCY) -> None:
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="auditmanager-run"
        )
        self._pending: set[Future[None]] = set()
        self._lock = threading.Lock()

    def submit(self, job: Callable[[], None]) -> None:
        future = self._pool.submit(job)
        with self._lock:
            self._pending.add(future)
        future.add_done_callback(self._forget)

    def _forget(self, future: Future[None]) -> None:
        with self._lock:
            self._pending.discard(future)

    def drain(self, timeout: float | None = None) -> bool:
        """Wait for every job submitted so far, including ones still queued behind others.

        Re-reads the pending set after each wait, because a future is discarded by a
        done-callback that has not necessarily run yet, and because with one worker a job
        submitted before the call can still be waiting behind another.

        ``timeout`` is a deadline for the whole call, not per iteration: a loop that
        handed each wait the full timeout would promise a bound it does not keep.
        """
        deadline = None if timeout is None else monotonic() + timeout
        while True:
            with self._lock:
                pending = set(self._pending)
            if not pending:
                return True
            remaining = None if deadline is None else deadline - monotonic()
            if remaining is not None and remaining <= 0:
                return False
            _finished, unfinished = wait(pending, timeout=remaining)
            if unfinished:
                return False

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


def run_to_terminal(
    session_factory: sessionmaker[Session],
    run_id: str,
    *,
    blob_store: Any,
    adapter: Any,
    provider_config: Any,
    runs: RunRepository | None = None,
) -> None:
    """Execute one **queued** run to a terminal, in its own sessions.

    The job a carrier carries. It owns its transactions -- the request that accepted the
    run has committed and gone -- and it raises nothing: there is nobody left to raise at,
    so every outcome is written to the run row instead.

    Called with a run that is not ``queued`` it fails at the first transition, which is a
    ``state_transition_not_allowed`` from the same compare-and-set every other move uses
    and is then recorded as the failure terminal like any other. It is not silently
    tolerated: a carrier handed a run somebody else is already executing must not join in.
    """
    run_repo = runs or RunRepository()

    # -- transaction 1: the state that makes this run observable --------------
    with session_factory() as session:
        run_repo.advance(
            session, run_id=run_id, from_state="queued", to_state="running"
        )
        session.commit()

    # -- transaction 2: the whole analysis, or none of it ---------------------
    try:
        with session_factory() as session:
            execute_run(
                session,
                run_id,
                blob_store=blob_store,
                adapter=adapter,
                provider_config=provider_config,
                runs=run_repo,
            )
            session.commit()
    except Exception as failure:  # noqa: BLE001 - see the module note
        _log.exception("run %s did not reach a terminal by itself", run_id)
        _record_crash(session_factory, run_id, failure, runs=run_repo)
        raise


def _record_crash(
    session_factory: sessionmaker[Session],
    run_id: str,
    failure: BaseException,
    *,
    runs: RunRepository,
) -> None:
    """Terminate a run whose execution raised, from whatever state it had reached.

    A fresh session, because the one the exception escaped has been rolled back and the
    stage rows it held are gone with it -- which is the point of the single boundary.

    The ``from_state`` is **read** rather than assumed: the exception can escape before
    ``running -> validating`` or after it, and both are declared edges to ``failed``. A
    run that is already terminal is left alone; the failure was then in whatever happened
    after the terminal was written, and overwriting a terminal is the one thing the
    contract refuses outright.

    If even this cannot be written -- the database is what died -- the run stays where it
    was and startup reconciliation is the backstop. Nothing here retries or hides.
    """
    try:
        with session_factory() as session:
            row = runs.find(session, run_id)
            if row is None or row.state in _TERMINAL_STATES:
                return
            runs.terminate(
                session,
                run_id=run_id,
                from_state=row.state,
                to_state=RECONCILIATION_TERMINAL,
                degradation_set=(),
                terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
                interrupted_reason=CRASHED_REASON,
            )
            session.commit()
    except Exception:  # pragma: no cover - the database is the thing that failed
        _log.exception("run %s could not be recorded as failed either", run_id)


#: Written out rather than read from the topology: this is a guard against overwriting a
#: terminal, and a guard that asks the thing it is guarding is not one.
_TERMINAL_STATES: Final[frozenset[str]] = frozenset(
    {"published", "partial", "failed", "cancelled"}
)
