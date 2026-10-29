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
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.ceilings import job_ceiling_micros
from auditmanager.comparison.spend.errors import (
    CallFailed,
    CallLost,
    CallRefused,
    OutcomeUnknown,
    SpendError,
)
from auditmanager.comparison.spend.model import (
    DAY_CEILING_USD,
    JOB_CEILING_USD,
    JOB_KEY as SPEND_JOB_KEY,
    CallEstimate,
    CallRecord,
    CallResult,
    CallRoute,
    Consent,
    SpendPause,
)
from auditmanager.comparison.spend.repository import ComparisonSpendRepository
from auditmanager.comparison.spend.settler import settle_lost_attempt
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

# `CMP-ENGINE-01`: the per-sheet comparison engine (the pair result, its cache, its mask and the `pair_result` work kind).
from auditmanager.comparison.engine import (
    ENGINE_ALGO_VERSION,
    PAIR_RESULT_KIND,
    DecodedMask,
    MaskFormatError,
    PairOutcome,
    PairResultHandler,
    PairResultRepository,
    StoredResult,
    compare_sheet_pair,
    decode_mask,
    encode_mask,
    encode_packed_planes,
    enqueue_pair_result,
    pair_result_dedupe_key,
    pair_result_handler,
    pair_result_payload,
)
from auditmanager.comparison.engine.mask_codec import (
    LAYERS as MASK_LAYERS,
    MASK_FORMAT,
)

# `CMP-MATRIX-01`: the effective matrix of a document set (its service, its work kind, the pairs the series reads).
from auditmanager.comparison.matrix.handler import MatrixBuildHandler, matrix_build_handler
from auditmanager.comparison.matrix.model import PageRef as MatrixPageRef
from auditmanager.comparison.matrix.pairs import AdjacentSheetPairs, SheetPairSpec, SplitSpec, TransitionPairs
from auditmanager.comparison.matrix.service import (
    MATRIX_BUILD_KIND,
    ComparisonMatrixService,
    EditInput as MatrixEditInput,
    matrix_build_dedupe_key,
    read_adjacent_sheet_pairs,
)

# `CMP-SERIES-01`: the series of adjacent transitions (its service, its three work kinds, the follow-up of a prepared set).
from auditmanager.comparison.series import (
    SERIES_AFTER_PREPARATION_KIND,
    SERIES_DRIVE_KIND,
    SERIES_PAIR_KIND,
    ComparisonSeriesService,
    SeriesAfterPreparationHandler,
    SeriesDriveHandler,
    SeriesPairHandler,
    enqueue_series_after_preparation,
    follow_up_dedupe_key,
    series_after_preparation_handler,
    series_drive_handler,
    series_pair_handler,
)

# `CMP-VC-OVERVIEW-01`: the overview of «Проекты и этапы» and the comparison queue summary (two reads, no work kind).
from auditmanager.comparison.overview import ComparisonOverviewService

# `CMP-VC-SPEC-01`: specifications of a version comparison (positions by GOST 21.110, the whole-specification comparison).
from auditmanager.comparison.specification.reader import SpecificationReader
from auditmanager.comparison.specification.service import SpecificationService
from auditmanager.comparison.specification.transition import TransitionRun

#: `CMP-WORK-01` (ADR-0025 decision 4). One tuple of handler factories, each
#: ``Callable[[WorkDependencies], WorkHandler]``: ``build_worker_runtime`` builds one dependency
#: bundle and applies every factory to it, and refuses to start on a duplicate ``kind``. A slice
#: adds its handler by appending its factory here (plan section 4.0 rule 2).
HANDLER_FACTORIES: tuple[HandlerFactory, ...] = (
    page_profile_handler,  # `CMP-PROFILE-QUEUE-01`: kind ``page_profile``
    pair_result_handler,  # `CMP-ENGINE-01`: kind ``pair_result``
    matrix_build_handler,  # `CMP-MATRIX-01`: kind ``matrix_build``
    series_pair_handler,  # `CMP-SERIES-01`: kind ``series_pair``
    series_drive_handler,  # `CMP-SERIES-01`: kind ``series_drive``
    series_after_preparation_handler,  # `CMP-SERIES-01`: kind ``series_after_preparation``
)

#: `CMP-WORK-01`. Called inside the reclaim transaction for each attempt whose lease was lost:
#: ``settle(session, attempt_id) -> bool`` marks the attempt's unfinished model calls ``unknown`` and
#: answers ``True`` if there were any, which ends the item ``spend_unknown`` instead of re-queueing
#: it (ADR-0025 decision 5). `CMP-SPEND-01` registers the settler of the comparison spend journal: the one
#: thing that stops a reclaimed item from being sent a second time.
SPEND_SETTLERS: tuple[SpendSettler, ...] = (settle_lost_attempt,)

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
from auditmanager.comparison.tiles.reader import PairTileReader

#: The name the queue can register `build_version_page_profiles` under; its payload is
#: ``{"version_uid": "ver_..."}`` (`CMP-PROFILE-01`). The registry belongs to `CMP-WORK-01`.
PAGE_PROFILE_WORK_KIND = "page_profile"

__all__ = [
    "ENGINE_ALGO_VERSION",
    "MASK_FORMAT",
    "MASK_LAYERS",
    "DecodedMask",
    "MaskFormatError",
    "PAIR_RESULT_KIND",
    "PairOutcome",
    "PairResultHandler",
    "PairResultRepository",
    "StoredResult",
    "compare_sheet_pair",
    "decode_mask",
    "encode_mask",
    "encode_packed_planes",
    "enqueue_pair_result",
    "pair_result_dedupe_key",
    "pair_result_handler",
    "pair_result_payload",
    "CANCEL_REQUESTED",
    "CallEstimate",
    "CallFailed",
    "CallLost",
    "CallRecord",
    "CallRefused",
    "CallResult",
    "CallRoute",
    "CancelResult",
    "ClaimGates",
    "ComparisonModelCaller",
    "ComparisonSpendRepository",
    "Consent",
    "DAY_CEILING_USD",
    "JOB_CEILING_USD",
    "OutcomeUnknown",
    "SPEND_JOB_KEY",
    "SpendError",
    "SpendPause",
    "job_ceiling_micros",
    "settle_lost_attempt",
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
    "PairTileReader",
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
    "AdjacentSheetPairs",
    "ComparisonMatrixService",
    "MATRIX_BUILD_KIND",
    "MatrixBuildHandler",
    "MatrixEditInput",
    "MatrixPageRef",
    "SheetPairSpec",
    "SplitSpec",
    "TransitionPairs",
    "matrix_build_dedupe_key",
    "matrix_build_handler",
    "read_adjacent_sheet_pairs",
    "ComparisonSeriesService",
    "SERIES_AFTER_PREPARATION_KIND",
    "SERIES_DRIVE_KIND",
    "SERIES_PAIR_KIND",
    "SeriesAfterPreparationHandler",
    "SeriesDriveHandler",
    "SeriesPairHandler",
    "enqueue_series_after_preparation",
    "follow_up_dedupe_key",
    "series_after_preparation_handler",
    "series_drive_handler",
    "series_pair_handler",
    "ComparisonOverviewService",
    "SpecificationReader",
    "SpecificationService",
    "TransitionRun",
]
