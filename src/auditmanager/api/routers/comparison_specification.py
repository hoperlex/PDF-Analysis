"""Specifications of the versions of a document set, sealed as stubs (`CMP-SEAL-C2`, ADR-0025 decisions
3, 17 and 19).

Part A is deterministic and calls no model: ``getVersionPageSpecPositions`` reads the positions of one
page of a version (GOST 21.110 table from the page's words and vector lines) and
``getComparisonSheetPairSpecPositions`` reads «Спецификация по позициям» of a sheet pair. Part B is the AI
comparison of the whole specifications of a transition: ``estimateComparisonSpecification``,
``startComparisonSpecification`` (carrying the estimate it consents to), ``getComparisonSpecification``,
``listComparisonSpecifications`` (the block «Полные спецификации (СО)»),
``listComparisonSpecificationChanges`` and ``cancelComparisonSpecification``. Reads are any one role; a
write is an expert's act (`R-60`) and keyed. All eight answer ``503 dependency_unavailable`` until
`CMP-VC-SPEC-01` wires the port, and ``comparison_modules`` first while the versions module is off for
part B.
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
from auditmanager.api.routers.ports import ComparisonSpecificationPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_specification_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_SPECIFICATION: Final[str] = "/comparison-transitions/{comparison_transition_id}/specification"

_SeriesId = Annotated[models.ComparisonSeriesId, Path()]
_TransitionId = Annotated[models.ComparisonTransitionId, Path()]
_SheetPairId = Annotated[models.ComparisonSheetPairId, Path()]
_PageProfileId = Annotated[models.ComparisonPageProfileId, Path()]
_JobId = Annotated[models.ComparisonAiJobId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_specification_routes(
    router: APIRouter, specifications: ComparisonSpecificationPort
) -> None:
    @router.get(
        "/page-profiles/{comparison_page_profile_id}/spec-positions",
        operation_id="getVersionPageSpecPositions", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSpecPage,
        responses={**success(200, "The positions of the page, when it is a specification sheet."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_version_page_spec_positions(
        comparison_page_profile_id: _PageProfileId
    ) -> WireResponse:
        view = specifications.get_page_positions(page_profile_id=comparison_page_profile_id)
        return json_response(200, _body(view))

    @router.get(
        "/comparison-sheet-pairs/{comparison_sheet_pair_id}/spec-positions",
        operation_id="getComparisonSheetPairSpecPositions", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSheetPairSpecPositions,
        responses={**success(200, "The position changes that fall on the pair's pages."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_sheet_pair_spec_positions(
        comparison_sheet_pair_id: _SheetPairId
    ) -> WireResponse:
        view = specifications.get_pair_positions(sheet_pair_id=comparison_sheet_pair_id)
        return json_response(200, _body(view))

    @router.get(
        "/comparison-series/{comparison_series_id}/specifications",
        operation_id="listComparisonSpecifications", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSpecificationPage,
        responses={**success(200, "One page of the transitions of the series that have a "
                                  "specification."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_specifications(
        comparison_series_id: _SeriesId,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = specifications.list_specifications(
            series_id=comparison_series_id, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))

    @router.get(
        _SPECIFICATION, operation_id="getComparisonSpecification", tags=_TAGS, status_code=200,
        response_model=models.ComparisonSpecification,
        responses={**success(200, "The specification comparison of the transition."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_specification(comparison_transition_id: _TransitionId) -> WireResponse:
        view = specifications.get_specification(transition_id=comparison_transition_id)
        return json_response(200, _body(view))

    @router.get(
        f"{_SPECIFICATION}/changes", operation_id="listComparisonSpecificationChanges",
        tags=_TAGS, status_code=200, response_model=models.ComparisonSpecChangePage,
        responses={**success(200, "One page of the changes of the transition's specification."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_specification_changes(
        comparison_transition_id: _TransitionId,
        kind: Annotated[models.ComparisonSpecChangeKind, Query()] = None,  # type: ignore[assignment]
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = specifications.list_changes(
            transition_id=comparison_transition_id, kind=kind, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))

    @router.get(
        f"{_SPECIFICATION}/estimate", operation_id="estimateComparisonSpecification", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiEstimate,
        responses={**success(200, "What comparing the whole specifications would do and cost."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def estimate_comparison_specification(
        comparison_transition_id: _TransitionId
    ) -> WireResponse:
        view = specifications.estimate_specification(transition_id=comparison_transition_id)
        return json_response(200, _body(view))

    @router.post(
        _SPECIFICATION, operation_id="startComparisonSpecification", tags=_TAGS, status_code=201,
        response_model=models.ComparisonAiJob,
        responses={**success(201, "The new job, or the recorded outcome of an identical earlier "
                                  "request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def start_comparison_specification(
        subject: CurrentSubject, comparison_transition_id: _TransitionId,
        body: models.StartComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = specifications.start_specification(
            transition_id=comparison_transition_id, consent=body.consent,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.post(
        "/comparison-ai-spec-jobs/{comparison_ai_job_id}/cancellation",
        operation_id="cancelComparisonSpecification", tags=_TAGS, status_code=200,
        response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, cancelled."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_comparison_specification(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = specifications.cancel_specification(
            job_id=comparison_ai_job_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))
