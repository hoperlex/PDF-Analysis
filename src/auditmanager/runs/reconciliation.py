"""Startup reconciliation for orphan running runs and stale commands.

W53 gives live Jobs their own lease heartbeat and recovery owner. Startup
preserves queued Jobs and live leases; it fails a running Run only when its Job
is absent or terminal.

**`D-20` made this module reachable and gave it a second state to handle.** Until a
carrier existed, a run was created, executed and terminated inside the *one* transaction
that answered ``startRun``, so no intermediate state was ever committed and this
reconciler could never find anything: it was correct code guarding a case the
architecture could not produce. Now the accepting transaction commits ``queued`` and
the worker commits ``running``. A durable Job owns both states across restarts.

The vocabulary is the contract's, not a new one
-----------------------------------------------
``OD-10`` fixes the reconciliation terminal as the **declared** terminal ``failed``,
carrying an explicit ``interrupted_reason``. No ``interrupted`` state is invented: the
``audit_run`` machine declares four terminals and ``interrupted`` is not among them, so
adding one would mean the application and the ``AM001`` trigger disagreeing about what
states exist. The interruption is recorded as a *reason*, which is a column, rather than
as a *state*, which is a contract.

``GJ-02-EO-01`` is honored in its non-silent half: an orphan ``running``
becomes an explicit terminal. A nonterminal Job follows lease recovery instead.

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
from sqlalchemy import text

from auditmanager.ingest.public import CommandRepository
from auditmanager.jobs.public import (
    JobRepository,
    SettledProviderEffect,
    UnresolvedProviderEffect,
)
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

#: Only running Runs without live Job authority are reconciled here. Queued Jobs
#: remain durable work for the dispatcher across process restarts.
#:
#: ``created`` is **not** here and must not be. A run in ``created`` was never scheduled,
#: so nothing was ever going to execute it and nothing was interrupted; it is the state a
#: run has for the few statements between its INSERT and the accepting commit, and a
#: reconciler that terminated those would be terminating runs mid-creation.
#: ``running -> failed`` is a declared edge; ``created -> failed`` is not.
STRANDED_STATES: Final[tuple[str, ...]] = ("running",)


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
    settled_provider_effects: tuple[SettledProviderEffect, ...] = ()
    unresolved_provider_effects: tuple[UnresolvedProviderEffect, ...] = ()

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
    jobs: JobRepository | None = None,
    interrupted_reason: str = INTERRUPTED_REASON,
) -> tuple[ReconciledRun, ...]:
    """Fail only a running run whose durable Job is absent or already terminal.

    ``older_than`` is a PostgreSQL interval literal for the scan. It cannot
    establish process death: Job and Lease state is authoritative even at startup.

    The transition goes through the same guard and the same trigger as every other
    move. ``running -> failed`` is a declared edge, so this is reconciliation inside the
    contract rather than a repair around it.
    """
    run_repo = runs or RunRepository()
    job_repo = jobs or JobRepository()
    reconciled: list[ReconciledRun] = []
    for state in STRANDED_STATES:
        for run in run_repo.stale_in_state(
            session, state=state, older_than=older_than
        ):
            # The scan is a hint. Claim/cancel can move the row between scan and
            # write, so lock and recheck it before consulting the Job.
            locked_state = session.execute(text(
                "SELECT state FROM audit_run WHERE run_id = :run_id "
                "FOR UPDATE SKIP LOCKED"
            ), {"run_id": run.run_id}).scalar_one_or_none()
            if locked_state != state:
                continue
            # A second serving process may hold the live Lease. Startup cannot
            # infer process death from run age; the Job/Lease recovery path owns it.
            job_state = session.execute(text(
                "SELECT state FROM job WHERE run_id = :run_id "
                "FOR UPDATE SKIP LOCKED"
            ), {"run_id": run.run_id}).scalar_one_or_none()
            # A locked Job may be mid-claim. Distinguish it from absence with a
            # nonlocking existence read, and leave it to its owner.
            if job_state is None and session.execute(text(
                "SELECT 1 FROM job WHERE run_id = :run_id"
            ), {"run_id": run.run_id}).scalar_one_or_none() is not None:
                continue
            if job_state in {"queued", "leased", "running", "retry_wait"}:
                continue
            job_repo.fail_for_run(session, run_id=run.run_id)
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
    jobs: JobRepository | None = None,
    commands: CommandRepository | None = None,
    provider_effect_batch_size: int = 100,
    command_older_than: str | None = None,
) -> ReconciliationReport:
    """Both clauses, in the order a startup wants them.

    Runs first: a run is the thing an operator is looking at, and leaving it ``running``
    while its command record has already been resolved would be the more confusing of
    the two intermediate states.
    """
    job_repo = jobs or JobRepository()
    reconciled = reconcile_interrupted_runs(
        session, older_than=older_than, runs=runs, jobs=job_repo
    )
    abandoned = abandon_stale_commands(
        session, older_than=command_older_than or older_than, commands=commands
    )
    settled = job_repo.settle_terminal_provider_effects(
        session,
        older_than=older_than,
        batch_size=provider_effect_batch_size,
    )
    unresolved = job_repo.unresolved_provider_effects(session)
    return ReconciliationReport(
        runs=reconciled,
        abandoned_command_ids=abandoned,
        settled_provider_effects=settled,
        unresolved_provider_effects=unresolved,
    )


#: The startup scan may run immediately because the locked Job recheck preserves
#: nonterminal authority, including a live lease held by another process.
STARTUP_THRESHOLD: Final[str] = "0 seconds"
STARTUP_COMMAND_THRESHOLD: Final[str] = "10 minutes"


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
        report = reconcile(
            session, older_than=STARTUP_THRESHOLD,
            command_older_than=STARTUP_COMMAND_THRESHOLD,
        )
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
