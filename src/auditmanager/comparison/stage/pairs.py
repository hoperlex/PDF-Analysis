"""Read the C3 pair catalog and derive nonbinding document suggestions.

Classification comes from the version-classification current view, including
expert corrections. A display title is only a designation hint for a suggestion;
the persisted pair always names document identities and needs expert confirmation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey, StagePairId

from .suggestions import StageDocument, StageSuggestion, suggest_stage_pairs

__all__ = ["StagePairCommandService", "StagePairReadRepository", "StagePairRow"]

_CONFIRM_COMMAND = "confirm_stage_pair"
_COMPLETENESS_COMMAND = "set_stage_pair_completeness"


@dataclass(frozen=True, slots=True)
class StagePairRow:
    pair_id: str
    project_uid: str
    left_document_uid: str
    right_document_uid: str | None
    assembly_id: str | None
    state: str
    completeness: str
    created_at: datetime
    confirmed_at: datetime | None


_PAIR_COLUMNS = (
    "stage_pair_id, project_uid, left_document_uid, right_document_uid, "
    "stage_assembly_id, state, completeness, created_at, confirmed_at"
)


def _pair(row: object) -> StagePairRow:
    return StagePairRow(*tuple(row))  # type: ignore[arg-type]


class StagePairReadRepository:
    """Explicit SQL for the stage-pair read side; no write or generic repository."""

    @staticmethod
    def require_project(session: Session, project_uid: str) -> None:
        if session.execute(
            text("SELECT 1 FROM project WHERE project_uid = :project"),
            {"project": project_uid},
        ).first() is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Project")

    @staticmethod
    def get(session: Session, pair_id: str) -> StagePairRow:
        row = session.execute(
            text(f"SELECT {_PAIR_COLUMNS} FROM stage_pair WHERE stage_pair_id = :pair"),
            {"pair": pair_id},
        ).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StagePair")
        return _pair(row)

    @staticmethod
    def page(
        session: Session, *, project_uid: str, after_pair_id: str | None, limit: int,
    ) -> tuple[tuple[StagePairRow, ...], str | None]:
        StagePairReadRepository.require_project(session, project_uid)
        rows = session.execute(
            text(
                f"SELECT {_PAIR_COLUMNS} FROM stage_pair "
                "WHERE project_uid = :project AND stage_pair_id > :after "
                "ORDER BY stage_pair_id LIMIT :take"
            ),
            {"project": project_uid, "after": after_pair_id or "", "take": limit + 1},
        ).all()
        visible = tuple(_pair(row) for row in rows[:limit])
        return visible, visible[-1].pair_id if len(rows) > limit else None

    @staticmethod
    def suggestions(session: Session, *, project_uid: str) -> tuple[StageSuggestion, ...]:
        StagePairReadRepository.require_project(session, project_uid)
        rows = session.execute(
            text(
                "SELECT d.document_uid, c.project_stage, c.section_code, "
                "COALESCE(stage_name.designation, legacy_name.designation, d.display_title), "
                "CASE WHEN stage_name.designation IS NOT NULL OR legacy_name.designation IS NOT NULL "
                "THEN 'confirmed' ELSE 'title' END "
                "FROM document d "
                "JOIN LATERAL (SELECT v.version_uid FROM document_version v "
                "WHERE v.document_uid = d.document_uid ORDER BY v.version_ordinal DESC LIMIT 1) latest ON TRUE "
                "JOIN version_classification_current c ON c.version_uid = latest.version_uid "
                "LEFT JOIN LATERAL (SELECT candidate.designation FROM stage_upload_candidate candidate "
                "WHERE candidate.document_uid = d.document_uid AND candidate.state = 'published' "
                "AND candidate.designation IS NOT NULL "
                "ORDER BY candidate.confirmed_at DESC LIMIT 1) stage_name ON TRUE "
                "LEFT JOIN LATERAL (SELECT upload_set.designation FROM comparison_upload_set upload_set "
                "WHERE upload_set.document_uid = d.document_uid AND upload_set.state = 'done' "
                "AND upload_set.designation IS NOT NULL "
                "ORDER BY upload_set.confirmed_at DESC LIMIT 1) legacy_name ON TRUE "
                "WHERE d.project_uid = :project ORDER BY d.document_uid"
            ),
            {"project": project_uid},
        ).all()
        documents = tuple(StageDocument(*tuple(row)) for row in rows)
        bound: set[str] = set()
        for left, right in session.execute(
            text(
                "SELECT left_document_uid, right_document_uid FROM stage_pair "
                "WHERE project_uid = :project AND state = 'confirmed'"
            ),
            {"project": project_uid},
        ):
            bound.add(left)
            if right is not None:
                bound.add(right)
        for (document_uid,) in session.execute(
            text(
                "SELECT m.document_uid FROM stage_assembly_member m "
                "JOIN stage_pair p ON p.stage_assembly_id = m.stage_assembly_id "
                "WHERE p.project_uid = :project AND p.state = 'confirmed' "
                "AND m.action = 'add' AND NOT EXISTS ("
                "SELECT 1 FROM stage_assembly_member r "
                "WHERE r.reverses_member_id = m.stage_assembly_member_id AND r.action = 'remove')"
            ),
            {"project": project_uid},
        ):
            bound.add(document_uid)
        return suggest_stage_pairs(documents, bound_document_uids=frozenset(bound))


def _classification(session: Session, *, project_uid: str, document_uid: str) -> tuple[str, str]:
    row = session.execute(
        text(
            "SELECT c.project_stage, c.section_code FROM document d "
            "JOIN LATERAL (SELECT v.version_uid FROM document_version v "
            "WHERE v.document_uid = d.document_uid ORDER BY v.version_ordinal DESC LIMIT 1) latest ON TRUE "
            "JOIN version_classification_current c ON c.version_uid = latest.version_uid "
            "WHERE d.project_uid = :project AND d.document_uid = :document"
        ),
        {"project": project_uid, "document": document_uid},
    ).first()
    if row is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageDocument")
    return str(row[0]), str(row[1])


class StagePairCommandService:
    """One keyed expert binding; suggestions never call this command themselves."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory
        self._reads = StagePairReadRepository()
        self._commands = CommandRepository()

    def confirm_pair(
        self, *, project_uid: str, left_document_uid: str,
        right_document_uid: str | None, assembly_id: str | None,
        user_uid: str, idempotency_key: str,
    ) -> StagePairRow:
        if (right_document_uid is None) == (assembly_id is None):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="right_document_uid",
                constraint="exactly_one_right_document_or_assembly",
            )
        fingerprint = payload_fingerprint({
            "command": "confirm_stage_pair.v1", "project_uid": project_uid,
            "left_document_uid": left_document_uid,
            "right_document_uid": right_document_uid, "assembly_id": assembly_id,
            "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            self._reads.require_project(session, project_uid)
            claim = self._commands.begin(
                session, command_type=_CONFIRM_COMMAND,
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._reads.get(session, str(claim.outcome["pair_id"]))
            # One active binding of a П document in a project. The project-scoped
            # transaction lock serializes two experts confirming at once.
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": f"stage_pair:{project_uid}"},
            )
            left_stage, section = _classification(
                session, project_uid=project_uid, document_uid=left_document_uid,
            )
            if left_stage != "P":
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="left_document_uid",
                    constraint="stage_pair_left_is_P",
                )
            if right_document_uid is not None:
                right_stage, right_section = _classification(
                    session, project_uid=project_uid, document_uid=right_document_uid,
                )
                if right_stage != "R" or right_section != section:
                    raise DomainError(
                        ErrorCode.VALIDATION_FAILED, field="right_document_uid",
                        constraint="stage_pair_right_is_R_same_section",
                    )
            else:
                assert assembly_id is not None
                if session.execute(
                    text(
                        "SELECT 1 FROM stage_assembly WHERE stage_assembly_id = :assembly "
                        "AND project_uid = :project"
                    ),
                    {"assembly": assembly_id, "project": project_uid},
                ).first() is None:
                    raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageAssembly")
                members = session.execute(
                    text(
                        "SELECT m.document_uid FROM stage_assembly_member m "
                        "WHERE m.stage_assembly_id = :assembly AND m.action = 'add' "
                        "AND NOT EXISTS (SELECT 1 FROM stage_assembly_member r "
                        "WHERE r.reverses_member_id = m.stage_assembly_member_id AND r.action = 'remove')"
                    ),
                    {"assembly": assembly_id},
                ).scalars().all()
                if len(members) < 2:
                    raise DomainError(
                        ErrorCode.VALIDATION_FAILED, field="assembly_id",
                        constraint="stage_pair_assembly_at_least_two",
                    )
                for document_uid in members:
                    stage, member_section = _classification(
                        session, project_uid=project_uid, document_uid=str(document_uid),
                    )
                    if stage != "R" or member_section != section:
                        raise DomainError(
                            ErrorCode.VALIDATION_FAILED, field="assembly_id",
                            constraint="stage_pair_assembly_R_same_section",
                        )
            if session.execute(
                text(
                    "SELECT 1 FROM stage_pair WHERE project_uid = :project "
                    "AND left_document_uid = :left AND state = 'confirmed'"
                ),
                {"project": project_uid, "left": left_document_uid},
            ).first() is not None:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_pair_left_already_bound")
            pair_id = str(StagePairId.new())
            session.execute(
                text(
                    "INSERT INTO stage_pair "
                    "(stage_pair_id, project_uid, left_document_uid, right_document_uid, "
                    "stage_assembly_id, state, confirmed_by_user_uid, command_id, confirmed_at) "
                    "VALUES (:pair, :project, :left, :right, :assembly, 'confirmed', "
                    ":actor, :command, clock_timestamp())"
                ),
                {
                    "pair": pair_id, "project": project_uid, "left": left_document_uid,
                    "right": right_document_uid, "assembly": assembly_id,
                    "actor": user_uid, "command": str(claim.command_id),
                },
            )
            self._commands.succeed(session, claim.command_id, {"pair_id": pair_id})
            return self._reads.get(session, pair_id)

    def set_completeness(
        self, *, pair_id: str, completeness: str, user_uid: str,
        idempotency_key: str,
    ) -> StagePairRow:
        if completeness not in ("full", "partial"):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="completeness",
                constraint="stage_pair_completeness_choice",
            )
        fingerprint = payload_fingerprint({
            "command": "set_stage_pair_completeness.v1", "pair_id": pair_id,
            "completeness": completeness, "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            row = session.execute(
                text(
                    "SELECT state, completeness FROM stage_pair "
                    "WHERE stage_pair_id = :pair FOR UPDATE"
                ),
                {"pair": pair_id},
            ).first()
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StagePair")
            claim = self._commands.begin(
                session, command_type=_COMPLETENESS_COMMAND,
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._reads.get(session, pair_id)
            if row[0] != "confirmed":
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_pair_not_confirmed")
            previous = str(row[1])
            if previous != completeness:
                session.execute(
                    text(
                        "UPDATE stage_pair SET completeness = :value "
                        "WHERE stage_pair_id = :pair"
                    ),
                    {"pair": pair_id, "value": completeness},
                )
                session.execute(
                    text(
                        "INSERT INTO audit_event "
                        "(audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
                        "VALUES (:event, 'stage.pair_completeness_changed', 'StagePair', "
                        ":pair, CAST(:payload AS jsonb))"
                    ),
                    {
                        "event": str(AuditEventId.new()), "pair": pair_id,
                        "payload": json.dumps({
                            "actor_uid": user_uid, "from": previous, "to": completeness,
                            "command_id": str(claim.command_id),
                        }, sort_keys=True),
                    },
                )
            self._commands.succeed(session, claim.command_id, {"pair_id": pair_id})
            return self._reads.get(session, pair_id)
