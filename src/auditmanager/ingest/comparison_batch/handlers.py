"""The two work kinds of the batch operations (`CMP-INGEST-02`): ``comparison_batch_drive`` and ``upload_abort_sweep``.

Both are handlers of the comparison queue (`CMP-WORK-01`): each ``run`` returns a typed outcome, publishes only in a
transaction that first proves its attempt still holds the item (``WorkItem.require_current``), and is safe to run again.

``comparison_batch_drive``
    One item per batch, payload ``{"upload_id": "cbt_..."}``. A poll is one transaction of
    :meth:`~.lifecycle.BatchLifecycle.drive`: release the next confirmed set when none is in flight, complete the batch,
    cancel a batch abandoned while ``uploading``. It answers :class:`Yielded` (come back after the delay the lifecycle
    chose) until the batch is finished, then :class:`Completed`.

``upload_abort_sweep``
    One item per cancelled (or abandoned) batch, payload ``{"upload_id": "cbt_...", "reason": "cancelled" |
    "abandoned"}``, enqueued by the cancel in the same transaction that cancels the batch (so the abort of the store's
    uploads is owed durably, never a side effect that can be lost with the process). It reads the tokens of the files
    that were never verified and hands them to ``abort_multipart_sweep``; it refuses to act on a batch that is not
    ``cancelled`` (a live batch's upload is never aborted by a sweep), never names a verified file, and never touches a
    published blob (the store's abort reaches the temporary key of a token and nothing else).
"""

from __future__ import annotations

import re
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.public import (
    Completed,
    Failed,
    Outcome,
    WorkDependencies,
    WorkItem,
    Yielded,
)
from auditmanager.ingest.comparison_batch.lifecycle import BatchLifecycle
from auditmanager.ingest.comparison_batch.repository import ComparisonBatchRepository
from auditmanager.ingest.comparison_batch.rules import DRIVE_KIND, SWEEP_KIND, SWEEP_REASONS
from auditmanager.ingest.comparison_pdf.public import ComparisonUploadRepository
from auditmanager.shared.db import session_scope
from auditmanager.storage.public import StorageError, abort_multipart_sweep

__all__ = [
    "REASON_NOT_CANCELLED",
    "REASON_PAYLOAD_INVALID",
    "REASON_STORE_UNAVAILABLE",
    "REASON_TOKEN_REJECTED",
    "BatchDriveHandler",
    "UploadSweepHandler",
    "batch_drive_handler",
    "upload_sweep_handler",
]

REASON_PAYLOAD_INVALID: Final[str] = "batch_payload_invalid"
REASON_NOT_CANCELLED: Final[str] = "sweep_upload_not_cancelled"
REASON_STORE_UNAVAILABLE: Final[str] = "sweep_store_unavailable"
REASON_TOKEN_REJECTED: Final[str] = "sweep_token_rejected"

_UPLOAD_ID = re.compile(r"^cbt_[0-9A-HJKMNP-TV-Z]{26}$")


def _upload_id(payload: Any, *, keys: frozenset[str]) -> str | None:
    """The batch a payload names, or ``None`` unless the payload is exactly the shape the enqueue writes."""
    if not isinstance(payload, dict) or set(payload) != keys:
        return None
    value = payload.get("upload_id")
    return value if isinstance(value, str) and _UPLOAD_ID.match(value) else None


class BatchDriveHandler:
    """``comparison_batch_drive``: the batch's poll."""

    kind = DRIVE_KIND

    def __init__(self, deps: WorkDependencies, *, lifecycle: BatchLifecycle | None = None) -> None:
        self._sessions: sessionmaker[Session] = deps.session_factory
        self._lifecycle = lifecycle or BatchLifecycle(work=deps.work)

    def run(self, item: WorkItem) -> Outcome:
        upload_id = _upload_id(item.payload, keys=frozenset({"upload_id"}))
        if upload_id is None:
            return Failed(REASON_PAYLOAD_INVALID)
        with session_scope(self._sessions) as session:
            item.require_current(session)
            step = self._lifecycle.drive(session, upload_id)
        if step.done:
            return Completed()
        return Yielded(step.delay_seconds)


class UploadSweepHandler:
    """``upload_abort_sweep``: abort the store's open multipart uploads of a cancelled batch."""

    kind = SWEEP_KIND

    def __init__(self, deps: WorkDependencies) -> None:
        self._sessions: sessionmaker[Session] = deps.session_factory
        self._store = deps.blob_store
        self._uploads = ComparisonUploadRepository()
        self._batches = ComparisonBatchRepository()

    def run(self, item: WorkItem) -> Outcome:
        upload_id = _upload_id(item.payload, keys=frozenset({"upload_id", "reason"}))
        if upload_id is None or item.payload.get("reason") not in SWEEP_REASONS:
            return Failed(REASON_PAYLOAD_INVALID)
        with session_scope(self._sessions) as session:
            item.check_current(session)
            upload = self._uploads.get_upload(session, upload_id)
            if upload is None or upload.state != "cancelled":
                # The database has not decided that the batch is over: nothing may be aborted on its behalf.
                return Failed(REASON_NOT_CANCELLED)
            tokens = self._batches.open_tokens(session, upload_id)
        try:
            report = abort_multipart_sweep(self._store, tokens)  # type: ignore[arg-type]  (the S3 store is a MultipartStaging)
        except StorageError:
            return Failed(REASON_STORE_UNAVAILABLE, retry=True)
        if report.rejected:
            return Failed(REASON_TOKEN_REJECTED)
        return Completed()


def batch_drive_handler(deps: WorkDependencies) -> BatchDriveHandler:
    """Factory for ``HANDLER_FACTORIES``-style registration (the composition root appends it)."""
    return BatchDriveHandler(deps)


def upload_sweep_handler(deps: WorkDependencies) -> UploadSweepHandler:
    return UploadSweepHandler(deps)
