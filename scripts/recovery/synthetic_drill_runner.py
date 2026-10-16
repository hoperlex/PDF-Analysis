"""Opt-in operator CLI for one real isolated synthetic W58 DB+Blob drill.

The CLI creates no database, bucket or Docker service. The operator owns a
fresh disposable PostgreSQL 17 database, an empty separate MinIO bucket and
the frozen synthetic copy built by ``synthetic_drill_fixture``. Running this
module does make DB and S3 calls; do so only in an assigned service lane.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

import boto3
from botocore.client import Config

from auditmanager.shared.db import DatabaseSettings, create_database_engine, parse_database_url
from auditmanager.storage.public import S3BlobStore, S3StorageSettings
from scripts.recovery.isolated_postgres_restore import (
    IsolatedPostgresTarget, restore_isolated_postgres,
)
from scripts.recovery.isolated_restore_drill import IsolatedRestoreDrillEvidence, run_isolated_restore_drill
from scripts.recovery.offline_restore_audit import _read_copy_metadata
from scripts.recovery.offline_restore_preflight import verify_offline_restore_inputs

_NAMES = frozenset({
    "FOUNDATION_INSTANCE", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "POSTGRES_PORT", "DATABASE_URL", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD",
    "S3_ENDPOINT_URL", "S3_API_PORT", "S3_CONSOLE_PORT", "S3_REGION",
    "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
})
_TARGET_INSTANCE = re.compile(r"auditmanager-w58-synthetic-target-[a-z0-9-]{1,32}\Z")
_VERSION = re.compile(r"(?:pg_dump|pg_restore|psql) \(PostgreSQL\) 17\.\d+(?:\s.*)?")
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


class SyntheticDrillRefused(ValueError):
    """The operator's isolated target or positive evidence is incomplete."""


@dataclass(frozen=True, slots=True)
class SyntheticTargetConfig:
    instance: str
    database: DatabaseSettings
    target: IsolatedPostgresTarget
    storage: S3StorageSettings
    password: str = field(repr=False)


def _private_env_bytes(path: Path) -> bytes:
    if not path.is_absolute():
        raise SyntheticDrillRefused("target .env must be an absolute private path")
    try:
        fd = os.open(path, _READ_FLAGS)
    except OSError:
        raise SyntheticDrillRefused("target .env cannot be opened without following links") from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() \
                or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 16 * 1024:
            raise SyntheticDrillRefused("target .env must be an owned private regular file")
        data = os.read(fd, 16 * 1024 + 1)
        if len(data) > 16 * 1024 or len(data) != info.st_size:
            raise SyntheticDrillRefused("target .env is too large or changed")
        after = os.fstat(fd)
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) \
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise SyntheticDrillRefused("target .env changed during read")
        return data
    finally:
        os.close(fd)


def load_target_config(path: Path) -> SyntheticTargetConfig:
    """Parse the foundation's exact 15-name .env as data, never as shell code."""
    try:
        data = _private_env_bytes(path).decode("ascii")
    except UnicodeDecodeError:
        raise SyntheticDrillRefused("target .env must be plain ASCII") from None
    values: dict[str, str] = {}
    for line in data.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or name not in _NAMES or name in values \
                or not value or value.strip() != value \
                or any(char in value for char in "'\"\r\n"):
            raise SyntheticDrillRefused("target .env has an unknown, repeated or unsupported assignment")
        values[name] = value
    if set(values) != _NAMES:
        raise SyntheticDrillRefused("target .env lacks a frozen foundation setting")
    instance = values["FOUNDATION_INSTANCE"]
    if not _TARGET_INSTANCE.fullmatch(instance) or values["S3_BUCKET"] != instance:
        raise SyntheticDrillRefused("target instance or bucket is not the disposable synthetic lane")
    try:
        pg_port, s3_port, console_port = (
            int(values[name]) for name in ("POSTGRES_PORT", "S3_API_PORT", "S3_CONSOLE_PORT")
        )
        if len({pg_port, s3_port, console_port}) != 3 \
                or not all(1024 <= port <= 65535 for port in (pg_port, s3_port, console_port)):
            raise ValueError("ports")
        target = IsolatedPostgresTarget(
            host="127.0.0.1", port=pg_port, database=values["POSTGRES_DB"],
            user=values["POSTGRES_USER"],
        )
        url = parse_database_url(values["DATABASE_URL"])
        if (url.host, url.port, url.database, url.username, url.password) != (
            target.host, target.port, target.database, target.user, values["POSTGRES_PASSWORD"]
        ) or url.query or not target.database.startswith("auditmanager_w58_target_"):
            raise ValueError("database URL")
        endpoint = urlsplit(values["S3_ENDPOINT_URL"])
        if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" \
                or endpoint.port != s3_port or endpoint.path or endpoint.query \
                or endpoint.fragment or endpoint.username or endpoint.password:
            raise ValueError("S3 endpoint")
        if not ipaddress.ip_address(endpoint.hostname).is_loopback:
            raise ValueError("S3 endpoint")
        if (values["S3_ACCESS_KEY_ID"], values["S3_SECRET_ACCESS_KEY"]) != (
            values["MINIO_ROOT_USER"], values["MINIO_ROOT_PASSWORD"]
        ):
            raise ValueError("S3 credentials")
        storage = S3StorageSettings.from_env(values)
    except (TypeError, ValueError):
        raise SyntheticDrillRefused("target foundation values are incoherent or unsafe") from None
    return SyntheticTargetConfig(instance, DatabaseSettings(url=url), target,
                                 storage, values["POSTGRES_PASSWORD"])


def require_pg17_tools(bin_dir: Path, *, runner=subprocess.run) -> None:
    """Refuse before service I/O unless the exact PATH prefix has PG17 clients."""
    if not bin_dir.is_absolute() or not bin_dir.is_dir():
        raise SyntheticDrillRefused("PostgreSQL 17 binary directory is invalid")
    for name in ("pg_dump", "pg_restore", "psql"):
        tool = bin_dir / name
        if not tool.is_file() or not os.access(tool, os.X_OK):
            raise SyntheticDrillRefused("PostgreSQL 17 tool is missing")
        try:
            result = runner([str(tool), "--version"], capture_output=True,
                            text=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise SyntheticDrillRefused("PostgreSQL 17 tool version cannot be checked") from None
        if result.returncode != 0 or not _VERSION.fullmatch(result.stdout.strip()) \
                or not result.stdout.startswith(f"{name} "):
            raise SyntheticDrillRefused("PostgreSQL tool is not version 17")


def _object_client(settings: S3StorageSettings):
    return boto3.client(
        "s3", endpoint_url=settings.endpoint_url, region_name=settings.region,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        config=Config(
            signature_version="s3v4", s3={"addressing_style": "path"},
            connect_timeout=settings.connect_timeout_seconds,
            read_timeout=settings.read_timeout_seconds,
            retries={"max_attempts": settings.max_attempts, "mode": "standard"},
        ),
    )


def _empty_bucket(client: object, bucket: str) -> None:
    try:
        page = client.list_objects_v2(Bucket=bucket, MaxKeys=1)  # type: ignore[attr-defined]
    except Exception:
        raise SyntheticDrillRefused("target bucket cannot be listed") from None
    if not isinstance(page, Mapping) or page.get("IsTruncated") is not False \
            or page.get("Contents", []) != [] or page.get("KeyCount", 0) != 0:
        raise SyntheticDrillRefused("target bucket is not provably empty")


def _pgpass(path: Path, target: IsolatedPostgresTarget, password: str) -> None:
    def escaped(value: str) -> str:
        return value.replace("\\", "\\\\").replace(":", "\\:")
    line = ":".join(escaped(value) for value in (
        target.host, str(target.port), target.database, target.user, password,
    )) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        remaining = memoryview(line.encode("utf-8"))
        while remaining:
            written = os.write(descriptor, remaining)
            if written < 1:
                raise SyntheticDrillRefused("private libpq passfile write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_synthetic_drill(
    *, copy_dir: Path, objects_root: Path, target_env: Path, pg17_bin: Path,
) -> IsolatedRestoreDrillEvidence:
    """Run only after an operator proves distinct disposable Docker resources."""
    config = load_target_config(target_env)
    require_pg17_tools(pg17_bin)
    verify_offline_restore_inputs(copy_dir, objects_root)
    record = json.loads(_read_copy_metadata(copy_dir)[0])
    if not record["instance"].startswith("auditmanager-w58-synthetic-source-") \
            or record["instance"] == config.instance or record["real_data_marker"] is not False \
            or record["migration_head"] != "0023_norm_citations" \
            or record["inventory"]["count"] != 1:
        raise SyntheticDrillRefused("copy is not the one-Blob synthetic source")
    client = _object_client(config.storage)
    _empty_bucket(client, config.storage.bucket)
    store = S3BlobStore(config.storage)
    with tempfile.TemporaryDirectory(prefix="w58-synthetic-pgpass-") as temporary:
        passfile = Path(temporary) / "pgpass"
        _pgpass(passfile, config.target, config.password)
        target = replace(config.target, pgpass_file=passfile)
        engine = create_database_engine(config.database)
        old_path = os.environ.get("PATH")
        try:
            os.environ["PATH"] = f"{pg17_bin}:{old_path or '/usr/bin:/bin'}"
            evidence = run_isolated_restore_drill(
                copy_dir=copy_dir, objects_root=objects_root,
                restore_database=partial(restore_isolated_postgres, engine=engine, target=target),
                target_bucket=config.storage.bucket, object_client=client,
                target_blobs=store,
            )
        finally:
            if old_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = old_path
            engine.dispose()
    if dict(evidence.source_counts).get("input_manifest_entry") != 1 \
            or evidence.target_objects.count != 1 or evidence.target_blobs.count != 1 \
            or evidence.target_objects.bytes_read != evidence.target_blobs.bytes_read:
        raise SyntheticDrillRefused("positive referenced-Blob target evidence is incomplete")
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copy-dir", type=Path, required=True)
    parser.add_argument("--objects-root", type=Path, required=True)
    parser.add_argument("--target-env", type=Path, required=True)
    parser.add_argument("--pg17-bin", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evidence = run_synthetic_drill(
            copy_dir=args.copy_dir, objects_root=args.objects_root,
            target_env=args.target_env, pg17_bin=args.pg17_bin,
        )
    except Exception as exc:
        parser.exit(3, f"REFUSED: {type(exc).__name__}; preserve target for inspection\n")
    print(json.dumps({
        "record_sha256": evidence.record_sha256, "dump_sha256": evidence.dump_sha256,
        "target_objects": evidence.target_objects.count,
        "target_object_bytes": evidence.target_objects.bytes_read,
        "target_blobs": evidence.target_blobs.count,
        "target_blob_bytes": evidence.target_blobs.bytes_read,
        "target_blob_facts_sha256": evidence.target_blobs.facts_sha256,
        "source_manifest_entries": dict(evidence.source_counts)["input_manifest_entry"],
        "synthetic_isolated_drill": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
