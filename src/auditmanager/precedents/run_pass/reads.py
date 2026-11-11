"""What the pass reads: the run's findings, the place of its version, the vectors of its findings and the cases they are near (`ADR-0029`, plan-v5 2.1, 2.2).

Read-only SQL over the caller's session; nothing here writes. Three things to know:

* **The findings of a run** are read with SQL of this module (`findings.public` does not export the list of a run's published findings, and the pass
  may not import the findings package's internals): a finding's text is its canonical observation's, exactly as ``findings.queries.group_published_findings``
  chooses it (the canonical member named on ``finding``, or the only observation of a legacy finding), and an ungrounded observation has no
  ``finding_uid`` so the join drops it.
* **The corpus scan is exact and in the database.** The cosine of a finding's probe against every case of the section is computed by pgvector's
  ``<=>`` (no index: `ADR-0029` decision 8), over the cases that are **active at this moment** (``decision_memory_case_current``: a withdraw or a
  forget acts at once, not overnight), of the finding's section and data class, using each case's latest content revision's vector. A case with no
  vector is not in the scan; a finding with no vector is not scanned at all (its answer is «Недоступно», there is no other way to look for a case).
* **A case's decisions and comments come from the memory** (``decision_memory.public.MemoryReader.comments_for_cases``; the decisions with the mark
  that was in force when each was taken are read here, because the memory's reader does not expose those two columns yet).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.precedents.models import CaseComment, DecisionEvent, PrecedentCase
from auditmanager.precedents.vectors.intents import EMBEDDING_PROFILE, VIEW_FINDING

__all__ = [
    "CaseText", "PassFinding", "ProbeRow", "RunFacts", "VersionPlace", "case_texts", "data_class", "finding_head", "findings_of_run",
    "load_cases", "memory_changed_since", "neighbours", "probe_rows", "refreshable_runs", "run_facts", "runs_to_schedule", "unfinished_runs",
    "version_place",
]

#: A run the pass takes is one that finished with findings to show.
_TERMINAL_STATES: Final[tuple[str, ...]] = ("published", "partial")
#: The settings whose change moves a label that is already computed (the switch changes only what is shown, not what is counted, but the tuned
#: threshold travels with the switch).
_LABEL_SETTINGS: Final[tuple[str, ...]] = ("stop_words", "thresholds", "section_labels")

_RUN = text("SELECT run_id, project_uid, version_uid, state, terminal_at FROM audit_run WHERE run_id = :run_id")
_FINDINGS = text(
    """
    SELECT o.finding_uid, o.finding_observation_id, f.canonical_observation_id, o.category, o.finding_text, o.recommendation_text,
           o.extended_observation_ref
      FROM finding_observation o
      JOIN finding f ON f.finding_uid = o.finding_uid
     WHERE o.run_id = :run_id
     ORDER BY f.finding_uid COLLATE "C", o.finding_observation_id COLLATE "C"
    """
)
_FINDING_HEAD = text("SELECT allocated_by_run_id, version_uid FROM finding WHERE finding_uid = :finding_uid")
_PROBES = text(
    "SELECT input_id, state, input_sha256, text_sha256, poison_reason FROM decision_memory_probe "
    "WHERE run_id = :run_id AND view_kind = :view AND embedding_profile = :profile"
)
_SCAN = text(
    """
    SELECT p.input_id AS finding_uid, e.case_id AS case_id, 1 - (e.embedding <=> p.embedding) AS cosine
      FROM decision_memory_probe p
      JOIN decision_memory_embedding e ON e.embedding_profile = p.embedding_profile AND e.view_kind = p.view_kind
      JOIN decision_memory_case_current c ON c.case_id = e.case_id
      JOIN (SELECT case_id, max(revision) AS revision FROM decision_memory_content GROUP BY case_id) latest
        ON latest.case_id = e.case_id AND latest.revision = e.revision
     WHERE p.run_id = :run_id AND p.state = 'done' AND p.view_kind = :view AND p.embedding_profile = :profile
       AND c.section_code = :section AND c.data_class = :data_class AND c.status = 'active'
       AND (CAST(:only AS text[]) IS NULL OR p.input_id = ANY(CAST(:only AS text[])))
       AND 1 - (e.embedding <=> p.embedding) >= :floor
    """
)
_CASES = text(
    "SELECT case_id, origin_project_uid, origin_document_uid, origin_version_uid, origin_run_id, category, section_code, data_class "
    "FROM decision_memory_case WHERE case_id = ANY(CAST(:ids AS text[]))"
)
_DECISIONS = text(
    "SELECT case_id, verdict, decided_at, origin_kind, precedent_label_at_decision, precedent_history_verdict_shown "
    "FROM decision_memory_decision WHERE case_id = ANY(CAST(:ids AS text[])) ORDER BY decided_at, memory_decision_id"
)
_CASE_TEXTS = text(
    "SELECT k.case_id, k.category, c.finding_text FROM decision_memory_case k "
    "JOIN decision_memory_content c ON c.case_id = k.case_id "
    "WHERE k.case_id = ANY(CAST(:ids AS text[])) "
    "AND c.revision = (SELECT max(revision) FROM decision_memory_content WHERE case_id = k.case_id)"
)
_CHANGED = text(
    "SELECT EXISTS (SELECT 1 FROM decision_memory_status_event WHERE created_at > :moment) "
    "OR EXISTS (SELECT 1 FROM precedent_setting_event WHERE setting_name = ANY(CAST(:names AS text[])) AND created_at > :moment)"
)
_TO_SCHEDULE = text(
    """
    SELECT r.run_id FROM audit_run r
     WHERE r.state = ANY(CAST(:states AS text[])) AND r.terminal_at >= :since
       AND NOT EXISTS (SELECT 1 FROM decision_memory_precedent_run p WHERE p.run_id = r.run_id)
       AND EXISTS (SELECT 1 FROM finding_observation o WHERE o.run_id = r.run_id AND o.finding_uid IS NOT NULL)
     ORDER BY r.terminal_at, r.run_id LIMIT :limit
    """
)
_UNFINISHED = text(
    "SELECT run_id FROM decision_memory_precedent_run WHERE state IN ('pending', 'running') ORDER BY state_changed_at, run_id LIMIT :limit"
)
_REFRESHABLE = text(
    """
    SELECT p.run_id FROM decision_memory_precedent_run p JOIN audit_run r ON r.run_id = p.run_id
     WHERE p.state IN ('done', 'failed') AND r.terminal_at >= :since ORDER BY p.state_changed_at, p.run_id LIMIT :limit
    """
)


@dataclass(frozen=True, slots=True)
class RunFacts:
    run_id: str
    project_uid: str
    version_uid: str
    state: str
    terminal_at: datetime | None

    @property
    def finished(self) -> bool:
        return self.state in _TERMINAL_STATES


@dataclass(frozen=True, slots=True)
class PassFinding:
    """A published finding of a run as the pass needs it: its canonical observation's words and the candidates its observations name."""

    finding_uid: str
    finding_observation_id: str
    category: str
    finding_text: str
    recommendation_text: str
    extended_observation_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VersionPlace:
    """Where a run's findings are: the version's document and its confirmed section (``None`` when the version has none)."""

    document_uid: str
    section: str | None


@dataclass(frozen=True, slots=True)
class ProbeRow:
    state: str
    input_sha256: str
    text_sha256: str
    poison_reason: str | None


@dataclass(frozen=True, slots=True)
class CaseText:
    category: str
    finding_text: str


def run_facts(session: Session, run_id: str) -> RunFacts | None:
    row = session.execute(_RUN, {"run_id": run_id}).first()
    return None if row is None else RunFacts(str(row[0]), str(row[1]), str(row[2]), str(row[3]), row[4])


def findings_of_run(session: Session, run_id: str) -> tuple[PassFinding, ...]:
    """The published findings of ``run_id``, in the order of their identities. A finding whose canonical observation cannot be told (two observations
    and none named canonical, or the named one missing) is **left out** rather than guessed at: the read layer of the findings refuses such a group,
    and a label for a finding no list shows would be a label for nothing."""
    by_uid: dict[str, list[Any]] = {}
    for row in session.execute(_FINDINGS, {"run_id": run_id}).all():
        by_uid.setdefault(str(row[0]), []).append(row)
    found: list[PassFinding] = []
    for uid, rows in by_uid.items():
        named = rows[0][2]
        if named is None and len(rows) == 1:
            canonical = rows[0]
        else:
            matching = [row for row in rows if row[1] == named]
            if len(matching) != 1:
                continue
            canonical = matching[0]
        refs = tuple(dict.fromkeys(str(row[6]) for row in rows if row[6]))
        found.append(PassFinding(uid, str(canonical[1]), str(canonical[3]), str(canonical[4]), str(canonical[5]), refs))
    return tuple(found)


def finding_head(session: Session, finding_uid: str) -> tuple[str, str] | None:
    """``(run_id, version_uid)`` of the run that allocated the finding (the run the card speaks for), or ``None`` for an unknown finding."""
    row = session.execute(_FINDING_HEAD, {"finding_uid": finding_uid}).first()
    return None if row is None else (str(row[0]), str(row[1]))


def version_place(session: Session, version_uid: str) -> VersionPlace:
    """The document and the confirmed section of a version, through the documents' public surface."""
    from auditmanager.documents.public import DocumentRepository
    from auditmanager.shared.identity import VersionUid

    record = DocumentRepository().get_version(session, VersionUid.parse(version_uid))
    classification = record.classification
    code = None if classification is None else getattr(classification, "section_code", None)
    return VersionPlace(document_uid=str(record.document_uid), section=None if code is None else str(getattr(code, "value", code)))


def data_class(session: Session) -> str:
    """The installation's data class (``test`` until the owner's tool says ``real``): the class a finding's cases must share."""
    from auditmanager.decision_memory.public import MemoryReader

    return str(MemoryReader().settings(session).data_class)


def probe_rows(session: Session, run_id: str) -> dict[str, ProbeRow]:
    """The probes of a run by finding. One probe per finding (a finding's text does not change, so its ``text_sha256`` is one)."""
    rows = session.execute(_PROBES, {"run_id": run_id, "view": VIEW_FINDING, "profile": EMBEDDING_PROFILE}).all()
    return {str(r[0]): ProbeRow(str(r[1]), str(r[2]), str(r[3]), None if r[4] is None else str(r[4])) for r in rows}


def neighbours(
    session: Session, *, run_id: str, section: str, data_class_: str, floor: float, only: Sequence[str] | None = None,
) -> dict[str, list[tuple[str, float]]]:
    """``{finding_uid: [(case_id, cosine), ...]}`` for the findings of the run that have a vector: every active case of ``section`` and ``data_class_``
    with a cosine at or above ``floor``. A finding with a vector and no neighbour is a key with an empty list (it was scanned)."""
    found: dict[str, list[tuple[str, float]]] = {
        uid: [] for uid, probe in probe_rows(session, run_id).items() if probe.state == "done" and (only is None or uid in only)
    }
    rows = session.execute(_SCAN, {
        "run_id": run_id, "view": VIEW_FINDING, "profile": EMBEDDING_PROFILE, "section": section, "data_class": data_class_,
        "floor": floor, "only": None if only is None else list(only),
    }).all()
    for uid, case_id, cosine in rows:
        found.setdefault(str(uid), []).append((str(case_id), max(-1.0, min(1.0, float(cosine)))))
    return found


def load_cases(session: Session, case_ids: Iterable[str]) -> dict[str, PrecedentCase]:
    """The cases of ``case_ids`` as the core's values: identity, section, class, every decision with the mark in force when it was taken, and the comments.

    The cases are read as **active**: the scan that named them already took only the active ones, in the same transaction."""
    from auditmanager.decision_memory.public import MemoryReader

    ids = sorted(set(case_ids))
    if not ids:
        return {}
    heads = {str(r[0]): r for r in session.execute(_CASES, {"ids": ids}).all()}
    decisions: dict[str, list[DecisionEvent]] = {}
    for case_id, verdict, decided_at, origin, label, history in session.execute(_DECISIONS, {"ids": ids}).all():
        decisions.setdefault(str(case_id), []).append(DecisionEvent(
            verdict=str(verdict), decided_at=decided_at, origin_kind=str(origin),
            label_at_decision=None if label is None else str(label), history_verdict_shown=None if history is None else str(history)))
    comments = MemoryReader().comments_for_cases(session, ids)
    cases: dict[str, PrecedentCase] = {}
    for case_id, head in heads.items():
        cases[case_id] = PrecedentCase(
            case_id=case_id, section=None if head[6] is None else str(head[6]), data_class=str(head[7]), project_uid=str(head[1]),
            document_uid=str(head[2]), version_uid=str(head[3]), run_id=str(head[4]), active=True,
            decisions=tuple(decisions.get(case_id, ())),
            comments=tuple(CaseComment(text=str(item["comment"]), written_at=item["decided_at"]) for item in comments.get(case_id, ())))
    return cases


def case_texts(session: Session, case_ids: Iterable[str]) -> dict[str, CaseText]:
    """The category and the finding text of each case's latest content: what the card shows of a similar case (the words live in the memory only)."""
    ids = sorted(set(case_ids))
    if not ids:
        return {}
    return {str(r[0]): CaseText(str(r[1]), str(r[2])) for r in session.execute(_CASE_TEXTS, {"ids": ids}).all()}


def memory_changed_since(session: Session, moment: datetime) -> bool:
    """Has the memory's standing changed since ``moment``: a case withdrawn, restored or forgotten, or a setting the labels read journalled?

    Deliberately wider than it needs to be (any case, any section): the answer only decides whether a label computed at ``moment`` is read again or
    taken as it is, and reading again is always right. New decisions are not a change: they reach the labels with the next pass."""
    return bool(session.execute(_CHANGED, {"moment": moment, "names": list(_LABEL_SETTINGS)}).scalar_one())


def runs_to_schedule(session: Session, *, since: datetime, limit: int) -> list[str]:
    """Runs that finished since ``since`` with a published finding and have no pass row yet, oldest first."""
    return [str(r[0]) for r in session.execute(_TO_SCHEDULE, {"states": list(_TERMINAL_STATES), "since": since, "limit": limit}).all()]


def unfinished_runs(session: Session, *, limit: int) -> list[str]:
    """Runs whose pass waits for vectors (``pending``)."""
    return [str(r[0]) for r in session.execute(_UNFINISHED, {"limit": limit}).all()]


def refreshable_runs(session: Session, *, since: datetime, limit: int) -> list[str]:
    """Runs the pass has finished (or failed) that are fresh, to be computed again after new vectors arrived."""
    return [str(r[0]) for r in session.execute(_REFRESHABLE, {"since": since, "limit": limit}).all()]

