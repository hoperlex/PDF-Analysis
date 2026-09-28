"""``getDashboardSummary``: one aggregate read, computed in the database, never walked.

`R-44` (``docs/program/OWNER_RULINGS_2026-09-17.md`` section 3.15): three of the four
dashboard panels are already reachable by walking an existing listing -- ``listProjects``'s
``document_count``, ``listDecisions`` with its filters, ``listRuns``'s cost fields -- and
the integrator ruled that the reseal this wave opens anyway (`R-40`) should carry one
aggregate operation that serves all four, rather than three client-side walks built now and
deleted the day a real aggregate read lands. See ``docs/program/W46-SEAL.md`` section 3 for
the full argument, including what this operation refuses to become.

Every count below is computed with ``GROUP BY``, in the database, over the whole
deployment. Nothing here paginates and nothing here is summed in Python from a page walked
one cursor at a time -- that is the shape `R-24` and `R-44` both rule against.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.documents.repository import DocumentRepository

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

#: Exactly ``db/migrations/versions/20260925_0011_document_section.py``'s
#: ``PROJECT_SECTIONS``, restated for the same reason.
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
)

#: Findings by their current verdict, across every project. One row per finding: the
#: view already reduces "every verdict-bearing event this finding ever had" to "the one
#: that stands now", so this is not a second projection -- it is a GROUP BY over the one
#: PostgreSQL already computes.
_FINDINGS_BY_VERDICT = text(
    "SELECT v.current_verdict, count(*) "
    "FROM finding f JOIN finding_current_verdict v ON v.finding_uid = f.finding_uid "
    "GROUP BY v.current_verdict"
)

#: Runs by their current state, across every project.
_RUNS_BY_STATE = text("SELECT state, count(*) FROM audit_run GROUP BY state")

#: What every run, across every project, has spent at the provider -- the same three
#: values ``runs.repository._COST_SUMMARY`` computes for one run, computed here with no
#: ``WHERE run_id = ...`` at all. See ``RunActivitySpendRecord`` for the conservative
#: basis rule.
_SPEND = text(
    "SELECT count(*) AS calls, "
    "       coalesce(sum(cost_micros), 0) AS cost_micros, "
    "       count(*) FILTER (WHERE cost_micros IS NULL OR cost_basis <> 'measured') "
    "         AS unmeasured "
    "FROM model_call"
)

#: Published documents by section. ``JOIN ... ON v.version_uid = d.current_version_uid``
#: is the same join ``DocumentRepository._LIST_PROJECTS`` counts through, so "a document"
#: means the same thing here as it does in every other count this contract publishes: one
#: with a published current version. ``GROUP BY d.section`` puts every unclassified
#: document in one NULL group, which SQL already groups together, rather than this
#: query having to special-case it.
_DOCUMENTS_BY_SECTION = text(
    "SELECT d.section, count(*) "
    "FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
    "GROUP BY d.section"
)


def _filled(
    counted: dict[str | None, int], vocabulary: tuple[str, ...]
) -> list[tuple[str, int]]:
    """Every member of ``vocabulary``, in order, defaulting an absent one to ``0``.

    This is the mechanism behind "absent is not empty": a state, a verdict or a section
    nothing has been recorded under is not missing from the response, it is present with
    the true count of zero.
    """
    return [(member, counted.get(member, 0)) for member in vocabulary]


class DashboardRepository:
    """One method, one read, four panels. No filter parameter exists to add to it.

    **Why there is no ``project_uid``, no date range and no free-text filter.** Each
    would turn this into a second, generic query surface over data three other
    operations already answer narrowly -- ``AGENTS.md`` section 4's ban on inventing a
    generic query endpoint. What this answers is fixed: *the operational shape of the
    whole deployment, right now*. A caller that wants one project's documents already has
    ``listDocuments``; one that wants one run's findings already has ``listRunFindings``.
    """

    __slots__ = ()

    def summary(self, session: Session) -> DashboardSummaryRecord:
        documents = DocumentRepository().list_projects(session)
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
            for row in (tuple(r) for r in session.execute(_FINDINGS_BY_VERDICT).all())
        }
        verdicts = tuple(
            VerdictCountRecord(verdict=verdict, count=count)
            for verdict, count in _filled(verdict_rows, VERDICTS)
        )

        state_rows: dict[str | None, int] = {
            row[0]: int(row[1])
            for row in (tuple(r) for r in session.execute(_RUNS_BY_STATE).all())
        }
        activity = tuple(
            RunStateCountRecord(state=state, count=count)
            for state, count in _filled(state_rows, RUN_STATES)
        )

        spend_row: Any = session.execute(_SPEND).one()
        calls, cost_micros, unmeasured = tuple(spend_row)
        calls = int(calls)
        # `F-1` (`docs/program/reviews/W46-JUDGE-A.md` section 3): the branch the lift
        # from `runs.repository.RunCost` dropped. `RunCost.calls == 0` answers `None`,
        # never `RunCost(0, 0, "measured")` -- those are different facts, and reporting
        # the first as the second is the same invented measurement `D-3` forbids. This
        # aggregate now keeps the branch it claims to lift: no `model_call` row anywhere
        # in the deployment means there is nothing to report, not a zero labelled
        # `measured` over a `FILTER` that is trivially satisfied by an empty table.
        spend = (
            None
            if calls == 0
            else RunActivitySpendRecord(
                model_call_count=calls,
                cost_micros=int(cost_micros),
                basis="measured" if int(unmeasured) == 0 else "estimated",
            )
        )

        section_rows: dict[str | None, int] = {
            row[0]: int(row[1])
            for row in (tuple(r) for r in session.execute(_DOCUMENTS_BY_SECTION).all())
        }
        sections = [
            SectionDocumentCountRecord(section=section, document_count=count)
            for section, count in _filled(section_rows, PROJECT_SECTIONS)
        ]
        # The unclassified bucket, appended rather than folded into `_filled`: `None` is
        # not a member of `PROJECT_SECTIONS` and forcing it into that tuple would make the
        # vocabulary say there are fifteen sections. Appended unconditionally, including
        # when its count is `0` -- omitting it there would silently say "no unclassified
        # documents exist as a concept" instead of "there happen to be none right now",
        # which is exactly the distinction the other fourteen already preserve.
        sections.append(
            SectionDocumentCountRecord(
                section=None, document_count=section_rows.get(None, 0)
            )
        )

        return DashboardSummaryRecord(
            documents_by_project=projects,
            findings_by_verdict=verdicts,
            run_activity=activity,
            run_spend=spend,
            section_breakdown=tuple(sections),
        )
