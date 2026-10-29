"""The statements of the series: ``comparison_series``, ``comparison_transition`` and ``comparison_sheet_pair``
(`CMP-SERIES-01`). Stateless; every method takes the caller's session and never commits.

The lock order every writer keeps, so that no two of them wait on each other: **work item rows, then the series row, then
its transition rows, then its pair rows**. A worker's first statement is the fence on its own item
(``WorkItem.require_current``); a command updates the work rows (``pause_for_series`` and the like) before it updates the
series.

The state edges and the frozen columns are the database's (migration ``0039``); a conditional ``UPDATE ... WHERE state IN
(...)`` is the check-and-set, and its row count is the answer.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.series.model import (
    PAIR_DONE,
    PAIR_QUEUED,
    SERIES_PAIR_KIND,
    PlannedPair,
)
from auditmanager.shared.identity import ComparisonSheetPairId, ComparisonTransitionId

__all__ = [
    "PairFact",
    "PairRow",
    "SeriesRepository",
    "SeriesRow",
    "TransitionRow",
    "pair_dedupe_key",
]

_SERIES_COLUMNS = (
    "comparison_series_id, project_uid, document_uid, state, order_id, comparison_matrix_id, matrix_edit_no, "
    "input_sha256, restarted_from_series_id, failure_reason, actor_user_uid, created_at, updated_at"
)
_TRANSITION_COLUMNS = (
    "comparison_transition_id, comparison_series_id, transition_no, source_version_uid, target_version_uid, state, "
    "summary, verdict, failure_reason"
)
_PAIR_COLUMNS = (
    "comparison_sheet_pair_id, comparison_transition_id, pair_no, state, status, page_a_profile_id, page_b_profile_id, "
    "confidence, flags, result_id, ai_dependent, permit, parts, failure_reason"
)

#: A difference list that holds something other than shifts and only line style: «из них только оформление линий».
_STYLE_ONLY = (
    "(EXISTS (SELECT 1 FROM jsonb_array_elements(r.result->'differences') d WHERE d->>'layer' <> 'moved') "
    "AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(r.result->'differences') d "
    "WHERE d->>'layer' <> 'moved' AND d->>'region_class' <> 'line_style'))"
)

_INSERT_SERIES = text(
    "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, state, order_id, "
    "comparison_matrix_id, matrix_edit_no, input_sha256, restarted_from_series_id, actor_user_uid, actor_label, "
    "command_id) VALUES (:id, :project, :document, 'queued', :order_id, :matrix_id, :edit_no, :digest, :restarted, "
    ":actor, :label, :command)"
)
_GET_SERIES = text(f"SELECT {_SERIES_COLUMNS} FROM comparison_series WHERE comparison_series_id = :id")
_GET_SERIES_LOCKED = text(
    f"SELECT {_SERIES_COLUMNS} FROM comparison_series WHERE comparison_series_id = :id FOR UPDATE"
)
_LIVE_SERIES = text(
    f"SELECT {_SERIES_COLUMNS} FROM comparison_series WHERE document_uid = :document "
    "AND state IN ('queued', 'running', 'paused')"
)
_LATEST_SERIES = text(
    f"SELECT {_SERIES_COLUMNS} FROM comparison_series WHERE document_uid = :document "
    "ORDER BY created_at DESC, comparison_series_id DESC LIMIT 1"
)
_LIST_SERIES = text(
    f"SELECT {_SERIES_COLUMNS} FROM comparison_series WHERE document_uid = :document "
    "AND (CAST(:after_at AS timestamptz) IS NULL OR (created_at, comparison_series_id) < (:after_at, :after_id)) "
    "ORDER BY created_at DESC, comparison_series_id DESC LIMIT :limit"
)
_SET_SERIES_STATE = text(
    "UPDATE comparison_series SET state = :to_state, failure_reason = :reason, updated_at = clock_timestamp() "
    "WHERE comparison_series_id = :id AND state = ANY (CAST(:from_states AS text[]))"
)
_BOUND_BUILD = text(
    "SELECT profile_signature, rules_version, algo_version FROM comparison_matrix WHERE comparison_matrix_id = :id"
)
_LATEST_BUILD_ID = text(
    "SELECT comparison_matrix_id FROM comparison_matrix WHERE document_uid = :document ORDER BY build_no DESC LIMIT 1"
)

_INSERT_TRANSITION = text(
    "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, "
    "source_version_uid, target_version_uid) VALUES (:id, :series, :no, :source, :target)"
)
_TRANSITIONS = text(
    f"SELECT {_TRANSITION_COLUMNS} FROM comparison_transition WHERE comparison_series_id = :series ORDER BY transition_no"
)
_GET_TRANSITION = text(f"SELECT {_TRANSITION_COLUMNS} FROM comparison_transition WHERE comparison_transition_id = :id")
_LOCK_TRANSITION = text(
    f"SELECT {_TRANSITION_COLUMNS} FROM comparison_transition WHERE comparison_transition_id = :id FOR UPDATE"
)
_SET_TRANSITION_STATE = text(
    "UPDATE comparison_transition SET state = :to_state, summary = CAST(:summary AS jsonb), "
    "verdict = CAST(:verdict AS jsonb), failure_reason = :reason, updated_at = clock_timestamp() "
    "WHERE comparison_transition_id = :id AND state = ANY (CAST(:from_states AS text[]))"
)
_CANCEL_TRANSITIONS = text(
    "UPDATE comparison_transition SET state = 'cancelled', updated_at = clock_timestamp() "
    "WHERE comparison_series_id = :series AND state IN ('queued', 'running')"
)
_RUN_TRANSITION = text(
    "UPDATE comparison_transition SET state = 'running', updated_at = clock_timestamp() "
    "WHERE comparison_transition_id = :id AND state = 'queued'"
)

_INSERT_PAIR = text(
    "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, state, status, "
    "page_a_profile_id, page_b_profile_id, confidence, flags, ai_dependent, parts) VALUES (:id, :transition, :no, "
    ":state, :status, :page_a, :page_b, :confidence, CAST(:flags AS jsonb), :ai, CAST(:parts AS jsonb))"
)
_GET_PAIR = text(f"SELECT {_PAIR_COLUMNS} FROM comparison_sheet_pair WHERE comparison_sheet_pair_id = :id")
_PAIRS_OF_TRANSITION = text(
    f"SELECT {_PAIR_COLUMNS} FROM comparison_sheet_pair WHERE comparison_transition_id = :transition ORDER BY pair_no"
)
_MARK_COMPUTING = text(
    "UPDATE comparison_sheet_pair SET state = 'computing', failure_reason = NULL, updated_at = clock_timestamp() "
    "WHERE comparison_sheet_pair_id = :id AND state IN ('queued', 'failed')"
)
_FINISH_PAIR = text(
    "UPDATE comparison_sheet_pair SET state = 'done', status = :status, result_id = :result, "
    "parts = coalesce(CAST(:parts AS jsonb), parts), failure_reason = NULL, updated_at = clock_timestamp() "
    "WHERE comparison_sheet_pair_id = :id AND state = 'computing'"
)
_FAIL_PAIR = text(
    "UPDATE comparison_sheet_pair SET state = 'failed', failure_reason = :reason, updated_at = clock_timestamp() "
    "WHERE comparison_sheet_pair_id = :id AND state IN ('queued', 'computing')"
)
_REQUEUE_PAIR = text(
    "UPDATE comparison_sheet_pair SET state = 'queued', failure_reason = NULL, updated_at = clock_timestamp() "
    "WHERE comparison_sheet_pair_id = :id AND state IN ('computing', 'failed')"
)
_REQUEUE_UNFINISHED = text(
    "UPDATE comparison_sheet_pair p SET state = 'queued', failure_reason = NULL, updated_at = clock_timestamp() "
    "WHERE p.comparison_transition_id = ANY (CAST(:transitions AS text[])) AND p.state IN ('computing', 'failed') "
    "RETURNING p.comparison_sheet_pair_id"
)
_QUEUED_PAIRS = text(
    "SELECT p.comparison_sheet_pair_id, t.transition_no, p.pair_no FROM comparison_sheet_pair p "
    "JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id "
    "WHERE t.comparison_series_id = :series AND p.state = 'queued' ORDER BY t.transition_no, p.pair_no"
)
_SET_PERMIT = text(
    "UPDATE comparison_sheet_pair SET permit = CAST(:permit AS jsonb), updated_at = clock_timestamp() "
    "WHERE comparison_sheet_pair_id = :id"
)
_SET_PARTS = text(
    "UPDATE comparison_sheet_pair SET parts = CAST(:parts AS jsonb), updated_at = clock_timestamp() "
    "WHERE comparison_sheet_pair_id = :id"
)

#: One row for each pair with what a summary reads: no jsonb is carried except through the style test.
_FACTS = text(
    "SELECT p.comparison_transition_id, p.comparison_sheet_pair_id, p.state, p.status, "
    "(p.page_a_profile_id IS NOT NULL AND p.page_b_profile_id IS NOT NULL) AS both_pages, p.ai_dependent, "
    f"CASE WHEN p.status = 'different' AND r.comparison_sheet_pair_result_id IS NOT NULL THEN {_STYLE_ONLY} "
    "ELSE false END AS style_only "
    "FROM comparison_sheet_pair p LEFT JOIN comparison_sheet_pair_result r "
    "ON r.comparison_sheet_pair_result_id = p.result_id "
    "WHERE p.comparison_transition_id = ANY (CAST(:transitions AS text[]))"
)
_PROGRESS = text(
    "SELECT comparison_transition_id, count(*) AS total, count(*) FILTER (WHERE state = 'done') AS done, "
    "count(*) FILTER (WHERE state IN ('queued', 'computing')) AS open_pairs, "
    "count(*) FILTER (WHERE state = 'failed') AS failed_pairs, "
    "count(*) FILTER (WHERE state IN ('computing', 'failed') OR (state = 'done' AND result_id IS NOT NULL)) AS started "
    "FROM comparison_sheet_pair WHERE comparison_transition_id = ANY (CAST(:transitions AS text[])) "
    "GROUP BY comparison_transition_id"
)
#: What the parts phase reads of a part pair: the engine's ``part`` member of its result.
_PART_FACTS = text(
    "SELECT p.comparison_sheet_pair_id, p.parts, r.result->'part' AS part "
    "FROM comparison_sheet_pair p LEFT JOIN comparison_sheet_pair_result r "
    "ON r.comparison_sheet_pair_result_id = p.result_id "
    "WHERE p.comparison_transition_id = :transition AND p.parts IS NOT NULL ORDER BY p.pair_no"
)
#: A pair that is going to run needs an item; the latest item with the pair's dedupe key says what became of it.
_ORPHANS = text(
    "SELECT p.comparison_sheet_pair_id AS pair_id, w.state AS item_state, w.failure_reason AS item_reason "
    "FROM comparison_sheet_pair p JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id "
    "LEFT JOIN LATERAL (SELECT x.state, x.failure_reason FROM comparison_work x WHERE x.project_uid = :project "
    "AND x.kind = :kind AND x.dedupe_key = 'series_pair:' || p.comparison_sheet_pair_id "
    "ORDER BY x.created_at DESC, x.comparison_work_id DESC LIMIT 1) w ON true "
    "WHERE t.comparison_series_id = :series AND p.state IN ('queued', 'computing') "
    "AND (w.state IS NULL OR w.state IN ('succeeded', 'failed', 'cancelled'))"
)

#: The newer page of each pair with the stamp fields the permit reconciliation matches the sheets by.
_PERMIT_PAIRS = text(
    "SELECT p.comparison_sheet_pair_id, p.state, p.status, pb.page_number, pb.profile->'stamp' AS stamp, "
    "pa.profile->'stamp' AS older_stamp FROM comparison_sheet_pair p "
    "LEFT JOIN comparison_page_profile pb ON pb.comparison_page_profile_id = p.page_b_profile_id "
    "LEFT JOIN comparison_page_profile pa ON pa.comparison_page_profile_id = p.page_a_profile_id "
    "WHERE p.comparison_transition_id = :transition ORDER BY p.pair_no"
)
_REVISION_NUMBERS = text(
    "SELECT profile->'stamp'->>'revision_number' FROM comparison_page_profile "
    "WHERE version_uid = :version AND algo_version = :algo"
)
_LEADING_PAGES = text(
    "SELECT comparison_page_profile_id FROM comparison_page_profile WHERE version_uid = :version "
    "AND algo_version = :algo AND status = 'ready' AND page_number <= :limit "
    "AND coalesce((profile->>'text_layer')::boolean, false) AND NOT coalesce((profile->>'scan')::boolean, false) "
    "ORDER BY page_number"
)

_PAGE_SELECT = (
    "pa.version_uid AS a_version, pa.page_number AS a_number, pa.profile->'stamp'->>'sheet_number' AS a_sheet, "
    "pa.profile->'stamp'->>'sheet_name' AS a_title, (pa.profile->>'scan')::boolean AS a_scan, "
    "pb.version_uid AS b_version, pb.page_number AS b_number, pb.profile->'stamp'->>'sheet_number' AS b_sheet, "
    "pb.profile->'stamp'->>'sheet_name' AS b_title, (pb.profile->>'scan')::boolean AS b_scan"
)
_PAIR_JOINS = (
    "FROM comparison_sheet_pair p "
    "LEFT JOIN comparison_page_profile pa ON pa.comparison_page_profile_id = p.page_a_profile_id "
    "LEFT JOIN comparison_page_profile pb ON pb.comparison_page_profile_id = p.page_b_profile_id "
    "LEFT JOIN comparison_sheet_pair_result r ON r.comparison_sheet_pair_result_id = p.result_id "
)
_PAIR_VIEW_COLUMNS = (
    "p.comparison_sheet_pair_id, p.comparison_transition_id, p.pair_no, p.state, p.status, p.page_a_profile_id, "
    "p.page_b_profile_id, p.confidence, p.flags, p.result_id, p.ai_dependent, p.permit, p.parts, p.failure_reason, "
    f"{_PAGE_SELECT}, r.channels AS r_channels, r.reasons AS r_reasons"
)
_PAIR_PAGE = text(
    f"SELECT {_PAIR_VIEW_COLUMNS} {_PAIR_JOINS} WHERE p.comparison_transition_id = :transition "
    "AND (CAST(:after AS integer) IS NULL OR p.pair_no > :after) "
    "AND (CAST(:status AS text) IS NULL OR p.status = :status) "
    "AND (NOT :only_changes OR p.status IS DISTINCT FROM 'same') ORDER BY p.pair_no LIMIT :limit"
)
_PAIR_VIEW = text(
    f"SELECT {_PAIR_VIEW_COLUMNS}, r.result AS r_result, tr.comparison_series_id AS series_id {_PAIR_JOINS} "
    "JOIN comparison_transition tr ON tr.comparison_transition_id = p.comparison_transition_id "
    "WHERE p.comparison_sheet_pair_id = :id"
)
_TRANSITION_OWNER = text(
    "SELECT s.project_uid, s.document_uid FROM comparison_transition t "
    "JOIN comparison_series s ON s.comparison_series_id = t.comparison_series_id "
    "WHERE t.comparison_transition_id = :id"
)


def pair_dedupe_key(pair_id: str) -> str:
    """One live item per sheet pair (the project is part of the queue's own unique index)."""
    return f"{SERIES_PAIR_KIND}:{pair_id}"


def _json(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    return json.loads(value)


@dataclass(frozen=True, slots=True)
class SeriesRow:
    series_id: str
    project_uid: str
    document_uid: str
    state: str
    order_id: str | None
    matrix_id: str
    edit_no: int
    input_sha256: str
    restarted_from: str | None
    failure_reason: str | None
    actor_user_uid: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TransitionRow:
    transition_id: str
    series_id: str
    transition_no: int
    source_version_uid: str
    target_version_uid: str
    state: str
    summary: dict[str, Any] | None
    verdict: list[str] | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class PairRow:
    pair_id: str
    transition_id: str
    pair_no: int
    state: str
    status: str | None
    page_a_profile_id: str | None
    page_b_profile_id: str | None
    confidence: str | None
    flags: tuple[str, ...]
    result_id: str | None
    ai_dependent: bool
    permit: dict[str, Any] | None
    parts: dict[str, Any] | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class PairFact:
    transition_id: str
    pair_id: str
    state: str
    status: str | None
    both_pages: bool
    ai_dependent: bool
    style_only: bool


def _series(row: Any) -> SeriesRow:
    v = tuple(row)
    return SeriesRow(
        series_id=v[0], project_uid=v[1], document_uid=v[2], state=v[3], order_id=v[4], matrix_id=v[5],
        edit_no=int(v[6]), input_sha256=v[7], restarted_from=v[8], failure_reason=v[9], actor_user_uid=v[10],
        created_at=v[11], updated_at=v[12],
    )


def _transition(row: Any) -> TransitionRow:
    v = tuple(row)
    return TransitionRow(
        transition_id=v[0], series_id=v[1], transition_no=int(v[2]), source_version_uid=v[3], target_version_uid=v[4],
        state=v[5], summary=_json(v[6]), verdict=_json(v[7]), failure_reason=v[8],
    )


def _pair(row: Any) -> PairRow:
    v = tuple(row)
    return PairRow(
        pair_id=v[0], transition_id=v[1], pair_no=int(v[2]), state=v[3], status=v[4], page_a_profile_id=v[5],
        page_b_profile_id=v[6], confidence=v[7], flags=tuple(_json(v[8]) or ()), result_id=v[9], ai_dependent=bool(v[10]),
        permit=_json(v[11]), parts=_json(v[12]), failure_reason=v[13],
    )


class SeriesRepository:
    """The statements of the three tables; stateless."""

    __slots__ = ()

    # -- series ---------------------------------------------------------------------------------------------

    def insert_series(
        self, session: Session, *, series_id: str, project_uid: str, document_uid: str, order_id: str | None,
        matrix_id: str, edit_no: int, digest: str, restarted_from: str | None, actor_user_uid: str, actor_label: str,
        command_id: str,
    ) -> None:
        session.execute(_INSERT_SERIES, {
            "id": series_id, "project": project_uid, "document": document_uid, "order_id": order_id,
            "matrix_id": matrix_id, "edit_no": edit_no, "digest": digest, "restarted": restarted_from,
            "actor": actor_user_uid, "label": actor_label, "command": command_id,
        })

    def get_series(self, session: Session, series_id: str, *, for_update: bool = False) -> SeriesRow | None:
        row = session.execute(_GET_SERIES_LOCKED if for_update else _GET_SERIES, {"id": series_id}).first()
        return None if row is None else _series(row)

    def live_series(self, session: Session, document_uid: str) -> SeriesRow | None:
        row = session.execute(_LIVE_SERIES, {"document": document_uid}).first()
        return None if row is None else _series(row)

    def latest_series(self, session: Session, document_uid: str) -> SeriesRow | None:
        row = session.execute(_LATEST_SERIES, {"document": document_uid}).first()
        return None if row is None else _series(row)

    def list_series(
        self, session: Session, document_uid: str, *, after: tuple[datetime, str] | None, limit: int
    ) -> list[SeriesRow]:
        rows = session.execute(_LIST_SERIES, {
            "document": document_uid, "after_at": None if after is None else after[0],
            "after_id": None if after is None else after[1], "limit": limit,
        }).all()
        return [_series(r) for r in rows]

    def set_series_state(
        self, session: Session, series_id: str, *, from_states: Sequence[str], to_state: str, reason: str | None = None
    ) -> bool:
        """``True`` when the series was in one of ``from_states`` and now is in ``to_state``."""
        return session.execute(_SET_SERIES_STATE, {
            "id": series_id, "from_states": list(from_states), "to_state": to_state, "reason": reason,
        }).rowcount == 1

    def bound_build(self, session: Session, matrix_id: str) -> tuple[str, str, str] | None:
        """``(profile_signature, rules_version, algo_version)`` of the build a series is bound to."""
        row = session.execute(_BOUND_BUILD, {"id": matrix_id}).first()
        return None if row is None else (row[0], row[1], row[2])

    def latest_build_id(self, session: Session, document_uid: str) -> str | None:
        return session.execute(_LATEST_BUILD_ID, {"document": document_uid}).scalar_one_or_none()

    # -- transitions ----------------------------------------------------------------------------------------

    def insert_transition(
        self, session: Session, *, series_id: str, number: int, source: str, target: str
    ) -> str:
        transition_id = str(ComparisonTransitionId.new())
        session.execute(_INSERT_TRANSITION, {
            "id": transition_id, "series": series_id, "no": number, "source": source, "target": target,
        })
        return transition_id

    def transitions(self, session: Session, series_id: str) -> list[TransitionRow]:
        return [_transition(r) for r in session.execute(_TRANSITIONS, {"series": series_id}).all()]

    def get_transition(self, session: Session, transition_id: str, *, for_update: bool = False) -> TransitionRow | None:
        row = session.execute(_LOCK_TRANSITION if for_update else _GET_TRANSITION, {"id": transition_id}).first()
        return None if row is None else _transition(row)

    def transition_owner(self, session: Session, transition_id: str) -> tuple[str, str] | None:
        """``(project_uid, document_uid)`` of the series a transition belongs to."""
        row = session.execute(_TRANSITION_OWNER, {"id": transition_id}).first()
        return None if row is None else (row[0], row[1])

    def set_transition_state(
        self, session: Session, transition_id: str, *, from_states: Sequence[str], to_state: str,
        summary: Mapping[str, Any] | None = None, verdict: Sequence[str] | None = None, reason: str | None = None,
    ) -> bool:
        return session.execute(_SET_TRANSITION_STATE, {
            "id": transition_id, "from_states": list(from_states), "to_state": to_state,
            "summary": None if summary is None else json.dumps(dict(summary), sort_keys=True),
            "verdict": None if verdict is None else json.dumps(list(verdict)), "reason": reason,
        }).rowcount == 1

    def cancel_transitions(self, session: Session, series_id: str) -> int:
        return int(session.execute(_CANCEL_TRANSITIONS, {"series": series_id}).rowcount)

    def run_transition(self, session: Session, transition_id: str) -> None:
        session.execute(_RUN_TRANSITION, {"id": transition_id})

    # -- pairs ----------------------------------------------------------------------------------------------

    def insert_pair(self, session: Session, transition_id: str, pair: PlannedPair, *, parts: Mapping[str, Any] | None) -> str:
        pair_id = str(ComparisonSheetPairId.new())
        immediate = pair.status is not None
        session.execute(_INSERT_PAIR, {
            "id": pair_id, "transition": transition_id, "no": pair.pair_no,
            "state": PAIR_DONE if immediate else PAIR_QUEUED, "status": pair.status,
            "page_a": pair.page_a_profile_id, "page_b": pair.page_b_profile_id, "confidence": pair.confidence,
            "flags": json.dumps(list(pair.flags)), "ai": pair.ai_dependent,
            "parts": None if parts is None else json.dumps(dict(parts), sort_keys=True),
        })
        return pair_id

    def get_pair(self, session: Session, pair_id: str) -> PairRow | None:
        row = session.execute(_GET_PAIR, {"id": pair_id}).first()
        return None if row is None else _pair(row)

    def pairs_of(self, session: Session, transition_id: str) -> list[PairRow]:
        return [_pair(r) for r in session.execute(_PAIRS_OF_TRANSITION, {"transition": transition_id}).all()]

    def mark_computing(self, session: Session, pair_id: str) -> bool:
        return session.execute(_MARK_COMPUTING, {"id": pair_id}).rowcount == 1

    def finish_pair(
        self, session: Session, pair_id: str, *, status: str, result_id: str | None, parts: Mapping[str, Any] | None
    ) -> bool:
        return session.execute(_FINISH_PAIR, {
            "id": pair_id, "status": status, "result": result_id,
            "parts": None if parts is None else json.dumps(dict(parts), sort_keys=True),
        }).rowcount == 1

    def fail_pair(self, session: Session, pair_id: str, reason: str) -> bool:
        return session.execute(_FAIL_PAIR, {"id": pair_id, "reason": reason[:128]}).rowcount == 1

    def requeue_pair(self, session: Session, pair_id: str) -> bool:
        return session.execute(_REQUEUE_PAIR, {"id": pair_id}).rowcount == 1

    def requeue_unfinished(self, session: Session, transition_ids: Sequence[str]) -> list[str]:
        if not transition_ids:
            return []
        return [str(r[0]) for r in session.execute(_REQUEUE_UNFINISHED, {"transitions": list(transition_ids)}).all()]

    def queued_pairs(self, session: Session, series_id: str) -> list[tuple[str, int, int]]:
        """``(pair_id, transition_no, pair_no)`` of the pairs waiting for the engine, in the order they should run."""
        return [(r[0], int(r[1]), int(r[2])) for r in session.execute(_QUEUED_PAIRS, {"series": series_id}).all()]

    def set_permit(self, session: Session, pair_id: str, permit: Mapping[str, Any] | None) -> None:
        session.execute(_SET_PERMIT, {"id": pair_id, "permit": None if permit is None else json.dumps(dict(permit))})

    def set_parts(self, session: Session, pair_id: str, parts: Mapping[str, Any]) -> None:
        session.execute(_SET_PARTS, {"id": pair_id, "parts": json.dumps(dict(parts), sort_keys=True)})

    # -- what the verdict and the phases read ----------------------------------------------------------------

    def facts(self, session: Session, transition_ids: Sequence[str]) -> list[PairFact]:
        if not transition_ids:
            return []
        rows = session.execute(_FACTS, {"transitions": list(transition_ids)}).all()
        return [PairFact(r[0], r[1], r[2], r[3], bool(r[4]), bool(r[5]), bool(r[6])) for r in (tuple(x) for x in rows)]

    def progress(self, session: Session, transition_ids: Sequence[str]) -> dict[str, dict[str, int]]:
        if not transition_ids:
            return {}
        rows = session.execute(_PROGRESS, {"transitions": list(transition_ids)}).all()
        return {
            r[0]: {"total": int(r[1]), "done": int(r[2]), "open": int(r[3]), "failed": int(r[4]), "started": int(r[5])}
            for r in (tuple(x) for x in rows)
        }

    def part_facts(self, session: Session, transition_id: str) -> list[tuple[str, dict[str, Any], dict[str, Any] | None]]:
        """``(pair_id, parts record, the engine's part member of its result)`` of each pair with a ``parts`` record."""
        rows = session.execute(_PART_FACTS, {"transition": transition_id}).all()
        return [(r[0], _json(r[1]) or {}, _json(r[2])) for r in (tuple(x) for x in rows)]

    def orphans(self, session: Session, series: SeriesRow) -> list[tuple[str, str | None, str | None]]:
        """Pairs that still wait for a result although no item of theirs is going to run: ``(pair_id, item state, reason)``."""
        rows = session.execute(
            _ORPHANS, {"series": series.series_id, "project": series.project_uid, "kind": SERIES_PAIR_KIND}
        ).all()
        return [(r[0], r[1], r[2]) for r in (tuple(x) for x in rows)]

    def permit_pairs(self, session: Session, transition_id: str) -> list[Mapping[str, Any]]:
        rows = session.execute(_PERMIT_PAIRS, {"transition": transition_id}).all()
        return [
            {
                "pair_id": r[0], "state": r[1], "status": r[2], "b_page": r[3], "stamp": _json(r[4]) or {},
                "older_stamp": _json(r[5]) or {},
            }
            for r in (tuple(x) for x in rows)
        ]

    def revision_numbers(self, session: Session, version_uid: str, algo_version: str) -> list[str | None]:
        return [r[0] for r in session.execute(_REVISION_NUMBERS, {"version": version_uid, "algo": algo_version}).all()]

    def leading_text_pages(self, session: Session, version_uid: str, algo_version: str, limit: int) -> list[str]:
        """The profile identities of the first ``limit`` pages of a version that have a text layer and are not scans."""
        return [r[0] for r in session.execute(
            _LEADING_PAGES, {"version": version_uid, "algo": algo_version, "limit": limit}
        ).all()]

    # -- the views -------------------------------------------------------------------------------------------

    def pair_page(
        self, session: Session, transition_id: str, *, after: int | None, status: str | None, only_changes: bool,
        limit: int,
    ) -> list[Mapping[str, Any]]:
        rows = session.execute(_PAIR_PAGE, {
            "transition": transition_id, "after": after, "status": status, "only_changes": only_changes, "limit": limit,
        }).mappings().all()
        return [dict(r) for r in rows]

    def pair_view(self, session: Session, pair_id: str) -> Mapping[str, Any] | None:
        row = session.execute(_PAIR_VIEW, {"id": pair_id}).mappings().first()
        return None if row is None else dict(row)
