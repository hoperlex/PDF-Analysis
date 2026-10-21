"""Read every restored available Blob through the public target storage port.

The caller owns an isolated target bucket and freezes the W54/W58 copy while
this read-only check runs. No metadata-only HEAD can prove restored payloads.
"""

from __future__ import annotations

import hashlib
from contextlib import closing
from dataclasses import dataclass

from auditmanager.storage.public import (
    BlobId,
    BlobStore,
    canonical_object_key_for_recovery,
    derive_blob_id,
)
from scripts.recovery.blob_object_binding import BoundBlobObject
from scripts.recovery.blob_reference_audit import BlobFact, BlobReferenceAudit
from scripts.recovery.offline_restore_audit import OfflineRestoreEvidence


class TargetBlobReadbackRefused(ValueError):
    """The target payloads or the supplied restored-DB evidence disagree."""


@dataclass(frozen=True, slots=True)
class TargetBlobReadback:
    count: int
    bytes_read: int
    facts_sha256: str


def _checked_objects(evidence: OfflineRestoreEvidence) -> tuple[BoundBlobObject, ...]:
    """Refuse forged, incomplete or ambiguous evidence before target I/O."""
    if type(evidence) is not OfflineRestoreEvidence or type(evidence.blob_references) is not BlobReferenceAudit \
            or type(evidence.bound_objects) is not tuple \
            or type(evidence.blob_references.available_blobs) is not tuple:
        raise TargetBlobReadbackRefused("offline restore evidence has the wrong shape")
    facts: dict[str, BlobFact] = {}
    for fact in evidence.blob_references.available_blobs:
        if type(fact) is not BlobFact or not isinstance(fact.blob_id, str) \
                or type(fact.sha256) is not str or len(fact.sha256) != 64 \
                or any(char not in "0123456789abcdef" for char in fact.sha256) \
                or type(fact.size_bytes) is not int or fact.size_bytes < 0 \
                or str(derive_blob_id(sha256=fact.sha256, size=fact.size_bytes)) != fact.blob_id \
                or fact.blob_id in facts:
            raise TargetBlobReadbackRefused("available DB Blob facts are invalid or repeated")
        facts[fact.blob_id] = fact
    bound: dict[str, BoundBlobObject] = {}
    for item in evidence.bound_objects:
        if type(item) is not BoundBlobObject or not isinstance(item.blob_id, str) \
                or item.blob_id in bound or item.blob_id not in facts:
            raise TargetBlobReadbackRefused("bound Blob identities differ from restored DB")
        fact = facts[item.blob_id]
        if item.sha256 != fact.sha256 or item.size_bytes != fact.size_bytes \
                or item.key != canonical_object_key_for_recovery(BlobId(item.blob_id)):
            raise TargetBlobReadbackRefused("bound object differs from restored DB or storage layout")
        bound[item.blob_id] = item
    if set(bound) != set(facts):
        raise TargetBlobReadbackRefused("available DB Blob set is not fully bound")
    return tuple(bound[blob_id] for blob_id in sorted(bound))


def audit_target_blob_readback(
    evidence: OfflineRestoreEvidence, target: BlobStore
) -> TargetBlobReadback:
    """Stream each target Blob by opaque ID and independently verify full bytes.

    ``open_stream`` itself checks the declared digest and size. This check also
    hashes the delivered chunks, so a broken adapter or fixture cannot turn a
    metadata-only inspection into a passing target readback. Storage failures
    propagate as typed storage errors; local evidence/payload failures refuse.
    """
    objects = _checked_objects(evidence)
    facts_digest = hashlib.sha256()
    total = 0
    for item in objects:
        digest = hashlib.sha256()
        size = 0
        with closing(target.open_stream(
            BlobId(item.blob_id), expected_sha256=item.sha256,
            expected_size=item.size_bytes, window=None,
        )) as chunks:
            for chunk in chunks:
                if type(chunk) is not bytes or not chunk:
                    raise TargetBlobReadbackRefused("target stream yielded an invalid chunk")
                size += len(chunk)
                if size > item.size_bytes:
                    raise TargetBlobReadbackRefused("target Blob exceeds restored DB size")
                digest.update(chunk)
        if size != item.size_bytes or digest.hexdigest() != item.sha256:
            raise TargetBlobReadbackRefused("target Blob bytes differ from restored DB")
        total += size
        facts_digest.update(f"{item.blob_id}\t{size}\t{item.sha256}\n".encode("ascii"))
    return TargetBlobReadback(len(objects), total, facts_digest.hexdigest())


__all__ = ["TargetBlobReadback", "TargetBlobReadbackRefused", "audit_target_blob_readback"]
