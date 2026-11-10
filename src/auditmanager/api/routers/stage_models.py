"""The models of the analysis stages (`HOSTS-SEAL-1`, ADR-0028, contract 1.45.0): five routes.

====================================  =====================================================================================
``getStageModelLayout``               ``expert`` or ``admin``; the layout in force, its history and the switch (read only for an expert)
``reviseStageModelLayout``            ``admin``, keyed; a new immutable revision of the layout
``setStageModelLayoutEnabled``        ``admin``, keyed; the switch «Модели по этапам: включены», journalled
``listModelCatalogue``                ``expert`` or ``admin``; the models, efforts and accepted reported strings the layout may name
``getRunStartReadiness``              ``expert`` or ``admin``; what the one button «Запустить» would do, writing nothing
====================================  =====================================================================================

The viewer («Наблюдатель», `R-150w`) is denied every one of them. A router decides nothing about roles (``api/security.py``) and nothing
about the layout: the plan a run freezes, the availability of a model and the estimate are ``HOSTS-LAYOUT-01``'s.

**Declared, and answerable only with a port.** ``build_router`` declares these routes whatever the port; a router built with no port
answers none (``503 dependency_unavailable``).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from auditmanager.api.routers.declarations import STATE_CONFLICT_DESCRIPTION, envelope_responses, success
from auditmanager.api.routers.hosts_ports import StageModelPort
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_stage_model_routes"]

_TAGS = ["execution"]


def _body(view: BaseModel) -> bytes:
    return encode_json(view.model_dump(mode="json", exclude_unset=True))


def build_stage_model_routes(router: APIRouter, stage_models: StageModelPort) -> None:
    @router.get(
        "/model-layout", operation_id="getStageModelLayout", tags=_TAGS,
        response_model=models.StageModelLayout,
        responses={**success(200, "The layout in force, its history and the switch."), **envelope_responses(401, 403, 500, 503)},
        description=(
            "`HOSTS-SEAL-1` (ADR-0028): the layout of models over the analysis stages -- for each row (text, blocks, cross-check, norms, "
            "critic, refinement) and role the model and the effort (no answer limit and no timeout: `LIMITS-01`) -- the revision in force, the revisions "
            "newest first, the switch and its journal, and the cells whose model no server can serve now. An expert reads it; only an "
            "administrator changes it. `role:admin|expert`; the viewer is denied."
        ),
    )
    def get_stage_model_layout() -> WireResponse:
        return json_response(200, _body(stage_models.get_layout()))

    @router.post(
        "/model-layout/revisions", operation_id="reviseStageModelLayout", tags=_TAGS, status_code=201,
        response_model=models.StageModelLayout,
        responses={**success(201, "The layout with the new revision as its current one, or the recorded outcome of an identical earlier "
                                  "request."),
                   **envelope_responses(401, 403, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1`: save a new immutable revision of the layout (author and time are kept). Every cell must be a pair of "
            "`listModelCatalogue` (model and effort); the blocks row is chosen from the closed list of schemes, never leg by leg; a cell "
            "key repeated or missing is `422 validation_failed`. A revision changes nothing for runs already started: they froze their "
            "plan. `role:admin`, `Idempotency-Key` required."
        ),
    )
    def revise_stage_model_layout(
        subject: CurrentSubject, body: models.ReviseStageModelLayoutRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = stage_models.revise_layout(body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(201, _body(view))

    @router.put(
        "/model-layout/enabled", operation_id="setStageModelLayoutEnabled", tags=_TAGS,
        response_model=models.StageModelLayout,
        responses={**success(200, "The layout with the switch as it now stands."),
                   **envelope_responses(401, 403, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1`: the switch «Модели по этапам: включены». On, runs started from now on take the layout; off, they follow the "
            "route as before. It needs a revision (`409 conflict` with `conflict_reason` `no_layout_revision`) and the database provider "
            "source (`409 conflict` with `conflict_reason` `provider_source_not_database`). Read only at the start of a run, so switching "
            "off breaks no run in progress. Each change is an append-only event with its author. `role:admin`, `Idempotency-Key` required."
        ),
    )
    def set_stage_model_layout_enabled(
        subject: CurrentSubject, body: models.SetStageModelLayoutEnabledRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = stage_models.set_layout_enabled(body=body, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, _body(view))

    @router.get(
        "/model-catalogue", operation_id="listModelCatalogue", tags=_TAGS,
        response_model=models.ModelCatalogue,
        responses={**success(200, "The models the layout may name."), **envelope_responses(401, 403, 500, 503)},
        description=(
            "`HOSTS-SEAL-1`: the catalogue of `contracts/analysis/v1/model-catalogue.json` -- the pins of the provider lock the layout offers, "
            "with the providers and accesses that can serve each, the efforts that may be asked for and the exact strings an answer may "
            "report as its model. A Haiku, an effort above `high` and `low` for Opus are never offered. `role:admin|expert`."
        ),
    )
    def list_model_catalogue() -> WireResponse:
        return json_response(200, _body(stage_models.list_catalogue()))

    @router.post(
        "/runs/start-readiness", operation_id="getRunStartReadiness", tags=_TAGS,
        response_model=models.RunStartReadiness,
        responses={**success(200, "The route, the cells with their access, whether the start is possible and the digest to confirm."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`HOSTS-SEAL-1` (ADR-0028): what the one button «Запустить» would do for this version, writing nothing and calling no model. "
            "A read by POST like `estimateRunCost`, with the same body. With the layout off the route is `legacy` and the answer is the "
            "estimate as before. With it on: the plan a start would freeze, every cell with the access it would run with (a subscription "
            "when an agent with one is on line, else an API key) and the reasons it cannot be served, the total access (`subscription`, "
            "`api` or `mixed`), the digest and amount of the estimate and, when every cell is on a subscription, an estimate of 0 whose "
            "confirmation is the press of the button. `ready` is false while any cell has no server. The explicit executor selectors of "
            "the body are `422 validation_failed` while the layout is on. `role:admin|expert`."
        ),
    )
    def get_run_start_readiness(body: models.RunCostEstimateRequest) -> WireResponse:
        return json_response(200, _body(stage_models.get_start_readiness(body=body)))
