"""What the pass writes: the probes of a run, the state of its pass and the advice of each finding at a revision (migration ``0064``).

Every function takes the caller's session and ends no transaction. What the database guards itself is relied on and not repeated: the advice is
immutable (``am_immutable_row``), its key is ``(run, finding, revision)``, a ``cancel_suggested`` row must say the critic reviewed it, the state of a
pass and its failure code come as a pair, and a probe's vector, its state and its norm are paired and checked.

**A revision is a whole set.** A run's advice at revision ``r`` is every row the pass wrote at ``r``; a later pass that finds a different result writes
a complete new set at ``r + 1`` and the earlier sets stay (the table is append-only), so a decision that names ``precedent_revision`` names a set that
is still there to read. A pass that finds the same result writes nothing: the pass is idempotent.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.precedents.run_pass.reads import PassFinding
from auditmanager.precedents.vectors.intents import EMBEDDING_PROFILE, VIEW_FINDING, build_finding_view, input_sha256

__all__ = [
    "FAILURE_CRITIC_UNREADABLE", "FAILURE_PASS_ERROR", "RunRow", "StoredAdvice", "advice_at", "ensure_probes", "ensure_run_row", "latest_revision",
    "mark_failed", "run_row", "set_run_state", "text_sha256", "write_advice",
]

STATE_PENDING: Final[str] = "pending"
STATE_DONE: Final[str] = "done"
STATE_FAILED: Final[str] = "failed"
#: ``decision_memory_precedent_run.failure_code`` (``^[a-z][a-z0-9_]{0,63}$``): what the administrator reads of a pass that did not finish.
FAILURE_PASS_ERROR: Final[str] = "pass_error"
FAILURE_CRITIC_UNREADABLE: Final[str] = "critic_unreadable"

_INSERT_PROBE = text(
    "INSERT INTO decision_memory_probe (run_id, input_id, text_sha256, view_kind, embedding_profile, input_sha256, finding_observation_id) "
    "VALUES (:run_id, :input_id, :text_sha, :view, :profile, :input_sha, :observation) "
    "ON CONFLICT ON CONSTRAINT pk_decision_memory_probe DO NOTHING"
)
_ENSURE_RUN = text("INSERT INTO decision_memory_precedent_run (run_id) VALUES (:run_id) ON CONFLICT (run_id) DO NOTHING")
_RUN_ROW = text(
    "SELECT revision, state, failure_code, state_changed_at, created_at FROM decision_memory_precedent_run WHERE run_id = :run_id"
)
_LOCK_RUN = text(
    "SELECT revision, state, failure_code, state_changed_at, created_at FROM decision_memory_precedent_run WHERE run_id = :run_id FOR UPDATE"
)
_SET_RUN = text(
    "UPDATE decision_memory_precedent_run SET revision = :revision, state = :state, failure_code = :code, "
    "state_changed_at = clock_timestamp() WHERE run_id = :run_id"
)
_LATEST = text("SELECT max(revision) FROM decision_memory_precedent_advice WHERE run_id = :run_id")
_ADVICE = text(
    "SELECT finding_uid, revision, label, critic_reviewed, votes, hint_codes, computed_at FROM decision_memory_precedent_advice "
    "WHERE run_id = :run_id AND revision = :revision ORDER BY finding_uid COLLATE \"C\""
)
_INSERT_ADVICE = text(
    "INSERT INTO decision_memory_precedent_advice (run_id, finding_uid, revision, label, critic_reviewed, votes, hint_codes, computed_at) "
    "VALUES (:run_id, :finding_uid, :revision, :label, :reviewed, CAST(:votes AS jsonb), CAST(:hints AS text[]), :computed_at)"
)
_CLOCK = text("SELECT clock_timestamp()")


def text_sha256(finding_text: str) -> str:
    """The digest of a finding's own words: half of a probe's key (the other half is the finding), so a probe is never taken for another text's."""
    import hashlib

    return hashlib.sha256(finding_text.encode("utf-8")).hexdigest()


def database_now(session: Session) -> datetime:
    """The database's clock: the moment a pass starts reading, stamped on its advice, compared with the standing events' own timestamps."""
    return session.execute(_CLOCK).scalar_one()


@dataclass(frozen=True, slots=True)
class RunRow:
    revision: int
    state: str
    failure_code: str | None
    state_changed_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredAdvice:
    """One finding's row at one revision. ``votes`` is the jsonb as stored: the five counts of the contract and the critic's projection."""

    finding_uid: str
    revision: int
    label: str
    critic_reviewed: bool
    votes: Mapping[str, Any]
    hint_codes: tuple[str, ...]
    computed_at: datetime


def ensure_probes(session: Session, run_id: str, findings: Sequence[PassFinding]) -> int:
    """Queue ``finding_v1`` of every finding that has no probe yet: idempotent, and the only place a probe is made. Returns how many were added.

    A finding whose view cannot be built (its text is only whitespace) gets no probe: it has no vector, and its answer is «Недоступно»."""
    added = 0
    for finding in findings:
        try:
            view = build_finding_view(category=finding.category, finding_text=finding.finding_text, recommendation_text=finding.recommendation_text)
        except ValueError:
            continue
        result = session.execute(_INSERT_PROBE, {
            "run_id": run_id, "input_id": finding.finding_uid, "text_sha": text_sha256(finding.finding_text), "view": VIEW_FINDING,
            "profile": EMBEDDING_PROFILE, "input_sha": input_sha256(view), "observation": finding.finding_observation_id,
        })
        added += int(result.rowcount or 0)
    return added


def run_row(session: Session, run_id: str) -> RunRow | None:
    row = session.execute(_RUN_ROW, {"run_id": run_id}).first()
    return None if row is None else RunRow(int(row[0]), str(row[1]), None if row[2] is None else str(row[2]), row[3], row[4])


def ensure_run_row(session: Session, run_id: str) -> RunRow:
    """The pass row of the run, made if it is not there, and **locked** for the rest of the transaction: one pass computes a run at a time."""
    session.execute(_ENSURE_RUN, {"run_id": run_id})
    row = session.execute(_LOCK_RUN, {"run_id": run_id}).one()
    return RunRow(int(row[0]), str(row[1]), None if row[2] is None else str(row[2]), row[3], row[4])


def set_run_state(session: Session, run_id: str, *, state: str, revision: int, failure_code: str | None = None) -> None:
    if (state == STATE_FAILED) != (failure_code is not None):
        raise ValueError("a failed pass has a failure code and no other state has one")
    session.execute(_SET_RUN, {"run_id": run_id, "state": state, "revision": revision, "code": failure_code})


def mark_failed(session: Session, run_id: str, *, code: str) -> None:
    """The pass of the run did not finish: ``failed`` with the code, keeping the revision the run already has. Loud: the administrator reads it."""
    row = ensure_run_row(session, run_id)
    set_run_state(session, run_id, state=STATE_FAILED, revision=row.revision, failure_code=code)


def latest_revision(session: Session, run_id: str) -> int | None:
    value = session.execute(_LATEST, {"run_id": run_id}).scalar_one()
    return None if value is None else int(value)


def advice_at(session: Session, run_id: str, revision: int) -> dict[str, StoredAdvice]:
    """The whole set of a revision, by finding."""
    found: dict[str, StoredAdvice] = {}
    for uid, rev, label, reviewed, votes, hints, computed_at in session.execute(_ADVICE, {"run_id": run_id, "revision": revision}).all():
        found[str(uid)] = StoredAdvice(
            str(uid), int(rev), str(label), bool(reviewed), json.loads(votes) if isinstance(votes, str) else dict(votes), tuple(hints or ()),
            computed_at)
    return found


def write_advice(session: Session, run_id: str, revision: int, rows: Sequence[Mapping[str, Any]], *, computed_at: datetime) -> None:
    """Write one revision's whole set. Each row is ``{finding_uid, label, critic_reviewed, votes, hint_codes}``."""
    for row in rows:
        session.execute(_INSERT_ADVICE, {
            "run_id": run_id, "finding_uid": row["finding_uid"], "revision": revision, "label": row["label"],
            "reviewed": row["critic_reviewed"], "votes": json.dumps(row["votes"], ensure_ascii=False, sort_keys=True),
            "hints": list(row["hint_codes"]), "computed_at": computed_at,
        })
