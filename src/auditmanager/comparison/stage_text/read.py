"""Immutable, pair-scoped Stage Text evidence reads with keyset pagination."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["StageTextReadService"]

_COLUMNS = {
    "exclusions": ("stage_text_exclusion", "stage_text_exclusion_id", "left_fragment_id, right_fragment_id, proof_kind"),
    "differences": ("stage_text_difference", "stage_text_difference_id", "left_fragment_id, right_fragment_id, status"),
    "hints": ("stage_text_hint", "stage_text_hint_id", "source_fragment_id, target_fragment_id"),
}


def _missing(aggregate: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate)


def _unmaterialized() -> DomainError:
    return DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                       dependency="comparison_stage_text_evidence")


class StageTextReadService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    @staticmethod
    def _pair(session: Session, pair_id: str) -> None:
        state = session.execute(text(
            "SELECT state FROM stage_pair WHERE stage_pair_id = :pair"
        ), {"pair": pair_id}).scalar_one_or_none()
        if state is None:
            raise _missing("StagePair")
        if state != "confirmed":
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_pair_not_confirmed")

    @staticmethod
    def _revision(session: Session, revision_id: str) -> str:
        pair_id = session.execute(text(
            "SELECT stage_pair_id FROM stage_link_revision "
            "WHERE stage_link_revision_id = :revision"
        ), {"revision": revision_id}).scalar_one_or_none()
        if pair_id is None:
            raise _missing("StageLinkRevision")
        return str(pair_id)

    @staticmethod
    def _has_revision_evidence(session: Session, revision_id: str) -> bool:
        return bool(session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM stage_chain_run r JOIN command_record c "
            "ON c.command_id = r.command_id WHERE r.stage_link_revision_id = :revision "
            "AND r.state = 'completed' AND c.command_type = 'recompute_stage_text_evidence')"
        ), {"revision": revision_id}).scalar_one())

    @staticmethod
    def _page(
        session: Session, *, table: str, identity: str, columns: str,
        scope_column: str, scope_id: str, after: str | None, limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], str | None]:
        # Every interpolated identifier comes from this module's fixed table map.
        if after is not None and not session.execute(text(
            f"SELECT 1 FROM {table} WHERE {scope_column} = :scope AND content_key = :after"
        ), {"scope": scope_id, "after": after}).first():
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
        rows = [dict(row) for row in session.execute(text(
            f"SELECT {identity}, content_key, {columns} FROM {table} "
            f"WHERE {scope_column} = :scope AND (CAST(:after AS text) IS NULL OR content_key > :after) "
            "ORDER BY content_key LIMIT :limit"
        ), {"scope": scope_id, "after": after, "limit": limit + 1}).mappings()]
        visible = rows[:limit]
        next_key = visible[-1]["content_key"] if len(rows) > limit else None
        return tuple(visible), next_key

    def fragments(
        self, *, pair_id: str, after: str | None, limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], str | None]:
        with session_scope(self._sessions) as session:
            self._pair(session, pair_id)
            sealed = session.execute(text(
                "SELECT 1 FROM stage_chain_run r "
                "JOIN command_record c ON c.command_id = r.command_id "
                "WHERE r.stage_pair_id = :pair AND r.state = 'completed' "
                "AND c.command_type = 'recompute_stage_text_evidence' "
                "ORDER BY r.created_at DESC LIMIT 1"
            ), {"pair": pair_id}).scalar_one_or_none()
            if sealed is None:
                raise _unmaterialized()
            # The pair endpoint is an immutable fragment catalogue. Historical
            # revision references must remain resolvable after a new version.
            return self._page(
                session, table="stage_text_fragment", identity="stage_text_fragment_id",
                columns="page_profile_id, side, normalised_text, box_anchor",
                scope_column="stage_pair_id", scope_id=pair_id,
                after=after, limit=limit,
            )

    def revision_rows(
        self, *, kind: str, revision_id: str, after: str | None, limit: int,
    ) -> tuple[tuple[dict[str, Any], ...], str | None]:
        table, identity, columns = _COLUMNS[kind]
        with session_scope(self._sessions) as session:
            pair_id = self._revision(session, revision_id)
            self._pair(session, pair_id)
            if not self._has_revision_evidence(session, revision_id):
                raise _unmaterialized()
            return self._page(
                session, table=table, identity=identity, columns=columns,
                scope_column="stage_link_revision_id", scope_id=revision_id,
                after=after, limit=limit,
            )
