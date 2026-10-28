"""Fixtures of the comparison queue's database tests (`CMP-WORK-01`).

Real PostgreSQL (the lane's own stack at migration head ``0038``), never a skip: a lease, a row lock,
``SKIP LOCKED`` and the state-edge trigger have no in-memory equivalent. Unlike the comparison
suite's rolled-back transactions, these tests **commit** -- two claimants, a heartbeat thread and a
worker service each use a connection of their own and see only what is committed -- so every test
cleans up after itself: the ``project`` fixture deletes the work items and attempts it made, then
the project, then the ``worker`` fixture deletes its worker rows.

Isolation from other rows in the shared lane database is by ``kind``: every test uses a kind of its
own (``kind_name``), and every claim in these tests names only that kind, so a foreign item can
never be picked up here and an item made here is never picked up elsewhere.

The Run harness is loaded by explicit path under the module name the other suites use (one copy
serves every suite). Its autouse ``_no_network`` is deliberately **not** bound: the worker service
and the slot threads open connections of their own.
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.identity import new_ulid

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[2] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness: ModuleType = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)

engine = harness.engine
blob_store = harness.blob_store


@pytest.fixture(scope="session")
def helpers() -> ModuleType:
    return harness


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    """A **committing** session factory."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture
def kind_name() -> str:
    """A kind no other test and no other lane uses (the column's pattern: ``[a-z][a-z0-9_]{2,63}``)."""
    return f"cw_{uuid.uuid4().hex[:16]}"


@pytest.fixture
def project(sessions: sessionmaker[Session], make_worker: Callable[[], str]) -> Iterator[str]:
    """A committed project, and the removal of every work item and attempt made under it.

    It asks for ``make_worker`` so that it is set up *after* it and torn down *before* it: an
    attempt names its worker by a foreign key, so the attempts go first and the workers last.
    """
    project_uid = f"prj_{new_ulid()}"
    with sessions() as session:
        session.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, 'cmp-work-01 test')"),
            {"p": project_uid},
        )
        session.commit()
    try:
        yield project_uid
    finally:
        with sessions() as session:
            session.execute(text(
                "DELETE FROM comparison_work_attempt WHERE comparison_work_id IN "
                "(SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p)"
            ), {"p": project_uid})
            session.execute(text("DELETE FROM comparison_work WHERE project_uid = :p"), {"p": project_uid})
            session.execute(text("DELETE FROM project WHERE project_uid = :p"), {"p": project_uid})
            session.commit()


@pytest.fixture
def make_worker(sessions: sessionmaker[Session]) -> Iterator[Callable[[], str]]:
    """Registers worker rows (an attempt names its worker by a foreign key) and removes them last."""
    from auditmanager.workers.public import WorkerRegistry

    made: list[str] = []

    def make() -> str:
        with sessions() as session:
            worker_id = WorkerRegistry().register(session, version="cmp-work-01-test", slots=1)
            session.commit()
        made.append(worker_id)
        return worker_id

    yield make
    with sessions() as session:
        for worker_id in made:
            # The ``project`` fixture, set up after this one, has already removed the attempts.
            session.execute(text("DELETE FROM worker WHERE worker_id = :w"), {"w": worker_id})
        session.commit()


@pytest.fixture
def worker_id(make_worker: Callable[[], str]) -> str:
    return make_worker()


@pytest.fixture
def quiet_runs(sessions: sessionmaker[Session]) -> Iterator[None]:
    """Park every Job other suites left queued and un-pause dispatch, for the length of a test.

    The comparison loop yields to a claimable Run, so a foreign queued Job in the shared lane
    database would silence it. Restored afterwards, including the pause flag.
    """
    from auditmanager.jobs.public import JobRepository

    with sessions() as setup:
        JobRepository().reclaim_expired(setup)
        setup.commit()
    with sessions() as setup:
        parked = setup.execute(text(
            "SELECT job_id, available_at FROM job WHERE state = 'queued' FOR UPDATE"
        )).all()
        setup.execute(text(
            "UPDATE job SET available_at = timestamptz '2099-01-01' WHERE state = 'queued'"
        ))
        paused = setup.execute(text(
            "SELECT paused FROM execution_control WHERE singleton"
        )).scalar_one_or_none()
        JobRepository().set_paused(setup, paused=False)
        setup.commit()
    try:
        yield
    finally:
        with sessions() as cleanup:
            for job_id, available_at in parked:
                cleanup.execute(text(
                    "UPDATE job SET available_at = :available_at WHERE job_id = :job_id "
                    "AND state = 'queued'"
                ), {"job_id": job_id, "available_at": available_at})
            JobRepository().set_paused(cleanup, paused=bool(paused))
            cleanup.commit()


class QueueHelper:
    """The small committed reads and writes the tests make beside the code under test."""

    def __init__(self, sessions: sessionmaker[Session], project_uid: str, kind: str) -> None:
        from auditmanager.comparison.public import ComparisonWorkRepository

        self.sessions = sessions
        self.project_uid = project_uid
        self.kind = kind
        self.repository = ComparisonWorkRepository()

    def enqueue(self, **options: object) -> str:
        options.setdefault("module", "versions")
        with self.sessions() as session:
            enqueued = self.repository.enqueue(
                session, project_uid=self.project_uid, kind=self.kind, **options,  # type: ignore[arg-type]
            )
            session.commit()
        return enqueued.work_id

    def claim(self, worker_id: str, *, modules: tuple[str, ...] = ("versions",)) -> object:
        with self.sessions() as session:
            item = self.repository.claim(
                session, worker_id=worker_id, modules=frozenset(modules), kinds=frozenset({self.kind}),
            )
            session.commit()
        return item

    def work(self, work_id: str) -> dict[str, object]:
        with self.sessions() as session:
            return dict(session.execute(text(
                "SELECT state, attempt_count, max_attempts, failure_reason, current_work_attempt_id, "
                "cancel_requested_at IS NOT NULL AS cancel_requested, terminal_at IS NOT NULL AS terminal, "
                "not_before > clock_timestamp() AS delayed FROM comparison_work WHERE comparison_work_id = :w"
            ), {"w": work_id}).mappings().one())

    def attempts(self, work_id: str) -> list[dict[str, object]]:
        with self.sessions() as session:
            return [dict(row) for row in session.execute(text(
                "SELECT comparison_work_attempt_id AS attempt_id, attempt_no, state, failure_reason, "
                "worker_id, lease_expires_at IS NOT NULL AS has_lease, "
                "lease_expires_at > statement_timestamp() AS lease_current "
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


@pytest.fixture
def queue(sessions: sessionmaker[Session], project: str, kind_name: str) -> QueueHelper:
    return QueueHelper(sessions, project, kind_name)


class StubHandler:
    """A handler whose ``run`` is whatever the test gives it (default: complete at once)."""

    def __init__(self, kind: str, run: Callable[..., object] | None = None) -> None:
        from auditmanager.comparison.public import Completed

        self.kind = kind
        self.items: list[object] = []
        self._run = run or (lambda item: Completed())

    def run(self, item: object) -> object:
        self.items.append(item)
        return self._run(item)


@pytest.fixture
def make_runner(sessions: sessionmaker[Session], queue: QueueHelper) -> Callable[..., object]:
    """``make_runner(modules=..., handler=...)``: the runner with the real gates and one handler."""
    from auditmanager.comparison.public import ComparisonWorkRunner, HandlerRegistry

    def make(*, modules: frozenset[str] = frozenset({"versions"}), handler: StubHandler | None = None,
             **options: object) -> ComparisonWorkRunner:
        stub = handler or StubHandler(queue.kind)
        return ComparisonWorkRunner(
            sessions, registry=HandlerRegistry({stub.kind: stub}), modules=modules,
            repository=queue.repository, **options,  # type: ignore[arg-type]
        )

    return make


@pytest.fixture
def queue_run(sessions: sessionmaker[Session], blob_store: object, helpers: ModuleType) -> Callable[[], str]:
    """``queue_run()``: a committed, queued Run whose Job is claimable and at the top of the order."""
    from auditmanager.jobs.public import JobRepository
    from auditmanager.runs import RunRepository, start_audit_run
    from auditmanager.shared.identity import IdempotencyKey

    def queue_one() -> str:
        with sessions() as session:
            seeded = helpers.seed_version(session, blob_store)
            started = start_audit_run(
                session, version_uid=seeded.version_uid,
                analysis_profile_id=seeded.analysis_profile_id,
                prompt_bundle_id=seeded.prompt_bundle_id, provider_mode="recorded",
                idempotency_key=IdempotencyKey(f"cmp-work-{uuid.uuid4().hex}"),
            )
            run_id = str(started.run_id)
            RunRepository().advance(session, run_id=run_id, from_state="created", to_state="queued")
            jobs = JobRepository()
            job_id = jobs.enqueue(session, run_id=run_id)
            jobs.set_priority(session, job_id=job_id, priority=100)
            session.commit()
        return run_id

    return queue_one
