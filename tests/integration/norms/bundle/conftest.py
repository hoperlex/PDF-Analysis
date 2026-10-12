"""Fixtures for the bundle suite's heavy cases: a promotion-like database, a disposable stand.

Nothing here is autouse: the container-free tests in this directory ask for none of it and
run without a database or an object store. The heavy cases (``test_bundle_postgres.py``,
selected out by ``-k "not postgres"``) need ``DATABASE_URL`` and the S3 variables of a lane
stack -- in the integrator's window, PostgreSQL ``57170`` and S3 ``60770/60771``.

* **promotion** -- one throwaway database per session at the migration head; the synthetic
  drop loaded by the real loader (``characters-v2:1200``), embedded by the embedder's fake
  encoder and stored by the real repository; then exported once by the real exporter.
* **stand** -- a second throwaway database per session at the migration head, its norm,
  custody, blob and event tables truncated before every test, one client event and one
  client Blob row written so the fingerprint covers real rows, and a fresh bucket per test.
"""

from __future__ import annotations

import os
import secrets
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.norms.bundle.copy_record import compute_fingerprint
from auditmanager.norms.bundle.export import export_bundle
from auditmanager.norms.bundle.stand import Stand
from auditmanager.norms.embedding.builder import embed_batch
from auditmanager.norms.embedding_repository import NormEmbeddingRepository
from auditmanager.norms.loader import load_corpus
from auditmanager.shared.db import current_revision
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import AuditEventId, NormsSnapshotId
from auditmanager.storage import S3BlobStore, S3StorageSettings, StorageError
from auditmanager.storage.public import (
    BlobMetadataRepository,
    declare_blob,
    parse_blob_role,
)
from auditmanager.storage.settings import REQUIRED_VARS
from tests.integration.norms.bundle.support import (
    CHUNKING_PROFILE,
    fingerprint_document,
    record_fields,
    record_text,
    write_drop,
)
from tests.integration.norms.embedding.support import FakeEncoder
from tests.integration.norms.reset import truncate_tables

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATE_ARGV = [
    ".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", "upgrade", "head",
]
#: Truncated before every stand test (``TRUNCATE``: the immutable tables refuse ``DELETE``).
STAND_TABLES = (
    "norm_custody_binding", "norm_custody_admission", "norm_embedding_build", "norm_embedding",
    "norm_chunk_build", "norm_chunk", "norm_paragraph", "norm_document", "norms_snapshot",
    "blob", "audit_event",
)


def _load_dotenv_if_needed() -> None:
    wanted = (*REQUIRED_VARS, "DATABASE_URL")
    if all(os.environ.get(name) for name in wanted):
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ").strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        name = name.strip()
        if separator and name in wanted and not os.environ.get(name):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ[name] = value


@contextmanager
def _throwaway_database(prefix: str) -> Iterator[DatabaseSettings]:
    _load_dotenv_if_needed()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set; the bundle's heavy cases need a real PostgreSQL.")
    configured = DatabaseSettings(url=parse_database_url(raw))
    maintenance = create_database_engine(
        DatabaseSettings(url=configured.url.set(database="postgres"))
    ).execution_options(isolation_level="AUTOCOMMIT")
    name = f"{prefix}_{secrets.token_hex(6)}"
    try:
        with maintenance.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        settings = DatabaseSettings(url=configured.url.set(database=name))
        environment = dict(os.environ, PYTHONPATH="src",
                           DATABASE_URL=settings.url.render_as_string(hide_password=False))
        completed = subprocess.run(MIGRATE_ARGV, cwd=REPOSITORY_ROOT, env=environment,
                                   capture_output=True, text=True, timeout=300, check=False)
        if completed.returncode != 0:
            pytest.fail(f"could not apply the migration head:\n{completed.stdout}\n{completed.stderr}")
        yield settings
    finally:
        with maintenance.connect() as connection:
            connection.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                     "WHERE datname = :name AND pid <> pg_backend_pid()"),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        maintenance.dispose()


@pytest.fixture(scope="session")
def promotion_engine() -> Iterator[Engine]:
    with _throwaway_database("w54_bundle_promotion") as settings:
        engine = create_database_engine(settings)
        try:
            yield engine
        finally:
            engine.dispose()


@pytest.fixture(scope="session")
def stand_engine() -> Iterator[Engine]:
    with _throwaway_database("w54_bundle_stand") as settings:
        engine = create_database_engine(settings)
        try:
            yield engine
        finally:
            engine.dispose()


@dataclass(frozen=True)
class Promoted:
    corpus: Path
    sums: Path
    snapshot_id: str
    content_key: str
    bundle: Path
    out: Path


@pytest.fixture(scope="session")
def promoted(promotion_engine: Engine, tmp_path_factory: pytest.TempPathFactory) -> Promoted:
    """The synthetic drop loaded, embedded and exported from a promotion-like database."""
    where = tmp_path_factory.mktemp("promotion")
    corpus, sums = write_drop(where / "drop")
    with Session(promotion_engine) as session, session.begin():
        loaded = load_corpus(session, corpus, chunking_version="characters-v2")
    snapshot_id = NormsSnapshotId.parse(str(loaded.norms_snapshot_id))
    with Session(promotion_engine) as session, session.begin():
        repository = NormEmbeddingRepository(session)
        chunks = list(repository.iter_chunk_inputs(snapshot_id, CHUNKING_PROFILE))
        repository.ensure_build(
            snapshot_id=snapshot_id, chunking_profile=CHUNKING_PROFILE,
            chunks=embed_batch(FakeEncoder(), chunks),
        )
    out = where / "bundles"
    with Session(promotion_engine) as session:
        result = export_bundle(
            session, snapshot_id=str(snapshot_id), chunking_profile=CHUNKING_PROFILE,
            corpus=corpus, drop_sums=sums, ledger=None, out=out,
        )
        session.rollback()
    return Promoted(corpus, sums, str(snapshot_id), loaded.content_key, result.directory, out)


# --- object storage ---------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_s3_settings() -> S3StorageSettings:
    _load_dotenv_if_needed()
    try:
        return S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(f"the bundle's heavy cases need a real S3-compatible service: {exc}")


@pytest.fixture
def store(base_s3_settings: S3StorageSettings) -> Iterator[S3BlobStore]:
    import boto3
    from botocore.client import Config

    raw = boto3.client(
        "s3", endpoint_url=base_s3_settings.endpoint_url, region_name=base_s3_settings.region,
        aws_access_key_id=base_s3_settings.access_key_id,
        aws_secret_access_key=base_s3_settings.secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = f"{base_s3_settings.bucket[:40]}-{secrets.token_hex(8)}"
    create: dict[str, Any] = {"Bucket": bucket}
    if base_s3_settings.region != "us-east-1":
        create["CreateBucketConfiguration"] = {"LocationConstraint": base_s3_settings.region}
    raw.create_bucket(**create)
    try:
        blob_store = S3BlobStore(replace(base_s3_settings, bucket=bucket))
        blob_store.check_access()
        yield blob_store
    finally:
        for page in raw.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            for item in page.get("Contents", []):
                raw.delete_object(Bucket=bucket, Key=item["Key"])
        raw.delete_bucket(Bucket=bucket)


# --- the stand --------------------------------------------------------------------------


def write_client_rows(engine: Engine) -> None:
    """One client event and one client Blob: what a test-data stand holds besides norms."""
    with Session(engine) as session, session.begin():
        session.execute(
            text("INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
                 "VALUES (:id, 'project.created', 'Project', :aggregate, '{}'::jsonb)"),
            {"id": str(AuditEventId.new()), "aggregate": str(NormsSnapshotId.new())},
        )
        BlobMetadataRepository().record_declared(
            session,
            declare_blob(sha256="5" * 64, size=10, role=parse_blob_role("source_document"),
                         media_type="application/pdf"),
        )


@pytest.fixture
def stand(stand_engine: Engine, store: S3BlobStore) -> Stand:
    # ``norms_snapshot ... CASCADE`` reaches 0020's current snapshot and history, whose
    # TRUNCATE refusals ``truncate_tables`` lifts for this reset alone (`W55A-FIX`).
    with stand_engine.begin() as connection:
        truncate_tables(connection, STAND_TABLES)
    write_client_rows(stand_engine)
    return Stand(session_factory=create_session_factory(stand_engine), engine=stand_engine, store=store)


def open_waiver(stand: Stand, where: Path, **overrides: Any) -> Path:
    """A test-data waiver over the stand as it is now (what ``attest --test-data`` writes)."""
    # An override (e.g. a stale `migration_head`) replaces the stand's own value.
    fields = record_fields(**{
        "fingerprint": fingerprint_document(compute_fingerprint(stand.engine)),
        "migration_head": current_revision(stand.engine),
        **overrides,
    })
    path = where / "record.json"
    path.write_text(record_text(fields), encoding="utf-8")
    return path
