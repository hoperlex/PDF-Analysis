"""Shared fixtures for the run-executor and CSV-export suites.

Both suites drive the *same* chain — B1's ingest rows, B2's stages, B3's recorded
adapter, B4's gate — so the seeding lives here once rather than in two copies that could
drift into disagreeing about what a seeded run is. ``tests/integration/exports`` imports
this module by path; both directories belong to this session.

Real services, no skips
-----------------------
PostgreSQL and MinIO, both real. A missing ``DATABASE_URL`` or a missing bucket is a hard
failure, never a skip: the behaviour under test here is transition triggers, CHECK
constraints and a projection view, none of which has an in-memory equivalent, and a
skipped integration suite reports success while proving nothing.

Isolation is by rollback
------------------------
Every test runs inside a transaction that is rolled back. That is not merely convenient:
``document_version``, ``input_manifest_entry`` and ``finding_observation`` refuse DELETE
with SQLSTATE ``AM003`` and the ledger refuses it with ``AM002``, so a fixture that tore
rows down afterwards would have to defeat the immutability guards this programme relies
on. Objects written to MinIO are content-addressed and are left in place; re-publishing
identical bytes is idempotent by content, so they cost nothing and collide with nothing.

Offline by construction
-----------------------
Every test here runs the **recorded** adapter. ``OD-13`` makes automated suites
recorded-only and there is no credential on this host; :func:`_no_network` refuses every
socket so that "offline" is enforced rather than intended.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.text import ProviderConfig, ProviderMode, RecordedAdapter
from auditmanager.documents import DocumentRepository, ManifestEntry
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    IdempotencyKey,
    PromptBundleId,
    VersionUid,
)
from auditmanager.storage import S3BlobStore, S3StorageSettings, StorageError, sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import ROLE_SOURCE_DOCUMENT, VerifiedBlob, parse_blob_role
from auditmanager.storage.settings import REQUIRED_VARS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE_PDF = CORPUS / "ar_baseline.pdf"
RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis"
VARIANTS = RECORDINGS / "variants"

#: The contract role of the bytes ``source_preparation`` reads.
# Imported, never restated. This constant used to be spelled out here with the contract's
# role while production ingest wrote the blob spelling, so the executor was only ever shown
# the role its own code expected and the real upload path could not start a run at all.
from auditmanager.documents.models import MANIFEST_ROLE_SOURCE_DOCUMENT

MANIFEST_ROLE_SOURCE: str = MANIFEST_ROLE_SOURCE_DOCUMENT

#: The model the recordings were made against. Pinned here so the suite does not depend
#: on an environment variable being exported.
RECORDED_MODEL_ID: str = "claude-opus-5"


def _load_dotenv_if_needed() -> None:
    """Fill missing frozen ``FF-01`` names from the repository-root ``.env``.

    The documented gate command is a literal ``.venv/bin/pytest tests/integration/runs``,
    so the names must be reachable without ``make`` having exported them. The file is
    data, as its own header says: parsed as ``NAME=VALUE``, never sourced, and an
    already-exported value is never overridden.
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


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse every socket the moment a test body starts.

    Autouse, so no test can opt out by forgetting. Installed *after* the session-scoped
    service fixtures have connected, which is why PostgreSQL and MinIO still work: their
    connections are already open, and what this forbids is a *new* outbound connection —
    which is what a live provider call would need.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "this suite runs the recorded adapter and must make no network call"
        )

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


# --- services ----------------------------------------------------------------


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _load_dotenv_if_needed()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. This suite runs against real PostgreSQL: the "
            "audit_run transition trigger, the degradation-set CHECK constraints and "
            "the finding_current_verdict view are database behaviour with no in-memory "
            "equivalent. It never skips. Create .env or export the name."
        )
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with built.connect() as connection:
            present = connection.execute(
                text("SELECT to_regclass('public.audit_run')")
            ).scalar_one_or_none()
        if present is None:
            pytest.fail(
                "the configured database has no audit_run table. Run `make migrate` "
                "(or `make foundation`) for this lane first; this suite asserts on the "
                "migrated schema and does not create it."
            )
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def blob_store() -> S3BlobStore:
    _load_dotenv_if_needed()
    try:
        settings = S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(
            f"this suite needs a real S3-compatible service. {exc} "
            "Export the FF-01 section 3 S3_* names, or create .env."
        )
    store = S3BlobStore(settings)
    try:
        store.check_access()
    except StorageError as exc:
        pytest.fail(f"the configured private bucket is not reachable: {exc}")
    return store


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """One unit of work on a transaction that is always rolled back.

    Rollback rather than cleanup: the rows these suites write cannot be deleted, and
    that refusal is itself under test elsewhere in the programme.
    """
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False, future=True)
    opened = factory()
    try:
        yield opened
    finally:
        opened.close()
        transaction.rollback()
        connection.close()


# --- adapters ----------------------------------------------------------------


@pytest.fixture(scope="session")
def provider_config() -> ProviderConfig:
    """Recorded mode, with the pinned model the recordings were made against.

    ``mode`` is only an *intent*: what reaches run provenance is read off the adapter
    that actually produced the responses, so this cannot make a replay look live.
    """
    return ProviderConfig(
        mode=ProviderMode.RECORDED,
        model_id=RECORDED_MODEL_ID,
        run_cost_ceiling_usd=1.0,
        api_key=None,
        ceiling_is_explicit=True,
    )


@pytest.fixture
def recorded_adapter() -> RecordedAdapter:
    """The baseline recording: a complete reply over the whole document."""
    return RecordedAdapter(RECORDINGS)


@pytest.fixture
def variant_adapter() -> Callable[[str], RecordedAdapter]:
    """An adapter over one of the committed ``variants/`` directories."""

    def build(name: str) -> RecordedAdapter:
        directory = VARIANTS / name
        if not directory.is_dir():
            pytest.fail(f"no recorded variant named {name!r} under {VARIANTS}")
        return RecordedAdapter(directory)

    return build


# --- the seeded document version ---------------------------------------------


@dataclass(frozen=True, slots=True)
class SeededVersion:
    """A published, immutable document version whose source bytes are in the store."""

    project_uid: str
    document_uid: str
    version_uid: str
    analysis_profile_id: str
    prompt_bundle_id: str
    source_blob_id: str
    sha256: str
    byte_size: int


def seed_version(session: Session, blob_store: S3BlobStore) -> SeededVersion:
    """Publish the baseline corpus PDF and the version whose manifest names it.

    Uses the owning modules' public surfaces throughout: ``S3BlobStore`` for the bytes,
    ``BlobMetadataRepository`` for the ``blob`` lifecycle, ``DocumentRepository`` for the
    project, document, version and manifest. Nothing here writes a row those modules own
    by hand, so a change to their rules reaches this fixture rather than being bypassed.
    """
    payload = BASELINE_PDF.read_bytes()
    digest = sha256_of(payload)

    published = blob_store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=parse_blob_role("source_document"),
        media_type="application/pdf",
    )

    # The blob's own lifecycle rows: temporary -> verifying -> available, through the
    # declared machine rather than an INSERT that skips it.
    blobs = BlobMetadataRepository()
    blobs.record_verified(
        session,
        VerifiedBlob(
            blob_id=published.blob_id,
            upload_token="seeded-by-test-harness",
            sha256=published.sha256,
            size=published.size,
            role=published.role,
            media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)

    documents = DocumentRepository()
    project = documents.create_project(session, "Синтетический проект")
    document_uid = documents.create_document(
        session, project_uid=project.project_uid, display_title="СП-7-АР"
    )
    version_uid = documents.publish_version(
        session,
        document_uid=document_uid,
        media_type="application/pdf",
        byte_size=len(payload),
        sha256=digest,
        page_count=8,
        source_filename="ar_baseline.pdf",
        entries=(
            ManifestEntry(
                role=MANIFEST_ROLE_SOURCE,
                blob_id=published.blob_id,
                sha256=published.sha256,
                size_bytes=published.size,
                media_type=published.media_type,
            ),
        ),
    )
    return SeededVersion(
        project_uid=str(project.project_uid),
        document_uid=str(document_uid),
        version_uid=str(version_uid),
        analysis_profile_id=AnalysisProfileId.new().value,
        prompt_bundle_id=PromptBundleId.new().value,
        source_blob_id=str(published.blob_id),
        sha256=digest,
        byte_size=len(payload),
    )


@pytest.fixture
def seeded(session: Session, blob_store: S3BlobStore) -> SeededVersion:
    return seed_version(session, blob_store)


@pytest.fixture
def new_key() -> Callable[[str], IdempotencyKey]:
    """A distinct, well-formed idempotency key per logical request.

    Derived from a caller-supplied label rather than random, so a failing test names the
    request that failed instead of a hex blob.
    """

    def build(label: str) -> IdempotencyKey:
        digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:32]
        return IdempotencyKey(f"b5-{digest}")

    return build


def run_state_of(session: Session, run_id: str) -> str:
    """The persisted state, read back rather than remembered."""
    return session.execute(
        text("SELECT state FROM audit_run WHERE run_id = :run_id"), {"run_id": run_id}
    ).scalar_one()


def audit_run_row(session: Session, run_id: str) -> dict[str, Any]:
    """The whole ``audit_run`` row as a mapping, for byte-for-byte comparisons."""
    row = (
        session.execute(
            text("SELECT * FROM audit_run WHERE run_id = :run_id"), {"run_id": run_id}
        )
        .mappings()
        .one()
    )
    return {key: value for key, value in row.items()}


def count_runs(session: Session) -> int:
    return int(session.execute(text("SELECT count(*) FROM audit_run")).scalar_one())


def json_of(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)
