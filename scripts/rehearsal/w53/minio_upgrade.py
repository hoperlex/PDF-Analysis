"""Disposable versioned-object MinIO upgrade and S3 rollback rehearsal.

Use ``--old-only`` when the new pinned image is unavailable. ``--full`` requires
both images. The script owns only gate-w53rehearsal-prefixed resources, uses the
reserved API port 60480, and always removes its containers and volumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import subprocess
import time
from dataclasses import dataclass

import boto3
from botocore.config import Config


OLD = "auditmanager-minio:RELEASE.2025-09-07T16-13-09Z-07c3a42"
NEW = "auditmanager-minio:RELEASE.2025-10-15T17-29-55Z-9e49d5e"
PREFIX = "gate-w53rehearsal-upgrade"
CONTAINER = f"{PREFIX}-server"
OLD_VOLUME = f"{PREFIX}-old"
COPY_VOLUME = f"{PREFIX}-copy"
RESTORE_VOLUME = f"{PREFIX}-restore"
BUCKET = "w53-versioned-disposable"
ENDPOINT = "http://127.0.0.1:60480"


def docker(*args: str, capture: bool = False) -> str:
    run = subprocess.run(
        ["docker", *args], check=True, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return run.stdout.strip() if capture else ""


@dataclass(frozen=True)
class Version:
    key: str
    version_id: str
    digest: str
    size: int
    metadata: dict[str, str]


@dataclass(frozen=True)
class ExportedVersion:
    key: str
    version_id: str
    body: bytes
    metadata: dict[str, str]


def s3_client(user: str, password: str):
    return boto3.client(
        "s3", endpoint_url=ENDPOINT, aws_access_key_id=user,
        aws_secret_access_key=password, region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ready(user: str, password: str):
    client = s3_client(user, password)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            client.list_buckets()
            return client
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("disposable MinIO was not ready")


def start(image: str, volume: str, user: str, password: str) -> None:
    docker(
        "run", "-d", "--name", CONTAINER,
        "--label", "auditmanager.lane=gate-w53rehearsal",
        "--env", f"MINIO_ROOT_USER={user}",
        "--env", f"MINIO_ROOT_PASSWORD={password}",
        "--mount", f"type=volume,source={volume},target=/data",
        "-p", "127.0.0.1:60480:9000", image,
        "server", "/data", "--address", ":9000",
    )


def stop() -> None:
    docker("rm", "-f", CONTAINER)


def writes(client) -> list[tuple[str, bytes, dict[str, str]]]:
    client.create_bucket(Bucket=BUCKET)
    client.put_bucket_versioning(
        Bucket=BUCKET, VersioningConfiguration={"Status": "Enabled"}
    )
    payloads = [
        ("alpha.txt", "v1: проверка".encode(), {"stage": "first"}),
        ("alpha.txt", "v2: changed bytes".encode(), {"stage": "second"}),
        ("nested/binary", hashlib.sha256(b"w53 object").digest() * 1024,
         {"stage": "binary"}),
        ("nested/empty", b"", {"stage": "empty"}),
    ]
    for key, body, metadata in payloads:
        client.put_object(Bucket=BUCKET, Key=key, Body=body, Metadata=metadata)
    return payloads


def listed_versions(client) -> list[dict]:
    """Read every version; an incomplete listing must never pass rollback QA."""
    rows: list[dict] = []
    markers: dict[str, str] = {}
    seen_markers: set[tuple[str, str]] = set()
    while True:
        listed = client.list_object_versions(Bucket=BUCKET, **markers)
        assert not listed.get("DeleteMarkers"), "unexpected delete marker"
        rows.extend(listed.get("Versions", []))
        if not listed.get("IsTruncated", False):
            return rows
        key_marker = listed.get("NextKeyMarker")
        version_marker = listed.get("NextVersionIdMarker")
        assert key_marker, "truncated listing without key marker"
        pair = (key_marker, version_marker or "")
        assert pair not in seen_markers, "repeated version-list marker"
        seen_markers.add(pair)
        markers = {"KeyMarker": key_marker}
        if version_marker is not None:
            markers["VersionIdMarker"] = version_marker


def export_versions(client) -> list[ExportedVersion]:
    """Export old-to-new versions from the upgraded server's S3 API."""
    listed = listed_versions(client)
    assert listed, "empty upgraded source"
    exported: list[ExportedVersion] = []
    for key in sorted({row["Key"] for row in listed}):
        by_key = [row for row in listed if row["Key"] == key]
        assert sum(bool(row["IsLatest"]) for row in by_key) == 1, key
        # ListObjectVersions is newest first within each key; PUT restores oldest first.
        for row in reversed(by_key):
            observed = client.get_object(
                Bucket=BUCKET, Key=key, VersionId=row["VersionId"]
            )
            body = observed["Body"].read()
            exported.append(ExportedVersion(
                key, row["VersionId"], body, observed["Metadata"]
            ))
    assert len(exported) == len(listed)
    return exported


def export_manifest(exported: list[ExportedVersion]) -> list[Version]:
    result: list[Version] = []
    for key in sorted({entry.key for entry in exported}):
        # manifest() observes newest first, whereas restore_export() puts oldest first.
        for entry in reversed([item for item in exported if item.key == key]):
            result.append(Version(
                entry.key, entry.version_id, hashlib.sha256(entry.body).hexdigest(),
                len(entry.body), entry.metadata,
            ))
    return result


def restore_export(client, exported: list[ExportedVersion]) -> None:
    assert exported, "empty S3 export"
    client.create_bucket(Bucket=BUCKET)
    client.put_bucket_versioning(
        Bucket=BUCKET, VersioningConfiguration={"Status": "Enabled"}
    )
    for entry in exported:
        client.put_object(
            Bucket=BUCKET, Key=entry.key, Body=entry.body,
            Metadata=entry.metadata,
        )


def manifest(client, payloads: list[tuple[str, bytes, dict[str, str]]]) -> list[Version]:
    expected: dict[str, list[tuple[bytes, dict[str, str]]]] = {}
    for key, body, metadata in payloads:
        expected.setdefault(key, []).append((body, metadata))
    versions = listed_versions(client)
    assert len(versions) == len(payloads), (len(versions), len(payloads))
    assert {row["Key"] for row in versions} == set(expected)
    result: list[Version] = []
    for key, wanted in expected.items():
        by_key = [row for row in versions if row["Key"] == key]
        assert len(by_key) == len(wanted), key
        assert sum(bool(row["IsLatest"]) for row in by_key) == 1, key
        # S3 ListObjectVersions returns newest first within a key.
        for row, (body, metadata) in zip(by_key, reversed(wanted), strict=True):
            observed = client.get_object(
                Bucket=BUCKET, Key=key, VersionId=row["VersionId"]
            )
            actual = observed["Body"].read()
            assert actual == body, (key, row["VersionId"])
            assert observed["Metadata"] == metadata, key
            result.append(Version(
                key, row["VersionId"], hashlib.sha256(actual).hexdigest(),
                len(actual), metadata,
            ))
    return result


def logical_manifest(entries: list[Version]) -> list[tuple[str, str, int, dict[str, str]]]:
    return [(item.key, item.digest, item.size, item.metadata) for item in entries]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-only", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.old_only == args.full:
        parser.error("choose exactly one of --old-only or --full")
    assert docker("image", "inspect", OLD, "--format", "{{.Id}}", capture=True)
    if args.full:
        assert docker("image", "inspect", NEW, "--format", "{{.Id}}", capture=True)
    assert not docker("ps", "-aq", "--filter", f"name=^/{CONTAINER}$", capture=True)
    names = (OLD_VOLUME, COPY_VOLUME, RESTORE_VOLUME) if args.full else (OLD_VOLUME,)
    assert not set(docker("volume", "ls", "-q", capture=True).splitlines()) & set(names)
    user = "w53rehearsal"
    password = secrets.token_urlsafe(32)
    created: list[str] = []
    running = False
    try:
        for name in names:
            docker("volume", "create", name)
            created.append(name)
        start(OLD, OLD_VOLUME, user, password)
        running = True
        client = ready(user, password)
        payloads = writes(client)
        old_manifest = manifest(client, payloads)
        print("old-versioned:", json.dumps(logical_manifest(old_manifest)))
        stop()
        running = False
        if args.old_only:
            return
        docker(
            "run", "--rm", "--entrypoint", "sh",
            "--mount", f"type=volume,source={OLD_VOLUME},target=/from,readonly",
            "--mount", f"type=volume,source={COPY_VOLUME},target=/to",
            OLD, "-c", "cp -a /from/. /to/",
        )
        start(NEW, COPY_VOLUME, user, password)
        running = True
        upgraded = ready(user, password)
        new_manifest = manifest(upgraded, payloads)
        assert new_manifest == old_manifest, "version IDs/keys/bytes changed on volume copy"
        exported = export_versions(upgraded)
        assert export_manifest(exported) == new_manifest, "S3 export differs from new-image read"
        print("old-volume-copy/new-image-read: PASS, exact version IDs and bytes")
        stop()
        running = False
        start(OLD, RESTORE_VOLUME, user, password)
        running = True
        restored = ready(user, password)
        restore_export(restored, exported)
        rollback_manifest = manifest(
            restored, [(entry.key, entry.body, entry.metadata) for entry in exported]
        )
        assert logical_manifest(rollback_manifest) == logical_manifest(old_manifest)
        print("S3-restore/old-image-read: PASS, logical versions and bytes")
        print("S3 restore creates new VersionIds; only the volume copy preserves them")
    finally:
        if running:
            stop()
        for name in created:
            docker("volume", "rm", name)


if __name__ == "__main__":
    main()
