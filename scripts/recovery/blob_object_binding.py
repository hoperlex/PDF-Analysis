"""Pure binding of restored available Blob facts to a sealed object mirror.

The storage adapter owns the canonical Blob-ID-to-key rule. Its resolver must
be passed explicitly; this recovery helper does not import the private object
layout or infer identity from an S3 key. Call the offline mirror-byte preflight
before this function while the mirror remains frozen.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

from auditmanager.storage.public import BlobId, derive_blob_id
from scripts.recovery.blob_reference_audit import BlobFact, BlobReferenceAudit
from scripts.recovery.copy_record_binding import (
    CopyRecordBindingRefused,
    verify_copy_record_binding,
)

_BLOB_ID = re.compile(r"blob_[0-9A-HJKMNP-TV-Z]{26}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class BlobObjectBindingRefused(ValueError):
    """The restored available Blob set and sealed mirror cannot be bound."""


@dataclass(frozen=True, slots=True)
class BoundBlobObject:
    blob_id: str
    key: str
    sha256: str
    size_bytes: int


def _valid_fact(fact: BlobFact) -> None:
    if type(fact) is not BlobFact or not isinstance(fact.blob_id, str) \
            or not _BLOB_ID.fullmatch(fact.blob_id) \
            or not isinstance(fact.sha256, str) or not _SHA256.fullmatch(fact.sha256) \
            or type(fact.size_bytes) is not int or fact.size_bytes < 0 \
            or not isinstance(fact.media_type, str) or not fact.media_type \
            or str(derive_blob_id(sha256=fact.sha256, size=fact.size_bytes)) != fact.blob_id:
        raise BlobObjectBindingRefused("available Blob fact is malformed or has wrong identity")


def bind_available_blob_objects(
    audit: BlobReferenceAudit,
    record_data: bytes,
    inventory_data: bytes,
    sealed_data: bytes,
    *,
    canonical_key_for: Callable[[BlobId], str],
) -> tuple[BoundBlobObject, ...]:
    """Match every available DB Blob to one exact sealed key, SHA-256 and size.

    ``canonical_key_for`` must be supplied by an owned storage adapter using
    its actual canonical layout. This function cannot authenticate an
    arbitrary callback. It reads no DB, object file or S3 endpoint and does
    not turn the binding into a recovery verdict.
    """
    if type(audit) is not BlobReferenceAudit or not callable(canonical_key_for):
        raise BlobObjectBindingRefused("DB audit or storage key resolver is missing")
    try:
        verify_copy_record_binding(record_data, inventory_data, sealed_data)
    except CopyRecordBindingRefused as exc:
        raise BlobObjectBindingRefused("W54 record and W58 object seal differ") from exc

    # The verifier above already refuses duplicate JSON keys, noncanonical
    # bytes, missing fields and any row differing from the W54 inventory.
    entries = json.loads(sealed_data)["objects"]
    by_key = {entry["key"]: entry for entry in entries}
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    bound: list[BoundBlobObject] = []
    for fact in audit.available_blobs:
        _valid_fact(fact)
        if fact.blob_id in seen_ids:
            raise BlobObjectBindingRefused("available Blob identity is repeated")
        seen_ids.add(fact.blob_id)
        try:
            key = canonical_key_for(BlobId(fact.blob_id))
        except Exception as exc:
            raise BlobObjectBindingRefused("storage key resolver refused a Blob") from exc
        if type(key) is not str or not key.startswith("blobs/") or key in seen_keys:
            raise BlobObjectBindingRefused("canonical Blob key is invalid or ambiguous")
        seen_keys.add(key)
        entry = by_key.get(key)
        if entry is None:
            raise BlobObjectBindingRefused("available Blob is missing at its canonical key")
        if entry["sha256"] != fact.sha256 or entry["size_bytes"] != fact.size_bytes:
            raise BlobObjectBindingRefused("canonical object facts differ from available Blob")
        bound.append(BoundBlobObject(fact.blob_id, key, fact.sha256, fact.size_bytes))
    return tuple(sorted(bound, key=lambda item: item.blob_id))


__all__ = ["BlobObjectBindingRefused", "BoundBlobObject", "bind_available_blob_objects"]
