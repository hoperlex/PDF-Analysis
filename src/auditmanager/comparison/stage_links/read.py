"""Current page passports of a confirmed stage pair, from frozen profile summaries."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .passports import SheetPassport, from_stamp
from .suggestions import SheetSuggestion, suggest_sheets

__all__ = ["StageSheetReadService"]


class StageSheetReadService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    @staticmethod
    def _documents(session: Session, pair_id: str) -> tuple[str, tuple[str, ...]]:
        pair = session.execute(text(
            "SELECT left_document_uid, right_document_uid, stage_assembly_id, state "
            "FROM stage_pair WHERE stage_pair_id = :pair"
        ), {"pair": pair_id}).first()
        if pair is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StagePair")
        if pair[3] != "confirmed":
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_pair_not_confirmed")
        if pair[1] is not None:
            return str(pair[0]), (str(pair[1]),)
        members = session.execute(text(
            "SELECT m.document_uid FROM stage_assembly_member m "
            "WHERE m.stage_assembly_id = :assembly AND m.action = 'add' "
            "AND NOT EXISTS (SELECT 1 FROM stage_assembly_member r "
            "WHERE r.reverses_member_id = m.stage_assembly_member_id "
            "AND r.action = 'remove') ORDER BY m.member_no"
        ), {"assembly": str(pair[2])}).scalars().all()
        if not members:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_assembly",
            )
        return str(pair[0]), tuple(str(member) for member in members)

    @staticmethod
    def _version_profiles(
        session: Session, *, document_uid: str, side: str,
    ) -> tuple[SheetPassport, ...]:
        from auditmanager.comparison.public import PAGE_PROFILE_ALGO_VERSION

        version = session.execute(text(
            "SELECT version_uid, page_count FROM document_version "
            "WHERE document_uid = :document ORDER BY version_ordinal DESC LIMIT 1"
        ), {"document": document_uid}).first()
        if version is None:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_profiles",
            )
        rows = session.execute(text(
            "SELECT comparison_page_profile_id, page_number, status, profile "
            "FROM comparison_page_profile WHERE version_uid = :version "
            "AND algo_version = :algo ORDER BY page_number"
        ), {"version": str(version[0]), "algo": PAGE_PROFILE_ALGO_VERSION}).all()
        if len(rows) != int(version[1]) or any(
            int(row[1]) != number or row[2] != "ready"
            for number, row in enumerate(rows, 1)
        ):
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_profiles",
            )
        passports = []
        for profile_id, page_number, _status, summary in rows:
            stamp = summary.get("stamp", {}) if isinstance(summary, dict) else {}
            if not isinstance(stamp, dict):
                stamp = {}
            passports.append(from_stamp(
                profile_id=str(profile_id), version_uid=str(version[0]),
                page_number=int(page_number), side=side,
                sheet_title=stamp.get("sheet_name") if isinstance(stamp.get("sheet_name"), str) else None,
                sheet_number=stamp.get("sheet_number") if isinstance(stamp.get("sheet_number"), str) else None,
            ))
        return tuple(passports)

    def passports(self, *, pair_id: str) -> tuple[SheetPassport, ...]:
        with session_scope(self._sessions) as session:
            left, right = self._documents(session, pair_id)
            return self._version_profiles(session, document_uid=left, side="left") + tuple(
                passport
                for document in right
                for passport in self._version_profiles(session, document_uid=document, side="right")
            )

    def suggestions(self, *, pair_id: str) -> tuple[SheetSuggestion, ...]:
        passports = self.passports(pair_id=pair_id)
        return suggest_sheets(
            tuple(page for page in passports if page.side == "left"),
            tuple(page for page in passports if page.side == "right"),
        )
