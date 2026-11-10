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


def fail_run_without_executor(session: Session, *, run_id: str, from_state: str) -> None:
    """End a Run admitted on a group that no member could ever take: ``failed``, ``dependency_unavailable``,
    ``dependency: no_executor_online`` (`EXEC2-GROUP-RUN-01`, ADR-0026 decision 15).

    The Job boundary decides that the wait is over (every member offline for longer than allowed) and has closed the
    Job; the Run boundary owns its declared failed edge and its terminal reason, and writes both in the caller's
    transaction, clearing the wait the Run no longer has. ``no_executor_online`` is the controlled word a pull task nobody
    claimed already carries, so a reader sees one reason for "no runner took the work". No model was called."""
    repository = RunRepository()
    repository.terminate(
        session,
        run_id=run_id,
        from_state=from_state,
        to_state="failed",
        terminal_reason=ErrorCode.DEPENDENCY_UNAVAILABLE.value,
        terminal_detail={"dependency": "no_executor_online"},
    )
    repository.clear_wait(session, run_id=run_id)


def fail_run_consent_lapsed(session: Session, *, run_id: str, from_state: str) -> None:
    """End a Run admitted on a group whose cost consent no longer holds: ``failed``, ``analysis_input_invalid``,
    ``stage_id: text_analysis``, ``reason: cost_estimate_binding_changed`` (`EXEC2-GROUP-RUN-01`, ADR-0026 decision 14).

    The Run path has one refusal for an approved estimate that no longer binds the work -- the one
    ``analysis.text.cost.require_approved_model`` and ``runs.cost_policy`` raise before any call -- and this is that refusal
    written as the terminal of a Run that never reached a call. A Run has no operation that renews its consent, so the
    Job boundary (which saw the consent lapse and has closed the queued Job) ends it, and the Run boundary writes its
    declared failed edge, the reason and the detail in the caller's transaction, clearing the wait the Run no longer has.
    No model was called and nothing was charged; the user starts again and consents afresh."""
    repository = RunRepository()
    repository.terminate(
        session,
        run_id=run_id,
        from_state=from_state,
        to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_INPUT_INVALID.value,
        terminal_detail={"stage_id": "text_analysis", "reason": "cost_estimate_binding_changed"},
    )
    repository.clear_wait(session, run_id=run_id)


from .cost_policy import RunCostPolicy, group_consent_holds, read_run_cost_policy
from .stage_layout import (  # HOSTS-LAYOUT-01; the comparison cells are HOSTS-CMP-01
    BLOCK_SCHEMES,
    COMPARISON_KINDS,
    FrozenStagePlan,
    KIT_CUSTOM,
    KIT_LABELS,
    KITS,
    PHASE_LABELS,
    PHASE_ROWS,
    PRESET_CELLS,
    ROW_LABELS,
    STAGE_ROWS,
    cells_to_wire,
    comparison_cells_to_wire,
    kit_of,
    parse_plan,
    preset_cells,
    require_valid_comparison_cells,
    require_valid_layout,
    row_of_phase,
    rows_in_use,
    validate_cells,
)
from .stage_layout_store import LayoutRevisionRow, SqlStageLayoutStore, StageLayoutStore, SwitchEventRow
from .stage_plan import (
    ModelAvailability,
    ModelAvailabilityPort,
    PROVIDER_SOURCE_DATABASE,
    StagePlanDraft,
    StagePlanFreezer,
    call_journal_columns,
    cell_binding,
    estimate_for_request,
    no_layout_revision,
    provider_source_not_database,
    start_readiness,
)

__all__ = [
    "RunCostPolicy",
    "fail_run_consent_lapsed",
    "fail_run_without_executor",
    "group_consent_holds",
    "read_run_cost_policy",
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
    "BLOCK_SCHEMES",
    "COMPARISON_KINDS",
    "FrozenStagePlan",
    "KITS",
    "KIT_CUSTOM",
    "KIT_LABELS",
    "LayoutRevisionRow",
    "ModelAvailability",
    "ModelAvailabilityPort",
    "PHASE_LABELS",
    "PHASE_ROWS",
    "PRESET_CELLS",
    "PROVIDER_SOURCE_DATABASE",
    "ROW_LABELS",
    "STAGE_ROWS",
    "SqlStageLayoutStore",
    "StageLayoutStore",
    "StagePlanDraft",
    "StagePlanFreezer",
    "SwitchEventRow",
    "cells_to_wire",
    "comparison_cells_to_wire",
    "kit_of",
    "no_layout_revision",
    "parse_plan",
    "preset_cells",
    "provider_source_not_database",
    "require_valid_comparison_cells",
    "require_valid_layout",
    "row_of_phase",
    "rows_in_use",
    "validate_cells",
    "call_journal_columns",
    "cell_binding",
    "estimate_for_request",
    "start_readiness",
]


def read_extended_review(sessions, blob_store, run_id: str):
    from auditmanager.runs.extended_review import read_extended_review as read
    return read(sessions, blob_store, run_id)
