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

from auditmanager.decisions.carryover import CarriedOrigin

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
#:
#: **Where a decision belongs** (`UI-PARITY-P0A`). The knowledge-base table shows, beside each
#: decision, the project, the document and the version it was taken in. ``document_uid`` and
#: ``version_uid`` are read through the finding (``finding.version_uid`` ->
#: ``document_version.document_uid``), ``project_name`` and ``document_name`` (the document's
#: ``display_title``) are **joined at read time and stored nowhere** -- a renamed project is renamed
#: in the next listing, and the ledger never holds a second copy of a label. All three joins are
#: inner and cannot drop a row: ``finding.project_uid`` and ``finding.version_uid`` are NOT NULL
#: foreign keys, and so are ``document_version.document_uid`` and ``document.project_uid``.
#:
#: **The version's section** is ``version_classification_current.section_code``: the latest revision
#: of the expert's confirmed classification of *that version* (`CLASSIFICATION-CORRECTION-01`) -- the
#: same view the dashboard's section breakdown counts through. ``LEFT JOIN``, so a version nobody has
#: classified has no row and ``section`` is NULL; the legacy ``document.section`` is not read at all,
#: for the reason the dashboard states.
#:
#: ``total`` on the wire is the length of what this returns, counted at the edge before it pages: the
#: listing already pages in Python over this whole result, so the count cannot be a second definition
#: of "matching" that drifts from the rows.
_JOURNAL = text(
    """
    SELECT
        e.decision_id,
        e.finding_uid,
        e.finding_observation_id,
        e.event_type,
        e.verdict,
        e.severity,
        e.comment,
        e.author_label,
        e.author_user_uid,
        e.recorded_at,
        f.project_uid,
        f.allocated_by_run_id,
        f.version_uid,
        dv.document_uid,
        p.name AS project_name,
        d.display_title AS document_name,
        c.section_code,
        o.category,
        o.finding_text,
        v.current_verdict,
        v.decision_event_count,
        cs.decision_id AS carried_decision_id,
        cs.finding_uid AS carried_finding_uid,
        cf.version_uid AS carried_version_uid,
        cv.version_ordinal AS carried_version_ordinal
    FROM expert_decision_event e
    JOIN finding f ON f.finding_uid = e.finding_uid
    JOIN finding_observation o ON o.finding_observation_id = e.finding_observation_id
    JOIN finding_current_verdict v ON v.finding_uid = e.finding_uid
    JOIN project p ON p.project_uid = f.project_uid
    JOIN document_version dv ON dv.version_uid = f.version_uid
    JOIN document d ON d.document_uid = dv.document_uid
    LEFT JOIN version_classification_current c ON c.version_uid = f.version_uid
    LEFT JOIN expert_decision_event cs ON cs.decision_id = e.carried_from_decision_id
    LEFT JOIN finding cf ON cf.finding_uid = cs.finding_uid
    LEFT JOIN document_version cv ON cv.version_uid = cf.version_uid
    WHERE (CAST(:category AS text) IS NULL OR o.category = CAST(:category AS text))
      AND (CAST(:verdict AS text) IS NULL OR v.current_verdict = CAST(:verdict AS text))
      AND (CAST(:project_uid AS text) IS NULL OR f.project_uid = CAST(:project_uid AS text))
    ORDER BY e.recorded_at DESC, e.decision_id COLLATE "C" DESC
    """
)


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """One event of the journal, with the finding context it was recorded against.

    The frozen ``DecisionRecord``, and deliberately the whole of it: a listing item that
    were a subset of a shape the contract declares would be a second shape of the same
    resource, and ``ports.py`` already records what the first one cost.

    One field more than the wire, and only one: ``author_user_uid``, the account that took
    the decision (`W49-PLAN.md` §3.1). The contract does not carry it -- "no wire change" --
    and the composition root maps the record field by field, so it never leaks onto the
    wire by being here. ``None`` means "author account unknown": every event written before
    migration ``0015``, listed like any other row and never treated as a fault.
    """

    decision_id: str
    finding_uid: str
    finding_observation_id: str
    event_type: str
    verdict: str | None
    comment: str | None
    author_label: str
    author_user_uid: str | None
    recorded_at: datetime
    project_uid: str
    run_id: str
    #: `UI-PARITY-P0A`. Where the decision belongs: the finding's version, its document, and the
    #: display names of the project and the document, joined at read time.
    version_uid: str
    document_uid: str
    project_name: str
    document_name: str
    category: str
    finding_text: str
    current_verdict: str
    decision_event_count: int
    severity: str | None = None
    #: The version's confirmed section code, or ``None`` for a version no expert has classified.
    section: str | None = None
    #: `UI-A-73` (migration ``0058``): where a carried event came from, or ``None`` for an event made directly (and for
    #: every event written before the migration).
    carried_from: CarriedOrigin | None = None


def decision_journal(
    session: Session,
    *,
    category: str | None = None,
    verdict: str | None = None,
    project_uid: str | None = None,
) -> tuple[JournalEntry, ...]:
    """Every recorded decision, newest first, optionally narrowed.

    ``category`` is the **finding's** category and ``verdict`` is the verdict that now
    stands for the finding -- the same two things the identically named parameters mean on
    ``listRunFindings``, and neither of them filters on the event. A caller that wanted
    "every event that carried a rejection" would be asking a third question, and this
    signature does not pretend to answer it.

    ``project_uid`` (`UI-PARITY-P0A`) narrows by the **finding's** project, the column the record
    reports as ``project_uid``. It is a filter and not a parent, so a project that does not exist
    matches nothing and is an empty tuple, not a refusal.

    All three are filtered **in the query**, against the same columns this function reports. A
    filter applied to one column and reported from another is the shape `W12` recorded: a
    query that shares an assumption with its subject cannot see the subject being wrong.

    Neither argument is re-validated here. The edge has already checked both against the
    frozen enums, and a second, hand-written copy of an enum is the hand-maintained subset
    `W30-LISTS` spent a wave removing. A value that is not in the vocabulary matches no row
    and yields an empty page, which is the truthful answer to a question about a category
    nothing was ever filed under.

    An ungrounded observation cannot appear: it carries no ``finding_uid``, so the join to
    ``finding`` drops it, and there is no ``WHERE grounded`` anywhere to forget.

    No join reaches ``app_user``. ``author_user_uid`` is read straight off the event, so an
    event whose account is unknown (NULL) is listed exactly as one whose account is known;
    an inner join there would silently drop the whole of history.
    """
    rows = session.execute(
        _JOURNAL, {"category": category, "verdict": verdict, "project_uid": project_uid}
    ).mappings()
    return tuple(
        JournalEntry(
            decision_id=row["decision_id"],
            finding_uid=row["finding_uid"],
            finding_observation_id=row["finding_observation_id"],
            event_type=row["event_type"],
            verdict=row["verdict"],
            severity=row["severity"],
            comment=row["comment"],
            author_label=row["author_label"],
            author_user_uid=row["author_user_uid"],
            recorded_at=row["recorded_at"],
            project_uid=row["project_uid"],
            run_id=row["allocated_by_run_id"],
            version_uid=row["version_uid"],
            document_uid=row["document_uid"],
            project_name=row["project_name"],
            document_name=row["document_name"],
            section=row["section_code"],
            category=row["category"],
            finding_text=row["finding_text"],
            current_verdict=row["current_verdict"],
            decision_event_count=row["decision_event_count"],
            carried_from=(
                None if row["carried_decision_id"] is None else CarriedOrigin(
                    decision_id=row["carried_decision_id"], finding_uid=row["carried_finding_uid"],
                    version_uid=row["carried_version_uid"], version_ordinal=int(row["carried_version_ordinal"]),
                )
            ),
        )
        for row in rows
    )
