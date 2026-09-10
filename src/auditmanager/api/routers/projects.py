"""``createProject`` and ``listProjects``."""

from __future__ import annotations

import json
from typing import Sequence

from auditmanager.api.routers.errors import decode_json_object
from auditmanager.api.routers.http import Request, Response, Route, json_response
from auditmanager.api.routers.idempotency import require_idempotency_key
from auditmanager.api.routers.ports import ProjectPort
from auditmanager.api.schemas.common import page_body, paginate, parse_limit
from auditmanager.api.schemas.projects import parse_create_project_request, project_body

__all__ = ["build_project_routes"]


def build_project_routes(projects: ProjectPort) -> Sequence[Route]:
    def create_project(request: Request) -> Response:
        key = require_idempotency_key(request)
        name = parse_create_project_request(decode_json_object(request.body))
        view = projects.create_project(name=name, idempotency_key=key)
        # 201 whether this created the project or replayed the recorded outcome of an
        # identical earlier request: the frozen document gives both answers one status.
        return json_response(201, _encode(project_body(view)))

    def list_projects(request: Request) -> Response:
        limit = parse_limit(request.query_one("limit"))
        cursor = request.query_one("cursor")
        rows = projects.list_projects()
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_project_sort_key)
        body = page_body([project_body(view) for view in page.items], page.next_cursor)
        return json_response(200, _encode(body))

    return (
        Route("createProject", "POST", "/projects", create_project),
        Route("listProjects", "GET", "/projects", list_projects),
    )


def _project_sort_key(view: object) -> tuple[str, ...]:
    """The opaque identity, which is also the listing's total order."""
    return (getattr(view, "project_uid"),)


def _encode(body: object) -> bytes:
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
