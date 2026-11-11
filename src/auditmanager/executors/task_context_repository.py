"""The only reader and writer of ``executor_task_context_delivery`` (migration ``0064``, `CTX-STAND`).

Statements only: the rules live in ``task_context.py``. The table is the stand's record of what it handed an agent as reference data: the task,
the run and the model call (opaque identities, **no foreign key**), the kind, the status, the cases by identity, the number of characters and the
digest of the block. It holds **no text** and outlives the erase of the project it was handed for (KEEP). A row is immutable (``am_immutable_row``)
and ``(task_id, kind)`` is unique, so the one request a kind is paid for is written once and a repeat finds it.

The application role may only ``SELECT`` and ``INSERT`` here (``infra/deploy/apply-grants.sh``); nothing below updates or deletes a row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import ExecutorTaskContextDeliveryId

__all__ = ["ContextDeliveryRepository", "DeliveryRecord"]

_COLUMNS: Final = (
    "delivery_id, task_id, run_id, model_call_id, kind, status, reason, case_ids, characters, block_sha256, delivered_at"
)


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    """One row of the journal. ``reason`` is set exactly when ``status`` is ``unavailable`` and ``block_sha256`` exactly when it is ``delivered``
    (the database's CHECKs say the same)."""

    delivery_id: str
    task_id: str
    run_id: str
    model_call_id: str | None
    kind: str
    status: str
    reason: str | None
    case_ids: tuple[str, ...]
    characters: int
    block_sha256: str | None
    delivered_at: datetime


def _record(row: Mapping[str, Any]) -> DeliveryRecord:
    return DeliveryRecord(
        delivery_id=row["delivery_id"], task_id=row["task_id"], run_id=row["run_id"], model_call_id=row["model_call_id"],
        kind=row["kind"], status=row["status"], reason=row["reason"], case_ids=tuple(row["case_ids"] or ()),
        characters=row["characters"], block_sha256=row["block_sha256"], delivered_at=row["delivered_at"])


class ContextDeliveryRepository:
    """Stateless; every method takes the caller's session and never commits."""

    def get(self, session: Session, task_id: str, kind: str) -> DeliveryRecord | None:
        row = session.execute(text(
            f"SELECT {_COLUMNS} FROM executor_task_context_delivery WHERE task_id = :task AND kind = :kind"
        ), {"task": task_id, "kind": kind}).mappings().first()
        return None if row is None else _record(row)

    def insert(
        self, session: Session, *, task_id: str, run_id: str, model_call_id: str | None, kind: str, status: str,
        reason: str | None, case_ids: Sequence[str], characters: int, block_sha256: str | None,
    ) -> DeliveryRecord:
        """Write the one row of ``(task_id, kind)``; when it already exists, the existing row, unchanged (the table is immutable and a request is
        paid for once)."""
        row = session.execute(text(
            "INSERT INTO executor_task_context_delivery (delivery_id, task_id, run_id, model_call_id, kind, status, reason, case_ids, "
            "characters, block_sha256) VALUES (:id, :task, :run, :call, :kind, :status, :reason, CAST(:cases AS text[]), :characters, :block) "
            f"ON CONFLICT (task_id, kind) DO NOTHING RETURNING {_COLUMNS}"
        ), {"id": str(ExecutorTaskContextDeliveryId.new()), "task": task_id, "run": run_id, "call": model_call_id, "kind": kind,
            "status": status, "reason": reason, "cases": list(case_ids), "characters": characters, "block": block_sha256}).mappings().first()
        if row is not None:
            return _record(row)
        found = self.get(session, task_id, kind)
        assert found is not None, "a conflict on (task_id, kind) names a row that exists"
        return found
