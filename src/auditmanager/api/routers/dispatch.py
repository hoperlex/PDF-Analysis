"""«Диспетчер» (`W61-DISPATCHER-01`): work assignments and their history.

Four operations under ``/assignments`` (tag ``dispatch``). The seam admits ``admin`` to
``createAssignment`` and any one role to the other three
(:data:`~auditmanager.api.security.OPERATION_ROLES`); every finer rule is the dispatch
context's, read in the command's own transaction -- who may make which move (the current
assignee, holding ``expert``, starts, completes and returns; an administrator reassigns and
cancels), what an expert may read (only the assignments currently given to them; anything
else is ``not_found``), the transition table and the exact-repeat rule. The acting account
is the verified subject, never a body field. This module parses, calls one port method and
renders.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query
from pydantic import BeforeValidator, WithJsonSchema

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.ports import DispatchPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.security import CurrentSubject

__all__ = ["build_dispatch_routes"]

AssignmentUidPath = Annotated[models.AssignmentUid, Path()]


def _absent(value: Any) -> Any:
    """An empty query value is the absent parameter, as for every other filter."""
    return None if value == "" else value


def _absent_flag(value: Any) -> Any:
    return False if value == "" else value


MineParam = Annotated[bool, BeforeValidator(_absent_flag), Query()]
StatusFilterParam = Annotated[
    models.AssignmentStatus | None,
    BeforeValidator(_absent),
    WithJsonSchema({"$ref": "#/components/schemas/AssignmentStatus"}),
    Query(json_schema_extra=optional_property),
]
ProjectFilterParam = Annotated[
    models.ProjectUid | None,
    BeforeValidator(_absent),
    WithJsonSchema({"$ref": "#/components/schemas/ProjectUid"}),
    Query(json_schema_extra=optional_property),
]

_CONFLICT = {409: STATE_CONFLICT_DESCRIPTION}


def _sort_key(view: models.Assignment) -> tuple[str, str]:
    return (view.created_at.isoformat(), view.assignment_uid)


def build_dispatch_routes(router: APIRouter, dispatch: DispatchPort) -> None:
    @router.post(
        "/assignments",
        operation_id="createAssignment",
        tags=["dispatch"],
        status_code=200,
        response_model=models.Assignment,
        responses={
            **success(200, "The assignment, new or an exact repeat of an open one."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions=_CONFLICT),
        },
        summary="Assign a project, or one document of it, to an expert.",
        description=(
            "Requires `admin`. Gives the named project, or one document of it (`document_uid`, "
            "which must belong to the project, otherwise `not_found`), to an active account "
            "holding `expert` (otherwise `validation_failed`, `constraint: "
            "active_expert_required`), with an optional note. The assignment starts "
            "`assigned` with its `assigned` event. One open assignment per scope: an exact "
            "repeat (same assignee and note) answers the open one, and any other creation "
            "there is `conflict` with `conflict_reason: assignment_open` -- reassign or cancel "
            "that one instead. No `Idempotency-Key`: the open-scope rule is what makes a "
            "repeat safe."
        ),
    )
    def create_assignment(
        subject: CurrentSubject, body: models.CreateAssignmentRequest
    ) -> WireResponse:
        view = dispatch.create_assignment(
            project_uid=body.project_uid,
            document_uid=body.document_uid,
            assignee_user_uid=body.assignee_user_uid,
            note=body.note,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(view.model_dump(mode="json")))

    @router.get(
        "/assignments",
        operation_id="listAssignments",
        tags=["dispatch"],
        status_code=200,
        response_model=models.AssignmentPage,
        responses={
            **success(200, "One page of the assignments the caller may read, newest first."),
            **envelope_responses(401, 403, 422, 500, 503),
        },
        summary="List assignments.",
        description=(
            "Any one role. An administrator reads every assignment (`mine=true` narrows to the "
            "ones currently given to them); an expert reads only the assignments currently "
            "given to them, whatever `mine` says. `status` and `project_uid` narrow the list; "
            "newest first, ordered by `(created_at, assignment_uid)`."
        ),
    )
    def list_assignments(
        subject: CurrentSubject,
        mine: MineParam = False,
        status: StatusFilterParam = None,
        project_uid: ProjectFilterParam = None,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        rows = dispatch.list_assignments(
            user_uid=subject.user_uid,
            mine=mine,
            status=None if status is None else status.value,
            project_uid=project_uid,
        )
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_sort_key)
        body = page_body([view.model_dump(mode="json") for view in page.items], page.next_cursor)
        return json_response(200, encode_json(body))

    @router.get(
        "/assignments/{assignment_uid}",
        operation_id="getAssignment",
        tags=["dispatch"],
        status_code=200,
        response_model=models.AssignmentDetail,
        responses={
            **success(200, "The assignment and its whole history, oldest event first."),
            # No 422: a path identity and nothing else, and a malformed path identity is
            # ``404 not_found`` by this surface's design (``api/app.py``).
            **envelope_responses(401, 403, 404, 500, 503),
        },
        summary="Read one assignment with its history.",
        description=(
            "Any one role. The assignment and every event of its append-only history, oldest "
            "first, each with its actor. An assignment the caller may not read -- an expert "
            "reading one that is not currently theirs -- is `not_found`."
        ),
    )
    def get_assignment(subject: CurrentSubject, assignment_uid: AssignmentUidPath) -> WireResponse:
        detail = dispatch.get_assignment(assignment_uid=assignment_uid, user_uid=subject.user_uid)
        return json_response(200, encode_json(detail.model_dump(mode="json")))

    @router.post(
        "/assignments/{assignment_uid}/transitions",
        operation_id="transitionAssignment",
        tags=["dispatch"],
        status_code=200,
        response_model=models.Assignment,
        responses={
            **success(200, "The assignment after the move, or unchanged for an exact repeat."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions=_CONFLICT),
        },
        summary="Move an assignment: start, complete, return, reassign or cancel it.",
        description=(
            "Appends one event. `started`, `completed` and `returned` (with a `reason`) are the "
            "current assignee's, holding `expert` (an administrator who is not the assignee is "
            "`permission_denied`, `required_capability: assignment:assignee`); `reassigned` "
            "(with `new_assignee_user_uid`, an active expert) and `cancelled` (optional "
            "`reason`) are an administrator's. A request equal to the latest event answers the "
            "assignment unchanged; any other move the `work_assignment` machine does not declare "
            "is `state_transition_not_allowed`. An expert addressing an assignment that is not "
            "currently theirs gets `not_found`."
        ),
    )
    def transition_assignment(
        subject: CurrentSubject,
        assignment_uid: AssignmentUidPath,
        body: models.TransitionAssignmentRequest,
    ) -> WireResponse:
        view = dispatch.transition_assignment(
            assignment_uid=assignment_uid,
            kind=body.kind.value,
            reason=body.reason,
            new_assignee_user_uid=body.new_assignee_user_uid,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(view.model_dump(mode="json")))
