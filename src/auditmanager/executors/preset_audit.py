"""The preset journal: ``executor.preset_*`` events in ``audit_event`` (`ANALYSIS-PRESETS-01`).

An administrator who creates, revises or archives a preset leaves a row in the append-only
``audit_event`` table **in the transaction of the change it describes** -- the idiom of the access
journal (`PROD-06`) and of ``comparison/audit.py``: the writer takes the caller's
:class:`~sqlalchemy.orm.Session` and lets every error propagate, so the change and its event commit or
roll back together. A writer that opened its own connection or swallowed its own failure would let the
change commit without its event.

The event's id **is** the revision's id (``revision_id``): one id, the row and its event. The aggregate
is the preset (``AnalysisPreset``, addressed by its ``preset_id``; not a foreign key, an audit trail
must survive what it describes). What a payload may hold: the preset and revision identities, the
revision number, the connection identity and the actor -- nothing else. **Never the name**: it is
free text an administrator typed, and it is already in the immutable revision row. Three independent
things keep it so, as in the access journal: a per-type allow-list of keys, a value rule per key, and
typed entry points that take arguments rather than a mapping.

The ``executor.`` prefix is a KEEP family of the product purge (``scripts/recovery/product_purge.py``):
a preset is executor configuration, so its history stays with the configuration.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import UserUid
from auditmanager.executors.presets import AGGREGATE_TYPE
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import (
    AuditEventId,
    CorrelationId,
    ExecutorConnectionId,
    IdentityError,
)

EVENT_PRESET_CREATED: Final[str] = "executor.preset_created"
EVENT_PRESET_REVISED: Final[str] = "executor.preset_revised"
EVENT_PRESET_ARCHIVED: Final[str] = "executor.preset_archived"

_KEYS: Final[frozenset[str]] = frozenset({
    "preset_id", "revision_id", "revision_no", "executor_connection_id", "actor_uid",
})
#: ``event_type`` -> (keys that must be present, keys that may be present).
PAYLOAD_KEYS: Final[Mapping[str, tuple[frozenset[str], frozenset[str]]]] = {
    EVENT_PRESET_CREATED: (_KEYS, frozenset()),
    EVENT_PRESET_REVISED: (_KEYS, frozenset()),
    EVENT_PRESET_ARCHIVED: (_KEYS, frozenset()),
}
PRESET_EVENT_TYPES: Final[tuple[str, ...]] = tuple(PAYLOAD_KEYS)

_INSERT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, "
    "correlation_id, payload) VALUES (:event_id, :event_type, :aggregate_type, "
    ":aggregate_id, :correlation_id, CAST(:payload AS jsonb))"
)

_IDENTITY_KEYS: Final[Mapping[str, type]] = {
    "preset_id": AuditEventId,
    "revision_id": AuditEventId,
    "executor_connection_id": ExecutorConnectionId,
    "actor_uid": UserUid,
}


def _checked(key: str, value: object) -> object:
    if key in _IDENTITY_KEYS:
        try:
            return str(_IDENTITY_KEYS[key].parse(value))  # type: ignore[attr-defined]
        except (IdentityError, DomainError, TypeError):
            raise ValueError(f"preset journal: {key} is not a valid identity") from None
    if key == "revision_no":
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("preset journal: revision_no must be a positive integer")
        return value
    raise ValueError(f"preset journal: no value rule for {key!r}")  # pragma: no cover


def validated(event_type: str, payload: Mapping[str, object]) -> dict[str, object]:
    """The payload as it will be stored, or a ``ValueError`` naming what is wrong."""
    required, optional = PAYLOAD_KEYS[event_type]
    keys = set(payload)
    if not required <= keys:
        raise ValueError(f"preset journal: {event_type} lacks {sorted(required - keys)}")
    if not keys <= required | optional:
        raise ValueError(
            f"preset journal: {event_type} payload contains a non-allowlisted field "
            f"{sorted(keys - (required | optional))}"
        )
    return {key: _checked(key, value) for key, value in payload.items()}


def _append(
    session: Session, *, event_type: str, payload: Mapping[str, object],
    correlation_id: str | None,
) -> None:
    """INSERT one event on the caller's session. It never commits and never swallows."""
    checked = validated(event_type, payload)
    bound = None if correlation_id is None else str(CorrelationId.parse(correlation_id))
    session.execute(_INSERT, {
        "event_id": checked["revision_id"],
        "event_type": event_type,
        "aggregate_type": AGGREGATE_TYPE,
        "aggregate_id": checked["preset_id"],
        "correlation_id": bound,
        "payload": json.dumps(checked, sort_keys=True),
    })


def _record(
    session: Session, event_type: str, *, preset_id: str, revision_id: str, revision_no: int,
    executor_connection_id: str, actor_uid: str, correlation_id: str | None,
) -> None:
    _append(
        session, event_type=event_type,
        payload={
            "preset_id": preset_id, "revision_id": revision_id, "revision_no": revision_no,
            "executor_connection_id": executor_connection_id, "actor_uid": actor_uid,
        },
        correlation_id=correlation_id,
    )


def record_preset_created(
    session: Session, *, preset_id: str, revision_id: str, revision_no: int,
    executor_connection_id: str, actor_uid: str, correlation_id: str | None,
) -> None:
    _record(session, EVENT_PRESET_CREATED, preset_id=preset_id, revision_id=revision_id,
            revision_no=revision_no, executor_connection_id=executor_connection_id,
            actor_uid=actor_uid, correlation_id=correlation_id)


def record_preset_revised(
    session: Session, *, preset_id: str, revision_id: str, revision_no: int,
    executor_connection_id: str, actor_uid: str, correlation_id: str | None,
) -> None:
    _record(session, EVENT_PRESET_REVISED, preset_id=preset_id, revision_id=revision_id,
            revision_no=revision_no, executor_connection_id=executor_connection_id,
            actor_uid=actor_uid, correlation_id=correlation_id)


def record_preset_archived(
    session: Session, *, preset_id: str, revision_id: str, revision_no: int,
    executor_connection_id: str, actor_uid: str, correlation_id: str | None,
) -> None:
    _record(session, EVENT_PRESET_ARCHIVED, preset_id=preset_id, revision_id=revision_id,
            revision_no=revision_no, executor_connection_id=executor_connection_id,
            actor_uid=actor_uid, correlation_id=correlation_id)


__all__ = [
    "EVENT_PRESET_ARCHIVED", "EVENT_PRESET_CREATED", "EVENT_PRESET_REVISED", "PAYLOAD_KEYS",
    "PRESET_EVENT_TYPES", "record_preset_archived", "record_preset_created",
    "record_preset_revised", "validated",
]
