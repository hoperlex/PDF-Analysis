"""Startup reconciliation — ``OD-10``: a restart leaves no run falsely ``running``.

PC-01 runs one execution per run in one process. There is no lease, no heartbeat and no
fencing token to consult, so when a process dies its run stays ``running`` forever unless
something reconciles it. That something is this module, called at startup --
:func:`reconcile_at_startup`, from the serving application's lifespan.

**`D-20` made this module reachable and gave it a second state to handle.** Until a
carrier existed, a run was created, executed and terminated inside the *one* transaction
that answered ``startRun``, so no intermediate state was ever committed and this
reconciler could never find anything: it was correct code guarding a case the
architecture could not produce. Now that the accepting transaction commits ``queued`` and
the worker commits ``running``, both are states a dead process can leave behind --
:data:`STRANDED_STATES`.

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
from typing import Any, Final

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

#: The two non-terminal states a dead executor can leave a run sitting in, in the order
#: a reader cares about them. `D-20` added the second: before the carrier existed nothing
#: ever committed a ``queued`` row either, because the accepting transaction wrote
#: ``created``, ``queued``, ``running`` and a terminal before it committed once.
#:
#: ``created`` is **not** here and must not be. A run in ``created`` was never scheduled,
#: so nothing was ever going to execute it and nothing was interrupted; it is the state a
#: run has for the few statements between its INSERT and the accepting commit, and a
#: reconciler that terminated those would be terminating runs mid-creation. Both
#: ``queued -> failed`` and ``running -> failed`` are declared edges of the frozen
#: ``audit_run`` machine; ``created -> failed`` is not, so the topology refuses that move
#: even if this tuple were wrong.
STRANDED_STATES: Final[tuple[str, ...]] = ("running", "queued")


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
    """Move every stranded run -- ``running`` or ``queued`` -- to the ``OD-10`` terminal.

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
    for state in STRANDED_STATES:
        for run in run_repo.stale_in_state(
            session, state=state, older_than=older_than
        ):
            run_repo.terminate(
                session,
                run_id=run.run_id,
                from_state=state,
                to_state=RECONCILIATION_TERMINAL,
                degradation_set=(),
                terminal_reason=INTERRUPTED_TERMINAL_REASON,
                interrupted_reason=interrupted_reason,
            )
            reconciled.append(
                ReconciledRun(
                    run_id=run.run_id,
                    from_state=state,
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


#: The threshold a *process start* reconciles with, and the assumption it rests on.
#:
#: ``PROTOTYPE_PROFILE.md`` section 2: "One local execution process is sufficient." One
#: process means that at the instant this one starts, and before it binds a socket, no
#: run anywhere can legitimately be executing -- so every ``running`` and ``queued`` row
#: is stranded whatever its age, and a threshold is not needed to tell.
#:
#: **The assumption is load-bearing and is stated rather than buried.** Start a second
#: process against the same database and this value terminates the first one's live run.
#: That configuration is outside the profile; if it ever comes inside, this constant is
#: the one place that has to change, and the ``1 hour`` default of the functions above is
#: what it would change to.
STARTUP_THRESHOLD: Final[str] = "0 seconds"


def reconcile_at_startup(session_factory: Any) -> ReconciliationReport:
    """One reconciliation pass in its own transaction, for a process that is starting.

    `D-20`. Before a carrier existed this had nothing to find: a run was created,
    executed and terminated inside one transaction, so no ``running`` row was ever
    committed for a crash to strand. It is now the backstop for the one case
    :mod:`auditmanager.runs.carrier` cannot cover itself -- a process that is killed runs
    no ``except`` clause.

    Takes the session factory rather than a session: the caller is a process startup, not
    a unit of work, and there is no transaction for it to be inside yet.
    """
    with session_factory() as session:
        report = reconcile(session, older_than=STARTUP_THRESHOLD)
        session.commit()
    return report


__all__ = [
    "INTERRUPTED_REASON",
    "STARTUP_THRESHOLD",
    "STRANDED_STATES",
    "INTERRUPTED_TERMINAL_REASON",
    "ReconciledRun",
    "ReconciliationReport",
    "abandon_stale_commands",
    "reconcile",
    "reconcile_at_startup",
    "reconcile_interrupted_runs",
]
