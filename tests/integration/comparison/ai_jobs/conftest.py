"""Fixtures of the AI-job core's database tests (`CMP-AI-JOBS-01`).

Real PostgreSQL (the lane's own stack at migration head ``0040``), never a skip: the live-scope unique indexes, the state-edge
trigger, the consent trigger, the frozen ``comparison_ai_job_id`` and the advisory locks of the spend wrapper have no in-memory
equivalent. Unlike the queue's and the spend journal's suites these tests do **not** commit: every test works on one connection
inside an outer transaction that is rolled back, and the session factory joins it with ``create_savepoint`` (a ``commit()``
of the service releases a savepoint), so a command is exercised as the production code runs it -- its own unit of work, its
own commit -- and nothing of a test stays in the shared lane database (``document_version`` refuses DELETE by trigger).

The helpers (``ai_jobs_support.py``) are loaded by explicit path and handed to a test by the ``h`` fixture: a test never imports
a ``conftest``.
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

from auditmanager.comparison.public import (
    AiConsentInput,
    AiJobCommand,
    AiMethod,
    AiScope,
    ComparisonAiJobService,
    ComparisonWorkRepository,
)


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load("cmp_ai_jobs_01_support", Path(__file__).resolve().parent / "ai_jobs_support.py")

EXPERT = frozenset({"expert"})


@dataclass
class Harness:
    """One rolled-back test: the connection, the session factory bound to it and the builders a test needs."""

    connection: Connection
    sessions: "sessionmaker[Session]"
    work: ComparisonWorkRepository

    def service(self, *methods: AiMethod, modules: str = "versions", provider_mode: str = "recorded", **over: Any) -> ComparisonAiJobService:
        return ComparisonAiJobService(
            self.sessions, methods=list(methods), work=self.work, comparison_modules=modules,
            provider_mode=provider_mode, **over,
        )

    def command(self, kind: str = "start_comparison_ai_pair_check", *, key: str | None = None, roles: frozenset[str] = EXPERT) -> AiJobCommand:
        return AiJobCommand(
            command_type=kind, idempotency_key=key or support.new_id("k")[:32], user_uid=support.ACTOR, actor_roles=roles,
        )

    @staticmethod
    def consent(digest: str, confirmed: bool = True) -> AiConsentInput:
        return AiConsentInput(estimate_digest=digest, confirmed=confirmed)

    def start(self, service: ComparisonAiJobService, scope: AiScope, **over: Any) -> Any:
        """Estimate and start with the digest just shown: the happy path of «Запустить»."""
        digest = service.estimate(scope).estimate_digest
        return service.start(scope=scope, consent=self.consent(digest), command=over.pop("command", None) or self.command(), **over)

    def state(self, sql: str, **values: Any) -> Any:
        from sqlalchemy import text

        return self.connection.execute(text(sql), values).scalar_one()

    def rows(self, sql: str, **values: Any) -> list[dict[str, Any]]:
        from sqlalchemy import text

        return [dict(row) for row in self.connection.execute(text(sql), values).mappings()]

    def worker(self) -> str:
        from auditmanager.workers.public import WorkerRegistry

        with self.sessions() as session:
            made = WorkerRegistry().register(session, version="cmp-ai-jobs-01-test", slots=1)
            session.commit()
        return made

    def claim(self, worker_id: str, kind: str) -> Any:
        with self.sessions() as session:
            item = self.work.claim(session, worker_id=worker_id, modules=frozenset({"versions"}), kinds=frozenset({kind}))
            session.commit()
        return item


@pytest.fixture
def h() -> ModuleType:
    return support


@pytest.fixture
def db(comparison_engine: Engine) -> Iterator[Harness]:
    connection = comparison_engine.connect()
    outer = connection.begin()
    sessions = sessionmaker(
        bind=connection, expire_on_commit=False, future=True, join_transaction_mode="create_savepoint",
    )
    try:
        yield Harness(connection=connection, sessions=sessions, work=ComparisonWorkRepository())
    finally:
        outer.rollback()
        connection.close()


@pytest.fixture
def world(db: Harness) -> dict[str, Any]:
    return support.new_world(db.connection)


@pytest.fixture
def scope_of(world: dict[str, Any]) -> Callable[..., AiScope]:
    """``scope_of("pair_check")`` -> the scope the method needs in the test's world (``sheet_changes`` takes ``pair=True`` for
    the single-sheet form, ``restart=True`` for «Описать заново»)."""

    def build(method: str, *, pair: bool = False, restart: bool = False) -> AiScope:
        base = {"method": method, "project_uid": world["project"], "document_uid": world["document"]}
        if method == "pair_check":
            return AiScope(matrix_id=world["build"], **base)
        if method == "sheet_changes":
            return AiScope(sheet_pair_id=world["pair"], restart=restart, **base) if pair else AiScope(series_id=world["series"], restart=restart, **base)
        if method == "spec":
            return AiScope(transition_id=world["transition"], **base)
        return AiScope(series_id=world["series"], **base)

    return build
