"""Providers of a planned run: the stub `HOSTS-SEAL-1` ships and `HOSTS-LAYOUT-01` replaces (ADR-0028 decisions 12, 13 and 17).

A run frozen with a ``stage_plan`` has no connection of its own. ``StagePlanProviders`` is what the database provider source resolves such a run
through: ``binding_for(cell_key)`` returns the adapter of the member the cell was bound to (``audit_run_cell_binding``) and a ``CallBinding``
whose ``expected_model`` is the cell's model, so the identity check (`R-133`) holds per call and a call without a binding is refused.
``EnvironmentProviders`` refuses a planned run with a typed error; ``DatabaseProviders`` resolves it here.

Every method refuses with ``503 dependency_unavailable`` (``dependency`` ``stage_plan_providers``) until the lane replaces it.
"""

from __future__ import annotations

from typing import Any, Final, NoReturn

from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "StagePlanProviders"]

DEPENDENCY: Final[str] = "stage_plan_providers"


def _not_implemented() -> NoReturn:
    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)


class StagePlanProviders:
    def binding_for(self, session: Session, *, run_id: str, cell_key: str) -> Any:
        """The adapter of the member bound to the cell, with the ``CallBinding`` of the cell's model."""
        _not_implemented()
