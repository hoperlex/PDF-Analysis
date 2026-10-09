"""Cross-context surface of the audit-run boundary."""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.runs.carrier import DurableCarrier, RunCarrier
from auditmanager.runs.reconciliation import reconcile_at_startup
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import ErrorCode


def start_serving_carrier(carrier: RunCarrier) -> None:
    """Start durable dispatch only when a serving application enters its lifespan.

    Constructed applications and direct callers keep their existing inert carrier.
    Other carrier implementations have no serving scheduler to start.
    """
    if isinstance(carrier, DurableCarrier):
        carrier.start()


def fail_reclaimed_run(
    session: Session, *, run_id: str, from_state: str, interrupted_reason: str
) -> None:
    """Record the Run terminal chosen after Job recovery fences a lost Attempt.

    The Job boundary decides whether the prior provider effect is ambiguous or the
    Attempt budget is exhausted. The Run boundary owns its declared failed edge and
    terminal reason; both writes remain in the caller's recovery transaction.
    """
    RunRepository().terminate(
        session,
        run_id=run_id,
        from_state=from_state,
        to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        interrupted_reason=interrupted_reason,
    )


__all__ = ["fail_reclaimed_run", "reconcile_at_startup", "start_serving_carrier"]
