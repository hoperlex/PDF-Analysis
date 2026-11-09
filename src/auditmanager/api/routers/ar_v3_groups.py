"""Explicit, gated AR v3 beta group operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ArV3GroupPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject


def build_ar_v3_group_routes(router: APIRouter, groups: ArV3GroupPort) -> None:
    @router.post(
        "/ar-v3-beta/groups/cost-estimate", operation_id="estimateArV3GroupCost", tags=["runs"], status_code=200,
        response_model=models.RunCostEstimate,
        description=(
            "`AR-V3-OPT-IN`: the price of the six checks of one AR v3 beta group, asked before startArV3BetaGroup. While a "
            "reviewed pack is installed and the deployment has not allowed starts (`AR_V3_BETA_START_ALLOWED`, off by "
            "default; getArV3BetaPackStatus.start_allowed says which), the answer is `409 conflict` with `conflict_reason` "
            "`ar_v3_start_not_enabled` and no figure, as the start's is. With no pack installed the answer is the "
            "`503 dependency_unavailable` it always was."
        ),
        responses={**success(200, "Pinned model cost estimate for all six AR checks."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def estimate_ar_v3_group_cost(body: models.ArV3GroupCostEstimateRequest) -> WireResponse:
        estimate = groups.estimate_ar_v3_group_cost(version_uid=body.version_uid, relaxed_limits=body.relaxed_limits is True)
        return json_response(200, encode_json(estimate.model_dump(mode="json")))

    @router.post(
        "/ar-v3-beta/groups",
        operation_id="startArV3BetaGroup",
        tags=["runs"],
        status_code=202,
        response_model=models.ArV3BetaGroup,
        description=(
            "`AR-V3-OPT-IN`: AR v3 is an opt-in analysis and its own operation; `startRun` and `reauditRun` never reach it, "
            "and no default, preset or repeat starts it. While a reviewed pack is installed and the deployment has not "
            "allowed starts (`AR_V3_BETA_START_ALLOWED`, off by default), the answer is `409 conflict` with "
            "`conflict_reason` `ar_v3_start_not_enabled` and nothing is written (no command, run, group or job). A repeat "
            "of an accepted key replays the group it created whether or not starts are still allowed, and runs already "
            "accepted finish when the allowance is withdrawn. Each member records the account that started it."
        ),
        responses={
            **success(202, "The six-run group was created or replayed."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
    )
    def start_ar_v3_beta_group(
        body: models.StartArV3BetaGroupRequest,
        idempotency_key: RequiredIdempotencyKey,
        subject: CurrentSubject,
    ) -> WireResponse:
        group = groups.start_ar_v3_group(
            version_uid=body.version_uid, idempotency_key=idempotency_key,
            relaxed_limits=body.relaxed_limits is True,
            **({"cost_consent": body.cost_consent.model_dump(mode="json"), "cost_actor_uid": subject.user_uid}
               if body.cost_consent is not None else {}),
            # `R-151v`: each member records who started it, as the ordinary start does.
            started_by_user_uid=subject.user_uid,
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
        description=(
            "`AR-V3-OPT-IN`: when the pack is installed, `start_allowed` says whether this deployment allows a start of "
            "an AR v3 group now (`AR_V3_BETA_START_ALLOWED`). The pack is the capability to execute, read and review; "
            "`start_allowed` is the separate permission to start. A screen offers the choice of AR v3 only when the pack "
            "is installed and `start_allowed` is true, and never makes it the default."
        ),
        responses={
            **success(200, "Whether a reviewed pack is installed, and its reviewer attestation."),
            **envelope_responses(401, 403, 500, 503),
        },
    )
    def get_ar_v3_beta_pack_status() -> WireResponse:
        status = groups.get_ar_v3_pack_status()
        # `exclude_unset`: a pack that is not installed omits every property but `state`.
        return json_response(200, encode_json(status.model_dump(mode="json", exclude_unset=True)))
