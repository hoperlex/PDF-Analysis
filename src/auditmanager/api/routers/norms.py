"""The seven norms operations: text search, documents, paragraphs, content and the current
snapshot. `W55A-SEAL-01` (`W55-PLAN.md` section A3.6; owner rulings R-80, R-112, R-113).

=============================  ========================================================  =======
operation                      method and path                                           roles
=============================  ========================================================  =======
``searchNorms``                ``GET /norms/search?q=&norms_snapshot_id=&cursor=&limit=``  any one
``getNormDocument``            ``GET /norm-documents/{norm_document_id}``                  any one
``listNormParagraphs``         ``GET /norm-documents/{norm_document_id}/paragraphs``       any one
``streamNormDocumentContent``  ``GET /norm-documents/{norm_document_id}/content``          any one
``listNormSnapshots``          ``GET /norms/snapshots``                                    any one
``listNormSnapshotEvents``     ``GET /norms/snapshots/events``                             admin
``setCurrentNormSnapshot``     ``PUT /norms/snapshots/current``                            admin
=============================  ========================================================  =======

The roles live in :data:`auditmanager.api.security.OPERATION_ROLES`, decided before a
handler runs. Every operation delegates to one port method and renders what comes back:
:class:`~auditmanager.api.routers.ports.NormsSearchPort` for six of them and
:class:`~auditmanager.api.routers.ports.NormContentPort` for the PDF. `W55A-SEARCH-01`
gave both their bodies in ``bootstrap/adapters.py`` (over ``auditmanager.norms.search`` and
``auditmanager.norms.current_snapshot``).

A malformed ``Range`` on a norm document that does not exist is ``404``, not ``422``: the
document is asked for before the parse refusal is re-raised, the precedence
``streamDocumentVersionContent`` keeps (``_parsed_range``).

``setCurrentNormSnapshot`` takes no ``Idempotency-Key``: it is a compare-and-set on durable
state. ``expected_current`` is the caller's belief about the current snapshot, a stale belief
is ``409 conflict`` (``stale_current_snapshot``), and an already-current target answers the
current designation as a replay without writing a history row.
"""

from __future__ import annotations

from typing import Annotated, Any, Final

from fastapi import APIRouter, Path, Query, Response
from pydantic import Field, WithJsonSchema

from auditmanager.api.routers.declarations import (
    STATE_CONFLICT_DESCRIPTION,
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.documents import RangeParam
from auditmanager.api.routers.ports import NormContentPort, NormsSearchPort
from auditmanager.api.routers.wire import (
    WireResponse,
    encode_json,
    json_response,
    streamed_content_response,
)
from auditmanager.api.schemas import models
from auditmanager.api.schemas.content import PDF_MEDIA_TYPE, ByteRange
from auditmanager.api.schemas.models import optional_property
from auditmanager.api.security import CurrentSubject
from auditmanager.shared.errors import DomainError

__all__ = ["build_norm_routes"]

#: ``q``: 1-200 characters -- an optional designation, an optional clause (``п. 7.1.4``) and
#: words, parsed by the search implementation (plan section A3.4).
QueryParam = Annotated[
    Annotated[str, Field(min_length=1, max_length=200)],
    Query(description="The search text: a designation, a clause, words, or a combination."),
]

#: An explicit scope. Accepted only for a snapshot that has been current at least once.
NormsSnapshotFilterParam = Annotated[
    models.NormsSnapshotId | None,
    WithJsonSchema({"$ref": "#/components/schemas/NormsSnapshotId"}),
    Query(json_schema_extra=optional_property),
]

NormDocumentIdParam = Annotated[models.NormDocumentId, Path()]

_PDF_CONTENT: Final[dict[str, Any]] = {
    PDF_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}
}


def build_norm_routes(
    router: APIRouter, norms: NormsSearchPort, content: NormContentPort
) -> None:
    @router.get(
        "/norms/search", operation_id="searchNorms", tags=["norms"],
        response_model=models.NormSearchPage,
        responses={**success(200, "Reliable paragraphs of the current (or a once-current) "
                                  "snapshot matching the query, with attribution."),
                   **envelope_responses(401, 403, 422, 500, 503)},
    )
    def search_norms(
        q: QueryParam,
        norms_snapshot_id: NormsSnapshotFilterParam = None,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        page = norms.search(
            q=q, norms_snapshot_id=norms_snapshot_id, cursor=cursor, limit=limit
        )
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.get(
        "/norm-documents/{norm_document_id}", operation_id="getNormDocument",
        tags=["norms"], response_model=models.NormDocument,
        responses={**success(200, "One norm document of a snapshot, with attribution."),
                   **envelope_responses(401, 403, 404, 500, 503)},
    )
    def get_norm_document(norm_document_id: NormDocumentIdParam) -> WireResponse:
        document = norms.get_document(norm_document_id=norm_document_id)
        return json_response(200, encode_json(document.model_dump(mode="json")))

    @router.get(
        "/norm-documents/{norm_document_id}/paragraphs", operation_id="listNormParagraphs",
        tags=["norms"], response_model=models.NormParagraphPage,
        responses={**success(200, "One page of the document's canonical paragraphs in "
                                  "order, unreliable ones marked."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def list_norm_paragraphs(
        norm_document_id: NormDocumentIdParam,
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        page = norms.list_paragraphs(
            norm_document_id=norm_document_id, cursor=cursor, limit=limit
        )
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.get(
        "/norm-documents/{norm_document_id}/content",
        operation_id="streamNormDocumentContent", tags=["norms"], status_code=200,
        response_class=Response,
        responses={
            **success(
                200, "The complete source PDF.", content=_PDF_CONTENT,
                headers={
                    "Content-Length": {
                        "schema": {"type": "integer", "minimum": 0},
                        "description": "Byte size of the source PDF.",
                    }
                },
            ),
            **success(206, "The requested byte range.", content=_PDF_CONTENT),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def stream_norm_document_content(
        norm_document_id: NormDocumentIdParam,
        range_header: RangeParam = None,  # type: ignore[assignment]
    ) -> Response:
        byte_range = _parsed_range(norms, norm_document_id, range_header)
        streamed = content.stream_content(
            norm_document_id=norm_document_id, byte_range=byte_range
        )
        return streamed_content_response(streamed)

    @router.get(
        "/norms/snapshots", operation_id="listNormSnapshots", tags=["norms"],
        response_model=models.NormSnapshotPage,
        responses={**success(200, "Every loaded snapshot: counts, build state, whether it "
                                  "qualifies and whether it is current."),
                   **envelope_responses(401, 403, 422, 500, 503)},
    )
    def list_norm_snapshots(
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        page = norms.list_snapshots(cursor=cursor, limit=limit)
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.get(
        "/norms/snapshots/events", operation_id="listNormSnapshotEvents", tags=["norms"],
        response_model=models.NormSnapshotEventPage,
        responses={**success(200, "The append-only history of the current snapshot, "
                                  "newest first."),
                   **envelope_responses(401, 403, 422, 500, 503)},
    )
    def list_norm_snapshot_events(
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        page = norms.list_snapshot_events(cursor=cursor, limit=limit)
        return json_response(200, encode_json(page.model_dump(mode="json")))

    @router.put(
        "/norms/snapshots/current", operation_id="setCurrentNormSnapshot", tags=["norms"],
        response_model=models.NormCurrentSnapshot,
        responses={
            **success(200, "The current designation, new or replayed."),
            **envelope_responses(
                401, 403, 404, 409, 422, 500, 503,
                descriptions={409: STATE_CONFLICT_DESCRIPTION},
            ),
        },
    )
    def set_current_norm_snapshot(
        subject: CurrentSubject, body: models.SetCurrentNormSnapshotRequest,
    ) -> WireResponse:
        current = norms.set_current_snapshot(
            norms_snapshot_id=body.norms_snapshot_id,
            expected_current=body.expected_current,
            user_uid=subject.user_uid,
        )
        return json_response(200, encode_json(current.model_dump(mode="json")))


def _parsed_range(
    norms: NormsSearchPort, norm_document_id: str, header: str | None
) -> ByteRange | None:
    """The ``Range`` syntax, refused only after the document is known to exist."""
    if header is None:
        return None
    try:
        return ByteRange.parse(header)
    except DomainError:
        norms.get_document(norm_document_id=norm_document_id)
        raise
