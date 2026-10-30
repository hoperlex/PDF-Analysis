"""Durable commands and serial worker edges on the sealed PostgreSQL tables."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.queue.handler import ComparisonLaunchHandler
from auditmanager.comparison.queue.service import ComparisonLaunchQueueService
from auditmanager.comparison.work.model import WorkDependencies, Yielded
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.ingest.public import CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonMatrixId, ComparisonSeriesId, DocumentUid, IdempotencyKey, ProjectUid
from tests.support.accounts import SUITE_DISPLAY_LABEL, complete_expert_account
from auditmanager.workers.public import WorkerRegistry

EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})


@dataclass
class Scene:
    sessions: sessionmaker[Session]
    project: str
    document: str
    user: str
    worker: str
    service: ComparisonLaunchQueueService
    work: ComparisonWorkRepository

    def enqueue(self, steps: list[str], key: str = "queue-enqueue", *, consent: str | None = None) -> dict:
        items = [{"document_uid": self.document, "step": step,
                  **({"consent": {"estimate_digest": consent, "confirmed": True}} if consent and step.startswith("ai_") else {})}
                 for step in steps]
        return self.service.enqueue(project_uid=self.project, items=items, restart=False,
                                    user_uid=self.user, actor_label=SUITE_DISPLAY_LABEL, actor_roles=EXPERT,
                                    idempotency_key=key)


@pytest.fixture
def scene(comparison_engine: Engine) -> Iterator[Scene]:
    connection = comparison_engine.connect()
    outer = connection.begin()
    sessions = sessionmaker(bind=connection, expire_on_commit=False, future=True,
                            join_transaction_mode="create_savepoint")
    project, document = str(ProjectUid.new()), str(DocumentUid.new())
    try:
        with session_scope(sessions) as session:
            user = str(complete_expert_account(session, "comparison-launch-queue-test").user_uid)
            worker = WorkerRegistry().register(session, version="cmp-queue-01-test", slots=1)
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Launch queue test')"), {"p": project})
            session.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                                 "VALUES (:d, :p, 'Set')"), {"d": document, "p": project})
        work = ComparisonWorkRepository()
        yield Scene(sessions, project, document, user, worker,
                    ComparisonLaunchQueueService(sessions, comparison_modules="versions", work=work), work)
    finally:
        outer.rollback()
        connection.close()


def test_keyed_commands_replay_and_a_project_queue_is_serial(scene: Scene, monkeypatch: pytest.MonkeyPatch) -> None:
    first = scene.enqueue(["matrix", "profile"])
    assert [row["step"] for row in first["entries"]] == ["profile", "matrix"]
    assert first["counts"] == {"total": 2, "done": 0, "running": 0, "waiting": 2,
                                "needs_consent": 0, "skipped": 0, "failed": 0}
    assert scene.enqueue(["matrix", "profile"]) == first
    with pytest.raises(DomainError) as duplicate:
        scene.enqueue(["profile"], "another-key")
    assert duplicate.value.code is ErrorCode.CONFLICT

    with session_scope(scene.sessions) as session:
        item = scene.work.claim(session, worker_id=scene.worker, modules={"versions"}, kinds={"comparison_launch"})
    assert item is not None
    handler = ComparisonLaunchHandler(WorkDependencies(None, scene.sessions, None, scene.work))  # type: ignore[arg-type]
    monkeypatch.setattr(handler, "_deterministic", lambda _item, _entry: "done")
    assert isinstance(handler.run(item), Yielded)
    after_one = scene.service.get_queue(project_uid=scene.project)
    assert after_one["counts"]["done"] == 1 and after_one["counts"]["waiting"] == 1
    assert isinstance(handler.run(item), Yielded)
    after_two = scene.service.get_queue(project_uid=scene.project)
    assert after_two["state"] == "done" and after_two["counts"]["done"] == 2


def test_moved_consent_waits_and_the_next_entry_can_finish(scene: Scene, monkeypatch: pytest.MonkeyPatch) -> None:
    queued = scene.enqueue(["ai_pairs", "profile"], "consent-key", consent="a" * 64)
    with session_scope(scene.sessions) as session:
        item = scene.work.claim(session, worker_id=scene.worker, modules={"versions"}, kinds={"comparison_launch"})
    assert item is not None
    handler = ComparisonLaunchHandler(WorkDependencies(None, scene.sessions, None, scene.work))  # type: ignore[arg-type]
    monkeypatch.setattr(handler, "_estimate", lambda _entry: {"estimate_digest": "b" * 64})
    monkeypatch.setattr(handler, "_deterministic", lambda _item, _entry: "done")
    assert isinstance(handler.run(item), Yielded)
    assert scene.service.get_queue(project_uid=scene.project)["counts"]["done"] == 1
    assert isinstance(handler.run(item), Yielded)
    after = scene.service.get_queue(project_uid=scene.project)
    assert after["entries"][1]["state"] == "needs_consent"  # profile is first by step order
    assert after["entries"][1]["entry_id"] == queued["entries"][1]["entry_id"]
    assert after["counts"]["done"] == 1 and after["counts"]["needs_consent"] == 1


def test_series_ai_entries_keep_the_series_used_for_consent(scene: Scene, monkeypatch: pytest.MonkeyPatch) -> None:
    matrix_id, series_id = str(ComparisonMatrixId.new()), str(ComparisonSeriesId.new())
    with session_scope(scene.sessions) as session:
        claim = CommandRepository().begin(
            session, command_type="queue_test_series", idempotency_key=IdempotencyKey("queue-test-series"),
            fingerprint=payload_fingerprint({"series_id": series_id}),
        )
        session.execute(text(
            "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, "
            "profile_signature, rules_version, algo_version, rows) "
            "VALUES (:matrix, :project, :document, 1, :digest, 'test', 'test', '[]'::jsonb)"
        ), {"matrix": matrix_id, "project": scene.project, "document": scene.document, "digest": "a" * 64})
        session.execute(text(
            "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, "
            "comparison_matrix_id, matrix_edit_no, input_sha256, actor_user_uid, actor_label, command_id) "
            "VALUES (:series, :project, :document, :matrix, 0, :digest, :actor, :label, :command)"
        ), {"series": series_id, "project": scene.project, "document": scene.document,
            "matrix": matrix_id, "digest": "b" * 64, "actor": scene.user,
            "label": SUITE_DISPLAY_LABEL, "command": str(claim.command_id)})
    scene.enqueue(["ai_changes", "report"], "series-ai-consent")
    with session_scope(scene.sessions) as session:
        item = scene.work.claim(session, worker_id=scene.worker, modules={"versions"}, kinds={"comparison_launch"})
    assert item is not None
    handler = ComparisonLaunchHandler(WorkDependencies(None, scene.sessions, None, scene.work))  # type: ignore[arg-type]
    monkeypatch.setattr(handler, "_latest_series", lambda _entry: series_id)

    def estimate(entry):
        assert entry["comparison_series_id"] == series_id
        return {"estimate_digest": "c" * 64}

    monkeypatch.setattr(handler, "_estimate", estimate)
    assert isinstance(handler.run(item), Yielded)
    assert isinstance(handler.run(item), Yielded)
    entries = scene.service.get_queue(project_uid=scene.project)["entries"]
    assert [(entry["step"], entry["state"], entry["series_id"]) for entry in entries] == [
        ("ai_changes", "needs_consent", series_id), ("report", "needs_consent", series_id),
    ]


def test_pause_resume_remove_clear_and_module_gate(scene: Scene) -> None:
    queued = scene.enqueue(["profile", "matrix"])
    service = scene.service
    paused = service.pause_queue(project_uid=scene.project, user_uid=scene.user, actor_roles=EXPERT,
                                 idempotency_key="pause-key")
    assert paused["state"] == "paused"
    assert service.pause_queue(project_uid=scene.project, user_uid=scene.user, actor_roles=EXPERT,
                               idempotency_key="pause-key") == paused
    removed = service.remove_entry(entry_id=queued["entries"][1]["entry_id"], user_uid=scene.user,
                                   actor_roles=EXPERT, idempotency_key="remove-key")
    assert removed["counts"]["total"] == 1
    resumed = service.resume_queue(project_uid=scene.project, user_uid=scene.user, actor_roles=EXPERT,
                                   idempotency_key="resume-key")
    assert resumed["state"] == "running"
    cleared = service.clear_queue(project_uid=scene.project, user_uid=scene.user, actor_roles=EXPERT,
                                  idempotency_key="clear-key")
    assert cleared["state"] == "idle" and cleared["counts"]["total"] == 0
    with pytest.raises(DomainError) as denied:
        service.enqueue(
            project_uid=scene.project, items=[{"document_uid": scene.document, "step": "profile"}], restart=False,
            user_uid=scene.user, actor_label=SUITE_DISPLAY_LABEL, actor_roles=ADMIN, idempotency_key="admin-key")
    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    off = ComparisonLaunchQueueService(scene.sessions, comparison_modules="none")
    with pytest.raises(DomainError) as unavailable:
        off.get_queue(project_uid=scene.project)
    assert unavailable.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_a_step_without_any_published_version_is_skipped(scene: Scene, monkeypatch: pytest.MonkeyPatch) -> None:
    scene.enqueue(["profile"])
    with session_scope(scene.sessions) as session:
        item = scene.work.claim(session, worker_id=scene.worker, modules={"versions"}, kinds={"comparison_launch"})
    assert item is not None
    handler = ComparisonLaunchHandler(WorkDependencies(None, scene.sessions, None, scene.work))  # type: ignore[arg-type]
    # The overview owns its read-only transaction and cannot change isolation inside this fixture's outer savepoint.
    monkeypatch.setattr(handler, "_overview_state", lambda _entry: "not_applicable")
    assert isinstance(handler.run(item), Yielded)
    queue = scene.service.get_queue(project_uid=scene.project)
    assert queue["state"] == "done" and queue["counts"]["skipped"] == 1
