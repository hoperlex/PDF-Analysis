"""``X-Correlation-Id``: present on every response, success or failure.

``docs/program/P02_SEAMS.md`` section 7: *every response carries*
``X-Correlation-Id``. The frozen document adds the other half -- *a caller may supply
one on the request; the edge assigns one when the caller does not*.

A supplied value is only honoured when it matches the frozen ``CorrelationId``
pattern. An unusable one is replaced rather than refused: a correlation id addresses a
diagnostic record and authorises nothing, so failing a whole request over its shape
would trade a working answer for a cosmetic complaint. It is never a foreign key and
never an identity -- ``P02_SEAMS.md`` section 2.2 lists it among the non-identities --
so nothing downstream may parse it.
"""

from __future__ import annotations

import re
import secrets
from typing import Final

from auditmanager.api.routers.http import Request

__all__ = [
    "CORRELATION_HEADER",
    "CORRELATION_PATTERN",
    "new_correlation_id",
    "resolve_correlation_id",
]

CORRELATION_HEADER: Final[str] = "X-Correlation-Id"

#: Exactly ``#/components/schemas/CorrelationId`` of contracts/api/v1/openapi.json.
CORRELATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
)


def new_correlation_id() -> str:
    """A fresh correlation id.

    ``token_hex`` rather than a counter or a timestamp: the value is opaque, and one
    that encoded a request ordinal would be a server-side sequence exposed to a client.
    """
    return f"cid-{secrets.token_hex(16)}"


def resolve_correlation_id(request: Request) -> str:
    """The caller's correlation id when it is usable, otherwise a fresh one."""
    supplied = request.headers.get(CORRELATION_HEADER)
    if supplied is not None and CORRELATION_PATTERN.match(supplied):
        return supplied
    return new_correlation_id()
