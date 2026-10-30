"""Keyed, durable request for the deterministic Stage Text work item."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.modules import MODULE_STAGES
from auditmanager.comparison.stage_links.read import StageSheetReadService
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey, StageChainRunId, StageChainStepId

__all__ = ["StageTextRecomputeService", "TextRun", "TextStep", "WORK_KIND"]

WORK_KIND = "stage_text_recompute"
_COMMAND = "recompute_stage_text_evidence"
_MAX_PAGES = 512


@dataclass(frozen=True, slots=True)
class TextStep:
    step_id: str
    step_no: int
    state: str
    counts: dict[str, int]
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class TextRun:
    run_id: str
    pair_id: str
    revision_id: str
    input_sha256: str
    pinned_version_uids: tuple[str, ...]
    state: str
    steps: tuple[TextStep, ...]
    created_at: datetime
    updated_at: datetime
    stale: bool


class StageTextRecomputeService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions
        self._commands = CommandRepository()
        self._work = ComparisonWorkRepository()
        self._sheets = StageSheetReadService(sessions)

    @staticmethod
    def _row(session: Session, run_id: str) -> TextRun:
        row = session.execute(text(
            "SELECT stage_chain_run_id, stage_pair_id, stage_link_revision_id, "
            "input_sha256, pinned_version_uids, state, created_at, updated_at "
            "FROM stage_chain_run r WHERE stage_chain_run_id = :run "
            "AND EXISTS (SELECT 1 FROM command_record c WHERE c.command_id = r.command_id "
            "AND c.command_type = 'recompute_stage_text_evidence')"
        ), {"run": run_id}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainRun")
        steps = session.execute(text(
            "SELECT stage_chain_step_id, step_no, state, counts, started_at, finished_at "
            "FROM stage_chain_step WHERE stage_chain_run_id = :run ORDER BY step_no"
        ), {"run": run_id}).all()
        latest = session.execute(text(
            "SELECT stage_link_revision_id FROM stage_link_revision "
            "WHERE stage_pair_id = :pair ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": row[1]}).scalar_one_or_none()
        pins = tuple(str(uid) for uid in row[4])
        version_stale = bool(session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM document_version v "
            "WHERE v.version_uid = ANY(CAST(:pins AS text[])) "
            "AND v.version_ordinal <> (SELECT max(latest.version_ordinal) "
            "FROM document_version latest WHERE latest.document_uid = v.document_uid))"
        ), {"pins": list(pins)}).scalar_one())
        return TextRun(
            str(row[0]), str(row[1]), str(row[2]), str(row[3]), pins,
            str(row[5]), tuple(TextStep(
                str(step[0]), int(step[1]), str(step[2]), dict(step[3]),
                step[4], step[5],
            ) for step in steps), row[6], row[7],
            latest != row[2] or version_stale,
        )

    def get(self, run_id: str) -> TextRun:
        with session_scope(self._sessions) as session:
            return self._row(session, run_id)

    def start(
        self, *, revision_id: str, user_uid: str,
        actor_roles: frozenset[str], idempotency_key: str,
    ) -> TextRun:
        with session_scope(self._sessions) as session:
            return self.start_in_session(
                session, revision_id=revision_id, user_uid=user_uid,
                actor_roles=actor_roles, idempotency_key=idempotency_key,
            )

    def start_in_session(
        self, session: Session, *, revision_id: str, user_uid: str,
        actor_roles: frozenset[str], idempotency_key: str,
    ) -> TextRun:
        require_expert(actor_roles)
        command_fingerprint = payload_fingerprint({
            "command": "recompute_stage_text_evidence.v1",
            "revision_id": revision_id, "user_uid": user_uid,
        })
        claim = self._commands.begin(
            session, command_type=_COMMAND,
            idempotency_key=IdempotencyKey(idempotency_key),
            fingerprint=command_fingerprint,
        )
        if isinstance(claim, CommandReplay):
            return self._row(session, str(claim.outcome["run_id"]))
        pair_id = session.execute(text(
            "SELECT stage_pair_id FROM stage_link_revision "
            "WHERE stage_link_revision_id = :revision"
        ), {"revision": revision_id}).scalar_one_or_none()
        if pair_id is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageLinkRevision")
        session.execute(text(
            "SELECT pg_advisory_xact_lock(hashtextextended('stage_link:' || :pair, 0))"
        ), {"pair": pair_id})
        pair = session.execute(text(
            "SELECT project_uid, state FROM stage_pair WHERE stage_pair_id = :pair"
        ), {"pair": pair_id}).first()
        latest = session.execute(text(
            "SELECT stage_link_revision_id FROM stage_link_revision "
            "WHERE stage_pair_id = :pair ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": pair_id}).scalar_one_or_none()
        if pair is None or pair[1] != "confirmed" or latest != revision_id:
            raise DomainError(ErrorCode.CONFLICT,
                              conflict_reason="stage_link_revision_stale")
        live = session.execute(text(
            "SELECT r.stage_chain_run_id FROM stage_chain_run r "
            "JOIN command_record c ON c.command_id = r.command_id "
            "WHERE r.stage_link_revision_id = :revision AND r.state IN ('queued', 'running') "
            "AND c.command_type = 'recompute_stage_text_evidence' "
            "ORDER BY r.created_at DESC LIMIT 1"
        ), {"revision": revision_id}).scalar_one_or_none()
        if live is not None:
            self._commands.succeed(session, claim.command_id, {"run_id": str(live)})
            return self._row(session, str(live))
        passports = self._sheets.passports(pair_id=str(pair_id))
        if len(passports) > _MAX_PAGES:
            raise DomainError(ErrorCode.VALIDATION_FAILED,
                              field="stage_pair_id", constraint="stage_text_page_budget")
        pins = tuple(dict.fromkeys(page.version_uid for page in passports))
        if not 2 <= len(pins) <= 100:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                              dependency="comparison_stage_profiles")
        input_sha = payload_fingerprint({
            "revision_id": revision_id,
            "profiles": [page.profile_id for page in passports],
            "versions": list(pins),
        })
        run_id = str(StageChainRunId.new())
        session.execute(text(
            "INSERT INTO stage_chain_run "
            "(stage_chain_run_id, stage_pair_id, stage_link_revision_id, input_sha256, "
            "pinned_version_uids, state, actor_user_uid, command_id) "
            "VALUES (:run, :pair, :revision, :sha, CAST(:pins AS jsonb), "
            "'queued', :actor, :command)"
        ), {"run": run_id, "pair": pair_id, "revision": revision_id,
            "sha": str(input_sha), "pins": json.dumps(pins),
            "actor": user_uid, "command": str(claim.command_id)})
        for step_no in (2, 3):
            session.execute(text(
                "INSERT INTO stage_chain_step (stage_chain_step_id, stage_chain_run_id, step_no) "
                "VALUES (:step, :run, :number)"
            ), {"step": str(StageChainStepId.new()), "run": run_id,
                "number": step_no})
        self._work.enqueue(
            session, project_uid=str(pair[0]), module=MODULE_STAGES,
            kind=WORK_KIND, payload={"run_id": run_id},
            dedupe_key=f"stage_text:{run_id}",
            created_by_user_uid=user_uid,
        )
        self._commands.succeed(session, claim.command_id, {"run_id": run_id})
        return self._row(session, run_id)
