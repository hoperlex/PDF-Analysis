"""The memory's read model: a case's current state, its detail, a page of cases, the settings in force and the counts (`DECISION-MEMORY-01`
sections 3.7 and 7.3).

Read-only SQL over ``decision_memory_case_current`` (the view of migration ``0061``) and the content tables. The memory is **not a
decision authority** (`ADR-0027` decision 3): nothing here reads a verdict into a product behaviour; a caller shows these as recorded
history. A **forgotten** case answers its tombstone only -- the content rows are gone, and this module never invents them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.decision_memory.settings import SETTING_DATA_CLASS, SETTING_DEFAULTS, SETTING_TRAINING_USE, MemorySettings
from auditmanager.decision_memory.status import CASE_STATUSES, STATUS_FORGOTTEN
from auditmanager.shared.errors import DomainError, ErrorCode

#: The page size ceiling of :meth:`MemoryReader.list_cases`.
MAX_PAGE: Final[int] = 200

_CURRENT_COLUMNS = (
    "case_id, category, section_code, data_class, crop_state, origin_project_uid, captured_at, status, status_event_id, "
    "status_reason_code, status_changed_at, current_decision_id, current_verdict, current_severity, current_origin_kind, "
    "current_decided_at, decision_count"
)

_SETTINGS = text(
    "SELECT DISTINCT ON (setting_name) setting_name, value, revision FROM decision_memory_setting_event "
    "ORDER BY setting_name, revision DESC"
)
_DECISIONS = text(
    "SELECT d.memory_decision_id, d.event_type, d.verdict, d.severity, d.origin_kind, d.author_user_uid, d.decided_at, t.comment "
    "FROM decision_memory_decision d LEFT JOIN decision_memory_decision_text t ON t.memory_decision_id = d.memory_decision_id "
    "WHERE d.case_id = :case_id ORDER BY d.decided_at, d.memory_decision_id"
)
_COMMENTS = text(
    "SELECT case_id, comment_id, author_user_uid, comment, decided_at FROM decision_memory_comment "
    "WHERE case_id IN :case_ids ORDER BY case_id, decided_at, comment_id"
).bindparams(bindparam("case_ids", expanding=True))
_CONTENT = text(
    "SELECT revision, finding_text, recommendation_text, proposed_severity, required_value, stated_value, stage_id, "
    "analysis_profile_id, prompt_bundle_id, provider_mode FROM decision_memory_content WHERE case_id = :case_id "
    "ORDER BY revision DESC LIMIT 1"
)
_EVIDENCE = text(
    "SELECT ordinal, page_number, quote, char_start, char_end, block_ref, bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_unit, bbox_origin "
    "FROM decision_memory_evidence WHERE case_id = :case_id AND revision = :revision ORDER BY ordinal"
)
_NORM_REFS = text(
    "SELECT ordinal, norms_snapshot_id, norm_document_id, norm_paragraph_id, designation, clause_number, page_label, quote, "
    "citation_state FROM decision_memory_norm_ref WHERE case_id = :case_id AND revision = :revision ORDER BY ordinal"
)
_CROPS = text(
    "SELECT crop_id, crop_ordinal, evidence_ordinal, kind, selection_rule, page_number, bbox_x0, bbox_y0, bbox_x1, bbox_y1, sha256, "
    "size_bytes, media_type, width_px, height_px, portal_description FROM decision_memory_crop "
    "WHERE case_id = :case_id AND revision = :revision ORDER BY crop_ordinal"
)
_STATUS_EVENTS = text(
    "SELECT status_event_id, kind, reason_code, actor_user_uid, command_id, owner_permission_ref, forgotten_content_sha256, created_at "
    "FROM decision_memory_status_event WHERE case_id = :case_id ORDER BY created_at, status_event_id"
)
_COUNTS = text(
    "SELECT status, data_class, count(*) AS cases FROM decision_memory_case_current GROUP BY status, data_class "
    "ORDER BY status, data_class"
)
_DECISION_COUNT = text("SELECT count(*) FROM decision_memory_decision")


@dataclass(frozen=True, slots=True)
class CaseSummary:
    """One row of ``decision_memory_case_current``."""

    case_id: str
    category: str
    section_code: str | None
    data_class: str
    crop_state: str
    origin_project_uid: str
    captured_at: datetime
    status: str
    status_event_id: str | None
    status_reason_code: str | None
    status_changed_at: datetime | None
    current_decision_id: str | None
    current_verdict: str | None
    current_severity: str | None
    current_origin_kind: str | None
    current_decided_at: datetime | None
    decision_count: int


@dataclass(frozen=True, slots=True)
class CaseDetail:
    """A case with everything it keeps. ``content`` is ``None`` for a forgotten case: it answers its tombstone and nothing else.

    ``comments`` are the experts' ``comment`` events kept beside the decisions (``decision_memory_comment``), oldest first, each
    ``{comment_id, author_user_uid, comment, decided_at}``; empty for a forgotten case. The 1.51.0 API contract has no field for them.
    """

    summary: CaseSummary
    decisions: tuple[dict[str, Any], ...]
    content: dict[str, Any] | None
    evidence: tuple[dict[str, Any], ...]
    norm_refs: tuple[dict[str, Any], ...]
    crops: tuple[dict[str, Any], ...]
    status_events: tuple[dict[str, Any], ...]
    comments: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class CasePage:
    items: tuple[CaseSummary, ...]
    #: ``(captured_at, case_id)`` of the last item when more exist, to pass back as ``after``.
    next_after: tuple[datetime, str] | None


@dataclass(frozen=True, slots=True)
class MemoryCounts:
    """What the memory holds: cases by standing and data class, and the decisions."""

    by_status_and_class: tuple[tuple[str, str, int], ...]
    cases: int
    decisions: int


class MemoryReader:
    """Typed reads. Stateless; the caller owns the transaction."""

    def settings(self, session: Session) -> MemorySettings:
        """The installation settings in force; a setting never journalled has its default (``test``, ``off``)."""
        found = {name: (value, int(revision)) for name, value, revision in session.execute(_SETTINGS).all()}
        data_class = found.get(SETTING_DATA_CLASS, (SETTING_DEFAULTS[SETTING_DATA_CLASS], 0))
        training = found.get(SETTING_TRAINING_USE, (SETTING_DEFAULTS[SETTING_TRAINING_USE], 0))
        return MemorySettings(
            data_class=data_class[0], training_use=training[0],
            data_class_revision=data_class[1], training_use_revision=training[1],
        )

    def case_summary(self, session: Session, case_id: str) -> CaseSummary | None:
        row = session.execute(
            text(f"SELECT {_CURRENT_COLUMNS} FROM decision_memory_case_current WHERE case_id = :case_id"), {"case_id": case_id}
        ).mappings().one_or_none()
        return None if row is None else CaseSummary(**row)

    def list_cases(
        self,
        session: Session,
        *,
        section: str | None = None,
        category: str | None = None,
        verdict: str | None = None,
        status: str | None = None,
        data_class: str | None = None,
        origin_project_uid: str | None = None,
        after: tuple[datetime, str] | None = None,
        limit: int = 50,
    ) -> CasePage:
        """A page of cases, newest capture first. Every filter is optional; an unknown ``status`` is a validation error."""
        if status is not None and status not in CASE_STATUSES:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="status", constraint="enum")
        if not 1 <= limit <= MAX_PAGE:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="limit", constraint="range")
        rows = session.execute(
            text(
                f"SELECT {_CURRENT_COLUMNS} FROM decision_memory_case_current WHERE "
                "(CAST(:section AS text) IS NULL OR section_code = :section) "
                "AND (CAST(:category AS text) IS NULL OR category = :category) "
                "AND (CAST(:verdict AS text) IS NULL OR current_verdict = :verdict) "
                "AND (CAST(:status AS text) IS NULL OR status = :status) "
                "AND (CAST(:data_class AS text) IS NULL OR data_class = :data_class) "
                "AND (CAST(:project AS text) IS NULL OR origin_project_uid = :project) "
                "AND (CAST(:after_at AS timestamptz) IS NULL OR (captured_at, case_id) < (:after_at, :after_id)) "
                "ORDER BY captured_at DESC, case_id DESC LIMIT :limit"
            ),
            {
                "section": section, "category": category, "verdict": verdict, "status": status, "data_class": data_class,
                "project": origin_project_uid, "after_at": None if after is None else after[0],
                "after_id": None if after is None else after[1], "limit": limit + 1,
            },
        ).mappings().all()
        items = tuple(CaseSummary(**row) for row in rows[:limit])
        more = len(rows) > limit
        return CasePage(items=items, next_after=(items[-1].captured_at, items[-1].case_id) if more and items else None)

    def comments_for_cases(self, session: Session, case_ids: Sequence[str]) -> dict[str, tuple[dict[str, Any], ...]]:
        """The experts' comments of these cases, oldest first: ``{case_id: ({comment_id, author_user_uid, comment, decided_at}, ...)}``.

        A case without comments, and an unknown or forgotten one, is not a key. The standing of a case is not read here: a caller that
        feeds a hint or a prompt reads the standing of the case (``withdrawn`` is out) before it uses what this answers.
        """
        wanted = sorted({value for value in case_ids if isinstance(value, str)})
        found: dict[str, list[dict[str, Any]]] = {}
        if wanted:
            for row in session.execute(_COMMENTS, {"case_ids": wanted}).mappings():
                found.setdefault(row["case_id"], []).append({key: row[key] for key in row if key != "case_id"})
        return {case_id: tuple(rows) for case_id, rows in found.items()}

    def get_case(self, session: Session, case_id: str) -> CaseDetail | None:
        """The case with its decisions, content, evidence, normative references, crops, comments and status history; ``None`` when unknown."""
        summary = self.case_summary(session, case_id)
        if summary is None:
            return None
        params = {"case_id": case_id}
        decisions = tuple(dict(row) for row in session.execute(_DECISIONS, params).mappings())
        events = tuple(dict(row) for row in session.execute(_STATUS_EVENTS, params).mappings())
        content: dict[str, Any] | None = None
        evidence: tuple[dict[str, Any], ...] = ()
        norm_refs: tuple[dict[str, Any], ...] = ()
        crops: tuple[dict[str, Any], ...] = ()
        comments: tuple[dict[str, Any], ...] = ()
        if summary.status != STATUS_FORGOTTEN:
            comments = self.comments_for_cases(session, [case_id]).get(case_id, ())
            head = session.execute(_CONTENT, params).mappings().one_or_none()
            if head is not None:
                content = dict(head)
                keyed = {"case_id": case_id, "revision": head["revision"]}
                evidence = tuple(dict(row) for row in session.execute(_EVIDENCE, keyed).mappings())
                norm_refs = tuple(dict(row) for row in session.execute(_NORM_REFS, keyed).mappings())
                crops = tuple(dict(row) for row in session.execute(_CROPS, keyed).mappings())
        else:
            # A forgotten case keeps its decisions' identities (verdict, severity, author, time) but no words of the expert.
            decisions = tuple({**row, "comment": None} for row in decisions)
        return CaseDetail(summary, decisions, content, evidence, norm_refs, crops, events, comments)

    def counts(self, session: Session) -> MemoryCounts:
        rows = tuple((str(status), str(klass), int(cases)) for status, klass, cases in session.execute(_COUNTS).all())
        return MemoryCounts(
            by_status_and_class=rows, cases=sum(cases for _, _, cases in rows),
            decisions=int(session.execute(_DECISION_COUNT).scalar_one()),
        )
