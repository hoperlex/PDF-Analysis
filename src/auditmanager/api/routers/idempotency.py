"""The ``Idempotency-Key`` header, and path-parameter identity validation.

``P02_SEAMS.md`` section 7: *every write takes a required* ``Idempotency-Key`` *header,
passed through to the owning command handler and never re-derived in the router.* Both
halves matter. The header is **required**, so a write without one is refused before
anything is attempted; and the router never hashes a payload, never derives a key from
a body and never invents one, because a key the client did not choose cannot make the
client's retry idempotent.

The key is also a **forbidden envelope detail key**. It never appears in a response
body, in a header or in an error envelope -- the frozen document says so on the
parameter itself.
"""

from __future__ import annotations

import re
from typing import Callable, Final, TypeVar

from auditmanager.api.routers.http import Request
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "IDEMPOTENCY_HEADER",
    "require_idempotency_key",
    "require_path_identity",
]

IDEMPOTENCY_HEADER: Final[str] = "Idempotency-Key"

#: Exactly ``#/components/schemas/IdempotencyKey``.
_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def require_idempotency_key(request: Request) -> str:
    """The caller's command key, or ``validation_failed``.

    Never falls back to a generated value. A generated key would make every retry a
    fresh command, which is precisely the failure the header exists to prevent, and it
    would do so silently.
    """
    supplied = request.headers.get(IDEMPOTENCY_HEADER)
    if supplied is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="This operation requires an Idempotency-Key header.",
            field="Idempotency-Key",
            constraint="required",
        )
    if not _KEY_PATTERN.match(supplied):
        # The offending value is not echoed: it is the caller's own opaque string and
        # a forbidden detail key.
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The Idempotency-Key header is not of the declared form.",
            field="Idempotency-Key",
            constraint="pattern",
        )
    return supplied


T = TypeVar("T")


def require_path_identity(
    raw: str,
    *,
    parse: Callable[[str], T],
    aggregate_type: str,
) -> T:
    """Validate a path parameter with its contract value type.

    ``auditmanager.shared.identity`` raises ``IdentifierFormatError`` /
    ``IdentifierPrefixError`` -- ``ValueError`` subclasses, not ``DomainError`` -- so
    the edge is where they become typed.

    The answer is ``not_found``, not ``validation_failed``. A well-formed identity that
    does not exist and a malformed one must be indistinguishable from outside: the
    frozen ``NotFound`` response says the surface "never reveals the existence of a
    resource the caller may not see", and answering ``422`` for a bad prefix while
    answering ``404`` for a good one would leak exactly that. It also stops a caller
    using the API as an oracle for which identifier shapes are real.
    """
    try:
        return parse(raw)
    except ValueError:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate_type) from None
