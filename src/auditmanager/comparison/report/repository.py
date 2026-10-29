"""The statements over ``comparison_report``, ``comparison_report_part`` and ``comparison_report_artifact`` (`CMP-VC-REPORT-01`).

Statements only, as ``comparison.work`` and ``comparison.ai_jobs`` do: every method takes the caller's session and **never commits**; the service
and the handler own the transactions. Each state change names the states it expects (``WHERE state = ANY(...)``), so a lost race is an answer of
``False``, never a quiet overwrite, and the table's trigger refuses an edge it does not declare. ``comparison_report_artifact`` is append-only
(a published file is never rewritten: a rebuilt PDF is a newer row of the same kind). ``comparison_ai_job`` is not written here: the report names
its job in ``comparison_ai_job_id`` and the shared core owns the job.

A report's **one live job** is held by this table: ``comparison_ai_job_id`` is unique and is set once, by the one statement that moves a
``draft`` to ``queued`` (:meth:`ReportRepository.link_job`); a second start finds a report that is not a draft.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import ComparisonReportArtifactId, ComparisonReportId, ComparisonReportPartId

__all__ = ["ArtifactRow", "PartRow", "ReportRepository", "ReportRow"]

_COLUMNS: Final[str] = (
    "comparison_report_id AS report_id, project_uid, document_uid, comparison_series_id AS series_id, kind, source, state, stage, "
    "comparison_ai_job_id AS job_id, estimate, estimate_digest, reuse, source_name, source_sha256, "
    "prepared_from_report_id AS prepared_from_id, failure_reason, deleted_at, actor_user_uid, created_at, updated_at, finished_at"
)
_INSERT = text(
    "INSERT INTO comparison_report (comparison_report_id, project_uid, document_uid, comparison_series_id, kind, source, estimate, "
    "estimate_digest, reuse, source_name, source_sha256, prepared_from_report_id, actor_user_uid, actor_label, command_id) "
    "VALUES (:id, :project, :document, :series, :kind, :source, CAST(:estimate AS jsonb), :digest, :reuse, :name, :sha, :prepared, "
    ":actor, :label, :command)"
)
_GET = text(f"SELECT {_COLUMNS} FROM comparison_report WHERE comparison_report_id = :id")
_GET_LOCKED = text(f"SELECT {_COLUMNS} FROM comparison_report WHERE comparison_report_id = :id FOR UPDATE")
_BY_JOB = text(f"SELECT {_COLUMNS} FROM comparison_report WHERE comparison_ai_job_id = :job")
_LIST = text(
    f"SELECT {_COLUMNS} FROM comparison_report WHERE comparison_series_id = :series AND deleted_at IS NULL "
    "AND (CAST(:after_at AS timestamptz) IS NULL OR (created_at, comparison_report_id) < (:after_at, :after_id)) "
    "ORDER BY created_at DESC, comparison_report_id DESC LIMIT :limit"
)
#: ``draft -> queued`` and the job, in one statement: a report that is not a draft (or already holds a job) is not moved.
_LINK_JOB = text(
    "UPDATE comparison_report SET state = 'queued', stage = :stage, comparison_ai_job_id = :job, updated_at = clock_timestamp() "
    "WHERE comparison_report_id = :id AND state = 'draft' AND comparison_ai_job_id IS NULL"
)
_MOVE = text(
    "UPDATE comparison_report SET state = :to_state, stage = :stage, failure_reason = :reason, updated_at = clock_timestamp(), "
    "finished_at = CASE WHEN :terminal THEN coalesce(finished_at, clock_timestamp()) ELSE NULL END "
    "WHERE comparison_report_id = :id AND state = ANY (CAST(:from_states AS text[]))"
)
_SET_STAGE = text(
    "UPDATE comparison_report SET stage = :stage, updated_at = clock_timestamp() WHERE comparison_report_id = :id"
)
_TOMBSTONE = text(
    "UPDATE comparison_report SET deleted_at = clock_timestamp(), updated_at = clock_timestamp() "
    "WHERE comparison_report_id = :id AND deleted_at IS NULL"
)
_PART_COLUMNS: Final[str] = (
    "p.comparison_report_part_id AS part_id, p.comparison_report_id AS report_id, p.comparison_transition_id AS transition_id, "
    "p.analysis, p.verification, p.selection, p.facts, p.warnings, p.points, p.questions, p.updated_at"
)
_PARTS = text(
    f"SELECT {_PART_COLUMNS} FROM comparison_report_part p JOIN comparison_transition t "
    "ON t.comparison_transition_id = p.comparison_transition_id WHERE p.comparison_report_id = :id ORDER BY t.transition_no"
)
_PART = text(
    f"SELECT {_PART_COLUMNS} FROM comparison_report_part p WHERE p.comparison_report_id = :id AND p.comparison_transition_id = :transition"
)
_ADD_PART = text(
    "INSERT INTO comparison_report_part (comparison_report_part_id, comparison_report_id, comparison_transition_id, analysis, "
    "verification, selection, facts, warnings, points, questions) VALUES (:part, :id, :transition, :analysis, :verification, "
    ":selection, CAST(:facts AS jsonb), :warnings, :points, :questions) "
    "ON CONFLICT (comparison_report_id, comparison_transition_id) DO NOTHING"
)
_SET_PART = text(
    "UPDATE comparison_report_part SET analysis = :analysis, verification = :verification, selection = :selection, "
    "facts = CAST(:facts AS jsonb), warnings = :warnings, points = :points, questions = :questions, updated_at = clock_timestamp() "
    "WHERE comparison_report_id = :id AND comparison_transition_id = :transition"
)
#: A finished part of an earlier report of the same series and transition under the same content key (never a deleted report's, never this one's).
_REUSABLE = text(
    "SELECT p.analysis, p.verification, p.selection, p.facts, p.warnings, p.points, p.questions "
    "FROM comparison_report_part p JOIN comparison_report r ON r.comparison_report_id = p.comparison_report_id "
    "WHERE r.comparison_series_id = :series AND p.comparison_transition_id = :transition AND r.comparison_report_id <> :self "
    "AND r.deleted_at IS NULL AND r.kind = :kind AND p.facts ->> 'content_key' = :key "
    "AND ((r.kind = 'client' AND p.selection = 'done') OR (r.kind = 'analytic' AND p.analysis = 'done' AND p.verification = 'done')) "
    "ORDER BY p.updated_at DESC, p.comparison_report_part_id DESC LIMIT 1"
)
_ADD_ARTIFACT = text(
    "INSERT INTO comparison_report_artifact (comparison_report_artifact_id, comparison_report_id, kind, blob_id, sha256, size_bytes) "
    "VALUES (:id, :report, :kind, :blob, :sha, :size) RETURNING created_at"
)
_ARTIFACTS = text(
    "SELECT comparison_report_artifact_id AS artifact_id, comparison_report_id AS report_id, kind, blob_id, sha256, size_bytes, created_at "
    "FROM comparison_report_artifact WHERE comparison_report_id = :id ORDER BY created_at, comparison_report_artifact_id"
)
_OTHER_LIVE_ITEMS = text(
    "SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id = :job AND terminal_at IS NULL AND comparison_work_id <> :me"
)
_OTHER_LIVE_UNITS = text(
    "SELECT count(*) FROM comparison_work WHERE comparison_ai_job_id = :job AND terminal_at IS NULL AND comparison_work_id <> :me "
    "AND payload ->> 'unit' = 'transition'"
)
_PROJECT_NAME = text("SELECT name FROM project WHERE project_uid = :project")
_TRANSITIONS = text(
    "SELECT transition_no, comparison_transition_id FROM comparison_transition WHERE comparison_series_id = :series ORDER BY transition_no"
)


@dataclass(frozen=True, slots=True)
class ReportRow:
    report_id: str
    project_uid: str
    document_uid: str
    series_id: str
    kind: str
    source: str
    state: str
    stage: str | None
    job_id: str | None
    estimate: Mapping[str, Any]
    estimate_digest: str
    reuse: bool
    source_name: str | None
    source_sha256: str
    prepared_from_id: str | None
    failure_reason: str | None
    deleted_at: datetime | None
    actor_user_uid: str
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class PartRow:
    part_id: str
    report_id: str
    transition_id: str
    analysis: str | None
    verification: str | None
    selection: str | None
    facts: Mapping[str, Any] | None
    warnings: int | None
    points: int | None
    questions: int | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ArtifactRow:
    artifact_id: str
    report_id: str
    kind: str
    blob_id: str
    sha256: str
    size_bytes: int
    created_at: datetime


def _report(row: Any) -> ReportRow:
    values = {name: row[name] for name in ReportRow.__dataclass_fields__ if name != "estimate"}
    return ReportRow(estimate=dict(row["estimate"]), **values)


def _part(row: Any) -> PartRow:
    values = {name: row[name] for name in PartRow.__dataclass_fields__ if name != "facts"}
    return PartRow(facts=None if row["facts"] is None else dict(row["facts"]), **values)


class ReportRepository:
    """Stateless; every method takes the caller's session and never commits."""

    __slots__ = ()

    # -- the report ---------------------------------------------------------------------------------
    def insert(
        self, session: Session, *, project_uid: str, document_uid: str, series_id: str, kind: str, source: str,
        estimate: Mapping[str, Any], reuse: bool, source_name: str | None, source_sha256: str, prepared_from_id: str | None,
        actor_user_uid: str, actor_label: str, command_id: str,
    ) -> str:
        report_id = str(ComparisonReportId.new())
        session.execute(_INSERT, {
            "id": report_id, "project": project_uid, "document": document_uid, "series": series_id, "kind": kind, "source": source,
            "estimate": json.dumps(dict(estimate), sort_keys=True, default=str), "digest": estimate["estimate_digest"], "reuse": reuse,
            "name": source_name, "sha": source_sha256, "prepared": prepared_from_id, "actor": actor_user_uid, "label": actor_label,
            "command": command_id,
        })
        return report_id

    def get(self, session: Session, report_id: str, *, lock: bool = False) -> ReportRow | None:
        row = session.execute(_GET_LOCKED if lock else _GET, {"id": report_id}).mappings().first()
        return None if row is None else _report(row)

    def by_job(self, session: Session, job_id: str) -> ReportRow | None:
        row = session.execute(_BY_JOB, {"job": job_id}).mappings().first()
        return None if row is None else _report(row)

    def list_for_series(
        self, session: Session, series_id: str, *, after: tuple[datetime, str] | None, limit: int,
    ) -> list[ReportRow]:
        rows = session.execute(_LIST, {
            "series": series_id, "after_at": None if after is None else after[0], "after_id": None if after is None else after[1],
            "limit": limit,
        }).mappings()
        return [_report(row) for row in rows]

    def link_job(self, session: Session, report_id: str, job_id: str, *, stage: str) -> bool:
        """The one statement that starts a report: ``draft -> queued`` with its job. ``False`` for a report that is not a draft."""
        return session.execute(_LINK_JOB, {"id": report_id, "job": job_id, "stage": stage}).rowcount == 1

    def move(
        self, session: Session, report_id: str, *, from_states: Sequence[str], to_state: str, stage: str | None = None,
        failure_reason: str | None = None,
    ) -> bool:
        """One state edge, guarded by the states it is taken from; the database refuses an edge it does not declare."""
        return session.execute(_MOVE, {
            "id": report_id, "to_state": to_state, "stage": stage, "reason": failure_reason,
            "terminal": to_state in ("completed", "partial", "failed", "cancelled"), "from_states": list(from_states),
        }).rowcount == 1

    def set_stage(self, session: Session, report_id: str, stage: str) -> None:
        session.execute(_SET_STAGE, {"id": report_id, "stage": stage})

    def tombstone(self, session: Session, report_id: str) -> bool:
        return session.execute(_TOMBSTONE, {"id": report_id}).rowcount == 1

    def project_name(self, session: Session, project_uid: str) -> str:
        return str(session.execute(_PROJECT_NAME, {"project": project_uid}).scalar_one_or_none() or "")

    def transition_numbers(self, session: Session, series_id: str) -> dict[int, str]:
        """The transitions of a series by their number (the ``N`` of «## N. … A → B»): ``{transition_no: comparison_transition_id}``."""
        return {int(n): str(i) for n, i in session.execute(_TRANSITIONS, {"series": series_id}).all()}

    # -- the parts ----------------------------------------------------------------------------------
    def parts(self, session: Session, report_id: str) -> list[PartRow]:
        return [_part(row) for row in session.execute(_PARTS, {"id": report_id}).mappings()]

    def part(self, session: Session, report_id: str, transition_id: str) -> PartRow | None:
        row = session.execute(_PART, {"id": report_id, "transition": transition_id}).mappings().first()
        return None if row is None else _part(row)

    def add_part(
        self, session: Session, report_id: str, transition_id: str, *, analysis: str | None = None, verification: str | None = None,
        selection: str | None = None, facts: Mapping[str, Any] | None = None, warnings: int | None = None,
        points: int | None = None, questions: int | None = None,
    ) -> None:
        """The progress of one transition; nothing is written if the report already has a part for it."""
        session.execute(_ADD_PART, {
            "part": str(ComparisonReportPartId.new()), "id": report_id, "transition": transition_id, "analysis": analysis,
            "verification": verification, "selection": selection,
            "facts": None if facts is None else json.dumps(dict(facts), sort_keys=True, ensure_ascii=False),
            "warnings": warnings, "points": points, "questions": questions,
        })

    def set_part(
        self, session: Session, report_id: str, transition_id: str, *, analysis: str | None, verification: str | None,
        selection: str | None, facts: Mapping[str, Any] | None, warnings: int | None, points: int | None, questions: int | None,
    ) -> bool:
        return session.execute(_SET_PART, {
            "id": report_id, "transition": transition_id, "analysis": analysis, "verification": verification, "selection": selection,
            "facts": None if facts is None else json.dumps(dict(facts), sort_keys=True, ensure_ascii=False),
            "warnings": warnings, "points": points, "questions": questions,
        }).rowcount == 1

    def reusable(
        self, session: Session, *, series_id: str, transition_id: str, kind: str, content_key: str, report_id: str,
    ) -> PartRow | None:
        row = session.execute(_REUSABLE, {
            "series": series_id, "transition": transition_id, "kind": kind, "key": content_key, "self": report_id,
        }).mappings().first()
        if row is None:
            return None
        return PartRow(
            part_id="", report_id="", transition_id=transition_id, analysis=row["analysis"], verification=row["verification"],
            selection=row["selection"], facts=None if row["facts"] is None else dict(row["facts"]), warnings=row["warnings"],
            points=row["points"], questions=row["questions"], updated_at=datetime.min,
        )

    # -- the artifacts (append-only) ---------------------------------------------------------------
    def add_artifact(self, session: Session, report_id: str, *, kind: str, blob_id: str, sha256: str, size_bytes: int) -> ArtifactRow:
        artifact_id = str(ComparisonReportArtifactId.new())
        created = session.execute(_ADD_ARTIFACT, {
            "id": artifact_id, "report": report_id, "kind": kind, "blob": blob_id, "sha": sha256, "size": size_bytes,
        }).scalar_one()
        return ArtifactRow(artifact_id, report_id, kind, blob_id, sha256, size_bytes, created)

    def artifacts(self, session: Session, report_id: str) -> list[ArtifactRow]:
        return [
            ArtifactRow(**{name: row[name] for name in ArtifactRow.__dataclass_fields__})
            for row in session.execute(_ARTIFACTS, {"id": report_id}).mappings()
        ]

    @staticmethod
    def latest(artifacts: Sequence[ArtifactRow], kind: str) -> ArtifactRow | None:
        """The newest artifact of a kind (a rebuilt PDF is a newer row; the older one stays)."""
        found = [a for a in artifacts if a.kind == kind]
        return found[-1] if found else None

    # -- the job's items (a read) -----------------------------------------------------------------
    def other_live_units(self, session: Session, job_id: str, work_id: str) -> int:
        """Live transition items of the job other than ``work_id``: the model work that is still to come (the final item makes no call of the client kind)."""
        return int(session.execute(_OTHER_LIVE_UNITS, {"job": job_id, "me": work_id}).scalar_one())

    def other_live_items(self, session: Session, job_id: str, work_id: str) -> int:
        """Live work items of the job other than ``work_id`` (the final item waits for every other one to end)."""
        return int(session.execute(_OTHER_LIVE_ITEMS, {"job": job_id, "me": work_id}).scalar_one())
