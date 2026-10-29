"""PostgreSQL and object-store fixtures of the matrix integration tests (`CMP-MATRIX-01`).

The lane's own services are required, never skipped. The tests **commit** (the service opens its own sessions, the
worker runner another), and ``document_version`` refuses DELETE by trigger, so every test works in documents of its
own with fresh identities and the shared database is never cleaned: a run never meets another run's rows.

The expensive part, profiling the five versions of VS-1 through the real page children (about thirty seconds), is done
once per session for a *template* document; a test's document is a clone of it (new project, document and versions,
the template's profile rows copied under the new versions -- a profile is a function of the page's bytes, so a copy
is the profile the builder would write). The synthetic corpus' answer key is the oracle.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile.publish import ProfileBlobPublisher
from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"
_NAMES = (
    "DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
)
SECRET = "comparison-matrix-suite"
TEMPLATE_PROJECT = "Матрица листов: образец"


def _load_dotenv() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        name, separator, value = raw.strip().partition("=")
        if separator and name in _NAMES and not os.environ.get(name):
            os.environ[name] = value.strip().strip("\"'")


@pytest.fixture(scope="session")
def engine() -> Engine:
    _load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: run `make up` and `make migrate` for this lane. These tests never skip.")
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    with built.connect() as connection:
        for table in ("comparison_matrix", "comparison_matrix_edit", "comparison_ai_link", "comparison_page_profile"):
            if connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one_or_none() is None:
                pytest.fail(f"the database has no {table} table: run `make migrate` (head 0039)")
    yield built
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


@pytest.fixture(scope="session")
def vs1_key() -> dict[str, Any]:
    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class Doc:
    project_uid: str
    document_uid: str
    versions: tuple[str, ...]  # oldest first (the document's own order)
    page_counts: dict[str, int]


class Lab:
    """The committed reads and writes the tests make beside the code under test."""

    def __init__(self, sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore, template: Doc) -> None:
        self.sessions, self.engine, self.blob_store, self.template = sessions, engine, blob_store, template

    def clone(self, *, versions: int | None = None, profiles: bool = True) -> Doc:
        """A document with the template's first ``versions`` versions and, if ``profiles``, their profile rows."""
        count = versions or len(self.template.versions)
        project, document = str(ProjectUid.new()), str(DocumentUid.new())
        made: list[str] = []
        with session_scope(self.sessions) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Матрица листов')"), {"p": project})
            session.execute(
                text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
                {"d": document, "p": project},
            )
            for ordinal, source in enumerate(self.template.versions[:count], start=1):
                version = str(VersionUid.new())
                made.append(version)
                session.execute(
                    text(
                        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                        "byte_size, sha256, page_count) SELECT :v, :d, :o, media_type, byte_size, sha256, page_count "
                        "FROM document_version WHERE version_uid = :s"
                    ),
                    {"v": version, "d": document, "o": ordinal, "s": source},
                )
                if profiles:
                    session.execute(
                        text(
                            "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, "
                            "content_key, algo_version, status, reason, profile, profile_blob_id, preview_blob_id, "
                            "thumbnail_blob_id) SELECT 'cpr_' || :ulid_prefix || lpad(page_number::text, 6, '0'), :v, "
                            "page_number, content_key, algo_version, status, reason, profile, profile_blob_id, "
                            "preview_blob_id, thumbnail_blob_id FROM comparison_page_profile WHERE version_uid = :s"
                        ),
                        {"v": version, "s": source, "ulid_prefix": new_ulid()[:20]},
                    )
        return Doc(project, document, tuple(made), {v: self.template.page_counts[s] for v, s in zip(made, self.template.versions)})

    def add_version(self, doc: Doc, source_version: str | None = None, *, profiles: bool = False) -> str:
        """Publish one more version (ordinal after the last), with a copy of the source's profile rows if asked."""
        source = source_version or self.template.versions[0]
        version = str(VersionUid.new())
        with session_scope(self.sessions) as session:
            ordinal = int(session.execute(
                text("SELECT max(version_ordinal) FROM document_version WHERE document_uid = :d"), {"d": doc.document_uid}
            ).scalar_one()) + 1
            session.execute(
                text(
                    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                    "sha256, page_count) SELECT :v, :d, :o, media_type, byte_size, sha256, page_count "
                    "FROM document_version WHERE version_uid = :s"
                ),
                {"v": version, "d": doc.document_uid, "o": ordinal, "s": source},
            )
            if profiles:
                session.execute(
                    text(
                        "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, "
                        "content_key, algo_version, status, reason, profile, profile_blob_id, preview_blob_id, "
                        "thumbnail_blob_id) SELECT 'cpr_' || :ulid_prefix || lpad(page_number::text, 6, '0'), :v, "
                        "page_number, content_key, algo_version, status, reason, profile, profile_blob_id, "
                        "preview_blob_id, thumbnail_blob_id FROM comparison_page_profile WHERE version_uid = :s"
                    ),
                    {"v": version, "s": source, "ulid_prefix": new_ulid()[:20]},
                )
        return version

    def seed_sources(self, files: list[str]) -> Doc:
        """A document whose versions are the given VS-1 files with their source blob in the manifest and **no**
        profiles: what a confirmed upload leaves before the worker has profiled it."""
        project, document = str(ProjectUid.new()), str(DocumentUid.new())
        versions: list[str] = []
        counts: dict[str, int] = {}
        with session_scope(self.sessions) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Матрица листов: подготовка')"), {"p": project})
            session.execute(
                text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
                {"d": document, "p": project},
            )
        for ordinal, name in enumerate(files, start=1):
            data = (FIXTURES / "vs1" / name).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            version = str(VersionUid.new())
            pages = {"v1.pdf": 6, "v2.pdf": 6, "v3.pdf": 6}[name]
            blob_id = ProfileBlobPublisher(self.sessions, self.blob_store).publish(
                data, role="source_document", media_type="application/pdf"
            )
            with session_scope(self.sessions) as session:
                session.execute(
                    text(
                        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                        "sha256, page_count) VALUES (:v, :d, :o, 'application/pdf', :n, :s, :c)"
                    ),
                    {"v": version, "d": document, "o": ordinal, "n": len(data), "s": digest, "c": pages},
                )
                session.execute(
                    text(
                        "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                        "VALUES (:v, :r, :b, :s, :n, 'application/pdf')"
                    ),
                    {"v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": digest, "n": len(data)},
                )
            versions.append(version)
            counts[version] = pages
        return Doc(project, document, tuple(versions), counts)

    def rows(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        with self.sessions() as session:
            return [dict(r) for r in session.execute(text(sql), params).mappings()]


@pytest.fixture(scope="session")
def template(sessions: sessionmaker[Session], blob_store: S3BlobStore, vs1_key: dict[str, Any]) -> Doc:
    """VS-1 as a published document of five versions with every page profiled by the real children.

    Built once per database: a later run of the suite finds the document (named by ``TEMPLATE_PROJECT``) with every
    page of the five versions profiled and reuses it, so only the first run pays the thirty seconds."""
    with sessions() as session:
        found = session.execute(text(
            "SELECT d.document_uid, p.project_uid FROM document d JOIN project p ON p.project_uid = d.project_uid "
            "WHERE p.name = :n ORDER BY p.created_at DESC LIMIT 1"), {"n": TEMPLATE_PROJECT}).first()
        if found is not None:
            rows = session.execute(text(
                "SELECT v.version_uid, v.page_count, count(cp.comparison_page_profile_id) AS profiled "
                "FROM document_version v LEFT JOIN comparison_page_profile cp ON cp.version_uid = v.version_uid "
                "WHERE v.document_uid = :d GROUP BY v.version_uid, v.page_count, v.version_ordinal "
                "ORDER BY v.version_ordinal"), {"d": found[0]}).all()
            if len(rows) == len(vs1_key["versions"]) and all(r[1] == r[2] for r in rows):
                return Doc(found[1], found[0], tuple(r[0] for r in rows), {r[0]: int(r[1]) for r in rows})
    project, document = str(ProjectUid.new()), str(DocumentUid.new())
    versions: list[str] = []
    counts: dict[str, int] = {}
    with session_scope(sessions) as session:
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, :n)"), {"p": project, "n": TEMPLATE_PROJECT})
        session.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Образец')"),
            {"d": document, "p": project},
        )
    for ordinal, version_key in enumerate(vs1_key["versions"], start=1):
        data = (FIXTURES / version_key["file"]).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        version = str(VersionUid.new())
        blob_id = ProfileBlobPublisher(sessions, blob_store).publish(
            data, role="source_document", media_type="application/pdf"
        )
        with session_scope(sessions) as session:
            session.execute(
                text(
                    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                    "sha256, page_count) VALUES (:v, :d, :o, 'application/pdf', :n, :s, :c)"
                ),
                {"v": version, "d": document, "o": ordinal, "n": len(data), "s": digest, "c": version_key["page_count"]},
            )
            session.execute(
                text(
                    "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                    "VALUES (:v, :r, :b, :s, :n, 'application/pdf')"
                ),
                {"v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": digest, "n": len(data)},
            )
        report = build_version_page_profiles(sessions, blob_store, version)
        assert report.complete, version_key["id"]
        versions.append(version)
        counts[version] = version_key["page_count"]
    return Doc(project, document, tuple(versions), counts)


@pytest.fixture
def lab(sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore, template: Doc) -> Lab:
    return Lab(sessions, engine, blob_store, template)


@pytest.fixture
def service(sessions: sessionmaker[Session], blob_store: S3BlobStore):
    from auditmanager.comparison.public import ComparisonMatrixService

    return ComparisonMatrixService(session_factory=sessions, blob_store=blob_store)


def _account(label: str, roles: tuple[str, ...]) -> Callable[[sessionmaker[Session]], tuple[str, str, frozenset[str]]]:
    def make(sessions: sessionmaker[Session]) -> tuple[str, str, frozenset[str]]:
        from auditmanager.access.accounts import AccountRepository
        from auditmanager.access.repository import UserRepository
        from tests.support.accounts import SUITE_NAMES, SUITE_PASSWORD, suite_login

        users = UserRepository()
        with sessions() as session:
            record = users.find_by_login(session, suite_login(label))
            if record is None:
                created = users.create_user(session, suite_login(label), SUITE_PASSWORD)
                accounts = AccountRepository()
                accounts.complete_profile(
                    session, user_uid=str(created.user_uid), email=None, last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1]
                )
                for role in roles:
                    accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
                record = users.find_by_login(session, suite_login(label))
                session.commit()
            return str(record.user_uid), record.login, frozenset(roles)

    return make


@pytest.fixture(scope="session")
def expert_uid(sessions: sessionmaker[Session]) -> str:
    return _account("matrix-expert", ("expert",))(sessions)[0]


@pytest.fixture(scope="session")
def admin_uid(sessions: sessionmaker[Session]) -> str:
    return _account("matrix-admin", ("admin",))(sessions)[0]
