"""Cross-context surface of the batch operations (`CMP-INGEST-02`): what the composition root imports.

The two handler factories are appended to the comparison queue's registry by the composition root (a ``comparison``
module may not import ``ingest``, and the registry refuses a duplicate kind, so the root is the one place that holds
both).
"""

from __future__ import annotations

from .handlers import (
    BatchDriveHandler,
    UploadSweepHandler,
    batch_drive_handler,
    upload_sweep_handler,
)
from .lifecycle import BatchLifecycle
from .rules import (
    ABANDON_AFTER_SECONDS,
    DRIVE_KIND,
    RETRYABLE_SET_REASONS,
    SWEEP_GRACE_SECONDS,
    SWEEP_KIND,
)
from .service import ComparisonBatchService
from .views import UploadPageView

#: Appended to ``comparison.public.HANDLER_FACTORIES`` by ``bootstrap.composition`` (one kind per factory).
BATCH_HANDLER_FACTORIES = (batch_drive_handler, upload_sweep_handler)

__all__ = [
    "ABANDON_AFTER_SECONDS",
    "BATCH_HANDLER_FACTORIES",
    "DRIVE_KIND",
    "RETRYABLE_SET_REASONS",
    "SWEEP_GRACE_SECONDS",
    "SWEEP_KIND",
    "BatchDriveHandler",
    "BatchLifecycle",
    "ComparisonBatchService",
    "UploadPageView",
    "UploadSweepHandler",
    "batch_drive_handler",
    "upload_sweep_handler",
]
