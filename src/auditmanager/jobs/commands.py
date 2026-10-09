"""Administrator commands for the durable queue and dispatch switch."""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.ingest.public import (
    CommandReplay, CommandRepository, CommandStarted, payload_fingerprint,
)
from auditmanager.jobs.repository import JobRepository
from auditmanager.jobs.events import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey


def _require_admin(roles: frozenset[str]) -> None:
    if "admin" not in roles:
        raise DomainError(ErrorCode.PERMISSION_DENIED)


def set_job_priority(
    session: Session, *, job_id: str, priority: int, roles: frozenset[str],
    idempotency_key: str, jobs: JobRepository | None = None,
    commands: CommandRepository | None = None,
) -> None:
    _require_admin(roles)
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type="set_job_priority", idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"job_id": job_id, "priority": priority}),
    )
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    (jobs or JobRepository()).set_priority(session, job_id=job_id, priority=priority)
    ledger.succeed(session, claimed.command_id, {"job_id": job_id})


def set_execution_paused(
    session: Session, *, paused: bool, roles: frozenset[str], idempotency_key: str,
    actor_uid: str,
    jobs: JobRepository | None = None, commands: CommandRepository | None = None,
) -> None:
    _require_admin(roles)
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type="set_execution_paused",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"paused": paused}),
    )
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    (jobs or JobRepository()).set_paused(session, paused=paused)
    append_execution_event(
        session, event_type="execution.dispatch_paused_changed",
        aggregate_type="CommandRecord", aggregate_id=str(claimed.command_id),
        payload={"paused": paused, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"paused": paused})
