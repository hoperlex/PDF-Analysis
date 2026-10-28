"""PostgreSQL and object-store fixtures of the engine's integration tests (`CMP-ENGINE-01`).

The lane's own services are required, never skipped. The tests **commit** (the cache is a table, a claim and a
heartbeat use connections of their own), so :class:`Lane` removes the rows it made (work items, results) and keeps the
rest: ``document_version`` and ``comparison_page_profile`` refuse DELETE by trigger and carry fresh identities, so a run
never meets another run's rows. The disposable lane database is dropped by ``make down``.

A version is a published ``document_version`` whose source PDF is a real blob; its page profiles are built by the real
children of `CMP-PROFILE-01`; the pair is then compared by the real engine child.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile.publish import ProfileBlobPublisher
from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
_NAMES = ("DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET")


def _load_dotenv() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        name, separator, value = raw.strip().partition("=")
        if separator and name in _NAMES and not os.environ.get(name):
            os.environ[name] = value.strip().strip("\"'")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: run `make up` and `make migrate` for this lane. These tests never skip.")
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with built.connect() as connection:
            if connection.execute(text("SELECT to_regclass('public.comparison_sheet_pair_result')")).scalar_one_or_none() is None:
                pytest.fail("the database has no comparison_sheet_pair_result table: run `make migrate` (head 0039)")
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def sessions(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture(scope="session")
def blob_store() -> S3BlobStore:
    _load_dotenv()
    try:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    except StorageError as failure:
        pytest.fail(f"the lane's private bucket is not reachable: {failure}")
    return store


@dataclass(frozen=True, slots=True)
class Seeded:
    project_uid: str
    version_uid: str
    pages: dict[int, str]  # page number -> comparison_page_profile_id


class Lane:
    def __init__(self, sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore) -> None:
        self.sessions, self.engine, self.blob_store = sessions, engine, blob_store
        self.projects: list[str] = []
        self.workers: list[str] = []

    def project(self) -> str:
        project = str(ProjectUid.new())
        with session_scope(self.sessions) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Сравнение листов')"), {"p": project})
        self.projects.append(project)
        return project

    def seed(self, relative: str | Path, page_count: int, *, project_uid: str) -> Seeded:
        """A published version of the corpus file in the project, with its page profiles built by the real children."""
        from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT

        data = (FIXTURES / relative).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        document, version = str(DocumentUid.new()), str(VersionUid.new())
        blob_id = ProfileBlobPublisher(self.sessions, self.blob_store).publish(data, role="source_document", media_type="application/pdf")
        with session_scope(self.sessions) as session:
            session.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
                            {"d": document, "p": project_uid})
            session.execute(text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', :n, :s, :c)"), {"v": version, "d": document, "n": len(data), "s": digest, "c": page_count})
            session.execute(text(
                "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                "VALUES (:v, :r, :b, :s, :n, 'application/pdf')"),
                {"v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": digest, "n": len(data)})
        build_version_page_profiles(self.sessions, self.blob_store, version)
        with session_scope(self.sessions) as session:
            rows = session.execute(text(
                "SELECT page_number, comparison_page_profile_id FROM comparison_page_profile WHERE version_uid = :v ORDER BY page_number"),
                {"v": version}).all()
        return Seeded(project_uid, version, {int(n): str(i) for n, i in rows})

    def results(self, project_uid: str) -> list[dict[str, Any]]:
        with session_scope(self.sessions) as session:
            return [dict(r) for r in session.execute(text(
                "SELECT comparison_sheet_pair_result_id AS id, content_key, status, reasons, channels, result, mask_blob_id, "
                "page_a_profile_id, page_b_profile_id FROM comparison_sheet_pair_result WHERE project_uid = :p "
                "ORDER BY created_at, comparison_sheet_pair_result_id"), {"p": project_uid}).mappings()]

    def blob_state(self, blob_id: str) -> str | None:
        with session_scope(self.sessions) as session:
            row = session.execute(text("SELECT state FROM blob WHERE blob_id = :b"), {"b": blob_id}).first()
        return None if row is None else str(row[0])

    def clean(self) -> None:
        with self.sessions() as session:
            for project in self.projects:
                session.execute(text(
                    "DELETE FROM comparison_work_attempt WHERE comparison_work_id IN "
                    "(SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p)"), {"p": project})
                session.execute(text("DELETE FROM comparison_work WHERE project_uid = :p"), {"p": project})
            for worker in self.workers:
                session.execute(text("DELETE FROM worker WHERE worker_id = :w"), {"w": worker})
            session.commit()


@pytest.fixture
def lane(sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore) -> Iterator[Lane]:
    made = Lane(sessions, engine, blob_store)
    try:
        yield made
    finally:
        made.clean()
