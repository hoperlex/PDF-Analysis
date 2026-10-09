"""Append the deliberately small execution journal payload in the caller's transaction.

The audit trail is a shared append-only table; only identity and controlled state
classifiers may enter this projection. Provider text, paths and credentials never do.
"""

from __future__ import annotations

import json
from typing import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import AuditEventId

_SAFE_KEYS = frozenset({
    "run_id", "job_id", "attempt_id", "from_state", "to_state", "state",
    "stage_id", "error_code", "dispatch_class", "priority", "paused", "actor_uid",
})
_INSERT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, "
    "aggregate_id, payload) VALUES (:event_id, :event_type, :aggregate_type, "
    ":aggregate_id, CAST(:payload AS jsonb))"
)


def append_execution_event(
    session: Session, *, event_type: str, aggregate_type: str,
    aggregate_id: str, run_id: str | None = None,
    payload: Mapping[str, str | int | bool | None] = {},
) -> None:
    if not set(payload).issubset(_SAFE_KEYS):
        raise ValueError("execution journal payload contains a non-allowlisted field")
    if any(not isinstance(value, (str, int, bool, type(None))) for value in payload.values()):
        raise ValueError("execution journal payload contains a non-scalar value")
    session.execute(_INSERT, {
        "event_id": str(AuditEventId.new()),
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "payload": json.dumps(
            {**({"run_id": run_id} if run_id is not None else {}), **payload},
            sort_keys=True,
        ),
    })
