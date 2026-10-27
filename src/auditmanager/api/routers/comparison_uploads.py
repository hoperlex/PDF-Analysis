"""The comparison upload operations, sealed as stubs (`CMP-SEAL-C0`, ADR-0025 decisions 9-11, 16, 25).

Twelve operations: create, list and read an upload batch, stage a part (at most 16 MiB), complete
a file, read the proposal, confirm / exclude / retry one set, pause and resume the batch, cancel it.
Every one answers ``503 dependency_unavailable`` until the lane that owns it wires the port
(`CMP-INGEST-01`: create, part, complete, proposal, confirm; `CMP-INGEST-02`: list, exclude, retry,
pause, resume, cancel; storage staging is `CMP-STORAGE-PARTS-01`'s). The router declares the
frozen shapes; behaviour is the lanes'.

Roles: reads are any one role; every write is an expert's act (`R-60`), like ``uploadDocument``.
Every write carries a required ``Idempotency-Key``.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel, WithJsonSchema

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import ComparisonUploadPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["MAX_PART_BYTES", "build_comparison_upload_routes"]

#: ADR-0025 decision 10: every comparison upload is chunked, 16 MiB per part, under the default
#: proxy body cap (32 MiB).
MAX_PART_BYTES: Final[int] = 16 * 1024 * 1024

_TAGS: Final[list[str]] = ["comparison"]

_UploadId = Annotated[models.ComparisonUploadId, Path()]
_FileId = Annotated[models.ComparisonUploadFileId, Path()]
_SetId = Annotated[models.ComparisonUploadSetId, Path()]
_PartNumber = Annotated[int, Query(ge=1, le=10000)]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_upload_routes(router: APIRouter, uploads: ComparisonUploadPort) -> None:
    @router.post(
        "/projects/{project_uid}/comparison-uploads",
        operation_id="createComparisonUpload", tags=_TAGS, status_code=201,
        response_model=models.ComparisonUpload,
        responses={**success(201, "The upload batch, or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def create_comparison_upload(
        subject: CurrentSubject, project_uid: Annotated[models.ProjectUid, Path()],
        body: models.CreateComparisonUploadRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.create_upload(
            project_uid=project_uid, files=body.files, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))

    @router.get(
        "/projects/{project_uid}/comparison-uploads",
        operation_id="listComparisonUploads", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUploadPage,
        responses={**success(200, "One page of the project's upload batches, newest first, "
                                  "without their files."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_uploads(
        subject: CurrentSubject, project_uid: Annotated[models.ProjectUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = uploads.list_uploads(project_uid=project_uid, cursor=cursor, limit=limit)
        return json_response(200, _body(view))

    @router.get(
        "/comparison-uploads/{comparison_upload_id}",
        operation_id="getComparisonUpload", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUpload,
        responses={**success(200, "The upload batch with its files and their states."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_upload(subject: CurrentSubject, comparison_upload_id: _UploadId) -> WireResponse:
        return json_response(200, _body(uploads.get_upload(upload_id=comparison_upload_id)))

    @router.get(
        "/comparison-uploads/{comparison_upload_id}/proposal",
        operation_id="getComparisonUploadProposal", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUploadProposal,
        responses={**success(200, "The proposed grouping, order, stage and section."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_upload_proposal(
        subject: CurrentSubject, comparison_upload_id: _UploadId
    ) -> WireResponse:
        return json_response(200, _body(uploads.get_proposal(upload_id=comparison_upload_id)))

    @router.put(
        "/comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/parts",
        operation_id="uploadComparisonUploadPart", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUploadPartReceipt,
        responses={**success(200, "The part as staged: its size and the SHA-256 the server "
                                  "computed."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def upload_comparison_upload_part(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        comparison_upload_file_id: _FileId, part_number: _PartNumber,
        content: Annotated[
            bytes,
            Body(media_type="application/octet-stream", max_length=MAX_PART_BYTES),
            # The same spelling as the PNG responses (`format: binary`), so the generated client
            # types the body as a ``Blob``.
            WithJsonSchema(
                {"type": "string", "format": "binary", "maxLength": MAX_PART_BYTES}
            ),
        ],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.put_part(
            upload_id=comparison_upload_id, file_id=comparison_upload_file_id,
            part_number=part_number, content=content, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/completion",
        operation_id="completeComparisonUploadFile", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUploadFile,
        responses={**success(200, "The file, verified against its declared SHA-256 and size."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def complete_comparison_upload_file(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        comparison_upload_file_id: _FileId, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.complete_file(
            upload_id=comparison_upload_id, file_id=comparison_upload_file_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/confirmation",
        operation_id="confirmComparisonUploadSet", tags=_TAGS, status_code=200,
        response_model=models.ComparisonProposalSet,
        responses={**success(200, "The set, confirmed with the user's membership and order."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def confirm_comparison_upload_set(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        comparison_upload_set_id: _SetId, body: models.ConfirmComparisonUploadSetRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.confirm_set(
            upload_id=comparison_upload_id, set_id=comparison_upload_set_id, request=body,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/exclusion",
        operation_id="excludeComparisonUploadSet", tags=_TAGS, status_code=200,
        response_model=models.ComparisonProposalSet,
        responses={**success(200, "The set, now excluded from the batch."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def exclude_comparison_upload_set(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        comparison_upload_set_id: _SetId, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.exclude_set(
            upload_id=comparison_upload_id, set_id=comparison_upload_set_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/retry",
        operation_id="retryComparisonUploadSet", tags=_TAGS, status_code=200,
        response_model=models.ComparisonProposalSet,
        responses={**success(200, "The failed set, queued again."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def retry_comparison_upload_set(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        comparison_upload_set_id: _SetId, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.retry_set(
            upload_id=comparison_upload_id, set_id=comparison_upload_set_id,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-uploads/{comparison_upload_id}/pause",
        operation_id="pauseComparisonUpload", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUpload,
        responses={**success(200, "The batch, set to pause after the set in hand."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def pause_comparison_upload(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.pause_upload(
            upload_id=comparison_upload_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-uploads/{comparison_upload_id}/resume",
        operation_id="resumeComparisonUpload", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUpload,
        responses={**success(200, "The paused batch, running again."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def resume_comparison_upload(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.resume_upload(
            upload_id=comparison_upload_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        "/comparison-uploads/{comparison_upload_id}/cancellation",
        operation_id="cancelComparisonUpload", tags=_TAGS, status_code=200,
        response_model=models.ComparisonUpload,
        responses={**success(200, "The cancelled batch («Отменить пакет»): parts never completed "
                                  "are aborted; completed versions stay."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def cancel_comparison_upload(
        subject: CurrentSubject, comparison_upload_id: _UploadId,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = uploads.cancel_upload(
            upload_id=comparison_upload_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))
