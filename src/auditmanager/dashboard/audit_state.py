"""The audit state of a document and the counters read off it (`UI-PARITY-P0B`, `R-150n` ... `R-150u`).

**One read model, three outputs.** ``listProjects`` (``Project.audit_counts``), the section panel of
``getDashboardSummary`` (``SectionDocumentCount``) and the tile of findings that await a decision
(``DashboardSummary.awaiting_decision_findings``) are all tallies of the *same* statement,
``_AUDIT_GROUPS``, through the *same* function, :func:`audit_state`. They cannot come to define a document,
a result or an undecided finding differently, so the numbers on the screen agree by construction and not by
a test that happens to compare them. ``docs/program/UI-PARITY-METRICS.md`` is the dictionary of what each
figure means and which ruling decided it.

The rules, as the owner ruled them:

* **The counted object is a document's current version only** (`R-150p`). A document is one row of
  ``document`` whose ``current_version_uid`` points at a version -- the join ``listProjects`` counts
  ``document_count`` through -- and an older version never counts: uploading V2 moves a fully checked V1
  document to ``not_run`` until V2 is run.
* **The result run of a version** is the latest of its runs in state ``published`` or ``partial``, ordered by
  ``(created_at, run_id)`` -- the order ``listRuns`` returns them in. A newer run still in flight does not
  displace it; ``failed`` and ``cancelled`` runs are not results (`R-150r`); ``partial`` is a result (`R-150s`).
* **The document audit state** is one of four words: ``not_run`` (no result run), ``clean`` (a result run with
  no published finding -- a state of its own, neither "checked" nor "awaiting", `R-150n`),
  ``awaiting_decision`` (a result run with at least one finding whose current verdict is undecided) and
  ``checked`` (a result run, every finding decided). ``partial`` is a flag beside the state, set when the
  result run is ``partial``.
* **Optimisation is not part of it** (`R-150u`): the state is computed on findings only.
* **AR v3 six-run groups** use the general per-run rule for now (`R-150t`): each run of a group is a run of
  its version, and the latest published or partial one is the result. The rule for a group as a whole is
  decided when AR v3 is switched on (`Q-MD-9`, a debt) and is deliberately not guessed here.

A finding is *undecided* when its current verdict, read from ``finding_current_verdict`` (the projection
``decisions.projection`` and the verdict panel already read), is ``pending`` -- no verdict was ever recorded --
or ``needs_manual_review``, which the database cannot produce today but which an expert would still have to
act on. The *findings of a run* are the grounded observations the run published (``finding_observation`` joined
to ``finding``, one per ``finding_uid``): the set ``listRunFindings`` returns, the same join
``findings.queries`` counts ``published_finding_count`` through.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

__all__ = [
    "AUDIT_STATES",
    "AuditCountsRecord",
    "AuditGroupRecord",
    "DocumentAuditReadModel",
    "DocumentAuditState",
    "RESULT_RUN_STATES",
    "SectionAuditRecord",
    "UNDECIDED_VERDICTS",
    "audit_state",
    "awaiting_decision_findings",
    "counts_by_project",
    "counts_by_section",
    "tally",
]

#: The four states of a document, in the order they are listed. Restated rather than imported from the
#: transport contract, like ``repository.VERDICTS``: the domain layer does not import the wire.
AUDIT_STATES: Final[tuple[str, ...]] = ("not_run", "clean", "awaiting_decision", "checked")

#: The run states that make a run a *result* (`R-150r`, `R-150s`). Anything else -- ``created``, ``queued``,
#: ``running``, ``validating`` (in flight), ``failed``, ``cancelled`` -- is not. The SQL below names the same
#: two words; ``tests/unit/dashboard/test_audit_state.py`` asserts the statement mentions exactly these.
RESULT_RUN_STATES: Final[tuple[str, ...]] = ("published", "partial")

#: The current verdicts that leave a finding waiting for the expert. ``pending`` is what a finding with no
#: recorded verdict reads as; ``needs_manual_review`` has no producer today and is treated as undecided so that
#: the day it gets one it is not silently counted as decided.
UNDECIDED_VERDICTS: Final[tuple[str, ...]] = ("pending", "needs_manual_review")

#: One row per *kind* of current document, grouped in the database: the project and the confirmed section of the
#: document's current version, the state of its result run (``NULL`` when it has none), whether that run
#: published any finding and whether any of them is undecided -- with the number of documents of that kind and the
#: findings they hold. Rows are bounded by projects x sections x a handful of kinds, never by documents or
#: findings, and nothing is summed in Python from a page walked one cursor at a time.
#:
#: ``current_docs`` is the join ``DocumentRepository._LIST_PROJECTS`` counts ``document_count`` through (a
#: document whose ``current_version_uid`` is ``NULL`` is not listed and not counted) plus
#: ``version_classification_current`` for the section, as the dashboard's section breakdown always joined it: a
#: ``LEFT JOIN``, so a version no expert has classified is one ``NULL`` section.
#:
#: ``result_run`` takes, per current version, the first of its published or partial runs in ``(created_at DESC,
#: run_id DESC)`` -- ``listRuns``' order, so the result run is the newest run ``listRuns`` would show among
#: those. ``run_finding`` is the set of ``finding_uid`` the result run published; ``GROUP BY`` makes it a set,
#: so a finding observed twice by one run counts once.
#:
#: The project scope is the predicate every statement of this package shares (`UI-PARITY-P0A`): absent, it is
#: true for every row; present, it narrows ``current_docs`` and everything after it. The cast is the one
#: ``decisions.journal`` explains.
_AUDIT_GROUPS = text(
    """
    WITH current_docs AS (
        SELECT d.project_uid, v.version_uid, c.section_code
        FROM document d
        JOIN document_version v ON v.version_uid = d.current_version_uid
        LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid
        WHERE (CAST(:project_uid AS text) IS NULL OR d.project_uid = CAST(:project_uid AS text))
    ),
    result_run AS (
        SELECT DISTINCT ON (r.version_uid) r.version_uid, r.run_id, r.state
        FROM audit_run r
        WHERE r.state IN ('published', 'partial')
          AND r.version_uid IN (SELECT version_uid FROM current_docs)
        ORDER BY r.version_uid, r.created_at DESC, r.run_id DESC
    ),
    run_finding AS (
        SELECT rr.version_uid, o.finding_uid
        FROM result_run rr
        JOIN finding_observation o ON o.run_id = rr.run_id
        JOIN finding f ON f.finding_uid = o.finding_uid
        GROUP BY rr.version_uid, o.finding_uid
    ),
    version_findings AS (
        SELECT rf.version_uid,
               count(*) AS findings,
               count(*) FILTER (
                   WHERE cv.current_verdict IN ('pending', 'needs_manual_review')
               ) AS undecided
        FROM run_finding rf
        JOIN finding_current_verdict cv ON cv.finding_uid = rf.finding_uid
        GROUP BY rf.version_uid
    ),
    document_facts AS (
        SELECT cd.project_uid, cd.section_code, rr.state AS result_state,
               coalesce(vf.findings, 0) AS findings,
               coalesce(vf.undecided, 0) AS undecided
        FROM current_docs cd
        LEFT JOIN result_run rr ON rr.version_uid = cd.version_uid
        LEFT JOIN version_findings vf ON vf.version_uid = cd.version_uid
    )
    SELECT project_uid, section_code, result_state,
           (findings > 0) AS has_findings,
           (undecided > 0) AS has_undecided,
           count(*) AS documents,
           sum(findings) AS findings,
           sum(undecided) AS undecided
    FROM document_facts
    GROUP BY project_uid, section_code, result_state, (findings > 0), (undecided > 0)
    """
)


@dataclass(frozen=True, slots=True)
class DocumentAuditState:
    """The audit state of one document: one of :data:`AUDIT_STATES` and the partial flag (`R-150s`)."""

    state: str
    partial: bool


def audit_state(
    result_state: str | None, has_findings: bool, has_undecided: bool
) -> DocumentAuditState:
    """The state of a document from the three facts that decide it. The one place the rule is written.

    ``result_state`` is the state of the document's result run -- ``published`` or ``partial`` -- or ``None``
    when the current version has none (never run, run only to ``failed`` or ``cancelled``, or its newest run
    still in flight with nothing earlier to fall back on). ``has_findings`` says the result run published at
    least one finding and ``has_undecided`` that at least one of them is still undecided.

    A combination the database cannot produce is refused out loud rather than classified: a state that
    quietly turned an impossible input into one of the four words would be the silent fallback `AGENTS.md`
    section 4 forbids.
    """
    if result_state is not None and result_state not in RESULT_RUN_STATES:
        raise ValueError(f"{result_state!r} is not the state of a result run")
    if has_undecided and not has_findings:
        raise ValueError("an undecided finding implies the result run has findings")
    if result_state is None:
        if has_findings:
            raise ValueError("a document with no result run cannot hold findings")
        return DocumentAuditState(state="not_run", partial=False)
    partial = result_state == "partial"
    if not has_findings:
        return DocumentAuditState(state="clean", partial=partial)
    if has_undecided:
        return DocumentAuditState(state="awaiting_decision", partial=partial)
    return DocumentAuditState(state="checked", partial=partial)


@dataclass(frozen=True, slots=True)
class AuditCountsRecord:
    """How many documents sit in each audit state, and the two derived figures (`R-150o`).

    ``document_count`` is the sum of the four states: a document is in exactly one. ``partial`` counts the
    documents whose result run is ``partial`` and is *not* a fifth state -- those documents are also in one
    of the four. ``awaiting_decision`` is the red badge «ждут решения»: documents with a result and undecided
    findings. ``no_expert_decision`` is the original's column «Нет решений эксперта»: every document not
    closed, the never-run ones included, **but not** ``clean`` (`R-150n`).
    """

    document_count: int = 0
    not_run: int = 0
    clean: int = 0
    awaiting_decision: int = 0
    checked: int = 0
    partial: int = 0

    @property
    def no_expert_decision(self) -> int:
        return self.not_run + self.awaiting_decision


@dataclass(frozen=True, slots=True)
class AuditGroupRecord:
    """One row of the read model: ``documents`` documents of one kind, and the findings they hold.

    ``project_uid`` and ``section`` (``None`` for a version no expert has classified) say where they are;
    the other three facts say what state they are in. ``findings`` is the number of published findings of
    these documents' result runs and ``undecided_findings`` the number of those still undecided.
    """

    project_uid: str
    section: str | None
    result_state: str | None
    has_findings: bool
    has_undecided: bool
    documents: int
    findings: int
    undecided_findings: int

    @property
    def state(self) -> DocumentAuditState:
        return audit_state(self.result_state, self.has_findings, self.has_undecided)


@dataclass(frozen=True, slots=True)
class SectionAuditRecord:
    """The tally of one section: the counts of its documents and the findings of their result runs."""

    counts: AuditCountsRecord
    finding_count: int


def tally(groups: Iterable[AuditGroupRecord]) -> AuditCountsRecord:
    """The counters of a set of groups. A group holds ``documents`` documents all in one state."""
    totals = {state: 0 for state in AUDIT_STATES}
    partial = 0
    for group in groups:
        state = group.state
        totals[state.state] += group.documents
        if state.partial:
            partial += group.documents
    return AuditCountsRecord(
        document_count=sum(totals.values()),
        not_run=totals["not_run"],
        clean=totals["clean"],
        awaiting_decision=totals["awaiting_decision"],
        checked=totals["checked"],
        partial=partial,
    )


def counts_by_project(groups: Iterable[AuditGroupRecord]) -> dict[str, AuditCountsRecord]:
    """The counters of every project that has a current document. A project with none is absent here;
    the caller that lists projects fills it with :class:`AuditCountsRecord`'s zeros, a measurement and not
    an omission."""
    grouped: dict[str, list[AuditGroupRecord]] = {}
    for group in groups:
        grouped.setdefault(group.project_uid, []).append(group)
    return {project: tally(rows) for project, rows in grouped.items()}


def counts_by_section(groups: Iterable[AuditGroupRecord]) -> dict[str | None, SectionAuditRecord]:
    """The counters and the finding count of every section (``None`` is the unclassified bucket) that has a
    current document."""
    grouped: dict[str | None, list[AuditGroupRecord]] = {}
    for group in groups:
        grouped.setdefault(group.section, []).append(group)
    return {
        section: SectionAuditRecord(
            counts=tally(rows), finding_count=sum(row.findings for row in rows)
        )
        for section, rows in grouped.items()
    }


def awaiting_decision_findings(groups: Iterable[AuditGroupRecord]) -> int:
    """Undecided findings in the result runs of current versions (`R-150q`): the figure of the tile
    «Находки, ожидающие решения». A finding of an older version, of a run that is not a result, or of a
    result run that a later result run superseded is not in it."""
    return sum(group.undecided_findings for group in groups)


class DocumentAuditReadModel:
    """The one query. ``groups`` reads it; the functions above turn it into the three outputs."""

    __slots__ = ()

    def groups(
        self, session: Session, *, project_uid: str | None = None
    ) -> tuple[AuditGroupRecord, ...]:
        """The read model over the whole deployment, or over one project. An unknown project is an empty
        answer here; a caller that must tell the two apart proves the project first, as
        ``DashboardRepository.summary`` does."""
        rows = session.execute(_AUDIT_GROUPS, {"project_uid": project_uid}).all()
        return tuple(
            AuditGroupRecord(
                project_uid=row[0],
                section=row[1],
                result_state=row[2],
                has_findings=bool(row[3]),
                has_undecided=bool(row[4]),
                documents=int(row[5]),
                findings=int(row[6]),
                undecided_findings=int(row[7]),
            )
            for row in (tuple(r) for r in rows)
        )
