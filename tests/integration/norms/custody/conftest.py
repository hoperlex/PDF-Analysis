"""Fixtures for the custody suite: a real PostgreSQL and a real S3-compatible service.

The database-backed tests ask for ``custody`` (a :class:`CustodyKit`); the offline tests in
this directory ask for nothing and run without either service. Nothing here is autouse,
so an offline test never needs a container.

Isolation mirrors ``tests/integration/ingest``: one throwaway database per session with the
migration head applied by the literal ``alembic`` command, the custody, norm and blob tables
truncated before every database test (``TRUNCATE`` because the immutable tables refuse
``DELETE`` by trigger), and one fresh bucket per test, emptied key by key and dropped.
Assertions about bucket contents use a plain ``boto3`` client, never the adapter.
"""

from __future__ import annotations

import os
import secrets
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.client import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.norms.public import (
    NORM_SOURCE,
    AdmissionRequest,
    CustodySlot,
    DeclaredContent,
    ManifestIndex,
)
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import NormDocumentId, NormsSnapshotId
from auditmanager.storage import S3BlobStore, S3StorageSettings, StorageError, sha256_of
from auditmanager.storage.settings import REQUIRED_VARS

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATE_ARGV = [
    ".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini",
    "upgrade", "head",
]
#: Truncated before every database test. ``CASCADE`` reaches the bindings through their
#: blob and admission keys; ``contract_state_transition`` is reference data and is kept.
TABLES = (
    "norm_custody_binding",
    "norm_custody_admission",
    "norm_paragraph",
    "norm_document",
    "norms_snapshot",
    "blob",
    "audit_event",
)


def _load_dotenv_if_needed() -> None:
    """Fill missing frozen names from the repository-root ``.env``; never override."""
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
            line = line[len("export "):].strip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or name not in wanted or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


# --- PostgreSQL ------------------------------------------------------------------------


@pytest.fixture(scope="session")
def custody_database() -> Iterator[DatabaseSettings]:
    _load_dotenv_if_needed()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set; the custody suite needs a real PostgreSQL.")
    configured = DatabaseSettings(url=parse_database_url(raw))
    maintenance = create_database_engine(
        DatabaseSettings(url=configured.url.set(database="postgres"))
    ).execution_options(isolation_level="AUTOCOMMIT")
    name = f"w54_custody_{secrets.token_hex(6)}"
    try:
        with maintenance.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        settings = DatabaseSettings(url=configured.url.set(database=name))
        environment = dict(os.environ)
        environment["PYTHONPATH"] = "src"
        environment["DATABASE_URL"] = settings.url.render_as_string(hide_password=False)
        completed = subprocess.run(
            MIGRATE_ARGV, cwd=REPOSITORY_ROOT, env=environment,
            capture_output=True, text=True, timeout=300,
        )
        if completed.returncode != 0:
            pytest.fail(
                "could not apply the migration head:\n"
                f"{completed.stdout}\n{completed.stderr}"
            )
        yield settings
    finally:
        with maintenance.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        maintenance.dispose()


@pytest.fixture(scope="session")
def engine(custody_database: DatabaseSettings) -> Iterator[Engine]:
    built = create_database_engine(custody_database)
    try:
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture
def clean_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {', '.join(TABLES)} CASCADE"))


# --- object storage --------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_s3_settings() -> S3StorageSettings:
    _load_dotenv_if_needed()
    try:
        return S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(f"the custody suite needs a real S3-compatible service: {exc}")


@pytest.fixture(scope="session")
def raw_s3(base_s3_settings: S3StorageSettings) -> Any:
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
    blob_store.check_access()
    return blob_store


# --- the kit ---------------------------------------------------------------------------


@dataclass
class MemorySource:
    """A :class:`CustodySource` over in-memory bytes, keyed by anchor. Counts its reads."""

    files: dict[str, bytes] = field(default_factory=dict)
    reads: int = 0

    def open(self, admission: Any) -> bytes:
        self.reads += 1
        return self.files[admission.anchor]


@dataclass
class CustodyKit:
    engine: Engine
    session_factory: sessionmaker[Session]
    store: S3BlobStore
    raw_s3: Any
    bucket: str
    source: MemorySource = field(default_factory=MemorySource)
    manifest_entries: dict[CustodySlot, DeclaredContent] = field(default_factory=dict)

    @property
    def manifest(self) -> ManifestIndex:
        return ManifestIndex(self.manifest_entries)

    def bucket_keys(self) -> list[str]:
        return _keys(self.raw_s3, self.bucket)

    def request(
        self,
        target_id: str,
        anchor: str,
        data: bytes,
        *,
        anchor_kind: str = "pdf",
        media_type: str = "application/pdf",
        declared: bytes | None = None,
    ) -> AdmissionRequest:
        """A request for ``data`` at ``anchor``, entered in the manifest and the source.

        ``declared`` makes the manifest (and the request) declare other bytes than the
        source will serve: the byte-mismatch case.
        """
        named = data if declared is None else declared
        content = DeclaredContent(sha256=sha256_of(named), size=len(named), media_type=media_type)
        slot = CustodySlot(NORM_SOURCE, "norm_document", target_id, anchor_kind, anchor)
        self.manifest_entries[slot] = content
        self.source.files[anchor] = data
        return AdmissionRequest(
            role=NORM_SOURCE, target_id=target_id, anchor_kind=anchor_kind, anchor=anchor,
            sha256=content.sha256, size=content.size, media_type=media_type,
        )

    def scalar(self, sql: str, **params: Any) -> Any:
        with self.engine.connect() as connection:
            return connection.execute(text(sql), params).scalar()


@pytest.fixture
def custody(
    clean_tables: None,
    engine: Engine,
    session_factory: sessionmaker[Session],
    store: S3BlobStore,
    raw_s3: Any,
    s3_settings: S3StorageSettings,
) -> CustodyKit:
    return CustodyKit(
        engine=engine, session_factory=session_factory, store=store, raw_s3=raw_s3,
        bucket=s3_settings.bucket,
    )


def new_document_id() -> str:
    return str(NormDocumentId.new())


def insert_target(session: Session, document_id: str) -> None:
    """One snapshot and one norm document with this identity, in the caller's transaction.

    This is what the bundle importer's snapshot transaction does before it publishes the
    bindings; the shapes are the migration's minimal valid rows.
    """
    snapshot = str(NormsSnapshotId.new())
    key = f"2026-07-23+1d.{snapshot[-12:].lower()}"
    session.execute(
        text(
            "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
            "content_digest, undated_documents, document_count, repair_count, "
            "segmentation_profile) VALUES (:snapshot, :key, :key, :digest, 0, 1, 0, "
            "'markdown-v1')"
        ),
        {"snapshot": snapshot, "key": key, "digest": "d" * 64},
    )
    session.execute(
        text(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, "
            "source_document_ref, slug, title, doc_type, source_attribution, pdf_page_count, "
            "block_count, page_heading_count, recognised_characters, paragraph_count) "
            "VALUES (:document, :snapshot, 'source-1', 'slug-1', 'title.pdf', 'СП', "
            "'unattributed', 1, 1, 0, 10, 0)"
        ),
        {"document": document_id, "snapshot": snapshot},
    )
