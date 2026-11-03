"""Executor groups and the routing rule of a work kind (`EXEC2-GROUP-STORE-01`, ADR-0026 decisions 10, 11 and 14).

Ten operations of contract 1.16.0:

====================================  ======================================================================
``listExecutorGroups``                any role; every group with its current revision
``createExecutorGroup``               an administrator; a group and its first revision
``getExecutorGroup``                  any role; one group and every revision, newest first
``reviseExecutorGroup``               an administrator; an immutable revision, full settings
``archiveExecutorGroup``              an administrator; one-way, not deletion
``getExecutorGroupCapacity``          any role; the current revision as dispatch would see it now
``listExecutorRoutingRules``          any role; the current rule of each work kind, and the routing mode
``setExecutorRoutingRule``            an administrator; point a work kind at a group revision
``previewExecutorRouting``            an administrator; the cut-over proposal, writing nothing (`EXEC2-CUTOVER-01`)
``setExecutorRoutingMode``            an administrator; the cut-over to ``rules`` or the rollback to ``legacy``
                                      (`EXEC2-CUTOVER-01`)
====================================  ======================================================================

Who may call what is decided by the authorization seam (``api/security.py``); a router decides nothing about roles. The
four group-store reads take no subject; the preview and the mode change pass the caller, whose role set the command
re-reads in its own transaction.

**Declared, and answerable only with a port.** ``build_router`` declares these routes whatever the port, as it does
for every operation: the served document is a function of the declarations. A router built with no port answers none.

Optional properties are absent, never null: every body is dumped with ``exclude_unset``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import WithJsonSchema

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ExecutorGroupPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_executor_group_routes"]

_TAGS = ["execution"]

#: ``work_kind`` is declared with the contract's ``ExecutorWorkKind`` schema and **not enforced by the framework**, for
#: the reason ``AgentPackageVersionParam`` is not: a constrained path parameter is a refusable one, and a path value the
#: framework cannot parse is ``404`` on this surface. This route's contract is different -- a work kind the enumeration
#: does not name is ``422 validation_failed`` (``field`` ``work_kind``, ``constraint`` ``enum``) -- so the shape is
#: checked by the module that owns the enumeration (``executors.groups.refuse_work_kind``), after the role check.
WorkKindParam = Annotated[
    str,
    WithJsonSchema({"$ref": "#/components/schemas/ExecutorWorkKind"}),
    Path(),
]


def build_executor_group_routes(router: APIRouter, groups: ExecutorGroupPort) -> None:
    @router.get(
        "/executor-groups", operation_id="listExecutorGroups", tags=_TAGS,
        response_model=models.ExecutorGroupList,
        responses={**success(200, "Every group, each with its current revision and the work kinds "
                                  "whose rule names it. Archived groups come last."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def list_executor_groups() -> WireResponse:
        answer = groups.list_groups()
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-groups", operation_id="createExecutorGroup", tags=_TAGS, status_code=201,
        response_model=models.ExecutorGroup,
        responses={**success(201, "The group with its first revision, or the recorded outcome of an "
                                  "identical earlier request."),
                   **envelope_responses(401, 403, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def create_executor_group(
        subject: CurrentSubject, body: models.CreateExecutorGroupRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = groups.create_group(
            body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/executor-groups/{group_id}", operation_id="getExecutorGroup", tags=_TAGS,
        response_model=models.ExecutorGroupDetail,
        responses={**success(200, "The group and its revisions, newest first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def get_executor_group(group_id: Annotated[models.ExecutorGroupId, Path()]) -> WireResponse:
        view = groups.get_group(group_id=group_id)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-groups/{group_id}/revisions", operation_id="reviseExecutorGroup", tags=_TAGS,
        status_code=201, response_model=models.ExecutorGroup,
        responses={**success(201, "The group with the new revision as its current one, or the "
                                  "recorded outcome of an identical earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def revise_executor_group(
        subject: CurrentSubject, group_id: Annotated[models.ExecutorGroupId, Path()],
        body: models.ReviseExecutorGroupRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = groups.revise_group(
            group_id=group_id, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key)
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-groups/{group_id}/archive", operation_id="archiveExecutorGroup", tags=_TAGS,
        response_model=models.ExecutorGroup,
        responses={**success(200, "The archived group. A group a rule still names is a conflict; "
                                  "an archived group answers as it stands."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def archive_executor_group(
        subject: CurrentSubject, group_id: Annotated[models.ExecutorGroupId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = groups.archive_group(
            group_id=group_id, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/executor-groups/{group_id}/capacity", operation_id="getExecutorGroupCapacity",
        tags=_TAGS, response_model=models.ExecutorGroupCapacity,
        responses={**success(200, "The derived capacity: per member its snapshot, occupancy and "
                                  "eligibility, and the group's capacity, units in use and waiting "
                                  "work."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def get_executor_group_capacity(
        group_id: Annotated[models.ExecutorGroupId, Path()],
    ) -> WireResponse:
        view = groups.get_capacity(group_id=group_id)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/executor-routing-rules", operation_id="listExecutorRoutingRules", tags=_TAGS,
        response_model=models.ExecutorRoutingRuleList,
        responses={**success(200, "The current rule of each work kind that has one, and the "
                                  "routing mode (legacy while the journal is empty)."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def list_executor_routing_rules() -> WireResponse:
        answer = groups.list_rules()
        return json_response(200, encode_json(answer.model_dump(mode="json", exclude_unset=True)))

    @router.put(
        "/executor-routing-rules/{work_kind}", operation_id="setExecutorRoutingRule", tags=_TAGS,
        response_model=models.ExecutorRoutingRule,
        responses={**success(200, "The rule as it now stands."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def set_executor_routing_rule(
        subject: CurrentSubject, work_kind: WorkKindParam,
        body: models.SetExecutorRoutingRuleRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = groups.set_rule(
            work_kind=work_kind, group_revision_id=body.group_revision_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    # EXEC2-CUTOVER-01 (ADR-0026 decision 17) ----------------------------------------------------------------

    @router.get(
        "/executor-routing/preview", operation_id="previewExecutorRouting", tags=_TAGS,
        response_model=models.ExecutorRoutingPreview,
        responses={**success(200, "The proposal: per work kind a one-member group of the primary's current "
                                  "revision, a standby shown and never converted, an incompatible route "
                                  "flagged, and the digest that binds them."),
                   **envelope_responses(401, 403, 500, 503)},
    )
    def preview_executor_routing(subject: CurrentSubject) -> WireResponse:
        view = groups.preview_routing(user_uid=subject.user_uid)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-routing/mode", operation_id="setExecutorRoutingMode", tags=_TAGS,
        response_model=models.ExecutorRoutingModeResult,
        responses={**success(200, "The mode as it now stands, the groups the change created and the rules "
                                  "now current."),
                   **envelope_responses(401, 403, 409, 422, 500, 503,
                                        descriptions={409: STATE_CONFLICT_DESCRIPTION})},
    )
    def set_executor_routing_mode(
        subject: CurrentSubject, body: models.SetExecutorRoutingModeRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = groups.set_routing_mode(
            body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))
