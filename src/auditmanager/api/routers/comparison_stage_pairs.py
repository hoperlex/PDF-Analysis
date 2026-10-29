"""Transport routes for the C3 document-pair and assembly boundary.

The seal supplies typed, module-gated 503 implementations. The pair lane later
replaces this port without changing the addresses or request shapes.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonStagePairPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_stage_pair_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_PAIRS: Final[str] = "/projects/{project_uid}/stage-pairs"
_ASSEMBLIES: Final[str] = "/projects/{project_uid}/stage-assemblies"
_ProjectUid = Annotated[models.ProjectUid, Path()]
_PairId = Annotated[models.StagePairId, Path()]
_AssemblyId = Annotated[models.StageAssemblyId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_stage_pair_routes(router: APIRouter, pairs: ComparisonStagePairPort) -> None:
    @router.get(
        _PAIRS, operation_id="listStagePairs", tags=_TAGS, status_code=200,
        response_model=models.StagePairPage,
        responses={**success(200, "One page of stage pairs for a project."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_pairs(
        project_uid: _ProjectUid, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(pairs.list_pairs(
            project_uid=project_uid, cursor=cursor, limit=limit,
        )))

    @router.get(
        "/stage-pairs/{stage_pair_id}", operation_id="getStagePair", tags=_TAGS,
        status_code=200, response_model=models.StagePair,
        responses={**success(200, "One stage pair by opaque identity."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_stage_pair(stage_pair_id: _PairId) -> WireResponse:
        return json_response(200, _body(pairs.get_pair(pair_id=stage_pair_id)))

    @router.get(
        "/projects/{project_uid}/stage-pair-suggestions",
        operation_id="listStagePairSuggestions", tags=_TAGS, status_code=200,
        response_model=models.StagePairSuggestionPage,
        responses={**success(200, "Deterministic section and designation suggestions; no binding."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_pair_suggestions(
        project_uid: _ProjectUid, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(pairs.list_suggestions(
            project_uid=project_uid, cursor=cursor, limit=limit,
        )))

    @router.post(
        _PAIRS, operation_id="confirmStagePair", tags=_TAGS, status_code=201,
        response_model=models.StagePair,
        responses={**success(201, "The expert-confirmed pair or the recorded keyed replay."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def confirm_stage_pair(
        subject: CurrentSubject, project_uid: _ProjectUid,
        body: models.ConfirmStagePairRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(201, _body(pairs.confirm_pair(
            project_uid=project_uid, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.post(
        _ASSEMBLIES, operation_id="createStageAssembly", tags=_TAGS, status_code=201,
        response_model=models.StageAssembly,
        responses={**success(201, "The Р-side assembly or its recorded keyed replay."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def create_stage_assembly(
        subject: CurrentSubject, project_uid: _ProjectUid,
        body: models.CreateStageAssemblyRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(201, _body(pairs.create_assembly(
            project_uid=project_uid, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.post(
        "/stage-assemblies/{stage_assembly_id}/members",
        operation_id="reviseStageAssembly", tags=_TAGS, status_code=200,
        response_model=models.StageAssembly,
        responses={**success(200, "The assembly after an append-only membership revision."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def revise_stage_assembly(
        subject: CurrentSubject, stage_assembly_id: _AssemblyId,
        body: models.ReviseStageAssemblyRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(pairs.revise_assembly(
            assembly_id=stage_assembly_id, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.post(
        "/stage-pairs/{stage_pair_id}/completeness",
        operation_id="setStagePairCompleteness", tags=_TAGS, status_code=200,
        response_model=models.StagePair,
        responses={**success(200, "The confirmed NEW-side completeness choice."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def set_stage_pair_completeness(
        subject: CurrentSubject, stage_pair_id: _PairId,
        body: models.SetStagePairCompletenessRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(pairs.set_completeness(
            pair_id=stage_pair_id, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))
