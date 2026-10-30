"""Fixtures of the sheet-description database tests (`CMP-VC-AISHEET-01`), after the AI-job core's.

Real PostgreSQL (the lane's own stack at head ``0040``), never a skip. Like the core's suite these tests do **not** commit: one
connection, an outer transaction that is rolled back, a session factory joined with ``create_savepoint`` -- the service, the handler
and the spend wrapper commit as in production and nothing stays in the shared database (``document_version`` refuses DELETE).

``lab`` is the whole of it wired: the world, the pages (a fake :class:`SheetMaterial`), the recorded model, the AI-job core with the
``sheet_changes`` method, the lane's service and the handler. A test files an answer under the digest of the request the handler will
build and runs the queue's items one by one, as the worker does. **No test calls a live model.**
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import ModelRequest
from auditmanager.comparison.ai_sheets import describe as ds
from auditmanager.comparison.ai_sheets import packet as pk
from auditmanager.comparison.ai_sheets import schema as sc
from auditmanager.comparison.ai_sheets.handler import SheetChangesHandler
from auditmanager.comparison.ai_sheets.method import SheetChangesMethod, facts_of
from auditmanager.comparison.ai_sheets.repository import AiSheetRepository
from auditmanager.comparison.ai_sheets.service import ComparisonAiSheetService
from auditmanager.comparison.public import (
    AiConsentInput,
    AiJobCommand,
    AiScope,
    ComparisonAiJobService,
    ComparisonModelCaller,
    ComparisonWorkRepository,
    RecordedAnswers,
)
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.comparison.work.model import WorkDependencies

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = _load("cmp_ai_jobs_01_support", _HERE.parents[0] / "ai_jobs" / "ai_jobs_support.py")
fx = _load("cmp_ai_sheets_fixtures", _HERE.parents[2] / "unit" / "comparison" / "ai_sheets" / "sheet_fixtures.py")
support = _load("cmp_ai_sheets_support", _HERE / "sheets_support.py")

EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})
NO_OTHER = {"what": "", "value_a": "", "value_b": "", "image_id": ""}


@dataclass
class Harness:
    connection: Connection
    sessions: "sessionmaker[Session]"
    work: ComparisonWorkRepository

    def state(self, sql: str, **values: Any) -> Any:
        return self.connection.execute(text(sql), values).scalar_one()

    def rows(self, sql: str, **values: Any) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(text(sql), values).mappings()]

    def worker(self) -> str:
        from auditmanager.workers.public import WorkerRegistry

        with self.sessions() as session:
            made = WorkerRegistry().register(session, version="cmp-vc-aisheet-01-test", slots=1)
            session.commit()
        return made

    def claim(self, worker_id: str, kind: str) -> Any:
        with self.sessions() as session:
            item = self.work.claim(session, worker_id=worker_id, modules=frozenset({"versions"}), kinds=frozenset({kind}))
            session.commit()
        return item


@pytest.fixture
def db(comparison_engine: Engine) -> Iterator[Harness]:
    connection = comparison_engine.connect()
    outer = connection.begin()
    sessions = sessionmaker(bind=connection, expire_on_commit=False, future=True, join_transaction_mode="create_savepoint")
    try:
        yield Harness(connection=connection, sessions=sessions, work=ComparisonWorkRepository())
    finally:
        outer.rollback()
        connection.close()


class FixedRoutes:
    """The route source of a test: one route, the recorded adapter (or a scripted one) for every job."""

    def __init__(self, adapter: Any, *, unmetered: bool = True, pin: Any = None) -> None:
        self.adapter, self.unmetered, self.pin = adapter, unmetered, pin
        self.jobs: list[str] = []

    def route_for(self, session: Session, job: Any) -> CallRoute:
        self.jobs.append(job.job_id)
        return CallRoute(
            adapter=self.adapter, model_identity=job.pinned_model, connection_revision_id=job.connection_revision_id,
            expected_model=core.GATEWAY, unmetered=self.unmetered, pin=self.pin,
        )


@dataclass
class Lab:
    db: Harness
    world: Any
    material: Any
    answers: RecordedAnswers
    route: Any
    method: SheetChangesMethod
    jobs: ComparisonAiJobService
    service: ComparisonAiSheetService
    handler: SheetChangesHandler
    routes: FixedRoutes
    repo: AiSheetRepository = field(default_factory=AiSheetRepository)
    worker_id: str = ""

    # -- commands and scopes ---------------------------------------------------------------------------------------
    def command(self, kind: str = "start_comparison_ai_sheet_changes", *, key: str | None = None, roles: frozenset[str] = EXPERT) -> AiJobCommand:
        return AiJobCommand(command_type=kind, idempotency_key=key or core.new_id("k")[:32], user_uid=core.ACTOR, actor_roles=roles)

    def series_scope(self, *, restart: bool = False) -> AiScope:
        return AiScope("sheet_changes", self.world.project, self.world.document, series_id=self.world.series, restart=restart)

    def pair_scope(self, name: str) -> AiScope:
        return AiScope("sheet_changes", self.world.project, self.world.document, sheet_pair_id=self.world[name].pair)

    def consent(self, digest: str, confirmed: bool = True) -> AiConsentInput:
        return AiConsentInput(estimate_digest=digest, confirmed=confirmed)

    def start_series(self, *, restart: bool = False, **over: Any) -> dict[str, Any]:
        estimate = self.service.estimate_series(series_id=self.world.series, only_failed=False)
        return self.service.start_series(
            series_id=self.world.series, consent=self.consent(estimate["estimate_digest"]), restart=restart,
            command=over.pop("command", None) or self.command(),
        )

    def start_pair(self, name: str) -> dict[str, Any]:
        estimate = self.service.estimate_description(sheet_pair_id=self.world[name].pair)
        return self.service.start_description(
            sheet_pair_id=self.world[name].pair, consent=self.consent(estimate["estimate_digest"]),
            command=self.command("start_comparison_sheet_description"),
        )

    # -- the model --------------------------------------------------------------------------------------------------
    def job_model(self) -> str:
        return self.route.pinned_model

    def packet_of(self, name: str) -> tuple[pk.Packet, ModelRequest]:
        """The packet and the request the handler builds for a pair of the world (through the same code)."""
        with self.db.sessions() as session:
            pair = self.repo.pair(session, self.world[name].pair)
            result = self.repo.result_document(session, pair.result_id)
        packet = pk.assemble(facts_of(pair), result, self.material, render=True, xrefs=True)
        images = [(i["id"], packet.image_bytes[i["id"]]) for i in packet.images]
        return packet, ds.build_request(self.job_model(), packet.prompt, sc.SHEET_CHANGES_SCHEMA, images)

    def good_answer(self, packet: pk.Packet, **over: Any) -> dict[str, Any]:
        change = {
            "object": "Люк Лк-1", "place": "таблица люков", "kind": "quantity", "summary": "Лк-1 — количество 2 → 3.",
            "fields": [{"name": "количество", "before": "2", "after": "3", "unit": "шт", "source": "text", "certainty": "confirmed"}],
            "members": [], "mapping": "one_to_one", "candidate_ids": ["O1"], "image_ids": ["I2"], "other_representation": NO_OTHER,
            "limitation": "",
        }
        rest = [{"candidate_ids": [c["id"]], "reason": "formatting", "note": ""} for c in packet.candidates if c["id"] != "O1"]
        return {"packet_id": packet.packet_id, "part_id": "P1", "changes": [change], "unresolved": [], "excluded": rest,
                "context_requests": []} | over

    def record(self, name: str, answer: dict[str, Any] | None = None) -> str:
        packet, request = self.packet_of(name)
        return self.answers.record(request, json.dumps(answer or self.good_answer(packet), ensure_ascii=False))

    def record_single(self, name: str, answer: dict[str, Any] | None = None) -> str:
        """File the answer for an added or a removed sheet: the request is built as the handler builds it."""
        sheet = self.world[name]
        with self.db.sessions() as session:
            pair = self.repo.pair(session, sheet.pair)
        kind, side = str(pair.single_kind), "B" if pair.single_kind == "added" else "A"
        profile = pair.subject_page_profile or ""
        page = self.material.page(profile)
        words = sorted(page.words, key=lambda w: (round(float(w.top) / 4.0), float(w.x0)))
        sheet_text = " ".join(w.text for w in words)
        facts = facts_of(pair)
        prompt = sc.SINGLE_PROMPT.format(
            what="появился новый лист" if kind == "added" else "лист удалён (был в прежней версии)",
            verb="добавлено" if kind == "added" else "убрано", title=pair.title or "—", side=side,
            label=facts.label_b if side == "B" else facts.label_a, page=(pair.page_b if side == "B" else pair.page_a) or 0,
            project=facts.designation or facts.project_title or "—", limit=6000, text=sheet_text[:6000] or "(текстового слоя нет)",
        )
        image = self.material.overview(profile)
        request = ds.build_request(self.job_model(), prompt, sc.SINGLE_SCHEMA, [("I1", image)] if image else [])
        body = answer or {"sheet_kind": "схема", "summary": "Схема щита ЩО-2.", "objects": [{"name": "щит", "detail": "ЩР-1"}],
                          "marks": ["ЩР-1", "ЩО-2"], "limitation": ""}
        return self.answers.record(request, json.dumps(body, ensure_ascii=False))

    # -- the worker -------------------------------------------------------------------------------------------------
    def run_next(self) -> tuple[Any, Any] | None:
        """Claim the next item of the kind and run it as the worker does: ``handler.run`` then the queue's ``finish``."""
        item = self.db.claim(self.worker_id, "comparison_sheet_changes")
        if item is None:
            return None
        outcome = self.handler.run(item)
        with self.db.sessions() as session:
            self.db.work.finish(session, item.authority, outcome)
            session.commit()
        return item, outcome

    def drain(self, limit: int = 40) -> list[tuple[str, Any]]:
        """Run items until the queue has none claimable; answers ``(sheet pair id or 'drain', outcome)`` in order."""
        ran = []
        for _ in range(limit):
            step = self.run_next()
            if step is None:
                return ran
            item, outcome = step
            ran.append((str(item.payload.get("sheet_pair_id") or "drain"), outcome))
        raise AssertionError("the queue did not drain")

    def job(self, job_id: str) -> dict[str, Any]:
        return self.db.rows("SELECT * FROM comparison_ai_job WHERE comparison_ai_job_id = :j", j=job_id)[0]

    def items(self, job_id: str) -> dict[str, str]:
        rows = self.db.rows("SELECT comparison_sheet_pair_id AS pair, state FROM comparison_ai_sheet_item WHERE comparison_ai_job_id = :j", j=job_id)
        names = {s.pair: n for n, s in self.world.sheets.items()}
        return {names[r["pair"]]: r["state"] for r in rows}

    def descriptions(self) -> list[dict[str, Any]]:
        return self.db.rows("SELECT * FROM comparison_sheet_description WHERE project_uid = :p ORDER BY created_at, comparison_sheet_description_id",
                            p=self.world.project)

    def calls(self) -> list[dict[str, Any]]:
        return self.db.rows("SELECT c.* FROM comparison_model_call c JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id "
                            "WHERE w.project_uid = :p ORDER BY c.prepared_at", p=self.world.project)


@pytest.fixture
def h() -> ModuleType:
    return support


@pytest.fixture
def lab(db: Harness, monkeypatch: pytest.MonkeyPatch) -> Lab:
    import auditmanager.comparison.ai_sheets.handler as handler_module

    monkeypatch.setattr(handler_module, "DRAIN_POLL_SECONDS", 0.0)
    monkeypatch.setattr(handler_module, "PAUSED_WAIT_SECONDS", 0.0)
    world = support.sheet_world(db.connection, fx)
    material = support.material_for(fx, world)
    route = core.recorded_route(db.connection, "comparison_sheet_changes", billing="not_metered")
    answers = RecordedAnswers()
    method = SheetChangesMethod(material)
    jobs = ComparisonAiJobService(db.sessions, methods=[method], work=db.work, comparison_modules="versions", provider_mode="recorded")
    service = ComparisonAiSheetService(db.sessions, jobs=jobs, method=method)
    routes = FixedRoutes(answers)
    handler = SheetChangesHandler(
        WorkDependencies(engine=None, session_factory=db.sessions, blob_store=None, work=db.work),  # type: ignore[arg-type]
        routes=routes, material=material, jobs=jobs, caller=ComparisonModelCaller(db.sessions),
    )
    built = Lab(db=db, world=world, material=material, answers=answers, route=route, method=method, jobs=jobs, service=service,
                handler=handler, routes=routes)
    built.worker_id = db.worker()
    return built
