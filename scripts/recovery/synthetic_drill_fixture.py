"""Build one private synthetic W54-shaped copy for a W58 service drill.

This prepares bytes only. A valid PostgreSQL 17 custom dump and its matching
stand-fingerprint-v1 lines must be supplied by an operator who has frozen the
synthetic source database. Two sources of object bytes exist: local payload
files (``prepare_synthetic_copy``; the ETag is explicitly ``synthetic-local``,
not a source-S3 mirror) and the source bucket itself (``prepare_copy_from_bucket``;
the inventory is the bucket's own listing and every byte is pulled by
``mirror_source_objects`` under an ``If-Match`` read of the listed ETag).

`RECOVERY-REBASE-01`: the record names the current migration head, and the
fingerprint lines must name exactly the tables the recovery declaration says
``stand-fingerprint-v1`` counts at that head.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auditmanager.storage.public import BlobId, canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery.isolated_postgres_restore import _fingerprint_digest
from scripts.recovery.object_copy import build_manifest, manifest_bytes
from scripts.recovery.offline_restore_preflight import verify_offline_restore_inputs
from scripts.recovery.schema_coverage import FINGERPRINTED_TABLES, HEAD
from scripts.recovery.source_object_mirror import SourceObjectMirrorRefused, mirror_source_objects

_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_INSTANCE = re.compile(r"auditmanager-w58-synthetic-source-[a-z0-9-]{1,32}\Z")
_LINE = re.compile(r"([a-z_][a-z0-9_]*)\|(0|[1-9][0-9]*)\|([0-9a-f]{64})\Z")
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_MAX_PAYLOADS = 64


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


def _check_identity(*, stamp: str, instance: str, tree_sha: str, output_root: Path) -> datetime:
    try:
        instant = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        raise SyntheticFixtureRefused("stamp must be a valid UTC YYYYMMDDTHHMMSSZ") from None
    if instant.strftime("%Y%m%dT%H%M%SZ") != stamp or not _INSTANCE.fullmatch(instance) \
            or not _SHA1.fullmatch(tree_sha) or not output_root.is_absolute() \
            or output_root.exists() or output_root.is_symlink():
        raise SyntheticFixtureRefused("synthetic identity or new absolute output root is invalid")
    return instant


def _read_dump_and_fingerprint(
    dump_path: Path, fingerprint_lines_path: Path
) -> tuple[bytes, str, dict[str, dict[str, object]]]:
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
    if set(tables) != FINGERPRINTED_TABLES:
        raise SyntheticFixtureRefused(
            "fingerprint tables differ from the declared schema at head "
            f"{HEAD}: missing={sorted(FINGERPRINTED_TABLES - set(tables))}, "
            f"unknown={sorted(set(tables) - FINGERPRINTED_TABLES)}"
        )
    return dump, fingerprint_sha256, tables


def _write_copy(
    *, dump: bytes, fingerprint_sha256: str, tables: dict[str, dict[str, object]],
    inventory: bytes, seal: bytes, object_count: int, object_bytes: int,
    copy_dir: Path, mirror: Path, instant: datetime, stamp: str, instance: str, tree_sha: str,
) -> None:
    dump_sha256 = hashlib.sha256(dump).hexdigest()
    instant_text = instant.strftime("%Y-%m-%dT%H:%M:%SZ")
    record: dict[str, object] = {
        "record_version": 1, "kind": "copy", "stamp": stamp, "state": "open",
        "purpose": "import", "target_sha": None, "instance": instance,
        "deployed_tree": tree_sha, "migration_head": HEAD,
        "opened_at": instant_text, "quiesced_at": instant_text,
        "writers_present": [], "writers_stopped": [],
        "dump": {"file": "db.dump", "size_bytes": len(dump), "sha256": dump_sha256},
        "fingerprint": {"algorithm": "stand-fingerprint-v1",
                        "sha256": fingerprint_sha256, "tables": tables},
        "rejected_blob_count": 0,
        "inventory": {"file": "inventory.tsv", "count": object_count,
                      "bytes": object_bytes,
                      "sha256": hashlib.sha256(inventory).hexdigest()},
        "attestation": None, "waiver": None, "real_data_marker": False,
        "restored_at": None, "closed_at": None,
    }
    _write_private(copy_dir / "db.dump", dump)
    _write_private(copy_dir / "inventory.tsv", inventory)
    _write_private(copy_dir / "objects.json", seal)
    _write_private(copy_dir / "record.json", _record_bytes(record))
    verify_offline_restore_inputs(copy_dir, mirror)


def prepare_synthetic_copy(
    *, dump_path: Path, fingerprint_lines_path: Path, payload_paths: Sequence[Path],
    output_root: Path, stamp: str, instance: str, tree_sha: str,
) -> tuple[Path, Path, tuple[str, ...]]:
    """Build a private copy holding one positive Blob object per payload file.

    This does not establish that the supplied dump and fingerprint came from
    the same database. The target PG restore and fingerprint comparison do.
    The Blob IDs returned are in payload order.
    """
    instant = _check_identity(stamp=stamp, instance=instance, tree_sha=tree_sha,
                              output_root=output_root)
    if not payload_paths or len(payload_paths) > _MAX_PAYLOADS:
        raise SyntheticFixtureRefused(f"between 1 and {_MAX_PAYLOADS} Blob payloads are required")
    dump, fingerprint_sha256, tables = _read_dump_and_fingerprint(dump_path, fingerprint_lines_path)
    payloads: list[tuple[str, str, bytes]] = []  # (blob_id, key, bytes)
    for payload_path in payload_paths:
        payload = _private_bytes(payload_path, maximum=1024 * 1024, label="Blob payload")
        payload_sha256 = hashlib.sha256(payload).hexdigest()
        blob_id = str(derive_blob_id(sha256=payload_sha256, size=len(payload)))
        payloads.append((blob_id, canonical_object_key_for_recovery(BlobId(blob_id)), payload))
    if len({blob_id for blob_id, _, _ in payloads}) != len(payloads):
        raise SyntheticFixtureRefused("two payloads are the same Blob")

    try:
        output_root.mkdir(mode=0o700)
        copy_dir = output_root / stamp
        mirror = output_root / "objects"
        copy_dir.mkdir(mode=0o700)
        mirror.mkdir(mode=0o700)
        for _, key, payload in payloads:
            directory = mirror
            for segment in key.split("/")[:-1]:
                directory = directory / segment
                directory.mkdir(mode=0o700, exist_ok=True)
            _write_private(mirror / key, payload)
        inventory = "".join(
            f"{key}\t{len(payload)}\tsynthetic-local-{hashlib.sha256(payload).hexdigest()[:16]}\n"
            for _, key, payload in sorted(payloads, key=lambda item: item[1])
        ).encode("ascii")
        seal = manifest_bytes(build_manifest(inventory, mirror))
        _write_copy(
            dump=dump, fingerprint_sha256=fingerprint_sha256, tables=tables,
            inventory=inventory, seal=seal, object_count=len(payloads),
            object_bytes=sum(len(payload) for _, _, payload in payloads),
            copy_dir=copy_dir, mirror=mirror, instant=instant, stamp=stamp,
            instance=instance, tree_sha=tree_sha,
        )
        return copy_dir, mirror, tuple(blob_id for blob_id, _, _ in payloads)
    except (OSError, ValueError) as exc:
        raise SyntheticFixtureRefused("synthetic copy could not be built and verified; inspect partial output") from exc


def _list_bucket(client: Any, bucket: str) -> bytes:
    """The bucket's complete listing as the copy key's sorted ``key TAB size TAB etag`` text."""
    rows: list[tuple[str, int, str]] = []
    token: str | None = None
    while True:
        arguments: dict[str, Any] = {"Bucket": bucket}
        if token is not None:
            arguments["ContinuationToken"] = token
        try:
            page = client.list_objects_v2(**arguments)
        except Exception:
            raise SyntheticFixtureRefused("source bucket cannot be listed") from None
        if not isinstance(page, Mapping):
            raise SyntheticFixtureRefused("source bucket listing is malformed")
        for item in page.get("Contents", []):
            etag = str(item.get("ETag", "")).strip('"')
            if not isinstance(item.get("Key"), str) or type(item.get("Size")) is not int or not etag:
                raise SyntheticFixtureRefused("source bucket listing row is malformed")
            rows.append((item["Key"], item["Size"], etag))
        if not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
        if not isinstance(token, str):
            raise SyntheticFixtureRefused("source bucket listing cannot continue")
    if not rows or len(rows) > 100_000 or any(not key.startswith("blobs/") for key, _, _ in rows):
        raise SyntheticFixtureRefused("source bucket is empty or holds a non-Blob key")
    rows.sort()
    return "".join(f"{key}\t{size}\t{etag}\n" for key, size, etag in rows).encode("ascii")


def prepare_copy_from_bucket(
    *, dump_path: Path, fingerprint_lines_path: Path, source_client: Any, source_bucket: str,
    output_root: Path, stamp: str, instance: str, tree_sha: str,
) -> tuple[Path, Path, int]:
    """Pull every object of the (frozen) source bucket into the private mirror and seal it.

    ``source_client`` is a boto3-like S3 client for the SOURCE only. The listing is taken
    once; ``mirror_source_objects`` then reads each key under ``If-Match`` of the listed
    ETag, rehashes the whole mirror and refuses a bucket that changed meanwhile. As with
    the payload mode, the operator guarantees that no source writer runs.
    """
    instant = _check_identity(stamp=stamp, instance=instance, tree_sha=tree_sha,
                              output_root=output_root)
    dump, fingerprint_sha256, tables = _read_dump_and_fingerprint(dump_path, fingerprint_lines_path)
    inventory = _list_bucket(source_client, source_bucket)
    try:
        output_root.mkdir(mode=0o700)
        copy_dir = output_root / stamp
        mirror = output_root / "objects"
        copy_dir.mkdir(mode=0o700)
        mirror.mkdir(mode=0o700)
        pulled = mirror_source_objects(
            inventory_data=inventory, objects_root=mirror, bucket=source_bucket,
            reader=source_client,
        )
        _write_copy(
            dump=dump, fingerprint_sha256=fingerprint_sha256, tables=tables,
            inventory=inventory, seal=pulled.manifest, object_count=pulled.count,
            object_bytes=pulled.size_bytes, copy_dir=copy_dir, mirror=mirror,
            instant=instant, stamp=stamp, instance=instance, tree_sha=tree_sha,
        )
        return copy_dir, mirror, pulled.count
    except (OSError, ValueError, SourceObjectMirrorRefused) as exc:
        raise SyntheticFixtureRefused("bucket copy could not be built and verified; inspect partial output") from exc


def _bucket_client(env_path: Path) -> tuple[Any, str]:
    """A boto3 client and bucket from a private ``.env`` of the SOURCE lane (data, never sourced)."""
    import boto3
    from botocore.client import Config

    values: dict[str, str] = {}
    for line in _private_bytes(env_path, maximum=16 * 1024, label="source .env").decode("ascii").splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and name in ("S3_ENDPOINT_URL", "S3_REGION", "S3_ACCESS_KEY_ID",
                                  "S3_SECRET_ACCESS_KEY", "S3_BUCKET"):
            values[name] = value
    if len(values) != 5 or not values["S3_ENDPOINT_URL"].startswith("http://127.0.0.1:"):
        raise SyntheticFixtureRefused("source .env must name a loopback S3 endpoint and its bucket")
    client = boto3.client(
        "s3", endpoint_url=values["S3_ENDPOINT_URL"], region_name=values["S3_REGION"],
        aws_access_key_id=values["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=values["S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 3, "mode": "standard"}),
    )
    return client, values["S3_BUCKET"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dump", "fingerprint-lines", "output-root"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--payload", action="append", type=Path, default=[],
                        help="a local Blob payload (repeatable); synthetic-local ETags")
    parser.add_argument("--source-env", type=Path,
                        help="the SOURCE lane's private .env: pull every object of its bucket")
    parser.add_argument("--stamp", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--tree-sha", required=True)
    args = parser.parse_args(argv)
    if bool(args.payload) == bool(args.source_env):
        parser.exit(2, "exactly one of --payload (repeatable) and --source-env is required\n")
    try:
        if args.source_env:
            client, bucket = _bucket_client(args.source_env)
            copy_dir, mirror, count = prepare_copy_from_bucket(
                dump_path=args.dump, fingerprint_lines_path=args.fingerprint_lines,
                source_client=client, source_bucket=bucket, output_root=args.output_root,
                stamp=args.stamp, instance=args.instance, tree_sha=args.tree_sha,
            )
            report: dict[str, Any] = {"objects": count, "source": "bucket"}
        else:
            copy_dir, mirror, blob_ids = prepare_synthetic_copy(
                dump_path=args.dump, fingerprint_lines_path=args.fingerprint_lines,
                payload_paths=args.payload, output_root=args.output_root,
                stamp=args.stamp, instance=args.instance, tree_sha=args.tree_sha,
            )
            report = {"blob_ids": list(blob_ids), "synthetic_local_payload": True}
    except SyntheticFixtureRefused as exc:
        parser.exit(3, f"REFUSED: {exc}\n")
    print(json.dumps({"copy_dir": str(copy_dir), "objects_root": str(mirror), **report},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
