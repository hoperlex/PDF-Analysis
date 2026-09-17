"""The transport's body limit -- the outer of the two size guards.

Two guards refuse an oversized upload and they are independently breakable:

* **this one**, :data:`MAX_BODY` = 26 MiB, which reads the request and is outermost. It
  answers ``details.constraint: "max_bytes"``;
* **the envelope's** ``ENV-SIZE``, ``auditmanager.ingest.MAX_BYTES`` = 25 MiB, which judges
  the document. It answers ``details.constraint: "byte_size <= 26214400"``.

``P4_CLOSURE.md`` section 5 explains why both exist and
``tests/integration/ingest/test_size_guard_boundary.py`` pins the window between them: a
body inside it passes the transport so that ``ENV-SIZE`` is the guard that speaks. The two
numbers are 26 MiB and 25 MiB respectively and **26214400 is the 25 MiB one** -- the phrase
"the 26 MiB boundary" names the transport's limit, which `W13-BASE` section 6.2 had to
correct in its own brief.

**What changed under `T-1`.** The hand-rolled ``email``-parser reader this module used to
be is gone: FastAPI parses ``multipart/form-data`` with ``python-multipart``, and
``UploadDocumentRequest`` -- a closed Pydantic model -- decides which parts are declared, so
an undeclared part is an ``extra_forbidden`` that
:func:`~auditmanager.api.routers.handlers.on_request_validation_error` renders as
``additionalProperties``. What could **not** move into the framework is the limit: a reader
that will happily materialise an unbounded body is a denial-of-service surface of its own,
and FastAPI has no equivalent. So the limit stays here, in front of the parser, as ASGI.
"""

from __future__ import annotations

from typing import Any, Final

from auditmanager.api.routers.correlation import current_correlation_id
from auditmanager.api.routers.errors import envelope_response
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["MAX_BODY", "BodyCapMiddleware"]

#: The upload envelope refuses anything larger long before this, but see the module note.
#: 25 MiB is the declared maximum; the slack covers part headers and the boundary.
MAX_BODY: Final[int] = 26 * 1024 * 1024

#: ``records/22-uploadDocument.refusal.max_bytes.json``, byte for byte.
_UPLOAD_TOO_LARGE: Final[str] = "The upload exceeds the maximum accepted size."
#: The same guard, for a body that is not an upload. A different sentence because
#: ``field: "file"`` would be a lie about a JSON body, and a refusal that names the wrong
#: part of the request is worse than one that names none.
_BODY_TOO_LARGE: Final[str] = "The request body exceeds the maximum accepted size."


class _BodyTooLarge(Exception):
    """Raised out of ``receive`` when the running total passes the limit."""


def _refusal(is_upload: bool) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=_UPLOAD_TOO_LARGE if is_upload else _BODY_TOO_LARGE,
        field="file" if is_upload else "body",
        constraint="max_bytes",
    )


class BodyCapMiddleware:
    """Refuse a body over :data:`MAX_BODY`, before anything materialises it.

    Two checks, and both are needed. ``Content-Length`` is refused up front so an oversized
    body is never read at all -- but a client may omit it, or lie, so the stream is counted
    as well and the request is refused the moment the running total passes the limit. A
    guard that trusted the declared length would be a guard a client can switch off.
    """

    __slots__ = ("app", "limit")

    def __init__(self, app: Any, limit: int = MAX_BODY) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_upload = False
        declared: int | None = None
        for name, value in scope.get("headers", ()):
            lowered = name.lower()
            if lowered == b"content-type":
                is_upload = b"multipart/form-data" in value.lower()
            elif lowered == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None

        if declared is not None and declared > self.limit:
            response = envelope_response(_refusal(is_upload), current_correlation_id())
            await response(scope, receive, send)
            return

        read = 0
        limit = self.limit

        async def counted() -> Any:
            nonlocal read
            message = await receive()
            if message["type"] == "http.request":
                read += len(message.get("body", b""))
                if read > limit:
                    raise _BodyTooLarge
            return message

        try:
            await self.app(scope, counted, send)
        except _BodyTooLarge:
            response = envelope_response(_refusal(is_upload), current_correlation_id())
            await response(scope, receive, send)
