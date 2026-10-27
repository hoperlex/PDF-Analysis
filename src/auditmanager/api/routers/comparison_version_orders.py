"""The order in which the versions of a document set are compared, sealed as stubs
(`CMP-SEAL-C0`, ADR-0025 decisions 14 and 16).

``listComparisonVersionOrders`` reads the revisions (any one role); ``appendComparisonVersionOrder``
appends one (an expert's act, `R-60`; an administrator without the expert role is refused). The
order never changes the documents' ordinal that runs and finding carry-over use (`D-5`).
Both answer ``503 dependency_unavailable`` until `CMP-INGEST-01` wires the port.
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
from auditmanager.api.routers.ports import ComparisonVersionOrderPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject

__all__ = ["build_comparison_version_order_routes"]

_TAGS: Final[list[str]] = ["comparison"]
_PATH: Final[str] = (
    "/projects/{project_uid}/documents/{document_uid}/comparison-version-orders"
)


def _body(model: BaseModel) -> bytes:
    return encode_json(model.model_dump(mode="json", exclude_unset=True))


def build_comparison_version_order_routes(
    router: APIRouter, orders: ComparisonVersionOrderPort
) -> None:
    @router.get(
        _PATH, operation_id="listComparisonVersionOrders", tags=_TAGS, status_code=200,
        response_model=models.ComparisonVersionOrderList,
        responses={**success(200, "One page of the order revisions of the document set, "
                                  "newest first."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_comparison_version_orders(
        subject: CurrentSubject, project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        view = orders.list_orders(
            project_uid=project_uid, document_uid=document_uid, cursor=cursor, limit=limit
        )
        return json_response(200, _body(view))

    @router.post(
        _PATH, operation_id="appendComparisonVersionOrder", tags=_TAGS, status_code=201,
        response_model=models.ComparisonVersionOrder,
        responses={**success(201, "The new revision, or the recorded outcome of an identical "
                                  "earlier request."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def append_comparison_version_order(
        subject: CurrentSubject, project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        body: models.AppendComparisonVersionOrderRequest,
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = orders.append_order(
            project_uid=project_uid, document_uid=document_uid,
            version_uids=body.version_uids, base_revision_no=body.base_revision_no,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, _body(view))
