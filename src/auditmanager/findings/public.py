"""Cross-context surface of the findings boundary."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.findings.artifacts import BlockIndex, ObservationSet, TextLayer
from auditmanager.findings.grounding import run_grounding_gate
from auditmanager.findings.publication import PublicationResult, publish_gate_result
from auditmanager.findings.queries import finding_exists, observation_belongs_to_finding
from auditmanager.findings.recorded_saved_plan import (
    SavedRecordedPublicationPlan, plan_recorded_saved_publication,
)
from auditmanager.findings.terminal import TerminalSelection, select_terminal
from auditmanager.findings.v2_publication import (
    V2PublicationContext, V2PublicationResult, publish_v2_merge_plan,
)


_PUBLICATION_ROWS_FOR_RUN = text(
    "SELECT EXISTS (SELECT 1 FROM finding WHERE allocated_by_run_id = :run_id "
    "UNION ALL SELECT 1 FROM finding_observation WHERE run_id = :run_id)"
)


def publication_rows_exist(session: Session, run_id: str) -> bool:
    """Refuse a second publication even if a prior finding has no observation."""
    return bool(session.execute(_PUBLICATION_ROWS_FOR_RUN, {"run_id": run_id}).scalar_one())

__all__ = [
    "BlockIndex",
    "ObservationSet",
    "PublicationResult",
    "SavedRecordedPublicationPlan",
    "TerminalSelection",
    "TextLayer",
    "V2PublicationContext",
    "V2PublicationResult",
    "finding_exists",
    "observation_belongs_to_finding",
    "publish_gate_result",
    "publish_v2_merge_plan",
    "plan_recorded_saved_publication",
    "publication_rows_exist",
    "run_grounding_gate",
    "select_terminal",
]
