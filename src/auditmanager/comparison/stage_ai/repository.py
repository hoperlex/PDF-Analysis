"""C4 Stage AI rows; callers own transactions and lease/run authority."""

from __future__ import annotations

import json
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid

from .validation import canonical_json, digest

ANSWER_TABLES = {
    "review": ("stage_ai_review", "sarev", "decisions"),
    "classify": ("stage_ai_classification", "sacls", "cards"),
    "synthesize": ("stage_ai_synthesis", "sasyn", "result"),
}


class StageAiRepository:
    def generation(self, session: Session, run_id: str, job_id: str | None) -> int:
        if job_id is None:
            return 0
        return int(session.execute(text(
            "SELECT count(*)-1 FROM comparison_ai_job a JOIN comparison_ai_job target "
            "ON target.comparison_ai_job_id=:job WHERE a.stage_chain_run_id=:run "
            "AND (a.created_at,a.comparison_ai_job_id)<=(target.created_at,target.comparison_ai_job_id)"
        ), {"run": run_id, "job": job_id}).scalar_one())

    def previous_progress(self, session: Session, *, run_id: str, kind: str, group_id: str,
                          source_sha256: str, content_key: str) -> dict[str, Any] | None:
        rows = session.execute(text(
            "SELECT progress FROM stage_ai_unit WHERE stage_chain_run_id=:run AND kind=:kind "
            "AND group_id=:group AND source_sha256=:sha ORDER BY generation DESC,created_at DESC"
        ), {"run": run_id, "kind": kind, "group": group_id, "sha": source_sha256}).scalars()
        return next((dict(value) for value in rows if value.get("content_key") == content_key), None)

    def fail_run(self, session: Session, *, run_id: str, phase: str | None, reason: str) -> None:
        session.execute(text(
            "UPDATE stage_chain_run SET state='failed',failure_reason=:reason,pause_reason=NULL,"
            "updated_at=clock_timestamp() WHERE stage_chain_run_id=:run AND state IN ('queued','running','paused')"
        ), {"run": run_id, "reason": reason})
        if phase in ANSWER_TABLES:
            session.execute(text(
                "UPDATE stage_chain_step SET state='failed',failure_reason=:reason,finished_at=clock_timestamp(),"
                "updated_at=clock_timestamp() WHERE stage_chain_run_id=:run AND step_no=:step AND state<>'completed'"
            ), {"run": run_id, "step": {"review": 4, "classify": 5, "synthesize": 6}[phase], "reason": reason})

    def graphic_receipts(self, session: Session, run_id: str, revision_id: str) -> set[tuple[str, str]]:
        return set(session.execute(text(
            "SELECT e.left_profile_id,e.right_profile_id FROM stage_graphic_evidence e "
            "JOIN stage_link_item i ON i.stage_link_item_id=e.stage_link_item_id "
            "WHERE e.stage_chain_run_id=:run AND i.stage_link_revision_id=:revision"
        ), {"run": run_id, "revision": revision_id}).all())

    def source_consent(self, session: Session, *, run_id: str, job_id: str, revision_id: str,
                       profiles, consent_no: int, approved: bool = False) -> bool:
        source = {"revision_id": revision_id, "profiles": [
            {key: row[key] for key in ("profile_id", "version_uid", "content_key")} for row in profiles]}
        key = digest(source)
        unit = self.unit(session, run_id=run_id, kind="review", group_id="source-consent",
            source_sha256=key, job_id=job_id, payload={"content_key": key,
                "accepted_consent_no": consent_no if approved else None, "required_after": consent_no,
                "immutable_source": source})
        progress = dict(unit["payload"])
        if progress.get("accepted_consent_no") is None and consent_no > progress["required_after"]:
            progress["accepted_consent_no"] = consent_no
        accepted = progress.get("accepted_consent_no") is not None
        self.update_unit(session, unit["stage_ai_unit_id"], payload=progress,
                         state="completed" if accepted else "queued")
        return accepted

    def graphic_progress(self, session: Session, run_id: str) -> dict[str, dict[str, Any]]:
        return {row["group_id"]: dict(row) for row in session.execute(text(
            "SELECT group_id,state,progress FROM stage_ai_unit WHERE stage_chain_run_id=:run "
            "AND kind='classify' AND group_id LIKE 'graphic:%' AND comparison_ai_job_id="
            "(SELECT comparison_ai_job_id FROM stage_chain_run WHERE stage_chain_run_id=:run)"
        ), {"run": run_id}).mappings()}

    def page(self, session: Session, *, run_id: str, kind: str, after: str | None,
             limit: int) -> tuple[tuple[dict[str, Any], ...], str | None]:
        self.run(session, run_id)
        if kind not in ANSWER_TABLES or type(limit) is not int or not 1 <= limit <= 500:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="limit", constraint="range")
        table, _prefix, field = ANSWER_TABLES[kind]
        identity = table + "_id"
        if after is not None and not session.execute(text(
            f"SELECT 1 FROM {table} WHERE stage_chain_run_id=:run AND {identity}=:after"
        ), {"run": run_id, "after": after}).first():
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="cursor", constraint="format")
        rows = [dict(row) for row in session.execute(text(
            f"SELECT * FROM {table} WHERE stage_chain_run_id=:run "
            f"AND (CAST(:after AS text) IS NULL OR {identity}>:after) ORDER BY {identity} LIMIT :limit"
        ), {"run": run_id, "after": after, "limit": limit + 1}).mappings()]
        result = []
        output_id = {"review": "review_id", "classify": "classification_id", "synthesize": "synthesis_id"}[kind]
        for row in rows[:limit]:
            item = {output_id: row[identity], "run_id": row["stage_chain_run_id"],
                    "unit_id": row["stage_ai_unit_id"], "content_key": row["content_key"],
                    field: row[field], "model_identity": row["model_identity"], "created_at": row["created_at"]}
            if kind != "synthesize":
                item.update(group_id=row["group_id"], source_sha256=row["source_sha256"])
            result.append(item)
        return tuple(result), (rows[limit - 1][identity] if len(rows) > limit else None)

    def run(self, session: Session, run_id: str) -> dict[str, Any]:
        row = session.execute(text(
            "SELECT r.*, p.project_uid, p.left_document_uid AS document_uid "
            "FROM stage_chain_run r JOIN stage_pair p ON p.stage_pair_id=r.stage_pair_id "
            "WHERE r.stage_chain_run_id=:run"
        ), {"run": run_id}).mappings().first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageChainRun")
        result = dict(row)
        result["revision_id"] = result.get("effective_link_revision_id") or result["stage_link_revision_id"]
        return result

    def revision(self, session: Session, revision_id: str) -> dict[str, Any]:
        row = session.execute(text(
            "SELECT r.stage_pair_id, r.stage_link_revision_id, p.project_uid, p.left_document_uid AS document_uid "
            "FROM stage_link_revision r JOIN stage_pair p ON p.stage_pair_id=r.stage_pair_id "
            "WHERE r.stage_link_revision_id=:revision AND p.state='confirmed'"
        ), {"revision": revision_id}).mappings().first()
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="StageLinkRevision")
        data = dict(row)
        data["links"] = [dict(link) for link in session.execute(text(
            "SELECT stage_link_item_id,left_profile_id,right_profile_id,relation,confidence,row_no "
            "FROM stage_link_item WHERE stage_link_revision_id=:revision ORDER BY row_no"
        ), {"revision": revision_id}).mappings()]
        profiles = sorted({str(link[key]) for link in data["links"]
                           for key in ("left_profile_id", "right_profile_id") if link[key] is not None})
        data["profiles"] = [dict(profile) for profile in session.execute(text(
            "SELECT pp.comparison_page_profile_id AS profile_id,pp.version_uid,pp.content_key,pp.status,pp.profile, "
            "pp.profile_blob_id,v.document_uid,v.version_ordinal, "
            "(SELECT max(latest.version_ordinal) FROM document_version latest WHERE latest.document_uid=v.document_uid) AS latest_ordinal "
            "FROM comparison_page_profile pp JOIN document_version v ON v.version_uid=pp.version_uid "
            "WHERE pp.comparison_page_profile_id=ANY(CAST(:profiles AS text[])) ORDER BY pp.comparison_page_profile_id"
        ), {"profiles": profiles}).mappings()]
        if len(data["profiles"]) != len(profiles) or any(
            row["status"] != "ready" or row["version_ordinal"] != row["latest_ordinal"]
            for row in data["profiles"]
        ):
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_profiles_stale")
        from auditmanager.comparison.profile.limits import ALGO_VERSION
        data["all_profiles"] = [dict(profile) for profile in session.execute(text(
            "SELECT pp.comparison_page_profile_id AS profile_id,pp.version_uid,pp.content_key,pp.status,pp.profile, "
            "pp.profile_blob_id,pp.page_number,v.page_count, "
            "CASE WHEN am_stage_profile_in_pair(:pair,pp.comparison_page_profile_id,'left') THEN 'left' ELSE 'right' END AS side "
            "FROM comparison_page_profile pp JOIN document_version v ON v.version_uid=pp.version_uid "
            "WHERE pp.algo_version=:algo AND v.version_ordinal=(SELECT max(latest.version_ordinal) "
            "FROM document_version latest WHERE latest.document_uid=v.document_uid) "
            "AND (am_stage_profile_in_pair(:pair,pp.comparison_page_profile_id,'left') "
            "OR am_stage_profile_in_pair(:pair,pp.comparison_page_profile_id,'right')) "
            "ORDER BY pp.comparison_page_profile_id"
        ), {"pair": data["stage_pair_id"], "algo": ALGO_VERSION}).mappings()]
        counts: dict[str, int] = {}
        for profile in data["all_profiles"]:
            counts[profile["version_uid"]] = counts.get(profile["version_uid"], 0) + 1
        if (len(data["all_profiles"]) > 64 or any(profile["status"] != "ready"
                or counts[profile["version_uid"]] != profile["page_count"] for profile in data["all_profiles"])):
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_profiles")
        all_profiles = [profile["profile_id"] for profile in data["all_profiles"]]
        data["fragments"] = [dict(fragment) for fragment in session.execute(text(
            "SELECT f.*,pp.version_uid FROM stage_text_fragment f "
            "JOIN comparison_page_profile pp ON pp.comparison_page_profile_id=f.page_profile_id "
            "WHERE f.stage_pair_id=:pair AND f.page_profile_id=ANY(CAST(:profiles AS text[])) "
            "ORDER BY f.stage_text_fragment_id"
        ), {"pair": data["stage_pair_id"], "profiles": all_profiles}).mappings()]
        data["differences"] = [dict(row) for row in session.execute(text(
            "SELECT * FROM stage_text_difference WHERE stage_link_revision_id=:revision ORDER BY stage_text_difference_id"
        ), {"revision": revision_id}).mappings()]
        data["hints"] = [dict(row) for row in session.execute(text(
            "SELECT * FROM stage_text_hint WHERE stage_link_revision_id=:revision ORDER BY stage_text_hint_id"
        ), {"revision": revision_id}).mappings()]
        return data

    def unit(self, session: Session, *, run_id: str, kind: str, group_id: str,
             source_sha256: str, payload: Mapping[str, Any], job_id: str | None = None) -> dict[str, Any]:
        unit_id = f"saunit_{new_ulid()}"
        progress = dict(payload)
        source_payload = progress.pop("immutable_source", {})
        generation = self.generation(session, run_id, job_id)
        previous = self.previous_progress(session, run_id=run_id, kind=kind, group_id=group_id,
            source_sha256=source_sha256, content_key=progress.get("content_key", ""))
        if previous is not None:
            for key in ("responses", "request_pins", "history", "last_failure", "provider_refusal"):
                if key in previous:
                    progress[key] = previous[key]
            progress["inherited_generations"] = generation
            proof = previous.get("last_failure") or previous.get("provider_refusal", {})
            if proof.get("retry_safe") is True or proof.get("dispatch_class") == "definite_refusal":
                progress["manual_resume_retry"] = {"request_key": proof.get("request_key"), "call_id": proof.get("call_id")}
        session.execute(text(
            "INSERT INTO stage_ai_unit(stage_ai_unit_id,stage_chain_run_id,comparison_ai_job_id,kind,group_id,source_sha256,payload,progress,generation) "
            "VALUES(:unit,:run,:job,:kind,:group,:sha,CAST(:payload AS jsonb),CAST(:progress AS jsonb),:generation) "
            "ON CONFLICT(stage_chain_run_id,kind,group_id,source_sha256,generation) DO NOTHING"
        ), {"unit": unit_id, "run": run_id, "kind": kind, "group": group_id,
            "sha": source_sha256, "payload": canonical_json(source_payload),
            "progress": canonical_json(progress), "job": job_id, "generation": generation})
        row = session.execute(text(
            "SELECT * FROM stage_ai_unit WHERE stage_chain_run_id=:run AND kind=:kind "
            "AND group_id=:group AND source_sha256=:sha AND generation=:generation FOR UPDATE"
        ), {"run": run_id, "kind": kind, "group": group_id, "sha": source_sha256, "generation": generation}).mappings().one()
        result = dict(row)
        if result["comparison_ai_job_id"] != job_id:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_unit_job_pin_mismatch")
        if result["payload"] != source_payload:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_unit_source_pin_mismatch")
        stored_progress = dict(result["progress"])
        result["source_payload"] = result["payload"]
        result["payload"] = stored_progress
        if stored_progress.get("content_key") != progress.get("content_key"):
            history = list(stored_progress.get("history", ()))
            if stored_progress:
                history.append({key: value for key, value in stored_progress.items() if key != "history"})
            progress["history"] = history
            self.update_unit(session, str(result["stage_ai_unit_id"]), payload=progress, state="queued")
            result.update(payload=progress, state="queued", failure_reason=None)
        return result

    def update_unit(self, session: Session, unit_id: str, *, payload: Mapping[str, Any],
                    state: str, reason: str | None = None, job_id: str | None = None) -> None:
        session.execute(text(
            "UPDATE stage_ai_unit SET progress=CAST(:payload AS jsonb),state=:state,failure_reason=:reason, "
            "updated_at=clock_timestamp() "
            "WHERE stage_ai_unit_id=:unit"
        ), {"unit": unit_id, "payload": canonical_json(payload), "state": state,
            "reason": reason})

    def answer(self, session: Session, *, run_id: str, kind: str, content_key: str) -> dict[str, Any] | None:
        table, _prefix, _field = ANSWER_TABLES[kind]
        row = session.execute(text(
            f"SELECT * FROM {table} WHERE stage_chain_run_id=:run AND content_key=:key"
        ), {"run": run_id, "key": content_key}).mappings().first()
        return None if row is None else dict(row)

    def latest_answers(self, session: Session, *, run_id: str, kind: str) -> dict[str, dict[str, Any]]:
        table, _prefix, _field = ANSWER_TABLES[kind]
        rows = session.execute(text(
            f"SELECT a.* FROM {table} a JOIN stage_ai_unit u ON u.stage_ai_unit_id=a.stage_ai_unit_id "
            "WHERE a.stage_chain_run_id=:run AND u.state='completed' ORDER BY a.created_at"
        ), {"run": run_id}).mappings()
        return {str(row["group_id"]): dict(row) for row in rows}

    def save_answer(self, session: Session, *, run_id: str, kind: str, unit: Mapping[str, Any],
                    content_key: str, value: Any, model_identity: Mapping[str, Any]) -> None:
        table, prefix, field = ANSWER_TABLES[kind]
        session.execute(text(
            f"INSERT INTO {table}({table}_id,stage_chain_run_id,stage_ai_unit_id,content_key,group_id,source_sha256,{field},model_identity) "
            "VALUES(:id,:run,:unit,:key,:group,:sha,CAST(:value AS jsonb),CAST(:model AS jsonb)) "
            "ON CONFLICT(stage_chain_run_id,content_key) DO NOTHING"
        ), {"id": f"{prefix}_{new_ulid()}", "run": run_id, "unit": unit["stage_ai_unit_id"],
            "key": content_key, "group": unit["group_id"], "sha": unit["source_sha256"],
            "value": canonical_json(value), "model": canonical_json(model_identity)})

    def prior_call(self, session: Session, *, job_id: str, request_sha256: str) -> dict[str, Any] | None:
        row = session.execute(text(
            "SELECT c.comparison_model_call_id,c.state,c.error_code FROM comparison_model_call c "
            "JOIN comparison_work w ON w.comparison_work_id=c.comparison_work_id "
            "JOIN comparison_ai_job j ON j.comparison_ai_job_id=w.comparison_ai_job_id "
            "WHERE j.stage_chain_run_id=(SELECT stage_chain_run_id FROM comparison_ai_job WHERE comparison_ai_job_id=:job) "
            "AND c.request_sha256=:sha ORDER BY CASE WHEN c.state IN ('unknown','prepared','sent') THEN 0 "
            "WHEN c.state='completed' THEN 1 ELSE 2 END,c.prepared_at DESC LIMIT 1"
        ), {"job": job_id, "sha": request_sha256}).mappings().first()
        return None if row is None else dict(row)

    def call_identities(self, session: Session, call_ids: list[str]) -> list[dict[str, Any]]:
        return [dict(row) for row in session.execute(text(
            "SELECT c.comparison_model_call_id AS call_id,c.connection_revision_id,c.provider_mode,c.model_identity,"
            "j.comparison_ai_job_id AS job_id,j.pinned_model FROM comparison_model_call c "
            "JOIN comparison_work w ON w.comparison_work_id=c.comparison_work_id "
            "JOIN comparison_ai_job j ON j.comparison_ai_job_id=w.comparison_ai_job_id "
            "WHERE c.comparison_model_call_id=ANY(CAST(:ids AS text[])) ORDER BY c.prepared_at,c.comparison_model_call_id"
        ), {"ids": call_ids}).mappings()]

    def authorize_refusal_retry(self, session: Session, *, run_id: str, job_id: str) -> None:
        """An explicit resume can retry only a saved proven pre-processing refusal."""
        rows = session.execute(text(
            "SELECT stage_ai_unit_id,progress,state FROM stage_ai_unit "
            "WHERE stage_chain_run_id=:run AND comparison_ai_job_id=:job FOR UPDATE"
        ), {"run": run_id, "job": job_id}).mappings()
        for row in rows:
            progress = dict(row["progress"])
            refusal = progress.get("provider_refusal", {})
            if refusal.get("kind") not in {"auth", "quota"} or not (
                refusal.get("dispatch_class") == "definite_refusal" or refusal.get("retry_safe") is True
            ):
                continue
            progress["manual_resume_retry"] = {
                "request_key": refusal["request_key"], "call_id": refusal["call_id"],
            }
            self.update_unit(session, row["stage_ai_unit_id"], payload=progress, state=row["state"])

    def pause_run(self, session: Session, run_id: str, reason: str) -> None:
        session.execute(text(
            "UPDATE stage_chain_run SET state='paused',pause_reason=:reason,updated_at=clock_timestamp() "
            "WHERE stage_chain_run_id=:run AND state IN ('queued','running','paused')"
        ), {"run": run_id, "reason": reason})

    def not_checked_graphics(self, session: Session, *, run_id: str, snapshot: Mapping[str, Any]) -> int:
        left_counts: dict[str, int] = {}
        right_counts: dict[str, int] = {}
        paired = [link for link in snapshot["links"] if link["relation"] == "paired"]
        for link in paired:
            left_counts[link["left_profile_id"]] = left_counts.get(link["left_profile_id"], 0) + 1
            right_counts[link["right_profile_id"]] = right_counts.get(link["right_profile_id"], 0) + 1
        for link in paired:
            reason = "stage_graphic_bridge_unavailable" if (
                left_counts[link["left_profile_id"]] == right_counts[link["right_profile_id"]] == 1
            ) else "stage_graphic_requires_one_to_one"
            key = digest({"link": link["stage_link_item_id"], "reason": reason})
            session.execute(text(
                "INSERT INTO stage_graphic_evidence(stage_graphic_evidence_id,stage_chain_run_id,stage_link_item_id, "
                "left_profile_id,right_profile_id,status,reason,regions,content_key) "
                "VALUES(:id,:run,:link,:left,:right,'not_checked',:reason,'[]'::jsonb,:key) "
                "ON CONFLICT(stage_chain_run_id,content_key) DO NOTHING"
            ), {"id": f"sge_{new_ulid()}", "run": run_id, "link": link["stage_link_item_id"],
                "left": link["left_profile_id"], "right": link["right_profile_id"], "reason": reason, "key": key})
        return len(paired)
