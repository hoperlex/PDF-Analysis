"""Read-only W54/W58 local input check before an isolated recovery restore.

The caller must keep the copy and mirror frozen until the restore finishes.
This check establishes local byte agreement only; it does not certify the
source bucket, a restored database, or DB-to-Blob references.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from contextlib import ExitStack
from pathlib import Path

from scripts.recovery.copy_record_binding import (
    CopyRecordBindingRefused,
    verify_copy_record_binding,
)
from scripts.recovery.object_copy import ObjectCopyRefused, verify_manifest

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_CHUNK = 1024 * 1024
_MAX_BYTES = {"record.json": _CHUNK, "inventory.tsv": 256 * _CHUNK, "objects.json": 512 * _CHUNK}
_COPY_FILES = ("record.json", "db.dump", "inventory.tsv", "objects.json")


class RecoveryPreflightRefused(ValueError):
    """The local copy cannot safely be passed to an isolated restore."""


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns,
    )


def _private_directory(path: Path, stack: ExitStack) -> tuple[int, tuple[int, ...]]:
    fd = os.open(path, _DIR_FLAGS)
    stack.callback(os.close, fd)
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RecoveryPreflightRefused(f"{path} must be an owned private directory")
    return fd, _identity(info)


def _copy_file(directory_fd: int, name: str, stack: ExitStack) -> tuple[int, tuple[int, ...]]:
    fd = os.open(name, _FILE_FLAGS, dir_fd=directory_fd)
    stack.callback(os.close, fd)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        raise RecoveryPreflightRefused(f"{name} is not a regular file")
    return fd, _identity(info)


def _read_small(fd: int, name: str) -> bytes:
    limit = _MAX_BYTES[name]
    parts: list[bytes] = []
    size = 0
    while block := os.read(fd, _CHUNK):
        size += len(block)
        if size > limit:
            raise RecoveryPreflightRefused(f"{name} exceeds the preflight size limit")
        parts.append(block)
    return b"".join(parts)


def _dump_digest(fd: int) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    while block := os.read(fd, _CHUNK):
        digest.update(block)
        size += len(block)
    return size, digest.hexdigest()


def verify_offline_restore_inputs(copy_dir: Path, objects_root: Path) -> None:
    """Refuse unless all five W54/W58 inputs still agree at this instant."""
    try:
        with ExitStack() as stack:
            directory_fd, directory_before = _private_directory(copy_dir, stack)
            mirror_fd, mirror_before = _private_directory(objects_root, stack)
            files = {
                name: _copy_file(directory_fd, name, stack) for name in _COPY_FILES
            }
            record_data = _read_small(files["record.json"][0], "record.json")
            inventory_data = _read_small(files["inventory.tsv"][0], "inventory.tsv")
            sealed_data = _read_small(files["objects.json"][0], "objects.json")

            verify_copy_record_binding(record_data, inventory_data, sealed_data)
            # The binding parser already proved canonical JSON and rejected
            # duplicate keys; this read obtains the pinned dump metadata.
            record = json.loads(record_data)
            if copy_dir.name != record["stamp"]:
                raise RecoveryPreflightRefused("copy directory differs from record stamp")
            dump_size, dump_sha256 = _dump_digest(files["db.dump"][0])
            if dump_size == 0 or (dump_size, dump_sha256) != (
                record["dump"]["size_bytes"], record["dump"]["sha256"]
            ):
                raise RecoveryPreflightRefused("db.dump size or SHA-256 differs from W54 record")

            verify_manifest(inventory_data, objects_root, sealed_data)

            # The scans use open descriptors. Also refuse replacement of any
            # pathname during the check, including a rename to a new inode.
            for name, (fd, before) in files.items():
                if _identity(os.fstat(fd)) != before or _identity(
                    os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                ) != before:
                    raise RecoveryPreflightRefused(f"{name} changed during preflight")
            if _identity(os.fstat(directory_fd)) != directory_before or _identity(
                os.stat(copy_dir, follow_symlinks=False)
            ) != directory_before:
                raise RecoveryPreflightRefused("copy directory changed during preflight")
            if _identity(os.fstat(mirror_fd)) != mirror_before or _identity(
                os.stat(objects_root, follow_symlinks=False)
            ) != mirror_before:
                raise RecoveryPreflightRefused("mirror directory changed during preflight")
    except (OSError, CopyRecordBindingRefused, ObjectCopyRefused) as exc:
        raise RecoveryPreflightRefused(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("copy_dir", type=Path)
    parser.add_argument("objects_root", type=Path)
    args = parser.parse_args(argv)
    try:
        verify_offline_restore_inputs(args.copy_dir, args.objects_root)
    except RecoveryPreflightRefused as exc:
        parser.exit(3, f"REFUSED: {exc}\n")
    print("offline-restore preflight: verified local inputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
