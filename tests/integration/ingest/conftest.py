"""Fixtures for the ingest lane's real-service suite.

PostgreSQL and MinIO, both real. Nothing is mocked and nothing skips itself when a
service is absent: a skip would let the negative paths -- the ones that prove a guard
can fire -- report success by not running. Missing configuration fails collection.

Isolation
---------
The suite creates **one throwaway database per session**, applies the migration head to
it with the literal ``alembic`` command, and truncates the domain tables between tests.
It never touches the lane's own ``DATABASE_URL`` database, so ``make foundation`` and
this suite cannot disturb each other.

``TRUNCATE`` rather than ``DELETE`` is not a shortcut, it is the only option:
``document_version`` and ``input_manifest_entry`` carry ``BEFORE DELETE`` row triggers
that refuse deletion with SQLSTATE ``AM003``. That the cleanup *has* to be a truncate is
itself evidence the immutability guard is real.

Object storage is the lane's own bucket with **scoped** cleanup: every blob a test
publishes is registered and deleted by exact identity at teardown. No fixture empties
the bucket, which would destroy a concurrently running lane's objects.

Assertions about what the bucket holds are made through a plain ``boto3`` client, never
through the adapter under test, so a bug in the adapter's own inspection path cannot
make a "nothing was published" assertion pass.
"""

from __future__ import annotations

import os
import secrets
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.client import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest import IngestService, Reconciler
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage import BlobId, S3BlobStore, S3StorageSettings, StorageError
from auditmanager.storage.settings import REQUIRED_VARS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
NEGATIVE = FIXTURES / "negative"

MIGRATE_ARGV = [
    ".venv/bin/python",
    "-m",
    "alembic",
    "--config",
    "db/migrations/alembic.ini",
    "upgrade",
    "head",
]

#: Everything this slice writes, plus the aggregates that reference them. Deliberately
#: an explicit list: ``contract_state_transition`` is seeded reference data frozen
#: against INSERT, so truncating it would leave a database no test could repair.
DOMAIN_TABLES = (
    "input_manifest_entry",
    "document_version",
    "document",
    "project",
    "blob",
    "command_record",
)


def _load_dotenv_if_needed() -> None:
    """Fill missing frozen names from the repository-root ``.env``, never overriding.

    The documented gate command is a literal ``.venv/bin/pytest tests/integration/ingest``,
    so the names have to be reachable without ``make`` having exported them. The file is
    data, as its own header says: parsed as ``NAME=VALUE``, never sourced.
    """
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
        if not separator:
            continue
        name = name.strip()
        if name not in wanted or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


@pytest.fixture(scope="session", autouse=True)
def lane_environment() -> None:
    _load_dotenv_if_needed()
    if not (REPOSITORY_ROOT / ".venv" / "bin" / "python").is_file():
        pytest.fail(
            "`.venv/bin/python` is missing. Run `make bootstrap` first: this suite runs "
            "the literal migration command against a real PostgreSQL server."
        )
    if not FIXTURES.is_dir() or not NEGATIVE.is_dir():
        pytest.fail(f"the AR corpus is missing under {FIXTURES}")


# --- PostgreSQL --------------------------------------------------------------


@pytest.fixture(scope="session")
def configured_settings(lane_environment: None) -> DatabaseSettings:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. tests/integration/ingest runs against a real "
            "PostgreSQL instance and never falls back to SQLite or skips itself."
        )
    return DatabaseSettings(url=parse_database_url(raw))


@pytest.fixture(scope="session")
def maintenance_engine(configured_settings: DatabaseSettings) -> Iterator[Engine]:
    maintenance = configured_settings.url.set(database="postgres")
    engine = create_database_engine(
        DatabaseSettings(url=maintenance)
    ).execution_options(isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        engine.dispose()
        pytest.fail(f"could not reach the PostgreSQL maintenance database: {exc}")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def ingest_database(
    configured_settings: DatabaseSettings, maintenance_engine: Engine
) -> Iterator[DatabaseSettings]:
    """A throwaway database with the migration head applied, dropped at session end."""
    name = f"b1_ingest_{secrets.token_hex(6)}"
    with maintenance_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    settings = DatabaseSettings(url=configured_settings.url.set(database=name))
    url = settings.url.render_as_string(hide_password=False)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src"
    environment["DATABASE_URL"] = url
    completed = subprocess.run(
        MIGRATE_ARGV,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0:
        pytest.fail(
            "could not apply the migration head to the suite's database:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    try:
        yield settings
    finally:
        with maintenance_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))


@pytest.fixture(scope="session")
def engine(ingest_database: DatabaseSettings) -> Iterator[Engine]:
    built = create_database_engine(ingest_database)
    try:
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture(autouse=True)
def clean_tables(engine: Engine) -> Iterator[None]:
    """Empty the domain tables before every test.

    ``TRUNCATE`` and not ``DELETE``: the immutable tables refuse row deletion by
    trigger, so a delete-based cleanup would fail with ``AM003`` on the first published
    version. Truncation does not fire row-level triggers, which is what makes it usable
    here and useless as a way to smuggle a mutation past the guard.
    """
    statement = text(f"TRUNCATE TABLE {', '.join(DOMAIN_TABLES)} CASCADE")
    with engine.begin() as connection:
        connection.execute(statement)
    yield


# --- object storage ----------------------------------------------------------


@pytest.fixture(scope="session")
def s3_settings(lane_environment: None) -> S3StorageSettings:
    try:
        return S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(f"tests/integration/ingest needs a real S3-compatible service: {exc}")


@pytest.fixture(scope="session")
def store(s3_settings: S3StorageSettings) -> S3BlobStore:
    blob_store = S3BlobStore(s3_settings)
    try:
        blob_store.check_access()
    except StorageError as exc:
        pytest.fail(f"the configured private bucket is not reachable: {exc}")
    return blob_store


@pytest.fixture(scope="session")
def raw_s3(s3_settings: S3StorageSettings) -> Any:
    """A plain boto3 client, independent of the adapter and of the service under test."""
    return boto3.client(
        "s3",
        endpoint_url=s3_settings.endpoint_url,
        region_name=s3_settings.region,
        aws_access_key_id=s3_settings.access_key_id,
        aws_secret_access_key=s3_settings.secret_access_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )


@pytest.fixture
def bucket_keys(raw_s3: Any, s3_settings: S3StorageSettings):
    """Every object key currently in the bucket, sorted. Read through boto3 directly."""

    def _keys() -> list[str]:
        found: list[str] = []
        token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": s3_settings.bucket}
            if token:
                kwargs["ContinuationToken"] = token
            page = raw_s3.list_objects_v2(**kwargs)
            found.extend(item["Key"] for item in page.get("Contents", []))
            if not page.get("IsTruncated"):
                return sorted(found)
            token = page.get("NextContinuationToken")

    return _keys


@pytest.fixture
def published_blobs(store: S3BlobStore) -> Iterator[list[BlobId]]:
    """Register blobs for scoped, per-identity cleanup. The bucket is never emptied."""
    registered: list[BlobId] = []
    yield registered
    for blob_id in registered:
        try:
            store._purge_published(blob_id)
        except StorageError:
            pass


@pytest.fixture
def track(published_blobs: list[BlobId]):
    """Register one blob identity for teardown and hand it back."""

    def _track(blob_id: BlobId) -> BlobId:
        if blob_id not in published_blobs:
            published_blobs.append(blob_id)
        return blob_id

    return _track


# --- the units under test ----------------------------------------------------


@pytest.fixture
def service(store: S3BlobStore, session_factory: sessionmaker[Session]) -> IngestService:
    return IngestService(store, session_factory=session_factory)


@pytest.fixture
def reconciler(store: S3BlobStore, session_factory: sessionmaker[Session]) -> Reconciler:
    return Reconciler(store, session_factory=session_factory)


@pytest.fixture
def project(service: IngestService):
    return service.create_project("Gate B1 ingest suite")


@pytest.fixture
def baseline_pdf() -> bytes:
    return (FIXTURES / "ar_baseline.pdf").read_bytes()


@pytest.fixture
def negative_pdf():
    def _read(name: str) -> bytes:
        path = NEGATIVE / name
        if not path.is_file():
            pytest.fail(f"missing negative fixture {name}")
        return path.read_bytes()

    return _read


@pytest.fixture
def key():
    """A fresh, well-formed idempotency key per call."""

    def _key(label: str = "upload") -> IdempotencyKey:
        return IdempotencyKey(f"{label}-{secrets.token_hex(8)}")

    return _key
