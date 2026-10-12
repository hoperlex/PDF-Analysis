"""The current norms snapshot: the reader, the qualification predicate and the setter.

`W55A-SEARCH-01` (`W55-PLAN.md` section A3.2; owner rulings R-112, R-113). Migration
``0020`` holds the state -- ``norm_current_snapshot`` (one row) and
``norm_current_snapshot_event`` (append-only) -- and refuses a change that does not name
its own history event. This module is the only writer and the only reader other contexts
use, through ``auditmanager.norms.public``: `W55A-PIN-01` reads :func:`current_snapshot`
inside the run-creating transaction, and W57a extends :func:`qualification` here.

**Qualification.** A snapshot may be designated only when

(a) it has a complete ``bge-m3-dense-v1`` build (`D-127`) over the reliability-aware chunks
    (``characters-v2:<n>``): a ``norm_embedding_build`` row, which W54's loader writes last
    and in the same transaction as every window (``W54-EMBED-01.md``), so its presence *is*
    completeness; and
(b) every document of the snapshot has a confirmed ``norm_source`` custody binding of its
    PDF: the slot ``(norm_source, norm_document, <ndoc>, pdf, <source_document_ref>)`` that
    W54's bundle declares for ``document.pdf``. A binding row exists only for a confirmed
    admission (``0018``'s guard), so its presence is the confirmation.

Otherwise the setter refuses ``required_norm_unavailable`` with ``reference_kind``
``norm_embedding_build`` (a) or ``norm_source`` (b). The predicate is written once, as the
SQL expressions :data:`BUILD_COMPLETE_SQL` and :data:`SOURCES_CONFIRMED_SQL`, and the snapshot
listing evaluates the very same expressions, so ``listNormSnapshots.qualified`` cannot
disagree with what the setter accepts. That the rows and the build equal the manifest is
procedural (``report <key>`` before any designation), not this predicate's.

**The setter** (``setCurrentNormSnapshot``) runs under one transaction-scoped advisory lock,
so two designations are serialised rather than racing the singleton row:

1. an unknown target is ``not_found`` (``NormsSnapshot``);
2. a target that is already current is a **replay**: the current designation is answered
   and nothing is written, whatever ``expected_current`` says;
3. a target that does not qualify is ``required_norm_unavailable`` (build first, then
   sources);
4. an ``expected_current`` that is not the current snapshot (``None`` meaning "none is
   current") is ``conflict`` with ``conflict_reason: stale_current_snapshot``;
5. otherwise one history row is appended and the singleton row names it.

There is no unset.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, NormsSnapshotId
from auditmanager.shared.identity.ids import UserUid

from .chunking import RELIABLE_CHUNKING_PROFILE_VERSION
from .embedding.profile import EMBEDDING_PROFILE

__all__ = [
    "BUILD_COMPLETE_SQL",
    "CurrentSnapshot",
    "Designation",
    "PDF_ANCHOR_KIND",
    "PDF_BINDING_SQL",
    "QUALIFICATION_PARAMETERS",
    "Qualification",
    "SOURCES_CONFIRMED_SQL",
    "SnapshotEvent",
    "current_snapshot",
    "has_been_current",
    "list_snapshot_events",
    "qualification",
    "set_current_snapshot",
]

#: The anchor kind of a document's source PDF (``ck_norm_custody_role_shape``).
PDF_ANCHOR_KIND: Final[str] = "pdf"

#: The bind parameters :data:`BUILD_COMPLETE_SQL` and :data:`PDF_BINDING_SQL` read.
QUALIFICATION_PARAMETERS: Final[dict[str, str]] = {
    "q_embedding_profile": EMBEDDING_PROFILE,
    "q_reliable_chunking": f"{RELIABLE_CHUNKING_PROFILE_VERSION}:%",
    "q_role": "norm_source",
    "q_target_kind": "norm_document",
    "q_anchor_kind": PDF_ANCHOR_KIND,
}

#: Condition (a), over a ``norms_snapshot`` aliased ``s``.
BUILD_COMPLETE_SQL: Final[str] = """
EXISTS (
    SELECT 1 FROM norm_embedding_build qb
     WHERE qb.norms_snapshot_id = s.norms_snapshot_id
       AND qb.embedding_profile = :q_embedding_profile
       AND qb.chunking_profile LIKE :q_reliable_chunking
)
"""

#: The confirmed binding of one document's PDF, over a ``norm_document`` aliased ``d``.
#: ``streamNormDocumentContent`` serves exactly this binding and ``content_available`` is its
#: existence, so the three can never disagree.
PDF_BINDING_SQL: Final[str] = """
SELECT qn.blob_id FROM norm_custody_binding qn
 WHERE qn.role = :q_role
   AND qn.target_kind = :q_target_kind
   AND qn.target_id = d.norm_document_id
   AND qn.anchor_kind = :q_anchor_kind
   AND qn.anchor = d.source_document_ref
"""

#: Condition (b), over a ``norms_snapshot`` aliased ``s``: no document lacks that binding.
SOURCES_CONFIRMED_SQL: Final[str] = f"""
NOT EXISTS (
    SELECT 1 FROM norm_document d
     WHERE d.norms_snapshot_id = s.norms_snapshot_id
       AND NOT EXISTS ({PDF_BINDING_SQL})
)
"""

_LOCK = text(
    "SELECT pg_advisory_xact_lock(hashtextextended('auditmanager.norm_current_snapshot', 0))"
)

_CURRENT = text(
    """
    SELECT c.norms_snapshot_id, c.event_id, e.changed_at, e.actor_user_uid
      FROM norm_current_snapshot c
      JOIN norm_current_snapshot_event e ON e.event_id = c.event_id
     WHERE c.singleton
    """
)

_HAS_BEEN_CURRENT = text(
    "SELECT EXISTS (SELECT 1 FROM norm_current_snapshot_event WHERE to_snapshot_id = :s)"
)

_QUALIFICATION = text(
    f"""
    SELECT ({BUILD_COMPLETE_SQL}) AS build_complete,
           ({SOURCES_CONFIRMED_SQL}) AS sources_confirmed
      FROM norms_snapshot s
     WHERE s.norms_snapshot_id = :s
    """
)

_APPEND_EVENT = text(
    """
    INSERT INTO norm_current_snapshot_event
        (event_id, from_snapshot_id, to_snapshot_id, actor_user_uid)
    VALUES (:event_id, :from_id, :to_id, :actor)
    RETURNING changed_at
    """
)

_INSERT_CURRENT = text(
    "INSERT INTO norm_current_snapshot (singleton, norms_snapshot_id, event_id) "
    "VALUES (true, :to_id, :event_id)"
)

_UPDATE_CURRENT = text(
    "UPDATE norm_current_snapshot SET norms_snapshot_id = :to_id, event_id = :event_id "
    "WHERE singleton"
)

_EVENTS = text(
    """
    SELECT event_id, from_snapshot_id, to_snapshot_id, actor_user_uid, changed_at
      FROM norm_current_snapshot_event
     WHERE CAST(:after_at AS timestamptz) IS NULL
        OR (changed_at, event_id COLLATE "C")
           < (CAST(:after_at AS timestamptz), CAST(:after_id AS text) COLLATE "C")
     ORDER BY changed_at DESC, event_id COLLATE "C" DESC
     LIMIT :row_limit
    """
)


@dataclass(frozen=True, slots=True)
class CurrentSnapshot:
    """The one current snapshot and the history event that designated it."""

    norms_snapshot_id: str
    event_id: str
    designated_at: datetime
    designated_by: str


@dataclass(frozen=True, slots=True)
class Designation:
    current: CurrentSnapshot
    #: ``True`` when the target was already current and nothing was written.
    replayed: bool


@dataclass(frozen=True, slots=True)
class Qualification:
    """Both halves of the predicate, so a refusal can name the missing one."""

    build_complete: bool
    sources_confirmed: bool

    @property
    def qualified(self) -> bool:
        return self.build_complete and self.sources_confirmed


@dataclass(frozen=True, slots=True)
class SnapshotEvent:
    event_id: str
    from_snapshot_id: str | None
    to_snapshot_id: str
    actor_user_uid: str
    changed_at: datetime


def current_snapshot(session: Session) -> CurrentSnapshot | None:
    """The current snapshot as the caller's transaction sees it, or ``None`` before the first
    designation (`CD-6`)."""
    row = session.execute(_CURRENT).one_or_none()
    if row is None:
        return None
    return CurrentSnapshot(
        norms_snapshot_id=str(row.norms_snapshot_id),
        event_id=str(row.event_id),
        designated_at=row.changed_at,
        designated_by=str(row.actor_user_uid),
    )


def has_been_current(session: Session, norms_snapshot_id: str) -> bool:
    """Whether the history names ``norms_snapshot_id`` as a designation's target."""
    return bool(session.execute(_HAS_BEEN_CURRENT, {"s": norms_snapshot_id}).scalar_one())


def qualification(session: Session, norms_snapshot_id: str) -> Qualification | None:
    """Both conditions for one snapshot, or ``None`` when no such snapshot is loaded."""
    row = session.execute(
        _QUALIFICATION, {"s": norms_snapshot_id, **QUALIFICATION_PARAMETERS}
    ).one_or_none()
    if row is None:
        return None
    return Qualification(bool(row.build_complete), bool(row.sources_confirmed))


def set_current_snapshot(
    session: Session,
    *,
    norms_snapshot_id: str,
    expected_current: str | None,
    actor_user_uid: str,
) -> Designation:
    """Designate ``norms_snapshot_id``; the caller commits. See the module docstring."""
    target = str(NormsSnapshotId.parse(norms_snapshot_id))
    expected = None if expected_current is None else str(NormsSnapshotId.parse(expected_current))
    actor = str(UserUid.parse(actor_user_uid))

    session.execute(_LOCK)
    qualified = qualification(session, target)
    if qualified is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="NormsSnapshot")
    current = current_snapshot(session)
    if current is not None and current.norms_snapshot_id == target:
        return Designation(current=current, replayed=True)
    if not qualified.build_complete:
        raise DomainError(
            ErrorCode.REQUIRED_NORM_UNAVAILABLE,
            reference_kind="norm_embedding_build",
            norms_snapshot_id=target,
        )
    if not qualified.sources_confirmed:
        raise DomainError(
            ErrorCode.REQUIRED_NORM_UNAVAILABLE,
            reference_kind="norm_source",
            norms_snapshot_id=target,
        )
    current_id = None if current is None else current.norms_snapshot_id
    if expected != current_id:
        raise DomainError(ErrorCode.CONFLICT, conflict_reason="stale_current_snapshot")

    event_id = str(AuditEventId.new())
    changed_at = session.execute(
        _APPEND_EVENT,
        {"event_id": event_id, "from_id": current_id, "to_id": target, "actor": actor},
    ).scalar_one()
    session.execute(
        _INSERT_CURRENT if current is None else _UPDATE_CURRENT,
        {"to_id": target, "event_id": event_id},
    )
    return Designation(
        current=CurrentSnapshot(
            norms_snapshot_id=target,
            event_id=event_id,
            designated_at=changed_at,
            designated_by=actor,
        ),
        replayed=False,
    )


def list_snapshot_events(
    session: Session,
    *,
    after: tuple[datetime, str] | None,
    limit: int,
) -> Sequence[SnapshotEvent]:
    """Up to ``limit`` history rows after ``after`` (``(changed_at, event_id)`` of the last
    row already seen), newest first."""
    rows = session.execute(
        _EVENTS,
        {
            "after_at": None if after is None else after[0],
            "after_id": None if after is None else after[1],
            "row_limit": limit,
        },
    ).all()
    return tuple(
        SnapshotEvent(
            event_id=str(row.event_id),
            from_snapshot_id=None if row.from_snapshot_id is None else str(row.from_snapshot_id),
            to_snapshot_id=str(row.to_snapshot_id),
            actor_user_uid=str(row.actor_user_uid),
            changed_at=row.changed_at,
        )
        for row in rows
    )
