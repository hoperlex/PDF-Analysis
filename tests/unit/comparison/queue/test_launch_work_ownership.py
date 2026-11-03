"""Every command that starts the launch queue owns its work item, so none can be absorbed by a dying one."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.queue.model import LAUNCH_KIND, launch_dedupe_key
from auditmanager.comparison.queue.service import ComparisonLaunchQueueService
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.shared.identity import CommandId, DocumentUid, ProjectUid

EXPERT = frozenset({"expert"})
NOW = "2026-11-02T00:00:00+00:00"


class _Session:
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


class _Commands:
    """Starts every new key once and replays a repeated one."""

    def __init__(self) -> None:
        self.started: dict[str, CommandId] = {}
        self.outcomes: dict[str, dict[str, Any]] = {}

    def begin(self, session: Any, *, command_type: str, idempotency_key: Any, fingerprint: Any) -> Any:
        key = (command_type, str(idempotency_key))
        if key in self.outcomes:
            return CommandReplay(self.started[key], self.outcomes[key])
        self.started[key] = CommandId.new()
        return CommandStarted(self.started[key])

    def succeed(self, session: Any, command_id: CommandId, outcome: dict[str, Any]) -> None:
        for key, started in self.started.items():
            if started == command_id:
                self.outcomes[key] = outcome


class _Repository:
    def __init__(self, entries: list[dict[str, Any]]) -> None:
        self.rows = entries

    def queue(self, session: Any, project_uid: str, *, lock: bool = False) -> dict[str, Any]:
        return {"paused": self.paused, "failure_reason": None, "updated_at": NOW}

    paused = False

    def ensure_queue(self, session: Any, project_uid: str) -> dict[str, Any]:
        return self.queue(session, project_uid)

    def entries(self, session: Any, project_uid: str, *, lock: bool = False) -> list[dict[str, Any]]:
        return list(self.rows)

    def insert_entries(self, session: Any, *, selected: Any, **_kw: Any) -> None:
        pass

    def set_queue(self, session: Any, project_uid: str, *, paused: bool, failure_reason: str | None = None) -> None:
        self.paused = paused

    def move(self, session: Any, entry_id: str, **_kw: Any) -> bool:
        return True


class _Work:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, Any]] = []

    def enqueue(self, session: Any, **kwargs: Any) -> None:
        self.enqueued.append(kwargs)


def _service(entries: list[dict[str, Any]] | None = None) -> tuple[ComparisonLaunchQueueService, _Work, _Repository, str, str]:
    project, document = str(ProjectUid.new()), str(DocumentUid.new())
    work, repository = _Work(), _Repository(entries or [])
    service = ComparisonLaunchQueueService(
        lambda: _Session(), comparison_modules="versions",  # type: ignore[arg-type]
        repository=repository, work=work, commands=_Commands(),  # type: ignore[arg-type]
    )
    service._accounts = SimpleNamespace(roles_of=lambda _session, _user: EXPERT)  # type: ignore[assignment]
    service._documents = SimpleNamespace(  # type: ignore[assignment]
        get_project=lambda _session, _project: None,
        require_document=lambda _session, _document: ProjectUid.parse(project),
    )
    return service, work, repository, project, document


@pytest.fixture(autouse=True)
def _plain_session_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def scope(factory: Any) -> Any:
        yield factory()

    monkeypatch.setattr("auditmanager.comparison.queue.service.session_scope", scope)


def _enqueue(service: ComparisonLaunchQueueService, project: str, document: str, step: str, key: str) -> Any:
    return service.enqueue(project_uid=project, items=[{"document_uid": document, "step": step}], restart=False,
                           user_uid="usr_00000000000000000000000001", actor_label="Expert",
                           actor_roles=EXPERT, idempotency_key=key)


def test_the_dedupe_key_carries_project_and_command() -> None:
    command = str(CommandId.new())
    key = launch_dedupe_key("prj_x", command)
    assert key == f"{LAUNCH_KIND}:prj_x:{command}" and len(key) <= 256
    assert launch_dedupe_key("prj_x", str(CommandId.new())) != key


def test_two_enqueues_never_share_a_work_item_key() -> None:
    """The old key was one per project, so the second enqueue joined whatever item was still live."""
    service, work, _repository, project, document = _service()
    _enqueue(service, project, document, "profile", "queue-key-one")
    _enqueue(service, project, document, "matrix", "queue-key-two")
    keys = [call["dedupe_key"] for call in work.enqueued]
    assert len(keys) == 2 and keys[0] != keys[1]
    assert all(key.startswith(f"{LAUNCH_KIND}:{project}:cmd_") for key in keys)
    assert all(call["kind"] == LAUNCH_KIND and call["payload"] == {"project_uid": project} for call in work.enqueued)


def test_a_replayed_enqueue_starts_no_second_item() -> None:
    service, work, _repository, project, document = _service()
    first = _enqueue(service, project, document, "profile", "queue-key-one")
    assert _enqueue(service, project, document, "profile", "queue-key-one") == first
    assert len(work.enqueued) == 1


def _row(state: str) -> dict[str, Any]:
    return {"comparison_launch_entry_id": "cle_00000000000000000000000001", "document_uid": "doc_x",
            "step": "profile", "state": state, "position": 1, "restart": False, "reason": None,
            "comparison_ai_job_id": None, "comparison_series_id": None, "created_at": NOW, "updated_at": NOW}


def test_resume_starts_its_own_item_beside_the_one_of_the_enqueue() -> None:
    """Resume of a paused queue is a start command too: it may follow an item that is finishing."""
    service, work, repository, project, document = _service()
    _enqueue(service, project, document, "profile", "queue-key-one")
    repository.rows, repository.paused = [_row("waiting")], True
    resumed = service.resume_queue(project_uid=project, user_uid="usr_00000000000000000000000001",
                                   actor_roles=EXPERT, idempotency_key="queue-resume-one")
    assert resumed["state"] == "running"
    keys = [call["dedupe_key"] for call in work.enqueued]
    assert len(keys) == 2 and keys[0] != keys[1]
    assert keys[1].startswith(f"{LAUNCH_KIND}:{project}:cmd_")
