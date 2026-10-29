"""The statements of the AI pair check (`CMP-VC-AIPAIR-01`): the only writer of ``comparison_ai_pair_question``,
``comparison_ai_pair_answer`` and ``comparison_ai_link``.

Statements only: every method takes the caller's session and **never commits**; the handler and the service own the transactions.
It reads, and never writes, ``comparison_page_profile`` and ``blob`` (what a page shows), ``comparison_work`` (the state of a
question's item) and ``comparison_ai_job`` (which job holds a document). The job row itself is written by
:class:`~auditmanager.comparison.ai_jobs.repository.AiJobRepository` only; this module never says ``UPDATE comparison_ai_job``.

The three tables are protected by the database as well: an answer is immutable (``UPDATE`` and ``DELETE`` are refused), a question
moves along the edges of migration ``0040`` and keeps its cell, and a link is append-only with the unique key
``(matrix, page, other page)``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.ai_pairs.model import HINT_DECISIONS, PageFacts
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonAiLinkId, ComparisonAiPairAnswerId, ComparisonAiPairQuestionId

__all__ = [
    "AiPairRepository",
    "HintRow",
    "JobFigures",
    "QuestionRow",
    "StoredAnswer",
]

_FACTS = text(
    "SELECT p.comparison_page_profile_id, p.version_uid, p.page_number, p.content_key, "
    "p.profile -> 'stamp' ->> 'sheet_number' AS sheet_number, p.profile -> 'stamp' ->> 'sheet_name' AS sheet_name, "
    "p.profile -> 'stamp' ->> 'designation' AS designation, p.preview_blob_id, b.sha256 AS preview_sha256, "
    "coalesce(b.size_bytes, 0) AS preview_size "
    "FROM comparison_page_profile p LEFT JOIN blob b ON b.blob_id = p.preview_blob_id AND b.state = 'available' "
    "WHERE p.version_uid = ANY (CAST(:versions AS text[])) AND p.algo_version = :algo ORDER BY p.version_uid, p.page_number"
)
_FACTS_OF = text(
    "SELECT p.comparison_page_profile_id, p.version_uid, p.page_number, p.content_key, "
    "p.profile -> 'stamp' ->> 'sheet_number' AS sheet_number, p.profile -> 'stamp' ->> 'sheet_name' AS sheet_name, "
    "p.profile -> 'stamp' ->> 'designation' AS designation, p.preview_blob_id, b.sha256 AS preview_sha256, "
    "coalesce(b.size_bytes, 0) AS preview_size "
    "FROM unnest(CAST(:versions AS text[]), CAST(:pages AS integer[])) AS w (version_uid, page_number) "
    "JOIN comparison_page_profile p ON p.version_uid = w.version_uid AND p.page_number = w.page_number AND p.algo_version = :algo "
    "LEFT JOIN blob b ON b.blob_id = p.preview_blob_id AND b.state = 'available'"
)
_DOCUMENT = text(
    "SELECT d.project_uid, d.display_title FROM document d WHERE d.document_uid = :document"
)
_PROJECT = text("SELECT 1 FROM project WHERE project_uid = :project")
_ANSWERS = text(
    "SELECT comparison_ai_pair_answer_id, content_key, question_kind, confidence, answer, comparison_model_call_id, created_at "
    "FROM comparison_ai_pair_answer WHERE project_uid = :project AND content_key = ANY (CAST(:keys AS text[]))"
)
_ANSWER_BY_ID = text(
    "SELECT comparison_ai_pair_answer_id, content_key, question_kind, confidence, answer, comparison_model_call_id, created_at "
    "FROM comparison_ai_pair_answer WHERE comparison_ai_pair_answer_id = :id"
)
_INSERT_ANSWER = text(
    "INSERT INTO comparison_ai_pair_answer (comparison_ai_pair_answer_id, project_uid, content_key, question_kind, "
    "prompt_version, model_identity, confidence, answer, comparison_model_call_id) "
    "VALUES (:id, :project, :key, :kind, :prompt_version, :model, :confidence, CAST(:answer AS jsonb), :call) "
    "ON CONFLICT (project_uid, content_key) DO NOTHING RETURNING comparison_ai_pair_answer_id"
)
_QUESTION_COLUMNS = (
    "q.comparison_ai_pair_question_id AS question_id, q.comparison_ai_job_id AS job_id, q.project_uid, q.document_uid, "
    "q.comparison_matrix_id AS matrix_id, q.kind, q.page_version_uid, q.page_number, q.version_uid, q.candidates, q.state, "
    "q.answer_id, q.reverse_answer_id, q.decision, q.hint_version_uid, q.hint_page_number, q.comparison_ai_link_id AS link_id, "
    "q.failure_reason, q.created_at"
)
_INSERT_QUESTION = text(
    "INSERT INTO comparison_ai_pair_question (comparison_ai_pair_question_id, comparison_ai_job_id, project_uid, document_uid, "
    "comparison_matrix_id, kind, page_version_uid, page_number, version_uid, candidates) "
    "VALUES (:id, :job, :project, :document, :matrix, :kind, :page_version, :page_number, :version, CAST(:candidates AS jsonb)) "
    "ON CONFLICT (comparison_ai_job_id, page_version_uid, page_number, version_uid) DO NOTHING "
    "RETURNING comparison_ai_pair_question_id"
)
_QUESTION_OF_CELL = text(
    "SELECT comparison_ai_pair_question_id FROM comparison_ai_pair_question WHERE comparison_ai_job_id = :job "
    "AND page_version_uid = :page_version AND page_number = :page_number AND version_uid = :version"
)
_QUESTION = text(f"SELECT {_QUESTION_COLUMNS} FROM comparison_ai_pair_question q WHERE q.comparison_ai_pair_question_id = :id")
_QUESTION_LOCKED = text(
    f"SELECT {_QUESTION_COLUMNS} FROM comparison_ai_pair_question q WHERE q.comparison_ai_pair_question_id = :id FOR UPDATE"
)
_QUESTIONS_OF_JOB = text(
    f"SELECT {_QUESTION_COLUMNS} FROM comparison_ai_pair_question q WHERE q.comparison_ai_job_id = :job "
    "ORDER BY q.created_at, q.comparison_ai_pair_question_id"
)
_SET_ANSWERS = text(
    "UPDATE comparison_ai_pair_question SET answer_id = coalesce(CAST(:answer AS text), answer_id), "
    "reverse_answer_id = coalesce(CAST(:reverse AS text), reverse_answer_id), updated_at = clock_timestamp() "
    "WHERE comparison_ai_pair_question_id = :id AND state = 'queued'"
)
_SETTLE = text(
    "UPDATE comparison_ai_pair_question SET state = :state, decision = :decision, hint_version_uid = :hint_version, "
    "hint_page_number = :hint_page, comparison_ai_link_id = :link, failure_reason = :failure, "
    "updated_at = clock_timestamp() WHERE comparison_ai_pair_question_id = :id AND state = 'queued'"
)
_INSERT_LINK = text(
    "INSERT INTO comparison_ai_link (comparison_ai_link_id, document_uid, comparison_matrix_id, page_version_uid, page_number, "
    "other_version_uid, other_page_number, answered_state, confidence, comparison_model_call_id, details) "
    "VALUES (:id, :document, :matrix, :page_version, :page_number, :other_version, :other_page, :answered_state, 'high', "
    ":call, CAST(:details AS jsonb)) "
    "ON CONFLICT (comparison_matrix_id, page_version_uid, page_number, other_version_uid, other_page_number) DO NOTHING "
    "RETURNING comparison_ai_link_id"
)
_LINK_OF_PAGES = text(
    "SELECT comparison_ai_link_id FROM comparison_ai_link WHERE comparison_matrix_id = :matrix AND page_version_uid = :page_version "
    "AND page_number = :page_number AND other_version_uid = :other_version AND other_page_number = :other_page"
)
_ITEMS_OF_JOB = text(
    "SELECT DISTINCT ON (dedupe_key) dedupe_key, state, failure_reason FROM comparison_work "
    "WHERE comparison_ai_job_id = :job AND dedupe_key IS NOT NULL "
    "ORDER BY dedupe_key, created_at DESC, comparison_work_id DESC"
)
_PAYLOADS = text(
    "SELECT payload, state FROM ("
    "SELECT DISTINCT ON (dedupe_key) payload, state FROM comparison_work WHERE comparison_ai_job_id = :job "
    "AND dedupe_key IS NOT NULL ORDER BY dedupe_key, created_at DESC, comparison_work_id DESC) newest "
    "WHERE payload ->> 'step' = 'ask' AND state = ANY (CAST(:states AS text[]))"
)
_REQUEUE = text(
    "UPDATE comparison_ai_pair_question SET state = 'queued', decision = NULL, failure_reason = NULL, "
    "updated_at = clock_timestamp() WHERE comparison_ai_pair_question_id = :id AND state = ANY (ARRAY['failed', 'cancelled'])"
)
_LIVE_JOB = text(
    "SELECT comparison_ai_job_id FROM comparison_ai_job WHERE method = 'pair_check' AND document_uid = :document "
    "AND state IN ('queued', 'running', 'paused') ORDER BY created_at DESC LIMIT 1"
)
_LATEST_JOB = text(
    "SELECT comparison_ai_job_id FROM comparison_ai_job WHERE method = 'pair_check' AND document_uid = :document "
    "ORDER BY created_at DESC, comparison_ai_job_id DESC LIMIT 1"
)
_FIGURES = text(
    "SELECT count(*) AS questions, count(*) FILTER (WHERE q.state = 'answered') AS answered, "
    "count(*) FILTER (WHERE q.decision = 'link_accepted') AS pairs, "
    "count(*) FILTER (WHERE q.decision = ANY (CAST(:hints AS text[]))) AS hints, "
    "count(*) FILTER (WHERE q.decision IN ('none', 'medium_none')) AS against, "
    "count(*) FILTER (WHERE q.state = 'failed') AS failed, "
    "count(*) FILTER (WHERE a.created_at < q.created_at) AS reused "
    "FROM comparison_ai_pair_question q "
    "LEFT JOIN comparison_ai_pair_answer a ON a.comparison_ai_pair_answer_id = q.answer_id "
    "WHERE q.comparison_ai_job_id = :job"
)
_HINTS = text(
    "SELECT q.comparison_ai_pair_question_id AS question_id, q.comparison_ai_job_id AS job_id, "
    "q.comparison_matrix_id AS matrix_id, q.kind, q.decision, q.page_version_uid, q.page_number, q.version_uid, q.candidates, "
    "q.hint_version_uid, q.hint_page_number, q.comparison_ai_link_id AS link_id, q.created_at, "
    "(q.comparison_matrix_id IS DISTINCT FROM (SELECT m.comparison_matrix_id FROM comparison_matrix m "
    " WHERE m.document_uid = q.document_uid ORDER BY m.build_no DESC LIMIT 1)) AS stale, "
    "a.confidence AS confidence, a.answer ->> 'reason' AS reason, "
    "(SELECT p.comparison_page_profile_id FROM comparison_page_profile p WHERE p.version_uid = q.page_version_uid "
    " AND p.page_number = q.page_number AND p.algo_version = :algo) AS page_profile_id, "
    "(SELECT p.comparison_page_profile_id FROM comparison_page_profile p WHERE p.version_uid = q.hint_version_uid "
    " AND p.page_number = q.hint_page_number AND p.algo_version = :algo) AS hint_profile_id "
    "FROM comparison_ai_pair_question q "
    "LEFT JOIN comparison_ai_pair_answer a ON a.comparison_ai_pair_answer_id = q.answer_id "
    "WHERE q.document_uid = :document AND q.decision IS NOT NULL "
    "AND (CAST(:after_at AS timestamptz) IS NULL OR (q.created_at, q.comparison_ai_pair_question_id) < (:after_at, :after_id)) "
    "ORDER BY q.created_at DESC, q.comparison_ai_pair_question_id DESC LIMIT :limit"
)


@dataclass(frozen=True, slots=True)
class StoredAnswer:
    """A row of ``comparison_ai_pair_answer``: the validated answer and when it was made."""

    answer_id: str
    content_key: str
    kind: str
    confidence: str
    answer: Mapping[str, Any]
    call_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class QuestionRow:
    """A row of ``comparison_ai_pair_question``."""

    question_id: str
    job_id: str
    project_uid: str
    document_uid: str
    matrix_id: str
    kind: str
    page_version_uid: str
    page_number: int
    version_uid: str
    candidates: tuple[Mapping[str, Any], ...]
    state: str
    answer_id: str | None
    reverse_answer_id: str | None
    decision: str | None
    hint_version_uid: str | None
    hint_page_number: int | None
    link_id: str | None
    failure_reason: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class HintRow:
    """One question that has a decision, as the hint list shows it."""

    question_id: str
    job_id: str
    matrix_id: str
    kind: str
    decision: str
    page_version_uid: str
    page_number: int
    page_profile_id: str | None
    version_uid: str
    candidates: tuple[Mapping[str, Any], ...]
    hint_version_uid: str | None
    hint_page_number: int | None
    hint_profile_id: str | None
    link_id: str | None
    stale: bool
    confidence: str | None
    reason: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class JobFigures:
    """«вопросов · пар · подсказок · против» of one job."""

    questions: int
    answered: int
    pairs: int
    hints: int
    against: int
    failed: int
    reused: int


def _json(value: Any) -> Any:
    return value if isinstance(value, (list, dict)) else json.loads(value)


def _question(row: Any) -> QuestionRow:
    candidates = tuple(_json(row["candidates"]))
    return QuestionRow(
        question_id=row["question_id"], job_id=row["job_id"], project_uid=row["project_uid"], document_uid=row["document_uid"],
        matrix_id=row["matrix_id"], kind=row["kind"], page_version_uid=row["page_version_uid"], page_number=int(row["page_number"]),
        version_uid=row["version_uid"], candidates=candidates, state=row["state"], answer_id=row["answer_id"],
        reverse_answer_id=row["reverse_answer_id"], decision=row["decision"], hint_version_uid=row["hint_version_uid"],
        hint_page_number=None if row["hint_page_number"] is None else int(row["hint_page_number"]), link_id=row["link_id"],
        failure_reason=row["failure_reason"], created_at=row["created_at"],
    )


def _facts(row: Any) -> PageFacts:
    sha = row["preview_sha256"]
    return PageFacts(
        page_profile_id=row["comparison_page_profile_id"], version_uid=row["version_uid"], page_number=int(row["page_number"]),
        content_key=row["content_key"], sheet_number=(row["sheet_number"] or "").strip(),
        title=" ".join((row["sheet_name"] or "").split()), designation=(row["designation"] or "").strip(),
        preview_blob_id=row["preview_blob_id"] if sha is not None else None, preview_sha256=sha,
        preview_size=int(row["preview_size"] or 0) if sha is not None else 0,
    )


def _stored(row: Any) -> StoredAnswer:
    return StoredAnswer(
        answer_id=row["comparison_ai_pair_answer_id"], content_key=row["content_key"], kind=row["question_kind"],
        confidence=row["confidence"], answer=dict(_json(row["answer"])), call_id=row["comparison_model_call_id"],
        created_at=row["created_at"],
    )


class AiPairRepository:
    """Stateless; every method takes the caller's session and never commits."""

    __slots__ = ()

    # -- reads of other tables -----------------------------------------------------------------------
    def require_document(self, session: Session, project_uid: str, document_uid: str) -> str:
        """The document's display title; ``not_found`` naming the project or the document when either is not there, or the
        document belongs to another project (never an empty answer for a parent that does not exist)."""
        if session.execute(_PROJECT, {"project": project_uid}).first() is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Project")
        row = session.execute(_DOCUMENT, {"document": document_uid}).first()
        if row is None or str(row[0]) != project_uid:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
        return str(row[1] or "")

    def page_facts(
        self, session: Session, version_uids: Sequence[str], algo_version: str,
    ) -> dict[tuple[str, int], PageFacts]:
        """What the stored profiles of the versions say of their pages, keyed by ``(version, page number)``: the stamp's sheet
        number, title and designation, the content key and the stored preview. The archive is not opened."""
        rows = session.execute(_FACTS, {"versions": list(version_uids), "algo": algo_version}).mappings()
        return {(row["version_uid"], int(row["page_number"])): _facts(row) for row in rows}

    def page_facts_of(
        self, session: Session, pages: Sequence[tuple[str, int]], algo_version: str,
    ) -> dict[tuple[str, int], PageFacts]:
        """:meth:`page_facts` for the named pages only (what one question needs, not the whole document set)."""
        wanted = sorted(set(pages))
        if not wanted:
            return {}
        rows = session.execute(
            _FACTS_OF, {"versions": [v for v, _ in wanted], "pages": [n for _, n in wanted], "algo": algo_version},
        ).mappings()
        return {(row["version_uid"], int(row["page_number"])): _facts(row) for row in rows}

    def live_job_of(self, session: Session, document_uid: str) -> str | None:
        row = session.execute(_LIVE_JOB, {"document": document_uid}).first()
        return None if row is None else str(row[0])

    def latest_job_of(self, session: Session, document_uid: str) -> str | None:
        row = session.execute(_LATEST_JOB, {"document": document_uid}).first()
        return None if row is None else str(row[0])

    def item_states(self, session: Session, job_id: str) -> dict[str, tuple[str, str | None]]:
        """``{dedupe key: (state, failure reason)}`` of the newest work item of each unit of a job."""
        return {
            str(row["dedupe_key"]): (str(row["state"]), row["failure_reason"])
            for row in session.execute(_ITEMS_OF_JOB, {"job": job_id}).mappings()
        }

    # -- answers -------------------------------------------------------------------------------------
    def stored_answers(self, session: Session, project_uid: str, keys: Sequence[str]) -> dict[str, StoredAnswer]:
        """The answers already stored under these content keys (a key never sent again is one that is here)."""
        if not keys:
            return {}
        rows = session.execute(_ANSWERS, {"project": project_uid, "keys": list(keys)}).mappings()
        return {row["content_key"]: _stored(row) for row in rows}

    def answer(self, session: Session, answer_id: str) -> StoredAnswer | None:
        row = session.execute(_ANSWER_BY_ID, {"id": answer_id}).mappings().first()
        return None if row is None else _stored(row)

    def store_answer(
        self, session: Session, *, project_uid: str, content_key: str, kind: str, prompt_version: str, model_identity: str,
        confidence: str, answer: Mapping[str, Any], call_id: str | None,
    ) -> StoredAnswer:
        """Store the answer under its content key and answer the row now stored. A concurrent writer of the same key wins and its
        row is returned (the table is unique on ``(project, content key)``: a question is answered once)."""
        inserted = session.execute(_INSERT_ANSWER, {
            "id": str(ComparisonAiPairAnswerId.new()), "project": project_uid, "key": content_key, "kind": kind,
            "prompt_version": prompt_version, "model": model_identity, "confidence": confidence,
            "answer": json.dumps(dict(answer), sort_keys=True, ensure_ascii=False), "call": call_id,
        }).scalar_one_or_none()
        stored = self.stored_answers(session, project_uid, [content_key])[content_key]
        if inserted is not None and stored.answer_id != str(inserted):  # pragma: no cover - the unique key says otherwise
            raise RuntimeError("the stored answer is not the one just written")
        return stored

    # -- questions -----------------------------------------------------------------------------------
    def insert_question(
        self, session: Session, *, job_id: str, project_uid: str, document_uid: str, matrix_id: str, kind: str,
        page_version_uid: str, page_number: int, version_uid: str, candidates: Sequence[Mapping[str, Any]],
    ) -> str:
        """Write the question of a cell for a job ``queued`` and answer its identity; a cell asked twice by one job is one row."""
        values = {
            "job": job_id, "project": project_uid, "document": document_uid, "matrix": matrix_id, "kind": kind,
            "page_version": page_version_uid, "page_number": page_number, "version": version_uid,
        }
        inserted = session.execute(
            _INSERT_QUESTION,
            {**values, "id": str(ComparisonAiPairQuestionId.new()), "candidates": json.dumps(list(candidates), sort_keys=True)},
        ).scalar_one_or_none()
        if inserted is not None:
            return str(inserted)
        return str(session.execute(_QUESTION_OF_CELL, values).scalar_one())

    def question(self, session: Session, question_id: str, *, lock: bool = False) -> QuestionRow | None:
        row = session.execute(_QUESTION_LOCKED if lock else _QUESTION, {"id": question_id}).mappings().first()
        return None if row is None else _question(row)

    def questions_of_job(self, session: Session, job_id: str) -> list[QuestionRow]:
        return [_question(row) for row in session.execute(_QUESTIONS_OF_JOB, {"job": job_id}).mappings()]

    def set_answers(
        self, session: Session, question_id: str, *, answer_id: str | None = None, reverse_answer_id: str | None = None,
    ) -> bool:
        """Remember which answers a question used (its state stays ``queued``: the decision is made once every question is
        asked, because one decision depends on the others). ``False`` when the question is no longer ``queued``."""
        return session.execute(
            _SET_ANSWERS, {"id": question_id, "answer": answer_id, "reverse": reverse_answer_id},
        ).rowcount == 1

    def settle(
        self, session: Session, question_id: str, *, state: str, decision: str | None, hint: tuple[str, int] | None = None,
        link_id: str | None = None, failure_reason: str | None = None,
    ) -> bool:
        """The one write that ends a question: ``queued`` -> ``answered`` (with its decision, the model's page when it named
        one and the link it wrote), ``failed`` (with its reason) or ``cancelled``. ``False`` when it already ended."""
        return session.execute(_SETTLE, {
            "id": question_id, "state": state, "decision": decision,
            "hint_version": None if hint is None else hint[0], "hint_page": None if hint is None else hint[1],
            "link": link_id, "failure": failure_reason,
        }).rowcount == 1

    def requeue_question(self, session: Session, question_id: str) -> bool:
        """``failed | cancelled`` -> ``queued`` (the database's edge): a question asked again by a retry."""
        return session.execute(_REQUEUE, {"id": question_id}).rowcount == 1

    def ask_payloads(self, session: Session, job_id: str, states: Sequence[str]) -> list[Mapping[str, Any]]:
        """The payloads of the job's question items whose newest work item is in one of ``states``: what a job still has to ask
        (``queued``, ``paused``, ...) or asked and failed (``failed``). Exact, unlike a re-derivation from a matrix that may
        have moved since."""
        rows = session.execute(_PAYLOADS, {"job": job_id, "states": list(states)}).mappings()
        return [dict(_json(row["payload"])) for row in rows]

    # -- the accepted link ---------------------------------------------------------------------------
    def insert_link(
        self, session: Session, *, document_uid: str, matrix_id: str, page_version_uid: str, page_number: int,
        other_version_uid: str, other_page_number: int, answered_state: str, call_id: str | None, details: Mapping[str, Any],
    ) -> str:
        """Write the accepted AI link (``confidence`` is ``high`` by the table's CHECK) and answer its identity; the same pages of
        the same build are one row. The link is the AI layer: the matrix reads it, and a manual edit wins over it there."""
        values = {
            "matrix": matrix_id, "page_version": page_version_uid, "page_number": page_number,
            "other_version": other_version_uid, "other_page": other_page_number,
        }
        inserted = session.execute(_INSERT_LINK, {
            **values, "id": str(ComparisonAiLinkId.new()), "document": document_uid, "answered_state": answered_state,
            "call": call_id, "details": json.dumps(dict(details), sort_keys=True),
        }).scalar_one_or_none()
        if inserted is not None:
            return str(inserted)
        return str(session.execute(_LINK_OF_PAGES, values).scalar_one())

    # -- reads for the screens -----------------------------------------------------------------------
    def figures(self, session: Session, job_id: str) -> JobFigures:
        row = session.execute(_FIGURES, {"job": job_id, "hints": sorted(HINT_DECISIONS)}).one()
        return JobFigures(
            questions=int(row.questions), answered=int(row.answered), pairs=int(row.pairs), hints=int(row.hints),
            against=int(row.against), failed=int(row.failed), reused=int(row.reused),
        )

    def hints(
        self, session: Session, document_uid: str, *, algo_version: str, after: tuple[datetime, str] | None, limit: int,
    ) -> list[HintRow]:
        rows = session.execute(_HINTS, {
            "document": document_uid, "algo": algo_version, "limit": limit,
            "after_at": None if after is None else after[0], "after_id": None if after is None else after[1],
        }).mappings()
        return [
            HintRow(
                question_id=r["question_id"], job_id=r["job_id"], matrix_id=r["matrix_id"], kind=r["kind"], decision=r["decision"],
                page_version_uid=r["page_version_uid"], page_number=int(r["page_number"]), page_profile_id=r["page_profile_id"],
                version_uid=r["version_uid"], candidates=tuple(_json(r["candidates"])), hint_version_uid=r["hint_version_uid"],
                hint_page_number=None if r["hint_page_number"] is None else int(r["hint_page_number"]),
                hint_profile_id=r["hint_profile_id"], link_id=r["link_id"], stale=bool(r["stale"]), confidence=r["confidence"],
                reason=r["reason"], created_at=r["created_at"],
            )
            for r in rows
        ]


LIVE_ITEM_STATES: Final[frozenset[str]] = frozenset({"queued", "leased", "running", "retry_wait", "paused", "spend_unknown"})
