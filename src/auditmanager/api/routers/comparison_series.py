"""The series of adjacent transitions of a document set and the sheet pairs of a transition
(`CMP-SEAL-C1` sealed them, `CMP-SERIES-01` serves them; ADR-0025 decisions 15, 16 and 21).

``startComparisonSeries`` («Запустить» / «Заново») compares every adjacent pair of versions for
the current order; ``getComparisonSeries`` and ``listComparisonSeries`` read it with the summary
counts and the deterministic verdict of each transition; ``pauseComparisonSeries``,
``resumeComparisonSeries``, ``cancelComparisonSeries`` and ``finishComparisonSeries``
(«Досчитать») steer it; ``listComparisonSheetPairs`` and ``getComparisonSheetPair`` read the
results. Reads are any one role; every write is an expert's act (`R-60`) and keyed.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonSeriesPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_series_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_SERIES_OF_DOCUMENT: Final[str] = (
    "/projects/{project_uid}/documents/{document_uid}/comparison-series"
)

_ProjectUid = Annotated[models.ProjectUid, Path()]
_DocumentUid = Annotated[models.DocumentUid, Path()]
_SeriesId = Annotated[models.ComparisonSeriesId, Path()]
_TransitionId = Annotated[models.ComparisonTransitionId, Path()]
_SheetPairId = Annotated[models.ComparisonSheetPairId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_series_routes(router: APIRouter, series: ComparisonSeriesPort) -> None:
    @router.post(
        _SERIES_OF_DOCUMENT, operation_id="startComparisonSeries", tags=_TAGS,
        status_code=201, response_model=models.ComparisonSeries,
        responses={**success(201, "The new series, or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def start_comparison_series(
        subject: CurrentSubject, project_uid: _ProjectUid, document_uid: _DocumentUid,
        body: models.StartComparisonSeriesRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = series.start_series(
            project_uid=project_uid, document_uid=document_uid,
            restart=bool(body.restart), base_order_revision_no=body.base_order_revision_no,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.get(
        _SERIES_OF_DOCUMENT, operation_id="listComparisonSeries", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSeriesPage,
        responses={**success(200, "One page of the series of the document set, newest first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_series(
        project_uid: _ProjectUid, document_uid: _DocumentUid,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = series.list_series(
            project_uid=project_uid, document_uid=document_uid, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))

    @router.get(
        "/comparison-series/{comparison_series_id}", operation_id="getComparisonSeries",
        tags=_TAGS, status_code=200, response_model=models.ComparisonSeries,
        responses={**success(200, "The series with its transitions."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_series(comparison_series_id: _SeriesId) -> WireResponse:
        view = series.get_series(series_id=comparison_series_id)
        return json_response(200, _body(view))

    @router.post(
        "/comparison-series/{comparison_series_id}/pause",
        operation_id="pauseComparisonSeries", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSeries,
        responses={**success(200, "The series, paused."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def pause_comparison_series(
        subject: CurrentSubject, comparison_series_id: _SeriesId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = series.pause_series(
            series_id=comparison_series_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-series/{comparison_series_id}/resume",
        operation_id="resumeComparisonSeries", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSeries,
        responses={**success(200, "The series, running again."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def resume_comparison_series(
        subject: CurrentSubject, comparison_series_id: _SeriesId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = series.resume_series(
            series_id=comparison_series_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-series/{comparison_series_id}/cancellation",
        operation_id="cancelComparisonSeries", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSeries,
        responses={**success(200, "The series, cancelled."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_comparison_series(
        subject: CurrentSubject, comparison_series_id: _SeriesId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = series.cancel_series(
            series_id=comparison_series_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-series/{comparison_series_id}/finish",
        operation_id="finishComparisonSeries", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSeries,
        responses={**success(200, "The series, with the transitions that had no result queued."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def finish_comparison_series(
        subject: CurrentSubject, comparison_series_id: _SeriesId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = series.finish_series(
            series_id=comparison_series_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.get(
        "/comparison-transitions/{comparison_transition_id}/sheet-pairs",
        operation_id="listComparisonSheetPairs", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSheetPairPage,
        responses={**success(200, "One page of the sheet pairs of the transition, in the order "
                                  "of the matrix rows."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_sheet_pairs(
        comparison_transition_id: _TransitionId,
        status: Annotated[models.ComparisonSheetStatus, Query()] = None,  # type: ignore[assignment]
        only_changes: Annotated[bool, Query()] = False,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = series.list_sheet_pairs(
            transition_id=comparison_transition_id, status=status,
            only_changes=only_changes, cursor=cursor, limit=limit,
        )
        return json_response(200, _body(view))

    @router.get(
        "/comparison-sheet-pairs/{comparison_sheet_pair_id}",
        operation_id="getComparisonSheetPair", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSheetPair,
        responses={**success(200, "The sheet pair with its raw deterministic evidence."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_sheet_pair(comparison_sheet_pair_id: _SheetPairId) -> WireResponse:
        view = series.get_sheet_pair(sheet_pair_id=comparison_sheet_pair_id)
        return json_response(200, _body(view))
