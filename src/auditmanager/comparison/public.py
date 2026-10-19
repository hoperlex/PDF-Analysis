"""Cross-context surface of the comparison boundary (`W59-VERSION-COMPARE-01`).

The composition root builds :class:`VersionComparisonService` with adapters for
its two ports and the sealed section catalogue; the API maps the read model.
Everything else in this package stays private to it.
"""

from __future__ import annotations

from auditmanager.comparison.read_model import (
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
    "ComparedVersion",
    "ComparisonIntegrityError",
    "ComparisonRefusal",
    "ComparisonRequest",
    "ComparisonRequestInvalid",
    "DEFAULT_DIFF_LIMIT",
    "DiffHunk",
    "FindingComparison",
    "FindingEvidenceSnapshot",
    "FindingProposal",
    "FindingRef",
    "FindingSnapshot",
    "MAX_DIFF_LIMIT",
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
]
