"""The value types ``getDashboardSummary`` returns. Plain facts, nothing rendered.

See ``repository.py`` for what each one is computed from and ``docs/program/W46-SEAL.md``
section 3 for the argument this whole module exists to satisfy: one operation answering a
fixed, named question about the whole deployment, not a filtered query a caller could steer.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DashboardSummaryRecord",
    "ProjectDocumentCountRecord",
    "RunActivitySpendRecord",
    "RunStateCountRecord",
    "SectionDocumentCountRecord",
    "VerdictCountRecord",
]


@dataclass(frozen=True, slots=True)
class ProjectDocumentCountRecord:
    """One row of the "documents per project" panel.

    **Not a second definition of the count `listProjects` already publishes.** This is
    the same join `DocumentRepository._LIST_PROJECTS` uses, read through
    ``DocumentRepository.list_projects`` rather than restated -- see
    ``DashboardRepository.summary``. A project with no documents reports ``0``, exactly
    as ``Project.document_count`` does, for the same `D-3` reason.
    """

    project_uid: str
    name: str
    document_count: int


@dataclass(frozen=True, slots=True)
class VerdictCountRecord:
    """How many findings currently stand at one verdict, across every project.

    Every member of the frozen ``Verdict`` enum is present, including one whose count is
    ``0`` -- "a verdict nobody has recorded" is a real, distinguishable answer and is
    never dropped from the list for reporting nothing. Read from
    ``finding_current_verdict``, the same rebuildable projection ``decisions.projection``
    and ``decisions.journal`` already read, so this is a second reader of one answer and
    not a second place a verdict lives.
    """

    verdict: str
    count: int


@dataclass(frozen=True, slots=True)
class RunStateCountRecord:
    """How many runs currently sit in one state, across every project.

    Every member of the frozen ``RunState`` enum is present, including a ``0``. A project
    -- or a deployment -- with no runs in a given state is that state's count reporting
    zero, not the state missing from the list.
    """

    state: str
    count: int


@dataclass(frozen=True, slots=True)
class RunActivitySpendRecord:
    """What every run, across the whole deployment, has spent at the provider so far.

    The same conservative rule ``runs.repository.RunCost`` applies to one run, lifted to
    every ``model_call`` row that exists: ``basis`` is ``"measured"`` only when every
    contributing row reported a measured cost, and ``"estimated"`` the moment one does
    not. Read from ``model_call`` directly and never from ``stage_result.metrics``, for
    the `D-15` reason ``runs.repository._COST_SUMMARY`` already gives.
    """

    model_call_count: int
    cost_micros: int
    basis: str


@dataclass(frozen=True, slots=True)
class SectionDocumentCountRecord:
    """How many published documents carry one project section (`R-40`, `D-56`).

    ``section`` is ``None`` for the bucket of documents nobody has classified yet -- it is
    reported, not dropped, because absent is not empty. Every one of the fourteen frozen
    codes is present even when its count is ``0``: "a section with no documents" is the
    example the dispatch brief itself names.
    """

    section: str | None
    document_count: int


@dataclass(frozen=True, slots=True)
class DashboardSummaryRecord:
    """The whole of what ``getDashboardSummary`` answers. See the module docstring."""

    documents_by_project: tuple[ProjectDocumentCountRecord, ...]
    findings_by_verdict: tuple[VerdictCountRecord, ...]
    run_activity: tuple[RunStateCountRecord, ...]
    run_spend: RunActivitySpendRecord
    section_breakdown: tuple[SectionDocumentCountRecord, ...]
