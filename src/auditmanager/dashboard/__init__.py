"""``getDashboardSummary``: one aggregate read across the whole deployment, or one project.

`R-44`; the optional ``project_uid`` is `UI-PARITY-P0A`'s. See ``repository.py`` for the query and ``docs/program/W46-SEAL.md`` section 3 for
the argument -- what this operation answers, and what it refuses to become.

``audit_state.py`` is the read model of a document's audit state and its counters (`UI-PARITY-P0B`), shared by this
operation's section panel and findings tile and by ``listProjects``' ``audit_counts``. The classifying function
``audit_state`` is imported from that module (``auditmanager.dashboard.audit_state``); it is not re-exported here, because
a package attribute named like its submodule would hide the module.
"""

from __future__ import annotations

from .audit_state import (
    AUDIT_STATES,
    AuditCountsRecord,
    AuditGroupRecord,
    DocumentAuditReadModel,
    DocumentAuditRecord,
    DocumentAuditState,
    SectionAuditRecord,
    audit_order_key,
    audit_order_rank,
    awaiting_decision_findings,
    counts_by_project,
    counts_by_section,
    tally,
)
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
    "AUDIT_STATES",
    "AuditCountsRecord",
    "AuditGroupRecord",
    "DashboardRepository",
    "DocumentAuditReadModel",
    "DocumentAuditRecord",
    "DocumentAuditState",
    "SectionAuditRecord",
    "audit_order_key",
    "audit_order_rank",
    "awaiting_decision_findings",
    "counts_by_project",
    "counts_by_section",
    "tally",
    "DashboardSummaryRecord",
    "ProjectDocumentCountRecord",
    "RunActivitySpendRecord",
    "RunStateCountRecord",
    "SectionDocumentCountRecord",
    "VerdictCountRecord",
]
