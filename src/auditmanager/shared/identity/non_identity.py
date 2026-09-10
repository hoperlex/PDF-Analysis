"""Correlation and command values that are explicitly **not** entity identities.

They live beside the identity types so the distinction is visible in the import
line rather than buried in a docstring. ``contracts/domain/v1/identifiers.json``
declares every value here with ``is_entity_identity: false``:

* a correlation id is never a foreign key and authorizes nothing;
* an idempotency key is never interpreted as, converted into or stored as a system
  identifier, and never appears in an error envelope;
* a payload fingerprint is a comparison value only.

None of these may be used where an :class:`~auditmanager.shared.identity.ids.OpaqueId`
is expected; they are separate types precisely so that mistake will not type-check
and will not construct.
"""

from __future__ import annotations

import re
from typing import Final, Self

from auditmanager.shared.identity.errors import IdentifierFormatError

#: Contract pattern for both ``correlation_id`` and ``idempotency_key``.
CORRELATION_PATTERN: Final[str] = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
IDEMPOTENCY_KEY_PATTERN: Final[str] = CORRELATION_PATTERN
#: sha256 digest, lowercase hexadecimal.
SHA256_PATTERN: Final[str] = r"^[0-9a-f]{64}$"

_CORRELATION_RE: Final[re.Pattern[str]] = re.compile(CORRELATION_PATTERN)
_SHA256_RE: Final[re.Pattern[str]] = re.compile(SHA256_PATTERN)


class _PatternValue:
    """A validated, immutable string value that is not an entity identity."""

    __slots__ = ("_value",)

    _regex: re.Pattern[str] = _CORRELATION_RE
    _label: str = "value"

    def __init__(self, value: str) -> None:
        if not isinstance(value, str) or not type(self)._regex.match(value):
            raise IdentifierFormatError(
                f"{type(self)._label} must match {type(self)._regex.pattern}"
            )
        object.__setattr__(self, "_value", value)

    @classmethod
    def parse(cls, value: str) -> Self:
        return cls(value)

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._value == other._value  # type: ignore[attr-defined]

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")


class CorrelationId(_PatternValue):
    """Correlates one externally visible request with its diagnostic record.

    Present in every error envelope. Never a foreign key, never authorizes anything
    and never encodes subject, tenant or path information.
    """

    _label = "correlation_id"


class IdempotencyKey(_PatternValue):
    """A client-supplied command key.

    Safe-detail rule from the frozen catalog: ``idempotency_key`` is a *forbidden*
    error-envelope detail key. This type must therefore never be serialized into an
    envelope; ``__repr__`` is for logs inside the trust boundary only.
    """

    _label = "idempotency_key"


class Sha256(_PatternValue):
    """A lowercase hexadecimal sha256 digest. A checksum is a verification value,
    never an identity, and never a foreign key."""

    _regex = _SHA256_RE
    _label = "sha256"


class PayloadFingerprint(Sha256):
    """sha256 over the RFC 8785 (JCS) serialization of a normalized command payload.

    Distinguishes an idempotent repeat from a same-key, different-payload conflict.
    A comparison value only: never an identity, never returned in an envelope.
    """

    _label = "payload_fingerprint"
