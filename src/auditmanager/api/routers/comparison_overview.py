"""The overview of a project for «Проекты и этапы» and the «Сравнение» block of «Очередь»,
sealed as stubs (`CMP-SEAL-C1`, ADR-0025 decisions 4, 6 and 23).

``getComparisonOverview`` reads, for every document set of a project, the state of the seven
steps and the next step; ``getComparisonQueueSummary`` reads the comparison work items by state
and kind. Both are read-only, start nothing and are open to any one role (the block is shown to
an administrator). Both answer ``503 dependency_unavailable`` until `CMP-VC-OVERVIEW-01` wires
the port.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import ComparisonOverviewPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models

__all__ = ["build_comparison_overview_routes"]

_TAGS: Final[list[str]] = ["comparison"]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_overview_routes(router: APIRouter, overview: ComparisonOverviewPort) -> None:
    @router.get(
        "/projects/{project_uid}/comparison-overview", operation_id="getComparisonOverview",
        tags=_TAGS, status_code=200, response_model=models.ComparisonOverview,
        responses={**success(200, "The overview of the project's document sets."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_overview(
        project_uid: Annotated[models.ProjectUid, Path()]
    ) -> WireResponse:
        return json_response(200, _body(overview.get_overview(project_uid=project_uid)))

    @router.get(
        "/execution/comparison-queue", operation_id="getComparisonQueueSummary",
        tags=["execution"], status_code=200, response_model=models.ComparisonQueueSummary,
        responses={**success(200, "The comparison work items by state and kind."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def get_comparison_queue_summary() -> WireResponse:
        return json_response(200, _body(overview.get_queue_summary()))
