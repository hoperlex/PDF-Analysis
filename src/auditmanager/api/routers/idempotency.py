"""The ``Idempotency-Key`` header, declared as a parameter of every write.

``P02_SEAMS.md`` section 7: *every write takes a required* ``Idempotency-Key`` *header,
passed through to the owning command handler and never re-derived in the router.* Both
halves matter. The header is **required**, so a write without one is refused before anything
is attempted; and the router never hashes a payload, never derives a key from a body and
never invents one, because a key the client did not choose cannot make the client's retry
idempotent.

The key is also a **forbidden envelope detail key**. It never appears in a response body, in
a header or in an error envelope -- the frozen document says so on the parameter itself, and
that is why the refusals below report a classifier and never the offending value.

**What changed under `T-1`.** This was a function taking the whole request and reading the
header out of it. It is now a FastAPI dependency whose signature *is* the contract's
``#/components/parameters/IdempotencyKey``: required, ``in: header``, schema
``$ref: IdempotencyKey``. The refusals did not move -- they are raised by the
``RequestValidationError`` handler in :mod:`auditmanager.api.routers.handlers`, which maps
the framework's error onto the catalog rather than letting its body reach a client.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import Depends, Header

from auditmanager.api.schemas import models

__all__ = [
    "IDEMPOTENCY_HEADER",
    "IdempotencyKeyParam",
    "RequiredIdempotencyKey",
    "require_idempotency_key",
]

IDEMPOTENCY_HEADER: Final[str] = "Idempotency-Key"

#: The declared parameter. ``alias`` is the contract's own spelling: FastAPI would otherwise
#: derive ``idempotency-key`` from the argument name, which is the same header to every
#: client and proxy (RFC 9110 section 5.1) but not the same string in a document diff.
IdempotencyKeyParam = Annotated[
    models.IdempotencyKey, Header(alias=IDEMPOTENCY_HEADER)
]


def require_idempotency_key(key: IdempotencyKeyParam) -> str:
    """The caller's command key.

    Never falls back to a generated value. A generated key would make every retry a fresh
    command, which is precisely the failure the header exists to prevent, and it would do so
    silently. An absent or malformed one never reaches this body: the parameter is declared
    required and constrained, so FastAPI refuses first and
    :func:`~auditmanager.api.routers.handlers.on_request_validation_error` turns that
    refusal into ``validation_failed`` with ``field: Idempotency-Key``.
    """
    return key


#: What a write's signature asks for. The dependency is the contract's parameter; the
#: annotation is how the four writes say "and this operation takes one".
RequiredIdempotencyKey = Annotated[str, Depends(require_idempotency_key)]
