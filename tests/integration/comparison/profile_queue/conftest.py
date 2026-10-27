"""PostgreSQL and object-store fixtures of the ``page_profile`` queue tests (`CMP-PROFILE-QUEUE-01`).

A lane's own services are required, never skipped: a test that skipped would report success while proving nothing.
The ``.env`` of the lane is read when the process environment lacks the names. The tests **commit** (a claim, a
heartbeat thread and a worker each use a connection of their own), so :class:`Lane` removes every work item and
attempt of the projects it seeded, then the worker rows it registered; the versions themselves stay
(``document_version`` refuses DELETE by trigger, which is not this suite's to defeat) and carry fresh identities, so a
run never meets another run's rows. The disposable lane database is dropped by ``make down``.

A version is a published ``document_version`` whose source PDF is a real blob, seeded the way
``tests/integration/comparison/profile`` seeds it; the claim is the real runner's, with the real gates.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.runner import ChildResult, ChildRunner, SubprocessChildRunner
from auditmanager.comparison.public import (
    ComparisonWorkRepository,
    ComparisonWorkRunner,
    HandlerRegistry,
    PageProfileHandler,
    WorkDependencies,
    WorkItem,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
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
def engine() -> Iterator[Engine]:
    _load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: run `make up` and `make migrate` for this lane. These tests never skip.")
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with built.connect() as connection:
            for table in ("comparison_page_profile", "comparison_work"):
                if connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one_or_none() is None:
                    pytest.fail(f"the database has no {table} table: run `make migrate` (head 0038)")
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def sessions(engine: Engine) -> sessionmaker[Session]:
    """A **committing** session factory."""
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
    import json

    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class Seeded:
    project_uid: str
    version_uid: str
    page_count: int


class SpyRunner:
    """The real child runner, with a hook on a ``(mode, page)`` call (page is 0-based).

    A hook may do something and return ``None`` (the real child then runs), raise (a child that never started), or
    return a :class:`ChildResult` (a child that ended as that result says, and was not started).
    """

    def __init__(self) -> None:
        self.real: ChildRunner = SubprocessChildRunner()
        self.calls: list[tuple[str, int]] = []
        self.hooks: dict[tuple[str, int], Callable[[], ChildResult | None]] = {}

    def run(self, settings: Mapping[str, Any], limits: Any) -> ChildResult:
        key = (str(settings["mode"]), int(settings["page"]))
        self.calls.append(key)
        hook = self.hooks.get(key)
        if hook is not None:
            answered = hook()
            if answered is not None:
                return answered
        return self.real.run(settings, limits)


class Lane:
    """The small committed reads and writes the tests make beside the code under test."""

    def __init__(self, sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore) -> None:
        self.sessions = sessions
        self.engine = engine
        self.blob_store = blob_store
        self.repository = ComparisonWorkRepository()
        self.projects: list[str] = []
        self.workers: list[str] = []
        self._worker: str | None = None

    # -- seeding ---------------------------------------------------------------------------------------------
    def seed(
        self, pdf_path: Path, page_count: int, *, project_uid: str | None = None, with_manifest: bool = True,
    ) -> Seeded:
        from auditmanager.comparison.profile.publish import ProfileBlobPublisher
        from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT

        data = pdf_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        project, document, version = project_uid or str(ProjectUid.new()), str(DocumentUid.new()), str(VersionUid.new())
        blob_id = ProfileBlobPublisher(self.sessions, self.blob_store).publish(
            data, role="source_document", media_type="application/pdf"
        )
        with session_scope(self.sessions) as session:
            if project_uid is None:
                session.execute(
                    text("INSERT INTO project (project_uid, name) VALUES (:p, 'Очередь профилей страниц')"), {"p": project}
                )
                self.projects.append(project)
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
                    {"v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": digest, "n": len(data)},
                )
        return Seeded(project, version, page_count)

    # -- the queue -------------------------------------------------------------------------------------------
    def worker_id(self) -> str:
        from auditmanager.workers.public import WorkerRegistry

        if self._worker is None:
            with self.sessions() as session:
                self._worker = WorkerRegistry().register(session, version="cmp-profile-queue-01-test", slots=1)
                session.commit()
            self.workers.append(self._worker)
        return self._worker

    def dependencies(self) -> WorkDependencies:
        return WorkDependencies(
            engine=self.engine, session_factory=self.sessions, blob_store=self.blob_store, work=self.repository,
        )

    def runner(
        self, child_runner: ChildRunner | None = None, *, heartbeat_seconds: float = 20.0,
    ) -> ComparisonWorkRunner:
        """The real runner and gates, with the one handler of the kind over ``child_runner`` (the real one if None)."""
        handler = PageProfileHandler(self.dependencies(), runner=child_runner)
        return ComparisonWorkRunner(
            self.sessions, registry=HandlerRegistry({handler.kind: handler}), modules=frozenset({"versions"}),
            repository=self.repository, heartbeat_seconds=heartbeat_seconds,
        )

    def enqueue(self, seeded: Seeded, *, retry_failed: bool = False) -> Any:
        """The call ``CMP-INGEST-02`` makes after a set is confirmed, committed."""
        from auditmanager.comparison.public import enqueue_version_page_profiles

        with self.sessions() as session:
            enqueued = enqueue_version_page_profiles(
                session, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
                created_by_user_uid=USER, retry_failed=retry_failed,
            )
            session.commit()
        return enqueued

    def claim(self, runner: ComparisonWorkRunner) -> WorkItem:
        item = runner.claim(self.worker_id())
        assert item is not None, "the runner claimed nothing: a gate is shut or no item is due"
        return item

    def cancel(self, work_id: str) -> str:
        with self.sessions() as session:
            answer = self.repository.cancel(session, work_id)
            session.commit()
        return answer

    def work(self, work_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            return dict(session.execute(text(
                "SELECT state, module, kind, payload, dedupe_key, priority, attempt_count, max_attempts, "
                "failure_reason, created_by_user_uid, project_uid, "
                "cancel_requested_at IS NOT NULL AS cancel_requested, terminal_at IS NOT NULL AS terminal "
                "FROM comparison_work WHERE comparison_work_id = :w"
            ), {"w": work_id}).mappings().one())

    def work_of(self, project_uid: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            return [dict(row) for row in session.execute(text(
                "SELECT comparison_work_id AS work_id, state, dedupe_key, payload FROM comparison_work "
                "WHERE project_uid = :p ORDER BY created_at, comparison_work_id"
            ), {"p": project_uid}).mappings()]

    def attempts(self, work_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            return [dict(row) for row in session.execute(text(
                "SELECT comparison_work_attempt_id AS attempt_id, attempt_no, state, failure_reason "
                "FROM comparison_work_attempt WHERE comparison_work_id = :w ORDER BY attempt_no"
            ), {"w": work_id}).mappings()]

    def expire_lease(self, attempt_id: str) -> None:
        """The state a killed worker leaves: its lease ran out and nothing renewed it."""
        with self.sessions() as session:
            session.execute(text(
                "UPDATE comparison_work_attempt SET lease_expires_at = statement_timestamp() - interval '1 second' "
                "WHERE comparison_work_attempt_id = :a"
            ), {"a": attempt_id})
            session.commit()

    def make_due(self, work_id: str) -> None:
        with self.sessions() as session:
            session.execute(text(
                "UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' "
                "WHERE comparison_work_id = :w"
            ), {"w": work_id})
            session.commit()

    # -- the profiles ----------------------------------------------------------------------------------------
    def rows(self, version_uid: str) -> list[Any]:
        with session_scope(self.sessions) as session:
            return list(session.execute(
                text(
                    "SELECT comparison_page_profile_id AS id, page_number, status, reason, content_key, profile_blob_id, "
                    "preview_blob_id, thumbnail_blob_id FROM comparison_page_profile "
                    "WHERE version_uid = :v ORDER BY page_number"
                ),
                {"v": version_uid},
            ).all())

    # -- cleanup ---------------------------------------------------------------------------------------------
    def clean(self) -> None:
        with self.sessions() as session:
            for project in self.projects:
                session.execute(text(
                    "DELETE FROM comparison_work_attempt WHERE comparison_work_id IN "
                    "(SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p)"
                ), {"p": project})
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


@pytest.fixture
def spy() -> SpyRunner:
    return SpyRunner()


@pytest.fixture
def small_pdf(tmp_path: Path) -> Callable[[int], Path]:
    """``small_pdf(pages)``: an A4 PDF whose pages the object store has never seen."""

    def make(pages: int = 3) -> Path:
        from reportlab.pdfgen import canvas

        path = tmp_path / f"queue-{uuid.uuid4().hex}.pdf"
        sheet = canvas.Canvas(str(path), pagesize=(595.28, 841.89))
        for number in range(pages):
            sheet.drawString(72, 700, f"queue {uuid.uuid4()} page {number}")
            sheet.showPage()
        sheet.save()
        return path

    return make


@pytest.fixture
def vs1_v1() -> Path:
    return FIXTURES / "vs1" / "v1.pdf"
