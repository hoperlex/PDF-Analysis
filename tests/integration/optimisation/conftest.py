"""Fixtures for the ``optimisation`` suite: real PostgreSQL and real MinIO, nothing mocked.

Each test gets its own clone of a session-local database migrated to head by the literal
command (``tests/integration/db/conftest.py``), dropped afterwards -- the price-list and
vendor-list tables refuse DELETE, so a shared database could not be cleaned. Each test that
stores a file gets its own bucket, emptied key by key and dropped at teardown; the bucket is
inspected through a plain ``boto3`` client, never through the adapter under test.

The people and projects every test needs are built through the ``access`` and ``documents``
boundaries, never by INSERT. Missing configuration fails collection; nothing skips itself.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.client import Config
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.db.session import create_session_factory
from auditmanager.storage import S3BlobStore, S3StorageSettings, StorageError
from auditmanager.storage.settings import REQUIRED_VARS
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    empty_database,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal

users = UserRepository()
accounts = AccountRepository()
documents = DocumentRepository()


def _load_dotenv_if_needed() -> None:
    """Fill missing names from the repository-root ``.env`` (data, never sourced)."""
    wanted = (*REQUIRED_VARS, "DATABASE_URL")
    if all(os.environ.get(name) for name in wanted):
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or name not in wanted or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


_load_dotenv_if_needed()


@dataclass(frozen=True, slots=True)
class Cast:
    """Who is who, and the projects they work on. Every value is an opaque identity string."""

    admin: str  # admin only
    expert: str  # expert only
    other_expert: str  # expert only
    admin_expert: str  # both roles
    nobody: str  # an active account with no role
    project: str
    other_project: str


def _person(session: Session, email: str, roles: tuple[str, ...]) -> str:
    uid = str(users.create_user(session, email, PASSWORD).user_uid)
    accounts.complete_profile(
        session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
    )
    for role in roles:
        accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
    return uid


@pytest.fixture
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(migrated_engine)


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    """A session on the fresh database. The test commits what it means to keep."""
    with Session(migrated_engine) as opened:
        yield opened


@pytest.fixture
def cast(session: Session) -> Cast:
    project = documents.create_project(session, "Школа на 550 мест")
    other_project = documents.create_project(session, "Детский сад")
    built = Cast(
        admin=_person(session, "admin.only@example.com", ("admin",)),
        expert=_person(session, "anna@example.com", ("expert",)),
        other_expert=_person(session, "boris@example.com", ("expert",)),
        admin_expert=_person(session, "vera@example.com", ("admin", "expert")),
        nobody=_person(session, "gleb@example.com", ()),
        project=str(project.project_uid),
        other_project=str(other_project.project_uid),
    )
    session.commit()
    return built


# --- object storage ----------------------------------------------------------


@pytest.fixture(scope="session")
def base_s3_settings() -> S3StorageSettings:
    try:
        return S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(f"tests/integration/optimisation needs a real S3-compatible service: {exc}")


@pytest.fixture(scope="session")
def raw_s3(base_s3_settings: S3StorageSettings) -> Any:
    """A plain boto3 client, independent of the adapter and of the service under test."""
    return boto3.client(
        "s3",
        endpoint_url=base_s3_settings.endpoint_url,
        region_name=base_s3_settings.region,
        aws_access_key_id=base_s3_settings.access_key_id,
        aws_secret_access_key=base_s3_settings.secret_access_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )


def _keys(raw_s3: Any, bucket: str) -> list[str]:
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
def s3_settings(base_s3_settings: S3StorageSettings, raw_s3: Any) -> Iterator[S3StorageSettings]:
    bucket = f"{base_s3_settings.bucket[:40]}-{secrets.token_hex(8)}"
    create: dict[str, Any] = {"Bucket": bucket}
    if base_s3_settings.region != "us-east-1":
        create["CreateBucketConfiguration"] = {"LocationConstraint": base_s3_settings.region}
    raw_s3.create_bucket(**create)
    try:
        yield replace(base_s3_settings, bucket=bucket)
    finally:
        for key in _keys(raw_s3, bucket):
            raw_s3.delete_object(Bucket=bucket, Key=key)
        raw_s3.delete_bucket(Bucket=bucket)


@pytest.fixture
def store(s3_settings: S3StorageSettings) -> S3BlobStore:
    blob_store = S3BlobStore(s3_settings)
    try:
        blob_store.check_access()
    except StorageError as exc:
        pytest.fail(f"the configured private bucket is not reachable: {exc}")
    return blob_store


@pytest.fixture
def bucket_keys(raw_s3: Any, s3_settings: S3StorageSettings):
    """Every object key currently in the test's bucket, sorted, read through boto3."""

    def _list() -> list[str]:
        return _keys(raw_s3, s3_settings.bucket)

    return _list
