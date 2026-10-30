"""Separate resumable PDF/ZIP intake boundary for stage comparison (C3 seal).

These routes are stubs until `CMP-STAGE-PAIR-01` supplies bounded admission,
disk readiness and per-PDF validation required by D-262. They never pass ZIP
bytes through the C0 PDF-only completion command.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel, WithJsonSchema

from auditmanager.api.routers.declarations import CursorParam, LimitParam, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonStageUploadPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_stage_upload_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_UPLOADS: Final[str] = "/projects/{project_uid}/stage-uploads"
_UPLOAD: Final[str] = "/stage-uploads/{stage_upload_id}"
_CANDIDATE: Final[str] = "/stage-upload-candidates/{stage_upload_candidate_id}"
_PART_BYTES: Final[int] = 16 * 1024 * 1024
_ProjectUid = Annotated[models.ProjectUid, Path()]
_UploadId = Annotated[models.StageUploadId, Path()]
_FileId = Annotated[models.StageUploadFileId, Path()]
_CandidateId = Annotated[models.StageUploadCandidateId, Path()]
_PartNumber = Annotated[int, Query(ge=1, le=10000)]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_stage_upload_routes(router: APIRouter, uploads: ComparisonStageUploadPort) -> None:
    @router.post(
        _UPLOADS, operation_id="createStageUpload", tags=_TAGS, status_code=201,
        response_model=models.StageUpload,
        responses={**success(201, "A resumable stage upload or its recorded keyed replay."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def create_stage_upload(
        subject: CurrentSubject, project_uid: _ProjectUid,
        body: models.CreateStageUploadRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(201, _body(uploads.create_upload(
            project_uid=project_uid, body=body, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.get(
        _UPLOADS, operation_id="listStageUploads", tags=_TAGS, status_code=200,
        response_model=models.StageUploadPage,
        responses={**success(200, "One page of the project's stage uploads."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_stage_uploads(
        project_uid: _ProjectUid, cursor: CursorParam = None, limit: LimitParam = 50,
    ) -> WireResponse:
        return json_response(200, _body(uploads.list_uploads(
            project_uid=project_uid, cursor=cursor, limit=limit,
        )))

    @router.get(
        _UPLOAD, operation_id="getStageUpload", tags=_TAGS, status_code=200,
        response_model=models.StageUpload,
        responses={**success(200, "The upload, its declared files and proposed candidates."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_stage_upload(stage_upload_id: _UploadId) -> WireResponse:
        return json_response(200, _body(uploads.get_upload(upload_id=stage_upload_id)))

    @router.put(
        f"{_UPLOAD}/files/{{stage_upload_file_id}}/parts",
        operation_id="uploadStageUploadPart", tags=_TAGS, status_code=200,
        response_model=models.StageUploadPartReceipt,
        responses={**success(200, "One 16 MiB-or-smaller part, measured by the server."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def upload_stage_upload_part(
        subject: CurrentSubject, stage_upload_id: _UploadId, stage_upload_file_id: _FileId,
        part_number: _PartNumber,
        content: Annotated[
            bytes,
            Body(media_type="application/octet-stream", max_length=_PART_BYTES),
            WithJsonSchema({"type": "string", "format": "binary", "maxLength": _PART_BYTES}),
        ],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(uploads.put_part(
            upload_id=stage_upload_id, file_id=stage_upload_file_id,
            part_number=part_number, content=content, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.post(
        f"{_UPLOAD}/files/{{stage_upload_file_id}}/completion",
        operation_id="completeStageUploadFile", tags=_TAGS, status_code=200,
        response_model=models.StageUploadFile,
        responses={**success(200, "The verified raw file and its admission state."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def complete_stage_upload_file(
        subject: CurrentSubject, stage_upload_id: _UploadId, stage_upload_file_id: _FileId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(uploads.complete_file(
            upload_id=stage_upload_id, file_id=stage_upload_file_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )))

    @router.post(
        f"{_CANDIDATE}/confirmation", operation_id="confirmStageUploadCandidate",
        tags=_TAGS, status_code=200, response_model=models.StageUploadCandidate,
        responses={**success(200, "The expert-confirmed stage and section proposal."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def confirm_stage_upload_candidate(
        subject: CurrentSubject, stage_upload_candidate_id: _CandidateId,
        body: models.ConfirmStageUploadCandidateRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(uploads.confirm_candidate(
            candidate_id=stage_upload_candidate_id, body=body,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )))

    @router.post(
        f"{_CANDIDATE}/rejection", operation_id="rejectStageUploadCandidate",
        tags=_TAGS, status_code=200, response_model=models.StageUploadCandidate,
        responses={**success(200, "The candidate rejected by an expert."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def reject_stage_upload_candidate(
        subject: CurrentSubject, stage_upload_candidate_id: _CandidateId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(uploads.reject_candidate(
            candidate_id=stage_upload_candidate_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.post(
        f"{_UPLOAD}/pause", operation_id="pauseStageUpload", tags=_TAGS,
        status_code=200, response_model=models.StageUpload,
        responses={**success(200, "The upload paused after the active admission step."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def pause_stage_upload(
        subject: CurrentSubject, stage_upload_id: _UploadId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(uploads.pause_upload(
            upload_id=stage_upload_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.post(
        f"{_UPLOAD}/resume", operation_id="resumeStageUpload", tags=_TAGS,
        status_code=200, response_model=models.StageUpload,
        responses={**success(200, "The upload resumed from its durable receipts."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def resume_stage_upload(
        subject: CurrentSubject, stage_upload_id: _UploadId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(uploads.resume_upload(
            upload_id=stage_upload_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))

    @router.post(
        f"{_UPLOAD}/cancellation", operation_id="cancelStageUpload", tags=_TAGS,
        status_code=200, response_model=models.StageUpload,
        responses={**success(200, "The upload cancelled and staged bytes scheduled for cleanup."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_stage_upload(
        subject: CurrentSubject, stage_upload_id: _UploadId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        return json_response(200, _body(uploads.cancel_upload(
            upload_id=stage_upload_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )))
