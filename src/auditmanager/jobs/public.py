"""Cross-context surface of the durable jobs boundary."""

from __future__ import annotations

from auditmanager.jobs.events import append_execution_event
from auditmanager.jobs.commands import set_execution_paused, set_job_priority
from auditmanager.jobs.repository import (
    AttemptAuthority,
    JobRepository,
    SettledProviderEffect,
    UnresolvedProviderEffect,
)

__all__ = [
    "AttemptAuthority",
    "JobRepository",
    "SettledProviderEffect",
    "UnresolvedProviderEffect",
    "append_execution_event",
    "set_execution_paused",
    "set_job_priority",
]
