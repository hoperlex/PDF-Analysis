"""Fixtures of the comparison spend journal's database tests (`CMP-SPEND-01`).

Real PostgreSQL (the lane's own stack at migration head ``0038``), never a skip: an advisory lock, a trigger
that refuses an insert in any state but ``prepared``, the state-edge guard and a Run's claim have no
in-memory equivalent. The tests **commit** -- a call's three transactions, a second worker and the Run claim
under test each use a connection of their own and see only what is committed -- so every test cleans up
after itself: the ``project`` fixture removes the journal rows, attempts and items it made, then the project;
the worker rows go last.

Isolation from other rows of the shared lane database is by ``kind`` (a name of its own per test) and by the
project; the **day** ceiling reads the whole installation, so a test that needs an empty day asks for the
``clean_day`` fixture, which refuses to run on a database where another project already spent today.

The helpers (``spend_support.py``) and the ``EXEC-PAR-QUEUE-01`` connection rows
(``tests/integration/jobs/connection_limit_support.py``) are loaded by explicit path and handed to a test by
the ``h`` and ``helpers`` fixtures: a test never imports a ``conftest``.
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.public import ComparisonModelCaller, ComparisonSpendRepository
from auditmanager.shared.identity import new_ulid


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load(
    "exec_par_queue_connection_limit_support",
    Path(__file__).resolve().parents[2] / "jobs" / "connection_limit_support.py",
)
spend_support = _load("cmp_spend_01_spend_support", Path(__file__).resolve().parent / "spend_support.py")


@pytest.fixture(scope="session")
def h() -> ModuleType:
    """The helper module: ``h.ScriptedAdapter``, ``h.make_call``, ``h.reply`` and the constants."""
    return spend_support


@pytest.fixture(scope="session")
def helpers() -> ModuleType:
    """The ``EXEC-PAR-QUEUE-01`` rows: connections, queued Runs, the shipped claim."""
    return support


@pytest.fixture
def sessions(comparison_engine: Engine) -> sessionmaker[Session]:
    """A **committing** session factory."""
    return sessionmaker(bind=comparison_engine, expire_on_commit=False, future=True)


@pytest.fixture
def kind_name() -> str:
    return f"cs_{uuid.uuid4().hex[:16]}"


@pytest.fixture
def worker_id(sessions: sessionmaker[Session]) -> Iterator[str]:
    from auditmanager.workers.public import WorkerRegistry

    with sessions() as session:
        made = WorkerRegistry().register(session, version="cmp-spend-01-test", slots=1)
        session.commit()
    yield made
    with sessions() as session:
        session.execute(text("DELETE FROM worker WHERE worker_id = :w"), {"w": made})
        session.commit()


@pytest.fixture
def project(sessions: sessionmaker[Session], worker_id: str) -> Iterator[str]:
    """A committed project and, on the way out, every journal row, attempt and item made under it.

    It asks for ``worker_id`` so it is torn down first: an attempt names its worker by a foreign key."""
    project_uid = f"prj_{new_ulid()}"
    with sessions() as session:
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'cmp-spend-01 test')"),
                        {"p": project_uid})
        session.commit()
    try:
        yield project_uid
    finally:
        with sessions() as session:
            session.execute(text(
                "DELETE FROM comparison_model_call WHERE comparison_work_id IN "
                "(SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p)"), {"p": project_uid})
            session.execute(text(
                "DELETE FROM executor_task WHERE comparison_attempt_id IN "
                "(SELECT a.comparison_work_attempt_id FROM comparison_work_attempt a JOIN comparison_work w "
                "ON w.comparison_work_id = a.comparison_work_id WHERE w.project_uid = :p)"), {"p": project_uid})
            session.execute(text(
                "DELETE FROM comparison_work_attempt WHERE comparison_work_id IN "
                "(SELECT comparison_work_id FROM comparison_work WHERE project_uid = :p)"), {"p": project_uid})
            session.execute(text("DELETE FROM comparison_work WHERE project_uid = :p"), {"p": project_uid})
            session.execute(text("DELETE FROM project WHERE project_uid = :p"), {"p": project_uid})
            session.commit()


@pytest.fixture
def clean_day(sessions: sessionmaker[Session], project: str) -> None:
    """The installation has spent nothing today apart from this test's own project."""
    with sessions() as session:
        others = session.execute(text(
            "SELECT count(*) FROM comparison_model_call c JOIN comparison_work w "
            "ON w.comparison_work_id = c.comparison_work_id WHERE w.project_uid <> :p "
            "AND c.prepared_at >= (date_trunc('day', clock_timestamp() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')"
        ), {"p": project}).scalar_one()
    assert others == 0, "another project has journalled calls today; the day ceiling tests need an empty day"


@pytest.fixture
def queue(sessions: sessionmaker[Session], project: str, kind_name: str, worker_id: str) -> object:
    return spend_support.Queue(sessions, project, kind_name, worker_id)


@pytest.fixture
def journal(sessions: sessionmaker[Session]) -> object:
    return spend_support.Journal(sessions)


@pytest.fixture
def caller(sessions: sessionmaker[Session]) -> ComparisonModelCaller:
    return ComparisonModelCaller(sessions)


@pytest.fixture
def repository() -> ComparisonSpendRepository:
    return ComparisonSpendRepository()


@pytest.fixture
def connection(sessions: sessionmaker[Session]) -> tuple[str, str]:
    """A committed executor connection and its first revision: ``(connection_id, revision_id)``."""
    return support.new_connection(sessions)
