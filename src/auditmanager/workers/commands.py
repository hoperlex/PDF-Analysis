"""The administrator's intake switch for one worker (`setWorkerIntake`, R-105, R-80)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.ingest.public import (
    CommandReplay, CommandRepository, CommandStarted, payload_fingerprint,
)
from auditmanager.jobs.public import JobRepository, append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.workers.registry import WorkerRecord, WorkerRegistry


def set_worker_intake(
    session: Session, *, worker_id: str, enabled: bool, roles: frozenset[str],
    idempotency_key: str, actor_uid: str,
    registry: WorkerRegistry | None = None, commands: CommandRepository | None = None,
) -> WorkerRecord:
    """Switch whether one worker claims new runs; runs it already holds are untouched.

    «Не брать новые» is a drain of one worker: its current run finishes under its Lease,
    and the claim (``jobs``) refuses every new one while intake is off. Switching it back
    on wakes the listening workers. Idempotent under the key like the other execution
    controls; a replay answers the worker as it is now.
    """
    if "admin" not in roles:
        raise DomainError(ErrorCode.PERMISSION_DENIED)
    workers = registry or WorkerRegistry()
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type="set_worker_intake",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"worker_id": worker_id, "enabled": enabled}),
    )
    if isinstance(claimed, CommandStarted):
        if not workers.set_intake(session, worker_id=worker_id, enabled=enabled):
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Worker")
        append_execution_event(
            session, event_type="execution.worker_intake_changed",
            aggregate_type="Worker", aggregate_id=worker_id,
            payload={"worker_id": worker_id, "intake_enabled": enabled,
                     "actor_uid": actor_uid},
        )
        if enabled:
            JobRepository.wake_workers(session)
        ledger.succeed(session, claimed.command_id, {"worker_id": worker_id,
                                                     "enabled": enabled})
    else:
        assert isinstance(claimed, CommandReplay)
    record = workers.get(session, worker_id)
    if record is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Worker")
    return record


__all__ = ["set_worker_intake"]
