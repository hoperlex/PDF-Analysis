"""The two reads that decide whether the comparison loop may claim at all.

Both belong to other contexts and are reached only through their ``public.py``:

* the hold on new work: the global pause, ``execution_control.paused``, through ``execution/public.py``
  (``ExecutionRepository.dispatch_status``) -- ``jobs/public.py`` exports only the setter, and the
  comparison context never queries ``execution_control`` itself (ADR-0025 decision 6) -- **or** the
  night window of the vectors, ``vector_control.window_state`` ``draining`` or ``encoding``, through
  ``precedents/public.py`` (``window_open``). The dispatcher's hint holds new Runs on the same two
  conditions in one statement (``jobs/repository.py``); the comparison loop holds new attempts on
  them too, so the encoder never runs beside a comparison attempt on the 4 GB host (``D-684``). An
  attempt that is already running is not touched: the window's drain waits for it
  (``precedents/vectors/repository.py`` ``running_work``). ``closed`` and ``skipped`` hold nothing;
* "a Run is claimable", through ``jobs/public.py`` (``JobRepository.next_queued_run``), which is the
  very read the worker's dispatch loop hints with, so the two cannot disagree about what is
  claimable: strict priority of Runs over comparison work (decision 6).

They are plain callables on a session so a test can hold one shut and prove the guard it stands for.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

__all__ = ["ClaimGates", "default_gates"]


@dataclass(frozen=True, slots=True)
class ClaimGates:
    #: ``True`` while new work is held: ``execution_control.paused`` is set, or the vectors' night window
    #: is open (``draining`` or ``encoding``). The queue overview reports the same read as its ``paused``.
    paused: Callable[[Session], bool]
    #: ``True`` while a Run is claimable by this process. Locks the hinted Run's row until the
    #: caller ends the transaction, so the caller rolls back at once.
    run_claimable: Callable[[Session], bool]


def default_gates(*, dispatch_groups: bool = True) -> ClaimGates:
    # Imported here: the gates are the only thing in this package that reaches those contexts, and
    # `comparison.public` is imported by processes that never claim.
    from auditmanager.execution.public import ExecutionRepository
    from auditmanager.jobs.public import JobRepository
    from auditmanager.precedents.public import window_open

    def paused(session: Session) -> bool:
        # The analysis pause first: when it holds, the window is not read. Either one holds the claim.
        return ExecutionRepository().dispatch_status(session).paused or window_open(session)

    def run_claimable(session: Session) -> bool:
        # `EXEC2-INT-3`: a non-`database` process never counts a pending group Run as claimable.
        return JobRepository(dispatch_groups=dispatch_groups).next_queued_run(session) is not None

    return ClaimGates(paused=paused, run_claimable=run_claimable)
