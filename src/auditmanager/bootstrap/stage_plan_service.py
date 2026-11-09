"""The stage layout, the catalogue and the readiness of a start, as a service: the stub `HOSTS-SEAL-1` ships and `HOSTS-LAYOUT-01` replaces.

``StagePlanService`` is what ``bootstrap/stage_plan_adapter.py`` delegates to. It will hold, over ``stage_layout*`` (migration ``0062``) and
``contracts/analysis/v1/model-catalogue.json``: the layout and its revisions (a pair of the catalogue per cell, the closed list of block schemes,
the kits «Только Claude» and «Только Codex»), the switch and its journal, the freezing of ``audit_run.stage_plan`` at the start of a run
(access: a subscription when an agent with one is on line, else an API key; no substitution mid-run), the consent v2 (the digest of the plan and
the model -> rate digest and access map), and the readiness the one button shows. The adapter parses nothing and decides nothing.

Every method refuses with ``503 dependency_unavailable`` (``dependency`` ``stage_models``) until the lane replaces its body: nothing is read,
written or sent to a model, and there is no fallback (AGENTS section 4).
"""

from __future__ import annotations

from typing import Any, Final, NoReturn

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "StagePlanService"]

DEPENDENCY: Final[str] = "stage_models"


def _not_implemented() -> NoReturn:
    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)


class StagePlanService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def get_layout(self) -> Any:
        _not_implemented()

    def revise_layout(self, *, body: Any, user_uid: str, idempotency_key: str) -> Any:
        _not_implemented()

    def set_layout_enabled(self, *, enabled: bool, user_uid: str, idempotency_key: str) -> Any:
        _not_implemented()

    def list_catalogue(self) -> Any:
        _not_implemented()

    def get_start_readiness(self, *, body: Any) -> Any:
        _not_implemented()
