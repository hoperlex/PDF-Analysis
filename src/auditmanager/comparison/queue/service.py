"""Keyed, expert-owned commands of the per-project launch queue."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.modules import MODULE_VERSIONS, enabled_modules, parse_modules
from auditmanager.comparison.queue.model import ACTIVE, AI_STEPS, LAUNCH_KIND, STEP_ORDER, STEPS, queue_view
from auditmanager.comparison.queue.repository import LaunchQueueRepository
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey, ProjectUid


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


class ComparisonLaunchQueueService:
    """The API's queue commands. The worker's step execution is in :mod:`.handler`."""

    def __init__(
        self, session_factory: sessionmaker[Session], *, comparison_modules: str = "none", provider_mode: str = "live",
        repository: LaunchQueueRepository | None = None, work: ComparisonWorkRepository | None = None,
        commands: CommandRepository | None = None,
    ) -> None:
        self._factory = session_factory
        self._modules = parse_modules(comparison_modules)
        self._provider_mode = provider_mode
        self._repo = repository or LaunchQueueRepository()
        self._work = work or ComparisonWorkRepository()
        self._commands = commands or CommandRepository()
        self._documents = DocumentRepository()
        self._accounts = AccountRepository()

    def _require_module(self) -> None:
        if MODULE_VERSIONS not in enabled_modules(self._modules):
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_modules")

    def _require_project(self, session: Session, project_uid: str) -> None:
        self._documents.get_project(session, ProjectUid.parse(project_uid))

    def _require_document(self, session: Session, project_uid: str, document_uid: str) -> None:
        if str(self._documents.require_document(session, DocumentUid.parse(document_uid))) != project_uid:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")

    def _require_expert(self, session: Session, user_uid: str, actor_roles: frozenset[str]) -> None:
        if "expert" not in actor_roles or "expert" not in self._accounts.roles_of(session, user_uid):
            raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")

    def _view(self, session: Session, project_uid: str) -> dict[str, Any]:
        return queue_view(project_uid, self._repo.queue(session, project_uid), self._repo.entries(session, project_uid))

    def _start_work(self, session: Session, project_uid: str, user_uid: str) -> None:
        self._work.enqueue(
            session, project_uid=project_uid, module=MODULE_VERSIONS, kind=LAUNCH_KIND,
            payload={"project_uid": project_uid}, dedupe_key=f"{LAUNCH_KIND}:{project_uid}",
            created_by_user_uid=user_uid, max_attempts=10,
        )

    def get_queue(self, *, project_uid: str) -> dict[str, Any]:
        self._require_module()
        with session_scope(self._factory) as session:
            self._require_project(session, project_uid)
            return self._view(session, project_uid)

    def get_ai_queue(self) -> dict[str, Any]:
        self._require_module()
        return ComparisonAiJobService(
            self._factory, methods=[], comparison_modules=self._modules, provider_mode=self._provider_mode,
        ).waiting().as_dict()

    def enqueue(
        self, *, project_uid: str, items: Sequence[Mapping[str, Any]], restart: bool,
        user_uid: str, actor_label: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_module()
        if not items or len(items) > 200:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="items", constraint="length")
        selected: list[dict[str, Any]] = []
        for item in items:
            step, document = str(item["step"]), str(item["document_uid"])
            if step not in STEPS:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="step", constraint="comparison_step_not_queueable")
            consent = item.get("consent")
            if consent is not None and step not in AI_STEPS:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="consent", constraint="comparison_consent_not_applicable")
            if consent is not None and not consent.get("confirmed"):
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="consent", constraint="comparison_consent_required")
            selected.append({"document_uid": document, "step": step,
                             "consent_digest": None if consent is None else str(consent["estimate_digest"])})
        selected.sort(key=lambda row: (STEP_ORDER[row["step"]], next(
            index for index, item in enumerate(items) if str(item["document_uid"]) == row["document_uid"]
            and str(item["step"]) == row["step"])))
        fingerprint = payload_fingerprint({"command": "enqueue_comparison_launch.v1", "project_uid": project_uid,
                                           "items": selected, "restart": restart})
        with session_scope(self._factory) as session:
            self._require_expert(session, user_uid, actor_roles)
            self._require_project(session, project_uid)
            for row in selected:
                self._require_document(session, project_uid, row["document_uid"])
            claim = self._commands.begin(session, command_type="enqueue_comparison_launch",
                                         idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint)
            if isinstance(claim, CommandReplay):
                return dict(claim.outcome["queue"])
            queue = self._repo.ensure_queue(session, project_uid)
            current_entries = self._repo.entries(session, project_uid, lock=True)
            if len(current_entries) + len(selected) > 500:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="items", constraint="length")
            existing = {(row["document_uid"], row["step"]) for row in current_entries
                        if row["state"] in ACTIVE}
            requested = [(row["document_uid"], row["step"]) for row in selected]
            if len(set(requested)) != len(requested) or any(pair in existing for pair in requested):
                raise _conflict("comparison_launch_entry_active")
            self._repo.insert_entries(session, project_uid=project_uid, selected=selected, restart=restart,
                                      actor_user_uid=user_uid, actor_label=actor_label, command_id=str(claim.command_id))
            if not queue["paused"] and queue["failure_reason"] is None:
                self._start_work(session, project_uid, user_uid)
            view = self._view(session, project_uid)
            self._commands.succeed(session, claim.command_id, {"queue": _jsonable(view)})
            return _jsonable(view)

    def _change(self, *, project_uid: str, command_type: str, user_uid: str, actor_roles: frozenset[str],
                idempotency_key: str) -> dict[str, Any]:
        self._require_module()
        with session_scope(self._factory) as session:
            self._require_expert(session, user_uid, actor_roles)
            self._require_project(session, project_uid)
            claim = self._commands.begin(
                session, command_type=command_type, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=payload_fingerprint({"command": command_type + ".v1", "project_uid": project_uid}),
            )
            if isinstance(claim, CommandReplay):
                return dict(claim.outcome["queue"])
            queue = self._repo.ensure_queue(session, project_uid)
            view = self._view(session, project_uid)
            if command_type == "pause_comparison_launch_queue":
                if view["state"] != "running":
                    raise _conflict("comparison_launch_queue_state")
                self._repo.set_queue(session, project_uid, paused=True)
            elif command_type == "resume_comparison_launch_queue":
                if view["state"] not in ("paused", "failed"):
                    raise _conflict("comparison_launch_queue_state")
                self._repo.set_queue(session, project_uid, paused=False)
                for entry in self._repo.entries(session, project_uid, lock=True):
                    if entry["state"] == "failed":
                        self._repo.move(session, entry["comparison_launch_entry_id"], from_state="failed", to_state="waiting")
                        break
                self._start_work(session, project_uid, user_uid)
            elif command_type == "clear_comparison_launch_queue":
                self._repo.delete_not_running(session, project_uid)
                if not any(row["state"] == "running" for row in self._repo.entries(session, project_uid)):
                    self._repo.set_queue(session, project_uid, paused=False)
            else:
                raise AssertionError(command_type)
            result = self._view(session, project_uid)
            self._commands.succeed(session, claim.command_id, {"queue": _jsonable(result)})
            return _jsonable(result)

    def pause_queue(self, *, project_uid: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        return self._change(project_uid=project_uid, command_type="pause_comparison_launch_queue",
                            user_uid=user_uid, actor_roles=actor_roles, idempotency_key=idempotency_key)

    def resume_queue(self, *, project_uid: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        return self._change(project_uid=project_uid, command_type="resume_comparison_launch_queue",
                            user_uid=user_uid, actor_roles=actor_roles, idempotency_key=idempotency_key)

    def clear_queue(self, *, project_uid: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        return self._change(project_uid=project_uid, command_type="clear_comparison_launch_queue",
                            user_uid=user_uid, actor_roles=actor_roles, idempotency_key=idempotency_key)

    def remove_entry(self, *, entry_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        self._require_module()
        with session_scope(self._factory) as session:
            self._require_expert(session, user_uid, actor_roles)
            claim = self._commands.begin(
                session, command_type="remove_comparison_launch_entry", idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=payload_fingerprint({"command": "remove_comparison_launch_entry.v1", "entry_id": entry_id}),
            )
            if isinstance(claim, CommandReplay):
                return dict(claim.outcome["queue"])
            entry = self._repo.entry(session, entry_id, lock=True)
            if entry is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonLaunchEntry")
            project_uid = str(entry["project_uid"])
            self._repo.ensure_queue(session, project_uid)
            if not self._repo.delete_entry(session, entry_id, states=("waiting", "needs_consent")):
                raise _conflict("comparison_launch_entry_state")
            result = self._view(session, project_uid)
            self._commands.succeed(session, claim.command_id, {"queue": _jsonable(result)})
            return _jsonable(result)
