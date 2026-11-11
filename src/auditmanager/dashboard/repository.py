"""``getDashboardSummary``: one aggregate read, computed in the database, never walked.

`R-44` (``docs/program/OWNER_RULINGS_2026-09-17.md`` section 3.15): three of the four
dashboard panels are already reachable by walking an existing listing -- ``listProjects``'s
``document_count``, ``listDecisions`` with its filters, ``listRuns``'s cost fields -- and
the integrator ruled that the reseal this wave opens anyway (`R-40`) should carry one
aggregate operation that serves all four, rather than three client-side walks built now and
deleted the day a real aggregate read lands. See ``docs/program/W46-SEAL.md`` section 3 for
the full argument, including what this operation refuses to become.

Every count below is computed with ``GROUP BY``, in the database, over the whole
deployment -- or, when the caller names one project (`UI-PARITY-P0A`, the optional
``project_uid`` of ``getDashboardSummary``), over that project alone with exactly the same
definitions. Nothing here paginates and nothing here is summed in Python from a page walked
one cursor at a time -- that is the shape `R-24` and `R-44` both rule against.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.identity import ProjectUid
from auditmanager.shared.errors import DomainError, ErrorCode

from .audit_state import (
    AuditCountsRecord,
    DocumentAuditReadModel,
    awaiting_decision_findings,
    counts_by_section,
)
from .models import (
    DashboardSummaryRecord,
    ProjectDocumentCountRecord,
    RunActivitySpendRecord,
    RunStateCountRecord,
    SectionDocumentCountRecord,
    VerdictCountRecord,
)

__all__ = ["DashboardRepository"]

#: Exactly ``api.schemas.models.Verdict``'s members. Restated rather than imported: this
#: is the domain layer and does not import the transport contract, the same boundary
#: ``documents.repository`` and ``decisions.journal`` already hold. Agreement is asserted
#: by ``tests/contract/domain_p02/test_project_section_catalog.py``.
VERDICTS: Final[tuple[str, ...]] = (
    "pending",
    "accepted",
    "rejected",
    "needs_manual_review",
)

#: Exactly ``api.schemas.models.RunState``'s members, restated for the same reason.
RUN_STATES: Final[tuple[str, ...]] = (
    "created",
    "queued",
    "running",
    "validating",
    "published",
    "partial",
    "failed",
    "cancelled",
)

#: Exactly ``api.schemas.models.ProjectSection``'s fifteen members and
#: ``db/migrations/versions/20261020_0024_version_classification.py``'s
#: ``PROJECT_SECTIONS``, restated for the same reason: legacy's fourteen, in legacy's order
#: (``0011_document_section`` keeps those as the historical record), then ``PS``
#: (`W59-SECTION-SEAL-01`).
PROJECT_SECTIONS: Final[tuple[str, ...]] = (
    "AR",
    "AI",
    "KM",
    "KJ",
    "OV",
    "EOM",
    "VK",
    "PT",
    "PB",
    "SS",
    "ITP",
    "GP",
    "TX",
    "POS",
    "PS",
)

#: Findings by their current verdict, across every project **and every run, all time** (`R-150q`): the
#: panel «Находки по вердикту» is the history of the deployment's verdicts, labelled «за всё время», and it
#: deliberately is *not* restricted to the current versions' result runs -- that is
#: ``DashboardSummaryRecord.awaiting_decision_findings``, which comes from the audit-state read model.
#: One row per finding: the view already reduces "every verdict-bearing event this finding ever had" to "the one
#: that stands now", so this is not a second projection -- it is a GROUP BY over the one
#: PostgreSQL already computes.
#:
#: **The project scope** (`UI-PARITY-P0A`) is the one predicate every panel below shares:
#: ``CAST(:project_uid AS text) IS NULL OR <project column> = CAST(:project_uid AS text)``. Absent
#: (``NULL``), it is true for every row and the statement is the whole-deployment one it always was;
#: present, it narrows the rows the same ``GROUP BY`` groups. One statement per panel, not a second
#: statement per panel, so the two modes cannot come to define a count differently. The cast is the
#: one ``decisions.journal`` explains: without it PostgreSQL cannot type the parameter on the
#: ``IS NULL`` branch.
_FINDINGS_BY_VERDICT = text(
    "SELECT v.current_verdict, count(*) "
    "FROM finding f JOIN finding_current_verdict v ON v.finding_uid = f.finding_uid "
    "WHERE (CAST(:project_uid AS text) IS NULL OR f.project_uid = CAST(:project_uid AS text)) "
    "GROUP BY v.current_verdict"
)

#: Runs by their current state, across every project. A run an expert deleted from the run lists (`RUN-DELETE-01`, a row of
#: ``audit_run_deletion``) is not counted: the panel counts what the lists show.
_RUNS_BY_STATE = text(
    "SELECT state, count(*) FROM audit_run "
    "WHERE (CAST(:project_uid AS text) IS NULL OR project_uid = CAST(:project_uid AS text)) "
    "AND NOT EXISTS (SELECT 1 FROM audit_run_deletion deleted WHERE deleted.run_id = audit_run.run_id) "
    "GROUP BY state"
)

#: What every run, across every project, has spent at the provider -- the same three
#: values ``runs.repository._COST_SUMMARY`` computes for one run, computed here with no
#: ``WHERE run_id = ...`` at all. See ``RunActivitySpendRecord`` for the conservative
#: basis rule.
#:
#: **The run-level cost rule** (`EXEC-HTTP-01`), the same as ``runs.repository._COST_SUMMARY``
#: states for one run: a call through an unmetered connection has no figure of its own but still
#: counts as a call. When every call in the deployment is unmetered the aggregate is ``0`` with
#: basis ``unmetered``; when unmetered and metered calls mix it is the metered sum, ``estimated``.
#:
#: **The union of the two journals** (`CMP-SPEND-01`, ADR-0025 decision 5, `R-29`). The deployment's
#: spend is what the Runs journalled in ``model_call`` **plus** what the comparison modules journalled
#: in ``comparison_model_call`` -- the per-run ``runs.repository._COST_SUMMARY`` is untouched, because a
#: comparison call has no Run. Of the comparison journal, a call counts when it may have cost something:
#: ``completed``; ``failed`` **with** a cost (the provider answered something unusable); ``unknown`` (it
#: may have spent, and nothing says how much, so it is a call whose cost is unmeasured: it turns the
#: basis to ``estimated`` and adds nothing to the sum). An open call (``prepared``, ``sent``) has not
#: spent yet and a ``failed`` call without a cost was proven not to have. The comparison rows carry a
#: ``NULL`` ``run_id`` so that the per-run form of this query, ``... WHERE run_id = :run``, which the
#: HTTP run-path test builds by appending to this text, still reads the Runs' rows and none of theirs.
#: The aggregate half of ``_SPEND`` and of ``_SPEND_IN_PROJECT``, written once: the two statements differ
#: only in which rows reach it, so they cannot come to count, sum or label a call differently.
_SPEND_AGGREGATE = (
    "SELECT count(*) AS calls, "
    "       coalesce(sum(cost_micros) FILTER (WHERE cost_basis <> 'unmetered'), 0) AS cost_micros, "
    "       count(*) FILTER (WHERE cost_basis = 'unmetered') AS unmetered, "
    "       count(*) FILTER (WHERE cost_basis <> 'unmetered' "
    "         AND (cost_micros IS NULL OR cost_basis <> 'measured')) AS unmeasured "
    "FROM ("
)
_SPEND = text(
    _SPEND_AGGREGATE
    + "SELECT run_id, cost_micros, cost_basis FROM model_call "
    "      UNION ALL "
    "      SELECT CAST(NULL AS text), cost_micros, coalesce(cost_basis, 'estimated') "
    "      FROM comparison_model_call "
    "      WHERE state IN ('completed', 'unknown') "
    "         OR (state = 'failed' AND cost_micros IS NOT NULL)) AS spend"
)

#: ``_SPEND`` restricted to one project (`UI-PARITY-P0A`): the same two journals, the same aggregate, the
#: rows narrowed to the project's own. A Run's calls are the ``model_call`` rows of its ``audit_run``
#: (``audit_run.project_uid``); a comparison call has no Run but belongs to the project of the
#: ``comparison_work`` it was made for (``comparison_work.project_uid``). It is a separate statement and
#: not a parameter of ``_SPEND`` because the Run-path tests build the per-run form of ``_SPEND`` by appending
#: ``WHERE run_id = :r`` to its text, which a bind parameter inside it would break.
_SPEND_IN_PROJECT = text(
    _SPEND_AGGREGATE
    + "SELECT m.run_id, m.cost_micros, m.cost_basis FROM model_call m "
    "      JOIN audit_run r ON r.run_id = m.run_id "
    "      WHERE r.project_uid = :project_uid "
    "      UNION ALL "
    "      SELECT CAST(NULL AS text), c.cost_micros, coalesce(c.cost_basis, 'estimated') "
    "      FROM comparison_model_call c "
    "      JOIN comparison_work w ON w.comparison_work_id = c.comparison_work_id "
    "      WHERE w.project_uid = :project_uid "
    "        AND (c.state IN ('completed', 'unknown') "
    "             OR (c.state = 'failed' AND c.cost_micros IS NOT NULL))) AS spend"
)

#: The section breakdown is a tally of the audit-state read model (`UI-PARITY-P0B`, ``audit_state.py``): documents
#: by the section their **current version** is confirmed in (`SECTION-READ-MODEL-01`,
#: `W59-SECTION-IDENTITY-DECISION-01`), a section an expert corrected (`CLASSIFICATION-CORRECTION-01`) counting
#: under the corrected one, a version nobody classified in the one ``NULL`` bucket, and the legacy
#: ``document.section`` not read at all. Its ``document_count`` is the sum of the audit states, read once from
#: the same statement as the counters beside it, so the two cannot disagree.


def _filled(
    counted: dict[str | None, int], vocabulary: tuple[str, ...]
) -> list[tuple[str, int]]:
    """Every member of ``vocabulary``, in order, defaulting an absent one to ``0``.

    This is the mechanism behind "absent is not empty": a state, a verdict or a section
    nothing has been recorded under is not missing from the response, it is present with
    the true count of zero.
    """
    return [(member, counted.get(member, 0)) for member in vocabulary]


def spend_record(
    calls: Any, cost_micros: Any, unmetered: Any, unmeasured: Any
) -> RunActivitySpendRecord | None:
    """The aggregate spend from the four figures ``_SPEND`` computes, or ``None`` for no call.

    `F-1` (`docs/program/reviews/W46-JUDGE-A.md` section 3): the branch the lift from
    `runs.repository.RunCost` dropped. `RunCost.calls == 0` answers `None`, never
    `RunCost(0, 0, "measured")` -- those are different facts, and reporting the first as the
    second is the same invented measurement `D-3` forbids. No `model_call` row anywhere in the
    deployment means there is nothing to report, not a zero labelled `measured` over a `FILTER`
    that is trivially satisfied by an empty table.

    **The run-level cost rule** (`EXEC-HTTP-01`): every call unmetered -> cost `0`, basis
    `unmetered`; unmetered and metered mixed -> the metered sum, `estimated`; otherwise
    `measured` only when no metered call is unmeasured. A function of its four arguments so the
    rule is testable per run, with the same SQL restricted to it.
    """
    calls, unmetered = int(calls), int(unmetered)
    if calls == 0:
        return None
    return RunActivitySpendRecord(
        model_call_count=calls,
        cost_micros=0 if unmetered == calls else int(cost_micros),
        basis=(
            "unmetered" if unmetered == calls
            else "measured" if unmetered == 0 and int(unmeasured) == 0
            else "estimated"
        ),
    )


class DashboardRepository:
    """One method, one read, four panels. One optional filter: a project.

    **The only filter, and why it is this one** (`UI-PARITY-P0A`). The header of the product
    names the project the expert is working in, and a dashboard that shows the whole deployment
    beside it answers a question nobody asked. ``project_uid`` restricts every panel to that
    project **with the definitions it already has** -- the same joins, the same ``GROUP BY``, the
    same spend rule -- so the numbers of a project are the numbers of the deployment minus every
    row of every other project, and nothing a metrics dictionary has not yet decided is
    redefined here.

    There is still no date range and no free-text filter. Each would turn this into a second,
    generic query surface over data three other operations already answer narrowly --
    ``AGENTS.md`` section 4's ban on inventing a generic query endpoint. A project is not a
    query language: it is the unit every other panel of this product is already read in.
    """

    __slots__ = ()

    def summary(
        self, session: Session, *, project_uid: str | None = None
    ) -> DashboardSummaryRecord:
        """The four panels, over the whole deployment or over one project.

        ``project_uid`` of ``None`` is the whole deployment and behaves exactly as it did
        before the parameter existed. A project that does not exist is
        ``DomainError(NOT_FOUND, aggregate_type="Project")`` -- the refusal
        ``DocumentRepository.get_project`` already answers every project-scoped read with,
        not a second one -- and never an all-zero summary, which would read as "a project with
        nothing in it".
        """
        listing = DocumentRepository()
        if project_uid is not None:
            # The existence check first: an unknown project is a refusal, not four empty panels.
            listing.get_project(session, ProjectUid(project_uid))
        documents = tuple(
            record
            for record in listing.list_projects(session)
            if project_uid is None or str(record.project_uid) == project_uid
        )
        scope = {"project_uid": project_uid}
        projects = tuple(
            ProjectDocumentCountRecord(
                project_uid=str(record.project_uid),
                name=record.name,
                document_count=record.document_count,
            )
            for record in documents
        )

        verdict_rows: dict[str | None, int] = {
            row[0]: int(row[1])
            for row in (tuple(r) for r in session.execute(_FINDINGS_BY_VERDICT, scope).all())
        }
        verdicts = tuple(
            VerdictCountRecord(verdict=verdict, count=count)
            for verdict, count in _filled(verdict_rows, VERDICTS)
        )

        state_rows: dict[str | None, int] = {
            row[0]: int(row[1])
            for row in (tuple(r) for r in session.execute(_RUNS_BY_STATE, scope).all())
        }
        activity = tuple(
            RunStateCountRecord(state=state, count=count)
            for state, count in _filled(state_rows, RUN_STATES)
        )

        spend = spend_record(
            *tuple(
                session.execute(_SPEND).one()
                if project_uid is None
                else session.execute(_SPEND_IN_PROJECT, scope).one()
            )
        )

        # One read of the audit-state model serves the section breakdown and the tile of findings that await a
        # decision (`R-150q`); `listProjects` tallies the same statement per project.
        groups = DocumentAuditReadModel().groups(session, project_uid=project_uid)
        by_section = counts_by_section(groups)
        # A code this vocabulary does not list would be dropped by the loop below and the breakdown would quietly
        # add up to fewer documents than exist. The database admits exactly the fifteen
        # (`ck_document_version_classification_section_code`), so this is unreachable until a sixteenth is added
        # there without being added here -- and then it is refused out loud rather than under-counted.
        if any(code is not None and code not in PROJECT_SECTIONS for code in by_section):
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message="a confirmed section is missing from the dashboard vocabulary",
            )
        # Every section is a row, a `0` included; the unclassified bucket is appended rather than folded into
        # the vocabulary, which would make it say there are sixteen sections. Appended unconditionally,
        # including when its count is `0`: omitting it would say "no unclassified documents exist as a concept"
        # instead of "there happen to be none right now", the distinction the other fifteen preserve.
        sections: list[SectionDocumentCountRecord] = []
        for section in (*PROJECT_SECTIONS, None):
            counted = by_section.get(section)
            counts = counted.counts if counted is not None else AuditCountsRecord()
            sections.append(
                SectionDocumentCountRecord(
                    section=section,
                    document_count=counts.document_count,
                    audit_counts=counts,
                    finding_count=0 if counted is None else counted.finding_count,
                )
            )

        return DashboardSummaryRecord(
            documents_by_project=projects,
            findings_by_verdict=verdicts,
            run_activity=activity,
            run_spend=spend,
            section_breakdown=tuple(sections),
            awaiting_decision_findings=awaiting_decision_findings(groups),
        )
