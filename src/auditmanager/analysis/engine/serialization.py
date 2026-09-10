"""Canonical JSON serialization for every published analysis artifact.

One function, used by every stage, because determinism is a contract obligation:
``P2-ENG-01`` requires that two runs over identical inputs publish byte-identical
artifact bytes, and byte-identical means the *serializer* has to be pinned as tightly
as the extractor is.

Three choices make that true and each of them would silently break it if changed:

``sort_keys=True``
    Key order becomes a function of the key set alone, not of dict insertion order,
    so a refactor that builds a dict in a different sequence cannot move a byte.

``ensure_ascii=False``
    The corpus is Russian. Escaping to ``\\uXXXX`` would still be deterministic, but
    it would quadruple the size of every text artifact and make the published bytes
    unreadable in exactly the artifact a human most needs to read.

``separators=(",", ":")``
    No insignificant whitespace, so indentation style is not part of the checksum.

The ``.encode("utf-8")`` below is the *only* legitimate encode in this package: it
turns a finished document into bytes for the blob store, long after every character
offset has been computed. Per ``P02_SEAMS`` section 4.1, an encode anywhere near an
offset calculation is a defect - offsets are Unicode code points, and this module is
deliberately the one place a byte view of the text is ever taken.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

#: Media type every artifact in this package is published under.
ARTIFACT_MEDIA_TYPE = "application/json"


def canonical_bytes(document: Any) -> bytes:
    """Serialize ``document`` to the one byte string it always serializes to."""
    text = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    """Lowercase hex SHA-256, the only checksum spelling the contracts accept."""
    return hashlib.sha256(payload).hexdigest()


__all__ = ["ARTIFACT_MEDIA_TYPE", "canonical_bytes", "sha256_hex"]
