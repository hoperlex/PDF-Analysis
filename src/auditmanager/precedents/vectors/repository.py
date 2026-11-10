"""The SQL of the night encoder: the control row, the queue of intents and the vectors (`ADR-0029` decision 8, migration ``0064``).

Every function takes the caller's session and ends no transaction: the pass and the routes decide what is one unit of work. What the database
guards itself is relied on, not repeated (the unit norm of a vector, the pair of a state and its reason, the number of an event without a gap,
the forget guard that refuses a new row for a forgotten case), and a row the database refuses is handled where it is written.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.precedents.vectors.intents import (
    EMBEDDING_PROFILE,
    MAX_ATTEMPTS,
    MODEL_REVISION,
    POISON_ATTEMPTS,
    POISON_TOKEN_LIMIT,
    VIEW_FINDING,
    EncodedVector,
    build_finding_view,
    input_sha256,
    pgvector_literal,
)
from auditmanager.precedents.vectors.window import DEFAULT_WINDOW, SETTING_NAME, WindowSetting, parse_setting
from auditmanager.shared.identity import DecisionMemoryEmbeddingIntentId, VectorControlEventId

__all__ = [
    "ControlRow", "IntentText", "ImportOutcome", "add_intents_for_new_cases", "bump_attempts", "count_intents", "import_vectors",
    "lock_control", "mark_poisoned", "pending_intent_texts", "read_control", "read_window_setting", "running_work", "set_paused",
    "set_window_state",
]

#: One tick adds at most this many intents; a backfill of many cases takes as many ticks as it needs.
BACKFILL_BATCH: Final[int] = 500
#: At most this many texts go to the encoder in one round. ``embed-texts`` is all or nothing (it keeps no partial answer), so a round is sized to
#: end in minutes, not hours: a window that is cut short loses one round and not the night, and a long queue is several rounds of the same night.
EXPORT_LIMIT: Final[int] = 500

_CONTROL = text(
    "SELECT paused, paused_since, window_state, window_reason, window_changed_at FROM vector_control WHERE control_key = 'default'"
)
_LOCK_CONTROL = text(
    "SELECT paused, paused_since, window_state, window_reason, window_changed_at FROM vector_control "
    "WHERE control_key = 'default' FOR UPDATE"
)
_NEXT_EVENT = text("SELECT COALESCE(MAX(event_no), 0) + 1 FROM vector_control_event WHERE control_key = 'default'")
_INSERT_EVENT = text(
    "INSERT INTO vector_control_event (control_event_id, control_key, event_no, kind, reason, actor_user_uid) "
    "VALUES (:event_id, 'default', :event_no, :kind, :reason, :actor)"
)
_SET_WINDOW = text(
    "UPDATE vector_control SET window_state = :state, window_reason = :reason, window_changed_at = COALESCE(:at, clock_timestamp()) "
    "WHERE control_key = 'default'"
)
_SET_PAUSED = text(
    "UPDATE vector_control SET paused = :paused, "
    "paused_since = CASE WHEN :paused THEN clock_timestamp() ELSE NULL END WHERE control_key = 'default'"
)
_WINDOW_SETTING = text(
    "SELECT value FROM precedent_setting_event WHERE setting_name = :name ORDER BY revision DESC LIMIT 1"
)
#: Cases that are not forgotten and have neither an intent nor a vector for the view: the backfill (plan-v5 section 5, «Добор»). A forgotten
#: case takes no new row (the database refuses it), so it is left out here rather than refused one by one.
_CASES_WITHOUT_INTENT = text(
    "SELECT k.case_id, c.revision, k.category, c.finding_text, c.recommendation_text "
    "FROM decision_memory_case k JOIN decision_memory_content c ON c.case_id = k.case_id "
    "WHERE NOT EXISTS (SELECT 1 FROM decision_memory_status_event f WHERE f.case_id = k.case_id AND f.kind = 'forget') "
    "AND NOT EXISTS (SELECT 1 FROM decision_memory_embedding_intent i WHERE i.case_id = c.case_id AND i.revision = c.revision "
    "AND i.view_kind = :view AND i.embedding_profile = :profile) "
    "AND NOT EXISTS (SELECT 1 FROM decision_memory_embedding e WHERE e.case_id = c.case_id AND e.revision = c.revision "
    "AND e.view_kind = :view AND e.embedding_profile = :profile) "
    "ORDER BY k.captured_at, k.case_id, c.revision LIMIT :batch"
)
_INSERT_INTENT = text(
    "INSERT INTO decision_memory_embedding_intent (intent_id, case_id, revision, view_kind, embedding_profile, input_sha256) "
    "VALUES (:intent_id, :case_id, :revision, :view, :profile, :digest) "
    "ON CONFLICT ON CONSTRAINT uq_decision_memory_embedding_intent_view DO NOTHING"
)
_PENDING = text(
    "SELECT i.intent_id, i.case_id, i.revision, i.input_sha256, k.category, c.finding_text, c.recommendation_text "
    "FROM decision_memory_embedding_intent i "
    "JOIN decision_memory_case k ON k.case_id = i.case_id "
    "JOIN decision_memory_content c ON c.case_id = i.case_id AND c.revision = i.revision "
    "WHERE i.state = 'pending' AND i.view_kind = :view AND i.embedding_profile = :profile "
    "ORDER BY i.created_at, i.intent_id LIMIT :limit"
)
_COUNTS = text(
    "SELECT count(*) FILTER (WHERE state = 'pending') AS pending, count(*) FILTER (WHERE state = 'poisoned') AS poisoned "
    "FROM decision_memory_embedding_intent WHERE embedding_profile = :profile"
)
_POISON = text(
    "UPDATE decision_memory_embedding_intent SET state = 'poisoned', poison_reason = :reason, state_changed_at = clock_timestamp() "
    "WHERE intent_id = ANY(:ids) AND state = 'pending'"
)
_POISON_BY_DIGEST = text(
    "UPDATE decision_memory_embedding_intent SET state = 'poisoned', poison_reason = :reason, state_changed_at = clock_timestamp() "
    "WHERE embedding_profile = :profile AND input_sha256 = :digest AND state = 'pending'"
)
_BUMP = text(
    "UPDATE decision_memory_embedding_intent SET attempts = attempts + 1, "
    "state = CASE WHEN attempts + 1 >= :limit THEN 'poisoned' ELSE state END, "
    "poison_reason = CASE WHEN attempts + 1 >= :limit THEN :reason ELSE poison_reason END, state_changed_at = clock_timestamp() "
    "WHERE embedding_profile = :profile AND input_sha256 = :digest AND state = 'pending'"
)
_INTENTS_OF_DIGEST = text(
    "SELECT intent_id, case_id, revision, view_kind FROM decision_memory_embedding_intent "
    "WHERE embedding_profile = :profile AND input_sha256 = :digest AND state = 'pending' ORDER BY intent_id FOR UPDATE"
)
_INSERT_EMBEDDING = text(
    "INSERT INTO decision_memory_embedding (case_id, revision, view_kind, embedding_profile, model_revision, input_sha256, "
    "embedding_sha256, embedding) VALUES (:case_id, :revision, :view, :profile, :model, :digest, :vector_digest, CAST(:vector AS vector)) "
    "ON CONFLICT ON CONSTRAINT pk_decision_memory_embedding DO NOTHING"
)
_DONE = text(
    "UPDATE decision_memory_embedding_intent SET state = 'done', state_changed_at = clock_timestamp() WHERE intent_id = :intent_id"
)
#: Work that holds the memory the encoder needs: a run's Job that is leased or running, and a comparison attempt that is. A Job in
#: ``retry_wait`` or ``queued`` holds none (and while the window is open it is not issued either).
_RUNNING_WORK = text(
    "SELECT (SELECT count(*) FROM job WHERE state IN ('leased', 'running')) "
    "+ (SELECT count(*) FROM comparison_work_attempt WHERE state IN ('created', 'leased', 'running'))"
)


@dataclass(frozen=True, slots=True)
class ControlRow:
    paused: bool
    paused_since: datetime | None
    window_state: str
    window_reason: str | None
    window_changed_at: datetime


def _control(row: Any) -> ControlRow:
    return ControlRow(bool(row[0]), row[1], str(row[2]), None if row[3] is None else str(row[3]), row[4])


def read_control(session: Session) -> ControlRow:
    row = session.execute(_CONTROL).first()
    if row is None:
        raise LookupError("vector_control has no row: the migration seeds it")
    return _control(row)


def lock_control(session: Session) -> ControlRow:
    """The control row, locked for the rest of the transaction: one writer of the state and of the journal's numbers at a time."""
    row = session.execute(_LOCK_CONTROL).first()
    if row is None:
        raise LookupError("vector_control has no row: the migration seeds it")
    return _control(row)


def _append_event(session: Session, *, kind: str, reason: str | None, actor: str | None) -> None:
    number = int(session.execute(_NEXT_EVENT).scalar_one())
    session.execute(_INSERT_EVENT, {
        "event_id": str(VectorControlEventId.new()), "event_no": number, "kind": kind, "reason": reason, "actor": actor,
    })


_WINDOW_EVENT: Final[dict[str, str]] = {
    "closed": "window_closed", "draining": "window_draining", "encoding": "window_encoding", "skipped": "window_skipped",
}


def set_window_state(session: Session, *, state: str, reason: str | None = None, at: datetime | None = None) -> None:
    """Move the window to ``state`` and journal it. The caller holds the control row (:func:`lock_control`). A reason belongs to ``skipped``
    and only to it (the database pairs them).

    ``at`` is the moment the pass looked at (the worker's clock): ``window_changed_at`` is compared with the window's own span, which is the
    worker's clock too, so the two agree whatever the database's clock says (a pass run against a made-up moment in a test, a clock that is
    seconds apart on another host). Without it the database's time is used."""
    if (state == "skipped") != (reason is not None):
        raise ValueError("a skipped window has a reason and no other state has one")
    session.execute(_SET_WINDOW, {"state": state, "reason": reason, "at": at})
    _append_event(session, kind=_WINDOW_EVENT[state], reason=reason, actor=None)


def set_paused(session: Session, *, paused: bool, actor: str) -> None:
    """Pause the vectors or resume them, journalled with the administrator. The caller holds the control row."""
    session.execute(_SET_PAUSED, {"paused": paused})
    _append_event(session, kind="paused" if paused else "resumed", reason=None, actor=actor)


def read_window_setting(session: Session) -> WindowSetting:
    """The window in force: the latest revision of ``vector_window``, or the default while nothing is journalled."""
    row = session.execute(_WINDOW_SETTING, {"name": SETTING_NAME}).first()
    if row is None:
        return DEFAULT_WINDOW
    value = row[0]
    return parse_setting(json.loads(value) if isinstance(value, str) else value)


def running_work(session: Session) -> int:
    """How many Jobs and comparison attempts are running now."""
    return int(session.execute(_RUNNING_WORK).scalar_one())


def count_intents(session: Session) -> tuple[int, int]:
    """``(pending, poisoned)`` intents of the profile: what the administrator reads in the pause menu."""
    row = session.execute(_COUNTS, {"profile": EMBEDDING_PROFILE}).one()
    return int(row[0]), int(row[1])


def add_intents_for_new_cases(session: Session, *, batch: int = BACKFILL_BATCH) -> int:
    """Queue ``finding_v1`` for the cases that have none (the backfill, and every case captured since): idempotent, at most ``batch`` a call.

    A case whose view cannot be built (a finding text that is only whitespace) is not queued; the check of the memory's content (1..4000
    characters) makes that a defect of the data, and a row left out is visible as a case with neither an intent nor a vector."""
    rows = session.execute(_CASES_WITHOUT_INTENT, {"view": VIEW_FINDING, "profile": EMBEDDING_PROFILE, "batch": batch}).all()
    added = 0
    for case_id, revision, category, finding_text, recommendation_text in rows:
        try:
            view = build_finding_view(
                category=str(category), finding_text=str(finding_text), recommendation_text=str(recommendation_text))
        except ValueError:
            continue
        result = session.execute(_INSERT_INTENT, {
            "intent_id": str(DecisionMemoryEmbeddingIntentId.new()), "case_id": case_id, "revision": revision,
            "view": VIEW_FINDING, "profile": EMBEDDING_PROFILE, "digest": input_sha256(view),
        })
        added += int(result.rowcount or 0)
    return added


@dataclass(frozen=True, slots=True)
class IntentText:
    """A pending intent with the text its view builds now. ``matches`` is false when that text is not the one the intent was queued for."""

    intent_id: str
    case_id: str
    revision: int
    input_sha256: str
    text: str

    @property
    def matches(self) -> bool:
        return input_sha256(self.text) == self.input_sha256


def pending_intent_texts(session: Session, *, limit: int = EXPORT_LIMIT) -> list[IntentText]:
    """The oldest pending intents of ``finding_v1`` with the text of each, rebuilt from the memory's content (a vector is a projection: it is
    always made again from ``decision_memory_content``, never from a copy of the text kept elsewhere)."""
    rows = session.execute(_PENDING, {"view": VIEW_FINDING, "profile": EMBEDDING_PROFILE, "limit": limit}).all()
    found: list[IntentText] = []
    for intent_id, case_id, revision, digest, category, finding_text, recommendation_text in rows:
        view = build_finding_view(
            category=str(category), finding_text=str(finding_text), recommendation_text=str(recommendation_text))
        found.append(IntentText(str(intent_id), str(case_id), int(revision), str(digest), view))
    return found


def mark_poisoned(session: Session, *, intent_ids: Iterable[str], reason: str) -> int:
    """``poisoned`` with a reason: visible to the administrator, never retried. Only a pending intent moves."""
    ids = list(intent_ids)
    if not ids:
        return 0
    return int(session.execute(_POISON, {"ids": ids, "reason": reason}).rowcount or 0)


def bump_attempts(session: Session, *, digest: str, reason: str = POISON_ATTEMPTS) -> None:
    """A failed attempt for every pending intent of a digest; the fifth poisons it (the CHECK of the column ends at 5)."""
    session.execute(_BUMP, {"profile": EMBEDDING_PROFILE, "digest": digest, "limit": MAX_ATTEMPTS, "reason": reason})


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    """What an import did, in intents: stored (``done``), poisoned for their length, retried, and left pending for want of an answer."""

    done: int = 0
    poisoned: int = 0
    retried: int = 0
    missing: int = 0
    skipped_forgotten: int = 0


def import_vectors(
    session: Session, *, vectors: Sequence[EncodedVector], over_limit: Iterable[str], rejected: Iterable[str], missing: Iterable[str],
) -> ImportOutcome:
    """Store the vectors for every pending intent of each digest, in the caller's transaction.

    Each vector is written to every pending intent whose ``input_sha256`` is its digest (the intents the export saw, and any queued since for
    the same text: the same input has the same vector). A row is written under a savepoint: a vector the database refuses (the unit-norm CHECK
    is the database's own, and a case forgotten between the export and now is refused by the forget guard) counts against that intent and
    never voids the others."""
    done = poisoned = retried = missing_count = forgotten = 0
    for vector in vectors:
        targets = session.execute(_INTENTS_OF_DIGEST, {"profile": EMBEDDING_PROFILE, "digest": vector.input_sha256}).all()
        literal = pgvector_literal(vector.values)
        for intent_id, case_id, revision, view_kind in targets:
            try:
                with session.begin_nested():
                    session.execute(_INSERT_EMBEDDING, {
                        "case_id": case_id, "revision": revision, "view": view_kind, "profile": EMBEDDING_PROFILE,
                        "model": MODEL_REVISION, "digest": vector.input_sha256, "vector_digest": vector.embedding_sha256, "vector": literal,
                    })
                    session.execute(_DONE, {"intent_id": intent_id})
                done += 1
            except Exception as exc:  # noqa: BLE001 - a row the database refuses is counted, whatever its class
                if "forgotten" in str(exc):
                    forgotten += 1
                    continue
                retried += 1
                bump_attempts(session, digest=vector.input_sha256)
    for digest in over_limit:
        poisoned += int(session.execute(_POISON_BY_DIGEST, {
            "profile": EMBEDDING_PROFILE, "digest": digest, "reason": POISON_TOKEN_LIMIT,
        }).rowcount or 0)
    for digest in rejected:
        retried += 1
        bump_attempts(session, digest=digest)
    for digest in missing:
        missing_count += 1
        bump_attempts(session, digest=digest)
    return ImportOutcome(done, poisoned, retried, missing_count, forgotten)
