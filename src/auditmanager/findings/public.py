"""Cross-context surface of the findings boundary."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.findings.artifacts import BlockIndex, ObservationSet, TextLayer
from auditmanager.findings.grounding import UngroundedReason, run_grounding_gate
from auditmanager.findings.publication import PublicationResult, publish_gate_result
from auditmanager.findings.citation_publication import (
    CitationEvidence,
    CitationPublicationRefused,
    PublishedV3CitationFinding,
    V3PublicationCandidate,
    publish_grounded_v3_finding,
)
from auditmanager.findings.retrieval_set_input import (
    RetrievalSetInputRefused,
    VerifiedRetrievalSetInput,
    load_verified_retrieval_set,
    recheck_verified_retrieval_set_facts,
)
from auditmanager.findings.citation_reader import (
    CitationReadRefused,
    VerifiedCitation,
    VerifiedCitationRead,
    VerifiedFindingPartitions,
    VerifiedObservationPartition,
    read_verified_citations,
)
from auditmanager.findings.citation_report import (
    CitationReportRefused,
    VerifiedCitationReport,
    read_verified_citation_report,
)
from auditmanager.findings.queries import (
    finding_exists,
    observation_belongs_to_finding,
    published_finding_evidence,
)
from auditmanager.findings.terminal import TerminalSelection, select_terminal


_PUBLICATION_ROWS_FOR_RUN = text(
    "SELECT EXISTS (SELECT 1 FROM finding WHERE allocated_by_run_id = :run_id "
    "UNION ALL SELECT 1 FROM finding_observation WHERE run_id = :run_id)"
)


def publication_rows_exist(session: Session, run_id: str) -> bool:
    """Refuse a second publication even if a prior finding has no observation."""
    return bool(session.execute(_PUBLICATION_ROWS_FOR_RUN, {"run_id": run_id}).scalar_one())

__all__ = [
    "BlockIndex",
    "CitationEvidence",
    "CitationPublicationRefused",
    "CitationReadRefused",
    "CitationReportRefused",
    "ObservationSet",
    "PublicationResult",
    "PublishedV3CitationFinding",
    "TerminalSelection",
    "TextLayer",
    "UngroundedReason",
    "RetrievalSetInputRefused",
    "VerifiedRetrievalSetInput",
    "V3PublicationCandidate",
    "VerifiedCitation",
    "VerifiedCitationRead",
    "VerifiedCitationReport",
    "VerifiedFindingPartitions",
    "VerifiedObservationPartition",
    "finding_exists",
    "observation_belongs_to_finding",
    "publish_gate_result",
    "publish_grounded_v3_finding",
    "publication_rows_exist",
    "published_finding_evidence",
    "read_verified_citation_report",
    "read_verified_citations",
    "load_verified_retrieval_set",
    "recheck_verified_retrieval_set_facts",
    "run_grounding_gate",
    "select_terminal",
]
