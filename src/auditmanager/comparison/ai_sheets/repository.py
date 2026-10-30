"""The statements of the sheet descriptions: ``comparison_sheet_description`` and ``comparison_ai_sheet_item`` (`CMP-VC-AISHEET-01`).

Stateless; every method takes the caller's session and never commits (the service and the handler own the transactions). This is the only
writer of the two tables. It **never writes ``comparison_ai_job``** -- that is ``CMP-AI-JOBS-01``'s repository, reached through
``ComparisonAiJobService`` -- and it reads the sheet pairs, their results and the page profiles of other lanes with plain ``SELECT``s, as
``comparison.series`` and ``comparison.ai_jobs`` read each other's tables.

A description is **content-keyed and immutable**: ``UNIQUE (project_uid, content_key)``, and the table refuses an update (trigger of
``0040``). ``insert_description`` therefore answers the stored row when the key exists, which is how a description is never sent twice.
A sheet item is one sheet pair of one job; it moves ``queued -> running -> done | failed | cancelled`` and, for a finish or a retry,
back to ``queued`` (the edges of ``0040``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import ComparisonAiSheetItemId, ComparisonSheetDescriptionId

__all__ = [
    "AiSheetRepository",
    "DescriptionRow",
    "ItemRow",
    "PairFacts",
    "PairState",
    "content_key",
    "prompt_version_of",
]

_PAIR_COLUMNS = (
    "p.comparison_sheet_pair_id AS pair_id, p.comparison_transition_id AS transition_id, p.pair_no, p.state AS pair_state, "
    "p.status, p.page_a_profile_id, p.page_b_profile_id, p.result_id, p.permit, tr.comparison_series_id AS series_id, "
    "tr.transition_no, tr.state AS transition_state, tr.source_version_uid, tr.target_version_uid, s.project_uid, s.document_uid, "
    "r.content_key AS result_key, r.status AS result_status, r.reasons AS result_reasons, "
    "pa.version_uid AS a_version, pa.page_number AS a_number, pa.content_key AS a_key, "
    "pa.profile->'stamp'->>'sheet_number' AS a_sheet, pa.profile->'stamp'->>'sheet_name' AS a_title, "
    "(pa.profile->>'scan')::boolean AS a_scan, "
    "pb.version_uid AS b_version, pb.page_number AS b_number, pb.content_key AS b_key, "
    "pb.profile->'stamp'->>'sheet_number' AS b_sheet, pb.profile->'stamp'->>'sheet_name' AS b_title, "
    "(pb.profile->>'scan')::boolean AS b_scan, pb.profile->'stamp'->>'designation' AS designation, "
    "va.version_ordinal AS a_ordinal, vb.version_ordinal AS b_ordinal, d.display_title AS document_title, pj.name AS project_name"
)
_PAIR_FROM = (
    "FROM comparison_sheet_pair p "
    "JOIN comparison_transition tr ON tr.comparison_transition_id = p.comparison_transition_id "
    "JOIN comparison_series s ON s.comparison_series_id = tr.comparison_series_id "
    "JOIN document d ON d.document_uid = s.document_uid JOIN project pj ON pj.project_uid = s.project_uid "
    "LEFT JOIN comparison_sheet_pair_result r ON r.comparison_sheet_pair_result_id = p.result_id "
    "LEFT JOIN comparison_page_profile pa ON pa.comparison_page_profile_id = p.page_a_profile_id "
    "LEFT JOIN comparison_page_profile pb ON pb.comparison_page_profile_id = p.page_b_profile_id "
    "LEFT JOIN document_version va ON va.version_uid = tr.source_version_uid "
    "LEFT JOIN document_version vb ON vb.version_uid = tr.target_version_uid "
)
_PAIR = text(f"SELECT {_PAIR_COLUMNS} {_PAIR_FROM} WHERE p.comparison_sheet_pair_id = :pair_id")
_TRANSITION_PAIRS = text(
    f"SELECT {_PAIR_COLUMNS} {_PAIR_FROM} WHERE p.comparison_transition_id = :transition_id ORDER BY p.pair_no"
)
_SERIES_PAIRS = text(
    f"SELECT {_PAIR_COLUMNS} {_PAIR_FROM} WHERE tr.comparison_series_id = :series_id ORDER BY tr.transition_no, p.pair_no"
)
_SERIES = text("SELECT comparison_series_id, project_uid, document_uid, state FROM comparison_series WHERE comparison_series_id = :id")
_TRANSITION = text(
    "SELECT tr.comparison_transition_id, tr.comparison_series_id, tr.transition_no, tr.state, s.project_uid, s.document_uid "
    "FROM comparison_transition tr JOIN comparison_series s ON s.comparison_series_id = tr.comparison_series_id "
    "WHERE tr.comparison_transition_id = :id"
)
_TRANSITIONS_OF = text(
    "SELECT comparison_transition_id, transition_no, state FROM comparison_transition WHERE comparison_series_id = :id ORDER BY transition_no"
)
_RESULT = text("SELECT result FROM comparison_sheet_pair_result WHERE comparison_sheet_pair_result_id = :id")
_KEYS = text(
    "SELECT content_key, comparison_sheet_description_id FROM comparison_sheet_description "
    "WHERE project_uid = :project AND content_key = ANY(CAST(:keys AS text[]))"
)
_INSERT_DESCRIPTION = text(
    "INSERT INTO comparison_sheet_description (comparison_sheet_description_id, project_uid, content_key, result_id, page_profile_id, "
    "state, source, prompt_version, model_identity, recorded, description, calls, input_tokens, output_tokens, comparison_model_call_id) "
    "VALUES (:id, :project, :key, :result_id, :page_id, :state, 'sheet', :prompt, :model, :recorded, CAST(:description AS jsonb), "
    ":calls, :input_tokens, :output_tokens, :call_id) ON CONFLICT (project_uid, content_key) DO NOTHING "
    "RETURNING comparison_sheet_description_id"
)
_DESCRIPTION_COLUMNS = (
    "comparison_sheet_description_id AS description_id, project_uid, content_key, result_id, page_profile_id, state, source, "
    "prompt_version, model_identity, recorded, description, calls, input_tokens, output_tokens, created_at"
)
_DESCRIPTION = text(f"SELECT {_DESCRIPTION_COLUMNS} FROM comparison_sheet_description WHERE comparison_sheet_description_id = :id")
_BY_KEY = text(
    f"SELECT {_DESCRIPTION_COLUMNS} FROM comparison_sheet_description WHERE project_uid = :project AND content_key = :key"
)
_SUBJECT = "((CAST(:result_id AS text) IS NOT NULL AND result_id = :result_id) OR (CAST(:page_id AS text) IS NOT NULL AND page_profile_id = :page_id))"
_HISTORY = text(
    f"SELECT {_DESCRIPTION_COLUMNS} FROM comparison_sheet_description WHERE project_uid = :project AND {_SUBJECT} "
    "AND (CAST(:after_at AS timestamptz) IS NULL OR (created_at, comparison_sheet_description_id) < (:after_at, :after_id)) "
    "ORDER BY created_at DESC, comparison_sheet_description_id DESC LIMIT :limit"
)
_HISTORY_COUNT = text(
    f"SELECT count(*) FROM comparison_sheet_description WHERE project_uid = :project AND {_SUBJECT}"
)
_LATEST = text(
    f"SELECT {_DESCRIPTION_COLUMNS} FROM comparison_sheet_description WHERE project_uid = :project AND {_SUBJECT} "
    "ORDER BY created_at DESC, comparison_sheet_description_id DESC LIMIT 1"
)
_ENSURE_ITEM = text(
    "INSERT INTO comparison_ai_sheet_item (comparison_ai_sheet_item_id, comparison_ai_job_id, project_uid, comparison_sheet_pair_id) "
    "VALUES (:id, :job, :project, :pair) ON CONFLICT (comparison_ai_job_id, comparison_sheet_pair_id) DO NOTHING"
)
_ITEM_COLUMNS = (
    "comparison_ai_sheet_item_id AS item_id, comparison_ai_job_id AS job_id, comparison_sheet_pair_id AS pair_id, state, "
    "comparison_sheet_description_id AS description_id, failure_reason, calls, input_tokens, output_tokens, elapsed_ms, updated_at"
)
_ITEM = text(
    f"SELECT {_ITEM_COLUMNS} FROM comparison_ai_sheet_item WHERE comparison_ai_job_id = :job AND comparison_sheet_pair_id = :pair"
)
_ITEM_MOVE = text(
    "UPDATE comparison_ai_sheet_item SET state = :to_state, comparison_sheet_description_id = :description, failure_reason = :reason, "
    "calls = calls + :calls, input_tokens = input_tokens + :input_tokens, output_tokens = output_tokens + :output_tokens, "
    "elapsed_ms = elapsed_ms + :elapsed_ms, updated_at = clock_timestamp() "
    "WHERE comparison_ai_job_id = :job AND comparison_sheet_pair_id = :pair AND state = ANY(CAST(:from_states AS text[]))"
)
_JOB_ITEMS = text(
    f"SELECT {_ITEM_COLUMNS} FROM comparison_ai_sheet_item WHERE comparison_ai_job_id = :job ORDER BY created_at, comparison_ai_sheet_item_id"
)
#: One row per eligible sheet pair with the newest description of its subject and the newest item of any job, for the states.
_STATE_ROWS = (
    "SELECT p.comparison_sheet_pair_id AS pair_id, p.comparison_transition_id AS transition_id, p.pair_no, p.status, "
    "p.state AS pair_state, tr.state AS transition_state, p.result_id, p.page_a_profile_id, p.page_b_profile_id, "
    "dsc.comparison_sheet_description_id AS description_id, dsc.state AS description_state, dsc.prompt_version AS description_prompt, "
    "dsc.created_at AS description_at, jsonb_array_length(coalesce(dsc.description->'changes', '[]'::jsonb)) AS changes_count, "
    "jsonb_array_length(coalesce(dsc.description->'unresolved', '[]'::jsonb)) AS unresolved_count, "
    "itm.state AS item_state, itm.failure_reason AS item_failure, itm.updated_at AS item_at, itm.job_state, itm.job_id, "
    "pa.version_uid AS a_version, pa.page_number AS a_number, pa.profile->'stamp'->>'sheet_number' AS a_sheet, "
    "pa.profile->'stamp'->>'sheet_name' AS a_title, (pa.profile->>'scan')::boolean AS a_scan, "
    "pb.version_uid AS b_version, pb.page_number AS b_number, pb.profile->'stamp'->>'sheet_number' AS b_sheet, "
    "pb.profile->'stamp'->>'sheet_name' AS b_title, (pb.profile->>'scan')::boolean AS b_scan "
    "FROM comparison_sheet_pair p "
    "JOIN comparison_transition tr ON tr.comparison_transition_id = p.comparison_transition_id "
    "JOIN comparison_series s ON s.comparison_series_id = tr.comparison_series_id "
    "LEFT JOIN comparison_page_profile pa ON pa.comparison_page_profile_id = p.page_a_profile_id "
    "LEFT JOIN comparison_page_profile pb ON pb.comparison_page_profile_id = p.page_b_profile_id "
    "LEFT JOIN LATERAL (SELECT * FROM comparison_sheet_description d WHERE d.project_uid = s.project_uid AND ("
    "(p.result_id IS NOT NULL AND d.result_id = p.result_id) OR "
    "(p.result_id IS NULL AND d.page_profile_id = coalesce(p.page_b_profile_id, p.page_a_profile_id))) "
    "ORDER BY d.created_at DESC, d.comparison_sheet_description_id DESC LIMIT 1) dsc ON true "
    "LEFT JOIN LATERAL (SELECT i.state, i.failure_reason, i.updated_at, i.comparison_ai_job_id AS job_id, j.state AS job_state "
    "FROM comparison_ai_sheet_item i JOIN comparison_ai_job j ON j.comparison_ai_job_id = i.comparison_ai_job_id "
    "WHERE i.comparison_sheet_pair_id = p.comparison_sheet_pair_id ORDER BY i.updated_at DESC, i.comparison_ai_sheet_item_id DESC "
    "LIMIT 1) itm ON true "
)
_STATE_ONE = text(_STATE_ROWS + "WHERE p.comparison_sheet_pair_id = :pair_id")
_STATE_TRANSITION = text(
    _STATE_ROWS + "WHERE p.comparison_transition_id = :transition_id AND p.pair_no > :after ORDER BY p.pair_no"
)
_STATE_SERIES = text(_STATE_ROWS + "WHERE tr.comparison_series_id = :series_id ORDER BY tr.transition_no, p.pair_no")
#: What the latest job on a series spent, per transition (the items of that job).
_JOB_SPEND_BY_TRANSITION = text(
    "SELECT p.comparison_transition_id AS transition_id, coalesce(sum(i.calls), 0) AS calls, coalesce(sum(i.input_tokens), 0) AS input_tokens, "
    "coalesce(sum(i.output_tokens), 0) AS output_tokens, coalesce(sum(i.elapsed_ms), 0) AS elapsed_ms "
    "FROM comparison_ai_sheet_item i JOIN comparison_sheet_pair p ON p.comparison_sheet_pair_id = i.comparison_sheet_pair_id "
    "WHERE i.comparison_ai_job_id = :job GROUP BY p.comparison_transition_id"
)
_LATEST_SERIES_JOB = text(
    "SELECT comparison_ai_job_id FROM comparison_ai_job WHERE method = 'sheet_changes' AND comparison_series_id = :series "
    "ORDER BY created_at DESC, comparison_ai_job_id DESC LIMIT 1"
)
_PERMIT = text("SELECT permit FROM comparison_sheet_pair WHERE comparison_sheet_pair_id = :pair_id")


def prompt_version_of(version: str, digest: str) -> str:
    """The ``prompt_version`` column: the name of the prompt and the start of its digest (at most 64 characters), so a prompt that is
    edited without a new name is still another version."""
    return f"{version}+{digest[:12]}"[:64]


def content_key(
    *, project_uid: str, kind: str, subject_key: str, prompt_version: str, model: str,
) -> str:
    """The content key of a description (``UNIQUE (project_uid, content_key)``): the project (a description is reused within a project
    only, ADR-0025 decision 15), what is described (the content key of the stored result, or of the page profile of a single sheet),
    the prompt version and the pinned model. Nothing else: not the job, the pair, the time, the user."""
    document = {"v": 1, "project": project_uid, "kind": kind, "subject": subject_key, "prompt": prompt_version, "model": model}
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PairFacts:
    """A sheet pair with what its description needs. ``result_key`` is the content key of the stored result (absent for a one-sided pair)."""

    pair_id: str
    transition_id: str
    series_id: str
    project_uid: str
    document_uid: str
    pair_no: int
    transition_no: int
    transition_state: str
    pair_state: str
    status: str | None
    page_a_profile_id: str | None
    page_b_profile_id: str | None
    result_id: str | None
    result_key: str | None
    result_status: str | None
    result_reasons: tuple[str, ...]
    permit: Mapping[str, Any] | None
    version_a: str
    version_b: str
    page_a: int | None
    page_b: int | None
    key_a: str | None
    key_b: str | None
    sheet_a: str | None
    sheet_b: str | None
    title_a: str | None
    title_b: str | None
    scan_a: bool | None
    scan_b: bool | None
    designation: str | None
    ordinal_a: int | None
    ordinal_b: int | None
    document_title: str
    project_name: str

    @property
    def one_sided(self) -> bool:
        return self.status in ("added", "removed")

    @property
    def single_kind(self) -> str | None:
        return self.status if self.one_sided else None

    @property
    def subject_page_profile(self) -> str | None:
        """The page a one-sided pair is described by: the newer for ``added``, the older for ``removed``."""
        return self.page_b_profile_id if self.status == "added" else self.page_a_profile_id if self.status == "removed" else None

    @property
    def subject_key(self) -> str | None:
        if self.one_sided:
            return self.key_b if self.status == "added" else self.key_a
        return self.result_key

    @property
    def title(self) -> str:
        return (self.title_b or self.title_a or self.sheet_b or self.sheet_a or "").strip()

    @property
    def sheet_number(self) -> str:
        return (self.sheet_b or self.sheet_a or "").strip()


def _pair(row: Mapping[str, Any]) -> PairFacts:
    return PairFacts(
        pair_id=row["pair_id"], transition_id=row["transition_id"], series_id=row["series_id"], project_uid=row["project_uid"],
        document_uid=row["document_uid"], pair_no=int(row["pair_no"]), transition_no=int(row["transition_no"]),
        transition_state=row["transition_state"], pair_state=row["pair_state"], status=row["status"],
        page_a_profile_id=row["page_a_profile_id"], page_b_profile_id=row["page_b_profile_id"], result_id=row["result_id"],
        result_key=row["result_key"], result_status=row["result_status"], result_reasons=tuple(row["result_reasons"] or ()),
        permit=row["permit"], version_a=row["source_version_uid"], version_b=row["target_version_uid"],
        page_a=None if row["a_number"] is None else int(row["a_number"]), page_b=None if row["b_number"] is None else int(row["b_number"]),
        key_a=row["a_key"], key_b=row["b_key"], sheet_a=row["a_sheet"], sheet_b=row["b_sheet"], title_a=row["a_title"],
        title_b=row["b_title"], scan_a=row["a_scan"], scan_b=row["b_scan"], designation=row["designation"],
        ordinal_a=row["a_ordinal"], ordinal_b=row["b_ordinal"], document_title=row["document_title"] or "",
        project_name=row["project_name"] or "",
    )


@dataclass(frozen=True, slots=True)
class DescriptionRow:
    description_id: str
    project_uid: str
    content_key: str
    result_id: str | None
    page_profile_id: str | None
    state: str
    source: str
    prompt_version: str
    model_identity: str
    recorded: bool
    description: Mapping[str, Any]
    calls: int
    input_tokens: int
    output_tokens: int
    created_at: datetime


def _description(row: Mapping[str, Any]) -> DescriptionRow:
    return DescriptionRow(
        description_id=row["description_id"], project_uid=row["project_uid"], content_key=row["content_key"],
        result_id=row["result_id"], page_profile_id=row["page_profile_id"], state=row["state"], source=row["source"],
        prompt_version=row["prompt_version"], model_identity=row["model_identity"], recorded=bool(row["recorded"]),
        description=dict(row["description"]), calls=int(row["calls"]), input_tokens=int(row["input_tokens"]),
        output_tokens=int(row["output_tokens"]), created_at=row["created_at"],
    )


@dataclass(frozen=True, slots=True)
class ItemRow:
    item_id: str
    job_id: str
    pair_id: str
    state: str
    description_id: str | None
    failure_reason: str | None
    calls: int
    input_tokens: int
    output_tokens: int
    elapsed_ms: int
    updated_at: datetime


def _item(row: Mapping[str, Any]) -> ItemRow:
    return ItemRow(
        item_id=row["item_id"], job_id=row["job_id"], pair_id=row["pair_id"], state=row["state"],
        description_id=row["description_id"], failure_reason=row["failure_reason"], calls=int(row["calls"]),
        input_tokens=int(row["input_tokens"]), output_tokens=int(row["output_tokens"]), elapsed_ms=int(row["elapsed_ms"]),
        updated_at=row["updated_at"],
    )


@dataclass(frozen=True, slots=True)
class PairState:
    """The newest description of a pair's subject and the newest sheet item of any job, as the state of the pair reads them."""

    pair_id: str
    transition_id: str
    pair_no: int
    status: str | None
    pair_state: str
    transition_state: str
    result_id: str | None
    description_id: str | None
    description_state: str | None
    description_prompt: str | None
    description_at: datetime | None
    changes_count: int
    unresolved_count: int
    item_state: str | None
    item_failure: str | None
    item_at: datetime | None
    job_state: str | None
    job_id: str | None
    row: Mapping[str, Any]


def _state_row(row: Mapping[str, Any]) -> PairState:
    return PairState(
        pair_id=row["pair_id"], transition_id=row["transition_id"], pair_no=int(row["pair_no"]), status=row["status"],
        pair_state=row["pair_state"], transition_state=row["transition_state"], result_id=row["result_id"],
        description_id=row["description_id"], description_state=row["description_state"],
        description_prompt=row["description_prompt"], description_at=row["description_at"],
        changes_count=int(row["changes_count"] or 0), unresolved_count=int(row["unresolved_count"] or 0),
        item_state=row["item_state"], item_failure=row["item_failure"], item_at=row["item_at"], job_state=row["job_state"],
        job_id=row["job_id"], row=dict(row),
    )


class AiSheetRepository:
    """Stateless; the caller's session, never a commit."""

    __slots__ = ()

    # -- reads of the sheet pairs ---------------------------------------------------------------------------------------
    def pair(self, session: Session, pair_id: str) -> PairFacts | None:
        row = session.execute(_PAIR, {"pair_id": pair_id}).mappings().first()
        return None if row is None else _pair(row)

    def pairs_of_transition(self, session: Session, transition_id: str) -> list[PairFacts]:
        return [_pair(r) for r in session.execute(_TRANSITION_PAIRS, {"transition_id": transition_id}).mappings()]

    def pairs_of_series(self, session: Session, series_id: str) -> list[PairFacts]:
        return [_pair(r) for r in session.execute(_SERIES_PAIRS, {"series_id": series_id}).mappings()]

    def series(self, session: Session, series_id: str) -> Mapping[str, Any] | None:
        row = session.execute(_SERIES, {"id": series_id}).mappings().first()
        return None if row is None else dict(row)

    def transition(self, session: Session, transition_id: str) -> Mapping[str, Any] | None:
        row = session.execute(_TRANSITION, {"id": transition_id}).mappings().first()
        return None if row is None else dict(row)

    def transitions_of(self, session: Session, series_id: str) -> list[Mapping[str, Any]]:
        return [dict(r) for r in session.execute(_TRANSITIONS_OF, {"id": series_id}).mappings()]

    def result_document(self, session: Session, result_id: str) -> Mapping[str, Any] | None:
        value = session.execute(_RESULT, {"id": result_id}).scalar_one_or_none()
        return None if value is None else dict(value)

    def permit_of(self, session: Session, pair_id: str) -> Mapping[str, Any] | None:
        value = session.execute(_PERMIT, {"pair_id": pair_id}).scalar_one_or_none()
        return None if value is None else dict(value)

    # -- descriptions ---------------------------------------------------------------------------------------------------
    def stored_keys(self, session: Session, project_uid: str, keys: Sequence[str]) -> dict[str, str]:
        """``{content key: description id}`` for the keys that already have a stored description."""
        if not keys:
            return {}
        return {
            str(r[0]): str(r[1]) for r in session.execute(_KEYS, {"project": project_uid, "keys": list(keys)}).all()
        }

    def description_by_key(self, session: Session, project_uid: str, key: str) -> DescriptionRow | None:
        row = session.execute(_BY_KEY, {"project": project_uid, "key": key}).mappings().first()
        return None if row is None else _description(row)

    def description(self, session: Session, description_id: str) -> DescriptionRow | None:
        row = session.execute(_DESCRIPTION, {"id": description_id}).mappings().first()
        return None if row is None else _description(row)

    def insert_description(
        self, session: Session, *, project_uid: str, key: str, result_id: str | None, page_profile_id: str | None, state: str,
        prompt_version: str, model_identity: str, recorded: bool, description: Mapping[str, Any], calls: int, input_tokens: int,
        output_tokens: int, model_call_id: str | None,
    ) -> tuple[str, bool]:
        """Store a description; answers ``(description id, created)``. A key that is stored already answers the stored row's id and
        ``False`` -- the description is immutable and never written twice."""
        new_id = str(ComparisonSheetDescriptionId.new())
        inserted = session.execute(_INSERT_DESCRIPTION, {
            "id": new_id, "project": project_uid, "key": key, "result_id": result_id, "page_id": page_profile_id, "state": state,
            "prompt": prompt_version, "model": model_identity, "recorded": recorded,
            "description": json.dumps(dict(description), sort_keys=True, ensure_ascii=False, default=str), "calls": calls,
            "input_tokens": input_tokens, "output_tokens": output_tokens, "call_id": model_call_id,
        }).scalar_one_or_none()
        if inserted is not None:
            return str(inserted), True
        stored = self.description_by_key(session, project_uid, key)
        assert stored is not None  # the conflict was on this very key
        return stored.description_id, False

    def latest_description(
        self, session: Session, *, project_uid: str, result_id: str | None, page_profile_id: str | None,
    ) -> DescriptionRow | None:
        row = session.execute(_LATEST, {"project": project_uid, "result_id": result_id, "page_id": page_profile_id}).mappings().first()
        return None if row is None else _description(row)

    def history(
        self, session: Session, *, project_uid: str, result_id: str | None, page_profile_id: str | None,
        after: tuple[datetime, str] | None, limit: int,
    ) -> list[DescriptionRow]:
        rows = session.execute(_HISTORY, {
            "project": project_uid, "result_id": result_id, "page_id": page_profile_id, "limit": limit,
            "after_at": None if after is None else after[0], "after_id": None if after is None else after[1],
        }).mappings()
        return [_description(r) for r in rows]

    def history_count(self, session: Session, *, project_uid: str, result_id: str | None, page_profile_id: str | None) -> int:
        return int(session.execute(
            _HISTORY_COUNT, {"project": project_uid, "result_id": result_id, "page_id": page_profile_id}
        ).scalar_one())

    # -- sheet items ----------------------------------------------------------------------------------------------------
    def ensure_item(self, session: Session, *, job_id: str, project_uid: str, pair_id: str) -> None:
        """The item row of a pair of a job, ``queued`` (written in the job's own transaction; a repeat leaves it as it is)."""
        session.execute(_ENSURE_ITEM, {
            "id": str(ComparisonAiSheetItemId.new()), "job": job_id, "project": project_uid, "pair": pair_id,
        })

    def requeue_item(self, session: Session, *, job_id: str, pair_id: str) -> bool:
        """A failed, cancelled or running item goes back to ``queued`` (a finish, a retry, a reclaimed attempt)."""
        return self.move_item(session, job_id=job_id, pair_id=pair_id, from_states=("failed", "cancelled", "running"), to_state="queued")

    def item(self, session: Session, job_id: str, pair_id: str) -> ItemRow | None:
        row = session.execute(_ITEM, {"job": job_id, "pair": pair_id}).mappings().first()
        return None if row is None else _item(row)

    def items_of_job(self, session: Session, job_id: str) -> list[ItemRow]:
        return [_item(r) for r in session.execute(_JOB_ITEMS, {"job": job_id}).mappings()]

    def move_item(
        self, session: Session, *, job_id: str, pair_id: str, from_states: Sequence[str], to_state: str,
        description_id: str | None = None, reason: str | None = None, calls: int = 0, input_tokens: int = 0, output_tokens: int = 0,
        elapsed_ms: int = 0,
    ) -> bool:
        return session.execute(_ITEM_MOVE, {
            "job": job_id, "pair": pair_id, "from_states": list(from_states), "to_state": to_state, "description": description_id,
            "reason": reason, "calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens, "elapsed_ms": elapsed_ms,
        }).rowcount == 1

    # -- the states and the progress ------------------------------------------------------------------------------------
    def state_of_pair(self, session: Session, pair_id: str) -> PairState | None:
        row = session.execute(_STATE_ONE, {"pair_id": pair_id}).mappings().first()
        return None if row is None else _state_row(row)

    def states_of_transition(self, session: Session, transition_id: str, *, after: int = 0, limit: int | None = None) -> list[PairState]:
        rows = [_state_row(r) for r in session.execute(_STATE_TRANSITION, {"transition_id": transition_id, "after": after}).mappings()]
        return rows if limit is None else rows[:limit]

    def states_of_series(self, session: Session, series_id: str) -> list[PairState]:
        return [_state_row(r) for r in session.execute(_STATE_SERIES, {"series_id": series_id}).mappings()]

    def latest_series_job(self, session: Session, series_id: str) -> str | None:
        value = session.execute(_LATEST_SERIES_JOB, {"series": series_id}).scalar_one_or_none()
        return None if value is None else str(value)

    def job_spend_by_transition(self, session: Session, job_id: str) -> dict[str, Mapping[str, int]]:
        return {
            str(r["transition_id"]): {
                "calls": int(r["calls"]), "input_tokens": int(r["input_tokens"]), "output_tokens": int(r["output_tokens"]),
                "elapsed_ms": int(r["elapsed_ms"]),
            }
            for r in session.execute(_JOB_SPEND_BY_TRANSITION, {"job": job_id}).mappings()
        }
