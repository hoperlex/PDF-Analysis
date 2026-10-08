"""Fixtures for the storage lane's real-service suite.

These tests run against a real S3-compatible service. Nothing here is mocked
and nothing is skipped when the service is absent: a skip would let the
negative paths -- the ones that prove the guards can fire -- pass by not
running, which is exactly the failure mode this suite exists to rule out. If
the service or its configuration is missing, collection fails loudly.

Configuration comes from the frozen ``FF-01`` section 3 environment names. A
literal ``.venv/bin/pytest tests/integration/storage`` is the documented gate
command, so when those names are not already exported the session reads them
out of the repository-root ``.env`` -- the same git-ignored file ``make`` reads
-- without overriding anything the caller set.

Each test owns a temporary bucket. The census sees every key; teardown
deletes observed keys individually before dropping that test's bucket.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator

import boto3
import pytest
from botocore.client import Config

from auditmanager.storage import (
    BlobId,
    PublishedBlob,
    S3BlobStore,
    S3StorageSettings,
    StorageError,
)
from auditmanager.storage.settings import REQUIRED_VARS

#: A port nothing listens on, used to prove the unavailable-service path.
CLOSED_PORT = 59099
CLOSED_ENDPOINT = f"http://127.0.0.1:{CLOSED_PORT}"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_dotenv_if_needed() -> None:
    """Fill in missing frozen names from the repository-root ``.env``.

    Deliberately narrow: only the names this adapter requires, never
    overriding an exported value, and no shell evaluation -- the file is data,
    as its own header says. This is not a general dotenv loader and must not
    grow into one.
    """
    if all(os.environ.get(name) for name in REQUIRED_VARS):
        return
    dotenv = _repository_root() / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        name, sep, value = line.partition("=")
        if not sep:
            continue
        name = name.strip()
        if name not in REQUIRED_VARS or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


@pytest.fixture(scope="session")
def base_settings() -> S3StorageSettings:
    _load_dotenv_if_needed()
    try:
        return S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(
            "tests/integration/storage needs a real S3-compatible service. "
            f"{exc} Export the FF-01 section 3 S3_* names, or create .env."
        )


def _keys_in_bucket(raw_s3: Any, bucket: str) -> list[str]:
    found: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket}
        if token:
            kwargs["ContinuationToken"] = token
        page = raw_s3.list_objects_v2(**kwargs)
        found.extend(item["Key"] for item in page.get("Contents", []))
        if not page.get("IsTruncated"):
            return sorted(found)
        token = page.get("NextContinuationToken")


@pytest.fixture
def settings(base_settings: S3StorageSettings, raw_s3: Any) -> Iterator[S3StorageSettings]:
    """Give this test every key in a new bucket, never a filtered shared view."""
    bucket = f"{base_settings.bucket[:40]}-{secrets.token_hex(8)}"
    create: dict[str, Any] = {"Bucket": bucket}
    if base_settings.region != "us-east-1":
        create["CreateBucketConfiguration"] = {"LocationConstraint": base_settings.region}
    raw_s3.create_bucket(**create)
    try:
        yield replace(base_settings, bucket=bucket)
    finally:
        for key in _keys_in_bucket(raw_s3, bucket):
            raw_s3.delete_object(Bucket=bucket, Key=key)
        raw_s3.delete_bucket(Bucket=bucket)


@pytest.fixture
def store(settings: S3StorageSettings) -> S3BlobStore:
    blob_store = S3BlobStore(settings)
    try:
        blob_store.check_access()
    except StorageError as exc:
        pytest.fail(
            "the configured private bucket is not reachable with the "
            f"configured application credentials: {exc}"
        )
    return blob_store


@pytest.fixture(scope="session")
def raw_s3(base_settings: S3StorageSettings) -> Any:
    """A plain boto3 client, independent of the adapter under test.

    Assertions about what the bucket does or does not contain are made through
    this client rather than through the adapter, so a bug in the adapter's own
    inspection path cannot make a "nothing was published" assertion pass.
    """
    return boto3.client(
        "s3",
        endpoint_url=base_settings.endpoint_url,
        region_name=base_settings.region,
        aws_access_key_id=base_settings.access_key_id,
        aws_secret_access_key=base_settings.secret_access_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )


@pytest.fixture
def bucket_keys(raw_s3: Any, settings: S3StorageSettings):
    """Return every object key currently in the bucket, sorted."""

    def _keys() -> list[str]:
        return _keys_in_bucket(raw_s3, settings.bucket)

    return _keys


@pytest.fixture
def blobs(store: S3BlobStore) -> Iterator[list[BlobId]]:
    """Register published blobs for scoped, per-key cleanup."""
    registered: list[BlobId] = []
    yield registered
    for blob_id in registered:
        store._purge_published(blob_id)


@pytest.fixture
def publish(store: S3BlobStore, blobs: list[BlobId]):
    """Publish content and register it for cleanup in one step."""

    def _publish(data: bytes, **kwargs: Any) -> PublishedBlob:
        from auditmanager.storage import ROLE_SOURCE_DOCUMENT, sha256_of

        kwargs.setdefault("declared_sha256", sha256_of(data))
        kwargs.setdefault("declared_size", len(data))
        kwargs.setdefault("role", ROLE_SOURCE_DOCUMENT)
        kwargs.setdefault("media_type", "application/pdf")
        published = store.put_blob(data, **kwargs)
        if published.blob_id not in blobs:
            blobs.append(published.blob_id)
        return published

    return _publish


@pytest.fixture
def unreachable_store(settings: S3StorageSettings) -> S3BlobStore:
    """An adapter pointed at a port nothing listens on."""
    return S3BlobStore(replace(settings, endpoint_url=CLOSED_ENDPOINT))
