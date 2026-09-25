"""``getDashboardSummary``: one aggregate read across the whole deployment.

`R-44`. See ``repository.py`` for the query and ``docs/program/W46-SEAL.md`` section 3 for
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
