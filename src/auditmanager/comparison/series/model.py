"""Vocabulary of the series of adjacent transitions (`CMP-SERIES-01`, ADR-0025 decisions 4, 15, 21).

The states and their edges are the database's (migration ``0039``): ``am_guard_comparison_core_state_edges`` refuses
any other move, so the constants here only name what the repository writes and the service reads. Nothing in this
module touches the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

__all__ = [
    "COMMAND_CANCEL",
    "COMMAND_FINISH",
    "COMMAND_PAUSE",
    "COMMAND_RESUME",
    "COMMAND_START",
    "COMPARED_STATUSES",
    "DIFF_STATUSES",
    "IMMEDIATE_STATUSES",
    "PAIR_DONE",
    "PAIR_FAILED",
    "PAIR_COMPUTING",
    "PAIR_QUEUED",
    "PartRecord",
    "PlannedPair",
    "PlannedTransition",
    "REASON_SPLIT_SHEET",
    "SERIES_AFTER_PREPARATION_KIND",
    "SERIES_DRIVE_KIND",
    "SERIES_LIVE",
    "SERIES_PAIR_KIND",
    "SERIES_TERMINAL",
    "SeriesPlan",
    "STATE_CANCELLED",
    "STATE_COMPLETED",
    "STATE_FAILED",
    "STATE_PAUSED",
    "STATE_QUEUED",
    "STATE_RUNNING",
    "VERDICT_CALCULATION_FAILED",
    "VERDICT_COMPOSITION_CHANGED",
    "VERDICT_CONTENT_SAME",
    "VERDICT_DIFFERENT",
    "VERDICT_INCOMPLETE",
    "VERDICT_NEEDS_REVIEW",
    "VERDICT_ORDER",
    "VERDICT_ZONES_ONLY",
]

#: The three work kinds of the series (``comparison_work.kind``): one item per sheet pair that needs the engine, one
#: polling item per series, one item per set whose preparation a batch has completed.
SERIES_PAIR_KIND: Final[str] = "series_pair"
SERIES_DRIVE_KIND: Final[str] = "series_drive"
SERIES_AFTER_PREPARATION_KIND: Final[str] = "series_after_preparation"

#: The command types are the snake case of the operationId (``scripts/recovery/product_purge.py`` registers them).
COMMAND_START: Final[str] = "start_comparison_series"
COMMAND_PAUSE: Final[str] = "pause_comparison_series"
COMMAND_RESUME: Final[str] = "resume_comparison_series"
COMMAND_CANCEL: Final[str] = "cancel_comparison_series"
COMMAND_FINISH: Final[str] = "finish_comparison_series"

STATE_QUEUED: Final[str] = "queued"
STATE_RUNNING: Final[str] = "running"
STATE_PAUSED: Final[str] = "paused"
STATE_COMPLETED: Final[str] = "completed"
STATE_FAILED: Final[str] = "failed"
STATE_CANCELLED: Final[str] = "cancelled"
#: A series in one of these states is live: at most one per document set (a partial unique index of ``0039``).
SERIES_LIVE: Final[tuple[str, ...]] = (STATE_QUEUED, STATE_RUNNING, STATE_PAUSED)
SERIES_TERMINAL: Final[tuple[str, ...]] = (STATE_COMPLETED, STATE_FAILED, STATE_CANCELLED)

PAIR_QUEUED: Final[str] = "queued"
PAIR_COMPUTING: Final[str] = "computing"
PAIR_DONE: Final[str] = "done"
PAIR_FAILED: Final[str] = "failed"

#: Statuses a pair gets without the engine: a sheet only in one version, or one the matrix could not place.
IMMEDIATE_STATUSES: Final[frozenset[str]] = frozenset({"added", "removed", "unmatched"})
#: The statuses the engine gives (they carry a ``result_id``).
COMPARED_STATUSES: Final[frozenset[str]] = frozenset({"same", "same_zones_changed", "different", "needs_review"})
#: What the permit reconciliation takes for «отличия найдены» (``permit.py:192``).
DIFF_STATUSES: Final[frozenset[str]] = frozenset({"different", "added", "removed"})

#: The forcing reason the series gives a sheet that was split across versions (the engine does not: ``CMP-ENGINE-01``
#: report section 5 item 1). A split is a change of composition that an expert confirms; it is never «Совпадает».
REASON_SPLIT_SHEET: Final[str] = "SPLIT_SHEET"

VERDICT_INCOMPLETE: Final[str] = "incomplete"
VERDICT_CONTENT_SAME: Final[str] = "content_same"
VERDICT_ZONES_ONLY: Final[str] = "zones_only"
VERDICT_DIFFERENT: Final[str] = "different"
VERDICT_COMPOSITION_CHANGED: Final[str] = "composition_changed"
VERDICT_NEEDS_REVIEW: Final[str] = "needs_review"
VERDICT_CALCULATION_FAILED: Final[str] = "calculation_failed"
#: The order the parts of a verdict are shown (``ComparisonVerdictCode``).
VERDICT_ORDER: Final[tuple[str, ...]] = (
    VERDICT_INCOMPLETE, VERDICT_CONTENT_SAME, VERDICT_ZONES_ONLY, VERDICT_DIFFERENT,
    VERDICT_COMPOSITION_CHANGED, VERDICT_NEEDS_REVIEW, VERDICT_CALCULATION_FAILED,
)


@dataclass(frozen=True, slots=True)
class PartRecord:
    """What a pair of a sheet split across versions keeps (the ``parts`` column).

    ``kind`` is ``split`` (the older sheet was cut into parts) or ``floors`` (a typical sheet repeated per floor: every
    newer page is the whole older sheet); ``role`` is ``part`` or ``whole`` (the matrix's word). ``text_percent`` is the
    matrix's text coverage of the older sheet by all its parts; ``parts`` are the other parts' pages."""

    kind: str
    role: str
    source_profile_id: str
    text_percent: float
    parts: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class PlannedPair:
    """One sheet pair of a transition, as it is written. ``compare`` says whether the engine is asked."""

    pair_no: int
    page_a_profile_id: str | None
    page_b_profile_id: str | None
    status: str | None
    confidence: str | None
    flags: tuple[str, ...]
    ai_dependent: bool
    part: PartRecord | None = None

    @property
    def compare(self) -> bool:
        return self.status is None


@dataclass(frozen=True, slots=True)
class PlannedTransition:
    transition_no: int
    source_version_uid: str
    target_version_uid: str
    pairs: tuple[PlannedPair, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SeriesPlan:
    """The adjacent transitions of one revision of the effective matrix, ready to be written."""

    matrix_id: str
    edit_no: int
    order_id: str | None
    order: tuple[str, ...]
    transitions: tuple[PlannedTransition, ...]
