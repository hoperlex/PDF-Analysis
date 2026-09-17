"""``createProject`` and ``listProjects``."""

from __future__ import annotations

from fastapi import APIRouter

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ProjectPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate
from auditmanager.api.schemas.projects import project_body

__all__ = ["build_project_routes"]


def build_project_routes(router: APIRouter, projects: ProjectPort) -> None:

    @router.post(
        "/projects",
        operation_id="createProject",
        tags=["projects"],
        status_code=201,
        response_model=models.Project,
        responses={
            **success(
                201,
                "The project was created, or the recorded outcome of an identical "
                "earlier request was replayed.",
            ),
            **envelope_responses(401, 403, 409, 422, 500, 503),
        },
    )
    def create_project(
        body: models.CreateProjectRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = projects.create_project(name=body.name, idempotency_key=idempotency_key)
        # 201 whether this created the project or replayed the recorded outcome of an
        # identical earlier request: the frozen document gives both answers one status.
        return json_response(201, encode_json(project_body(view)))

    @router.get(
        "/projects",
        operation_id="listProjects",
        tags=["projects"],
        status_code=200,
        response_model=models.ProjectPage,
        responses={
            **success(200, "One page of projects, newest first."),
            **envelope_responses(401, 403, 422, 500, 503),
        },
    )
    def list_projects(
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        rows = projects.list_projects()
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_project_sort_key)
        body = page_body([project_body(view) for view in page.items], page.next_cursor)
        return json_response(200, encode_json(body))



def _project_sort_key(view: object) -> tuple[str, ...]:
    """The opaque identity, which is also the listing's total order."""
    return (getattr(view, "project_uid"),)
