"""Cross-context surface of the durable jobs boundary."""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.jobs.events import append_execution_event
from auditmanager.jobs.commands import set_execution_paused, set_job_priority
from auditmanager.jobs.repository import (
    AttemptAuthority,
    JobRepository,
    SettledProviderEffect,
    UnresolvedProviderEffect,
)
from auditmanager.jobs.lease import start_for_current_thread, stop_for_current_thread


def start_attempt_lease_heartbeat(session: Session, authority: AttemptAuthority) -> None:
    """Keep this execution thread's current Attempt lease alive independently."""
    start_for_current_thread(session, authority)


def stop_attempt_lease_heartbeat() -> None:
    """Stop only the heartbeat owned by this execution thread."""
    stop_for_current_thread()

__all__ = [
    "AttemptAuthority",
    "JobRepository",
    "SettledProviderEffect",
    "UnresolvedProviderEffect",
    "append_execution_event",
    "set_execution_paused",
    "set_job_priority",
    "start_attempt_lease_heartbeat",
    "stop_attempt_lease_heartbeat",
]
