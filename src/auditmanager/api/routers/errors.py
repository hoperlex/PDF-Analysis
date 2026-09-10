"""The error middleware: every failure leaves this edge as one typed envelope.

``docs/program/P02_SEAMS.md`` section 3.2 gives this module its whole job::

    B6's error middleware turns a DBAPIError carrying one of these into the envelope.
    Nothing else in the stack should be catching them: a refusal here means the caller
    asked for something the contract forbids, and the answer is the typed code.

Four rules are structural here rather than reviewed.

**Map on the SQLSTATE, never on the message text.** The three custom SQLSTATEs of the
P02 migration head -- ``AM001`` an undeclared transition or a non-initial insert,
``AM002`` UPDATE or DELETE on an append-only ledger, ``AM003`` UPDATE or DELETE on an
immutable row -- all report ``state_transition_not_allowed``. The mapping is read from
:data:`auditmanager.shared.db.schema.SQLSTATE_TO_CATALOG_CODE`; this module does not
restate it, because a restatement is a second place to be wrong. The SQLSTATE itself is
read with :func:`auditmanager.documents.sqlstate_of`, which reads the driver's
structured field and never the prose.

**``retryable`` is pinned by the catalog.** It is not a parameter of
:func:`auditmanager.shared.errors.build` at all, so no call site here can disagree with
the catalog or infer it from an HTTP status. The HTTP status travels the other way:
it is read *from* the code, by :attr:`ErrorCode.http_status`.

**The message never carries the driver's prose.** A PostgreSQL exception message can
contain a row value, a table name or a fragment of SQL. Nothing from ``exc`` is ever
rendered into the envelope; the message is the catalog summary, and the only details
are the ones a handler supplied for itself.

**An unmapped failure is ``internal_error``.** Not the driver's SQLSTATE, not the
exception class name, not a message: those stay in the diagnostic record that the
correlation id addresses.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Final, Mapping

from sqlalchemy.exc import DBAPIError

from auditmanager.documents import sqlstate_of
from auditmanager.shared.db.schema import SQLSTATE_TO_CATALOG_CODE
from auditmanager.shared.errors import DomainError, ErrorCode, build
from auditmanager.api.routers.correlation import CORRELATION_HEADER, resolve_correlation_id
from auditmanager.api.routers.http import (
    MethodNotAllowed,
    NoRoute,
    Request,
    Response,
    Router,
    json_response,
)

__all__ = [
    "CORRELATION_HEADER",
    "dispatch",
    "envelope_response",
    "error_code_for",
    "to_domain_error",
]

#: 405 has no catalog code of its own. The surface declares twelve operations and no
#: other method on any of their paths, so a method the document does not declare is
#: simply not a resource here.
_METHOD_NOT_ALLOWED_CODE: Final[ErrorCode] = ErrorCode.NOT_FOUND


def error_code_for(exc: BaseException) -> ErrorCode | None:
    """The catalog code a database refusal reports, or ``None`` when it is not ours.

    Reads the SQLSTATE out of the driver's structured diagnostics and looks it up in
    the shared kernel's map. A refusal that is not one of the three custom SQLSTATEs is
    a genuine integrity or availability fault, not a contract refusal, and is left for
    the caller of this function to classify.
    """
    sqlstate = sqlstate_of(exc)
    if sqlstate is None:
        return None
    code = SQLSTATE_TO_CATALOG_CODE.get(sqlstate)
    return ErrorCode(code) if code is not None else None


def to_domain_error(exc: BaseException) -> DomainError:
    """Classify any exception into a typed failure.

    * a :class:`DomainError` is already typed and passes through unchanged;
    * a :class:`DBAPIError` carrying ``AM001``, ``AM002`` or ``AM003`` becomes
      ``state_transition_not_allowed``;
    * everything else becomes ``internal_error``, carrying nothing from the original.
    """
    if isinstance(exc, DomainError):
        return exc
    if isinstance(exc, DBAPIError):
        code = error_code_for(exc)
        if code is not None:
            # No details: this middleware does not know which machine the handler was
            # asking about, and it will not scrape one out of the driver's message.
            return DomainError(code)
    return DomainError(ErrorCode.INTERNAL_ERROR)


def envelope_response(error: DomainError, correlation_id: str) -> Response:
    """Render a typed failure as the frozen ``ErrorEnvelope``.

    ``retryable`` comes from the catalog through
    :meth:`auditmanager.shared.errors.ErrorEnvelope.retryable`, and the HTTP status
    from :attr:`ErrorCode.http_status`. Neither is derived from the other.
    """
    envelope = error.envelope(correlation_id)
    payload = json.dumps(envelope.as_dict(), ensure_ascii=False).encode("utf-8")
    return json_response(envelope.http_status, payload)


def dispatch(
    router: Router,
    request: Request,
    *,
    correlation_id: str | None = None,
) -> Response:
    """Resolve one request through ``router`` and guarantee a typed answer.

    Every path out of this function -- a match, a miss, a handler's typed refusal, a
    database refusal, an unclassified fault -- produces a response carrying
    ``X-Correlation-Id``. There is no route through it that returns an untyped body.
    """
    resolved = correlation_id or resolve_correlation_id(request)
    try:
        route, bound = router.match(request)
    except MethodNotAllowed:
        return envelope_response(
            DomainError(_METHOD_NOT_ALLOWED_CODE), resolved
        ).with_header(CORRELATION_HEADER, resolved)
    except NoRoute:
        return envelope_response(DomainError(ErrorCode.NOT_FOUND), resolved).with_header(
            CORRELATION_HEADER, resolved
        )

    try:
        response = route.handler(bound)
    except BaseException as exc:  # noqa: BLE001 - the edge classifies everything
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        response = envelope_response(to_domain_error(exc), resolved)

    if response.header(CORRELATION_HEADER) is None:
        response = response.with_header(CORRELATION_HEADER, resolved)
    return response


def guarded(
    handler: Callable[[Request], Response],
    **details: Any,
) -> Callable[[Request], Response]:
    """Wrap a handler so its database refusals carry the caller's own ``details``.

    The middleware itself adds no details, because it does not know what the handler
    was asking the database for. A handler that *does* know -- "I was moving an
    ``audit_run`` from ``published``" -- wraps itself with this and supplies them; the
    envelope screens each key against the reported code's ``safe_detail_keys``.
    """

    def run(request: Request) -> Response:
        try:
            return handler(request)
        except DomainError:
            raise
        except DBAPIError as exc:
            code = error_code_for(exc)
            if code is None:
                raise
            raise DomainError(code, **details) from exc

    return run


def decode_json_object(body: bytes) -> Mapping[str, Any]:
    """Parse a request body that must be one JSON object.

    Anything else -- malformed bytes, a bare array, a string, ``null`` -- is
    ``validation_failed``. The parse error itself never reaches the caller: a JSON
    decoder's message quotes the offending input.
    """
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The request body is not valid JSON.",
        ) from exc
    if not isinstance(parsed, dict):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The request body must be a JSON object.",
        )
    return parsed
