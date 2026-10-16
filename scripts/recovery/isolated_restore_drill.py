"""Offline W58 sequencing for an operator-owned isolated DB and object target.

The injected database restore must use a fresh isolated PostgreSQL target,
reproduce the W54 stand fingerprint, and yield a stable read-only Session.
The object client and BlobStore must address the same isolated bucket. This
module cannot authenticate those external choices or certify an actual drill.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from auditmanager.storage.public import BlobStore
from scripts.recovery.offline_restore_audit import (
    _read_copy_metadata,
    collect_offline_restore_evidence,
)
from scripts.recovery.offline_restore_preflight import verify_offline_restore_inputs
from scripts.recovery.target_blob_readback import TargetBlobReadback, audit_target_blob_readback
from scripts.recovery.target_object_restore import (
    TargetObjectClient,
    TargetObjectRestore,
    restore_sealed_objects,
)


class IsolatedRestoreDrillRefused(ValueError):
    """Local copy metadata changed between ordered recovery checks."""


@dataclass(frozen=True, slots=True)
class RestoredDatabase:
    session: Session
    fingerprint_sha256: str


@dataclass(frozen=True, slots=True)
class IsolatedRestoreDrillEvidence:
    record_sha256: str
    dump_sha256: str
    source_counts: tuple[tuple[str, int], ...]
    target_objects: TargetObjectRestore
    target_blobs: TargetBlobReadback


def run_isolated_restore_drill(
    *, copy_dir: Path, objects_root: Path,
    restore_database: Callable[[Path], AbstractContextManager[RestoredDatabase]],
    target_bucket: str, object_client: TargetObjectClient, target_blobs: BlobStore,
) -> IsolatedRestoreDrillEvidence:
    """Sequence validated local inputs, isolated DB restore and complete target reads.

    The restore callback is the only DB writer and must run `pg_restore`
    atomically into an empty isolated target before yielding a read-only
    repeatable-read Session and the stand-fingerprint-v1 digest calculated
    from that restored database. A failed partial target upload may be retried;
    the object helper verifies existing bytes and never overwrites them.
    """
    verify_offline_restore_inputs(copy_dir, objects_root)
    metadata = _read_copy_metadata(copy_dir)
    record_data, inventory_data, sealed_data = metadata
    expected_fingerprint = json.loads(record_data)["fingerprint"]["sha256"]
    with restore_database(copy_dir / "db.dump") as restored:
        if type(restored) is not RestoredDatabase \
                or restored.fingerprint_sha256 != expected_fingerprint:
            raise IsolatedRestoreDrillRefused("restored DB fingerprint differs from copy record")
        evidence = collect_offline_restore_evidence(restored.session, copy_dir, objects_root)
        if _read_copy_metadata(copy_dir) != metadata:
            raise IsolatedRestoreDrillRefused("copy metadata changed before target restore")
        objects = restore_sealed_objects(
            inventory_data=inventory_data, sealed_data=sealed_data,
            objects_root=objects_root, target_bucket=target_bucket, client=object_client,
        )
        blobs = audit_target_blob_readback(evidence, target_blobs)
        verify_offline_restore_inputs(copy_dir, objects_root)
        if _read_copy_metadata(copy_dir) != metadata:
            raise IsolatedRestoreDrillRefused("copy metadata changed during target readback")
        return IsolatedRestoreDrillEvidence(
            record_sha256=hashlib.sha256(record_data).hexdigest(),
            dump_sha256=json.loads(record_data)["dump"]["sha256"],
            source_counts=evidence.blob_references.source_counts,
            target_objects=objects, target_blobs=blobs,
        )


__all__ = [
    "IsolatedRestoreDrillEvidence", "IsolatedRestoreDrillRefused", "RestoredDatabase",
    "run_isolated_restore_drill",
]
