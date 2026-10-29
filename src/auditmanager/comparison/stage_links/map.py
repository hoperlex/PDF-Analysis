"""Expert-owned, append-only complete sheet-map revisions for a confirmed stage pair."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AuditEventId, IdempotencyKey, StageLinkItemId, StageLinkRevisionId,
)

__all__ = ["LinkInput", "LinkItem", "LinkRevision", "StageSheetMapService"]

_COMMAND = "apply_stage_sheet_map"


@dataclass(frozen=True, slots=True)
class LinkInput:
    relation: str
    left_profile_id: str | None
    right_profile_id: str | None


@dataclass(frozen=True, slots=True)
class LinkItem:
    item_id: str
    row_no: int
    relation: str
    confidence: str
    left_profile_id: str | None
    right_profile_id: str | None


@dataclass(frozen=True, slots=True)
class LinkRevision:
    revision_id: str
    pair_id: str
    revision_no: int
    base_revision_id: str | None
    source: str
    input_sha256: str
    items: tuple[LinkItem, ...]
    created_at: datetime


class StageSheetMapService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions
        self._commands = CommandRepository()

    @staticmethod
    def _require_pair(session: Session, pair_id: str) -> None:
        row = session.execute(text(
            "SELECT state FROM stage_pair WHERE stage_pair_id = :pair"
        ), {"pair": pair_id}).scalar_one_or_none()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StagePair")
        if row != "confirmed":
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_pair_not_confirmed")

    @staticmethod
    def _revision(session: Session, revision_id: str) -> LinkRevision:
        row = session.execute(text(
            "SELECT stage_link_revision_id, stage_pair_id, revision_no, base_revision_id, "
            "source, input_sha256, created_at FROM stage_link_revision "
            "WHERE stage_link_revision_id = :revision"
        ), {"revision": revision_id}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageLinkRevision")
        items = session.execute(text(
            "SELECT stage_link_item_id, row_no, relation, confidence, "
            "left_profile_id, right_profile_id FROM stage_link_item "
            "WHERE stage_link_revision_id = :revision ORDER BY row_no"
        ), {"revision": revision_id}).all()
        return LinkRevision(
            str(row[0]), str(row[1]), int(row[2]),
            None if row[3] is None else str(row[3]), str(row[4]), str(row[5]),
            tuple(LinkItem(str(item[0]), int(item[1]), str(item[2]), str(item[3]),
                           None if item[4] is None else str(item[4]),
                           None if item[5] is None else str(item[5])) for item in items),
            row[6],
        )

    @staticmethod
    def _latest(session: Session, pair_id: str) -> tuple[str, int] | None:
        row = session.execute(text(
            "SELECT stage_link_revision_id, revision_no FROM stage_link_revision "
            "WHERE stage_pair_id = :pair ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": pair_id}).first()
        return None if row is None else (str(row[0]), int(row[1]))

    @staticmethod
    def _validate_items(items: tuple[LinkInput, ...]) -> None:
        if not 1 <= len(items) <= 1000:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="items", constraint="stage_link_item_count",
            )
        seen: set[tuple[str | None, str | None]] = set()
        paired_left: set[str] = set()
        paired_right: set[str] = set()
        unpaired_left: set[str] = set()
        unpaired_right: set[str] = set()
        for item in items:
            valid = (
                (item.relation == "paired" and item.left_profile_id is not None
                 and item.right_profile_id is not None)
                or (item.relation == "only_left" and item.left_profile_id is not None
                    and item.right_profile_id is None)
                or (item.relation == "only_right" and item.left_profile_id is None
                    and item.right_profile_id is not None)
            )
            if not valid:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="items", constraint="stage_link_relation",
                )
            key = (item.left_profile_id, item.right_profile_id)
            if key in seen:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="items", constraint="stage_link_duplicate",
                )
            seen.add(key)
            if item.relation == "paired":
                assert item.left_profile_id is not None and item.right_profile_id is not None
                paired_left.add(item.left_profile_id)
                paired_right.add(item.right_profile_id)
            elif item.relation == "only_left":
                assert item.left_profile_id is not None
                unpaired_left.add(item.left_profile_id)
            else:
                assert item.right_profile_id is not None
                unpaired_right.add(item.right_profile_id)
        if paired_left & unpaired_left or paired_right & unpaired_right:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="items", constraint="stage_link_unpaired_conflict",
            )

    @staticmethod
    def _require_profile(session: Session, pair_id: str, profile_id: str, side: str) -> None:
        from auditmanager.comparison.public import PAGE_PROFILE_ALGO_VERSION

        exists = session.execute(text(
            "SELECT 1 FROM comparison_page_profile pp "
            "JOIN document_version v ON v.version_uid = pp.version_uid "
            "WHERE pp.comparison_page_profile_id = :profile AND pp.status = 'ready' "
            "AND pp.algo_version = :algo "
            "AND v.version_ordinal = (SELECT max(latest.version_ordinal) "
            "FROM document_version latest WHERE latest.document_uid = v.document_uid) "
            "AND am_stage_profile_in_pair(:pair, :profile, :side)"
        ), {
            "pair": pair_id, "profile": profile_id, "side": side,
            "algo": PAGE_PROFILE_ALGO_VERSION,
        }).first()
        if exists is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="PageProfile")

    def apply(
        self, *, pair_id: str, base_revision_id: str | None,
        items: tuple[LinkInput, ...], user_uid: str, actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> LinkRevision:
        require_expert(actor_roles)
        self._validate_items(items)
        payload = {
            "command": "apply_stage_sheet_map.v1", "pair_id": pair_id,
            "base_revision_id": base_revision_id, "user_uid": user_uid,
            "items": [
                [item.relation, item.left_profile_id, item.right_profile_id]
                for item in items
            ],
        }
        fingerprint = payload_fingerprint(payload)
        with session_scope(self._sessions) as session:
            self._require_pair(session, pair_id)
            claim = self._commands.begin(
                session, command_type=_COMMAND,
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._revision(session, str(claim.outcome["revision_id"]))
            session.execute(text(
                "SELECT pg_advisory_xact_lock(hashtextextended(:lock, 0))"
            ), {"lock": f"stage_link:{pair_id}"})
            latest = self._latest(session, pair_id)
            if (None if latest is None else latest[0]) != base_revision_id:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_link_revision_stale")
            prior_items = () if latest is None else self._revision(session, latest[0]).items
            for item in items:
                if item.left_profile_id is not None:
                    self._require_profile(session, pair_id, item.left_profile_id, "left")
                if item.right_profile_id is not None:
                    self._require_profile(session, pair_id, item.right_profile_id, "right")
            revision_id = str(StageLinkRevisionId.new())
            session.execute(text(
                "INSERT INTO stage_link_revision (stage_link_revision_id, stage_pair_id, "
                "revision_no, base_revision_id, source, input_sha256, actor_user_uid, command_id) "
                "VALUES (:revision, :pair, :number, :base, 'expert', :sha, :actor, :command)"
            ), {
                "revision": revision_id, "pair": pair_id,
                "number": 1 if latest is None else latest[1] + 1,
                "base": base_revision_id, "sha": str(fingerprint),
                "actor": user_uid, "command": str(claim.command_id),
            })
            for number, item in enumerate(items, 1):
                prior = prior_items[number - 1] if number <= len(prior_items) else None
                unchanged = (
                    prior is not None and prior.relation == item.relation
                    and prior.left_profile_id == item.left_profile_id
                    and prior.right_profile_id == item.right_profile_id
                )
                session.execute(text(
                    "INSERT INTO stage_link_item "
                    "(stage_link_item_id, stage_link_revision_id, row_no, left_profile_id, "
                    "right_profile_id, relation, confidence) "
                    "VALUES (:item, :revision, :number, :left, :right, :relation, :confidence)"
                ), {
                    "item": str(StageLinkItemId.new()), "revision": revision_id,
                    "number": number, "left": item.left_profile_id,
                    "right": item.right_profile_id, "relation": item.relation,
                    "confidence": prior.confidence if unchanged else (
                        "manual" if item.relation == "paired" else "unpaired"
                    ),
                })
            session.execute(text(
                "INSERT INTO audit_event "
                "(audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
                "VALUES (:event, 'stage.sheet_map_applied', 'StagePair', :pair, "
                "CAST(:payload AS jsonb))"
            ), {
                "event": str(AuditEventId.new()), "pair": pair_id,
                "payload": json.dumps({
                    "actor_uid": user_uid, "command_id": str(claim.command_id),
                    "revision_id": revision_id, "base_revision_id": base_revision_id,
                    "item_count": len(items),
                }, sort_keys=True),
            })
            self._commands.succeed(session, claim.command_id, {"revision_id": revision_id})
            return self._revision(session, revision_id)

    def current(self, *, pair_id: str) -> LinkRevision:
        with session_scope(self._sessions) as session:
            self._require_pair(session, pair_id)
            latest = self._latest(session, pair_id)
            if latest is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageLinkRevision")
            return self._revision(session, latest[0])

    def get(self, *, revision_id: str) -> LinkRevision:
        with session_scope(self._sessions) as session:
            return self._revision(session, revision_id)

    def page(
        self, *, pair_id: str, after_revision_no: int | None, limit: int,
    ) -> tuple[tuple[LinkRevision, ...], int | None]:
        with session_scope(self._sessions) as session:
            self._require_pair(session, pair_id)
            rows = session.execute(text(
                "SELECT stage_link_revision_id, revision_no FROM stage_link_revision "
                "WHERE stage_pair_id = :pair AND "
                "(CAST(:after AS integer) IS NULL OR revision_no < CAST(:after AS integer)) "
                "ORDER BY revision_no DESC LIMIT :take"
            ), {"pair": pair_id, "after": after_revision_no, "take": limit + 1}).all()
            visible = tuple(self._revision(session, str(row[0])) for row in rows[:limit])
            return visible, int(rows[limit - 1][1]) if len(rows) > limit else None
