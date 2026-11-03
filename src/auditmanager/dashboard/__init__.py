"""``getDashboardSummary``: one aggregate read across the whole deployment, or one project.

`R-44`; the optional ``project_uid`` is `UI-PARITY-P0A`'s. See ``repository.py`` for the query and ``docs/program/W46-SEAL.md`` section 3 for
the argument -- what this operation answers, and what it refuses to become.
"""

from __future__ import annotations

from .models import (
    DashboardSummaryRecord,
    ProjectDocumentCountRecord,
    RunActivitySpendRecord,
    RunStateCountRecord,
    SectionDocumentCountRecord,
    VerdictCountRecord,
)
from .repository import DashboardRepository

__all__ = [
    "DashboardRepository",
    "DashboardSummaryRecord",
    "ProjectDocumentCountRecord",
    "RunActivitySpendRecord",
    "RunStateCountRecord",
    "SectionDocumentCountRecord",
    "VerdictCountRecord",
]
