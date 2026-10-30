"""The statements of the two tables part B writes: ``comparison_spec_extraction`` and ``comparison_spec_comparison`` (`CMP-VC-SPEC-01`).

Stateless; every method takes the caller's session and never commits. The identity columns, the content key and the state edges are
the database's (migration ``0040``): an extraction is immutable and content-keyed (``UNIQUE (project_uid, content_key)``), a
comparison is one row per ``(transition, source)`` whose state moves only along the allowed edges (``queued -> running ->
completed | incomplete | failed | cancelled``, and a terminal state back to ``queued`` for a re-run).

The job row (``comparison_ai_job``) is read, never written, here: the AI-job core is its only writer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import new_ulid

__all__ = ["ComparisonRow", "ExtractionRow", "SpecificationRepository", "TransitionScope"]

_EXTRACTION_COLUMNS = (
    "comparison_spec_extraction_id, project_uid, version_uid, content_key, state, prompt_version, model_identity, recorded, "
    "source_sha256, positions, coverage, comparison_model_call_id, created_at"
)
_COMPARISON_COLUMNS = (
    "c.comparison_spec_comparison_id, c.project_uid, c.document_uid, c.comparison_transition_id, c.source, c.state, c.phase, "
    "c.comparison_ai_job_id, c.extraction_a_id, c.extraction_b_id, c.sheets_a, c.sheets_b, c.coverage_a, c.coverage_b, c.totals, "
    "c.changes, c.reason, c.updated_at, j.state AS job_state"
)
_TRANSITION = text(
    "SELECT t.comparison_transition_id, t.comparison_series_id, t.transition_no, t.source_version_uid, t.target_version_uid, "
    "s.project_uid, s.document_uid FROM comparison_transition t JOIN comparison_series s "
    "ON s.comparison_series_id = t.comparison_series_id WHERE t.comparison_transition_id = :id"
)
_SERIES = text("SELECT project_uid, document_uid FROM comparison_series WHERE comparison_series_id = :id")
_TRANSITIONS = text(
    "SELECT t.comparison_transition_id, t.comparison_series_id, t.transition_no, t.source_version_uid, t.target_version_uid, "
    "s.project_uid, s.document_uid FROM comparison_transition t JOIN comparison_series s "
    "ON s.comparison_series_id = t.comparison_series_id WHERE t.comparison_series_id = :series AND t.transition_no > :after "
    "ORDER BY t.transition_no"
)
_FIND_EXTRACTION = text(f"SELECT {_EXTRACTION_COLUMNS} FROM comparison_spec_extraction WHERE project_uid = :project AND content_key = :key")
_GET_EXTRACTION = text(f"SELECT {_EXTRACTION_COLUMNS} FROM comparison_spec_extraction WHERE comparison_spec_extraction_id = :id")
_INSERT_EXTRACTION = text(
    "INSERT INTO comparison_spec_extraction (comparison_spec_extraction_id, project_uid, version_uid, content_key, state, "
    "prompt_version, model_identity, recorded, source_sha256, positions, coverage, comparison_model_call_id) VALUES "
    "(:id, :project, :version, :key, :state, :prompt, :model, :recorded, :source, CAST(:positions AS jsonb), "
    "CAST(:coverage AS jsonb), :call) ON CONFLICT (project_uid, content_key) DO NOTHING"
)
_WHOLE = text(
    f"SELECT {_COMPARISON_COLUMNS} FROM comparison_spec_comparison c LEFT JOIN comparison_ai_job j "
    "ON j.comparison_ai_job_id = c.comparison_ai_job_id WHERE c.comparison_transition_id = :transition AND c.source = :source"
)
_WHOLE_OF_SERIES = text(
    f"SELECT {_COMPARISON_COLUMNS} FROM comparison_spec_comparison c JOIN comparison_transition t "
    "ON t.comparison_transition_id = c.comparison_transition_id LEFT JOIN comparison_ai_job j "
    "ON j.comparison_ai_job_id = c.comparison_ai_job_id WHERE t.comparison_series_id = :series AND c.source = 'whole'"
)
_INSERT_WHOLE = text(
    "INSERT INTO comparison_spec_comparison (comparison_spec_comparison_id, project_uid, document_uid, comparison_transition_id, "
    "source, state, phase, comparison_ai_job_id, sheets_a, sheets_b) VALUES (:id, :project, :document, :transition, 'whole', "
    "'queued', 'preparing', :job, :sheets_a, :sheets_b) ON CONFLICT (comparison_transition_id, source) DO NOTHING"
)
_RESET_WHOLE = text(
    "UPDATE comparison_spec_comparison SET state = 'queued', phase = 'preparing', comparison_ai_job_id = :job, extraction_a_id = NULL, "
    "extraction_b_id = NULL, sheets_a = :sheets_a, sheets_b = :sheets_b, coverage_a = NULL, coverage_b = NULL, totals = NULL, "
    "changes = '[]'::jsonb, reason = NULL, updated_at = clock_timestamp() WHERE comparison_transition_id = :transition "
    "AND source = 'whole' AND state IN ('completed', 'incomplete', 'failed', 'cancelled')"
)
_SET_STATE = text(
    "UPDATE comparison_spec_comparison SET state = :to_state, phase = :phase, reason = :reason, updated_at = clock_timestamp() "
    "WHERE comparison_transition_id = :transition AND source = 'whole' AND state = ANY (CAST(:from_states AS text[]))"
)
_CANCEL_OF_JOB = text(
    "UPDATE comparison_spec_comparison SET state = 'cancelled', phase = 'done', updated_at = clock_timestamp() "
    "WHERE comparison_ai_job_id = :job AND source = 'whole' AND state IN ('queued', 'running')"
)
_FINISH = text(
    "UPDATE comparison_spec_comparison SET state = :to_state, phase = 'done', extraction_a_id = :a, extraction_b_id = :b, "
    "coverage_a = CAST(:coverage_a AS jsonb), coverage_b = CAST(:coverage_b AS jsonb), totals = CAST(:totals AS jsonb), "
    "changes = CAST(:changes AS jsonb), reason = :reason, updated_at = clock_timestamp() "
    "WHERE comparison_transition_id = :transition AND source = 'whole' AND state = 'running'"
)


@dataclass(frozen=True, slots=True)
class TransitionScope:
    transition_id: str
    series_id: str
    transition_no: int
    source_version_uid: str
    target_version_uid: str
    project_uid: str
    document_uid: str


@dataclass(frozen=True, slots=True)
class ExtractionRow:
    extraction_id: str
    project_uid: str
    version_uid: str
    content_key: str
    state: str
    prompt_version: str
    model_identity: str
    recorded: bool
    source_sha256: str
    positions: list[dict[str, Any]]
    coverage: dict[str, Any]
    model_call_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ComparisonRow:
    comparison_id: str
    project_uid: str
    document_uid: str
    transition_id: str
    source: str
    state: str
    phase: str | None
    job_id: str | None
    extraction_a_id: str | None
    extraction_b_id: str | None
    sheets_a: int
    sheets_b: int
    coverage_a: dict[str, Any] | None
    coverage_b: dict[str, Any] | None
    totals: dict[str, int] | None
    changes: list[dict[str, Any]]
    reason: str | None
    updated_at: datetime
    job_state: str | None


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _scope(row: Any) -> TransitionScope:
    return TransitionScope(
        row["comparison_transition_id"], row["comparison_series_id"], int(row["transition_no"]), row["source_version_uid"],
        row["target_version_uid"], row["project_uid"], row["document_uid"],
    )


def _extraction(row: Any) -> ExtractionRow:
    return ExtractionRow(
        row["comparison_spec_extraction_id"], row["project_uid"], row["version_uid"], row["content_key"], row["state"],
        row["prompt_version"], row["model_identity"], bool(row["recorded"]), row["source_sha256"], list(_json(row["positions"])),
        dict(_json(row["coverage"])), row["comparison_model_call_id"], row["created_at"],
    )


def _comparison(row: Any) -> ComparisonRow:
    return ComparisonRow(
        row["comparison_spec_comparison_id"], row["project_uid"], row["document_uid"], row["comparison_transition_id"], row["source"],
        row["state"], row["phase"], row["comparison_ai_job_id"], row["extraction_a_id"], row["extraction_b_id"], int(row["sheets_a"]),
        int(row["sheets_b"]), None if row["coverage_a"] is None else dict(_json(row["coverage_a"])),
        None if row["coverage_b"] is None else dict(_json(row["coverage_b"])),
        None if row["totals"] is None else {k: int(v) for k, v in dict(_json(row["totals"])).items()},
        list(_json(row["changes"])), row["reason"], row["updated_at"], row["job_state"],
    )


class SpecificationRepository:
    def pin_plan(self,session:Session,transition_id:str,keys:list[str|None])->None:
        session.execute(text("UPDATE comparison_spec_comparison SET "
            "coverage_a=coalesce(coverage_a,'{}'::jsonb)||CAST(:a AS jsonb), "
            "coverage_b=coalesce(coverage_b,'{}'::jsonb)||CAST(:b AS jsonb) "
            "WHERE comparison_transition_id=:id AND source='whole'"),
            {"id":transition_id,"a":json.dumps({'planning_revision':'spec-batches-v1','source_key':keys[0]}),
                "b":json.dumps({'planning_revision':'spec-batches-v1','source_key':keys[1]})})

    def progress(self,session:Session,transition_id:str,side:str,coverage:dict)->None:
        column='coverage_a' if side=='a' else 'coverage_b'
        session.execute(text(f"UPDATE comparison_spec_comparison SET {column}=CAST(:coverage AS jsonb), "
            "updated_at=clock_timestamp() WHERE comparison_transition_id=:id AND source='whole' AND state='running'"),
            {'id':transition_id,'coverage':json.dumps(coverage,ensure_ascii=False)})

    def paid_dispatch_fence(self,session:Session,*,project_uid:str,job_id:str,request_sha256:str)->str|None:
        value=session.execute(text("SELECT c.state FROM comparison_model_call c JOIN comparison_work w "
            "ON w.comparison_work_id=c.comparison_work_id WHERE w.project_uid=:project AND "
            "((w.payload->>'ai_job_id'=:job AND c.state IN ('prepared','sent','unknown')) OR "
            "(c.request_sha256=:sha AND (c.state IN ('prepared','sent','unknown','completed') OR "
            "(c.state='failed' AND (c.response_sha256 IS NOT NULL OR c.cost_micros>0))))) "
            "ORDER BY CASE c.state WHEN 'unknown' THEN 0 WHEN 'prepared' THEN 1 WHEN 'sent' THEN 1 ELSE 2 END LIMIT 1"),
            {'project':project_uid,'job':job_id,'sha':request_sha256}).scalar_one_or_none()
        return None if value is None else str(value)

    # -- scope ----------------------------------------------------------------------------------------------------------

    def transition(self, session: Session, transition_id: str) -> TransitionScope | None:
        row = session.execute(_TRANSITION, {"id": transition_id}).mappings().first()
        return None if row is None else _scope(row)

    def series_exists(self, session: Session, series_id: str) -> bool:
        return session.execute(_SERIES, {"id": series_id}).first() is not None

    def transitions_after(self, session: Session, series_id: str, *, after_no: int) -> list[TransitionScope]:
        return [_scope(r) for r in session.execute(_TRANSITIONS, {"series": series_id, "after": after_no}).mappings()]

    # -- extractions (immutable, content-keyed) -------------------------------------------------------------------------

    def find_extraction(self, session: Session, project_uid: str, content_key: str) -> ExtractionRow | None:
        row = session.execute(_FIND_EXTRACTION, {"project": project_uid, "key": content_key}).mappings().first()
        return None if row is None else _extraction(row)

    def get_extraction(self, session: Session, extraction_id: str) -> ExtractionRow | None:
        row = session.execute(_GET_EXTRACTION, {"id": extraction_id}).mappings().first()
        return None if row is None else _extraction(row)

    def insert_extraction(
        self, session: Session, *, project_uid: str, version_uid: str, content_key: str, state: str, prompt_version: str,
        model_identity: str, recorded: bool, source_sha256: str, positions: list[dict[str, Any]], coverage: dict[str, Any],
        model_call_id: str | None,
    ) -> ExtractionRow:
        """Write the extraction, or answer the one that exists under the key (a concurrent writer's): the table is immutable."""
        session.execute(_INSERT_EXTRACTION, {
            "id": f"cse_{new_ulid()}", "project": project_uid, "version": version_uid, "key": content_key, "state": state,
            "prompt": prompt_version, "model": model_identity, "recorded": recorded, "source": source_sha256,
            "positions": json.dumps(positions, ensure_ascii=False), "coverage": json.dumps(coverage, ensure_ascii=False),
            "call": model_call_id,
        })
        found = self.find_extraction(session, project_uid, content_key)
        assert found is not None
        return found

    # -- the comparison of a transition ---------------------------------------------------------------------------------

    def whole(self, session: Session, transition_id: str) -> ComparisonRow | None:
        row = session.execute(_WHOLE, {"transition": transition_id, "source": "whole"}).mappings().first()
        return None if row is None else _comparison(row)

    def wholes_of_series(self, session: Session, series_id: str) -> dict[str, ComparisonRow]:
        return {r["comparison_transition_id"]: _comparison(r) for r in session.execute(_WHOLE_OF_SERIES, {"series": series_id}).mappings()}

    def open_whole(
        self, session: Session, scope: TransitionScope, *, job_id: str, sheets_a: int, sheets_b: int
    ) -> ComparisonRow:
        """The row of the transition for a job just started: a new one, or a terminal one taken back to ``queued``."""
        values = {"job": job_id, "sheets_a": sheets_a, "sheets_b": sheets_b, "transition": scope.transition_id}
        session.execute(_INSERT_WHOLE, {**values, "id": f"cscp_{new_ulid()}", "project": scope.project_uid, "document": scope.document_uid})
        session.execute(_RESET_WHOLE, values)
        row = self.whole(session, scope.transition_id)
        assert row is not None
        return row

    def set_state(self, session: Session, transition_id: str, *, to_state: str, from_states: tuple[str, ...], phase: str | None, reason: str | None = None) -> bool:
        done = session.execute(_SET_STATE, {
            "transition": transition_id, "to_state": to_state, "from_states": list(from_states), "phase": phase, "reason": reason,
        })
        return bool(done.rowcount)

    def cancel_of_job(self, session: Session, job_id: str) -> bool:
        return bool(session.execute(_CANCEL_OF_JOB, {"job": job_id}).rowcount)

    def finish_whole(
        self, session: Session, transition_id: str, *, state: str, extraction_a_id: str | None, extraction_b_id: str | None,
        coverage_a: dict[str, Any] | None, coverage_b: dict[str, Any] | None, totals: dict[str, int] | None,
        changes: list[dict[str, Any]], reason: str | None,
    ) -> bool:
        done = session.execute(_FINISH, {
            "transition": transition_id, "to_state": state, "a": extraction_a_id, "b": extraction_b_id,
            "coverage_a": None if coverage_a is None else json.dumps(coverage_a, ensure_ascii=False),
            "coverage_b": None if coverage_b is None else json.dumps(coverage_b, ensure_ascii=False),
            "totals": None if totals is None else json.dumps(totals), "changes": json.dumps(changes, ensure_ascii=False),
            "reason": reason,
        })
        return bool(done.rowcount)
