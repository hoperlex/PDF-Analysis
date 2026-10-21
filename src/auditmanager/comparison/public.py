"""Cross-context surface of the comparison boundary (`W59-VERSION-COMPARE-01`).

The composition root builds :class:`VersionComparisonService` with adapters for
its two ports and the sealed section catalogue; the API maps the read model.
`W59-DECISION-CARRYOVER-01` adds :class:`DecisionCarryoverService` (the confirmed
carryover command over that service) and :func:`carryover_candidates` (its read).
Everything else in this package stays private to it.
"""

from __future__ import annotations

from auditmanager.comparison.carryover import (
    CarriedSourceDecision,
    CarryoverCandidate,
    CarryoverOutcome,
    CarryoverRequest,
    DecisionCarryoverService,
    carryover_candidates,
)
from auditmanager.comparison.read_model import (
    MODE_STAGE,
    MODE_VERSION,
    MODES,
    OUTCOME_COMPARED,
    OUTCOME_REFUSED,
    PROPOSAL_BASES,
    PROPOSAL_KINDS,
    REFUSAL_REASONS,
    SHEET_STATUSES,
    ComparedVersion,
    ComparisonRefusal,
    DiffHunk,
    FindingComparison,
    FindingProposal,
    FindingRef,
    SheetDiff,
    SheetDiffPage,
    SheetPairing,
    VersionComparison,
)
from auditmanager.comparison.service import (
    DEFAULT_DIFF_LIMIT,
    MAX_DIFF_LIMIT,
    ComparisonIntegrityError,
    ComparisonRequest,
    ComparisonRequestInvalid,
    CurrentFindingProposals,
    FindingEvidenceSnapshot,
    FindingSnapshot,
    RunCandidate,
    SavedPageText,
    VersionAnalysisReader,
    VersionClassificationReader,
    VersionComparisonService,
)
from auditmanager.comparison.version_reader import VersionFacts
from auditmanager.comparison.version_section_pair import SuppliedVersionClassification

__all__ = [
    "CarriedSourceDecision",
    "CarryoverCandidate",
    "CarryoverOutcome",
    "CarryoverRequest",
    "ComparedVersion",
    "ComparisonIntegrityError",
    "ComparisonRefusal",
    "ComparisonRequest",
    "ComparisonRequestInvalid",
    "CurrentFindingProposals",
    "DEFAULT_DIFF_LIMIT",
    "DecisionCarryoverService",
    "DiffHunk",
    "FindingComparison",
    "FindingEvidenceSnapshot",
    "FindingProposal",
    "FindingRef",
    "FindingSnapshot",
    "MAX_DIFF_LIMIT",
    "MODES",
    "MODE_STAGE",
    "MODE_VERSION",
    "OUTCOME_COMPARED",
    "OUTCOME_REFUSED",
    "PROPOSAL_BASES",
    "PROPOSAL_KINDS",
    "REFUSAL_REASONS",
    "RunCandidate",
    "SHEET_STATUSES",
    "SavedPageText",
    "SheetDiff",
    "SheetDiffPage",
    "SheetPairing",
    "SuppliedVersionClassification",
    "VersionAnalysisReader",
    "VersionClassificationReader",
    "VersionComparison",
    "VersionComparisonService",
    "VersionFacts",
    "carryover_candidates",
]
