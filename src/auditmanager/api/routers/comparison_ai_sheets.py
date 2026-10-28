"""The AI description of changes, sealed as stubs (`CMP-SEAL-C2`, ADR-0025 decisions 3, 17, 19 and 20).

Per series: ``estimateComparisonAiSheetChanges``, ``startComparisonAiSheetChanges`` (carrying the estimate
it consents to), ``getComparisonAiSheetChanges`` (the progress of each transition), and the controls
``pauseComparisonAiSheetChanges``, ``resumeComparisonAiSheetChanges``, ``cancelComparisonAiSheetChanges``,
``finishComparisonAiSheetChanges`` («Досчитать»), ``dequeueComparisonAiSheetChanges`` («Убрать из
очереди») and ``retryComparisonAiSheetChanges`` («Повторить листы с ошибкой»). Per sheet pair, added or
removed sheet: ``getComparisonSheetDescription``, ``listComparisonSheetDescriptionHistory``,
``estimateComparisonSheetDescription``, ``startComparisonSheetDescription`` (cancelled through
``cancelComparisonAiSheetChanges``), ``streamComparisonSheetDescriptionMd`` and, per transition,
``listComparisonReviewSheets``. Reading a description calls no model. Reads are any one role; every
write is an expert's act (`R-60`) and keyed. All fifteen answer ``503 dependency_unavailable`` until
`CMP-VC-AISHEET-01` wires the port, and ``comparison_modules`` first while the versions module is off.
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
from auditmanager.api.routers.ports import ComparisonAiSheetPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_ai_sheet_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_MARKDOWN: Final[str] = "text/markdown; charset=utf-8"
_MARKDOWN_CONTENT = {"text/markdown": {"schema": {"type": "string"}}}
_SERIES_CHANGES: Final[str] = "/comparison-series/{comparison_series_id}/ai-sheet-changes"
_JOB: Final[str] = "/comparison-ai-sheet-jobs/{comparison_ai_job_id}"
_PAIR_DESCRIPTION: Final[str] = "/comparison-sheet-pairs/{comparison_sheet_pair_id}/description"

_SeriesId = Annotated[models.ComparisonSeriesId, Path()]
_TransitionId = Annotated[models.ComparisonTransitionId, Path()]
_SheetPairId = Annotated[models.ComparisonSheetPairId, Path()]
_JobId = Annotated[models.ComparisonAiJobId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_ai_sheet_routes(router: APIRouter, sheets: ComparisonAiSheetPort) -> None:
    @router.get(
        f"{_SERIES_CHANGES}/estimate", operation_id="estimateComparisonAiSheetChanges",
        tags=_TAGS, status_code=200, response_model=models.ComparisonAiEstimate,
        responses={**success(200, "What describing the series would do and cost."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def estimate_comparison_ai_sheet_changes(
        comparison_series_id: _SeriesId,
        only_failed: Annotated[bool, Query()] = False,
    ) -> WireResponse:
        view = sheets.estimate_series_changes(
            series_id=comparison_series_id, only_failed=only_failed
        )
        return json_response(200, _body(view))

    @router.post(
        _SERIES_CHANGES, operation_id="startComparisonAiSheetChanges", tags=_TAGS,
        status_code=201, response_model=models.ComparisonAiJob,
        responses={**success(201, "The new job, or the recorded outcome of an identical earlier "
                                  "request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def start_comparison_ai_sheet_changes(
        subject: CurrentSubject, comparison_series_id: _SeriesId,
        body: models.StartComparisonAiSheetChangesRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.start_series_changes(
            series_id=comparison_series_id, consent=body.consent, restart=bool(body.restart),
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.get(
        _SERIES_CHANGES, operation_id="getComparisonAiSheetChanges", tags=_TAGS, status_code=200,
        response_model=models.ComparisonAiSheetChanges,
        responses={**success(200, "The latest job and the progress of each transition."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_ai_sheet_changes(comparison_series_id: _SeriesId) -> WireResponse:
        view = sheets.get_series_changes(series_id=comparison_series_id)
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/pause", operation_id="pauseComparisonAiSheetChanges", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, paused."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def pause_comparison_ai_sheet_changes(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.pause_changes_job(
            job_id=comparison_ai_job_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/resume", operation_id="resumeComparisonAiSheetChanges", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, running again."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def resume_comparison_ai_sheet_changes(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        body: models.ResumeComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.resume_changes_job(
            job_id=comparison_ai_job_id, consent=body.consent, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/cancellation", operation_id="cancelComparisonAiSheetChanges", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, cancelled."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_comparison_ai_sheet_changes(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.cancel_changes_job(
            job_id=comparison_ai_job_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/finish", operation_id="finishComparisonAiSheetChanges", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, with the sheets that had no result queued."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def finish_comparison_ai_sheet_changes(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.finish_changes_job(
            job_id=comparison_ai_job_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/dequeue", operation_id="dequeueComparisonAiSheetChanges", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, taken out of the AI queue and cancelled."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def dequeue_comparison_ai_sheet_changes(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.dequeue_changes_job(
            job_id=comparison_ai_job_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/retry", operation_id="retryComparisonAiSheetChanges", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, with the sheets that failed queued again."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def retry_comparison_ai_sheet_changes(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        body: models.StartComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.retry_changes_job(
            job_id=comparison_ai_job_id, consent=body.consent, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.get(
        _PAIR_DESCRIPTION, operation_id="getComparisonSheetDescription", tags=_TAGS,
        status_code=200, response_model=models.ComparisonSheetDescription,
        responses={**success(200, "The stored description of the sheet pair."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_sheet_description(comparison_sheet_pair_id: _SheetPairId) -> WireResponse:
        view = sheets.get_sheet_description(sheet_pair_id=comparison_sheet_pair_id)
        return json_response(200, _body(view))

    @router.get(
        "/comparison-sheet-pairs/{comparison_sheet_pair_id}/description-history",
        operation_id="listComparisonSheetDescriptionHistory", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSheetDescriptionHistory,
        responses={**success(200, "One page of the descriptions of the sheet pair, newest first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_sheet_description_history(
        comparison_sheet_pair_id: _SheetPairId,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = sheets.list_sheet_description_history(
            sheet_pair_id=comparison_sheet_pair_id, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))

    @router.get(
        f"{_PAIR_DESCRIPTION}/estimate", operation_id="estimateComparisonSheetDescription",
        tags=_TAGS, status_code=200, response_model=models.ComparisonAiEstimate,
        responses={**success(200, "What describing the sheet would do and cost."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def estimate_comparison_sheet_description(
        comparison_sheet_pair_id: _SheetPairId
    ) -> WireResponse:
        view = sheets.estimate_sheet_description(sheet_pair_id=comparison_sheet_pair_id)
        return json_response(200, _body(view))

    @router.post(
        _PAIR_DESCRIPTION, operation_id="startComparisonSheetDescription", tags=_TAGS,
        status_code=201, response_model=models.ComparisonAiJob,
        responses={**success(201, "The new job, or the recorded outcome of an identical earlier "
                                  "request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def start_comparison_sheet_description(
        subject: CurrentSubject, comparison_sheet_pair_id: _SheetPairId,
        body: models.StartComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = sheets.start_sheet_description(
            sheet_pair_id=comparison_sheet_pair_id, consent=body.consent,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.get(
        f"{_PAIR_DESCRIPTION}/md", operation_id="streamComparisonSheetDescriptionMd", tags=_TAGS,
        status_code=200, response_class=WireResponse,
        responses={**success(200, "The sheet's description as Markdown.", content=_MARKDOWN_CONTENT),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def stream_comparison_sheet_description_md(
        comparison_sheet_pair_id: _SheetPairId
    ) -> WireResponse:
        content = sheets.read_sheet_description_md(sheet_pair_id=comparison_sheet_pair_id)
        return WireResponse(
            200, (("Content-Type", _MARKDOWN), ("Content-Length", str(len(content)))), content
        )

    @router.get(
        "/comparison-transitions/{comparison_transition_id}/review-sheets",
        operation_id="listComparisonReviewSheets", tags=_TAGS, status_code=200,
        response_model=models.ComparisonReviewSheetPage,
        responses={**success(200, "One page of the sheets to review and the single sheets of the "
                                  "transition."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_review_sheets(
        comparison_transition_id: _TransitionId,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = sheets.list_review_sheets(
            transition_id=comparison_transition_id, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))
