"""``uploadDocument``, ``getDocumentVersion``, ``streamDocumentVersionContent``,
``listDocuments`` and ``listVersions``.

``uploadDocument`` takes a portal bundle (`W55B-SEAL-01`, R-116): one ZIP holding the PDF
and the portal's own files. The route hands the part's file handle to the port and reads
nothing itself.

The streaming operation is the one with a rule worth restating: **the server streams the
bytes itself**. There is no redirect and no presigned link. A URL into object storage is the
internal address the contract forbids in a response, and it would outlive the request that
authorised it. The bytes arrive here as chunks from :meth:`DocumentPort.stream_content`
(`W55A-CONTENT-01`, plan section A3.5), having been resolved from a ``blob_id``; nothing on
this path knows a bucket or a key, and nothing on it holds the object whole.
"""

from __future__ import annotations

from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, Form, Header, Path, Response

from auditmanager.api.routers.declarations import (
    CursorParam,
    LimitParam,
    envelope_responses,
    success,
)
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.multipart import (
    CheckedUpload,
    UploadRoute,
    require_a_strict_multipart_body,
)
from auditmanager.api.routers.ports import DocumentPort
from auditmanager.api.routers.wire import (
    StreamingWireResponse,
    WireResponse,
    encode_json,
    json_response,
    streamed_content_response,
)
from auditmanager.api.schemas import models
from auditmanager.api.schemas.content import ByteRange
from auditmanager.api.schemas.common import page_body, paginate
from auditmanager.api.schemas.documents import document_version_body
from auditmanager.shared.errors import DomainError

__all__ = ["build_document_routes"]

_PDF: Final[str] = "application/pdf"
#: `W55B-SEAL-01` (R-116). The upload is a portal bundle: one ZIP. The server decides by the
#: archive's magic bytes, not by this label -- browsers send ``application/zip``,
#: ``application/x-zip-compressed`` or nothing -- so the label is the contract's declaration,
#: not a gate.
_ZIP: Final[str] = "application/zip"

#: The contract declares this body as ``multipart/form-data`` and only that. FastAPI would
#: otherwise declare ``application/x-www-form-urlencoded`` for a Pydantic form model -- a
#: second media type the contract does not accept, and one that cannot carry a PDF.
_MULTIPART: Final[str] = "multipart/form-data"

#: The contract declares the ``file`` part as ``application/zip``, in
#: ``requestBody.content.multipart/form-data.encoding.file.contentType``. **FastAPI does not
#: emit it** -- `W13-CONF` measured that on a real generated document -- and it is a declared
#: constraint on the part, so it is restored with ``openapi_extra``.
#: ``test_a_dropped_multipart_encoding_is_caught`` is the case that keeps it restored.
_MULTIPART_ENCODING: Final[dict[str, Any]] = {
    "requestBody": {
        "content": {
            "multipart/form-data": {"encoding": {"file": {"contentType": _ZIP}}}
        }
    }
}

#: ``#/paths./versions/{version_uid}/content.get.parameters`` -- a plain string, optional.
RangeParam = Annotated[
    str,
    Header(
        alias="Range",
        json_schema_extra=models.optional_property,
        description="Byte range, so the viewer can page a large document without "
        "fetching all of it.",
    ),
]


def build_document_routes(router: APIRouter, documents: DocumentPort) -> None:

    # `W55B-FIX` (X-3): declared through ``add_api_route`` for its ``route_class_override``,
    # the one argument the decorator does not take. ``UploadRoute`` parses this operation's
    # form under small part bounds; every argument of the declaration is the decorator's,
    # so the generated document does not move.
    def upload_document(
        project_uid: Annotated[models.ProjectUid, Path()],
        body: Annotated[models.UploadDocumentRequest, Form(media_type=_MULTIPART)],
        idempotency_key: RequiredIdempotencyKey,
        checked: Annotated[CheckedUpload, Depends(require_a_strict_multipart_body)],
    ) -> WireResponse:
        # `UploadDocumentRequest` is closed, so an undeclared part is an `extra_forbidden`
        # that `on_request_validation_error` renders as `additionalProperties` -- the same
        # answer a JSON body's undeclared property gets, which is the point.
        # `checked` ran first -- FastAPI resolves sub-dependencies before the body -- so
        # by here the body is a readable multipart of uniquely named parts, the file part
        # has a filename, and `checked.display_title` is the text the caller actually
        # encoded rather than Starlette's latin-1 reading of it.
        # `W55B-SEAL-01`: the part's own file handle goes to the port unread. It is positioned
        # at the start; what reads it, and how much of it at a time, is the port's to say
        # (`DocumentPort.upload_document`). `W55B-STREAM-01`: Starlette has already spooled
        # a part this size to a temporary file, so the handle is seekable and the bytes
        # are never in memory here -- nothing on this route reads, joins or copies them.
        filename = body.file.filename or ""
        outcome = documents.upload_document(
            project_uid=project_uid,
            content=body.file.file,
            source_filename=filename,
            display_title=checked.display_title,
            section=body.section.value if body.section is not None else None,
            idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(document_version_body(outcome.version)))

    router.add_api_route(
        "/projects/{project_uid}/documents",
        upload_document,
        methods=["POST"],
        operation_id="uploadDocument",
        tags=["documents"],
        status_code=201,
        response_model=models.DocumentVersion,
        openapi_extra=_MULTIPART_ENCODING,
        responses={
            **success(201, "The version was published, or an identical upload replayed."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
        route_class_override=UploadRoute,
    )

    # `W59-VERSION-UPLOAD-01`: the next version of an existing document. Declared exactly as
    # `uploadDocument` -- the same `UploadRoute` part bounds, the same strict multipart pass,
    # the same handle handed to the port unread -- with the document in the path and a closed
    # body that holds the bundle only. `BodyCapMiddleware` matches this path too, so it gets
    # the upload body cap and takes an upload slot like `uploadDocument`.
    def upload_document_version(
        project_uid: Annotated[models.ProjectUid, Path()],
        document_uid: Annotated[models.DocumentUid, Path()],
        body: Annotated[models.UploadDocumentVersionRequest, Form(media_type=_MULTIPART)],
        idempotency_key: RequiredIdempotencyKey,
        checked: Annotated[CheckedUpload, Depends(require_a_strict_multipart_body)],
    ) -> WireResponse:
        del checked  # the strict pass is the point; this body has no title to decode
        outcome = documents.upload_document_version(
            project_uid=project_uid,
            document_uid=document_uid,
            content=body.file.file,
            source_filename=body.file.filename or "",
            idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(document_version_body(outcome.version)))

    router.add_api_route(
        "/projects/{project_uid}/documents/{document_uid}/versions",
        upload_document_version,
        methods=["POST"],
        operation_id="uploadDocumentVersion",
        tags=["documents"],
        status_code=201,
        response_model=models.DocumentVersion,
        openapi_extra=_MULTIPART_ENCODING,
        responses={
            **success(
                201,
                "The next version was published, or an identical upload replayed.",
            ),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
        route_class_override=UploadRoute,
    )

    @router.get(
        "/projects/{project_uid}/documents",
        operation_id="listDocuments",
        tags=["documents"],
        status_code=200,
        response_model=models.DocumentVersionPage,
        responses={
            **success(
                200,
                "One page of the current version of each document in this project.",
            ),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def list_documents(
        project_uid: Annotated[models.ProjectUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        # `GET` of the collection `uploadDocument` `POST`s into, returning a page of
        # exactly the resource that `POST` returns -- which is the rule `listProjects`
        # already follows against `createProject`.
        rows = documents.list_documents(project_uid=project_uid)
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_version_sort_key)
        body = page_body(
            [document_version_body(view) for view in page.items], page.next_cursor
        )
        return json_response(200, encode_json(body))

    @router.get(
        "/documents/{document_uid}/versions",
        operation_id="listVersions",
        tags=["documents"],
        status_code=200,
        response_model=models.DocumentVersionPage,
        responses={
            **success(200, "One page of this document's published versions."),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def list_versions(
        document_uid: Annotated[models.DocumentUid, Path()],
        cursor: CursorParam = None,  # type: ignore[assignment]
        limit: LimitParam = 50,
    ) -> WireResponse:
        rows = documents.list_versions(document_uid=document_uid)
        page = paginate(rows, limit=limit, cursor=cursor, sort_key=_version_sort_key)
        body = page_body(
            [document_version_body(view) for view in page.items], page.next_cursor
        )
        return json_response(200, encode_json(body))

    @router.get(
        "/versions/{version_uid}",
        operation_id="getDocumentVersion",
        tags=["documents"],
        status_code=200,
        response_model=models.DocumentVersion,
        responses={
            **success(200, "One published version and its input manifest."),
            **envelope_responses(401, 403, 404, 500, 503),
        },
    )
    def get_document_version(
        version_uid: Annotated[models.VersionUid, Path()],
    ) -> WireResponse:
        view = documents.get_version(version_uid=version_uid)
        return json_response(200, encode_json(document_version_body(view)))

    @router.get(
        "/versions/{version_uid}/content",
        operation_id="streamDocumentVersionContent",
        tags=["documents"],
        status_code=200,
        response_class=Response,
        responses={
            **success(
                200,
                "The complete PDF.",
                content={_PDF: {"schema": {"type": "string", "format": "binary"}}},
                headers={
                    "Content-Length": {
                        "schema": {"type": "integer", "minimum": 0},
                        "description": "Byte size of the published version.",
                    }
                },
            ),
            **success(
                206,
                "The requested byte range.",
                content={_PDF: {"schema": {"type": "string", "format": "binary"}}},
            ),
            **envelope_responses(401, 403, 404, 422, 500, 503),
        },
    )
    def stream_document_version_content(
        version_uid: Annotated[models.VersionUid, Path()],
        range_header: RangeParam = None,  # type: ignore[assignment]
    ) -> StreamingWireResponse:
        byte_range = _parsed_range(documents, version_uid, range_header)
        streamed = documents.stream_content(version_uid=version_uid, byte_range=byte_range)
        return streamed_content_response(streamed)


def _version_sort_key(view: object) -> tuple[str, ...]:
    """The opaque identity, which is also each listing's total order.

    Both listings order by a display value -- ``published_at`` for documents,
    ``version_ordinal`` for versions -- and both carry the identity as their tiebreaker,
    so the key the cursor carries is the identity and nothing else.
    ``auditmanager.api.schemas.common.encode_cursor`` is explicit that a cursor never
    carries a row number, a sequence value or an ordinal, and ``P02_SEAMS.md`` section 2.2
    lists a display ordinal among the things that are never an identity.
    """
    return (getattr(view, "version_uid"),)


def _parsed_range(
    documents: DocumentPort, version_uid: str, header: str | None
) -> ByteRange | None:
    """The ``Range`` header's syntax, refused only after the version is known to exist.

    Before `W55A-CONTENT-01` the version was read first and the header checked second, so
    a malformed header on an unknown version answered ``404``. :class:`ByteRange` parses
    before the port is called; this keeps that precedence by asking for the version
    before reporting the malformed header -- a ``404`` stays a ``404`` whatever the header
    says. ``unsatisfiable`` needs the size and is the port's, after the same lookup.
    """
    if header is None:
        return None
    try:
        return ByteRange.parse(header)
    except DomainError:
        documents.get_version(version_uid=version_uid)
        raise
