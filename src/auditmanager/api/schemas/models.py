"""The ``components.schemas`` of ``contracts/api/v1/openapi.json``, as Pydantic models.

`T-1` makes FastAPI generate the served document, and `W13-CONF`'s conformance gate compares
that document against the frozen contract. **The contract stays the authority**: every class
here is named exactly as its ``components.schemas`` key, and every keyword it emits is the
one the contract writes. Where the two could drift the gate says so on every run; this module
is the side that has to move.

Three spellings in here are deliberate and are the reason the generated document matches:

* **``Field(default=None, json_schema_extra=optional_property)``** for a property the contract
  declares *optional but not nullable* -- ``StartRunRequest.provider_mode``,
  ``Project.document_count``, ``UploadDocumentRequest.display_title`` and the rest.
  Pydantic's ordinary spelling for "may be absent" is ``X | None = None``, which emits a
  ``{"type": "null"}`` branch **and** a ``"default": null`` the contract does not declare.
  Both are semantic: a null branch admits ``{"provider_mode": null}``, which the contract
  refuses, and ``default`` is compared by the gate
  (``test_a_changed_parameter_default_is_caught``). The field's *type* stays the declared
  one, so a present value is still validated against it, and an absent one is ``None`` --
  which is what the previous parser forwarded and what `W13-BASE` section 7 pins across
  baseline cases ``04``, ``05`` and ``05b``.
* **A ``TypeAliasType`` per scalar newtype** -- ``ProjectUid``, ``Sha256``, ``Cursor``, ... --
  because a bare ``Annotated[str, ...]`` is inlined by Pydantic and the contract spells
  these as ``$ref``s into ``components.schemas``. A resolved ``$ref`` is exactly the drift
  `W13-CONF` refuses to normalize away (`N1` resolves component *parameters*, *responses*
  and *headers*, and deliberately not schemas).
* **``extra="forbid"`` on every object**, because every object schema in the contract
  declare ``additionalProperties: false``. There is no object schema here that does not.

Nothing in this module renders a response. The wire bytes are produced by the ``*_body``
functions beside it, which the response baseline pins byte for byte; these models declare
the *document*, and validate the declared request bodies.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import UploadFile
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, WithJsonSchema, model_validator
from typing_extensions import TypeAliasType

__all__ = [
    "DecisionMemoryCase",
    "DecisionMemoryCaseId",
    "DecisionMemoryCasePage",
    "DecisionMemoryCaseSummary",
    "DecisionMemoryContent",
    "DecisionMemoryCountRow",
    "DecisionMemoryCrop",
    "DecisionMemoryDecision",
    "DecisionMemoryEvidence",
    "DecisionMemoryNormRef",
    "DecisionMemoryStatus",
    "DecisionMemoryStatusChange",
    "DecisionMemoryStatusChangeRequest",
    "DecisionMemoryStatusEvent",
    "Account",
    "AccountPage",
    "AuthEvent",
    "AuthEventPage",
    "AuthEventType",
    "AnalysisProfileId",
    "AnalysisProfileList",
    "AnalysisProfileListItem",
    "AnalysisProfileSource",
    "AnalysisProfileSourceFile",
    "AnalysisProfileStatus",
    "AnalysisProfileSummary",
    "ApproveRegistrationRequest",
    "ApproveSheetPairingRequest",
    "ApprovedDiffHunk",
    "ApprovedSheetDiff",
    "ApprovedSheetPair",
    "ApprovedSheetPairs",
    "ComparisonSummary",
    "GenerateComparisonSummaryRequest",
    "GenerateComparisonSummaryResponse",
    "SummaryStatement",
    "ComparisonId",
    "SheetLinkId",
    "SheetPairingEvent",
    "WithdrawSheetPairingRequest",
    "AppendDecisionRequest",
    "AppendDecisionResponse",
    "ClassifyDocumentVersionRequest",
    "CorrectVersionClassificationRequest",
    "BlockGeometry",
    "CorrelationId",
    "CostBasis",
    "CreateProjectRequest",
    "Cursor",
    "DecisionEvent",
    "DecisionEventPage",
    "DecisionRecord",
    "DecisionRecordPage",
    "DecisionEventType",
    "DecisionId",
    "DocumentUid",
    "DocumentVersion",
    "DocumentVersionPage",
    "ErrorCode",
    "ErrorEnvelope",
    "Evidence",
    "Finding",
    "FindingCategory",
    "FindingDetail",
    "FindingObservation",
    "FindingObservationId",
    "FindingPage",
    "FindingUid",
    "IdempotencyKey",
    "InputManifestEntry",
    "ModelCallId",
    "ObservationProvenance",
    "PageInfo",
    "PersonNames",
    "Project",
    "ProjectPage",
    "ProjectSection",
    "ProjectStage",
    "ProjectUid",
    "PromptBundleId",
    "ProviderMode",
    "RegistrationRequest",
    "RegistrationRequestId",
    "RegistrationRequestPage",
    "RegistrationStatus",
    "RegistrationStatusResponse",
    "RejectRegistrationRequest",
    "ResetUserPasswordRequest",
    "Role",
    "ProductVersion",
    "ReleaseNoteKind",
    "ReleaseNoteItem",
    "ReleaseEntry",
    "ReleaseList",
    "MarkReleaseNotesReadRequest",
    "RunId",
    "JobId",
    "RunState",
    "RunExecutor",
    "RunPreset",
    "RunStatus",
    "RunStatusPage",
    "Severity",
    "ExecutionQueueItem",
    "ExecutionQueuePage",
    "ExecutionJournalEntry",
    "ExecutionJournalPage",
    "SetJobPriorityRequest",
    "SetExecutionPausedRequest",
    "ExecutionDispatchStatus",
    "WorkerId",
    "WorkerState",
    "ExecutionWorker",
    "ExecutionWorkerPage",
    "SetWorkerIntakeRequest",
    "NormsSnapshotId",
    "NormRetrievalSetId",
    "NormDocumentId",
    "NormParagraphId",
    "NormSourceAttribution",
    "NormCitationState",
    "NormCitation",
    "NormReferenceCounts",
    "NormReferenceAnchor",
    "NormReferenceItem",
    "NormReferenceUnrecognised",
    "RunNormReferences",
    "NormParagraphKind",
    "NormTextReliability",
    "NormBuildState",
    "NormHighlight",
    "NormFragment",
    "NormSearchHit",
    "NormSearchPage",
    "NormDocument",
    "NormCatalogueEntry",
    "NormCatalogueEntryPage",
    "NormKindCount",
    "NormParagraph",
    "NormParagraphPage",
    "NormSnapshot",
    "NormSnapshotPage",
    "NormSnapshotEvent",
    "NormSnapshotEventPage",
    "SetCurrentNormSnapshotRequest",
    "NormCurrentSnapshot",
    "PortalBlockId",
    "PortalBlockType",
    "PortalGeometryState",
    "PortalCrop",
    "PortalRecognisedText",
    "PortalBlock",
    "PortalBlockPage",
    "SectionReview",
    "SectionReviewOption",
    "SectionSuggestion",
    "Sha256",
    "StageId",
    "StageState",
    "StageStatus",
    "StartRunRequest",
    "RunCostConsent",
    "RunCostEstimateRequest",
    "RunCostEstimate",
    "ReauditRunRequest",
    "StartRunFromStageRequest",
    "SubmitRegistrationRequest",
    "UpdateMyProfileRequest",
    "UpdateUserRequest",
    "UploadDocumentRequest",
    "UploadDocumentVersionRequest",
    "UserUid",
    "Verdict",
    "VersionBlockIndex",
    "VersionClassification",
    "VersionClassificationRevision",
    "ComparedVersion",
    "ComparisonRefusal",
    "DiffHunk",
    "FindingComparison",
    "FindingMatchProposal",
    "FindingRef",
    "SheetDiff",
    "SheetDiffPage",
    "SheetPairing",
    "CarryOverDecisionRequest",
    "CarryOverDecisionResponse",
    "CarryoverCandidate",
    "CarryoverSourceDecision",
    "VersionComparison",
    "VersionUid",
    "PriceListId",
    "PriceListPositionId",
    "VendorListId",
    "PriceListFormat",
    "PriceListField",
    "PriceListRowReason",
    "PriceListCurrencySource",
    "PriceListColumn",
    "PriceListAmbiguousColumn",
    "PriceListRowNote",
    "PriceListReasonCount",
    "PriceListCurrencySourceCount",
    "PriceListParseReport",
    "PriceListRevision",
    "PriceListRevisionList",
    "PriceListPosition",
    "PriceListPositionPage",
    "UploadPriceListRequest",
    "VendorListMode",
    "VendorListScope",
    "VendorListSource",
    "VendorListEntry",
    "VendorListRevision",
    "SectionVendorList",
    "EffectiveVendorLists",
    "SetGlobalVendorListRequest",
    "SetProjectVendorListRequest",
    "SpecificationPriceListRef",
    "SpecificationSkipCounts",
    "SpecificationSkippedLine",
    "SpecificationTable",
    "SpecificationExtractionSummary",
    "SpecificationMatchCounts",
    "SpecificationExclusionCounts",
    "SpecificationCurrencyTotal",
    "SpecificationMatching",
    "SpecificationPricePosition",
    "SpecificationPriceRow",
    "SpecificationRowPage",
    "SpecificationPrices",
    "OptimisationPass",
    "OptimisationPassId",
    "OptimisationPassList",
    "OptimisationProposal",
    "OptimisationProposalId",
    "OptimisationProposalPage",
    "OptimisationProposalType",
    "ProposalAnalogBasis",
    "ProposalDecision",
    "ProposalDecisionCounts",
    "ProposalDecisionId",
    "ProposalDecisionList",
    "ProposalDecisionResult",
    "ProposalDecisionState",
    "ProposalMatchBasis",
    "ProposalPosition",
    "ProposalVerdict",
    "DecideOptimisationProposalRequest",
    "optional_property",
    "ExecutorConnectionId",
    "ExecutorRevisionId",
    "ExecutorSecretId",
    "ExecutorProbeId",
    "ExecutorRunnerTokenId",
    "ExecutorTaskId",
    "ExecutorEnrollmentId",
    "ExecutorAgentInstallId",
    "AgentPackageVersion",
    "ExecutorKind",
    "ExecutorWorkKind",
    "ExecutorApiFlavour",
    "ExecutorTransport",
    "ExecutorSshProfile",
    "ExecutorPullClient",
    "ExecutorBilling",
    "ExecutorSecretPurpose",
    "ExecutorProbeState",
    "ExecutorProbeOutcome",
    "ExecutorIdentityBasis",
    "ExecutorRateCheck",
    "ExecutorPinnedModel",
    "ExecutorRevisionSettings",
    "ReviseExecutorConnectionRequest",
    "ExecutorRevision",
    "ExecutorProbe",
    "ExecutorSecretMetadata",
    "ExecutorConnection",
    "ExecutorConnectionList",
    "ExecutorConnectionDetail",
    "CreateExecutorConnectionRequest",
    "SetExecutorSecretRequest",
    "ExecutorSshKey",
    "ExecutorRoute",
    "ExecutorRouteList",
    "SetExecutorRouteRequest",
    "ExecutorGroupId",
    "ExecutorGroupRevisionId",
    "ExecutorRoutingRuleRevisionId",
    "ExecutorRoutingModeEventId",
    "ExecutorBindingState",
    "ExecutorRoutingMode",
    "ExecutorGroupStrategy",
    "ExecutorGroupMemberIssue",
    "ExecutorRoutingPreviewStatus",
    "ExecutorRoutingPreviewIssue",
    "ExecutorGroupMember",
    "ExecutorGroupRevision",
    "ExecutorGroup",
    "ExecutorGroupList",
    "ExecutorGroupDetail",
    "CreateExecutorGroupRequest",
    "ReviseExecutorGroupRequest",
    "ExecutorGroupMemberStatus",
    "ExecutorGroupCapacity",
    "ExecutorRoutingRule",
    "ExecutorRoutingModeState",
    "ExecutorRoutingRuleList",
    "SetExecutorRoutingRuleRequest",
    "ExecutorRoutingPreviewItem",
    "ExecutorRoutingPreview",
    "ExecutorRoutingMappingEntry",
    "SetExecutorRoutingModeRequest",
    "ExecutorRoutingModeResult",
    "ExecutorGroupPlan",
    "ExecutorBinding",
    "ExecutorOccupancy",
    "ExecutorIntegrationAuthorisation",
    "RunQueueReason",
    "RunWaitCause",
    "RunWaitCell",
    "RunnerCliName",
    "RunnerCliAuthState",
    "RunnerExecutionProfile",
    "RunnerFeature",
    "RunnerCliHealth",
    "ExecutorEnrollmentState",
    "ExecutorAgentInstallAccess",
    "ExecutorAgentInstallState",
    "ExecutorAgentInstallFailure",
    "ExecutorEnrollmentMetadata",
    "IssuedExecutorEnrollment",
    "RedeemExecutorEnrollmentRequest",
    "ReportRunnerHealthRequest",
    "RunnerHealthAck",
    "SetExecutorIntegrationAuthorisationRequest",
    "CreateExecutorAgentInstallRequest",
    "ExecutorAgentInstall",
    "ConfirmExecutorAgentInstallHostKeyRequest",
    "PresetId",
    "PresetRevisionId",
    "AnalysisPresetState",
    "AnalysisPreset",
    "AnalysisPresetList",
    "SaveAnalysisPresetRequest",
    "ComparisonModules",
    "VersionUploadKind",
    "ComparisonUploadState",
    "ComparisonUploadFileState",
    "ComparisonUploadSetState",
    "ComparisonProposalWarning",
    "ComparisonUploadFileDeclaration",
    "CreateComparisonUploadRequest",
    "ComparisonUploadFile",
    "ComparisonUpload",
    "ComparisonUploadPage",
    "ComparisonUploadPartReceipt",
    "ComparisonProposalFile",
    "ComparisonProposalSet",
    "ComparisonUploadProposal",
    "ConfirmedComparisonFile",
    "ConfirmComparisonUploadSetRequest",
    "ComparisonVersionOrderSource",
    "ComparisonVersionOrder",
    "ComparisonVersionOrderList",
    "AppendComparisonVersionOrderRequest",
    "PageProfileStatus",
    "PageStamp",
    "VersionPageProfile",
    "VersionPageProfilePage",
    "ComparisonUploadId",
    "ComparisonUploadFileId",
    "ComparisonUploadSetId",
    "ComparisonVersionOrderId",
    "ComparisonPageProfileId",
    "ExecutorTaskState",
    "RunnerTokenMetadata",
    "IssueRunnerTokenRequest",
    "IssuedRunnerToken",
    "ClaimExecutorTaskRequest",
    "ClaimedExecutorTask",
    "ExtendedExecutorTaskClaim",
    "SubmitExecutorTaskAnswerRequest",
    "FailExecutorTaskRequest",
    "ExecutorTaskAck",
    "Assignment",
    "AssignmentDetail",
    "AssignmentEvent",
    "AssignmentEventKind",
    "AssignmentPage",
    "AssignmentStatus",
    "AssignmentStatusCount",
    "AssignmentTransitionKind",
    "AssignmentUid",
    "CreateAssignmentRequest",
    "TransitionAssignmentRequest",
    "ComparisonMatrixId",
    "ComparisonMatrixEditId",
    "ComparisonAiLinkId",
    "ComparisonSeriesId",
    "ComparisonTransitionId",
    "ComparisonSheetPairId",
    "ComparisonSheetPairResultId",
    "ComparisonPageRef",
    "ComparisonMatrixRevision",
    "ComparisonMatrixState",
    "ComparisonMatrixStaleReason",
    "ComparisonCellState",
    "ComparisonCellConfidence",
    "ComparisonCellFlag",
    "ComparisonMatrixCandidate",
    "ComparisonMatrixCell",
    "ComparisonMatrixRow",
    "ComparisonMatrixLabelSource",
    "ComparisonMatrixColumn",
    "ComparisonMatrixProgress",
    "ComparisonMatrixCounts",
    "ComparisonMatrix",
    "ComparisonMatrixPreparation",
    "ComparisonMatrixEditKind",
    "ComparisonMatrixEditInputKind",
    "ComparisonMatrixEditSource",
    "ComparisonMatrixEditStatus",
    "ComparisonMatrixEditInput",
    "ApplyComparisonMatrixEditsRequest",
    "UndoComparisonMatrixEditRequest",
    "ComparisonEditProvenance",
    "ComparisonMatrixEdit",
    "ComparisonMatrixEditList",
    "ComparisonAiLinkAnsweredState",
    "ComparisonAiLinkStatus",
    "ComparisonAiLink",
    "ComparisonAiLinkList",
    "ComparisonSeriesState",
    "ComparisonTransitionState",
    "ComparisonVerdictCode",
    "ComparisonTransitionSummary",
    "ComparisonTransition",
    "ComparisonSeriesStaleReason",
    "ComparisonSeries",
    "ComparisonSeriesPage",
    "StartComparisonSeriesRequest",
    "ComparisonSheetStatus",
    "ComparisonSheetPairState",
    "ComparisonChannelState",
    "ComparisonChannel",
    "ComparisonChannels",
    "ComparisonLayer",
    "ComparisonBox",
    "ComparisonDifference",
    "ComparisonNumberChange",
    "ComparisonTextChange",
    "ComparisonNoteChange",
    "ComparisonServiceNote",
    "ComparisonHowCompared",
    "ComparisonPermitState",
    "ComparisonPermitItem",
    "ComparisonPermit",
    "ComparisonPartRole",
    "ComparisonPartsCoverage",
    "ComparisonRasterSize",
    "ComparisonPairPage",
    "ComparisonCanvas",
    "ComparisonSheetPair",
    "ComparisonSheetPairPage",
    "ComparisonPairTileMode",
    "ComparisonStepId",
    "ComparisonStepState",
    "ComparisonStepCounts",
    "ComparisonOverviewStep",
    "ComparisonOverviewSet",
    "ComparisonOverviewTotals",
    "ComparisonOverviewCounters",
    "ComparisonOverviewUpload",
    "ComparisonOverview",
    "ComparisonQueueCounts",
    "ComparisonQueueModule",
    "ComparisonQueueKind",
    "ComparisonQueueSummary",
    "ComparisonAiJobId",
    "ComparisonAiPairQuestionId",
    "ComparisonSheetDescriptionId",
    "ComparisonSpecExtractionId",
    "ComparisonSpecComparisonId",
    "ComparisonReportId",
    "ComparisonLaunchEntryId",
    "ComparisonAiMethod",
    "ComparisonAiJobState",
    "ComparisonAiPauseReason",
    "ComparisonAiCeiling",
    "ComparisonAiRoute",
    "ComparisonAiEstimate",
    "ComparisonAiConsent",
    "StartComparisonAiJobRequest",
    "StartComparisonAiSheetChangesRequest",
    "ResumeComparisonAiJobRequest",
    "ComparisonAiSpend",
    "ComparisonAiJobCounts",
    "ComparisonAiJob",
    "ComparisonAiPairQuestionKind",
    "ComparisonAiPairDecision",
    "ComparisonAiConfidence",
    "ComparisonAiPairCounts",
    "ComparisonAiPairCheck",
    "ComparisonAiPairHint",
    "ComparisonAiPairHintPage",
    "ComparisonAiSheetState",
    "ComparisonAiTier",
    "ComparisonAiCertainty",
    "ComparisonAiSide",
    "ComparisonAiExcludeReason",
    "ComparisonAiChange",
    "ComparisonAiUnresolved",
    "ComparisonAiDeclaredItem",
    "ComparisonAiExcluded",
    "ComparisonAiCoverage",
    "ComparisonAiDiagnostics",
    "ComparisonSheetDescriptionSource",
    "ComparisonSheetDescription",
    "ComparisonSheetDescriptionRevision",
    "ComparisonSheetDescriptionHistory",
    "ComparisonAiTransitionProgress",
    "ComparisonAiSheetChanges",
    "ComparisonReviewSheetKind",
    "ComparisonReviewSheet",
    "ComparisonReviewSheetPage",
    "ComparisonAiQueueItem",
    "ComparisonAiQueue",
    "ComparisonSpecMethod",
    "ComparisonSpecState",
    "ComparisonSpecPhase",
    "ComparisonSpecChangeKind",
    "ComparisonSpecPosition",
    "ComparisonSpecFieldChange",
    "ComparisonSpecChange",
    "ComparisonSpecTotals",
    "ComparisonSpecCoverage",
    "ComparisonSpecification",
    "ComparisonSpecificationPage",
    "ComparisonSpecChangePage",
    "ComparisonSpecPage",
    "ComparisonSheetPairSpecPositions",
    "ComparisonLaunchEntryState",
    "ComparisonLaunchQueueState",
    "ComparisonLaunchEntry",
    "ComparisonLaunchQueueCounts",
    "ComparisonLaunchQueue",
    "ComparisonLaunchItem",
    "EnqueueComparisonLaunchRequest",
    "ComparisonReportKind",
    "ComparisonReportSource",
    "ComparisonReportState",
    "ComparisonReportStage",
    "ComparisonReportUnitMark",
    "ComparisonReportFacts",
    "ComparisonReportPart",
    "ComparisonReportArtifactKind",
    "ComparisonReportArtifact",
    "ComparisonReport",
    "ComparisonReportPage",
    "CreateComparisonReportRequest",
    "PrepareComparisonClientReportRequest",
    "CreateExecutorHostAgentInstallRequest",
    "ExecutorHost",
    "ExecutorHostDetails",
    "ExecutorHostId",
    "ExecutorHostList",
    "ExecutorHostModel",
    "ExecutorHostModelStatus",
    "ExecutorHostProviderDetail",
    "ExecutorHostSlotUse",
    "ExecutorHostSlots",
    "ExecutorHostState",
    "ExecutorHostTask",
    "ExecutorModelAccess",
    "ExecutorProvider",
    "ExecutorTaskUsage",
    "IssueExecutorHostEnrollmentRequest",
    "ModelCatalogue",
    "ModelCatalogueEntry",
    "ModelEffort",
    "ModelProbeState",
    "ModelUnavailableReason",
    "ProviderAuthState",
    "ReviseStageModelLayoutRequest",
    "RunCostModelLine",
    "RunStartReadiness",
    "RunnerKeyFileReport",
    "RunStartReadinessCell",
    "RunStartRoute",
    "RunnerCatalogueEntry",
    "RunnerProviderModelState",
    "RunnerProviderReport",
    "SetExecutorHostEnabledRequest",
    "SetExecutorHostSlotsRequest",
    "SetStageModelLayoutEnabledRequest",
    "StageCellKey",
    "StageCellRole",
    "ComparisonLayoutKind",
    "StageComparisonCell",
    "StageLayoutCell",
    "StageLayoutRevision",
    "StageLayoutRevisionId",
    "StageLayoutSwitchEvent",
    "StageModelKit",
    "StageModelLayout",
    "StageRowKey",
    "RunStage",
    "RunStageCell",
    "RunStageChip",
    "RunStageFacts",
    "RunStagePlanSource",
    "RunStageState",
    "RunStages",
]


def optional_property(schema: dict[str, Any]) -> None:
    """Drop the ``default`` Pydantic emits for a field that merely may be absent.

    A callable ``json_schema_extra`` is handed the generated property schema to mutate. The
    contract declares no ``default`` on any property, and the conformance gate compares
    ``default``, so emitting one would be a difference -- and a wrong one: ``default: null``
    says the server substitutes ``null``, which is not what an absent property means here.

    **Measured, and it is belt and braces rather than load-bearing.** Replacing this body
    with ``pass`` changes the generated document by **nothing**: with
    ``separate_input_output_schemas=False`` FastAPI generates one schema per model in
    *serialization* mode, and Pydantic omits ``default`` there. ``model_json_schema()``
    alone -- validation mode -- does emit it, which is what this was written against.

    It is kept, and said out loud rather than quietly deleted, because the property it
    declares is the contract's and the mode FastAPI happens to choose is not.
    ``test_no_schema_property_declares_a_default`` pins the property itself, which is the
    thing worth guarding; this function is the declaration of intent beside it. The half of
    the spelling that **is** load-bearing is the type: ``ProviderMode`` with
    ``default=None`` rather than ``ProviderMode | None``, which the sweep's ``M16``
    reddens at two dotted locations.
    """
    schema.pop("default", None)


#: ``#/components/schemas/ErrorEnvelope.properties.details``, verbatim.
#:
#: Pydantic has no spelling for ``maxProperties`` or ``propertyNames``, and this schema is
#: not a validation surface in this application in any case: the envelope is built by
#: :mod:`auditmanager.shared.errors` and screened by its own detail-key rules, which is
#: where that bound is actually enforced. The declaration is written out so the *document*
#: still carries the contract's constraint rather than a looser one.
_DETAILS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "maxProperties": 16,
    "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,63}$"},
    "additionalProperties": {
        "type": ["string", "number", "integer", "boolean", "null"],
        "maxLength": 256,
    },
}

#: ``#/components/schemas/BlockGeometry.properties.bbox``, verbatim. A plain nested
#: ``BaseModel`` would make FastAPI mint a fourth top-level ``components.schemas`` entry
#: (``Bbox``) that the frozen contract does not declare, the same drift ``_DETAILS_SCHEMA``
#: exists to avoid one property up. The bbox is inline in the contract and stays inline here.
_BBOX_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["x0", "y0", "x1", "y1"],
    "properties": {
        "x0": {"type": "number"},
        "y0": {"type": "number"},
        "x1": {"type": "number"},
        "y1": {"type": "number"},
    },
}

#: ``{"type": "string", "format": "binary"}`` -- how the contract spells an opaque byte
#: payload, in ``UploadDocumentRequest.file`` and in the two binary response bodies.
#: FastAPI's ``UploadFile`` generates OpenAPI 3.1's other spelling for the same thing,
#: ``{"type": "string", "contentMediaType": "application/octet-stream"}``, which is a
#: *different media type* as well as a different keyword. The contract is the authority and
#: this is what it says.
_BINARY_STRING: dict[str, Any] = {"type": "string", "format": "binary"}

#: Every identity in this contract is a prefixed Crockford base32 ULID of 26 characters.
_ULID = "[0-9A-HJKMNP-TV-Z]{26}"


class _Object(BaseModel):
    """Every object schema in this contract is closed."""

    model_config = ConfigDict(extra="forbid")


# --- the scalar newtypes -----------------------------------------------------------
#
# ``TypeAliasType`` and not ``RootModel``. Both give the contract's ``$ref`` into
# ``components.schemas`` -- which is what these are, since a resolved ``$ref`` is exactly
# the drift `W13-CONF` refuses to normalize away (`N1` resolves component *parameters*,
# *responses* and *headers*, and deliberately not schemas). Only the alias is also a
# **scalar** to FastAPI, so the same declaration serves ``Path``, ``Query`` and ``Header``
# parameters: a ``RootModel`` in a path parameter is an outright
# ``AssertionError: Path params must be of one of the supported types`` at import, and
# spelling the constraint inline instead would put a second copy of every pattern in the
# document beside the one the ``$ref`` names.


ProjectUid = TypeAliasType(
    "ProjectUid", Annotated[str, Field(pattern=rf"^prj_{_ULID}$")]
)
DocumentUid = TypeAliasType(
    "DocumentUid", Annotated[str, Field(pattern=rf"^doc_{_ULID}$")]
)
VersionUid = TypeAliasType(
    "VersionUid", Annotated[str, Field(pattern=rf"^ver_{_ULID}$")]
)
RunId = TypeAliasType("RunId", Annotated[str, Field(pattern=rf"^run_{_ULID}$")])
JobId = TypeAliasType("JobId", Annotated[str, Field(pattern=rf"^job_{_ULID}$")])
#: `W54-SEAL-01`. One registered worker process (``worker_id``, ``wrk``), migration ``0019``.
WorkerId = TypeAliasType("WorkerId", Annotated[str, Field(pattern=rf"^wrk_{_ULID}$")])
#: `EXEC-SEAL-01`. The executor connections' public identities (migration ``0030``).
ExecutorConnectionId = TypeAliasType(
    "ExecutorConnectionId", Annotated[str, Field(pattern=rf"^exc_{_ULID}$")]
)
ExecutorRevisionId = TypeAliasType(
    "ExecutorRevisionId", Annotated[str, Field(pattern=rf"^excr_{_ULID}$")]
)
#: `ANALYSIS-PRESETS-01`. A preset and each of its revisions are identified by the audit event
#: written with them (``evt``, migration ``0037``): the first revision's id is the preset's.
PresetId = TypeAliasType("PresetId", Annotated[str, Field(pattern=rf"^evt_{_ULID}$")])
PresetRevisionId = TypeAliasType(
    "PresetRevisionId", Annotated[str, Field(pattern=rf"^evt_{_ULID}$")]
)
ExecutorSecretId = TypeAliasType(
    "ExecutorSecretId", Annotated[str, Field(pattern=rf"^exs_{_ULID}$")]
)
ExecutorProbeId = TypeAliasType(
    "ExecutorProbeId", Annotated[str, Field(pattern=rf"^epb_{_ULID}$")]
)
#: `EXEC-PULL-01`. A runner token of a ``pull`` connection and a task a runner takes
#: (migration ``0031``).
ExecutorRunnerTokenId = TypeAliasType(
    "ExecutorRunnerTokenId", Annotated[str, Field(pattern=rf"^ern_{_ULID}$")]
)
ExecutorTaskId = TypeAliasType(
    "ExecutorTaskId", Annotated[str, Field(pattern=rf"^ext_{_ULID}$")]
)
#: `EXEC2-SEAL-1` (ADR-0026, migration ``0046``). An enrollment grant of the universal agent, an install
#: session of it over SSH, and the version of the agent package the image holds (``major.minor.patch``).
ExecutorEnrollmentId = TypeAliasType(
    "ExecutorEnrollmentId", Annotated[str, Field(pattern=rf"^exen_{_ULID}$")]
)
ExecutorAgentInstallId = TypeAliasType(
    "ExecutorAgentInstallId", Annotated[str, Field(pattern=rf"^exai_{_ULID}$")]
)
AgentPackageVersion = TypeAliasType(
    "AgentPackageVersion",
    Annotated[str, Field(pattern=r"^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}$")],
)
#: `EXEC2-SEAL-2` (ADR-0026 decisions 10 and 11, migration ``0047``). An executor group, one immutable revision of it, one
#: revision of a work kind's routing rule and one change of the routing mode.
ExecutorGroupId = TypeAliasType(
    "ExecutorGroupId", Annotated[str, Field(pattern=rf"^exg_{_ULID}$")]
)
ExecutorGroupRevisionId = TypeAliasType(
    "ExecutorGroupRevisionId", Annotated[str, Field(pattern=rf"^exgr_{_ULID}$")]
)
ExecutorRoutingRuleRevisionId = TypeAliasType(
    "ExecutorRoutingRuleRevisionId", Annotated[str, Field(pattern=rf"^exrr_{_ULID}$")]
)
ExecutorRoutingModeEventId = TypeAliasType(
    "ExecutorRoutingModeEventId", Annotated[str, Field(pattern=rf"^exrm_{_ULID}$")]
)
#: `HOSTS-SEAL-1` (ADR-0028, migration ``0062``). An executor host -- a server with its one agent process and one host token -- and
#: one revision of the stage layout (the models of the analysis stages), and the key of one cell of a plan (`row:role`).
ExecutorHostId = TypeAliasType(
    "ExecutorHostId", Annotated[str, Field(pattern=rf"^exh_{_ULID}$")]
)
StageLayoutRevisionId = TypeAliasType(
    "StageLayoutRevisionId", Annotated[str, Field(pattern=rf"^slr_{_ULID}$")]
)
StageCellKey = TypeAliasType(
    "StageCellKey", Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}:(main|leg1|leg2|judge)$")]
)
#: `W55A-SEAL-01`. The normative corpus's three public identities (`NORM-Q07`), declared in
#: ``contracts/domain/v1/identifiers.json`` since `0012_norms_corpus`, cross the wire.
NormsSnapshotId = TypeAliasType(
    "NormsSnapshotId", Annotated[str, Field(pattern=rf"^ns_{_ULID}$")]
)
NormRetrievalSetId = TypeAliasType(
    "NormRetrievalSetId", Annotated[str, Field(pattern=rf"^nrs_{_ULID}$")]
)
NormDocumentId = TypeAliasType(
    "NormDocumentId", Annotated[str, Field(pattern=rf"^ndoc_{_ULID}$")]
)
NormParagraphId = TypeAliasType(
    "NormParagraphId", Annotated[str, Field(pattern=rf"^npar_{_ULID}$")]
)
#: `W55B-SEAL-01`. An **external** identifier: minted by the portal that produced a bundle and
#: carried verbatim from its block list, 32 lowercase hexadecimal digits after ``blk_``. Not a
#: ULID identity of this product, never generated here, and addressed only under a version
#: (``contracts/domain/v1/identifiers.json``, ``external_identifiers``).
PortalBlockId = TypeAliasType(
    "PortalBlockId", Annotated[str, Field(pattern=r"^blk_[0-9a-f]{32}$")]
)
FindingUid = TypeAliasType(
    "FindingUid", Annotated[str, Field(pattern=rf"^fnd_{_ULID}$")]
)
FindingObservationId = TypeAliasType(
    "FindingObservationId", Annotated[str, Field(pattern=rf"^fobs_{_ULID}$")]
)
DecisionId = TypeAliasType(
    "DecisionId", Annotated[str, Field(pattern=rf"^dec_{_ULID}$")]
)
#: `COMPARE-PERSISTED-SUMMARY-01`. A comparison (one ordered pair of versions of one set) and one
#: approved sheet link; both declared in ``contracts/domain/v1/identifiers.json`` and allocated
#: from migration ``0035``.
ComparisonId = TypeAliasType(
    "ComparisonId", Annotated[str, Field(pattern=rf"^cmp_{_ULID}$")]
)
SheetLinkId = TypeAliasType(
    "SheetLinkId", Annotated[str, Field(pattern=rf"^sln_{_ULID}$")]
)
AnalysisProfileId = TypeAliasType(
    "AnalysisProfileId", Annotated[str, Field(pattern=rf"^ap_{_ULID}$")]
)
PromptBundleId = TypeAliasType(
    "PromptBundleId", Annotated[str, Field(pattern=rf"^pb_{_ULID}$")]
)
ModelCallId = TypeAliasType(
    "ModelCallId", Annotated[str, Field(pattern=rf"^mc_{_ULID}$")]
)
#: `W49-SEAL-01`. The account and the registration request crossed the wire, so their
#: identities entered ``contracts/domain/v1/identifiers.json`` and are spelled here like
#: every other one.
UserUid = TypeAliasType("UserUid", Annotated[str, Field(pattern=rf"^usr_{_ULID}$")])
RegistrationRequestId = TypeAliasType(
    "RegistrationRequestId", Annotated[str, Field(pattern=rf"^reg_{_ULID}$")]
)
CorrelationId = TypeAliasType(
    "CorrelationId",
    Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", min_length=1, max_length=128),
    ],
)
IdempotencyKey = TypeAliasType(
    "IdempotencyKey",
    Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", min_length=1, max_length=128),
    ],
)
Sha256 = TypeAliasType("Sha256", Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")])
Cursor = TypeAliasType("Cursor", Annotated[str, Field(min_length=1, max_length=512)])


# --- the closed enumerations -------------------------------------------------------


class ErrorCode(str, enum.Enum):
    """Exactly the key set of ``contracts/domain/v1/error-codes.json``.

    Twenty-seven codes since `BETA-CONTRACT-SEAL-01` added ``version_classification_required``
    and ``section_profile_unavailable`` (`D-179`); the twenty-fifth came with `W56A-SEAL-01`, which
    added ``model_identity_mismatch``; the
    twenty-third, ``rate_limited``, came with `W49-SEAL-01` and only the edge in
    front of ``/api/v1`` answers it; the twenty-second was ``staged_upload_lost``, added by
    `W20-CODE` under owner ruling `R-8`, settling `D-18`, and the twenty-first
    ``dependency_credential_refused``, added at `e6d0a6a` under `R-3`. The catalog is the
    authority;
    ``tests/contract/shared_kernel/test_error_kernel.py`` refuses a disagreement at import.
    """

    VALIDATION_FAILED = "validation_failed"
    NOT_FOUND = "not_found"
    AUTHENTICATION_REQUIRED = "authentication_required"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    STATE_TRANSITION_NOT_ALLOWED = "state_transition_not_allowed"
    IDEMPOTENCY_KEY_REUSE = "idempotency_key_reuse"
    IDEMPOTENCY_KEY_IN_PROGRESS = "idempotency_key_in_progress"
    IDEMPOTENCY_KEY_STALE = "idempotency_key_stale"
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    STORAGE_INTEGRITY_ERROR = "storage_integrity_error"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    DEPENDENCY_CREDENTIAL_REFUSED = "dependency_credential_refused"
    STAGED_UPLOAD_LOST = "staged_upload_lost"
    REQUIRED_NORM_UNAVAILABLE = "required_norm_unavailable"
    VERSION_CLASSIFICATION_REQUIRED = "version_classification_required"
    SECTION_PROFILE_UNAVAILABLE = "section_profile_unavailable"
    ANALYSIS_INPUT_INVALID = "analysis_input_invalid"
    ANALYSIS_FAILED = "analysis_failed"
    PARTIAL_RESULT_NOT_PUBLISHABLE = "partial_result_not_publishable"
    COST_BUDGET_EXCEEDED = "cost_budget_exceeded"
    ANALYSIS_INPUT_BUDGET_EXCEEDED = "analysis_input_budget_exceeded"
    MODEL_IDENTITY_MISMATCH = "model_identity_mismatch"
    STALE_ATTEMPT = "stale_attempt"
    EXECUTION_TOKEN_INVALID = "execution_token_invalid"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"


class RunState(str, enum.Enum):
    """The success terminal is ``published``. There is deliberately no ``succeeded``."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    VALIDATING = "validating"
    PUBLISHED = "published"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageId(str, enum.Enum):
    SOURCE_PREPARATION = "source_preparation"
    PAGE_GEOMETRY_EXTRACTION = "page_geometry_extraction"
    DOCUMENT_CONTEXT_BUILD = "document_context_build"
    TEXT_ANALYSIS = "text_analysis"
    BLOCK_ANALYSIS = "block_analysis"
    FINDING_MERGE = "finding_merge"
    FINDING_REVIEW = "finding_review"
    FINDING_CORRECTION = "finding_correction"
    NORM_VERIFICATION = "norm_verification"


class ProviderMode(str, enum.Enum):
    LIVE = "live"
    RECORDED = "recorded"


class CostBasis(str, enum.Enum):
    """How well a published cost figure is known. `D-21`.

    ``measured`` means every provider call the figure sums reported its own cost.
    ``estimated`` means at least one did not, so the total is derived. ``unmetered``
    (`EXEC-SEAL-01`, `R-143f`) means a call ran on a connection that has no per-call cost
    (a subscription session): the figure is absent, never a zero. The value is an
    aggregate over every contributing call and never the last one's basis -- see
    ``auditmanager.runs.repository.RunCost`` and `DEBT_REGISTER.md` `D-15`.
    """

    MEASURED = "measured"
    ESTIMATED = "estimated"
    UNMETERED = "unmetered"


class FindingCategory(str, enum.Enum):
    INTERNAL_CONTRADICTION = "internal_contradiction"
    EXPLICIT_PLACEHOLDER = "explicit_placeholder"
    DIMENSIONS = "dimensions"
    LAYOUT = "layout"
    FACADE = "facade"
    ROOF = "roof"
    DOCUMENTATION = "documentation"
    EVACUATION = "evacuation"
    FIRE_SAFETY = "fire_safety"
    ACCESSIBILITY = "accessibility"
    INSULATION = "insulation"
    SOUND = "sound"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    ECONOMIC = "economic"
    OPERATIONAL = "operational"
    RECOMMENDATION = "recommendation"
    CHECK_ADJACENT = "check_adjacent"


class Verdict(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class DecisionEventType(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    COMMENT = "comment"
    REVOKE = "revoke"


class ProjectSection(str, enum.Enum):
    """The fifteen project sections: legacy's fourteen (`D-56`, `R-40`) and ``PS``.

    ``backend/app/pipeline/stages/prepare/task_builder.py:1362`` names the first fourteen;
    ``db/migrations/versions/20260925_0011_document_section.py`` keeps them as the historical
    ``document.section`` CHECK. `W59-SECTION-SEAL-01` adds ``PS`` (the explanatory note,
    distinct from ``PB``, fire safety) and ``0024_version_classification`` widens that CHECK
    and declares the version classification over the same fifteen;
    ``tests/contract/domain_p02/test_project_section_catalog.py`` keeps the copies in step.
    A document or version with no section is not a sixteenth member of this enum -- the
    property is absent, which is a different, equally real fact.
    """

    AR = "AR"
    AI = "AI"
    KM = "KM"
    KJ = "KJ"
    OV = "OV"
    EOM = "EOM"
    VK = "VK"
    PT = "PT"
    PB = "PB"
    SS = "SS"
    ITP = "ITP"
    GP = "GP"
    TX = "TX"
    POS = "POS"
    PS = "PS"


class ProjectStage(str, enum.Enum):
    """`W59-SECTION-SEAL-01`. The explicit project stage of one version.

    ``P`` (design documentation) or ``R`` (working documentation). Bound to the version, never
    inferred from a file name, and never the analysis ``stage_id``, which is why the property
    that carries it is named ``project_stage``.
    """

    P = "P"
    R = "R"


class Role(str, enum.Enum):
    """`R-55`, `R-60`. The closed role vocabulary; an account holds a set of these."""

    EXPERT = "expert"
    ADMIN = "admin"
    VIEWER = "viewer"


class RegistrationStatus(str, enum.Enum):
    """The ``registration_request`` machine's states (``state-machines.json``)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# --- the shared envelopes ----------------------------------------------------------


class PageInfo(_Object):
    next_cursor: Cursor | None


class ErrorEnvelope(_Object):
    """The one failure shape. Rendered by ``envelope_response`` and by nothing else."""

    contract_version: Literal["1.49.0"]
    error_code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=512)]
    correlation_id: CorrelationId
    retryable: bool
    details: Annotated[
        dict[str, str | float | int | bool | None] | None,
        WithJsonSchema(_DETAILS_SCHEMA),
    ] = Field(default=None, json_schema_extra=optional_property)


# --- projects ----------------------------------------------------------------------


class CreateProjectRequest(_Object):
    name: Annotated[str, Field(min_length=1, max_length=200)]


class DocumentAuditCounts(_Object):
    """Documents by audit state: the counters of a project or of a section (`UI-PARITY-P0B`).

    Every figure counts documents by their **current version only** (`R-150p`) and reads that version's
    **result run**: its latest run in state `published` or `partial`, ordered by `(created_at, run_id)` as
    `listRuns` orders them. A newer run still in flight does not displace it, and a `failed` or `cancelled`
    run is not a result (`R-150r`). Optimisation proposals are not part of any state (`R-150u`).

    A document is in exactly one of four states, so `document_count` is `not_run + clean + awaiting_decision
    + checked`: `not_run` has no result run; `clean` has a result run with no published finding (a state of its
    own, neither checked nor awaiting, `R-150n`); `awaiting_decision` has a result run with at least one
    finding whose current verdict is undecided (`pending` or `needs_manual_review`); `checked` has a result
    run and every finding decided. `partial` is not a fifth state: it counts the documents, in any of the
    four, whose result run is `partial` (`R-150s`).

    Two figures are derived and named for what they mean (`R-150o`). `awaiting_decision` is the red badge
    «ждут решения»: documents with a result and undecided findings. `no_expert_decision` is `not_run +
    awaiting_decision`, the original's column «Нет решений эксперта»: everything not closed, documents never
    run included, but not `clean`.
    """

    document_count: Annotated[int, Field(ge=0)]
    not_run: Annotated[int, Field(ge=0)]
    clean: Annotated[int, Field(ge=0)]
    awaiting_decision: Annotated[int, Field(ge=0)]
    checked: Annotated[int, Field(ge=0)]
    partial: Annotated[int, Field(ge=0)]
    no_expert_decision: Annotated[int, Field(ge=0)]


class Project(_Object):
    project_uid: ProjectUid
    name: Annotated[str, Field(min_length=1, max_length=200)]
    created_at: datetime
    document_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: Present on a `listProjects` item, absent from `createProject`'s answer (the same reason `document_count`
    #: is optional): that path reads no documents and claims no count.
    audit_counts: DocumentAuditCounts = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class ProjectPage(_Object):
    items: list[Project]
    page: PageInfo


# --- documents ---------------------------------------------------------------------


class UploadDocumentRequest(_Object):
    """The multipart body. ``file`` is ``format: binary``; ``FastAPI.UploadFile`` emits that.

    The ``encoding.file.contentType: application/pdf`` the contract declares beside this
    schema is **not** generated by FastAPI and is restored with ``openapi_extra`` on the
    operation -- `W13-CONF` measured its absence and
    ``test_a_dropped_multipart_encoding_is_caught`` is the case that keeps it restored.
    """

    file: Annotated[UploadFile, WithJsonSchema(_BINARY_STRING)]
    display_title: Annotated[str, Field(min_length=1, max_length=400)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: `R-40`. Optional, like ``display_title`` beside it and for the same reason: a
    #: caller that does not yet know which of the fifteen sections a document belongs
    #: in gets a document with none, not a refused upload. See
    #: ``db/migrations/versions/20260925_0011_document_section.py``.
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class UploadDocumentVersionRequest(_Object):
    """`W59-VERSION-UPLOAD-01`. The multipart body of ``uploadDocumentVersion``: the bundle only.

    A further version takes no title and no section, so neither is declared; closed like
    every object here, an undeclared part is refused rather than ignored. The ``file`` part's
    ``encoding`` is restored with ``openapi_extra``, as for :class:`UploadDocumentRequest`.
    """

    file: Annotated[UploadFile, WithJsonSchema(_BINARY_STRING)]


class InputManifestEntry(_Object):
    role: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")]
    sha256: Sha256
    size_bytes: Annotated[int, Field(ge=0)]
    media_type: str


class ClassifyDocumentVersionRequest(_Object):
    """`W59-SECTION-SEAL-01`. An expert's explicit stage and section for one version."""

    project_stage: ProjectStage
    section_code: ProjectSection


class CorrectVersionClassificationRequest(_Object):
    """`CLASSIFICATION-CORRECTION-01`. An expert's correction of one version's classification.

    The full target pair, why, and the revision the caller was looking at
    (``expected_revision``): the optimistic-concurrency token that also makes an exact retry
    safe. At least one of the two values must differ from the current classification.
    """

    project_stage: ProjectStage
    section_code: ProjectSection
    reason: Annotated[str, Field(min_length=1, max_length=2000)]
    expected_revision: Annotated[int, Field(ge=1)]


class VersionClassification(_Object):
    """`W59-SECTION-SEAL-01`. The persisted, expert-confirmed classification of one version.

    The original confirmation is stored once (``0024_version_classification``) and never
    changed. `CLASSIFICATION-CORRECTION-01` (``0028_classification_corrections``): an expert
    may append corrections, each a numbered ``revision`` (1 is the original); this is the
    latest revision, or, in the answer to a correction retried after someone corrected again,
    the revision that request created. ``confirmed_by_user_uid`` and ``confirmed_at`` are those
    of **that revision** -- who stands behind these values.
    """

    version_uid: VersionUid
    project_stage: ProjectStage
    section_code: ProjectSection
    confirmed_by_user_uid: UserUid
    confirmed_at: datetime
    revision: Annotated[int, Field(ge=1)]


class VersionClassificationRevision(_Object):
    """`CLASSIFICATION-CORRECTION-01`. One entry of a version's classification history.

    Revision 1 is the original expert confirmation (``reason`` is ``null``); revisions 2..
    are the corrections, each with the expert who made it, when, and why. Never changed.
    """

    revision: Annotated[int, Field(ge=1)]
    project_stage: ProjectStage
    section_code: ProjectSection
    actor_user_uid: UserUid
    at: datetime
    reason: Annotated[str, Field(min_length=1, max_length=2000)] | None


class SectionSuggestion(_Object):
    """Display evidence for one section: never a confirmation and never a route."""

    score: Annotated[int, Field(ge=1)]
    filename_patterns: list[Annotated[str, Field(min_length=1, max_length=64)]]
    text_keywords: list[Annotated[str, Field(min_length=1, max_length=128)]]
    name_in_text: bool


class SectionReviewOption(_Object):
    section_code: ProjectSection
    name: Annotated[str, Field(min_length=1, max_length=200)]
    #: Whether a text profile is registered for this section, so a version confirmed with it
    #: can start a run. ``false`` is a refusal at run start, never an AR fallback.
    executable: bool
    suggestion: SectionSuggestion | None


class SectionReview(_Object):
    """All fifteen choices for one version, the current classification or ``null``."""

    version_uid: VersionUid
    classification: VersionClassification | None
    #: `CLASSIFICATION-CORRECTION-01`. Every revision of the classification, oldest first
    #: (revision 1 is the original confirmation); empty while the version is unclassified.
    revisions: list[VersionClassificationRevision]
    #: Whether the version's recognised-text markdown was read as suggestion evidence.
    recognised_text_consulted: bool
    options: Annotated[list[SectionReviewOption], Field(min_length=15, max_length=15)]


#: The module set (ADR-0025 decision 23): which comparison modules this deployment serves.
class ComparisonModules(str, enum.Enum):
    """``none`` serves neither comparison module (the default), ``versions`` «Сравнение
    версий», ``versions,stages`` both. A module that is off has no menu entry and its
    operations answer ``dependency_unavailable``."""

    NONE = "none"
    VERSIONS = "versions"
    VERSIONS_STAGES = "versions,stages"


class VersionUploadKind(str, enum.Enum):
    """How a version reached the product. ``comparison_pdf`` is a plain PDF admitted through
    comparison without a portal bundle. Ordinary section analysis can use its native PDF text and pages;
    portal-dependent operations still require a bundle."""

    PORTAL_BUNDLE = "portal_bundle"
    COMPARISON_PDF = "comparison_pdf"


class DocumentActiveRun(_Object):
    """`UI-A-47` (contract 1.40.0): the run of a version that is in flight -- admitted and not yet terminal.

    `state` is `queued` (waiting for an executor), `running` or `validating`; a `created` run has not been admitted and
    a terminal run is not active. No progress figure is carried: the run reports its stages, and a figure of
    «пакет n/m» would need a plan of its own (`D-345`).
    """

    run_id: RunId
    state: Literal["queued", "running", "validating"]


class DocumentAudit(_Object):
    """The audit of one version, as `listDocuments` shows it on each document (`UI-PARITY-DOC-AUDIT`, `UI-A-46`).

    The per-document form of the counters of `DocumentAuditCounts`, read by the same rules (`R-150n`, `R-150p`,
    `R-150r`, `R-150s`, `R-150t`): the version's **result run** is its latest run in state `published` or `partial`,
    ordered by `(created_at, run_id)` as `listRuns` orders them. A newer run still in flight does not displace it,
    and a `failed` or `cancelled` run is not a result.

    `state` is one of four words. `not_run`: no result run (never run, run only to `failed` or `cancelled`, or only
    in flight); there is then no `result_run_id`, and a failed or cancelled latest run does not change that, so the
    chip «отказ» (`R-150r`) is a marking of the screen's own and not a fifth state. `clean`: a result run that
    published no finding, a state of its own (`R-150n`). `awaiting_decision`: a result run with at least one finding
    whose current verdict is undecided (`pending` or `needs_manual_review`). `checked`: a result run, every finding
    decided. `partial` is not a fifth state: it is true when the result run is `partial` and marks the document in
    any of the four states (`R-150s`).

    `finding_count` is the number of published findings of the result run and `undecided_finding_count` the number of
    those still undecided; both are zero when there is no result run. Optimisation proposals are not part of any
    figure (`R-150u`).

    `active_run` (`UI-A-47`, contract 1.40.0) names the version's run in flight -- its latest run of the standard
    analysis in state `queued`, `running` or `validating`, by the order of the result run -- and is absent when none
    is. It is a fact beside the four words and changes none of them: a document whose first run is in flight is still
    `not_run`, and a `checked` one with a re-run in flight is still `checked`.

    `optimisation_proposal_count` and `optimisation_undecided_count` (`D-361`, contract 1.43.0) are the proposals of the
    version's latest optimisation pass and how many of them have no decision in force (none, or a withdrawn one) -- the
    original's «Оптимизация N» pill. Both are present when a pass was started over the version and both are absent when none
    was; they are a fact beside the four words and change none of them (`R-150u`).
    """

    state: Literal["not_run", "clean", "awaiting_decision", "checked"]
    partial: bool
    #: The result run the card links to «Разбор»; absent exactly when `state` is `not_run`.
    result_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    finding_count: Annotated[int, Field(ge=0)]
    undecided_finding_count: Annotated[int, Field(ge=0)]
    active_run: DocumentActiveRun = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `D-361` (contract 1.43.0): the proposals of the version's latest optimisation pass and, of those, how many have no
    #: decision in force (none, or a withdrawn one). Both are present when a pass was started over the version and both are
    #: absent when none was: absent is "no optimisation read", never zero. A fact beside the four words (`R-150u`).
    optimisation_proposal_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    optimisation_undecided_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)


class DocumentVersion(_Object):
    version_uid: VersionUid
    document_uid: DocumentUid
    project_uid: ProjectUid
    version_ordinal: Annotated[int, Field(ge=1)]
    display_title: Annotated[str, Field(min_length=1, max_length=400)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: `R-40`. See ``UploadDocumentRequest.section``: optional for the same reason, and
    #: never defaulted to one of the fifteen when a document was uploaded with none.
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `W59-SECTION-SEAL-01`. The version's persisted classification; absent while no expert
    #: has classified it. Never inherited from another version or from ``section``.
    classification: VersionClassification = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    source_filename: str | None = Field(default=None, json_schema_extra=optional_property)
    media_type: Literal["application/pdf"]
    byte_size: Annotated[int, Field(ge=0)]
    sha256: Sha256
    page_count: Annotated[int, Field(ge=1)]
    published_at: datetime
    input_manifest: list[InputManifestEntry]
    #: `CMP-SEAL-C0`. How the version reached the product; see :class:`VersionUploadKind`.
    #: Always sent from `1.9.0`.
    upload_kind: VersionUploadKind = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `R-151a` (contract 1.22.0): when the document was archived; absent while it is in use.
    archived_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `R-151e` (contract 1.23.0): the document's free tags, on the reads that carry them.
    tags: Annotated[list[Annotated[str, Field(min_length=1, max_length=40)]], Field(max_length=10)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    #: `UI-PARITY-DOC-AUDIT` (contract 1.34.0): the audit of this version. Present on the items of `listDocuments`
    #: only, where it is the audit of the document's current version; absent from every other answer that carries a
    #: `DocumentVersion` (`uploadDocument`, `uploadDocumentVersion`, `getDocumentVersion`, `listVersions`,
    #: `setDocumentArchived`, `renameDocument`, `setDocumentTags`), which read no runs.
    audit: DocumentAudit = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class DocumentVersionPage(_Object):
    items: list[DocumentVersion]
    page: PageInfo


class BlockGeometry(_Object):
    block_id: Annotated[str, Field(pattern=r"^b_[0-9]{6}$")]
    page_number: Annotated[int, Field(ge=1)]
    block_ordinal: Annotated[int, Field(ge=0)]
    bbox: Annotated[dict[str, float], WithJsonSchema(_BBOX_SCHEMA)]
    bbox_unit: Literal["pt"]
    bbox_origin: Literal["top_left"]
    char_start: Annotated[int, Field(ge=0)]
    char_end: Annotated[int, Field(ge=1)]


class VersionBlockIndex(_Object):
    version_uid: VersionUid
    status: Literal["produced", "not_produced"]
    #: Required and nullable, not optional: the contract's ``VersionBlockIndex`` carries
    #: both fields on every answer, null exactly when ``status`` is ``not_produced``. A
    #: plain ``X | None`` with no default -- unlike ``Evidence.block_id`` above -- is what
    #: makes Pydantic require the key in the emitted document rather than merely permit it.
    produced_by_run_id: RunId | None
    text_layer_sha256: Sha256 | None
    block_count: Annotated[int, Field(ge=0)]
    blocks: list[BlockGeometry]


# --- portal blocks (`W55B-SEAL-01`) --------------------------------------------------------


class PortalBlockType(str, enum.Enum):
    """The portal's own three block types, lower-cased. A stamp block exists only in the
    block list; the recognised-text markdown never carries one."""

    TEXT = "text"
    IMAGE = "image"
    STAMP = "stamp"


class PortalGeometryState(str, enum.Enum):
    """The page-box check (`W55-PLAN.md` section B3.7). ``geometry_mismatch`` means the
    portal's page size and the PDF's page box disagree beyond the frozen tolerance: no crop
    was cut for the page, and the block is shown without one rather than with a wrong one."""

    OK = "ok"
    GEOMETRY_MISMATCH = "geometry_mismatch"


class PortalCrop(_Object):
    """A crop this product cut itself from the PDF -- never the portal's ``crop_url``, which is
    a capability URL and is neither fetched, stored nor served. The bytes are
    ``streamVersionPortalBlockCrop``."""

    media_type: Literal["image/png"]
    width_px: Annotated[int, Field(ge=1)]
    height_px: Annotated[int, Field(ge=1)]
    sha256: Sha256


class PortalRecognisedText(_Object):
    """The portal's OCR text of a TEXT block, always marked ``recognised`` (R-116): it is never
    merged into the PDF text layer, and ``flags`` are the quality signals found in it
    (mixed-script words, Latin/Cyrillic homoglyphs, CJK, doubled list markers, degeneracy).
    ``text`` is markdown and is rendered as text, never as HTML."""

    quote_source: Literal["recognised"]
    text: Annotated[str, Field(min_length=1)]
    flags: list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]]


class PortalBlock(_Object):
    """One block of the portal's block list. The pair ``(version_uid, portal_block_id)``
    addresses it; ``ordinal`` is the portal's own order, not unique and null for a stamp."""

    portal_block_id: PortalBlockId
    page_number: Annotated[int, Field(ge=1)]
    page_label: Annotated[int, Field(ge=1)]
    ordinal: Annotated[int, Field(ge=0)] | None
    block_type: PortalBlockType
    status: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")]
    bbox_norm: Annotated[list[float], Field(min_length=4, max_length=4)]
    polygon_points: Annotated[
        list[Annotated[list[float], Field(min_length=2, max_length=2)]],
        Field(min_length=3, max_length=64),
    ] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    geometry: PortalGeometryState
    crop: PortalCrop = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    recognised_text: PortalRecognisedText = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    portal_description: Annotated[str, Field(min_length=1)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class VersionSheetLabel(_Object):
    """`UI-PARITY-P0O` (contract 1.30.0): one page of a version and the drawing sheet its portal blocks name."""

    page_number: Annotated[int, Field(ge=1)]
    #: The portal's ``page_label`` of the page's blocks; absent when they name different sheets (never guessed).
    page_label: Annotated[int, Field(ge=1)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    block_count: Annotated[int, Field(ge=1)]


class VersionSheetLabelList(_Object):
    """`UI-PARITY-P0O`: a version's pages with their sheet labels, as the original's «Лист» column, from the same portal
    geometry `listVersionPortalBlocks` reads; ``not_produced`` and no items while no run has produced it. A page without a
    portal block is not listed: a page number is never shown as a sheet."""

    version_uid: VersionUid
    status: Literal["produced", "not_produced"]
    items: list[VersionSheetLabel]


class FindingBlockLink(_Object):
    """`UI-PARITY-C6` (contract 1.41.0): the portal blocks that hold one finding's evidence."""

    finding_uid: FindingUid
    #: The blocks whose box covers at least half of the box of some evidence item, in the portal list's order; empty
    #: when the finding is on a page where a link can be derived and no block holds its evidence. Never a block the
    #: evidence is not in.
    portal_block_ids: list[PortalBlockId]


class RunFindingBlockLinks(_Object):
    """`UI-PARITY-C6`: a run's findings and the portal blocks their evidence sits in, derived on read from the run's text
    layer geometry, its page inventory and the version's portal blocks (``docs/program/UI-PARITY-01.md``); nothing is
    stored and the evidence is not changed. One item per published finding of the run, ``portal_block_ids`` empty where
    no block holds the evidence. ``unlinked_pages`` are the pages of the portal geometry on which no link can be derived
    (the portal's raster does not describe the PDF page): a block of such a page is **unknown**, never "no findings".
    ``not_produced`` and no items while the run has no text-layer geometry or the version no portal geometry."""

    run_id: RunId
    version_uid: VersionUid
    status: Literal["produced", "not_produced"]
    unlinked_pages: list[Annotated[int, Field(ge=1)]]
    items: list[FindingBlockLink]


class PortalBlockPage(_Object):
    """One page of a version's portal blocks, ordered by page, ordinal (null last) and id.

    ``status`` carries the distinction ``VersionBlockIndex.status`` carries: ``not_produced``
    is a version no run of which has produced portal geometry yet, ``produced`` one whose
    geometry stage succeeded and which may genuinely have no blocks. Both answer ``items=[]``
    and ``block_count=0`` only when they have none; a caller reads ``status``."""

    version_uid: VersionUid
    status: Literal["produced", "not_produced"]
    produced_by_run_id: RunId | None
    block_count: Annotated[int, Field(ge=0)]
    items: list[PortalBlock]
    page: PageInfo


# --- runs --------------------------------------------------------------------------


class RunCostConsent(_Object):
    """The expert confirms a fresh estimate (`HOSTS-SEAL-1`, consent v2). The body is the same whatever the route: the digest of
    the estimate that was shown, the ceiling the person approves and `confirmed`. When every cell of a run on the stage layout
    runs on a subscription the estimate is 0 and pressing the button that says so is the consent, with `ceiling_micros` 0. The
    consent the stand stores is built from the estimate the digest names and adds to it the digest of the stage plan and, per
    model, the digest of the rates and the access it was priced at; a start whose plan or access differs from them is refused."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [
            {"estimate_digest": "0" * 64, "ceiling_micros": 0, "confirmed": True},
            {"estimate_digest": "f" * 64, "ceiling_micros": 1500000, "confirmed": True},
        ]},
    )

    estimate_digest: Sha256
    ceiling_micros: Annotated[int, Field(ge=0, le=9007199254740991, strict=True)]
    confirmed: Annotated[bool, Field(strict=True)]


class RunCostModelLine(_Object):
    """One model of a run on the stage layout, priced (`HOSTS-SEAL-1`, consent v2): the digest of the rates it was priced at and
    the access, so a start that finds another rate or another access refuses with `cost_estimate_binding_changed`."""

    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    access: ExecutorModelAccess
    rate_sha256: Sha256
    calls: Annotated[int, Field(ge=0)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    estimated_cost_micros: Annotated[int, Field(ge=0)]


class RunCostEstimateRequest(_Object):
    version_uid: VersionUid
    reaudit_of_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    executor_connection_id: ExecutorConnectionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    preset_id: PresetId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `EXEC2-SEAL-2`. Exclusive with ``executor_connection_id`` and ``preset_id``.
    executor_group_id: ExecutorGroupId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    relaxed_limits: bool = Field(default=None, strict=True, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `R-151i` (contract 1.42.0). The price of a run started from ``start_stage_id`` of this earlier run; both or neither,
    #: and exclusive with ``reaudit_of_run_id``, the connection, the preset, the group and ``relaxed_limits`` (the new run
    #: follows today's route, as a re-audit does).
    start_from_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    start_stage_id: StageId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class RunCostEstimate(_Object):
    estimate_digest: Sha256
    scope: Literal["run"]
    version_uid: VersionUid
    provider_mode: ProviderMode
    #: `HOSTS-SEAL-1`: ``mixed`` is a run on the stage layout whose cells are paid in both ways; ``models`` then has a line per model.
    billing: Literal["metered", "unmetered", "mixed"]
    #: For a run on the stage layout, the model of its first cell; ``models`` lists every model it uses.
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    connection_revision_id: ExecutorRevisionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    preset_revision_id: PresetRevisionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `EXEC2-SEAL-2`. Present for an estimate on an executor group: what admission would freeze. No connection yet.
    executor_group_id: ExecutorGroupId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    executor_group_revision_id: ExecutorGroupRevisionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    routing_rule_revision_id: ExecutorRoutingRuleRevisionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    pin_id: Annotated[str, Field(min_length=1, max_length=128)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    text_characters: Annotated[int, Field(ge=0)]
    page_count: Annotated[int, Field(ge=1)]
    windows: Annotated[int, Field(ge=1)]
    calls: Annotated[int, Field(ge=1)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    estimated_cost_micros: Annotated[int, Field(ge=0)]
    recommended_ceiling_micros: Annotated[int, Field(ge=0)]
    currency: Literal["USD"]
    relaxed_limits: bool
    #: `R-151i` (contract 1.42.0). Present for the estimate of a run started from a stage: the earlier run, the first stage
    #: the new run computes, the stages it takes from the earlier run and the stages it computes (the price is for those).
    start_from_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    start_stage_id: StageId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reused_stage_ids: list[StageId] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    computed_stage_ids: list[StageId] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `HOSTS-SEAL-1` (consent v2). Present for the estimate of a run on the stage layout: the digest of the frozen plan and one
    #: line per model with the digest of its rates, the access it is priced at and its share of the estimate.
    stage_plan_digest: Sha256 = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    models: Annotated[list[RunCostModelLine], Field(max_length=16)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class StartRunRequest(_Object):
    version_uid: VersionUid
    cost_consent: RunCostConsent = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    relaxed_limits: bool = Field(default=None, strict=True, json_schema_extra=optional_property)  # type: ignore[assignment]
    provider_mode: ProviderMode = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `EXEC-PAR-START-01`. Optional and **not nullable**, like ``provider_mode``: absent means
    #: the global route, exactly as before; present means that connection or a refusal.
    executor_connection_id: ExecutorConnectionId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: `ANALYSIS-PRESETS-01`. Optional and **not nullable**, like ``executor_connection_id``, and
    #: exclusive with it: a person either takes a preset or names an executor.
    preset_id: PresetId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: `EXEC2-SEAL-2`. Optional and **not nullable**, and exclusive with ``executor_connection_id`` and
    #: ``preset_id``: the run is admitted on the group's current revision and the connection is chosen at dispatch.
    executor_group_id: ExecutorGroupId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class ReauditRunRequest(_Object):
    cost_consent: RunCostConsent = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class StartRunFromStageRequest(_Object):
    """`R-151i` (contract 1.42.0): the first stage the new run computes; the earlier stages are taken from the run in the path."""

    stage_id: StageId
    cost_consent: RunCostConsent = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class StageState(_Object):
    stage_id: StageId
    stage_version: Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    status: StageStatus
    error_code: str | None = Field(default=None, json_schema_extra=optional_property)
    started_at: datetime | None = Field(default=None, json_schema_extra=optional_property)
    finished_at: datetime | None = Field(default=None, json_schema_extra=optional_property)


class RunExecutor(_Object):
    """`EXEC-PAR-START-01`. Which executor a run is on: the connection, the name an administrator
    gave it and the model its frozen revision pins. Nothing else about the connection."""

    connection_id: ExecutorConnectionId
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    pin_id: Annotated[str, Field(min_length=1, max_length=128)]


class RunPreset(_Object):
    """`ANALYSIS-PRESETS-01`. The preset revision a run was started with: the preset, the number of
    the revision and the name it had then (a later rename does not change it)."""

    preset_id: PresetId
    revision_no: Annotated[int, Field(ge=1)]
    name: Annotated[str, Field(min_length=1, max_length=120)]


class RunQueueReason(str, enum.Enum):
    """`EXEC2-SEAL-1` (ADR-0026 decisions 1 and 5), widened by `EXEC2-SEAL-2` (decisions 14 and 15): why work
    is not running. `executor_at_capacity`: every unit of its executor connection (of every eligible member of
    its group) is in use. `runner_offline`: the connection is a `pull` connection and no runner of it is online
    (no eligible member has one). `needs_reconsent`: dispatch found the consent envelope no longer holds and
    called nothing. `model_unavailable` (`HOSTS-SEAL-1`, ADR-0028 decision 15): a run started on the stage layout waits
    because no available server can serve a model that one of its cells needs. The persisted `wait_reason` of pending
    work uses the same words."""

    EXECUTOR_AT_CAPACITY = "executor_at_capacity"
    RUNNER_OFFLINE = "runner_offline"
    NEEDS_RECONSENT = "needs_reconsent"
    #: `HOSTS-SEAL-1` (ADR-0028 decision 15): a run started on the stage layout waits because no available server can serve
    #: a model one of its cells needs; the cells are named in the run's wait detail. Before the start, nothing has run.
    MODEL_UNAVAILABLE = "model_unavailable"


class RunWaitCause(str, enum.Enum):
    """`HOSTS-L1` (contract 1.48.0): why one cell of a waiting planned run cannot be bound now. The six words of `ModelUnavailableReason` (no
    available server for the cell's model and access: switched off, off line, not logged in, the model not verified, cooling down, on no
    server) and `at_capacity`: a server serves the model and every place for it is taken."""

    HOST_DISABLED = "host_disabled"
    HOST_OFFLINE = "host_offline"
    LOGIN_REQUIRED = "login_required"
    MODEL_NOT_VERIFIED = "model_not_verified"
    MODEL_COOLING_DOWN = "model_cooling_down"
    NOT_ON_ANY_SERVER = "not_on_any_server"
    AT_CAPACITY = "at_capacity"


class RunWaitCell(_Object):
    """`HOSTS-L1` (contract 1.48.0, `D-660`): a cell of the run's frozen stage plan that has no server to take it now, and why. The model
    and the access are the plan's own; the cause is read at the moment of the status, from the same evaluation that keeps the run's
    `wait_reason` true. It names a model and a cause, never a server."""

    cell_key: StageCellKey
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    access: ExecutorModelAccess
    cause: RunWaitCause


class RunStatus(_Object):
    run_id: RunId
    reaudit_of_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `R-151i` (contract 1.42.0): the earlier run whose stage outputs this run reuses and the first stage it computes
    #: itself (every earlier PC-01 stage is the earlier run's). Absent for a run started from a version or as a re-audit.
    started_from_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    start_stage_id: StageId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    project_uid: ProjectUid
    version_uid: VersionUid
    state: RunState
    provider_mode: ProviderMode
    analysis_profile_id: AnalysisProfileId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    prompt_bundle_id: PromptBundleId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: `W55A-SEAL-01` (R-113, CD-6). The norms snapshot the run pinned when it was created:
    #: the current snapshot then, absent while none is current.
    norms_snapshot_id: NormsSnapshotId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    norm_retrieval_set_id: NormRetrievalSetId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    stages: list[StageState]
    degradation_set: list[StageId] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    terminal_reason: ErrorCode | None = Field(default=None, json_schema_extra=optional_property)
    #: `D-46`. **The same shape as ``ErrorEnvelope.details``, and the same constant**: it
    #: is the same rule -- safe scalar classifiers, restricted to the ``safe_detail_keys``
    #: the catalog declares for the reported code -- applied to the code in
    #: ``terminal_reason`` instead of to the code in ``error_code``. A second spelling of
    #: one constraint is a second thing to get wrong, so there is one.
    terminal_detail: Annotated[
        dict[str, str | float | int | bool | None] | None,
        WithJsonSchema(_DETAILS_SCHEMA),
    ] = Field(default=None, json_schema_extra=optional_property)
    terminal_message: Annotated[str, Field(min_length=1, max_length=512)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    interrupted_reason: str | None = Field(default=None, json_schema_extra=optional_property)
    published_finding_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    diagnostic_observation_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    cost_micros: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    cost_basis: CostBasis = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    model_call_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    created_at: datetime
    terminal_at: datetime | None = Field(default=None, json_schema_extra=optional_property)
    #: `EXEC-PAR-START-01`. The executor the run froze, read-only; null (and omitted) for a run
    #: that froze none.
    executor: RunExecutor | None = Field(default=None, json_schema_extra=optional_property)
    #: `ANALYSIS-PRESETS-01`. The preset the run was started with, read-only; null (and omitted)
    #: for a run started without one.
    preset: RunPreset | None = Field(default=None, json_schema_extra=optional_property)
    #: `EXEC2-SEAL-1`. Why a ``queued`` Run is waiting for its executor, derived at read time; null (and
    #: omitted) for a Run that is not waiting for one.
    queue_reason: RunQueueReason | None = Field(default=None, json_schema_extra=optional_property)
    #: `EXEC2-SEAL-2` (ADR-0026 decisions 12 to 15). Absent is read as ``frozen_at_start``. ``planned`` and
    #: ``binding`` are present for a Run admitted by a rule or a group (``binding`` once ``bound``);
    #: ``wait_reason`` and ``waiting_since`` while a ``pending`` Run waits for an executor.
    binding_state: ExecutorBindingState = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    planned: ExecutorGroupPlan = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    binding: ExecutorBinding = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    wait_reason: RunQueueReason = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    waiting_since: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `HOSTS-L1` (contract 1.48.0, `D-660`). The cells of a planned (stage-layout) run that waits and cannot be bound now, each with its
    #: model, its access and the cause; present only for a ``pending`` planned run that is ``queued`` with a ``wait_reason``.
    wait_cells: Annotated[list[RunWaitCell], Field(min_length=1, max_length=32)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    #: `R-151v` (contract 1.21.0): the account that started the run and its display label; absent for a run
    #: created before migration 0051.
    started_by_user_uid: UserUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    started_by_label: Annotated[str, Field(min_length=1, max_length=254)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    #: `UI-A-65` / `UI-B-45` (contract 1.40.0): the run's estimated finish, by the rule of
    #: `ExecutionQueueItem.estimated_finish_at` (`R-151u`) and by the same function -- the job's first attempt plus the
    #: median duration of similar recent runs. Absent while the run's job is not leased or running, before its first
    #: attempt, and without enough similar history; never invented.
    estimated_finish_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class RunStatusPage(_Object):
    items: list[RunStatus]
    page: PageInfo


class ExecutionQueueItem(_Object):
    __doc__ = (
        "`EXEC2-SEAL-2`: `binding_state` and `wait_reason` are present for a job whose Run was admitted by a rule or a "
        "group (`pending` while it waits for an executor). `UI-PARITY-QUEUE-A` (contract 1.18.0): the queue names what "
        "it lists. Every job executes exactly one audit run of one version of one document (`job.run_id` is "
        "not null and unique), so `project_uid`, `project_name`, `document_uid`, `document_name`, `version_uid` and "
        "`version_ordinal` are always present; the two names and the ordinal are joined at read time and stored "
        "nowhere. `started_at` is the creation time of the job's first attempt and is absent while no attempt "
        "exists; `finished_at` is the time the job reached a terminal state and is absent while it has not; "
        "`error_code` is the run's `terminal_reason` and `interrupted_reason` the run's own, each absent when the "
        "run records none. An absent property is omitted, never sent as null."
    )

    job_id: JobId
    run_id: RunId
    state: str
    priority: int
    created_at: datetime
    available_at: datetime
    project_uid: ProjectUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_uid: DocumentUid
    document_name: Annotated[str, Field(min_length=1, max_length=400)]
    version_uid: VersionUid
    #: The version's display number (``v1``, ``v2``): the only label a version has, and not an identity.
    version_ordinal: Annotated[int, Field(ge=1)]
    started_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    finished_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    error_code: ErrorCode = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    interrupted_reason: str = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `R-151v` (contract 1.21.0): who started the job's run, by display label; absent before migration 0051.
    started_by_label: Annotated[str, Field(min_length=1, max_length=254)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    #: `R-151u` (contract 1.26.0): a running job's estimated finish -- its start plus the median duration of similar
    #: recent runs; absent without enough history or while the job is not running.
    estimated_finish_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `UI-PARITY-P0M` (contract 1.28.0): a queued job's place among every queued job in the dispatcher's order
    #: (priority, then the oldest first), as the original numbers its queue; absent for a job that is not queued.
    #: It is the order, not a forecast: a job whose executor is busy can be passed by the next one.
    queue_position: Annotated[int, Field(ge=1)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    #: `UI-PARITY-P0M`: how many attempts the job has had (0 before its first).
    attempt_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    binding_state: ExecutorBindingState = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    wait_reason: RunQueueReason = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutionQueueStateCount(_Object):
    """`UI-PARITY-P0M` (contract 1.28.0): how many jobs stand in one state."""

    state: Literal["queued", "leased", "running", "retry_wait", "succeeded", "failed", "cancelled", "dead_letter"]
    count: Annotated[int, Field(ge=0)]


class ExecutionQueuePage(_Object):
    items: list[ExecutionQueueItem]
    page: PageInfo
    paused: bool
    #: `UI-PARITY-P0M` (contract 1.28.0): every job state with its count over the period filter (not the state
    #: filter), in the queue's state order, as the original's «N / M» and «N ✓ M ✗» line; a state with no job is 0.
    overview: list[ExecutionQueueStateCount] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    #: `D-395` (contract 1.43.0): how many failed jobs (`failed` or `dead_letter`) nothing has answered yet -- those with no
    #: later job for a run of the same document version and the same analysis -- over all history, whatever the period or
    #: state filter of this page. The original's «ошибки» figure: a failure drops out by being retried or superseded, not by
    #: ageing. Independent of the filters, so a one-row page carries it too.
    live_failure_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)


class ExecutionJournalEntry(_Object):
    event_id: str
    run_id: RunId
    aggregate_type: str
    aggregate_id: str
    event_type: str
    occurred_at: datetime
    payload: dict[str, str | int | float | bool | None]


class ExecutionJournalPage(_Object):
    items: list[ExecutionJournalEntry]
    page: PageInfo


class SetJobPriorityRequest(_Object):
    priority: Annotated[int, Field(ge=-100, le=100)]


class SetExecutionPausedRequest(_Object):
    paused: bool


class SetDocumentArchivedRequest(_Object):
    """`R-151a` (contract 1.22.0): archive (``true``) or restore (``false``) one document. Nothing is deleted."""

    archived: bool


class FindingExecutionStatus(str, enum.Enum):
    """`R-151g` (contract 1.24.0): what the designer did with an accepted finding, the original's SU-10 labels:
    ``taken_into_account`` «Учтено», ``amended`` «Внесено», ``declined`` «Отклонено», ``agreed`` «По согласованию»."""

    TAKEN_INTO_ACCOUNT = "taken_into_account"
    AMENDED = "amended"
    DECLINED = "declined"
    AGREED = "agreed"


class SetFindingExecutionStatusRequest(_Object):
    """`R-151g`: the new execution status, or ``null`` to clear it."""

    status: FindingExecutionStatus | None


class FindingExecutionState(_Object):
    """`R-151g`: a finding's execution status after the command; ``status`` and ``set_at`` absent when it has none."""

    finding_uid: FindingUid
    status: FindingExecutionStatus = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    set_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ImportRunDecisionsRequest(_Object):
    """`R-151d` (contract 1.27.0): the multipart body of ``importRunDecisions``.

    ``file`` is the run's workbook as ``exportRunXlsx`` produced it, edited, at most 10 MiB.
    """

    file: Annotated[UploadFile, WithJsonSchema(_BINARY_STRING)]


class DecisionImportOutcome(str, enum.Enum):
    """``recorded``: a decision event was appended; ``unchanged``: the ledger already says it; ``refused``."""

    RECORDED = "recorded"
    UNCHANGED = "unchanged"
    REFUSED = "refused"


class DecisionImportRefusal(str, enum.Enum):
    """Why a row of the workbook was refused."""

    NO_FINDING_UID = "no_finding_uid"
    DUPLICATE_FINDING = "duplicate_finding"
    UNKNOWN_FINDING = "unknown_finding"
    FINDING_NOT_IN_RUN = "finding_not_in_run"
    UNKNOWN_DECISION = "unknown_decision"
    NOT_IMPORTABLE = "not_importable"


class DecisionImportRow(_Object):
    """`R-151d`: one row of «Замечания» that names an ID or a decision; ``finding_uid`` only for a known finding."""

    row: Annotated[int, Field(ge=2)]
    outcome: DecisionImportOutcome
    finding_uid: FindingUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reason: DecisionImportRefusal = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class DecisionImportReport(_Object):
    """`R-151d`: what an import of edited decisions did, row by row, in sheet order."""

    run_id: RunId
    recorded: Annotated[int, Field(ge=0)]
    unchanged: Annotated[int, Field(ge=0)]
    refused: Annotated[int, Field(ge=0)]
    rows: list[DecisionImportRow]


class ImportProposalDecisionsRequest(_Object):
    """`UI-B-15` (contract 1.35.0): the multipart body of ``importOptimisationProposalDecisions``.

    ``file`` is the pass's workbook as ``exportOptimisationProposalsXlsx`` produced it, edited, at most 10 MiB.
    """

    file: Annotated[UploadFile, WithJsonSchema(_BINARY_STRING)]


class ProposalDecisionImportRefusal(str, enum.Enum):
    """Why a row of the proposals workbook was refused."""

    NO_PROPOSAL_ID = "no_proposal_id"
    DUPLICATE_PROPOSAL = "duplicate_proposal"
    UNKNOWN_PROPOSAL = "unknown_proposal"
    UNKNOWN_DECISION = "unknown_decision"
    COMMENT_REQUIRED = "comment_required"
    COMMENT_TOO_LONG = "comment_too_long"


class ProposalDecisionImportRow(_Object):
    """`UI-B-15`: one row of «Предложения» that names an ID or a decision; the proposal's identity only for a proposal of the pass."""

    row: Annotated[int, Field(ge=2)]
    outcome: DecisionImportOutcome
    optimisation_proposal_id: OptimisationProposalId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reason: ProposalDecisionImportRefusal = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ProposalDecisionImportReport(_Object):
    """`UI-B-15`: what an import of edited proposal decisions did, row by row, in sheet order."""

    optimisation_pass_id: OptimisationPassId
    recorded: Annotated[int, Field(ge=0)]
    unchanged: Annotated[int, Field(ge=0)]
    refused: Annotated[int, Field(ge=0)]
    rows: list[ProposalDecisionImportRow]


class SetDocumentTagsRequest(_Object):
    """`R-151e` (contract 1.23.0): the document's whole new set of free tags; an empty list removes them all."""

    tags: Annotated[list[Annotated[str, Field(min_length=1, max_length=40)]], Field(max_length=10)]


class DocumentTagCount(_Object):
    """`R-151e`: one tag of a project's documents in use, and how many documents carry it."""

    tag: Annotated[str, Field(min_length=1, max_length=40)]
    document_count: Annotated[int, Field(ge=1)]


class DocumentTagList(_Object):
    """`R-151e`: the project's tag catalogue, in case-insensitive order; archived documents are not counted."""

    items: list[DocumentTagCount]


class RenameDocumentRequest(_Object):
    """`R-151a` (contract 1.22.0): the document's new display title; ``document_uid`` stays its identity."""

    display_title: Annotated[str, Field(min_length=1, max_length=400)]


class ExecutionDispatchStatus(_Object):
    paused: bool
    changed_at: datetime


class WorkerState(str, enum.Enum):
    """`W54-SEAL-01`, plan section 3.6. Derived from the worker's last heartbeat: stale
    after 90 seconds without one, offline after 600 seconds."""

    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"


class ExecutionWorker(_Object):
    """One row of the worker registry (``worker``, migration ``0019``) and the runs it holds."""

    worker_id: WorkerId
    state: WorkerState
    intake_enabled: bool
    slots: Annotated[int, Field(ge=1)]
    version: Annotated[str, Field(min_length=1, max_length=128)]
    started_at: datetime
    heartbeat_at: datetime
    current_run_ids: list[RunId]


class ExecutionWorkerPage(_Object):
    items: list[ExecutionWorker]
    page: PageInfo


class SetWorkerIntakeRequest(_Object):
    enabled: bool


# --- norms (`W55A-SEAL-01`, plan section A3.6) ------------------------------------------


class NormSourceAttribution(str, enum.Enum):
    """`NORM-Q04`. Where a norm document's text came from, carried exactly on every norms
    response. The corpus is internal (D-4.1); nothing here is a publication claim."""

    CONSULTANT_PLUS = "consultant_plus"
    UNATTRIBUTED = "unattributed"


class NormParagraphKind(str, enum.Enum):
    BODY = "body"
    HEADING = "heading"
    TABLE_ROW = "table_row"


class NormTextReliability(str, enum.Enum):
    """F-4. An ``unreliable`` paragraph's recognised text did not survive repair; it is
    shown marked in a document view and is never a search result."""

    RELIABLE = "reliable"
    UNRELIABLE = "unreliable"


class NormBuildState(str, enum.Enum):
    """The snapshot's ``bge-m3-dense-v1`` build (D-127) over its reliability-aware chunks."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    ABSENT = "absent"


class NormHighlight(_Object):
    """One matched span of a fragment, as character offsets into ``NormFragment.text``."""

    char_start: Annotated[int, Field(ge=0)]
    char_end: Annotated[int, Field(ge=1)]


class NormFragment(_Object):
    """`NORM-Q01`. A plain-text excerpt of the canonical paragraph text, with the matched
    spans as offsets rather than markup."""

    text: Annotated[str, Field(min_length=1, max_length=4000)]
    highlights: list[NormHighlight]


class NormSearchHit(_Object):
    """One reliable canonical paragraph of the searched snapshot."""

    norms_snapshot_id: NormsSnapshotId
    norm_document_id: NormDocumentId
    norm_paragraph_id: NormParagraphId
    designation: Annotated[str, Field(min_length=1, max_length=500)]
    title: Annotated[str, Field(min_length=1, max_length=1000)]
    doc_type: Annotated[str, Field(min_length=1, max_length=100)]
    clause_number: Annotated[str, Field(min_length=1, max_length=100)] | None
    page_label: Annotated[int, Field(ge=1)]
    block_ref: Annotated[str, Field(min_length=1, max_length=200)]
    fragment: NormFragment
    source_attribution: NormSourceAttribution


class NormSearchPage(_Object):
    items: list[NormSearchHit]
    page: PageInfo


class NormDocument(_Object):
    """One document of a snapshot. ``content_available`` is true exactly when its PDF has a
    confirmed custody binding, which is the only way ``streamNormDocumentContent`` serves it."""

    norm_document_id: NormDocumentId
    norms_snapshot_id: NormsSnapshotId
    designation: Annotated[str, Field(min_length=1, max_length=500)]
    title: Annotated[str, Field(min_length=1, max_length=1000)]
    doc_type: Annotated[str, Field(min_length=1, max_length=100)]
    drawn_on: date | None
    pdf_page_count: Annotated[int, Field(ge=1)]
    paragraph_count: Annotated[int, Field(ge=0)]
    unreliable_paragraph_count: Annotated[int, Field(ge=0)]
    content_available: bool
    source_attribution: NormSourceAttribution


class NormCatalogueEntry(_Object):
    """One document of the current snapshot as the catalogue lists it
    (`W57B-NORMS-CATALOGUE-XLSX-01`). ``designation`` and ``title`` are derived for display
    from the stored file name and are never identities; ``title`` is null when the name
    carries nothing after the designation. ``kind`` is the stored document type verbatim."""

    norm_document_id: NormDocumentId
    designation: Annotated[str, Field(min_length=1, max_length=520)]
    title: Annotated[str, Field(min_length=1, max_length=1000)] | None
    kind: Annotated[str, Field(min_length=1, max_length=100)]
    page_count: Annotated[int, Field(ge=1)]
    paragraph_count: Annotated[int, Field(ge=0)]
    content_available: bool
    source_attribution: NormSourceAttribution


class NormKindCount(_Object):
    kind: Annotated[str, Field(min_length=1, max_length=100)]
    document_count: Annotated[int, Field(ge=1)]


class NormCatalogueEntryPage(_Object):
    """One page of the catalogue; ``total`` counts the documents the filters keep and
    ``kinds`` lists every kind of the snapshot with its document count."""

    norms_snapshot_id: NormsSnapshotId
    items: list[NormCatalogueEntry]
    page: PageInfo
    total: Annotated[int, Field(ge=0)]
    kinds: list[NormKindCount]


class NormParagraph(_Object):
    norm_paragraph_id: NormParagraphId
    ordinal: Annotated[int, Field(ge=0)]
    page_label: Annotated[int, Field(ge=1)]
    block_ref: Annotated[str, Field(min_length=1, max_length=200)]
    kind: NormParagraphKind
    clause_number: Annotated[str, Field(min_length=1, max_length=100)] | None
    text: Annotated[str, Field(min_length=1)]
    text_reliability: NormTextReliability


class NormParagraphPage(_Object):
    """One document's canonical paragraphs in ``ordinal`` order, and its attribution."""

    items: list[NormParagraph]
    page: PageInfo
    source_attribution: NormSourceAttribution


class NormSnapshot(_Object):
    """One loaded snapshot. ``qualified`` is the setter's own predicate (a complete build
    and a confirmed source binding for every document's PDF); ``current`` marks the one
    current snapshot."""

    norms_snapshot_id: NormsSnapshotId
    content_key: Annotated[str, Field(min_length=1, max_length=240)]
    document_count: Annotated[int, Field(ge=1)]
    paragraph_count: Annotated[int, Field(ge=0)]
    unreliable_count: Annotated[int, Field(ge=0)]
    build_state: NormBuildState
    qualified: bool
    current: bool
    created_at: datetime


class NormSnapshotPage(_Object):
    items: list[NormSnapshot]
    page: PageInfo


class NormSnapshotEvent(_Object):
    """One row of the append-only history of the current snapshot, newest first."""

    event_id: Annotated[str, Field(pattern=rf"^evt_{_ULID}$")]
    from_norms_snapshot_id: NormsSnapshotId | None
    to_norms_snapshot_id: NormsSnapshotId
    actor_user_uid: UserUid
    changed_at: datetime


class NormSnapshotEventPage(_Object):
    items: list[NormSnapshotEvent]
    page: PageInfo


class SetCurrentNormSnapshotRequest(_Object):
    """``expected_current`` is the snapshot the caller believes is current, ``null`` when it
    believes none is; a stale belief is ``conflict`` (``stale_current_snapshot``)."""

    norms_snapshot_id: NormsSnapshotId
    expected_current: NormsSnapshotId | None


class NormCurrentSnapshot(_Object):
    norms_snapshot_id: NormsSnapshotId
    designated_at: datetime
    designated_by: UserUid


# --- findings ----------------------------------------------------------------------


class DecisionCarriedFrom(_Object):
    """`UI-A-73` (contract 1.39.0): where a carried decision came from -- the decision of an earlier version's finding
    that an expert carried over to this finding (`W59-DECISION-CARRYOVER-01`).

    ``decision_id`` is the source decision's own identity and ``finding_uid`` and ``version_uid`` the finding and the
    version it was made on. ``version_ordinal`` is the version's display order («V2») and is never an identity."""

    decision_id: DecisionId
    finding_uid: FindingUid
    version_uid: VersionUid
    version_ordinal: Annotated[int, Field(ge=1)]


class Evidence(_Object):
    evidence_ordinal: Annotated[int, Field(ge=0)]
    page_number: Annotated[int, Field(ge=1)]
    quote: Annotated[str, Field(min_length=1, max_length=2000)]
    char_start: Annotated[int, Field(ge=0)]
    char_end: Annotated[int, Field(ge=1)]
    block_id: Annotated[str, Field(pattern=r"^b_[0-9]{6}$")] | None = Field(
        default=None, json_schema_extra=optional_property
    )


class ObservationProvenance(_Object):
    stage_id: StageId
    analysis_profile_id: AnalysisProfileId
    prompt_bundle_id: PromptBundleId
    provider_mode: ProviderMode
    model_call_id: ModelCallId | None = Field(default=None, json_schema_extra=optional_property)
    model_identity: str | None = Field(default=None, json_schema_extra=optional_property)


class NormCitationState(str, enum.Enum):
    VERIFIED = "verified"
    REBOUND = "rebound"


class NormCitation(_Object):
    norms_snapshot_id: NormsSnapshotId
    norm_document_id: NormDocumentId
    norm_paragraph_id: NormParagraphId
    designation: Annotated[str, Field(min_length=1, max_length=500)]
    title: Annotated[str, Field(min_length=1, max_length=1000)]
    clause_number: Annotated[str, Field(min_length=1, max_length=100)] | None
    page_label: Annotated[int, Field(ge=1)]
    quote: Annotated[str, Field(min_length=20, max_length=4000)]
    state: NormCitationState
    source_attribution: NormSourceAttribution


class FindingObservation(_Object):
    finding_observation_id: FindingObservationId
    run_id: RunId
    category: FindingCategory
    finding_text: Annotated[str, Field(min_length=1, max_length=4000)]
    recommendation_text: Annotated[str, Field(min_length=1, max_length=4000)]
    proposed_severity: Severity = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    evidence: Annotated[list[Evidence], Field(min_length=1)]
    provenance: ObservationProvenance
    norm_citations: Annotated[list[NormCitation], Field(max_length=5)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    required_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    stated_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class Finding(_Object):
    finding_uid: FindingUid
    project_uid: ProjectUid
    version_uid: VersionUid
    run_id: RunId
    category: FindingCategory
    observation: FindingObservation
    norm_citations: Annotated[list[NormCitation], Field(max_length=5)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    required_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    stated_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    merged_observations: list[FindingObservation] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    decided_severity: Severity = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `R-151g` (contract 1.24.0): the designer's execution status of an accepted finding, and when it was set.
    execution_status: FindingExecutionStatus = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    execution_status_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    current_verdict: Verdict
    latest_decision_id: DecisionId | None = Field(default=None, json_schema_extra=optional_property)
    decision_recorded_at: datetime | None = Field(default=None, json_schema_extra=optional_property)
    #: `UI-A-73` (contract 1.39.0): where the decision that carries ``current_verdict`` came from, when an expert carried
    #: it over from an earlier version; absent when the verdict was decided directly (and for every verdict decided
    #: before the field existed).
    current_verdict_carried_from: DecisionCarriedFrom = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)


class FindingDetail(_Object):
    """``Finding``'s property set restated, plus exactly two.

    It is restated and not composed with ``allOf``: under JSON Schema 2020-12 an
    ``additionalProperties: false`` sees only its own schema object's properties, so an
    ``allOf`` branch over the closed ``Finding`` would reject the two this adds.
    ``tests/contract/api_v1/test_finding_detail_composition.py`` pins it.
    """

    finding_uid: FindingUid
    project_uid: ProjectUid
    version_uid: VersionUid
    run_id: RunId
    category: FindingCategory
    observation: FindingObservation
    norm_citations: Annotated[list[NormCitation], Field(max_length=5)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    required_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    stated_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    merged_observations: list[FindingObservation] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    decided_severity: Severity = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `R-151g` (contract 1.24.0): as on ``Finding``.
    execution_status: FindingExecutionStatus = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    execution_status_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    current_verdict: Verdict
    latest_decision_id: DecisionId | None = Field(default=None, json_schema_extra=optional_property)
    decision_recorded_at: datetime | None = Field(default=None, json_schema_extra=optional_property)
    #: `UI-A-73` (contract 1.39.0): as on ``Finding``.
    current_verdict_carried_from: DecisionCarriedFrom = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    latest_comment: str | None = Field(default=None, json_schema_extra=optional_property)
    decision_event_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


# --- the norms a run's text cites (`NORM-REFS-RUN-01`) ----------------------------------------
#
# «Нормативные ссылки» on the run page: the normative documents the run's saved text cites,
# each resolved against the norms snapshot the run pinned. Computed per request and read-only:
# no finding is published, no severity is proposed and no model is called. The five outcomes are
# the resolver's (`W57-PLAN.md` B3.3): ``in_corpus``, ``newer_edition``, ``older_edition_only``
# (the corpus holds only an earlier edition than the one cited), ``not_in_corpus`` and
# ``not_recognised`` (the citation could not be read as a designation). The state and the
# outcome are inline closed sets, not component schemas: nothing else uses them.

_NormReferenceState = Literal["ready", "snapshot_not_pinned", "text_unavailable", "too_many_citations"]
_NormReferenceOutcome = Literal[
    "in_corpus", "newer_edition", "older_edition_only", "not_in_corpus", "not_recognised"
]


class NormReferenceCounts(_Object):
    """Distinct cited designations per outcome; every outcome is present, zeros written."""

    in_corpus: Annotated[int, Field(ge=0)]
    newer_edition: Annotated[int, Field(ge=0)]
    older_edition_only: Annotated[int, Field(ge=0)]
    not_in_corpus: Annotated[int, Field(ge=0)]
    not_recognised: Annotated[int, Field(ge=0)]


class NormReferenceAnchor(_Object):
    """One occurrence of a citation: the PDF page and the offsets inside that page's text."""

    page_number: Annotated[int, Field(ge=1)]
    char_start: Annotated[int, Field(ge=0)]
    char_end: Annotated[int, Field(ge=1)]
    quote: Annotated[str, Field(min_length=1, max_length=300)]


class NormReferenceItem(_Object):
    """One distinct cited designation and what the pinned snapshot holds for it.

    ``anchors`` keeps at most ten occurrences in reading order; ``occurrence_count`` is the
    true number. The ``matched_*`` properties name the corpus document the outcome points at
    (the same edition, the newer one, or the newest earlier one) and are absent exactly for
    ``not_in_corpus`` and ``not_recognised``. ``matched_designation`` and ``matched_title`` are
    derived for display from the stored file name and are never identities.
    """

    cited: Annotated[str, Field(min_length=1, max_length=300)]
    outcome: _NormReferenceOutcome
    occurrence_count: Annotated[int, Field(ge=1)]
    anchors: Annotated[list[NormReferenceAnchor], Field(min_length=1, max_length=10)]
    matched_norm_document_id: NormDocumentId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    matched_designation: Annotated[str, Field(min_length=1, max_length=500)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    matched_title: Annotated[str, Field(min_length=1, max_length=1000)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class NormReferenceUnrecognised(_Object):
    """A document of the pinned snapshot whose designation the parser cannot read.

    Such a document can never be matched by a citation, so the list is explicit rather than
    inferred. ``slug`` is the stored file name without ``.pdf``; ``designation`` and ``title``
    are derived for display from it.
    """

    norm_document_id: NormDocumentId
    slug: Annotated[str, Field(min_length=1, max_length=500)]
    designation: Annotated[str, Field(min_length=1, max_length=500)]
    title: Annotated[str, Field(min_length=1, max_length=1000)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class RunNormReferences(_Object):
    """The norms a run's text cites, or the explicit reason that cannot be said.

    ``state`` is ``ready`` when the list was computed; ``snapshot_not_pinned`` when the run
    pinned no norms snapshot (none was current when it was created); ``text_unavailable`` when
    it has no saved text layer; ``too_many_citations`` when the text cites more than one answer
    carries (over 1000 distinct designations, or one longer than 300 characters). Everything
    after ``text_layer_sha256`` is
    present exactly when ``state`` is ``ready``. ``unread_pages`` are pages with no text layer,
    on which no citation can be found; ``occurrence_count`` counts every occurrence, not only
    the anchors kept.
    """

    run_id: RunId
    version_uid: VersionUid
    state: _NormReferenceState
    page_count: Annotated[int, Field(ge=1)]
    norms_snapshot_id: NormsSnapshotId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    text_layer_sha256: Sha256 = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    snapshot_document_count: Annotated[int, Field(ge=1)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    counts: NormReferenceCounts = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    occurrence_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    unread_pages: list[Annotated[int, Field(ge=1)]] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    items: Annotated[list[NormReferenceItem], Field(max_length=1000)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    unrecognised: Annotated[list[NormReferenceUnrecognised], Field(max_length=20000)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class FindingPage(_Object):
    items: list[Finding]
    page: PageInfo


# --- decisions ---------------------------------------------------------------------


class AppendDecisionRequest(_Object):
    event_type: DecisionEventType
    finding_observation_id: FindingObservationId
    severity: Severity = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    comment: Annotated[str, Field(min_length=1, max_length=4000)] | None = Field(
        default=None, json_schema_extra=optional_property
    )

    @model_validator(mode="after")
    def severity_requires_accept(self) -> AppendDecisionRequest:
        if self.severity is not None and self.event_type is not DecisionEventType.ACCEPT:
            raise ValueError("severity_requires_accept")
        return self


class DecisionEvent(_Object):
    decision_id: DecisionId
    finding_uid: FindingUid
    finding_observation_id: FindingObservationId
    event_type: DecisionEventType
    verdict: Verdict | None = Field(default=None, json_schema_extra=optional_property)
    severity: Severity = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    comment: str | None = Field(default=None, json_schema_extra=optional_property)
    author_label: Annotated[str, Field(min_length=1, max_length=128)]
    recorded_at: datetime
    #: `UI-A-73` (contract 1.39.0): the decision this event carries over from an earlier version's finding; absent for an
    #: event an expert made directly (and for every event written before the field existed).
    carried_from: DecisionCarriedFrom = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class AppendDecisionResponse(_Object):
    event: DecisionEvent
    current_verdict: Verdict


class DecisionEventPage(_Object):
    items: list[DecisionEvent]
    page: PageInfo


class DecisionRecord(_Object):
    """``DecisionEvent``'s property set restated, plus the finding context.

    Restated and not composed with ``allOf``, for the reason ``FindingDetail`` gives:
    under JSON Schema 2020-12 an ``additionalProperties: false`` sees only its own schema
    object's properties, so an ``allOf`` branch over the closed ``DecisionEvent`` would
    reject the six this adds.

    The six are required, and ``FindingDetail.decision_event_count`` is not: there the
    count describes a finding that may never have been decided, and here every record IS
    an event, so the count is at least one and its absence would mean nothing.
    """

    decision_id: DecisionId
    finding_uid: FindingUid
    finding_observation_id: FindingObservationId
    event_type: DecisionEventType
    verdict: Verdict | None = Field(default=None, json_schema_extra=optional_property)
    severity: Severity = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    comment: str | None = Field(default=None, json_schema_extra=optional_property)
    author_label: Annotated[str, Field(min_length=1, max_length=128)]
    recorded_at: datetime
    project_uid: ProjectUid
    run_id: RunId
    #: `UI-PARITY-P0A`. Where the decision belongs. The two names are joined at read time and
    #: stored nowhere.
    document_uid: DocumentUid
    version_uid: VersionUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_name: Annotated[str, Field(min_length=1, max_length=400)]
    #: The expert-confirmed section of the finding's version; absent while it is unclassified.
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    category: FindingCategory
    finding_text: Annotated[str, Field(min_length=1, max_length=4000)]
    current_verdict: Verdict
    decision_event_count: Annotated[int, Field(ge=0)]
    #: `UI-A-73` (contract 1.39.0): as on ``DecisionEvent``.
    carried_from: DecisionCarriedFrom = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class DecisionRecordPage(_Object):
    items: list[DecisionRecord]
    page: PageInfo
    #: `UI-PARITY-P0A`. The number of entries that match the filters, not the number on this page.
    total: Annotated[int, Field(ge=0)]


class ProposalDecisionCarriedFrom(_Object):
    """`UI-B-14` (contract 1.37.0): where a carried decision came from -- the decision of an earlier version's pass
    that an expert carried over to this proposal.

    ``proposal_decision_id`` is the source decision's own identity and ``optimisation_pass_id`` and ``version_uid`` the
    pass and version it was made in. ``version_ordinal`` is the version's display order («V2») and is never an identity.
    """

    proposal_decision_id: ProposalDecisionId
    optimisation_pass_id: OptimisationPassId
    version_uid: VersionUid
    version_ordinal: Annotated[int, Field(ge=1)]


class ProposalDecisionRecord(_Object):
    """`R-151h` (contract 1.25.0): one expert decision on an optimisation proposal, with where it belongs and what it
    decided about -- the knowledge base's «Предложения» half, as ``DecisionRecord`` is its «Замечания» half.

    ``carried_from`` (`D-335`, contract 1.43.0) is present only for a decision an expert carried over from an earlier
    version's pass, and names the source; it is absent for a decision made directly."""

    proposal_decision_id: ProposalDecisionId
    optimisation_proposal_id: OptimisationProposalId
    optimisation_pass_id: OptimisationPassId
    verdict: ProposalVerdict
    comment: Annotated[str, Field(min_length=1, max_length=2000)] | None
    actor_label: Annotated[str, Field(min_length=1, max_length=254)]
    decided_at: datetime
    project_uid: ProjectUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_uid: DocumentUid
    document_name: Annotated[str, Field(min_length=1, max_length=400)]
    version_uid: VersionUid
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    row_text: Annotated[str, Field(min_length=1)]
    proposed_vendor: Annotated[str, Field(min_length=1)]
    unit: Annotated[str, Field(min_length=1)]
    #: `D-335` (contract 1.43.0): as on ``ProposalDecision`` -- present only for a decision an expert carried over from
    #: an earlier version's pass, naming the source decision, its pass and its version (with the display ordinal);
    #: absent for one made directly.
    carried_from: ProposalDecisionCarriedFrom = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ProposalDecisionRecordPage(_Object):
    """`R-151h`: one page of the proposal decision journal, newest first, and how many entries match."""

    items: list[ProposalDecisionRecord]
    page: PageInfo
    total: Annotated[int, Field(ge=0)]


class KnowledgeBaseEntry(_Object):
    """`R-151h`, `D-317`: one row of the knowledge base's «Все».

    A decision on a finding (``kind: finding``, the ``DecisionRecord`` in ``finding``) or on an optimisation proposal
    (``kind: proposal``, the ``ProposalDecisionRecord`` in ``proposal``); exactly the one its kind names is present. The
    two keep their own identities -- a row is named by its kind and that record's id, never by a number of its own.
    ``occurred_at`` is the record's own time (``recorded_at`` or ``decided_at``), by which the merged journal is ordered.
    """

    kind: Literal["finding", "proposal"]
    occurred_at: datetime
    finding: DecisionRecord = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    proposal: ProposalDecisionRecord = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class KnowledgeBaseEntryPage(_Object):
    """`R-151h`, `D-317`: one page of both journals merged, newest first, and how many entries match in both."""

    items: list[KnowledgeBaseEntry]
    page: PageInfo
    total: Annotated[int, Field(ge=0)]


# --- «График работ» (`UI-PARITY-P0P`, contract 1.31.0) ------------------------------------

class WorkScheduleSettings(_Object):
    """`R-152b`: the default monthly plan of an engineer without one (initially 20) and the time zone of the days."""

    default_monthly_plan: Annotated[int, Field(ge=0, le=999)]
    time_zone: Annotated[str, Field(min_length=1, max_length=64)]


class WorkScheduleDay(_Object):
    """One day of the schedule; ``override`` says the administrator decided it (`R-152d`), absent for the week's rule."""

    day: date
    day_off: bool
    override: Literal["day_off", "workday"] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class WorkScheduleDoneDocument(_Object):
    """`R-151x`: a document that became «Проверено экспертом» on ``day``, credited to the author of its last verdict."""

    day: date
    project_uid: ProjectUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_uid: DocumentUid
    document_title: Annotated[str, Field(min_length=1, max_length=400)]


class WorkScheduleEngineer(_Object):
    """One engineer's month: the plan (``plan_is_default`` when the stored default applies), done work and absences."""

    user_uid: UserUid
    label: Annotated[str, Field(min_length=1, max_length=254)]
    plan: Annotated[int, Field(ge=0, le=999)]
    plan_is_default: bool
    fact: Annotated[int, Field(ge=0)]
    done: list[WorkScheduleDoneDocument]
    absences: list[date]


class WorkScheduleMonth(_Object):
    """`UI-PARITY-P0P`: «Выполнено» for one month: an administrator reads every active expert, an expert their own."""

    month: Annotated[str, Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")]
    settings: WorkScheduleSettings
    days: list[WorkScheduleDay]
    engineers: list[WorkScheduleEngineer]


class WorkScheduleReserveItem(_Object):
    """`R-152e`: an open assignment of «Диспетчер» and its planned date; ``planned_on`` absent is «без даты»."""

    assignment_uid: AssignmentUid
    status: AssignmentStatus
    project_uid: ProjectUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_uid: DocumentUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    document_title: Annotated[str, Field(min_length=1, max_length=400)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)
    planned_on: date = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class WorkScheduleReserveEngineer(_Object):
    user_uid: UserUid
    label: Annotated[str, Field(min_length=1, max_length=254)]
    items: list[WorkScheduleReserveItem]


class WorkScheduleReserve(_Object):
    """`R-150y`, `R-152e`…`R-152h`: «Календарь запаса» -- open assignments by engineer over the days from ``start``."""

    start: date
    days: list[WorkScheduleDay]
    engineers: list[WorkScheduleReserveEngineer]


class SetWorkSchedulePlansRequest(_Object):
    """`R-151x`: the administrator's plans for one month; an engineer not named keeps the plan they have."""

    month: Annotated[str, Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")]
    plans: Annotated[list["WorkSchedulePlan"], Field(min_length=1, max_length=500)]


class WorkSchedulePlan(_Object):
    user_uid: UserUid
    planned: Annotated[int, Field(ge=0, le=999)]


class SetWorkCalendarDaysRequest(_Object):
    """`R-152d`: days made days off or working days; ``default`` returns a day to the week's rule."""

    days: Annotated[list["WorkCalendarDayChange"], Field(min_length=1, max_length=400)]


class WorkCalendarDayChange(_Object):
    day: date
    kind: Literal["day_off", "workday", "default"]


class SetEngineerAbsencesRequest(_Object):
    """`R-152d`: one engineer's absent days, marked (``absent``) or cleared."""

    user_uid: UserUid
    days: Annotated[list["EngineerAbsenceChange"], Field(min_length=1, max_length=400)]


class EngineerAbsenceChange(_Object):
    day: date
    absent: bool


class ScheduleAssignmentsRequest(_Object):
    """`R-152g`, `R-152h`: move one or several assignments to a day (``planned_on`` absent: «без даты»), and to another
    engineer when ``assignee_user_uid`` names one (a reassignment)."""

    moves: Annotated[list["AssignmentMove"], Field(min_length=1, max_length=200)]


class AssignmentMove(_Object):
    assignment_uid: AssignmentUid
    planned_on: date = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    assignee_user_uid: UserUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


# --- dashboard -----------------------------------------------------------------------
#
# `R-44`. One aggregate read across the whole deployment; see ``getDashboardSummary`` in
# ``api/routers/dashboard.py`` for what it answers and ``docs/program/W46-SEAL.md``
# section 3 for the argument.


class ProjectDocumentCount(_Object):
    """One row of the "documents per project" panel. Same fact ``Project.document_count``
    already publishes, gathered here for every project in one read."""

    project_uid: ProjectUid
    name: Annotated[str, Field(min_length=1, max_length=200)]
    document_count: Annotated[int, Field(ge=0)]


class VerdictCount(_Object):
    """How many findings, across every project, currently stand at one verdict -- every finding of every run,
    «за всё время».

    This is the history of the deployment's verdicts (`R-150q`), not the state of the current documents: it counts
    findings of older versions and of runs that are no longer the result. The findings that still await a decision
    on current versions are `DashboardSummary.awaiting_decision_findings`, and the two differ whenever a version has
    more than one run or a document more than one version.

    Every member of ``Verdict`` is present. A verdict nobody has recorded is ``count: 0``,
    not an absent row -- absent is not empty.
    """

    verdict: Verdict
    count: Annotated[int, Field(ge=0)]


class RunStateCount(_Object):
    """How many runs, across every project, currently sit in one state.

    Every member of ``RunState`` is present, for the same reason ``VerdictCount`` states.
    """

    state: RunState
    count: Annotated[int, Field(ge=0)]


class RunActivitySpend(_Object):
    """What every run, across every project, has spent at the provider so far.

    The same conservative rule ``RunStatus``'s own ``cost_basis`` applies to one run,
    computed here over every ``model_call`` row that exists: ``measured`` only when every
    contributing row reported a measured cost.
    """

    model_call_count: Annotated[int, Field(ge=0)]
    cost_micros: Annotated[int, Field(ge=0)]
    cost_basis: CostBasis


class RunActivity(_Object):
    by_state: list[RunStateCount]
    #: Optional, not nullable -- absent on a deployment with no ``model_call`` row at
    #: all. ``RunRepository.cost()`` answers ``None`` for the identical state on one run
    #: and says why in its own docstring; this aggregate now keeps that branch rather
    #: than reporting a zero labelled ``measured`` over an empty table (`F-1`,
    #: ``docs/program/reviews/W46-JUDGE-A.md`` section 3).
    spend: RunActivitySpend = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class SectionDocumentCount(_Object):
    """How many published documents carry one project section (`R-40`, `D-56`).

    ``section`` is optional, exactly as ``DocumentVersion.section`` is, and its absence on
    one row of this list means the same thing it means there: this row is the
    unclassified bucket, not a sixteenth section. Every one of the fifteen current codes
    is present even at ``document_count: 0`` -- "a section with no documents" is the
    dispatch brief's own example of absent not being empty.

    `audit_counts` are the section's documents by audit state (`UI-PARITY-P0B`; see `DocumentAuditCounts` for the
    rules) and `document_count` equals `audit_counts.document_count`. `finding_count` is the number of published
    findings of those documents' result runs.
    """

    document_count: Annotated[int, Field(ge=0)]
    audit_counts: DocumentAuditCounts
    finding_count: Annotated[int, Field(ge=0)]
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class DashboardSummary(_Object):
    """``getDashboardSummary``'s whole answer. All four panels and the figure of findings that await a decision,
    one read, one optional filter.

    The filter is the request's ``project_uid`` (`UI-PARITY-P0A`); the answer carries no echo of it.
    """

    documents_by_project: list[ProjectDocumentCount]
    findings_by_verdict: list[VerdictCount]
    run_activity: RunActivity
    section_breakdown: list[SectionDocumentCount]
    #: Findings still awaiting a decision -- current verdict `pending` or `needs_manual_review` -- in the result
    #: runs of current versions (`R-150q`). Unlike `findings_by_verdict` (every finding of every run, all time) this
    #: is the figure of the tile «Находки, ожидающие решения»; it follows the optional `project_uid` as every panel does.
    awaiting_decision_findings: Annotated[int, Field(ge=0)]


# --- accounts and registration requests ------------------------------------------------
#
# `W49-SEAL-01`, owner rulings `R-55` ... `R-61`. The operations are in
# ``api/routers/me.py``, ``api/routers/registrations.py`` and ``api/routers/users.py``; the
# rules they answer by are ``auditmanager.access``'s and are not restated here. What is
# restated is the bound a transport schema states for a body: a name is 1..60 characters,
# a login as typed is at most 320 (the exchange's own bound; ``access`` folds and checks the
# stored 254), a password 1..1024, a rejection reason 1..256.


def _unique_roles(value: list[Any]) -> list[Any]:
    """``uniqueItems: true``, enforced and not only declared: a role named twice is a
    refused request, never a silently de-duplicated one."""
    from pydantic_core import PydanticCustomError

    if len(set(value)) != len(value):
        raise PydanticCustomError("unique_items", "the roles must be distinct")
    return value


_PersonName = Annotated[str, Field(min_length=1, max_length=60)]

def _declare_unique_items(schema: dict[str, Any]) -> None:
    """``uniqueItems: true`` in the document. A callable rather than a dict, so it composes
    with :func:`optional_property` on the one optional role set (``UpdateUserRequest``)."""
    schema["uniqueItems"] = True


def _optional_unique_items(schema: dict[str, Any]) -> None:
    """Both of the above for an optional role set: an outer ``json_schema_extra`` replaces
    the inner one rather than composing with it, so the two are applied together here."""
    optional_property(schema)
    _declare_unique_items(schema)


#: A role set on the wire: a JSON array of distinct ``Role`` values.
_RoleSet = Annotated[
    list[Role],
    AfterValidator(_unique_roles),
    Field(json_schema_extra=_declare_unique_items),
]


class Account(_Object):
    """One account, as the account itself and an administrator read it."""

    user_uid: UserUid
    login: Annotated[str, Field(min_length=1, max_length=254)]
    display_label: Annotated[str, Field(min_length=1, max_length=254)]
    last_name: _PersonName | None
    first_name: _PersonName | None
    middle_name: _PersonName | None
    roles: _RoleSet
    profile_complete: bool
    is_default_credential: bool
    archived_at: datetime | None
    #: Contract 1.36.0 (`UI-A-92`): the instant of the account's latest successful sign-in, read from the access
    #: journal; null when none is recorded (it never signed in, or signed in before the journal began).
    last_sign_in_at: datetime | None


class AccountPage(_Object):
    items: list[Account]
    page: PageInfo


class AuthEventType(str, enum.Enum):
    """Contract 1.36.0 (`UI-A-94`): the kinds of line the access journal holds, the ``access.*`` events of its writer.

    ``sign_in_succeeded``; ``sign_in_blocked`` (a refused attempt that started a cooling-off period, at most one per
    account per period); ``password_changed`` (the account's own); ``password_reset`` (an administrator's temporary
    password); ``role_granted`` and ``role_revoked``; ``sessions_ended`` (an administrator ended every session of the
    account).
    """

    SIGN_IN_SUCCEEDED = "sign_in_succeeded"
    SIGN_IN_BLOCKED = "sign_in_blocked"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    ROLE_GRANTED = "role_granted"
    ROLE_REVOKED = "role_revoked"
    SESSIONS_ENDED = "sessions_ended"


class AuthEvent(_Object):
    """Contract 1.36.0 (`UI-A-94`): one line of the access journal, as it was recorded; never changed.

    Never a password, a token, an address or a login as typed: the account is named by identity and by the label it has
    now, and an event about an account that has since been deleted keeps its identity with a null label.
    """

    event_id: Annotated[str, Field(pattern=rf"^evt_{_ULID}$")]
    event_type: AuthEventType
    occurred_at: datetime
    subject_user_uid: UserUid
    subject_label: Annotated[str, Field(min_length=1, max_length=254)] | None
    actor_user_uid: UserUid | None
    actor_label: Annotated[str, Field(min_length=1, max_length=254)] | None
    source: Literal["api", "host_cli"]
    role: Role | None
    failures: Annotated[int, Field(ge=1)] | None
    default_credential: bool | None


class AuthEventPage(_Object):
    """Contract 1.36.0 (`UI-A-94`): one page of the access journal, newest first."""

    items: list[AuthEvent]
    page: PageInfo


# --- `W61-DISPATCHER-01`: «Диспетчер» -------------------------------------------------

AssignmentUid = TypeAliasType(
    "AssignmentUid", Annotated[str, Field(pattern=rf"^asg_{_ULID}$")]
)


class AssignmentStatus(str, enum.Enum):
    """`W61-DISPATCHER-01`. An assignment's status, derived from its latest event.

    ``assigned`` (after ``assigned`` or ``reassigned``), ``in_progress`` (``started``),
    ``done`` (``completed``), ``returned`` and ``cancelled``. ``done`` and ``cancelled`` are
    terminal.
    """

    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class AssignmentEventKind(str, enum.Enum):
    """`W61-DISPATCHER-01`. One event of an assignment's append-only history."""

    ASSIGNED = "assigned"
    STARTED = "started"
    COMPLETED = "completed"
    RETURNED = "returned"
    REASSIGNED = "reassigned"
    CANCELLED = "cancelled"


class AssignmentTransitionKind(str, enum.Enum):
    """`W61-DISPATCHER-01`. The events a transition may append: every kind but ``assigned``."""

    STARTED = "started"
    COMPLETED = "completed"
    RETURNED = "returned"
    REASSIGNED = "reassigned"
    CANCELLED = "cancelled"


_AssignmentText = Annotated[str, Field(min_length=1, max_length=2000)]


class CreateAssignmentRequest(_Object):
    """`W61-DISPATCHER-01`. Give a project, or one document of it, to an active expert."""

    project_uid: ProjectUid
    document_uid: DocumentUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    assignee_user_uid: UserUid
    note: _AssignmentText = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class TransitionAssignmentRequest(_Object):
    """`W61-DISPATCHER-01`. One move along an assignment's history."""

    kind: AssignmentTransitionKind
    reason: _AssignmentText = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    new_assignee_user_uid: UserUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class Assignment(_Object):
    """`W61-DISPATCHER-01`. One assignment as it now stands."""

    assignment_uid: AssignmentUid
    project_uid: ProjectUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_uid: DocumentUid | None
    document_title: Annotated[str, Field(min_length=1, max_length=400)] | None
    assignee_user_uid: UserUid
    assignee_label: Annotated[str, Field(min_length=1, max_length=254)]
    created_by_user_uid: UserUid
    created_by_label: Annotated[str, Field(min_length=1, max_length=254)]
    note: _AssignmentText | None
    status: AssignmentStatus
    status_reason: _AssignmentText | None
    created_at: datetime
    updated_at: datetime


class AssignmentEvent(_Object):
    """`W61-DISPATCHER-01`. One recorded event; never changed."""

    event_id: Annotated[str, Field(pattern=rf"^evt_{_ULID}$")]
    kind: AssignmentEventKind
    actor_user_uid: UserUid
    actor_label: Annotated[str, Field(min_length=1, max_length=254)]
    reason: _AssignmentText | None
    new_assignee_user_uid: UserUid | None
    new_assignee_label: Annotated[str, Field(min_length=1, max_length=254)] | None
    occurred_at: datetime


class AssignmentDetail(_Object):
    """`W61-DISPATCHER-01`. One assignment and its whole history, oldest event first."""

    assignment: Assignment
    history: list[AssignmentEvent]


class AssignmentStatusCount(_Object):
    """Contract 1.36.0: how many assignments stand in one status."""

    status: AssignmentStatus
    count: Annotated[int, Field(ge=0)]


class AssignmentPage(_Object):
    items: list[Assignment]
    page: PageInfo
    #: Contract 1.36.0: how many assignments the caller may read under every filter of the request, the status included.
    total: Annotated[int, Field(ge=0)]
    #: Contract 1.36.0: every status with its count over the request's scope filters (`project_uid`, `mine` and what the
    #: caller may read) and not its `status` filter, in the order of ``AssignmentStatus``; a status with none is 0. These
    #: are the numbers of the dispatcher's state chips: each is what choosing that status would list.
    overview: list[AssignmentStatusCount]


class ProductVersion(_Object):
    product_version: str
    build_id: str
    contract_version: str
    #: `CMP-SEAL-C0` (ADR-0025 decision 23). The comparison modules this deployment serves; see
    #: :class:`ComparisonModules`. Always sent from `1.9.0`; a client that finds it absent treats
    #: the set as ``none``.
    comparison_modules: ComparisonModules = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ReleaseNoteKind(str, enum.Enum):
    new = "new"
    improved = "improved"
    fixed = "fixed"


class ReleaseNoteItem(_Object):
    kind: ReleaseNoteKind
    screen: str
    where: str
    text: str


class ReleaseEntry(_Object):
    version: str
    revision: Annotated[int, Field(ge=1)]
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    title: str
    is_archive: bool
    range_label: str | None
    items: list[ReleaseNoteItem]


class ReleaseList(_Object):
    items: list[ReleaseEntry]
    whats_new: list[str]


class MarkReleaseNotesReadRequest(_Object):
    read_through: str


class PersonNames(_Object):
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class UpdateMyProfileRequest(_Object):
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    email: Annotated[str, Field(min_length=1, max_length=320)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class UpdateUserRequest(_Object):
    names: PersonNames = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    roles: _RoleSet = Field(default=None, json_schema_extra=_optional_unique_items)  # type: ignore[assignment]


class ResetUserPasswordRequest(_Object):
    temporary_password: Annotated[str, Field(min_length=1, max_length=1024)]


class SubmitRegistrationRequest(_Object):
    login: Annotated[str, Field(min_length=1, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class RegistrationStatusResponse(_Object):
    """`R-56` with its 2026-10-06 addendum: the only status ever shown is ``pending``."""

    status: Literal["pending"]


class RegistrationRequest(_Object):
    request_id: RegistrationRequestId
    login: Annotated[str, Field(min_length=1, max_length=254)]
    display_label: Annotated[str, Field(min_length=1, max_length=66)]
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName | None
    status: RegistrationStatus
    submitted_at: datetime
    decided_at: datetime | None
    decided_by: UserUid | None
    rejection_reason: Annotated[str, Field(min_length=1, max_length=256)] | None
    created_user_uid: UserUid | None


class RegistrationRequestPage(_Object):
    items: list[RegistrationRequest]
    page: PageInfo
    pending_total: Annotated[int, Field(ge=0)]


class ApproveRegistrationRequest(_Object):
    roles: Annotated[_RoleSet, Field(min_length=1)]


class RejectRegistrationRequest(_Object):
    reason: Annotated[str, Field(min_length=1, max_length=256)]


# --- version comparison (`W59-VERSION-COMPARE-01`) -----------------------------------------
#
# The served read model of ``auditmanager.comparison``. Every pairing and every finding label
# is a proposal; nothing here is an approved SheetLink, a finding match or a decision. The
# closed vocabularies are ``Literal`` enums so they stay inline and the schema count small.

_PageNumber = Annotated[int, Field(ge=1)]
_LineIndex = Annotated[int, Field(ge=0, le=1000)]


class ComparedVersion(_Object):
    """One side of a comparison, as far as it was established before any refusal."""

    version_uid: VersionUid
    version_ordinal: Annotated[int, Field(ge=1)]
    page_count: _PageNumber
    sha256: Sha256
    project_stage: ProjectStage | None
    section_code: ProjectSection | None
    run_id: RunId | None
    text_layer_sha256: Sha256 | None


class ComparisonRefusal(_Object):
    """Why two versions are not compared; ``side`` when the reason is one side's."""

    reason: Literal[
        "same_version",
        "version_not_found",
        "different_set",
        "foreign_project",
        "version_not_published",
        "version_order_invalid",
        "stage_unclassified",
        "section_unconfirmed",
        "project_stage_mismatch",
        "confirmed_section_mismatch",
        "stage_pair_invalid",
        "analysis_missing",
        "run_not_of_version",
        "run_not_published",
        "text_unavailable",
        "text_too_large",
    ]
    side: Literal["source", "target"] | None


class SheetPairing(_Object):
    """One sheet of either version and its proposed counterpart, if any."""

    status: Literal["unchanged", "changed", "removed", "added"]
    source_page_number: _PageNumber | None
    target_page_number: _PageNumber | None
    pairing_basis: Literal["exact_text", "similar_text"] | None
    similarity_permille: Annotated[int, Field(ge=0, le=1000)] | None
    shared_line_count: Annotated[int, Field(ge=0)] | None
    suggestion_sha256: Sha256 | None
    #: A present page whose text is blank: it cannot be paired by text.
    textless: bool


class DiffHunk(_Object):
    """One span of a raw line diff; 0-based line indices, end exclusive. An ``equal`` span
    carries its ranges and no lines."""

    tag: Literal["equal", "insert", "delete", "replace"]
    source_start: _LineIndex
    source_end: _LineIndex
    target_start: _LineIndex
    target_end: _LineIndex
    source_lines: Annotated[list[str], Field(max_length=1000)]
    target_lines: Annotated[list[str], Field(max_length=1000)]


class SheetDiff(_Object):
    status: Literal["changed", "removed", "added"]
    source_page_number: _PageNumber | None
    target_page_number: _PageNumber | None
    outcome: Literal["computed", "too_large"]
    too_large_reason: Literal[
        "source_text_too_large",
        "source_text_too_many_lines",
        "target_text_too_large",
        "target_text_too_many_lines",
        "text_not_utf8_encodable",
    ] | None
    source_line_count: _LineIndex | None
    target_line_count: _LineIndex | None
    added_line_count: _LineIndex | None
    removed_line_count: _LineIndex | None
    hunks: list[DiffHunk]
    #: Binds the complete raw diff of the sheet, equal lines included.
    evidence_sha256: Sha256 | None


class SheetDiffPage(_Object):
    """One page of the sheets with text differences; ``next_offset`` is null on the last."""

    offset: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=25)]
    total: Annotated[int, Field(ge=0, le=1000)]
    next_offset: Annotated[int, Field(ge=1)] | None
    items: Annotated[list[SheetDiff], Field(max_length=25)]


class FindingRef(_Object):
    finding_uid: FindingUid
    category: FindingCategory
    finding_text: Annotated[str, Field(min_length=1, max_length=4000)]
    page_numbers: Annotated[list[Annotated[int, Field(ge=1)]], Field(min_length=1)]


class FindingMatchProposal(_Object):
    """A proposed label for a finding of either run; never a decision or a carryover."""

    kind: Literal["unchanged", "probably_fixed", "undetermined", "new"]
    basis: Literal[
        "exact_issue_and_quotes",
        "quotes_absent_from_paired_sheets",
        "quote_still_on_paired_sheet",
        "evidence_sheet_unpaired",
        "evidence_over_limit",
        "no_exact_source_match",
    ]
    source_finding: FindingRef | None
    target_finding: FindingRef | None
    proposal_sha256: Sha256 | None


class CarryoverSourceDecision(_Object):
    """`W59-DECISION-CARRYOVER-01`. The source finding's current verdict-bearing event, as
    the confirming expert is shown it before «Перенести решение»."""

    decision_id: DecisionId
    verdict: Literal["accepted", "rejected"]
    severity: Severity | None
    comment: str | None
    author_label: Annotated[str, Field(min_length=1, max_length=128)]
    recorded_at: datetime


class CarryoverCandidate(_Object):
    """`W59-DECISION-CARRYOVER-01`. An ``unchanged`` proposal whose source finding carries an
    expert decision and whose target finding has no decision event yet. Listing it carries
    nothing: only ``carryOverDecision``, confirmed by an expert, does."""

    proposal_sha256: Sha256
    source_finding_uid: FindingUid
    target_finding_uid: FindingUid
    source_decision: CarryoverSourceDecision


class FindingComparison(_Object):
    status: Literal["compared", "unavailable"]
    unavailable_reason: Literal["findings_over_limit"] | None
    source_finding_count: Annotated[int, Field(ge=0)]
    target_finding_count: Annotated[int, Field(ge=0)]
    proposals: Annotated[list[FindingMatchProposal], Field(max_length=400)]
    #: `W59-DECISION-CARRYOVER-01`. Empty when the findings are unavailable.
    carryover_candidates: Annotated[list[CarryoverCandidate], Field(max_length=200)]


class ApprovedDiffHunk(_Object):
    """One span of an approved pair's raw line diff; 0-based line indices, end exclusive. A
    changed span carries ``hunk_id`` (``<sheet_link_id>:<n>``, ``n`` counting the sheet's
    non-equal spans from 0); an ``equal`` span carries its ranges and neither lines nor an id."""

    tag: Literal["equal", "insert", "delete", "replace"]
    source_start: _LineIndex
    source_end: _LineIndex
    target_start: _LineIndex
    target_end: _LineIndex
    source_lines: Annotated[list[str], Field(max_length=1000)]
    target_lines: Annotated[list[str], Field(max_length=1000)]
    hunk_id: Annotated[str, Field(pattern=rf"^sln_{_ULID}:[0-9]{{1,4}}$")] | None


class ApprovedSheetDiff(_Object):
    """The deterministic differences of one approved pair, recomputed on every read."""

    source_line_count: _LineIndex
    target_line_count: _LineIndex
    added_line_count: _LineIndex
    removed_line_count: _LineIndex
    hunks: list[ApprovedDiffHunk]
    #: Binds the complete raw diff of the sheet and its link, equal lines included.
    evidence_sha256: Sha256


class ApprovedSheetPair(_Object):
    """One active expert approval of a source page against a target page."""

    sheet_link_id: SheetLinkId
    source_page_number: _PageNumber
    target_page_number: _PageNumber
    #: ``verified``: both pages still have the text digest the expert saw. ``text_changed``: a
    #: page is of another text now; no difference is served for any pair of the set.
    state: Literal["verified", "text_changed"]
    #: The proposal the expert confirmed (``SheetPairing.suggestion_sha256``).
    suggestion_sha256: Sha256
    approved_by_label: Annotated[str, Field(min_length=1, max_length=128)]
    approved_at: datetime
    #: The link revision of the approval itself.
    link_revision: Annotated[int, Field(ge=1)]
    #: Present only when the whole set is ``sealed``.
    diff: ApprovedSheetDiff | None


class SummaryStatement(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01` (B2). One statement of a summary and the changed spans of the
    approved pairs it cites, each ``<sheet_link_id>:<n>`` (``n`` counts the sheet's non-equal spans
    from 0), the same identities ``ApprovedDiffHunk.hunk_id`` carries."""

    text: Annotated[str, Field(min_length=1, max_length=1000)]
    hunk_ids: Annotated[
        list[Annotated[str, Field(pattern=rf"^sln_{_ULID}:[0-9]{{1,4}}$")]],
        Field(min_length=1, max_length=50),
    ]


class ComparisonSummary(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01` (B2). A model's summary of the approved pairs, stored beside
    their raw differences and never inside them. ``label`` is fixed and shown with it: no human has
    reviewed the text. ``state`` is ``ready`` or ``rejected`` (the check refused the reply: no
    statements, one ``rejection_reason``; the reply was paid for, so it is recorded). ``provider_mode``
    ``recorded`` is a replayed reply, ``model_identity`` ``recorded`` then, and ``cost_basis``
    ``unmetered``. ``is_current``: it describes the approved set as it stands now."""

    summary_id: Annotated[str, Field(pattern=rf"^evt_{_ULID}$")]
    link_revision: Annotated[int, Field(ge=1)]
    state: Literal["ready", "rejected"]
    rejection_reason: Literal["reply_not_json", "reply_shape_invalid", "unknown_hunk_reference"] | None
    label: Literal["Сводка подготовлена моделью, проверка человеком не проводилась"]
    statements: Annotated[list[SummaryStatement], Field(max_length=20)]
    prompt_version: Annotated[str, Field(min_length=3, max_length=64)]
    provider_mode: Literal["recorded", "live"]
    model_identity: Annotated[str, Field(min_length=1, max_length=128)]
    input_sha256: Sha256
    raw_evidence_seal_sha256: Sha256
    cost_basis: CostBasis
    is_current: bool
    created_by_label: Annotated[str, Field(min_length=1, max_length=128)]
    created_at: datetime


class ApprovedSheetPairs(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01`. The active approvals of the compared pair and their
    deterministic evidence. ``evidence_state``: ``none`` (no active approval), ``sealed`` (the
    differences were recomputed and their seal equals the stored one), ``text_changed``,
    ``seal_changed`` or ``too_large`` (no difference is served, none is truncated)."""

    #: The comparison's current link revision; null when nothing was ever approved.
    link_revision: Annotated[int, Field(ge=1)] | None
    evidence_state: Literal["none", "sealed", "text_changed", "seal_changed", "too_large"]
    #: The recomputed ``raw_evidence_seal`` of the active set; null unless ``sealed``.
    raw_evidence_seal_sha256: Sha256 | None
    items: Annotated[list[ApprovedSheetPair], Field(max_length=32)]
    #: The newest stored summary of the comparison, beside the items and never inside them; null
    #: when none was asked for. Reading it calls no model.
    summary: ComparisonSummary | None = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class VersionComparison(_Object):
    """Two versions of one set compared, or the explicit reason they are not."""

    project_uid: ProjectUid
    document_uid: DocumentUid
    source_version_uid: VersionUid
    target_version_uid: VersionUid
    #: ``version``: the same stage and section on both. ``stage``: a ``P`` source and an
    #: ``R`` target of the same section (the W62 design-to-working comparison).
    mode: Literal["version", "stage"]
    outcome: Literal["compared", "refused"]
    refusal: ComparisonRefusal | None
    source: ComparedVersion | None
    target: ComparedVersion | None
    comparison_sha256: Sha256 | None
    sheets: Annotated[list[SheetPairing], Field(max_length=1000)]
    sheet_diffs: SheetDiffPage | None
    findings: FindingComparison | None
    #: `COMPARE-PERSISTED-SUMMARY-01`. Optional and nullable like ``RunStatus.executor``: a client or a
    #: fixture that predates it still validates, and the server always sends it (null for a refused
    #: comparison).
    approved_pairs: ApprovedSheetPairs | None = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ApproveSheetPairingRequest(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01`. One expert confirmation of one proposed sheet pair.

    The path names the source (older) version; the comparison is recomputed with these values
    when the confirmation arrives and must still propose exactly these pages under exactly this
    ``suggestion_sha256``.
    """

    target_version_uid: VersionUid
    mode: Literal["version", "stage"]
    source_page_number: _PageNumber
    target_page_number: _PageNumber
    suggestion_sha256: Sha256
    source_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    target_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class WithdrawSheetPairingRequest(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01`. The comparison view the withdrawing expert was looking at:
    the text the remaining approved set is sealed over is that view's text."""

    mode: Literal["version", "stage"]
    source_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    target_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class SheetPairingEvent(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01`. The stored approval or withdrawal of one sheet link.
    ``replayed`` is true when this call appended nothing: the same key repeated, or an exact
    repeat of an active link under another key."""

    comparison_id: ComparisonId
    sheet_link_id: SheetLinkId
    event_kind: Literal["approved", "withdrawn"]
    link_revision: Annotated[int, Field(ge=1)]
    replayed: bool
    source_version_uid: VersionUid
    target_version_uid: VersionUid
    source_page_number: _PageNumber
    target_page_number: _PageNumber
    suggestion_sha256: Sha256
    #: The seal of the approved set after this event; null when a withdrawal left nothing, or
    #: nothing that can be sealed.
    raw_evidence_seal_sha256: Sha256 | None
    actor_label: Annotated[str, Field(min_length=1, max_length=128)]
    decided_at: datetime


class GenerateComparisonSummaryRequest(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01` (B2). The comparison view the expert is looking at; the
    command recomputes the sealed evidence in its own transaction and takes nothing else from the
    client: not the input, not the model, not the seal."""

    target_version_uid: VersionUid
    mode: Literal["version", "stage"]
    source_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    target_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class GenerateComparisonSummaryResponse(_Object):
    """`COMPARE-PERSISTED-SUMMARY-01` (B2). The stored summary, new or an exact repeat
    (``replayed``: nothing was called and nothing was appended)."""

    summary: ComparisonSummary
    replayed: bool


class CarryOverDecisionRequest(_Object):
    """`W59-DECISION-CARRYOVER-01`. One expert confirmation of one proposed pair.

    The path names the source (older) version; the comparison is recomputed with these
    values when the confirmation arrives. ``source_decision_id`` is the decision the expert
    was shown: if the source's current verdict has moved on, nothing is carried.
    """

    target_version_uid: VersionUid
    mode: Literal["version", "stage"]
    source_finding_uid: FindingUid
    target_finding_uid: FindingUid
    source_decision_id: DecisionId
    source_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    target_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class CarryOverDecisionResponse(_Object):
    """`W59-DECISION-CARRYOVER-01`. The carried event on the target finding and where it
    came from. ``replayed`` is true when the target already carried exactly this event (an
    exact repeat): nothing was appended and the first confirmation stands."""

    event: DecisionEvent
    current_verdict: Verdict
    replayed: bool
    source_finding_uid: FindingUid
    source_decision_id: DecisionId
    source_version_uid: VersionUid
    source_version_ordinal: Annotated[int, Field(ge=1)]
    target_version_uid: VersionUid
    mode: Literal["version", "stage"]
# --- analysis profiles (`W59-ANALYSIS-SETTINGS-01`) ----------------------------------------
#
# The section-keyed text-profile registry as «Настройки анализа» reads it: one row per section
# in the project-structure order, each with its registered profile or ``null``. Read-only: no
# operation edits a profile or changes its status.


class AnalysisProfileStatus(str, enum.Enum):
    """`W59-ANALYSIS-SETTINGS-01`. Where a registered text profile stands.

    ``draft``: a package ported from the legacy prompts, or authored in this repository, whose
    open questions no lane has answered in writing. ``reviewed``: a package whose open questions a
    lane answered in writing; no human review (`R-146ag`). Every status is executable; the status is
    recorded, never hidden. АР has no status because it has no text profile
    (`PROD-11-AR-V1-V2-REMOVAL-01`): its row carries ``profile: null``.
    """

    DRAFT = "draft"
    REVIEWED = "reviewed"


class AnalysisProfileSourceFile(_Object):
    """One legacy file a package's prompt was ported from, with its SHA-256."""

    path: Annotated[str, Field(min_length=1, max_length=400)]
    sha256: Sha256


class AnalysisProfileSource(_Object):
    """The legacy repository, commit and files a package's prompt was ported from."""

    repository: Annotated[str, Field(min_length=1, max_length=200)]
    commit: Annotated[str, Field(min_length=1, max_length=200)]
    files: Annotated[list[AnalysisProfileSourceFile], Field(min_length=1, max_length=50)]


class AnalysisProfileSummary(_Object):
    """One registered text profile: its identities, version, status and content hashes."""

    analysis_profile_id: AnalysisProfileId
    prompt_bundle_id: PromptBundleId
    profile_version: Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
    status: AnalysisProfileStatus
    prompt_bundle_sha256: Sha256
    content_sha256: Sha256
    #: ``null`` for an authored profile (ПБ), whose prompt was written here, not ported.
    source: AnalysisProfileSource | None


class AnalysisProfileListItem(_Object):
    """One section and its registered profile, or ``null`` when none is registered."""

    section_code: ProjectSection
    section_name: Annotated[str, Field(min_length=1, max_length=200)]
    profile: AnalysisProfileSummary | None


class AnalysisProfileList(_Object):
    """All fifteen sections, in the project-structure order, each with its profile or ``null``."""

    items: Annotated[list[AnalysisProfileListItem], Field(min_length=15, max_length=15)]


# --- optimisation: project price lists and vendor lists (`W60-PRICE-LIST-01`) ------------
#
# The storage slice of «Оптимизация проекта». A money figure exists only as a position of an
# uploaded price list: these shapes carry stored prices and vendor restrictions, never a
# total, a proposal or an inferred price. A unit price crosses the wire as its exact decimal
# text, never as a JSON number that a client would read as a binary float.

#: `W60-PRICE-LIST-01`. The three identities ``contracts/domain/v1/identifiers.json``
#: revision 15 adds: a price-list revision, one of its positions, a vendor-list revision.
PriceListId = TypeAliasType("PriceListId", Annotated[str, Field(pattern=rf"^prl_{_ULID}$")])
PriceListPositionId = TypeAliasType(
    "PriceListPositionId", Annotated[str, Field(pattern=rf"^prp_{_ULID}$")]
)
VendorListId = TypeAliasType("VendorListId", Annotated[str, Field(pattern=rf"^vnl_{_ULID}$")])

#: An ISO 4217 currency code, as the price list or the uploader stated it; never converted.
_CURRENCY = r"^[A-Z]{3}$"
#: The exact unit price as stored: a positive plain decimal below 10^14 with at most six
#: decimals and no trailing zero (``125.5``, ``12345.67``, ``0.000001``).
_UNIT_PRICE = r"^(0|[1-9][0-9]{0,13})(\.[0-9]{0,5}[1-9])?$"


class PriceListFormat(str, enum.Enum):
    """The uploaded file's format, recognised by its bytes and never by its name."""

    CSV = "csv"
    XLSX = "xlsx"


class PriceListField(str, enum.Enum):
    """A position field a header column was mapped to."""

    NAME = "name"
    UNIT = "unit"
    UNIT_PRICE = "unit_price"
    CODE = "code"
    MARK = "mark"
    CURRENCY = "currency"
    VENDOR = "vendor"
    SECTION = "section"


class PriceListRowReason(str, enum.Enum):
    """Why a data row was skipped (the first ten), or a warning on an accepted row (the last).

    A skipped row is never repaired: a price that is not a plain number, not positive, finer
    than six decimals or not below 10^14 is reported, never guessed or rounded.
    """

    NAME_MISSING = "name_missing"
    UNIT_MISSING = "unit_missing"
    PRICE_MISSING = "price_missing"
    PRICE_NOT_A_NUMBER = "price_not_a_number"
    PRICE_NOT_POSITIVE = "price_not_positive"
    PRICE_PRECISION = "price_precision"
    PRICE_TOO_LARGE = "price_too_large"
    CURRENCY_MISSING = "currency_missing"
    CURRENCY_UNRECOGNISED = "currency_unrecognised"
    VALUE_TOO_LONG = "value_too_long"
    SECTION_UNRECOGNISED = "section_unrecognised"


class PriceListCurrencySource(str, enum.Enum):
    """Where an accepted row's currency came from: its cell, the price header, the default."""

    COLUMN = "column"
    PRICE_HEADER = "price_header"
    DEFAULT = "default"


class PriceListColumn(_Object):
    """One header column mapped to a field: its 1-based position and its header text."""

    field: PriceListField
    column: Annotated[int, Field(ge=1, le=200)]
    header: Annotated[str, Field(min_length=1, max_length=200)]


class PriceListAmbiguousColumn(_Object):
    """An optional field two or more columns could be: none of them was read."""

    field: PriceListField
    headers: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=200)]], Field(min_length=2)
    ]


class PriceListRowNote(_Object):
    """One source row (as the spreadsheet numbers it) and why it is reported."""

    row: Annotated[int, Field(ge=1)]
    reason: PriceListRowReason


class PriceListReasonCount(_Object):
    reason: PriceListRowReason
    count: Annotated[int, Field(ge=1)]


class PriceListCurrencySourceCount(_Object):
    source: PriceListCurrencySource
    count: Annotated[int, Field(ge=1)]


class PriceListParseReport(_Object):
    """How one file was read: deterministic, so the same bytes always report the same.

    ``skipped`` and ``warnings`` list at most the first 1000 rows each;
    ``skipped_by_reason`` and ``warnings_by_reason`` always count every one.
    """

    report_version: Literal[1]
    format: PriceListFormat
    #: The first sheet's name (XLSX), else ``null``.
    sheet: Annotated[str, Field(max_length=200)] | None
    encoding: Literal["utf-8", "utf-8-sig", "utf-16", "cp1251"] | None
    delimiter: Literal[";", "\t", ","] | None
    header_row: Annotated[int, Field(ge=1)]
    columns: Annotated[list[PriceListColumn], Field(min_length=3, max_length=8)]
    ambiguous_columns: Annotated[list[PriceListAmbiguousColumn], Field(max_length=5)]
    ignored_columns: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=200)]], Field(max_length=50)
    ]
    price_header_currency: Annotated[str, Field(pattern=_CURRENCY)] | None
    default_currency: Annotated[str, Field(pattern=_CURRENCY)] | None
    preamble_rows: Annotated[int, Field(ge=0)]
    blank_rows: Annotated[int, Field(ge=0)]
    data_rows: Annotated[int, Field(ge=1, le=20000)]
    accepted_rows: Annotated[int, Field(ge=1, le=20000)]
    skipped_rows: Annotated[int, Field(ge=0, le=20000)]
    skipped_by_reason: list[PriceListReasonCount]
    skipped: Annotated[list[PriceListRowNote], Field(max_length=1000)]
    skipped_listed_in_full: bool
    warnings_by_reason: list[PriceListReasonCount]
    warnings: Annotated[list[PriceListRowNote], Field(max_length=1000)]
    currency_sources: Annotated[list[PriceListCurrencySourceCount], Field(min_length=1)]


class PriceListRevision(_Object):
    """One uploaded price list of a project: an immutable revision; the highest is current.

    ``revision_number`` orders a project's revisions for display and is never an identity;
    ``source_filename`` is the uploaded file's name, display only.
    """

    price_list_id: PriceListId
    project_uid: ProjectUid
    revision_number: Annotated[int, Field(ge=1)]
    is_current: bool
    uploaded_by_user_uid: UserUid
    uploaded_at: datetime
    source_format: PriceListFormat
    source_filename: Annotated[str, Field(min_length=1, max_length=255)]
    media_type: Literal[
        "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    size_bytes: Annotated[int, Field(ge=1, le=10485760)]
    sha256: Sha256
    default_currency: Annotated[str, Field(pattern=_CURRENCY)] | None
    data_row_count: Annotated[int, Field(ge=1, le=20000)]
    accepted_row_count: Annotated[int, Field(ge=1, le=20000)]
    skipped_row_count: Annotated[int, Field(ge=0, le=20000)]


class PriceListRevisionList(_Object):
    """Every price-list revision of one project, newest first; the first one is current."""

    items: list[PriceListRevision]


class PriceListPosition(_Object):
    """One parsed position. ``row_number`` is its source row, never an identity."""

    price_list_position_id: PriceListPositionId
    row_number: Annotated[int, Field(ge=1)]
    code: Annotated[str, Field(min_length=1, max_length=200)] | None
    name: Annotated[str, Field(min_length=1, max_length=2000)]
    mark: Annotated[str, Field(min_length=1, max_length=500)] | None
    unit: Annotated[str, Field(min_length=1, max_length=50)]
    unit_price: Annotated[str, Field(pattern=_UNIT_PRICE)]
    currency: Annotated[str, Field(pattern=_CURRENCY)]
    vendor: Annotated[str, Field(min_length=1, max_length=500)] | None
    section_code: ProjectSection | None


class PriceListPositionPage(_Object):
    """One page of a revision's positions in source-row order, with the revision's report."""

    revision: PriceListRevision
    parse_report: PriceListParseReport
    items: Annotated[list[PriceListPosition], Field(max_length=500)]
    offset: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=500)]
    total: Annotated[int, Field(ge=1, le=20000)]
    next_offset: Annotated[int, Field(ge=1)] | None


class UploadPriceListRequest(_Object):
    """`W60-PRICE-LIST-01`. The multipart body of ``uploadPriceList``.

    ``file`` is the price list (CSV, or an XLSX whose first sheet is read), at most 10 MiB;
    ``default_currency`` applies to rows whose currency neither their own cell nor the price
    column's header names.
    """

    file: Annotated[UploadFile, WithJsonSchema(_BINARY_STRING)]
    default_currency: Annotated[str, Field(pattern=_CURRENCY)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class VendorListMode(str, enum.Enum):
    """``list``: these entries apply (none at all is an explicit "no restriction").
    ``inherit``: a project revision that removes the override; the global list applies."""

    LIST = "list"
    INHERIT = "inherit"


class VendorListScope(str, enum.Enum):
    GLOBAL = "global"
    PROJECT = "project"


class VendorListSource(str, enum.Enum):
    """Which revision applies to a project's section: its own list, the global one, or none."""

    PROJECT = "project"
    GLOBAL = "global"
    NONE = "none"


class VendorListEntry(_Object):
    """One entry: the material or equipment group it covers, the allowed vendor, a note."""

    material: Annotated[str, Field(min_length=1, max_length=500)] | None = Field(
        default=None, json_schema_extra=optional_property
    )
    vendor: Annotated[str, Field(min_length=1, max_length=500)]
    note: Annotated[str, Field(min_length=1, max_length=1000)] | None = Field(
        default=None, json_schema_extra=optional_property
    )


class VendorListRevision(_Object):
    """One immutable revision of a section's vendor list, global or of one project."""

    vendor_list_id: VendorListId
    scope: VendorListScope
    project_uid: ProjectUid | None
    section_code: ProjectSection
    mode: VendorListMode
    revision_number: Annotated[int, Field(ge=1)]
    entries: Annotated[list[VendorListEntry], Field(max_length=500)]
    set_by_user_uid: UserUid
    set_at: datetime


class SectionVendorList(_Object):
    """One section's vendor list as it applies to a project, with both scopes' latest."""

    section_code: ProjectSection
    source: VendorListSource
    effective: VendorListRevision | None
    global_revision: VendorListRevision | None
    project_revision: VendorListRevision | None


class EffectiveVendorLists(_Object):
    """All fifteen sections' vendor lists as they apply to one project, in section order."""

    project_uid: ProjectUid
    items: Annotated[list[SectionVendorList], Field(min_length=15, max_length=15)]


class SetGlobalVendorListRequest(_Object):
    """`W60-PRICE-LIST-01`. A section's global vendor list, as a whole new revision.

    ``expected_vendor_list_id``, when present, is the revision the caller read (``null``:
    there was none); a different latest revision is ``conflict`` and nothing is written.
    """

    entries: Annotated[list[VendorListEntry], Field(max_length=500)]
    expected_vendor_list_id: VendorListId | None = Field(
        default=None, json_schema_extra=optional_property
    )


class SetProjectVendorListRequest(_Object):
    """`W60-PRICE-LIST-01`. A project's own vendor list for a section, or its removal.

    ``mode: inherit`` takes ``entries: []`` and removes the override. ``expected_vendor_list_id``
    as for :class:`SetGlobalVendorListRequest`, for this project's revisions.
    """

    mode: VendorListMode
    entries: Annotated[list[VendorListEntry], Field(max_length=500)]
    expected_vendor_list_id: VendorListId | None = Field(
        default=None, json_schema_extra=optional_property
    )
# --- the priced specification (`W60-OPT-MATCH-01`) -------------------------------------------
#
# «Спецификация и цены»: the specification rows of a document set's current AR version, read
# from the newest published run's saved text and matched to the project's current price list
# (``auditmanager.optimisation``). A price and an amount appear only on a row matched to exactly
# one position in the same unit with a numeric quantity; totals are per currency over those
# rows only. Money is exact decimal text, never a JSON number and never rounded. The closed
# vocabularies are ``Literal`` enums so they stay inline; the price-list identities are the
# price-list reseal's (`PriceListId`, `PriceListPositionId`).

_SpecificationDecimal = Annotated[str, Field(pattern=r"^-?[0-9]+(\.[0-9]+)?$", max_length=48)]
_SpecificationCurrency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
_SpecificationPage = Annotated[int, Field(ge=1)]
_SpecificationLine = Annotated[int, Field(ge=1)]
_SpecificationCount = Annotated[int, Field(ge=0)]
_SpecificationUnit = Literal["шт", "м", "м2", "м3", "кг", "т", "компл", "п.м"]
_SpecificationSkipReason = Literal[
    "table_header_ambiguous",
    "text_before_first_row",
    "continuation_limit",
    "anchor_ambiguous",
    "position_missing",
    "name_missing",
    "column_numbering",
    "rows_over_limit",
]
_SpecificationExclusion = Literal[
    "no_position", "unit_mismatch", "row_unit_missing", "ambiguous", "quantity_not_numeric",
]


class SpecificationPriceListRef(_Object):
    """The price-list revision the rows were matched against: the project's current one."""

    price_list_id: PriceListId
    #: Display order within the project, never an identity.
    revision_number: Annotated[int, Field(ge=1)]
    #: The uploaded file's base name, for display only.
    source_filename: Annotated[str, Field(min_length=1, max_length=255)]
    uploaded_at: datetime
    default_currency: _SpecificationCurrency | None
    position_count: Annotated[int, Field(ge=1, le=20000)]


class SpecificationSkipCounts(_Object):
    """Lines inside detected tables that became neither a row nor part of one, by reason."""

    table_header_ambiguous: _SpecificationCount
    text_before_first_row: _SpecificationCount
    continuation_limit: _SpecificationCount
    anchor_ambiguous: _SpecificationCount
    position_missing: _SpecificationCount
    name_missing: _SpecificationCount
    column_numbering: _SpecificationCount
    rows_over_limit: _SpecificationCount


class SpecificationSkippedLine(_Object):
    """One skipped line: where it is, why, and the start of its text."""

    page_number: _SpecificationPage
    line: _SpecificationLine
    reason: _SpecificationSkipReason
    excerpt: Annotated[str, Field(max_length=200)]


class SpecificationTable(_Object):
    """One detected specification table: its header lines and the Form-7 columns it names."""

    ordinal: Annotated[int, Field(ge=1)]
    page_number: _SpecificationPage
    header_line_start: _SpecificationLine
    header_line_end: _SpecificationLine
    columns: Annotated[
        list[Literal[
            "position", "name", "type_mark", "code", "manufacturer", "unit", "quantity",
            "mass", "note",
        ]],
        Field(min_length=3, max_length=9),
    ]
    #: The unit the quantity header carries (``Кол-во, шт.``) when there is no unit column.
    implicit_unit: _SpecificationUnit | None
    status: Literal["parsed", "header_ambiguous"]
    row_count: _SpecificationCount


class SpecificationExtractionSummary(_Object):
    """What the extractor found: counts complete, listings capped at 200 each."""

    algorithm: Literal["specification-text-v1"]
    table_count: _SpecificationCount
    row_count: Annotated[int, Field(ge=0, le=10000)]
    skipped_count: _SpecificationCount
    skipped_by_reason: SpecificationSkipCounts
    skipped: Annotated[list[SpecificationSkippedLine], Field(max_length=200)]
    tables: Annotated[list[SpecificationTable], Field(max_length=200)]


class SpecificationMatchCounts(_Object):
    matched: _SpecificationCount
    ambiguous: _SpecificationCount
    unmatched: _SpecificationCount


class SpecificationExclusionCounts(_Object):
    """Rows left out of every total, by the one reason each carries."""

    no_position: _SpecificationCount
    unit_mismatch: _SpecificationCount
    row_unit_missing: _SpecificationCount
    ambiguous: _SpecificationCount
    quantity_not_numeric: _SpecificationCount


class SpecificationCurrencyTotal(_Object):
    """The exact sum of the amounts in one currency; never converted, never rounded."""

    currency: _SpecificationCurrency
    amount: _SpecificationDecimal
    row_count: Annotated[int, Field(ge=1)]


class SpecificationMatching(_Object):
    """Every row's match counted, the totals per currency and what they leave out."""

    algorithm: Literal["price-match-v1", "price-match-v2"]
    counts: SpecificationMatchCounts
    totals: Annotated[list[SpecificationCurrencyTotal], Field(max_length=200)]
    excluded: SpecificationExclusionCounts


class SpecificationPricePosition(_Object):
    """The one price-list position a row is matched to, as the price list states it."""

    price_list_position_id: PriceListPositionId
    #: The source row in the uploaded file, for display only.
    row_number: Annotated[int, Field(ge=1)]
    code: str | None
    name: Annotated[str, Field(min_length=1)]
    mark: str | None
    unit: Annotated[str, Field(min_length=1)]
    unit_price: _SpecificationDecimal
    currency: _SpecificationCurrency
    vendor: str | None


class SpecificationPriceRow(_Object):
    """One specification row and its match. ``amount`` only when it counts in a total."""

    #: A digest of the version, page and line span: provenance, not a stored identity.
    row_id: Annotated[str, Field(pattern=r"^sr-[0-9a-f]{32}$")]
    page_number: _SpecificationPage
    sheet_label: str | None
    line_start: _SpecificationLine
    line_end: _SpecificationLine
    table_ordinal: Annotated[int, Field(ge=1)]
    group: str | None
    position: str | None
    #: The name and, when the row fills them, the type/mark, code and manufacturer cells in
    #: the Form-7 order: a text layer does not separate them.
    name: Annotated[str, Field(min_length=1)]
    unit_text: str | None
    unit: _SpecificationUnit | None
    quantity_text: str | None
    quantity: _SpecificationDecimal | None
    quantity_issue: Literal["not_numeric", "ambiguous"] | None
    mass_text: str | None
    note: str | None
    status: Literal["matched", "ambiguous", "unmatched"]
    reason: Literal["no_position", "unit_mismatch", "row_unit_missing", "several_positions"] | None
    basis: Literal["code", "mark", "name"] | None
    price_position: SpecificationPricePosition | None
    #: At most five candidates in source-row order: the tie, or the positions in another unit.
    candidate_position_ids: Annotated[list[PriceListPositionId], Field(max_length=5)]
    candidate_count: _SpecificationCount
    amount: _SpecificationDecimal | None
    excluded_reason: _SpecificationExclusion | None


class SpecificationRowPage(_Object):
    """One page of the rows; the counts and totals always cover every row."""

    offset: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=200)]
    total: Annotated[int, Field(ge=0, le=10000)]
    next_offset: Annotated[int, Field(ge=1)] | None
    items: Annotated[list[SpecificationPriceRow], Field(max_length=200)]


class SpecificationPrices(_Object):
    """The priced specification of a set's current version, or the state that stops it.

    The states are checked in order -- ``version_unclassified``, ``section_not_ar``,
    ``price_list_missing``, ``analysis_missing``, ``text_unavailable``,
    ``specification_too_large`` -- and each answer carries the facts read before it stopped.
    ``section_not_ar`` is kept so that no value is removed, but it is no longer produced: a version
    confirmed in any of the fifteen sections is read.
    """

    project_uid: ProjectUid
    document_uid: DocumentUid
    version_uid: VersionUid
    version_ordinal: Annotated[int, Field(ge=1)]
    page_count: _SpecificationPage
    state: Literal[
        "ready",
        "version_unclassified",
        "section_not_ar",
        "price_list_missing",
        "analysis_missing",
        "text_unavailable",
        "specification_too_large",
    ]
    project_stage: ProjectStage | None
    section_code: ProjectSection | None
    price_list: SpecificationPriceListRef | None
    run_id: RunId | None
    text_layer_sha256: Sha256 | None
    extraction: SpecificationExtractionSummary | None
    matching: SpecificationMatching | None
    rows: SpecificationRowPage | None


# --- optimisation proposals (`W60-OPT-PROPOSALS-01`) --------------------------------------
#
# The deterministic «более дешёвый аналог» proposals of an optimisation pass, and the experts'
# decisions on them. A proposal is a separate entity beside findings: its own identity, its own
# append-only decisions, its own counts and its own CSV. Every money figure is a price-list
# position's stored price or a product of one with a numeric specification quantity; a saving
# is absent (``null``), never ``0``, when the row's quantity is not a number. Prices, quantities
# and savings cross the wire as exact decimal text, never as JSON numbers.

#: `W60-OPT-PROPOSALS-01`. The three identities ``contracts/domain/v1/identifiers.json``
#: revision 17 adds: a pass, one of its proposals, one decision on a proposal.
OptimisationPassId = TypeAliasType(
    "OptimisationPassId", Annotated[str, Field(pattern=rf"^opp_{_ULID}$")]
)
OptimisationProposalId = TypeAliasType(
    "OptimisationProposalId", Annotated[str, Field(pattern=rf"^opr_{_ULID}$")]
)
ProposalDecisionId = TypeAliasType(
    "ProposalDecisionId", Annotated[str, Field(pattern=rf"^opd_{_ULID}$")]
)

#: A non-negative exact decimal: a quantity (below 10^13, at most six decimals) or a saving
#: (the product of a price difference below 10^14 by such a quantity, at most twelve
#: decimals), plain text with no exponent and no trailing zero.
_EXACT_DECIMAL = r"^(0|[1-9][0-9]{0,26})(\.[0-9]{0,11}[1-9])?$"
#: `UI-B-07` (contract 1.40.0): a percent between 0 and 100 with at most two decimals, no trailing zero.
_PERCENT = r"^(0|100|(0|[1-9][0-9]?)\.[0-9]?[1-9]|[1-9][0-9]?)$"
#: The share of shared words of two names, ``0`` to ``1`` with at most four decimals.
_SIMILARITY = r"^(0|1|0\.[0-9]{0,3}[1-9])$"
_SPEC_ROW_KEY = r"^sr-[0-9a-f]{32}$"


class OptimisationProposalType(str, enum.Enum):
    """The kind of a proposal. Only the deterministic one exists: a cheaper position of the
    same price list. The legacy ``faster_install``, ``simpler_design`` and ``lifecycle`` need
    judgement and wait for the model-assisted slice."""

    CHEAPER_ANALOG = "cheaper_analog"


class ProposalMatchBasis(str, enum.Enum):
    """How the specification row was matched to its current price-list position."""

    CODE = "code"
    MARK = "mark"
    NAME = "name"


class ProposalAnalogBasis(str, enum.Enum):
    """Why the proposed position is the same kind of product: one code family (the leading
    letters of the code or mark, ``ПК 60-12-8`` ~ ``ПК 63-15-8``), or at least half of the
    words of the two names in common."""

    CODE_FAMILY = "code_family"
    NAME_SIMILARITY = "name_similarity"


class ProposalVerdict(str, enum.Enum):
    """An expert's verdict on a proposal. ``revise`` says the analog is right in principle
    and the proposal needs changing; its comment is required. ``revoke`` (`UI-B-12`, contract
    1.35.0, «Снять решение») withdraws the decision in force: it is one more appended event, it
    takes the proposal back to ``pending``, and it is refused (``409 conflict``,
    ``conflict_reason`` ``no_decision_to_revoke``) when no decision stands."""

    ACCEPT = "accept"
    REJECT = "reject"
    REVISE = "revise"
    REVOKE = "revoke"


class ProposalDecisionState(str, enum.Enum):
    """A proposal's current decision: its latest verdict, or ``pending`` when nobody decided.
    Also the ``decision`` filter of ``listOptimisationProposals``."""

    PENDING = "pending"
    ACCEPT = "accept"
    REJECT = "reject"
    REVISE = "revise"


class ProposalDecisionCounts(_Object):
    """How many of a pass's proposals stand in each decision state; the four sum to the
    pass's ``proposal_count``. These are the proposals' own counts, never finding counts."""

    pending: Annotated[int, Field(ge=0, le=30000)]
    accept: Annotated[int, Field(ge=0, le=30000)]
    reject: Annotated[int, Field(ge=0, le=30000)]
    revise: Annotated[int, Field(ge=0, le=30000)]


class OptimisationPass(_Object):
    """One optimisation pass, pinned to everything it read: the version, its published run
    and that run's text layer, the price-list revision and the vendor-list revision (global
    or the project's own, ``vendor_list_source``), and the three algorithm versions.

    ``version_ordinal`` (contract 1.37.0, `UI-B-14`) is the display order of the version the pass was started over
    («V2»), so a screen can name an earlier version's pass; it is never an identity."""

    optimisation_pass_id: OptimisationPassId
    project_uid: ProjectUid
    document_uid: DocumentUid
    version_uid: VersionUid
    version_ordinal: Annotated[int, Field(ge=1)]
    run_id: RunId
    text_layer_sha256: Sha256
    price_list_id: PriceListId
    vendor_list_id: VendorListId
    vendor_list_source: VendorListScope
    extraction_algorithm: Annotated[str, Field(min_length=1, max_length=64)]
    match_algorithm: Annotated[str, Field(min_length=1, max_length=64)]
    generator_version: Annotated[str, Field(min_length=1, max_length=64)]
    specification_row_count: Annotated[int, Field(ge=0, le=10000)]
    matched_row_count: Annotated[int, Field(ge=0, le=10000)]
    proposed_row_count: Annotated[int, Field(ge=0, le=10000)]
    proposal_count: Annotated[int, Field(ge=0, le=30000)]
    decision_counts: ProposalDecisionCounts
    started_by_user_uid: UserUid
    started_by_label: Annotated[str, Field(min_length=1, max_length=254)]
    started_at: datetime


class OptimisationPassList(_Object):
    """A project's passes, newest first."""

    items: Annotated[list[OptimisationPass], Field(max_length=100)]


class ProposalPosition(_Object):
    """A price-list position a proposal names. ``row_number`` is its source row, never an
    identity."""

    price_list_position_id: PriceListPositionId
    row_number: Annotated[int, Field(ge=1)]
    code: Annotated[str, Field(min_length=1, max_length=200)] | None
    name: Annotated[str, Field(min_length=1, max_length=2000)]
    mark: Annotated[str, Field(min_length=1, max_length=500)] | None
    vendor: Annotated[str, Field(min_length=1, max_length=500)] | None


class ProposalDecision(_Object):
    """One appended expert decision. Never changed; the proposal's latest one is current -- unless
    that is a ``revoke``, which withdrew the decision before it and left the proposal ``pending``.

    ``carried_from`` (`UI-B-14`) is ``null`` for a decision an expert made directly and names the source when the
    expert carried it over from an earlier version's pass; the decision is the confirming expert's own either way
    (``actor_user_uid``), and a later decision on the proposal supersedes it like any other."""

    proposal_decision_id: ProposalDecisionId
    optimisation_proposal_id: OptimisationProposalId
    verdict: ProposalVerdict
    comment: Annotated[str, Field(min_length=1, max_length=2000)] | None
    actor_user_uid: UserUid
    actor_label: Annotated[str, Field(min_length=1, max_length=254)]
    decided_at: datetime
    carried_from: ProposalDecisionCarriedFrom | None


class OptimisationProposal(_Object):
    """One proposal: a specification row matched to ``matched_position`` and a cheaper
    ``proposed_position`` of the same price-list revision, in the same unit and currency,
    from a vendor on the pass's vendor list.

    ``row_text`` is the description as the saved text layer shows it (name, mark, code and
    manufacturer cells run together); page, sheet and lines say where it is. Both unit prices
    are the positions' stored prices. ``saving`` is ``(current_unit_price −
    proposed_unit_price) × quantity`` and is ``null`` -- never ``0`` -- when ``quantity`` is
    ``null`` because the row's quantity text is not a plain number. ``ordinal`` is a display
    order inside the pass, never an identity.
    """

    optimisation_proposal_id: OptimisationProposalId
    optimisation_pass_id: OptimisationPassId
    ordinal: Annotated[int, Field(ge=1, le=30000)]
    proposal_type: OptimisationProposalType
    spec_row_key: Annotated[str, Field(pattern=_SPEC_ROW_KEY)]
    page_number: Annotated[int, Field(ge=1)]
    sheet_label: Annotated[str, Field(min_length=1, max_length=100)] | None
    line_start: Annotated[int, Field(ge=1)]
    line_end: Annotated[int, Field(ge=1)]
    table_ordinal: Annotated[int, Field(ge=1)]
    row_position: Annotated[str, Field(min_length=1, max_length=100)] | None
    row_text: Annotated[str, Field(min_length=1, max_length=8000)]
    matched_position: ProposalPosition
    matched_basis: ProposalMatchBasis
    proposed_position: ProposalPosition
    analog_basis: ProposalAnalogBasis
    name_similarity: Annotated[str, Field(pattern=_SIMILARITY)]
    proposed_vendor: Annotated[str, Field(min_length=1, max_length=500)]
    unit: Annotated[str, Field(min_length=1, max_length=50)]
    quantity: Annotated[str, Field(pattern=_EXACT_DECIMAL)] | None
    quantity_text: Annotated[str, Field(min_length=1, max_length=100)] | None
    current_unit_price: Annotated[str, Field(pattern=_UNIT_PRICE)]
    proposed_unit_price: Annotated[str, Field(pattern=_UNIT_PRICE)]
    currency: Annotated[str, Field(pattern=_CURRENCY)]
    saving: Annotated[str, Field(pattern=_EXACT_DECIMAL)] | None
    rationale: Annotated[str, Field(min_length=1, max_length=10000)]
    current_verdict: ProposalDecisionState
    current_decision: ProposalDecision | None
    #: `UI-B-07` (contract 1.40.0): how much cheaper the proposed unit price is than the current one, in percent of the
    #: current unit price, rounded half up to two decimals; absent when the current unit price is zero.
    saving_percent: Annotated[str, Field(pattern=_PERCENT)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)


class OptimisationProposalPage(_Object):
    """One page of a pass's proposals in ordinal order. ``total`` counts the proposals the
    ``decision`` filter admits; the pass's ``decision_counts`` count all of them."""

    optimisation_pass: OptimisationPass
    decision: ProposalDecisionState | None
    items: Annotated[list[OptimisationProposal], Field(max_length=200)]
    offset: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=200)]
    total: Annotated[int, Field(ge=0, le=30000)]
    next_offset: Annotated[int, Field(ge=1)] | None


class DecideOptimisationProposalRequest(_Object):
    """`W60-OPT-PROPOSALS-01`. An expert's verdict on a proposal, with a comment that
    ``revise`` requires."""

    verdict: ProposalVerdict
    comment: Annotated[str, Field(min_length=1, max_length=2000)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class CarryOverProposalDecisionsRequest(_Object):
    """`UI-B-14` (contract 1.37.0): the pass whose decisions in force are carried into the pass of the path."""

    source_optimisation_pass_id: OptimisationPassId


class ProposalDecisionCarryoverReport(_Object):
    """`UI-B-14`: what a carryover did. Every decision in force of the source pass (``source_decided``) is counted in
    exactly one of four outcomes: ``carried`` (appended to the target pass), ``target_decided`` (the one proposal of the
    target with the same content already has an event, which stands), ``ambiguous`` (more than one proposal of either
    pass has that content, so nothing is guessed) or ``unmatched`` (no proposal of the target pass has it).
    ``source_version_ordinal`` is the display order of the source's version («V2»), never an identity."""

    optimisation_pass_id: OptimisationPassId
    source_optimisation_pass_id: OptimisationPassId
    source_version_ordinal: Annotated[int, Field(ge=1)]
    source_decided: Annotated[int, Field(ge=0, le=30000)]
    carried: Annotated[int, Field(ge=0, le=30000)]
    target_decided: Annotated[int, Field(ge=0, le=30000)]
    ambiguous: Annotated[int, Field(ge=0, le=30000)]
    unmatched: Annotated[int, Field(ge=0, le=30000)]


class ProposalDecisionResult(_Object):
    """The decision appended (or replayed) and the proposal as it now stands."""

    decision: ProposalDecision
    proposal: OptimisationProposal


class ProposalDecisionList(_Object):
    """Every decision of one proposal, oldest first; the last is current."""

    items: list[ProposalDecision]


class AcceptedOptimisationProposal(_Object):
    """`UI-B-27` (contract 1.35.0): one proposal whose decision in force is an acceptance, with where it belongs
    (project, document set, version, the version's section) and the acceptance itself.

    A row is named by its proposal's own identity (``optimisation_proposal_id``); ``page_number`` and ``row_position``
    locate it in the drawing and are never an identity. The prices and the saving are the proposal's own exact decimal
    text; ``saving`` is ``null`` -- never ``0`` -- when the row's quantity is not a plain number. ``saving_percent``
    (`D-346`, contract 1.43.0) is the proposals read's percent of the current unit price, present where ``saving`` is
    ``null`` too."""

    optimisation_proposal_id: OptimisationProposalId
    optimisation_pass_id: OptimisationPassId
    proposal_decision_id: ProposalDecisionId
    proposal_type: OptimisationProposalType
    project_uid: ProjectUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_uid: DocumentUid
    document_name: Annotated[str, Field(min_length=1, max_length=400)]
    version_uid: VersionUid
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    page_number: Annotated[int, Field(ge=1)]
    row_position: Annotated[str, Field(min_length=1, max_length=100)] | None
    row_text: Annotated[str, Field(min_length=1, max_length=8000)]
    matched_name: Annotated[str, Field(min_length=1, max_length=2000)]
    proposed_name: Annotated[str, Field(min_length=1, max_length=2000)]
    proposed_vendor: Annotated[str, Field(min_length=1, max_length=500)]
    unit: Annotated[str, Field(min_length=1, max_length=50)]
    quantity: Annotated[str, Field(pattern=_EXACT_DECIMAL)] | None
    current_unit_price: Annotated[str, Field(pattern=_UNIT_PRICE)]
    proposed_unit_price: Annotated[str, Field(pattern=_UNIT_PRICE)]
    currency: Annotated[str, Field(pattern=_CURRENCY)]
    saving: Annotated[str, Field(pattern=_EXACT_DECIMAL)] | None
    comment: Annotated[str, Field(min_length=1, max_length=2000)] | None
    actor_label: Annotated[str, Field(min_length=1, max_length=254)]
    decided_at: datetime
    #: `D-335` (contract 1.39.0): as on ``ProposalDecision`` -- ``null`` for an acceptance an expert made directly, the
    #: source decision (with its pass, version and the version's display ordinal) for one carried over from an earlier
    #: version's pass.
    carried_from: ProposalDecisionCarriedFrom | None
    #: `D-346` (contract 1.43.0): as on ``OptimisationProposal`` -- how much cheaper the proposed unit price is than the
    #: current one, in percent of the current unit price, rounded half up to two decimals; the same figure the proposals
    #: read states. It does not wait for a numeric quantity, so it is present where ``saving`` is ``null``; absent only when
    #: the current unit price is zero.
    saving_percent: Annotated[str, Field(pattern=_PERCENT)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property)


class AcceptedOptimisationProposalPage(_Object):
    """`UI-B-27`: one page of the accepted proposals, newest acceptance first, and how many match the filters."""

    items: list[AcceptedOptimisationProposal]
    page: PageInfo
    total: Annotated[int, Field(ge=0)]
# --- the section's combined specification (`W63-SECTION-FORM7-01`) ---------------------------
#
# «Оптимизация разделов»: for one section code, the Form-7 rows of every project whose document
# set's *current* version an expert confirmed in that section, each priced from **its own**
# project's current price list (``auditmanager.optimisation.section_specification``). The
# section code is a filter, not an identity: every row names its project, set and version, rows
# are never merged across projects, and totals exist per project and per currency only -- there
# is deliberately no section total. The row, the price position, the match counts, the totals
# and the price-list reference are the priced specification's own schemas
# (`W60-OPT-MATCH-01`); money is exact decimal text.

_SectionSourceState = Literal[
    "ready", "analysis_missing", "text_unavailable", "specification_too_large", "not_read",
]


class SectionSpecificationSource(_Object):
    """One document set whose current version is confirmed in the section, and how far it read.

    ``state`` is ``ready`` when the saved text was read and the rows extracted;
    ``analysis_missing`` (no published run) and ``text_unavailable`` (a run without a saved
    text layer) name what is missing; ``specification_too_large`` is the extractor's own row
    bound; ``not_read`` is a set the answer did not read because it is over a bound
    (``SectionSpecification.limit_reason``). The extraction facts are ``null`` until read.
    """

    document_uid: DocumentUid
    display_title: Annotated[str, Field(min_length=1, max_length=400)]
    version_uid: VersionUid
    #: Display order within the set, never an identity.
    version_ordinal: Annotated[int, Field(ge=1)]
    page_count: _SpecificationPage
    project_stage: ProjectStage
    state: _SectionSourceState
    run_id: RunId | None
    text_layer_sha256: Sha256 | None
    row_count: Annotated[int, Field(ge=0, le=10000)] | None
    table_count: _SpecificationCount | None
    skipped_by_reason: SpecificationSkipCounts | None


class SectionSpecificationProject(_Object):
    """One project with member sets: its price list, its sets and its own totals.

    ``price_state`` is ``priced`` (the current price-list revision was read), ``price_list_missing``
    (none uploaded: the rows are served without any match and no figure) or ``not_read`` (over a
    bound). ``matching`` covers this project's rows only and is ``null`` unless ``priced``; its
    totals are per currency and never mixed with another project's.
    """

    project_uid: ProjectUid
    name: Annotated[str, Field(min_length=1, max_length=200)]
    price_state: Literal["priced", "price_list_missing", "not_read"]
    price_list: SpecificationPriceListRef | None
    sources: list[SectionSpecificationSource]
    row_count: Annotated[int, Field(ge=0, le=20000)]
    matching: SpecificationMatching | None


class SectionSpecificationExcludedVersion(_Object):
    """A current version that cannot be placed in a section yet: nobody classified it."""

    project_uid: ProjectUid
    project_name: Annotated[str, Field(min_length=1, max_length=200)]
    document_uid: DocumentUid
    display_title: Annotated[str, Field(min_length=1, max_length=400)]
    version_uid: VersionUid
    version_ordinal: Annotated[int, Field(ge=1)]
    reason: Literal["version_unclassified"]


class SectionSpecificationRow(_Object):
    """One Form-7 row with its full address and, where the project has a price list, its match.

    ``price_status`` is the match (``matched``, ``ambiguous``, ``unmatched``) or
    ``price_list_missing`` when the row's project has no price list: then every match field is
    empty and no price or amount exists. ``amount`` only when the row counts in its project's
    total for its currency.
    """

    project_uid: ProjectUid
    document_uid: DocumentUid
    version_uid: VersionUid
    #: A digest of the version, page and line span: provenance, not a stored identity.
    row_id: Annotated[str, Field(pattern=r"^sr-[0-9a-f]{32}$")]
    page_number: _SpecificationPage
    sheet_label: str | None
    line_start: _SpecificationLine
    line_end: _SpecificationLine
    table_ordinal: Annotated[int, Field(ge=1)]
    group: str | None
    position: str | None
    #: The name and, when the row fills them, the type/mark, code and manufacturer cells in
    #: the Form-7 order: a text layer does not separate them.
    name: Annotated[str, Field(min_length=1)]
    unit_text: str | None
    unit: _SpecificationUnit | None
    quantity_text: str | None
    quantity: _SpecificationDecimal | None
    quantity_issue: Literal["not_numeric", "ambiguous"] | None
    mass_text: str | None
    note: str | None
    price_status: Literal["matched", "ambiguous", "unmatched", "price_list_missing"]
    reason: Literal["no_position", "unit_mismatch", "row_unit_missing", "several_positions"] | None
    basis: Literal["code", "mark", "name"] | None
    price_position: SpecificationPricePosition | None
    #: At most five candidates in source-row order: the tie, or the positions in another unit.
    candidate_position_ids: Annotated[list[PriceListPositionId], Field(max_length=5)]
    candidate_count: _SpecificationCount
    amount: _SpecificationDecimal | None
    excluded_reason: _SpecificationExclusion | None


class SectionSpecificationRowPage(_Object):
    """One page of the rows that survive the text search; the counts cover every row."""

    offset: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=200)]
    total: Annotated[int, Field(ge=0, le=20000)]
    next_offset: Annotated[int, Field(ge=1)] | None
    items: Annotated[list[SectionSpecificationRow], Field(max_length=200)]


class SectionSpecification(_Object):
    """The combined Form-7 specification of one section, project by project.

    ``state`` is ``ready`` or ``section_too_large`` with ``limit_reason`` naming the bound that
    stopped it (``projects`` scanned, member ``sources`` read, ``rows`` held); then the
    membership is still listed with every set ``not_read`` and ``rows`` is ``null`` -- narrowing
    to one project (``project_filter``) is the way in. ``excluded`` lists the current versions
    nobody classified (the first 200; ``excluded_count`` is complete). ``row_count`` counts
    every row in scope and ``rows.total`` the rows the text search keeps. There is no section
    total: the totals live in each project's ``matching``.
    """

    section_code: ProjectSection
    state: Literal["ready", "section_too_large"]
    limit_reason: Literal["projects", "sources", "rows"] | None
    project_filter: ProjectUid | None
    query: Annotated[str, Field(min_length=1, max_length=200)] | None
    extraction_algorithm: Literal["specification-text-v1"]
    match_algorithm: Literal["price-match-v1", "price-match-v2"]
    projects: Annotated[list[SectionSpecificationProject], Field(max_length=1000)]
    excluded: Annotated[list[SectionSpecificationExcludedVersion], Field(max_length=200)]
    excluded_count: _SpecificationCount
    source_count: _SpecificationCount
    row_count: Annotated[int, Field(ge=0, le=20000)]
    rows: SectionSpecificationRowPage | None


# --- executor connections (`EXEC-SEAL-01`, `R-143`) -------------------------------------


class ExecutorKind(str, enum.Enum):
    """How a connection reaches the model: the stand calls an HTTP API, the stand runs a
    command over SSH, or a remote runner pulls the stand's tasks."""

    HTTP_API = "http_api"
    SSH_COMMAND = "ssh_command"
    PULL = "pull"


class ExecutorWorkKind(str, enum.Enum):
    """The kind of model work a route serves: the one run stage that calls a model, and (`CMP-SEAL-C2`,
    ADR-0025 decision 17) the four kinds of model work of the version comparison. Their images ride the
    image channel of `CMP-EXEC-IMAGES-01`; ``comparison_stage_review`` joins with `CMP-SEAL-C4`."""

    TEXT_ANALYSIS = "text_analysis"
    COMPARISON_PAIR_CHECK = "comparison_pair_check"
    COMPARISON_SHEET_CHANGES = "comparison_sheet_changes"
    COMPARISON_SPEC = "comparison_spec"
    COMPARISON_REPORT = "comparison_report"
    COMPARISON_STAGE_REVIEW = "comparison_stage_review"


class ExecutorApiFlavour(str, enum.Enum):
    OPENAI_CHAT = "openai_chat"
    ANTHROPIC_MESSAGES = "anthropic_messages"


class ExecutorTransport(str, enum.Enum):
    DIRECT = "direct"
    VPN = "vpn"
    SSH_TUNNEL = "ssh_tunnel"


class ExecutorSshProfile(str, enum.Enum):
    CLAUDE_CODE_HEADLESS = "claude_code_headless"
    CUSTOM_COMMAND = "custom_command"


class ExecutorPullClient(str, enum.Enum):
    CLAUDE_CODE_SESSION = "claude_code_session"
    AGENT = "agent"


class ExecutorBilling(str, enum.Enum):
    METERED = "metered"
    NOT_METERED = "not_metered"


class ExecutorSecretPurpose(str, enum.Enum):
    API_KEY = "api_key"
    SSH_PRIVATE_KEY = "ssh_private_key"


class ExecutorProbeState(str, enum.Enum):
    REQUESTED = "requested"
    RUNNING = "running"
    FINISHED = "finished"


class ExecutorProbeOutcome(str, enum.Enum):
    OK = "ok"
    IP_REFUSED = "ip_refused"
    CREDENTIAL_REFUSED = "credential_refused"
    MODEL_MISMATCH = "model_mismatch"
    RATE_MISMATCH = "rate_mismatch"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    PROTOCOL_ERROR = "protocol_error"
    SECRET_UNREADABLE = "secret_unreadable"
    HOST_KEY_UNPINNED = "host_key_unpinned"
    HOST_KEY_CHANGED = "host_key_changed"
    NO_RUNNER_ONLINE = "no_runner_online"
    DESTINATION_REFUSED = "destination_refused"
    KIND_NOT_SERVED = "kind_not_served"
    NO_WORKER = "no_worker"


class ExecutorIdentityBasis(str, enum.Enum):
    """``reported``: the response named the model. ``declared``: the executor asserted it."""

    REPORTED = "reported"
    DECLARED = "declared"


class ExecutorRateCheck(str, enum.Enum):
    CHECKED = "checked"
    NOT_REPORTED = "not_reported"
    MISMATCH = "mismatch"
    NOT_METERED = "not_metered"


class ExecutorPinnedModel(_Object):
    """One model of the provider lock a revision may name, with its pinned rates (USD per
    million tokens). The same list validates a revision, so the choice and the refusal agree."""

    pin_id: Annotated[str, Field(min_length=1, max_length=128)]
    input_per_mtok_usd: Annotated[float, Field(ge=0)]
    output_per_mtok_usd: Annotated[float, Field(ge=0)]


class ExecutorRevisionSettings(_Object):
    """The non-secret settings of one revision. Which fields a kind takes is validated by the
    executors context: a field its kind does not use is refused, a missing one is refused."""

    pin_id: Annotated[str, Field(min_length=1, max_length=128)]
    gateway_model: Annotated[str, Field(min_length=1, max_length=200)]
    billing: ExecutorBilling
    allow_client_documents: bool
    timeout_seconds: Annotated[int, Field(ge=1, le=3600)]
    api_flavour: ExecutorApiFlavour = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    base_url: Annotated[str, Field(min_length=1, max_length=2048)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    transport: ExecutorTransport = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    max_parallel_calls: Annotated[int, Field(ge=1, le=16)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    ssh_host: Annotated[str, Field(min_length=1, max_length=253)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    ssh_port: Annotated[int, Field(ge=1, le=65535)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    ssh_user: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    host_key: Annotated[str, Field(min_length=1, max_length=2048)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    ssh_profile: ExecutorSshProfile = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    pull_client: ExecutorPullClient = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    answer_deadline_seconds: Annotated[int, Field(ge=10, le=3600)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    max_claimed_tasks: Annotated[int, Field(ge=1, le=16)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `EXEC2-SEAL-1` (ADR-0026 decision 1). The capacity of the connection, for every kind; absent
    #: means 1. The coupled limits of decision 2 are validated by the executors context.
    max_active_runs: Annotated[int, Field(ge=1, le=16)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


_CAPACITY_NOTE = (
    "`EXEC2-SEAL-1` (ADR-0026 decisions 1 and 2): `max_active_runs` (1 to 16, absent means 1) is the most "
    "units of this connection that may be in use at once, where a Run in `leased`, `running` or `retry_wait` "
    "and a comparison model call in `prepared` or `sent` each count one. A lowered value governs new claims "
    "only and never stops work in flight. The coupled limits are validated on the revision and refused as "
    "`422 validation_failed`: `max_claimed_tasks` of a `pull` connection and a set `max_parallel_calls` of an "
    "`http_api` connection must each be at least `max_active_runs` (field `max_claimed_tasks` or "
    "`max_parallel_calls`, constraint `below_max_active_runs`), and an `ssh_command` connection takes a value "
    "above one only once its wrappers isolate concurrent invocations (field `max_active_runs`, constraint "
    "`capacity_not_supported_for_kind`)."
)


class ReviseExecutorConnectionRequest(ExecutorRevisionSettings):
    __doc__ = (
        "A new immutable revision of a connection: the full settings, never a patch.\n\n" + _CAPACITY_NOTE
    )


class ExecutorProbe(_Object):
    """One probe of a connection revision. ``requested`` until the worker takes it; a probe
    nobody takes within 120 seconds ends as ``no_worker``. ``detail`` is scrubbed and never a
    response body."""

    probe_id: ExecutorProbeId
    connection_id: ExecutorConnectionId
    revision_id: ExecutorRevisionId
    state: ExecutorProbeState
    requested_at: datetime
    requested_by: UserUid
    secret_id: ExecutorSecretId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    outcome: ExecutorProbeOutcome = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reported_model: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    identity_basis: ExecutorIdentityBasis = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    latency_ms: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    http_status: Annotated[int, Field(ge=100, le=599)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    rate_check: ExecutorRateCheck = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    observed_host_key: Annotated[str, Field(min_length=1, max_length=2048)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    detail: Annotated[str, Field(max_length=500)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    started_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    finished_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutorRevision(ExecutorRevisionSettings):
    __doc__ = "One immutable revision of a connection, with its latest probe.\n\n" + _CAPACITY_NOTE

    revision_id: ExecutorRevisionId
    connection_id: ExecutorConnectionId
    revision_no: Annotated[int, Field(ge=1)]
    created_at: datetime
    created_by: UserUid
    host_key_fingerprint: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    latest_probe: ExecutorProbe = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutorSecretMetadata(_Object):
    """What the API ever says about a secret: that it exists, for what, when and by whom, and
    its last four characters. The value is write-only; no operation returns it."""

    secret_id: ExecutorSecretId
    connection_id: ExecutorConnectionId
    purpose: ExecutorSecretPurpose
    last4: Annotated[str, Field(max_length=4)]
    kid: Annotated[str, Field(min_length=1, max_length=64)]
    bound_to_current_revision: bool
    set_at: datetime
    set_by: UserUid
    public_key: Annotated[str, Field(min_length=1, max_length=2048)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorOccupancy(_Object):
    """Used and total capacity of a connection (`EXEC2-SEAL-1`, ADR-0026 decision 1), derived from the
    database at read time and stored nowhere. `capacity` is `max_active_runs` of the current revision
    (1 when absent); `active_runs` counts the connection's Runs in `leased`, `running` or `retry_wait`;
    `active_calls` counts its comparison model calls in `prepared` or `sent` whose attempt is live. Each
    counts one unit, so the connection is full when their sum reaches `capacity`."""

    capacity: Annotated[int, Field(ge=1, le=16)]
    active_runs: Annotated[int, Field(ge=0)]
    active_calls: Annotated[int, Field(ge=0)]


class ExecutorIntegrationAuthorisation(_Object):
    """The administrator's mark that the command-line clients behind a `pull` connection are authorised
    for this integration (`R-149b`, ADR-0026 decision 8): when it was set and by whom. It is one of four
    distinct statuses (installed, authentication valid, authorised for this integration, model probe
    passed) and implies none of the other three."""

    authorised_at: datetime
    authorised_by: UserUid


class ExecutorConnection(_Object):
    __doc__ = (
        "A connection: where a process sends model work. Its secrets are metadata only."
        " `occupancy` (`EXEC2-SEAL-1`) is present once the connection has a current revision;"
        " `integration_authorisation` is present while the administrator's mark is set (`pull` connections only)."
    )

    connection_id: ExecutorConnectionId
    kind: ExecutorKind
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    created_at: datetime
    created_by: UserUid
    secrets: list[ExecutorSecretMetadata]
    routed_work_kinds: list[ExecutorWorkKind]
    archived_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    current_revision_id: ExecutorRevisionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    current_revision_no: Annotated[int, Field(ge=1)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    occupancy: ExecutorOccupancy = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    integration_authorisation: ExecutorIntegrationAuthorisation = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorConnectionList(_Object):
    items: list[ExecutorConnection]
    pinned_models: list[ExecutorPinnedModel]


class ExecutorConnectionDetail(_Object):
    """One connection with every revision (each with its latest probe) and its last 10 probes.

    For a ``pull`` connection (`EXEC-PULL-01`) it also carries the runner tokens' metadata and
    the number of tasks waiting for, or held by, a runner right now. Both are absent for the
    other kinds. A token's value is never here: it was shown once, when it was issued.

    `EXEC2-SEAL-1` (ADR-0026 decision 4): for a ``pull`` connection it also carries its last 10 enrollment grants, newest first, as metadata only (state, expiry, redemption time): the grant's secret and its hash are never here, since the secret was shown once, when it was issued. Absent for the other kinds."""

    connection: ExecutorConnection
    revisions: list[ExecutorRevision]
    probes: Annotated[list[ExecutorProbe], Field(max_length=10)]
    runner_tokens: Annotated[list["RunnerTokenMetadata"], Field(max_length=50)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    open_task_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    enrollments: Annotated[list["ExecutorEnrollmentMetadata"], Field(max_length=10)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class CreateExecutorConnectionRequest(_Object):
    kind: ExecutorKind
    display_name: Annotated[str, Field(min_length=1, max_length=120)]


class SetExecutorSecretRequest(_Object):
    """Write-only. The API seals ``value`` to the stand's public key and never returns it."""

    purpose: ExecutorSecretPurpose
    value: Annotated[str, Field(min_length=8, max_length=8192)] = Field(
        json_schema_extra={"writeOnly": True}
    )


class ExecutorSshKey(_Object):
    """A generated ed25519 pair: the private half is sealed to the connection's SSH endpoint
    and never returned; the public half and its ``authorized_keys`` line are."""

    sealed_private_key: ExecutorSecretMetadata
    public_key: Annotated[str, Field(min_length=1, max_length=2048)]
    authorized_keys_line: Annotated[str, Field(min_length=1, max_length=2200)]


class ExecutorRoute(_Object):
    """Which connection serves one kind of model work, with an optional standby that only an
    administrator configures. The standby is never used implicitly."""

    work_kind: ExecutorWorkKind
    primary_connection_id: ExecutorConnectionId
    set_at: datetime
    set_by: UserUid
    standby_connection_id: ExecutorConnectionId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorRouteList(_Object):
    items: list[ExecutorRoute]


class SetExecutorRouteRequest(_Object):
    work_kind: ExecutorWorkKind
    primary_connection_id: ExecutorConnectionId
    standby_connection_id: ExecutorConnectionId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


# --- executor groups, routing rules, the routing mode and dispatch-time binding (`EXEC2-SEAL-2`) --------
#
# ADR-0026 decisions 10 to 17, owner rulings `R-149a` to `R-149f`. Sealed as contract 1.16.0 with the storage of
# migrations ``0047`` and ``0048``; the operations are implemented by `EXEC2-GROUP-STORE-01` (groups and rules),
# `EXEC2-GROUP-RUN-01` and `EXEC2-GROUP-CMP-01` (admission and dispatch) and `EXEC2-CUTOVER-01` (preview and mode).
# A lane that needs a field stops to the integrator and never edits these. Refusals are the catalogue's existing
# codes with typed details only (``executors.model`` names the values).

class ExecutorBindingState(str, enum.Enum):
    """`EXEC2-SEAL-2` (ADR-0026 decision 12): whether the executor of a Run or a comparison AI job was fixed
    when the work started. `frozen_at_start`: the connection revision was frozen at start (every existing
    row, an explicit connection and a preset), behaviour unchanged. `pending`: the work was admitted by a
    rule or a group and no connection is chosen yet. `bound`: dispatch chose a member and wrote the
    connection revision. The only move is `pending` to `bound`, once; `frozen_at_start` and `bound` are
    terminal."""

    FROZEN_AT_START = "frozen_at_start"
    PENDING = "pending"
    BOUND = "bound"


class ExecutorRoutingMode(str, enum.Enum):
    """`EXEC2-SEAL-2` (ADR-0026 decision 17): which store decides where new model work goes. `legacy` (the
    default): the Primary/Standby route of `setExecutorRoute`. `rules`: the rule of the work kind, targeting
    an executor group. Each change is journalled; work already admitted keeps its own routing."""

    LEGACY = "legacy"
    RULES = "rules"


class ExecutorGroupStrategy(str, enum.Enum):
    """`EXEC2-SEAL-2` (ADR-0026 decision 10): how dispatch picks among the eligible members of a group.
    `least_loaded`: the lowest used/capacity ratio, ties broken by a rotation kept in the database."""

    LEAST_LOADED = "least_loaded"


class ExecutorGroupMemberIssue(str, enum.Enum):
    """`EXEC2-SEAL-2` (ADR-0026 decision 14): why a group member would not be chosen by dispatch right now.
    `revision_changed`: the connection's current revision is not the snapshot the group revision holds.
    `connection_archived`: the connection is archived. `not_served`: this release does not serve the
    connection. `probe_not_ok`: the probe of the current key is not `ok`. `runner_offline`: a `pull`
    connection has no runner online. `at_capacity`: every unit of the connection is in use. `HOSTS-SEAL-1` (ADR-0028):
    `host_disabled`: the member's host is switched off. `model_not_verified`: the agent of the host has not reported the
    model as verified. `model_cooling_down`: the host took the model out of availability after a real refusal."""

    REVISION_CHANGED = "revision_changed"
    CONNECTION_ARCHIVED = "connection_archived"
    NOT_SERVED = "not_served"
    PROBE_NOT_OK = "probe_not_ok"
    RUNNER_OFFLINE = "runner_offline"
    AT_CAPACITY = "at_capacity"
    #: `HOSTS-SEAL-1` (ADR-0028): the member's host is switched off («Использовать»), the model is not verified on the host (the
    #: agent has not reported it as such), or the host took the model out of availability after a real refusal.
    HOST_DISABLED = "host_disabled"
    MODEL_NOT_VERIFIED = "model_not_verified"
    MODEL_COOLING_DOWN = "model_cooling_down"


class ExecutorRoutingPreviewStatus(str, enum.Enum):
    """`EXEC2-SEAL-2` (ADR-0026 decision 17): what the cut-over would do with one work kind. `ready`: a
    one-member group can be made from the primary of the legacy route. `no_route`: the work kind has no
    legacy route, so it gets no rule. `incompatible`: the route exists but cannot become a group (see the
    reason)."""

    READY = "ready"
    NO_ROUTE = "no_route"
    INCOMPATIBLE = "incompatible"


class ExecutorRoutingPreviewIssue(str, enum.Enum):
    """`EXEC2-SEAL-2`: why a legacy route cannot become a one-member group. `connection_archived`: the primary
    is archived. `no_revision`: it has no revision. `kind_not_served`: this release does not serve its kind."""

    CONNECTION_ARCHIVED = "connection_archived"
    NO_REVISION = "no_revision"
    KIND_NOT_SERVED = "kind_not_served"


class ExecutorGroupMember(_Object):
    """One member of a group revision (`EXEC2-SEAL-2`, ADR-0026 decision 10): a connection and the connection
    **revision** snapshotted into the group revision. Dispatch considers the member only while the
    connection's current revision is still this snapshot. `tie_break_order` (1 to 16, unique inside the
    revision) orders members that tie on load before the persisted rotation does."""

    connection_id: ExecutorConnectionId
    connection_revision_id: ExecutorRevisionId
    tie_break_order: Annotated[int, Field(ge=1, le=16)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorGroupRevision(_Object):
    """One immutable revision of an executor group (`EXEC2-SEAL-2`, ADR-0026 decision 10). A group is
    homogeneous: every member revision pins exactly `pin_id` and `gateway_model` and shares `billing` and
    the pinned rates, which are snapshotted here as USD per million tokens. `strategy` is `least_loaded`.
    Mixed groups are refused."""

    group_revision_id: ExecutorGroupRevisionId
    group_id: ExecutorGroupId
    revision_no: Annotated[int, Field(ge=1)]
    pin_id: Annotated[str, Field(min_length=1, max_length=128)]
    gateway_model: Annotated[str, Field(min_length=1, max_length=200)]
    billing: ExecutorBilling
    input_per_mtok_usd: Annotated[float, Field(ge=0)]
    output_per_mtok_usd: Annotated[float, Field(ge=0)]
    strategy: ExecutorGroupStrategy
    members: Annotated[list[ExecutorGroupMember], Field(min_length=1, max_length=16)]
    created_at: datetime
    created_by: UserUid


class ExecutorGroup(_Object):
    """A group of interchangeable executors for one model (`EXEC2-SEAL-2`, ADR-0026 decision 10), with its
    current revision. `routed_work_kinds` are the work kinds whose rule currently targets a revision of this
    group; a group a rule still names cannot be archived. Archiving is one-way and is not deletion."""

    group_id: ExecutorGroupId
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    created_at: datetime
    created_by: UserUid
    current_revision: ExecutorGroupRevision
    routed_work_kinds: list[ExecutorWorkKind]
    archived_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutorGroupList(_Object):
    """Every executor group with its current revision, archived ones included."""

    items: list[ExecutorGroup]


class ExecutorGroupDetail(_Object):
    """One group and every revision of it, newest first."""

    group: ExecutorGroup
    revisions: list[ExecutorGroupRevision]


class CreateExecutorGroupRequest(_Object):
    """A new group and its first revision (`EXEC2-SEAL-2`, ADR-0026 decision 10). The pinned rates are not
    sent: the server takes them from the provider lock for `pin_id`. `strategy` absent means `least_loaded`.
    A member names a connection and the revision of it the group should snapshot; every member must match
    `pin_id`, `gateway_model` and `billing` exactly."""

    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    pin_id: Annotated[str, Field(min_length=1, max_length=128)]
    gateway_model: Annotated[str, Field(min_length=1, max_length=200)]
    billing: ExecutorBilling
    strategy: ExecutorGroupStrategy = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    members: Annotated[list[ExecutorGroupMember], Field(min_length=1, max_length=16)]


class ReviseExecutorGroupRequest(_Object):
    """A new immutable revision of a group: the full settings, never a patch (`EXEC2-SEAL-2`). Work already
    admitted on an earlier revision finishes on it."""

    pin_id: Annotated[str, Field(min_length=1, max_length=128)]
    gateway_model: Annotated[str, Field(min_length=1, max_length=200)]
    billing: ExecutorBilling
    strategy: ExecutorGroupStrategy = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    members: Annotated[list[ExecutorGroupMember], Field(min_length=1, max_length=16)]


class ExecutorGroupMemberStatus(_Object):
    """One member as dispatch sees it right now (`EXEC2-SEAL-2`, ADR-0026 decision 14), derived at read time:
    the snapshot, the connection's current revision, its occupancy, and whether it would be chosen.
    `ineligible_reason` is present exactly when `eligible` is false; when several apply the first of the
    enumeration's order is reported."""

    connection_id: ExecutorConnectionId
    snapshot_revision_id: ExecutorRevisionId
    current_revision_id: ExecutorRevisionId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    occupancy: ExecutorOccupancy = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    eligible: bool
    ineligible_reason: ExecutorGroupMemberIssue = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorGroupCapacity(_Object):
    """The capacity of the current revision of a group, derived from the database at read time and stored
    nowhere (`EXEC2-SEAL-2`). `capacity` sums the capacity of the members still in service (not archived,
    current revision equal to the snapshot); `used` sums their active Runs and calls; `waiting` counts the
    Runs and comparison jobs admitted on any revision of this group that are still `pending`."""

    group_id: ExecutorGroupId
    group_revision_id: ExecutorGroupRevisionId
    members: Annotated[list[ExecutorGroupMemberStatus], Field(min_length=1, max_length=16)]
    capacity: Annotated[int, Field(ge=0)]
    used: Annotated[int, Field(ge=0)]
    waiting: Annotated[int, Field(ge=0)]


class ExecutorRoutingRule(_Object):
    """The current rule of one work kind (`EXEC2-SEAL-2`, ADR-0026 decision 11): the group revision new work of
    that kind is admitted on while the routing mode is `rules`. Rules are append-only; `rule_revision_id`
    identifies this one."""

    work_kind: ExecutorWorkKind
    rule_revision_id: ExecutorRoutingRuleRevisionId
    group_id: ExecutorGroupId
    group_revision_id: ExecutorGroupRevisionId
    set_at: datetime
    set_by: UserUid


class ExecutorRoutingModeState(_Object):
    """The routing mode and its last change (`EXEC2-SEAL-2`, ADR-0026 decision 17). Before the first change the
    mode is `legacy` and the other fields are absent."""

    mode: ExecutorRoutingMode
    mode_event_id: ExecutorRoutingModeEventId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    changed_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    changed_by: UserUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutorRoutingRuleList(_Object):
    """The current rule of each work kind that has one, and the current routing mode."""

    routing_mode: ExecutorRoutingModeState
    items: Annotated[list[ExecutorRoutingRule], Field(max_length=6)]


class SetExecutorRoutingRuleRequest(_Object):
    """Point the rule of a work kind at an immutable group revision (`EXEC2-SEAL-2`). The path names the work
    kind. A group revision other than the current one of an active group is accepted; an archived group's is
    refused."""

    group_revision_id: ExecutorGroupRevisionId


class ExecutorRoutingPreviewItem(_Object):
    """What the cut-over would do with one work kind (`EXEC2-SEAL-2`, ADR-0026 decision 17): a one-member group
    made from the primary of the legacy route, named `proposed_group_name`. A standby is shown and never
    converted into a member."""

    work_kind: ExecutorWorkKind
    status: ExecutorRoutingPreviewStatus
    primary_connection_id: ExecutorConnectionId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    connection_revision_id: ExecutorRevisionId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    standby_connection_id: ExecutorConnectionId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    pin_id: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    gateway_model: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    billing: ExecutorBilling = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    proposed_group_name: Annotated[str, Field(min_length=1, max_length=120)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    incompatible_reason: ExecutorRoutingPreviewIssue = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorRoutingPreview(_Object):
    """The proposed cut-over, computed from the legacy routes without writing anything (`EXEC2-SEAL-2`,
    ADR-0026 decision 17). `preview_digest` binds every item below; the confirmation carries it, and a
    confirmation whose digest is not the one now computed is `409 conflict` (`preview_stale`)."""

    routing_mode: ExecutorRoutingModeState
    preview_digest: Sha256
    items: Annotated[list[ExecutorRoutingPreviewItem], Field(max_length=6)]


class ExecutorRoutingMappingEntry(_Object):
    """One confirmed line of a cut-over: the work kind and the name of the one-member group to create for it."""

    work_kind: ExecutorWorkKind
    group_display_name: Annotated[str, Field(min_length=1, max_length=120)]


class SetExecutorRoutingModeRequest(_Object):
    """Change the routing mode (`EXEC2-SEAL-2`, ADR-0026 decision 17). `rules` is the cut-over and needs the
    `preview_digest` that was shown and a `mapping` that confirms each `ready` work kind to be converted:
    the groups, the rules and the mode are created in one transaction. `legacy` is the rollback and takes
    neither field. Work already admitted by rules finishes on its own group revisions."""

    mode: ExecutorRoutingMode
    preview_digest: Sha256 = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    mapping: Annotated[list[ExecutorRoutingMappingEntry], Field(max_length=6)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorRoutingModeResult(_Object):
    """The routing mode after a change, the groups the change created (a cut-over's one-member groups; none for
    a rollback) and the rules now current."""

    routing_mode: ExecutorRoutingModeState
    groups: Annotated[list[ExecutorGroup], Field(max_length=6)]
    rules: Annotated[list[ExecutorRoutingRule], Field(max_length=6)]


class ExecutorGroupPlan(_Object):
    """What admission froze for a Run or a comparison AI job admitted by a rule or a group (`EXEC2-SEAL-2`,
    ADR-0026 decision 13): the group and its revision, the rule revision when a rule routed it (absent when
    the group was named explicitly), and the planned model with its billing. The connection is not here: it
    is chosen at dispatch (see `ExecutorBinding`)."""

    executor_group_id: ExecutorGroupId
    executor_group_revision_id: ExecutorGroupRevisionId
    routing_rule_revision_id: ExecutorRoutingRuleRevisionId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    pin_id: Annotated[str, Field(min_length=1, max_length=128)]
    gateway_model: Annotated[str, Field(min_length=1, max_length=200)]
    billing: ExecutorBilling


class ExecutorBinding(_Object):
    """The connection and model work was bound to at dispatch (`EXEC2-SEAL-2`, ADR-0026 decision 14). Present
    exactly when `binding_state` is `bound`. It never changes afterwards: an Attempt retry stays on this
    connection revision."""

    connection_id: ExecutorConnectionId
    connection_revision_id: ExecutorRevisionId
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    pin_id: Annotated[str, Field(min_length=1, max_length=128)]
    gateway_model: Annotated[str, Field(min_length=1, max_length=200)]


# --- analysis presets (`ANALYSIS-PRESETS-01`, `R-146av`) ----------------------------------
#
# A preset is a named, saved choice of how a run starts. A run start selects one setting per run,
# the executor connection, so a preset is a name and that connection: no cost limit, no threshold
# and no provider mode (none of them is selectable per run). Revisions are append-only; the list
# shows the current revision of each preset.


class AnalysisPresetState(str, enum.Enum):
    """``active`` can be chosen at run start; ``archived`` is retired for good."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class AnalysisPreset(_Object):
    """The current revision of one preset. ``preset_id`` is the preset for its whole life;
    ``revision_id`` and ``revision_no`` name this revision. The name is a label, never an
    identity."""

    preset_id: PresetId
    revision_id: PresetRevisionId
    revision_no: Annotated[int, Field(ge=1)]
    name: Annotated[str, Field(min_length=1, max_length=120)]
    executor_connection_id: ExecutorConnectionId
    state: AnalysisPresetState
    created_at: datetime
    revised_at: datetime
    revised_by: UserUid


class AnalysisPresetList(_Object):
    """Every preset by its current revision: active ones first by name, then archived ones."""

    items: Annotated[list[AnalysisPreset], Field(max_length=100)]


class SaveAnalysisPresetRequest(_Object):
    """The full settings of a preset, for a new preset and for a new revision alike (never a
    patch)."""

    name: Annotated[str, Field(min_length=1, max_length=120)]
    executor_connection_id: ExecutorConnectionId


# --- the pull channel (`EXEC-PULL-01`, `R-143`) ------------------------------------------
#
# Four operations are the runner's, authenticated by a runner token (its own principal, never a
# user session; the document's one `bearerAuth` scheme carries it), and two are the
# administrator's. The wire is `tools/executor-runner/RUNNER_API.md`.


class ExecutorTaskState(str, enum.Enum):
    """``open -> claimed -> answered | failed``; ``expired`` and ``cancelled`` end an ``open`` or
    ``claimed`` task. A claim whose lease lapses returns the task to ``open``."""

    OPEN = "open"
    CLAIMED = "claimed"
    ANSWERED = "answered"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RunnerCliName(str, enum.Enum):
    """The official command-line clients an agent detects (ADR-0026 decision 8)."""

    CLAUDE = "claude"
    CODEX = "codex"


class RunnerCliAuthState(str, enum.Enum):
    """The authentication state of a client, read only through its official mechanism and reported as a
    closed enumeration: `valid`, `login_required`, or `unknown` (not installed, or the client offers no
    official way to tell). Never a credential, a path or an account name."""

    VALID = "valid"
    LOGIN_REQUIRED = "login_required"
    UNKNOWN = "unknown"


class RunnerExecutionProfile(str, enum.Enum):
    """How the agent answers a task: it runs a command (`command`) or calls a local OpenAI-compatible
    endpoint (`endpoint`)."""

    COMMAND = "command"
    ENDPOINT = "endpoint"


class RunnerFeature(str, enum.Enum):
    """A capability the agent declares; `images` means it serves tasks that carry images."""

    IMAGES = "images"


class RunnerCliHealth(_Object):
    """One client's sanitised health as an agent reports it (`EXEC2-SEAL-1`, ADR-0026 decision 5)."""

    cli: RunnerCliName
    installed: bool
    version: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    auth_state: RunnerCliAuthState


# --- the host protocol (`HOSTS-SEAL-1`, ADR-0028, contract 1.45.0) ---------------------------------------
#
# One agent process serves one host: it reports which providers and models are usable on the machine, takes tasks of any of them
# and answers with the exact model that produced the answer. The same words are encoded by `tools/executor-runner` and by the stand.


class ExecutorProvider(str, enum.Enum):
    """Where a model answer comes from. `claude_code` and `codex` are the command-line clients installed on the host (logged in
    with an account, or with an API key); `anthropic_api`, `openai_api` and `openrouter_api` are direct calls with a key from the
    service key file of the host."""

    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    ANTHROPIC_API = "anthropic_api"
    OPENAI_API = "openai_api"
    OPENROUTER_API = "openrouter_api"


class ExecutorModelAccess(str, enum.Enum):
    """How a call is paid: `subscription` (an account, not metered) or `api` (an API key, billed per token)."""

    SUBSCRIPTION = "subscription"
    API = "api"


class ModelEffort(str, enum.Enum):
    """The reasoning effort a model is asked for. Only these three are ever offered: `xhigh` and `max` are not, and `low` is
    not offered for Opus (`contracts/analysis/v1/model-catalogue.json`)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProviderAuthState(str, enum.Enum):
    """What the agent knows of a provider's login on the host: `valid`, `login_required` or `unknown`."""

    VALID = "valid"
    LOGIN_REQUIRED = "login_required"
    UNKNOWN = "unknown"


class ModelProbeState(str, enum.Enum):
    """What the agent knows of one model: `verified` by a minimal call that answered with an accepted model string,
    `not_verified` (not checked yet) or `failed` (the check ended in a refusal, with a code)."""

    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"
    FAILED = "failed"


class RunnerCatalogueEntry(_Object):
    """One model the stand offers and one provider that may serve it, as handed to an agent: the efforts it may be asked for
    and the exact strings an answer may report as its model (no prefix or date-suffix rule)."""

    provider: ExecutorProvider
    model_id: Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")]
    efforts: Annotated[list[ModelEffort], Field(min_length=1, max_length=3)]
    accepted_reported: Annotated[list[Annotated[str, Field(min_length=1, max_length=200)]], Field(min_length=1, max_length=4)]


class RunnerProviderModelState(_Object):
    """One model of a provider as the agent last checked it. `failure_code` is a lower-case code (`login_required`,
    `quota_exceeded`, `model_not_found`, ...), never the provider's text."""

    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    state: ModelProbeState
    checked_at: datetime
    failure_code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class RunnerProviderReport(_Object):
    """One provider found on the host: how it is paid for, where its client is and which version, whether it is logged in and
    the state of each model of the catalogue on it. No secret, no key and no path to a credential.

    `access` of a command-line client is read from the client's own status command: a subscription login is `subscription`, a
    login with an API key is `api`; a client that is not signed in is reported `subscription` with `auth_state` `login_required`,
    and one signed in by a method the agent does not recognise `api` with `auth_state` `unknown` and no verified model. A direct
    API provider is always `api`: its `auth_state` is `valid` once a model has been verified, `login_required` when the provider
    refused the key, else `unknown`. `cli_path` is left out unless the operator opted in. `accept_images` says whether the
    provider can take a task that carries images on this host."""

    provider: ExecutorProvider
    access: ExecutorModelAccess
    cli_path: Annotated[str, Field(min_length=1, max_length=512)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    cli_version: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    auth_state: ProviderAuthState
    accept_images: bool = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    models: Annotated[list[RunnerProviderModelState], Field(max_length=16)]


class RunnerKeyFileReport(_Object):
    """What the agent found of the service key file of the direct API providers (diagnostics for the server's details; no key and
    no path): `ok` (read), `absent` (no file) or `ignored` (the file exists but was not read), with a lower-case `reason` code
    when it was ignored (`mode_is_not_0600`, `not_owned_by_the_service_user`, `not_a_regular_file`, `unreadable`, `too_large`)."""

    state: Literal["ok", "absent", "ignored"]
    reason: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ExecutorHostSlots(_Object):
    """How many calls of a provider the host may run at once (1 to 16). A provider that is absent has its default: 1 for a
    subscription, 2 for an API key."""

    claude_code: Annotated[int, Field(ge=1, le=16)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    codex: Annotated[int, Field(ge=1, le=16)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    anthropic_api: Annotated[int, Field(ge=1, le=16)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    openai_api: Annotated[int, Field(ge=1, le=16)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    openrouter_api: Annotated[int, Field(ge=1, le=16)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutorTaskUsage(_Object):
    """The token counts of the call that produced an answer, as the agent measured them."""

    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]


class RunnerTokenMetadata(_Object):
    __doc__ = (
        "What the API ever says about a runner token after it was issued: that it exists, its\n"
        "non-secret prefix, when it expires or was revoked, and when and from where it was last seen.\n"
        "The value and its hash are never returned."
        "\n\n`EXEC2-SEAL-1` (ADR-0026 decision 5): the health an agent last reported on this token, as closed "
        "enumerations and bounded strings (no secret, no path to a credential and no document text), and `online`, "
        "the freshness of `last_seen_at` under a bounded threshold, read at the time of the request. All of them "
        "are absent for a token whose runner has not reported."
    )

    token_id: ExecutorRunnerTokenId
    #: Exactly one of ``connection_id`` and ``host_id`` is present (`HOSTS-SEAL-1`): a token of a ``pull`` connection, or the
    #: host token of a server, which serves every system connection of that host.
    connection_id: ExecutorConnectionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    host_id: ExecutorHostId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    token_prefix: Annotated[str, Field(pattern=r"^amr_[0-9a-z]{8}$")]
    created_at: datetime
    created_by: UserUid
    expires_at: datetime
    revoked_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    revoked_by: UserUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    last_seen_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    last_seen_address: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    agent_version: Annotated[str, Field(pattern=r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    clis: Annotated[list[RunnerCliHealth], Field(max_length=8)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    concurrency: Annotated[int, Field(ge=1, le=16)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    execution_profile: RunnerExecutionProfile = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    features: Annotated[list[RunnerFeature], Field(max_length=8)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    health_reported_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    online: bool = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class IssueRunnerTokenRequest(_Object):
    """``expires_in_days`` defaults to 30 when absent."""

    expires_in_days: Annotated[int, Field(ge=1, le=365)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class IssuedRunnerToken(_Object):
    """The token's value, **shown once**: it is stored only as a one-way hash, so no operation
    can return it again. Copy it now; a lost value is revoked and replaced."""

    token: Annotated[str, Field(min_length=56, max_length=56)] = Field(
        json_schema_extra={"readOnly": True}
    )
    #: Always present for a token of a ``pull`` connection; optional in a host document (`HOSTS-SEAL-1`).
    runner_token: RunnerTokenMetadata = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: `HOSTS-SEAL-1`: present when the exchange was made with the grant of a host. The token is then bound to this host, and
    #: `catalogue` is the list of models the agent may be asked for, with their efforts and accepted reported strings.
    host_id: ExecutorHostId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    catalogue: Annotated[list[RunnerCatalogueEntry], Field(max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ClaimExecutorTaskRequest(_Object):
    __doc__ = (
        "The long poll holds the request open for up to ``wait_seconds`` (0 to 25, default 25)."
        "\n\n`EXEC2-SEAL-1` (ADR-0026 decision 3): the optional `runner_instance_id` names the agent process making "
        "the claim. A task already held by a token is redelivered only to the instance that claimed it; a claim "
        "without the field behaves as before. One token is served by one agent process."
    )

    wait_seconds: Annotated[int, Field(ge=0, le=25)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `CMP-SEAL-C0` (ADR-0025 decision 18). The most images one task may carry that this runner
    #: serves; absent means 1, the shape every deployed runner sends today. The server never hands
    #: out a task with more images than declared.
    max_images: Annotated[int, Field(ge=1, le=8)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `EXEC2-SEAL-1`. The agent process making the claim; 8 to 64 characters of ``A-Za-z0-9_-``.
    runner_instance_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


RunnerImageBlobId = TypeAliasType(
    "RunnerImageBlobId", Annotated[str, Field(pattern=r"^blob_[0-9A-HJKMNP-TV-Z]{26}$")],
)


class RunnerImage(_Object):
    """One checked saved PNG, retrievable only by the current runner claim."""

    blob_id: RunnerImageBlobId
    #: `CMP-SEAL-C0` (ADR-0025 decision 18): no longer required. A portal-block crop carries it; a
    #: comparison crop carries ``crop_id`` instead.
    portal_block_id: PortalBlockId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    #: An opaque crop reference, echoed and never parsed.
    crop_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    size_bytes: Annotated[int, Field(ge=1, le=16 * 1024 * 1024)]
    media_type: Literal["image/png"]


class ClaimedExecutorTask(_Object):
    """A task, now claimed by the calling token. ``system`` and ``user_text`` are untrusted,
    document-derived text. ``model`` is the pinned gateway model the answer must declare."""

    task_id: ExecutorTaskId
    claim_expires_at: datetime
    deadline_at: datetime
    model: Annotated[str, Field(min_length=1, max_length=200)]
    system: str
    user_text: str
    output_schema: Annotated[dict[str, Any], WithJsonSchema({"type": "object"})]
    images: Annotated[list[RunnerImage], Field(max_length=8)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `HOSTS-SEAL-1`: present on a task claimed with a host token -- all six members (`provider`, `access`, `model_id`, `effort`,
    #: `timeout_seconds`, `cell_key`) or none. The agent runs exactly this provider, access, model and effort and refuses a model it
    #: does not report as verified (`failExecutorTask`, code `model_not_available`); `model` is then equal to `model_id`.
    #: `LIMITS-01` (contract 1.49.0, `R-153n`): there is no `max_output_tokens`; no answer cap reaches a model. `timeout_seconds` is the
    #: call's window, the constant of its row or kind (`R-153o`).
    provider: ExecutorProvider = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    access: ExecutorModelAccess = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    model_id: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    effort: ModelEffort = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    timeout_seconds: Annotated[int, Field(ge=1, le=7200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    cell_key: StageCellKey = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExtendedExecutorTaskClaim(_Object):
    claim_expires_at: datetime


class SubmitExecutorTaskAnswerRequest(_Object):
    """``output_text`` is the bare JSON document (no code fence, no commentary) the task's
    ``output_schema`` describes. ``model`` is the model that produced it, as the runner declares
    it: an assertion the stand records as such, and holds equal to the connection's pinned model.
    The token counts are the runner's own; the call is recorded as unmetered."""

    output_text: Annotated[str, Field(min_length=1)]
    model: Annotated[str, Field(min_length=1, max_length=200)]
    input_tokens: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    output_tokens: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `HOSTS-SEAL-1`: the answer of a host agent carries `model` (the task's `model_id`), `provider` and `access` (the task's),
    #: the **exact** model string the provider reported (held against `model_id` and the catalogue's `accepted_reported`, never
    #: trimmed) and, when the provider gave a count, `usage`; it sends no top-level token counts.
    provider: ExecutorProvider = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    access: ExecutorModelAccess = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reported_model: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    usage: ExecutorTaskUsage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class FailExecutorTaskRequest(_Object):
    """A lower-case code, optionally followed by ``: `` and a short, payload-free detail."""

    reason: Annotated[str, Field(min_length=1, max_length=512)]


class ExecutorTaskAck(_Object):
    task_id: ExecutorTaskId
    state: ExecutorTaskState


# --- the universal agent: enrollment, health and the install over SSH (`EXEC2-SEAL-1`) ------------
#
# ADR-0026 decisions 4 to 9, owner ruling `R-149b`. Sealed as contract 1.15.0 with the storage of
# migration ``0046``; the operations are implemented by `EXEC2-ENROLL-01` (enrollment, health, package),
# `EXEC2-ENROLL-SSH-01` (the install session) and `EXEC2-CAP-01` (capacity). A lane that needs a field
# stops to the integrator and never edits these. Refusals are the catalogue's existing codes with typed
# details only (``executors.model`` names the values).


class ExecutorEnrollmentState(str, enum.Enum):
    """Derived at read time: `pending` until redeemed, revoked or past `expires_at`."""

    PENDING = "pending"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ExecutorAgentInstallAccess(str, enum.Enum):
    """How the administrator gives the stand SSH access to the host: a key the stand generates (the
    administrator adds its public half to the host) or a pasted private key, which is sealed.
    Passwords are not accepted."""

    GENERATED_KEY = "generated_key"
    PASTED_KEY = "pasted_key"


class ExecutorAgentInstallState(str, enum.Enum):
    """`requested -> scanning -> awaiting_host_key -> installing -> succeeded | failed`."""

    REQUESTED = "requested"
    SCANNING = "scanning"
    AWAITING_HOST_KEY = "awaiting_host_key"
    INSTALLING = "installing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExecutorAgentInstallFailure(str, enum.Enum):
    """The sanitised reason a failed install failed; never a host output, a path or a credential."""

    HOST_UNREACHABLE = "host_unreachable"
    SSH_REFUSED = "ssh_refused"
    HOST_KEY_CHANGED = "host_key_changed"
    HOST_KEY_NOT_CONFIRMED = "host_key_not_confirmed"
    SUDO_PASSWORD_REQUIRED = "sudo_password_required"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    PACKAGE_UNAVAILABLE = "package_unavailable"
    INSTALL_FAILED = "install_failed"
    ENROLLMENT_FAILED = "enrollment_failed"
    SECRET_UNREADABLE = "secret_unreadable"
    NO_WORKER = "no_worker"
    TIMED_OUT = "timed_out"


class ExecutorEnrollmentMetadata(_Object):
    """What the API ever says about an enrollment grant after it was issued (`EXEC2-SEAL-1`, ADR-0026
    decision 4): that it exists, its non-secret prefix, its derived state and its dates. The secret and
    its hash are never returned."""

    enrollment_id: ExecutorEnrollmentId
    #: Exactly one of ``connection_id`` and ``host_id`` is present (`HOSTS-SEAL-1`): a grant for a ``pull`` connection, or for a
    #: host, whose redemption yields a host token and takes no model.
    connection_id: ExecutorConnectionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    host_id: ExecutorHostId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    secret_prefix: Annotated[str, Field(pattern=r"^ame_[0-9a-z]{8}$")]
    state: ExecutorEnrollmentState
    created_at: datetime
    created_by: UserUid
    expires_at: datetime
    redeemed_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    runner_token_id: ExecutorRunnerTokenId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    revoked_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    revoked_by: UserUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class IssuedExecutorEnrollment(_Object):
    """The grant, **shown once**: it is stored only as a one-way hash, so no operation can return the
    `secret` or the `command` that carries it again. `package_version` and `package_sha256` name the agent
    package the command downloads and verifies. Copy the command now; a lost one is replaced by a new
    grant, which revokes this one."""

    secret: Annotated[str, Field(min_length=56, max_length=56)] = Field(
        json_schema_extra={"readOnly": True}
    )
    package_version: AgentPackageVersion
    package_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    command: Annotated[str, Field(min_length=1, max_length=4096)] = Field(
        json_schema_extra={"readOnly": True}
    )
    enrollment: ExecutorEnrollmentMetadata


class RedeemExecutorEnrollmentRequest(_Object):
    """The exchange of an enrollment secret for a runner token. `runner_instance_id` names the agent process
    and makes a repeat of the exchange inside its window idempotent."""

    runner_instance_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")]
    agent_version: Annotated[str, Field(pattern=r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ReportRunnerHealthRequest(_Object):
    """An agent's health report (`EXEC2-SEAL-1`, ADR-0026 decision 5): sanitised enumerations and bounded
    strings only."""

    agent_version: Annotated[str, Field(pattern=r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$")]
    clis: Annotated[list[RunnerCliHealth], Field(max_length=8)]
    concurrency: Annotated[int, Field(ge=1, le=16)]
    execution_profile: RunnerExecutionProfile
    features: Annotated[list[RunnerFeature], Field(max_length=8)]
    runner_instance_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `HOSTS-SEAL-1`: required of a host token, refused of a connection token. The providers found on the host with the
    #: state of each model, and the slots the agent is configured with; the stand keeps the latest snapshot per host and
    #: writes a new one only when it changes.
    providers: Annotated[list[RunnerProviderReport], Field(max_length=8)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    slots: ExecutorHostSlots = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    key_file: RunnerKeyFileReport = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class RunnerHealthAck(_Object):
    """The report was stored on the calling runner token. A host token also gets the catalogue it should check and whether the
    host is switched on («Использовать»)."""

    recorded_at: datetime
    catalogue: Annotated[list[RunnerCatalogueEntry], Field(max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    enabled: bool = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class SetExecutorIntegrationAuthorisationRequest(_Object):
    """`true` sets the mark, `false` clears it. Setting an already set mark or clearing an absent one
    answers the connection as it stands."""

    authorised: bool


def _optional_write_only(schema: dict[str, Any]) -> None:
    """``optional_property`` and ``writeOnly`` for one field: absent is allowed, and no response carries it."""
    optional_property(schema)
    schema["writeOnly"] = True


class CreateExecutorAgentInstallRequest(_Object):
    """Write-only where it carries a key. `private_key` is required for `pasted_key` and refused for
    `generated_key`; the API seals it to the stand's public key and never returns it."""

    access: ExecutorAgentInstallAccess
    ssh_host: Annotated[str, Field(min_length=1, max_length=253)]
    ssh_port: Annotated[int, Field(ge=1, le=65535)]
    ssh_user: Annotated[str, Field(min_length=1, max_length=64)]
    private_key: Annotated[str, Field(min_length=8, max_length=8192)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=_optional_write_only
    )


class ExecutorAgentInstall(_Object):
    """One install session of the universal agent over SSH (path A, `EXEC2-SEAL-1`, ADR-0026 decision 7).
    For `generated_key` access it carries the public half and its `authorized_keys` line, which the
    administrator adds to the host; the private half is sealed and never returned.
    `observed_host_key_fingerprint` is what the worker saw (derived from the stored key line, as
    `ExecutorRevision.host_key_fingerprint` is); the install does not proceed until the administrator
    confirms exactly that fingerprint. `key_removed_at` is when the stand's key was removed from the
    host and its sealed secret destroyed."""

    install_id: ExecutorAgentInstallId
    #: Exactly one of ``connection_id`` and ``host_id`` is present (`HOSTS-SEAL-1`).
    connection_id: ExecutorConnectionId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    host_id: ExecutorHostId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    state: ExecutorAgentInstallState
    access: ExecutorAgentInstallAccess
    ssh_host: Annotated[str, Field(min_length=1, max_length=253)]
    ssh_port: Annotated[int, Field(ge=1, le=65535)]
    ssh_user: Annotated[str, Field(min_length=1, max_length=64)]
    public_key: Annotated[str, Field(min_length=1, max_length=2048)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    authorized_keys_line: Annotated[str, Field(min_length=1, max_length=2200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    observed_host_key_fingerprint: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    host_key_confirmed_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    host_key_confirmed_by: UserUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    package_version: AgentPackageVersion = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    package_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    failure_reason: ExecutorAgentInstallFailure = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    key_removed_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    created_at: datetime
    created_by: UserUid
    updated_at: datetime
    finished_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ConfirmExecutorAgentInstallHostKeyRequest(_Object):
    """The fingerprint the administrator read and confirms. It must equal the one the worker observed;
    there is no trust on first use."""

    host_key_fingerprint: Annotated[str, Field(pattern=r"^SHA256:[A-Za-z0-9+/]{43}$")]


# --- comparison modules (`CMP-SEAL-C0`, ADR-0025) ----------------------------------------
#
# Sealed as stubs: every operation below answers `503 dependency_unavailable` until its lane
# (CMP-INGEST-01, CMP-INGEST-02, CMP-PROFILE-01) wires it. The shapes are exactly what the C0
# lanes implement; a lane that needs a field STOPs to the wave's FIX slot and never edits them.

ComparisonUploadId = TypeAliasType(
    "ComparisonUploadId", Annotated[str, Field(pattern=rf"^cbt_{_ULID}$")]
)
ComparisonUploadFileId = TypeAliasType(
    "ComparisonUploadFileId", Annotated[str, Field(pattern=rf"^cuf_{_ULID}$")]
)
ComparisonUploadSetId = TypeAliasType(
    "ComparisonUploadSetId", Annotated[str, Field(pattern=rf"^cus_{_ULID}$")]
)
ComparisonVersionOrderId = TypeAliasType(
    "ComparisonVersionOrderId", Annotated[str, Field(pattern=rf"^cvo_{_ULID}$")]
)
ComparisonPageProfileId = TypeAliasType(
    "ComparisonPageProfileId", Annotated[str, Field(pattern=rf"^cpr_{_ULID}$")]
)


class ComparisonUploadState(str, enum.Enum):
    UPLOADING = "uploading"
    PROPOSED = "proposed"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ComparisonUploadFileState(str, enum.Enum):
    DECLARED = "declared"
    UPLOADING = "uploading"
    VERIFIED = "verified"
    FAILED = "failed"


class ComparisonUploadSetState(str, enum.Enum):
    UPLOADING = "uploading"
    READING = "reading"
    NEEDS_CONFIRMATION = "needs_confirmation"
    READY = "ready"
    ADMITTING = "admitting"
    DONE = "done"
    FAILED = "failed"
    EXCLUDED = "excluded"


class ComparisonProposalWarning(str, enum.Enum):
    """What the stamp reader noticed about a proposed set; the user has the final word."""

    DESIGNATIONS_DIFFER = "designations_differ"
    ORDER_DISAGREES_WITH_FILE_NUMBERS = "order_disagrees_with_file_numbers"
    DUPLICATE_REVISION_NUMBER = "duplicate_revision_number"
    NO_STAMP_FOUND = "no_stamp_found"
    SCAN_WITHOUT_TEXT = "scan_without_text"


class ComparisonUploadFileDeclaration(_Object):
    """One file the client will send. ``display_name`` is a hint for the proposal and never an
    identity; ``sha256`` and ``size_bytes`` are checked against the received bytes when the file
    is completed."""

    display_name: Annotated[str, Field(min_length=1, max_length=255)]
    size_bytes: Annotated[int, Field(ge=1)]
    sha256: Sha256
    page_count: Annotated[int, Field(ge=1)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class CreateComparisonUploadRequest(_Object):
    """The declared files of one upload batch. The limits of ADR-0025 decision 9 (files, sets,
    declared bytes and pages, the project's stored bytes, active batches) are refused here,
    before the first part, as typed reasons under existing error codes."""

    files: Annotated[list[ComparisonUploadFileDeclaration], Field(min_length=1)]
    #: `CMP-SEAL-C1`. «После подготовки сравнить все соседние версии»: when true, the series of
    #: adjacent transitions is queued for every set of the batch as soon as the set is prepared.
    #: Absent means false. Until `CMP-SERIES-01` stores it, ``true`` is refused with ``503
    #: dependency_unavailable`` and nothing is created.
    compare_after_preparation: bool = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonUploadFile(_Object):
    file_id: ComparisonUploadFileId
    display_name: Annotated[str, Field(min_length=1, max_length=255)]
    size_bytes: Annotated[int, Field(ge=1)]
    sha256: Sha256
    state: ComparisonUploadFileState
    #: How many parts are staged so far (a resumable client sends the missing ones).
    parts_staged: Annotated[int, Field(ge=0)]
    #: The set the proposal placed this file in, once there is a proposal.
    set_id: ComparisonUploadSetId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: The typed reason a ``failed`` file failed.
    failure_reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonUpload(_Object):
    """One upload batch. ``files`` is present on ``getComparisonUpload`` and absent in the
    items of ``listComparisonUploads``. ``part_size_bytes`` is the size of every part but the
    last (16 MiB, ADR-0025 decision 10)."""

    upload_id: ComparisonUploadId
    project_uid: ProjectUid
    state: ComparisonUploadState
    part_size_bytes: Annotated[int, Field(ge=1, le=16 * 1024 * 1024)]
    declared_files: Annotated[int, Field(ge=1)]
    declared_bytes: Annotated[int, Field(ge=1)]
    created_at: datetime
    updated_at: datetime
    files: list[ComparisonUploadFile] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `CMP-SEAL-C1`. The flag the batch was declared with; absent until `CMP-SERIES-01` stores it
    #: (a batch declared without it is a batch that does not compare after preparation).
    compare_after_preparation: bool = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonUploadPage(_Object):
    items: list[ComparisonUpload]
    page: PageInfo


class ComparisonUploadPartReceipt(_Object):
    """What the server staged for one part: its size and the SHA-256 it computed, which the
    client may compare with its own."""

    file_id: ComparisonUploadFileId
    part_number: Annotated[int, Field(ge=1, le=10000)]
    size_bytes: Annotated[int, Field(ge=1, le=16 * 1024 * 1024)]
    sha256: Sha256


class ComparisonProposalFile(_Object):
    file_id: ComparisonUploadFileId
    #: 1-based place in the proposed order of the set.
    position: Annotated[int, Field(ge=1)]
    #: The suggested version label (for example «V2 Изм.3»); editable by the user.
    version_label: Annotated[str, Field(min_length=1, max_length=80)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonProposalSet(_Object):
    """One proposed document set. ``designation`` is the «шифр» read from the stamp: metadata
    an expert confirms, never an identity. ``existing_document_uid`` names the document of the
    project the designation matches, when there is one."""

    set_id: ComparisonUploadSetId
    state: ComparisonUploadSetState
    files: list[ComparisonProposalFile]
    designation: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    existing_document_uid: DocumentUid = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    project_stage: ProjectStage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    section_code: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    warnings: list[ComparisonProposalWarning] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: The typed reason a ``failed`` set failed.
    failure_reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: The document this set became, once its versions are admitted.
    document_uid: DocumentUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonUploadProposal(_Object):
    """The grouping, order, stage and section the reader proposes for an upload. Nothing is
    admitted as a version until the user confirms a set (``confirmComparisonUploadSet``)."""

    upload_id: ComparisonUploadId
    state: ComparisonUploadState
    sets: list[ComparisonProposalSet]


class ConfirmedComparisonFile(_Object):
    file_id: ComparisonUploadFileId
    version_label: Annotated[str, Field(min_length=1, max_length=80)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ConfirmComparisonUploadSetRequest(_Object):
    """The user's final word on one set: its members in their order (the array order is the
    version order), the labels, and the designation, stage, section and existing document the
    set belongs to. The stage and section are a proposal an expert confirms, never inferred."""

    files: Annotated[list[ConfirmedComparisonFile], Field(min_length=1)]
    designation: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    existing_document_uid: DocumentUid = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    project_stage: ProjectStage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    section_code: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonVersionOrderSource(str, enum.Enum):
    PROPOSAL = "proposal"
    EXPERT = "expert"


class ComparisonVersionOrder(_Object):
    """One revision of the order in which the versions of a document set are compared. It
    never changes the documents' ordinal that runs and finding carry-over use (ADR-0025
    decision 16, `D-5`)."""

    order_id: ComparisonVersionOrderId
    document_uid: DocumentUid
    revision_no: Annotated[int, Field(ge=1)]
    version_uids: Annotated[list[VersionUid], Field(min_length=1, max_length=500)]
    source: ComparisonVersionOrderSource
    created_at: datetime
    created_by: UserUid


class ComparisonVersionOrderList(_Object):
    """Newest revision first."""

    items: list[ComparisonVersionOrder]
    page: PageInfo


class AppendComparisonVersionOrderRequest(_Object):
    """A new revision of the order. ``base_revision_no`` is the latest revision the caller saw
    (``0`` for none); a mismatch is ``409 conflict`` and the caller rebases."""

    version_uids: Annotated[list[VersionUid], Field(min_length=1, max_length=500)]
    base_revision_no: Annotated[int, Field(ge=0)]


class PageProfileStatus(str, enum.Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    REFUSED = "refused"


class PageStamp(_Object):
    """The stamp fields read from one page; every member is absent when the page has none."""

    designation: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    sheet_number: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    sheet_name: Annotated[str, Field(min_length=1, max_length=400)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    revision_number: Annotated[str, Field(min_length=1, max_length=32)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    release_date: date = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    project_stage: ProjectStage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    section_code: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class VersionPageProfile(_Object):
    """The deterministic profile of one page of one version (raw evidence, never rewritten by
    an AI layer). ``reason`` is the typed reason of a ``needs_review`` or ``refused`` page, for
    example ``RENDER_FAILED``. ``content_key`` is the digest the profile is cached under."""

    page_profile_id: ComparisonPageProfileId
    version_uid: VersionUid
    page_number: Annotated[int, Field(ge=1)]
    status: PageProfileStatus
    algo_version: Annotated[str, Field(min_length=1, max_length=64)]
    content_key: Sha256
    has_text_layer: bool
    word_count: Annotated[int, Field(ge=0)]
    vector_line_count: Annotated[int, Field(ge=0)]
    annotation_count: Annotated[int, Field(ge=0)]
    preview_available: bool
    thumbnail_available: bool
    reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    width_pt: Annotated[float, Field(gt=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    height_pt: Annotated[float, Field(gt=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    raster_width_px: Annotated[int, Field(ge=1)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    raster_height_px: Annotated[int, Field(ge=1)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    stamp: PageStamp = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class VersionPageProfilePage(_Object):
    """The profiles stored for a version, by page number ascending. A page whose profile has not
    been computed is absent; the version's ``page_count`` says how many pages it has."""

    items: list[VersionPageProfile]
    page: PageInfo


# --- version comparison core (`CMP-SEAL-C1`, ADR-0025) ------------------------------------
#
# Sealed as stubs: every operation below answers `503 dependency_unavailable` until its lane
# (CMP-MATRIX-01, CMP-SERIES-01, CMP-VIEWER-01, CMP-VC-OVERVIEW-01) wires it. The shapes are
# exactly what those lanes implement; a lane that needs a field STOPs to the wave's FIX slot and
# never edits them. Every member that a lane may leave out is explicitly optional (R3-21).

ComparisonMatrixId = TypeAliasType(
    "ComparisonMatrixId", Annotated[str, Field(pattern=rf"^cmx_{_ULID}$")]
)
ComparisonMatrixEditId = TypeAliasType(
    "ComparisonMatrixEditId", Annotated[str, Field(pattern=rf"^cme_{_ULID}$")]
)
ComparisonAiLinkId = TypeAliasType(
    "ComparisonAiLinkId", Annotated[str, Field(pattern=rf"^cak_{_ULID}$")]
)
ComparisonSeriesId = TypeAliasType(
    "ComparisonSeriesId", Annotated[str, Field(pattern=rf"^cser_{_ULID}$")]
)
ComparisonTransitionId = TypeAliasType(
    "ComparisonTransitionId", Annotated[str, Field(pattern=rf"^ctn_{_ULID}$")]
)
ComparisonSheetPairId = TypeAliasType(
    "ComparisonSheetPairId", Annotated[str, Field(pattern=rf"^ctp_{_ULID}$")]
)
ComparisonSheetPairResultId = TypeAliasType(
    "ComparisonSheetPairResultId", Annotated[str, Field(pattern=rf"^csp_{_ULID}$")]
)


class ComparisonPageRef(_Object):
    """A page of a version: the version's identity and the page's coordinate inside that
    immutable version (never a display number). ``page_profile_id`` is the identity of the page's
    stored profile once there is one; the cells of a built matrix always carry it."""

    version_uid: VersionUid
    page_number: Annotated[int, Field(ge=1)]
    page_profile_id: ComparisonPageProfileId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonMatrixRevision(_Object):
    """The revision of an effective matrix: the algorithmic build it rests on and the number of
    manual edit events of the document set up to it (``0`` for none). An edit batch carries the
    revision the caller saw; a mismatch is ``409 conflict`` and the caller rebases its draft
    (ADR-0025 decision 14)."""

    matrix_id: ComparisonMatrixId
    edit_no: Annotated[int, Field(ge=0)]


class ComparisonMatrixState(str, enum.Enum):
    """``absent``: nothing has been built or queued. ``building``: profiles or the matrix are
    being computed. ``ready``: the build matches the current order and profiles. ``stale``: it
    does not, see ``stale_reasons``. ``failed``: the last build failed."""

    ABSENT = "absent"
    BUILDING = "building"
    READY = "ready"
    STALE = "stale"
    FAILED = "failed"


class ComparisonMatrixStaleReason(str, enum.Enum):
    """Why the latest build no longer matches: ``order_changed`` the version order moved,
    ``profiles_changed`` a page profile was recomputed, ``algorithm_changed`` the matching algorithm or its
    rule set (``ALGO_VERSION``, ``RULES_VERSION``) is not the one the build was made with
    (`CMP-SEAL-C2`, from `CMP-MATRIX-01`)."""

    ORDER_CHANGED = "order_changed"
    PROFILES_CHANGED = "profiles_changed"
    ALGORITHM_CHANGED = "algorithm_changed"


class ComparisonCellState(str, enum.Enum):
    """``matched``: the cell holds a page of this version. ``unmatched``: no page was matched,
    candidates may be offered. ``absent``: the version has no such sheet (determined, or marked
    by an expert)."""

    MATCHED = "matched"
    UNMATCHED = "unmatched"
    ABSENT = "absent"


class ComparisonCellConfidence(str, enum.Enum):
    """How a matched cell was linked: ``high`` and ``medium`` by the algorithm, ``group`` as a
    member of a table-sheet group, ``manual`` by an expert, ``ai`` by an accepted AI link."""

    HIGH = "high"
    MEDIUM = "medium"
    GROUP = "group"
    MANUAL = "manual"
    AI = "ai"


class ComparisonCellFlag(str, enum.Enum):
    """``split``: the sheet is split across versions. ``duplicate``: the same content stands on
    several pages. ``scan``: an image-only page whose text is not compared. ``bridge``: the cell
    was linked across a version that lacks the sheet."""

    SPLIT = "split"
    DUPLICATE = "duplicate"
    SCAN = "scan"
    BRIDGE = "bridge"


class ComparisonMatrixCandidate(_Object):
    """A page offered for an unmatched cell, with the algorithm's score."""

    page: ComparisonPageRef
    score: Annotated[float, Field(ge=0, le=1)]


class ComparisonMatrixCell(_Object):
    """One cell of a row, for the version column named by ``version_uid``. ``page``,
    ``confidence`` and ``flags`` belong to a matched cell; ``candidates`` and ``reason`` to an
    unmatched one. ``edit_id`` names the manual edit that made a ``manual`` cell, ``ai_link_id``
    the accepted AI link that made an ``ai`` cell."""

    version_uid: VersionUid
    state: ComparisonCellState
    page: ComparisonPageRef = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    confidence: ComparisonCellConfidence = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    flags: list[ComparisonCellFlag] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    candidates: Annotated[list[ComparisonMatrixCandidate], Field(max_length=8)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    reason: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    edit_id: ComparisonMatrixEditId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    ai_link_id: ComparisonAiLinkId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonMatrixRow(_Object):
    """One sheet identity across the versions. ``row_id`` is the identity of the stored profile
    of the row's first page and is valid within one revision. ``cells`` holds one cell per column,
    in the order of the columns."""

    row_id: ComparisonPageProfileId
    cells: list[ComparisonMatrixCell]
    title: Annotated[str, Field(min_length=1, max_length=400)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    sheet_number: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonMatrixLabelSource(str, enum.Enum):
    """Where a column label comes from: ``proposal`` the version's label the user confirmed with its
    upload set (the suggested label of the proposal when the user left it), ``file_name`` the stored file
    name of the version, which is a hint and never an identity."""

    PROPOSAL = "proposal"
    FILE_NAME = "file_name"


class ComparisonMatrixColumn(_Object):
    """One version, in the position of the current comparison order. ``label`` is the version's label of
    the upload proposal (``label_source`` ``proposal``) or, for a version that carried none, its stored
    file name (``file_name``); both are absent for a version that came from a portal bundle, and the
    client then writes «Версия №N» for the N-th column (`CMP-SEAL-C2`, from `CMP-MATRIX-01`)."""

    version_uid: VersionUid
    page_count: Annotated[int, Field(ge=0)]
    label: Annotated[str, Field(min_length=1, max_length=80)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    label_source: ComparisonMatrixLabelSource = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonMatrixProgress(_Object):
    """Profiles of the document set's pages: ``ready`` of ``total``, ``failed`` among the rest."""

    total: Annotated[int, Field(ge=0)]
    ready: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]


class ComparisonMatrixCounts(_Object):
    rows: Annotated[int, Field(ge=0)]
    unmatched: Annotated[int, Field(ge=0)]
    manual: Annotated[int, Field(ge=0)]
    ai: Annotated[int, Field(ge=0)]
    groups: Annotated[int, Field(ge=0)]
    duplicates: Annotated[int, Field(ge=0)]


class ComparisonMatrix(_Object):
    """The effective matrix of a document set: the algorithm, then accepted AI links (labelled,
    never an expert act), then manual edits (manual wins) (ADR-0025 decision 3). Rows are sheet
    identities, ``columns`` are the versions in the current comparison order. ``revision``,
    ``columns``, ``rows`` and ``counts`` are absent while no build exists. ``order_id`` is the
    version-order revision the build used (absent for the document's own order).
    ``orphaned_edit_ids`` lists the edits that no longer apply after a reorder: they are never
    applied silently. ``unassigned_pages`` are the pages no row holds."""

    project_uid: ProjectUid
    document_uid: DocumentUid
    state: ComparisonMatrixState
    progress: ComparisonMatrixProgress
    revision: ComparisonMatrixRevision = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    order_id: ComparisonVersionOrderId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    stale_reasons: list[ComparisonMatrixStaleReason] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    columns: list[ComparisonMatrixColumn] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    rows: list[ComparisonMatrixRow] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    unassigned_pages: list[ComparisonPageRef] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    counts: ComparisonMatrixCounts = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    orphaned_edit_ids: list[ComparisonMatrixEditId] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    built_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    failure_reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonMatrixPreparation(_Object):
    """What ``prepareComparisonMatrix`` queued: the matrix state after the call and the
    progress of the profiles. Profiles that are missing or failed are queued again, then the
    matrix is built."""

    document_uid: DocumentUid
    state: ComparisonMatrixState
    progress: ComparisonMatrixProgress


class ComparisonMatrixEditKind(str, enum.Enum):
    """``link``: ``page`` and ``other_page`` are one sheet. ``unlink``: ``page`` leaves its row
    for a row of its own. ``mark_absent``: the row of ``page`` has no sheet in
    ``absent_version_uid``. ``undo``: the event reverses the edit named by ``undoes_edit_id``
    (read side only; an undo is asked for with ``undoComparisonMatrixEdit``)."""

    LINK = "link"
    UNLINK = "unlink"
    MARK_ABSENT = "mark_absent"
    UNDO = "undo"


class ComparisonMatrixEditInputKind(str, enum.Enum):
    LINK = "link"
    UNLINK = "unlink"
    MARK_ABSENT = "mark_absent"


class ComparisonMatrixEditSource(str, enum.Enum):
    """``expert``: made through ``applyComparisonMatrixEdits``. ``migrated_sheet_link``: the
    approved pairing of ``approveSheetPairing`` (migration ``0039``, ADR-0025 decision 13); the
    ``0035`` ids are in ``provenance``."""

    EXPERT = "expert"
    MIGRATED_SHEET_LINK = "migrated_sheet_link"


class ComparisonMatrixEditStatus(str, enum.Enum):
    """``applied``: the edit shapes the effective matrix. ``undone``: a later undo reversed it.
    ``orphaned``: its cells no longer exist in the current order."""

    APPLIED = "applied"
    UNDONE = "undone"
    ORPHANED = "orphaned"


class ComparisonMatrixEditInput(_Object):
    """One edit of a batch. ``link`` needs ``page`` and ``other_page`` (two versions of the
    document set), ``unlink`` needs ``page``, ``mark_absent`` needs ``page`` and
    ``absent_version_uid``; any other member is refused as ``validation_failed``."""

    kind: ComparisonMatrixEditInputKind
    page: ComparisonPageRef
    other_page: ComparisonPageRef = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    absent_version_uid: VersionUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ApplyComparisonMatrixEditsRequest(_Object):
    """«Применить сопоставления (N)»: the batch an expert drafted, with the revision the draft
    started from. The edits are applied together or not at all."""

    base_revision: ComparisonMatrixRevision
    edits: Annotated[list[ComparisonMatrixEditInput], Field(min_length=1, max_length=500)]


class UndoComparisonMatrixEditRequest(_Object):
    """«Отменить правку»: reverses the latest applied edit. ``base_revision`` is the revision the
    caller saw, so an edit made meanwhile by someone else is never undone by mistake."""

    base_revision: ComparisonMatrixRevision


class ComparisonEditProvenance(_Object):
    """For a migrated edit, the ``0035`` records it came from. Absent for an expert's edit."""

    comparison_id: ComparisonId
    sheet_link_id: Annotated[str, Field(pattern=rf"^sln_{_ULID}$")]
    link_revision: Annotated[int, Field(ge=1)]


class ComparisonMatrixEdit(_Object):
    """One event of the append-only edit history of a document set, numbered ``edit_no`` from 1
    without a gap. ``order_id`` is the version-order revision the edit was made against (absent
    for the document's own order)."""

    edit_id: ComparisonMatrixEditId
    document_uid: DocumentUid
    edit_no: Annotated[int, Field(ge=1)]
    kind: ComparisonMatrixEditKind
    source: ComparisonMatrixEditSource
    status: ComparisonMatrixEditStatus
    created_at: datetime
    created_by: UserUid
    page: ComparisonPageRef = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    other_page: ComparisonPageRef = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    absent_version_uid: VersionUid = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    undoes_edit_id: ComparisonMatrixEditId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    order_id: ComparisonVersionOrderId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    provenance: ComparisonEditProvenance = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonMatrixEditList(_Object):
    """Newest event first."""

    items: list[ComparisonMatrixEdit]
    page: PageInfo


class ComparisonAiLinkAnsweredState(str, enum.Enum):
    UNMATCHED = "unmatched"
    DOUBTFUL = "doubtful"


class ComparisonAiLinkStatus(str, enum.Enum):
    """``applied``: the cell it answered is still in the state it answered. ``superseded``: the
    cell has since been matched otherwise or edited, so the link no longer shapes the matrix."""

    APPLIED = "applied"
    SUPERSEDED = "superseded"


class ComparisonAiLink(_Object):
    """An accepted AI link (ADR-0025 decisions 3 and 14): a model's answer that the validator
    accepted, shown labelled «ИИ» and never an expert act. It binds the algorithmic build
    (``matrix_id``) and the cell state it answered. Written in wave C2; this wave reads."""

    ai_link_id: ComparisonAiLinkId
    document_uid: DocumentUid
    matrix_id: ComparisonMatrixId
    page: ComparisonPageRef
    other_page: ComparisonPageRef
    answered_state: ComparisonAiLinkAnsweredState
    status: ComparisonAiLinkStatus
    created_at: datetime


class ComparisonAiLinkList(_Object):
    """Newest first."""

    items: list[ComparisonAiLink]
    page: PageInfo


class ComparisonSeriesState(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComparisonTransitionState(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComparisonVerdictCode(str, enum.Enum):
    """The parts of the deterministic verdict of a transition, in the order they are shown; the
    figures they quote are in the transition's ``summary``. A transition has one or more parts.
    The client renders the sentence."""

    INCOMPLETE = "incomplete"
    CONTENT_SAME = "content_same"
    ZONES_ONLY = "zones_only"
    DIFFERENT = "different"
    COMPOSITION_CHANGED = "composition_changed"
    NEEDS_REVIEW = "needs_review"
    CALCULATION_FAILED = "calculation_failed"


class ComparisonTransitionSummary(_Object):
    """The counts of a transition's sheet pairs. ``needs_review`` includes the unmatched ones.
    ``style_only`` counts the ``different`` sheets whose only difference is line style.
    ``ai_dependent`` counts the pairs that rest on an accepted AI link."""

    sheets: Annotated[int, Field(ge=0)]
    compared: Annotated[int, Field(ge=0)]
    same: Annotated[int, Field(ge=0)]
    zones_only: Annotated[int, Field(ge=0)]
    different: Annotated[int, Field(ge=0)]
    style_only: Annotated[int, Field(ge=0)]
    needs_review: Annotated[int, Field(ge=0)]
    added: Annotated[int, Field(ge=0)]
    removed: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    ai_dependent: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonTransition(_Object):
    """One adjacent transition of a series: the older version ``source_version_uid`` and the
    next one ``target_version_uid``. ``items_done`` of ``items_total`` sheet pairs have a result.
    ``verdict`` is absent until the transition has run."""

    transition_id: ComparisonTransitionId
    series_id: ComparisonSeriesId
    source_version_uid: VersionUid
    target_version_uid: VersionUid
    state: ComparisonTransitionState
    items_total: Annotated[int, Field(ge=0)]
    items_done: Annotated[int, Field(ge=0)]
    summary: ComparisonTransitionSummary
    verdict: Annotated[list[ComparisonVerdictCode], Field(min_length=1, max_length=7)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    failure_reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonSeriesStaleReason(str, enum.Enum):
    ORDER_CHANGED = "order_changed"
    MATRIX_CHANGED = "matrix_changed"
    PROFILES_CHANGED = "profiles_changed"


class ComparisonSeries(_Object):
    """The comparison of every adjacent pair of the versions of a document set, for one version
    order (ADR-0025 decisions 15 and 21). ``transitions`` is present on ``getComparisonSeries``
    and absent in the items of ``listComparisonSeries``. ``stale_reasons`` is present when the
    stored input digests no longer match the current order, matrix or profiles («Сохранённая
    сводка для прежнего порядка версий»). ``restarted_from`` names the series a «Заново» replaced.
    ``order_id`` is the version-order revision the series ran on (absent for the document's own
    order)."""

    series_id: ComparisonSeriesId
    project_uid: ProjectUid
    document_uid: DocumentUid
    state: ComparisonSeriesState
    created_at: datetime
    updated_at: datetime
    transitions_total: Annotated[int, Field(ge=0)]
    transitions_done: Annotated[int, Field(ge=0)]
    order_id: ComparisonVersionOrderId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    matrix_revision: ComparisonMatrixRevision = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    restarted_from: ComparisonSeriesId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    stale_reasons: list[ComparisonSeriesStaleReason] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    failure_reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    transitions: list[ComparisonTransition] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonSeriesPage(_Object):
    """Newest first."""

    items: list[ComparisonSeries]
    page: PageInfo


class StartComparisonSeriesRequest(_Object):
    """«Запустить» (``restart`` false or absent) or «Заново» (``restart`` true: every transition
    is computed again for the current order; sheet pairs whose content did not change come from
    the result cache). ``base_order_revision_no`` is the revision of the version order the caller
    saw (``0`` for none); a mismatch is ``409 conflict`` (``comparison_version_order_stale``)."""

    restart: bool = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    base_order_revision_no: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonSheetStatus(str, enum.Enum):
    """The status of one sheet pair (the original's ``result_status``): ``same``, ``same_zones_changed``
    (the main content is the same, service zones changed), ``different``, ``needs_review``,
    ``added`` (only in the newer version), ``removed`` (only in the older one) and
    ``unmatched``."""

    SAME = "same"
    SAME_ZONES_CHANGED = "same_zones_changed"
    DIFFERENT = "different"
    NEEDS_REVIEW = "needs_review"
    ADDED = "added"
    REMOVED = "removed"
    UNMATCHED = "unmatched"


class ComparisonSheetPairState(str, enum.Enum):
    QUEUED = "queued"
    COMPUTING = "computing"
    DONE = "done"
    FAILED = "failed"


class ComparisonChannelState(str, enum.Enum):
    CHECKED = "checked"
    UNCHECKED = "unchecked"
    NOT_APPLICABLE = "not_applicable"


class ComparisonChannel(_Object):
    """One channel of the comparison: ``checked`` with the number of differences it found,
    ``unchecked`` with the reason it could not look, or ``not_applicable``."""

    state: ComparisonChannelState
    diffs: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonChannels(_Object):
    """The eight channels: ``geometry``, ``color``, ``text``, ``text_coverage``, ``zones``,
    ``annotations``, ``warnings`` and ``spec_positions``. A sheet is «Совпадает» only when every
    applicable channel is ``checked``."""

    geometry: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    color: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    text: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    text_coverage: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    zones: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    annotations: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    warnings: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    spec_positions: ComparisonChannel = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonLayer(str, enum.Enum):
    """The layers of the overlay: ``main`` «Основное», ``light_elements`` «Светлые элементы»,
    ``color_change`` «места, где изменился цвет», ``line_style`` «Оформление линий», ``moved``
    «Перемещено (сдвиг — не изменение)», ``within_tolerance`` «В пределах допуска», ``noise``
    «Шум» and ``service_zones`` «Служебные зоны»."""

    MAIN = "main"
    LIGHT_ELEMENTS = "light_elements"
    COLOR_CHANGE = "color_change"
    LINE_STYLE = "line_style"
    MOVED = "moved"
    WITHIN_TOLERANCE = "within_tolerance"
    NOISE = "noise"
    SERVICE_ZONES = "service_zones"


class ComparisonBox(_Object):
    """A rectangle on the canvas of the older page, in points."""

    x: float
    y: float
    width: Annotated[float, Field(ge=0)]
    height: Annotated[float, Field(ge=0)]


class ComparisonDifference(_Object):
    """One entry of «Отличия: N». ``region_class`` is a lower-case word the engine defines
    (``text``, ``text_moved``, ``graphic_added``, ``graphic_removed``, ``graphic_changed``,
    ``color_change``, ``light_fill``, ``line_style``, ``block_moved``, ``shifted``)."""

    region_class: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
    layer: ComparisonLayer
    box: ComparisonBox
    before_text: Annotated[str, Field(min_length=1, max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    after_text: Annotated[str, Field(min_length=1, max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonNumberChange(_Object):
    before: Annotated[str, Field(min_length=1, max_length=64)]
    after: Annotated[str, Field(min_length=1, max_length=64)]


class ComparisonTextChange(_Object):
    """«было → стало» of one text fragment; ``numbers`` lists the numeric values that changed
    inside it, to be highlighted."""

    kind: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
    before: Annotated[str, Field(min_length=1, max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    after: Annotated[str, Field(min_length=1, max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    numbers: list[ComparisonNumberChange] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    box: ComparisonBox = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonNoteChange(str, enum.Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


class ComparisonServiceNote(_Object):
    """A change in the service zones: ``zone`` and ``field`` name where, ``kind`` what (a
    ``stamp``, ``warning``, ``qr`` code, ``field`` or PDF ``annotation``). The disappearance of a
    warning does not confirm an approval."""

    kind: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
    change: ComparisonNoteChange
    zone: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    field: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    before: Annotated[str, Field(min_length=1, max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    after: Annotated[str, Field(min_length=1, max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonHowCompared(_Object):
    """«Как сравнивалось»: the registration transform of the newer page onto the older one (an
    affine matrix ``[a, b, c, d, e, f]``), the raster resolution, the tolerance and the counts of
    what was set aside."""

    algo_version: Annotated[str, Field(min_length=1, max_length=64)]
    dpi: Annotated[int, Field(ge=1)]
    tolerance_pt: Annotated[float, Field(ge=0)]
    transform: Annotated[list[float], Field(min_length=6, max_length=6)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    within_tolerance_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    noise_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    separated_objects: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    aligned_blocks: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonPermitState(str, enum.Enum):
    """The reconciliation of the changes a permit stamp declares with the changes found:
    ``declared_and_found``, ``declared_no_diff``, ``diff_not_declared`` and ``needs_review``."""

    DECLARED_AND_FOUND = "declared_and_found"
    DECLARED_NO_DIFF = "declared_no_diff"
    DIFF_NOT_DECLARED = "diff_not_declared"
    NEEDS_REVIEW = "needs_review"


class ComparisonPermitItem(_Object):
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    state: ComparisonPermitState


class ComparisonPermit(_Object):
    """«Заявлено проектировщиком в разрешении»: the declared items and how each fared."""

    state: ComparisonPermitState
    items: Annotated[list[ComparisonPermitItem], Field(max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class ComparisonPartRole(str, enum.Enum):
    WHOLE = "whole"
    PART = "part"


class ComparisonPartsCoverage(_Object):
    """The coverage of a sheet that is split across versions (``◫``, ``⇉``): whether this pair
    holds the whole sheet or one part, the other parts, and how much of the older sheet the parts
    cover together."""

    role: ComparisonPartRole
    covered_percent: Annotated[float, Field(ge=0, le=100)]
    parts: Annotated[list[ComparisonPageRef], Field(max_length=64)]


class ComparisonRasterSize(_Object):
    """The size in pixels of the full-resolution raster of a page, the base of its tile pyramid
    (level 0): the viewer lays tiles on it and need not derive it (`CMP-SEAL-C2`, from
    `CMP-VIEWER-01`)."""

    width_px: Annotated[int, Field(ge=1)]
    height_px: Annotated[int, Field(ge=1)]


class ComparisonPairPage(_Object):
    """One side of a sheet pair: the page, its sheet number and title from the stamp, and
    whether it is an image-only page. ``raster`` is the size of the page's raster pyramid."""

    page: ComparisonPageRef
    sheet_number: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    title: Annotated[str, Field(min_length=1, max_length=400)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    scan: bool = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    raster: ComparisonRasterSize = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonCanvas(_Object):
    """The canvas of the older page, in points; the boxes of the differences are on it."""

    width_pt: Annotated[float, Field(gt=0)]
    height_pt: Annotated[float, Field(gt=0)]


class ComparisonSheetPair(_Object):
    """One sheet pair of a transition: the older page ``page_a``, the newer ``page_b``, either
    absent for an ``added`` or ``removed`` sheet. ``status`` and the members after it are absent
    until the pair has a result. ``result_id`` is the content-keyed result the pair uses
    (ADR-0025 decision 15); it is shared by pairs of equal content within a project. The members
    from ``canvas`` on are the raw deterministic evidence and are present on
    ``getComparisonSheetPair`` only; an AI layer never rewrites them."""

    sheet_pair_id: ComparisonSheetPairId
    transition_id: ComparisonTransitionId
    state: ComparisonSheetPairState
    page_a: ComparisonPairPage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    page_b: ComparisonPairPage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    status: ComparisonSheetStatus = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    confidence: ComparisonCellConfidence = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    flags: list[ComparisonCellFlag] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reasons: Annotated[list[Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]], Field(max_length=32)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    channels: ComparisonChannels = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    permit: ComparisonPermit = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    parts: ComparisonPartsCoverage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    result_id: ComparisonSheetPairResultId = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    ai_dependent: bool = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    failure_reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    canvas: ComparisonCanvas = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    differences: Annotated[list[ComparisonDifference], Field(max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    text_changes: Annotated[list[ComparisonTextChange], Field(max_length=2000)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    service_notes: Annotated[list[ComparisonServiceNote], Field(max_length=500)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    how_compared: ComparisonHowCompared = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonSheetPairPage(_Object):
    """The sheet pairs of a transition in the order of the matrix rows."""

    items: list[ComparisonSheetPair]
    page: PageInfo


class ComparisonPairTileMode(str, enum.Enum):
    """``overlay``: the older and the newer page on one canvas with the difference layers.
    ``a`` and ``b``: the older or the newer page alone."""

    OVERLAY = "overlay"
    A = "a"
    B = "b"


class ComparisonStepId(str, enum.Enum):
    """The seven steps of a document set on «Проекты и этапы», in order: ``upload`` «Загрузка»,
    ``profile`` «Разбор версий», ``matrix`` «Сопоставление листов», ``ai_pairs`` «ИИ-проверка
    сомнительных пар», ``series`` «Сравнение соседних», ``ai_changes`` «ИИ-описание изменений»,
    ``report`` «Сводка и отчёт»."""

    UPLOAD = "upload"
    PROFILE = "profile"
    MATRIX = "matrix"
    AI_PAIRS = "ai_pairs"
    SERIES = "series"
    AI_CHANGES = "ai_changes"
    REPORT = "report"


class ComparisonStepState(str, enum.Enum):
    """The state words of the original's seven columns, as codes. ``not_started`` and
    ``not_applicable`` are the two ways a step has nothing to show; ``attention``, ``partial``,
    ``stale``, ``interrupted`` and ``paused`` are the amber ones, ``queued``, ``running`` and
    ``pausing`` the running ones, ``failed`` the red one, ``blocked`` a step waiting for the one
    before it."""

    NOT_STARTED = "not_started"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    DONE = "done"
    PARTIAL = "partial"
    STALE = "stale"
    ATTENTION = "attention"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class ComparisonStepCounts(_Object):
    """The figures a step's note quotes; each is absent when the step has no such figure."""

    total: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    ready: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    failed: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    rows: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    unmatched: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    manual_edits: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    done: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    with_changes: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonOverviewStep(_Object):
    step: ComparisonStepId
    state: ComparisonStepState
    counts: ComparisonStepCounts = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonOverviewSet(_Object):
    """One row of «Проекты и этапы»: a document set («комплект (шифр)»). ``designation`` is the
    «шифр», metadata and never an identity. ``steps`` lists the seven steps in order;
    ``next_step`` is the step the chip proposes and is absent when nothing is left to do."""

    document_uid: DocumentUid
    version_count: Annotated[int, Field(ge=0)]
    steps: Annotated[list[ComparisonOverviewStep], Field(min_length=7, max_length=7)]
    designation: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    title: Annotated[str, Field(min_length=1, max_length=400)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    project_stage: ProjectStage = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    section_code: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    next_step: ComparisonStepId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    updated_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ComparisonOverviewTotals(_Object):
    """«N версий · M переходов»."""

    versions: Annotated[int, Field(ge=0)]
    transitions: Annotated[int, Field(ge=0)]


class ComparisonOverviewCounters(_Object):
    """«Все / Ждут действия / Идут / Ошибки / Готовы»."""

    all: Annotated[int, Field(ge=0)]
    waiting: Annotated[int, Field(ge=0)]
    running: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    ready: Annotated[int, Field(ge=0)]


class ComparisonOverviewUpload(_Object):
    """A batch that is not finished: «В загрузке, ещё не в списке проектов»."""

    upload_id: ComparisonUploadId
    state: ComparisonUploadState
    declared_files: Annotated[int, Field(ge=1)]
    sets_total: Annotated[int, Field(ge=0)]
    sets_done: Annotated[int, Field(ge=0)]


class ComparisonOverview(_Object):
    """The overview of a project for «Проекты и этапы»: one entry per document set, the totals
    and counters, and the batches still being uploaded. Reading it starts nothing."""

    project_uid: ProjectUid
    generated_at: datetime
    totals: ComparisonOverviewTotals
    counters: ComparisonOverviewCounters
    sets: Annotated[list[ComparisonOverviewSet], Field(max_length=1000)]
    pending_uploads: Annotated[list[ComparisonOverviewUpload], Field(max_length=100)]


class ComparisonQueueCounts(_Object):
    """Comparison work items by state."""

    queued: Annotated[int, Field(ge=0)]
    leased: Annotated[int, Field(ge=0)]
    running: Annotated[int, Field(ge=0)]
    retry_wait: Annotated[int, Field(ge=0)]
    paused: Annotated[int, Field(ge=0)]
    spend_unknown: Annotated[int, Field(ge=0)]
    succeeded: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    cancelled: Annotated[int, Field(ge=0)]


class ComparisonQueueModule(str, enum.Enum):
    VERSIONS = "versions"
    STAGES = "stages"


class ComparisonQueueKind(_Object):
    kind: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")]
    module: ComparisonQueueModule
    counts: ComparisonQueueCounts


class ComparisonQueueSummary(_Object):
    """The read-only «Сравнение» block of «Очередь»: the module set, whether execution is
    paused for the whole installation, the items by state and by kind, and the age of the oldest
    queued one. Comparison work yields to section runs and honours the pause."""

    modules: ComparisonModules
    paused: bool
    counts: ComparisonQueueCounts
    kinds: list[ComparisonQueueKind]
    oldest_queued_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


# --- version comparison AI, specifications, reports and the launch queue (`CMP-SEAL-C2`, ADR-0025) ---
#
# Sealed as stubs: every operation below answers `503 dependency_unavailable` until its lane
# (CMP-VC-AIPAIR-01, CMP-VC-AISHEET-01, CMP-VC-SPEC-01, CMP-VC-QUEUE-01, CMP-VC-REPORT-01) wires it,
# and, with the module off, `comparison_modules` before anything is read. The shapes are exactly what
# those lanes implement; a lane that needs a field STOPs to the wave's FIX slot and never edits them.
# Every member a lane may leave out is explicitly optional (R3-21). Money is integer micro-USD, like
# the spend journal (`comparison_model_call.cost_micros`).

ComparisonAiJobId = TypeAliasType("ComparisonAiJobId", Annotated[str, Field(pattern=rf"^cai_{_ULID}$")])
ComparisonAiPairQuestionId = TypeAliasType(
    "ComparisonAiPairQuestionId", Annotated[str, Field(pattern=rf"^cpq_{_ULID}$")]
)
ComparisonSheetDescriptionId = TypeAliasType(
    "ComparisonSheetDescriptionId", Annotated[str, Field(pattern=rf"^csd_{_ULID}$")]
)
ComparisonSpecExtractionId = TypeAliasType(
    "ComparisonSpecExtractionId", Annotated[str, Field(pattern=rf"^cse_{_ULID}$")]
)
ComparisonSpecComparisonId = TypeAliasType(
    "ComparisonSpecComparisonId", Annotated[str, Field(pattern=rf"^cscp_{_ULID}$")]
)
ComparisonReportId = TypeAliasType("ComparisonReportId", Annotated[str, Field(pattern=rf"^crt_{_ULID}$")])
ComparisonLaunchEntryId = TypeAliasType(
    "ComparisonLaunchEntryId", Annotated[str, Field(pattern=rf"^cle_{_ULID}$")]
)

_REASON_CODE = r"^[a-z][a-z0-9_]{2,63}$"
_ENGINE_CODE = r"^[A-Z][A-Z0-9_]{2,63}$"
_NOT_GIVEN: dict[str, Any] = {"default": None, "json_schema_extra": optional_property}


class ComparisonAiMethod(str, enum.Enum):
    """The four kinds of model work of the version comparison. Each is also an executor work kind,
    ``comparison_<method>`` (``ExecutorWorkKind``), routed in «Назначения»: ``pair_check`` the AI check
    of the doubtful pairs of the matrix, ``sheet_changes`` the AI description of changes, ``spec`` the
    comparison of whole specifications, ``report`` the report from the summary."""

    PAIR_CHECK = "pair_check"
    SHEET_CHANGES = "sheet_changes"
    SPEC = "spec"
    REPORT = "report"
    STAGE_REVIEW = "stage_review"


class ComparisonAiJobState(str, enum.Enum):
    """``queued``: waiting, in the installation's AI queue or for a free executor. ``paused``: stopped,
    see ``pause_reason``. A ``completed`` job whose ``counts.failed`` is not zero is the original's
    «частично»."""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComparisonAiPauseReason(str, enum.Enum):
    """Why a job is ``paused``: ``user`` asked; ``quota`` the subscription's quota is spent; ``auth`` the
    executor is not authorised; ``overrun`` the actual spend passed 1.2 times the consented estimate;
    ``route_changed`` the route or the revision of the connection changed since the consent;
    ``module_off`` the versions module was turned off. After ``overrun`` and ``route_changed`` a
    resume carries a new consent."""

    USER = "user"
    QUOTA = "quota"
    AUTH = "auth"
    OVERRUN = "overrun"
    ROUTE_CHANGED = "route_changed"
    MODULE_OFF = "module_off"


class ComparisonAiCeiling(str, enum.Enum):
    """The hard ceilings of ``Q-CMP-7``: ``job`` USD 10 for one job, ``day`` USD 50 per day for the
    installation. A connection that is not metered has none."""

    JOB = "job"
    DAY = "day"


class ComparisonLayoutKind(str, enum.Enum):
    """A kind of comparison work that the stage layout chooses a model for (`HOSTS-CMP-01`): `comparison_pair_check` (the AI check of
    doubtful sheet pairs), `comparison_sheet_changes` (the AI description of a sheet's changes), `comparison_spec` (the comparison of whole
    specifications) and `comparison_report` (the report of a comparison). `comparison_stage_review` has no handler and is not offered."""

    COMPARISON_PAIR_CHECK = "comparison_pair_check"
    COMPARISON_SHEET_CHANGES = "comparison_sheet_changes"
    COMPARISON_SPEC = "comparison_spec"
    COMPARISON_REPORT = "comparison_report"


class StageComparisonCell(_Object):
    """The settings of one kind of comparison work (`HOSTS-CMP-01`): model and effort. The model and the effort must be a pair of
    `listModelCatalogue`. A comparison job freezes its cell when it starts. `LIMITS-01` (contract 1.49.0): no answer limit and no
    timeout per cell -- a call carries no answer cap, and its window is the constant of its kind (`R-153n`, `R-153o`)."""

    work_kind: ComparisonLayoutKind
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    effort: ModelEffort


class ComparisonAiRoute(_Object):
    """What serves the calls of an estimate or a job: the connection and its revision, the model the
    revision pins (a reply from another model is refused, ``R-133``), how it is billed and whether the
    process is in recorded mode, in which case every answer is a recorded test answer.

    `HOSTS-CMP-01` (ADR-0028 decision 19): a route chosen by the stage layout also carries the `cell` of its kind of work -- the
    model and effort the job froze. The estimate digest binds it, so the consent names what will run."""

    #: `EXEC2-SEAL-2` (ADR-0026 decisions 12 and 13). For work admitted by a rule or a group the connection and its
    #: revision are absent until dispatch binds the work, and the group, the rule revision and the planned model
    #: (``pinned_model``, ``billing``) are what admission froze.
    connection_id: ExecutorConnectionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    revision_id: ExecutorRevisionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    pinned_model: Annotated[str, Field(min_length=1, max_length=128)]
    billing: ExecutorBilling
    provider_mode: ProviderMode
    executor_group_id: ExecutorGroupId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    executor_group_revision_id: ExecutorGroupRevisionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    routing_rule_revision_id: ExecutorRoutingRuleRevisionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    cell: StageComparisonCell = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiEstimate(_Object):
    """What an AI start would do and cost, computed without a model call. ``estimate_digest`` binds the
    route, the pinned model, the ceilings and every figure below: the start carries it, and a start whose
    digest is not the one now computed is ``409 conflict`` (``comparison_estimate_stale``). ``units`` is
    what the job works on (questions, sheets, transitions, versions or report parts); ``reused`` of the
    units already have a stored answer under the same content key and are never sent again. For a
    connection that is not metered ``estimate_micros`` is ``0`` and no ceiling applies. ``blocked_by`` is
    present when the start would be refused for a ceiling (``comparison_ceiling_job`` or
    ``comparison_ceiling_day``)."""

    method: ComparisonAiMethod
    estimate_digest: Sha256
    route: ComparisonAiRoute
    units: Annotated[int, Field(ge=0)]
    reused: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    questions: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    pairs: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    sheets: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    transitions: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    versions: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    calls: Annotated[int, Field(ge=0)]
    images: Annotated[int, Field(ge=0)]
    image_bytes: Annotated[int, Field(ge=0)]
    prompt_chars: Annotated[int, Field(ge=0)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    estimate_micros: Annotated[int, Field(ge=0)]
    ceiling_micros: Annotated[int, Field(ge=0)]
    day_remaining_micros: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    blocked_by: ComparisonAiCeiling = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiConsent(_Object):
    """The user's consent to one estimate: the digest of the estimate that was shown and the explicit
    confirmation of the line «Подтверждаю передачу материалов исполнителю». ``confirmed`` false is
    ``422 validation_failed`` (``comparison_consent_required``)."""

    estimate_digest: Sha256
    confirmed: bool


class StartComparisonAiJobRequest(_Object):
    """Starts an AI job. Refused before anything is read or written when the versions module is off."""

    consent: ComparisonAiConsent


class StartComparisonAiSheetChangesRequest(_Object):
    """«Запустить» (``restart`` false or absent) or «Описать заново» (``restart`` true: every sheet is
    described again; a sheet whose content, prompt version and model did not change keeps its stored
    answer and is not sent)."""

    consent: ComparisonAiConsent
    restart: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ResumeComparisonAiJobRequest(_Object):
    """Resumes a paused job. ``consent`` is required after ``overrun`` and ``route_changed`` (a new
    estimate for what is left) and ignored after the other pause reasons."""

    consent: ComparisonAiConsent = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiSpend(_Object):
    """The spend of a job so far, from the comparison journal. ``reserved_micros`` is what the calls in
    flight may still cost; ``unknown_calls`` are calls whose outcome is not known and that are never sent
    again until a person says «Повторить»."""

    spent_micros: Annotated[int, Field(ge=0)]
    reserved_micros: Annotated[int, Field(ge=0)]
    calls: Annotated[int, Field(ge=0)]
    unknown_calls: Annotated[int, Field(ge=0)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]


class ComparisonAiJobCounts(_Object):
    """The units of a job: ``total``, those ``done``, those ``failed`` and those whose call outcome is
    ``unknown``."""

    total: Annotated[int, Field(ge=0)]
    done: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    unknown: Annotated[int, Field(ge=0)]


class ComparisonAiJob(_Object):
    """One AI job: the consented estimate (frozen), the state, the units and the spend. A job belongs to
    one document set; ``series_id``, ``transition_id`` and ``sheet_pair_id`` name its scope when it has
    one. ``queue_position`` is present while the job waits in the installation's AI queue.
    Every AI text a job produces is model output not confirmed by an engineer."""

    job_id: ComparisonAiJobId
    method: ComparisonAiMethod
    project_uid: ProjectUid
    document_uid: DocumentUid
    state: ComparisonAiJobState
    estimate: ComparisonAiEstimate
    consented_by: UserUid
    consented_at: datetime
    spend: ComparisonAiSpend
    counts: ComparisonAiJobCounts
    created_at: datetime
    updated_at: datetime
    series_id: ComparisonSeriesId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    transition_id: ComparisonTransitionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    sheet_pair_id: ComparisonSheetPairId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    pause_reason: ComparisonAiPauseReason = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    failure_reason: Annotated[str, Field(pattern=_REASON_CODE)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    queue_position: Annotated[int, Field(ge=1)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    finished_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    #: `EXEC2-SEAL-2` (ADR-0026 decisions 12 to 15). Absent ``binding_state`` is read as ``frozen_at_start``.
    binding_state: ExecutorBindingState = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    planned: ExecutorGroupPlan = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    binding: ExecutorBinding = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    wait_reason: RunQueueReason = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    waiting_since: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]


# --- AI check of doubtful pairs (CMP-VC-AIPAIR-01) -----------------------------------------


class ComparisonAiPairQuestionKind(str, enum.Enum):
    """``no_pair``: sheet A has no pair and the cell of B has candidates («⁇»). ``medium_pair``: the algorithm's
    pair has medium confidence. Sheets of a multi-sheet table group are not asked."""

    NO_PAIR = "no_pair"
    MEDIUM_PAIR = "medium_pair"


class ComparisonAiPairDecision(str, enum.Enum):
    """What the lane's rule made of the answers. ``link_accepted``: written as an accepted AI link
    (high confidence, the candidate number and the page agree, the sheet is not inside a multi-sheet
    specification, B is not linked to another A, no other A chose the same B, the reverse question
    returned A with high confidence). The ``hint_*`` values are shown as «ИИ ?» or «вероятно стр. N»
    and change nothing: ``hint_table`` a multi-sheet table, ``hint_confidence`` not high,
    ``hint_taken`` B is already paired by the algorithm, ``hint_shared`` two sheets chose one,
    ``hint_reverse`` the reverse question did not confirm. ``none``: no candidate is the same sheet.
    ``answer_mismatch``: the number and the page disagree and the answer is dropped. ``failed``: no usable
    answer. ``medium_confirm``, ``medium_weak``, ``medium_other`` and ``medium_none``: the answers to a
    ``medium`` question (the pair is confirmed, confirmed without confidence, another sheet is
    named, none is the same sheet). A manual edit always wins over any of them."""

    LINK_ACCEPTED = "link_accepted"
    HINT_TABLE = "hint_table"
    HINT_CONFIDENCE = "hint_confidence"
    HINT_TAKEN = "hint_taken"
    HINT_SHARED = "hint_shared"
    HINT_REVERSE = "hint_reverse"
    NONE = "none"
    ANSWER_MISMATCH = "answer_mismatch"
    FAILED = "failed"
    MEDIUM_CONFIRM = "medium_confirm"
    MEDIUM_WEAK = "medium_weak"
    MEDIUM_OTHER = "medium_other"
    MEDIUM_NONE = "medium_none"


class ComparisonAiConfidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComparisonAiPairCounts(_Object):
    """«вопросов · пар · подсказок · против»: ``questions`` asked, ``answered`` of them, ``pairs``
    accepted as AI links, ``hints`` shown, ``against`` the model said no candidate is the same sheet,
    ``failed`` without a usable answer, ``reused`` answered from the store without a call."""

    questions: Annotated[int, Field(ge=0)]
    answered: Annotated[int, Field(ge=0)]
    pairs: Annotated[int, Field(ge=0)]
    hints: Annotated[int, Field(ge=0)]
    against: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    reused: Annotated[int, Field(ge=0)]


class ComparisonAiPairCheck(_Object):
    """The AI check of the doubtful pairs of a document set: the latest job and its figures. Both are
    absent until a check was started. Accepted answers are written as accepted AI links by the
    lane's rule and never by a client call (``AGENTS.md`` section 4)."""

    document_uid: DocumentUid
    job: ComparisonAiJob = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    counts: ComparisonAiPairCounts = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiPairHint(_Object):
    """The answer to one question, for the matrix cell it concerns: sheet ``page`` of the older version
    against the cell of ``version_uid``. ``hint_page`` is «вероятно стр. N». ``link_id`` names the
    accepted AI link a ``link_accepted`` decision wrote. ``stale`` is true when the question was asked of a
    matrix build that is no longer the latest. ``reason`` is the model's own sentence, not confirmed by an
    engineer."""

    question_id: ComparisonAiPairQuestionId
    job_id: ComparisonAiJobId
    matrix_id: ComparisonMatrixId
    kind: ComparisonAiPairQuestionKind
    decision: ComparisonAiPairDecision
    page: ComparisonPageRef
    version_uid: VersionUid
    candidates: Annotated[list[ComparisonPageRef], Field(max_length=8)]
    stale: bool
    created_at: datetime
    hint_page: ComparisonPageRef = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    confidence: ComparisonAiConfidence = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    link_id: ComparisonAiLinkId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    reason: Annotated[str, Field(min_length=1, max_length=300)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiPairHintPage(_Object):
    """Newest first."""

    items: list[ComparisonAiPairHint]
    page: PageInfo


# --- AI description of changes (CMP-VC-AISHEET-01) -----------------------------------------


class ComparisonAiSheetState(str, enum.Enum):
    """The eleven states of «Изменения в листе»: ``not_processed`` «Не обработано» (not the same as no
    changes), ``queued`` «В очереди», ``running`` «В обработке», ``done`` «Готово», ``needs_clarification``
    «Требуется уточнение», ``partial`` «Частично», ``no_construction_changes`` «Строительных изменений не
    выявлено», ``stale`` «Описание устарело», ``failed`` «Ошибка», ``cancelled`` «Отменено»,
    ``engine_same`` «По данным сравнения изменений нет»."""

    NOT_PROCESSED = "not_processed"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    NEEDS_CLARIFICATION = "needs_clarification"
    PARTIAL = "partial"
    NO_CONSTRUCTION_CHANGES = "no_construction_changes"
    STALE = "stale"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ENGINE_SAME = "engine_same"


class ComparisonAiTier(str, enum.Enum):
    """How a value of a change was checked by the program: ``from_text`` found in the text layer of its own
    side, ``from_image`` read from the drawing the model cited («с изображения»), ``unverified`` found in
    neither («не подтверждено»)."""

    FROM_TEXT = "from_text"
    FROM_IMAGE = "from_image"
    UNVERIFIED = "unverified"


class ComparisonAiCertainty(str, enum.Enum):
    CONFIRMED = "confirmed"
    UNCLEAR = "unclear"


class ComparisonAiSide(str, enum.Enum):
    A = "a"
    B = "b"


class ComparisonAiExcludeReason(str, enum.Enum):
    """Why an engine pointer is «Не включено в сводку»."""

    SERVICE = "service"
    FORMATTING = "formatting"
    LABEL_MOVE = "label_move"
    REVISION_MARK = "revision_mark"
    DUPLICATE = "duplicate"
    NOT_CONSTRUCTION = "not_construction"


class ComparisonAiChange(_Object):
    """One change of the description: the construction object and its place, «Было» (only from side A)
    and «стало» (only from side B), the tier of each value and, for an item the model could not settle,
    the limitation («Неясно»). ``box`` and ``side`` serve «Показать на чертеже»."""

    change_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,31}$")]
    object_name: Annotated[str, Field(min_length=1, max_length=300)]
    certainty: ComparisonAiCertainty
    kind: Annotated[str, Field(pattern=r"^[a-z][a-z_]{1,31}$")] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    place: Annotated[str, Field(min_length=1, max_length=300)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    was: Annotated[str, Field(min_length=1, max_length=500)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    now: Annotated[str, Field(min_length=1, max_length=500)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    was_tier: ComparisonAiTier = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    now_tier: ComparisonAiTier = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    limitation: Annotated[str, Field(min_length=1, max_length=300)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    side: ComparisonAiSide = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    box: ComparisonBox = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiUnresolved(_Object):
    """An item under «Требует уточнения (N)»."""

    question: Annotated[str, Field(min_length=1, max_length=500)]
    side: ComparisonAiSide = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    box: ComparisonBox = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiDeclaredItem(_Object):
    """An item under «Заявлено проектировщиком в разрешении (N)», from the permit's stamp."""

    text: Annotated[str, Field(min_length=1, max_length=500)]
    reference: Annotated[str, Field(min_length=1, max_length=120)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiExcluded(_Object):
    """An engine pointer the program ruled out of the description, with the reason."""

    reason: ComparisonAiExcludeReason
    text: Annotated[str, Field(min_length=1, max_length=300)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiCoverage(_Object):
    """How many engine candidates the description covers: ``candidates`` offered, ``in_changes`` named in
    a change, ``not_reviewed`` left unreviewed."""

    candidates: Annotated[int, Field(ge=0)]
    in_changes: Annotated[int, Field(ge=0)]
    not_reviewed: Annotated[int, Field(ge=0)]


class ComparisonAiDiagnostics(_Object):
    """The «Диагностика» panel: kept out of the main report. ``issues`` are the codes of the checks that
    failed."""

    issues: Annotated[list[Annotated[str, Field(pattern=_ENGINE_CODE)]], Field(max_length=64)]
    excluded_by_program: Annotated[int, Field(ge=0)]
    candidates: Annotated[int, Field(ge=0)]


class ComparisonSheetDescriptionSource(str, enum.Enum):
    """``sheet`` the description of the sheet pair; ``whole_specification`` the changes of this sheet
    were taken from the comparison of the whole specifications («По полной спецификации · только
    изменения этого листа»)."""

    SHEET = "sheet"
    WHOLE_SPECIFICATION = "whole_specification"


class ComparisonSheetDescription(_Object):
    """The stored AI description of one sheet pair (or of one added or removed sheet). Reading it never
    calls a model. ``description_id`` and the members after ``source`` are absent while the state is
    ``not_processed``, ``queued``, ``running`` or ``engine_same``. ``job_id`` names the job that is
    queued or running for the sheet. ``recorded`` is true for a recorded (test) answer, which the client
    labels as such. The description is model output not confirmed by an engineer and never changes the
    raw comparison of the pair."""

    sheet_pair_id: ComparisonSheetPairId
    state: ComparisonAiSheetState
    history_count: Annotated[int, Field(ge=0)]
    description_id: ComparisonSheetDescriptionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    source: ComparisonSheetDescriptionSource = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    changes: Annotated[list[ComparisonAiChange], Field(max_length=300)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    unresolved: Annotated[list[ComparisonAiUnresolved], Field(max_length=100)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    declared: Annotated[list[ComparisonAiDeclaredItem], Field(max_length=100)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    excluded: Annotated[list[ComparisonAiExcluded], Field(max_length=300)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    coverage: ComparisonAiCoverage = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    diagnostics: ComparisonAiDiagnostics = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    job_id: ComparisonAiJobId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    model: Annotated[str, Field(min_length=1, max_length=128)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    prompt_version: Annotated[str, Field(min_length=1, max_length=64)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    recorded: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    created_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonSheetDescriptionRevision(_Object):
    """One entry of «История (N)»."""

    description_id: ComparisonSheetDescriptionId
    state: ComparisonAiSheetState
    changes_count: Annotated[int, Field(ge=0)]
    unresolved_count: Annotated[int, Field(ge=0)]
    recorded: bool
    created_at: datetime
    model: Annotated[str, Field(min_length=1, max_length=128)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    prompt_version: Annotated[str, Field(min_length=1, max_length=64)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonSheetDescriptionHistory(_Object):
    """Newest first."""

    items: list[ComparisonSheetDescriptionRevision]
    page: PageInfo


class ComparisonAiTransitionProgress(_Object):
    """One row of «ИИ-описание изменений»: «Листов» (``sheets`` to describe, ``done`` of them),
    «Изм.» (``changed``: sheets with changes), «Вопр.» (``questions``), «Ошибок» (``errors``),
    «Проверить» (``to_review``), «Обращ.» (``calls``), tokens and ``seconds``."""

    transition_id: ComparisonTransitionId
    sheets: Annotated[int, Field(ge=0)]
    done: Annotated[int, Field(ge=0)]
    changed: Annotated[int, Field(ge=0)]
    questions: Annotated[int, Field(ge=0)]
    errors: Annotated[int, Field(ge=0)]
    to_review: Annotated[int, Field(ge=0)]
    calls: Annotated[int, Field(ge=0)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    seconds: Annotated[int, Field(ge=0)]


class ComparisonAiSheetChanges(_Object):
    """The AI description of changes of a series: the latest job (absent until one was started) and the
    progress of each transition."""

    series_id: ComparisonSeriesId
    transitions: Annotated[list[ComparisonAiTransitionProgress], Field(max_length=100)]
    job: ComparisonAiJob = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonReviewSheetKind(str, enum.Enum):
    """``to_check``: the AI found no change but the comparison left marks («Проверить»). ``added`` and
    ``removed``: a single sheet of the transition, described on its own."""

    TO_CHECK = "to_check"
    ADDED = "added"
    REMOVED = "removed"


class ComparisonReviewSheet(_Object):
    sheet_pair_id: ComparisonSheetPairId
    kind: ComparisonReviewSheetKind
    state: ComparisonAiSheetState
    page_a: ComparisonPairPage = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    page_b: ComparisonPairPage = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonReviewSheetPage(_Object):
    """In the order of the matrix rows."""

    items: list[ComparisonReviewSheet]
    page: PageInfo


class ComparisonAiQueueItem(_Object):
    """One job in the installation's AI queue «Очередь «ИИ-описание изменений»»."""

    job_id: ComparisonAiJobId
    method: ComparisonAiMethod
    state: ComparisonAiJobState
    project_uid: ProjectUid
    document_uid: DocumentUid
    counts: ComparisonAiJobCounts
    created_at: datetime
    series_id: ComparisonSeriesId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    queue_position: Annotated[int, Field(ge=1)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    binding_state: ExecutorBindingState = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    wait_reason: RunQueueReason = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonAiQueue(_Object):
    """The AI jobs that are queued, running or paused anywhere in the installation, running first, then
    in the order they will start. A read for any role; it starts nothing."""

    items: Annotated[list[ComparisonAiQueueItem], Field(max_length=200)]
    queued: Annotated[int, Field(ge=0)]
    running: Annotated[int, Field(ge=0)]
    paused: Annotated[int, Field(ge=0)]


# --- specifications (CMP-VC-SPEC-01) ---------------------------------------------------------


class ComparisonSpecMethod(str, enum.Enum):
    """``whole``: «полное сравнение», the whole specification of each version was read by a model and the
    two were compared order-independently. ``sheet_ai``: «листовой ИИ», the specification sheets are
    described one by one in the AI description of changes."""

    WHOLE = "whole"
    SHEET_AI = "sheet_ai"


class ComparisonSpecState(str, enum.Enum):
    """``not_applicable``: the transition has no specification sheet. ``incomplete``: a side could not be
    read completely and no addition, removal or absence of change is published. ``running`` and
    ``paused`` carry the phase."""

    NOT_APPLICABLE = "not_applicable"
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComparisonSpecPhase(str, enum.Enum):
    PREPARING = "preparing"
    COMPARING = "comparing"
    DONE = "done"


class ComparisonSpecChangeKind(str, enum.Enum):
    """``changed``, ``added`` «+добавлено», ``removed`` «−удалено», ``unclear`` «?неясно» (the match is
    ambiguous), ``renumbered`` (only the position number differs) and ``moved`` (the same position under
    another section, not a change)."""

    CHANGED = "changed"
    ADDED = "added"
    REMOVED = "removed"
    UNCLEAR = "unclear"
    RENUMBERED = "renumbered"
    MOVED = "moved"


class ComparisonSpecPosition(_Object):
    """One position of a specification, every value verbatim as the sheet writes it (nothing is summed,
    rounded or normalised). ``section`` and ``parent`` place the row; ``ambiguous`` marks a row whose type
    the parser could not decide and did not guess."""

    name: Annotated[str, Field(max_length=400)]
    pos: Annotated[str, Field(max_length=32)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    mark: Annotated[str, Field(max_length=200)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    code: Annotated[str, Field(max_length=120)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    supplier: Annotated[str, Field(max_length=200)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    unit: Annotated[str, Field(max_length=32)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    quantity: Annotated[str, Field(max_length=64)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    mass: Annotated[str, Field(max_length=64)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    note: Annotated[str, Field(max_length=400)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    section: Annotated[str, Field(max_length=200)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    parent: Annotated[str, Field(max_length=400)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    ambiguous: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    page: ComparisonPageRef = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonSpecFieldChange(_Object):
    """«было → стало» of one field. ``field`` is one of the nine fields of a position of a specification
    (GOST 21.110): ``pos``, ``name``, ``mark``, ``code``, ``supplier``, ``unit``, ``quantity``, ``mass``
    and ``note`` (an open word, so that the contract does not freeze the table layout)."""

    field: Annotated[str, Field(pattern=r"^[a-z][a-z_]{1,15}$")]
    was: Annotated[str, Field(max_length=400)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    now: Annotated[str, Field(max_length=400)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonSpecChange(_Object):
    """One change between two specifications: the position before (``old``) and after (``new``), the
    fields that differ, and the sentence the comparison renders. A position that exists on one side only
    is ``added`` or ``removed`` and carries that side."""

    change_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,31}$")]
    kind: ComparisonSpecChangeKind
    fields: Annotated[list[ComparisonSpecFieldChange], Field(max_length=9)]
    old: ComparisonSpecPosition = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    new: ComparisonSpecPosition = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    text: Annotated[str, Field(min_length=1, max_length=600)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonSpecTotals(_Object):
    """«изменено / +добавлено / −удалено / ?неясно», and the two kinds that are not changes."""

    changed: Annotated[int, Field(ge=0)]
    added: Annotated[int, Field(ge=0)]
    removed: Annotated[int, Field(ge=0)]
    unclear: Annotated[int, Field(ge=0)]
    renumbered: Annotated[int, Field(ge=0)]
    moved: Annotated[int, Field(ge=0)]


class ComparisonSpecCoverage(_Object):
    """«покрыто»: the blocks of the specification text the model's markup covers and the rows it could
    not settle. A quote or a value the program cannot find in the source makes that side incomplete."""

    blocks_total: Annotated[int, Field(ge=0)]
    blocks_covered: Annotated[int, Field(ge=0)]
    rows_total: Annotated[int, Field(ge=0)]
    rows_unresolved: Annotated[int, Field(ge=0)]


class ComparisonSpecification(_Object):
    """The comparison of the specifications of one transition: the method, the number of specification
    sheets of the older and of the newer version, the coverage and the totals once there are any, and the
    reason a side is incomplete or the comparison failed (an engine-style code). The changes themselves
    are read page by page. Part B is model output not confirmed by an engineer; the deterministic
    positions of part A are read per sheet."""

    transition_id: ComparisonTransitionId
    method: ComparisonSpecMethod
    state: ComparisonSpecState
    sheets_a: Annotated[int, Field(ge=0)]
    sheets_b: Annotated[int, Field(ge=0)]
    comparison_id: ComparisonSpecComparisonId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    phase: ComparisonSpecPhase = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    coverage_a: ComparisonSpecCoverage = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    coverage_b: ComparisonSpecCoverage = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    totals: ComparisonSpecTotals = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    reason: Annotated[str, Field(pattern=_ENGINE_CODE)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    job_id: ComparisonAiJobId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    extraction_a_id: ComparisonSpecExtractionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    extraction_b_id: ComparisonSpecExtractionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    updated_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonSpecificationPage(_Object):
    """The transitions of a series that have a specification, in transition order."""

    items: list[ComparisonSpecification]
    page: PageInfo


class ComparisonSpecChangePage(_Object):
    """The changes of a transition's specification comparison, in the order the comparison lists them
    (changed, removed, added, unclear, renumbered)."""

    items: list[ComparisonSpecChange]
    page: PageInfo


class ComparisonSpecPage(_Object):
    """Part A for one page of a version: whether the page is a specification sheet and, when it is, the
    positions the deterministic parser reads from the page's words and vector lines (``spec_version`` is
    the parser's). Deterministic; no model is called."""

    page_profile_id: ComparisonPageProfileId
    is_specification: bool
    spec_version: Annotated[str, Field(min_length=1, max_length=32)]
    positions: Annotated[list[ComparisonSpecPosition], Field(max_length=2000)]
    ambiguous_rows: Annotated[int, Field(ge=0)]


class ComparisonSheetPairSpecPositions(_Object):
    """«Спецификация по позициям» of a sheet pair: the position changes that fall on the pair's pages,
    deterministic, from the positions of the whole specification of each version (a position may move
    between pages without changing)."""

    sheet_pair_id: ComparisonSheetPairId
    is_specification: bool
    totals: ComparisonSpecTotals
    changes: Annotated[list[ComparisonSpecChange], Field(max_length=2000)]


# --- the launch queue (CMP-VC-QUEUE-01) --------------------------------------------------------


class ComparisonLaunchEntryState(str, enum.Enum):
    """``waiting``, ``running``, ``done``, ``skipped`` (the step needed nothing or its set was removed),
    ``failed``, and ``needs_consent``: an AI step whose estimate now exists and has not been consented
    to. A queue asks for AI consent per set only when its estimate exists."""

    WAITING = "waiting"
    RUNNING = "running"
    NEEDS_CONSENT = "needs_consent"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


class ComparisonLaunchQueueState(str, enum.Enum):
    """«идёт», «на паузе», «ошибка — процесс остановлен», «выполнена», «пусто»."""

    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    DONE = "done"
    IDLE = "idle"


class ComparisonLaunchEntry(_Object):
    """One selected step of one document set. The queue runs one step at a time across sets, in the order
    of ``position`` (``1`` first): the profiles, the matrix, the AI check of pairs, the series, the AI
    description, the summary and report. ``job_id`` and ``series_id`` name what the entry started."""

    entry_id: ComparisonLaunchEntryId
    document_uid: DocumentUid
    step: ComparisonStepId
    state: ComparisonLaunchEntryState
    position: Annotated[int, Field(ge=1)]
    restart: bool
    created_at: datetime
    updated_at: datetime
    reason: Annotated[str, Field(pattern=_REASON_CODE)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    job_id: ComparisonAiJobId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    series_id: ComparisonSeriesId = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonLaunchQueueCounts(_Object):
    """«готово N из M · пропущено K · ошибок E»: ``done`` of ``total``, ``skipped``, ``failed``, and those
    ``running``, ``waiting`` and ``needs_consent``."""

    total: Annotated[int, Field(ge=0)]
    done: Annotated[int, Field(ge=0)]
    running: Annotated[int, Field(ge=0)]
    waiting: Annotated[int, Field(ge=0)]
    needs_consent: Annotated[int, Field(ge=0)]
    skipped: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]


class ComparisonLaunchQueue(_Object):
    """«Очередь запуска» of a project. A project has one queue; reading it starts nothing."""

    project_uid: ProjectUid
    state: ComparisonLaunchQueueState
    counts: ComparisonLaunchQueueCounts
    entries: Annotated[list[ComparisonLaunchEntry], Field(max_length=500)]
    updated_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonLaunchItem(_Object):
    """A set and a step to queue. ``consent`` is given for an AI step (``ai_pairs``, ``ai_changes``,
    ``report``) whose estimate exists, one consent per set; for a step with no estimate yet the entry waits
    and becomes ``needs_consent``. A consent on a step that is not an AI step is
    ``422 validation_failed``."""

    document_uid: DocumentUid
    step: ComparisonStepId
    consent: ComparisonAiConsent = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class EnqueueComparisonLaunchRequest(_Object):
    """«Запустить выбранные по очереди» / «Поставить в очередь». The ``upload`` step cannot be queued
    (``422 validation_failed``, ``comparison_step_not_queueable``). ``restart`` is «Заново» for the
    ``series`` and ``ai_changes`` steps."""

    items: Annotated[list[ComparisonLaunchItem], Field(min_length=1, max_length=200)]
    restart: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]


# --- the MD summary and the PDF report (CMP-VC-REPORT-01) ----------------------------------------


class ComparisonReportKind(str, enum.Enum):
    """``client``: «Отчёт для заказчика · Изменения проектных решений», one model call per transition over
    the summary's facts; a program check drops every point whose number, mark or direction the facts do not
    confirm. ``analytic``: analyst, verifier and composer."""

    CLIENT = "client"
    ANALYTIC = "analytic"


class ComparisonReportSource(str, enum.Enum):
    """``series_summary``: the deterministic MD summary of the series. ``uploaded_md``: an MD file the
    user uploaded (UTF-8, at most 20 MiB, with the transitions headed «## N. … A → B»)."""

    SERIES_SUMMARY = "series_summary"
    UPLOADED_MD = "uploaded_md"


class ComparisonReportState(str, enum.Enum):
    """``draft``: created with its estimate, not started and nothing spent. ``partial``: finished with a
    transition missing or a unit failed («неполный результат»)."""

    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComparisonReportStage(str, enum.Enum):
    """«файл принят, подготовка», «анализ переходов», «проверка выводов», «составление отчёта»,
    «написание текста для заказчика» (the client kind) and «формирование PDF»."""

    INTAKE = "intake"
    TRANSITION_ANALYSIS = "transition_analysis"
    VERIFICATION = "verification"
    COMPOSITION = "composition"
    CLIENT_WRITING = "client_writing"
    PDF_WRITING = "pdf_writing"


class ComparisonReportUnitMark(str, enum.Enum):
    """«✓ ⟳ ✗ ·»."""

    DONE = "done"
    RUNNING = "running"
    FAILED = "failed"
    PENDING = "pending"


class ComparisonReportFacts(_Object):
    """The program's check of the analyst's claims against the source: found, confirmed, contradicted,
    unconfirmed."""

    found: Annotated[int, Field(ge=0)]
    confirmed: Annotated[int, Field(ge=0)]
    contradicted: Annotated[int, Field(ge=0)]
    unconfirmed: Annotated[int, Field(ge=0)]


class ComparisonReportPart(_Object):
    """The progress of one transition of a report. An analytic report fills ``analysis``,
    ``verification``, ``facts`` and ``warnings`` («Анализ», «Проверка», «Факты», «Предупреждения»); a
    client report ``selection``, ``points`` and ``questions`` («Отбор», «Пунктов», «Вопросов»)."""

    transition_id: ComparisonTransitionId
    analysis: ComparisonReportUnitMark = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    verification: ComparisonReportUnitMark = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    selection: ComparisonReportUnitMark = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    facts: ComparisonReportFacts = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    warnings: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    points: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    questions: Annotated[int, Field(ge=0)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonReportArtifactKind(str, enum.Enum):
    REPORT_PDF = "report_pdf"
    SOURCE_MD = "source_md"


class ComparisonReportArtifact(_Object):
    """A stored file of a report, downloaded by ``streamComparisonReportPdf`` or
    ``streamComparisonReportSourceMd``."""

    kind: ComparisonReportArtifactKind
    size_bytes: Annotated[int, Field(ge=0)]
    sha256: Sha256
    created_at: datetime


class ComparisonReport(_Object):
    """A report built from the MD summary of a series. A ``draft`` carries the ``estimate`` the start
    consents to; once started, ``job`` holds the consented estimate and the spend. ``prepared_from_id``
    names the analytic report a client report was prepared from. ``reuse`` reuses the finished parts of
    earlier reports of the same summary. Every page of the PDF carries the unconfirmed-by-an-engineer
    label and the recall line («изменённых листов N, описано K, отброшено проверкой D»); the label is the
    client's text, the figures are the report's."""

    report_id: ComparisonReportId
    series_id: ComparisonSeriesId
    project_uid: ProjectUid
    document_uid: DocumentUid
    kind: ComparisonReportKind
    source: ComparisonReportSource
    state: ComparisonReportState
    reuse: bool
    parts: Annotated[list[ComparisonReportPart], Field(max_length=100)]
    artifacts: Annotated[list[ComparisonReportArtifact], Field(max_length=4)]
    created_at: datetime
    updated_at: datetime
    stage: ComparisonReportStage = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    estimate: ComparisonAiEstimate = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    job: ComparisonAiJob = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    source_name: Annotated[str, Field(min_length=1, max_length=200)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    prepared_from_id: ComparisonReportId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    failure_reason: Annotated[str, Field(pattern=_REASON_CODE)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    finished_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ComparisonReportPage(_Object):
    """The report history of a series, newest first."""

    items: list[ComparisonReport]
    page: PageInfo


class CreateComparisonReportRequest(_Object):
    """Creates a ``draft`` report from the series' MD summary and computes its estimate; no model is
    called and nothing is spent. ``kind`` defaults to ``client``."""

    kind: ComparisonReportKind = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    reuse: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class PrepareComparisonClientReportRequest(_Object):
    """«Подготовить отчёт для заказчика» from a finished analytic report: a new ``client`` draft that
    reads the analytic report's verified facts."""

    reuse: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]


# --- deterministic stage comparison (`CMP-SEAL-C3`, ADR-0025) --------------------------

StageUploadId = TypeAliasType("StageUploadId", Annotated[str, Field(pattern=rf"^stu_{_ULID}$")])
StageUploadFileId = TypeAliasType("StageUploadFileId", Annotated[str, Field(pattern=rf"^suf_{_ULID}$")])
StageUploadCandidateId = TypeAliasType(
    "StageUploadCandidateId", Annotated[str, Field(pattern=rf"^suc_{_ULID}$")]
)
StagePairId = TypeAliasType("StagePairId", Annotated[str, Field(pattern=rf"^stp_{_ULID}$")])
StageAssemblyId = TypeAliasType("StageAssemblyId", Annotated[str, Field(pattern=rf"^sas_{_ULID}$")])
StageLinkRevisionId = TypeAliasType(
    "StageLinkRevisionId", Annotated[str, Field(pattern=rf"^slk_{_ULID}$")]
)
StageLinkItemId = TypeAliasType("StageLinkItemId", Annotated[str, Field(pattern=rf"^sli_{_ULID}$")])
StageTextFragmentId = TypeAliasType(
    "StageTextFragmentId", Annotated[str, Field(pattern=rf"^stf_{_ULID}$")]
)
StageTextExclusionId = TypeAliasType(
    "StageTextExclusionId", Annotated[str, Field(pattern=rf"^ste_{_ULID}$")]
)
StageTextDifferenceId = TypeAliasType(
    "StageTextDifferenceId", Annotated[str, Field(pattern=rf"^std_{_ULID}$")]
)
StageTextHintId = TypeAliasType("StageTextHintId", Annotated[str, Field(pattern=rf"^sth_{_ULID}$")])
StageChainRunId = TypeAliasType("StageChainRunId", Annotated[str, Field(pattern=rf"^crn_{_ULID}$")])
StageChainStepId = TypeAliasType("StageChainStepId", Annotated[str, Field(pattern=rf"^cst_{_ULID}$")])


class StageUploadFileKind(str, enum.Enum):
    PDF = "pdf"
    ZIP = "zip"


class StageUploadFileDeclaration(_Object):
    display_name: Annotated[str, Field(min_length=1, max_length=255)]
    media_kind: StageUploadFileKind
    size_bytes: Annotated[int, Field(ge=1)]
    sha256: Sha256


class CreateStageUploadRequest(_Object):
    files: Annotated[list[StageUploadFileDeclaration], Field(min_length=1)]


class StageUploadFile(_Object):
    file_id: StageUploadFileId
    upload_id: StageUploadId
    declaration: StageUploadFileDeclaration
    state: Literal["declared", "receiving", "received", "admitting", "ready", "failed", "cancelled"]
    received_parts: int
    received_bytes: int
    created_at: datetime
    failure_reason: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageUploadCandidate(_Object):
    candidate_id: StageUploadCandidateId
    file_id: StageUploadFileId
    member_number: Annotated[int, Field(ge=1, le=2**31 - 1)]
    display_name: Annotated[str, Field(min_length=1, max_length=255)]
    state: Literal["proposed", "confirmed", "admitting", "published", "rejected", "failed"]
    proposed_stage: Literal["P", "R"] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    proposed_section: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    designation: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    confirmed_stage: Literal["P", "R"] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    confirmed_section: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    document_uid: DocumentUid = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    version_uid: VersionUid = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    failure_reason: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageUpload(_Object):
    upload_id: StageUploadId
    project_uid: ProjectUid
    state: Literal["uploading", "paused", "admitting", "completed", "failed", "cancelled"]
    files: list[StageUploadFile]
    candidates: list[StageUploadCandidate]
    created_at: datetime
    updated_at: datetime


class StageUploadPage(_Object):
    items: list[StageUpload]
    page: PageInfo


class StageUploadPartReceipt(_Object):
    upload_id: StageUploadId
    file_id: StageUploadFileId
    part_number: Annotated[int, Field(ge=1, le=10000)]
    size_bytes: Annotated[int, Field(ge=1, le=16_777_216)]
    sha256: Sha256
    received_bytes: int


class ConfirmStageUploadCandidateRequest(_Object):
    stage: Literal["P", "R"]
    section_code: Annotated[str, Field(pattern=r"^[A-Z]{2,3}$")]
    designation: Annotated[str, Field(min_length=1, max_length=200)]
    existing_document_uid: DocumentUid = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageAssemblyMember(_Object):
    document_uid: DocumentUid
    member_no: Annotated[int, Field(ge=1)]


class StageAssembly(_Object):
    assembly_id: StageAssemblyId
    project_uid: ProjectUid
    label: Annotated[str, Field(min_length=1, max_length=200)]
    members: list[StageAssemblyMember]
    member_revision_no: Annotated[int, Field(ge=0)]
    created_at: datetime


class CreateStageAssemblyRequest(_Object):
    label: Annotated[str, Field(min_length=1, max_length=200)]
    document_uids: Annotated[list[DocumentUid], Field(min_length=2, max_length=100)]


class ReviseStageAssemblyRequest(_Object):
    base_member_no: Annotated[int, Field(ge=0)]
    add_document_uids: Annotated[list[DocumentUid], Field(max_length=100)]
    remove_document_uids: Annotated[list[DocumentUid], Field(max_length=100)]


class StagePair(_Object):
    pair_id: StagePairId
    project_uid: ProjectUid
    left_document_uid: DocumentUid
    state: Literal["suggested", "confirmed", "archived"]
    completeness: Literal["unknown", "full", "partial"]
    created_at: datetime
    right_document_uid: DocumentUid = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    assembly_id: StageAssemblyId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    confirmed_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StagePairPage(_Object):
    items: list[StagePair]
    page: PageInfo


class StagePairSuggestion(_Object):
    left_document_uid: DocumentUid
    right_document_uid: DocumentUid
    reason: str
    score: Annotated[float, Field(ge=0, le=1)]


class StagePairSuggestionPage(_Object):
    items: list[StagePairSuggestion]
    page: PageInfo


class ConfirmStagePairRequest(_Object):
    left_document_uid: DocumentUid
    right_document_uid: DocumentUid = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    assembly_id: StageAssemblyId = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class SetStagePairCompletenessRequest(_Object):
    completeness: Literal["full", "partial"]


class StageSheetPassport(_Object):
    profile_id: ComparisonPageProfileId
    version_uid: VersionUid
    page_number: Annotated[int, Field(ge=1)]
    side: Literal["left", "right"]
    sheet_type: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    building: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    floor: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    level: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    sheet_number: str = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageSheetPassportPage(_Object):
    items: list[StageSheetPassport]
    page: PageInfo


class StageSheetSuggestion(_Object):
    left_profile_id: ComparisonPageProfileId
    right_profile_id: ComparisonPageProfileId
    score: Annotated[int, Field(ge=0)]
    confidence: Literal["high", "review"]
    reasons: list[str]


class StageSheetSuggestionPage(_Object):
    items: list[StageSheetSuggestion]
    page: PageInfo


class StageLinkItem(_Object):
    item_id: StageLinkItemId
    row_no: Annotated[int, Field(ge=1)]
    relation: Literal["paired", "only_left", "only_right"]
    confidence: Literal["high", "manual", "review", "automatic_repair", "unpaired"]
    left_profile_id: ComparisonPageProfileId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    right_profile_id: ComparisonPageProfileId = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageLinkRevision(_Object):
    revision_id: StageLinkRevisionId
    pair_id: StagePairId
    revision_no: Annotated[int, Field(ge=1)]
    source: Literal["expert", "automatic"]
    input_sha256: Sha256
    items: list[StageLinkItem]
    created_at: datetime
    base_revision_id: StageLinkRevisionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageLinkRevisionPage(_Object):
    items: list[StageLinkRevision]
    page: PageInfo


class StageLinkInput(_Object):
    relation: Literal["paired", "only_left", "only_right"]
    left_profile_id: ComparisonPageProfileId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    right_profile_id: ComparisonPageProfileId = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class ApplyStageSheetMapRequest(_Object):
    base_revision_id: StageLinkRevisionId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    items: Annotated[list[StageLinkInput], Field(min_length=1, max_length=1000)]


class StageTextFragment(_Object):
    fragment_id: StageTextFragmentId
    pair_id: StagePairId
    profile_id: ComparisonPageProfileId
    side: Literal["left", "right"]
    text: Annotated[str, Field(min_length=1, max_length=20000)]
    box_anchor: dict[str, float]
    content_key: Sha256


class StageTextFragmentPage(_Object):
    items: list[StageTextFragment]
    page: PageInfo


class StageTextExclusion(_Object):
    exclusion_id: StageTextExclusionId
    revision_id: StageLinkRevisionId
    left_fragment_id: StageTextFragmentId
    right_fragment_id: StageTextFragmentId
    proof_kind: Literal["same", "moved"]


class StageTextExclusionPage(_Object):
    items: list[StageTextExclusion]
    page: PageInfo


class StageTextDifference(_Object):
    difference_id: StageTextDifferenceId
    revision_id: StageLinkRevisionId
    status: Literal["changed", "removed", "added"]
    left_fragment_id: StageTextFragmentId = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    right_fragment_id: StageTextFragmentId = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageTextDifferencePage(_Object):
    items: list[StageTextDifference]
    page: PageInfo


class StageTextHint(_Object):
    source_side: Literal["left", "right"] = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    hint_id: StageTextHintId
    revision_id: StageLinkRevisionId
    source_fragment_id: StageTextFragmentId
    target_fragment_id: StageTextFragmentId


class StageTextHintPage(_Object):
    items: list[StageTextHint]
    page: PageInfo


class StageChainStep(_Object):
    step_id: StageChainStepId
    step_no: Annotated[int, Field(ge=1, le=7)]
    state: Literal["queued", "running", "paused", "completed", "failed", "cancelled"]
    counts: dict[str, int]
    started_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    finished_at: datetime = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageChainRun(_Object):
    engine: Literal["classic", "v3_native_text_experimental"] = "classic"
    experimental_progress: dict[str, Any] | None = None
    run_id: StageChainRunId
    pair_id: StagePairId
    link_revision_id: StageLinkRevisionId
    input_sha256: Sha256
    pinned_version_uids: Annotated[list[VersionUid], Field(min_length=2, max_length=100)]
    state: Literal["queued", "running", "paused", "completed", "failed", "cancelled"]
    steps: Annotated[list[StageChainStep], Field(max_length=7)]
    created_at: datetime
    updated_at: datetime
    stale: bool
    effective_link_revision_id: StageLinkRevisionId = Field(**_NOT_GIVEN)
    kind: Literal["deterministic", "full"] = Field(**_NOT_GIVEN)
    with_ai: bool = Field(**_NOT_GIVEN)
    ai_job_id: ComparisonAiJobId = Field(**_NOT_GIVEN)
    batch_id: Annotated[str, Field(pattern=rf"^scb_{_ULID}$")] = Field(**_NOT_GIVEN)
    pause_reason: str = Field(**_NOT_GIVEN)
    failure_reason: str = Field(**_NOT_GIVEN)


class StageChainRunPage(_Object):
    items: list[StageChainRun]
    page: PageInfo


class StartStageChainRunRequest(_Object):
    engine: Literal["classic", "v3_native_text_experimental"] = "classic"
    link_revision_id: StageLinkRevisionId
    restart: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    consent: ComparisonAiConsent = Field(**_NOT_GIVEN)  # type: ignore[assignment]
    with_ai: bool = Field(**_NOT_GIVEN)  # type: ignore[assignment]


# CMP-SEAL-C4: versioned stage AI, repairs, expert cards and journal contracts.
StageAiUnitId = TypeAliasType("StageAiUnitId", Annotated[str, Field(pattern=rf"^saunit_{_ULID}$")])
StageAiReviewId = TypeAliasType("StageAiReviewId", Annotated[str, Field(pattern=rf"^sarev_{_ULID}$")])
StageAiClassificationId = TypeAliasType("StageAiClassificationId", Annotated[str, Field(pattern=rf"^sacls_{_ULID}$")])
StageAiSynthesisId = TypeAliasType("StageAiSynthesisId", Annotated[str, Field(pattern=rf"^sasyn_{_ULID}$")])
StageGraphicEvidenceId = TypeAliasType("StageGraphicEvidenceId", Annotated[str, Field(pattern=rf"^sge_{_ULID}$")])
StageLinkRepairId = TypeAliasType("StageLinkRepairId", Annotated[str, Field(pattern=rf"^crp_{_ULID}$")])
StageLinkRepairEventId = TypeAliasType("StageLinkRepairEventId", Annotated[str, Field(pattern=rf"^crpe_{_ULID}$")])
StageChangeCardId = TypeAliasType("StageChangeCardId", Annotated[str, Field(pattern=rf"^ccd_{_ULID}$")])
StageCardEvidenceId = TypeAliasType("StageCardEvidenceId", Annotated[str, Field(pattern=rf"^sce_{_ULID}$")])
StageCardVerdictId = TypeAliasType("StageCardVerdictId", Annotated[str, Field(pattern=rf"^cdv_{_ULID}$")])
StageChainBatchId = TypeAliasType("StageChainBatchId", Annotated[str, Field(pattern=rf"^scb_{_ULID}$")])
StageChainBatchItemId = TypeAliasType("StageChainBatchItemId", Annotated[str, Field(pattern=rf"^scbi_{_ULID}$")])
StageAtomicEvidenceId = TypeAliasType("StageAtomicEvidenceId", Annotated[str, Field(pattern=rf"^(stf|std|sge)_{_ULID}$")])


class StageSystem(str, enum.Enum):
    UNKNOWN = "unknown"
    ARCHITECTURE = "architecture"
    STRUCTURAL = "structural"
    ELECTRICAL = "electrical"
    HEATING_VENTILATION = "heating_ventilation"
    WATER_SEWAGE = "water_sewage"
    FIRE_PROTECTION = "fire_protection"
    LOW_CURRENT = "low_current"
    TECHNOLOGY = "technology"
    SITE = "site"
    OTHER = "other"


class StageChangeCategory(str, enum.Enum):
    AREAS = "areas"
    FLOORS = "floors"
    ELECTRICAL_LOAD = "electrical_load"
    CALCULATION_METHOD = "calculation_method"
    CONSUMER_COMPOSITION = "consumer_composition"
    ROOM_COMPOSITION = "room_composition"
    DIMENSIONS = "dimensions"
    MATERIALS = "materials"
    EQUIPMENT_PARAMETERS = "equipment_parameters"
    SYSTEM_CONFIGURATION = "system_configuration"
    FIRE_SAFETY = "fire_safety"
    DESIGNATION_RENAME = "designation_rename"
    ADMINISTRATIVE = "administrative"
    DOCUMENTATION_STRUCTURE = "documentation_structure"
    FORMATTING = "formatting"
    OTHER_PROJECT = "other_project"
    OTHER_SERVICE = "other_service"
    UNCERTAIN = "uncertain"


class StageReviewDecision(_Object):
    left_fragment_ids: list[StageTextFragmentId]
    right_fragment_ids: list[StageTextFragmentId]
    status: Literal["SAME", "MOVED", "CHANGED", "REMOVED", "ADDED", "UNCERTAIN"]
    confidence: Literal["high", "medium", "low"]
    summary: Annotated[str, Field(max_length=2000)]
    reason: Annotated[str, Field(max_length=2000)]
    actual_right_profile_ids: list[ComparisonPageProfileId] = Field(default_factory=list)
    model_status: str = Field(**_NOT_GIVEN)
    policy_reasons: list[str] = Field(default_factory=list)


class StageAiReview(_Object):
    review_id: StageAiReviewId
    run_id: StageChainRunId
    unit_id: StageAiUnitId
    group_id: Annotated[str, Field(min_length=1, max_length=128)]
    source_sha256: Sha256
    content_key: Sha256
    decisions: Annotated[list[StageReviewDecision], Field(max_length=800)]
    model_identity: dict[str, Any]
    created_at: datetime


class StageAiReviewPage(_Object):
    items: list[StageAiReview]
    page: PageInfo


class StageClassificationCard(_Object):
    card_key: Sha256
    evidence_digest: Sha256
    class_name: Literal["PROJECT_CHANGE", "SERVICE_STRUCTURE", "REVIEW"]
    category: StageChangeCategory
    title: Annotated[str, Field(min_length=1, max_length=260)]
    system: StageSystem
    evidence_ids: Annotated[list[StageAtomicEvidenceId], Field(min_length=1)]
    model_class: str = Field(**_NOT_GIVEN)
    policy_reasons: list[str] = Field(default_factory=list)
    materiality: Literal["material", "non_material", "unknown"] = Field(**_NOT_GIVEN)
    importance: Literal["high", "normal", "unknown"] = Field(**_NOT_GIVEN)
    detail_increased: bool = Field(**_NOT_GIVEN)



class StageAiClassification(_Object):
    classification_id: StageAiClassificationId
    run_id: StageChainRunId
    unit_id: StageAiUnitId
    group_id: Annotated[str, Field(min_length=1, max_length=128)]
    source_sha256: Sha256
    content_key: Sha256
    cards: list[StageClassificationCard]
    model_identity: dict[str, Any]
    created_at: datetime


class StageAiClassificationPage(_Object):
    items: list[StageAiClassification]
    page: PageInfo


class StageSynthesisResult(_Object):
    group_id: str
    source_sha256: Sha256
    evidence_ids: list[StageAtomicEvidenceId]
    decision: str
    change_type: str
    title: Annotated[str, Field(max_length=260)]
    reason: Annotated[str, Field(max_length=2000)]


class StageAiSynthesis(_Object):
    synthesis_id: StageAiSynthesisId
    run_id: StageChainRunId
    unit_id: StageAiUnitId
    content_key: Sha256
    result: StageSynthesisResult
    model_identity: dict[str, Any]
    created_at: datetime


class StageGraphicEvidence(_Object):
    graphic_id: StageGraphicEvidenceId
    run_id: StageChainRunId
    link_item_id: StageLinkItemId
    status: Literal["not_checked", "unreliable", "reliable"]
    reason: str
    left_profile_id: ComparisonPageProfileId = Field(**_NOT_GIVEN)
    right_profile_id: ComparisonPageProfileId = Field(**_NOT_GIVEN)
    result_id: ComparisonSheetPairResultId = Field(**_NOT_GIVEN)
    regions: list[dict[str, Any]] = Field(default_factory=list)
    content_key: Sha256


class StageGraphicEvidencePage(_Object):
    items: list[StageGraphicEvidence]
    page: PageInfo


class StageLinkRepair(_Object):
    repair_id: StageLinkRepairId
    run_id: StageChainRunId
    before_revision_id: StageLinkRevisionId
    after_revision_id: StageLinkRevisionId
    proof: dict[str, Any]
    state: Literal["applied", "undone", "superseded"]
    created_at: datetime


class StageLinkRepairPage(_Object):
    items: list[StageLinkRepair]
    page: PageInfo


class UndoStageLinkRepairRequest(_Object):
    base_revision_id: StageLinkRevisionId


class StageCardEvidence(_Object):
    evidence_id: StageCardEvidenceId
    kind: Literal["TEXT", "TABLE", "GRAPHIC"]
    source_id: StageAtomicEvidenceId
    side: Literal["left", "right", "both"]
    profile_id: ComparisonPageProfileId = Field(**_NOT_GIVEN)
    box_anchor: dict[str, float] = Field(default_factory=dict)
    absence_proven: bool = False


class StageCardVerdict(_Object):
    verdict_id: StageCardVerdictId
    card_id: StageChangeCardId
    revision_no: Annotated[int, Field(ge=1)]
    decision: Literal["accepted", "rejected"]
    reason: Annotated[str, Field(max_length=2000)]
    evidence_digest: Sha256
    created_at: datetime


class StageCardVerdictPage(_Object):
    items: list[StageCardVerdict]
    page: PageInfo


class StageChangeCard(_Object):
    experimental: dict[str, Any] | None = None
    card_id: StageChangeCardId
    run_id: StageChainRunId
    card_key: Sha256
    evidence_digest: Sha256
    class_name: Literal["PROJECT_CHANGE", "SERVICE_STRUCTURE", "REVIEW"]
    category: StageChangeCategory
    title: Annotated[str, Field(min_length=1, max_length=260)]
    system: StageSystem
    evidence_ids: list[StageAtomicEvidenceId]
    before: Annotated[str, Field(max_length=20000)]
    after: Annotated[str, Field(max_length=20000)]
    evidence: list[StageCardEvidence] = Field(default_factory=list)
    verdict: StageCardVerdict = Field(**_NOT_GIVEN)
    carryover: Literal["none", "full", "partial", "stale"] = "none"
    carried_verdict_ids: list[StageCardVerdictId] = Field(default_factory=list)
    stale: bool
    materiality: Literal["material", "non_material", "unknown"] = Field(**_NOT_GIVEN)
    importance: Literal["high", "normal", "unknown"] = Field(**_NOT_GIVEN)
    detail_increased: bool = Field(**_NOT_GIVEN)



class StageChangeCardPage(_Object):
    items: list[StageChangeCard]
    page: PageInfo
    counts: dict[str, int]


class StageCardVerdictInput(_Object):
    card_id: StageChangeCardId
    expected_revision: Annotated[int, Field(ge=0)]
    decision: Literal["accepted", "rejected"]
    reason: Annotated[str, Field(max_length=2000)]


class ApplyStageCardVerdictsRequest(_Object):
    updates: Annotated[list[StageCardVerdictInput], Field(min_length=1, max_length=500)]


class StageChangeJournal(_Object):
    run_id: StageChainRunId
    grouping: Literal["designation", "section", "system"]
    groups: list[dict[str, Any]]
    accepted_count: Annotated[int, Field(ge=0)]
    ai_hidden_same_count: Annotated[int, Field(ge=0)]
    ai_service_count: Annotated[int, Field(ge=0)]
    stale: bool


class StageChainBatchSelection(_Object):
    pair_id: StagePairId
    link_revision_id: StageLinkRevisionId
    consent: ComparisonAiConsent = Field(**_NOT_GIVEN)


class StartStageChainBatchRequest(_Object):
    engine: Literal["classic", "v3_native_text_experimental"] = "classic"
    selections: Annotated[list[StageChainBatchSelection], Field(min_length=1, max_length=100)]
    with_ai: bool = True


class StageChainBatchItem(_Object):
    item_id: StageChainBatchItemId
    pair_id: StagePairId
    link_revision_id: StageLinkRevisionId
    position: Annotated[int, Field(ge=1)]
    state: Literal["queued", "running", "completed", "failed", "cancelled"]
    run_id: StageChainRunId = Field(**_NOT_GIVEN)


class StageChainBatch(_Object):
    batch_id: StageChainBatchId
    project_uid: ProjectUid
    state: Literal["queued", "running", "paused", "completed", "failed", "cancelled"]
    items: list[StageChainBatchItem]
    counts: dict[str, int]
    created_at: datetime
    updated_at: datetime


class StageProfileWord(_Object):
    text: Annotated[str, Field(max_length=20000)]
    x0: float
    top: float
    x1: float
    bottom: float


class StageProfileText(_Object):
    profile_id: ComparisonPageProfileId
    version_uid: VersionUid
    page_number: Annotated[int, Field(ge=1)]
    scan: bool
    has_text_layer: bool
    width_pt: float
    height_pt: float
    words: list[StageProfileWord]


class StageAiSynthesisPage(_Object):
    items: list[StageAiSynthesis]
    page: PageInfo


class ResumeStageChainRunRequest(_Object):
    consent: ComparisonAiConsent = Field(**_NOT_GIVEN)
    retry_failed: bool = False


class CreateStageReviewCardRequest(_Object):
    source_ids: Annotated[list[StageAtomicEvidenceId], Field(min_length=1, max_length=400)]
    reason: Annotated[str, Field(min_length=1, max_length=2000)]


class ExtendedRunReview(_Object):
    run_id: RunId
    status: Literal["not_started", "running", "completed", "partial", "failed", "unavailable"]
    result: dict[str, Any] | None = None


# --- the decision memory (`DECISION-MEMORY-01` phase M2, contract 1.44.0) ----------------------------
#
# A case is the copy of what an expert saw and said when a decision was taken (`ADR-0027`); it outlives the project and the document it came
# from. These schemas are read-only history except the two standing changes (withdraw, restore). **A forgotten case answers its tombstone
# only**: ``content`` is ``null`` and the lists are empty. The memory is not a decision authority; nothing here is a verdict in force.

DecisionMemoryCaseId = TypeAliasType(
    "DecisionMemoryCaseId", Annotated[str, Field(pattern=rf"^dmc_{_ULID}$")]
)
_MemoryCaseStatus = Literal["active", "withdrawn", "forgotten"]
_MemoryStatusReason = Literal["capture_defect", "wrong_decision", "client_request", "test_data", "other"]
_MemoryDataClass = Literal["test", "real"]
_MemoryVerdict = Literal["accepted", "rejected"]
_MemoryOrigin = Literal["direct", "carried", "imported"]


class DecisionMemoryCaseSummary(_Object):
    """One case as the list gives it: where it stands (``status``), the verdict of its latest decision and how many decisions it holds."""

    case_id: DecisionMemoryCaseId
    category: Annotated[str, Field(min_length=1, max_length=64)]
    section_code: Annotated[str, Field(min_length=1, max_length=64)] | None
    data_class: _MemoryDataClass
    crop_state: Literal["referenced", "none_available"]
    origin_project_uid: ProjectUid
    captured_at: datetime
    status: _MemoryCaseStatus
    status_reason_code: _MemoryStatusReason | None
    status_changed_at: datetime | None
    current_verdict: _MemoryVerdict | None
    current_severity: Severity | None
    current_origin_kind: _MemoryOrigin | None
    current_decided_at: datetime | None
    decision_count: Annotated[int, Field(ge=0)]


class DecisionMemoryCasePage(_Object):
    items: list[DecisionMemoryCaseSummary]
    page: PageInfo


class DecisionMemoryDecision(_Object):
    """One captured decision. ``comment`` is the expert's own words, ``null`` for a carried decision and for a forgotten case."""

    memory_decision_id: Annotated[str, Field(pattern=rf"^dmd_{_ULID}$")]
    event_type: Literal["accept", "reject"]
    verdict: _MemoryVerdict
    severity: Severity | None
    origin_kind: _MemoryOrigin
    decided_at: datetime
    comment: Annotated[str, Field(min_length=1, max_length=4000)] | None


class DecisionMemoryContent(_Object):
    """What the model proposed, as it stood when the decision was taken (immutable, a primary record from capture)."""

    finding_text: Annotated[str, Field(min_length=1, max_length=4000)]
    recommendation_text: Annotated[str, Field(min_length=1, max_length=4000)]
    proposed_severity: Severity | None
    required_value: Annotated[str, Field(min_length=1, max_length=200)] | None
    stated_value: Annotated[str, Field(min_length=1, max_length=200)] | None
    stage_id: Annotated[str, Field(min_length=1, max_length=64)]
    analysis_profile_id: AnalysisProfileId
    provider_mode: Literal["live", "recorded"]


class DecisionMemoryEvidence(_Object):
    """A quoted span the expert looked at. ``bbox`` is ``[x0, y0, x1, y1]`` in ``bbox_unit`` from ``bbox_origin`` when the block was known."""

    ordinal: Annotated[int, Field(ge=0)]
    page_number: Annotated[int, Field(ge=1)]
    quote: Annotated[str, Field(min_length=1, max_length=2000)]
    char_start: Annotated[int, Field(ge=0)]
    char_end: Annotated[int, Field(ge=1)]
    block_ref: Annotated[str, Field(pattern=r"^b_[0-9]{6}$")] | None
    bbox: Annotated[list[float], Field(min_length=4, max_length=4)] | None
    bbox_unit: Annotated[str, Field(min_length=1, max_length=32)] | None
    bbox_origin: Annotated[str, Field(min_length=1, max_length=32)] | None


class DecisionMemoryNormRef(_Object):
    """A certified normative reference the finding rested on (ids that stay resolvable, and the quoted norm text)."""

    ordinal: Annotated[int, Field(ge=1, le=5)]
    norm_document_id: NormDocumentId
    norm_paragraph_id: NormParagraphId
    designation: Annotated[str, Field(min_length=1, max_length=512)]
    clause_number: Annotated[str, Field(min_length=1, max_length=128)] | None
    page_label: Annotated[int, Field(ge=1)]
    quote: Annotated[str, Field(min_length=20, max_length=4000)]
    citation_state: Literal["verified", "rebound"]


class DecisionMemoryCrop(_Object):
    """A crop image the case references (a binding to an existing Blob, never a copy); ``bbox`` is the normalised box on the page."""

    crop_id: Annotated[str, Field(pattern=rf"^dmx_{_ULID}$")]
    crop_ordinal: Annotated[int, Field(ge=1, le=4)]
    evidence_ordinal: Annotated[int, Field(ge=0)] | None
    selection_rule: Annotated[str, Field(min_length=1, max_length=64)]
    page_number: Annotated[int, Field(ge=1)]
    bbox: Annotated[list[float], Field(min_length=4, max_length=4)]
    media_type: Literal["image/png"]
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    size_bytes: Annotated[int, Field(ge=1)]
    width_px: Annotated[int, Field(ge=1)]
    height_px: Annotated[int, Field(ge=1)]
    portal_description: Annotated[str, Field(min_length=1, max_length=4000)] | None


class DecisionMemoryStatusEvent(_Object):
    """One change of standing, newest last. A ``forget`` carries the digest of the content that was forgotten, never the content."""

    status_event_id: Annotated[str, Field(pattern=rf"^dmw_{_ULID}$")]
    kind: Literal["withdraw", "restore", "forget"]
    reason_code: _MemoryStatusReason
    created_at: datetime
    forgotten_content_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None


class DecisionMemoryCase(_Object):
    """A case with everything it keeps. ``content`` is ``null`` and the lists are empty for a forgotten case (its tombstone only)."""

    summary: DecisionMemoryCaseSummary
    content: DecisionMemoryContent | None
    decisions: list[DecisionMemoryDecision]
    evidence: list[DecisionMemoryEvidence]
    norm_refs: list[DecisionMemoryNormRef]
    crops: list[DecisionMemoryCrop]
    status_events: list[DecisionMemoryStatusEvent]


class DecisionMemoryCountRow(_Object):
    status: _MemoryCaseStatus
    data_class: _MemoryDataClass
    cases: Annotated[int, Field(ge=0)]


class DecisionMemoryStatus(_Object):
    """What the memory holds and the installation settings in force (nothing journalled means ``test`` and ``off``)."""

    data_class: _MemoryDataClass
    training_use: Literal["off", "on"]
    cases: Annotated[int, Field(ge=0)]
    decisions: Annotated[int, Field(ge=0)]
    by_status_and_class: list[DecisionMemoryCountRow]


class DecisionMemoryStatusChangeRequest(_Object):
    """Why a case is withdrawn or restored: a closed reason (free text would put personal data into an append-only record)."""

    reason_code: _MemoryStatusReason


class DecisionMemoryStatusChange(_Object):
    """What a withdraw or a restore did: the status event written (or, for a replay, the first call's) and the standing after it."""

    case_id: DecisionMemoryCaseId
    status_event_id: Annotated[str, Field(pattern=rf"^dmw_{_ULID}$")]
    kind: Literal["withdraw", "restore"]
    status: Literal["active", "withdrawn"]
    reason_code: _MemoryStatusReason
    changed_at: datetime


# --- executor hosts, the stage layout and the model catalogue (`HOSTS-SEAL-1`, ADR-0028, contract 1.45.0) ----------------
#
# A *host* is a server: one agent process, one host token, every provider client and key on that machine. The user sees servers,
# the models the servers can serve and the «Использовать» switch; connections, groups and capacity pools behind them are the stand's
# own (system-managed) and are never listed. The layout says which model answers each analysis stage; a run freezes the plan it was
# started with. This section is vocabulary and shapes only: no operation behaves before the wave-1 lanes implement it.


class ExecutorHostState(str, enum.Enum):
    """`online`: the agent reported within the last 120 seconds and a free slot exists. `busy`: online, every slot is in use.
    `offline`: no report within the last 120 seconds (or never)."""

    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"


class ModelUnavailableReason(str, enum.Enum):
    """Why a model cannot be used on a host, or anywhere, right now. Lists of servers and models hide what is unavailable; the
    reasons are shown only where an action is blocked or a run waits, and to the administrator in a server's details."""

    HOST_DISABLED = "host_disabled"
    HOST_OFFLINE = "host_offline"
    LOGIN_REQUIRED = "login_required"
    MODEL_NOT_VERIFIED = "model_not_verified"
    MODEL_COOLING_DOWN = "model_cooling_down"
    NOT_ON_ANY_SERVER = "not_on_any_server"


class ExecutorHostModel(_Object):
    """A model the host can serve now: `available` or, with every slot of its provider in use, `busy`."""

    provider: ExecutorProvider
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    access: ExecutorModelAccess
    state: Literal["available", "busy"]


class ExecutorHost(_Object):
    """A server (ADR-0028): its name, the «Использовать» switch, whether it is on line, the models it can serve now and its slots.
    `models` holds only what can be used (an unavailable model is not listed); the reasons are in `ExecutorHostDetails`."""

    host_id: ExecutorHostId
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    enabled: bool
    state: ExecutorHostState
    last_seen_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    agent_version: Annotated[str, Field(pattern=r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    models: Annotated[list[ExecutorHostModel], Field(max_length=64)]
    slots_total: Annotated[int, Field(ge=0)]
    slots_in_use: Annotated[int, Field(ge=0)]
    created_at: datetime
    created_by: UserUid
    archived_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutorHostList(_Object):
    """The servers, newest first, with the summary line of the screen: servers on line of all, free slots of all."""

    items: list[ExecutorHost]
    online: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=0)]
    slots_free: Annotated[int, Field(ge=0)]
    slots_total: Annotated[int, Field(ge=0)]


class ExecutorHostSlotUse(_Object):
    """The slots of a provider on a host: how many may run at once and how many do."""

    provider: ExecutorProvider
    access: ExecutorModelAccess
    slots: Annotated[int, Field(ge=1, le=16)]
    in_use: Annotated[int, Field(ge=0)]


class ExecutorHostModelStatus(_Object):
    """One model of a provider on a host with the reasons it cannot be used, if it cannot (administrator's view)."""

    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    state: Literal["available", "busy", "unavailable"]
    reasons: Annotated[list[ModelUnavailableReason], Field(max_length=8)]
    cooldown_until: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class ExecutorHostProviderDetail(_Object):
    """A provider found on the host: its access, its login, its client version and its models."""

    provider: ExecutorProvider
    access: ExecutorModelAccess
    auth_state: ProviderAuthState
    cli_version: Annotated[str, Field(min_length=1, max_length=64)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    models: Annotated[list[ExecutorHostModelStatus], Field(max_length=32)]


class ExecutorHostTask(_Object):
    """A call running on the host now: the run, the stage and since when."""

    task_id: ExecutorTaskId
    run_id: RunId
    provider: ExecutorProvider
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    stage_key: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    since: datetime


class ExecutorHostDetails(_Object):
    """«Подробнее» of a server (administrator): its slots, each provider with the reasons its models cannot be used, and the
    tasks running on it."""

    host: ExecutorHost
    slots: Annotated[list[ExecutorHostSlotUse], Field(max_length=8)]
    providers: Annotated[list[ExecutorHostProviderDetail], Field(max_length=8)]
    tasks: Annotated[list[ExecutorHostTask], Field(max_length=64)]


class SetExecutorHostEnabledRequest(_Object):
    """`true` switches the server on, `false` off. A server that is off takes no new run; runs already bound to it finish."""

    enabled: Annotated[bool, Field(strict=True)]


class SetExecutorHostSlotsRequest(_Object):
    """The providers whose slots change; at least one. Each change is a journalled event with its author."""

    slots: ExecutorHostSlots


class IssueExecutorHostEnrollmentRequest(_Object):
    """A new server and its one-time grant. The name is the administrator's; no model is asked for."""

    display_name: Annotated[str, Field(min_length=1, max_length=120)]


class CreateExecutorHostAgentInstallRequest(_Object):
    """A new server and an install session of the agent over SSH (path A). As `CreateExecutorAgentInstallRequest`, with a name and
    no model: `private_key` is required for `pasted_key` and refused for `generated_key`, sealed and never returned."""

    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    access: ExecutorAgentInstallAccess
    ssh_host: Annotated[str, Field(min_length=1, max_length=253)]
    ssh_port: Annotated[int, Field(ge=1, le=65535)]
    ssh_user: Annotated[str, Field(min_length=1, max_length=64)]
    private_key: Annotated[str, Field(min_length=8, max_length=8192)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=_optional_write_only
    )


class StageRowKey(str, enum.Enum):
    """A row of the stage layout: the analysis stage whose model is chosen. `text` (analysis of the text), `blocks` (analysis of
    the blocks), `cross_check` (the complex cross-check and the parameter passport), `norms` (the norms), `review` (the critic)
    and `correction` (the refinement)."""

    TEXT = "text"
    BLOCKS = "blocks"
    CROSS_CHECK = "cross_check"
    NORMS = "norms"
    REVIEW = "review"
    CORRECTION = "correction"


class StageCellRole(str, enum.Enum):
    """The part of a row a cell plays: `main` (the single answer), `leg1` and `leg2` (the two legs of an ensemble) and `judge`."""

    MAIN = "main"
    LEG1 = "leg1"
    LEG2 = "leg2"
    JUDGE = "judge"


class StageModelKit(str, enum.Enum):
    """The set the layout is based on: `claude_only`, `codex_only`, or `custom` (any edit of a set)."""

    CLAUDE_ONLY = "claude_only"
    CODEX_ONLY = "codex_only"
    CUSTOM = "custom"


class StageLayoutCell(_Object):
    """The settings of one cell (a row and a role): model and effort. The model and the effort must be a pair of `listModelCatalogue`.
    `LIMITS-01` (contract 1.49.0, `R-153n`, `R-153o`): a cell has no answer limit and no timeout -- no answer cap reaches a model, and a
    call's timeout is a constant of its row. A request that still names either member is refused (`validation_failed`), not ignored."""

    cell_key: StageCellKey
    row: StageRowKey
    role: StageCellRole
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    effort: ModelEffort


class StageLayoutRevision(_Object):
    """One immutable revision of the layout: the kit and every cell, with its author and time. `comparison_cells` are the cells of the four
    kinds of comparison work in force (`HOSTS-CMP-01`): what the revision stored, else the table of its kit. They are absent only for a
    `custom` revision that stored none: a comparison is then refused, never served by a model nobody chose."""

    layout_revision_id: StageLayoutRevisionId
    revision_no: Annotated[int, Field(ge=1)]
    kit: StageModelKit
    cells: Annotated[list[StageLayoutCell], Field(min_length=1, max_length=32)]
    created_at: datetime
    created_by: UserUid
    comparison_cells: Annotated[list[StageComparisonCell], Field(min_length=4, max_length=4)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class StageLayoutSwitchEvent(_Object):
    """One change of the switch «Модели по этапам: включены», with its author."""

    enabled: bool
    set_at: datetime
    set_by: UserUid


class StageModelLayout(_Object):
    """The layout of models over the analysis stages (ADR-0028). `enabled`: runs started now take the layout; off, they follow
    the route as before. `current` is the revision in force (absent before the first), `history` the revisions newest first and
    `switch_journal` the switch events newest first. `unavailable_cell_keys` are the cells of `current` whose model no server can
    serve now (shown as «нет на серверах»)."""

    enabled: bool
    current: StageLayoutRevision = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    history: Annotated[list[StageLayoutRevision], Field(max_length=50)]
    switch_journal: Annotated[list[StageLayoutSwitchEvent], Field(max_length=50)]
    unavailable_cell_keys: Annotated[list[StageCellKey], Field(max_length=32)]


class ReviseStageModelLayoutRequest(_Object):
    """A new revision: the kit and every cell. Only pairs of the catalogue are accepted; a row of the closed list of block schemes
    is chosen as a whole. `comparison_cells` (`HOSTS-CMP-01`, optional) are the four kinds of comparison work, each once; left out, a named
    kit follows its table and `custom` has none."""

    kit: StageModelKit
    cells: Annotated[list[StageLayoutCell], Field(min_length=1, max_length=32)]
    comparison_cells: Annotated[list[StageComparisonCell], Field(min_length=4, max_length=4)] = Field(**_NOT_GIVEN)  # type: ignore[assignment]


class SetStageModelLayoutEnabledRequest(_Object):
    """`true` puts the layout in force for runs started from now on (it needs a revision and the database provider source);
    `false` takes it out. Runs already started keep the plan they froze."""

    enabled: Annotated[bool, Field(strict=True)]


class ModelCatalogueEntry(_Object):
    """One model and one provider that may serve it: the accesses it can be served with, the efforts that may be asked for and the
    exact strings an answer may report (`contracts/analysis/v1/model-catalogue.json`)."""

    provider: ExecutorProvider
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    access: Annotated[list[ExecutorModelAccess], Field(min_length=1, max_length=2)]
    efforts: Annotated[list[ModelEffort], Field(min_length=1, max_length=3)]
    accepted_reported: Annotated[list[Annotated[str, Field(min_length=1, max_length=200)]], Field(min_length=1, max_length=4)]


class ModelCatalogue(_Object):
    """The models the layout may name. Only pins of the provider lock; Haiku, the efforts above `high` and `low` for Opus are
    never offered."""

    contract_version: Annotated[str, Field(pattern=r"^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}$")]
    items: Annotated[list[ModelCatalogueEntry], Field(max_length=64)]


class RunStartRoute(str, enum.Enum):
    """`stage_plan`: the run takes the layout. `legacy`: the layout is off and the run follows the automatic route as before."""

    STAGE_PLAN = "stage_plan"
    LEGACY = "legacy"


class RunStartReadinessCell(_Object):
    """One cell of the plan a start would freeze, with the access it would run with (absent when no server can serve it) and
    why it cannot be served, if it cannot."""

    cell_key: StageCellKey
    row: StageRowKey
    role: StageCellRole
    model_id: Annotated[str, Field(min_length=1, max_length=200)]
    effort: ModelEffort
    access: ExecutorModelAccess = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    available: bool
    reasons: Annotated[list[ModelUnavailableReason], Field(max_length=8)]


class RunStartReadiness(_Object):
    """What the one button «Запустить» says (ADR-0028): the route, the kit, every cell with its access, whether the start is
    possible and, when it is, the digest of the estimate to confirm. `access` is the total: all cells on a subscription (the
    estimate is 0 and the press of the button is the consent), all on an API key, or mixed (one dialog with the estimate by
    model). An unavailable cell makes `ready` false and names itself in `cells`."""

    route: RunStartRoute
    ready: bool
    kit: StageModelKit = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    access: Literal["subscription", "api", "mixed"] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    estimate_digest: Sha256 = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    stage_plan_digest: Sha256 = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    estimated_cost_micros: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    recommended_ceiling_micros: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    cells: Annotated[list[RunStartReadinessCell], Field(max_length=32)]


# --- the stages of a run: plan and fact (`HOSTS-SEAL-2`, ADR-0028, contract 1.46.0) ----------------------------------------
#
# One read, ``getRunStages``, answers the window «Этапы анализа раздела»: for each chip the run has, what it was planned to run
# on and what happened. It joins three places -- the PC-01 ``stage_result`` rows, the extended review's procedures and
# ``phase_coverage``, and the call journal (``model_call`` and ``provider_call_effect``) -- and invents nothing: a figure the
# journal does not hold is absent, not zero, and a chip no place mentions is not listed.


class RunStageChip(str, enum.Enum):
    """A chip of a run: a reader's name for the phase or phases of code that do one kind of work. The eight chips in the order the
    rail draws them -- `preparation` (the three PC-01 preparation stages), `text` (analysis of the text), `blocks` (analysis of the
    blocks), `cross_check` (the complex cross-check and the parameter passport), `merge` (the deterministic merge), `norms` (the
    norms), `review` (the critic) and `correction` (the refinement).
    A chip order is a display order, not the order of the stage graph."""

    PREPARATION = "preparation"
    TEXT = "text"
    BLOCKS = "blocks"
    CROSS_CHECK = "cross_check"
    MERGE = "merge"
    NORMS = "norms"
    REVIEW = "review"
    CORRECTION = "correction"


class RunStageState(str, enum.Enum):
    """How a chip stands. `pending`: not started. `running`: the work is under way (a stage or procedure running, or a call in flight).
    `done`: completed. `partial`: completed with a typed shortfall. `failed`: refused. `skipped`: not run by decision. `unavailable`:
    could not run (for example, the corpus is missing)."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


class RunStagePlanSource(str, enum.Enum):
    """Where the plan of the chips comes from. `stage_plan`: the plan the run froze at its start, one cell per row and role.
    `run_binding`: the run froze none (it started on the route as before), so each chip that calls a model has one line, «модель
    прогона», from the run's binding -- or from the journal when it has none."""

    STAGE_PLAN = "stage_plan"
    RUN_BINDING = "run_binding"


class RunStageCell(_Object):
    """One line of a chip's plan: the part it plays (`main`, `leg1`, `leg2`, `judge`), the model and the effort the run froze, and -- for an
    expert and an administrator -- the access and the server the cell is bound to. `LIMITS-01` (contract 1.49.0): no answer limit and no timeout. Of a run
    without a stage plan the line has `role` `main`, the model of the run's binding and nothing else it does not know.
    `access` and `server` are omitted for the viewer («Наблюдатель», `R-150w`); `server` is also absent while the cell is not bound."""

    cell_key: StageCellKey = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    role: StageCellRole
    model_id: Annotated[str, Field(min_length=1, max_length=200)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    effort: ModelEffort = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    access: ExecutorModelAccess = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    server: Annotated[str, Field(min_length=1, max_length=120)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class RunStageFacts(_Object):
    """What happened on a chip. `started_at` and `finished_at` are the earliest and the latest call of a chip that calls a model, or
    the times of its stage results (`finished_at` only once the chip has finished, and never from a stage taken from an earlier
    run). `calls_succeeded` and `calls_failed` count the calls the journal ended, `calls_retried` the calls that repeated an earlier
    call of the same request (a reply replayed from custody is not a call). `input_tokens`, `output_tokens` and `cost_micros` are
    the totals of the journal; `subscription_input_tokens` and `subscription_output_tokens` are the part of the tokens served by a
    subscription (not metered, never in `cost_micros`). `planned` and `completed` are the batches of the extended review's
    `phase_coverage` and are absent where the review keeps none. `last_error_code` is the code of the stage result that failed or,
    else, of the latest failed call; `reason` the extended review's reason a procedure did not complete."""

    state: RunStageState
    started_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    finished_at: datetime = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    calls_succeeded: Annotated[int, Field(ge=0)]
    calls_failed: Annotated[int, Field(ge=0)]
    calls_retried: Annotated[int, Field(ge=0)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    subscription_input_tokens: Annotated[int, Field(ge=0)]
    subscription_output_tokens: Annotated[int, Field(ge=0)]
    cost_micros: Annotated[int, Field(ge=0)]
    last_error_code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    reason: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    planned: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    completed: Annotated[int, Field(ge=0)] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    reused_from_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class RunStage(_Object):
    """One chip of the run: the code stage and procedure ids it covers, its plan (empty for a chip that calls no model) and its facts."""

    chip: RunStageChip
    stage_ids: Annotated[list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]], Field(min_length=1, max_length=8)]
    plan: Annotated[list[RunStageCell], Field(max_length=16)]
    facts: RunStageFacts


_RUN_STAGES_EXAMPLES: list[dict[str, Any]] = [
    {
        "run_id": "run_01M2545JSD15ETSNNV904X991K",
        "state": "running",
        "plan_source": "stage_plan",
        "items": [
            {
                "chip": "preparation",
                "stage_ids": ["source_preparation", "page_geometry_extraction", "document_context_build"],
                "plan": [],
                "facts": {
                    "state": "done", "started_at": "2026-11-10T09:00:03Z", "finished_at": "2026-11-10T09:01:12Z",
                    "calls_succeeded": 0, "calls_failed": 0, "calls_retried": 0, "input_tokens": 0, "output_tokens": 0,
                    "subscription_input_tokens": 0, "subscription_output_tokens": 0, "cost_micros": 0,
                },
            },
            {
                "chip": "text",
                "stage_ids": ["text_analysis"],
                "plan": [{
                    "cell_key": "text:main", "role": "main", "model_id": "claude-sonnet-5-5", "effort": "medium",
                    "access": "subscription", "server": "adm1.hlab.kz",
                }],
                "facts": {
                    "state": "done", "started_at": "2026-11-10T09:01:13Z", "finished_at": "2026-11-10T09:06:40Z",
                    "calls_succeeded": 5, "calls_failed": 1, "calls_retried": 1, "input_tokens": 61240, "output_tokens": 9310,
                    "subscription_input_tokens": 61240, "subscription_output_tokens": 9310, "cost_micros": 0,
                    "last_error_code": "dependency_unavailable",
                },
            },
            {
                "chip": "blocks",
                "stage_ids": ["block_analysis"],
                "plan": [{
                    "cell_key": "blocks:main", "role": "main", "model_id": "claude-opus-5-5", "effort": "medium",
                    "access": "subscription", "server": "adm1.hlab.kz",
                }],
                "facts": {
                    "state": "running", "started_at": "2026-11-10T09:06:41Z",
                    "calls_succeeded": 12, "calls_failed": 0, "calls_retried": 0, "input_tokens": 102400, "output_tokens": 18800,
                    "subscription_input_tokens": 102400, "subscription_output_tokens": 18800, "cost_micros": 0,
                    "planned": 40, "completed": 12,
                },
            },
        ],
    },
    {
        "run_id": "run_01M2545JSD15ETSNNV904X991K",
        "state": "published",
        "plan_source": "stage_plan",
        "items": [{
            "chip": "norms",
            "stage_ids": ["norm_verification"],
            "plan": [{
                "cell_key": "norms:main", "role": "main", "model_id": "claude-sonnet-5-5", "effort": "medium",
            }],
            "facts": {
                "state": "done", "started_at": "2026-11-10T09:30:00Z", "finished_at": "2026-11-10T09:41:10Z",
                "calls_succeeded": 8, "calls_failed": 0, "calls_retried": 0, "input_tokens": 48000, "output_tokens": 7200,
                "subscription_input_tokens": 0, "subscription_output_tokens": 0, "cost_micros": 412000,
                "planned": 8, "completed": 8,
            },
        }],
    },
    {
        "run_id": "run_01M2545JSD15ETSNNV904X991K",
        "state": "published",
        "plan_source": "run_binding",
        "items": [{
            "chip": "text",
            "stage_ids": ["text_analysis"],
            "plan": [{"role": "main", "model_id": "claude-sonnet-5", "access": "subscription", "server": "kzSonnet"}],
            "facts": {
                "state": "done", "started_at": "2026-11-09T11:00:00Z", "finished_at": "2026-11-09T11:03:30Z",
                "calls_succeeded": 3, "calls_failed": 0, "calls_retried": 0, "input_tokens": 30100, "output_tokens": 4200,
                "subscription_input_tokens": 30100, "subscription_output_tokens": 4200, "cost_micros": 0,
            },
        }],
    },
]


class RunStages(_Object):
    """The stages of a run, plan and fact (`HOSTS-SEAL-2`, ADR-0028): each chip the run has, in the order the rail draws them, with
    what it was planned to run on and what the journal and the stage results say happened. A chip that no stage result, procedure,
    plan cell or call mentions is not listed. `state` is the run's own, so a reader knows whether a chip that is `running` is still
    being worked on. `plan_source` says whether the plans are the run's frozen `stage_plan` or the one line of its binding. The
    examples are: a run in progress on the stage layout; a finished run's norms chip as the viewer reads it (no `access`, no
    `server`); and a run that started on the route as before."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": _RUN_STAGES_EXAMPLES})

    run_id: RunId
    state: RunState
    plan_source: RunStagePlanSource
    items: Annotated[list[RunStage], Field(max_length=9)]
