"""The stored sheet links of a comparison: an append-only history in ``comparison_sheet_link``.

`COMPARE-PERSISTED-SUMMARY-01`. One row is one event of one sheet link, ``approved`` or
``withdrawn`` (migration ``0035_comparison_records``). A pairing is never updated: withdrawing is a
new row naming the same ``sln_`` identity. The rows of one comparison -- one ordered pair of
versions of one document -- are numbered 1, 2, 3, ... and that number is the ``link_revision`` that
:mod:`~auditmanager.comparison.raw_text`, :mod:`~auditmanager.comparison.raw_evidence_seal` and
:mod:`~auditmanager.comparison.summary_input` already take.

A sheet is never identified by a display number or a file name: it is a version, a page
coordinate in that immutable version and the SHA-256 of the page's text. The **active set** is the
``approved`` events that have no ``withdrawn`` event; it is derived here from the history on every
read, so nothing can disagree with it.

This module is SQL and values only: it validates nothing about *whether* a pairing should be
approved (that is :mod:`~auditmanager.comparison.pairing`) and it enforces nothing the database
does not also enforce (the chain trigger ``am_check_comparison_sheet_link_chain``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Protocol, runtime_checkable

from sqlalchemy import text
from sqlalchemy.orm import Session

KIND_APPROVED: Final[str] = "approved"
KIND_WITHDRAWN: Final[str] = "withdrawn"
EVENT_KINDS: Final[tuple[str, ...]] = (KIND_APPROVED, KIND_WITHDRAWN)

#: ``raw_text.MAX_PAIRS``: restated in the migration (a migration is history), held equal by a test.
MAX_ACTIVE_LINKS: Final[int] = 32

_COLUMNS: Final[str] = (
    "comparison_id, link_revision, event_kind, sheet_link_id, project_uid, document_uid, "
    "source_version_uid, target_version_uid, source_page_number, target_page_number, "
    "source_page_text_sha256, target_page_text_sha256, suggestion_sha256, "
    "raw_evidence_seal_sha256, actor_user_uid, actor_label, command_id, decided_at"
)
_BY_PAIR = text(
    f"SELECT {_COLUMNS} FROM comparison_sheet_link "
    "WHERE source_version_uid = :source_version_uid AND target_version_uid = :target_version_uid "
    "ORDER BY link_revision"
)
_FIND_APPROVAL = text(
    f"SELECT {_COLUMNS} FROM comparison_sheet_link "
    "WHERE sheet_link_id = :sheet_link_id AND event_kind = 'approved' "
    "AND project_uid = :project_uid AND document_uid = :document_uid "
    "AND source_version_uid = :source_version_uid"
)
_AT_REVISION = text(
    f"SELECT {_COLUMNS} FROM comparison_sheet_link "
    "WHERE comparison_id = :comparison_id AND link_revision = :link_revision"
)
_BY_COMMAND = text(f"SELECT {_COLUMNS} FROM comparison_sheet_link WHERE command_id = :command_id")
_LOCK = text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))")
_INSERT = text(
    "INSERT INTO comparison_sheet_link (comparison_id, link_revision, event_kind, sheet_link_id, "
    "project_uid, document_uid, source_version_uid, target_version_uid, source_page_number, "
    "target_page_number, source_page_text_sha256, target_page_text_sha256, suggestion_sha256, "
    "raw_evidence_seal_sha256, actor_user_uid, actor_label, command_id) VALUES "
    "(:comparison_id, :link_revision, :event_kind, :sheet_link_id, :project_uid, :document_uid, "
    ":source_version_uid, :target_version_uid, :source_page_number, :target_page_number, "
    ":source_page_text_sha256, :target_page_text_sha256, :suggestion_sha256, "
    ":raw_evidence_seal_sha256, :actor_user_uid, :actor_label, :command_id) "
    "RETURNING decided_at"
)


@dataclass(frozen=True, slots=True)
class LinkEvent:
    """One stored row."""

    comparison_id: str
    link_revision: int
    event_kind: str
    sheet_link_id: str
    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    source_page_number: int
    target_page_number: int
    source_page_text_sha256: str
    target_page_text_sha256: str
    suggestion_sha256: str
    raw_evidence_seal_sha256: str | None
    actor_user_uid: str
    actor_label: str
    command_id: str
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class LinkState:
    """The history of one ordered pair of versions, oldest first, and what is active in it."""

    events: tuple[LinkEvent, ...]

    @property
    def comparison_id(self) -> str | None:
        return self.events[0].comparison_id if self.events else None

    @property
    def latest_revision(self) -> int:
        return self.events[-1].link_revision if self.events else 0

    @property
    def latest_seal_sha256(self) -> str | None:
        return self.events[-1].raw_evidence_seal_sha256 if self.events else None

    @property
    def active(self) -> tuple[LinkEvent, ...]:
        """The ``approved`` events with no ``withdrawn`` event, ordered by source page."""
        withdrawn = {e.sheet_link_id for e in self.events if e.event_kind == KIND_WITHDRAWN}
        return tuple(sorted(
            (
                e for e in self.events
                if e.event_kind == KIND_APPROVED and e.sheet_link_id not in withdrawn
            ),
            key=lambda e: (e.source_page_number, e.sheet_link_id),
        ))


@dataclass(frozen=True, slots=True)
class NewLinkEvent:
    """A row to append. ``decided_at`` is the database's."""

    comparison_id: str
    link_revision: int
    event_kind: str
    sheet_link_id: str
    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    source_page_number: int
    target_page_number: int
    source_page_text_sha256: str
    target_page_text_sha256: str
    suggestion_sha256: str
    raw_evidence_seal_sha256: str | None
    actor_user_uid: str
    actor_label: str
    command_id: str


@runtime_checkable
class ApprovedLinkReader(Protocol):
    """What the served comparison needs of the store: the history of one ordered pair."""

    def state(
        self, session: Session, *, source_version_uid: str, target_version_uid: str,
    ) -> LinkState:
        """Every stored event of the pair, oldest first (empty if it was never paired)."""


def _event(row: object) -> LinkEvent:
    values = tuple(row)  # type: ignore[call-overload]
    return LinkEvent(*values)


class SheetLinkRepository:
    """SQL for ``comparison_sheet_link``. The caller owns the transaction."""

    def state(
        self, session: Session, *, source_version_uid: str, target_version_uid: str,
    ) -> LinkState:
        rows = session.execute(_BY_PAIR, {
            "source_version_uid": source_version_uid, "target_version_uid": target_version_uid,
        }).all()
        return LinkState(tuple(_event(row) for row in rows))

    def lock_pair(
        self, session: Session, *, source_version_uid: str, target_version_uid: str,
    ) -> None:
        """Serialise the writers of one pair until the transaction ends.

        The application role holds no UPDATE privilege, so it cannot take a row lock; the chain
        trigger takes the same advisory lock, so a writer that did not call this is serialised
        there, only later.
        """
        session.execute(_LOCK, {"key": lock_key(source_version_uid, target_version_uid)})

    def find_approval(
        self,
        session: Session,
        *,
        project_uid: str,
        document_uid: str,
        source_version_uid: str,
        sheet_link_id: str,
    ) -> LinkEvent | None:
        """The approval row of a link, if the link belongs to this project, document and source."""
        row = session.execute(_FIND_APPROVAL, {
            "sheet_link_id": sheet_link_id, "project_uid": project_uid,
            "document_uid": document_uid, "source_version_uid": source_version_uid,
        }).first()
        return None if row is None else _event(row)

    def event_at(
        self, session: Session, *, comparison_id: str, link_revision: int,
    ) -> LinkEvent | None:
        row = session.execute(
            _AT_REVISION, {"comparison_id": comparison_id, "link_revision": link_revision},
        ).first()
        return None if row is None else _event(row)

    def event_of_command(self, session: Session, *, command_id: str) -> LinkEvent | None:
        row = session.execute(_BY_COMMAND, {"command_id": command_id}).first()
        return None if row is None else _event(row)

    def append(self, session: Session, event: NewLinkEvent) -> LinkEvent:
        """INSERT one event. The chain trigger refuses anything the history does not admit."""
        decided_at = session.execute(_INSERT, {
            name: getattr(event, name) for name in NewLinkEvent.__dataclass_fields__
        }).scalar_one()
        return _with_time(event, decided_at)


def _with_time(event: NewLinkEvent, decided_at: datetime) -> LinkEvent:
    values = {name: getattr(event, name) for name in NewLinkEvent.__dataclass_fields__}
    return LinkEvent(**values, decided_at=decided_at)


def lock_key(source_version_uid: str, target_version_uid: str) -> str:
    """The advisory-lock key of a pair; the chain trigger builds the same string."""
    return f"comparison_sheet_link:{source_version_uid}:{target_version_uid}"


__all__ = [
    "ApprovedLinkReader", "EVENT_KINDS", "KIND_APPROVED", "KIND_WITHDRAWN", "LinkEvent",
    "LinkState", "MAX_ACTIVE_LINKS", "NewLinkEvent", "SheetLinkRepository", "lock_key",
]
