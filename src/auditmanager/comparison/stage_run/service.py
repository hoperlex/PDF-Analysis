"""Expert commands for pinned seven-step stage comparisons."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.modules import enabled_modules
from auditmanager.comparison.stage_links.read import StageSheetReadService
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey, StageChainRunId, StageChainStepId

WORK_KIND = "stage_chain"
BATCH_WORK_KIND = "stage_chain_batch"


class StagePipeline(Protocol):
    def estimate(self, *, revision_id: str, user_uid: str) -> Any: ...
    def prepare(self, session: Session, *, run_id: str, user_uid: str,
                consent: Mapping[str, Any]) -> str | None: ...
    def resume(self, session: Session, *, run_id: str, user_uid: str,
               consent: Mapping[str, Any] | None) -> None: ...
    def cancel(self, session: Session, *, run_id: str, user_uid: str) -> None: ...
    def advance(self, item: Any, *, run_id: str, phase: str) -> Any: ...


@dataclass(frozen=True, slots=True)
class RunStep:
    step_id: str
    step_no: int
    state: str
    counts: dict[str, int]
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class ChainRun:
    run_id: str
    pair_id: str
    revision_id: str
    effective_revision_id: str | None
    input_sha256: str
    pinned_version_uids: tuple[str, ...]
    state: str
    steps: tuple[RunStep, ...]
    created_at: datetime
    updated_at: datetime
    stale: bool
    kind: str
    with_ai: bool
    ai_job_id: str | None
    pause_reason: str | None
    repair_cycle_count: int


def conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


class StageChainService:
    def __init__(self, sessions: sessionmaker[Session], *, comparison_modules: str = "none",
                 ai: StagePipeline | None = None) -> None:
        self.sessions = sessions
        self.modules = enabled_modules(comparison_modules)
        self.ai = ai
        self.commands = CommandRepository()
        self.work = ComparisonWorkRepository()
        self.sheets = StageSheetReadService(sessions)

    def _enabled(self) -> None:
        if "stages" not in self.modules:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_modules")

    @staticmethod
    def _pair(session: Session, pair_id: str) -> Mapping[str, Any]:
        pair = session.execute(text(
            "SELECT stage_pair_id, project_uid, state FROM stage_pair WHERE stage_pair_id = :pair"
        ), {"pair": pair_id}).mappings().first()
        if pair is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StagePair")
        if pair["state"] != "confirmed":
            raise conflict("stage_pair_not_confirmed")
        return pair

    @staticmethod
    def _latest(session: Session, pair_id: str) -> str | None:
        value = session.execute(text(
            "SELECT stage_link_revision_id FROM stage_link_revision WHERE stage_pair_id = :pair "
            "ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": pair_id}).scalar_one_or_none()
        return None if value is None else str(value)

    @staticmethod
    def _current_versions(session: Session, pair_id: str) -> tuple[str, ...]:
        left, right = StageSheetReadService._documents(session, pair_id)
        versions = []
        for document in (left, *right):
            uid = session.execute(text(
                "SELECT version_uid FROM document_version WHERE document_uid = :document "
                "ORDER BY version_ordinal DESC LIMIT 1"
            ), {"document": document}).scalar_one_or_none()
            if uid is not None:
                versions.append(str(uid))
        return tuple(versions)

    @classmethod
    def record(cls, session: Session, run_id: str) -> ChainRun:
        row = session.execute(text(
            "SELECT stage_chain_run_id, stage_pair_id, stage_link_revision_id, "
            "effective_link_revision_id, input_sha256, pinned_version_uids, state, "
            "created_at, updated_at, kind, with_ai, comparison_ai_job_id, pause_reason, "
            "repair_cycle_count FROM stage_chain_run WHERE stage_chain_run_id = :run"
        ), {"run": run_id}).mappings().first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainRun")
        steps = session.execute(text(
            "SELECT stage_chain_step_id, step_no, state, counts, started_at, finished_at "
            "FROM stage_chain_step WHERE stage_chain_run_id = :run ORDER BY step_no"
        ), {"run": run_id}).all()
        pins = tuple(str(uid) for uid in row["pinned_version_uids"])
        effective = row["effective_link_revision_id"] or row["stage_link_revision_id"]
        stale = (cls._latest(session, row["stage_pair_id"]) != effective
                 or cls._current_versions(session, row["stage_pair_id"]) != pins)
        return ChainRun(
            str(row["stage_chain_run_id"]), str(row["stage_pair_id"]),
            str(row["stage_link_revision_id"]), row["effective_link_revision_id"],
            str(row["input_sha256"]), pins, str(row["state"]),
            tuple(RunStep(str(step[0]), int(step[1]), str(step[2]), dict(step[3]),
                          step[4], step[5]) for step in steps),
            row["created_at"], row["updated_at"], stale, str(row["kind"]),
            bool(row["with_ai"]), row["comparison_ai_job_id"], row["pause_reason"],
            int(row["repair_cycle_count"]),
        )

    @staticmethod
    def _event(session: Session, run_id: str, event: str, payload: Mapping[str, Any]) -> None:
        session.execute(text(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
            "VALUES (:id, :event, 'StageChainRun', :run, CAST(:payload AS jsonb))"
        ), {"id": str(AuditEventId.new()), "event": event, "run": run_id,
            "payload": json.dumps(dict(payload), sort_keys=True)})

    def estimate(self, *, pair_id: str, revision_id: str, user_uid: str) -> Any:
        self._enabled()
        with session_scope(self.sessions) as session:
            self._pair(session, pair_id)
            if self._latest(session, pair_id) != revision_id:
                raise conflict("stage_link_revision_stale")
        if self.ai is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_ai")
        return self.ai.estimate(revision_id=revision_id, user_uid=user_uid)

    def start(self, *, pair_id: str, revision_id: str, user_uid: str,
              actor_roles: frozenset[str], idempotency_key: str,
              with_ai: bool = True, consent: Mapping[str, Any] | None = None,
              restart: bool = False, batch_id: str | None = None) -> ChainRun:
        self._enabled()
        require_expert(actor_roles)
        payload = {"pair_id": pair_id, "revision_id": revision_id,
                   "user_uid": user_uid, "with_ai": with_ai, "consent": dict(consent or {}),
                   "restart": restart, "batch_id": batch_id}
        with session_scope(self.sessions) as session:
            claim = self.commands.begin(session, command_type="start_stage_chain_run",
                                        idempotency_key=IdempotencyKey(idempotency_key),
                                        fingerprint=payload_fingerprint(payload))
            if isinstance(claim, CommandReplay):
                return self.record(session, str(claim.outcome["run_id"]))
            session.execute(text(
                "SELECT pg_advisory_xact_lock(hashtextextended('stage_link:' || :pair, 0))"
            ), {"pair": pair_id})
            pair = self._pair(session, pair_id)
            if self._latest(session, pair_id) != revision_id:
                raise conflict("stage_link_revision_stale")
            live = session.execute(text(
                "SELECT stage_chain_run_id FROM stage_chain_run WHERE stage_pair_id = :pair "
                "AND kind = 'full' AND state IN ('queued', 'running', 'paused') "
                "ORDER BY created_at DESC LIMIT 1"
            ), {"pair": pair_id}).scalar_one_or_none()
            if live is not None:
                existing = self.record(session, str(live))
                if restart or existing.stale or existing.with_ai != with_ai:
                    raise conflict("stage_chain_run_active")
                self.commands.succeed(session, claim.command_id, {"run_id": existing.run_id})
                return existing
            passports = self.sheets.passports(pair_id=pair_id)
            pins = tuple(dict.fromkeys(page.version_uid for page in passports))
            if not 2 <= len(pins) <= 100:
                raise conflict("stage_chain_version_pins_invalid")
            if with_ai and (self.ai is None or consent is None):
                raise conflict("comparison_consent_required")
            run_id = str(StageChainRunId.new())
            input_sha = payload_fingerprint({"revision_id": revision_id,
                                             "profiles": [p.profile_id for p in passports],
                                             "versions": list(pins), "with_ai": with_ai})
            session.execute(text(
                "INSERT INTO stage_chain_run "
                "(stage_chain_run_id, stage_pair_id, stage_link_revision_id, input_sha256, "
                "pinned_version_uids, actor_user_uid, command_id, kind, with_ai, stage_chain_batch_id) "
                "VALUES (:run, :pair, :revision, :sha, CAST(:pins AS jsonb), :actor, :command, "
                "'full', :with_ai, :batch)"
            ), {"run": run_id, "pair": pair_id, "revision": revision_id,
                "sha": str(input_sha), "pins": json.dumps(pins), "actor": user_uid,
                "command": str(claim.command_id), "with_ai": with_ai, "batch": batch_id})
            for step_no in range(1, 8):
                session.execute(text(
                    "INSERT INTO stage_chain_step (stage_chain_step_id, stage_chain_run_id, step_no) "
                    "VALUES (:step, :run, :number)"
                ), {"step": str(StageChainStepId.new()), "run": run_id, "number": step_no})
            job_id = None
            if with_ai:
                assert self.ai is not None and consent is not None
                job_id = self.ai.prepare(session, run_id=run_id, user_uid=user_uid, consent=consent)
                session.execute(text(
                    "UPDATE stage_chain_run SET comparison_ai_job_id = :job WHERE stage_chain_run_id = :run"
                ), {"run": run_id, "job": job_id})
            self.work.enqueue(session, project_uid=str(pair["project_uid"]), module="stages",
                              kind=WORK_KIND, payload={"run_id": run_id,
                                  **({"ai_job_id": job_id} if job_id else {})},
                              comparison_ai_job_id=job_id,
                              dedupe_key=f"stage_chain:{run_id}", created_by_user_uid=user_uid)
            self._event(session, run_id, "stage.chain_started",
                        {"actor_uid": user_uid, "command_id": str(claim.command_id),
                         "revision_id": revision_id, "with_ai": with_ai})
            self.commands.succeed(session, claim.command_id, {"run_id": run_id})
            return self.record(session, run_id)

    def get(self, run_id: str) -> ChainRun:
        self._enabled()
        with session_scope(self.sessions) as session:
            return self.record(session, run_id)

    def page(self, *, pair_id: str, after: str | None, limit: int) -> tuple[tuple[ChainRun, ...], str | None]:
        self._enabled()
        with session_scope(self.sessions) as session:
            self._pair(session, pair_id)
            if after is not None and self.record(session, after).pair_id != pair_id:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="scope")
            rows = session.execute(text(
                "SELECT stage_chain_run_id FROM stage_chain_run WHERE stage_pair_id = :pair "
                "AND (CAST(:after AS text) IS NULL OR stage_chain_run_id < :after) "
                "ORDER BY stage_chain_run_id DESC LIMIT :limit"
            ), {"pair": pair_id, "after": after, "limit": limit + 1}).scalars().all()
            return tuple(self.record(session, str(uid)) for uid in rows[:limit]), (
                str(rows[limit - 1]) if len(rows) > limit else None
            )

    def _work_ids(self, session: Session, run_id: str) -> tuple[str, ...]:
        children = session.execute(text(
            "SELECT outcome->>'run_id' FROM command_record WHERE command_type = "
            "'recompute_stage_text_evidence' AND idempotency_key LIKE :prefix "
            "AND state = 'succeeded'"
        ), {"prefix": f"stage-chain-text:{run_id}:%"}).scalars().all()
        ids = session.execute(text(
            "SELECT comparison_work_id FROM comparison_work WHERE module = 'stages' "
            "AND payload->>'run_id' = ANY(CAST(:runs AS text[])) "
            "AND state NOT IN ('succeeded', 'failed', 'cancelled')"
        ), {"runs": [run_id, *(str(uid) for uid in children if uid)]}).scalars().all()
        return tuple(str(uid) for uid in ids)

    def cancel(self, *, run_id: str, user_uid: str, actor_roles: frozenset[str],
               idempotency_key: str) -> ChainRun:
        self._enabled()
        require_expert(actor_roles)
        with session_scope(self.sessions) as session:
            claim = self.commands.begin(session, command_type="cancel_stage_chain_run",
                                        idempotency_key=IdempotencyKey(idempotency_key),
                                        fingerprint=payload_fingerprint({"run_id": run_id, "user_uid": user_uid}))
            if isinstance(claim, CommandReplay):
                return self.record(session, run_id)
            session.execute(text("SELECT stage_chain_run_id FROM stage_chain_run "
                                 "WHERE stage_chain_run_id = :run FOR UPDATE"), {"run": run_id})
            record = self.record(session, run_id)
            if record.state not in {"completed", "cancelled"}:
                if record.with_ai and self.ai is not None:
                    self.ai.cancel(session, run_id=run_id, user_uid=user_uid)
                for work_id in self._work_ids(session, run_id):
                    self.work.cancel(session, work_id)
                session.execute(text(
                    "UPDATE stage_chain_run SET state = 'cancelled', updated_at = clock_timestamp() "
                    "WHERE stage_chain_run_id = :run"
                ), {"run": run_id})
                session.execute(text(
                    "UPDATE stage_chain_step SET state = 'cancelled', finished_at = clock_timestamp(), "
                    "updated_at = clock_timestamp() WHERE stage_chain_run_id = :run "
                    "AND state <> 'completed'"
                ), {"run": run_id})
                self._event(session, run_id, "stage.chain_cancelled", {"actor_uid": user_uid})
            self.commands.succeed(session, claim.command_id, {"run_id": run_id})
            return self.record(session, run_id)

    def resume(self, *, run_id: str, user_uid: str, actor_roles: frozenset[str],
               idempotency_key: str, consent: Mapping[str, Any] | None = None,
               retry_failed: bool = False) -> ChainRun:
        self._enabled()
        require_expert(actor_roles)
        payload = {"run_id": run_id, "user_uid": user_uid,
                   "consent": dict(consent or {}), "retry_failed": retry_failed}
        with session_scope(self.sessions) as session:
            claim = self.commands.begin(session, command_type="resume_stage_chain_run",
                                        idempotency_key=IdempotencyKey(idempotency_key),
                                        fingerprint=payload_fingerprint(payload))
            if isinstance(claim, CommandReplay):
                return self.record(session, run_id)
            session.execute(text("SELECT stage_chain_run_id FROM stage_chain_run "
                                 "WHERE stage_chain_run_id = :run FOR UPDATE"), {"run": run_id})
            record = self.record(session, run_id)
            if record.stale:
                raise conflict("stage_chain_run_stale")
            if record.state == "completed":
                self.commands.succeed(session, claim.command_id, {"run_id": run_id})
                return record
            if record.state == "failed" and not retry_failed:
                raise conflict("stage_chain_retry_required")
            if record.with_ai:
                if self.ai is None:
                    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_ai")
                self.ai.resume(session, run_id=run_id, user_uid=user_uid, consent=consent)
            session.execute(text(
                "UPDATE stage_chain_step SET state = 'queued', failure_reason = NULL, "
                "finished_at = NULL, updated_at = clock_timestamp() "
                "WHERE stage_chain_run_id = :run AND state IN ('paused','failed','cancelled','running')"
            ), {"run": run_id})
            session.execute(text(
                "UPDATE stage_chain_run SET state = 'queued', failure_reason = NULL, "
                "pause_reason = NULL, updated_at = clock_timestamp() WHERE stage_chain_run_id = :run"
            ), {"run": run_id})
            work_ids = self._work_ids(session, run_id)
            has_chain_work = False
            for work_id in work_ids:
                state, kind = session.execute(text(
                    "SELECT state, kind FROM comparison_work WHERE comparison_work_id = :work"
                ), {"work": work_id}).one()
                has_chain_work = has_chain_work or kind == WORK_KIND
                if state == "paused":
                    self.work.resume(session, work_id)
            if not has_chain_work:
                project = self._pair(session, record.pair_id)["project_uid"]
                self.work.enqueue(session, project_uid=str(project), module="stages", kind=WORK_KIND,
                                  payload={"run_id": run_id, **({"ai_job_id": record.ai_job_id}
                                           if record.ai_job_id else {})},
                                  comparison_ai_job_id=record.ai_job_id,
                                  dedupe_key=f"stage_chain:{run_id}",
                                  created_by_user_uid=user_uid)
            self._event(session, run_id, "stage.chain_resumed", {"actor_uid": user_uid})
            self.commands.succeed(session, claim.command_id, {"run_id": run_id})
            return self.record(session, run_id)
