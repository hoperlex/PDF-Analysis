"""PostgreSQL and object-store fixtures of the ``page_profile`` queue tests (`CMP-PROFILE-QUEUE-01`).

A lane's own services are required, never skipped: a test that skipped would report success while proving nothing.
The ``.env`` of the lane is read when the process environment lacks the names. The tests **commit** (a claim, a
heartbeat thread and a worker each use a connection of their own), so :class:`Lane` removes every work item and
attempt of the projects it seeded, then the worker rows it registered; the versions themselves stay
(``document_version`` refuses DELETE by trigger, which is not this suite's to defeat) and carry fresh identities, so a
run never meets another run's rows. The disposable lane database is dropped by ``make down``.

A version is a published ``document_version`` whose source PDF is a real blob, seeded the way
``tests/integration/comparison/profile`` seeds it; the claim is the real runner's.

**The suite shares its database with other integration directories** and must not depend on what they leave in it
(`CMP-PQ-ISOLATION-01`). The comparison queue yields to *any* claimable Run, picks the strongest queued item of *any*
project and reclaims *every* expired lease, which is right for a worker and wrong for a test that asks about its own
items. So the lane reads the queue through its own projects only: the runner's Run-priority gate is scoped to the
lane's projects (the pause gate is the real one), :meth:`Lane.claim` leases only an item of the lane's projects, and
:meth:`Lane.reclaim` counts only the lane's attempts. The strict priority of Runs over comparison work is not this
suite's to prove; ``tests/integration/comparison/work/test_claim_gates.py`` proves it against the real gates.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.bootstrap.composition import build_comparison_work
from auditmanager.comparison.profile.runner import ChildResult, ChildRunner, SubprocessChildRunner
from auditmanager.comparison.public import (
    ClaimGates,
    ComparisonWorkRepository,
    ComparisonWorkRunner,
    HandlerRegistry,
    PageProfileHandler,
    WorkDependencies,
    WorkItem,
    default_gates,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    JobId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
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
        #: Projects of *foreign* data the isolation test plants (they are removed, never claimed, by the lane).
        self.foreign_projects: list[str] = []
        self.foreign_runs: list[str] = []
        self.workers: list[str] = []
        self._worker: str | None = None

    # -- seeding ---------------------------------------------------------------------------------------------
    def seed(
        self, pdf_path: Path, page_count: int, *, project_uid: str | None = None, with_manifest: bool = True,
        manifest_sha256: str | None = None, manifest_role: str | None = None,
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
                    {"v": version, "r": manifest_role or MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": manifest_sha256 or digest, "n": len(data)},
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

    def gates(self) -> ClaimGates:
        """The real pause gate and a Run-priority gate that reads the lane's own projects only.

        ``default_gates().run_claimable`` is true while *any* Run of the database is claimable, and a database that
        other integration directories have used holds such Runs. This gate asks the same question (a queued Job of a
        Run that is queued or running and due) of the Runs of the projects this lane seeded: the lane seeds none, so
        it stays open, and it shuts for a Run of the lane's own, which :func:`test_foreign_rows` proves.
        """
        return ClaimGates(paused=default_gates().paused, run_claimable=self._own_run_claimable)

    def _own_run_claimable(self, session: Session) -> bool:
        return bool(session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM job j JOIN audit_run r ON r.run_id = j.run_id "
            "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
            "AND j.available_at <= statement_timestamp() AND r.project_uid = ANY (CAST(:p AS text[])))"
        ), {"p": list(self.projects)}).scalar_one())

    def runner(
        self, child_runner: ChildRunner | None = None, *, heartbeat_seconds: float = 20.0,
        pages_per_attempt: int | None = None,
    ) -> ComparisonWorkRunner:
        """The real runner with the one handler of the kind over ``child_runner`` (the real one if None).

        ``pages_per_attempt`` is the handler's bound (the shipped one if None): a test that shows a version longer than
        an attempt holds makes the attempt short instead of making the PDF long."""
        options: dict[str, Any] = {} if pages_per_attempt is None else {"pages_per_attempt": pages_per_attempt}
        handler = PageProfileHandler(self.dependencies(), runner=child_runner, **options)
        return ComparisonWorkRunner(
            self.sessions, registry=HandlerRegistry({handler.kind: handler}), modules=frozenset({"versions"}),
            repository=self.repository, gates=self.gates(), heartbeat_seconds=heartbeat_seconds,
        )

    def worker_runner(self) -> ComparisonWorkRunner:
        """The runner the worker builds (``build_comparison_work`` over the shipped handler tuples), module ``versions`` on.

        ``build_comparison_work`` takes no gates, so the runner is built while the module's ``default_gates`` is this
        lane's :meth:`gates`; nothing else about it is changed, and the patch ends with the build.
        """
        from unittest import mock

        with mock.patch("auditmanager.comparison.work.runner.default_gates", self.gates):
            return build_comparison_work(
                sessions=self.sessions, engine=self.engine, blob_store=self.blob_store,
                environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"},
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

    @contextmanager
    def _foreign_items_fenced(self) -> Iterator[None]:
        """Lock every queued item of a project that is not the lane's, for the length of the block.

        The pick is ``FOR UPDATE SKIP LOCKED`` of the strongest queued item of *any* project, so a foreign item that is
        stronger or older would be leased instead of the lane's own. A lock held on the foreign rows by a connection
        of its own makes the pick pass over them, and changes nothing in them (the transaction ends by a rollback).
        """
        with self.engine.connect() as fence:
            fence.execute(text(
                "SELECT comparison_work_id FROM comparison_work WHERE state = 'queued' "
                "AND NOT (project_uid = ANY (CAST(:p AS text[]))) ORDER BY comparison_work_id "
                "FOR UPDATE SKIP LOCKED"
            ), {"p": list(self.projects)})
            try:
                yield
            finally:
                fence.rollback()

    def claim(self, runner: ComparisonWorkRunner) -> WorkItem:
        """The runner's claim, which can lease an item of the lane's projects only."""
        with self._foreign_items_fenced():
            item = runner.claim(self.worker_id())
        if item is None:
            with self.sessions() as session:
                gates = self.gates()
                shut = {"paused": gates.paused(session), "own run claimable": gates.run_claimable(session)}
                session.rollback()
            raise AssertionError(f"the runner claimed nothing of the lane's projects: gates {shut}, or no item is due")
        assert item.project_uid in self.projects, f"the runner leased {item.work_id} of a foreign project"
        return item

    def reclaim(self, runner: ComparisonWorkRunner) -> int:
        """Run the runner's reclaim and answer how many of the lane's own attempts it ended.

        The reclaim fences every expired lease of the database (the worker's job), so its own answer counts other
        directories' attempts too; what the lane asks about is its own.
        """
        def live() -> set[str]:
            with self.sessions() as session:
                return {str(row[0]) for row in session.execute(text(
                    "SELECT a.comparison_work_attempt_id FROM comparison_work_attempt a "
                    "JOIN comparison_work w ON w.comparison_work_id = a.comparison_work_id "
                    "WHERE w.project_uid = ANY (CAST(:p AS text[])) AND a.state IN ('leased', 'running')"
                ), {"p": list(self.projects)})}

        before = live()
        runner.reclaim()
        return len(before - live())

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

    # -- rows of other directories (planted by the isolation test only) ------------------------------------------
    def queue_run(self, session: Session, *, project_uid: str, version_uid: str) -> str:
        """A Run in state ``queued`` with a due, queued Job, written in the caller's transaction."""
        run, job = str(RunId.new()), str(JobId.new())
        session.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, "
            "provider_mode, frozen_input_digest) VALUES (:r, :p, :v, :a, :b, 'recorded', :d)"
        ), {"r": run, "p": project_uid, "v": version_uid, "a": str(AnalysisProfileId.new()),
            "b": str(PromptBundleId.new()), "d": "b" * 64})
        session.execute(text("INSERT INTO job (job_id, run_id) VALUES (:j, :r)"), {"j": job, "r": run})
        session.execute(text("UPDATE audit_run SET state = 'queued' WHERE run_id = :r"), {"r": run})
        return run

    def foreign_project(self) -> str:
        project = str(ProjectUid.new())
        with session_scope(self.sessions) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Чужой проект')"), {"p": project})
        self.foreign_projects.append(project)
        return project

    def foreign_run(self) -> str:
        """A committed queued Run of a project that is not the lane's: what makes the real Run-priority gate yield."""
        project, document, version = self.foreign_project(), str(DocumentUid.new()), str(VersionUid.new())
        with session_scope(self.sessions) as session:
            session.execute(text(
                "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Чужой')"
            ), {"d": document, "p": project})
            session.execute(text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                "sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', 1, :s, 1)"
            ), {"v": version, "d": document, "s": "a" * 64})
            run = self.queue_run(session, project_uid=project, version_uid=version)
        self.foreign_runs.append(run)
        return run

    def foreign_item(self, *, priority: int = 100) -> str:
        """A committed queued ``page_profile`` item of a foreign project, stronger than any item the lane makes."""
        project = self.foreign_project()
        with session_scope(self.sessions) as session:
            return self.repository.enqueue(
                session, project_uid=project, module="versions", kind="page_profile",
                payload={"version_uid": str(VersionUid.new())}, priority=priority,
            ).work_id

    def foreign_expired_lease(self) -> tuple[str, str]:
        """A foreign item leased and left with an expired lease -- what a worker killed in another suite leaves.

        Answers ``(work_id, attempt_id)``. The item is the strongest in the database when it is claimed (priority 100).
        """
        work_id = self.foreign_item()
        with self.sessions() as session:
            claimed = self.repository.claim(
                session, worker_id=self.worker_id(), modules=frozenset({"versions"}), kinds=frozenset({"page_profile"}),
            )
            session.commit()
        assert claimed is not None and claimed.work_id == work_id, (
            "the planted item was not the strongest queued one: another item of priority 100 is in the database"
        )
        self.expire_lease(claimed.attempt_id)
        return work_id, claimed.attempt_id

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
            for run in self.foreign_runs:
                session.execute(text("DELETE FROM job WHERE run_id = :r"), {"r": run})
                session.execute(text("DELETE FROM audit_run WHERE run_id = :r"), {"r": run})
            for project in [*self.projects, *self.foreign_projects]:
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
