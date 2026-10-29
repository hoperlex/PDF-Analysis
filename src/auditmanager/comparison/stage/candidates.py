"""Expert decisions on validated stage PDF candidates.

Confirmation records stage, section, designation and optional existing document
identity. It moves no bytes; publication is a separate reconciled step.
"""

from __future__ import annotations

import json
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.sections.public import SECTION_CODES
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, DocumentUid, IdempotencyKey

from .uploads import StageUploadCandidateRow, StageUploadService

__all__ = ["StageCandidateDecisionService"]

_CONFIRM = "confirm_stage_upload_candidate"
_REJECT = "reject_stage_upload_candidate"


class StageCandidateDecisionService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory
        self._commands = CommandRepository()
        self._documents = DocumentRepository()

    @staticmethod
    def _row(session: Session, candidate_id: str):
        row = session.execute(
            text(
                "SELECT c.state, c.confirmed_stage, c.confirmed_section, c.designation, "
                "c.document_uid, f.state, f.stage_upload_id, u.project_uid "
                "FROM stage_upload_candidate c "
                "JOIN stage_upload_file f ON f.stage_upload_file_id = c.stage_upload_file_id "
                "JOIN stage_upload u ON u.stage_upload_id = f.stage_upload_id "
                "WHERE c.stage_upload_candidate_id = :candidate FOR UPDATE OF c, f, u"
            ), {"candidate": candidate_id},
        ).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadCandidate")
        return row

    @staticmethod
    def _view(session: Session, upload_id: str, candidate_id: str) -> StageUploadCandidateRow:
        for item in StageUploadService._read(session, upload_id).candidates:
            if item.candidate_id == candidate_id:
                return item
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageUploadCandidate")

    @staticmethod
    def _designation(value: str) -> str:
        clean = unicodedata.normalize("NFC", value).strip()
        if not 1 <= len(clean) <= 200 or any(
            unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in clean
        ):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="designation",
                constraint="stage_candidate_designation",
            )
        return clean

    def confirm(
        self, *, candidate_id: str, stage: str, section_code: str,
        designation: str, existing_document_uid: str | None,
        user_uid: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> StageUploadCandidateRow:
        require_expert(actor_roles)
        if stage not in ("P", "R"):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage", constraint="enum")
        if section_code not in SECTION_CODES:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="section_code", constraint="enum")
        shown = self._designation(designation)
        fingerprint = payload_fingerprint({
            "command": "confirm_stage_upload_candidate.v1", "candidate_id": candidate_id,
            "stage": stage, "section_code": section_code, "designation": shown,
            "existing_document_uid": existing_document_uid, "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            row = self._row(session, candidate_id)
            state, _stage, _section, _designation, _document, file_state, upload_id, project_uid = row
            claim = self._commands.begin(
                session, command_type=_CONFIRM, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._view(session, upload_id, candidate_id)
            if state != "proposed" or file_state != "ready":
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_candidate_state")
            if existing_document_uid is not None:
                document_id = DocumentUid.parse(existing_document_uid)
                if str(self._documents.require_document(session, document_id)) != project_uid:
                    raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
                placement = session.execute(
                    text("SELECT section FROM document WHERE document_uid = :document"),
                    {"document": existing_document_uid},
                ).scalar_one()
                if placement is not None and placement != section_code:
                    raise DomainError(
                        ErrorCode.VALIDATION_FAILED, field="existing_document_uid",
                        constraint="stage_candidate_existing_section",
                    )
                latest = session.execute(
                    text(
                        "SELECT c.project_stage, c.section_code FROM document_version v "
                        "JOIN version_classification_current c ON c.version_uid = v.version_uid "
                        "WHERE v.document_uid = :document ORDER BY v.version_ordinal DESC LIMIT 1"
                    ), {"document": existing_document_uid},
                ).first()
                if latest is not None and (latest[0], latest[1]) != (stage, section_code):
                    raise DomainError(
                        ErrorCode.VALIDATION_FAILED, field="existing_document_uid",
                        constraint="stage_candidate_existing_classification",
                    )
            session.execute(
                text(
                    "UPDATE stage_upload_candidate SET state = 'confirmed', "
                    "confirmed_stage = :stage, confirmed_section = :section, "
                    "designation = :designation, document_uid = :document, "
                    "confirmed_by_user_uid = :actor, confirmed_at = clock_timestamp(), "
                    "updated_at = clock_timestamp() "
                    "WHERE stage_upload_candidate_id = :candidate"
                ),
                {
                    "candidate": candidate_id, "stage": stage, "section": section_code,
                    "designation": shown, "document": existing_document_uid, "actor": user_uid,
                },
            )
            self._audit(
                session, "stage.upload_candidate_confirmed", candidate_id,
                {"stage": stage, "section_code": section_code, "designation": shown,
                 "existing_document_uid": existing_document_uid,
                 "actor_uid": user_uid, "command_id": str(claim.command_id)},
            )
            self._commands.succeed(session, claim.command_id, {"candidate_id": candidate_id})
            return self._view(session, upload_id, candidate_id)

    def reject(
        self, *, candidate_id: str, user_uid: str, actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> StageUploadCandidateRow:
        require_expert(actor_roles)
        fingerprint = payload_fingerprint({
            "command": "reject_stage_upload_candidate.v1", "candidate_id": candidate_id,
            "user_uid": user_uid,
        })
        with session_scope(self._sessions) as session:
            row = self._row(session, candidate_id)
            state, _stage, _section, _designation, _document, file_state, upload_id, _project = row
            claim = self._commands.begin(
                session, command_type=_REJECT, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=fingerprint,
            )
            if isinstance(claim, CommandReplay):
                return self._view(session, upload_id, candidate_id)
            if state != "proposed" or file_state != "ready":
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_candidate_state")
            session.execute(
                text(
                    "UPDATE stage_upload_candidate SET state = 'rejected', "
                    "updated_at = clock_timestamp() WHERE stage_upload_candidate_id = :candidate"
                ), {"candidate": candidate_id},
            )
            self._audit(
                session, "stage.upload_candidate_rejected", candidate_id,
                {"actor_uid": user_uid, "command_id": str(claim.command_id)},
            )
            self._commands.succeed(session, claim.command_id, {"candidate_id": candidate_id})
            return self._view(session, upload_id, candidate_id)

    @staticmethod
    def _audit(session: Session, kind: str, candidate_id: str, payload: dict[str, object]) -> None:
        session.execute(
            text(
                "INSERT INTO audit_event "
                "(audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
                "VALUES (:event, :kind, 'StageUploadCandidate', :candidate, CAST(:payload AS jsonb))"
            ),
            {
                "event": str(AuditEventId.new()), "kind": kind,
                "candidate": candidate_id, "payload": json.dumps(payload, sort_keys=True),
            },
        )
