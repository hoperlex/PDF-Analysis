"""``DocumentAuditCounts``: the audit-state counters of a set of documents, as the wire carries them.

`UI-PARITY-P0B`, `R-150n` ... `R-150u`. One shape, three places: ``Project.audit_counts`` (``listProjects``),
``SectionDocumentCount.audit_counts`` and the totals behind ``DashboardSummary``. Nothing is computed here: the
read model (``auditmanager.dashboard.audit_state``) decides what a document's state is and tallies it, and the
adapters copy its record field for field into this view, including the derived ``no_expert_decision``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["DocumentAuditCountsView", "audit_counts_body"]


@dataclass(frozen=True, slots=True)
class DocumentAuditCountsView:
    document_count: int
    not_run: int
    clean: int
    awaiting_decision: int
    checked: int
    partial: int
    no_expert_decision: int


def audit_counts_body(view: DocumentAuditCountsView) -> dict[str, Any]:
    return {
        "document_count": view.document_count,
        "not_run": view.not_run,
        "clean": view.clean,
        "awaiting_decision": view.awaiting_decision,
        "checked": view.checked,
        "partial": view.partial,
        "no_expert_decision": view.no_expert_decision,
    }
