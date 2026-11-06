"""The designer's execution status of an accepted finding (`UI-PARITY-P0I`, ruling `R-151g`, migration 0054).

The original shows «Принято · Учтено / Внесено / Отклонено / По согл.» from the SU-10 registry. Ours is entered by hand:
``taken_into_account`` (Учтено), ``amended`` (Внесено), ``declined`` (Отклонено), ``agreed`` (По согласованию). As in the
original, it belongs to a finding the expert accepted; setting it on any other finding is refused, clearing it never is.

It is not an expert decision: it never touches the verdict, the decision journal or a counter. A keyed command; every
change appends ``finding.execution_status_set`` to the audit trail, and the same status again records nothing.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.ingest.public import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey

EXECUTION_STATUSES = ("taken_into_account", "amended", "declined", "agreed")

_VERDICT = text("SELECT current_verdict FROM finding_current_verdict WHERE finding_uid = :finding_uid")
_CURRENT = text("SELECT status FROM finding_execution_status WHERE finding_uid = :finding_uid FOR UPDATE")
_UPSERT = text(
    "INSERT INTO finding_execution_status (finding_uid, status, set_by_user_uid) VALUES (:finding_uid, :status, :actor) "
    "ON CONFLICT (finding_uid) DO UPDATE SET status = EXCLUDED.status, set_by_user_uid = EXCLUDED.set_by_user_uid, "
    "set_at = now()"
)
_CLEAR = text("DELETE FROM finding_execution_status WHERE finding_uid = :finding_uid")
_EVENT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
    "VALUES (:event_id, 'finding.execution_status_set', 'Finding', :finding_uid, CAST(:payload AS jsonb))"
)
_READ = text(
    "SELECT finding_uid, status, set_at FROM finding_execution_status WHERE finding_uid = ANY(:finding_uids)"
)


def execution_statuses(session: Session, finding_uids: Iterable[str]) -> dict[str, tuple[str, datetime]]:
    """``{finding_uid: (status, set_at)}`` of the findings that have one."""
    uids = list(finding_uids)
    if not uids:
        return {}
    return {str(row[0]): (str(row[1]), row[2]) for row in session.execute(_READ, {"finding_uids": uids}).all()}


def set_execution_status(
    session: Session, *, finding_uid: str, status: str | None, actor_uid: str, idempotency_key: str,
    commands: CommandRepository | None = None,
) -> None:
    """Set (or, with ``None``, clear) the execution status of one finding."""
    if status is not None and status not in EXECUTION_STATUSES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="status", constraint="enum")
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type="set_finding_execution_status", idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"finding_uid": finding_uid, "status": status}),
    )
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    verdict = session.execute(_VERDICT, {"finding_uid": finding_uid}).scalar_one_or_none()
    if verdict is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Finding")
    if status is not None and verdict != "accepted":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="status", constraint="finding_not_accepted",
            message="an execution status belongs to a finding the expert accepted",
        )
    current = session.execute(_CURRENT, {"finding_uid": finding_uid}).scalar_one_or_none()
    if current != status:
        if status is None:
            session.execute(_CLEAR, {"finding_uid": finding_uid})
        else:
            session.execute(_UPSERT, {"finding_uid": finding_uid, "status": status, "actor": actor_uid})
        session.execute(_EVENT, {
            "event_id": str(AuditEventId.new()),
            "finding_uid": finding_uid,
            "payload": json.dumps({"actor_uid": actor_uid, "from": current, "to": status}, sort_keys=True),
        })
    ledger.succeed(session, claimed.command_id, {"finding_uid": finding_uid, "status": status})
