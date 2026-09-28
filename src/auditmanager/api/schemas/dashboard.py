"""``DashboardSummary`` and its four panels. See ``getDashboardSummary`` in
``api/routers/dashboard.py`` and ``docs/program/W46-SEAL.md`` section 3 for the argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "DashboardSummaryView",
    "ProjectDocumentCountView",
    "RunActivitySpendView",
    "RunStateCountView",
    "SectionDocumentCountView",
    "VerdictCountView",
    "dashboard_summary_body",
]


@dataclass(frozen=True, slots=True)
class ProjectDocumentCountView:
    project_uid: str
    name: str
    document_count: int


@dataclass(frozen=True, slots=True)
class VerdictCountView:
    verdict: str
    count: int


@dataclass(frozen=True, slots=True)
class RunStateCountView:
    state: str
    count: int


@dataclass(frozen=True, slots=True)
class RunActivitySpendView:
    model_call_count: int
    cost_micros: int
    cost_basis: str


@dataclass(frozen=True, slots=True)
class SectionDocumentCountView:
    document_count: int
    #: ``None`` for the unclassified bucket. Omitted from the wire body, never sent as
    #: ``null`` -- the same convention ``DocumentVersion.section`` already carries, so a
    #: reader of either shape learns "no section" the same way.
    section: str | None = None


@dataclass(frozen=True, slots=True)
class DashboardSummaryView:
    """See the module docstring for the argument. ``run_spend`` is ``None`` on a
    deployment with no ``model_call`` row anywhere -- `F-1`
    (``docs/program/reviews/W46-JUDGE-A.md`` section 3). ``dashboard_summary_body``
    carries that absence to an absent ``spend`` key, never to a zero labelled
    ``measured``.
    """

    documents_by_project: tuple[ProjectDocumentCountView, ...]
    findings_by_verdict: tuple[VerdictCountView, ...]
    run_activity: tuple[RunStateCountView, ...]
    run_spend: RunActivitySpendView | None
    section_breakdown: tuple[SectionDocumentCountView, ...]


def _section_body(view: SectionDocumentCountView) -> dict[str, Any]:
    body: dict[str, Any] = {"document_count": view.document_count}
    if view.section is not None:
        body["section"] = view.section
    return body


def _run_activity_body(view: DashboardSummaryView) -> dict[str, Any]:
    body: dict[str, Any] = {
        "by_state": [{"state": row.state, "count": row.count} for row in view.run_activity]
    }
    # `F-1` (`docs/program/reviews/W46-JUDGE-A.md` section 3). `spend` is omitted, never
    # sent as a zero, when this deployment has made no provider call at all -- the same
    # convention `_section_body` already carries for the unclassified bucket's `section`
    # key. A reader of either shape learns "nothing to report" the same way.
    if view.run_spend is not None:
        body["spend"] = {
            "model_call_count": view.run_spend.model_call_count,
            "cost_micros": view.run_spend.cost_micros,
            "cost_basis": view.run_spend.cost_basis,
        }
    return body


def dashboard_summary_body(view: DashboardSummaryView) -> dict[str, Any]:
    return {
        "documents_by_project": [
            {
                "project_uid": row.project_uid,
                "name": row.name,
                "document_count": row.document_count,
            }
            for row in view.documents_by_project
        ],
        "findings_by_verdict": [
            {"verdict": row.verdict, "count": row.count}
            for row in view.findings_by_verdict
        ],
        "run_activity": _run_activity_body(view),
        "section_breakdown": [_section_body(row) for row in view.section_breakdown],
    }
