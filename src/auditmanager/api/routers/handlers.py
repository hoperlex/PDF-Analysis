"""Where FastAPI's own failures stop being FastAPI's.

**This module is the single highest-risk item of wave 13**, and the reason is not the
models. Four certifications and the response baseline assert *which rule refused*, not
merely that something did. FastAPI's default answer to a bad request is
``422 {"detail": [{"type": "string_too_short", "loc": ["body", "name"], ...}]}`` and its
default answer to an undeclared method is ``405 {"detail": "Method Not Allowed"}``. Either
reaching a client is a criterion-10 regression wearing a status code that looks right.

So every exception this application can raise is registered here, and every one of them
leaves as an ``ErrorEnvelope`` built by
:func:`~auditmanager.api.routers.errors.envelope_response`:

============================= ==========================================================
raised by                     mapped to
============================= ==========================================================
``DomainError``               itself -- it is already typed, and passes through unchanged
``RequestValidationError``    the catalog, by :data:`_REFUSALS` and the rules below
``StarletteHTTPException``    the catalog, by :data:`_STATUS_CODES` -- 405 becomes **404**
anything else                 ``internal_error``, or the SQLSTATE's code, carrying nothing
============================= ==========================================================

**Every expectation in this module is a literal**, including the catalog messages and the
``details`` keys. ``OPERATING_CONSTRAINTS.md`` section 12 records three failures of the
opposite here, one of them the integrator's: a refusal whose message is computed from the
thing it is describing cannot tell you that the thing moved.
"""

from __future__ import annotations

from typing import Any, Final, Mapping, Sequence

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from auditmanager.api.routers.correlation import current_correlation_id
from auditmanager.api.routers.errors import (
    METHOD_NOT_ALLOWED_CODE,
    envelope_response,
    to_domain_error,
)
from auditmanager.api.routers.wire import WireResponse
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AGGREGATE_OF_PATH_PARAMETER",
    "install_exception_handlers",
    "on_domain_error",
    "on_http_exception",
    "on_request_validation_error",
    "on_unhandled",
]


# ---------------------------------------------------------------------------------------
# the literals
# ---------------------------------------------------------------------------------------

#: A malformed path identity answers ``404 not_found`` carrying the aggregate it addressed,
#: never ``422``. The frozen ``NotFound`` response says this surface "never reveals the
#: existence of a resource the caller may not see", and answering 422 for a bad prefix while
#: answering 404 for a well-formed identity that does not exist would leak exactly that -- a
#: caller could use the API as an oracle for which identifier shapes are real.
#: ``records/30-getRunStatus.not_found.json`` pins the 404 and the ``aggregate_type``.
AGGREGATE_OF_PATH_PARAMETER: Final[Mapping[str, str]] = {
    "project_uid": "Project",
    "version_uid": "DocumentVersion",
    "run_id": "AuditRun",
    "finding_uid": "Finding",
}

#: The contract's spelling of each header this surface reads, keyed by the lower-cased name
#: FastAPI reports in ``loc``. HTTP folds header case; an error envelope does not, and the
#: baseline records ``"field": "Idempotency-Key"``.
_HEADER_FIELD: Final[Mapping[str, str]] = {
    "idempotency-key": "Idempotency-Key",
    "x-correlation-id": "X-Correlation-Id",
    "range": "Range",
}

#: Pydantic's error ``type`` to this surface's ``details.constraint``. A pydantic type that
#: is not in here falls back to ``_DEFAULT_CONSTRAINT`` rather than being echoed: the
#: vocabulary a client sees is this contract's, not the validation library's.
_CONSTRAINT_OF_PYDANTIC_TYPE: Final[Mapping[str, str]] = {
    "missing": "required",
    "extra_forbidden": "additionalProperties",
    "string_pattern_mismatch": "pattern",
    "string_too_short": "length",
    "string_too_long": "length",
    "string_type": "type",
    "enum": "enum",
    "literal_error": "enum",
    "int_parsing": "integer",
    "int_type": "integer",
    "greater_than_equal": "range",
    "less_than_equal": "range",
    "greater_than": "range",
    "less_than": "range",
    "too_short": "length",
    "too_long": "length",
    "bool_parsing": "type",
    "bool_type": "type",
    "datetime_parsing": "format",
    "datetime_type": "format",
}
_DEFAULT_CONSTRAINT: Final[str] = "type"

#: The catalog message for each refusal this edge raises for itself, as a literal.
_BODY_NOT_JSON: Final[str] = "The request body is not valid JSON."
_BODY_NOT_OBJECT: Final[str] = "The request body must be a JSON object."
_BODY_UNDECLARED_PROPERTY: Final[str] = (
    "The request body carries a property the schema does not declare."
)
_FORM_UNDECLARED_PART: Final[str] = (
    "The upload carries a part the schema does not declare."
)
_FILE_REQUIRED: Final[str] = "The upload requires a file part."
_BODY_NOT_READABLE: Final[str] = "The multipart body could not be read."
_IDEMPOTENCY_REQUIRED: Final[str] = (
    "This operation requires an Idempotency-Key header."
)
_IDEMPOTENCY_MALFORMED: Final[str] = (
    "The Idempotency-Key header is not of the declared form."
)
_HEADER_MALFORMED: Final[str] = "The {field} header is not of the declared form."
_QUERY_REFUSED: Final[str] = "The {field} parameter is not of the declared form."
_LIMIT_NOT_INTEGER: Final[str] = "The limit parameter must be an integer."
_LIMIT_OUT_OF_RANGE: Final[str] = "The limit parameter must be between 1 and 200."
_CURSOR_MALFORMED: Final[str] = (
    "The cursor parameter is not a continuation token from this API."
)
_ENUM_FILTER: Final[str] = "The {field} filter must be one of: {allowed}."
_BODY_PROPERTY_REFUSED: Final[str] = (
    "The {field} property of the request body is not of the declared form."
)

#: ``startRun`` is the one operation whose *declared analysis inputs* are the thing that can
#: be wrong, and the frozen ``RunInputInvalid`` response describes exactly that split: a
#: malformed body is ``validation_failed``, a body that names something that is not an
#: analysis input is ``analysis_input_invalid``. Keyed by ``(operationId, property)``.
_ANALYSIS_INPUTS: Final[Mapping[tuple[str, str], str]] = {
    ("startRun", "version_uid"): (
        "The run must declare the version_uid of a published version."
    ),
}

#: The enum vocabularies, written out, so a refusal names the values the contract declares
#: rather than the ones a Python enum happens to carry today.
_ENUM_VALUES: Final[Mapping[str, str]] = {
    "category": "explicit_placeholder, internal_contradiction",
    "verdict": "accepted, needs_manual_review, pending, rejected",
    "event_type": "accept, comment, reject, revoke",
    "provider_mode": "live, recorded",
}

#: An HTTP status Starlette raises for itself, and the catalog code that answers it. 405 is
#: deliberately 404's code: see ``METHOD_NOT_ALLOWED_CODE``.
_STATUS_CODES: Final[Mapping[int, ErrorCode]] = {
    400: ErrorCode.VALIDATION_FAILED,
    401: ErrorCode.AUTHENTICATION_REQUIRED,
    403: ErrorCode.PERMISSION_DENIED,
    404: ErrorCode.NOT_FOUND,
    405: METHOD_NOT_ALLOWED_CODE,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_FAILED,
    503: ErrorCode.DEPENDENCY_UNAVAILABLE,
}


# ---------------------------------------------------------------------------------------
# the handlers
# ---------------------------------------------------------------------------------------


def on_domain_error(request: Request, exc: DomainError) -> WireResponse:
    """A typed failure renders itself. The status comes from the code, never the reverse."""
    del request
    return envelope_response(exc, current_correlation_id())


def on_http_exception(request: Request, exc: StarletteHTTPException) -> WireResponse:
    """Starlette's own refusals, re-stated in this contract's vocabulary.

    ``exc.detail`` is deliberately dropped. It is the framework's prose -- *"Method Not
    Allowed"*, *"Not Found"* -- and the envelope carries the catalog summary instead, so a
    client reads one vocabulary and not two.
    """
    del request
    if exc.status_code == 400:
        # FastAPI raises exactly one 400 in this application: ``routing.py:470`` wraps any
        # failure of ``await request.form()`` in ``HTTPException(400, "There was an error
        # parsing the body")``. Starlette's parser raises for a missing part name, a part
        # over its size bound, or too many parts or files -- the one remaining cause, a
        # missing boundary, is refused on the header before this and reports
        # ``constraint: boundary``. The classifier here is the family, because the cause is
        # only distinguishable from the parser's own prose and this contract does not map
        # refusals on another library's message text.
        return envelope_response(
            DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=_BODY_NOT_READABLE,
                field="body",
                constraint="readable_multipart",
            ),
            current_correlation_id(),
        )
    code = _STATUS_CODES.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    return envelope_response(DomainError(code), current_correlation_id())


def on_request_validation_error(
    request: Request, exc: RequestValidationError
) -> WireResponse:
    """Map FastAPI's validation report onto the catalog, first error wins.

    First error rather than all of them, because the envelope reports **one** refusal with
    one ``field`` and one ``constraint``: that is the shape four certifications read, and a
    list of them is the framework's shape, not this contract's. The remaining errors are
    still a failure -- the request is refused either way -- and a caller who fixes the first
    is told about the second on the next attempt.
    """
    errors = exc.errors()
    if not errors:  # pragma: no cover - FastAPI does not raise an empty report
        return envelope_response(
            DomainError(ErrorCode.VALIDATION_FAILED), current_correlation_id()
        )
    return envelope_response(
        _refusal(errors[0], _operation_id(request), _is_multipart(request)),
        current_correlation_id(),
    )


def on_unhandled(request: Request, exc: Exception) -> WireResponse:
    """Anything that got this far is classified and stripped.

    :func:`~auditmanager.api.routers.errors.to_domain_error` reads a database refusal's
    SQLSTATE and reports nothing else -- not the driver's message, not the exception class,
    not the SQLSTATE itself. Those stay in the diagnostic record the correlation id
    addresses.
    """
    del request
    return envelope_response(to_domain_error(exc), current_correlation_id())


def install_exception_handlers(app: Any) -> None:
    """Register all four on one application.

    A function rather than four calls at the wiring site, so that a second application --
    the health plane, a test's miniature app -- cannot be built with three of them.
    """
    app.add_exception_handler(DomainError, on_domain_error)
    app.add_exception_handler(RequestValidationError, on_request_validation_error)
    app.add_exception_handler(StarletteHTTPException, on_http_exception)


# ---------------------------------------------------------------------------------------
# the mapping
# ---------------------------------------------------------------------------------------


def _operation_id(request: Request) -> str | None:
    """The ``operationId`` being served, when a route matched.

    A validation error is raised after routing, so there is always a route -- but the
    lookup is defensive because a handler that raised ``AttributeError`` while explaining
    a refusal would replace a 422 with a 500.
    """
    route = request.scope.get("route")
    return getattr(route, "operation_id", None)


def _is_multipart(request: Request) -> bool:
    """Whether the refused body was the multipart upload.

    FastAPI reports a form field's location as ``("body", <part>)``, exactly as it reports a
    JSON property -- the two are indistinguishable from the error alone, and the contract
    calls one a *part* and the other a *property*. ``records/26`` pins *"The upload carries a
    part the schema does not declare."* and ``records/23-25`` pin the property sentence, so
    the two have to be told apart, and the request's own media type is what tells them.
    """
    return "multipart/form-data" in (request.headers.get("content-type") or "").lower()


def _refusal(
    error: Mapping[str, Any], operation: str | None, is_multipart: bool = False
) -> DomainError:
    """One pydantic error, as this contract's refusal."""
    location: Sequence[Any] = tuple(error.get("loc", ()))
    kind = str(error.get("type", ""))
    where = str(location[0]) if location else "body"
    name = str(location[-1]) if len(location) > 1 else ""
    constraint = _CONSTRAINT_OF_PYDANTIC_TYPE.get(kind, _DEFAULT_CONSTRAINT)

    if where == "path":
        # 404, and no `validation_failed`: see AGGREGATE_OF_PATH_PARAMETER.
        aggregate = AGGREGATE_OF_PATH_PARAMETER.get(name)
        if aggregate is None:
            return DomainError(ErrorCode.NOT_FOUND)
        return DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate)

    if where == "header":
        field = _HEADER_FIELD.get(name.lower(), name)
        if field == "Idempotency-Key":
            message = (
                _IDEMPOTENCY_REQUIRED if kind == "missing" else _IDEMPOTENCY_MALFORMED
            )
        else:
            message = _HEADER_MALFORMED.format(field=field)
        # The offending value is never echoed: it is the caller's own opaque string, and
        # `Idempotency-Key` is a forbidden envelope detail key on the parameter itself.
        return DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=message,
            field=field,
            constraint=constraint,
        )

    if where == "query":
        return _query_refusal(name, kind, constraint)

    if where == "body" and is_multipart:
        where = "form"

    if kind == "extra_forbidden":
        # A closed schema. The offending property name is **not** echoed -- it is
        # caller-controlled text, and `details` values are screened by the six `_FORBIDDEN`
        # patterns in `shared/errors/envelope.py`, which would turn this caller's 422 into
        # an unhandled `UnsafeDetailValue`. `B6` shipped the echo and a property named
        # `/etc/passwd` came back inside the envelope; `constraint` is the classifier that
        # replaced it.
        return DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=_FORM_UNDECLARED_PART if where == "form" else _BODY_UNDECLARED_PROPERTY,
            field="body",
            constraint="additionalProperties",
        )

    if where == "form":
        if name == "file" and kind == "missing":
            return DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=_FILE_REQUIRED,
                field="file",
                constraint="required",
            )
        return DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=_BODY_PROPERTY_REFUSED.format(field=name or "body"),
            field=name or "body",
            constraint=constraint,
        )

    return _body_refusal(name, kind, constraint, operation)


def _query_refusal(name: str, kind: str, constraint: str) -> DomainError:
    """``limit``, ``cursor`` and the two closed-enum filters.

    A filter value outside its enum is refused rather than answered with an empty page. An
    empty page reads as "this run has no findings of that kind", which is a different and
    wrong answer to "that kind does not exist".
    """
    if name == "limit":
        message = _LIMIT_NOT_INTEGER if constraint == "integer" else _LIMIT_OUT_OF_RANGE
        return DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=message,
            field="limit",
            constraint=constraint,
        )
    if name == "cursor":
        return DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=_CURSOR_MALFORMED,
            field="cursor",
            constraint="format",
        )
    allowed = _ENUM_VALUES.get(name)
    if allowed is not None:
        return DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=_ENUM_FILTER.format(field=name, allowed=allowed),
            field=name,
            constraint="enum",
        )
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=_QUERY_REFUSED.format(field=name),
        field=name,
        constraint=constraint,
    )


def _body_refusal(
    name: str, kind: str, constraint: str, operation: str | None
) -> DomainError:
    """A JSON request body: malformed bytes, a non-object, or one property.

    The split between ``validation_failed`` and ``analysis_input_invalid`` is the frozen
    ``RunInputInvalid`` response's, and it is the only place an operation's identity changes
    the code.
    """
    if kind in ("json_invalid", "value_error.jsondecode"):
        return DomainError(ErrorCode.VALIDATION_FAILED, message=_BODY_NOT_JSON)
    if not name or kind in ("model_attributes_type", "dict_type", "model_type"):
        return DomainError(ErrorCode.VALIDATION_FAILED, message=_BODY_NOT_OBJECT)

    analysis_input = _ANALYSIS_INPUTS.get((operation or "", name))
    if analysis_input is not None:
        # No `field`/`constraint`: `analysis_input_invalid` declares neither in its
        # `safe_detail_keys`, and the envelope screen refuses a key the code does not
        # declare rather than dropping it quietly.
        return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message=analysis_input)

    allowed = _ENUM_VALUES.get(name)
    if allowed is not None and constraint == "enum":
        return DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"{name} must be one of: {allowed}.",
            field=name,
            constraint="enum",
        )
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=_BODY_PROPERTY_REFUSED.format(field=name),
        field=name,
        constraint=constraint,
    )


# ---------------------------------------------------------------------------------------
# the last resort
# ---------------------------------------------------------------------------------------


class FailureEnvelopeMiddleware:
    """The one path out that no handler registration can miss.

    Starlette's ``ExceptionMiddleware`` answers only the exception classes registered with
    it; anything else reaches ``ServerErrorMiddleware``, which sends **its own** 500 body
    and re-raises. That body is HTML in debug mode and ``"Internal Server Error"``
    otherwise, and neither is an ``ErrorEnvelope``.

    This wrapper sits *inside* the correlation middleware and *outside* the exception
    middleware, so anything the registrations do not cover -- a ``DBAPIError`` carrying one
    of the three custom SQLSTATEs, a genuine bug -- still leaves as one typed envelope
    carrying ``X-Correlation-Id``. It also declines to re-raise: a client is owed an answer,
    and the diagnostic record is what the correlation id addresses.

    It only answers when the response has not started. A failure half-way through a body is
    a truncated response, and writing an envelope after the headers have gone would corrupt
    it rather than explain it.
    """

    __slots__ = ("app",)

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = False

        async def watched(message: Any) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, watched)
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:  # noqa: BLE001 - the edge classifies everything
            if started:
                raise
            response = envelope_response(to_domain_error(exc), current_correlation_id())
            await response(scope, receive, send)
