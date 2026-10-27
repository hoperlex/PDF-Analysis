"""Cross-context surface of the comparison boundary (`W59-VERSION-COMPARE-01`).

The composition root builds :class:`VersionComparisonService` with adapters for
its two ports and the sealed section catalogue; the API maps the read model.
`W59-DECISION-CARRYOVER-01` adds :class:`DecisionCarryoverService` (the confirmed
carryover command over that service) and :func:`carryover_candidates` (its read).
`COMPARE-PERSISTED-SUMMARY-01` adds :class:`SheetPairingService` (approve and withdraw a sheet
pairing over the append-only history in ``comparison_sheet_link``) and the approved pairs the read
now carries.
Everything else in this package stays private to it.
"""

from __future__ import annotations

from auditmanager.comparison.modules import (
    COMPARISON_MODULES_ENV,
    DEFAULT_MODULES,
    MODULE_SETS,
    MODULE_STAGES,
    MODULE_VERSIONS,
    enabled_modules,
    parse_modules,
)
from auditmanager.comparison.carryover import (
    CarriedSourceDecision,
    CarryoverCandidate,
    CarryoverOutcome,
    CarryoverRequest,
    DecisionCarryoverService,
    carryover_candidates,
)
from auditmanager.comparison.pairing import (
    CONFLICT_REASONS as PAIRING_CONFLICT_REASONS,
)
from auditmanager.comparison.pairing import (
    ApproveSheetPairingRequest,
    PairingOutcome,
    SheetPairingService,
    WithdrawSheetPairingRequest,
)
from auditmanager.comparison.summaries import (
    CONFLICT_SUMMARY_EVIDENCE_NOT_SEALED,
    CONFLICT_SUMMARY_INPUT_EMPTY,
    CONFLICT_SUMMARY_INPUT_TOO_LARGE,
    DEPENDENCY_SUMMARY_MODEL,
    GenerateSummaryRequest,
    SummaryCostGate,
    SummaryOutcome,
    SummaryService,
    SummaryStore,
)
from auditmanager.comparison.summary_model import RecordedSummaryModel, SummaryModel, SummaryReply
from auditmanager.comparison.summary_records import LatestSummaryReader, StoredSummary
from auditmanager.comparison.read_model import (
    SUMMARY_LABEL,
    ComparisonSummaryView,
    SummaryStatementView,
    EVIDENCE_NONE,
    EVIDENCE_SEAL_CHANGED,
    EVIDENCE_SEALED,
    EVIDENCE_STATES,
    EVIDENCE_TEXT_CHANGED,
    EVIDENCE_TOO_LARGE,
    LINK_STATES,
    LINK_TEXT_CHANGED,
    LINK_VERIFIED,
    MODE_STAGE,
    MODE_VERSION,
    MODES,
    OUTCOME_COMPARED,
    OUTCOME_REFUSED,
    PROPOSAL_BASES,
    PROPOSAL_KINDS,
    REFUSAL_REASONS,
    SHEET_STATUSES,
    ApprovedDiffHunk,
    ApprovedSheetDiff,
    ApprovedSheetPair,
    ApprovedSheetPairs,
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
    CurrentComparison,
    CurrentFindingProposals,
    FindingEvidenceSnapshot,
    FindingSnapshot,
    RunCandidate,
    SavedPageText,
    VersionAnalysisReader,
    VersionClassificationReader,
    VersionComparisonService,
)
from auditmanager.comparison.sheet_links import ApprovedLinkReader, LinkEvent, SheetLinkRepository
from auditmanager.comparison.version_reader import VersionFacts
from auditmanager.comparison.version_section_pair import SuppliedVersionClassification
from auditmanager.comparison.work.errors import (
    HandlerRegistryError,
    UnhandledKindError,
    WorkQueueError,
)
from auditmanager.comparison.work.gates import ClaimGates, default_gates
from auditmanager.comparison.work.model import (
    Completed,
    Failed,
    HandlerFactory,
    ItemAuthority,
    Outcome,
    SpendSettler,
    WorkDependencies,
    WorkHandler,
    WorkItem,
    Yielded,
)
from auditmanager.comparison.work.registry import HandlerRegistry
from auditmanager.comparison.work.repository import (
    CANCEL_REQUESTED,
    CancelResult,
    ComparisonWorkRepository,
    Enqueued,
    WorkRecord,
)
from auditmanager.comparison.work.runner import ComparisonWorkRunner

# `CMP-PROFILE-QUEUE-01`: the `page_profile` work kind (its handler, its factory and the call that enqueues a version).
from auditmanager.comparison.profile_queue.enqueue import (
    enqueue_version_page_profiles,
    page_profile_dedupe_key,
)
from auditmanager.comparison.profile_queue.handler import (
    PageProfileHandler,
    page_profile_handler,
)

#: `CMP-WORK-01` (ADR-0025 decision 4). One tuple of handler factories, each
#: ``Callable[[WorkDependencies], WorkHandler]``: ``build_worker_runtime`` builds one dependency
#: bundle and applies every factory to it, and refuses to start on a duplicate ``kind``. A slice
#: adds its handler by appending its factory here (plan section 4.0 rule 2).
HANDLER_FACTORIES: tuple[HandlerFactory, ...] = (
    page_profile_handler,  # `CMP-PROFILE-QUEUE-01`: kind ``page_profile``
)

#: `CMP-WORK-01`. Called inside the reclaim transaction for each attempt whose lease was lost:
#: ``settle(session, attempt_id) -> bool`` marks the attempt's unfinished model calls ``unknown`` and
#: answers ``True`` if there were any, which ends the item ``spend_unknown`` instead of re-queueing
#: it (ADR-0025 decision 5). ``CMP-SPEND-01`` appends its settler here. None is registered yet.
SPEND_SETTLERS: tuple[SpendSettler, ...] = ()

# `CMP-PROFILE-01`: page profiles (words, vector lines, stamp, ink mask, scan flag, stored previews and tiles).
from auditmanager.comparison.profile.builder import (
    PageBuildReport,
    VersionBuildReport,
    build_version_page_profiles,
)
from auditmanager.comparison.profile.limits import (
    ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION,
    PIXEL_CAP as PAGE_PIXEL_CAP,
    REASON_PAGE_TOO_LARGE,
    REASON_RENDER_FAILED,
    STATUS_NEEDS_REVIEW as PROFILE_NEEDS_REVIEW,
    STATUS_READY as PROFILE_READY,
    STATUS_REFUSED as PROFILE_REFUSED,
    ChildLimits,
    registration_dpi,
)
from auditmanager.comparison.profile.models import (
    Annotation as PageAnnotation,
    InkMask,
    PageProfileData,
    PageProfileRow,
    StampFields,
    VectorLine,
    Word as PageWord,
)
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.profile.runner import (
    ChildResult,
    ChildRunner,
    ChildStartError,
    SubprocessChildRunner,
)
from auditmanager.comparison.profile.tiles import TileRenderer

#: The name the queue can register `build_version_page_profiles` under; its payload is
#: ``{"version_uid": "ver_..."}`` (`CMP-PROFILE-01`). The registry belongs to `CMP-WORK-01`.
PAGE_PROFILE_WORK_KIND = "page_profile"

__all__ = [
    "CANCEL_REQUESTED",
    "CancelResult",
    "ClaimGates",
    "Completed",
    "ComparisonWorkRepository",
    "ComparisonWorkRunner",
    "Enqueued",
    "Failed",
    "HANDLER_FACTORIES",
    "HandlerFactory",
    "HandlerRegistry",
    "HandlerRegistryError",
    "ItemAuthority",
    "Outcome",
    "SPEND_SETTLERS",
    "SpendSettler",
    "UnhandledKindError",
    "WorkDependencies",
    "WorkHandler",
    "WorkItem",
    "WorkQueueError",
    "WorkRecord",
    "Yielded",
    "default_gates",
    "COMPARISON_MODULES_ENV",
    "DEFAULT_MODULES",
    "MODULE_SETS",
    "MODULE_STAGES",
    "MODULE_VERSIONS",
    "enabled_modules",
    "parse_modules",
    "CONFLICT_SUMMARY_EVIDENCE_NOT_SEALED",
    "CONFLICT_SUMMARY_INPUT_EMPTY",
    "CONFLICT_SUMMARY_INPUT_TOO_LARGE",
    "ComparisonSummaryView",
    "DEPENDENCY_SUMMARY_MODEL",
    "GenerateSummaryRequest",
    "LatestSummaryReader",
    "RecordedSummaryModel",
    "SUMMARY_LABEL",
    "StoredSummary",
    "SummaryCostGate",
    "SummaryModel",
    "SummaryOutcome",
    "SummaryReply",
    "SummaryService",
    "SummaryStatementView",
    "SummaryStore",
    "ApproveSheetPairingRequest",
    "ApprovedDiffHunk",
    "ApprovedLinkReader",
    "ApprovedSheetDiff",
    "ApprovedSheetPair",
    "ApprovedSheetPairs",
    "CarriedSourceDecision",
    "CarryoverCandidate",
    "CarryoverOutcome",
    "CarryoverRequest",
    "ComparedVersion",
    "ComparisonIntegrityError",
    "ComparisonRefusal",
    "ComparisonRequest",
    "ComparisonRequestInvalid",
    "CurrentComparison",
    "CurrentFindingProposals",
    "DEFAULT_DIFF_LIMIT",
    "DecisionCarryoverService",
    "DiffHunk",
    "EVIDENCE_NONE",
    "EVIDENCE_SEALED",
    "EVIDENCE_SEAL_CHANGED",
    "EVIDENCE_STATES",
    "EVIDENCE_TEXT_CHANGED",
    "EVIDENCE_TOO_LARGE",
    "FindingComparison",
    "FindingEvidenceSnapshot",
    "FindingProposal",
    "FindingRef",
    "FindingSnapshot",
    "LINK_STATES",
    "LINK_TEXT_CHANGED",
    "LINK_VERIFIED",
    "LinkEvent",
    "MAX_DIFF_LIMIT",
    "MODES",
    "MODE_STAGE",
    "MODE_VERSION",
    "OUTCOME_COMPARED",
    "OUTCOME_REFUSED",
    "PAIRING_CONFLICT_REASONS",
    "PROPOSAL_BASES",
    "PairingOutcome",
    "PROPOSAL_KINDS",
    "REFUSAL_REASONS",
    "RunCandidate",
    "SHEET_STATUSES",
    "SavedPageText",
    "SheetDiff",
    "SheetDiffPage",
    "SheetLinkRepository",
    "SheetPairing",
    "SheetPairingService",
    "SuppliedVersionClassification",
    "VersionAnalysisReader",
    "VersionClassificationReader",
    "VersionComparison",
    "VersionComparisonService",
    "VersionFacts",
    "WithdrawSheetPairingRequest",
    "carryover_candidates",
    "ChildLimits",
    "ChildResult",
    "ChildRunner",
    "ChildStartError",
    "InkMask",
    "PAGE_PIXEL_CAP",
    "PAGE_PROFILE_ALGO_VERSION",
    "PAGE_PROFILE_WORK_KIND",
    "PageProfileHandler",
    "PROFILE_NEEDS_REVIEW",
    "PROFILE_READY",
    "PROFILE_REFUSED",
    "PageAnnotation",
    "PageBuildReport",
    "PageProfileData",
    "PageProfileReader",
    "PageProfileRow",
    "PageWord",
    "REASON_PAGE_TOO_LARGE",
    "REASON_RENDER_FAILED",
    "StampFields",
    "SubprocessChildRunner",
    "TileRenderer",
    "VectorLine",
    "VersionBuildReport",
    "build_version_page_profiles",
    "enqueue_version_page_profiles",
    "page_profile_dedupe_key",
    "page_profile_handler",
    "registration_dpi",
]
