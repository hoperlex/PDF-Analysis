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

from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode

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
#:
#: **The run-level cost rule** (`EXEC-HTTP-01`), the same as ``runs.repository._COST_SUMMARY``
#: states for one run: a call through an unmetered connection has no figure of its own but still
#: counts as a call. When every call in the deployment is unmetered the aggregate is ``0`` with
#: basis ``unmetered``; when unmetered and metered calls mix it is the metered sum, ``estimated``.
_SPEND = text(
    "SELECT count(*) AS calls, "
    "       coalesce(sum(cost_micros) FILTER (WHERE cost_basis <> 'unmetered'), 0) AS cost_micros, "
    "       count(*) FILTER (WHERE cost_basis = 'unmetered') AS unmetered, "
    "       count(*) FILTER (WHERE cost_basis <> 'unmetered' "
    "         AND (cost_micros IS NULL OR cost_basis <> 'measured')) AS unmeasured "
    "FROM model_call"
)

#: Published documents by the section their **current version** is confirmed in
#: (`SECTION-READ-MODEL-01`, `W59-SECTION-IDENTITY-DECISION-01`). ``document.current_version_uid``
#: selects the version -- the same join ``DocumentRepository._LIST_PROJECTS`` counts through,
#: so "a document" means one with a published current version here as in every other count
#: this contract publishes -- and that version's row in ``version_classification_current`` is
#: its confirmed section: the latest revision, so a section an expert corrected
#: (`CLASSIFICATION-CORRECTION-01`) counts under the corrected one and never under the original.
#: The ``LEFT JOIN`` is the unclassified rule: a current version no
#: expert has classified has no row, so ``section_code`` is NULL and ``GROUP BY`` puts every
#: such document in one NULL group, which SQL already groups together, rather than this query
#: having to special-case it. The legacy ``document.section`` is **not read at all**: it is
#: the old document-level label, not an expert's confirmation, and an older version's
#: classification never counts for the set whose head moved on.
_DOCUMENTS_BY_SECTION = text(
    "SELECT c.section_code, count(*) "
    "FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
    "LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid "
    "GROUP BY c.section_code"
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

        spend = spend_record(*tuple(session.execute(_SPEND).one()))

        section_rows: dict[str | None, int] = {
            row[0]: int(row[1])
            for row in (tuple(r) for r in session.execute(_DOCUMENTS_BY_SECTION).all())
        }
        # A code this vocabulary does not list would be dropped by `_filled` and the
        # breakdown would quietly add up to fewer documents than exist. The database admits
        # exactly the fifteen (`ck_document_version_classification_section_code`), so this is
        # unreachable until a sixteenth is added there without being added here -- and then
        # it is refused out loud rather than under-counted.
        if any(code is not None and code not in PROJECT_SECTIONS for code in section_rows):
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message="a confirmed section is missing from the dashboard vocabulary",
            )
        sections = [
            SectionDocumentCountRecord(section=section, document_count=count)
            for section, count in _filled(section_rows, PROJECT_SECTIONS)
        ]
        # The unclassified bucket, appended rather than folded into `_filled`: `None` is
        # not a member of `PROJECT_SECTIONS` and forcing it into that tuple would make the
        # vocabulary say there are sixteen sections. Appended unconditionally, including
        # when its count is `0` -- omitting it there would silently say "no unclassified
        # documents exist as a concept" instead of "there happen to be none right now",
        # which is exactly the distinction the other fifteen already preserve.
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
