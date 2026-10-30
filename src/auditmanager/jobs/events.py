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
    # `W54-WORKER-01`: the worker registry's intake switch (R-105).
    "worker_id", "intake_enabled",
    # `EXEC-SEAL-01`: the executor connections' journal. Identities and controlled classifiers
    # only; a setting's value, an address and a secret are never in a payload.
    "connection_id", "connection_kind", "revision_id", "revision_no", "secret_id", "purpose",
    "probe_id", "work_kind", "primary_connection_id", "standby_connection_id",
    # `EXEC-HTTP-01`: why a run started on the standby (``primary_archived``,
    # ``primary_not_probed``, ``primary_kind_not_served``): a controlled classifier.
    "reason",
    # BETA-PDF-PRECHECK-1030: scalar page progress of the existing source stage.
    "completed_pages", "total_pages", "phase",
})
# `EXEC-PULL-01`: a runner token is addressed by its identity, never by its value, its prefix
# or its hash.
_SAFE_KEYS = _SAFE_KEYS | frozenset({"token_id", "task_id"})
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
