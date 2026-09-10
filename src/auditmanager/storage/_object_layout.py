"""Private object-key layout. Adapter-only.

This module is the *only* place in the repository that knows how a ``blob_id``
or an upload token becomes an S3 object key. It is underscore-prefixed, absent
from the package's ``__all__``, and imported by ``s3.py`` and by nothing else.

``FF-01`` section 2 item 4: "A blob is addressed in business code by opaque
``blob_id``; bucket/key remain adapter details." ``identifiers.json`` says the
same thing from the other side -- "A project folder, an upload batch name or an
S3 key is none of these."

Layout::

    temporary/<upload_token>
    blobs/<c1><c2>/<c3><c4>/<blob_id without its prefix>

The two fan-out levels exist so a prototype bucket does not accumulate a single
flat prefix with every object in it; they carry no meaning and nothing may parse
them. Temporary keys live under a different top-level prefix from canonical
ones, which is what makes "did this failed upload leave anything canonical?" a
question about a prefix rather than about a naming convention.
"""

from __future__ import annotations

from typing import Final

from .models import BLOB_ID_PREFIX, BlobId

TEMPORARY_PREFIX: Final[str] = "temporary/"
CANONICAL_PREFIX: Final[str] = "blobs/"


def temporary_key(upload_token: str) -> str:
    """Key of a staged, unverified upload."""
    return f"{TEMPORARY_PREFIX}{upload_token}"


def canonical_key(blob_id: BlobId) -> str:
    """Key of published, immutable bytes.

    Derived from ``blob_id`` alone so that inspection and read need no lookup
    table. That is what makes the P02 metadata repository an addition: it
    records lifecycle and provenance, it does not resolve locations.
    """
    body = blob_id[len(BLOB_ID_PREFIX) :]
    return f"{CANONICAL_PREFIX}{body[0:2]}/{body[2:4]}/{body}"


def is_canonical_key(key: str) -> bool:
    return key.startswith(CANONICAL_PREFIX)


def is_temporary_key(key: str) -> bool:
    return key.startswith(TEMPORARY_PREFIX)


__all__ = [
    "CANONICAL_PREFIX",
    "TEMPORARY_PREFIX",
    "canonical_key",
    "is_canonical_key",
    "is_temporary_key",
    "temporary_key",
]
