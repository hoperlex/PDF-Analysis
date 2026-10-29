"""The effective matrix of a document set and its manual edits, sealed as stubs (`CMP-SEAL-C1`,
ADR-0025 decisions 3, 13, 14 and 16).

``getComparisonMatrix`` reads the effective matrix (the algorithm, then accepted AI links, then
manual edits), ``prepareComparisonMatrix`` queues the profiles that are missing or failed and the
build, ``applyComparisonMatrixEdits`` applies a drafted batch against the revision the caller saw,
``undoComparisonMatrixEdit`` reverses the latest applied edit, ``listComparisonMatrixEdits`` is the
edit history and ``listComparisonAiLinks`` the accepted AI links (written in wave C2). Reads are any
one role; every write is an expert's act (`R-60`) and keyed. All six answer ``503
dependency_unavailable`` until `CMP-MATRIX-01` wires the port.
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
from auditmanager.api.routers.ports import ComparisonMatrixPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_matrix_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_DOCUMENT: Final[str] = "/projects/{project_uid}/documents/{document_uid}"
_MATRIX: Final[str] = _DOCUMENT + "/comparison-matrix"

_ProjectUid = Annotated[models.ProjectUid, Path()]
_DocumentUid = Annotated[models.DocumentUid, Path()]


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_matrix_routes(router: APIRouter, matrices: ComparisonMatrixPort) -> None:
    @router.get(
        _MATRIX, operation_id="getComparisonMatrix", tags=_TAGS, status_code=200,
        response_model=models.ComparisonMatrix,
        responses={**success(200, "The effective matrix of the document set, or its state while "
                                  "none is built."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_comparison_matrix(
        project_uid: _ProjectUid, document_uid: _DocumentUid
    ) -> WireResponse:
        view = matrices.get_matrix(project_uid=project_uid, document_uid=document_uid)
        return json_response(200, _body(view))

    @router.post(
        _MATRIX + "/preparation", operation_id="prepareComparisonMatrix", tags=_TAGS,
        status_code=200, response_model=models.ComparisonMatrixPreparation,
        responses={**success(200, "What was queued, or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 404, 409, 500, 503)},
    )
    def prepare_comparison_matrix(
        subject: CurrentSubject, project_uid: _ProjectUid, document_uid: _DocumentUid,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = matrices.prepare_matrix(
            project_uid=project_uid, document_uid=document_uid,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.get(
        _MATRIX + "/edits", operation_id="listComparisonMatrixEdits", tags=_TAGS,
        status_code=200, response_model=models.ComparisonMatrixEditList,
        responses={**success(200, "One page of the manual edit history, newest event first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_matrix_edits(
        project_uid: _ProjectUid, document_uid: _DocumentUid,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = matrices.list_edits(
            project_uid=project_uid, document_uid=document_uid, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))

    @router.post(
        _MATRIX + "/edits", operation_id="applyComparisonMatrixEdits", tags=_TAGS,
        status_code=200, response_model=models.ComparisonMatrix,
        responses={**success(200, "The effective matrix after the batch, or the recorded "
                                  "outcome of an identical earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def apply_comparison_matrix_edits(
        subject: CurrentSubject, project_uid: _ProjectUid, document_uid: _DocumentUid,
        body: models.ApplyComparisonMatrixEditsRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = matrices.apply_edits(
            project_uid=project_uid, document_uid=document_uid,
            base_revision=body.base_revision, edits=body.edits,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.post(
        _MATRIX + "/edits/undo", operation_id="undoComparisonMatrixEdit", tags=_TAGS,
        status_code=200, response_model=models.ComparisonMatrix,
        responses={**success(200, "The effective matrix after the undo, or the recorded "
                                  "outcome of an identical earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def undo_comparison_matrix_edit(
        subject: CurrentSubject, project_uid: _ProjectUid, document_uid: _DocumentUid,
        body: models.UndoComparisonMatrixEditRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = matrices.undo_edit(
            project_uid=project_uid, document_uid=document_uid,
            base_revision=body.base_revision,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(200, _body(view))

    @router.get(
        _DOCUMENT + "/comparison-ai-links", operation_id="listComparisonAiLinks", tags=_TAGS,
        status_code=200, response_model=models.ComparisonAiLinkList,
        responses={**success(200, "One page of the accepted AI links of the document set, "
                                  "newest first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_ai_links(
        project_uid: _ProjectUid, document_uid: _DocumentUid,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = matrices.list_ai_links(
            project_uid=project_uid, document_uid=document_uid, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))
