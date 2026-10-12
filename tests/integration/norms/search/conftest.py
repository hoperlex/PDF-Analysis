"""Fixtures for the norms search window suites: a real PostgreSQL, and S3 for the PDF.

`W55A-SEARCH-01`. The database-backed tests ask for ``corpus`` (a :class:`Corpus` over one
throwaway database at the migration head) and, for the PDF, ``pdf_store``; the offline
tests in this directory ask for neither and run without a container. Nothing here is
autouse.

Isolation follows ``tests/integration/norms/custody/conftest.py``: one throwaway database
per session, migrated by the literal ``alembic`` command, and every norms, custody and blob
table truncated before each database test (``TRUNCATE`` because the history and the corpus
tables refuse ``DELETE`` by trigger; ``0020`` refuses TRUNCATE of the history too, which
``tests/integration/norms/reset.py`` lifts for this reset alone). The rows are written by
plain SQL here -- never by the code under test -- so a seeding helper cannot share a defect
with what it seeds.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.client import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import (
    AuditEventId,
    NormDocumentId,
    NormParagraphId,
    NormsSnapshotId,
)
from auditmanager.shared.identity.ulid import new_ulid
from auditmanager.storage import S3BlobStore, S3StorageSettings, StorageError, derive_blob_id
from auditmanager.storage.public import BlobMetadataRepository, VerifiedBlob, parse_blob_role
from tests.integration.norms.reset import truncate_tables

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATE_ARGV = [
    ".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini",
    "upgrade", "head",
]
TABLES = (
    "norm_current_snapshot",
    "norm_current_snapshot_event",
    "norm_custody_binding",
    "norm_custody_admission",
    "norm_embedding",
    "norm_embedding_build",
    "norm_chunk",
    "norm_chunk_build",
    "norm_paragraph",
    "norm_document",
    "norms_snapshot",
    "blob",
)
ADMIN = "usr_01M2545JSD15ETSNNV904X991S"


def _load_dotenv_if_needed(names: tuple[str, ...]) -> None:
    """Fill missing names from the lane's ``.env``; never override."""
    if all(os.environ.get(name) for name in names):
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if name not in names or os.environ.get(name):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


@pytest.fixture(scope="session")
def search_database() -> Iterator[DatabaseSettings]:
    _load_dotenv_if_needed(("DATABASE_URL",))
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set; the norms search window suites need PostgreSQL.")
    configured = DatabaseSettings(url=parse_database_url(raw))
    maintenance = create_database_engine(
        DatabaseSettings(url=configured.url.set(database="postgres"))
    ).execution_options(isolation_level="AUTOCOMMIT")
    name = f"w55a_search_{secrets.token_hex(6)}"
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
                f"could not apply the migration head:\n{completed.stdout}\n{completed.stderr}"
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
def search_engine(search_database: DatabaseSettings) -> Iterator[Engine]:
    built = create_database_engine(search_database)
    try:
        yield built
    finally:
        built.dispose()


@dataclass
class Corpus:
    """Rows written by plain SQL, one committed transaction per helper call."""

    engine: Engine
    session_factory: sessionmaker[Session]

    def run(self, sql: str, **parameters: Any) -> Any:
        with self.engine.begin() as connection:
            return connection.execute(text(sql), parameters)

    def scalar(self, sql: str, **parameters: Any) -> Any:
        with self.engine.connect() as connection:
            return connection.execute(text(sql), parameters).scalar()

    # --- the corpus -------------------------------------------------------------------------

    def snapshot(self, *, unreliable: int = 0, documents: int = 1) -> str:
        snapshot = str(NormsSnapshotId.new())
        tail = snapshot[-12:].lower()
        base = f"2026-07-23+{documents}d.{tail}"
        content = base if unreliable == 0 else f"{base}+{unreliable}u"
        self.run(
            "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
            "content_digest, undated_documents, document_count, repair_count, "
            "unreliable_count, segmentation_profile) VALUES (:s, :content, :base, :digest, "
            "0, :documents, 0, :unreliable, 'markdown-v1')",
            s=snapshot, content=content, base=base, digest="d" * 64, documents=documents,
            unreliable=unreliable,
        )
        return snapshot

    def document(self, snapshot: str, slug: str, *, ref: str | None = None,
                 pages: int = 50) -> str:
        document = str(NormDocumentId.new())
        self.run(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, "
            "source_document_ref, slug, title, doc_type, source_attribution, pdf_page_count, "
            "block_count, page_heading_count, recognised_characters, paragraph_count) "
            "VALUES (:d, :s, :ref, :slug, :title, :doc_type, 'consultant_plus', :pages, 1, 0, "
            "10, 0)",
            d=document, s=snapshot, ref=ref or f"ref-{document[-8:]}", slug=slug,
            title=slug.split("__", 1)[-1].replace("_", " ") or slug,
            doc_type=slug.split("_", 1)[0], pages=pages,
        )
        return document

    def paragraph(self, document: str, body: str, *, ordinal: int, page: int = 1,
                  clause: str | None = None, reliable: bool = True) -> str:
        paragraph = str(NormParagraphId.new())
        self.run(
            "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, "
            "norm_document_pk, ordinal, page_label, block_ref, char_offset, char_length, kind, "
            "clause_number, text, text_reliability) "
            "SELECT :p, d.norms_snapshot_id, d.norm_document_pk, :ordinal, :page, :block, 0, "
            "char_length(:body), 'body', :clause, :body, :reliability "
            "FROM norm_document d WHERE d.norm_document_id = :d",
            p=paragraph, d=document, ordinal=ordinal, page=page,
            block=f"blk_{ordinal:06d}", clause=clause, body=body,
            reliability="reliable" if reliable else "unreliable",
        )
        return paragraph

    def build(self, snapshot: str, *, chunking: str = "characters-v2:1200",
              embedding: str = "bge-m3-dense-v1") -> None:
        """A completion row: what W54's loader writes last (condition (a))."""
        self.run(
            "INSERT INTO norm_chunk_build (norms_snapshot_id, chunking_profile, "
            "target_characters, chunk_count) VALUES (:s, :c, 1200, 0) ON CONFLICT DO NOTHING",
            s=snapshot, c=chunking,
        )
        if embedding:
            self.run(
                "INSERT INTO norm_embedding_build (norms_snapshot_id, chunking_profile, "
                "embedding_profile, chunk_count, window_count, embedding_set_sha256) "
                "VALUES (:s, :c, :e, 0, 0, :sha)",
                s=snapshot, c=chunking, e=embedding, sha="e" * 64,
            )

    def blob(self, data: bytes) -> tuple[str, str, int]:
        """An ``available`` Blob row for ``data`` (no object): what a confirmed admission
        leaves behind. The PDF suite puts the object with the real store first."""
        sha256 = hashlib.sha256(data).hexdigest()
        blob_id = derive_blob_id(sha256=sha256, size=len(data))
        repository = BlobMetadataRepository()
        with self.session_factory() as session:
            repository.record_verified(
                session,
                VerifiedBlob(
                    blob_id=blob_id, upload_token="norm-search-suite", sha256=sha256,
                    size=len(data), role=parse_blob_role("norm_source"),
                    media_type="application/pdf",
                ),
            )
            repository.mark_available(session, blob_id)
            session.commit()
        return str(blob_id), sha256, len(data)

    def bind_pdf(self, document: str, data: bytes | None = None, *,
                 anchor: str | None = None) -> str:
        """A confirmed ``norm_source`` admission and its binding for the document's PDF."""
        blob_id, sha256, size = self.blob(data or f"%PDF-1.7 {document}".encode())
        ref = self.scalar(
            "SELECT source_document_ref FROM norm_document WHERE norm_document_id = :d",
            d=document,
        )
        admission = f"nad_{new_ulid()}"
        slot = {
            "role": "norm_source", "target_kind": "norm_document", "target_id": document,
            "anchor_kind": "pdf", "anchor": anchor or ref,
        }
        self.run(
            "INSERT INTO norm_custody_admission (norm_custody_admission_id, role, target_kind, "
            "target_id, anchor_kind, anchor, blob_id, declared_size_bytes, declared_sha256, "
            "media_type) VALUES (:a, :role, :target_kind, :target_id, :anchor_kind, :anchor, "
            ":blob, :size, :sha, 'application/pdf')",
            a=admission, blob=blob_id, size=size, sha=sha256, **slot,
        )
        self.run(
            "UPDATE norm_custody_admission SET state = 'confirmed', "
            "confirmed_at = clock_timestamp() WHERE norm_custody_admission_id = :a",
            a=admission,
        )
        self.run(
            "INSERT INTO norm_custody_binding (norm_custody_binding_id, "
            "norm_custody_admission_id, role, target_kind, target_id, anchor_kind, anchor, "
            "blob_id) VALUES (:b, :a, :role, :target_kind, :target_id, :anchor_kind, :anchor, "
            ":blob)",
            b=f"nbd_{new_ulid()}", a=admission, blob=blob_id, **slot,
        )
        return blob_id

    def designate(self, snapshot: str, actor: str = ADMIN) -> str:
        """A designation by plain SQL: the event, then the singleton row naming it, in one
        transaction -- ``0020`` refuses at COMMIT an event the current row does not name."""
        event = str(AuditEventId.new())
        with self.engine.begin() as connection:
            current = connection.execute(
                text("SELECT norms_snapshot_id FROM norm_current_snapshot")
            ).scalar()
            connection.execute(text(
                "INSERT INTO norm_current_snapshot_event (event_id, from_snapshot_id, "
                "to_snapshot_id, actor_user_uid) VALUES (:e, :f, :t, :a)"
            ), {"e": event, "f": current, "t": snapshot, "a": actor})
            if current is None:
                connection.execute(text(
                    "INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id) "
                    "VALUES (:t, :e)"
                ), {"t": snapshot, "e": event})
            else:
                connection.execute(text(
                    "UPDATE norm_current_snapshot SET norms_snapshot_id = :t, event_id = :e"
                ), {"t": snapshot, "e": event})
        return event

    def qualify(self, snapshot: str) -> None:
        """Both conditions: the build and a binding for every document's PDF."""
        self.build(snapshot)
        documents = self.run(
            "SELECT norm_document_id FROM norm_document WHERE norms_snapshot_id = :s",
            s=snapshot,
        ).scalars().all()
        for document in documents:
            self.bind_pdf(document)


@pytest.fixture
def corpus(search_engine: Engine) -> Corpus:
    with search_engine.begin() as connection:
        truncate_tables(connection, TABLES)
    return Corpus(search_engine, create_session_factory(search_engine))


# --- object storage, for the PDF -----------------------------------------------------------


@pytest.fixture(scope="session")
def base_s3_settings() -> S3StorageSettings:
    _load_dotenv_if_needed(
        ("S3_ENDPOINT_URL", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET")
    )
    try:
        return S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(f"the norm PDF suite needs a real S3-compatible service: {exc}")


@pytest.fixture
def pdf_store(base_s3_settings: S3StorageSettings) -> Iterator[S3BlobStore]:
    raw = boto3.client(
        "s3",
        endpoint_url=base_s3_settings.endpoint_url,
        region_name=base_s3_settings.region,
        aws_access_key_id=base_s3_settings.access_key_id,
        aws_secret_access_key=base_s3_settings.secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = f"{base_s3_settings.bucket[:40]}-{secrets.token_hex(8)}"
    create: dict[str, Any] = {"Bucket": bucket}
    if base_s3_settings.region != "us-east-1":
        create["CreateBucketConfiguration"] = {"LocationConstraint": base_s3_settings.region}
    raw.create_bucket(**create)
    settings = S3StorageSettings(
        endpoint_url=base_s3_settings.endpoint_url,
        region=base_s3_settings.region,
        access_key_id=base_s3_settings.access_key_id,
        secret_access_key=base_s3_settings.secret_access_key,
        bucket=bucket,
    )
    try:
        yield S3BlobStore(settings)
    finally:
        listed = raw.list_objects_v2(Bucket=bucket).get("Contents", [])
        for item in listed:
            raw.delete_object(Bucket=bucket, Key=item["Key"])
        raw.delete_bucket(Bucket=bucket)
