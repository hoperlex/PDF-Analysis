"""Cross-context surface of the findings boundary."""

from __future__ import annotations

from auditmanager.findings.artifacts import (
    BlockEvidenceItem,
    BlockGateInputs,
    BlockIndex,
    BlockObservation,
    ObservationSet,
    TextLayer,
)
from auditmanager.findings.grounding import (
    BlockGateResult,
    UngroundedReason,
    check_block_observation,
    run_block_gate,
    run_grounding_gate,
)
from auditmanager.findings.publication import (
    CandidateGroup,
    CandidateMember,
    CandidatePublicationResult,
    GroupClassification,
    PublicationResult,
    PublishedCandidateFinding,
    SkippedGroup,
    classify_group,
    publish_candidate_groups,
    publish_gate_result,
)
from auditmanager.findings.citation_reader import (
    CitationReadRefused,
    VerifiedCitation,
    VerifiedCitationRead,
    VerifiedFindingPartitions,
    VerifiedObservationPartition,
    read_verified_citations,
)
from auditmanager.findings.queries import (
    BlockEvidenceRow,
    finding_exists,
    observation_belongs_to_finding,
    published_finding_block_evidence,
    published_finding_evidence,
)
from auditmanager.findings.terminal import TerminalSelection, select_terminal

__all__ = [
    "BlockEvidenceItem",
    "BlockEvidenceRow",
    "BlockGateInputs",
    "BlockGateResult",
    "BlockIndex",
    "BlockObservation",
    "CandidateGroup",
    "CandidateMember",
    "CandidatePublicationResult",
    "CitationReadRefused",
    "GroupClassification",
    "ObservationSet",
    "PublicationResult",
    "PublishedCandidateFinding",
    "SkippedGroup",
    "TerminalSelection",
    "TextLayer",
    "UngroundedReason",
    "VerifiedCitation",
    "VerifiedCitationRead",
    "VerifiedFindingPartitions",
    "VerifiedObservationPartition",
    "check_block_observation",
    "classify_group",
    "finding_exists",
    "observation_belongs_to_finding",
    "publish_candidate_groups",
    "publish_gate_result",
    "published_finding_block_evidence",
    "published_finding_evidence",
    "read_verified_citations",
    "run_block_gate",
    "run_grounding_gate",
    "select_terminal",
]
