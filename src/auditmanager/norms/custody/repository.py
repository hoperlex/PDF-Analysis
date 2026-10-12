"""Custody persistence: the only writer of ``norm_custody_admission`` and ``norm_custody_binding``.

Every statement runs in the caller's session and transaction; nothing here commits. The
state guard ``trg_norm_custody_admission_guard`` and the binding guard re-check every move
in the database, so a statement below that disagreed with the declared machine would be
refused there rather than recorded.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import (
    AuditEventId,
    NormCustodyAdmissionId,
    NormCustodyBindingId,
)

from .model import (
    MAX_ATTEMPTS,
    RETRY_DELAYS_SECONDS,
    Admission,
    AdmissionState,
    Binding,
    CustodySlot,
    DeclaredContent,
    RejectedBlob,
)
from .roles import TARGET_TABLES

_ADMISSION_COLUMNS = (
    "norm_custody_admission_id, role, target_kind, target_id, anchor_kind, anchor, blob_id, "
    "declared_size_bytes, declared_sha256, media_type, state, attempt_count, available_at, "
    "last_failure, created_at, confirmed_at"
)
_BINDING_COLUMNS = (
    "norm_custody_binding_id, norm_custody_admission_id, role, target_kind, target_id, "
    "anchor_kind, anchor, blob_id, bound_at"
)
_SLOT_MATCH = (
    "role = :role AND target_kind = :target_kind AND target_id = :target_id "
    "AND anchor_kind = :anchor_kind AND anchor = :anchor"
)

_INSERT_ADMISSION = text(
    f"""
    INSERT INTO norm_custody_admission (
        norm_custody_admission_id, role, target_kind, target_id, anchor_kind, anchor,
        blob_id, declared_size_bytes, declared_sha256, media_type
    ) VALUES (
        :admission_id, :role, :target_kind, :target_id, :anchor_kind, :anchor,
        :blob_id, :size, :sha256, :media_type
    )
    ON CONFLICT (role, target_kind, target_id, anchor_kind, anchor)
        WHERE state <> 'rejected' DO NOTHING
    RETURNING {_ADMISSION_COLUMNS}
    """
)
_LIVE_IN_SLOT = text(
    f"SELECT {_ADMISSION_COLUMNS} FROM norm_custody_admission "
    f"WHERE {_SLOT_MATCH} AND state <> 'rejected'"
)
_SELECT_ADMISSION = text(
    f"SELECT {_ADMISSION_COLUMNS} FROM norm_custody_admission "
    "WHERE norm_custody_admission_id = :admission_id"
)
_LOCK_ADMISSION = text(
    f"SELECT {_ADMISSION_COLUMNS} FROM norm_custody_admission "
    "WHERE norm_custody_admission_id = :admission_id FOR UPDATE"
)
_CLAIM_NEXT = text(
    f"SELECT {_ADMISSION_COLUMNS} FROM norm_custody_admission "
    "WHERE state = 'pending' AND available_at <= clock_timestamp() "
    "ORDER BY available_at, norm_custody_admission_id LIMIT 1 FOR UPDATE SKIP LOCKED"
)
_CONFIRM = text(
    "UPDATE norm_custody_admission SET state = 'confirmed', confirmed_at = clock_timestamp(), "
    "updated_at = clock_timestamp() "
    "WHERE norm_custody_admission_id = :admission_id AND state = 'pending'"
)
_REJECT = text(
    "UPDATE norm_custody_admission SET state = 'rejected', last_failure = :failure, "
    "updated_at = clock_timestamp() "
    "WHERE norm_custody_admission_id = :admission_id AND state IN ('pending', 'poisoned')"
)
_RETRY = text(
    "UPDATE norm_custody_admission SET attempt_count = :attempt_count, last_failure = :failure, "
    "available_at = clock_timestamp() + make_interval(secs => :delay), "
    "updated_at = clock_timestamp() "
    "WHERE norm_custody_admission_id = :admission_id AND state = 'pending'"
)
_POISON = text(
    "UPDATE norm_custody_admission SET state = 'poisoned', attempt_count = :attempt_count, "
    "last_failure = :failure, updated_at = clock_timestamp() "
    "WHERE norm_custody_admission_id = :admission_id AND state = 'pending'"
)
_REQUEUE = text(
    "UPDATE norm_custody_admission SET state = 'pending', attempt_count = 0, "
    "available_at = clock_timestamp(), updated_at = clock_timestamp() "
    "WHERE norm_custody_admission_id = :admission_id AND state = 'poisoned'"
)
_LOCK_FOR_TARGETS = text(
    f"SELECT {_ADMISSION_COLUMNS} FROM norm_custody_admission "
    "WHERE role = :role AND target_kind = :target_kind "
    "AND target_id = ANY(CAST(:target_ids AS text[])) "
    "AND state <> 'rejected' ORDER BY norm_custody_admission_id FOR UPDATE"
)
_INSERT_BINDING = text(
    f"""
    INSERT INTO norm_custody_binding (
        norm_custody_binding_id, norm_custody_admission_id, role, target_kind, target_id,
        anchor_kind, anchor, blob_id
    ) VALUES (
        :binding_id, :admission_id, :role, :target_kind, :target_id,
        :anchor_kind, :anchor, :blob_id
    )
    ON CONFLICT (norm_custody_admission_id) DO NOTHING
    RETURNING {_BINDING_COLUMNS}
    """
)
_BLOB_FACTS = text(
    "SELECT blob_id, state, sha256, size_bytes, media_type FROM blob "
    "WHERE blob_id = ANY(CAST(:blob_ids AS text[]))"
)
_INSERT_EVENT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
    "VALUES (:event_id, :event_type, :aggregate_type, :aggregate_id, CAST(:payload AS jsonb))"
)

_SCOPE = (
    "(CAST(:role AS text) IS NULL OR a.role = CAST(:role AS text)) "
    "AND (CAST(:target_ids AS text[]) IS NULL "
    "     OR a.target_id = ANY(CAST(:target_ids AS text[])))"
)
_STATE_COUNTS = text(
    f"SELECT a.state, count(*) FROM norm_custody_admission a WHERE {_SCOPE} GROUP BY a.state"
)
_IN_STATE = text(
    f"SELECT {', '.join('a.' + c.strip() for c in _ADMISSION_COLUMNS.split(','))} "
    f"FROM norm_custody_admission a WHERE a.state = :state AND {_SCOPE} "
    "ORDER BY a.created_at, a.norm_custody_admission_id"
)
_UNBOUND_CONFIRMED = text(
    f"SELECT {', '.join('a.' + c.strip() for c in _ADMISSION_COLUMNS.split(','))} "
    f"FROM norm_custody_admission a WHERE a.state = 'confirmed' AND {_SCOPE} "
    "AND NOT EXISTS (SELECT 1 FROM norm_custody_binding b "
    "                WHERE b.norm_custody_admission_id = a.norm_custody_admission_id) "
    "ORDER BY a.created_at, a.norm_custody_admission_id"
)
_BINDINGS_IN_SCOPE = text(
    f"SELECT {', '.join('a.' + c.strip() for c in _BINDING_COLUMNS.split(','))} "
    f"FROM norm_custody_binding a WHERE {_SCOPE} ORDER BY a.norm_custody_binding_id"
)
_REJECTED_BLOBS = text(
    "SELECT b.blob_id, EXISTS (SELECT 1 FROM norm_custody_admission a "
    "                          WHERE a.blob_id = b.blob_id) "
    "FROM blob b WHERE b.state = 'rejected' ORDER BY b.blob_id"
)
_CONFIRMED_WITH_BINDING = text(
    "SELECT a.norm_custody_admission_id, a.blob_id, a.declared_sha256, a.declared_size_bytes, "
    "a.media_type, b.norm_custody_binding_id, blob.state "
    "FROM norm_custody_admission a "
    "LEFT JOIN norm_custody_binding b ON b.norm_custody_admission_id = a.norm_custody_admission_id "
    "LEFT JOIN blob ON blob.blob_id = a.blob_id "
    "WHERE a.state = 'confirmed' ORDER BY a.blob_id, a.norm_custody_admission_id"
)
_REDRIVE_DUE = text(
    "SELECT norm_custody_admission_id FROM norm_custody_admission "
    "WHERE state = 'pending' AND available_at <= clock_timestamp() "
    "ORDER BY available_at, norm_custody_admission_id"
)


def _admission(row: Any) -> Admission:
    values = tuple(row)
    return Admission(
        admission_id=str(values[0]),
        role=str(values[1]),
        target_kind=str(values[2]),
        target_id=str(values[3]),
        anchor_kind=str(values[4]),
        anchor=str(values[5]),
        blob_id=str(values[6]),
        declared_size_bytes=int(values[7]),
        declared_sha256=str(values[8]),
        media_type=str(values[9]),
        state=AdmissionState(values[10]),
        attempt_count=int(values[11]),
        available_at=values[12],
        last_failure=None if values[13] is None else str(values[13]),
        created_at=values[14],
        confirmed_at=values[15],
    )


def _binding(row: Any) -> Binding:
    values = tuple(row)
    return Binding(
        binding_id=str(values[0]),
        admission_id=str(values[1]),
        role=str(values[2]),
        target_kind=str(values[3]),
        target_id=str(values[4]),
        anchor_kind=str(values[5]),
        anchor=str(values[6]),
        blob_id=str(values[7]),
        bound_at=values[8],
    )


def _slot_params(slot: CustodySlot) -> dict[str, str]:
    return {
        "role": slot.role,
        "target_kind": slot.target_kind,
        "target_id": slot.target_id,
        "anchor_kind": slot.anchor_kind,
        "anchor": slot.anchor,
    }


def _scope_params(role: str | None, target_ids: Sequence[str] | None) -> dict[str, Any]:
    return {"role": role, "target_ids": None if target_ids is None else list(target_ids)}


class CustodyRepository:
    """Rows of the two custody tables, and the custody events in ``audit_event``."""

    __slots__ = ()

    # -- admissions ----------------------------------------------------------

    def live_in_slot(self, session: Session, slot: CustodySlot) -> Admission | None:
        row = session.execute(_LIVE_IN_SLOT, _slot_params(slot)).first()
        return None if row is None else _admission(row)

    def insert_admission(
        self, session: Session, slot: CustodySlot, *, blob_id: str, content: DeclaredContent
    ) -> Admission | None:
        """Append one ``pending`` admission, or ``None`` when a live one holds the slot."""
        row = session.execute(
            _INSERT_ADMISSION,
            {
                **_slot_params(slot),
                "admission_id": str(NormCustodyAdmissionId.new()),
                "blob_id": blob_id,
                "size": content.size,
                "sha256": content.sha256,
                "media_type": content.media_type,
            },
        ).first()
        return None if row is None else _admission(row)

    def get(self, session: Session, admission_id: str) -> Admission | None:
        row = session.execute(_SELECT_ADMISSION, {"admission_id": admission_id}).first()
        return None if row is None else _admission(row)

    def lock(self, session: Session, admission_id: str) -> Admission | None:
        row = session.execute(_LOCK_ADMISSION, {"admission_id": admission_id}).first()
        return None if row is None else _admission(row)

    def claim_next(self, session: Session) -> Admission | None:
        """The next due ``pending`` admission, locked; another dispatcher skips it."""
        row = session.execute(_CLAIM_NEXT).first()
        return None if row is None else _admission(row)

    def confirm(self, session: Session, admission: Admission) -> bool:
        return session.execute(_CONFIRM, {"admission_id": admission.admission_id}).rowcount == 1

    def reject(self, session: Session, admission: Admission, failure: str) -> bool:
        return (
            session.execute(
                _REJECT, {"admission_id": admission.admission_id, "failure": failure}
            ).rowcount
            == 1
        )

    def record_failed_try(
        self, session: Session, admission: Admission, failure: str
    ) -> AdmissionState:
        """Count one failed try: reschedule it, or poison it after the fifth."""
        attempt = admission.attempt_count + 1
        if attempt >= MAX_ATTEMPTS:
            session.execute(
                _POISON,
                {
                    "admission_id": admission.admission_id,
                    "attempt_count": MAX_ATTEMPTS,
                    "failure": failure,
                },
            )
            return AdmissionState.POISONED
        session.execute(
            _RETRY,
            {
                "admission_id": admission.admission_id,
                "attempt_count": attempt,
                "failure": failure,
                "delay": float(RETRY_DELAYS_SECONDS[attempt - 1]),
            },
        )
        return AdmissionState.PENDING

    def requeue(self, session: Session, admission: Admission) -> bool:
        return session.execute(_REQUEUE, {"admission_id": admission.admission_id}).rowcount == 1

    def lock_for_targets(
        self, session: Session, *, role: str, target_kind: str, target_ids: Sequence[str]
    ) -> tuple[Admission, ...]:
        rows = session.execute(
            _LOCK_FOR_TARGETS,
            {"role": role, "target_kind": target_kind, "target_ids": list(target_ids)},
        ).all()
        return tuple(_admission(row) for row in rows)

    # -- targets and blobs ---------------------------------------------------

    def existing_targets(
        self, session: Session, *, target_kind: str, target_ids: Sequence[str]
    ) -> frozenset[str]:
        table, column = TARGET_TABLES[target_kind]
        rows = session.execute(
            text(f"SELECT {column} FROM {table} WHERE {column} = ANY(CAST(:ids AS text[]))"),
            {"ids": list(target_ids)},
        ).all()
        return frozenset(str(row[0]) for row in rows)

    def blob_facts(
        self, session: Session, blob_ids: Sequence[str]
    ) -> Mapping[str, tuple[str, str | None, int | None, str | None]]:
        rows = session.execute(_BLOB_FACTS, {"blob_ids": list(blob_ids)}).all()
        return {
            str(blob_id): (
                str(state),
                sha256,
                None if size is None else int(size),
                media_type,
            )
            for blob_id, state, sha256, size, media_type in rows
        }

    # -- bindings ------------------------------------------------------------

    def insert_binding(self, session: Session, admission: Admission) -> Binding | None:
        """Insert the binding of one confirmed admission; ``None`` if it already exists."""
        row = session.execute(
            _INSERT_BINDING,
            {
                "binding_id": str(NormCustodyBindingId.new()),
                "admission_id": admission.admission_id,
                "role": admission.role,
                "target_kind": admission.target_kind,
                "target_id": admission.target_id,
                "anchor_kind": admission.anchor_kind,
                "anchor": admission.anchor,
                "blob_id": admission.blob_id,
            },
        ).first()
        return None if row is None else _binding(row)

    # -- report --------------------------------------------------------------

    def state_counts(
        self, session: Session, *, role: str | None, target_ids: Sequence[str] | None
    ) -> dict[AdmissionState, int]:
        rows = session.execute(_STATE_COUNTS, _scope_params(role, target_ids)).all()
        return {AdmissionState(state): int(count) for state, count in rows}

    def in_state(
        self,
        session: Session,
        state: AdmissionState,
        *,
        role: str | None,
        target_ids: Sequence[str] | None,
    ) -> tuple[Admission, ...]:
        rows = session.execute(
            _IN_STATE, {"state": state.value, **_scope_params(role, target_ids)}
        ).all()
        return tuple(_admission(row) for row in rows)

    def unbound_confirmed(
        self, session: Session, *, role: str | None, target_ids: Sequence[str] | None
    ) -> tuple[Admission, ...]:
        rows = session.execute(_UNBOUND_CONFIRMED, _scope_params(role, target_ids)).all()
        return tuple(_admission(row) for row in rows)

    def bindings(
        self, session: Session, *, role: str | None, target_ids: Sequence[str] | None
    ) -> tuple[Binding, ...]:
        rows = session.execute(_BINDINGS_IN_SCOPE, _scope_params(role, target_ids)).all()
        return tuple(_binding(row) for row in rows)

    def rejected_blobs(self, session: Session) -> tuple[RejectedBlob, ...]:
        return tuple(
            RejectedBlob(blob_id=str(blob_id), named_by_custody=bool(named))
            for blob_id, named in session.execute(_REJECTED_BLOBS).all()
        )

    def confirmed_with_binding(self, session: Session) -> tuple[tuple[Any, ...], ...]:
        return tuple(tuple(row) for row in session.execute(_CONFIRMED_WITH_BINDING).all())

    def redrive_due(self, session: Session) -> tuple[str, ...]:
        return tuple(str(row[0]) for row in session.execute(_REDRIVE_DUE).all())

    # -- events --------------------------------------------------------------

    def append_event(
        self,
        session: Session,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Mapping[str, str | int | None],
    ) -> None:
        """One ``norm_custody.*`` audit event in the caller's transaction.

        The payload carries identities and classifiers only -- never an anchor's text, a
        file name or a checksum -- and the copy-record fingerprint excludes exactly this
        event-type family (plan §3.5).
        """
        if not event_type.startswith("norm_custody."):
            raise ValueError("custody events are the norm_custody.* family")
        session.execute(
            _INSERT_EVENT,
            {
                "event_id": str(AuditEventId.new()),
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "payload": json.dumps(dict(payload), sort_keys=True),
            },
        )


__all__ = ["CustodyRepository"]
