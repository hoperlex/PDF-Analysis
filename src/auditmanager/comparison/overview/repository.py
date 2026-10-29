"""The reads of the overview: a fixed number of set-based statements for one project, and three for the queue.

`CMP-VC-OVERVIEW-01`. Read only: every statement is a ``SELECT``; the service runs them in one read-only
``REPEATABLE READ`` transaction, so a row is never half-seen and a write is refused by the database. The statements
take the project (or the document sets of the project) and return one row per fact, never one query per set -- the
per-set reads of the matrix (``get_matrix``), the series (``list_series``) and the queue (``counts``) would be N+1
(``docs/program/tasks/CMP-VC-OVERVIEW-01.md``, P-03). The pure rules of those lanes are reused by the service; the
tables are read here with the same columns and the same order as their own repositories read them, and
``tests/integration/comparison/overview`` proves the two agree on the same data.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.matrix.model import AiLinkRecord, BuildRecord, EditRecord, PageRef
from auditmanager.comparison.matrix.repository import ProfileFact

__all__ = [
    "DocumentRow",
    "KIND_FOLLOW_UP",
    "KIND_MATRIX_BUILD",
    "KIND_PAGE_PROFILE",
    "OrderRow",
    "OverviewRepository",
    "PendingUploadRow",
    "QueueRow",
    "SeriesRow",
    "SetMetaRow",
    "TransitionRow",
    "VersionRow",
    "WorkRow",
]

#: The three work kinds the overview looks at (pinned against the lanes' own constants by a unit test).
KIND_PAGE_PROFILE: Final[str] = "page_profile"
KIND_MATRIX_BUILD: Final[str] = "matrix_build"
KIND_FOLLOW_UP: Final[str] = "series_after_preparation"
#: A batch that is not finished (the contract's ``ComparisonOverviewUpload``): everything but ``completed`` and ``cancelled``.
PENDING_UPLOAD_STATES: Final[tuple[str, ...]] = ("uploading", "proposed", "processing", "paused")
#: The contract's cap on ``ComparisonOverview.sets`` and ``pending_uploads``.
MAX_SETS: Final[int] = 1000
MAX_PENDING: Final[int] = 100

_LIVE: Final[tuple[str, ...]] = ("queued", "leased", "running", "retry_wait", "paused", "spend_unknown")


@dataclass(frozen=True, slots=True)
class DocumentRow:
    document_uid: str
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class VersionRow:
    version_uid: str
    document_uid: str
    ordinal: int
    page_count: int
    published_at: datetime


@dataclass(frozen=True, slots=True)
class SetMetaRow:
    document_uid: str
    designation: str | None
    project_stage: str | None
    section_code: str | None


@dataclass(frozen=True, slots=True)
class OrderRow:
    document_uid: str
    order_id: str
    version_uids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkRow:
    work_id: str
    kind: str
    state: str
    dedupe_key: str | None
    document_uid: str | None
    failure_reason: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SeriesRow:
    series_id: str
    document_uid: str
    state: str
    matrix_id: str
    edit_no: int
    input_sha256: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TransitionRow:
    series_id: str
    transition_no: int
    source_version_uid: str
    target_version_uid: str
    state: str
    summary: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class PendingUploadRow:
    upload_id: str
    state: str
    declared_files: int
    sets_total: int
    sets_done: int


@dataclass(frozen=True, slots=True)
class QueueRow:
    module: str
    kind: str
    state: str
    count: int


_DOCUMENTS = text(
    "SELECT document_uid, display_title, created_at, updated_at FROM document WHERE project_uid = :project "
    "ORDER BY document_uid LIMIT :limit"
)
_VERSIONS = text(
    "SELECT v.version_uid, v.document_uid, v.version_ordinal, v.page_count, v.published_at FROM document_version v "
    "JOIN document d ON d.document_uid = v.document_uid WHERE d.project_uid = :project "
    "ORDER BY v.document_uid, v.version_ordinal"
)
_SET_META = text(
    "SELECT DISTINCT ON (s.document_uid) s.document_uid, s.designation, s.project_stage, s.section_code "
    "FROM comparison_upload_set s JOIN comparison_upload u ON u.comparison_upload_id = s.comparison_upload_id "
    "WHERE u.project_uid = :project AND s.state = 'done' AND s.document_uid IS NOT NULL "
    "ORDER BY s.document_uid, s.confirmed_at DESC, s.comparison_upload_set_id DESC"
)
_ORDERS = text(
    "SELECT DISTINCT ON (o.document_uid) o.document_uid, o.comparison_version_order_id, o.version_uids "
    "FROM comparison_version_order o WHERE o.document_uid = ANY(CAST(:documents AS text[])) "
    "ORDER BY o.document_uid, o.revision_no DESC"
)
_PROFILES = text(
    "SELECT comparison_page_profile_id, version_uid, page_number, content_key, status FROM comparison_page_profile "
    "WHERE version_uid = ANY(CAST(:versions AS text[])) AND algo_version = :algo ORDER BY version_uid, page_number"
)
_BUILD_COLUMNS = (
    "comparison_matrix_id, build_no, order_id, profile_signature, rules_version, algo_version, rows, "
    "unassigned, summary, created_at"
)
_LATEST_BUILDS = text(
    f"SELECT DISTINCT ON (document_uid) document_uid, {_BUILD_COLUMNS} FROM comparison_matrix "
    "WHERE document_uid = ANY(CAST(:documents AS text[])) ORDER BY document_uid, build_no DESC"
)
_BOUND_BUILDS = text(
    "SELECT comparison_matrix_id, profile_signature FROM comparison_matrix "
    "WHERE comparison_matrix_id = ANY(CAST(:ids AS text[]))"
)
_EDIT_COLUMNS = (
    "comparison_matrix_edit_id, edit_no, batch_position, kind, source, page_version_uid, page_number, "
    "other_version_uid, other_page_number, absent_version_uid, undoes_edit_id, order_id, provenance, "
    "actor_user_uid, command_id, decided_at"
)
_EDITS = text(
    f"SELECT document_uid, {_EDIT_COLUMNS} FROM comparison_matrix_edit "
    "WHERE document_uid = ANY(CAST(:documents AS text[])) ORDER BY document_uid, edit_no"
)
_AI_COLUMNS = (
    "comparison_ai_link_id, document_uid, comparison_matrix_id, page_version_uid, page_number, "
    "other_version_uid, other_page_number, answered_state, created_at"
)
_AI_LINKS = text(
    f"SELECT {_AI_COLUMNS} FROM comparison_ai_link WHERE document_uid = ANY(CAST(:documents AS text[])) "
    "ORDER BY document_uid, created_at DESC, comparison_ai_link_id DESC"
)
# The items that decide the states of the steps: the live ones of the three kinds, and, for the matrix build, the newest
# one of each document whatever its state (the matrix read's ``failed`` is "the newest build item failed").
_WORK = text(
    "SELECT w.comparison_work_id, w.kind, w.state, w.dedupe_key, w.payload->>'document_uid', w.failure_reason, "
    "w.created_at FROM comparison_work w WHERE w.project_uid = :project AND ("
    "(w.kind = ANY(CAST(:kinds AS text[])) AND w.state = ANY(CAST(:live AS text[]))) "
    "OR (w.kind = :build_kind AND w.created_at = (SELECT max(n.created_at) FROM comparison_work n "
    "WHERE n.project_uid = w.project_uid AND n.kind = w.kind AND n.dedupe_key = w.dedupe_key))) "
    "ORDER BY w.created_at DESC, w.comparison_work_id DESC"
)
_SERIES_COLUMNS = (
    "document_uid, comparison_series_id, state, comparison_matrix_id, matrix_edit_no, input_sha256, created_at"
)
_LATEST_SERIES = text(
    f"SELECT DISTINCT ON (document_uid) {_SERIES_COLUMNS} FROM comparison_series "
    "WHERE document_uid = ANY(CAST(:documents AS text[])) "
    "ORDER BY document_uid, created_at DESC, comparison_series_id DESC"
)
_TRANSITIONS = text(
    "SELECT comparison_series_id, transition_no, source_version_uid, target_version_uid, state, summary "
    "FROM comparison_transition WHERE comparison_series_id = ANY(CAST(:series AS text[])) "
    "ORDER BY comparison_series_id, transition_no"
)
_PENDING_UPLOADS = text(
    "SELECT u.comparison_upload_id, u.state, u.declared_files, "
    "count(s.comparison_upload_set_id) FILTER (WHERE s.state <> 'excluded'), "
    "count(s.comparison_upload_set_id) FILTER (WHERE s.state = 'done') "
    "FROM comparison_upload u LEFT JOIN comparison_upload_set s ON s.comparison_upload_id = u.comparison_upload_id "
    "WHERE u.project_uid = :project AND u.state = ANY(CAST(:states AS text[])) "
    "GROUP BY u.comparison_upload_id, u.state, u.declared_files, u.created_at "
    "ORDER BY u.created_at DESC, u.comparison_upload_id DESC LIMIT :limit"
)
_QUEUE_COUNTS = text(
    "SELECT module, kind, state, count(*) FROM comparison_work GROUP BY module, kind, state ORDER BY module, kind, state"
)
_QUEUE_OLDEST = text("SELECT min(created_at) FROM comparison_work WHERE state = 'queued'")


def _json(value: Any) -> Any:
    return value if value is None or isinstance(value, (list, dict)) else json.loads(value)


def _ids(values: Sequence[str]) -> list[str]:
    return list(values)


class OverviewRepository:
    """The statements of the overview. Stateless; every method takes the caller's session and only reads."""

    __slots__ = ()

    def documents(self, session: Session, project_uid: str) -> list[DocumentRow]:
        rows = session.execute(_DOCUMENTS, {"project": project_uid, "limit": MAX_SETS + 1}).all()
        return [DocumentRow(r[0], r[1], r[2], r[3]) for r in rows]

    def versions(self, session: Session, project_uid: str) -> list[VersionRow]:
        rows = session.execute(_VERSIONS, {"project": project_uid}).all()
        return [VersionRow(r[0], r[1], int(r[2]), int(r[3]), r[4]) for r in rows]

    def set_metadata(self, session: Session, project_uid: str) -> dict[str, SetMetaRow]:
        rows = session.execute(_SET_META, {"project": project_uid}).all()
        return {r[0]: SetMetaRow(r[0], r[1], r[2], r[3]) for r in rows}

    def latest_orders(self, session: Session, documents: Sequence[str]) -> dict[str, OrderRow]:
        if not documents:
            return {}
        out: dict[str, OrderRow] = {}
        for r in session.execute(_ORDERS, {"documents": _ids(documents)}).all():
            out[r[0]] = OrderRow(r[0], r[1], tuple(_json(r[2])))
        return out

    def profile_facts(self, session: Session, versions: Sequence[str], algo_version: str) -> list[ProfileFact]:
        if not versions:
            return []
        rows = session.execute(_PROFILES, {"versions": _ids(versions), "algo": algo_version}).all()
        return [ProfileFact(r[0], r[1], int(r[2]), r[3], r[4]) for r in rows]

    def latest_builds(self, session: Session, documents: Sequence[str]) -> dict[str, BuildRecord]:
        if not documents:
            return {}
        out: dict[str, BuildRecord] = {}
        for r in session.execute(_LATEST_BUILDS, {"documents": _ids(documents)}).all():
            v = tuple(r)
            out[v[0]] = BuildRecord(
                matrix_id=v[1], build_no=int(v[2]), order_id=v[3], profile_signature=v[4], rules_version=v[5],
                algo_version=v[6], rows=_json(v[7]), unassigned=_json(v[8]), summary=_json(v[9]), created_at=v[10],
            )
        return out

    def bound_signatures(self, session: Session, matrix_ids: Sequence[str]) -> dict[str, str]:
        if not matrix_ids:
            return {}
        return {r[0]: r[1] for r in session.execute(_BOUND_BUILDS, {"ids": _ids(matrix_ids)}).all()}

    def edits(self, session: Session, documents: Sequence[str]) -> dict[str, list[EditRecord]]:
        out: dict[str, list[EditRecord]] = {}
        if not documents:
            return out
        for r in session.execute(_EDITS, {"documents": _ids(documents)}).all():
            v = tuple(r)
            page = None if v[6] is None else PageRef(v[6], int(v[7]))
            other = None if v[8] is None else PageRef(v[8], int(v[9]))
            out.setdefault(v[0], []).append(EditRecord(
                edit_id=v[1], edit_no=int(v[2]), batch_position=int(v[3]), kind=v[4], source=v[5], page=page,
                other_page=other, absent_version_uid=v[10], undoes_edit_id=v[11], order_id=v[12],
                provenance=_json(v[13]), actor_user_uid=v[14], decided_at=v[16],
            ))
        return out

    def ai_links(self, session: Session, documents: Sequence[str]) -> dict[str, list[AiLinkRecord]]:
        out: dict[str, list[AiLinkRecord]] = {}
        if not documents:
            return out
        for r in session.execute(_AI_LINKS, {"documents": _ids(documents)}).all():
            v = tuple(r)
            out.setdefault(v[1], []).append(AiLinkRecord(
                ai_link_id=v[0], document_uid=v[1], matrix_id=v[2], page=PageRef(v[3], int(v[4])),
                other_page=PageRef(v[5], int(v[6])), answered_state=v[7], created_at=v[8],
            ))
        return out

    def work(self, session: Session, project_uid: str) -> list[WorkRow]:
        rows = session.execute(_WORK, {
            "project": project_uid, "kinds": [KIND_PAGE_PROFILE, KIND_MATRIX_BUILD, KIND_FOLLOW_UP],
            "live": list(_LIVE), "build_kind": KIND_MATRIX_BUILD,
        }).all()
        return [WorkRow(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows]

    def latest_series(self, session: Session, documents: Sequence[str]) -> dict[str, SeriesRow]:
        if not documents:
            return {}
        out: dict[str, SeriesRow] = {}
        for r in session.execute(_LATEST_SERIES, {"documents": _ids(documents)}).all():
            out[r[0]] = SeriesRow(series_id=r[1], document_uid=r[0], state=r[2], matrix_id=r[3], edit_no=int(r[4]),
                                  input_sha256=r[5], created_at=r[6])
        return out

    def transitions(self, session: Session, series_ids: Sequence[str]) -> dict[str, list[TransitionRow]]:
        out: dict[str, list[TransitionRow]] = {}
        if not series_ids:
            return out
        for r in session.execute(_TRANSITIONS, {"series": _ids(series_ids)}).all():
            out.setdefault(r[0], []).append(TransitionRow(r[0], int(r[1]), r[2], r[3], r[4], _json(r[5])))
        return out

    def pending_uploads(self, session: Session, project_uid: str) -> list[PendingUploadRow]:
        rows = session.execute(
            _PENDING_UPLOADS, {"project": project_uid, "states": list(PENDING_UPLOAD_STATES), "limit": MAX_PENDING}
        ).all()
        return [PendingUploadRow(r[0], r[1], int(r[2]), int(r[3]), int(r[4])) for r in rows]

    def queue_counts(self, session: Session) -> list[QueueRow]:
        return [QueueRow(r[0], r[1], r[2], int(r[3])) for r in session.execute(_QUEUE_COUNTS).all()]

    def oldest_queued_at(self, session: Session) -> datetime | None:
        return session.execute(_QUEUE_OLDEST).scalar_one_or_none()
