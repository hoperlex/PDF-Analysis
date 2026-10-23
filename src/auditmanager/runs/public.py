"""Cross-context surface of the audit-run boundary."""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.orm import Session

from auditmanager.jobs.public import sweep_stale_temporaries
from auditmanager.runs.carrier import (
    DurableCarrier,
    ReclaimingCarrier,
    RunCarrier,
    run_to_terminal,
)
from auditmanager.runs.reconciliation import reconcile_at_startup
from auditmanager.runs.reference_pipeline import (
    STATE_READY as NORM_REFERENCES_READY,  # NORM-REFS-RUN-01
    STATE_SNAPSHOT_NOT_PINNED as NORM_REFERENCES_SNAPSHOT_NOT_PINNED,
    STATE_TEXT_UNAVAILABLE as NORM_REFERENCES_TEXT_UNAVAILABLE,
    STATE_TOO_MANY_CITATIONS as NORM_REFERENCES_TOO_MANY_CITATIONS,
    STATES as NORM_REFERENCES_STATES,
    ReferenceRunPins,
    RunNormReferences,
    RunReferenceReport,
    SavedRunPageText,
    SavedRunTextReader,
    read_run_norm_references,
    read_run_references,
)
from auditmanager.runs.geometry_crop_item_input import (
    SavedImageCropItemInput,
    load_saved_image_crop_item,
)
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_group import TrustedPackRegistry, get_ar_v3_group, start_ar_v3_group
from auditmanager.shared.errors import ErrorCode


def start_serving_carrier(carrier: RunCarrier) -> None:
    """Start durable dispatch only when a serving application enters its lifespan.

    Constructed applications and direct callers keep their existing inert carrier.
    ``EXECUTION_ROLE=all`` starts the in-process claimant (:class:`DurableCarrier`);
    ``EXECUTION_ROLE=api`` starts only the lease reclaim (:class:`ReclaimingCarrier`).
    Other carrier implementations have no serving scheduler to start.
    """
    if isinstance(carrier, (DurableCarrier, ReclaimingCarrier)):
        # `RUN-ROBUSTNESS-01` (D-170): a serving process that starts is the moment a killed
        # predecessor's temporary PDFs and bundle directories can be reclaimed. Never raises.
        sweep_stale_temporaries()
        carrier.start()


def fail_reclaimed_run(
    session: Session,
    *,
    run_id: str,
    from_state: str,
    interrupted_reason: str,
    terminal_detail: Mapping[str, Any] | None = None,
) -> None:
    """Record the Run terminal chosen after Job recovery fences a lost Attempt.

    The Job boundary decides whether the prior provider effect is ambiguous or the
    Attempt budget is exhausted. The Run boundary owns its declared failed edge and
    terminal reason; both writes remain in the caller's recovery transaction.

    ``terminal_detail`` is what the Job boundary could establish about the loss
    (`RUN-ROBUSTNESS-01`, D-169: the stage a worker was killed in again and again). It is
    screened against the keys ``analysis_failed`` declares safe by the repository.
    """
    RunRepository().terminate(
        session,
        run_id=run_id,
        from_state=from_state,
        to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        terminal_detail=terminal_detail,
        interrupted_reason=interrupted_reason,
    )


__all__ = [
    "TrustedPackRegistry",
    "get_ar_v3_group",
    "start_ar_v3_group",
    "DurableCarrier",
    "NORM_REFERENCES_READY",
    "NORM_REFERENCES_SNAPSHOT_NOT_PINNED",
    "NORM_REFERENCES_STATES",
    "NORM_REFERENCES_TEXT_UNAVAILABLE",
    "NORM_REFERENCES_TOO_MANY_CITATIONS",
    "ReclaimingCarrier",
    "ReferenceRunPins",
    "RunNormReferences",
    "RunReferenceReport",
    "SavedImageCropItemInput",
    "SavedRunPageText",
    "SavedRunTextReader",
    "fail_reclaimed_run",
    "reconcile_at_startup",
    "read_run_norm_references",
    "read_run_references",
    "load_saved_image_crop_item",
    "run_to_terminal",
    "start_serving_carrier",
]
