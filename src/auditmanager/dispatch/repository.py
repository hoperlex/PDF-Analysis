"""Reads and writes of ``work_assignment``, its history and the derived current state.

Statements only; every rule is in :mod:`.policy` and every decision in :mod:`.commands`.
The caller owns the transaction (the composition root's unit of work).

**Concurrency.** A transition locks its assignment row (``FOR UPDATE``; the immutability
trigger fires on UPDATE and DELETE, never on a row lock) before it reads the latest event,
so two moves on one assignment are serialized and the second is decided against the first.
``uq_work_assignment_event_assignment_uid_seq`` is the backstop. A creation takes a
transaction-scoped advisory lock on its scope (the project, or the project and document)
before it looks for an open assignment there, so two concurrent creations on one scope
cannot both find none.

**Order.** Listings are newest first, ``(created_at, assignment_uid)`` with the identifier
under ``COLLATE "C"`` so the tie-break does not move with the server's locale. ``seq`` orders
one assignment's history and is never selected into a record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.dispatch.identity import AssignmentUid
from auditmanager.dispatch.policy import KIND_REASSIGNED, STATUS_AFTER, CurrentState
from auditmanager.shared.identity import AuditEventId

__all__ = ["AssignmentEvent", "AssignmentRecord", "AssignmentRepository", "LockedAssignment"]


@dataclass(frozen=True, slots=True)
class AssignmentRecord:
    """One assignment as a reader sees it: identity, scope, people, status and when.

    ``assignee_user_uid`` is the **current** assignee. ``status_reason`` is the reason the
    latest event carried (a return's, a cancellation's or a reassignment's), ``None`` when it
    carried none. ``project_name`` and ``document_title`` are display labels, never keys.
    """

    assignment_uid: str
    project_uid: str
    project_name: str
    document_uid: str | None
    document_title: str | None
    assignee_user_uid: str
    created_by_user_uid: str
    note: str | None
    status: str
    status_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AssignmentEvent:
    """One history event, as it stands for ever. No ``seq``: the list's order carries it."""

    event_id: str
    kind: str
    actor_user_uid: str
    reason: str | None
    new_assignee_user_uid: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class LockedAssignment:
    """The current state of a locked assignment and the ``seq`` its next event takes."""

    state: CurrentState
    next_seq: int


_COLUMNS: Final[str] = """
    c.assignment_uid, c.project_uid, p.name AS project_name, c.document_uid,
    d.display_title AS document_title, c.current_assignee_user_uid, c.created_by_user_uid,
    c.note, c.last_kind, c.last_reason, c.created_at, c.last_occurred_at
"""

_FROM: Final[str] = """
    FROM work_assignment_current c
    JOIN project p ON p.project_uid = c.project_uid
    LEFT JOIN document d ON d.document_uid = c.document_uid
"""

_ORDER: Final[str] = 'ORDER BY c.created_at DESC, c.assignment_uid COLLATE "C" DESC'

_SELECT_ONE = text(f"SELECT {_COLUMNS} {_FROM} WHERE c.assignment_uid = :assignment_uid")

#: The filters bind as ``CAST(:x AS ...) IS NULL OR ...``: without the cast PostgreSQL cannot
#: type the parameter on the ``IS NULL`` branch.
_LIST = text(
    f"""
    SELECT {_COLUMNS} {_FROM}
    WHERE (CAST(:assignee AS text) IS NULL
           OR c.current_assignee_user_uid = CAST(:assignee AS text))
      AND (CAST(:project AS text) IS NULL OR c.project_uid = CAST(:project AS text))
      AND (CAST(:kinds AS text[]) IS NULL OR c.last_kind = ANY (CAST(:kinds AS text[])))
    {_ORDER}
    """
)

_OPEN_IN_SCOPE = text(
    f"""
    SELECT {_COLUMNS}, c.first_assignee_user_uid {_FROM}
    WHERE c.project_uid = :project
      AND c.document_uid IS NOT DISTINCT FROM CAST(:document AS text)
      AND c.last_kind <> ALL (CAST(:terminal_kinds AS text[]))
    {_ORDER}
    """
)

_LOCK_SCOPE = text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))")

_LOCK_ASSIGNMENT = text(
    "SELECT assignment_uid FROM work_assignment WHERE assignment_uid = :assignment_uid "
    "FOR UPDATE"
)

_CURRENT = text(
    "SELECT current_assignee_user_uid, last_kind, last_reason, last_seq "
    "FROM work_assignment_current WHERE assignment_uid = :assignment_uid"
)

_HISTORY = text(
    "SELECT event_id, kind, actor_user_uid, reason, new_assignee_user_uid, occurred_at "
    "FROM work_assignment_event WHERE assignment_uid = :assignment_uid ORDER BY seq"
)

_INSERT_ASSIGNMENT = text(
    "INSERT INTO work_assignment (assignment_uid, project_uid, document_uid, "
    "assignee_user_uid, created_by_user_uid, note) "
    "VALUES (:assignment_uid, :project_uid, :document_uid, :assignee_user_uid, "
    ":created_by_user_uid, :note)"
)

_INSERT_EVENT = text(
    "INSERT INTO work_assignment_event (event_id, assignment_uid, seq, kind, actor_user_uid, "
    "reason, new_assignee_user_uid) "
    "VALUES (:event_id, :assignment_uid, :seq, :kind, :actor_user_uid, :reason, "
    ":new_assignee_user_uid)"
)


def _record(row: Any) -> AssignmentRecord:
    return AssignmentRecord(
        assignment_uid=row.assignment_uid,
        project_uid=row.project_uid,
        project_name=row.project_name,
        document_uid=row.document_uid,
        document_title=row.document_title,
        assignee_user_uid=row.current_assignee_user_uid,
        created_by_user_uid=row.created_by_user_uid,
        note=row.note,
        status=STATUS_AFTER[row.last_kind],
        status_reason=row.last_reason,
        created_at=row.created_at,
        updated_at=row.last_occurred_at,
    )


class AssignmentRepository:
    """The statements of the dispatch boundary. Stateless; the session is the caller's."""

    __slots__ = ()

    # -- reads -------------------------------------------------------------------------

    def get(self, session: Session, assignment_uid: AssignmentUid) -> AssignmentRecord | None:
        row = session.execute(_SELECT_ONE, {"assignment_uid": str(assignment_uid)}).first()
        return None if row is None else _record(row)

    def list(
        self,
        session: Session,
        *,
        assignee_user_uid: str | None,
        project_uid: str | None,
        kinds: frozenset[str] | None,
    ) -> tuple[AssignmentRecord, ...]:
        rows = session.execute(
            _LIST,
            {
                "assignee": assignee_user_uid,
                "project": project_uid,
                "kinds": None if kinds is None else sorted(kinds),
            },
        ).all()
        return tuple(_record(row) for row in rows)

    def history(self, session: Session, assignment_uid: AssignmentUid) -> tuple[AssignmentEvent, ...]:
        rows = session.execute(_HISTORY, {"assignment_uid": str(assignment_uid)}).all()
        return tuple(
            AssignmentEvent(
                event_id=row.event_id,
                kind=row.kind,
                actor_user_uid=row.actor_user_uid,
                reason=row.reason,
                new_assignee_user_uid=row.new_assignee_user_uid,
                occurred_at=row.occurred_at,
            )
            for row in rows
        )

    def open_in_scope(
        self,
        session: Session,
        *,
        project_uid: str,
        document_uid: str | None,
        terminal_kinds: frozenset[str],
    ) -> tuple[tuple[AssignmentRecord, str], ...]:
        """Open assignments of exactly this scope, each with its **first** assignee."""
        rows = session.execute(
            _OPEN_IN_SCOPE,
            {
                "project": project_uid,
                "document": document_uid,
                "terminal_kinds": sorted(terminal_kinds),
            },
        ).all()
        return tuple((_record(row), row.first_assignee_user_uid) for row in rows)

    # -- locks -------------------------------------------------------------------------

    def lock_scope(self, session: Session, *, project_uid: str, document_uid: str | None) -> None:
        """Serialize creations on one scope until this transaction ends."""
        scope = f"work_assignment:{project_uid}:{document_uid or '-'}"
        session.execute(_LOCK_SCOPE, {"scope": scope})

    def lock(self, session: Session, assignment_uid: AssignmentUid) -> LockedAssignment | None:
        """Lock the assignment row and read its current state; ``None`` for no such row."""
        locked = session.execute(
            _LOCK_ASSIGNMENT, {"assignment_uid": str(assignment_uid)}
        ).first()
        if locked is None:
            return None
        row = session.execute(_CURRENT, {"assignment_uid": str(assignment_uid)}).one()
        state = CurrentState(
            current_assignee=row.current_assignee_user_uid,
            last_kind=row.last_kind,
            last_reason=row.last_reason,
            # The latest event names a new assignee only when it is a reassignment, and then
            # that assignee is the current one.
            last_new_assignee=(
                row.current_assignee_user_uid if row.last_kind == KIND_REASSIGNED else None
            ),
        )
        return LockedAssignment(state=state, next_seq=int(row.last_seq) + 1)

    # -- writes ------------------------------------------------------------------------

    def insert_assignment(
        self,
        session: Session,
        *,
        assignment_uid: AssignmentUid,
        project_uid: str,
        document_uid: str | None,
        assignee_user_uid: str,
        created_by_user_uid: str,
        note: str | None,
    ) -> None:
        session.execute(
            _INSERT_ASSIGNMENT,
            {
                "assignment_uid": str(assignment_uid),
                "project_uid": project_uid,
                "document_uid": document_uid,
                "assignee_user_uid": assignee_user_uid,
                "created_by_user_uid": created_by_user_uid,
                "note": note,
            },
        )

    def append_event(
        self,
        session: Session,
        *,
        assignment_uid: AssignmentUid,
        seq: int,
        kind: str,
        actor_user_uid: str,
        reason: str | None = None,
        new_assignee_user_uid: str | None = None,
    ) -> None:
        session.execute(
            _INSERT_EVENT,
            {
                "event_id": str(AuditEventId.new()),
                "assignment_uid": str(assignment_uid),
                "seq": seq,
                "kind": kind,
                "actor_user_uid": actor_user_uid,
                "reason": reason,
                "new_assignee_user_uid": new_assignee_user_uid,
            },
        )
