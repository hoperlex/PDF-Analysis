"""The vocabulary of the overview: the seven steps, their state words, the four groups of the counters.

`CMP-VC-OVERVIEW-01`. Pure: no database, no clock. The words are those of the contract (``ComparisonStepId``,
``ComparisonStepState``); the groups are the original's four tones (``version-comparison-projects.js:319``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

__all__ = [
    "ATTENTION",
    "BLOCKED",
    "DONE",
    "FAILED",
    "GROUP_FAILED",
    "GROUP_READY",
    "GROUP_RUNNING",
    "GROUP_WAITING",
    "INTERRUPTED",
    "NOT_APPLICABLE",
    "NOT_STARTED",
    "PARTIAL",
    "PAUSED",
    "PAUSING",
    "QUEUED",
    "RUNNING",
    "RUNNING_STATES",
    "STALE",
    "STEP_AI_CHANGES",
    "STEP_AI_PAIRS",
    "STEP_MATRIX",
    "STEP_ORDER",
    "STEP_PROFILE",
    "STEP_REPORT",
    "STEP_SERIES",
    "STEP_UPLOAD",
    "Step",
]

STEP_UPLOAD: Final[str] = "upload"
STEP_PROFILE: Final[str] = "profile"
STEP_MATRIX: Final[str] = "matrix"
STEP_AI_PAIRS: Final[str] = "ai_pairs"
STEP_SERIES: Final[str] = "series"
STEP_AI_CHANGES: Final[str] = "ai_changes"
STEP_REPORT: Final[str] = "report"
#: The seven steps in the order the table shows them (the contract's ``ComparisonStepId``).
STEP_ORDER: Final[tuple[str, ...]] = (
    STEP_UPLOAD, STEP_PROFILE, STEP_MATRIX, STEP_AI_PAIRS, STEP_SERIES, STEP_AI_CHANGES, STEP_REPORT,
)

NOT_STARTED: Final[str] = "not_started"
QUEUED: Final[str] = "queued"
RUNNING: Final[str] = "running"
PAUSING: Final[str] = "pausing"
PAUSED: Final[str] = "paused"
INTERRUPTED: Final[str] = "interrupted"
DONE: Final[str] = "done"
PARTIAL: Final[str] = "partial"
STALE: Final[str] = "stale"
ATTENTION: Final[str] = "attention"
FAILED: Final[str] = "failed"
BLOCKED: Final[str] = "blocked"
NOT_APPLICABLE: Final[str] = "not_applicable"
#: The running tone of the original (``TONE`` at ``version-comparison-projects.js:15``: running, queued, pausing).
RUNNING_STATES: Final[frozenset[str]] = frozenset({QUEUED, RUNNING, PAUSING})

#: The four groups of the counters (the original's ``act`` / ``run`` / ``bad`` / ``ok``).
GROUP_WAITING: Final[str] = "waiting"
GROUP_RUNNING: Final[str] = "running"
GROUP_FAILED: Final[str] = "failed"
GROUP_READY: Final[str] = "ready"


@dataclass(frozen=True, slots=True)
class Step:
    """One step of one document set: its state word and the figures its note quotes (keys of ``ComparisonStepCounts``;
    ``None`` when the step has no figure)."""

    state: str
    counts: Mapping[str, int] | None = None
