"""One vector's bytes: float32, big-endian, 1024 values, L2 norm 1.

Every phase uses this one representation. The checkpoint files and ``embed-texts`` carry it
base64-encoded, ``norm_embedding.embedding_sha256`` is SHA-256 over it, and the pgvector
literal is printed from it with nine significant digits, which round-trips float32 exactly.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import math
import struct
from collections.abc import Sequence

from .profile import DIMENSIONS, UNIT_NORM_TOLERANCE

_FORMAT = f"!{DIMENSIONS}f"
VECTOR_BYTES = struct.calcsize(_FORMAT)


class VectorRefused(ValueError):
    """A vector is not 1024 finite float32 values of unit L2 norm."""


def pack(values: Sequence[float]) -> bytes:
    """Round to float32 and pack, refusing a wrong dimension, a non-finite value or a norm ≠ 1."""
    if len(values) != DIMENSIONS:
        raise VectorRefused(f"a vector has {DIMENSIONS} dimensions, got {len(values)}")
    try:
        packed = struct.pack(_FORMAT, *(float(value) for value in values))
    except (OverflowError, TypeError, ValueError, struct.error) as exc:
        raise VectorRefused("a vector value is not a finite float32") from exc
    require_unit(packed)
    return packed


def unpack(packed: bytes) -> tuple[float, ...]:
    if len(packed) != VECTOR_BYTES:
        raise VectorRefused(f"a packed vector has {VECTOR_BYTES} bytes, got {len(packed)}")
    return struct.unpack(_FORMAT, packed)


def require_unit(packed: bytes) -> None:
    values = unpack(packed)
    if not all(math.isfinite(value) for value in values):
        raise VectorRefused("a vector holds NaN or infinity")
    norm = math.sqrt(math.fsum(value * value for value in values))
    if abs(norm - 1.0) > UNIT_NORM_TOLERANCE:
        raise VectorRefused(
            f"a vector must be L2-normalized within {UNIT_NORM_TOLERANCE}, got {norm:.8f}"
        )


def sha256(packed: bytes) -> str:
    return hashlib.sha256(packed).hexdigest()


def to_base64(packed: bytes) -> str:
    return base64.b64encode(packed).decode("ascii")


def from_base64(value: str) -> bytes:
    try:
        packed = base64.b64decode(value.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise VectorRefused("a vector is not valid base64") from exc
    unpack(packed)
    return packed


def pgvector_literal(packed: bytes) -> str:
    return "[" + ",".join(format(value, ".9g") for value in unpack(packed)) + "]"
