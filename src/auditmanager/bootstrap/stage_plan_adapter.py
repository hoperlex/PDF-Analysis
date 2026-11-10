"""The adapter of ``StageModelPort`` (`HOSTS-SEAL-1`, ADR-0028): the router's seam to ``StagePlanService``.

Shipped as a stub: every call is delegated to :class:`~auditmanager.bootstrap.stage_plan_service.StagePlanService`, whose bodies refuse with
``503 dependency_unavailable`` until ``HOSTS-LAYOUT-01`` fills them. The integrator wires it with ``build_router(stage_models=
StageModelAdapter(sessions))`` in the composition root.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas import models
from auditmanager.bootstrap.stage_plan_service import StagePlanService

__all__ = ["StageModelAdapter"]


class StageModelAdapter:
    def __init__(self, session_factory: sessionmaker[Session], *, service: StagePlanService | None = None) -> None:
        self._service = service or StagePlanService(session_factory=session_factory)

    def get_layout(self) -> models.StageModelLayout:
        return models.StageModelLayout.model_validate(self._service.get_layout())

    def revise_layout(
        self, *, body: models.ReviseStageModelLayoutRequest, user_uid: str, idempotency_key: str
    ) -> models.StageModelLayout:
        return models.StageModelLayout.model_validate(
            self._service.revise_layout(body=body, user_uid=user_uid, idempotency_key=idempotency_key))

    def set_layout_enabled(
        self, *, body: models.SetStageModelLayoutEnabledRequest, user_uid: str, idempotency_key: str
    ) -> models.StageModelLayout:
        return models.StageModelLayout.model_validate(self._service.set_layout_enabled(
            enabled=body.enabled, user_uid=user_uid, idempotency_key=idempotency_key))

    def list_catalogue(self) -> models.ModelCatalogue:
        return models.ModelCatalogue.model_validate(self._service.list_catalogue())

    def get_start_readiness(self, *, body: models.RunCostEstimateRequest) -> models.RunStartReadiness:
        return models.RunStartReadiness.model_validate(self._service.get_start_readiness(body=body))
