"""Withdraw and restore a case: the two status events the product may write (`DECISION-MEMORY-01` sections 3.7 and 7.3).

Append-only: a change of standing is a new ``decision_memory_status_event`` row, never an edit; the current standing is the latest event
(:mod:`auditmanager.decision_memory.status` is the rule). The caller owns the transaction and has already decided who may call (the API
layer: ``admin``) and, for a keyed operation, has claimed the command (the composition root's adapter) and passes ``command_id``.

The rule is checked here first, so the caller gets the typed refusal -- ``state_transition_not_allowed`` or ``conflict`` for a forgotten
case -- and **again by the database**: ``am_guard_decision_memory_status`` repeats it on INSERT under the same advisory lock, so a second
writer that raced past this check is refused with ``AM003`` instead of recording a standing the rule forbids. The lock key here is the
trigger's, character for character (:data:`STATUS_LOCK_PREFIX`); a test pins that.

**Forget is not here.** A forget removes content and objects, so it is the operator's tool (``scripts/recovery/memory_forget.py``,
`DECISION-MEMORY-01` section 4.5), not a product operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.decision_memory.status import (
    KIND_RESTORE,
    KIND_WITHDRAW,
    check_reason,
    next_status,
    status_after_events,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionMemoryCaseId, DecisionMemoryStatusEventId, IdentityError

#: The advisory-lock key prefix of ``am_guard_decision_memory_status`` (migration ``0061``). One writer per case at a time.
STATUS_LOCK_PREFIX: Final[str] = "decision_memory_status:"
AGGREGATE_TYPE: Final[str] = "DecisionMemoryCase"

_LOCK = text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))")
_CASE_EXISTS = text("SELECT 1 FROM decision_memory_case WHERE case_id = :case_id")
_LAST_EVENT = text(
    "SELECT kind FROM decision_memory_status_event WHERE case_id = :case_id "
    "ORDER BY created_at DESC, status_event_id DESC LIMIT 1"
)
_INSERT = text(
    "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, command_id) "
    "VALUES (:status_event_id, :case_id, :kind, :reason_code, :actor_user_uid, :command_id) RETURNING created_at"
)


@dataclass(frozen=True, slots=True)
class StatusChange:
    """What a withdraw or a restore did."""

    case_id: str
    status_event_id: str
    kind: str
    status: str
    reason_code: str
    changed_at: datetime


def withdraw_case(
    session: Session, *, case_id: str, actor_user_uid: str, reason_code: str, command_id: str | None = None
) -> StatusChange:
    """Take a case out of hints, prompts and exports. ``state_transition_not_allowed`` when it is already withdrawn."""
    return _change(session, KIND_WITHDRAW, case_id, actor_user_uid, reason_code, command_id)


def restore_case(
    session: Session, *, case_id: str, actor_user_uid: str, reason_code: str, command_id: str | None = None
) -> StatusChange:
    """Undo a withdraw. ``state_transition_not_allowed`` when the case is not withdrawn."""
    return _change(session, KIND_RESTORE, case_id, actor_user_uid, reason_code, command_id)


def _change(
    session: Session, kind: str, case_id: str, actor_user_uid: str, reason_code: str, command_id: str | None
) -> StatusChange:
    check_reason(reason_code)
    try:
        DecisionMemoryCaseId.parse(case_id)
    except IdentityError:
        # a malformed identity is a validation error before any query
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="case_id", constraint="format") from None
    session.execute(_LOCK, {"key": STATUS_LOCK_PREFIX + case_id})
    if session.execute(_CASE_EXISTS, {"case_id": case_id}).first() is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_TYPE)
    current = status_after_events(session.execute(_LAST_EVENT, {"case_id": case_id}).scalar_one_or_none())
    after = next_status(current, kind)
    event_id = DecisionMemoryStatusEventId.new().value
    changed_at = session.execute(
        _INSERT,
        {
            "status_event_id": event_id, "case_id": case_id, "kind": kind, "reason_code": reason_code,
            "actor_user_uid": actor_user_uid, "command_id": command_id,
        },
    ).scalar_one()
    return StatusChange(
        case_id=case_id, status_event_id=event_id, kind=kind, status=after, reason_code=reason_code, changed_at=changed_at
    )
