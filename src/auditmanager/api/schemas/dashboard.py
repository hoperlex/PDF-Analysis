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
    documents_by_project: tuple[ProjectDocumentCountView, ...]
    findings_by_verdict: tuple[VerdictCountView, ...]
    run_activity: tuple[RunStateCountView, ...]
    run_spend: RunActivitySpendView
    section_breakdown: tuple[SectionDocumentCountView, ...]


def _section_body(view: SectionDocumentCountView) -> dict[str, Any]:
    body: dict[str, Any] = {"document_count": view.document_count}
    if view.section is not None:
        body["section"] = view.section
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
        "run_activity": {
            "by_state": [
                {"state": row.state, "count": row.count} for row in view.run_activity
            ],
            "spend": {
                "model_call_count": view.run_spend.model_call_count,
                "cost_micros": view.run_spend.cost_micros,
                "cost_basis": view.run_spend.cost_basis,
            },
        },
        "section_breakdown": [_section_body(row) for row in view.section_breakdown],
    }
