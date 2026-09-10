"""Public BlobStore value types.

These are the only shapes business code ever sees. None of them carries a
bucket, an object key, an endpoint or a credential: a consumer holds an opaque
``blob_id`` plus the four recorded facts ``FF-01`` section 2 item 5 requires --
role, media type, size and SHA-256.

Identity
--------
``contracts/domain/v1/identifiers.json`` fixes the ``blob`` prefix and
``contracts/analysis/v1`` fixes the wire pattern ``^blob_[0-9A-HJKMNP-TV-Z]{26}$``
-- twenty-six Crockford base32 characters. ``machines.blob.retry`` in
``contracts/domain/v1/state-machines.json`` fixes the rule that re-uploading
identical content is idempotent by ``(sha256, size)``.

This package satisfies both by *deriving* the identifier from ``(sha256, size)``
through a namespaced digest. Identical verified bytes therefore resolve to the
identical ``blob_id`` without a metadata table, which is what lets P01 be
idempotent before P02's blob-metadata repository exists -- and what lets that
repository be added later as a cache and a lifecycle record rather than as the
allocator of a different identity.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final, NewType

from .errors import BlobMetadataInvalidError, InvalidBlobIdError

# --- blob_id -----------------------------------------------------------------

BlobId = NewType("BlobId", str)
"""Opaque business identity of published bytes. Never a path, never a key."""

BLOB_ID_PREFIX: Final[str] = "blob_"

#: Crockford base32: the digits and the uppercase letters, less I, L, O and U.
_CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

#: The frozen wire pattern. Kept identical to the analysis contract schemas.
BLOB_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^blob_[0-9A-HJKMNP-TV-Z]{26}$"
)

#: Domain separation for the identifier digest. Changing this string changes
#: every derived blob_id, so it is a freeze-break, not an implementation detail.
_BLOB_ID_NAMESPACE: Final[bytes] = b"auditmanager.blob.identity.v1"


def _crockford_base32(value: int, length: int) -> str:
    out: list[str] = []
    for _ in range(length):
        value, remainder = divmod(value, 32)
        out.append(_CROCKFORD_ALPHABET[remainder])
    return "".join(reversed(out))


def derive_blob_id(*, sha256: str, size: int) -> BlobId:
    """Return the ``blob_id`` identical verified content always resolves to.

    Pure and total: no network, no state, no clock. ``(sha256, size)`` in, the
    same twenty-six character identifier out, on every process and every host.
    """
    normalized = f"{sha256.lower()}:{size}".encode("ascii")
    digest = hashlib.sha256(_BLOB_ID_NAMESPACE + b"|" + normalized).digest()
    # 128 bits, exactly what twenty-six Crockford base32 characters address.
    return BlobId(BLOB_ID_PREFIX + _crockford_base32(int.from_bytes(digest[:16], "big"), 26))


def parse_blob_id(value: str) -> BlobId:
    """Validate an untrusted string as a ``blob_id``."""
    if not isinstance(value, str) or not BLOB_ID_PATTERN.match(value):
        raise InvalidBlobIdError(field="blob_id", constraint=BLOB_ID_PATTERN.pattern)
    return BlobId(value)


# --- role --------------------------------------------------------------------

BlobRole = NewType("BlobRole", str)
"""What the bytes are *for*, recorded with every published blob.

Deliberately an open, validated vocabulary rather than a closed enum. P01 has
no approved product domain, and every later stage that publishes an artifact
(``contracts/analysis/v1/stage-registry.json``) brings its own role name. A
closed enum here would make each of those a rewrite of this package instead of
an addition to its callers.
"""

_ROLE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]{2,63}$")

#: The two roles P01 itself uses. Consumers are not limited to these.
ROLE_SOURCE_DOCUMENT: Final[BlobRole] = BlobRole("source_document")
ROLE_FOUNDATION_CHECK: Final[BlobRole] = BlobRole("foundation_check")


def parse_blob_role(value: str) -> BlobRole:
    """Validate a role name: lowercase, snake_case, 3-64 characters."""
    if not isinstance(value, str) or not _ROLE_PATTERN.match(value):
        raise BlobMetadataInvalidError(
            field="role", constraint=_ROLE_PATTERN.pattern
        )
    return BlobRole(value)


# --- state -------------------------------------------------------------------


class BlobState(str, Enum):
    """The closed ``machines.blob`` state set from the frozen domain contract.

    P01 drives only ``temporary -> verifying -> available`` and the
    ``-> rejected`` guards. ``erasure_pending`` and ``erased`` are declared so
    that the P02 metadata repository persists this package's vocabulary rather
    than inventing a second one.
    """

    TEMPORARY = "temporary"
    VERIFYING = "verifying"
    AVAILABLE = "available"
    REJECTED = "rejected"
    ERASURE_PENDING = "erasure_pending"
    ERASED = "erased"


# --- records -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TemporaryBlob:
    """Bytes uploaded but not yet verified.

    Never readable by business code -- ``OQ-05`` in the domain contract makes
    that explicit -- and never addressed by a ``blob_id``, because the content
    has not been proved yet. ``upload_token`` is an opaque handle; only the
    adapter knows what object it names.
    """

    upload_token: str
    declared_sha256: str
    declared_size: int
    role: BlobRole
    media_type: str
    state: BlobState = BlobState.TEMPORARY


@dataclass(frozen=True, slots=True)
class VerifiedBlob:
    """A temporary upload whose stored bytes matched the declared metadata.

    Holds the ``blob_id`` the content resolves to, but nothing canonical exists
    yet: publication is the next step and may still be refused.
    """

    blob_id: BlobId
    upload_token: str
    sha256: str
    size: int
    role: BlobRole
    media_type: str
    state: BlobState = BlobState.VERIFYING


@dataclass(frozen=True, slots=True)
class PublishedBlob:
    """Canonically published, immutable bytes.

    The whole public surface of a stored object: opaque identity plus the four
    facts ``FF-01`` requires. There is deliberately no ``bucket``, ``key``,
    ``uri``, ``url`` or ``path`` field, and adding one would be a freeze-break.
    """

    blob_id: BlobId
    role: BlobRole
    media_type: str
    size: int
    sha256: str
    published_at: datetime
    state: BlobState = BlobState.AVAILABLE


__all__ = [
    "BLOB_ID_PATTERN",
    "BLOB_ID_PREFIX",
    "ROLE_FOUNDATION_CHECK",
    "ROLE_SOURCE_DOCUMENT",
    "BlobId",
    "BlobRole",
    "BlobState",
    "PublishedBlob",
    "TemporaryBlob",
    "VerifiedBlob",
    "derive_blob_id",
    "parse_blob_id",
    "parse_blob_role",
]
