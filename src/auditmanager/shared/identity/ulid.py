"""ULID generation and shape validation for opaque identifiers.

The domain contract (``contracts/domain/v1/identifiers.json``) fixes the identifier
format as ``<prefix>_<ULID>`` where the ULID body is 26 characters of uppercase
Crockford base32.

This module deliberately exposes *generation* and *shape validation* only. It offers
no decoder. Contract rule: "The ULID body must not be decoded by domain or consumer
logic to derive creation time, ownership, ordering or any other business attribute."
Shipping a decoder would make that rule depend on reviewer vigilance, so the
capability does not exist in the codebase at all.
"""

from __future__ import annotations

import os
import time
from typing import Final

# Crockford base32, uppercase, excluding I, L, O and U.
_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

ULID_LENGTH: Final[int] = 26
_TIMESTAMP_BITS: Final[int] = 48
_RANDOM_BITS: Final[int] = 80
_TOTAL_BITS: Final[int] = _TIMESTAMP_BITS + _RANDOM_BITS
_MAX_TIMESTAMP_MS: Final[int] = (1 << _TIMESTAMP_BITS) - 1

_ALPHABET_SET: Final[frozenset[str]] = frozenset(_ALPHABET)


class UlidFormatError(ValueError):
    """A value is not a syntactically valid ULID body."""


def _encode(value: int) -> str:
    if value < 0 or value >= (1 << _TOTAL_BITS):
        raise UlidFormatError("ULID integer value out of range")
    characters = [""] * ULID_LENGTH
    for position in range(ULID_LENGTH - 1, -1, -1):
        characters[position] = _ALPHABET[value & 0x1F]
        value >>= 5
    return "".join(characters)


def new_ulid() -> str:
    """Return a fresh ULID body: 48 bits of millisecond time, 80 bits of randomness.

    Randomness comes from ``os.urandom``. Monotonicity inside a single millisecond
    is deliberately *not* promised: the contract forbids consumers from deriving
    ordering from the body, so guaranteeing it here would invite exactly the
    coupling the contract prohibits.
    """
    timestamp_ms = int(time.time() * 1000)
    if timestamp_ms > _MAX_TIMESTAMP_MS:
        raise UlidFormatError("current time exceeds the 48-bit ULID timestamp range")
    randomness = int.from_bytes(os.urandom(_RANDOM_BITS // 8), "big")
    return _encode((timestamp_ms << _RANDOM_BITS) | randomness)


def is_valid_ulid(value: object) -> bool:
    """True when ``value`` is 26 characters drawn from the Crockford alphabet."""
    if not isinstance(value, str) or len(value) != ULID_LENGTH:
        return False
    return all(character in _ALPHABET_SET for character in value)


def alphabet() -> str:
    """The uppercase Crockford base32 alphabet this module encodes with."""
    return _ALPHABET
