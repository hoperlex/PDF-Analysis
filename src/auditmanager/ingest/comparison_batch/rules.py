"""The names and numbers of the batch operations (`CMP-INGEST-02`, ADR-0025 decisions 9, 10 and 16).

Nothing here touches a database or a store. The states are the ones migration ``0038`` declares (its trigger refuses any
other move); the constants name what this package writes and what it waits for.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "ABANDON_AFTER_SECONDS",
    "ACTIVE_FOR_SET_OPERATIONS",
    "COMMAND_CANCEL_UPLOAD",
    "COMMAND_EXCLUDE_SET",
    "COMMAND_PAUSE_UPLOAD",
    "COMMAND_RESUME_UPLOAD",
    "COMMAND_RETRY_SET",
    "DRIVE_ACTIVE_SECONDS",
    "DRIVE_IDLE_SECONDS",
    "DRIVE_KIND",
    "EXCLUDABLE_SET_STATES",
    "LIVE_ITEM_STATES",
    "REASON_BATCH_CANCELLED",
    "REASON_SETS_LIMIT",
    "RETRYABLE_SET_REASONS",
    "SWEEP_GRACE_SECONDS",
    "SWEEP_KIND",
    "SWEEP_REASONS",
    "drive_dedupe_key",
    "sweep_dedupe_key",
]

#: The command types are the snake case of the operationId (``scripts/recovery/product_purge.py`` registers them).
COMMAND_EXCLUDE_SET: Final[str] = "exclude_comparison_upload_set"
COMMAND_RETRY_SET: Final[str] = "retry_comparison_upload_set"
COMMAND_PAUSE_UPLOAD: Final[str] = "pause_comparison_upload"
COMMAND_RESUME_UPLOAD: Final[str] = "resume_comparison_upload"
COMMAND_CANCEL_UPLOAD: Final[str] = "cancel_comparison_upload"

#: The two work kinds this package registers (the handler registry refuses a duplicate kind).
DRIVE_KIND: Final[str] = "comparison_batch_drive"
SWEEP_KIND: Final[str] = "upload_abort_sweep"

#: The drive polls often while a set's items are live and rarely otherwise. A poll is one claim and one attempt row, so
#: the idle figure is a minute: a batch in flight is at most two per installation (ADR-0025 decision 9).
DRIVE_ACTIVE_SECONDS: Final[float] = 10.0
DRIVE_IDLE_SECONDS: Final[float] = 60.0

#: A batch still ``uploading`` after this long without any part, completion or placement is abandoned: it is cancelled
#: by the drive exactly as a person's cancel would, so its multipart parts are aborted and its slot is freed.
ABANDON_AFTER_SECONDS: Final[float] = 24 * 3600.0

#: How long after a cancel the abort sweep runs. A part whose request began before the cancel may still be on its way
#: to the store (a request is bounded by the browser edge's 290 s); aborting before it lands would leave the upload it
#: opens. The database refuses every later part, so nothing new can start during the grace.
SWEEP_GRACE_SECONDS: Final[float] = 300.0
SWEEP_REASONS: Final[tuple[str, ...]] = ("cancelled", "abandoned")

#: The states of ``comparison_work`` that are not terminal (``comparison.work.model.LIVE_STATES``; a test pins equality).
LIVE_ITEM_STATES: Final[frozenset[str]] = frozenset(
    ("queued", "leased", "running", "retry_wait", "paused", "spend_unknown")
)

#: A set operation (exclude, retry) acts on a batch that has been proposed and is not finished.
ACTIVE_FOR_SET_OPERATIONS: Final[tuple[str, ...]] = ("proposed", "processing", "paused")
#: A set can be left out while it waits for the user or after it failed; a set that is ``done`` has made versions, and
#: ``excluded`` is final (no edge leaves it, so nothing can undo it, silently or otherwise).
EXCLUDABLE_SET_STATES: Final[frozenset[str]] = frozenset(("needs_confirmation", "failed"))

#: ``CMP-INGEST-01`` writes this reason on a set it refused because the batch grouped into more sets than the limit of
#: decision 9 allows.
REASON_SETS_LIMIT: Final[str] = "comparison_sets_limit"
#: Why a failed set may be queued again. The limit is retryable while the batch has room (a set the user left out makes
#: room); every other reason belongs to the document or to a decision and a retry would meet it again.
RETRYABLE_SET_REASONS: Final[frozenset[str]] = frozenset((REASON_SETS_LIMIT,))

#: The reason a file that never completed carries once its batch is cancelled (not one a client can fix by sending).
REASON_BATCH_CANCELLED: Final[str] = "batch_cancelled"


def drive_dedupe_key(upload_id: str) -> str:
    """One live drive per batch (at most 256 characters)."""
    return f"batch_drive:{upload_id}"


def sweep_dedupe_key(upload_id: str) -> str:
    """One live abort sweep per batch."""
    return f"upload_abort:{upload_id}"
