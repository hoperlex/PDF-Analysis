"""The AI check of the doubtful pairs of a document set, sealed as stubs (`CMP-SEAL-C2`, ADR-0025
decisions 3, 14, 17 and 19).

``estimateComparisonAiPairCheck`` computes the questions, pairs, images, prompt size, routed model and
USD estimate without a model call; ``startComparisonAiPairCheck`` carries the estimate it consents to;
``getComparisonAiPairCheck`` reads the latest job with «вопросов · пар · подсказок · против»;
``pauseComparisonAiPairCheck``, ``resumeComparisonAiPairCheck`` and ``cancelComparisonAiPairCheck`` steer
it; ``listComparisonAiPairHints`` reads the answers and hints per matrix cell. Accepted answers are
written as accepted AI links by the lane's rule and never by a client call. Reads are any one role; every
write is an expert's act (`R-60`) and keyed. All seven answer ``503 dependency_unavailable`` until
`CMP-VC-AIPAIR-01` wires the port, and ``comparison_modules`` first while the versions module is off.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path
from pydantic import BaseModel

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonAiPairPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_ai_pair_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_PAIR_CHECK: Final[str] = "/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check"
_JOB: Final[str] = "/comparison-ai-pair-checks/{comparison_ai_job_id}"

_ProjectUid = Annotated[models.ProjectUid, Path()]
_DocumentUid = Annotated[models.DocumentUid, Path()]
_JobId = Annotated[models.ComparisonAiJobId, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_ai_pair_routes(router: APIRouter, pairs: ComparisonAiPairPort) -> None:
    @router.get(
        f"{_PAIR_CHECK}/estimate", operation_id="estimateComparisonAiPairCheck", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiEstimate,
        responses={**success(200, "What a check of the latest matrix would do and cost."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def estimate_comparison_ai_pair_check(
        project_uid: _ProjectUid, document_uid: _DocumentUid
    ) -> WireResponse:
        view = pairs.estimate_pair_check(project_uid=project_uid, document_uid=document_uid)
        return json_response(200, _body(view))

    @router.post(
        _PAIR_CHECK, operation_id="startComparisonAiPairCheck", tags=_TAGS, status_code=201,
        response_model=models.ComparisonAiJob,
        responses={**success(201, "The new job, or the recorded outcome of an identical earlier "
                                  "request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def start_comparison_ai_pair_check(
        subject: CurrentSubject, project_uid: _ProjectUid, document_uid: _DocumentUid,
        body: models.StartComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = pairs.start_pair_check(
            project_uid=project_uid, document_uid=document_uid, consent=body.consent,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.get(
        _PAIR_CHECK, operation_id="getComparisonAiPairCheck", tags=_TAGS, status_code=200,
        response_model=models.ComparisonAiPairCheck,
        responses={**success(200, "The latest check of the document set and its figures."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_ai_pair_check(
        project_uid: _ProjectUid, document_uid: _DocumentUid
    ) -> WireResponse:
        view = pairs.get_pair_check(project_uid=project_uid, document_uid=document_uid)
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/pause", operation_id="pauseComparisonAiPairCheck", tags=_TAGS, status_code=200,
        response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, paused."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def pause_comparison_ai_pair_check(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = pairs.pause_pair_check(
            job_id=comparison_ai_job_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/resume", operation_id="resumeComparisonAiPairCheck", tags=_TAGS, status_code=200,
        response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, running again."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def resume_comparison_ai_pair_check(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        body: models.ResumeComparisonAiJobRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = pairs.resume_pair_check(
            job_id=comparison_ai_job_id, consent=body.consent, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        f"{_JOB}/cancellation", operation_id="cancelComparisonAiPairCheck", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiJob,
        responses={**success(200, "The job, cancelled."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_comparison_ai_pair_check(
        subject: CurrentSubject, comparison_ai_job_id: _JobId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = pairs.cancel_pair_check(
            job_id=comparison_ai_job_id, user_uid=subject.user_uid, idempotency_key=idempotency_key
        )
        return json_response(200, _body(view))

    @router.get(
        "/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-hints",
        operation_id="listComparisonAiPairHints", tags=_TAGS, status_code=200,
        response_model=models.ComparisonAiPairHintPage,
        responses={**success(200, "One page of the answers and hints per matrix cell, newest first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_ai_pair_hints(
        project_uid: _ProjectUid, document_uid: _DocumentUid,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = pairs.list_pair_hints(
            project_uid=project_uid, document_uid=document_uid, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))
