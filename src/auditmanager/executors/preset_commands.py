"""The administrator's commands on analysis presets, and what a run start asks of them.

Each write: (1) the role check, (2) the name rule, (3) ``CommandRepository.begin`` with an idempotency
key and a payload fingerprint, (4) the family's advisory lock, (5) the preconditions, each with a typed
refusal, (6) the append-only row, (7) the audit event with the revision's id, in the same transaction,
(8) ``ledger.succeed`` with the identities of what was made. A replay answers the revision that command
wrote. The caller owns the transaction. Any refusal ends the transaction before the key is claimed for
good, so a refused request leaves nothing behind -- not even the Idempotency-Key.

``choose_preset`` is the read a run start applies. It takes the preset's **current** revision in the
start's own transaction (the administrator's latest word -- the same "today's configuration" rule as
the executor, ``R-82``) and refuses a preset that does not exist or is archived. It returns the one
setting a start can take; the freezer then does exactly what it does for an executor the caller named.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from auditmanager.executors.preset_audit import (
    record_preset_archived,
    record_preset_created,
    record_preset_revised,
)
from auditmanager.executors.preset_store import PresetStore
from auditmanager.executors.presets import (
    MAX_PRESETS,
    ChosenPreset,
    PresetRecord,
    RunPresetRecord,
    clean_name,
    name_key,
    not_found,
    preset_archived,
    preset_conflict,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey

__all__ = [
    "archive_preset",
    "choose_preset",
    "create_preset",
    "list_presets",
    "preset_of_revision",
    "revise_preset",
]

_CREATE = "create_analysis_preset"
_REVISE = "revise_analysis_preset"
_ARCHIVE = "archive_analysis_preset"


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _begin(
    session: Session, ledger: CommandRepository, command_type: str, idempotency_key: str,
    payload: dict[str, object],
) -> CommandStarted | CommandReplay:
    return ledger.begin(
        session, command_type=command_type, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(payload),
    )


def _replayed(session: Session, store: PresetStore, claimed: CommandReplay) -> PresetRecord:
    found = store.revision(session, str(claimed.outcome["revision_id"]))
    if found is None:
        raise not_found()
    return found


def _require_connection(
    session: Session, repository: ExecutorRepository, connection_id: str
) -> None:
    """The connection exists and is not archived. Its row is locked until the transaction ends,
    so it cannot be archived between this check and the INSERT."""
    if not isinstance(connection_id, str):
        raise _unknown_connection()
    connection = repository.get_connection(session, connection_id, lock=True)
    if connection is None:
        raise _unknown_connection()
    if connection.archived_at is not None:
        raise DomainError(
            ErrorCode.CONFLICT, message="the connection is not in a state that allows this",
            conflict_reason="connection_archived",
        )


def _unknown_connection() -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message="the executor connection is not known",
        field="executor_connection_id", constraint="unknown_connection",
    )


def _refuse_taken_name(
    session: Session, store: PresetStore, *, name: str, own_preset_id: str | None
) -> None:
    key = name_key(name)
    for other in store.list_current(session):
        if other.preset_id == own_preset_id or other.state != "active":
            continue
        if name_key(other.name) == key:
            raise preset_conflict("preset_name_in_use")


def create_preset(
    session: Session, *, name: str, executor_connection_id: str, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, correlation_id: str | None = None,
    store: PresetStore | None = None, executors: ExecutorRepository | None = None,
    commands: CommandRepository | None = None,
) -> PresetRecord:
    _admin(roles)
    clean = clean_name(name)
    presets, connections, ledger = (
        store or PresetStore(), executors or ExecutorRepository(), commands or CommandRepository()
    )
    claimed = _begin(session, ledger, _CREATE, idempotency_key,
                     {"name": clean, "executor_connection_id": executor_connection_id})
    if isinstance(claimed, CommandReplay):
        return _replayed(session, presets, claimed)
    presets.lock(session)
    _require_connection(session, connections, executor_connection_id)
    if presets.count_presets(session) >= MAX_PRESETS:
        raise preset_conflict("preset_limit_reached")
    _refuse_taken_name(session, presets, name=clean, own_preset_id=None)
    revision_id = str(AuditEventId.new())
    record = presets.insert_revision(
        session, revision_id=revision_id, preset_id=revision_id, revision_no=1, state="active",
        name=clean, executor_connection_id=executor_connection_id, actor_uid=actor_uid,
    )
    record_preset_created(
        session, preset_id=record.preset_id, revision_id=record.revision_id,
        revision_no=record.revision_no, executor_connection_id=record.executor_connection_id,
        actor_uid=actor_uid, correlation_id=correlation_id,
    )
    ledger.succeed(session, claimed.command_id, {
        "preset_id": record.preset_id, "revision_id": record.revision_id})
    return record


def revise_preset(
    session: Session, *, preset_id: str, name: str, executor_connection_id: str,
    roles: Iterable[str], idempotency_key: str, actor_uid: str,
    correlation_id: str | None = None, store: PresetStore | None = None,
    executors: ExecutorRepository | None = None, commands: CommandRepository | None = None,
) -> PresetRecord:
    """Append a revision with the full settings, never a patch."""
    _admin(roles)
    clean = clean_name(name)
    presets, connections, ledger = (
        store or PresetStore(), executors or ExecutorRepository(), commands or CommandRepository()
    )
    claimed = _begin(session, ledger, _REVISE, idempotency_key, {
        "preset_id": preset_id, "name": clean, "executor_connection_id": executor_connection_id})
    if isinstance(claimed, CommandReplay):
        return _replayed(session, presets, claimed)
    presets.lock(session)
    current = presets.current(session, preset_id)
    if current is None:
        raise not_found()
    if current.state == "archived":
        raise preset_archived()
    if current.name == clean and current.executor_connection_id == executor_connection_id:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the revision would change nothing",
            field="name", constraint="differs_from_current",
        )
    _require_connection(session, connections, executor_connection_id)
    _refuse_taken_name(session, presets, name=clean, own_preset_id=preset_id)
    record = presets.insert_revision(
        session, revision_id=str(AuditEventId.new()), preset_id=preset_id,
        revision_no=current.revision_no + 1, state="active", name=clean,
        executor_connection_id=executor_connection_id, actor_uid=actor_uid,
    )
    record_preset_revised(
        session, preset_id=record.preset_id, revision_id=record.revision_id,
        revision_no=record.revision_no, executor_connection_id=record.executor_connection_id,
        actor_uid=actor_uid, correlation_id=correlation_id,
    )
    ledger.succeed(session, claimed.command_id, {
        "preset_id": record.preset_id, "revision_id": record.revision_id})
    return record


def archive_preset(
    session: Session, *, preset_id: str, roles: Iterable[str], idempotency_key: str,
    actor_uid: str, correlation_id: str | None = None, store: PresetStore | None = None,
    commands: CommandRepository | None = None,
) -> PresetRecord:
    """Append the archived revision. It repeats the previous name and connection; one-way."""
    _admin(roles)
    presets, ledger = store or PresetStore(), commands or CommandRepository()
    claimed = _begin(session, ledger, _ARCHIVE, idempotency_key, {"preset_id": preset_id})
    if isinstance(claimed, CommandReplay):
        return _replayed(session, presets, claimed)
    presets.lock(session)
    current = presets.current(session, preset_id)
    if current is None:
        raise not_found()
    if current.state == "archived":
        raise preset_archived()
    record = presets.insert_revision(
        session, revision_id=str(AuditEventId.new()), preset_id=preset_id,
        revision_no=current.revision_no + 1, state="archived", name=current.name,
        executor_connection_id=current.executor_connection_id, actor_uid=actor_uid,
    )
    record_preset_archived(
        session, preset_id=record.preset_id, revision_id=record.revision_id,
        revision_no=record.revision_no, executor_connection_id=record.executor_connection_id,
        actor_uid=actor_uid, correlation_id=correlation_id,
    )
    ledger.succeed(session, claimed.command_id, {
        "preset_id": record.preset_id, "revision_id": record.revision_id})
    return record


def list_presets(session: Session, store: PresetStore | None = None) -> list[PresetRecord]:
    """Every preset by its current revision: active first by name, then archived."""
    return (store or PresetStore()).list_current(session)


def choose_preset(
    session: Session, preset_id: str, store: PresetStore | None = None
) -> ChosenPreset:
    """The preset a run start applies, or the refusal that stops the start before anything is written.

    An unknown preset is ``validation_failed`` on ``preset_id`` (``unknown_preset``, the analogue of
    the executor's ``unknown_connection``); an archived one is ``conflict`` (``preset_archived``).
    """
    current = (store or PresetStore()).current(session, preset_id)
    if current is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the analysis preset is not known",
            field="preset_id", constraint="unknown_preset",
        )
    if current.state == "archived":
        raise preset_archived()
    return ChosenPreset(
        preset_id=current.preset_id, revision_id=current.revision_id,
        revision_no=current.revision_no, executor_connection_id=current.executor_connection_id,
    )


def preset_of_revision(
    session: Session, revision_id: str, store: PresetStore | None = None
) -> RunPresetRecord | None:
    """The preset revision a run recorded, as it was named then; ``None`` for no such revision."""
    return (store or PresetStore()).run_preset(session, revision_id)
