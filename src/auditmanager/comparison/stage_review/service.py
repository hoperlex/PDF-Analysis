"""Stage review application service. All publications share a DB transaction and fence."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.work.model import WorkItem
from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AuditEventId, IdempotencyKey, IdentityError, StageCardEvidenceId, StageCardVerdictId, StageChangeCardId,
    StageGraphicEvidenceId, StageTextDifferenceId, StageTextFragmentId,
)

from .cards import anchor_key, carryover_match, digest, invalid, prepare_cards
from .writers import render_html, render_pdf, render_xlsx

_CARD = ("c.stage_change_card_id AS card_id,c.stage_chain_run_id AS run_id,c.card_key,"
         "c.stage_ai_classification_id AS classification_id,"
         "c.evidence_digest,c.class_name,c.category,c.title,c.system,c.evidence_ids,"
         "c.before_text AS before,c.after_text AS after")
_VERDICT = ("stage_card_verdict_id AS verdict_id,stage_change_card_id AS card_id,"
            "revision_no,decision,reason,evidence_digest,created_at")


def _missing(aggregate: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate)


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= 500:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="limit", constraint="range")


class StageReviewService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions
        self._commands = CommandRepository()

    @staticmethod
    def _run(session: Session, run_id: str) -> dict[str, Any]:
        row = session.execute(text(
            "SELECT r.*,p.project_uid,coalesce(r.effective_link_revision_id,r.stage_link_revision_id) "
            "AS revision_id,(SELECT v.stage_link_revision_id FROM stage_link_revision v "
            "WHERE v.stage_pair_id=r.stage_pair_id ORDER BY revision_no DESC LIMIT 1) AS latest_revision "
            "FROM stage_chain_run r JOIN stage_pair p ON p.stage_pair_id=r.stage_pair_id "
            "WHERE r.stage_chain_run_id=:run"
        ), {"run": run_id}).mappings().first()
        if row is None:
            raise _missing("StageChainRun")
        result = dict(row)
        version_stale = bool(session.execute(text(
            "SELECT EXISTS(SELECT 1 FROM document_version v WHERE v.version_uid=ANY(CAST(:pins AS text[])) "
            "AND v.version_ordinal<>(SELECT max(n.version_ordinal) FROM document_version n "
            "WHERE n.document_uid=v.document_uid))"
        ), {"pins": list(row["pinned_version_uids"])}).scalar_one())
        result["stale"] = row["revision_id"] != row["latest_revision"] or version_stale
        return result

    @staticmethod
    def _sources(session: Session, revision_id: str, run_id: str) -> dict[str, dict[str, Any]]:
        from auditmanager.comparison.stage_v3.mode import ENGINE, engine_for_run
        if engine_for_run(session, run_id) == ENGINE:
            from auditmanager.comparison.stage_ai.repository import StageAiRepository
            snapshot = StageAiRepository().revision(session, revision_id)
            rows = session.execute(text(
                "SELECT f.*,dv.document_uid,pp.page_number FROM stage_text_fragment f "
                "JOIN comparison_page_profile pp ON pp.comparison_page_profile_id=f.page_profile_id "
                "JOIN document_version dv ON dv.version_uid=pp.version_uid "
                "WHERE f.stage_pair_id=:pair AND f.page_profile_id=ANY(CAST(:profiles AS text[]))"
            ), {"pair": snapshot["stage_pair_id"], "profiles": [r["profile_id"] for r in snapshot["all_profiles"]]}).mappings()
            return {r["stage_text_fragment_id"]: {
                "kind": "TEXT", "fragment_id": r["stage_text_fragment_id"], "difference_id": None, "graphic_id": None,
                "before": r["normalised_text"] if r["side"] == "left" else "",
                "after": r["normalised_text"] if r["side"] == "right" else "",
                "parts": [{"side": r["side"], "profile_id": r["page_profile_id"], "document_uid": r["document_uid"],
                           "page_number": r["page_number"], "content_key": r["content_key"], "box_anchor": r["box_anchor"]}],
            } for r in rows}
        rows = session.execute(text(
            "SELECT d.stage_text_difference_id AS id,d.content_key,d.status,"
            "l.stage_text_fragment_id AS left_id,l.page_profile_id AS left_profile,"
            "l.content_key AS left_key,l.normalised_text AS left_text,l.box_anchor AS left_box,"
            "r.stage_text_fragment_id AS right_id,r.page_profile_id AS right_profile,"
            "r.content_key AS right_key,r.normalised_text AS right_text,r.box_anchor AS right_box,"
            "lv.document_uid AS left_document,lp.page_number AS left_page,"
            "rv.document_uid AS right_document,rp.page_number AS right_page "
            "FROM stage_text_difference d LEFT JOIN stage_text_fragment l "
            "ON l.stage_text_fragment_id=d.left_fragment_id LEFT JOIN stage_text_fragment r "
            "ON r.stage_text_fragment_id=d.right_fragment_id "
            "LEFT JOIN comparison_page_profile lp ON lp.comparison_page_profile_id=l.page_profile_id "
            "LEFT JOIN document_version lv ON lv.version_uid=lp.version_uid "
            "LEFT JOIN comparison_page_profile rp ON rp.comparison_page_profile_id=r.page_profile_id "
            "LEFT JOIN document_version rv ON rv.version_uid=rp.version_uid "
            "WHERE d.stage_link_revision_id=:revision "
            "ORDER BY d.content_key LIMIT 20001"
        ), {"revision": revision_id}).mappings().all()
        if len(rows) > 20_000:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_chain_run_id",
                              constraint="stage_review_evidence_budget")
        sources: dict[str, dict[str, Any]] = {}
        for row in rows:
            parts = []
            for side in ("left", "right"):
                if row[f"{side}_id"]:
                    parts.append({"side": side, "profile_id": row[f"{side}_profile"],
                                  "content_key": row[f"{side}_key"],
                                  "document_uid": row[f"{side}_document"],
                                  "page_number": row[f"{side}_page"],
                                  "box_anchor": row[f"{side}_box"]})
            sources[row["id"]] = {"kind": "TEXT", "parts": parts,
                                  "before": row["left_text"] or "", "after": row["right_text"] or "",
                                  "difference_id": row["id"], "graphic_id": None}
        # Not-checked/unreliable graphics are status records, never change claims.
        for row in session.execute(text(
            "SELECT g.*,er.content_key AS engine_key,lp.page_number AS left_page,lv.document_uid AS left_document,"
            "rp.page_number AS right_page,rv.document_uid AS right_document FROM stage_graphic_evidence g "
            "JOIN stage_link_item gi ON gi.stage_link_item_id=g.stage_link_item_id "
            "JOIN comparison_sheet_pair_result er ON er.comparison_sheet_pair_result_id=g.comparison_sheet_pair_result_id "
            "JOIN comparison_page_profile lp ON lp.comparison_page_profile_id=g.left_profile_id "
            "JOIN document_version lv ON lv.version_uid=lp.version_uid "
            "JOIN comparison_page_profile rp ON rp.comparison_page_profile_id=g.right_profile_id "
            "JOIN document_version rv ON rv.version_uid=rp.version_uid "
            "WHERE g.stage_chain_run_id=:run AND gi.stage_link_revision_id=:revision AND g.status='reliable' "
            "AND jsonb_array_length(g.regions)>0 ORDER BY g.content_key"
        ), {"run": run_id, "revision": revision_id}).mappings():
            parts, region_keys = [], []
            for region in row["regions"]:
                proof = region.get("registration", {})
                region_key = region.get("region_key", "")
                if (proof.get("source") != "comparison_sheet_pair_result" or proof.get("reliable") is not True
                        or proof.get("result_id") != row["comparison_sheet_pair_result_id"]
                        or proof.get("content_key") != row["engine_key"]
                        or len(region_key) != 64 or region_key in region_keys):
                    raise invalid("stage_review_graphic_proof_invalid")
                region_keys.append(region_key)
                for side in ("left", "right"):
                    box = region.get(f"{side}_box", [])
                    if (not isinstance(box, list) or len(box) != 4
                            or any(type(v) not in {int, float} or not math.isfinite(v) for v in box)
                            or not (0 <= box[0] < box[2] and 0 <= box[1] < box[3])):
                        raise invalid("stage_review_graphic_box_invalid")
                    parts.append({"side": side, "profile_id": row[f"{side}_profile_id"],
                                  "document_uid": row[f"{side}_document"], "page_number": row[f"{side}_page"],
                                  "content_key": digest({"engine": row["engine_key"], "region": region_key, "side": side}),
                                  "box_anchor": dict(zip(("x0", "top", "x1", "bottom"), box, strict=True))})
            sources[row["stage_graphic_evidence_id"]] = {
                "kind": "GRAPHIC", "parts": parts, "before": "", "after": "",
                "difference_id": None, "graphic_id": row["stage_graphic_evidence_id"],
                "graphic_key": digest({"engine": row["engine_key"], "regions": sorted(region_keys),
                                       "profiles": [row["left_profile_id"], row["right_profile_id"]]}),
            }
        return sources

    @staticmethod
    def _previous(session: Session, run: Mapping[str, Any]) -> list[dict[str, Any]]:
        previous = [dict(row) for row in session.execute(text(
            "SELECT c.evidence_digest,c.evidence_ids,v.*,coalesce(a.anchors,'[]'::jsonb) AS anchors "
            "FROM stage_change_card c "
            "JOIN stage_chain_run r ON r.stage_chain_run_id=c.stage_chain_run_id "
            "JOIN LATERAL(SELECT * FROM stage_card_verdict x "
            "WHERE x.stage_change_card_id=c.stage_change_card_id ORDER BY revision_no DESC LIMIT 1) v ON true "
            "LEFT JOIN LATERAL(SELECT jsonb_agg(DISTINCT jsonb_build_object("
            "'document_uid',dv.document_uid,'page_number',p.page_number,'side',e.side,'box_anchor',e.box_anchor)) AS anchors "
            "FROM stage_card_evidence e JOIN comparison_page_profile p ON p.comparison_page_profile_id=e.page_profile_id "
            "JOIN document_version dv ON dv.version_uid=p.version_uid "
            "WHERE e.stage_change_card_id=c.stage_change_card_id) a ON true "
            "WHERE r.stage_pair_id=:pair AND r.stage_chain_run_id<>:run AND r.created_at<:created "
            "ORDER BY v.created_at DESC,v.stage_card_verdict_id DESC LIMIT 10001"
        ), {"pair": run["stage_pair_id"], "run": run["stage_chain_run_id"],
            "created": run["created_at"]}).mappings()]
        if len(previous) > 10_000:
            raise invalid("stage_review_carryover_budget")
        for card in previous:
            card["anchor_keys"] = [anchor_key(p) for p in card.pop("anchors")]
        return previous

    @staticmethod
    def _audit(session: Session, run_id: str, event: str, payload: dict[str, Any]) -> None:
        session.execute(text(
            "INSERT INTO audit_event(audit_event_id,event_type,aggregate_type,aggregate_id,payload) "
            "VALUES(:id,:event,'StageChainRun',:run,CAST(:payload AS jsonb))"
        ), {"id": str(AuditEventId.new()), "event": event, "run": run_id,
            "payload": json.dumps(payload, ensure_ascii=False)})

    @staticmethod
    def _insert_verdict(session: Session, *, card_id: str, revision: int, decision: str,
                        reason: str, evidence_digest: str, actor: str, command: str,
                        carried_from: str | None = None) -> str:
        identity = str(StageCardVerdictId.new())
        session.execute(text(
            "INSERT INTO stage_card_verdict(stage_card_verdict_id,stage_change_card_id,revision_no,"
            "decision,reason,evidence_digest,actor_user_uid,command_id,carried_from_verdict_id) "
            "VALUES(:id,:card,:revision,:decision,:reason,:digest,:actor,:command,:carried)"
        ), {"id": identity, "card": card_id, "revision": revision, "decision": decision,
            "reason": reason, "digest": evidence_digest, "actor": actor,
            "command": command, "carried": carried_from})
        return identity

    def advance(self, item: WorkItem, run_id: str) -> dict[str, int]:
        """Step 7: one fenced transaction, append-only cards/evidence and exact carryover."""
        with session_scope(self._sessions) as session:
            item.require_current(session)
            run = self._run(session, run_id)
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                            {"key": "stage_link:" + run["stage_pair_id"]})
            run = self._run(session, run_id)
            if (item.project_uid != run["project_uid"] or item.module != "stages" or item.kind != "stage_chain"
                    or item.payload.get("run_id") != run_id or run["state"] != "running"
                    or run["kind"] != "full"
                    or run["stale"]):
                raise invalid("stage_review_run_scope_invalid")
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                            {"key": "stage_review:" + run_id})
            sources = self._sources(session, run["revision_id"], run_id)
            from auditmanager.comparison.stage_v3.mode import ENGINE, engine_for_run
            from auditmanager.comparison.stage_v3.policy import policy_for_run
            experimental = engine_for_run(session, run_id) == ENGINE
            policy = policy_for_run(session, run_id) if experimental else None
            answers = []
            if run["with_ai"]:
                if experimental:
                    from auditmanager.comparison.stage_v3.procedures import BUNDLE
                    bundle = BUNDLE if policy is None else policy["bundle"]
                    answers = [dict(row) for row in session.execute(text(
                        "SELECT a.stage_ai_classification_id AS classification_id,a.cards "
                        "FROM stage_ai_classification a JOIN stage_ai_unit u ON u.stage_ai_unit_id=a.stage_ai_unit_id "
                        "WHERE a.stage_chain_run_id=:run AND u.state='completed' AND u.group_id='v3:final:cards' "
                        "AND u.progress->>'prompt_bundle_version'=:bundle "
                        "ORDER BY u.generation DESC,u.created_at DESC,u.stage_ai_unit_id DESC LIMIT 1"
                    ), {"run": run_id, "bundle": bundle}).mappings()]
                else:
                    answers = [dict(row) for row in session.execute(text(
                        "SELECT a.stage_ai_classification_id AS classification_id,a.cards "
                        "FROM stage_ai_classification a JOIN stage_ai_unit u ON u.stage_ai_unit_id=a.stage_ai_unit_id "
                        "WHERE a.stage_chain_run_id=:run AND u.state='completed' ORDER BY a.content_key"
                    ), {"run": run_id}).mappings()]
            plans = prepare_cards(sources, answers, include_uncovered=not experimental, display_excerpts=policy is not None)
            source_digest = digest(plans)
            publication = session.execute(text(
                "SELECT payload->>'source_digest' FROM audit_event WHERE aggregate_type='StageChainRun' "
                "AND aggregate_id=:run AND event_type='stage.cards_materialized' ORDER BY occurred_at DESC LIMIT 1"
            ), {"run": run_id}).scalar_one_or_none()
            if publication is not None and publication != source_digest:
                raise invalid("stage_review_materialization_changed")
            existing = session.execute(text(
                "SELECT card_key,evidence_digest FROM stage_change_card WHERE stage_chain_run_id=:run"
            ), {"run": run_id}).all()
            if existing or publication is not None:
                if set(existing) != {(p["card_key"], p["evidence_digest"]) for p in plans}:
                    raise invalid("stage_review_materialization_changed")
                return self._counts(session, run)
            previous = [] if experimental else self._previous(session, run)
            for plan in plans:
                card_id = str(StageChangeCardId.new())
                session.execute(text(
                    "INSERT INTO stage_change_card(stage_change_card_id,stage_chain_run_id,"
                    "stage_ai_classification_id,card_key,evidence_digest,class_name,category,title,"
                    "system,evidence_ids,before_text,after_text) VALUES(:id,:run,:classification,"
                    ":key,:digest,:class,:category,:title,:system,CAST(:ids AS jsonb),:before,:after)"
                ), {"id": card_id, "run": run_id, "classification": plan["classification_id"],
                    "key": plan["card_key"], "digest": plan["evidence_digest"],
                    "class": plan["class_name"], "category": plan["category"],
                    "title": plan["title"], "system": plan["system"],
                    "ids": json.dumps(plan["evidence_ids"]), "before": plan["before"], "after": plan["after"]})
                for source_id in plan["evidence_ids"]:
                    source = sources[source_id]
                    for part in source["parts"]:
                        session.execute(text(
                            "INSERT INTO stage_card_evidence(stage_card_evidence_id,stage_chain_run_id,"
                            "stage_change_card_id,kind,source_difference_id,source_graphic_evidence_id,"
                            "source_fragment_id,side,page_profile_id,box_anchor,absence_proven) VALUES(:id,:run,:card,"
                            ":kind,:difference,:graphic,:fragment,:side,:profile,CAST(:box AS jsonb),false)"
                        ), {"id": str(StageCardEvidenceId.new()), "run": run_id, "card": card_id,
                            "kind": source["kind"], "difference": source["difference_id"],
                            "graphic": source["graphic_id"], "fragment": source.get("fragment_id"), "side": part["side"],
                            "profile": part["profile_id"], "box": json.dumps(part["box_anchor"])})
                label, matches = carryover_match(plan, previous)
                if plan["class_name"] != "SERVICE_STRUCTURE" and label == "full":
                    source = matches[0]
                    self._insert_verdict(session, card_id=card_id, revision=1,
                        decision=source["decision"], reason=source["reason"],
                        evidence_digest=plan["evidence_digest"], actor=source["actor_user_uid"],
                        command=source["command_id"], carried_from=source["stage_card_verdict_id"])
            self._audit(session, run_id, "stage.cards_materialized",
                        {"cards": len(plans), "source_digest": source_digest})
            return self._counts(session, run)

    @staticmethod
    def _latest(session: Session, card_id: str) -> dict[str, Any] | None:
        row = session.execute(text(
            f"SELECT {_VERDICT},carried_from_verdict_id FROM stage_card_verdict "
            "WHERE stage_change_card_id=:card ORDER BY revision_no DESC LIMIT 1"
        ), {"card": card_id}).mappings().first()
        return dict(row) if row else None

    def _project_card(self, session: Session, card: dict[str, Any], run: Mapping[str, Any],
                      previous: Sequence[dict[str, Any]]) -> dict[str, Any]:
        classification_id = card.pop("classification_id", None)
        metadata = None
        if classification_id is not None:
            matches = session.execute(text(
                "SELECT entry.value FROM stage_ai_classification a CROSS JOIN LATERAL jsonb_array_elements(a.cards) entry(value) "
                "WHERE a.stage_ai_classification_id=:classification AND entry.value->>'class_name'=:class "
                "AND ((entry.value->>'card_key')=:key OR (entry.value->>'card_key') IS NULL) "
                "AND (entry.value->'evidence_ids') @> CAST(:ids AS jsonb) AND CAST(:ids AS jsonb) @> (entry.value->'evidence_ids') LIMIT 2"
            ), {"classification": classification_id, "key": card["card_key"], "class": card["class_name"],
                "ids": json.dumps(card["evidence_ids"])}).scalars().all()
            if len(matches) == 1:
                metadata = matches[0]
        metadata = metadata or {}
        card["experimental"] = metadata.get("experimental")
        card["materiality"] = metadata.get("materiality") if metadata.get("materiality") in ("material", "non_material") else "unknown"
        card["importance"] = metadata.get("importance") if metadata.get("importance") in ("high", "normal") else "unknown"
        card["detail_increased"] = metadata.get("detail_increased") is True
        evidence = []
        anchors = []
        for row in session.execute(text(
            "SELECT e.stage_card_evidence_id AS evidence_id,e.kind,coalesce(e.source_difference_id,"
            "source_graphic_evidence_id,source_fragment_id) AS source_id,side,"
            "page_profile_id AS profile_id,box_anchor,absence_proven,"
            "dv.document_uid,p.page_number FROM stage_card_evidence e "
            "LEFT JOIN comparison_page_profile p ON p.comparison_page_profile_id=e.page_profile_id "
            "LEFT JOIN document_version dv ON dv.version_uid=p.version_uid "
            "WHERE stage_change_card_id=:card ORDER BY stage_card_evidence_id"
        ), {"card": card["card_id"]}).mappings():
            part = dict(row)
            if part["document_uid"]:
                anchors.append(anchor_key(part))
            part.pop("document_uid")
            part.pop("page_number")
            evidence.append({k: v for k, v in part.items() if v is not None})
        card["evidence"] = evidence
        card["stale"] = bool(run["stale"])
        latest = self._latest(session, card["card_id"])
        if latest:
            source = latest.pop("carried_from_verdict_id")
            card["verdict"] = latest
            card["carryover"] = "full" if source else "none"
            card["carried_verdict_ids"] = [source] if source else []
        else:
            label, matches = carryover_match(card | {"anchor_keys": anchors}, previous)
            card["carryover"] = label
            card["carried_verdict_ids"] = [p["stage_card_verdict_id"] for p in matches]
        return card

    def _counts(self, session: Session, run: Mapping[str, Any]) -> dict[str, int]:
        row = session.execute(text(
            "SELECT count(*) AS total,count(*) FILTER(WHERE class_name='REVIEW') AS review,"
            "count(*) FILTER(WHERE class_name='PROJECT_CHANGE') AS project_changes "
            "FROM stage_change_card WHERE stage_chain_run_id=:run"
        ), {"run": run["stage_chain_run_id"]}).one()
        conflicts = session.execute(text(
            "SELECT count(DISTINCT c.stage_change_card_id) FROM stage_change_card c WHERE "
            "c.stage_chain_run_id=:run AND EXISTS(SELECT 1 FROM stage_change_card old "
            "JOIN stage_chain_run r ON r.stage_chain_run_id=old.stage_chain_run_id "
            "JOIN LATERAL(SELECT decision FROM stage_card_verdict vv WHERE "
            "vv.stage_change_card_id=old.stage_change_card_id ORDER BY revision_no DESC LIMIT 1) v ON true "
            "WHERE r.stage_pair_id=:pair AND r.created_at<:created AND "
            "old.evidence_digest=c.evidence_digest GROUP BY old.evidence_digest "
            "HAVING count(DISTINCT v.decision)>1)"
        ), {"run": run["stage_chain_run_id"], "pair": run["stage_pair_id"],
            "created": run["created_at"]}).scalar_one()
        labels = session.execute(text(
            "SELECT count(*) FILTER(WHERE m.importance='high'),count(*) FILTER(WHERE m.importance IS NULL OR "
            "m.importance NOT IN ('high','normal')) FROM stage_change_card c "
            "LEFT JOIN stage_ai_classification a ON a.stage_ai_classification_id=c.stage_ai_classification_id "
            "LEFT JOIN LATERAL(SELECT CASE WHEN count(*)=1 THEN max(entry.value->>'importance') ELSE NULL END AS importance "
            "FROM jsonb_array_elements(a.cards) entry(value) WHERE entry.value->>'class_name'=c.class_name "
            "AND (entry.value->>'card_key'=c.card_key OR (entry.value->>'card_key') IS NULL) "
            "AND (entry.value->'evidence_ids') @> c.evidence_ids AND c.evidence_ids @> (entry.value->'evidence_ids')) m ON true "
            "WHERE c.stage_chain_run_id=:run"
        ), {"run": run["stage_chain_run_id"]}).one()
        return {"total": int(row[0]), "review": int(row[1]), "project_changes": int(row[2]),
                "conflicts": int(conflicts), "high_importance": int(labels[0]), "importance_unknown": int(labels[1])}

    def page(self, run_id: str, after: str | None = None, limit: int = 100
             ) -> tuple[tuple[dict[str, Any], ...], str | None, dict[str, int]]:
        _validate_limit(limit)
        with session_scope(self._sessions) as session:
            run = self._run(session, run_id)
            if after and not session.execute(text(
                "SELECT 1 FROM stage_change_card WHERE stage_chain_run_id=:run AND card_key=:key"
            ), {"run": run_id, "key": after}).first():
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
            rows = session.execute(text(
                f"SELECT {_CARD} FROM stage_change_card c WHERE c.stage_chain_run_id=:run "
                "AND c.card_key>:after ORDER BY c.card_key LIMIT :limit"
            ), {"run": run_id, "after": after or "", "limit": limit + 1}).mappings().all()
            previous = self._previous(session, run)
            visible = tuple(self._project_card(session, dict(row), run, previous) for row in rows[:limit])
            return visible, visible[-1]["card_key"] if len(rows) > limit else None, self._counts(session, run)

    def get(self, card_id: str) -> dict[str, Any]:
        with session_scope(self._sessions) as session:
            row = session.execute(text(f"SELECT {_CARD} FROM stage_change_card c "
                                       "WHERE c.stage_change_card_id=:card"), {"card": card_id}).mappings().first()
            if row is None:
                raise _missing("StageChangeCard")
            run = self._run(session, row["run_id"])
            return self._project_card(session, dict(row), run, self._previous(session, run))

    def promote(self, run_id: str, source_ids: Sequence[str], reason: str, *, user_uid: str,
                actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        """Expert escalation reveals source evidence; it neither rewrites AI nor accepts a card."""
        require_expert(actor_roles)
        if (not isinstance(source_ids, (tuple, list)) or not 1 <= len(source_ids) <= 400
                or any(not isinstance(value, str) for value in source_ids) or len(set(source_ids)) != len(source_ids)
                or not isinstance(reason, str) or len(reason) > 2000 or not reason.strip()):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="source_ids", constraint="review_card_input")
        try:
            types = {"std": StageTextDifferenceId, "sge": StageGraphicEvidenceId, "stf": StageTextFragmentId}
            ids = sorted(str(types[value.split("_", 1)[0]].parse(value)) for value in source_ids)
        except (IdentityError, KeyError, AttributeError, TypeError):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="source_ids", constraint="format") from None
        reason = reason.strip()
        fingerprint = payload_fingerprint({"command": "create_stage_review_card.v1", "run_id": run_id,
                                           "source_ids": ids, "reason": reason, "actor_uid": user_uid})
        with session_scope(self._sessions) as session:
            claim = self._commands.begin(session, command_type="create_stage_review_card",
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint)
            if isinstance(claim, CommandReplay):
                row = session.execute(text(f"SELECT {_CARD} FROM stage_change_card c WHERE c.stage_change_card_id=:card"),
                                      {"card": claim.outcome["card_id"]}).mappings().first()
                if row is None:
                    raise _missing("StageChangeCard")
                run = self._run(session, run_id)
                return self._project_card(session, dict(row), run, self._previous(session, run))
            run = self._run(session, run_id)
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                            {"key": "stage_link:" + run["stage_pair_id"]})
            run = self._run(session, run_id)
            if run["stale"] or run["state"] != "completed":
                raise invalid("stage_review_run_not_current_completed")
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                            {"key": "stage_review:" + run_id})
            raw = self._sources(session, run["revision_id"], run_id)
            sources = {identity: raw[identity] for identity in ids if identity in raw}
            fragment_ids = [identity for identity in ids if identity.startswith("stf_")]
            for row in session.execute(text(
                "SELECT f.*,p.page_number,v.document_uid FROM stage_text_fragment f "
                "JOIN comparison_page_profile p ON p.comparison_page_profile_id=f.page_profile_id "
                "JOIN document_version v ON v.version_uid=p.version_uid WHERE f.stage_pair_id=:pair "
                "AND f.stage_text_fragment_id=ANY(CAST(:ids AS text[])) AND p.version_uid=ANY(CAST(:pins AS text[])) "
                "AND EXISTS(SELECT 1 FROM stage_link_item i WHERE i.stage_link_revision_id=:revision AND "
                "((f.side='left' AND i.left_profile_id=f.page_profile_id) OR (f.side='right' AND i.right_profile_id=f.page_profile_id)))"
            ), {"pair": run["stage_pair_id"], "ids": fragment_ids, "pins": list(run["pinned_version_uids"]),
                "revision": run["revision_id"]}).mappings():
                identity, side = row["stage_text_fragment_id"], row["side"]
                sources[identity] = {"kind": "TEXT", "fragment_id": identity, "difference_id": None,
                    "graphic_id": None, "before": row["normalised_text"] if side == "left" else "",
                    "after": row["normalised_text"] if side == "right" else "", "parts": [{
                        "side": side, "profile_id": row["page_profile_id"], "content_key": row["content_key"],
                        "document_uid": row["document_uid"], "page_number": row["page_number"], "box_anchor": row["box_anchor"]}]}
            if set(sources) != set(ids):
                raise _missing("StageAtomicEvidence")
            plan = prepare_cards(sources, [{"classification_id": None, "cards": [{
                "class_name": "REVIEW", "category": "uncertain", "title": "Экспертная проверка свидетельств",
                "system": "unknown", "evidence_ids": ids}]}])[0]
            row = session.execute(text(f"SELECT {_CARD} FROM stage_change_card c "
                "WHERE c.stage_chain_run_id=:run AND c.card_key=:key"), {"run": run_id, "key": plan["card_key"]}).mappings().first()
            if row is None:
                card_id = str(StageChangeCardId.new())
                session.execute(text(
                    "INSERT INTO stage_change_card(stage_change_card_id,stage_chain_run_id,card_key,evidence_digest,"
                    "class_name,category,title,system,evidence_ids,before_text,after_text) VALUES(:card,:run,:key,:digest,"
                    "'REVIEW','uncertain',:title,'unknown',CAST(:ids AS jsonb),:before,:after)"
                ), {"card": card_id, "run": run_id, "key": plan["card_key"], "digest": plan["evidence_digest"],
                    "title": plan["title"], "ids": json.dumps(ids), "before": plan["before"], "after": plan["after"]})
                for identity in ids:
                    source = sources[identity]
                    for part in source["parts"]:
                        session.execute(text(
                            "INSERT INTO stage_card_evidence(stage_card_evidence_id,stage_chain_run_id,stage_change_card_id,"
                            "kind,source_fragment_id,source_difference_id,source_graphic_evidence_id,side,page_profile_id,box_anchor) "
                            "VALUES(:id,:run,:card,:kind,:fragment,:difference,:graphic,:side,:profile,CAST(:box AS jsonb))"
                        ), {"id": str(StageCardEvidenceId.new()), "run": run_id, "card": card_id, "kind": source["kind"],
                            "fragment": source.get("fragment_id"), "difference": source["difference_id"],
                            "graphic": source["graphic_id"], "side": part["side"], "profile": part["profile_id"],
                            "box": json.dumps(part["box_anchor"])})
                row = session.execute(text(f"SELECT {_CARD} FROM stage_change_card c WHERE c.stage_change_card_id=:card"),
                                      {"card": card_id}).mappings().one()
            elif row["evidence_digest"] != plan["evidence_digest"]:
                raise invalid("stage_review_materialization_changed")
            card_id = row["card_id"]
            self._audit(session, run_id, "stage.review_card_created", {"card_id": card_id, "source_ids": ids,
                "actor_uid": user_uid, "command_id": str(claim.command_id), "reason": reason})
            self._commands.succeed(session, claim.command_id, {"card_id": card_id})
            return self._project_card(session, dict(row), run, self._previous(session, run))

    def apply_verdicts(self, run_id: str, updates: Sequence[Mapping[str, Any]], *, user_uid: str,
                       actor_roles: frozenset[str], idempotency_key: str) -> tuple[dict[str, Any], ...]:
        require_expert(actor_roles)
        updates = [dict(update) for update in updates]
        if not 1 <= len(updates) <= 500 or len({u.get("card_id") for u in updates}) != len(updates):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="updates", constraint="unique_bounded")
        for update in updates:
            if (set(update) != {"card_id", "expected_revision", "decision", "reason"}
                    or type(update["expected_revision"]) is not int or update["expected_revision"] < 0
                    or update["decision"] not in {"accepted", "rejected"}
                    or not isinstance(update["reason"], str) or len(update["reason"]) > 2000
                    or (update["decision"] == "rejected" and not update["reason"].strip())):
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="updates", constraint="verdict_input")
        fingerprint = payload_fingerprint({"command": "apply_stage_card_verdicts.v1", "run_id": run_id,
                                           "user_uid": user_uid, "updates": updates})
        with session_scope(self._sessions) as session:
            claim = self._commands.begin(session, command_type="apply_stage_card_verdicts",
                idempotency_key=IdempotencyKey(idempotency_key), fingerprint=fingerprint)
            if isinstance(claim, CommandReplay):
                ids = list(claim.outcome["verdict_ids"])
                records = {r["verdict_id"]: dict(r) for r in session.execute(text(
                    f"SELECT {_VERDICT} FROM stage_card_verdict WHERE stage_card_verdict_id=ANY(CAST(:ids AS text[]))"
                ), {"ids": ids}).mappings()}
                return tuple(records[i] for i in ids)
            run = self._run(session, run_id)
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                            {"key": "stage_link:" + run["stage_pair_id"]})
            run = self._run(session, run_id)
            if run["stale"] or run["state"] != "completed":
                raise invalid("stage_review_run_not_current_completed")
            # Stable lock order makes two overlapping bulk commands serialize without a deadlock.
            cards = {}
            for identity in sorted(u["card_id"] for u in updates):
                session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                                {"key": "stage_verdict:" + identity})
                row = session.execute(text(f"SELECT {_CARD} FROM stage_change_card c "
                    "WHERE c.stage_change_card_id=:card AND c.stage_chain_run_id=:run"
                ), {"card": identity, "run": run_id}).mappings().first()
                if row is None:
                    raise _missing("StageChangeCard")
                if row["class_name"] == "SERVICE_STRUCTURE":
                    raise invalid("stage_service_card_has_no_verdict")
                cards[identity] = dict(row)
            ids = []
            for update in updates:
                latest = self._latest(session, update["card_id"])
                revision = latest["revision_no"] if latest else 0
                if revision != update["expected_revision"]:
                    raise invalid("stage_card_verdict_revision_changed")
                ids.append(self._insert_verdict(session, card_id=update["card_id"], revision=revision + 1,
                    decision=update["decision"], reason=update["reason"].strip(),
                    evidence_digest=cards[update["card_id"]]["evidence_digest"], actor=user_uid,
                    command=str(claim.command_id)))
            self._commands.succeed(session, claim.command_id, {"verdict_ids": ids})
            self._audit(session, run_id, "stage.card_verdicts_applied", {"verdict_ids": ids, "actor_user_uid": user_uid})
            records = {r["verdict_id"]: dict(r) for r in session.execute(text(
                f"SELECT {_VERDICT} FROM stage_card_verdict WHERE stage_card_verdict_id=ANY(CAST(:ids AS text[]))"
            ), {"ids": ids}).mappings()}
            return tuple(records[i] for i in ids)

    def verdicts(self, card_id: str, after_revision: int | None = None, limit: int = 100
                 ) -> tuple[tuple[dict[str, Any], ...], int | None]:
        _validate_limit(limit)
        with session_scope(self._sessions) as session:
            if not session.execute(text("SELECT 1 FROM stage_change_card WHERE stage_change_card_id=:card"),
                                   {"card": card_id}).first():
                raise _missing("StageChangeCard")
            if after_revision is not None and not session.execute(text(
                "SELECT 1 FROM stage_card_verdict WHERE stage_change_card_id=:card AND revision_no=:revision"
            ), {"card": card_id, "revision": after_revision}).first():
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
            rows = [dict(r) for r in session.execute(text(
                f"SELECT {_VERDICT} FROM stage_card_verdict WHERE stage_change_card_id=:card "
                "AND revision_no>:after ORDER BY revision_no LIMIT :limit"
            ), {"card": card_id, "after": after_revision or 0, "limit": limit + 1}).mappings()]
            visible = tuple(rows[:limit])
            return visible, visible[-1]["revision_no"] if len(rows) > limit else None

    def journal(self, run_id: str, grouping: str = "designation") -> dict[str, Any]:
        if grouping not in {"designation", "section", "system"}:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="grouping", constraint="enum")
        with session_scope(self._sessions) as session:
            run = self._run(session, run_id)
            records = session.execute(text(
                f"SELECT {_CARD} FROM stage_change_card c JOIN LATERAL(SELECT v.decision FROM stage_card_verdict v "
                "WHERE v.stage_change_card_id=c.stage_change_card_id ORDER BY revision_no DESC LIMIT 1) latest ON true "
                "WHERE c.stage_chain_run_id=:run AND c.class_name<>'SERVICE_STRUCTURE' "
                "AND latest.decision='accepted' ORDER BY c.class_name,c.category,c.card_key LIMIT 10001"
            ), {"run": run_id}).mappings().all()
            if len(records) > 10_000:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_chain_run_id",
                                  constraint="stage_journal_card_budget")
            cards = [self._project_card(session, dict(row), run, ()) for row in records]
            labels = {}
            for row in session.execute(text(
                "SELECT p.comparison_page_profile_id,d.document_uid,coalesce("
                "(SELECT c.designation FROM stage_upload_candidate c WHERE c.document_uid=d.document_uid "
                "AND c.state='published' AND c.designation IS NOT NULL ORDER BY c.confirmed_at DESC LIMIT 1),"
                "(SELECT u.designation FROM comparison_upload_set u WHERE u.document_uid=d.document_uid "
                "AND u.state='done' AND u.designation IS NOT NULL ORDER BY u.confirmed_at DESC LIMIT 1),"
                "d.display_title) AS display_title,"
                "coalesce(v.section_code,'unknown') AS section FROM comparison_page_profile p "
                "JOIN document_version ver ON ver.version_uid=p.version_uid JOIN document d ON d.document_uid=ver.document_uid "
                "LEFT JOIN version_classification_current v ON v.version_uid=ver.version_uid "
                "WHERE ver.version_uid=ANY(CAST(:pins AS text[]))"
            ), {"pins": list(run["pinned_version_uids"])}).mappings():
                labels[row["comparison_page_profile_id"]] = dict(row)
            groups: dict[str, dict[str, Any]] = {}
            for card in cards:
                if grouping == "system":
                    key, label = card["system"], card["system"]
                else:
                    scope = [labels[e["profile_id"]] for e in card["evidence"]
                             if e.get("profile_id") in labels]
                    if grouping == "section":
                        sections = sorted({s["section"] for s in scope}) or ["unknown"]
                        key = label = " / ".join(sections)
                    else:
                        docs = sorted({(s["document_uid"], s["display_title"]) for s in scope})
                        key = " / ".join(d[0] for d in docs) or "unknown"
                        label = " / ".join(d[1] for d in docs) or "Без обозначения"
                group = groups.setdefault(key, {"key": key, "label": label, "rows": []})
                group["rows"].append(card)
            hidden = sum(1 for row in session.execute(text(
                "SELECT decisions FROM stage_ai_review WHERE stage_chain_run_id=:run"
            ), {"run": run_id}) for decision in row[0] if decision.get("status") in {"SAME", "MOVED"})
            service = session.execute(text(
                "SELECT count(*) FROM stage_change_card WHERE stage_chain_run_id=:run AND class_name='SERVICE_STRUCTURE'"
            ), {"run": run_id}).scalar_one()
            return {"run_id": run_id, "grouping": grouping,
                    "groups": [groups[key] for key in sorted(groups)], "accepted_count": len(cards),
                    "ai_hidden_same_count": hidden, "ai_service_count": int(service), "stale": bool(run["stale"])}

    def export(self, run_id: str, format: str, grouping: str = "designation") -> bytes:
        writer = {"xlsx": render_xlsx, "pdf": render_pdf, "html": render_html}.get(format)
        if writer is None:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="format", constraint="enum")
        return writer(self.journal(run_id, grouping))
