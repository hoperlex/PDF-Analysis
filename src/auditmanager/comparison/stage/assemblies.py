"""Keyed creation and readback of a Р-side document assembly.

Each membership event has its own command record because `0041` requires a
unique command ID for every append-only member row. The request's command and
all derived member commands commit in one database transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    IdempotencyKey,
    StageAssemblyId,
    StageAssemblyMemberId,
)

from .pairs import StagePairReadRepository, _classification

__all__ = ["StageAssemblyMemberRow", "StageAssemblyRow", "StageAssemblyService"]

_CREATE_COMMAND = "create_stage_assembly"
_ADD_COMMAND = "stage_assembly_member_add"
_REVISE_COMMAND = "revise_stage_assembly"
_REMOVE_COMMAND = "stage_assembly_member_remove"


@dataclass(frozen=True, slots=True)
class StageAssemblyMemberRow:
    document_uid: str
    member_no: int


@dataclass(frozen=True, slots=True)
class StageAssemblyRow:
    assembly_id: str
    project_uid: str
    label: str
    members: tuple[StageAssemblyMemberRow, ...]
    created_at: datetime


class StageAssemblyService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory
        self._commands = CommandRepository()

    @staticmethod
    def read(session: Session, assembly_id: str) -> StageAssemblyRow:
        row = session.execute(
            text(
                "SELECT stage_assembly_id, project_uid, label, created_at "
                "FROM stage_assembly WHERE stage_assembly_id = :assembly"
            ),
            {"assembly": assembly_id},
        ).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageAssembly")
        members = session.execute(
            text(
                "SELECT m.document_uid, m.member_no FROM stage_assembly_member m "
                "WHERE m.stage_assembly_id = :assembly AND m.action = 'add' "
                "AND NOT EXISTS (SELECT 1 FROM stage_assembly_member r "
                "WHERE r.reverses_member_id = m.stage_assembly_member_id AND r.action = 'remove') "
                "ORDER BY m.member_no"
            ),
            {"assembly": assembly_id},
        ).all()
        return StageAssemblyRow(
            assembly_id=str(row[0]), project_uid=str(row[1]), label=str(row[2]),
            members=tuple(StageAssemblyMemberRow(str(doc), int(no)) for doc, no in members),
            created_at=row[3],
        )

    def create(
        self, *, project_uid: str, label: str, document_uids: tuple[str, ...],
        user_uid: str, idempotency_key: str,
    ) -> StageAssemblyRow:
        if not 2 <= len(document_uids) <= 100 or len(set(document_uids)) != len(document_uids):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="document_uids",
                constraint="stage_assembly_unique_2_to_100_R_documents",
            )
        fingerprint = payload_fingerprint({
            "command": "create_stage_assembly.v1", "project_uid": project_uid,
            "label": label, "document_uids": list(document_uids), "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            StagePairReadRepository.require_project(session, project_uid)
            claim = self._commands.begin(
                session, command_type=_CREATE_COMMAND,
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self.read(session, str(claim.outcome["assembly_id"]))
            section: str | None = None
            for document_uid in document_uids:
                stage, current_section = _classification(
                    session, project_uid=project_uid, document_uid=document_uid,
                )
                if stage != "R" or (section is not None and current_section != section):
                    raise DomainError(
                        ErrorCode.VALIDATION_FAILED, field="document_uids",
                        constraint="stage_assembly_R_same_section",
                    )
                section = current_section
            assembly_id = str(StageAssemblyId.new())
            session.execute(
                text(
                    "INSERT INTO stage_assembly "
                    "(stage_assembly_id, project_uid, label, actor_user_uid, command_id) "
                    "VALUES (:assembly, :project, :label, :actor, :command)"
                ),
                {
                    "assembly": assembly_id, "project": project_uid, "label": label,
                    "actor": user_uid, "command": str(claim.command_id),
                },
            )
            for member_no, document_uid in enumerate(document_uids, 1):
                member_claim = self._commands.begin(
                    session, command_type=_ADD_COMMAND,
                    idempotency_key=IdempotencyKey(f"member-{claim.command_id}-{member_no}"),
                    fingerprint=payload_fingerprint({
                        "assembly_id": assembly_id, "member_no": member_no,
                        "document_uid": document_uid,
                    }),
                )
                if isinstance(member_claim, CommandReplay):
                    raise RuntimeError("a fresh assembly member command already exists")
                member_id = str(StageAssemblyMemberId.new())
                session.execute(
                    text(
                        "INSERT INTO stage_assembly_member "
                        "(stage_assembly_member_id, stage_assembly_id, member_no, document_uid, "
                        "action, actor_user_uid, command_id) "
                        "VALUES (:member, :assembly, :member_no, :document, 'add', :actor, :command)"
                    ),
                    {
                        "member": member_id, "assembly": assembly_id,
                        "member_no": member_no, "document": document_uid,
                        "actor": user_uid, "command": str(member_claim.command_id),
                    },
                )
                self._commands.succeed(session, member_claim.command_id, {"member_id": member_id})
            self._commands.succeed(session, claim.command_id, {"assembly_id": assembly_id})
            return self.read(session, assembly_id)

    def revise(
        self, *, assembly_id: str, base_member_no: int,
        add_document_uids: tuple[str, ...], remove_document_uids: tuple[str, ...],
        user_uid: str, idempotency_key: str,
    ) -> StageAssemblyRow:
        if (len(add_document_uids) > 100 or len(remove_document_uids) > 100
                or len(set(add_document_uids)) != len(add_document_uids)
                or len(set(remove_document_uids)) != len(remove_document_uids)
                or set(add_document_uids) & set(remove_document_uids)):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="document_uids",
                constraint="stage_assembly_revision_distinct_members",
            )
        if not add_document_uids and not remove_document_uids:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="document_uids",
                constraint="stage_assembly_revision_has_change",
            )
        fingerprint = payload_fingerprint({
            "command": "revise_stage_assembly.v1", "assembly_id": assembly_id,
            "base_member_no": base_member_no,
            "add_document_uids": list(add_document_uids),
            "remove_document_uids": list(remove_document_uids), "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            # The row lock serializes membership edits and protects base_member_no.
            assembly = session.execute(
                text(
                    "SELECT project_uid FROM stage_assembly "
                    "WHERE stage_assembly_id = :assembly FOR UPDATE"
                ),
                {"assembly": assembly_id},
            ).first()
            if assembly is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageAssembly")
            project_uid = str(assembly[0])
            claim = self._commands.begin(
                session, command_type=_REVISE_COMMAND,
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self.read(session, str(claim.outcome["assembly_id"]))
            current_no = int(session.execute(
                text(
                    "SELECT COALESCE(max(member_no), 0) FROM stage_assembly_member "
                    "WHERE stage_assembly_id = :assembly"
                ),
                {"assembly": assembly_id},
            ).scalar_one())
            if base_member_no != current_no:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_assembly_stale")
            active_rows = session.execute(
                text(
                    "SELECT m.stage_assembly_member_id, m.document_uid "
                    "FROM stage_assembly_member m "
                    "WHERE m.stage_assembly_id = :assembly AND m.action = 'add' "
                    "AND NOT EXISTS (SELECT 1 FROM stage_assembly_member r "
                    "WHERE r.reverses_member_id = m.stage_assembly_member_id AND r.action = 'remove')"
                ),
                {"assembly": assembly_id},
            ).all()
            active = {str(document): str(member) for member, document in active_rows}
            if not set(remove_document_uids) <= active.keys() or set(add_document_uids) & active.keys():
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="document_uids",
                    constraint="stage_assembly_revision_membership",
                )
            final = (active.keys() - set(remove_document_uids)) | set(add_document_uids)
            if not 2 <= len(final) <= 100:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="document_uids",
                    constraint="stage_assembly_2_to_100_R_documents",
                )
            sections = {
                _classification(session, project_uid=project_uid, document_uid=doc)
                for doc in final
            }
            if len(sections) != 1 or next(iter(sections))[0] != "R":
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="document_uids",
                    constraint="stage_assembly_R_same_section",
                )
            changes = (
                [("remove", doc, active[doc]) for doc in remove_document_uids]
                + [("add", doc, None) for doc in add_document_uids]
            )
            for member_no, (action, document_uid, reverses) in enumerate(changes, current_no + 1):
                command_type = _ADD_COMMAND if action == "add" else _REMOVE_COMMAND
                member_claim = self._commands.begin(
                    session, command_type=command_type,
                    idempotency_key=IdempotencyKey(f"member-{claim.command_id}-{member_no}"),
                    fingerprint=payload_fingerprint({
                        "assembly_id": assembly_id, "member_no": member_no,
                        "document_uid": document_uid, "action": action,
                    }),
                )
                if isinstance(member_claim, CommandReplay):
                    raise RuntimeError("a fresh assembly member command already exists")
                member_id = str(StageAssemblyMemberId.new())
                session.execute(
                    text(
                        "INSERT INTO stage_assembly_member "
                        "(stage_assembly_member_id, stage_assembly_id, member_no, document_uid, "
                        "action, reverses_member_id, actor_user_uid, command_id) "
                        "VALUES (:member, :assembly, :no, :document, :action, :reverses, :actor, :command)"
                    ),
                    {
                        "member": member_id, "assembly": assembly_id, "no": member_no,
                        "document": document_uid, "action": action, "reverses": reverses,
                        "actor": user_uid, "command": str(member_claim.command_id),
                    },
                )
                self._commands.succeed(session, member_claim.command_id, {"member_id": member_id})
            self._commands.succeed(session, claim.command_id, {"assembly_id": assembly_id})
            return self.read(session, assembly_id)
