"""Build one private synthetic W54-shaped copy for a later W58 service drill.

This prepares bytes only. A valid PostgreSQL 17 custom dump and its matching
stand-fingerprint-v1 lines must be supplied by an operator who has frozen the
synthetic source database. The local payload is not a source-S3 mirror.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path

from auditmanager.storage.public import BlobId, canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery.isolated_postgres_restore import _fingerprint_digest
from scripts.recovery.object_copy import build_manifest, manifest_bytes
from scripts.recovery.offline_restore_preflight import verify_offline_restore_inputs

_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_INSTANCE = re.compile(r"auditmanager-w58-synthetic-source-[a-z0-9-]{1,32}\Z")
_LINE = re.compile(r"([a-z_][a-z0-9_]*)\|(0|[1-9][0-9]*)\|([0-9a-f]{64})\Z")
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


class SyntheticFixtureRefused(ValueError):
    """A synthetic input or private output cannot be trusted."""


def _private_bytes(path: Path, *, maximum: int, label: str) -> bytes:
    try:
        fd = os.open(path, _READ_FLAGS)
    except OSError:
        raise SyntheticFixtureRefused(f"{label} is not a readable private file") from None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() \
                or before.st_mode & 0o077 or before.st_nlink != 1 \
                or before.st_size < 1 or before.st_size > maximum:
            raise SyntheticFixtureRefused(f"{label} is not a bounded owned private regular file")
        chunks: list[bytes] = []
        size = 0
        while chunk := os.read(fd, min(1024 * 1024, maximum + 1 - size)):
            size += len(chunk)
            if size > maximum:
                raise SyntheticFixtureRefused(f"{label} exceeds its synthetic size limit")
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) \
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) \
                or size != before.st_size:
            raise SyntheticFixtureRefused(f"{label} changed during read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, _WRITE_FLAGS, 0o600)
    try:
        remaining = memoryview(data)
        while remaining:
            written = os.write(fd, remaining)
            if written < 1:
                raise SyntheticFixtureRefused("private fixture write made no progress")
            remaining = remaining[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _record_bytes(record: dict[str, object]) -> bytes:
    lines = [
        f'  "{name}": {json.dumps(value, ensure_ascii=True, separators=(", ", ": "))}'
        for name, value in record.items()
    ]
    return ("{\n" + ",\n".join(lines) + "\n}\n").encode("ascii")


def prepare_synthetic_copy(
    *, dump_path: Path, fingerprint_lines_path: Path, payload_path: Path,
    output_root: Path, stamp: str, instance: str, tree_sha: str,
) -> tuple[Path, Path, str]:
    """Build exactly one positive Blob copy and recheck all W54/W58 local inputs.

    This does not establish that the supplied dump and fingerprint came from
    the same database. The target PG restore and fingerprint comparison do.
    """
    try:
        instant = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        raise SyntheticFixtureRefused("stamp must be a valid UTC YYYYMMDDTHHMMSSZ") from None
    if instant.strftime("%Y%m%dT%H%M%SZ") != stamp or not _INSTANCE.fullmatch(instance) \
            or not _SHA1.fullmatch(tree_sha) or not output_root.is_absolute() \
            or output_root.exists() or output_root.is_symlink():
        raise SyntheticFixtureRefused("synthetic identity or new absolute output root is invalid")

    dump = _private_bytes(dump_path, maximum=64 * 1024 * 1024, label="db.dump")
    if not dump.startswith(b"PGDMP"):
        raise SyntheticFixtureRefused("db.dump lacks the PostgreSQL custom-format header")
    lines_data = _private_bytes(fingerprint_lines_path, maximum=64 * 1024,
                                label="fingerprint lines")
    try:
        lines = lines_data.decode("ascii")
        fingerprint_sha256 = _fingerprint_digest(lines)
    except (UnicodeDecodeError, ValueError):
        raise SyntheticFixtureRefused("fingerprint lines are not stand-fingerprint-v1 output") from None
    tables: dict[str, dict[str, object]] = {}
    for line in lines.rstrip("\n").split("\n"):
        match = _LINE.fullmatch(line)
        if match is None:
            raise SyntheticFixtureRefused("fingerprint table line is invalid")
        tables[match.group(1)] = {"rows": int(match.group(2)), "sha256": match.group(3)}
    payload = _private_bytes(payload_path, maximum=1024 * 1024, label="Blob payload")
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    blob_id = str(derive_blob_id(sha256=payload_sha256, size=len(payload)))
    key = canonical_object_key_for_recovery(BlobId(blob_id))
    inventory = f"{key}\t{len(payload)}\tsynthetic-local-{payload_sha256[:16]}\n".encode("ascii")

    try:
        output_root.mkdir(mode=0o700)
        copy_dir = output_root / stamp
        mirror = output_root / "objects"
        copy_dir.mkdir(mode=0o700)
        mirror.mkdir(mode=0o700)
        object_path = mirror / key
        directory = mirror
        for segment in key.split("/")[:-1]:
            directory = directory / segment
            directory.mkdir(mode=0o700)
        _write_private(object_path, payload)
        seal = manifest_bytes(build_manifest(inventory, mirror))
        dump_sha256 = hashlib.sha256(dump).hexdigest()
        instant_text = instant.strftime("%Y-%m-%dT%H:%M:%SZ")
        record: dict[str, object] = {
            "record_version": 1, "kind": "copy", "stamp": stamp, "state": "open",
            "purpose": "import", "target_sha": None, "instance": instance,
            "deployed_tree": tree_sha, "migration_head": "0023_norm_citations",
            "opened_at": instant_text, "quiesced_at": instant_text,
            "writers_present": [], "writers_stopped": [],
            "dump": {"file": "db.dump", "size_bytes": len(dump), "sha256": dump_sha256},
            "fingerprint": {"algorithm": "stand-fingerprint-v1",
                            "sha256": fingerprint_sha256, "tables": tables},
            "rejected_blob_count": 0,
            "inventory": {"file": "inventory.tsv", "count": 1,
                          "bytes": len(payload),
                          "sha256": hashlib.sha256(inventory).hexdigest()},
            "attestation": None, "waiver": None, "real_data_marker": False,
            "restored_at": None, "closed_at": None,
        }
        _write_private(copy_dir / "db.dump", dump)
        _write_private(copy_dir / "inventory.tsv", inventory)
        _write_private(copy_dir / "objects.json", seal)
        _write_private(copy_dir / "record.json", _record_bytes(record))
        verify_offline_restore_inputs(copy_dir, mirror)
        return copy_dir, mirror, blob_id
    except (OSError, ValueError) as exc:
        raise SyntheticFixtureRefused("synthetic copy could not be built and verified; inspect partial output") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dump", "fingerprint-lines", "payload", "output-root"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--stamp", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--tree-sha", required=True)
    args = parser.parse_args(argv)
    try:
        copy_dir, mirror, blob_id = prepare_synthetic_copy(
            dump_path=args.dump, fingerprint_lines_path=args.fingerprint_lines,
            payload_path=args.payload, output_root=args.output_root,
            stamp=args.stamp, instance=args.instance, tree_sha=args.tree_sha,
        )
    except SyntheticFixtureRefused as exc:
        parser.exit(3, f"REFUSED: {exc}\n")
    print(json.dumps({"copy_dir": str(copy_dir), "objects_root": str(mirror),
                      "blob_id": blob_id, "synthetic_local_payload": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
