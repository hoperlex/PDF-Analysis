"""Startup reconciliation — ``OD-10``: a restart leaves no run falsely ``running``.

PC-01 runs one execution per run in one process. There is no lease, no heartbeat and no
fencing token to consult, so when a process dies its run stays ``running`` forever unless
something reconciles it. That something is this module, called at startup.

The vocabulary is the contract's, not a new one
-----------------------------------------------
``OD-10`` fixes the reconciliation terminal as the **declared** terminal ``failed``,
carrying an explicit ``interrupted_reason``. No ``interrupted`` state is invented: the
``audit_run`` machine declares four terminals and ``interrupted`` is not among them, so
adding one would mean the application and the ``AM001`` trigger disagreeing about what
states exist. The interruption is recorded as a *reason*, which is a column, rather than
as a *state*, which is a contract.

``GJ-02-EO-01`` is honored in its non-silent half: a stale ``running`` becomes an
explicit terminal. PC-01 does not resume, because the profile defers resume — and a
reconciler that quietly re-queued the run would be a resume by another name.

Two independent clauses
-----------------------
:func:`reconcile_interrupted_runs` handles runs. :func:`abandon_stale_commands` handles
command records that are still ``in_progress`` with nobody left to finish them: those
move to ``abandoned``, which is terminal, so the key is never reused and a repeat under
it answers ``idempotency_key_stale`` rather than replaying an outcome that was never
established. They are separate because a stale run and a stale command record are not
the same fault and do not necessarily occur together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.ingest import CommandRepository
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.scope import RECONCILIATION_TERMINAL
from auditmanager.shared.errors import ErrorCode

#: The typed reason a reconciled run carries. It names what actually happened — the
#: executing process ended without reaching a terminal — and is deliberately not a
#: state name.
INTERRUPTED_REASON: Final[str] = "executor_process_ended_before_terminal"

#: ``failed`` requires a ``terminal_reason`` drawn from the frozen catalog. An
#: interrupted run produced no acceptable result, which is what this code means.
INTERRUPTED_TERMINAL_REASON: Final[str] = ErrorCode.ANALYSIS_FAILED.value


@dataclass(frozen=True, slots=True)
class ReconciledRun:
    """One run this reconciliation moved out of ``running``."""

    run_id: str
    from_state: str
    to_state: str
    interrupted_reason: str


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """What one reconciliation pass established."""

    runs: tuple[ReconciledRun, ...] = ()
    abandoned_command_ids: tuple[str, ...] = ()

    @property
    def run_count(self) -> int:
        return len(self.runs)

    @property
    def abandoned_count(self) -> int:
        return len(self.abandoned_command_ids)


def reconcile_interrupted_runs(
    session: Session,
    *,
    older_than: str = "1 hour",
    runs: RunRepository | None = None,
    interrupted_reason: str = INTERRUPTED_REASON,
) -> tuple[ReconciledRun, ...]:
    """Move every stale ``running`` run to the ``OD-10`` terminal.

    ``older_than`` is a PostgreSQL interval literal. It exists because "stale" has no
    meaning without a threshold and PC-01 has no heartbeat to derive one from; a caller
    reconciling at startup can pass ``'0 seconds'``, since by definition no execution is
    in flight at that moment.

    The transition goes through the same guard and the same trigger as every other
    move. ``running -> failed`` is a declared edge, so this is reconciliation inside the
    contract rather than a repair around it.
    """
    run_repo = runs or RunRepository()
    reconciled: list[ReconciledRun] = []
    for run in run_repo.stale_running(session, older_than=older_than):
        run_repo.terminate(
            session,
            run_id=run.run_id,
            from_state="running",
            to_state=RECONCILIATION_TERMINAL,
            degradation_set=(),
            terminal_reason=INTERRUPTED_TERMINAL_REASON,
            interrupted_reason=interrupted_reason,
        )
        reconciled.append(
            ReconciledRun(
                run_id=run.run_id,
                from_state="running",
                to_state=RECONCILIATION_TERMINAL,
                interrupted_reason=interrupted_reason,
            )
        )
    return tuple(reconciled)


def abandon_stale_commands(
    session: Session,
    *,
    older_than: str = "1 hour",
    commands: CommandRepository | None = None,
) -> tuple[str, ...]:
    """Mark unresolvable ``in_progress`` command records ``abandoned``.

    Nobody can establish what such a command did, so its key must never be reused: a
    repeat under it answers ``idempotency_key_stale``. ``abandoned`` is terminal in the
    ``command_idempotency`` machine, which is what makes that permanent.
    """
    command_repo = commands or CommandRepository()
    abandoned: list[str] = []
    for record in command_repo.stale_in_progress(session, older_than=older_than):
        command_repo.abandon(session, record.command_id)
        abandoned.append(str(record.command_id))
    return tuple(abandoned)


def reconcile(
    session: Session,
    *,
    older_than: str = "1 hour",
    runs: RunRepository | None = None,
    commands: CommandRepository | None = None,
) -> ReconciliationReport:
    """Both clauses, in the order a startup wants them.

    Runs first: a run is the thing an operator is looking at, and leaving it ``running``
    while its command record has already been resolved would be the more confusing of
    the two intermediate states.
    """
    reconciled = reconcile_interrupted_runs(session, older_than=older_than, runs=runs)
    abandoned = abandon_stale_commands(session, older_than=older_than, commands=commands)
    return ReconciliationReport(runs=reconciled, abandoned_command_ids=abandoned)


__all__ = [
    "INTERRUPTED_REASON",
    "INTERRUPTED_TERMINAL_REASON",
    "ReconciledRun",
    "ReconciliationReport",
    "abandon_stale_commands",
    "reconcile",
    "reconcile_interrupted_runs",
]
