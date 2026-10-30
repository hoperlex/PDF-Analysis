"""Fixtures of the report lane's database tests (`CMP-VC-REPORT-01`).

Real PostgreSQL (the lane's own stack at migration head ``0040``) and the lane's private bucket, never a skip: the report's state edges, the one-job
link, the append-only artifacts and the frozen job column have no in-memory equivalent. Like the AI-job core's suite the tests do **not** commit: one
connection inside an outer transaction that is rolled back, a session factory joined to it with ``create_savepoint`` (a ``commit()`` of the service
releases a savepoint), so every command runs as production runs it -- its own unit of work, its own commit -- and nothing of a test stays in the
lane's database. ``document_version`` refuses DELETE by trigger, which is why a test cannot clean up after itself.
"""

from __future__ import annotations

import importlib.util
import os
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
    ComparisonReportService,
    ComparisonWorkRepository,
    RecordedAnswers,
    ReportStaticModelSource,
    report_handler,
)
from auditmanager.comparison.report import handler as handler_module
from auditmanager.comparison.work.model import WorkDependencies
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError

EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load("cmp_report_support", Path(__file__).resolve().parent / "report_support.py")


@pytest.fixture(scope="session")
def blob_store() -> S3BlobStore:
    if not os.environ.get("S3_ENDPOINT_URL"):
        pytest.fail("the lane's .env is not loaded (S3_ENDPOINT_URL): `set -a; . ./.env; set +a`")
    try:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    except StorageError as failure:
        pytest.fail(f"the lane's private bucket is not reachable: {failure}")
    return store


@dataclass
class Harness:
    """One rolled-back test: the connection, the session factory bound to it, the services and the worker's side."""

    connection: Connection
    sessions: "sessionmaker[Session]"
    work: ComparisonWorkRepository
    store: S3BlobStore
    answers: RecordedAnswers

    def service(self, *, modules: str = "versions", provider_mode: str = "recorded", **over: Any) -> ComparisonReportService:
        return ComparisonReportService(self.sessions, blob_store=self.store, comparison_modules=modules, provider_mode=provider_mode, **over)

    def handler(self, **over: Any) -> Any:
        deps = WorkDependencies(engine=None, session_factory=self.sessions, blob_store=self.store, work=self.work)  # type: ignore[arg-type]
        over.setdefault("model_source", ReportStaticModelSource(self.answers))
        return handler_module.ReportHandler(deps, **over)

    @staticmethod
    def consent(digest: str, confirmed: bool = True) -> AiConsentInput:
        return AiConsentInput(estimate_digest=digest, confirmed=confirmed)

    def state(self, sql: str, **values: Any) -> Any:
        from sqlalchemy import text

        return self.connection.execute(text(sql), values).scalar_one()

    def rows(self, sql: str, **values: Any) -> list[dict[str, Any]]:
        from sqlalchemy import text

        return [dict(row) for row in self.connection.execute(text(sql), values).mappings()]

    def worker(self) -> str:
        from auditmanager.workers.public import WorkerRegistry

        with self.sessions() as session:
            made = WorkerRegistry().register(session, version="cmp-report-test", slots=1)
            session.commit()
        return made

    def claim(self, worker_id: str, kind: str = "comparison_report") -> Any:
        with self.sessions() as session:
            item = self.work.claim(session, worker_id=worker_id, modules=frozenset({"versions"}), kinds=frozenset({kind}))
            session.commit()
        return item

    def drain(self, handler: Any, *, rounds: int = 60) -> list[str]:
        """Run the worker's side until nothing of this kind can be claimed: every claimed item is handled and ended with its outcome. Answers the
        outcomes (class names) in order."""
        worker = self.worker()
        outcomes: list[str] = []
        for _ in range(rounds):
            item = self.claim(worker)
            if item is None:
                break
            outcome = handler.run(item)
            with self.sessions() as session:
                self.work.finish(session, item.authority, outcome)
                session.commit()
            outcomes.append(type(outcome).__name__ + (f":{outcome.reason}" if hasattr(outcome, "reason") else ""))
        return outcomes


@pytest.fixture
def db(comparison_engine: Engine, blob_store: S3BlobStore, monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness]:
    monkeypatch.setattr(handler_module, "FINAL_POLL_SECONDS", 0.0)
    monkeypatch.setattr(handler_module, "PAUSED_POLL_SECONDS", 0.0)
    connection = comparison_engine.connect()
    outer = connection.begin()
    sessions = sessionmaker(bind=connection, expire_on_commit=False, future=True, join_transaction_mode="create_savepoint")
    try:
        yield Harness(connection=connection, sessions=sessions, work=ComparisonWorkRepository(), store=blob_store, answers=RecordedAnswers())
    finally:
        outer.rollback()
        connection.close()


@pytest.fixture
def h() -> ModuleType:
    return support


@pytest.fixture
def route(db: Harness) -> Any:
    """The executor connection routed to the report work kind (recorded: it names a connection and a model, and calls nothing)."""
    return support.base.recorded_route(db.connection, "comparison_report")


@pytest.fixture
def world(db: Harness, route: Any) -> dict[str, Any]:
    return support.report_world(db.connection)


@pytest.fixture
def make(db: Harness) -> Callable[..., Any]:
    """``make(kind, ...)``: an expert makes a draft report from the series' summary."""

    def build(world: dict[str, Any], kind: str = "client", *, reuse: bool = False, key: str | None = None, service: ComparisonReportService | None = None) -> dict[str, Any]:
        return (service or db.service()).create_report(
            series_id=world["series"], kind=kind, reuse=reuse, user_uid=support.ACTOR, actor_label="Эксперт", actor_roles=EXPERT,
            idempotency_key=key or support.new_id("k")[:32],
        )

    return build
