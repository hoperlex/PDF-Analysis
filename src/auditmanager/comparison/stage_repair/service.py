"""Recorded automatic map revisions and expert undo; all evidence stays immutable."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.stage_links.read import StageSheetReadService
from auditmanager.comparison.stage_text.recompute import StageTextRecomputeService
from auditmanager.comparison.work.model import WorkItem
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey, StageLinkItemId, StageLinkRevisionId

from .planner import plan_repairs
from .purpose import normalize_title, precheck_purpose
from .types import ContentScore, MapLink, RepairRefused, SheetTitle


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


class StageRepairService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions
        self.commands = CommandRepository()

    @staticmethod
    def _snapshot(session: Session, revision_id: str) -> tuple[MapLink, ...]:
        rows = session.execute(text(
            "SELECT i.stage_link_item_id, i.left_profile_id, i.right_profile_id, "
            "i.relation, i.confidence, r.source FROM stage_link_item i "
            "JOIN stage_link_revision r USING(stage_link_revision_id) "
            "WHERE i.stage_link_revision_id = :revision ORDER BY i.row_no"
        ), {"revision": revision_id}).all()
        return tuple(MapLink(str(row[0]), row[1], row[2], str(row[3]), str(row[4]), str(row[5]))
                     for row in rows)

    @staticmethod
    def _latest(session: Session, pair_id: str) -> tuple[str, int, str]:
        row = session.execute(text(
            "SELECT stage_link_revision_id, revision_no, source FROM stage_link_revision "
            "WHERE stage_pair_id = :pair ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": pair_id}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageLinkRevision")
        return str(row[0]), int(row[1]), str(row[2])

    @staticmethod
    def _revision(session: Session, *, pair_id: str, base: str, number: int,
                  actor: str, command_id: str, source: str,
                  snapshot: Sequence[MapLink], digest: str) -> tuple[str, tuple[MapLink, ...]]:
        revision_id = str(StageLinkRevisionId.new())
        session.execute(text(
            "INSERT INTO stage_link_revision "
            "(stage_link_revision_id, stage_pair_id, revision_no, base_revision_id, source, "
            "input_sha256, actor_user_uid, command_id) "
            "VALUES (:revision, :pair, :number, :base, :source, :sha, :actor, :command)"
        ), {"revision": revision_id, "pair": pair_id, "number": number,
            "base": base, "source": source, "sha": digest,
            "actor": actor, "command": command_id})
        stored = []
        for row_no, row in enumerate(snapshot, 1):
            item_id = str(StageLinkItemId.new())
            session.execute(text(
                "INSERT INTO stage_link_item "
                "(stage_link_item_id, stage_link_revision_id, row_no, left_profile_id, "
                "right_profile_id, relation, confidence) "
                "VALUES (:item, :revision, :number, :left, :right, :relation, :confidence)"
            ), {"item": item_id, "revision": revision_id, "number": row_no,
                "left": row.left_profile_id, "right": row.right_profile_id,
                "relation": row.relation, "confidence": row.confidence})
            stored.append(MapLink(item_id, row.left_profile_id, row.right_profile_id,
                                  row.relation, row.confidence, source))
        return revision_id, tuple(stored)

    @staticmethod
    def _event(session: Session, repair_id: str, action: str, actor: str,
               command: str, revision: str, recompute: str | None = None) -> None:
        from auditmanager.shared.identity import StageLinkRepairEventId

        session.execute(text(
            "INSERT INTO stage_link_repair_event "
            "(stage_link_repair_event_id, stage_link_repair_id, action, actor_user_uid, "
            "command_id, revision_id, recompute_run_id) "
            "VALUES (:event, :repair, :action, :actor, :command, :revision, :recompute)"
        ), {"event": str(StageLinkRepairEventId.new()), "repair": repair_id,
            "action": action, "actor": actor, "command": command,
            "revision": revision, "recompute": recompute})

    @staticmethod
    def _score_inventory(
        session: Session, pair_id: str, passports: Sequence[Any],
    ) -> tuple[tuple[SheetTitle, ...], tuple[SheetTitle, ...], tuple[ContentScore, ...]]:
        profile_ids = [page.profile_id for page in passports]
        rows = session.execute(text(
            "SELECT comparison_page_profile_id, profile FROM comparison_page_profile "
            "WHERE comparison_page_profile_id = ANY(CAST(:profiles AS text[]))"
        ), {"profiles": profile_ids}).all()
        summaries = {str(profile): summary for profile, summary in rows}
        titles: dict[str, str] = {}
        for page in passports:
            stamp = (summaries.get(page.profile_id) or {}).get("stamp", {})
            titles[page.profile_id] = str(stamp.get("sheet_name") or stamp.get("sheet_title") or "")
        left = tuple(SheetTitle(page.profile_id, titles[page.profile_id])
                     for page in passports if page.side == "left")
        right = tuple(SheetTitle(page.profile_id, titles[page.profile_id])
                      for page in passports if page.side == "right")
        if len(left) * len(right) > 4_096:
            return left, right, ()
        texts = session.execute(text(
            "SELECT page_profile_id, normalised_text FROM stage_text_fragment "
            "WHERE stage_pair_id = :pair AND page_profile_id = ANY(CAST(:profiles AS text[]))"
        ), {"pair": pair_id, "profiles": profile_ids}).all()
        tokens: dict[str, set[str]] = {profile: set() for profile in profile_ids}
        for profile, value in texts:
            tokens[str(profile)].update(re.findall(r"[\w.-]+", str(value).casefold()))
        left_frequency = Counter(token for sheet in left for token in tokens[sheet.profile_id])
        right_frequency = Counter(token for sheet in right for token in tokens[sheet.profile_id])

        def overlap(a: set[str], b: set[str]) -> float:
            return len(a & b) / min(len(a), len(b)) if a and b else 0.0

        matrix = []
        for a in left:
            for b in right:
                ta, tb = tokens[a.profile_id], tokens[b.profile_id]
                title_score = overlap(set(normalize_title(a.title).split()), set(normalize_title(b.title).split()))
                words = overlap({t for t in ta if not any(c.isdigit() for c in t)},
                                {t for t in tb if not any(c.isdigit() for c in t)})
                numbers = overlap({t for t in ta if any(c.isdigit() for c in t)},
                                  {t for t in tb if any(c.isdigit() for c in t)})
                shared = {t for t in ta & tb if left_frequency[t] == right_frequency[t] == 1}
                anchors = {t for t in shared if len(t) >= 4 or any(c.isdigit() for c in t)}
                strong = {t for t in anchors if any(c.isalpha() for c in t) and any(c.isdigit() for c in t)}
                purpose = precheck_purpose([a.title], [b.title])
                matrix.append(ContentScore(
                    a.profile_id, b.profile_id, 0.25 * title_score + 0.45 * words + 0.30 * numbers,
                    sum(value >= 0.22 for value in (title_score, words, numbers)),
                    len(strong), len(anchors), purpose.status != "PAIR_REVIEW_REQUIRED",
                ))
        return left, right, tuple(matrix)

    def advance(self, item: WorkItem, *, run_id: str) -> dict[str, int]:
        from auditmanager.shared.identity import StageLinkRepairId

        with session_scope(self.sessions) as session:
            item.require_current(session)
            row = session.execute(text(
                "SELECT r.stage_pair_id, coalesce(r.effective_link_revision_id,r.stage_link_revision_id), "
                "r.actor_user_uid, r.repair_cycle_count, p.project_uid "
                "FROM stage_chain_run r JOIN stage_pair p ON p.stage_pair_id = r.stage_pair_id "
                "WHERE r.stage_chain_run_id = :run FOR UPDATE OF r"
            ), {"run": run_id}).first()
            if row is None or row[4] != item.project_uid:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainRun")
            if row[3] >= 1:
                return {"repair_cycles": 1, "repairs": 0}
            pair_id, base, actor = str(row[0]), str(row[1]), str(row[2])
            session.execute(text(
                "SELECT pg_advisory_xact_lock(hashtextextended('stage_link:' || :pair, 0))"
            ), {"pair": pair_id})
            latest, number, _source = self._latest(session, pair_id)
            if latest != base:
                raise _conflict("stage_link_revision_stale")
            passports = StageSheetReadService(self.sessions).passports(pair_id=pair_id)
            snapshot = self._snapshot(session, base)
            left, right, scores = self._score_inventory(session, pair_id, passports)
            by_title = {sheet.profile_id: sheet.title for sheet in (*left, *right)}
            problems = frozenset(str(link.item_id) for link in snapshot
                                 if link.relation == "paired" and normalize_title(by_title.get(
                                     str(link.left_profile_id), "")) != normalize_title(by_title.get(
                                     str(link.right_profile_id), "")))
            try:
                plan = plan_repairs(run_id=run_id, base_revision_id=base, links=snapshot,
                                    left_sheets=left, right_sheets=right,
                                    problem_link_ids=problems, content_scores=scores)
            except RepairRefused:
                session.execute(text(
                    "UPDATE stage_chain_run SET repair_cycle_count = 1 WHERE stage_chain_run_id = :run"
                ), {"run": run_id})
                return {"repair_cycles": 1, "repair_not_checked": 1}
            if plan is None:
                session.execute(text(
                    "UPDATE stage_chain_run SET repair_cycle_count = 1 WHERE stage_chain_run_id = :run"
                ), {"run": run_id})
                return {"repair_cycles": 1, "repairs": 0}
            claim = self.commands.begin(session, command_type="apply_stage_link_repair",
                                        idempotency_key=IdempotencyKey(f"stage-repair:{run_id}"),
                                        fingerprint=payload_fingerprint({"plan_key": plan.plan_key}))
            if isinstance(claim, CommandReplay):
                return {"repair_cycles": 1, "repairs": 1}
            after, stored = self._revision(
                session, pair_id=pair_id, base=base, number=number + 1,
                actor=actor, command_id=str(claim.command_id), source="automatic",
                snapshot=plan.after_snapshot, digest=plan.plan_key,
            )
            repair_id = str(StageLinkRepairId.new())
            proof = {"confidence": "high", "source_signature": plan.source_signature,
                     "changes": [asdict(change) for change in plan.changes]}
            session.execute(text(
                "INSERT INTO stage_link_repair "
                "(stage_link_repair_id, stage_chain_run_id, before_revision_id, after_revision_id, "
                "proof, before_snapshot, after_snapshot, content_key) "
                "VALUES (:repair, :run, :before, :after, CAST(:proof AS jsonb), "
                "CAST(:before_snapshot AS jsonb), CAST(:after_snapshot AS jsonb), :key)"
            ), {"repair": repair_id, "run": run_id, "before": base, "after": after,
                "proof": json.dumps(proof), "before_snapshot": json.dumps([asdict(x) for x in snapshot]),
                "after_snapshot": json.dumps([asdict(x) for x in stored]), "key": plan.plan_key})
            self._event(session, repair_id, "applied", actor, str(claim.command_id), after)
            session.execute(text(
                "UPDATE stage_chain_run SET effective_link_revision_id = :revision, "
                "repair_cycle_count = 1, updated_at = clock_timestamp() WHERE stage_chain_run_id = :run"
            ), {"run": run_id, "revision": after})
            session.execute(text(
                "UPDATE stage_chain_step SET state = 'queued', counts = '{}'::jsonb, "
                "failure_reason = NULL, started_at = NULL, finished_at = NULL, "
                "updated_at = clock_timestamp() WHERE stage_chain_run_id = :run AND step_no >= 2"
            ), {"run": run_id})
            session.execute(text(
                "INSERT INTO audit_event (audit_event_id,event_type,aggregate_type,aggregate_id,payload) "
                "VALUES (:event,'stage.link_repair_applied','StagePair',:pair,CAST(:payload AS jsonb))"
            ), {"event": str(AuditEventId.new()), "pair": pair_id,
                "payload": json.dumps({"run_id": run_id, "repair_id": repair_id,
                                       "before_revision_id": base, "after_revision_id": after})})
            self.commands.succeed(session, claim.command_id,
                                  {"repair_id": repair_id, "revision_id": after})
            return {"repair_cycles": 1, "repairs": 1, "recompute": 1}

    @staticmethod
    def _view(session: Session, repair_id: str) -> dict[str, Any]:
        row = session.execute(text(
            "SELECT x.stage_link_repair_id, x.stage_chain_run_id, x.before_revision_id, "
            "x.after_revision_id, x.proof, x.created_at, r.stage_pair_id "
            "FROM stage_link_repair x JOIN stage_chain_run r USING(stage_chain_run_id) "
            "WHERE x.stage_link_repair_id = :repair"
        ), {"repair": repair_id}).first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageLinkRepair")
        event = session.execute(text(
            "SELECT action FROM stage_link_repair_event WHERE stage_link_repair_id = :repair "
            "ORDER BY created_at DESC, stage_link_repair_event_id DESC LIMIT 1"
        ), {"repair": repair_id}).scalar_one_or_none()
        state = str(event or "applied")
        latest, _number, source = StageRepairService._latest(session, str(row[6]))
        if state == "applied" and latest != row[3] and source == "expert":
            state = "superseded"
        return {"repair_id": str(row[0]), "run_id": str(row[1]),
                "before_revision_id": str(row[2]), "after_revision_id": str(row[3]),
                "proof": dict(row[4]), "created_at": row[5], "state": state}

    def page(self, *, run_id: str, after: str | None, limit: int) -> tuple[tuple[dict[str, Any], ...], str | None]:
        with session_scope(self.sessions) as session:
            if not session.execute(text("SELECT 1 FROM stage_chain_run WHERE stage_chain_run_id = :run"),
                                   {"run": run_id}).first():
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainRun")
            if after is not None:
                prior = self._view(session, after)
                if prior["run_id"] != run_id:
                    raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="scope")
            ids = session.execute(text(
                "SELECT stage_link_repair_id FROM stage_link_repair WHERE stage_chain_run_id = :run "
                "AND (CAST(:after AS text) IS NULL OR stage_link_repair_id > :after) "
                "ORDER BY stage_link_repair_id LIMIT :limit"
            ), {"run": run_id, "after": after, "limit": limit + 1}).scalars().all()
            return tuple(self._view(session, str(uid)) for uid in ids[:limit]), (
                str(ids[limit - 1]) if len(ids) > limit else None)

    def undo(self, *, repair_id: str, base_revision_id: str, user_uid: str,
             actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        require_expert(actor_roles)
        with session_scope(self.sessions) as session:
            claim = self.commands.begin(session, command_type="undo_stage_link_repair",
                                        idempotency_key=IdempotencyKey(idempotency_key),
                                        fingerprint=payload_fingerprint({"repair_id": repair_id,
                                            "base_revision_id": base_revision_id, "user_uid": user_uid}))
            if isinstance(claim, CommandReplay):
                return self._view(session, repair_id)
            row = session.execute(text(
                "SELECT x.stage_chain_run_id, x.before_snapshot, x.after_revision_id, "
                "r.stage_pair_id, r.with_ai, r.pinned_version_uids, p.project_uid "
                "FROM stage_link_repair x JOIN stage_chain_run r USING(stage_chain_run_id) "
                "JOIN stage_pair p ON p.stage_pair_id = r.stage_pair_id "
                "WHERE x.stage_link_repair_id = :repair FOR UPDATE OF r"
            ), {"repair": repair_id}).first()
            if row is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageLinkRepair")
            session.execute(text(
                "SELECT pg_advisory_xact_lock(hashtextextended('stage_link:' || :pair, 0))"
            ), {"pair": row[3]})
            latest, number, _source = self._latest(session, str(row[3]))
            if self._view(session, repair_id)["state"] != "applied" or latest != base_revision_id or latest != row[2]:
                raise _conflict("stage_link_repair_superseded")
            before = tuple(MapLink(**value) for value in row[1])
            digest = str(payload_fingerprint({"repair_id": repair_id, "undo": True,
                                              "base_revision_id": base_revision_id}))
            revision, _stored = self._revision(
                session, pair_id=str(row[3]), base=latest, number=number + 1,
                actor=user_uid, command_id=str(claim.command_id), source="expert",
                snapshot=before, digest=digest,
            )
            child = StageTextRecomputeService(self.sessions).start_in_session(
                session, revision_id=revision, user_uid=user_uid, actor_roles=actor_roles,
                idempotency_key=f"stage-repair-undo-text:{repair_id}:{revision}",
            )
            self._event(session, repair_id, "undone", user_uid, str(claim.command_id), revision, child.run_id)
            session.execute(text(
                "UPDATE stage_chain_run SET effective_link_revision_id = :revision, "
                "state = :state, pause_reason = :reason, updated_at = clock_timestamp() "
                "WHERE stage_chain_run_id = :run"
            ), {"run": row[0], "revision": revision,
                "state": "paused" if row[4] else "queued",
                "reason": "comparison_consent_required" if row[4] else None})
            session.execute(text(
                "UPDATE stage_chain_step SET state = 'queued', counts = '{}'::jsonb, "
                "failure_reason = NULL, started_at = NULL, finished_at = NULL "
                "WHERE stage_chain_run_id = :run AND step_no >= 2"
            ), {"run": row[0]})
            if not row[4]:
                ComparisonWorkRepository().enqueue(
                    session, project_uid=str(row[6]), module="stages", kind="stage_chain",
                    payload={"run_id": str(row[0])}, dedupe_key=f"stage_chain:{row[0]}",
                    created_by_user_uid=user_uid,
                )
            self.commands.succeed(session, claim.command_id,
                                  {"repair_id": repair_id, "revision_id": revision,
                                   "recompute_run_id": child.run_id})
            return self._view(session, repair_id)
