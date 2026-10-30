"""Cross-context surface of the durable jobs boundary."""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.jobs.events import append_execution_event
from auditmanager.jobs.commands import set_execution_paused, set_job_priority
from auditmanager.jobs.repository import (
    JOB_WAKEUP_CHANNEL,
    AttemptAuthority,
    CompletedWindowCall,
    ExecutionNotClaimed,
    JobRepository,
    V3CompletedCall,
    SettledProviderEffect,
    UnresolvedProviderEffect,
)
from auditmanager.jobs.lease import (
    ATTEMPT_HARD_CAP_SECONDS,
    ATTEMPT_STALL_SECONDS,
    ATTEMPT_WATCHDOG_SECONDS,
    AttemptContext,
    start_for_current_thread,
    stop_for_current_thread,
)
from auditmanager.jobs.temporaries import SweepReport, sweep_stale_temporaries


def start_attempt_lease_heartbeat(
    session: Session, authority: AttemptAuthority
) -> AttemptContext:
    """Keep this execution thread's current Attempt lease alive independently.

    Returns the Attempt's context (`EXEC-HTTP-01`): the run, the Attempt, the instant the
    watchdog counts from and how long it allows, for the provider adapter factory."""
    return start_for_current_thread(session, authority)


def stop_attempt_lease_heartbeat() -> None:
    """Stop only the heartbeat owned by this execution thread."""
    stop_for_current_thread()

__all__ = [
    "ATTEMPT_HARD_CAP_SECONDS",
    "ATTEMPT_STALL_SECONDS",
    "ATTEMPT_WATCHDOG_SECONDS",
    "JOB_WAKEUP_CHANNEL",
    "AttemptAuthority",
    "AttemptContext",
    "CompletedWindowCall",
    "ExecutionNotClaimed",
    "JobRepository",
    "V3CompletedCall",
    "SettledProviderEffect",
    "SweepReport",
    "UnresolvedProviderEffect",
    "append_execution_event",
    "set_execution_paused",
    "set_job_priority",
    "start_attempt_lease_heartbeat",
    "stop_attempt_lease_heartbeat",
    "sweep_stale_temporaries",
]

# HOTFIX-ANALYSIS-1030: durable unit reply/effect inspection.
from auditmanager.jobs.extended_review import extended_unit

__all__.append("extended_unit")

from auditmanager.jobs.extended_review import has_ambiguous_provider_effect

__all__.append("has_ambiguous_provider_effect")
