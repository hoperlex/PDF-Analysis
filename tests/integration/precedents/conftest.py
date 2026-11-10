"""Fixtures for the «Прецеденты» surface suite (`PREC-SETTINGS-01`): the run-suite harness, loaded by explicit path, and a factory that rolls back.

The same harness ``tests/integration/jobs/conftest.py`` binds (real PostgreSQL, never a skip), registered under the same module name so one copy
serves every suite; its autouse ``_no_network`` is not bound here, as there. What is different is ``journalled_sessions``: the journal of settings is
**append-only** (``AM003`` on any update or delete), so a test that committed a revision would leave it for every later suite -- and the window
setting is read by the night window's own tests. The factory below hands the service a session on one connection whose outer transaction is rolled
back when the test ends; ``join_transaction_mode="create_savepoint"`` makes the service's own ``commit()`` release a savepoint, and a refusal
(its session closing on an error) roll back to it, so what an earlier call of the same test wrote is still there to be read.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness: ModuleType = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)

engine = harness.engine


@pytest.fixture
def journalled_sessions(engine: Engine) -> Iterator[sessionmaker[Session]]:
    """A session factory whose every unit of work joins one transaction that is rolled back at the end of the test."""
    connection = engine.connect()
    outer = connection.begin()
    try:
        yield sessionmaker(bind=connection, expire_on_commit=False, future=True, join_transaction_mode="create_savepoint")
    finally:
        outer.rollback()
        connection.close()


@pytest.fixture
def admin_uid(journalled_sessions: sessionmaker[Session]) -> str:
    """The seeded administrator: the actor of every write below (the journal's foreign key needs an account that exists)."""
    with journalled_sessions() as session:
        return str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
