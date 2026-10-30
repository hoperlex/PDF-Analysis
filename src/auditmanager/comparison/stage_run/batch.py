"""Ordered durable batches; pausing the queue keeps its active run intact."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.ingest.public import CommandReplay, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey

from .service import BATCH_WORK_KIND, StageChainService, StagePipeline, conflict


class StageBatchService:
    def __init__(self, chains: StageChainService) -> None:
        self.chains = chains

    @staticmethod
    def _event(session: Session, batch_id: str, action: str, actor: str) -> None:
        session.execute(text(
            "INSERT INTO audit_event (audit_event_id,event_type,aggregate_type,aggregate_id,payload) "
            "VALUES (:event,:type,'StageChainBatch',:batch,CAST(:payload AS jsonb))"
        ), {"event": str(AuditEventId.new()), "type": f"stage.batch_{action}",
            "batch": batch_id, "payload": json.dumps({"actor_uid": actor})})

    @staticmethod
    def record(session: Session, batch_id: str) -> dict[str, Any]:
        row = session.execute(text(
            "SELECT stage_chain_batch_id, project_uid, state, created_at, updated_at "
            "FROM stage_chain_batch WHERE stage_chain_batch_id = :batch"
        ), {"batch": batch_id}).mappings().first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainBatch")
        items = session.execute(text(
            "SELECT stage_chain_batch_item_id, stage_pair_id, stage_link_revision_id, "
            "position, state, stage_chain_run_id FROM stage_chain_batch_item "
            "WHERE stage_chain_batch_id = :batch ORDER BY position"
        ), {"batch": batch_id}).mappings().all()
        counts = Counter(str(item["state"]) for item in items)
        return {
            "batch_id": str(row["stage_chain_batch_id"]), "project_uid": str(row["project_uid"]),
            "state": row["state"], "created_at": row["created_at"], "updated_at": row["updated_at"],
            "items": [{"item_id": str(item["stage_chain_batch_item_id"]),
                       "pair_id": str(item["stage_pair_id"]),
                       "link_revision_id": str(item["stage_link_revision_id"]),
                       "position": int(item["position"]), "state": item["state"],
                       **({"run_id": str(item["stage_chain_run_id"])}
                          if item["stage_chain_run_id"] is not None else {})} for item in items],
            "counts": {"total": len(items), **{state: counts[state] for state in
                       ("queued", "running", "completed", "failed", "cancelled")}},
        }

    def get(self, batch_id: str) -> dict[str, Any]:
        self.chains._enabled()
        with session_scope(self.chains.sessions) as session:
            return self.record(session, batch_id)

    def start(self, *, project_uid: str, selections: Sequence[Mapping[str, Any]],
              user_uid: str, actor_roles: frozenset[str], idempotency_key: str,
              with_ai: bool = True) -> dict[str, Any]:
        from auditmanager.shared.identity import StageChainBatchId, StageChainBatchItemId

        self.chains._enabled()
        require_expert(actor_roles)
        if not 1 <= len(selections) <= 100 or len({s["pair_id"] for s in selections}) != len(selections):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="selections", constraint="unique_pairs")
        payload = {"project_uid": project_uid, "selections": [dict(s) for s in selections],
                   "user_uid": user_uid, "with_ai": with_ai}
        with session_scope(self.chains.sessions) as session:
            claim = self.chains.commands.begin(session, command_type="start_stage_chain_batch",
                                               idempotency_key=IdempotencyKey(idempotency_key),
                                               fingerprint=payload_fingerprint(payload))
            if isinstance(claim, CommandReplay):
                return self.record(session, str(claim.outcome["batch_id"]))
            for selection in selections:
                pair = self.chains._pair(session, str(selection["pair_id"]))
                if pair["project_uid"] != project_uid:
                    raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StagePair")
                if self.chains._latest(session, str(selection["pair_id"])) != selection["link_revision_id"]:
                    raise conflict("stage_link_revision_stale")
                if with_ai and not selection.get("consent"):
                    raise conflict("comparison_consent_required")
            batch_id = str(StageChainBatchId.new())
            session.execute(text(
                "INSERT INTO stage_chain_batch "
                "(stage_chain_batch_id, project_uid, with_ai, actor_user_uid, command_id) "
                "VALUES (:batch, :project, :ai, :actor, :command)"
            ), {"batch": batch_id, "project": project_uid, "ai": with_ai,
                "actor": user_uid, "command": str(claim.command_id)})
            for position, selection in enumerate(selections, 1):
                session.execute(text(
                    "INSERT INTO stage_chain_batch_item "
                    "(stage_chain_batch_item_id, stage_chain_batch_id, stage_pair_id, "
                    "stage_link_revision_id, position, consent) "
                    "VALUES (:item, :batch, :pair, :revision, :position, CAST(:consent AS jsonb))"
                ), {"item": str(StageChainBatchItemId.new()), "batch": batch_id,
                    "pair": selection["pair_id"], "revision": selection["link_revision_id"],
                    "position": position, "consent": json.dumps(selection.get("consent") or {})})
            self.chains.work.enqueue(session, project_uid=project_uid, module="stages",
                                     kind=BATCH_WORK_KIND, payload={"batch_id": batch_id},
                                     dedupe_key=f"stage_batch:{batch_id}", created_by_user_uid=user_uid)
            self.chains.commands.succeed(session, claim.command_id, {"batch_id": batch_id})
            self._event(session, batch_id, "started", user_uid)
            return self.record(session, batch_id)

    def control(self, *, batch_id: str, action: str, user_uid: str,
                actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        self.chains._enabled()
        require_expert(actor_roles)
        if action not in {"pause", "resume", "cancel"}:
            raise ValueError("unknown batch action")
        with session_scope(self.chains.sessions) as session:
            claim = self.chains.commands.begin(session, command_type=f"{action}_stage_chain_batch",
                                               idempotency_key=IdempotencyKey(idempotency_key),
                                               fingerprint=payload_fingerprint({"batch_id": batch_id,
                                                                                "user_uid": user_uid}))
            if isinstance(claim, CommandReplay):
                return self.record(session, batch_id)
            row = session.execute(text(
                "SELECT state, project_uid FROM stage_chain_batch WHERE stage_chain_batch_id = :batch FOR UPDATE"
            ), {"batch": batch_id}).first()
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainBatch")
            terminal = row[0] in {"completed", "failed", "cancelled"}
            if not terminal:
                state = {"pause": "paused", "resume": "queued", "cancel": "cancelled"}[action]
                session.execute(text(
                    "UPDATE stage_chain_batch SET state = :state, updated_at = clock_timestamp() "
                    "WHERE stage_chain_batch_id = :batch"
                ), {"batch": batch_id, "state": state})
                if action == "cancel":
                    runs = session.execute(text(
                        "SELECT stage_chain_run_id FROM stage_chain_batch_item "
                        "WHERE stage_chain_batch_id = :batch AND stage_chain_run_id IS NOT NULL "
                        "AND state IN ('queued','running')"
                    ), {"batch": batch_id}).scalars().all()
                    for run_id in runs:
                        if self.chains.ai is not None:
                            self.chains.ai.cancel(session, run_id=str(run_id), user_uid=user_uid)
                        for work_id in self.chains._work_ids(session, str(run_id)):
                            self.chains.work.cancel(session, work_id)
                        session.execute(text(
                            "UPDATE stage_chain_run SET state = 'cancelled', updated_at = clock_timestamp() "
                            "WHERE stage_chain_run_id = :run AND state <> 'completed'"
                        ), {"run": run_id})
                        session.execute(text(
                            "UPDATE stage_chain_step SET state = 'cancelled', finished_at = clock_timestamp(), "
                            "updated_at = clock_timestamp() WHERE stage_chain_run_id = :run "
                            "AND state <> 'completed'"
                        ), {"run": run_id})
                    session.execute(text(
                        "UPDATE stage_chain_batch_item SET state = 'cancelled', updated_at = clock_timestamp() "
                        "WHERE stage_chain_batch_id = :batch AND state IN ('queued','running')"
                    ), {"batch": batch_id})
                if action == "resume":
                    self.chains.work.enqueue(session, project_uid=str(row[1]), module="stages",
                                             kind=BATCH_WORK_KIND, payload={"batch_id": batch_id},
                                             dedupe_key=f"stage_batch:{batch_id}", created_by_user_uid=user_uid)
            self.chains.commands.succeed(session, claim.command_id, {"batch_id": batch_id})
            self._event(session, batch_id, action, user_uid)
            return self.record(session, batch_id)


class StageBatchHandler:
    kind = BATCH_WORK_KIND

    def __init__(self, dependencies: WorkDependencies, *, ai: StagePipeline | None = None) -> None:
        self.deps = dependencies
        self.chains = StageChainService(getattr(dependencies, "session_factory", None),
                                        comparison_modules="versions,stages", ai=ai)

    def run(self, item: WorkItem) -> Outcome:
        batch_id = item.payload.get("batch_id")
        if (item.kind != self.kind or item.module != "stages" or not isinstance(batch_id, str)
                or set(item.payload) != {"batch_id"}):
            return Failed("stage_batch_payload_invalid")
        try:
            with session_scope(self.deps.session_factory) as session:
                item.require_current(session)
                batch = session.execute(text(
                    "SELECT state, project_uid, actor_user_uid, with_ai FROM stage_chain_batch "
                    "WHERE stage_chain_batch_id = :batch FOR UPDATE"
                ), {"batch": batch_id}).first()
                if batch is None or batch[1] != item.project_uid:
                    return Failed("stage_batch_scope_invalid")
                if batch[0] == "paused":
                    return Yielded(5.0)
                if batch[0] in {"completed", "failed", "cancelled"}:
                    return Completed()
                row = session.execute(text(
                    "SELECT stage_chain_batch_item_id, stage_pair_id, stage_link_revision_id, "
                    "state, stage_chain_run_id, consent FROM stage_chain_batch_item "
                    "WHERE stage_chain_batch_id = :batch AND state IN ('queued','running') "
                    "ORDER BY CASE WHEN state = 'running' THEN 0 ELSE 1 END, position LIMIT 1"
                ), {"batch": batch_id}).first()
                if row is None:
                    failed = session.execute(text(
                        "SELECT count(*) FROM stage_chain_batch_item "
                        "WHERE stage_chain_batch_id = :batch AND state = 'failed'"
                    ), {"batch": batch_id}).scalar_one()
                    session.execute(text(
                        "UPDATE stage_chain_batch SET state = :state, updated_at = clock_timestamp() "
                        "WHERE stage_chain_batch_id = :batch"
                    ), {"batch": batch_id, "state": "failed" if failed else "completed"})
                    return Completed()
                session.execute(text(
                    "UPDATE stage_chain_batch SET state = 'running', updated_at = clock_timestamp() "
                    "WHERE stage_chain_batch_id = :batch"
                ), {"batch": batch_id})
                roles = AccountRepository().roles_of(session, str(batch[2]))
            run_id = row[4]
            if run_id is None:
                with session_scope(self.deps.session_factory) as session:
                    item.require_current(session)
                    state = session.execute(text(
                        "SELECT state FROM stage_chain_batch WHERE stage_chain_batch_id = :batch "
                        "FOR NO KEY UPDATE"
                    ), {"batch": batch_id}).scalar_one()
                    if state == "paused":
                        return Yielded(5.0)
                    if state == "cancelled":
                        return Completed()
                    try:
                        run = self.chains.start(pair_id=str(row[1]), revision_id=str(row[2]),
                                                user_uid=str(batch[2]), actor_roles=roles,
                                                idempotency_key=f"stage-batch:{batch_id}:{row[0]}",
                                                with_ai=bool(batch[3]), consent=dict(row[5]) or None,
                                                batch_id=batch_id)
                    except DomainError:
                        session.execute(text(
                            "UPDATE stage_chain_batch_item SET state = 'failed', updated_at = clock_timestamp() "
                            "WHERE stage_chain_batch_item_id = :item"
                        ), {"item": row[0]})
                        return Yielded()
                    session.execute(text(
                        "UPDATE stage_chain_batch_item SET state = 'running', stage_chain_run_id = :run, "
                        "updated_at = clock_timestamp() WHERE stage_chain_batch_item_id = :item"
                    ), {"item": row[0], "run": run.run_id})
                return Yielded(2.0)
            run = self.chains.get(str(run_id))
            if run.state in {"queued", "running", "paused"}:
                return Yielded(3.0)
            with session_scope(self.deps.session_factory) as session:
                item.require_current(session)
                session.execute(text(
                    "UPDATE stage_chain_batch_item SET state = :state, updated_at = clock_timestamp() "
                    "WHERE stage_chain_batch_item_id = :item"
                ), {"item": row[0], "state": run.state if run.state in
                    {"completed", "failed", "cancelled"} else "failed"})
            return Yielded()
        except DomainError as error:
            if error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
                return Yielded()
            return Failed("stage_batch_step_failed")
