"""Fixtures of the AI pair check's database tests (`CMP-VC-AIPAIR-01`).

Real PostgreSQL (the lane's own stack at migration head ``0040``), never a skip: the question table's state edges and checks, the
immutable answer table, the unique content key and the live-scope index have no in-memory equivalent. As in the core's suite, no test
commits: one connection inside an outer transaction that is rolled back, with a session factory joined to it through
``create_savepoint``, so a command runs as production runs it (its own unit of work, its own commit) and nothing of a test
stays in the shared lane database.

The helpers are loaded by explicit path (a test never imports a ``conftest``); the core's recorded-mode support
(``ai_jobs_support.py``) is loaded the same way.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
core = _load("cmp_ai_jobs_01_support", HERE.parents[0] / "ai_jobs" / "ai_jobs_support.py")
support = _load("cmp_vc_aipair_01_support", HERE / "pairs_support.py")

EXPERT = frozenset({"expert"})


@dataclass
class Harness:
    connection: Connection
    sessions: "sessionmaker[Session]"
    engine: Engine

    def route(self, *, billing: str = "metered") -> Any:
        """An executor connection with a revision, routed to the work kind of the pair check in «Назначения»."""
        return core.recorded_route(self.connection, support.KIND, billing=billing)

    def world(self, **over: Any) -> Any:
        return support.new_world(self.connection, **over)

    def rig(self, world: Any, **over: Any) -> Any:
        return support.make_rig(self.connection, self.sessions, world, engine=self.engine, **over)


@pytest.fixture
def h() -> ModuleType:
    return support


@pytest.fixture
def core_support() -> ModuleType:
    """The AI-job core's recorded-mode helpers (``ai_jobs_support.py``): routes, revisions, the scripted live adapter."""
    return core


@pytest.fixture
def db(comparison_engine: Engine) -> Iterator[Harness]:
    connection = comparison_engine.connect()
    outer = connection.begin()
    sessions = sessionmaker(
        bind=connection, expire_on_commit=False, future=True, join_transaction_mode="create_savepoint",
    )
    try:
        yield Harness(connection=connection, sessions=sessions, engine=comparison_engine)
    finally:
        outer.rollback()
        connection.close()
