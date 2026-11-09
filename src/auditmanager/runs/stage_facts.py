"""The facts of a run's stages, read from three places: the stub `HOSTS-SEAL-1` ships and `RUN-STAGES-01` replaces (contract 1.46.0).

``getRunStages`` (``HOSTS-SEAL-2``) answers, per stage of a run, the plan (cells: role, model, effort, limits, server and access) and the fact
(state, first and last call, calls done / failed / retried against the planned coverage, tokens, cost, error code). The facts come from
``stage_result`` for the PC-01 stages, the extended-review artifact (``procedures``, ``phase_coverage``) and the call journal
(``model_call`` and ``provider_call_effect`` by ``stage_key``; a row written before ``0062`` has none, so the value is derived on read or left
empty). This module holds only the name and the refusal until then: nothing is read.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "read_run_stage_facts"]

DEPENDENCY: Final[str] = "run_stage_facts"


def read_run_stage_facts(session: Session, *, run_id: str) -> Any:
    """The stage facts of one run, or a ``503 dependency_unavailable`` while the lane has not written them."""
    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)


