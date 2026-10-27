"""The stored form of a summary and the one thing the served read asks of its store (`COMPARE-PERSISTED-SUMMARY-01`, B2).

A leaf module: ``service`` (the read) and ``summaries`` (the command and the store) both need these
values, and neither may import the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Protocol, runtime_checkable

from sqlalchemy.orm import Session

from auditmanager.comparison.summary_validation import Statement

STATE_READY: Final[str] = "ready"
STATE_REJECTED: Final[str] = "rejected"
SUMMARY_STATES: Final[tuple[str, ...]] = (STATE_READY, STATE_REJECTED)
COST_BASES: Final[tuple[str, ...]] = ("unmetered", "measured", "estimated")


@dataclass(frozen=True, slots=True)
class StoredSummary:
    """One row of ``comparison_summary``."""

    summary_id: str
    comparison_id: str
    link_revision: int
    project_uid: str
    raw_evidence_seal_sha256: str
    input_sha256: str
    request_sha256: str
    prompt_version: str
    provider_mode: str
    model_identity: str
    state: str
    rejection_reason: str | None
    statements: tuple[Statement, ...]
    cost_basis: str
    cost_micros: int
    actor_user_uid: str
    actor_label: str
    command_id: str
    created_at: datetime


@runtime_checkable
class LatestSummaryReader(Protocol):
    """What the served comparison needs of the store: the newest summary of a comparison."""

    def latest(self, session: Session, *, comparison_id: str) -> StoredSummary | None:
        """The newest stored summary of the comparison, ready or rejected."""


__all__ = [
    "COST_BASES", "LatestSummaryReader", "STATE_READY", "STATE_REJECTED", "SUMMARY_STATES",
    "StoredSummary",
]
