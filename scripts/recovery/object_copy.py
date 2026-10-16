"""Seal and verify an offline copy of every object in a stand S3 inventory.

The W54 one-off copy contains a database dump and an object *listing*, but no
object payloads. W58 must transfer the payloads before a DB+Blob recovery can
be claimed. This tool accepts a separately mirrored, objects-only directory
and proves that its files exactly match ``inventory.tsv`` by key and size. It
adds a SHA-256 of every local payload because an S3 ETag is not a content hash.

The inventory key is a transport locator here, never a business identity.
This tool makes no DB/S3 connection and does not restore or publish anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

_SEGMENT = re.compile(r"[A-Za-z0-9._-]+\Z")
_SIZE = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_ETAG = re.compile(r"[\x21-\x7e]*\Z")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


class ObjectCopyRefused(ValueError):
    """The copy is incomplete, ambiguous or changed."""


def _valid_key(key: str) -> bool:
    parts = key.split("/")
    return bool(parts[0]) and parts[0][0].isalnum() and all(
        part not in ("", ".", "..") and _SEGMENT.fullmatch(part) for part in parts
    )


def parse_inventory(data: bytes) -> tuple[tuple[str, int, str], ...]:
    """Parse the copy key's sorted ``key TAB size TAB etag`` inventory exactly."""
    if b"\r" in data:
        raise ObjectCopyRefused("inventory is not the copy key's LF-only format")
    if data and not data.endswith(b"\n"):
        raise ObjectCopyRefused("inventory lacks its final newline")
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ObjectCopyRefused("inventory is not ASCII") from exc
    result: list[tuple[str, int, str]] = []
    previous = ""
    for line in lines:
        columns = line.split("\t")
        if len(columns) != 3:
            raise ObjectCopyRefused("inventory row must have key, size and ETag")
        key, size, etag = columns
        if not _valid_key(key) or not _SIZE.fullmatch(size) or not _ETAG.fullmatch(etag):
            raise ObjectCopyRefused(f"invalid inventory row for {key!r}")
        if key <= previous:
            raise ObjectCopyRefused("inventory keys are repeated or out of order")
        result.append((key, int(size), etag))
        previous = key
    return tuple(result)


def _hash_regular_file(directory_fd: int, name: str) -> tuple[int, str]:
    fd = os.open(name, _FILE_FLAGS, dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ObjectCopyRefused(f"{name!r} is not a regular object file")
        digest = hashlib.sha256()
        size = 0
        while block := os.read(fd, 1024 * 1024):
            digest.update(block)
            size += len(block)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ) or size != after.st_size:
            raise ObjectCopyRefused(f"{name!r} changed while it was hashed")
        return size, digest.hexdigest()
    finally:
        os.close(fd)


def _scan(directory_fd: int, prefix: str = "") -> dict[str, tuple[int, str]]:
    actual: dict[str, tuple[int, str]] = {}
    with os.scandir(directory_fd) as entries:
        children = sorted(entries, key=lambda item: item.name)
    for entry in children:
        key = f"{prefix}{entry.name}"
        if not _valid_key(key):
            raise ObjectCopyRefused(f"unsafe object path {key!r}")
        if entry.is_symlink():
            raise ObjectCopyRefused(f"object path {key!r} is a symlink")
        try:
            if entry.is_dir(follow_symlinks=False):
                child_fd = os.open(entry.name, _DIR_FLAGS, dir_fd=directory_fd)
                try:
                    actual.update(_scan(child_fd, f"{key}/"))
                finally:
                    os.close(child_fd)
            else:
                actual[key] = _hash_regular_file(directory_fd, entry.name)
        except OSError as exc:
            raise ObjectCopyRefused(f"cannot read object path {key!r}: {exc.strerror}") from exc
    return actual


def build_manifest(inventory_data: bytes, objects_root: Path) -> dict[str, object]:
    """Hash a complete, private local mirror and return its deterministic seal."""
    expected = parse_inventory(inventory_data)
    try:
        root_fd = os.open(objects_root, _DIR_FLAGS)
        try:
            actual = _scan(root_fd)
        finally:
            os.close(root_fd)
    except OSError as exc:
        raise ObjectCopyRefused(f"cannot open objects root: {exc.strerror}") from exc

    expected_keys = {key for key, _, _ in expected}
    if set(actual) != expected_keys:
        missing = sorted(expected_keys - set(actual))
        extra = sorted(set(actual) - expected_keys)
        raise ObjectCopyRefused(f"object set differs: missing={missing[:3]}, extra={extra[:3]}")

    objects = []
    for key, expected_size, etag in expected:
        size, sha256 = actual[key]
        if size != expected_size:
            raise ObjectCopyRefused(f"object {key!r} has {size} bytes; inventory says {expected_size}")
        objects.append({"key": key, "size_bytes": size, "etag": etag, "sha256": sha256})
    return {
        "format": "offline-object-copy-v1",
        "inventory_sha256": hashlib.sha256(inventory_data).hexdigest(),
        "count": len(objects),
        "bytes": sum(item["size_bytes"] for item in objects),
        "objects": objects,
    }


def manifest_bytes(manifest: dict[str, object]) -> bytes:
    return (json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def verify_manifest(inventory_data: bytes, objects_root: Path, sealed_bytes: bytes) -> None:
    """Refuse any missing, added or changed payload or manifest field."""
    if sealed_bytes != manifest_bytes(build_manifest(inventory_data, objects_root)):
        raise ObjectCopyRefused("sealed object manifest does not match this inventory and mirror")


def _seal(path: Path, payload: bytes) -> None:
    if path.is_symlink():
        raise ObjectCopyRefused("manifest destination is a symlink")
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise ObjectCopyRefused("existing manifest differs; a new copy needs a new destination")
    fd, temporary = tempfile.mkstemp(prefix=".object-copy-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        try:
            # link(2) is atomic and refuses an existing destination. A concurrent
            # process cannot replace a different seal between the check and write.
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise ObjectCopyRefused("manifest destination appeared while sealing") from exc
        directory_fd = os.open(path.parent, _DIR_FLAGS)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "verify"))
    parser.add_argument("inventory", type=Path)
    parser.add_argument("objects_root", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.manifest.resolve().parent != args.inventory.resolve().parent:
            raise ObjectCopyRefused("manifest must stay beside inventory.tsv in the private copy directory")
        for directory in (args.inventory.parent, args.objects_root):
            info = directory.stat(follow_symlinks=False)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ObjectCopyRefused(f"{directory} must be owned by this user and private")
        inventory_data = args.inventory.read_bytes()
        if args.action == "seal":
            _seal(args.manifest, manifest_bytes(build_manifest(inventory_data, args.objects_root)))
        else:
            verify_manifest(inventory_data, args.objects_root, args.manifest.read_bytes())
    except (ObjectCopyRefused, OSError) as exc:
        parser.exit(3, f"REFUSED: {exc}\n")
    print(f"object-copy {args.action}: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
