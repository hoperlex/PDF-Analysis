"""Explicit, gated AR v3 beta group operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ArV3GroupPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models


def build_ar_v3_group_routes(router: APIRouter, groups: ArV3GroupPort) -> None:
    @router.post(
        "/ar-v3-beta/groups",
        operation_id="startArV3BetaGroup",
        tags=["runs"],
        status_code=202,
        response_model=models.ArV3BetaGroup,
        responses={
            **success(202, "The six-run group was created or replayed."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
    )
    def start_ar_v3_beta_group(
        body: models.StartArV3BetaGroupRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        group = groups.start_ar_v3_group(
            version_uid=body.version_uid, idempotency_key=idempotency_key,
            relaxed_limits=body.relaxed_limits is True,
        )
        return json_response(202, encode_json(group.model_dump(mode="json")))

    @router.get(
        "/ar-v3-beta/groups/{group_id}",
        operation_id="getArV3BetaGroup",
        tags=["runs"],
        status_code=200,
        response_model=models.ArV3BetaGroup,
        responses={
            **success(200, "The six child Run IDs and their current states."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
    )
    def get_ar_v3_beta_group(
        group_id: Annotated[models.ArV3RunGroupId, Path()],
    ) -> WireResponse:
        group = groups.get_ar_v3_group(group_id=group_id)
        return json_response(200, encode_json(group.model_dump(mode="json")))

    @router.get(
        "/ar-v3-beta/groups/{group_id}/review",
        operation_id="getArV3BetaGroupReview",
        tags=["runs"],
        status_code=200,
        response_model=models.ArV3BetaGroupReview,
        responses={
            **success(200, "The six verified, review-only scope outcomes."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
    )
    def get_ar_v3_beta_group_review(
        group_id: Annotated[models.ArV3RunGroupId, Path()],
    ) -> WireResponse:
        review = groups.get_ar_v3_group_review(group_id=group_id)
        return json_response(200, encode_json(review.model_dump(mode="json")))

    @router.get(
        "/ar-v3-beta/pack",
        operation_id="getArV3BetaPackStatus",
        tags=["runs"],
        status_code=200,
        response_model=models.ArV3BetaPackStatus,
        responses={
            **success(200, "Whether a reviewed pack is installed, and its reviewer attestation."),
            **envelope_responses(401, 403, 500, 503),
        },
    )
    def get_ar_v3_beta_pack_status() -> WireResponse:
        status = groups.get_ar_v3_pack_status()
        # `exclude_unset`: a pack that is not installed omits every property but `state`.
        return json_response(200, encode_json(status.model_dump(mode="json", exclude_unset=True)))
