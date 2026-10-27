"""PostgreSQL and object-store fixtures of the page-profile integration tests (`CMP-PROFILE-01`).

A lane's own services are required, never skipped: a database test that skipped would report success while proving
nothing. The ``.env`` of the lane is read when the process environment lacks the names. Versions are seeded as
committed rows (``document_version`` refuses DELETE by trigger, which is not this suite's to defeat), each with its
own fresh identities, so a run never meets another run's rows; the disposable lane database is dropped by
``make down``.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"
_NAMES = (
    "DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
)


def _load_dotenv() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        name, separator, value = raw.strip().partition("=")
        if separator and name in _NAMES and not os.environ.get(name):
            os.environ[name] = value.strip().strip("\"'")


@pytest.fixture(scope="session")
def session_factory():
    _load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: run `make up` and `make migrate` for this lane. These tests never skip.")
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT to_regclass('public.comparison_page_profile')")).scalar_one_or_none() is None:
                pytest.fail("the database has no comparison_page_profile table: run `make migrate` (head 0038)")
        yield create_session_factory(engine)
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def blob_store() -> S3BlobStore:
    _load_dotenv()
    try:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    except StorageError as failure:
        pytest.fail(f"the lane's private bucket is not reachable: {failure}")
    return store


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def vs1_key() -> dict:
    import json

    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@pytest.fixture
def seed_version(session_factory, blob_store) -> Callable[..., str]:
    """``seed(pdf_path, page_count, with_manifest=True, manifest_sha256=None) -> version_uid``: a published
    version whose source document is the PDF, published through the blob journal like any other.
    ``manifest_sha256`` records a digest that is not the blob's, to prove the check on the way out."""
    from auditmanager.comparison.profile.publish import ProfileBlobPublisher
    from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT

    def seed(
        pdf_path: Path, page_count: int, *, with_manifest: bool = True, manifest_sha256: str | None = None
    ) -> str:
        data = pdf_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        project, document, version = str(ProjectUid.new()), str(DocumentUid.new()), str(VersionUid.new())
        blob_id = ProfileBlobPublisher(session_factory, blob_store).publish(
            data, role="source_document", media_type="application/pdf"
        )
        with session_scope(session_factory) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Профили страниц')"), {"p": project})
            session.execute(
                text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
                {"d": document, "p": project},
            )
            session.execute(
                text(
                    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                    "sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', :n, :s, :c)"
                ),
                {"v": version, "d": document, "n": len(data), "s": digest, "c": page_count},
            )
            if with_manifest:
                session.execute(
                    text(
                        "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                        "VALUES (:v, :r, :b, :s, :n, 'application/pdf')"
                    ),
                    {
                        "v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id,
                        "s": manifest_sha256 or digest, "n": len(data),
                    },
                )
        return version

    return seed


@pytest.fixture
def rows_of(session_factory) -> Callable[[str], list[Any]]:
    def read(version_uid: str) -> list[Any]:
        with session_scope(session_factory) as session:
            return list(
                session.execute(
                    text(
                        "SELECT comparison_page_profile_id, page_number, status, reason, content_key, profile_blob_id, "
                        "preview_blob_id, thumbnail_blob_id FROM comparison_page_profile "
                        "WHERE version_uid = :v ORDER BY page_number"
                    ),
                    {"v": version_uid},
                ).all()
            )

    return read
