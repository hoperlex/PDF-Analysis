"""``X-Correlation-Id``: present on every response, success or failure.

``docs/program/P02_SEAMS.md`` section 7: *every response carries* ``X-Correlation-Id``. The
frozen document adds the other half -- *a caller may supply one on the request; the edge
assigns one when the caller does not*.

A supplied value is only honoured when it matches the frozen ``CorrelationId`` pattern. An
unusable one is replaced rather than refused: a correlation id addresses a diagnostic record
and authorises nothing, so failing a whole request over its shape would trade a working
answer for a cosmetic complaint. It is never a foreign key and never an identity --
``P02_SEAMS.md`` section 2.2 lists it among the non-identities -- so nothing downstream may
parse it.

**Why a pure-ASGI middleware and not a FastAPI dependency.** The header has to be on
*every* response, including the ones no path operation produces: a request to a path the
document does not declare, a method it does not declare, and any failure raised before or
after a handler runs. A dependency cannot reach those. This wrapper sits outside the router
and outside the exception middleware, so there is no path through the application that can
answer without it.
"""

from __future__ import annotations

import re
import secrets
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Final, MutableMapping

__all__ = [
    "CORRELATION_HEADER",
    "CORRELATION_PATTERN",
    "CorrelationMiddleware",
    "current_correlation_id",
    "new_correlation_id",
    "resolve_correlation_id",
]

CORRELATION_HEADER: Final[str] = "X-Correlation-Id"

_HEADER_BYTES: Final[bytes] = CORRELATION_HEADER.lower().encode("latin-1")

#: Exactly ``#/components/schemas/CorrelationId`` of contracts/api/v1/openapi.json.
CORRELATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
)

#: The id resolved for the request being served, readable by a handler or an exception
#: handler without threading it through every signature. A ``ContextVar`` rather than a
#: module global because the value is per-request: a global would be a cross-request leak
#: the moment two requests overlap, and an id that addressed the wrong diagnostic record
#: is worse than no id at all.
_CURRENT: ContextVar[str] = ContextVar("auditmanager_correlation_id")


def new_correlation_id() -> str:
    """A fresh correlation id.

    ``token_hex`` rather than a counter or a timestamp: the value is opaque, and one that
    encoded a request ordinal would be a server-side sequence exposed to a client.
    """
    return f"cid-{secrets.token_hex(16)}"


def resolve_correlation_id(supplied: str | None) -> str:
    """The caller's correlation id when it is usable, otherwise a fresh one."""
    if supplied is not None and CORRELATION_PATTERN.match(supplied):
        return supplied
    return new_correlation_id()


def current_correlation_id() -> str:
    """The id of the request being served, or a fresh one outside a request.

    The fallback is never reached through the ASGI app -- the middleware sets the value
    before anything else runs -- and exists so that a direct unit call cannot raise a
    ``LookupError`` in place of the failure it was testing.
    """
    try:
        return _CURRENT.get()
    except LookupError:
        return new_correlation_id()


class CorrelationMiddleware:
    """Resolve the id, publish it, and put it on the way out.

    Appends rather than overwrites: a response that already carries the header wrote it
    deliberately and keeps it. Nothing in this application does, which is why the header is
    last in every recorded response.
    """

    __slots__ = ("app",)

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied: str | None = None
        for name, value in scope.get("headers", ()):
            if name.lower() == _HEADER_BYTES:
                supplied = value.decode("latin-1")
                break
        resolved = resolve_correlation_id(supplied)
        token = _CURRENT.set(resolved)

        async def send_with_header(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", ()))
                if not any(name.lower() == _HEADER_BYTES for name, _ in headers):
                    headers.append(
                        (
                            CORRELATION_HEADER.encode("latin-1"),
                            resolved.encode("latin-1"),
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            _CURRENT.reset(token)
