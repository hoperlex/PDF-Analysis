"""The statements of the matrix: builds, edits, accepted AI links, and the few reads of other tables it needs.

`CMP-MATRIX-01`. Every statement is written out (``docs/program/P02_SEAMS.md`` section 3.5: no base repository,
no generic CRUD). The database is the owner of the invariants -- builds and edits numbered without a gap, an edit's
pages existing in the document's versions, an undo naming one earlier edit once, the append-only guards -- and this
module never repeats or works around one: the use cases check first so that the caller reads a typed refusal and
not a driver error.

**Tables it writes**: ``comparison_matrix`` (a build, once per input set) and ``comparison_matrix_edit`` (an
expert's edit or an undo). **Tables it only reads**: ``comparison_ai_link`` (empty until wave C2),
``comparison_page_profile`` (the digest of what a build read, the progress of the profiles) and
``comparison_work`` (is a build or a profile still queued, did the last build fail -- read-only, the queue itself is
``comparison/work``'s).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditmanager.comparison.matrix.model import (
    AiLinkRecord,
    BuildRecord,
    EditRecord,
    PageRef,
)
from auditmanager.documents.public import UNIQUE_VIOLATION, sqlstate_of
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.identity import new_ulid

__all__ = [
    "MatrixRepository",
    "ProfileFact",
    "WorkFact",
    "new_ai_link_id",
    "new_edit_id",
    "new_matrix_id",
]

#: Work states in which an item is still going to run (the non-terminal states of ``comparison_work``).
_LIVE_STATES: Final[tuple[str, ...]] = ("queued", "leased", "running", "retry_wait", "paused", "spend_unknown")


def new_matrix_id() -> str:
    return f"cmx_{new_ulid()}"


def new_edit_id() -> str:
    return f"cme_{new_ulid()}"


def new_ai_link_id() -> str:
    return f"cak_{new_ulid()}"


@dataclass(frozen=True, slots=True)
class ProfileFact:
    """What the matrix needs to know about one stored page profile without opening its archive."""

    page_profile_id: str
    version_uid: str
    page_number: int
    content_key: str
    status: str


@dataclass(frozen=True, slots=True)
class WorkFact:
    """The state of one ``comparison_work`` item, read-only."""

    work_id: str
    state: str
    failure_reason: str | None
    created_at: datetime


_BUILD_COLUMNS = (
    "comparison_matrix_id, build_no, order_id, profile_signature, rules_version, algo_version, rows, "
    "unassigned, summary, created_at"
)
_EDIT_COLUMNS = (
    "comparison_matrix_edit_id, edit_no, batch_position, kind, source, page_version_uid, page_number, "
    "other_version_uid, other_page_number, absent_version_uid, undoes_edit_id, order_id, provenance, "
    "actor_user_uid, command_id, decided_at"
)
_AI_COLUMNS = (
    "comparison_ai_link_id, document_uid, comparison_matrix_id, page_version_uid, page_number, "
    "other_version_uid, other_page_number, answered_state, created_at"
)

_PROFILES = text(
    "SELECT comparison_page_profile_id, version_uid, page_number, content_key, status "
    "FROM comparison_page_profile WHERE version_uid = ANY(CAST(:versions AS text[])) AND algo_version = :algo "
    "ORDER BY version_uid, page_number"
)
_LATEST_BUILD = text(
    f"SELECT {_BUILD_COLUMNS} FROM comparison_matrix WHERE document_uid = :document ORDER BY build_no DESC LIMIT 1"
)
_BUILD_BY_INPUTS = text(
    f"SELECT {_BUILD_COLUMNS} FROM comparison_matrix WHERE document_uid = :document "
    "AND coalesce(order_id, '') = coalesce(CAST(:order_id AS text), '') AND profile_signature = :signature "
    "AND rules_version = :rules AND algo_version = :algo"
)
_BUILD_BY_ID = text(f"SELECT {_BUILD_COLUMNS} FROM comparison_matrix WHERE comparison_matrix_id = :id")
_NEXT_BUILD_NO = text("SELECT coalesce(max(build_no), 0) + 1 FROM comparison_matrix WHERE document_uid = :document")
_INSERT_BUILD = text(
    "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, order_id, "
    "profile_signature, rules_version, algo_version, rows, unassigned, summary) VALUES (:id, :project, :document, "
    ":build_no, :order_id, :signature, :rules, :algo, CAST(:rows AS jsonb), CAST(:unassigned AS jsonb), "
    f"CAST(:summary AS jsonb)) RETURNING {_BUILD_COLUMNS}"
)
_LOCK_EDITS = text("SELECT pg_advisory_xact_lock(hashtextextended('comparison_matrix_edit:' || :document, 0))")
_MAX_EDIT_NO = text("SELECT coalesce(max(edit_no), 0) FROM comparison_matrix_edit WHERE document_uid = :document")
_ALL_EDITS = text(
    f"SELECT {_EDIT_COLUMNS} FROM comparison_matrix_edit WHERE document_uid = :document ORDER BY edit_no"
)
_EDITS_PAGE = text(
    f"SELECT {_EDIT_COLUMNS} FROM comparison_matrix_edit WHERE document_uid = :document "
    "AND (CAST(:before AS integer) IS NULL OR edit_no < :before) ORDER BY edit_no DESC LIMIT :limit"
)
_INSERT_EDIT = text(
    "INSERT INTO comparison_matrix_edit (comparison_matrix_edit_id, project_uid, document_uid, edit_no, "
    "batch_position, kind, source, page_version_uid, page_number, other_version_uid, other_page_number, "
    "absent_version_uid, undoes_edit_id, order_id, provenance, actor_user_uid, actor_label, command_id) "
    "VALUES (:id, :project, :document, :edit_no, :position, :kind, 'expert', :page_version, :page_number, "
    ":other_version, :other_number, :absent_version, :undoes, :order_id, '{}'::jsonb, :actor, :label, :command)"
)
_AI_LINKS = text(
    f"SELECT {_AI_COLUMNS} FROM comparison_ai_link WHERE document_uid = :document "
    "ORDER BY created_at DESC, comparison_ai_link_id DESC"
)
_LIVE_WORK = text(
    "SELECT comparison_work_id, state, failure_reason, created_at FROM comparison_work "
    "WHERE project_uid = :project AND kind = :kind AND dedupe_key = ANY(CAST(:keys AS text[])) "
    "AND state = ANY(CAST(:live AS text[])) ORDER BY created_at DESC"
)
_LATEST_WORK = text(
    "SELECT comparison_work_id, state, failure_reason, created_at FROM comparison_work "
    "WHERE project_uid = :project AND kind = :kind AND dedupe_key = :key ORDER BY created_at DESC LIMIT 1"
)


def _json(value: Any) -> Any:
    return value if isinstance(value, (list, dict)) else json.loads(value)


def _build(row: Any) -> BuildRecord:
    v = tuple(row)
    return BuildRecord(
        matrix_id=v[0], build_no=int(v[1]), order_id=v[2], profile_signature=v[3], rules_version=v[4],
        algo_version=v[5], rows=_json(v[6]), unassigned=_json(v[7]), summary=_json(v[8]), created_at=v[9],
    )


def _edit(row: Any) -> EditRecord:
    v = tuple(row)
    page = None if v[5] is None else PageRef(v[5], int(v[6]))
    other = None if v[7] is None else PageRef(v[7], int(v[8]))
    return EditRecord(
        edit_id=v[0], edit_no=int(v[1]), batch_position=int(v[2]), kind=v[3], source=v[4], page=page,
        other_page=other, absent_version_uid=v[9], undoes_edit_id=v[10], order_id=v[11],
        provenance=_json(v[12]), actor_user_uid=v[13], decided_at=v[15],
    )


def _ai(row: Any) -> AiLinkRecord:
    v = tuple(row)
    return AiLinkRecord(
        ai_link_id=v[0], document_uid=v[1], matrix_id=v[2], page=PageRef(v[3], int(v[4])),
        other_page=PageRef(v[5], int(v[6])), answered_state=v[7], created_at=v[8],
    )


class MatrixRepository:
    """The statements of the matrix. Stateless; every method takes the caller's session."""

    __slots__ = ()

    # -- reads of other tables ------------------------------------------------------------------------------

    def profile_facts(self, session: Session, version_uids: Sequence[str], algo_version: str) -> list[ProfileFact]:
        rows = session.execute(_PROFILES, {"versions": list(version_uids), "algo": algo_version}).all()
        return [ProfileFact(r[0], r[1], int(r[2]), r[3], r[4]) for r in (tuple(x) for x in rows)]

    def live_work(self, session: Session, *, project_uid: str, kind: str, dedupe_keys: Sequence[str]) -> list[WorkFact]:
        """Items of ``kind`` and one of ``dedupe_keys`` that are still going to run, newest first."""
        if not dedupe_keys:
            return []
        rows = session.execute(
            _LIVE_WORK,
            {"project": project_uid, "kind": kind, "keys": list(dedupe_keys), "live": list(_LIVE_STATES)},
        ).all()
        return [WorkFact(r[0], r[1], r[2], r[3]) for r in (tuple(x) for x in rows)]

    def latest_work(self, session: Session, *, project_uid: str, kind: str, dedupe_key: str) -> WorkFact | None:
        row = session.execute(_LATEST_WORK, {"project": project_uid, "kind": kind, "key": dedupe_key}).first()
        return None if row is None else WorkFact(*tuple(row))

    # -- builds ------------------------------------------------------------------------------------------------

    def latest_build(self, session: Session, document_uid: str) -> BuildRecord | None:
        row = session.execute(_LATEST_BUILD, {"document": document_uid}).first()
        return None if row is None else _build(row)

    def build_by_id(self, session: Session, matrix_id: str) -> BuildRecord | None:
        row = session.execute(_BUILD_BY_ID, {"id": matrix_id}).first()
        return None if row is None else _build(row)

    def build_for_inputs(
        self, session: Session, *, document_uid: str, order_id: str | None, signature: str, rules: str, algo: str
    ) -> BuildRecord | None:
        row = session.execute(
            _BUILD_BY_INPUTS,
            {"document": document_uid, "order_id": order_id, "signature": signature, "rules": rules, "algo": algo},
        ).first()
        return None if row is None else _build(row)

    def lock_builds(self, session: Session, document_uid: str) -> None:
        """The advisory lock the build chain trigger takes, taken first so the existence check and the insert are
        one decision."""
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended('comparison_matrix:' || :document, 0))"),
            {"document": document_uid},
        )

    def insert_build(
        self,
        session: Session,
        *,
        project_uid: str,
        document_uid: str,
        order_id: str | None,
        signature: str,
        rules: str,
        algo: str,
        rows: Sequence[Mapping[str, Any]],
        unassigned: Sequence[Mapping[str, Any]],
        summary: Mapping[str, Any],
    ) -> BuildRecord | None:
        """Append a build, numbered after the latest. ``None`` when this input set was built meanwhile (the unique
        index): the caller reads that build instead."""
        build_no = int(session.execute(_NEXT_BUILD_NO, {"document": document_uid}).scalar_one())
        try:
            with nested_transaction(session):
                row = session.execute(
                    _INSERT_BUILD,
                    {
                        "id": new_matrix_id(), "project": project_uid, "document": document_uid,
                        "build_no": build_no, "order_id": order_id, "signature": signature, "rules": rules,
                        "algo": algo,
                        "rows": json.dumps(rows, ensure_ascii=False, sort_keys=True),
                        "unassigned": json.dumps(unassigned, ensure_ascii=False, sort_keys=True),
                        "summary": json.dumps(summary, ensure_ascii=False, sort_keys=True),
                    },
                ).first()
        except IntegrityError as failure:
            if sqlstate_of(failure) != UNIQUE_VIOLATION:
                raise
            return None
        assert row is not None
        return _build(row)

    # -- edits -------------------------------------------------------------------------------------------------

    def lock_edits(self, session: Session, document_uid: str) -> None:
        """The advisory lock the edit chain trigger takes, taken first so the revision check and the inserts are
        one decision."""
        session.execute(_LOCK_EDITS, {"document": document_uid})

    def max_edit_no(self, session: Session, document_uid: str) -> int:
        return int(session.execute(_MAX_EDIT_NO, {"document": document_uid}).scalar_one())

    def all_edits(self, session: Session, document_uid: str) -> list[EditRecord]:
        return [_edit(r) for r in session.execute(_ALL_EDITS, {"document": document_uid}).all()]

    def edits_page(self, session: Session, document_uid: str, *, before: int | None, limit: int) -> list[EditRecord]:
        rows = session.execute(_EDITS_PAGE, {"document": document_uid, "before": before, "limit": limit}).all()
        return [_edit(r) for r in rows]

    def insert_edit(
        self,
        session: Session,
        *,
        project_uid: str,
        document_uid: str,
        edit_no: int,
        batch_position: int,
        kind: str,
        page: PageRef | None,
        other_page: PageRef | None,
        absent_version_uid: str | None,
        undoes_edit_id: str | None,
        order_id: str | None,
        actor_user_uid: str,
        actor_label: str,
        command_id: str,
    ) -> str:
        edit_id = new_edit_id()
        session.execute(
            _INSERT_EDIT,
            {
                "id": edit_id, "project": project_uid, "document": document_uid, "edit_no": edit_no,
                "position": batch_position, "kind": kind,
                "page_version": None if page is None else page.version_uid,
                "page_number": None if page is None else page.page_number,
                "other_version": None if other_page is None else other_page.version_uid,
                "other_number": None if other_page is None else other_page.page_number,
                "absent_version": absent_version_uid, "undoes": undoes_edit_id, "order_id": order_id,
                "actor": actor_user_uid, "label": actor_label, "command": command_id,
            },
        )
        return edit_id

    # -- accepted AI links (read only) ---------------------------------------------------------------------------

    def ai_links(self, session: Session, document_uid: str) -> list[AiLinkRecord]:
        return [_ai(r) for r in session.execute(_AI_LINKS, {"document": document_uid}).all()]
