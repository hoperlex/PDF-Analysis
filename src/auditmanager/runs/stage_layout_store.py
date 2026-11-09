"""Storage of the stage layout: its revisions and the journal of its switch (`HOSTS-LAYOUT-01`, ADR-0028 decision 14, migration ``0062``).

Three tables hold it and nothing else does: ``stage_layout`` (one row, key ``default``), ``stage_layout_revision`` (append-only,
numbered without a gap, ``slr_<ULID>``, the author) and ``stage_layout_switch_event`` (append-only, ``sls_<ULID>``, the author). The switch
in force is the **latest event**; an empty journal means off. Nothing is updated and nothing is deleted: the database refuses both.

This module only reads and appends. Who may, what a revision must satisfy and what the switch needs are decided by
:mod:`auditmanager.bootstrap.stage_plan_service`; what a revision means for a run is :mod:`auditmanager.runs.stage_layout`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Mapping, Protocol, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import CellSettings
from auditmanager.runs.stage_layout import cells_to_wire
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import StageLayoutRevisionId, StageLayoutSwitchEventId

__all__ = ["LAYOUT_KEY", "LayoutRevisionRow", "SqlStageLayoutStore", "StageLayoutStore", "SwitchEventRow"]

LAYOUT_KEY: Final[str] = "default"


@dataclass(frozen=True, slots=True)
class LayoutRevisionRow:
    layout_revision_id: str
    revision_no: int
    kit: str
    cells: tuple[CellSettings, ...]
    created_at: datetime
    created_by: str


@dataclass(frozen=True, slots=True)
class SwitchEventRow:
    enabled: bool
    set_at: datetime
    set_by: str


class StageLayoutStore(Protocol):
    """What the service and the start commands need of the storage. The SQL implementation is :class:`SqlStageLayoutStore`; a unit test
    hands the same shape from memory."""

    def lock(self, session: Session) -> None: ...

    def enabled(self, session: Session) -> bool: ...

    def current_revision(self, session: Session) -> LayoutRevisionRow | None: ...

    def history(self, session: Session, *, limit: int) -> Sequence[LayoutRevisionRow]: ...

    def switch_journal(self, session: Session, *, limit: int) -> Sequence[SwitchEventRow]: ...

    def append_revision(
        self, session: Session, *, kit: str, cells: Sequence[CellSettings], created_by: str,
    ) -> LayoutRevisionRow: ...

    def append_switch(self, session: Session, *, enabled: bool, set_by: str) -> SwitchEventRow: ...


_SELECT_REVISIONS = text(
    "SELECT layout_revision_id, revision_no, kit, cells, created_at, created_by FROM stage_layout_revision "
    "WHERE layout_key = :key ORDER BY revision_no DESC LIMIT :limit"
)
_SELECT_SWITCH_EVENTS = text(
    "SELECT enabled, set_at, set_by FROM stage_layout_switch_event WHERE layout_key = :key ORDER BY event_no DESC LIMIT :limit"
)
_NEXT_REVISION_NO = text("SELECT coalesce(max(revision_no), 0) + 1 FROM stage_layout_revision WHERE layout_key = :key")
_NEXT_EVENT_NO = text("SELECT coalesce(max(event_no), 0) + 1 FROM stage_layout_switch_event WHERE layout_key = :key")
_INSERT_REVISION = text(
    "INSERT INTO stage_layout_revision (layout_revision_id, layout_key, revision_no, kit, cells, created_by) "
    "VALUES (:id, :key, :no, :kit, CAST(:cells AS jsonb), :by) RETURNING created_at"
)
_INSERT_SWITCH = text(
    "INSERT INTO stage_layout_switch_event (switch_event_id, layout_key, event_no, enabled, set_by) "
    "VALUES (:id, :key, :no, :enabled, :by) RETURNING set_at"
)
# The two numbering triggers take ``pg_advisory_xact_lock(hashtextextended(table || ':' || key, 0))``; taking the same lock first makes the
# read of the next number and the insert one step for every writer.
_LOCK_REVISIONS = text("SELECT pg_advisory_xact_lock(hashtextextended('stage_layout_revision:' || :key, 0))")
_LOCK_SWITCH = text("SELECT pg_advisory_xact_lock(hashtextextended('stage_layout_switch_event:' || :key, 0))")


def _cells_of(document: Any) -> tuple[CellSettings, ...]:
    try:
        return tuple(
            CellSettings(
                cell_key=str(item["cell_key"]), model_id=str(item["model_id"]), effort=str(item["effort"]),
                max_output_tokens=int(item["max_output_tokens"]), timeout_seconds=int(item["timeout_seconds"]),
            )
            for item in document
        )
    except (KeyError, TypeError, ValueError):
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="a stored stage layout revision is invalid") from None


def _revision(row: Mapping[str, Any]) -> LayoutRevisionRow:
    return LayoutRevisionRow(
        layout_revision_id=row["layout_revision_id"], revision_no=int(row["revision_no"]), kit=row["kit"],
        cells=_cells_of(row["cells"]), created_at=row["created_at"], created_by=row["created_by"],
    )


class SqlStageLayoutStore:
    def lock(self, session: Session) -> None:
        """Serialise the writers of the layout (a revision and a switch change queue behind each other) for this transaction."""
        session.execute(_LOCK_REVISIONS, {"key": LAYOUT_KEY})
        session.execute(_LOCK_SWITCH, {"key": LAYOUT_KEY})

    def enabled(self, session: Session) -> bool:
        events = self.switch_journal(session, limit=1)
        return bool(events) and events[0].enabled

    def current_revision(self, session: Session) -> LayoutRevisionRow | None:
        rows = self.history(session, limit=1)
        return rows[0] if rows else None

    def history(self, session: Session, *, limit: int) -> Sequence[LayoutRevisionRow]:
        rows = session.execute(_SELECT_REVISIONS, {"key": LAYOUT_KEY, "limit": limit}).mappings().all()
        return [_revision(row) for row in rows]

    def switch_journal(self, session: Session, *, limit: int) -> Sequence[SwitchEventRow]:
        rows = session.execute(_SELECT_SWITCH_EVENTS, {"key": LAYOUT_KEY, "limit": limit}).mappings().all()
        return [SwitchEventRow(enabled=bool(row["enabled"]), set_at=row["set_at"], set_by=row["set_by"]) for row in rows]

    def append_revision(
        self, session: Session, *, kit: str, cells: Sequence[CellSettings], created_by: str,
    ) -> LayoutRevisionRow:
        import json

        session.execute(_LOCK_REVISIONS, {"key": LAYOUT_KEY})
        number = int(session.execute(_NEXT_REVISION_NO, {"key": LAYOUT_KEY}).scalar_one())
        identity = StageLayoutRevisionId.new().value
        created_at = session.execute(_INSERT_REVISION, {
            "id": identity, "key": LAYOUT_KEY, "no": number, "kit": kit, "by": created_by,
            "cells": json.dumps(cells_to_wire(cells), sort_keys=True),
        }).scalar_one()
        return LayoutRevisionRow(identity, number, kit, tuple(cells), created_at, created_by)

    def append_switch(self, session: Session, *, enabled: bool, set_by: str) -> SwitchEventRow:
        session.execute(_LOCK_SWITCH, {"key": LAYOUT_KEY})
        number = int(session.execute(_NEXT_EVENT_NO, {"key": LAYOUT_KEY}).scalar_one())
        set_at = session.execute(_INSERT_SWITCH, {
            "id": StageLayoutSwitchEventId.new().value, "key": LAYOUT_KEY, "no": number, "enabled": enabled, "by": set_by,
        }).scalar_one()
        return SwitchEventRow(enabled, set_at, set_by)
