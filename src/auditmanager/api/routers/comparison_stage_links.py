"""C3 sheet passports and append-only stage link map revisions."""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonStageLinkPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_stage_link_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_PAIR: Final[str] = "/stage-pairs/{stage_pair_id}"
_MAP: Final[str] = f"{_PAIR}/sheet-map"
_PairId = Annotated[models.StagePairId, Path()]
_RevisionId = Annotated[models.StageLinkRevisionId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_stage_link_routes(router: APIRouter, links: ComparisonStageLinkPort) -> None:
    @router.get(
        f"{_PAIR}/sheet-passports", operation_id="listStageSheetPassports", tags=_TAGS,
        status_code=200, response_model=models.StageSheetPassportPage,
        responses={**success(200, "One page of sheet passports from the pair's versions."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_sheet_passports(
        stage_pair_id: _PairId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(links.list_passports(
            pair_id=stage_pair_id, cursor=cursor, limit=limit,
        )))

    @router.get(
        f"{_PAIR}/sheet-suggestions", operation_id="listStageSheetSuggestions",
        tags=_TAGS, status_code=200, response_model=models.StageSheetSuggestionPage,
        responses={**success(200, "Deterministic, non-binding sheet suggestions."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_sheet_suggestions(
        stage_pair_id: _PairId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(links.list_suggestions(
            pair_id=stage_pair_id, cursor=cursor, limit=limit,
        )))

    @router.get(
        _MAP, operation_id="getStageSheetMap", tags=_TAGS, status_code=200,
        response_model=models.StageLinkRevision,
        responses={**success(200, "The current full sheet map revision."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_stage_sheet_map(stage_pair_id: _PairId) -> WireResponse:
        return json_response(200, _body(links.get_current_map(pair_id=stage_pair_id)))

    @router.post(
        _MAP, operation_id="applyStageSheetMap", tags=_TAGS, status_code=201,
        response_model=models.StageLinkRevision,
        responses={**success(201, "An expert's complete map revision or keyed replay."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def apply_stage_sheet_map(
        subject: CurrentSubject, stage_pair_id: _PairId,
        body: models.ApplyStageSheetMapRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(201, _body(links.apply_map(
            pair_id=stage_pair_id, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.get(
        f"{_MAP}/revisions", operation_id="listStageSheetMapHistory", tags=_TAGS,
        status_code=200, response_model=models.StageLinkRevisionPage,
        responses={**success(200, "Append-only sheet map revision history."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_sheet_map_history(
        stage_pair_id: _PairId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(links.list_history(
            pair_id=stage_pair_id, cursor=cursor, limit=limit,
        )))

    @router.get(
        "/stage-link-revisions/{stage_link_revision_id}", operation_id="getStageSheetMapRevision",
        tags=_TAGS, status_code=200, response_model=models.StageLinkRevision,
        responses={**success(200, "One immutable sheet map revision."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_stage_sheet_map_revision(stage_link_revision_id: _RevisionId) -> WireResponse:
        return json_response(200, _body(links.get_revision(revision_id=stage_link_revision_id)))
