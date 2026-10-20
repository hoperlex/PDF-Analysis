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

import re
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Final

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException

from auditmanager.api.routers.correlation import current_correlation_id
from auditmanager.api.routers.errors import envelope_response
from auditmanager.api.routers.wire import (
    JSON_MEDIA_TYPE,
    WireResponse,
    encode_json,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "MAX_BODY",
    "MAX_CONCURRENT_UPLOADS",
    "UPLOAD_CAPACITY_DEPENDENCY",
    "UPLOAD_FORM_MAX_FIELDS",
    "UPLOAD_FORM_MAX_FILES",
    "UPLOAD_FORM_MAX_PART_BYTES",
    "UPLOAD_MAX_BODY",
    "UPLOAD_RETRY_AFTER_SECONDS",
    "BodyCapMiddleware",
    "CheckedUpload",
    "UploadGate",
    "UploadRoute",
    "require_a_strict_multipart_body",
]

#: The body cap of every route that is not an upload, as it has always been. The upload
#: envelope refuses anything larger long before this, but see the module note. 25 MiB is the
#: declared maximum; the slack covers part headers and the boundary.
MAX_BODY: Final[int] = 26 * 1024 * 1024

#: The body cap of ``uploadDocument`` alone: a 250 MiB portal bundle and the multipart
#: framing around it. It sits below nginx's 260m for that location and above the browser's
#: pre-check (`D-44`, ``tests/e2e/test_upload_limit_headroom.py``), so that the typed refusal
#: is the one a caller sees.
UPLOAD_MAX_BODY: Final[int] = 251 * 1024 * 1024

#: Uploads in flight in one API process. The freeze states one uvicorn process per stand.
MAX_CONCURRENT_UPLOADS: Final[int] = 2

#: ``details.dependency`` of the busy refusal -- registered in ``error-codes.json`` under
#: ``dependency_unavailable``, a stable class name and never a count.
UPLOAD_CAPACITY_DEPENDENCY: Final[str] = "upload_capacity"

#: The ``Retry-After`` of the busy refusal, in seconds. A hint and not a promise: an upload
#: that fits the envelope today takes seconds, and a retry costs nothing -- the refusal is
#: answered before the body is read.
UPLOAD_RETRY_AFTER_SECONDS: Final[int] = 5

#: The parts ``uploadDocument``'s form parser reads (`W55B-FIX`, X-3), where Starlette's own
#: defaults are a thousand files and a thousand text fields of a MiB each, held in memory. The
#: operation declares one file part (``file``) and two text parts (``display_title``, at most
#: 400 characters, and ``section``, a name of fifteen). Two files and four text parts let a
#: repeated or undeclared part reach the strict pass below, which names it (``unique_part``,
#: ``additionalProperties``); one more is the parser's ``readable_multipart``. A text part of
#: 16 KiB is ten times the longest title in UTF-8.
UPLOAD_FORM_MAX_FILES: Final[int] = 2
UPLOAD_FORM_MAX_FIELDS: Final[int] = 4
UPLOAD_FORM_MAX_PART_BYTES: Final[int] = 16 * 1024

#: ``POST /projects/{project_uid}/documents`` (``uploadDocument``) and, `W59-VERSION-UPLOAD-01`,
#: ``POST /projects/{project_uid}/documents/{document_uid}/versions`` (``uploadDocumentVersion``)
#: as the application serves them -- the proxy has already removed ``/api/v1``. Matched whole,
#: never as a prefix, so no other route (not ``GET`` of the same collection, and not the
#: classification, section-review or comparison routes under a version) gets the upload cap or
#: takes an upload slot. Both uploads share the one pool of ``MAX_CONCURRENT_UPLOADS`` slots.
_UPLOAD_ROUTE: Final[re.Pattern[str]] = re.compile(
    r"^/projects/[^/]+/documents(?:/[^/]+/versions)?$"
)

#: ``records/22-uploadDocument.refusal.max_bytes.json``, byte for byte.
_UPLOAD_TOO_LARGE: Final[str] = "The upload exceeds the maximum accepted size."
#: The same guard, for a body that is not an upload. A different sentence because
#: ``field: "file"`` would be a lie about a JSON body, and a refusal that names the wrong
#: part of the request is worse than one that names none.
_BODY_TOO_LARGE: Final[str] = "The request body exceeds the maximum accepted size."
#: The certified reader's own sentence for an unreadable multipart body, kept.
_NO_BOUNDARY: Final[str] = (
    "The multipart body could not be read; the boundary may be missing."
)


class _BodyTooLarge(Exception):
    """Raised out of ``receive`` when the running total passes the limit."""


def _refusal(is_upload: bool) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=_UPLOAD_TOO_LARGE if is_upload else _BODY_TOO_LARGE,
        field="file" if is_upload else "body",
        constraint="max_bytes",
    )


class UploadGate:
    """A counter of uploads in flight that never waits: it admits or it refuses.

    One instance per application, touched only from the event loop and never across an
    ``await`` between the check and the increment, so it needs no lock. A request that
    takes a slot must give it back with :meth:`release`; :class:`BodyCapMiddleware` does so
    in a ``finally``.
    """

    __slots__ = ("capacity", "_in_flight")

    def __init__(self, capacity: int = MAX_CONCURRENT_UPLOADS) -> None:
        self.capacity = capacity
        self._in_flight = 0

    @property
    def in_flight(self) -> int:
        return self._in_flight

    def try_acquire(self) -> bool:
        if self._in_flight >= self.capacity:
            return False
        self._in_flight += 1
        return True

    def release(self) -> None:
        assert self._in_flight > 0, "an upload slot was released that was never taken"
        self._in_flight -= 1


def _busy_response() -> WireResponse:
    """``503 dependency_unavailable`` for ``upload_capacity``, with ``Retry-After``.

    Built from the same two wire helpers :func:`~auditmanager.api.routers.errors.envelope_response`
    uses, with the one extra header between ``Content-Length`` and the correlation id the
    outer middleware appends. Every other response is still made by ``envelope_response``.
    """
    envelope = DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=UPLOAD_CAPACITY_DEPENDENCY
    ).envelope(current_correlation_id())
    payload = encode_json(envelope.as_dict())
    return WireResponse(
        envelope.http_status,
        (
            ("Content-Type", JSON_MEDIA_TYPE),
            ("Content-Length", str(len(payload))),
            ("Retry-After", str(UPLOAD_RETRY_AFTER_SECONDS)),
        ),
        payload,
    )


def _bearer_token(value: bytes) -> str | None:
    """The credential of an ``Authorization: Bearer <token>`` header, as the seam reads one."""
    try:
        text = value.decode("latin-1")
    except UnicodeDecodeError:  # pragma: no cover - latin-1 decodes every byte
        return None
    scheme, _, token = text.partition(" ")
    token = token.strip()
    return token if scheme.lower() == "bearer" and token else None


def _media_type(value: bytes) -> bytes:
    """The media type of a ``Content-Type`` header, without its parameters."""
    return value.split(b";", 1)[0].strip().lower()


def _no_body() -> Callable[[], Coroutine[Any, Any, dict[str, Any]]]:
    """A ``receive`` that delivers an empty body and then reports the client gone.

    For an upload-route request whose body is not multipart: the application answers it from
    its headers alone (the seam, then ``media_type``), so it is given nothing to read and the
    caller's bytes are never pulled off the connection.
    """
    delivered = False

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    return receive


def _route_path(scope: Any) -> str:
    """The path below any ``root_path``, which is how the routes are declared."""
    path: str = scope.get("path", "")
    root: str = scope.get("root_path", "")
    return path[len(root):] if root and path.startswith(root) else path


class BodyCapMiddleware:
    """Refuse a body over its route's cap, or a multipart body with no boundary, and hold
    the upload gate.

    Three rules, all here for the same reason: they must be settled **before any parser
    reads the body**. The size one because materialising an unbounded body to discover it
    is unbounded is the denial-of-service surface the limit exists to close; the boundary
    one because FastAPI parses a form before it resolves dependencies, so an application
    handler cannot get in front of it; the gate because a third upload must not have its
    body read into a third temporary file to be told the server is busy.

    The size rule has two checks, and both are needed. ``Content-Length`` is refused up front so an oversized
    body is never read at all -- but a client may omit it, or lie, so the stream is counted
    as well and the request is refused the moment the running total passes the limit. A
    guard that trusted the declared length would be a guard a client can switch off.

    **The limit is per route.** ``POST /projects/{project_uid}/documents`` has
    ``upload_limit``; every other route keeps ``limit``, so a large body to a JSON route is
    refused exactly as before even though the upload route now takes hundreds of MiB.

    **The upload route has a front door** (`W55B-FIX`, X-3; `W55B-QA-01` QA-1). FastAPI
    reads and parses a form before it solves the authorization seam, so a caller with no
    credential had its body of up to 251 MiB read, spooled and parsed, holding one of the
    two upload slots, before the seam answered ``401``. Two of them kept every upload
    refused as busy. Now, before the slot and before any byte of the body:

    * a request with no bearer credential this deployment signed and that has not expired --
      the seam's cheap half, checked by ``verify_credential`` with no database read -- is
      answered here, ``401 authentication_required``;
    * a signed request whose body is not ``multipart/form-data`` takes no slot and has none
      of its body read: the application is handed an empty body, so the seam (the account's
      standing, roles and generation, `test_role_register`) and then the strict pass
      (``media_type``) answer it exactly as they always did, without a byte of the caller's;
    * only a signed multipart request goes on to the gate and the parser.

    The full seam still runs for every request this lets through: this is only a door in
    front of it. ``verify_credential`` absent is a door that admits nobody, the seam's own
    rule for a deployment with no secret.
    """

    __slots__ = ("app", "limit", "upload_limit", "gate", "verify_credential")

    def __init__(
        self,
        app: Any,
        limit: int = MAX_BODY,
        *,
        upload_limit: int = UPLOAD_MAX_BODY,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        verify_credential: Callable[[str], bool] | None = None,
    ) -> None:
        self.app = app
        self.limit = limit
        self.upload_limit = upload_limit
        self.gate = UploadGate(max_concurrent_uploads)
        self.verify_credential = verify_credential

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_upload_route = scope.get("method") == "POST" and bool(
            _UPLOAD_ROUTE.match(_route_path(scope))
        )
        limit = self.upload_limit if is_upload_route else self.limit

        is_upload = False
        has_boundary = False
        media_type = b""
        token: str | None = None
        declared: int | None = None
        for name, value in scope.get("headers", ()):
            lowered = name.lower()
            if lowered == b"content-type":
                is_upload = b"multipart/form-data" in value.lower()
                has_boundary = b"boundary=" in value.lower()
                media_type = _media_type(value)
            elif lowered == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None
            elif lowered == b"authorization":
                token = _bearer_token(value)

        if declared is not None and declared > limit:
            response = envelope_response(_refusal(is_upload), current_correlation_id())
            await response(scope, receive, send)
            return

        if is_upload and not has_boundary:
            # Checked on the header, before anything reads the body, because FastAPI parses
            # a form *before* it resolves dependencies and Starlette's "Missing boundary in
            # multipart" is an exception the route has already turned into its own
            # ``HTTPException(400)`` by the time an application handler could see it. Read
            # from the header rather than from the parser's message: mapping a refusal on
            # another library's prose is exactly what ``routers/errors.py`` refuses to do
            # with a database driver, and it is no better here.
            response = envelope_response(
                DomainError(
                    ErrorCode.VALIDATION_FAILED,
                    message=_NO_BOUNDARY,
                    field="Content-Type",
                    constraint="boundary",
                ),
                current_correlation_id(),
            )
            await response(scope, receive, send)
            return

        if not is_upload_route:
            await self._serve(scope, receive, send, limit, is_upload)
            return

        # The front door, before the gate and before `receive` is touched: a credential this
        # deployment signed and that has not expired; then a body that is not multipart is
        # never read and takes no slot -- the seam and the strict pass answer it.
        refusal = self._front_door(token)
        if refusal is not None:
            await envelope_response(refusal, current_correlation_id())(scope, receive, send)
            return
        if media_type != b"multipart/form-data":
            await self.app(scope, _no_body(), send)
            return

        # The gate. After the cheap refusals above, which a retry could never turn into
        # a success, and before `receive` is touched.
        if not self.gate.try_acquire():
            await _busy_response()(scope, receive, send)
            return
        try:
            await self._serve(scope, receive, send, limit, is_upload)
        finally:
            # Finished, failed, cancelled or disconnected: all of them leave this block.
            self.gate.release()

    def _front_door(self, token: str | None) -> DomainError | None:
        """The upload route's refusal before its body, or ``None`` to go on."""
        verify = self.verify_credential
        if token is None or verify is None or not verify(token):
            return DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        return None

    async def _serve(
        self, scope: Any, receive: Any, send: Any, limit: int, is_upload: bool
    ) -> None:
        read = 0
        exceeded = False
        started = False

        async def counted() -> Any:
            nonlocal read, exceeded
            message = await receive()
            if message["type"] == "http.request":
                read += len(message.get("body", b""))
                if read > limit:
                    exceeded = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Any) -> None:
            # Once the cap has been passed the only answer is ours. FastAPI turns whatever
            # `receive` raised while it read the form into its own 400, and that would
            # reach the client as `readable_multipart` -- a different refusal for a body
            # that sent no `Content-Length` (every request the BFF streams) than for one
            # that declared its size.
            nonlocal started
            if exceeded:
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counted, guarded_send)
        except _BodyTooLarge:
            pass
        if exceeded and not started:
            response = envelope_response(_refusal(is_upload), current_correlation_id())
            await response(scope, receive, send)


# ---------------------------------------------------------------------------------------
# the upload's form parser, bounded (`W55B-FIX`, X-3)
# ---------------------------------------------------------------------------------------


class _BoundedFormRequest(Request):
    """A request whose form is parsed under the upload's part bounds, whoever asks for it.

    FastAPI calls ``request.form()`` with Starlette's defaults; the strict pass below calls it
    again and gets the parsed form back. Both reach this method, so the bounds hold for every
    reader of the form, and an explicit argument can only lower them.
    """

    def form(
        self,
        *,
        max_files: int | float = UPLOAD_FORM_MAX_FILES,
        max_fields: int | float = UPLOAD_FORM_MAX_FIELDS,
        max_part_size: int = UPLOAD_FORM_MAX_PART_BYTES,
    ) -> Any:
        return super().form(
            max_files=min(max_files, UPLOAD_FORM_MAX_FILES),
            max_fields=min(max_fields, UPLOAD_FORM_MAX_FIELDS),
            max_part_size=min(max_part_size, UPLOAD_FORM_MAX_PART_BYTES),
        )


class UploadRoute(APIRoute):
    """``uploadDocument``'s and ``uploadDocumentVersion``'s route: the operation's handler, given a :class:`_BoundedFormRequest`.

    FastAPI's own way to give one route another request class; the route is declared with it
    (``documents.py``), so no other operation's parsing changes.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def bounded(request: Request) -> Response:
            return await handler(_BoundedFormRequest(request.scope, request.receive))

        return bounded


# ---------------------------------------------------------------------------------------
# the four rules a closed Pydantic model cannot state
# ---------------------------------------------------------------------------------------

_FILE_PART: Final[str] = "file"
_TITLE_PART: Final[str] = "display_title"


def _refuse(message: str, *, field: str, constraint: str) -> DomainError:
    """One refusal of the strict pass. Distinct from ``_refusal`` above, which is the
    body cap's and takes no message."""
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message=message, field=field, constraint=constraint
    )


@dataclass(frozen=True, slots=True)
class CheckedUpload:
    """What the strict pass established about the body, beyond the declared parts."""

    display_title: str | None


async def require_a_strict_multipart_body(request: Request) -> CheckedUpload:
    """Refuse a multipart body the declared schema cannot judge, and fix the one it misreads.

    ``UploadDocumentRequest`` is a closed Pydantic model, so FastAPI already refuses an
    **undeclared part** as ``additionalProperties`` -- the same answer a JSON object's
    undeclared property gets, which is the point. Four things it cannot say, each of which
    the hand-written reader `T-1` retired *did* say, and each of which was a refusal some
    caller could otherwise get as a 500 or, worse, not get at all:

    * **the media type.** A JSON body posted here parses as an empty form, so the model
      reports ``file`` missing. That is true and useless: the caller's mistake is the
      media type and ``Content-Type`` is the field to name.
    * **an empty part name.** ``name=""`` parses, so the parser says nothing; the part
      simply is not one the schema declares and nothing would report it. (An *absent*
      ``name`` is a different case and is refused before this runs -- see
      :class:`BodyCapMiddleware` for the boundary, and ``handlers._STATUS_CODES`` for the
      parser's own refusals.)
    * **a repeated part.** ``FormData`` is a multidict and Pydantic sees only the last
      value, so ``file`` sent twice would be *silently accepted* and the second one
      published. A lenient multipart reader is a security surface; this is the case that
      makes it strict.
    * **a text part that is not text at all.** See :func:`_decoded_title`, which also
      records the one refusal of the retired reader that this transport cannot reconstruct
      and does not pretend to.

    The part name and the filename are **never echoed**. They are caller-controlled text,
    and ``details`` values are screened by the six ``_FORBIDDEN`` patterns in
    ``shared/errors/envelope.py`` -- an echo would turn this caller's 422 into an unhandled
    ``UnsafeDetailValue``, and one carrying no forbidden shape would still reflect the
    caller's own input back out. ``constraint`` is the classifier that replaces it.
    """
    content_type = request.headers.get("content-type") or ""
    if "multipart/form-data" not in content_type.lower():
        raise _refuse(
            "This operation expects a multipart/form-data body.",
            field="Content-Type",
            constraint="media_type",
        )
    # No ``try`` around this: FastAPI has already parsed the form by the time a
    # dependency runs (``fastapi/routing.py:429``), so a ``MultiPartException`` has
    # already become its ``HTTPException(400)`` and is handled in ``handlers.py``. This
    # call gets Starlette's cached ``FormData`` and cannot raise.
    form = await request.form()

    seen: set[str] = set()
    for name, _value in form.multi_items():
        if not name:
            raise _refuse(
                "A multipart part carries no name.",
                field="file",
                constraint="part_name",
            )
        if name in seen:
            raise _refuse(
                "A multipart part is repeated.", field="body", constraint="unique_part"
            )
        seen.add(name)

    uploaded = form.get(_FILE_PART)
    # ``starlette.datastructures.UploadFile``, not ``fastapi.UploadFile``: the parser
    # produces the former and the latter is a *subclass* of it, so the obvious import
    # makes this ``isinstance`` always false and every upload answer "requires a filename".
    if uploaded is not None and (
        not isinstance(uploaded, UploadFile) or not uploaded.filename
    ):
        raise _refuse(
            "The file part requires a filename.", field="file", constraint="filename"
        )

    return CheckedUpload(display_title=_decoded_title(form.get(_TITLE_PART)))


def _decoded_title(value: Any) -> str | None:
    """The ``display_title`` part as Starlette decoded it.

    **The certified reader's UTF-8 refusal is not reconstructible here, and this says so
    rather than approximating it.** ``MultiPartParser.parse`` reads ``charset`` off the
    request's Content-Type and defaults it to ``utf-8``, so a correctly encoded title
    arrives correctly decoded. What Starlette does not do is *refuse*: for bytes that are
    not valid UTF-8, ``_user_safe_decode`` falls back to latin-1 and returns a string. The
    retired reader did ``payload.decode("utf-8")`` and raised
    ``display_title`` / ``encoding`` instead.

    **Why the refusal is not recovered from the decoded string.** Two different requests
    produce the *same* string:

    * ``b"co\xc3\xbbts"`` -- valid UTF-8 -- decodes to ``"coûts"``;
    * ``b"co\xfbts"`` -- not valid UTF-8 -- *falls back* and also gives ``"coûts"``.

    Every character is under ``U+0100`` in both, so re-encoding as latin-1 gives back
    ``b"co\xfbts"`` in both, and that is not valid UTF-8 in both. The two are
    indistinguishable, and an earlier version of this function that refused on that test
    **refused the first one** -- every UTF-8 title made only of Latin-1-range characters,
    which is most titles in French, German or Spanish. That is a far worse regression than
    the one it was trying to prevent, and it is the property ``agent/display-title`` has
    already been fixed for once: *the display title reaches the reviewer who typed it*.

    So the refusal is dropped, deliberately and once, and recorded in
    ``docs/program/reviews/W13-API.md``. The bytes a client sent are no longer available at
    this point -- Starlette has consumed the stream -- and recovering them would mean
    parsing the multipart body a second time in front of the framework, which is a large
    amount of machinery for a malformed title.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        # A part that is itself multipart, or a file part sent under this name. Not a
        # title, and not something to hand to the ingest command.
        raise _refuse(
            "The display_title part could not be decoded.",
            field=_TITLE_PART,
            constraint="encoding",
        )
    return value
