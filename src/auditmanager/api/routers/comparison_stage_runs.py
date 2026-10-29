"""C3 seven-step deterministic stage chain run boundary."""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonStageRunPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_stage_run_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_RUNS: Final[str] = "/stage-pairs/{stage_pair_id}/chain-runs"
_RUN: Final[str] = "/stage-chain-runs/{stage_chain_run_id}"
_PairId = Annotated[models.StagePairId, Path()]
_RunId = Annotated[models.StageChainRunId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_stage_run_routes(router: APIRouter, runs: ComparisonStageRunPort) -> None:
    @router.post(
        _RUNS, operation_id="startStageChainRun", tags=_TAGS, status_code=201,
        response_model=models.StageChainRun,
        responses={**success(201, "A pinned seven-step run or keyed replay."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def start_stage_chain_run(
        subject: CurrentSubject, stage_pair_id: _PairId,
        body: models.StartStageChainRunRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(201, _body(runs.start_run(
            pair_id=stage_pair_id, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.get(
        _RUNS, operation_id="listStageChainRuns", tags=_TAGS, status_code=200,
        response_model=models.StageChainRunPage,
        responses={**success(200, "One page of pinned chain runs."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_chain_runs(
        stage_pair_id: _PairId, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(runs.list_runs(
            pair_id=stage_pair_id, cursor=cursor, limit=limit,
        )))

    @router.get(
        _RUN, operation_id="getStageChainRun", tags=_TAGS, status_code=200,
        response_model=models.StageChainRun,
        responses={**success(200, "The persisted state and seven step receipts."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_stage_chain_run(stage_chain_run_id: _RunId) -> WireResponse:
        return json_response(200, _body(runs.get_run(run_id=stage_chain_run_id)))

    @router.post(
        f"{_RUN}/cancellation", operation_id="cancelStageChainRun", tags=_TAGS,
        status_code=200, response_model=models.StageChainRun,
        responses={**success(200, "The run cancelled after its active step."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_stage_chain_run(
        subject: CurrentSubject, stage_chain_run_id: _RunId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(runs.cancel_run(
            run_id=stage_chain_run_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))
