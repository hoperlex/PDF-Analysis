"""``uploadDocument``, ``getDocumentVersion`` and ``streamDocumentVersionContent``.

The streaming operation is the one with a rule worth restating: **the server streams
the bytes itself**. There is no redirect and no presigned link. A URL into object
storage is the internal address the contract forbids in a response, and it would
outlive the request that authorised it. The bytes arrive here as ``bytes`` from
:meth:`DocumentPort.read_content`, having been resolved from a ``blob_id``; nothing on
this path knows a bucket or a key.
"""

from __future__ import annotations

import json
import re
from typing import Final, Sequence

from auditmanager.api.routers.http import Request, Response, Route, json_response
from auditmanager.api.routers.idempotency import (
    require_idempotency_key,
    require_path_identity,
)
from auditmanager.api.routers.multipart import parse_multipart_upload
from auditmanager.api.routers.ports import DocumentPort
from auditmanager.api.schemas.documents import document_version_body
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ProjectUid, VersionUid

__all__ = ["build_document_routes"]

_PDF: Final[str] = "application/pdf"

#: ``bytes=<first>-<last>`` with an optional open end. A multi-range request is not
#: served: the frozen 206 declares one ``application/pdf`` body, and a multipart/byteranges
#: response would not be that shape.
_RANGE: Final[re.Pattern[str]] = re.compile(r"^bytes=(\d*)-(\d*)$")


def build_document_routes(documents: DocumentPort) -> Sequence[Route]:
    def upload_document(request: Request) -> Response:
        key = require_idempotency_key(request)
        project_uid = require_path_identity(
            request.path_params["project_uid"],
            parse=ProjectUid,
            aggregate_type="Project",
        )
        upload = parse_multipart_upload(request.body, request.headers.get("Content-Type"))
        outcome = documents.upload_document(
            project_uid=str(project_uid),
            content=upload.content,
            source_filename=upload.filename,
            display_title=upload.display_title,
            idempotency_key=key,
        )
        return json_response(201, _encode(document_version_body(outcome.version)))

    def get_document_version(request: Request) -> Response:
        version_uid = require_path_identity(
            request.path_params["version_uid"],
            parse=VersionUid,
            aggregate_type="DocumentVersion",
        )
        view = documents.get_version(version_uid=str(version_uid))
        return json_response(200, _encode(document_version_body(view)))

    def stream_content(request: Request) -> Response:
        version_uid = require_path_identity(
            request.path_params["version_uid"],
            parse=VersionUid,
            aggregate_type="DocumentVersion",
        )
        content = documents.read_content(version_uid=str(version_uid))
        requested = request.headers.get("Range")
        if requested is None:
            return Response(
                200,
                (
                    ("Content-Type", _PDF),
                    ("Content-Length", str(len(content))),
                    ("Accept-Ranges", "bytes"),
                ),
                content,
            )
        start, end = _resolve_range(requested, len(content))
        window = content[start : end + 1]
        return Response(
            206,
            (
                ("Content-Type", _PDF),
                ("Content-Length", str(len(window))),
                ("Content-Range", f"bytes {start}-{end}/{len(content)}"),
                ("Accept-Ranges", "bytes"),
            ),
            window,
        )

    return (
        Route(
            "uploadDocument", "POST", "/projects/{project_uid}/documents", upload_document
        ),
        Route("getDocumentVersion", "GET", "/versions/{version_uid}", get_document_version),
        Route(
            "streamDocumentVersionContent",
            "GET",
            "/versions/{version_uid}/content",
            stream_content,
        ),
    )


def _resolve_range(header: str, size: int) -> tuple[int, int]:
    """Resolve one byte range against a known size.

    An unsatisfiable or malformed range is ``validation_failed`` rather than a silent
    full body: a viewer that asked for page 40 of a 30-page document has a bug, and
    answering with the whole file hides it behind a much larger download.
    """
    match = _RANGE.match(header.strip())
    if match is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The Range header is not a single satisfiable byte range.",
            field="Range",
            constraint="format",
        )
    first, last = match.group(1), match.group(2)
    if first == "" and last == "":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The Range header is not a single satisfiable byte range.",
            field="Range",
            constraint="format",
        )
    if first == "":
        # A suffix range: the final `last` bytes.
        length = int(last)
        if length == 0:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="The Range header is not a single satisfiable byte range.",
                field="Range",
                constraint="unsatisfiable",
            )
        start = max(0, size - length)
        end = size - 1
    else:
        start = int(first)
        end = size - 1 if last == "" else min(int(last), size - 1)
    if size == 0 or start >= size or start > end:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The Range header is not a single satisfiable byte range.",
            field="Range",
            constraint="unsatisfiable",
        )
    return start, end


def _encode(body: object) -> bytes:
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
