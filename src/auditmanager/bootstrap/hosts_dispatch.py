"""Dispatch of a planned run and the claim of a host token: the stub `HOSTS-SEAL-1` ships and `HOSTS-BACKEND-01` replaces (ADR-0028).

Two seams the lane fills; both refuse until then with ``503 dependency_unavailable`` (``dependency`` ``executor_host_dispatch``), calling
nothing and writing nothing.

``bind_planned_run``
    A run frozen with a ``stage_plan`` is ``pending``. At dispatch **every cell** of its plan is bound, in one transaction, each to a member of
    the system group of its (model, access): rows of ``audit_run_cell_binding`` (written once; the trigger accepts only a system member that
    pins the cell's model), then ``binding_state`` ``pending`` -> ``bound``, which the database allows only when every cell has its row. If one
    cell has no free available member the run stays ``pending`` with ``wait_reason`` ``model_unavailable`` and the exact cells named; nothing
    has run, nothing is lost. The unit of capacity is the pair (run, ``capacity_pool`` = host and provider); the advisory lock is taken by pool
    in the four places the plan names (claim, hint, comparison mirror, binding).
``claim_for_host_token``
    A host token claims the tasks of the system connections of its host: the task carries provider, access, model, effort, limits and cell key
    (all seven or none); the agent refuses a model it does not report as verified.
"""

from __future__ import annotations

from typing import Any, Final, NoReturn

from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "bind_planned_run", "claim_for_host_token"]

DEPENDENCY: Final[str] = "executor_host_dispatch"


def _not_implemented() -> NoReturn:
    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)


def bind_planned_run(session: Session, *, run_id: str) -> Any:
    """Bind every cell of the run's frozen stage plan, or leave it ``pending`` naming the cells that wait."""
    _not_implemented()


def claim_for_host_token(session: Session, *, token_id: str, runner_instance_id: str | None, wait_seconds: int) -> Any:
    """Hand a host token the next task of any system connection of its host that it may run, or none."""
    _not_implemented()
