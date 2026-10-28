"""The two reads that decide whether the comparison loop may claim at all.

Both belong to other contexts and are reached only through their ``public.py``:

* the global pause, ``execution_control.paused``, through ``execution/public.py``
  (``ExecutionRepository.dispatch_status``) -- ``jobs/public.py`` exports only the setter, and the
  comparison context never queries ``execution_control`` itself (ADR-0025 decision 6);
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
    #: ``True`` while ``execution_control.paused`` is set.
    paused: Callable[[Session], bool]
    #: ``True`` while a Run is claimable by this process. Locks the hinted Run's row until the
    #: caller ends the transaction, so the caller rolls back at once.
    run_claimable: Callable[[Session], bool]


def default_gates() -> ClaimGates:
    # Imported here: the gates are the only thing in this package that reaches those contexts, and
    # `comparison.public` is imported by processes that never claim.
    from auditmanager.execution.public import ExecutionRepository
    from auditmanager.jobs.public import JobRepository

    def paused(session: Session) -> bool:
        return ExecutionRepository().dispatch_status(session).paused

    def run_claimable(session: Session) -> bool:
        return JobRepository().next_queued_run(session) is not None

    return ClaimGates(paused=paused, run_claimable=run_claimable)
