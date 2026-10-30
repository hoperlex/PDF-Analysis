"""One durable seven-step chain advances one step and yields to other work."""

from __future__ import annotations

import json
from typing import Any, Mapping, Protocol

from sqlalchemy import text

from auditmanager.access.public import AccountRepository
from auditmanager.comparison.stage_text.recompute import StageTextRecomputeService
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .service import ChainRun, StageChainService, StagePipeline, WORK_KIND


class StageAction(Protocol):
    def advance(self, item: WorkItem, *, run_id: str) -> Mapping[str, int] | Outcome: ...


class _Cancelled(Exception):
    pass


class StageChainHandler:
    kind = WORK_KIND

    def __init__(self, dependencies: WorkDependencies, *, ai: StagePipeline | None = None,
                 repair: StageAction | None = None, review: StageAction | None = None,
                 graphics: StageAction | None = None) -> None:
        self.deps = dependencies
        self.service = StageChainService(getattr(dependencies, "session_factory", None),
                                         comparison_modules="versions,stages", ai=ai)
        self.text = StageTextRecomputeService(getattr(dependencies, "session_factory", None))
        self.ai, self.repair, self.review, self.graphics = ai, repair, review, graphics

    def _authority(self, session: Any, item: WorkItem, run_id: str) -> None:
        item.require_current(session)
        row = session.execute(text(
            "SELECT r.state, p.project_uid FROM stage_chain_run r "
            "JOIN stage_pair p ON p.stage_pair_id = r.stage_pair_id "
            "WHERE r.stage_chain_run_id = :run"
        ), {"run": run_id}).first()
        if row is None or row[1] != item.project_uid:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainRun")
        if row[0] == "cancelled" or self.deps.work.cancel_requested(session, item.work_id):
            raise _Cancelled()

    def _state(self, item: WorkItem, run_id: str, state: str, reason: str | None = None,
               *, step_no: int | None = None) -> None:
        with session_scope(self.deps.session_factory) as session:
            self._authority(session, item, run_id)
            session.execute(text(
                "UPDATE stage_chain_run SET state = :state, pause_reason = :pause, "
                "failure_reason = :failure, updated_at = clock_timestamp() "
                "WHERE stage_chain_run_id = :run"
            ), {"run": run_id, "state": state,
                "pause": reason if state == "paused" else None,
                "failure": reason if state == "failed" else None})
            if step_no is not None:
                session.execute(text(
                    "UPDATE stage_chain_step SET state = :state, failure_reason = :reason, "
                    "started_at = coalesce(started_at, clock_timestamp()), "
                    "finished_at = CASE WHEN :state IN ('failed','completed') "
                    "THEN clock_timestamp() ELSE finished_at END, updated_at = clock_timestamp() "
                    "WHERE stage_chain_run_id = :run AND step_no = :step"
                ), {"run": run_id, "step": step_no, "state": state, "reason": reason})

    def _finish(self, item: WorkItem, run_id: str, step_no: int,
                counts: Mapping[str, int]) -> None:
        safe = {str(key): int(value) for key, value in counts.items()
                if isinstance(value, int) and not isinstance(value, bool)}
        with session_scope(self.deps.session_factory) as session:
            self._authority(session, item, run_id)
            session.execute(text(
                "UPDATE stage_chain_step SET state = 'completed', counts = CAST(:counts AS jsonb), "
                "failure_reason = NULL, started_at = coalesce(started_at, clock_timestamp()), "
                "finished_at = clock_timestamp(), updated_at = clock_timestamp() "
                "WHERE stage_chain_run_id = :run AND step_no = :step"
            ), {"run": run_id, "step": step_no, "counts": json.dumps(safe)})

    def _ai_phase(self, item: WorkItem, record: ChainRun, step_no: int, phase: str) -> Any:
        if not record.with_ai:
            return {"skipped": 1}
        if self.ai is None:
            self._state(item, record.run_id, "paused", "comparison_stage_ai_unavailable",
                        step_no=step_no)
            return Completed()
        result = self.ai.advance(item, run_id=record.run_id, phase=phase)
        if isinstance(result, Yielded) and record.ai_job_id is not None:
            with session_scope(self.deps.session_factory) as session:
                job = session.execute(text(
                    "SELECT state, pause_reason FROM comparison_ai_job WHERE comparison_ai_job_id = :job"
                ), {"job": record.ai_job_id}).first()
            if job is not None and job[0] == "paused":
                self._state(item, record.run_id, "paused", str(job[1] or "comparison_ai_paused"),
                            step_no=step_no)
                return Completed()
        return result

    def _deterministic(self, item: WorkItem, record: ChainRun) -> Outcome:
        with session_scope(self.deps.session_factory) as session:
            self._authority(session, item, record.run_id)
            actor = session.execute(text(
                "SELECT actor_user_uid FROM stage_chain_run WHERE stage_chain_run_id = :run"
            ), {"run": record.run_id}).scalar_one()
            roles = AccountRepository().roles_of(session, str(actor))
        revision = record.effective_revision_id or record.revision_id
        child = self.text.start(
            revision_id=revision, user_uid=str(actor), actor_roles=roles,
            idempotency_key=f"stage-chain-text:{record.run_id}:{revision}",
        )
        if child.state in {"queued", "running"}:
            return Yielded(2.0)
        if child.state != "completed":
            self._state(item, record.run_id, "failed", "stage_chain_text_failed", step_no=2)
            return Failed("stage_chain_text_failed")
        for step in child.steps:
            if step.step_no != 3 or self.graphics is None:
                self._finish(item, record.run_id, step.step_no, step.counts)
        if self.graphics is not None:
            result = self.graphics.advance(item, run_id=record.run_id)
            if isinstance(result, Failed):
                self._state(item, record.run_id, "failed", result.reason, step_no=3)
                return result
            if isinstance(result, (Completed, Yielded)):
                return result
            self._finish(item, record.run_id, 3, {
                **next((step.counts for step in child.steps if step.step_no == 3), {}),
                **dict(result),
            })
        return Yielded()

    def run(self, item: WorkItem) -> Outcome:
        run_id = item.payload.get("run_id")
        if (item.kind != self.kind or item.module != "stages" or "run_id" not in item.payload
                or set(item.payload) - {"run_id", "ai_job_id"}):
            return Failed("stage_chain_payload_invalid")
        if not isinstance(run_id, str):
            return Failed("stage_chain_payload_invalid")
        record: ChainRun | None = None
        step_no: int | None = None
        try:
            with session_scope(self.deps.session_factory) as session:
                self._authority(session, item, run_id)
                record = self.service.record(session, run_id)
            if record.kind != "full":
                return Failed("stage_chain_run_kind_invalid")
            if item.payload.get("ai_job_id") != record.ai_job_id:
                return Failed("stage_chain_ai_job_scope_invalid")
            if record.state == "completed":
                return Completed()
            if record.state in {"paused", "failed"}:
                return Completed()
            if record.stale:
                self._state(item, run_id, "paused", "stage_chain_run_stale")
                return Completed()
            next_step = next((step for step in record.steps if step.state != "completed"), None)
            if next_step is None:
                self._state(item, run_id, "completed")
                return Completed()
            step_no = next_step.step_no
            self._state(item, run_id, "running", step_no=step_no)
            result: Any
            if step_no == 1:
                with session_scope(self.deps.session_factory) as session:
                    count = session.execute(text(
                        "SELECT count(*) FROM stage_link_item WHERE stage_link_revision_id = :revision"
                    ), {"revision": record.effective_revision_id or record.revision_id}).scalar_one()
                result = {"links": int(count)}
            elif step_no in {2, 3}:
                return self._deterministic(item, record)
            elif step_no == 4:
                result = self._ai_phase(item, record, step_no, "review")
            elif step_no == 5:
                result = self._ai_phase(item, record, step_no, "classify")
                if isinstance(result, Mapping) and self.repair is not None:
                    repaired = self.repair.advance(item, run_id=run_id)
                    if isinstance(repaired, (Completed, Failed, Yielded)):
                        return repaired
                    if repaired.get("recompute", 0):
                        return Yielded()
                    result = {**dict(result), **dict(repaired)}
            elif step_no == 6:
                result = self._ai_phase(item, record, step_no, "synthesize")
            else:
                if self.review is None:
                    self._state(item, run_id, "paused", "comparison_stage_review_unavailable",
                                step_no=step_no)
                    return Completed()
                result = self.review.advance(item, run_id=run_id)
            if isinstance(result, Failed):
                self._state(item, run_id, "failed", result.reason, step_no=step_no)
                return result
            if isinstance(result, (Completed, Yielded)):
                return result
            self._finish(item, run_id, step_no, result)
            return Yielded()
        except _Cancelled:
            return Yielded()
        except DomainError as error:
            if error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
                return Yielded()
            if record is None:
                return Failed("stage_chain_run_not_found")
            try:
                self._state(item, run_id, "failed", "stage_chain_step_failed", step_no=step_no)
            except _Cancelled:
                return Yielded()
            return Failed("stage_chain_step_failed")
