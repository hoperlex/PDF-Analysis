"""The decision journal: the append-only ledger read **across** findings.

``ledger.py`` owns the write path and the history of **one** finding. ``projection.py``
owns the per-finding current verdict, which PostgreSQL computes in the
``finding_current_verdict`` view. This module owns the third question, and it is a
different question from both: *what has this deployment decided?*

**Why a third module rather than a function in ``projection.py``.** That module is about
one projection -- the verdict of one finding -- and every function in it takes a
``finding_uid``. A cross-finding listing that joined four relations would make its
docstring false in its first sentence, and the module whose whole argument is *"there is
one answer to this question and PostgreSQL computes it"* is the wrong place to put a
second, differently-shaped read. Adding it to ``ledger.py`` would be worse: that module
is the one place a decision is written, and the reason it can promise "nothing is ever
updated and nothing is ever removed" is that it is small enough to read.

**It is a projection, in the sense ``ADR-0012`` fixes.** Every column below is read from
``expert_decision_event``, ``finding``, ``finding_observation`` and the
``finding_current_verdict`` view. Nothing is stored in this shape, nothing is cached, and
dropping every row this module could return loses nothing that cannot be recomputed from
the event stream. The knowledge base is a *view* of this journal and not an aggregate of
its own: if it were, it would be a second place a verdict lives, and the first thing a
second place does is disagree.

**A finding is identified by ``finding_uid`` and by nothing else.** ``ADR-0010``: no
display number, no path, no row sequence. ``sequence_no`` orders the rows inside the
database and is never selected here, because the client-visible order is
``(recorded_at, decision_id)`` and ``P02_SEAMS.md`` section 5.3 says the server's
sequence is never exposed, in a field or inside a cursor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

__all__ = ["JournalEntry", "decision_journal"]

#: Newest first, and the order is part of what this module returns rather than a detail of
#: it: the edge pages what it is given and never re-sorts, so an order changed here would
#: page correctly through a different listing.
#:
#: ``COLLATE "C"`` on the identifier, as ``findings/queries.py`` does, because the database's
#: default collation is locale-dependent and a listing whose tie-break moves with the
#: server's locale is not a total order.
#:
#: The filters bind as ``:name IS NULL OR column = :name`` rather than being concatenated
#: into the statement. The cast is not decoration: without it PostgreSQL cannot infer the
#: parameter's type on the ``IS NULL`` branch and refuses the whole statement.
_JOURNAL = text(
    """
    SELECT
        e.decision_id,
        e.finding_uid,
        e.finding_observation_id,
        e.event_type,
        e.verdict,
        e.comment,
        e.author_label,
        e.recorded_at,
        f.project_uid,
        f.allocated_by_run_id,
        o.category,
        o.finding_text,
        v.current_verdict,
        v.decision_event_count
    FROM expert_decision_event e
    JOIN finding f ON f.finding_uid = e.finding_uid
    JOIN finding_observation o ON o.finding_observation_id = e.finding_observation_id
    JOIN finding_current_verdict v ON v.finding_uid = e.finding_uid
    WHERE (CAST(:category AS text) IS NULL OR o.category = CAST(:category AS text))
      AND (CAST(:verdict AS text) IS NULL OR v.current_verdict = CAST(:verdict AS text))
    ORDER BY e.recorded_at DESC, e.decision_id COLLATE "C" DESC
    """
)


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """One event of the journal, with the finding context it was recorded against.

    The frozen ``DecisionRecord``, and deliberately the whole of it: a listing item that
    were a subset of a shape the contract declares would be a second shape of the same
    resource, and ``ports.py`` already records what the first one cost.
    """

    decision_id: str
    finding_uid: str
    finding_observation_id: str
    event_type: str
    verdict: str | None
    comment: str | None
    author_label: str
    recorded_at: datetime
    project_uid: str
    run_id: str
    category: str
    finding_text: str
    current_verdict: str
    decision_event_count: int


def decision_journal(
    session: Session,
    *,
    category: str | None = None,
    verdict: str | None = None,
) -> tuple[JournalEntry, ...]:
    """Every recorded decision, newest first, optionally narrowed.

    ``category`` is the **finding's** category and ``verdict`` is the verdict that now
    stands for the finding -- the same two things the identically named parameters mean on
    ``listRunFindings``, and neither of them filters on the event. A caller that wanted
    "every event that carried a rejection" would be asking a third question, and this
    signature does not pretend to answer it.

    Both are filtered **in the query**, against the same columns this function reports. A
    filter applied to one column and reported from another is the shape `W12` recorded: a
    query that shares an assumption with its subject cannot see the subject being wrong.

    Neither argument is re-validated here. The edge has already checked both against the
    frozen enums, and a second, hand-written copy of an enum is the hand-maintained subset
    `W30-LISTS` spent a wave removing. A value that is not in the vocabulary matches no row
    and yields an empty page, which is the truthful answer to a question about a category
    nothing was ever filed under.

    An ungrounded observation cannot appear: it carries no ``finding_uid``, so the join to
    ``finding`` drops it, and there is no ``WHERE grounded`` anywhere to forget.
    """
    rows = session.execute(_JOURNAL, {"category": category, "verdict": verdict}).mappings()
    return tuple(
        JournalEntry(
            decision_id=row["decision_id"],
            finding_uid=row["finding_uid"],
            finding_observation_id=row["finding_observation_id"],
            event_type=row["event_type"],
            verdict=row["verdict"],
            comment=row["comment"],
            author_label=row["author_label"],
            recorded_at=row["recorded_at"],
            project_uid=row["project_uid"],
            run_id=row["allocated_by_run_id"],
            category=row["category"],
            finding_text=row["finding_text"],
            current_verdict=row["current_verdict"],
            decision_event_count=row["decision_event_count"],
        )
        for row in rows
    )
