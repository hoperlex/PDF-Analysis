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
    "Account",
    "AccountPage",
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
    "ArV3RunGroupId",
    "StartArV3BetaGroupRequest",
    "ArV3BetaGroupMember",
    "ArV3BetaGroup",
    "ArV3BetaGroupReview",
    "ArV3BetaGroupReviewMember",
    "ArV3BetaPackReview",
    "ArV3BetaPackStatus",
    "ArV3BetaVisibleReview",
    "ArV3BetaVisibleTopic",
    "ArV3BetaVisibleProposal",
    "ArV3BetaVisibleCitation",
    "ArV3BetaVisibleEvidence",
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
    "UngroundedReason",
    "NormObservationCitationPartition",
    "NormFindingVerification",
    "NormVerificationReport",
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
    "ArV3BetaStageId",
    "StageId",
    "StageState",
    "StageStatus",
    "StartRunRequest",
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
    "AssignmentTransitionKind",
    "AssignmentUid",
    "CreateAssignmentRequest",
    "TransitionAssignmentRequest",
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
ArV3RunGroupId = TypeAliasType(
    "ArV3RunGroupId", Annotated[str, Field(pattern=rf"^arg_{_ULID}$")]
)
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


class ArV3BetaStageId(str, enum.Enum):
    CITATION_REVIEW = "ar_v3_citation_review"


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

    contract_version: Literal["1.9.0"]
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


class Project(_Object):
    project_uid: ProjectUid
    name: Annotated[str, Field(min_length=1, max_length=200)]
    created_at: datetime
    document_count: Annotated[int, Field(ge=0)] = Field(
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
    """How a version reached the product. ``comparison_pdf`` is a plain PDF admitted for
    comparison only (`Q-CMP-5`): no section analysis can start on it."""

    PORTAL_BUNDLE = "portal_bundle"
    COMPARISON_PDF = "comparison_pdf"


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
    page_count: Annotated[int, Field(ge=1, le=500)]
    published_at: datetime
    input_manifest: list[InputManifestEntry]
    #: `CMP-SEAL-C0`. How the version reached the product; see :class:`VersionUploadKind`.
    #: Always sent from `1.9.0`.
    upload_kind: VersionUploadKind = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


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


class StartRunRequest(_Object):
    version_uid: VersionUid
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


class StartArV3BetaGroupRequest(_Object):
    version_uid: VersionUid


class ArV3BetaGroupMember(_Object):
    scope_id: Literal["F1", "F2", "A1", "A2", "S1", "S2"]
    run_id: RunId
    state: RunState
    map_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    norm_retrieval_set_id: NormRetrievalSetId


class ArV3BetaGroup(_Object):
    group_id: ArV3RunGroupId
    project_uid: ProjectUid
    version_uid: VersionUid
    norms_snapshot_id: NormsSnapshotId
    analysis_profile_id: AnalysisProfileId
    prompt_bundle_id: PromptBundleId
    pack_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    provider_mode: ProviderMode
    members: Annotated[list[ArV3BetaGroupMember], Field(min_length=6, max_length=6)]


class ArV3BetaVisibleTopic(_Object):
    item_id: str
    mode: str
    reason: str
    source_ids: list[str]
    review_status: str
    provisional_citation_count: Annotated[int, Field(ge=0)]


class ArV3BetaVisibleEvidence(_Object):
    page_number: Annotated[int, Field(ge=1)]
    quote: str


class ArV3BetaVisibleCitation(_Object):
    item_id: str
    label: str
    document_id: str
    paragraph_id: str
    raw_quote: str
    state: str


class ArV3BetaVisibleProposal(_Object):
    proposal_ordinal: Annotated[int, Field(ge=0)]
    evidence: list[ArV3BetaVisibleEvidence]
    citations: list[ArV3BetaVisibleCitation]


class ArV3BetaVisibleReview(_Object):
    topics: list[ArV3BetaVisibleTopic]
    provisional_citations: list[ArV3BetaVisibleProposal]
    withheld_proposal_count: Annotated[int, Field(ge=0)]
    rejected_proposal_count: Annotated[int, Field(ge=0)]


class ArV3BetaGroupReviewMember(_Object):
    scope_id: Literal["F1", "F2", "A1", "A2", "S1", "S2"]
    run_id: RunId
    run_state: RunState
    review_state: Literal["pending", "failed", "verification_refused", "available"]
    terminal_reason: str | None
    refusal_code: str | None
    review: ArV3BetaVisibleReview | None


class ArV3BetaGroupReview(_Object):
    group_id: ArV3RunGroupId
    version_uid: VersionUid
    members: Annotated[list[ArV3BetaGroupReviewMember], Field(min_length=6, max_length=6)]


class ArV3BetaPackReview(_Object):
    """The human attestation that travelled with the installed pack's manifest.

    A record, not a check: the server shows what the manifest says and nothing about
    whether anyone really reviewed anything.
    """

    reviewer: str
    capacity: str
    reviewed_at: Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]
    decision_ref: str
    scope_statement: str


class ArV3BetaPackStatus(_Object):
    """Whether a reviewed AR v3 beta pack is installed on this server, and its attestation.

    Everything but `state` is absent, never null, while no pack is installed. No map, set or
    snapshot identity, digest of a scope, path or environment value is ever a property.
    """

    state: Literal["installed", "not_installed"]
    analysis_profile_id: AnalysisProfileId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    prompt_bundle_id: PromptBundleId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    pack_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    scope_ids: Annotated[
        list[Literal["F1", "F2", "A1", "A2", "S1", "S2"]],
        Field(min_length=6, max_length=6),
    ] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    review: ArV3BetaPackReview = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class StageState(_Object):
    stage_id: StageId | ArV3BetaStageId
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


class RunStatus(_Object):
    run_id: RunId
    reaudit_of_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
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
    degradation_set: list[StageId | ArV3BetaStageId] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
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


class RunStatusPage(_Object):
    items: list[RunStatus]
    page: PageInfo


class ExecutionQueueItem(_Object):
    job_id: JobId
    run_id: RunId
    state: str
    priority: int
    created_at: datetime
    available_at: datetime


class ExecutionQueuePage(_Object):
    items: list[ExecutionQueueItem]
    page: PageInfo
    paused: bool


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


class UngroundedReason(str, enum.Enum):
    QUOTATION_ABSENT = "quotation_absent"
    QUOTATION_ON_DIFFERENT_PAGE = "quotation_on_different_page"
    SPAN_OUTSIDE_PAGE = "span_outside_page"
    SPAN_OUTSIDE_BLOCK = "span_outside_block"
    SPAN_LENGTH_MISMATCH = "span_length_mismatch"
    QUOTE_IN_RECOGNISED_TEXT = "quote_in_recognised_text"
    NORM_LABEL_UNKNOWN = "norm_label_unknown"
    NORM_QUOTE_TOO_SHORT = "norm_quote_too_short"
    NORM_QUOTE_AMBIGUOUS = "norm_quote_ambiguous"
    NORM_QUOTE_ABSENT = "norm_quote_absent"
    NORM_VALUE_NOT_IN_QUOTE = "norm_value_not_in_quote"
    STATED_VALUE_NOT_IN_EVIDENCE = "stated_value_not_in_evidence"


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
    current_verdict: Verdict
    latest_decision_id: DecisionId | None = Field(default=None, json_schema_extra=optional_property)
    decision_recorded_at: datetime | None = Field(default=None, json_schema_extra=optional_property)


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
    current_verdict: Verdict
    latest_decision_id: DecisionId | None = Field(default=None, json_schema_extra=optional_property)
    decision_recorded_at: datetime | None = Field(default=None, json_schema_extra=optional_property)
    latest_comment: str | None = Field(default=None, json_schema_extra=optional_property)
    decision_event_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class NormObservationCitationPartition(_Object):
    finding_observation_id: FindingObservationId
    norm_citations: Annotated[list[NormCitation], Field(max_length=5)]
    required_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    stated_value: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class NormFindingVerification(_Object):
    finding_uid: FindingUid
    canonical: NormObservationCitationPartition
    merged_observations: list[NormObservationCitationPartition]


class NormVerificationReport(_Object):
    run_id: RunId
    norms_snapshot_id: NormsSnapshotId
    norm_retrieval_set_id: NormRetrievalSetId
    status: Literal["complete", "partial"]
    findings: list[NormFindingVerification]
    withheld_by_reason: Annotated[
        dict[UngroundedReason, Annotated[int, Field(ge=0)]],
        WithJsonSchema({
            "type": "object",
            "propertyNames": {"$ref": "#/components/schemas/UngroundedReason"},
            "additionalProperties": {"type": "integer", "minimum": 0},
        }),
    ]
    textless_pages: list[Annotated[int, Field(ge=1)]]
    error_code: ErrorCode = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


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

    page_number: Annotated[int, Field(ge=1, le=500)]
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
    page_count: Annotated[int, Field(ge=1, le=500)]
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
    unread_pages: Annotated[list[Annotated[int, Field(ge=1, le=500)]], Field(max_length=500)] = Field(
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
    category: FindingCategory
    finding_text: Annotated[str, Field(min_length=1, max_length=4000)]
    current_verdict: Verdict
    decision_event_count: Annotated[int, Field(ge=0)]


class DecisionRecordPage(_Object):
    items: list[DecisionRecord]
    page: PageInfo


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
    """How many findings, across every project, currently stand at one verdict.

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
    """

    document_count: Annotated[int, Field(ge=0)]
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class DashboardSummary(_Object):
    """``getDashboardSummary``'s whole answer. All four panels, one read, no filter."""

    documents_by_project: list[ProjectDocumentCount]
    findings_by_verdict: list[VerdictCount]
    run_activity: RunActivity
    section_breakdown: list[SectionDocumentCount]


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


class AccountPage(_Object):
    items: list[Account]
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


class AssignmentPage(_Object):
    items: list[Assignment]
    page: PageInfo


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

_PageNumber = Annotated[int, Field(ge=1, le=500)]
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
_SpecificationPage = Annotated[int, Field(ge=1, le=500)]
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

    algorithm: Literal["price-match-v1"]
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
    and the proposal needs changing; its comment is required."""

    ACCEPT = "accept"
    REJECT = "reject"
    REVISE = "revise"


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
    or the project's own, ``vendor_list_source``), and the three algorithm versions."""

    optimisation_pass_id: OptimisationPassId
    project_uid: ProjectUid
    document_uid: DocumentUid
    version_uid: VersionUid
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
    """One appended expert decision. Never changed; the proposal's latest one is current."""

    proposal_decision_id: ProposalDecisionId
    optimisation_proposal_id: OptimisationProposalId
    verdict: ProposalVerdict
    comment: Annotated[str, Field(min_length=1, max_length=2000)] | None
    actor_user_uid: UserUid
    actor_label: Annotated[str, Field(min_length=1, max_length=254)]
    decided_at: datetime


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


class ProposalDecisionResult(_Object):
    """The decision appended (or replayed) and the proposal as it now stands."""

    decision: ProposalDecision
    proposal: OptimisationProposal


class ProposalDecisionList(_Object):
    """Every decision of one proposal, oldest first; the last is current."""

    items: list[ProposalDecision]
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
    match_algorithm: Literal["price-match-v1"]
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
    """The kind of model work a route serves. Today exactly one stage calls a model."""

    TEXT_ANALYSIS = "text_analysis"


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


class ReviseExecutorConnectionRequest(ExecutorRevisionSettings):
    """A new immutable revision of a connection: the full settings, never a patch."""


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
    """One immutable revision of a connection, with its latest probe."""

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


class ExecutorConnection(_Object):
    """A connection: where a process sends model work. Its secrets are metadata only."""

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


class ExecutorConnectionList(_Object):
    items: list[ExecutorConnection]
    pinned_models: list[ExecutorPinnedModel]


class ExecutorConnectionDetail(_Object):
    """One connection with every revision (each with its latest probe) and its last 10 probes.

    For a ``pull`` connection (`EXEC-PULL-01`) it also carries the runner tokens' metadata and
    the number of tasks waiting for, or held by, a runner right now. Both are absent for the
    other kinds. A token's value is never here: it was shown once, when it was issued."""

    connection: ExecutorConnection
    revisions: list[ExecutorRevision]
    probes: Annotated[list[ExecutorProbe], Field(max_length=10)]
    runner_tokens: Annotated[list["RunnerTokenMetadata"], Field(max_length=50)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    open_task_count: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
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


class RunnerTokenMetadata(_Object):
    """What the API ever says about a runner token after it was issued: that it exists, its
    non-secret prefix, when it expires or was revoked, and when and from where it was last seen.
    The value and its hash are never returned."""

    token_id: ExecutorRunnerTokenId
    connection_id: ExecutorConnectionId
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
    runner_token: RunnerTokenMetadata


class ClaimExecutorTaskRequest(_Object):
    """The long poll holds the request open for up to ``wait_seconds`` (0 to 25, default 25)."""

    wait_seconds: Annotated[int, Field(ge=0, le=25)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    #: `CMP-SEAL-C0` (ADR-0025 decision 18). The most images one task may carry that this runner
    #: serves; absent means 1, the shape every deployed runner sends today. The server never hands
    #: out a task with more images than declared.
    max_images: Annotated[int, Field(ge=1, le=8)] = Field(  # type: ignore[assignment]
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


class ExtendedExecutorTaskClaim(_Object):
    claim_expires_at: datetime


class SubmitExecutorTaskAnswerRequest(_Object):
    """``output_text`` is the bare JSON document (no code fence, no commentary) the task's
    ``output_schema`` describes. ``model`` is the model that produced it, as the runner declares
    it: an assertion the stand records as such, and holds equal to the connection's pinned model.
    The token counts are the runner's own; the call is recorded as unmetered."""

    output_text: Annotated[str, Field(min_length=1, max_length=1000000)]
    model: Annotated[str, Field(min_length=1, max_length=200)]
    input_tokens: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )
    output_tokens: Annotated[int, Field(ge=0)] = Field(  # type: ignore[assignment]
        default=None, json_schema_extra=optional_property
    )


class FailExecutorTaskRequest(_Object):
    """A lower-case code, optionally followed by ``: `` and a short, payload-free detail."""

    reason: Annotated[str, Field(min_length=1, max_length=512)]


class ExecutorTaskAck(_Object):
    task_id: ExecutorTaskId
    state: ExecutorTaskState


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
    REVIEW = "review"
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
    page_count: Annotated[int, Field(ge=1, le=500)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class CreateComparisonUploadRequest(_Object):
    """The declared files of one upload batch. The limits of ADR-0025 decision 9 (files, sets,
    declared bytes and pages, the project's stored bytes, active batches) are refused here,
    before the first part, as typed reasons under existing error codes."""

    files: Annotated[list[ComparisonUploadFileDeclaration], Field(min_length=1)]


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
    page_number: Annotated[int, Field(ge=1, le=500)]
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
