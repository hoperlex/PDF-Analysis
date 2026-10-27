"""The only reader and writer of ``analysis_preset_revision`` (migration ``0037``).

Statements only: no rule lives here (``presets.py`` and ``preset_commands.py`` own them). Every
method takes the caller's session and never commits.

The table is append-only, so the *current* revision of a preset is a query -- its highest
``revision_no`` -- and a preset's list is one pass over those. :meth:`PresetStore.lock` takes the same
advisory lock the schema's chain trigger takes, so a writer that has read the current revision cannot
have it moved under it before its INSERT (the application role holds no UPDATE privilege on the
table and so no row lock to lean on).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.presets import PresetRecord, RunPresetRecord

__all__ = ["PresetStore"]

_LOCK_KEY: Final[str] = "analysis_preset_revision"
_COLUMNS: Final[str] = (
    "r.preset_id, r.preset_revision_id AS revision_id, r.revision_no, r.state, r.name, r.executor_connection_id, "
    "f.created_at AS created_at, r.created_at AS revised_at, r.created_by AS revised_by"
)
_FROM: Final[str] = (
    "FROM analysis_preset_revision r "
    "JOIN analysis_preset_revision f ON f.preset_id = r.preset_id AND f.revision_no = 1"
)
_CURRENT: Final[str] = (
    "r.revision_no = (SELECT max(x.revision_no) FROM analysis_preset_revision x "
    "WHERE x.preset_id = r.preset_id)"
)


def _record(row: Mapping[str, Any]) -> PresetRecord:
    return PresetRecord(**{name: row[name] for name in (
        "preset_id", "revision_id", "revision_no", "state", "name", "executor_connection_id",
        "created_at", "revised_at", "revised_by")})


class PresetStore:
    """Stateless."""

    def lock(self, session: Session) -> None:
        """Serialise the writers of the preset family until the transaction ends."""
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": _LOCK_KEY}
        )

    def insert_revision(
        self, session: Session, *, revision_id: str, preset_id: str, revision_no: int,
        state: str, name: str, executor_connection_id: str, actor_uid: str,
    ) -> PresetRecord:
        session.execute(text(
            "INSERT INTO analysis_preset_revision (preset_revision_id, preset_id, revision_no, state, "
            "name, executor_connection_id, created_by) VALUES (:revision_id, :preset_id, "
            ":revision_no, :state, :name, :connection, :actor)"
        ), {"revision_id": revision_id, "preset_id": preset_id, "revision_no": revision_no,
            "state": state, "name": name, "connection": executor_connection_id,
            "actor": actor_uid})
        stored = self.revision(session, revision_id)
        assert stored is not None  # the row was just written by this transaction
        return stored

    def revision(self, session: Session, revision_id: str) -> PresetRecord | None:
        """One revision as it was written (not necessarily the current one)."""
        row = session.execute(text(
            f"SELECT {_COLUMNS} {_FROM} WHERE r.preset_revision_id = :id"
        ), {"id": revision_id}).mappings().first()
        return None if row is None else _record(row)

    def current(self, session: Session, preset_id: str) -> PresetRecord | None:
        """The highest-numbered revision of a preset, or ``None`` when no such preset exists."""
        row = session.execute(text(
            f"SELECT {_COLUMNS} {_FROM} WHERE r.preset_id = :id AND {_CURRENT}"
        ), {"id": preset_id}).mappings().first()
        return None if row is None else _record(row)

    def list_current(self, session: Session) -> list[PresetRecord]:
        """Every preset, archived ones included: active first by name, then archived by name."""
        rows = session.execute(text(
            f"SELECT {_COLUMNS} {_FROM} WHERE {_CURRENT} "
            "ORDER BY (r.state = 'archived'), lower(r.name), r.preset_id"
        )).mappings().all()
        return [_record(row) for row in rows]

    def count_presets(self, session: Session) -> int:
        return int(session.execute(text(
            "SELECT count(*) FROM analysis_preset_revision WHERE revision_no = 1"
        )).scalar_one())

    def run_preset(self, session: Session, revision_id: str) -> RunPresetRecord | None:
        """The preset a run recorded, with the name and revision number it had then."""
        row = session.execute(text(
            "SELECT preset_id, revision_no, name FROM analysis_preset_revision "
            "WHERE preset_revision_id = :id"
        ), {"id": revision_id}).mappings().first()
        return None if row is None else RunPresetRecord(
            preset_id=row["preset_id"], revision_no=row["revision_no"], name=row["name"])
