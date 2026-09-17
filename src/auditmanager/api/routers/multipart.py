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

from dataclasses import dataclass
from typing import Any, Final

from fastapi import Request
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException

from auditmanager.api.routers.correlation import current_correlation_id
from auditmanager.api.routers.errors import envelope_response
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "MAX_BODY",
    "BodyCapMiddleware",
    "CheckedUpload",
    "require_a_strict_multipart_body",
]

#: The upload envelope refuses anything larger long before this, but see the module note.
#: 25 MiB is the declared maximum; the slack covers part headers and the boundary.
MAX_BODY: Final[int] = 26 * 1024 * 1024

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


class BodyCapMiddleware:
    """Refuse a body over :data:`MAX_BODY`, or a multipart body with no boundary.

    Two rules, both here for the same reason: they must be settled **before any parser
    reads the body**. The size one because materialising an unbounded body to discover it
    is unbounded is the denial-of-service surface the limit exists to close; the boundary
    one because FastAPI parses a form before it resolves dependencies, so an application
    handler cannot get in front of it.

    The size rule has two checks, and both are needed. ``Content-Length`` is refused up front so an oversized
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
        has_boundary = False
        declared: int | None = None
        for name, value in scope.get("headers", ()):
            lowered = name.lower()
            if lowered == b"content-type":
                is_upload = b"multipart/form-data" in value.lower()
                has_boundary = b"boundary=" in value.lower()
            elif lowered == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None

        if declared is not None and declared > self.limit:
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
