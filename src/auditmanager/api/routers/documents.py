"""``uploadDocument``, ``getDocumentVersion``, ``streamDocumentVersionContent``,
``listDocuments`` and ``listVersions``.

The streaming operation is the one with a rule worth restating: **the server streams the
bytes itself**. There is no redirect and no presigned link. A URL into object storage is the
internal address the contract forbids in a response, and it would outlive the request that
authorised it. The bytes arrive here as ``bytes`` from :meth:`DocumentPort.read_content`,
having been resolved from a ``blob_id``; nothing on this path knows a bucket or a key.
"""

from __future__ import annotations

import re
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
    require_a_strict_multipart_body,
)
from auditmanager.api.routers.ports import DocumentPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import page_body, paginate
from auditmanager.api.schemas.documents import document_version_body
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["build_document_routes"]

_PDF: Final[str] = "application/pdf"

#: The contract declares this body as ``multipart/form-data`` and only that. FastAPI would
#: otherwise declare ``application/x-www-form-urlencoded`` for a Pydantic form model -- a
#: second media type the contract does not accept, and one that cannot carry a PDF.
_MULTIPART: Final[str] = "multipart/form-data"

#: The contract declares the ``file`` part as ``application/pdf``, in
#: ``requestBody.content.multipart/form-data.encoding.file.contentType``. **FastAPI does not
#: emit it** -- `W13-CONF` measured that on a real generated document -- and it is a declared
#: constraint on the part, so it is restored with ``openapi_extra``.
#: ``test_a_dropped_multipart_encoding_is_caught`` is the case that keeps it restored.
_MULTIPART_ENCODING: Final[dict[str, Any]] = {
    "requestBody": {
        "content": {
            "multipart/form-data": {"encoding": {"file": {"contentType": _PDF}}}
        }
    }
}

#: ``bytes=<first>-<last>`` with an optional open end. A multi-range request is not served:
#: the frozen 206 declares one ``application/pdf`` body, and a multipart/byteranges response
#: would not be that shape.
_RANGE: Final[re.Pattern[str]] = re.compile(r"^bytes=(\d*)-(\d*)$")

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

    @router.post(
        "/projects/{project_uid}/documents",
        operation_id="uploadDocument",
        tags=["documents"],
        status_code=201,
        response_model=models.DocumentVersion,
        openapi_extra=_MULTIPART_ENCODING,
        responses={
            **success(201, "The version was published, or an identical upload replayed."),
            **envelope_responses(401, 403, 404, 409, 422, 500, 503),
        },
    )
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
        filename = body.file.filename or ""
        content = body.file.file.read()
        outcome = documents.upload_document(
            project_uid=project_uid,
            content=content,
            source_filename=filename,
            display_title=checked.display_title,
            idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(document_version_body(outcome.version)))

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
    ) -> WireResponse:
        content = documents.read_content(version_uid=version_uid)
        if range_header is None:
            return WireResponse(
                200,
                (
                    ("Content-Type", _PDF),
                    ("Content-Length", str(len(content))),
                    ("Accept-Ranges", "bytes"),
                ),
                content,
            )
        start, end = _resolve_range(range_header, len(content))
        window = content[start : end + 1]
        return WireResponse(
            206,
            (
                ("Content-Type", _PDF),
                ("Content-Length", str(len(window))),
                ("Content-Range", f"bytes {start}-{end}/{len(content)}"),
                ("Accept-Ranges", "bytes"),
            ),
            window,
        )



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


def _resolve_range(header: str, size: int) -> tuple[int, int]:
    """Resolve one byte range against a known size.

    An unsatisfiable or malformed range is ``validation_failed`` rather than a silent full
    body: a viewer that asked for page 40 of a 30-page document has a bug, and answering
    with the whole file hides it behind a much larger download.
    """
    match = _RANGE.match(header.strip())
    if match is None:
        raise _unsatisfiable("format")
    first, last = match.group(1), match.group(2)
    if first == "" and last == "":
        raise _unsatisfiable("format")
    if first == "":
        # A suffix range: the final `last` bytes.
        length = int(last)
        if length == 0:
            raise _unsatisfiable("unsatisfiable")
        start = max(0, size - length)
        end = size - 1
    else:
        start = int(first)
        end = size - 1 if last == "" else min(int(last), size - 1)
    if size == 0 or start >= size or start > end:
        raise _unsatisfiable("unsatisfiable")
    return start, end


def _unsatisfiable(constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="The Range header is not a single satisfiable byte range.",
        field="Range",
        constraint=constraint,
    )
