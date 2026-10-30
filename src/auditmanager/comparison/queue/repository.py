"""Only writer of ``comparison_launch_queue`` and ``comparison_launch_entry``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import ComparisonLaunchEntryId


class LaunchQueueRepository:
    def queue(self, session: Session, project_uid: str, *, lock: bool = False) -> Mapping[str, Any] | None:
        suffix = " FOR UPDATE" if lock else ""
        row = session.execute(text(
            "SELECT project_uid, paused, failure_reason, created_at, updated_at "
            "FROM comparison_launch_queue WHERE project_uid = :project" + suffix
        ), {"project": project_uid}).mappings().first()
        return None if row is None else dict(row)

    def ensure_queue(self, session: Session, project_uid: str) -> Mapping[str, Any]:
        session.execute(text(
            "INSERT INTO comparison_launch_queue (project_uid) VALUES (:project) ON CONFLICT DO NOTHING"
        ), {"project": project_uid})
        row = self.queue(session, project_uid, lock=True)
        assert row is not None
        return row

    def entries(self, session: Session, project_uid: str, *, lock: bool = False) -> list[dict[str, Any]]:
        suffix = " FOR UPDATE" if lock else ""
        rows = session.execute(text(
            "SELECT comparison_launch_entry_id, project_uid, document_uid, step, state, position, restart, reason, "
            "consent_digest, comparison_ai_job_id, comparison_series_id, actor_user_uid, actor_label, command_id, "
            "created_at, updated_at FROM comparison_launch_entry WHERE project_uid = :project "
            "ORDER BY position, comparison_launch_entry_id" + suffix
        ), {"project": project_uid}).mappings()
        return [dict(row) for row in rows]

    def entry(self, session: Session, entry_id: str, *, lock: bool = False) -> Mapping[str, Any] | None:
        suffix = " FOR UPDATE" if lock else ""
        row = session.execute(text(
            "SELECT comparison_launch_entry_id, project_uid, document_uid, step, state, position, restart, reason, "
            "consent_digest, comparison_ai_job_id, comparison_series_id, actor_user_uid, actor_label, command_id, "
            "created_at, updated_at FROM comparison_launch_entry WHERE comparison_launch_entry_id = :entry" + suffix
        ), {"entry": entry_id}).mappings().first()
        return None if row is None else dict(row)

    def insert_entries(
        self, session: Session, *, project_uid: str, selected: Sequence[Mapping[str, Any]],
        restart: bool, actor_user_uid: str, actor_label: str, command_id: str,
    ) -> None:
        position = session.execute(text(
            "SELECT coalesce(max(position), 0) FROM comparison_launch_entry WHERE project_uid = :project"
        ), {"project": project_uid}).scalar_one()
        for item in selected:
            position += 1
            session.execute(text(
                "INSERT INTO comparison_launch_entry (comparison_launch_entry_id, project_uid, document_uid, step, position, "
                "restart, consent_digest, actor_user_uid, actor_label, command_id) VALUES "
                "(:entry, :project, :document, :step, :position, :restart, :consent, :actor, :label, :command)"
            ), {
                "entry": str(ComparisonLaunchEntryId.new()), "project": project_uid, "document": item["document_uid"],
                "step": item["step"], "position": position, "restart": restart,
                "consent": item.get("consent_digest"), "actor": actor_user_uid, "label": actor_label,
                "command": command_id,
            })

    def set_queue(self, session: Session, project_uid: str, *, paused: bool, failure_reason: str | None = None) -> None:
        session.execute(text(
            "UPDATE comparison_launch_queue SET paused = :paused, failure_reason = :reason, "
            "updated_at = statement_timestamp() WHERE project_uid = :project"
        ), {"project": project_uid, "paused": paused, "reason": failure_reason})

    def move(self, session: Session, entry_id: str, *, from_state: str, to_state: str,
             reason: str | None = None, job_id: str | None = None, series_id: str | None = None) -> bool:
        changed = session.execute(text(
            "UPDATE comparison_launch_entry SET state = :to_state, reason = :reason, "
            "comparison_ai_job_id = coalesce(:job_id, comparison_ai_job_id), "
            "comparison_series_id = coalesce(:series_id, comparison_series_id), "
            "updated_at = statement_timestamp() WHERE comparison_launch_entry_id = :entry AND state = :from_state"
        ), {"entry": entry_id, "from_state": from_state, "to_state": to_state, "reason": reason,
            "job_id": job_id, "series_id": series_id}).rowcount
        return changed == 1

    def attach(self, session: Session, entry_id: str, *, job_id: str | None = None, series_id: str | None = None) -> None:
        session.execute(text(
            "UPDATE comparison_launch_entry SET comparison_ai_job_id = coalesce(:job_id, comparison_ai_job_id), "
            "comparison_series_id = coalesce(:series_id, comparison_series_id), updated_at = statement_timestamp() "
            "WHERE comparison_launch_entry_id = :entry AND state = 'running'"
        ), {"entry": entry_id, "job_id": job_id, "series_id": series_id})

    def attach_waiting_series(self, session: Session, entry_id: str, series_id: str) -> bool:
        """Freeze the series used for consent before a waiting AI step advances."""
        return session.execute(text(
            "UPDATE comparison_launch_entry SET comparison_series_id = :series_id, "
            "updated_at = statement_timestamp() WHERE comparison_launch_entry_id = :entry "
            "AND state = 'waiting' AND step IN ('ai_changes', 'report') "
            "AND (comparison_series_id IS NULL OR comparison_series_id = :series_id)"
        ), {"entry": entry_id, "series_id": series_id}).rowcount == 1

    def delete_not_running(self, session: Session, project_uid: str) -> None:
        session.execute(text(
            "DELETE FROM comparison_launch_entry WHERE project_uid = :project AND state <> 'running'"
        ), {"project": project_uid})

    def delete_entry(self, session: Session, entry_id: str, *, states: tuple[str, ...]) -> bool:
        return session.execute(text(
            "DELETE FROM comparison_launch_entry WHERE comparison_launch_entry_id = :entry "
            "AND state = ANY (CAST(:states AS text[]))"
        ), {"entry": entry_id, "states": list(states)}).rowcount == 1
