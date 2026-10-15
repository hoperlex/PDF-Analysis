"""Collect read-only W58 recovery evidence from frozen local copy and restored DB.

The caller owns an isolated restored database in a stable read-only transaction
and must keep both private copy directories frozen for the whole call. Two
preflight scans detect drift but do not create an atomic filesystem snapshot.
This returns facts, not a recovery or source-bucket verdict.
"""

from __future__ import annotations

import os
import stat
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from auditmanager.storage.public import canonical_object_key_for_recovery
from scripts.recovery.blob_object_binding import BoundBlobObject, bind_available_blob_objects
from scripts.recovery.blob_reference_audit import BlobReferenceAudit, audit_blob_references
from scripts.recovery.offline_restore_preflight import verify_offline_restore_inputs

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_CHUNK = 1024 * 1024
_LIMITS = {"record.json": _CHUNK, "inventory.tsv": 256 * _CHUNK, "objects.json": 512 * _CHUNK}


class RecoveryEvidenceRefused(ValueError):
    """Copy metadata could not be read consistently after local preflight."""


@dataclass(frozen=True, slots=True)
class OfflineRestoreEvidence:
    blob_references: BlobReferenceAudit
    bound_objects: tuple[BoundBlobObject, ...]


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _read_limited(fd: int, limit: int) -> bytes:
    parts: list[bytes] = []
    size = 0
    while block := os.read(fd, _CHUNK):
        size += len(block)
        if size > limit:
            raise RecoveryEvidenceRefused("copy metadata exceeds its size limit")
        parts.append(block)
    return b"".join(parts)


def _read_copy_metadata(copy_dir: Path) -> tuple[bytes, bytes, bytes]:
    """Read the three bounded metadata files without following path symlinks."""
    try:
        with ExitStack() as stack:
            directory_fd = os.open(copy_dir, _DIR_FLAGS)
            stack.callback(os.close, directory_fd)
            directory_before = os.fstat(directory_fd)
            if not stat.S_ISDIR(directory_before.st_mode) \
                    or directory_before.st_uid != os.getuid() \
                    or directory_before.st_mode & 0o077:
                raise RecoveryEvidenceRefused("copy directory must be owned and private")
            result: list[bytes] = []
            for name, limit in _LIMITS.items():
                fd = os.open(name, _FILE_FLAGS, dir_fd=directory_fd)
                stack.callback(os.close, fd)
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    raise RecoveryEvidenceRefused("copy metadata is not a regular file")
                result.append(_read_limited(fd, limit))
                if _identity(os.fstat(fd)) != _identity(before) \
                        or _identity(os.stat(name, dir_fd=directory_fd,
                                             follow_symlinks=False)) != _identity(before):
                    raise RecoveryEvidenceRefused("copy metadata changed while read")
            if _identity(os.fstat(directory_fd)) != _identity(directory_before) \
                    or _identity(os.stat(copy_dir, follow_symlinks=False)) \
                    != _identity(directory_before):
                raise RecoveryEvidenceRefused("copy directory changed while read")
            return result[0], result[1], result[2]
    except OSError as exc:
        raise RecoveryEvidenceRefused("copy metadata cannot be read safely") from exc


def collect_offline_restore_evidence(
    session: Session, copy_dir: Path, objects_root: Path
) -> OfflineRestoreEvidence:
    """Return checked DB and object facts, preserving local-before-DB order.

    The first preflight must finish before ``audit_blob_references`` issues any
    SELECT. The second detects a changed dump or mirror after the DB read; the
    final metadata read must exactly equal the bytes consumed by the binder.
    The caller's frozen-copy invariant remains necessary between these scans.
    """
    verify_offline_restore_inputs(copy_dir, objects_root)
    record_data, inventory_data, sealed_data = _read_copy_metadata(copy_dir)
    audit = audit_blob_references(session)
    bound = bind_available_blob_objects(
        audit, record_data, inventory_data, sealed_data,
        canonical_key_for=canonical_object_key_for_recovery,
    )
    verify_offline_restore_inputs(copy_dir, objects_root)
    if _read_copy_metadata(copy_dir) != (record_data, inventory_data, sealed_data):
        raise RecoveryEvidenceRefused("copy metadata changed across recovery audit")
    return OfflineRestoreEvidence(audit, bound)


__all__ = ["OfflineRestoreEvidence", "RecoveryEvidenceRefused", "collect_offline_restore_evidence"]
