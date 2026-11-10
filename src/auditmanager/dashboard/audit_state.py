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
  ``(created_at, run_id)`` -- the order ``listRuns`` returns them in. A newer run still in flight does not displace
  it; ``failed`` and ``cancelled`` runs are not results (`R-150r`); ``partial`` is a result (`R-150s`).
* **The document audit state** is one of four words: ``not_run`` (no result run), ``clean`` (a result run with
  no published finding -- a state of its own, neither "checked" nor "awaiting", `R-150n`),
  ``awaiting_decision`` (a result run with at least one finding whose current verdict is undecided) and
  ``checked`` (a result run, every finding decided). ``partial`` is a flag beside the state, set when the
  result run is ``partial``.
* **Optimisation is not part of it** (`R-150u`): the state is computed on findings only.
* **An active run is a fact beside the state, not a fifth state** (`UI-A-47`, contract 1.40.0). The version's *active
  run* is its latest run in state ``queued``, ``running`` or ``validating`` (``created`` has
  not been admitted yet; the terminal states are not active), ordered by ``(created_at, run_id)`` as the result run is.
  It is read by the per-document statement only, in the same statement as the audit, and changes none of the four
  words: a document whose first run is in flight is still ``not_run`` and a checked one with a re-run in flight is
  still ``checked``. The counters do not read it.

A finding is *undecided* when its current verdict, read from ``finding_current_verdict`` (the projection
``decisions.projection`` and the verdict panel already read), is ``pending`` -- no verdict was ever recorded --
or ``needs_manual_review``, which the database cannot produce today but which an expert would still have to
act on. The *findings of a run* are the grounded observations the run published (``finding_observation`` joined
to ``finding``, one per ``finding_uid``): the set ``listRunFindings`` returns, the same join
``findings.queries`` counts ``published_finding_count`` through.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

__all__ = [
    "AUDIT_STATES",
    "AuditCountsRecord",
    "AuditGroupRecord",
    "DocumentAuditReadModel",
    "DocumentAuditRecord",
    "DocumentAuditState",
    "IN_FLIGHT_RUN_STATES",
    "RESULT_RUN_STATES",
    "SectionAuditRecord",
    "UNDECIDED_VERDICTS",
    "audit_order_key",
    "audit_order_rank",
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

#: The run states of an *active* run (`UI-A-47`): admitted and not yet terminal. ``created`` is not among them -- a run
#: that has not been queued is not yet an audit anyone waits for -- and the SQL names the same three words.
IN_FLIGHT_RUN_STATES: Final[tuple[str, ...]] = ("queued", "running", "validating")

#: The current verdicts that leave a finding waiting for the expert. ``pending`` is what a finding with no
#: recorded verdict reads as; ``needs_manual_review`` has no producer today and is treated as undecided so that
#: the day it gets one it is not silently counted as decided.
UNDECIDED_VERDICTS: Final[tuple[str, ...]] = ("pending", "needs_manual_review")

#: The scope of the whole-deployment read: the project and the confirmed section of every document's current
#: version, narrowed to one project when ``:project_uid`` is given. ``current_docs`` is the join
#: ``DocumentRepository._LIST_PROJECTS`` counts ``document_count`` through (a document whose
#: ``current_version_uid`` is ``NULL`` is not listed and not counted) plus ``version_classification_current`` for
#: the section, as the dashboard's section breakdown always joined it: a ``LEFT JOIN``, so a version no expert has
#: classified is one ``NULL`` section.
#:
#: The project scope is the predicate every statement of this package shares (`UI-PARITY-P0A`): absent, it is
#: true for every row; present, it narrows ``current_docs`` and everything after it. The cast is the one
#: ``decisions.journal`` explains.
_CURRENT_DOCS_OF_A_PROJECT_OR_ALL = """
    WITH current_docs AS (
        SELECT d.project_uid, v.version_uid, c.section_code
        FROM document d
        JOIN document_version v ON v.version_uid = d.current_version_uid
        LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid
        WHERE (CAST(:project_uid AS text) IS NULL OR d.project_uid = CAST(:project_uid AS text))
          -- `R-151a`: an archived document is out of every counter, as the original's deleted one is.
          AND d.archived_at IS NULL
    )"""

#: The scope of the per-document read (`UI-PARITY-DOC-AUDIT`, `UI-A-46`): the versions the caller names -- for
#: ``listDocuments`` the current version of each document it lists, archived ones included when they were asked
#: for (the counters leave them out, a listing that was asked to show them says what state they are in). It is
#: keyed by version and not by document so that an item and its audit always describe the same version, even if
#: an upload moves the document's current version between the listing and this read. The CTE keeps the name
#: ``current_docs`` because the shared tail below reads ``version_uid`` from it and from nothing else.
_CURRENT_DOCS_OF_VERSIONS = """
    WITH current_docs AS (
        SELECT v.version_uid
        FROM document_version v
        WHERE v.version_uid IN :version_uids
    )"""

#: **The rules, written once.** Both statements below are their scope plus this tail, so the result-run rule and
#: the undecided rule cannot drift apart between the counters and the per-document read.
#:
#: ``result_run`` takes, per version in scope, the first of its published or partial runs in ``(created_at DESC,
#: run_id DESC)`` -- ``listRuns``' order, so the result run is the newest run ``listRuns`` would show among
#: those. ``run_finding`` is the set of ``finding_uid`` the result run published; ``GROUP BY`` makes it a set,
#: so a finding observed twice by one run counts once. ``version_findings`` counts them and the undecided ones.
_RESULT_RUN_RULES = """,
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
    )"""

#: The active run of each version in scope (`UI-A-47`): the newest run that is in flight, by the
#: same ``(created_at DESC, run_id DESC)`` order as the result run. ``IN_FLIGHT_RUN_STATES`` is what this statement
#: names; ``tests/unit/dashboard/test_audit_state.py`` asserts the two agree.
_ACTIVE_RUN_RULE = """,
    active_run AS (
        SELECT DISTINCT ON (r.version_uid) r.version_uid, r.run_id, r.state
        FROM audit_run r
        WHERE r.state IN ('queued', 'running', 'validating')
          AND r.version_uid IN (SELECT version_uid FROM current_docs)
        ORDER BY r.version_uid, r.created_at DESC, r.run_id DESC
    )"""

#: The optimisation of each version in scope (`D-361`, contract 1.43.0): its latest pass -- by ``(started_at DESC,
#: optimisation_pass_id DESC)`` -- with the number of its proposals and the number whose decision in force is none (no
#: decision, or a withdrawn one: ``pending``, as the pass's ``decision_counts`` say it). A version no pass was started over
#: has no row. A fact beside the audit state, never part of it (`R-150u`): it changes none of the four words, and the
#: counters' statement does not read it.
#:
#: **How the undecided ones are counted (`D-463`).** The decision in force of a proposal is its latest one by ``seq``. The first
#: form of this statement looked it up for every proposal of every pass on the page with one ``LATERAL`` index probe each: a page
#: of 200 documents whose passes held ~530 proposals (106,000 probes) cost 0.83 s of a 1.29 s statement, and the planner's
#: over-estimate of that nested loop switched JIT on for another ~0.4 s (measured on a stand, `DEBT_REGISTER.md` `D-463`). It is now
#: one pass over the decisions of those proposals -- ``DISTINCT ON (proposal) ... ORDER BY proposal, seq DESC`` -- joined once to the
#: proposals of the latest passes: a proposal is decided exactly when it has a row there whose verdict is not ``revoke``, and the
#: undecided ones are the pass's ``proposal_count`` minus those. ``proposal_count`` is the number of the pass's proposals by the
#: database's own rule (``am_require_optimisation_proposals``: a pass is refused at commit unless exactly that many proposals name
#: it, and both tables are immutable), which is also the figure this statement returns beside it. The answers are equal, proposal
#: for proposal, to the per-proposal form (``tests/integration/dashboard/test_document_audit_optimisation_counts.py`` replays
#: every history shape and runs the old statement as the reference). The same page's counts now cost 0.31 s of its 0.45 s; what remains is
#: proportional to the proposals and decisions of those passes and only a stored per-pass tally removes it (`D-570`).
_OPTIMISATION_RULE = """,
    latest_pass AS (
        SELECT DISTINCT ON (p.version_uid) p.version_uid, p.optimisation_pass_id, p.proposal_count
        FROM optimisation_pass p
        WHERE p.version_uid IN (SELECT version_uid FROM current_docs)
        ORDER BY p.version_uid, p.started_at DESC, p.optimisation_pass_id DESC
    ),
    pass_undecided AS (
        SELECT lp.version_uid,
               lp.proposal_count - count(*) FILTER (WHERE cur.verdict <> 'revoke') AS undecided
        FROM latest_pass lp
        LEFT JOIN (
            SELECT DISTINCT ON (d.optimisation_proposal_id) d.optimisation_proposal_id, q.optimisation_pass_id, d.verdict
            FROM optimisation_proposal_decision d
            JOIN optimisation_proposal q ON q.optimisation_proposal_id = d.optimisation_proposal_id
            WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM latest_pass)
            ORDER BY d.optimisation_proposal_id, d.seq DESC
        ) cur ON cur.optimisation_pass_id = lp.optimisation_pass_id
        GROUP BY lp.version_uid, lp.proposal_count
    )"""

#: One row per *kind* of current document, grouped in the database: the project and the confirmed section of the
#: document's current version, the state of its result run (``NULL`` when it has none), whether that run
#: published any finding and whether any of them is undecided -- with the number of documents of that kind and the
#: findings they hold. Rows are bounded by projects x sections x a handful of kinds, never by documents or
#: findings, and nothing is summed in Python from a page walked one cursor at a time.
_AUDIT_GROUPS = text(
    _CURRENT_DOCS_OF_A_PROJECT_OR_ALL
    + _RESULT_RUN_RULES
    + """,
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

#: One row per named version, in ONE statement however many versions are named (`UI-PARITY-DOC-AUDIT`, `UI-A-46`):
#: the state of its result run (``NULL`` when it has none), that run's id, the number of its published findings
#: and of those still undecided, and (`UI-A-47`) the id and state of its active run (``NULL`` when none is in flight).
#: A named version that exists always has a row: ``current_docs`` is the driving side and everything after it is a
#: ``LEFT JOIN``.
_DOCUMENT_AUDITS = text(
    _CURRENT_DOCS_OF_VERSIONS
    + _RESULT_RUN_RULES
    + _ACTIVE_RUN_RULE
    + _OPTIMISATION_RULE
    + """
    SELECT cd.version_uid, rr.state AS result_state, rr.run_id,
           coalesce(vf.findings, 0) AS findings,
           coalesce(vf.undecided, 0) AS undecided,
           ar.run_id AS active_run_id, ar.state AS active_run_state,
           lp.proposal_count AS optimisation_proposals,
           CASE WHEN lp.version_uid IS NULL THEN NULL ELSE coalesce(pu.undecided, 0) END AS optimisation_undecided
    FROM current_docs cd
    LEFT JOIN result_run rr ON rr.version_uid = cd.version_uid
    LEFT JOIN version_findings vf ON vf.version_uid = cd.version_uid
    LEFT JOIN active_run ar ON ar.version_uid = cd.version_uid
    LEFT JOIN latest_pass lp ON lp.version_uid = cd.version_uid
    LEFT JOIN pass_undecided pu ON pu.version_uid = cd.version_uid
    """
).bindparams(bindparam("version_uids", expanding=True))


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


@dataclass(frozen=True, slots=True)
class DocumentAuditRecord:
    """The audit of one version, as `listDocuments` shows it on a document (`UI-A-46`).

    ``result_state`` / ``finding_count`` / ``undecided_finding_count`` are the facts the read model measured;
    :attr:`state` and :attr:`partial` are :func:`audit_state` over them, the same function the counters use.
    ``result_run_id`` is the result run the card links to, ``None`` exactly when the state is ``not_run``. A
    version whose only runs are ``failed`` or ``cancelled`` is ``not_run`` (`R-150r`); the record does not say
    why, and the «отказ» chip is not decided here. ``active_run_id`` / ``active_run_state`` (`UI-A-47`) name the
    run in flight, whatever the state is.
    """

    version_uid: str
    result_state: str | None
    result_run_id: str | None
    finding_count: int
    undecided_finding_count: int
    #: `UI-A-47`: the version's active run (:data:`IN_FLIGHT_RUN_STATES`) and its state, both ``None`` when none is in
    #: flight. A fact beside the audit state: it never changes :attr:`state`.
    active_run_id: str | None = None
    active_run_state: str | None = None
    #: `D-361` (contract 1.43.0): the proposals of the version's latest optimisation pass and how many of them have no decision
    #: in force; both ``None`` when no pass was started over the version. A fact beside the audit state, never part of it.
    optimisation_proposal_count: int | None = None
    optimisation_undecided_count: int | None = None

    @property
    def audit(self) -> DocumentAuditState:
        return audit_state(
            self.result_state, self.finding_count > 0, self.undecided_finding_count > 0
        )

    @property
    def state(self) -> str:
        return self.audit.state

    @property
    def partial(self) -> bool:
        return self.audit.partial


#: The order of a section's documents (`UI-A-49`, the original's ``projectOrderRank``): 0 the ones the expert
#: has checked, 1 the ones processed and still without every verdict -- ``clean`` and ``awaiting_decision`` --
#: and 2 the ones never audited. The words are :data:`AUDIT_STATES`; a state outside them is refused by
#: :func:`audit_order_rank` and not placed.
_AUDIT_ORDER_RANK: Final[dict[str, int]] = {
    "checked": 0,
    "clean": 1,
    "awaiting_decision": 1,
    "not_run": 2,
}


def audit_order_rank(state: str) -> int:
    """The rank of an audit state in the order ``order=audit`` gives (`UI-A-49`): checked, processed, never run."""
    try:
        return _AUDIT_ORDER_RANK[state]
    except KeyError:
        raise ValueError(f"{state!r} is not an audit state") from None


_DIGITS = re.compile(r"(\d+)")


def _natural_name_key(name: str) -> tuple[tuple[int, int | str], ...]:
    """A name as the original compares one: ``Intl.Collator('ru', {numeric: true, sensitivity: 'base'})``.

    Runs of digits compare as numbers (so «АР1-2» comes before «АР1-10»), everything else compares without
    regard to case or to the marks that sit on a letter (``ё`` as ``е``, ``й`` as ``и``). A digit run sorts
    before a letter run, as ICU puts digits before letters. The comparison is code-point order outside those
    rules, which is ICU's order for names made of Cyrillic and Latin letters, digits, spaces and the usual
    punctuation; it is not a claim to reproduce the collator on every symbol.
    """
    key: list[tuple[int, int | str]] = []
    for chunk in _DIGITS.split(name):
        if not chunk:
            continue
        if chunk.isdigit():
            key.append((0, int(chunk)))
        else:
            base = "".join(
                ch for ch in unicodedata.normalize("NFD", chunk.casefold()) if unicodedata.category(ch) != "Mn"
            )
            key.append((1, base))
    return tuple(key)


def audit_order_key(
    state: str, name: str | None, version_uid: str
) -> tuple[int, tuple[tuple[int, int | str], ...], str]:
    """The sort key of ``order=audit`` (`UI-A-49`): rank by audit state, then the name in natural Russian order,
    then the identity, so that two documents the collator calls equal still have one total order -- the cursor
    of the listing is built on it."""
    return (audit_order_rank(state), _natural_name_key(name or ""), version_uid)


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

    def audits(
        self, session: Session, *, version_uids: Sequence[str]
    ) -> dict[str, DocumentAuditRecord]:
        """The audit of each named version, in one statement (`UI-A-46`).

        The same result-run rule and undecided rule as :meth:`groups` -- the statements share their tail
        (``_RESULT_RUN_RULES``) -- so the audit of a document agrees with the counters that count it. A name
        that is no version is absent from the answer; the caller decides what that means (the port refuses).
        No names is no statement.
        """
        names = tuple(dict.fromkeys(version_uids))
        if not names:
            return {}
        rows = session.execute(_DOCUMENT_AUDITS, {"version_uids": list(names)}).all()
        return {
            str(row[0]): DocumentAuditRecord(
                version_uid=str(row[0]),
                result_state=row[1],
                result_run_id=None if row[2] is None else str(row[2]),
                finding_count=int(row[3]),
                undecided_finding_count=int(row[4]),
                active_run_id=None if row[5] is None else str(row[5]),
                active_run_state=None if row[6] is None else str(row[6]),
                optimisation_proposal_count=None if row[7] is None else int(row[7]),
                optimisation_undecided_count=None if row[8] is None else int(row[8]),
            )
            for row in (tuple(r) for r in rows)
        }
