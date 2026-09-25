"""``getDashboardSummary``. `R-44`.

No path and no query parameter -- see ``DashboardPort`` for why. Its own tag, because it
does not belong to any one of ``projects``, ``documents``, ``runs``, ``findings`` or
``decisions``: it reads across all of them.
"""

from __future__ import annotations

from fastapi import APIRouter

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import DashboardPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.dashboard import dashboard_summary_body

__all__ = ["build_dashboard_routes"]


def build_dashboard_routes(router: APIRouter, dashboard: DashboardPort) -> None:

    @router.get(
        "/dashboard",
        operation_id="getDashboardSummary",
        tags=["dashboard"],
        status_code=200,
        response_model=models.DashboardSummary,
        responses={
            **success(
                200,
                "Documents per project, findings by verdict, run activity and spend, "
                "and the per-section breakdown -- one read, computed over the whole "
                "deployment.",
            ),
            **envelope_responses(401, 403, 500, 503),
        },
    )
    def get_dashboard_summary() -> WireResponse:
        view = dashboard.get_summary()
        return json_response(200, encode_json(dashboard_summary_body(view)))
