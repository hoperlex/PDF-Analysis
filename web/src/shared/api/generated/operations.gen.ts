/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * One typed input and result per operation, plus the runtime descriptor table the
 * transport executes.
 *
 * Produced by `npm --prefix web run api:generate`
 * (web/scripts/generate-api-client.mjs, generator 1.0.0)
 * from contracts/api/v1/openapi.json
 *   AuditManager PC-01 API 1.53.0 (OpenAPI 3.1.0)
 *   sha256 6c1189b17ef9162e5222ac57a379e906d34b9c7919d4b0b32c745d242a261924
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

import type {
  AcceptedOptimisationProposalPage,
  Account,
  AccountPage,
  AgentPackageVersion,
  AnalysisPreset,
  AnalysisPresetList,
  AnalysisProfileList,
  AppendComparisonVersionOrderRequest,
  AppendDecisionRequest,
  AppendDecisionResponse,
  AppendPrecedentSettingRequest,
  ApplyComparisonMatrixEditsRequest,
  ApplyStageCardVerdictsRequest,
  ApplyStageSheetMapRequest,
  ApproveRegistrationRequest,
  ApproveSheetPairingRequest,
  Assignment,
  AssignmentDetail,
  AssignmentPage,
  AssignmentStatus,
  AssignmentUid,
  AuthEventPage,
  CarryOverDecisionRequest,
  CarryOverDecisionResponse,
  CarryOverProposalDecisionsRequest,
  ChangePasswordRequest,
  ClaimExecutorTaskRequest,
  ClaimedExecutorTask,
  ClassifyDocumentVersionRequest,
  ComparisonAiEstimate,
  ComparisonAiJob,
  ComparisonAiJobId,
  ComparisonAiLinkList,
  ComparisonAiPairCheck,
  ComparisonAiPairHintPage,
  ComparisonAiQueue,
  ComparisonAiSheetChanges,
  ComparisonLaunchEntryId,
  ComparisonLaunchQueue,
  ComparisonMatrix,
  ComparisonMatrixEditList,
  ComparisonMatrixPreparation,
  ComparisonOverview,
  ComparisonPageProfileId,
  ComparisonPairTileMode,
  ComparisonProposalSet,
  ComparisonQueueSummary,
  ComparisonReport,
  ComparisonReportId,
  ComparisonReportKind,
  ComparisonReportPage,
  ComparisonReviewSheetPage,
  ComparisonSeries,
  ComparisonSeriesId,
  ComparisonSeriesPage,
  ComparisonSheetDescription,
  ComparisonSheetDescriptionHistory,
  ComparisonSheetPair,
  ComparisonSheetPairId,
  ComparisonSheetPairPage,
  ComparisonSheetPairSpecPositions,
  ComparisonSheetStatus,
  ComparisonSpecChangeKind,
  ComparisonSpecChangePage,
  ComparisonSpecPage,
  ComparisonSpecification,
  ComparisonSpecificationPage,
  ComparisonTransitionId,
  ComparisonUpload,
  ComparisonUploadFile,
  ComparisonUploadFileId,
  ComparisonUploadId,
  ComparisonUploadPage,
  ComparisonUploadPartReceipt,
  ComparisonUploadProposal,
  ComparisonUploadSetId,
  ComparisonVersionOrder,
  ComparisonVersionOrderList,
  ConfirmComparisonUploadSetRequest,
  ConfirmExecutorAgentInstallHostKeyRequest,
  ConfirmStagePairRequest,
  ConfirmStageUploadCandidateRequest,
  CorrectVersionClassificationRequest,
  CorrelationId,
  CreateAssignmentRequest,
  CreateComparisonReportRequest,
  CreateComparisonUploadRequest,
  CreateExecutorAgentInstallRequest,
  CreateExecutorConnectionRequest,
  CreateExecutorGroupRequest,
  CreateExecutorHostAgentInstallRequest,
  CreateProjectRequest,
  CreateStageAssemblyRequest,
  CreateStageReviewCardRequest,
  CreateStageUploadRequest,
  Cursor,
  DashboardSummary,
  DecideOptimisationProposalRequest,
  DecisionEventPage,
  DecisionImportReport,
  DecisionMemoryCase,
  DecisionMemoryCaseId,
  DecisionMemoryCasePage,
  DecisionMemoryStatus,
  DecisionMemoryStatusChange,
  DecisionMemoryStatusChangeRequest,
  DecisionPattern,
  DecisionPatternId,
  DecisionPatternList,
  DecisionRecordPage,
  DocumentTagList,
  DocumentUid,
  DocumentVersion,
  DocumentVersionPage,
  EffectiveVendorLists,
  EnqueueComparisonLaunchRequest,
  ExecutionDispatchStatus,
  ExecutionJournalPage,
  ExecutionQueueItem,
  ExecutionQueuePage,
  ExecutionWorker,
  ExecutionWorkerPage,
  ExecutorAgentInstall,
  ExecutorAgentInstallId,
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorConnectionId,
  ExecutorConnectionList,
  ExecutorGroup,
  ExecutorGroupCapacity,
  ExecutorGroupDetail,
  ExecutorGroupId,
  ExecutorGroupList,
  ExecutorHost,
  ExecutorHostDetails,
  ExecutorHostId,
  ExecutorHostList,
  ExecutorProbe,
  ExecutorRevision,
  ExecutorRoute,
  ExecutorRouteList,
  ExecutorRoutingModeResult,
  ExecutorRoutingPreview,
  ExecutorRoutingRule,
  ExecutorRoutingRuleList,
  ExecutorRunnerTokenId,
  ExecutorSecretMetadata,
  ExecutorSshKey,
  ExecutorTaskAck,
  ExecutorTaskContext,
  ExecutorTaskContextRequest,
  ExecutorTaskId,
  ExecutorWorkKind,
  ExtendedExecutorTaskClaim,
  ExtendedRunReview,
  FailExecutorTaskRequest,
  FindingCategory,
  FindingDetail,
  FindingExecutionState,
  FindingPage,
  FindingPrecedents,
  FindingUid,
  GenerateComparisonSummaryRequest,
  GenerateComparisonSummaryResponse,
  IdempotencyKey,
  ImportProposalDecisionsRequest,
  ImportRunDecisionsRequest,
  IssueExecutorHostEnrollmentRequest,
  IssueRunnerTokenRequest,
  IssueTokenRequest,
  IssueTokenResponse,
  IssuedExecutorEnrollment,
  IssuedRunnerToken,
  JobId,
  KnowledgeBaseEntryPage,
  MarkReleaseNotesReadRequest,
  ModelCatalogue,
  NormCatalogueEntryPage,
  NormCurrentSnapshot,
  NormDocument,
  NormDocumentId,
  NormParagraphPage,
  NormSearchPage,
  NormSnapshotEventPage,
  NormSnapshotPage,
  NormsSnapshotId,
  OptimisationPass,
  OptimisationPassId,
  OptimisationPassList,
  OptimisationProposalId,
  OptimisationProposalPage,
  PortalBlockId,
  PortalBlockPage,
  PrecedentSetting,
  PrecedentSettingList,
  PrepareComparisonClientReportRequest,
  PresetId,
  PriceListId,
  PriceListPositionPage,
  PriceListRevision,
  PriceListRevisionList,
  ProductVersion,
  Project,
  ProjectPage,
  ProjectSection,
  ProjectUid,
  ProposalDecisionCarryoverReport,
  ProposalDecisionImportReport,
  ProposalDecisionList,
  ProposalDecisionRecordPage,
  ProposalDecisionResult,
  ProposalDecisionState,
  ReauditRunRequest,
  RedeemExecutorEnrollmentRequest,
  RegistrationRequest,
  RegistrationRequestId,
  RegistrationRequestPage,
  RegistrationStatus,
  RegistrationStatusResponse,
  RejectRegistrationRequest,
  ReleaseList,
  RenameDocumentRequest,
  ReportRunnerHealthRequest,
  ResetUserPasswordRequest,
  ResumeComparisonAiJobRequest,
  ResumeStageChainRunRequest,
  ReviewDecisionPatternRequest,
  ReviseExecutorConnectionRequest,
  ReviseExecutorGroupRequest,
  ReviseStageAssemblyRequest,
  ReviseStageModelLayoutRequest,
  RunCostEstimate,
  RunCostEstimateRequest,
  RunFindingBlockLinks,
  RunId,
  RunNormReferences,
  RunPrecedents,
  RunStages,
  RunStartReadiness,
  RunStatus,
  RunStatusPage,
  RunnerHealthAck,
  RunnerImageBlobId,
  RunnerTokenMetadata,
  SaveAnalysisPresetRequest,
  ScheduleAssignmentsRequest,
  SectionReview,
  SectionSpecification,
  SectionVendorList,
  SetCurrentNormSnapshotRequest,
  SetDocumentArchivedRequest,
  SetDocumentTagsRequest,
  SetEngineerAbsencesRequest,
  SetExecutionPausedRequest,
  SetExecutorHostEnabledRequest,
  SetExecutorHostSlotsRequest,
  SetExecutorIntegrationAuthorisationRequest,
  SetExecutorRouteRequest,
  SetExecutorRoutingModeRequest,
  SetExecutorRoutingRuleRequest,
  SetExecutorSecretRequest,
  SetFindingExecutionStatusRequest,
  SetGlobalVendorListRequest,
  SetJobPriorityRequest,
  SetProjectVendorListRequest,
  SetStageModelLayoutEnabledRequest,
  SetStagePairCompletenessRequest,
  SetVectorPausedRequest,
  SetWorkCalendarDaysRequest,
  SetWorkSchedulePlansRequest,
  SetWorkerIntakeRequest,
  SheetLinkId,
  SheetPairingEvent,
  SpecificationPrices,
  StageAiClassificationPage,
  StageAiReviewPage,
  StageAiSynthesisPage,
  StageAssembly,
  StageAssemblyId,
  StageCardVerdictPage,
  StageChainBatch,
  StageChainBatchId,
  StageChainRun,
  StageChainRunId,
  StageChainRunPage,
  StageChangeCard,
  StageChangeCardId,
  StageChangeCardPage,
  StageChangeJournal,
  StageGraphicEvidencePage,
  StageLinkRepair,
  StageLinkRepairId,
  StageLinkRepairPage,
  StageLinkRevision,
  StageLinkRevisionId,
  StageLinkRevisionPage,
  StageModelLayout,
  StagePair,
  StagePairId,
  StagePairPage,
  StagePairSuggestionPage,
  StageProfileText,
  StageQualityTable,
  StageSheetPassportPage,
  StageSheetSuggestionPage,
  StageTextDifferencePage,
  StageTextExclusionPage,
  StageTextFragmentPage,
  StageTextHintPage,
  StageUpload,
  StageUploadCandidate,
  StageUploadCandidateId,
  StageUploadFile,
  StageUploadFileId,
  StageUploadId,
  StageUploadPage,
  StageUploadPartReceipt,
  StartComparisonAiJobRequest,
  StartComparisonAiSheetChangesRequest,
  StartComparisonSeriesRequest,
  StartRunFromStageRequest,
  StartRunRequest,
  StartStageChainBatchRequest,
  StartStageChainRunRequest,
  SubmitExecutorTaskAnswerRequest,
  SubmitRegistrationRequest,
  TransitionAssignmentRequest,
  UndoComparisonMatrixEditRequest,
  UndoStageLinkRepairRequest,
  UpdateMyProfileRequest,
  UpdateUserRequest,
  UploadDocumentRequest,
  UploadDocumentVersionRequest,
  UploadPriceListRequest,
  UserUid,
  VectorControl,
  VendorListRevision,
  Verdict,
  VersionBlockIndex,
  VersionClassification,
  VersionComparison,
  VersionPageProfile,
  VersionPageProfilePage,
  VersionSheetLabelList,
  VersionUid,
  WithdrawSheetPairingRequest,
  WorkScheduleMonth,
  WorkScheduleReserve,
  WorkScheduleSettings,
  WorkerId,
} from './types.gen';

/** Every operationId in the contract, sorted. */
export const OPERATION_IDS = [
  'appendComparisonVersionOrder',
  'appendDecision',
  'appendPrecedentSetting',
  'applyComparisonMatrixEdits',
  'applyStageCardVerdicts',
  'applyStageSheetMap',
  'approveRegistration',
  'approveSheetPairing',
  'archiveAnalysisPreset',
  'archiveExecutorConnection',
  'archiveExecutorGroup',
  'archiveExecutorHost',
  'archiveUser',
  'cancelComparisonAiPairCheck',
  'cancelComparisonAiSheetChanges',
  'cancelComparisonReport',
  'cancelComparisonSeries',
  'cancelComparisonSpecification',
  'cancelComparisonUpload',
  'cancelRun',
  'cancelStageChainBatch',
  'cancelStageChainRun',
  'cancelStageUpload',
  'carryOverDecision',
  'carryOverProposalDecisions',
  'changePassword',
  'claimExecutorTask',
  'classifyDocumentVersion',
  'clearComparisonLaunchQueue',
  'compareDocumentVersions',
  'completeComparisonUploadFile',
  'completeStageUploadFile',
  'confirmComparisonUploadSet',
  'confirmExecutorAgentInstallHostKey',
  'confirmExecutorHostAgentInstallHostKey',
  'confirmStagePair',
  'confirmStageUploadCandidate',
  'continueComparisonReport',
  'correctVersionClassification',
  'createAnalysisPreset',
  'createAssignment',
  'createComparisonReport',
  'createComparisonUpload',
  'createExecutorAgentInstall',
  'createExecutorConnection',
  'createExecutorGroup',
  'createExecutorHostAgentInstall',
  'createProject',
  'createStageAssembly',
  'createStageReviewCard',
  'createStageUpload',
  'decideOptimisationProposal',
  'deleteComparisonReport',
  'dequeueComparisonAiSheetChanges',
  'downloadAgentPackage',
  'endUserSessions',
  'enqueueComparisonLaunch',
  'estimateComparisonAiPairCheck',
  'estimateComparisonAiSheetChanges',
  'estimateComparisonSheetDescription',
  'estimateComparisonSpecification',
  'estimateRunCost',
  'estimateStageChainRun',
  'excludeComparisonUploadSet',
  'exportOptimisationProposalsCsv',
  'exportOptimisationProposalsXlsx',
  'exportRunCsv',
  'exportRunXlsx',
  'extendExecutorTaskClaim',
  'failExecutorTask',
  'finishComparisonAiSheetChanges',
  'finishComparisonSeries',
  'generateComparisonSummary',
  'generateExecutorSshKey',
  'getAssignment',
  'getComparisonAiPairCheck',
  'getComparisonAiQueue',
  'getComparisonAiSheetChanges',
  'getComparisonLaunchQueue',
  'getComparisonMatrix',
  'getComparisonOverview',
  'getComparisonQueueSummary',
  'getComparisonReport',
  'getComparisonSeries',
  'getComparisonSheetDescription',
  'getComparisonSheetPair',
  'getComparisonSheetPairSpecPositions',
  'getComparisonSpecification',
  'getComparisonUpload',
  'getComparisonUploadProposal',
  'getDashboardSummary',
  'getDecisionMemoryCase',
  'getDecisionMemoryStatus',
  'getDocumentVersion',
  'getEffectiveVendorLists',
  'getExecutionDispatch',
  'getExecutorAgentInstall',
  'getExecutorConnection',
  'getExecutorGroup',
  'getExecutorGroupCapacity',
  'getExecutorHost',
  'getExecutorHostAgentInstall',
  'getExecutorHostDetails',
  'getExecutorTaskContext',
  'getExecutorTaskImage',
  'getExtendedRunReview',
  'getFinding',
  'getFindingPrecedents',
  'getMe',
  'getNormDocument',
  'getProductVersion',
  'getProject',
  'getRunNormReferences',
  'getRunPrecedents',
  'getRunStages',
  'getRunStartReadiness',
  'getRunStatus',
  'getSectionSpecification',
  'getSpecificationPrices',
  'getStageAssembly',
  'getStageChainBatch',
  'getStageChainRun',
  'getStageChangeCard',
  'getStageChangeJournal',
  'getStageModelLayout',
  'getStagePair',
  'getStageProfileText',
  'getStageQuality',
  'getStageSheetMap',
  'getStageSheetMapRevision',
  'getStageSynthesis',
  'getStageUpload',
  'getUser',
  'getVectorControl',
  'getVersionBlocks',
  'getVersionPageProfile',
  'getVersionPageSpecPositions',
  'getVersionSectionReview',
  'getWorkSchedule',
  'getWorkScheduleReserve',
  'importComparisonZip',
  'importOptimisationProposalDecisions',
  'importRunDecisions',
  'issueExecutorEnrollment',
  'issueExecutorHostEnrollment',
  'issueRunnerToken',
  'issueToken',
  'listAcceptedOptimisationProposals',
  'listAnalysisPresets',
  'listAnalysisProfiles',
  'listAssignments',
  'listAuthEvents',
  'listComparisonAiLinks',
  'listComparisonAiPairHints',
  'listComparisonMatrixEdits',
  'listComparisonReports',
  'listComparisonReviewSheets',
  'listComparisonSeries',
  'listComparisonSheetDescriptionHistory',
  'listComparisonSheetPairs',
  'listComparisonSpecificationChanges',
  'listComparisonSpecifications',
  'listComparisonUploads',
  'listComparisonVersionOrders',
  'listDecisionHistory',
  'listDecisionMemoryCases',
  'listDecisionPatterns',
  'listDecisions',
  'listDocumentTags',
  'listDocuments',
  'listExecutionJournal',
  'listExecutionQueue',
  'listExecutorConnections',
  'listExecutorGroups',
  'listExecutorHosts',
  'listExecutorRoutes',
  'listExecutorRoutingRules',
  'listKnowledgeBaseEntries',
  'listModelCatalogue',
  'listNormDocuments',
  'listNormParagraphs',
  'listNormSnapshotEvents',
  'listNormSnapshots',
  'listOptimisationPasses',
  'listOptimisationProposals',
  'listPrecedentSettings',
  'listPriceListPositions',
  'listPriceListRevisions',
  'listProjects',
  'listProposalDecisionJournal',
  'listProposalDecisions',
  'listRegistrations',
  'listReleases',
  'listRunFindingBlocks',
  'listRunFindings',
  'listRuns',
  'listStageAiReviews',
  'listStageCardVerdicts',
  'listStageChainRuns',
  'listStageChangeCards',
  'listStageClassifications',
  'listStageGraphicEvidence',
  'listStageLinkRepairs',
  'listStagePairSuggestions',
  'listStagePairs',
  'listStageRawDifferences',
  'listStageSheetMapHistory',
  'listStageSheetPassports',
  'listStageSheetSuggestions',
  'listStageTextExclusions',
  'listStageTextFragments',
  'listStageTextHints',
  'listStageUploads',
  'listUsers',
  'listVersionPageProfiles',
  'listVersionPortalBlocks',
  'listVersionSheetLabels',
  'listVersions',
  'listWorkers',
  'markReleaseNotesRead',
  'pauseComparisonAiPairCheck',
  'pauseComparisonAiSheetChanges',
  'pauseComparisonLaunchQueue',
  'pauseComparisonSeries',
  'pauseComparisonUpload',
  'pauseStageChainBatch',
  'pauseStageUpload',
  'prepareComparisonClientReport',
  'prepareComparisonMatrix',
  'previewExecutorRouting',
  'purgeUser',
  'readRegistrationStatus',
  'reauditRun',
  'rebuildComparisonReportPdf',
  'recomputeStageTextEvidence',
  'redeemExecutorEnrollment',
  'rejectRegistration',
  'rejectStageUploadCandidate',
  'removeComparisonLaunchEntry',
  'renameDocument',
  'reportRunnerHealth',
  'requestExecutorProbe',
  'resetUserPassword',
  'restoreDecisionMemoryCase',
  'restoreUser',
  'resumeComparisonAiPairCheck',
  'resumeComparisonAiSheetChanges',
  'resumeComparisonLaunchQueue',
  'resumeComparisonSeries',
  'resumeComparisonUpload',
  'resumeStageChainBatch',
  'resumeStageChainRun',
  'resumeStageUpload',
  'retryComparisonAiSheetChanges',
  'retryComparisonUploadSet',
  'reviewDecisionPattern',
  'reviseAnalysisPreset',
  'reviseExecutorConnection',
  'reviseExecutorGroup',
  'reviseStageAssembly',
  'reviseStageModelLayout',
  'revokeRunnerToken',
  'scheduleAssignments',
  'searchNorms',
  'setCurrentNormSnapshot',
  'setDocumentArchived',
  'setDocumentTags',
  'setEngineerAbsences',
  'setExecutionPaused',
  'setExecutorHostEnabled',
  'setExecutorHostSlots',
  'setExecutorIntegrationAuthorisation',
  'setExecutorRoute',
  'setExecutorRoutingMode',
  'setExecutorRoutingRule',
  'setExecutorSecret',
  'setFindingExecutionStatus',
  'setGlobalVendorList',
  'setJobPriority',
  'setProjectVendorList',
  'setStageModelLayoutEnabled',
  'setStagePairCompleteness',
  'setVectorPaused',
  'setWorkCalendarDays',
  'setWorkSchedulePlans',
  'setWorkScheduleSettings',
  'setWorkerIntake',
  'startComparisonAiPairCheck',
  'startComparisonAiSheetChanges',
  'startComparisonReport',
  'startComparisonSeries',
  'startComparisonSheetDescription',
  'startComparisonSpecification',
  'startOptimisationPass',
  'startRun',
  'startRunFromStage',
  'startStageChainBatch',
  'startStageChainRun',
  'streamComparisonPairTile',
  'streamComparisonReportPdf',
  'streamComparisonReportSourceMd',
  'streamComparisonSeriesSummary',
  'streamComparisonSheetDescriptionMd',
  'streamComparisonTechnicalReport',
  'streamDocumentVersionContent',
  'streamNormDocumentContent',
  'streamStageChangeJournalHtml',
  'streamStageChangeJournalPdf',
  'streamStageChangeJournalXlsx',
  'streamVersionPagePreview',
  'streamVersionPageThumbnail',
  'streamVersionPageTile',
  'streamVersionPortalBlockCrop',
  'submitExecutorTaskAnswer',
  'submitRegistration',
  'transitionAssignment',
  'undoComparisonMatrixEdit',
  'undoStageLinkRepair',
  'updateMyProfile',
  'updateUser',
  'uploadComparisonReportSource',
  'uploadComparisonUploadPart',
  'uploadDocument',
  'uploadDocumentVersion',
  'uploadPriceList',
  'uploadStageUploadPart',
  'withdrawDecisionMemoryCase',
  'withdrawSheetPairing',
] as const;

/** The closed set of operations this client can perform. */
export type OperationId = (typeof OPERATION_IDS)[number];

// ------------------------------------------------------------------------------------
// appendComparisonVersionOrder - POST /projects/{project_uid}/documents/{document_uid}/comparison-version-orders
// ------------------------------------------------------------------------------------

/**
 * Append a revision of the comparison order of a document set.
 *
 * Appends a revision listing the versions of the document, each once. `base_revision_no` is the latest revision the caller saw (`0` for none); a stale one is `409 conflict` (`comparison_version_order_stale`) and the caller rebases (`ADR-0025` decision 14). History is append-only. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_version_orders`) and nothing is read or written.
 */
export type AppendComparisonVersionOrderInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-version-orders`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: AppendComparisonVersionOrderRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `appendComparisonVersionOrder` (`application/json`, HTTP 201). */
export type AppendComparisonVersionOrderResult = ComparisonVersionOrder;

// ------------------------------------------------------------------------------------
// appendDecision - POST /findings/{finding_uid}/decisions
// ------------------------------------------------------------------------------------

/**
 * Append one expert decision event.
 *
 * Append-only. Nothing is updated: an accept after a reject is a third event, and the current verdict is a projection over the stream. Replaying under one idempotency key appends exactly one event, which the database enforces rather than the handler promising it.
 *
 * PC-01 emits `accept`, `reject` and `comment`. `revoke` is declared so the PD-01 revocation semantics stay implementable without a schema change; no PC-01 client offers it.
 */
export type AppendDecisionInput = {
  /** Path parameters, substituted into `/findings/{finding_uid}/decisions`. */
  path: {
    finding_uid: FindingUid;
  };
  /** Request body, sent as `application/json`. */
  body: AppendDecisionRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `appendDecision` (`application/json`, HTTP 201). */
export type AppendDecisionResult = AppendDecisionResponse;

// ------------------------------------------------------------------------------------
// appendPrecedentSetting - POST /precedent-settings
// ------------------------------------------------------------------------------------

/**
 * Append Precedent Setting
 *
 * `CRIT-SEAL-50` (plan-v5 sections 3.1 and 3.6): a new revision of a setting, journalled with the administrator who made it. `422 validation_failed` for a value that is not the shape of its setting. A switch changes the behaviour of runs started after it; a run's publication mode is frozen at its start. `role:admin`, `Idempotency-Key` required.
 */
export type AppendPrecedentSettingInput = {
  /** Request body, sent as `application/json`. */
  body: AppendPrecedentSettingRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `appendPrecedentSetting` (`application/json`, HTTP 201). */
export type AppendPrecedentSettingResult = PrecedentSetting;

// ------------------------------------------------------------------------------------
// applyComparisonMatrixEdits - POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits
// ------------------------------------------------------------------------------------

/**
 * Apply a drafted batch of manual matrix edits.
 *
 * «Применить сопоставления (N)»: applies the batch an expert drafted (`link`, `unlink` and `mark_absent`, at most 500) together or not at all. `base_revision` is the revision of the matrix the caller saw (the build and the number of edit events); when either is no longer current the answer is `409 conflict` (`comparison_matrix_stale`), nothing is applied and the client rebases its draft (`ADR-0025` decision 14). A batch that names a page outside its version, joins a version to itself or carries a member its kind does not take is `422 validation_failed`. An edit binds the version-order revision in force; a later reorder marks the edits whose cells no longer exist as orphaned and never applies them silently. History is append-only. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). An unknown project, or a document of another project, is `404`. Served by `CMP-MATRIX-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_matrix`) until the lane wired it.
 */
export type ApplyComparisonMatrixEditsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: ApplyComparisonMatrixEditsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `applyComparisonMatrixEdits` (`application/json`, HTTP 200). */
export type ApplyComparisonMatrixEditsResult = ComparisonMatrix;

// ------------------------------------------------------------------------------------
// applyStageCardVerdicts - POST /stage-chain-runs/{stage_chain_run_id}/card-verdicts
// ------------------------------------------------------------------------------------

/** Apply Verdicts */
export type ApplyStageCardVerdictsInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/card-verdicts`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Request body, sent as `application/json`. */
  body: ApplyStageCardVerdictsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `applyStageCardVerdicts` (`application/json`, HTTP 200). */
export type ApplyStageCardVerdictsResult = StageCardVerdictPage;

// ------------------------------------------------------------------------------------
// applyStageSheetMap - POST /stage-pairs/{stage_pair_id}/sheet-map
// ------------------------------------------------------------------------------------

/** Apply Stage Sheet Map */
export type ApplyStageSheetMapInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/sheet-map`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Request body, sent as `application/json`. */
  body: ApplyStageSheetMapRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `applyStageSheetMap` (`application/json`, HTTP 201). */
export type ApplyStageSheetMapResult = StageLinkRevision;

// ------------------------------------------------------------------------------------
// approveRegistration - POST /registrations/{request_id}/approve
// ------------------------------------------------------------------------------------

/**
 * Approve a registration request and create the account.
 *
 * Requires `admin`. In one transaction, with the request locked: the account is created from the request's login, names and password, with a complete profile and the roles the body names (at least one); the request is decided and its password removed. The same `Idempotency-Key` with the same payload replays the recorded outcome; with another payload it is `idempotency_key_reuse`.
 */
export type ApproveRegistrationInput = {
  /** Path parameters, substituted into `/registrations/{request_id}/approve`. */
  path: {
    request_id: RegistrationRequestId;
  };
  /** Request body, sent as `application/json`. */
  body: ApproveRegistrationRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `approveRegistration` (`application/json`, HTTP 200). */
export type ApproveRegistrationResult = RegistrationRequest;

// ------------------------------------------------------------------------------------
// approveSheetPairing - POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings
// ------------------------------------------------------------------------------------

/**
 * Approve Sheet Pairing
 *
 * Store the calling expert's approval of one sheet pair that the comparison of the path's (older) version with `target_version_uid` proposes: a source page and a target page of the two immutable versions, identified by the SHA-256 of their text and by `suggestion_sha256`, never by a display number. The comparison is recomputed with the body's `mode` and runs when the confirmation arrives and must still propose exactly this pair under this digest. The approval is one new row of an append-only history, with the actor, the time and the seal of the raw evidence of the approved set, and one audit event, in one transaction; it is never updated. An exact repeat of an active approval answers it, `replayed: true`. A refusal is `conflict` with `conflict_reason` `sheet_pair_not_proposed`, `sheet_page_already_paired`, `sheet_pair_limit_reached` (at most 32 active approvals), `approved_text_changed` (an earlier approval's page text is no longer the approved one; withdraw it first) or `sheet_pair_too_large`. `expert` is required; `admin` alone is refused (`required_capability: role:expert`). While the «Сравнение версий» module is on (`AUDITMANAGER_COMPARISON_MODULES` names `versions`) this operation answers `503 dependency_unavailable` (`details.dependency: comparison_versions_module`) and writes nothing: the effective matrix is the only store of which page of one version is which page of another (`ADR-0025` decision 13; migration `0039` turned the active approvals into manual matrix edits and kept the `0035` rows as history). With the module off it works as before.
 */
export type ApproveSheetPairingInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    version_uid: VersionUid;
  };
  /** Request body, sent as `application/json`. */
  body: ApproveSheetPairingRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `approveSheetPairing` (`application/json`, HTTP 201). */
export type ApproveSheetPairingResult = SheetPairingEvent;

// ------------------------------------------------------------------------------------
// archiveAnalysisPreset - POST /analysis/presets/{preset_id}/archive
// ------------------------------------------------------------------------------------

/**
 * Archive an analysis preset.
 *
 * Append the archived revision, which repeats the previous name and connection. One-way: nothing follows an archive, and the name is free again. An administrator's act (`role:admin`). Refusals: `403`, `404` for an unknown preset, `409 conflict` (`preset_archived`) for one already archived.
 */
export type ArchiveAnalysisPresetInput = {
  /** Path parameters, substituted into `/analysis/presets/{preset_id}/archive`. */
  path: {
    preset_id: PresetId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `archiveAnalysisPreset` (`application/json`, HTTP 200). */
export type ArchiveAnalysisPresetResult = AnalysisPreset;

// ------------------------------------------------------------------------------------
// archiveExecutorConnection - POST /executor-connections/{connection_id}/archive
// ------------------------------------------------------------------------------------

/** Archive Executor Connection */
export type ArchiveExecutorConnectionInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/archive`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `archiveExecutorConnection` (`application/json`, HTTP 200). */
export type ArchiveExecutorConnectionResult = ExecutorConnection;

// ------------------------------------------------------------------------------------
// archiveExecutorGroup - POST /executor-groups/{group_id}/archive
// ------------------------------------------------------------------------------------

/**
 * Archive Executor Group
 *
 * Archive a group (`EXEC2-SEAL-2`): one-way, not deletion. An archived group takes no revision, rule or run; work already admitted on it finishes. `409 conflict` with `conflict_reason` `group_routed` while a rule still names it; archiving an archived group answers it as it stands. `404 not_found`; `403 permission_denied` for a caller without `admin`.
 */
export type ArchiveExecutorGroupInput = {
  /** Path parameters, substituted into `/executor-groups/{group_id}/archive`. */
  path: {
    group_id: ExecutorGroupId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `archiveExecutorGroup` (`application/json`, HTTP 200). */
export type ArchiveExecutorGroupResult = ExecutorGroup;

// ------------------------------------------------------------------------------------
// archiveExecutorHost - POST /executor-hosts/{host_id}/archive
// ------------------------------------------------------------------------------------

/**
 * Archive Executor Host
 *
 * `HOSTS-SEAL-1`: «Удалить» a server -- one-way, not deletion (a call names its host by identity for good). The host token is revoked, the system connections of the host are archived, and runs already bound to it finish as they can. Archiving an archived server answers it as it stands. `role:admin`, `Idempotency-Key` required.
 */
export type ArchiveExecutorHostInput = {
  /** Path parameters, substituted into `/executor-hosts/{host_id}/archive`. */
  path: {
    host_id: ExecutorHostId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `archiveExecutorHost` (`application/json`, HTTP 200). */
export type ArchiveExecutorHostResult = ExecutorHost;

// ------------------------------------------------------------------------------------
// archiveUser - POST /users/{user_uid}/archive
// ------------------------------------------------------------------------------------

/**
 * Archive an account.
 *
 * Requires `admin`. Archive is the normal removal (R-61) and is reversible: the account cannot sign in and every credential it holds is refused from its next request. Oneself is `permission_denied`; an archived account is `state_transition_not_allowed` against `app_user`; the last active account holding `admin` is `conflict` with `conflict_reason: last_admin`.
 */
export type ArchiveUserInput = {
  /** Path parameters, substituted into `/users/{user_uid}/archive`. */
  path: {
    user_uid: UserUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `archiveUser` (`application/json`, HTTP 200). */
export type ArchiveUserResult = Account;

// ------------------------------------------------------------------------------------
// cancelComparisonAiPairCheck - POST /comparison-ai-pair-checks/{comparison_ai_job_id}/cancellation
// ------------------------------------------------------------------------------------

/**
 * Cancel an AI check of pairs.
 *
 * Cancels the unfinished questions; answers already stored stay and are never asked again. A job that is already finished is `409 conflict` (`comparison_ai_job_state`). An unknown job is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AIPAIR-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_pairs`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type CancelComparisonAiPairCheckInput = {
  /** Path parameters, substituted into `/comparison-ai-pair-checks/{comparison_ai_job_id}/cancellation`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelComparisonAiPairCheck` (`application/json`, HTTP 200). */
export type CancelComparisonAiPairCheckResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// cancelComparisonAiSheetChanges - POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/cancellation
// ------------------------------------------------------------------------------------

/**
 * Cancel an AI description of changes.
 *
 * «Отменить» and «Отменить задание»: cancels the unfinished sheets of a series job or of a single-sheet job. A job that is already finished is `409 conflict` (`comparison_ai_job_state`). An unknown job is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type CancelComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-ai-sheet-jobs/{comparison_ai_job_id}/cancellation`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type CancelComparisonAiSheetChangesResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// cancelComparisonReport - POST /comparison-reports/{comparison_report_id}/cancellation
// ------------------------------------------------------------------------------------

/**
 * Cancel a report.
 *
 * «Отменить»: stops a queued, running or paused report; its finished parts are kept. A report in another state is `409 conflict` (`comparison_report_state`). An unknown report is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type CancelComparisonReportInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/cancellation`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelComparisonReport` (`application/json`, HTTP 200). */
export type CancelComparisonReportResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// cancelComparisonSeries - POST /comparison-series/{comparison_series_id}/cancellation
// ------------------------------------------------------------------------------------

/**
 * Cancel a series.
 *
 * «Отменить»: cancels the items that have not run; results already computed stay. A series that is already finished is `409 conflict` (`comparison_series_state`). An unknown series is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type CancelComparisonSeriesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/cancellation`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelComparisonSeries` (`application/json`, HTTP 200). */
export type CancelComparisonSeriesResult = ComparisonSeries;

// ------------------------------------------------------------------------------------
// cancelComparisonSpecification - POST /comparison-ai-spec-jobs/{comparison_ai_job_id}/cancellation
// ------------------------------------------------------------------------------------

/**
 * Cancel a specification comparison.
 *
 * Cancels the unfinished versions of a `spec` job. A job that is already finished is `409 conflict` (`comparison_ai_job_state`). An unknown job, or a job of another method, is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type CancelComparisonSpecificationInput = {
  /** Path parameters, substituted into `/comparison-ai-spec-jobs/{comparison_ai_job_id}/cancellation`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelComparisonSpecification` (`application/json`, HTTP 200). */
export type CancelComparisonSpecificationResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// cancelComparisonUpload - POST /comparison-uploads/{comparison_upload_id}/cancellation
// ------------------------------------------------------------------------------------

/**
 * Cancel an upload batch («Отменить пакет»).
 *
 * Aborts the parts that were never completed. The bytes of versions that were already admitted are not removed by this act; they are removed only by the operator's project erase (`ADR-0025` decision 10, `R-146c`). A finished batch is `409 conflict` (`comparison_upload_state`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-02` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type CancelComparisonUploadInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/cancellation`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelComparisonUpload` (`application/json`, HTTP 200). */
export type CancelComparisonUploadResult = ComparisonUpload;

// ------------------------------------------------------------------------------------
// cancelRun - POST /runs/{run_id}/cancel
// ------------------------------------------------------------------------------------

/** Cancel Run */
export type CancelRunInput = {
  /** Path parameters, substituted into `/runs/{run_id}/cancel`. */
  path: {
    run_id: RunId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelRun` (`application/json`, HTTP 200). */
export type CancelRunResult = RunStatus;

// ------------------------------------------------------------------------------------
// cancelStageChainBatch - POST /stage-chain-batches/{stage_chain_batch_id}/cancellation
// ------------------------------------------------------------------------------------

/** Cancel Batch */
export type CancelStageChainBatchInput = {
  /** Path parameters, substituted into `/stage-chain-batches/{stage_chain_batch_id}/cancellation`. */
  path: {
    stage_chain_batch_id: StageChainBatchId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelStageChainBatch` (`application/json`, HTTP 200). */
export type CancelStageChainBatchResult = StageChainBatch;

// ------------------------------------------------------------------------------------
// cancelStageChainRun - POST /stage-chain-runs/{stage_chain_run_id}/cancellation
// ------------------------------------------------------------------------------------

/** Cancel Stage Chain Run */
export type CancelStageChainRunInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/cancellation`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelStageChainRun` (`application/json`, HTTP 200). */
export type CancelStageChainRunResult = StageChainRun;

// ------------------------------------------------------------------------------------
// cancelStageUpload - POST /stage-uploads/{stage_upload_id}/cancellation
// ------------------------------------------------------------------------------------

/** Cancel Stage Upload */
export type CancelStageUploadInput = {
  /** Path parameters, substituted into `/stage-uploads/{stage_upload_id}/cancellation`. */
  path: {
    stage_upload_id: StageUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `cancelStageUpload` (`application/json`, HTTP 200). */
export type CancelStageUploadResult = StageUpload;

// ------------------------------------------------------------------------------------
// carryOverDecision - POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/carryovers
// ------------------------------------------------------------------------------------

/**
 * Carry Over Decision
 *
 * Carry one expert decision from a finding of the path's (older) version to the finding of `target_version_uid` that the comparison proposes as `unchanged`, on the calling expert's confirmation. The comparison is recomputed with the body's `mode` and runs when the confirmation arrives, and must still propose exactly this pair; the source finding's current verdict must still be the `source_decision_id` the expert was shown (`accepted` or `rejected`), and the target finding must have no decision event yet. The target receives one new `accept` or `reject` event authored by the caller, whose `comment` records the carried-from finding, decision and versions; a severity is carried with an accept or the carryover is refused, never dropped. Nothing else is written: the source finding and its decisions stay as they were. An exact repeat answers the event already carried, `replayed: true`, and keeps its first expert. A refusal is `conflict` with `conflict_reason` `carryover_pair_not_proposed`, `carryover_source_decision_not_current`, `carryover_target_already_decided` or `carryover_severity_not_carryable`. `expert` is required; `admin` alone is refused (`required_capability: role:expert`).
 */
export type CarryOverDecisionInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/carryovers`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    version_uid: VersionUid;
  };
  /** Request body, sent as `application/json`. */
  body: CarryOverDecisionRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `carryOverDecision` (`application/json`, HTTP 201). */
export type CarryOverDecisionResult = CarryOverDecisionResponse;

// ------------------------------------------------------------------------------------
// carryOverProposalDecisions - POST /optimisation-passes/{optimisation_pass_id}/decision-carryovers
// ------------------------------------------------------------------------------------

/**
 * Carry Over Proposal Decisions
 *
 * `UI-B-14` (contract 1.37.0), «Перенести решения из V#»: carry the decisions in force of `source_optimisation_pass_id` -- a pass of the same document set started over an earlier version -- into the pass of the path. A source decision (an `accept`, a `reject` or a `revise`; a proposal nobody decided or whose decision was withdrawn carries nothing) is appended to a proposal of this pass only where exactly one proposal of each pass has the same content -- the type, the specification row's text, the unit, the currency, both positions by code, mark, name and supplier, and both unit prices; never a display number, a name alone or a position in the drawing -- and only when that proposal has no event at all. Each carried decision is an ordinary appended event, authored by the caller, with the source's verdict and comment and `carried_from` naming the source decision and its version; a later decision on the proposal supersedes it. The report counts every decision in force of the source in exactly one of `carried`, `target_decided` (the proposal already has an event, which stands), `ambiguous` (more than one proposal of either pass has that content) and `unmatched` (no proposal of this pass has it). An unknown target pass is `404`; a source that names no pass, is the target, belongs to another document set or was not started over an earlier version is `409 conflict` with `conflict_reason` `carryover_source_unknown`, `carryover_source_is_target`, `carryover_source_other_document` or `carryover_source_not_earlier`, and nothing is written. An exact repeat of the `Idempotency-Key` answers the stored report and appends nothing; the same key with another source or caller is `409 idempotency_key_reuse`; a new key repeats the matching and carries nothing more once the targets are decided. `expert` only (`admin` alone is `permission_denied`).
 */
export type CarryOverProposalDecisionsInput = {
  /** Path parameters, substituted into `/optimisation-passes/{optimisation_pass_id}/decision-carryovers`. */
  path: {
    optimisation_pass_id: OptimisationPassId;
  };
  /** Request body, sent as `application/json`. */
  body: CarryOverProposalDecisionsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `carryOverProposalDecisions` (`application/json`, HTTP 200). */
export type CarryOverProposalDecisionsResult = ProposalDecisionCarryoverReport;

// ------------------------------------------------------------------------------------
// changePassword - POST /auth/password
// ------------------------------------------------------------------------------------

/**
 * Change the signed-in account's password and revoke its old credentials.
 *
 * Two things happen here and they are one write. The account's password becomes the one supplied, and every credential this deployment ever minted for that account stops being accepted -- **including the credential this request presented**. A password change that leaves the old password's credentials working is a password change in name only, so the two are not offered separately and cannot land separately.
 *
 * **Whose password changes is decided by the credential, never by the body.** There is no login property and there will not be one: the caller may change their own password and no other, and a login in the body would be an operation one caller could aim at another.
 *
 * **The response is the replacement credential**, minted after the change, and the only one this account now accepts. It is answered rather than left to a second exchange because the caller's own credential was revoked by this very request: a `204` would leave them holding something already dead with no way to tell that from a failure.
 *
 * The `403` is declared because every operation behind the seam declares it: `permission_denied` means an authenticated subject was refused, and a generated client needs a typed shape for it on every authorized operation. This operation does not raise it today: an account still on a default credential reaches it, so does an incomplete profile, and it needs no role.
 *
 * Nothing is created, so there is no idempotency key. A repeat of the same request is refused by its own `current_password`, which is no longer current -- it is not replayed and there is no `409` here.
 *
 * Revocation has no operation of its own on this surface. Ending a pilot -- taking credentials away from accounts whose passwords nobody is changing -- is an operator's action taken on the deployment; an administrator's changes that take an account's rights away (`archiveUser`, a role change through `updateUser`, `resetUserPassword`) revoke that account's credentials as part of the change.
 */
export type ChangePasswordInput = {
  /** Request body, sent as `application/json`. */
  body: ChangePasswordRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `changePassword` (`application/json`, HTTP 200). */
export type ChangePasswordResult = IssueTokenResponse;

// ------------------------------------------------------------------------------------
// claimExecutorTask - POST /runner/tasks/claim
// ------------------------------------------------------------------------------------

/**
 * Claim Executor Task
 *
 * `HOSTS-SEAL-1` (ADR-0028): with a **host token** the task gains `provider`, `access`, `model_id`, `effort`, `timeout_seconds` and `cell_key` -- all six or none; since contract 1.49.0 there is no `max_output_tokens`: no answer cap reaches a model (`R-153n`), and `timeout_seconds` is the constant of the task's row or kind (`R-153o`) -- and `model` equals `model_id`. The agent claims only while at least one model is verified and a slot is free behind one (no per-provider free capacity is sent: the stand's capacity pool decides). It refuses a task whose model it does not report as verified for that provider and access, or whose effort is not one of the model's, with `failExecutorTask` before anything runs (`model_not_available`, `effort_not_allowed`), a task with none of the host members with `host_task_incomplete`, and one with images the host cannot take with `image_input_unsupported`.
 */
export type ClaimExecutorTaskInput = {
  /** Request body, sent as `application/json`. */
  body: ClaimExecutorTaskRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `claimExecutorTask` (`application/json`, HTTP 200/204). */
export type ClaimExecutorTaskResult = ClaimedExecutorTask;

// ------------------------------------------------------------------------------------
// classifyDocumentVersion - PUT /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification
// ------------------------------------------------------------------------------------

/**
 * Classify Document Version
 *
 * Classify one version: its project stage (`P` or `R`) and one of the fifteen sections, confirmed by the calling expert. `expert` is required; `admin` alone is refused with `permission_denied` (`required_capability: role:expert`). The version must belong to the named document and the document to the named project, otherwise `not_found`. An exact repeat answers the stored row and keeps the first confirmer; a different stage or section is `conflict` with `conflict_reason: version_already_classified` and changes nothing -- to change an existing classification an expert uses `correctVersionClassification`, with a reason. A suggestion, a file name or the legacy document `section` is never a classification.
 */
export type ClassifyDocumentVersionInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    version_uid: VersionUid;
  };
  /** Request body, sent as `application/json`. */
  body: ClassifyDocumentVersionRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `classifyDocumentVersion` (`application/json`, HTTP 200). */
export type ClassifyDocumentVersionResult = VersionClassification;

// ------------------------------------------------------------------------------------
// clearComparisonLaunchQueue - POST /projects/{project_uid}/comparison-launch-queue/clear
// ------------------------------------------------------------------------------------

/**
 * Clear the launch queue.
 *
 * «Очистить»: the waiting entries and the history leave the queue; the step that is running continues. An unknown project is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-QUEUE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_launch_queue`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ClearComparisonLaunchQueueInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-launch-queue/clear`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `clearComparisonLaunchQueue` (`application/json`, HTTP 200). */
export type ClearComparisonLaunchQueueResult = ComparisonLaunchQueue;

// ------------------------------------------------------------------------------------
// compareDocumentVersions - GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison
// ------------------------------------------------------------------------------------

/**
 * Compare Document Versions
 *
 * Compare two versions of one document set: the path names the older (source) version and `target_version_uid` the newer one. Both must be published versions of the named document in the named project with the same confirmed section and, with `mode=version` (the default), the same explicit project stage; with `mode=stage` the source must be classified `P` and the target `R` (design to working documentation of one set). Each needs a published run (the newest one, or the one `source_run_id` / `target_run_id` names). A path that names no such version is `404`; otherwise a pair the rule does not admit is `outcome: refused` with one `refusal.reason`, never relabelled. The answer carries proposed sheet pairs with their evidence, one page of raw line differences (`diff_offset`, `diff_limit`, `next_offset`) and proposed matches between the two runs' findings. Every pairing and match in `sheets`, `sheet_diffs` and `findings` is a proposal; this read writes nothing. `approved_pairs` (null for a refused comparison) lists the sheet pairs an expert approved for exactly this pair of versions (`approveSheetPairing`) and, for approved pairs only, their deterministic line differences, recomputed from the immutable text and bound to the version bytes by a seal; when a page's text is no longer the approved one (`text_changed`), the seal differs (`seal_changed`) or the set exceeds the response budget (`too_large`) the differences are withheld, never truncated. Any one role, `role:admin|expert|viewer`.
 */
export type CompareDocumentVersionsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    version_uid: VersionUid;
  };
  /** Query string parameters. */
  query: {
    /** Sheets with text differences per answer. */
    diff_limit?: number;
    /** Position in the list of sheets with text differences. */
    diff_offset?: number;
    /** `version`: both versions carry the same project stage and section. `stage`: the source is classified `P`, the target `R`, with the same section. */
    mode?: "version" | "stage";
    source_run_id?: RunId;
    target_run_id?: RunId;
    /** The newer version of the same set; the path names the older one. */
    target_version_uid: VersionUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `compareDocumentVersions` (`application/json`, HTTP 200). */
export type CompareDocumentVersionsResult = VersionComparison;

// ------------------------------------------------------------------------------------
// completeComparisonUploadFile - POST /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/completion
// ------------------------------------------------------------------------------------

/**
 * Complete one file and check it against its declared values.
 *
 * Completes the multipart object of the file and verifies the whole object against the declared SHA-256 and size (`ADR-0025` decision 10). A mismatch is `422 storage_integrity_error` (`expected_sha256` and `actual_sha256`, or `role: comparison_file_size`): the file is marked failed, nothing is published, and the client sends it again. Names are never identity. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type CompleteComparisonUploadFileInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/completion`. */
  path: {
    comparison_upload_file_id: ComparisonUploadFileId;
    comparison_upload_id: ComparisonUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `completeComparisonUploadFile` (`application/json`, HTTP 200). */
export type CompleteComparisonUploadFileResult = ComparisonUploadFile;

// ------------------------------------------------------------------------------------
// completeStageUploadFile - POST /stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/completion
// ------------------------------------------------------------------------------------

/** Complete Stage Upload File */
export type CompleteStageUploadFileInput = {
  /** Path parameters, substituted into `/stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/completion`. */
  path: {
    stage_upload_file_id: StageUploadFileId;
    stage_upload_id: StageUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `completeStageUploadFile` (`application/json`, HTTP 200). */
export type CompleteStageUploadFileResult = StageUploadFile;

// ------------------------------------------------------------------------------------
// confirmComparisonUploadSet - POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/confirmation
// ------------------------------------------------------------------------------------

/**
 * Confirm the membership and order of one proposed set.
 *
 * The user's final word on one set: its files in their order (the array order is the version order), their labels, and the designation, stage, section and existing document it belongs to. The stage and section are a proposal an expert confirms through this act; they are never inferred. A file listed twice, a file of another set or a missing file is `422 validation_failed` (`comparison_set_members`); a set that is not awaiting confirmation is `409 conflict` (`comparison_set_state`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type ConfirmComparisonUploadSetInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/confirmation`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
    comparison_upload_set_id: ComparisonUploadSetId;
  };
  /** Request body, sent as `application/json`. */
  body: ConfirmComparisonUploadSetRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `confirmComparisonUploadSet` (`application/json`, HTTP 200). */
export type ConfirmComparisonUploadSetResult = ComparisonProposalSet;

// ------------------------------------------------------------------------------------
// confirmExecutorAgentInstallHostKey - POST /executor-connections/{connection_id}/agent-installs/{install_id}/confirm-host-key
// ------------------------------------------------------------------------------------

/**
 * Confirm Executor Agent Install Host Key
 *
 * Confirm the host-key fingerprint the worker observed, explicitly and by value (`EXEC2-SEAL-1`, ADR-0026 decision 7): there is no trust on first use. The install proceeds only with the fingerprint the administrator read. Refusals: `403 permission_denied`; `404 not_found`; `409 conflict` with `conflict_reason` `install_not_awaiting_host_key` (the install is in another state) or `host_key_changed` (the fingerprint named is not the one observed); `422 validation_failed`.
 */
export type ConfirmExecutorAgentInstallHostKeyInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/agent-installs/{install_id}/confirm-host-key`. */
  path: {
    connection_id: ExecutorConnectionId;
    install_id: ExecutorAgentInstallId;
  };
  /** Request body, sent as `application/json`. */
  body: ConfirmExecutorAgentInstallHostKeyRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `confirmExecutorAgentInstallHostKey` (`application/json`, HTTP 200). */
export type ConfirmExecutorAgentInstallHostKeyResult = ExecutorAgentInstall;

// ------------------------------------------------------------------------------------
// confirmExecutorHostAgentInstallHostKey - POST /executor-hosts/{host_id}/agent-installs/{install_id}/confirm-host-key
// ------------------------------------------------------------------------------------

/**
 * Confirm Executor Host Agent Install Host Key
 *
 * `HOSTS-SEAL-1`: confirm the host key of the install session of a host, as `confirmExecutorAgentInstallHostKey`: the fingerprint must equal the one the worker observed; there is no trust on first use. `role:admin`, `Idempotency-Key` required.
 */
export type ConfirmExecutorHostAgentInstallHostKeyInput = {
  /** Path parameters, substituted into `/executor-hosts/{host_id}/agent-installs/{install_id}/confirm-host-key`. */
  path: {
    host_id: ExecutorHostId;
    install_id: ExecutorAgentInstallId;
  };
  /** Request body, sent as `application/json`. */
  body: ConfirmExecutorAgentInstallHostKeyRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `confirmExecutorHostAgentInstallHostKey` (`application/json`, HTTP 200). */
export type ConfirmExecutorHostAgentInstallHostKeyResult = ExecutorAgentInstall;

// ------------------------------------------------------------------------------------
// confirmStagePair - POST /projects/{project_uid}/stage-pairs
// ------------------------------------------------------------------------------------

/** Confirm Stage Pair */
export type ConfirmStagePairInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/stage-pairs`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: ConfirmStagePairRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `confirmStagePair` (`application/json`, HTTP 201). */
export type ConfirmStagePairResult = StagePair;

// ------------------------------------------------------------------------------------
// confirmStageUploadCandidate - POST /stage-upload-candidates/{stage_upload_candidate_id}/confirmation
// ------------------------------------------------------------------------------------

/** Confirm Stage Upload Candidate */
export type ConfirmStageUploadCandidateInput = {
  /** Path parameters, substituted into `/stage-upload-candidates/{stage_upload_candidate_id}/confirmation`. */
  path: {
    stage_upload_candidate_id: StageUploadCandidateId;
  };
  /** Request body, sent as `application/json`. */
  body: ConfirmStageUploadCandidateRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `confirmStageUploadCandidate` (`application/json`, HTTP 200). */
export type ConfirmStageUploadCandidateResult = StageUploadCandidate;

// ------------------------------------------------------------------------------------
// continueComparisonReport - POST /comparison-reports/{comparison_report_id}/continuation
// ------------------------------------------------------------------------------------

/**
 * Continue a report.
 *
 * «Продолжить»: an interrupted, partial, failed or paused report goes on, its finished parts reused. After a pause for `overrun` or `route_changed` the request carries a new consent for what is left. A report in another state is `409 conflict` (`comparison_report_state`). An unknown report is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ContinueComparisonReportInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/continuation`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /** Request body, sent as `application/json`. */
  body: ResumeComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `continueComparisonReport` (`application/json`, HTTP 200). */
export type ContinueComparisonReportResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// correctVersionClassification - POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification/corrections
// ------------------------------------------------------------------------------------

/**
 * Correct Version Classification
 *
 * Correct one version's classification: append a new revision with the full target `project_stage` and `section_code`, a `reason` (1 to 2000 characters, with a letter or a digit) and the `expected_revision` the caller was looking at. `expert` is required; `admin` alone is refused with `permission_denied` (`required_capability: role:expert`). The version must belong to the named document and the document to the named project, otherwise `not_found`. Revision 1 is the original confirmation and is never changed; the current classification is the latest revision. An unclassified version is `conflict` with `conflict_reason: version_not_classified` -- classify it first. An `expected_revision` behind the current one is `conflict` with `conflict_reason: classification_revision_stale` and writes nothing, unless the request is an exact repeat (same expert, same values, same reason) of the revision after it, which answers that stored revision with `201` and writes nothing; one ahead of the current revision, a pair equal to the current classification (`constraint: differs_from_current`) and a blank, over-long or unprintable reason are `validation_failed`. Runs already started keep the analysis profile they pinned; a re-audit routes from the corrected classification. No `Idempotency-Key`: `expected_revision` is what makes a retry safe.
 */
export type CorrectVersionClassificationInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification/corrections`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    version_uid: VersionUid;
  };
  /** Request body, sent as `application/json`. */
  body: CorrectVersionClassificationRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `correctVersionClassification` (`application/json`, HTTP 201). */
export type CorrectVersionClassificationResult = VersionClassification;

// ------------------------------------------------------------------------------------
// createAnalysisPreset - POST /analysis/presets
// ------------------------------------------------------------------------------------

/**
 * Save an analysis preset.
 *
 * Save a preset: a name and an executor connection. An administrator's act, like every executor write (`role:admin`; the command re-reads the role set in its own transaction). The name is trimmed, 1 to 120 characters without control characters, and unique among active presets without regard to case. The connection must exist and must not be archived. At most 100 presets exist. The change and its audit event commit together. Refusals: `403`, `422 validation_failed` (`name`: `required`, `max_length`, `printable`; `executor_connection_id`: `unknown_connection`), `409 conflict` (`preset_name_in_use`, `preset_limit_reached`, `connection_archived`).
 */
export type CreateAnalysisPresetInput = {
  /** Request body, sent as `application/json`. */
  body: SaveAnalysisPresetRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createAnalysisPreset` (`application/json`, HTTP 201). */
export type CreateAnalysisPresetResult = AnalysisPreset;

// ------------------------------------------------------------------------------------
// createAssignment - POST /assignments
// ------------------------------------------------------------------------------------

/**
 * Assign a project, or one document of it, to an expert.
 *
 * Requires `admin`. Gives the named project, or one document of it (`document_uid`, which must belong to the project, otherwise `not_found`), to an active account holding `expert` (otherwise `validation_failed`, `constraint: active_expert_required`), with an optional note. The assignment starts `assigned` with its `assigned` event. One open assignment per scope: an exact repeat (same assignee and note) answers the open one, and any other creation there is `conflict` with `conflict_reason: assignment_open` -- reassign or cancel that one instead. No `Idempotency-Key`: the open-scope rule is what makes a repeat safe.
 */
export type CreateAssignmentInput = {
  /** Request body, sent as `application/json`. */
  body: CreateAssignmentRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createAssignment` (`application/json`, HTTP 200). */
export type CreateAssignmentResult = Assignment;

// ------------------------------------------------------------------------------------
// createComparisonReport - POST /comparison-series/{comparison_series_id}/reports
// ------------------------------------------------------------------------------------

/**
 * Make a report draft from the summary of a series.
 *
 * «Сформировать PDF-отчёт…», source «сводка проекта»: makes a `draft` report of the given kind (`client` by default, `analytic`) with its estimate (transitions to write, prompt size, routed model, USD estimate). No model is called and nothing is spent; `startComparisonReport` consents to the estimate. A series with no summary is `409 conflict` (`comparison_summary_unavailable`). An unknown series is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type CreateComparisonReportInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/reports`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /** Request body, sent as `application/json`. */
  body: CreateComparisonReportRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createComparisonReport` (`application/json`, HTTP 201). */
export type CreateComparisonReportResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// createComparisonUpload - POST /projects/{project_uid}/comparison-uploads
// ------------------------------------------------------------------------------------

/**
 * Declare an upload batch of plain PDFs for comparison.
 *
 * Declares the files of one batch under a project: for each a display name (a hint for the grouping proposal, never an identity), its size in bytes and its SHA-256, optionally its page count. Nothing is stored yet; the response names the batch, the part size (16 MiB, `ADR-0025` decision 10) and each file's identity, and the client then sends the parts. Temporary statistics intake removes the application limits on files, sets, batch bytes, declared pages and project bytes; the multipart store still has its technical part-count bound. Invalid declarations are refused as `422 validation_failed`; an account that already has an active batch, or an installation that already has two, is `409 conflict` (`conflict_reason: comparison_upload_active`). No error code is added. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written. `compare_after_preparation` («После подготовки сравнить все соседние версии», optional, absent means false) asks for the series of adjacent transitions to be queued for every set of the batch as soon as the set is prepared; until `CMP-SERIES-01` stores it, `true` answers `503 dependency_unavailable` (`details.dependency: comparison_series`) and creates nothing.
 */
export type CreateComparisonUploadInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-uploads`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: CreateComparisonUploadRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createComparisonUpload` (`application/json`, HTTP 201). */
export type CreateComparisonUploadResult = ComparisonUpload;

// ------------------------------------------------------------------------------------
// createExecutorAgentInstall - POST /executor-connections/{connection_id}/agent-installs
// ------------------------------------------------------------------------------------

/**
 * Create Executor Agent Install
 *
 * Start the install of the universal agent over SSH (path A, `EXEC2-SEAL-1`, ADR-0026 decision 7) on a `pull` connection. The administrator supplies host, port and user and either a key the stand generates (`generated_key`: the response carries the public half and its `authorized_keys` line) or a pasted private key (`pasted_key`: sealed, never returned). Passwords are not accepted. The worker scans the host key and the install waits in `awaiting_host_key` for `confirmExecutorAgentInstallHostKey`; no command text comes from the caller. Refusals use existing codes: `403 permission_denied`; `404 not_found`; `409 conflict` with `conflict_reason` `connection_archived`, `no_revision` or `install_in_progress` (an install of this connection has not finished); `422 validation_failed` with field `kind` and constraint `kind_not_pull`, or field `private_key` and constraint `private_key_required` (`pasted_key` without a key) or `private_key_not_accepted` (a key sent with `generated_key`); `503 dependency_unavailable` with dependency `secrets_public_key_missing` or `agent_package`.
 *
 * `HOSTS-SEAL-1` (contract 1.45.0): this operation stays the form for a `pull` connection. A server is connected over SSH with `createExecutorHostAgentInstall`, which takes no connection and no model.
 */
export type CreateExecutorAgentInstallInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/agent-installs`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /** Request body, sent as `application/json`. */
  body: CreateExecutorAgentInstallRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createExecutorAgentInstall` (`application/json`, HTTP 201). */
export type CreateExecutorAgentInstallResult = ExecutorAgentInstall;

// ------------------------------------------------------------------------------------
// createExecutorConnection - POST /executor-connections
// ------------------------------------------------------------------------------------

/** Create Executor Connection */
export type CreateExecutorConnectionInput = {
  /** Request body, sent as `application/json`. */
  body: CreateExecutorConnectionRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createExecutorConnection` (`application/json`, HTTP 201). */
export type CreateExecutorConnectionResult = ExecutorConnection;

// ------------------------------------------------------------------------------------
// createExecutorGroup - POST /executor-groups
// ------------------------------------------------------------------------------------

/**
 * Create Executor Group
 *
 * Create a group and its first revision (`EXEC2-SEAL-2`, ADR-0026 decision 10). A group is a set of interchangeable executors of one model; the revision is immutable and snapshots each member's connection revision. Every member must be of a connection that exists and is not archived, must name a revision of that connection, and that revision must pin exactly `pin_id` and `gateway_model` and share `billing` (and therefore the pinned rates, which the server snapshots from the provider lock): `422 validation_failed` with `details.field` `members` and constraint `unknown_executor_connection`, `member_revision_not_of_connection`, `member_repeated`, `tie_break_order_repeated` or `member_kind_not_served`, or with field `pin_id`, `gateway_model` or `billing` and constraint `member_pin_mismatch`, `member_model_mismatch` or `member_billing_mismatch`; a `pin_id` the provider lock does not hold is `model_not_pinned`; one to 16 members are accepted (`range`). An archived member connection is `409 conflict` with `conflict_reason` `connection_archived`. Mixed groups are not accepted. `409 conflict` with `conflict_reason` `group_name_in_use` for a name an active group holds. `403 permission_denied` for a caller without `admin`.
 */
export type CreateExecutorGroupInput = {
  /** Request body, sent as `application/json`. */
  body: CreateExecutorGroupRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createExecutorGroup` (`application/json`, HTTP 201). */
export type CreateExecutorGroupResult = ExecutorGroup;

// ------------------------------------------------------------------------------------
// createExecutorHostAgentInstall - POST /executor-hosts/agent-installs
// ------------------------------------------------------------------------------------

/**
 * Create Executor Host Agent Install
 *
 * `HOSTS-SEAL-1`: connect a server over SSH (path A) -- create the host and an install session, with no model. As `createExecutorAgentInstall`: `private_key` is required for `pasted_key` and refused for `generated_key`, sealed to the stand's public key and never returned; the session carries `host_id`. `role:admin`, `Idempotency-Key` required.
 */
export type CreateExecutorHostAgentInstallInput = {
  /** Request body, sent as `application/json`. */
  body: CreateExecutorHostAgentInstallRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createExecutorHostAgentInstall` (`application/json`, HTTP 201). */
export type CreateExecutorHostAgentInstallResult = ExecutorAgentInstall;

// ------------------------------------------------------------------------------------
// createProject - POST /projects
// ------------------------------------------------------------------------------------

/** Create a project. */
export type CreateProjectInput = {
  /** Request body, sent as `application/json`. */
  body: CreateProjectRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createProject` (`application/json`, HTTP 201). */
export type CreateProjectResult = Project;

// ------------------------------------------------------------------------------------
// createStageAssembly - POST /projects/{project_uid}/stage-assemblies
// ------------------------------------------------------------------------------------

/** Create Stage Assembly */
export type CreateStageAssemblyInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/stage-assemblies`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: CreateStageAssemblyRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createStageAssembly` (`application/json`, HTTP 201). */
export type CreateStageAssemblyResult = StageAssembly;

// ------------------------------------------------------------------------------------
// createStageReviewCard - POST /stage-chain-runs/{stage_chain_run_id}/review-cards
// ------------------------------------------------------------------------------------

/** Create Review Card */
export type CreateStageReviewCardInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/review-cards`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Request body, sent as `application/json`. */
  body: CreateStageReviewCardRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createStageReviewCard` (`application/json`, HTTP 201). */
export type CreateStageReviewCardResult = StageChangeCard;

// ------------------------------------------------------------------------------------
// createStageUpload - POST /projects/{project_uid}/stage-uploads
// ------------------------------------------------------------------------------------

/** Create Stage Upload */
export type CreateStageUploadInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/stage-uploads`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: CreateStageUploadRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `createStageUpload` (`application/json`, HTTP 201). */
export type CreateStageUploadResult = StageUpload;

// ------------------------------------------------------------------------------------
// decideOptimisationProposal - POST /optimisation-proposals/{optimisation_proposal_id}/decisions
// ------------------------------------------------------------------------------------

/**
 * Decide Optimisation Proposal
 *
 * Append an expert's decision on a proposal: `accept`, `reject` or `revise` (the comment is required for `revise`, at most 2000 characters), or `revoke` -- the withdrawal of the decision in force («Снять решение»), an event like any other that takes the proposal back to `pending`, with an optional comment, refused with `409 conflict` and `conflict_reason` `no_decision_to_revoke` when the proposal has no decision in force. Decisions are only appended, never changed; the latest one is current (unless it is a `revoke`), and any number may follow. `expert` is required (`admin` alone is `permission_denied`); an unknown proposal is `404`. An exact repeat of the `Idempotency-Key` answers the stored decision; the same key with another verdict, comment, proposal or caller is `409 idempotency_key_reuse`. The decision belongs to the proposal alone: no finding is read or changed. A decision that is ordered after a carried decision on the same proposal (`carryOverProposalDecisions`) simply takes the next place; the one case in which its place was taken meanwhile by a writer that held no lock is `409 conflict` with `conflict_reason` `proposal_decision_raced`, nothing is written and the same request can be repeated (contract 1.40.0).
 */
export type DecideOptimisationProposalInput = {
  /** Path parameters, substituted into `/optimisation-proposals/{optimisation_proposal_id}/decisions`. */
  path: {
    optimisation_proposal_id: OptimisationProposalId;
  };
  /** Request body, sent as `application/json`. */
  body: DecideOptimisationProposalRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `decideOptimisationProposal` (`application/json`, HTTP 201). */
export type DecideOptimisationProposalResult = ProposalDecisionResult;

// ------------------------------------------------------------------------------------
// deleteComparisonReport - POST /comparison-reports/{comparison_report_id}/deletion
// ------------------------------------------------------------------------------------

/**
 * Delete a report.
 *
 * «Удалить»: the report leaves the history. The stored bytes stay (the storage offers no delete of a published blob; only the operator's project erase removes them). A report that is queued or running is `409 conflict` (`comparison_report_state`). An unknown report is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type DeleteComparisonReportInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/deletion`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `deleteComparisonReport` (`application/json`, HTTP 200). */
export type DeleteComparisonReportResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// dequeueComparisonAiSheetChanges - POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/dequeue
// ------------------------------------------------------------------------------------

/**
 * Take an AI description of changes out of the AI queue.
 *
 * «Убрать из очереди»: a job that has not started leaves the installation's AI queue and is cancelled. A job that has started is `409 conflict` (`comparison_ai_job_state`). An unknown job is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type DequeueComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-ai-sheet-jobs/{comparison_ai_job_id}/dequeue`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `dequeueComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type DequeueComparisonAiSheetChangesResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// downloadAgentPackage - GET /runner/agent-package/{version}
// ------------------------------------------------------------------------------------

/**
 * Download Agent Package
 *
 * The agent package of exactly this version, as `application/gzip` (`EXEC2-SEAL-1`, ADR-0026 decision 6). It is built deterministically from `tools/executor-runner/` into the image and served by version with no authentication: it is public code with no secret, and its integrity is the sha256 that `issueExecutorEnrollment` writes into the install command. A version the image does not hold is `422 validation_failed` with field `version` and constraint `package_version_unknown`, never a listing of the versions that exist; an image with no package is `503 dependency_unavailable` with dependency `agent_package`. The proxy throttles the route per address.
 */
export type DownloadAgentPackageInput = {
  /** Path parameters, substituted into `/runner/agent-package/{version}`. */
  path: {
    version: AgentPackageVersion;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `downloadAgentPackage` (`application/gzip`, HTTP 200). */
export type DownloadAgentPackageResult = Blob;

// ------------------------------------------------------------------------------------
// endUserSessions - POST /users/{user_uid}/sessions/end
// ------------------------------------------------------------------------------------

/**
 * End every session of an account.
 *
 * Requires `admin` and an `Idempotency-Key`. Raises the account's credential epoch, so every credential it holds -- in every browser and on every device -- is refused from its next request and it signs in again; its password, roles and sign-in brake are untouched. The event `sessions_ended` is journalled in the same transaction (`listAuthEvents`). Not oneself (`permission_denied`): an administrator ends their own sessions by changing their password. An archived or missing account is `not_found`. An exact repeat of the key answers the account unchanged and ends nothing more; the key under another account or another administrator is `idempotency_key_reuse`.
 */
export type EndUserSessionsInput = {
  /** Path parameters, substituted into `/users/{user_uid}/sessions/end`. */
  path: {
    user_uid: UserUid;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `endUserSessions` (`application/json`, HTTP 200). */
export type EndUserSessionsResult = Account;

// ------------------------------------------------------------------------------------
// enqueueComparisonLaunch - POST /projects/{project_uid}/comparison-launch-queue/entries
// ------------------------------------------------------------------------------------

/**
 * Queue document sets and steps.
 *
 * «Запустить выбранные по очереди»: queues the selected document sets × steps (`profile`, `matrix`, `ai_pairs`, `series`, `ai_changes`, `report`); the queue runs one step at a time across sets. The `upload` step cannot be queued (`422 validation_failed`, `comparison_step_not_queueable`), nor can a consent be given to a step that is not an AI step. An AI step carries its own consent when its estimate exists, one consent per set; without one it waits and becomes `needs_consent`. A set or step already queued is `409 conflict` (`comparison_launch_entry_active`). An unknown project, or a document of another project, is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-QUEUE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_launch_queue`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type EnqueueComparisonLaunchInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-launch-queue/entries`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: EnqueueComparisonLaunchRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `enqueueComparisonLaunch` (`application/json`, HTTP 201). */
export type EnqueueComparisonLaunchResult = ComparisonLaunchQueue;

// ------------------------------------------------------------------------------------
// estimateComparisonAiPairCheck - GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check/estimate
// ------------------------------------------------------------------------------------

/**
 * Estimate the AI check of the doubtful pairs of a document set.
 *
 * The estimate behind «Проверить» of step 4: the questions the latest matrix would ask (`no_pair` for a sheet with no pair whose cell has candidates, `medium_pair` for a pair of medium confidence; a sheet of a multi-sheet table group is never asked), the pairs, the images with their bytes, the prompt size, the routed model and the USD estimate; `reused` of the questions already have a stored answer under the same content key and are never sent again. Computing it calls no model. A matrix that is not `ready` is `409 conflict` (`comparison_matrix_stale`); nothing to ask is `409 conflict` (`comparison_ai_nothing_to_do`). An unknown project, or a document of another project, is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AIPAIR-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_pairs`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type EstimateComparisonAiPairCheckInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check/estimate`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `estimateComparisonAiPairCheck` (`application/json`, HTTP 200). */
export type EstimateComparisonAiPairCheckResult = ComparisonAiEstimate;

// ------------------------------------------------------------------------------------
// estimateComparisonAiSheetChanges - GET /comparison-series/{comparison_series_id}/ai-sheet-changes/estimate
// ------------------------------------------------------------------------------------

/**
 * Estimate the AI description of changes of a series.
 *
 * The estimate behind «Запустить» of step 6: the sheets whose comparison is not `same`, the images with their bytes, the prompt size, the routed model and the USD estimate; `reused` of the sheets keep a stored answer for the same content, prompt version and model. With `only_failed` true it is the estimate of «Повторить листы с ошибкой». Computing it calls no model. A series with no finished transition is `409 conflict` (`comparison_ai_nothing_to_do`). An unknown series is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type EstimateComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/ai-sheet-changes/estimate`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /** Query string parameters. */
  query?: {
    only_failed?: boolean;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `estimateComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type EstimateComparisonAiSheetChangesResult = ComparisonAiEstimate;

// ------------------------------------------------------------------------------------
// estimateComparisonSheetDescription - GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description/estimate
// ------------------------------------------------------------------------------------

/**
 * Estimate the AI description of one sheet.
 *
 * «Описать этот лист…»: the sheets, images with their bytes, prompt size, model and USD estimate of describing one sheet pair, or one added or removed sheet. Computing it calls no model. A sheet pair whose comparison is `same` needs no description and is `409 conflict` (`comparison_ai_nothing_to_do`). An unknown sheet pair is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type EstimateComparisonSheetDescriptionInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}/description/estimate`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `estimateComparisonSheetDescription` (`application/json`, HTTP 200). */
export type EstimateComparisonSheetDescriptionResult = ComparisonAiEstimate;

// ------------------------------------------------------------------------------------
// estimateComparisonSpecification - GET /comparison-transitions/{comparison_transition_id}/specification/estimate
// ------------------------------------------------------------------------------------

/**
 * Estimate the comparison of the whole specifications of a transition.
 *
 * The versions to read, the images, the prompt size, the routed model and the USD estimate; a version whose specification already has a stored extraction under the same content key is `reused`. Computing it calls no model. A transition with no specification sheet is `409 conflict` (`comparison_ai_nothing_to_do`). An unknown transition is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type EstimateComparisonSpecificationInput = {
  /** Path parameters, substituted into `/comparison-transitions/{comparison_transition_id}/specification/estimate`. */
  path: {
    comparison_transition_id: ComparisonTransitionId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `estimateComparisonSpecification` (`application/json`, HTTP 200). */
export type EstimateComparisonSpecificationResult = ComparisonAiEstimate;

// ------------------------------------------------------------------------------------
// estimateRunCost - POST /runs/cost-estimate
// ------------------------------------------------------------------------------------

/**
 * Estimate selected section analysis before spend.
 *
 * Read-only cost preflight. A changed source, profile, preset, route or model makes an earlier estimate digest stale. Unmetered connections are explicit; estimates are not measured spend. With reaudit_of_run_id, version_uid must match the source Run and no executor, preset or raised-limit override is allowed: the server derives same-version/current-section/current-route execution, retaining an originally named connection. Source Run ID is bound into the estimate digest. `EXEC2-SEAL-2`: `executor_group_id` (exclusive with `executor_connection_id` and `preset_id`, with the same refusals as `startRun`) estimates a run on the group's current revision; the estimate then carries `executor_group_id`, `executor_group_revision_id`, `routing_rule_revision_id` (when a rule routed it) and the planned `pin_id`, and no `connection_revision_id`. The estimate digest binds them.
 *
 * `HOSTS-SEAL-1` (ADR-0028): while the stage layout is switched on, the estimate is for the plan a start would freeze: `billing` is `unmetered` when every cell runs on a subscription, `metered` when every cell is on an API key and `mixed` otherwise; `models` has one line per model with the digest of its rates, its access, its calls, tokens and share of the cost, and `stage_plan_digest` is the digest of the plan. `estimate_digest` binds all of them (consent v2). The explicit executor selectors are `422 validation_failed` with constraint `stage_layout_enabled`. With the layout off the estimate is what it was.
 */
export type EstimateRunCostInput = {
  /** Request body, sent as `application/json`. */
  body: RunCostEstimateRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `estimateRunCost` (`application/json`, HTTP 200). */
export type EstimateRunCostResult = RunCostEstimate;

// ------------------------------------------------------------------------------------
// estimateStageChainRun - GET /stage-link-revisions/{stage_link_revision_id}/chain-estimate
// ------------------------------------------------------------------------------------

/** Estimate Run */
export type EstimateStageChainRunInput = {
  /** Path parameters, substituted into `/stage-link-revisions/{stage_link_revision_id}/chain-estimate`. */
  path: {
    stage_link_revision_id: StageLinkRevisionId;
  };
  /** Query string parameters. */
  query?: {
    engine?: "classic" | "v3_native_text_experimental";
    stage_chain_run_id?: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `estimateStageChainRun` (`application/json`, HTTP 200). */
export type EstimateStageChainRunResult = ComparisonAiEstimate;

// ------------------------------------------------------------------------------------
// excludeComparisonUploadSet - POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/exclusion
// ------------------------------------------------------------------------------------

/**
 * Leave one set out of the batch.
 *
 * The set is excluded: its files stay in the batch as history and nothing is admitted from it. A set that is already done, or already excluded, is `409 conflict` (`comparison_set_state`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-02` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type ExcludeComparisonUploadSetInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/exclusion`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
    comparison_upload_set_id: ComparisonUploadSetId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `excludeComparisonUploadSet` (`application/json`, HTTP 200). */
export type ExcludeComparisonUploadSetResult = ComparisonProposalSet;

// ------------------------------------------------------------------------------------
// exportOptimisationProposalsCsv - GET /optimisation-passes/{optimisation_pass_id}/export.csv
// ------------------------------------------------------------------------------------

/**
 * Export Optimisation Proposals Csv
 *
 * Every proposal of the pass as a CSV file, one row each in ordinal order: the pass, the specification row's provenance, both positions, both exact unit prices, the saving (an empty cell when it is absent, never `0`) and the current decision, and, as the last two columns, `saving_percent` (`D-346`, contract 1.43.0: the share of the current unit price the proposed one saves, empty only at a zero current price) and `decision_carried_from_version` (`D-335`: the display ordinal of the earlier version the decision in force was carried over from, empty for one made directly). UTF-8 with a byte-order mark, CRLF line endings, RFC 4180 quoting; every cell that a spreadsheet would read as a formula is prefixed with an apostrophe. Computed on request from the stored rows; separate from the findings' CSV. An unknown pass is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type ExportOptimisationProposalsCsvInput = {
  /** Path parameters, substituted into `/optimisation-passes/{optimisation_pass_id}/export.csv`. */
  path: {
    optimisation_pass_id: OptimisationPassId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `exportOptimisationProposalsCsv` (`text/csv`, HTTP 200). */
export type ExportOptimisationProposalsCsvResult = Blob;

// ------------------------------------------------------------------------------------
// exportOptimisationProposalsXlsx - GET /optimisation-passes/{optimisation_pass_id}/export.xlsx
// ------------------------------------------------------------------------------------

/**
 * Export Optimisation Proposals Xlsx
 *
 * `UI-B-15` (contract 1.35.0): every proposal of the pass as a workbook with one sheet, «Предложения», one row each in ordinal order. The first column, «ID предложения», is the proposal's own identity -- the key by which `importOptimisationProposalDecisions` reads the file back, never the display number «№»; then the specification row, both positions, the exact prices and the saving (an empty cell when it is absent, never `0`), «Экономия, %» (`D-346`, contract 1.43.0: the share of the current unit price the proposed one saves, empty only at a zero current price), and the two columns an expert edits, «Решение эксперта» (`не решено`, `принято`, `отклонено` or `на доработку`) and «Комментарий», filled with the decision in force. The last column, «Перенесено из версии» (`D-335`), reads «V2» for a decision in force that was carried over from the earlier version's pass and is empty otherwise; it moves none of the columns above. Every cell is text, so one that begins with `=` is shown and not evaluated. Computed on request from the stored rows. An unknown pass is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type ExportOptimisationProposalsXlsxInput = {
  /** Path parameters, substituted into `/optimisation-passes/{optimisation_pass_id}/export.xlsx`. */
  path: {
    optimisation_pass_id: OptimisationPassId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `exportOptimisationProposalsXlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, HTTP 200). */
export type ExportOptimisationProposalsXlsxResult = Blob;

// ------------------------------------------------------------------------------------
// exportRunCsv - GET /runs/{run_id}/export.csv
// ------------------------------------------------------------------------------------

/**
 * Download the CSV for one run.
 *
 * Synchronous. Nothing is created, so there is no export resource, no export identity and nothing to poll. Repeating the request returns byte-identical bytes.
 *
 * The discriminator is the frozen `terminal_semantics.publishes_result` flag, not a hand-written state list (`OD-11`). A run whose terminal declares `publishes_result: true` - `published` or `partial` - is exported, with the degraded state carried explicitly in the `run_state` column rather than as a silent empty file. Every other state is refused with `state_transition_not_allowed`: a non-terminal run, and the terminal `failed`. `cancelled` is likewise not exportable and is unreachable in PC-01. `partial_result_not_publishable` is never emitted by this surface.
 *
 * Bytes: UTF-8 with a byte-order mark, comma delimiter, CRLF line ending, RFC 4180 quoting. A text cell is written with one leading apostrophe when a spreadsheet could read it as a formula: when the first character that is not a space, a no-break space, a byte-order mark, a zero-width character, a tab, a carriage return or a line feed is `=`, `+`, `-` or `@` (or its fullwidth form), or when the cell itself starts with a tab, a carriage return or a line feed. Every other text is written as it is, an apostrophe is never doubled, and a number or a date is never touched (`SMALL-HARDENING-02`, `R-146ax`, `D-246`, `D-253`). The column list and its order are frozen in `docs/program/P02_SEAMS.md` section 6.
 */
export type ExportRunCsvInput = {
  /** Path parameters, substituted into `/runs/{run_id}/export.csv`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `exportRunCsv` (`text/csv`, HTTP 200). */
export type ExportRunCsvResult = Blob;

// ------------------------------------------------------------------------------------
// exportRunXlsx - GET /runs/{run_id}/export.xlsx
// ------------------------------------------------------------------------------------

/**
 * Download the Excel workbook for one run.
 *
 * Synchronous, like `exportRunCsv`, and with its states and role: nothing is created, there is no export resource or identity, and repeating the request returns byte-identical bytes. An unknown run is `404`; a run whose terminal does not declare `publishes_result: true` is `409 state_transition_not_allowed`, decided on the run before anything else is read. A `partial` run is exported.
 *
 * The workbook is the W57b layout (`docs/program/dispatch/W57-PLAN.md` section B3.5): «Сводка» with the run's identity and the counts by severity (decided, else proposed) and by category, and «Замечания» with one row per finding -- № | Лист/стр. | Категория | Замечание | Рекомендация | Серьёзность (решение эксперта) | Серьёзность (предложение модели) | Норма (документ, пункт) | Цитата нормы | Решение эксперта | Комментарий | ID замечания -- and a «также найдено» row per merged member. «ID замечания» is the finding's `finding_uid` (contract 1.27.0, `R-151d`), the key `importRunDecisions` reads an edited workbook back by; a «также найдено» row leaves it empty. Standard-library writer, stored ZIP parts in a fixed order with fixed timestamps, inline strings, no formula; XML-forbidden characters become U+FFFD.
 *
 * «Лист/стр.» comes only from the version's verified portal companion: a version without one, or whose companion does not verify, is `422 storage_integrity_error` with `role: source.structured_companion`; a page number is never shown as a sheet label. The norm columns carry a finding's verified citations when the run has certified citation partitions, read through its pinned retrieval set; when they do not verify the answer is `422 required_norm_unavailable` with `reference_kind: norm_retrieval_set`, never a workbook without them. A run without citation partitions exports with the norm columns empty. Roles: `expert` (`role:expert`), as `exportRunCsv`. Added by W57B-NORMS-CATALOGUE-XLSX-01.
 */
export type ExportRunXlsxInput = {
  /** Path parameters, substituted into `/runs/{run_id}/export.xlsx`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `exportRunXlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, HTTP 200). */
export type ExportRunXlsxResult = Blob;

// ------------------------------------------------------------------------------------
// extendExecutorTaskClaim - POST /runner/tasks/{task_id}/extend
// ------------------------------------------------------------------------------------

/**
 * Extend Executor Task Claim
 *
 * `HOSTS-SEAL-1` (ADR-0028): a host agent sends an extension **only while the call has produced output** (bytes on the client's stdout or stderr, or a streamed chunk or keep-alive of an API response) in the last 120 seconds, so a hung call lets its claim lapse and the lease rule takes the task back. The answer and the refusals are unchanged.
 */
export type ExtendExecutorTaskClaimInput = {
  /** Path parameters, substituted into `/runner/tasks/{task_id}/extend`. */
  path: {
    task_id: ExecutorTaskId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `extendExecutorTaskClaim` (`application/json`, HTTP 200). */
export type ExtendExecutorTaskClaimResult = ExtendedExecutorTaskClaim;

// ------------------------------------------------------------------------------------
// failExecutorTask - POST /runner/tasks/{task_id}/fail
// ------------------------------------------------------------------------------------

/**
 * Fail Executor Task
 *
 * `HOSTS-SEAL-1` (ADR-0028): a host agent's reason is `<code>` or `<code>: <detail>` with the code matching `^[a-z][a-z0-9_]{0,63}$`: `model_not_available`, `effort_not_allowed`, `host_task_incomplete`, `image_input_unsupported`, `quota_exceeded`, `auth_failed`, `model_not_found` (the last three also take the model out of availability on the host for 15 minutes), or a fixed word of the answerer. No detail holds text of the document, of the provider's answer or a key.
 */
export type FailExecutorTaskInput = {
  /** Path parameters, substituted into `/runner/tasks/{task_id}/fail`. */
  path: {
    task_id: ExecutorTaskId;
  };
  /** Request body, sent as `application/json`. */
  body: FailExecutorTaskRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `failExecutorTask` (`application/json`, HTTP 200). */
export type FailExecutorTaskResult = ExecutorTaskAck;

// ------------------------------------------------------------------------------------
// finishComparisonAiSheetChanges - POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/finish
// ------------------------------------------------------------------------------------

/**
 * Finish an interrupted AI description of changes.
 *
 * «Досчитать»: queues the sheets of an interrupted, paused or cancelled job that have no result, under the consent the job already holds. A job with nothing left is `409 conflict` (`comparison_ai_nothing_to_do`); a job that is running is `409 conflict` (`comparison_ai_job_state`). An unknown job is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type FinishComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-ai-sheet-jobs/{comparison_ai_job_id}/finish`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `finishComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type FinishComparisonAiSheetChangesResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// finishComparisonSeries - POST /comparison-series/{comparison_series_id}/finish
// ------------------------------------------------------------------------------------

/**
 * Finish the transitions of a series that have no result.
 *
 * «Досчитать»: queues, in the same series, the transitions that have no complete result (cancelled, failed or incomplete ones), reusing what is done. A series that is queued, running or paused, or that has nothing left, is `409 conflict` (`comparison_series_state`). An unknown series is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type FinishComparisonSeriesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/finish`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `finishComparisonSeries` (`application/json`, HTTP 200). */
export type FinishComparisonSeriesResult = ComparisonSeries;

// ------------------------------------------------------------------------------------
// generateComparisonSummary - POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/summaries
// ------------------------------------------------------------------------------------

/**
 * Generate Comparison Summary
 *
 * Ask the model once, on purpose, for a summary of the approved sheet pairs of the path's (older) version and `target_version_uid`, and store the answer. This is the only operation that calls a model about a comparison; reading the comparison never does. The command recomputes the approved pairs' raw differences and their seal in its own transaction and needs them `sealed`; it builds the bounded input from the changed lines only (an input beyond the bound is refused, never shortened) and takes nothing from the client but the view. The reply is checked: every change it cites must exist; a reply that cites one that does not is stored as `rejected` (it was paid for) and returned as an answer, with no statements. The summary is stored append-only with the input digest, the prompt version, the provider mode and model identity, its statements and the span identities each cites; it never alters the raw differences, which the comparison returns exactly as computed, and it carries a fixed label saying no human reviewed it. The cost goes through the cost meter; in this release only the recorded implementation exists (`provider_mode: recorded`, `cost_basis: unmetered`), and a process in any other mode answers `503 dependency_unavailable` (`dependency: comparison_summary_model`). A missing recording is `422 analysis_input_invalid` and stores nothing. An exact repeat (same sealed input and prompt version, any key) answers the stored summary, `replayed: true`. A refusal before any call is `conflict` with `conflict_reason` `summary_evidence_not_sealed`, `summary_input_empty` or `summary_input_too_large`, or `comparison_not_available`. `expert` is required; `admin` alone is refused (`required_capability: role:expert`). While the «Сравнение версий» module is on (`AUDITMANAGER_COMPARISON_MODULES` names `versions`) this operation answers `503 dependency_unavailable` (`details.dependency: comparison_versions_module`) and writes nothing: the effective matrix is the only store of which page of one version is which page of another (`ADR-0025` decision 13; migration `0039` turned the active approvals into manual matrix edits and kept the `0035` rows as history). With the module off it works as before.
 */
export type GenerateComparisonSummaryInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/summaries`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    version_uid: VersionUid;
  };
  /** Request body, sent as `application/json`. */
  body: GenerateComparisonSummaryRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `generateComparisonSummary` (`application/json`, HTTP 201). */
export type GenerateComparisonSummaryResult = GenerateComparisonSummaryResponse;

// ------------------------------------------------------------------------------------
// generateExecutorSshKey - POST /executor-connections/{connection_id}/ssh-key
// ------------------------------------------------------------------------------------

/** Generate Executor Ssh Key */
export type GenerateExecutorSshKeyInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/ssh-key`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `generateExecutorSshKey` (`application/json`, HTTP 201). */
export type GenerateExecutorSshKeyResult = ExecutorSshKey;

// ------------------------------------------------------------------------------------
// getAssignment - GET /assignments/{assignment_uid}
// ------------------------------------------------------------------------------------

/**
 * Read one assignment with its history.
 *
 * Any one role. The assignment and every event of its append-only history, oldest first, each with its actor. An assignment the caller may not read -- an expert reading one that is not currently theirs -- is `not_found`.
 */
export type GetAssignmentInput = {
  /** Path parameters, substituted into `/assignments/{assignment_uid}`. */
  path: {
    assignment_uid: AssignmentUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getAssignment` (`application/json`, HTTP 200). */
export type GetAssignmentResult = AssignmentDetail;

// ------------------------------------------------------------------------------------
// getComparisonAiPairCheck - GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check
// ------------------------------------------------------------------------------------

/**
 * Read the latest AI check of a document set.
 *
 * The latest job of the AI check of the doubtful pairs and its counts «вопросов · пар · подсказок · против». Both are absent until a check was started. Reading starts nothing. An unknown project, or a document of another project, is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AIPAIR-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_pairs`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonAiPairCheckInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonAiPairCheck` (`application/json`, HTTP 200). */
export type GetComparisonAiPairCheckResult = ComparisonAiPairCheck;

// ------------------------------------------------------------------------------------
// getComparisonAiQueue - GET /execution/comparison-ai-queue
// ------------------------------------------------------------------------------------

/**
 * Read the AI queue of the installation.
 *
 * «Очередь «ИИ-описание изменений»»: the AI jobs of the installation that are queued, running or paused, running first, then in the order they will start (one series at a time). Reading starts nothing. Any one role (`role:admin|expert`, `R-80`). Any one role (`role:admin|expert`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-QUEUE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_launch_queue`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonAiQueueInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonAiQueue` (`application/json`, HTTP 200). */
export type GetComparisonAiQueueResult = ComparisonAiQueue;

// ------------------------------------------------------------------------------------
// getComparisonAiSheetChanges - GET /comparison-series/{comparison_series_id}/ai-sheet-changes
// ------------------------------------------------------------------------------------

/**
 * Read the AI description of changes of a series.
 *
 * The latest job and, per transition, the progress «Листов / Изм. / Вопр. / Ошибок / Проверить / Обращ.», the tokens and the time. Reading starts nothing and calls no model. An unknown series is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/ai-sheet-changes`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type GetComparisonAiSheetChangesResult = ComparisonAiSheetChanges;

// ------------------------------------------------------------------------------------
// getComparisonLaunchQueue - GET /projects/{project_uid}/comparison-launch-queue
// ------------------------------------------------------------------------------------

/**
 * Read the launch queue of a project.
 *
 * «Очередь запуска»: «готово N из M · пропущено K · ошибок E», its state, and the entries in the order they run. A project has one queue. Reading starts nothing. An unknown project is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-QUEUE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_launch_queue`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonLaunchQueueInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-launch-queue`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonLaunchQueue` (`application/json`, HTTP 200). */
export type GetComparisonLaunchQueueResult = ComparisonLaunchQueue;

// ------------------------------------------------------------------------------------
// getComparisonMatrix - GET /projects/{project_uid}/documents/{document_uid}/comparison-matrix
// ------------------------------------------------------------------------------------

/**
 * Read the effective matrix of a document set.
 *
 * The effective matrix of the versions of a document set (`ADR-0025` decision 3): rows are sheet identities, columns are the versions in the current comparison order, and a cell is matched (with its confidence `high`, `medium`, `group`, `manual` or `ai` and the flags `split`, `duplicate`, `scan` and `bridge`), unmatched (with candidates and a reason) or absent. The algorithm comes first, then accepted AI links (labelled, never an expert act), then manual edits, and manual wins. `revision` is what an edit batch names as its base. `state` is `absent` while nothing is built, `building` while profiles or the matrix are computed, `stale` when the build no longer matches the current order or profiles (`stale_reasons` says which) and `failed` when the last build failed; `revision`, `columns`, `rows` and `counts` are absent while no build exists. Edits made against another order that no longer apply are listed in `orphaned_edit_ids` and are never applied silently. The read starts nothing and changes nothing. An unknown project, or a document of another project, is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-MATRIX-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_matrix`) until the lane wired it.
 */
export type GetComparisonMatrixInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-matrix`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonMatrix` (`application/json`, HTTP 200). */
export type GetComparisonMatrixResult = ComparisonMatrix;

// ------------------------------------------------------------------------------------
// getComparisonOverview - GET /projects/{project_uid}/comparison-overview
// ------------------------------------------------------------------------------------

/**
 * Read the overview of the comparison of a project.
 *
 * The overview behind «Проекты и этапы»: for every document set of the project («комплект (шифр)»; the designation is metadata and never an identity) the number of versions, the state and figures of the seven steps (`upload`, `profile`, `matrix`, `ai_pairs`, `series`, `ai_changes`, `report`) and the next step the chip proposes; the totals «N версий · M переходов», the counters «Все / Ждут действия / Идут / Ошибки / Готовы» and the batches that are still being uploaded. The steps of waves after the first report `not_started` or `not_applicable`. Reading it starts nothing. An unknown project is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-VC-OVERVIEW-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_overview`) until the lane wired it.
 */
export type GetComparisonOverviewInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-overview`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonOverview` (`application/json`, HTTP 200). */
export type GetComparisonOverviewResult = ComparisonOverview;

// ------------------------------------------------------------------------------------
// getComparisonQueueSummary - GET /execution/comparison-queue
// ------------------------------------------------------------------------------------

/**
 * Read the comparison work queue.
 *
 * The read-only «Сравнение» block of «Очередь» (`ADR-0025` decision 6): the module set the deployment serves, whether execution is paused for the whole installation, and the comparison work items by state and by kind. Comparison work claims only when no section run is claimable, yields between items and honours the pause and a module that is off. Any one role (`role:admin|expert`, `R-80`). Served by `CMP-VC-OVERVIEW-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_overview`) until the lane wired it.
 */
export type GetComparisonQueueSummaryInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonQueueSummary` (`application/json`, HTTP 200). */
export type GetComparisonQueueSummaryResult = ComparisonQueueSummary;

// ------------------------------------------------------------------------------------
// getComparisonReport - GET /comparison-reports/{comparison_report_id}
// ------------------------------------------------------------------------------------

/**
 * Read a report.
 *
 * State, stage, kind, source, the per-transition progress (for an analytic report «Анализ», «Проверка», «Факты», «Предупреждения»; for a client report «Отбор», «Пунктов», «Вопросов»), the estimate of a draft or the job with the usage of a started one, and the stored files. Reading starts nothing. An unknown report is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonReportInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonReport` (`application/json`, HTTP 200). */
export type GetComparisonReportResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// getComparisonSeries - GET /comparison-series/{comparison_series_id}
// ------------------------------------------------------------------------------------

/**
 * Read a series with its transitions.
 *
 * One series with its transitions in the order of the versions: for each, the older and the newer version, the state, the sheet pairs done of the total, the counts (`compared`, `same`, `zones_only`, `different`, `style_only`, `needs_review`, `added`, `removed`, `failed`) and the deterministic verdict as an ordered list of codes. A transition whose pairs rest on an accepted AI link counts them in `ai_dependent` (`ADR-0025` decision 3). An unknown series is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type GetComparisonSeriesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonSeries` (`application/json`, HTTP 200). */
export type GetComparisonSeriesResult = ComparisonSeries;

// ------------------------------------------------------------------------------------
// getComparisonSheetDescription - GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description
// ------------------------------------------------------------------------------------

/**
 * Read the AI description of a sheet pair.
 *
 * The stored description behind the panel «Изменения в листе»: the state (one of the eleven labels), the changes with object, «Было» / «стало», place, «Неясно» and the tier of each value, «Требует уточнения», «Заявлено проектировщиком в разрешении», what was left out of the summary, the coverage, the diagnostics and the number of earlier descriptions. It works for an added or removed sheet too. Reading calls no model; a sheet that was never described is `not_processed`, which is not the same as no changes. The description is model output not confirmed by an engineer, and a recorded answer is marked `recorded`. An unknown sheet pair is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonSheetDescriptionInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}/description`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonSheetDescription` (`application/json`, HTTP 200). */
export type GetComparisonSheetDescriptionResult = ComparisonSheetDescription;

// ------------------------------------------------------------------------------------
// getComparisonSheetPair - GET /comparison-sheet-pairs/{comparison_sheet_pair_id}
// ------------------------------------------------------------------------------------

/**
 * Read one sheet pair with its raw deterministic evidence.
 *
 * One sheet pair of a transition with everything the viewer shows: the channels (`geometry`, `color`, `text`, `text_coverage`, `zones`, `annotations`, `warnings`, `spec_positions`, each `checked` with its difference count, `unchecked` with a reason, or `not_applicable`), the list of differences with their class, layer and box on the canvas of the older page, the text changes with the numbers that changed («было → стало»), the service-zone notes («Исчезновение предупреждения не подтверждает согласования.») and «Как сравнивалось». This is raw evidence: an AI layer never rewrites it (`ADR-0025` decision 3). `result_id` is the content-keyed result the pair uses; pairs of equal content within a project share it (decision 15). A pair with no result yet has `state` `queued`, `computing` or `failed`. An unknown pair is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type GetComparisonSheetPairInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonSheetPair` (`application/json`, HTTP 200). */
export type GetComparisonSheetPairResult = ComparisonSheetPair;

// ------------------------------------------------------------------------------------
// getComparisonSheetPairSpecPositions - GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/spec-positions
// ------------------------------------------------------------------------------------

/**
 * Read the positions that changed on a sheet pair.
 *
 * «Спецификация по позициям»: the position changes that fall on the pages of the sheet pair, deterministic, from the positions of the whole specification of each version (a page change alone is not a change). No model is called. An unknown sheet pair is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonSheetPairSpecPositionsInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}/spec-positions`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonSheetPairSpecPositions` (`application/json`, HTTP 200). */
export type GetComparisonSheetPairSpecPositionsResult = ComparisonSheetPairSpecPositions;

// ------------------------------------------------------------------------------------
// getComparisonSpecification - GET /comparison-transitions/{comparison_transition_id}/specification
// ------------------------------------------------------------------------------------

/**
 * Read the specification comparison of a transition.
 *
 * Method, state and phase, the sheets A and B, the coverage of each side, the totals and the reason a side is incomplete or the comparison failed. Reading starts nothing. An unknown transition is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetComparisonSpecificationInput = {
  /** Path parameters, substituted into `/comparison-transitions/{comparison_transition_id}/specification`. */
  path: {
    comparison_transition_id: ComparisonTransitionId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonSpecification` (`application/json`, HTTP 200). */
export type GetComparisonSpecificationResult = ComparisonSpecification;

// ------------------------------------------------------------------------------------
// getComparisonUpload - GET /comparison-uploads/{comparison_upload_id}
// ------------------------------------------------------------------------------------

/**
 * Read an upload batch with its files.
 *
 * The batch, its state and the state of every declared file with the parts staged so far, which is what a resumable client needs: it sends the parts that are missing. An unknown batch is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type GetComparisonUploadInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonUpload` (`application/json`, HTTP 200). */
export type GetComparisonUploadResult = ComparisonUpload;

// ------------------------------------------------------------------------------------
// getComparisonUploadProposal - GET /comparison-uploads/{comparison_upload_id}/proposal
// ------------------------------------------------------------------------------------

/**
 * Read the grouping proposal of an upload batch.
 *
 * The proposed grouping of the batch's files into document sets by designation (the «шифр» read from the stamp, metadata an expert confirms and never an identity), the proposed order in each set, the stage and section proposal and the warnings the reader noticed. Nothing becomes a version until the user confirms a set. A scan without text is compared as an image only and says so as a warning. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type GetComparisonUploadProposalInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/proposal`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getComparisonUploadProposal` (`application/json`, HTTP 200). */
export type GetComparisonUploadProposalResult = ComparisonUploadProposal;

// ------------------------------------------------------------------------------------
// getDashboardSummary - GET /dashboard
// ------------------------------------------------------------------------------------

/**
 * One aggregate read across the whole deployment: all four dashboard panels.
 *
 * Documents per project, findings by verdict, run activity and spend, and the per-section breakdown -- computed server-side over the whole deployment, never walked client-side (`R-44`). Without a parameter it is the fixed shape of the deployment right now; it is not a filtered query over the data three narrower operations already answer (`listProjects`, `listDecisions`, `listRuns`). The one filter it takes is `project_uid` (`UI-PARITY-P0A`): the product's header names the project the expert is working in, and with it every one of the four panels is restricted to that project **by exactly the definitions it has without it** -- the same joins, the same grouping and the same spend rule (a Run's model calls and the comparison calls made for that project's work), so a count is the whole-deployment count minus every row of every other project. `documents_by_project` is then the one project's row. A `project_uid` naming no project is `not_found`, never a summary of zeros; a malformed one is `validation_failed`. No counter is redefined. Absent is not empty throughout: every `Verdict` and `RunState` is present even at zero, every one of the fifteen sections is present even with no documents, and the unclassified documents are their own row. The section panel carries each section's documents by audit state (`audit_counts`) and the findings of their result runs (`finding_count`), and `awaiting_decision_findings` counts the findings still awaiting a decision on the current versions (`UI-PARITY-P0B`); `findings_by_verdict` stays the all-time count of every finding of every run (`R-150q`).
 */
export type GetDashboardSummaryInput = {
  /** Query string parameters. */
  query?: {
    /** Restrict all four panels to this project. Absent means the whole deployment. */
    project_uid?: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getDashboardSummary` (`application/json`, HTTP 200). */
export type GetDashboardSummaryResult = DashboardSummary;

// ------------------------------------------------------------------------------------
// getDecisionMemoryCase - GET /decision-memory/cases/{case_id}
// ------------------------------------------------------------------------------------

/**
 * Get Decision Memory Case
 *
 * `DECISION-MEMORY-01` phase M2: one case -- its summary, the model's finding and recommendation as they stood, the evidence quotes with their page geometry, the certified normative references, the crop images it references (a binding to an existing Blob), every captured decision with the expert's own comment, and the history of its standing. **A forgotten case answers its tombstone only**: `content` is `null`, the lists are empty and no decision carries a comment; the `forget` event carries the digest of what was forgotten. An unknown case is `404`. `role:admin|expert`.
 */
export type GetDecisionMemoryCaseInput = {
  /** Path parameters, substituted into `/decision-memory/cases/{case_id}`. */
  path: {
    case_id: DecisionMemoryCaseId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getDecisionMemoryCase` (`application/json`, HTTP 200). */
export type GetDecisionMemoryCaseResult = DecisionMemoryCase;

// ------------------------------------------------------------------------------------
// getDecisionMemoryStatus - GET /decision-memory/status
// ------------------------------------------------------------------------------------

/**
 * Get Decision Memory Status
 *
 * `DECISION-MEMORY-01` phase M2: how many cases and decisions the memory holds, by standing and data class, and the installation settings in force -- `data_class`, what a case captured now is (`test` until an operator journals `real`), and `training_use`, whether the training export may run (`off` until the owner's permission is recorded). The settings are changed by an operator tool, not by this surface. `role:admin`.
 */
export type GetDecisionMemoryStatusInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getDecisionMemoryStatus` (`application/json`, HTTP 200). */
export type GetDecisionMemoryStatusResult = DecisionMemoryStatus;

// ------------------------------------------------------------------------------------
// getDocumentVersion - GET /versions/{version_uid}
// ------------------------------------------------------------------------------------

/** Read one published document version. */
export type GetDocumentVersionInput = {
  /** Path parameters, substituted into `/versions/{version_uid}`. */
  path: {
    version_uid: VersionUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getDocumentVersion` (`application/json`, HTTP 200). */
export type GetDocumentVersionResult = DocumentVersion;

// ------------------------------------------------------------------------------------
// getEffectiveVendorLists - GET /projects/{project_uid}/vendor-lists
// ------------------------------------------------------------------------------------

/**
 * Get Effective Vendor Lists
 *
 * All fifteen sections' vendor lists as they apply to the project, in section order. For each: `source` `project` (the project's own latest revision, mode `list`), `global` (the administrator's latest) or `none`; the `effective` revision; and the latest revision of each scope. An unknown project is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type GetEffectiveVendorListsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/vendor-lists`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getEffectiveVendorLists` (`application/json`, HTTP 200). */
export type GetEffectiveVendorListsResult = EffectiveVendorLists;

// ------------------------------------------------------------------------------------
// getExecutionDispatch - GET /execution/dispatch
// ------------------------------------------------------------------------------------

/**
 * Get Dispatch
 *
 * Whether the installation's execution dispatch is paused, and since when: the state `setExecutionPaused` writes. `UI-PARITY-P0E` (contract 1.20.0, ruling `R-151f`): the top strip shows the pause state without reading the queue. Readable by `expert` and `admin`; the `viewer` role is refused (`R-150w`), as for the queue.
 */
export type GetExecutionDispatchInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutionDispatch` (`application/json`, HTTP 200). */
export type GetExecutionDispatchResult = ExecutionDispatchStatus;

// ------------------------------------------------------------------------------------
// getExecutorAgentInstall - GET /executor-connections/{connection_id}/agent-installs/{install_id}
// ------------------------------------------------------------------------------------

/**
 * Get Executor Agent Install
 *
 * One install session of the universal agent (`EXEC2-SEAL-1`): its state, the host-key fingerprint the worker observed once it has, and the sanitised reason it failed. An administrator reads it; the install names a host and a user. `404 not_found` for an install that does not belong to this connection.
 */
export type GetExecutorAgentInstallInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/agent-installs/{install_id}`. */
  path: {
    connection_id: ExecutorConnectionId;
    install_id: ExecutorAgentInstallId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorAgentInstall` (`application/json`, HTTP 200). */
export type GetExecutorAgentInstallResult = ExecutorAgentInstall;

// ------------------------------------------------------------------------------------
// getExecutorConnection - GET /executor-connections/{connection_id}
// ------------------------------------------------------------------------------------

/** Get Executor Connection */
export type GetExecutorConnectionInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorConnection` (`application/json`, HTTP 200). */
export type GetExecutorConnectionResult = ExecutorConnectionDetail;

// ------------------------------------------------------------------------------------
// getExecutorGroup - GET /executor-groups/{group_id}
// ------------------------------------------------------------------------------------

/**
 * Get Executor Group
 *
 * Read one group and every revision of it, newest first (`EXEC2-SEAL-2`). `404 not_found` for a group that does not exist. Readable by every role, as `listExecutorConnections` is (`EXEC2-GROUP-STORE-01`).
 */
export type GetExecutorGroupInput = {
  /** Path parameters, substituted into `/executor-groups/{group_id}`. */
  path: {
    group_id: ExecutorGroupId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorGroup` (`application/json`, HTTP 200). */
export type GetExecutorGroupResult = ExecutorGroupDetail;

// ------------------------------------------------------------------------------------
// getExecutorGroupCapacity - GET /executor-groups/{group_id}/capacity
// ------------------------------------------------------------------------------------

/**
 * Get Executor Group Capacity
 *
 * The capacity of a group's current revision as dispatch would see it right now (`EXEC2-SEAL-2`, ADR-0026 decisions 1 and 14): per member its snapshot, its connection's current revision and occupancy and whether it is eligible and, if not, why; and the group's capacity, units in use and pending work. Derived at read time, stored nowhere. `404 not_found`; Readable by every role, as `listExecutorConnections` is (`EXEC2-GROUP-STORE-01`).
 */
export type GetExecutorGroupCapacityInput = {
  /** Path parameters, substituted into `/executor-groups/{group_id}/capacity`. */
  path: {
    group_id: ExecutorGroupId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorGroupCapacity` (`application/json`, HTTP 200). */
export type GetExecutorGroupCapacityResult = ExecutorGroupCapacity;

// ------------------------------------------------------------------------------------
// getExecutorHost - GET /executor-hosts/{host_id}
// ------------------------------------------------------------------------------------

/**
 * Get Executor Host
 *
 * `HOSTS-SEAL-1`: one server, as `listExecutorHosts` lists it. `404 not_found` for an unknown host. `role:admin|expert`.
 */
export type GetExecutorHostInput = {
  /** Path parameters, substituted into `/executor-hosts/{host_id}`. */
  path: {
    host_id: ExecutorHostId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorHost` (`application/json`, HTTP 200). */
export type GetExecutorHostResult = ExecutorHost;

// ------------------------------------------------------------------------------------
// getExecutorHostAgentInstall - GET /executor-hosts/{host_id}/agent-installs/{install_id}
// ------------------------------------------------------------------------------------

/**
 * Get Executor Host Agent Install
 *
 * `HOSTS-SEAL-1`: one install session of a host, as `getExecutorAgentInstall` reads one of a connection. `role:admin`.
 */
export type GetExecutorHostAgentInstallInput = {
  /** Path parameters, substituted into `/executor-hosts/{host_id}/agent-installs/{install_id}`. */
  path: {
    host_id: ExecutorHostId;
    install_id: ExecutorAgentInstallId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorHostAgentInstall` (`application/json`, HTTP 200). */
export type GetExecutorHostAgentInstallResult = ExecutorAgentInstall;

// ------------------------------------------------------------------------------------
// getExecutorHostDetails - GET /executor-hosts/{host_id}/details
// ------------------------------------------------------------------------------------

/**
 * Get Executor Host Details
 *
 * `HOSTS-SEAL-1`: «Подробнее» of a server -- its slots and their use, each provider found on it with its login and, for every model, why it cannot be used (`host_disabled`, `host_offline`, `login_required`, `model_not_verified`, `model_cooling_down`), and the tasks running on it now (run, stage, since when). Derived at read time. `role:admin`.
 */
export type GetExecutorHostDetailsInput = {
  /** Path parameters, substituted into `/executor-hosts/{host_id}/details`. */
  path: {
    host_id: ExecutorHostId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorHostDetails` (`application/json`, HTTP 200). */
export type GetExecutorHostDetailsResult = ExecutorHostDetails;

// ------------------------------------------------------------------------------------
// getExecutorTaskContext - POST /runner/tasks/{task_id}/context
// ------------------------------------------------------------------------------------

/**
 * Get Executor Task Context
 *
 * `CRIT-SEAL-50` (plan-v5 section 3.2): the agent behind the claim of a `review:main` task asks once per kind for the decisions of experts on findings like the task's own. The stand answers by the `input_id` of the task's `context_request` and journals what it gave (no text). **Idempotent by (task, kind)**: a repeat returns the same answer and spends no budget. While the night encoder is the only one the answer is `status: unavailable, reason: until_move`. The agent appends the data to the prompt as reference, never as ground, and echoes `context_sha256` in `submitExecutorTaskAnswer`; an error here never fails the task. Runner token only; no role.
 */
export type GetExecutorTaskContextInput = {
  /** Path parameters, substituted into `/runner/tasks/{task_id}/context`. */
  path: {
    task_id: ExecutorTaskId;
  };
  /** Request body, sent as `application/json`. */
  body: ExecutorTaskContextRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorTaskContext` (`application/json`, HTTP 200). */
export type GetExecutorTaskContextResult = ExecutorTaskContext;

// ------------------------------------------------------------------------------------
// getExecutorTaskImage - GET /runner/tasks/{task_id}/images/{blob_id}
// ------------------------------------------------------------------------------------

/** Get Executor Task Image */
export type GetExecutorTaskImageInput = {
  /** Path parameters, substituted into `/runner/tasks/{task_id}/images/{blob_id}`. */
  path: {
    blob_id: RunnerImageBlobId;
    task_id: ExecutorTaskId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExecutorTaskImage` (`image/png`, HTTP 200). */
export type GetExecutorTaskImageResult = Blob;

// ------------------------------------------------------------------------------------
// getExtendedRunReview - GET /runs/{run_id}/extended-review
// ------------------------------------------------------------------------------------

/** Get Extended Run Review */
export type GetExtendedRunReviewInput = {
  /** Path parameters, substituted into `/runs/{run_id}/extended-review`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getExtendedRunReview` (`application/json`, HTTP 200). */
export type GetExtendedRunReviewResult = ExtendedRunReview;

// ------------------------------------------------------------------------------------
// getFinding - GET /findings/{finding_uid}
// ------------------------------------------------------------------------------------

/** Read one finding with its observation, evidence and provenance. */
export type GetFindingInput = {
  /** Path parameters, substituted into `/findings/{finding_uid}`. */
  path: {
    finding_uid: FindingUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getFinding` (`application/json`, HTTP 200). */
export type GetFindingResult = FindingDetail;

// ------------------------------------------------------------------------------------
// getFindingPrecedents - GET /findings/{finding_uid}/precedents
// ------------------------------------------------------------------------------------

/**
 * Get Finding Precedents
 *
 * `CRIT-SEAL-50` (plan-v5 sections 2.5 and 3.4): the card of a finding -- its label, at most two hints, the similar cases and the possible norms (paragraphs the run already holds). `404 not_found` for an unknown finding. `role:admin|expert`; the viewer is denied.
 */
export type GetFindingPrecedentsInput = {
  /** Path parameters, substituted into `/findings/{finding_uid}/precedents`. */
  path: {
    finding_uid: FindingUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getFindingPrecedents` (`application/json`, HTTP 200). */
export type GetFindingPrecedentsResult = FindingPrecedents;

// ------------------------------------------------------------------------------------
// getMe - GET /me
// ------------------------------------------------------------------------------------

/**
 * Read the signed-in account.
 *
 * The account the presented credential names: its login, names, role set and state. Reachable by an account still on a default credential and by an incomplete profile, because it is how a client learns either state; every operation that is not this one, `updateMyProfile` or `changePassword` answers an incomplete profile with `permission_denied` and `required_capability: profile_completed`. Nothing is created or changed.
 */
export type GetMeInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getMe` (`application/json`, HTTP 200). */
export type GetMeResult = Account;

// ------------------------------------------------------------------------------------
// getNormDocument - GET /norm-documents/{norm_document_id}
// ------------------------------------------------------------------------------------

/**
 * Get Norm Document
 *
 * One norm document of a snapshot, with its attribution (NORM-Q04) and whether its source PDF is available through a confirmed custody binding. Roles: any one role (`role:admin|expert|viewer`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
 */
export type GetNormDocumentInput = {
  /** Path parameters, substituted into `/norm-documents/{norm_document_id}`. */
  path: {
    norm_document_id: NormDocumentId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getNormDocument` (`application/json`, HTTP 200). */
export type GetNormDocumentResult = NormDocument;

// ------------------------------------------------------------------------------------
// getProductVersion - GET /system/version
// ------------------------------------------------------------------------------------

/**
 * Read the running product version.
 *
 * Requires an active account with a complete profile. product_version comes from VERSION, build_id identifies this API process's content, and contract_version remains the API contract version.
 */
export type GetProductVersionInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getProductVersion` (`application/json`, HTTP 200). */
export type GetProductVersionResult = ProductVersion;

// ------------------------------------------------------------------------------------
// getProject - GET /projects/{project_uid}
// ------------------------------------------------------------------------------------

/**
 * Get Project
 *
 * `UI-PARITY-P0N` (contract 1.29.0): one project by its identity, exactly as `listProjects` lists it -- its name, creation time, document count and audit counters -- so a screen that names its project need not find it on a page of the listing. An unknown project is `404`. Any role that may list projects (`role:admin|expert|viewer`).
 */
export type GetProjectInput = {
  /** Path parameters, substituted into `/projects/{project_uid}`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getProject` (`application/json`, HTTP 200). */
export type GetProjectResult = Project;

// ------------------------------------------------------------------------------------
// getRunNormReferences - GET /runs/{run_id}/norm-references
// ------------------------------------------------------------------------------------

/**
 * Get Run Norm References
 *
 * «Нормативные ссылки»: the normative documents (СП, ГОСТ, СНиП, СанПиН, ВСН, federal laws and government acts) cited in the run's saved text, each resolved against the norms snapshot the run pinned as `in_corpus`, `newer_edition`, `older_edition_only` (the corpus holds only an earlier edition than the one cited), `not_in_corpus` or `not_recognised`, with the pages each occurs on and the corpus document it points at. Computed per request by the same resolver the W57b rule uses; publishes no finding, proposes no severity and calls no model. A precondition that does not hold is `state` (`snapshot_not_pinned`, `text_unavailable`, `too_many_citations`), never an empty list; the corpus documents whose designation the parser cannot read are listed as `unrecognised`; pages without a text layer are `unread_pages`. An unknown run is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type GetRunNormReferencesInput = {
  /** Path parameters, substituted into `/runs/{run_id}/norm-references`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getRunNormReferences` (`application/json`, HTTP 200). */
export type GetRunNormReferencesResult = RunNormReferences;

// ------------------------------------------------------------------------------------
// getRunPrecedents - GET /runs/{run_id}/precedents
// ------------------------------------------------------------------------------------

/**
 * Get Run Precedents
 *
 * `CRIT-SEAL-50` (plan-v5 sections 2.3 and 6): what the «Прецеденты» pass gave the findings of a run -- the neutral label of each, and the items with `label: cancel_suggested` are the queue «Рекомендовано снять». `404 not_found` for an unknown run. `role:admin|expert`; the viewer («Наблюдатель») is denied.
 */
export type GetRunPrecedentsInput = {
  /** Path parameters, substituted into `/runs/{run_id}/precedents`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getRunPrecedents` (`application/json`, HTTP 200). */
export type GetRunPrecedentsResult = RunPrecedents;

// ------------------------------------------------------------------------------------
// getRunStages - GET /runs/{run_id}/stages
// ------------------------------------------------------------------------------------

/**
 * Get Run Stages
 *
 * `HOSTS-SEAL-2` (ADR-0028, plan section 9.4): the data of the window «Этапы анализа раздела». For each chip of the run -- `preparation`, `text`, `blocks`, `cross_check`, `merge`, `norms`, `review`, `correction`, in that order, only those the run has -- the code stage ids it covers, its **plan** (the cells the run froze in its `stage_plan`: role, model, effort, access and the server the cell is bound to; for a run that froze none, one line from its binding) and its **facts**: the state; the first and last call (or the stage result's times); the calls succeeded, failed and retried; the input and output tokens, the part of them served by a subscription and the cost; the last error code; and the batches planned and completed where the extended review keeps them. The facts come from the stage results, the extended review artifact and the call journal; a call journalled before migration `0062` has no `stage_key` and is placed by its extended phase. `role:admin|expert|viewer`: the viewer reads the run's stages but never the server or the access (`R-150w`), which are absent from the answer. `404 not_found` for an unknown run.
 */
export type GetRunStagesInput = {
  /** Path parameters, substituted into `/runs/{run_id}/stages`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getRunStages` (`application/json`, HTTP 200). */
export type GetRunStagesResult = RunStages;

// ------------------------------------------------------------------------------------
// getRunStartReadiness - POST /runs/start-readiness
// ------------------------------------------------------------------------------------

/**
 * Get Run Start Readiness
 *
 * `HOSTS-SEAL-1` (ADR-0028): what the one button «Запустить» would do for this version, writing nothing and calling no model. A read by POST like `estimateRunCost`, with the same body. With the layout off the route is `legacy` and the answer is the estimate as before. With it on: the plan a start would freeze, every cell with the access it would run with (a subscription when an agent with one is on line, else an API key) and the reasons it cannot be served, the total access (`subscription`, `api` or `mixed`), the digest and amount of the estimate and, when every cell is on a subscription, an estimate of 0 whose confirmation is the press of the button. `ready` is false while any cell has no server. The explicit executor selectors of the body are `422 validation_failed` while the layout is on. `role:admin|expert`.
 */
export type GetRunStartReadinessInput = {
  /** Request body, sent as `application/json`. */
  body: RunCostEstimateRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getRunStartReadiness` (`application/json`, HTTP 200). */
export type GetRunStartReadinessResult = RunStartReadiness;

// ------------------------------------------------------------------------------------
// getRunStatus - GET /runs/{run_id}
// ------------------------------------------------------------------------------------

/**
 * Read run state and per-stage state.
 *
 * The polling target. `state` is the contract run state; `stages` carries one entry per stage the run scheduled, with the `StageResult` status vocabulary. A client stops polling on any terminal state. `estimated_finish_at` (`UI-A-65`, contract 1.40.0) is the same estimate the queue shows for the run's job, present only while the run is being worked on.
 */
export type GetRunStatusInput = {
  /** Path parameters, substituted into `/runs/{run_id}`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getRunStatus` (`application/json`, HTTP 200). */
export type GetRunStatusResult = RunStatus;

// ------------------------------------------------------------------------------------
// getSectionSpecification - GET /sections/{section_code}/specification
// ------------------------------------------------------------------------------------

/**
 * Get Section Specification
 *
 * «Оптимизация разделов»: the Form-7 rows of every project whose document set's current version an expert confirmed in the section, each row priced from its own project's current price list as `matched`, `ambiguous` or `unmatched` with its reason (or `price_list_missing` when the project has none). The section code is a filter, not an identity: every row carries its project, document set, version, page, sheet and line span, rows are never merged across projects, and totals exist per project and per currency only -- there is no section total. A current version nobody classified is listed in `excluded`; one confirmed in another section never appears. `project_uid` narrows the answer to one project (an unknown one is `404`); `q` keeps the rows whose own text contains it and never changes a total; rows are paged (`offset`, `limit`, `next_offset`). A set without a published run or a saved text layer is its own `state`. Over a bound (projects scanned, member sets read, rows held) the answer is `200` with `state: section_too_large`, the bound in `limit_reason`, the membership listed and no rows; narrow to one project. A section code outside the fifteen is `404`. Nothing is written. Any one role, `role:admin|expert|viewer`.
 */
export type GetSectionSpecificationInput = {
  /** Path parameters, substituted into `/sections/{section_code}/specification`. */
  path: {
    section_code: ProjectSection;
  };
  /** Query string parameters. */
  query?: {
    /** Specification rows per answer. */
    limit?: number;
    /** Position in the list of rows that survive the search. */
    offset?: number;
    project_uid?: ProjectUid;
    /** Text a row's position, description, group, unit or note contains, ignoring case, `ё` and runs of spaces. Narrows the rows only, never a project's totals. */
    q?: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getSectionSpecification` (`application/json`, HTTP 200). */
export type GetSectionSpecificationResult = SectionSpecification;

// ------------------------------------------------------------------------------------
// getSpecificationPrices - GET /projects/{project_uid}/documents/{document_uid}/specification-prices
// ------------------------------------------------------------------------------------

/**
 * Get Specification Prices
 *
 * «Спецификация и цены»: the specification rows of the document set's current version, read deterministically from its newest published run's saved text layer, each matched to the project's current price-list revision as `matched`, `ambiguous` or `unmatched` with its reason (code or mark first, then the normalised name, in the same unit; never a fuzzy guess). The version must be classified by an expert in one of the fifteen sections; the section is reported in the answer and does not change how the rows are read or priced. A precondition that does not hold is `state` (`version_unclassified`, `price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large`) with the facts read so far; the value `section_not_ar` stays in the enum so that no value is removed, and is no longer produced for a confirmed section; a path naming no such set is `404`. A price and an amount appear only on a matched row with a numeric quantity; totals are per currency over those rows only, with every other row counted by its reason. Rows are paged (`offset`, `limit`, `next_offset`); counts and totals cover every row. Nothing is written. Any one role, `role:admin|expert|viewer`.
 */
export type GetSpecificationPricesInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/specification-prices`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** Specification rows per answer. */
    limit?: number;
    /** Position in the list of specification rows. */
    offset?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getSpecificationPrices` (`application/json`, HTTP 200). */
export type GetSpecificationPricesResult = SpecificationPrices;

// ------------------------------------------------------------------------------------
// getStageAssembly - GET /stage-assemblies/{stage_assembly_id}
// ------------------------------------------------------------------------------------

/** Get Assembly */
export type GetStageAssemblyInput = {
  /** Path parameters, substituted into `/stage-assemblies/{stage_assembly_id}`. */
  path: {
    stage_assembly_id: StageAssemblyId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageAssembly` (`application/json`, HTTP 200). */
export type GetStageAssemblyResult = StageAssembly;

// ------------------------------------------------------------------------------------
// getStageChainBatch - GET /stage-chain-batches/{stage_chain_batch_id}
// ------------------------------------------------------------------------------------

/** Get Batch */
export type GetStageChainBatchInput = {
  /** Path parameters, substituted into `/stage-chain-batches/{stage_chain_batch_id}`. */
  path: {
    stage_chain_batch_id: StageChainBatchId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageChainBatch` (`application/json`, HTTP 200). */
export type GetStageChainBatchResult = StageChainBatch;

// ------------------------------------------------------------------------------------
// getStageChainRun - GET /stage-chain-runs/{stage_chain_run_id}
// ------------------------------------------------------------------------------------

/** Get Stage Chain Run */
export type GetStageChainRunInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageChainRun` (`application/json`, HTTP 200). */
export type GetStageChainRunResult = StageChainRun;

// ------------------------------------------------------------------------------------
// getStageChangeCard - GET /stage-change-cards/{stage_change_card_id}
// ------------------------------------------------------------------------------------

/** Get Card */
export type GetStageChangeCardInput = {
  /** Path parameters, substituted into `/stage-change-cards/{stage_change_card_id}`. */
  path: {
    stage_change_card_id: StageChangeCardId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageChangeCard` (`application/json`, HTTP 200). */
export type GetStageChangeCardResult = StageChangeCard;

// ------------------------------------------------------------------------------------
// getStageChangeJournal - GET /stage-chain-runs/{stage_chain_run_id}/journal
// ------------------------------------------------------------------------------------

/** Get Journal */
export type GetStageChangeJournalInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/journal`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Query string parameters. */
  query?: {
    grouping?: "designation" | "section" | "system";
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageChangeJournal` (`application/json`, HTTP 200). */
export type GetStageChangeJournalResult = StageChangeJournal;

// ------------------------------------------------------------------------------------
// getStageModelLayout - GET /model-layout
// ------------------------------------------------------------------------------------

/**
 * Get Stage Model Layout
 *
 * `HOSTS-SEAL-1` (ADR-0028): the layout of models over the analysis stages -- for each row (text, blocks, cross-check, norms, critic, refinement) and role the model and the effort (no answer limit and no timeout: `LIMITS-01`) -- the revision in force, the revisions newest first, the switch and its journal, and the cells whose model no server can serve now. An expert reads it; only an administrator changes it. `role:admin|expert`; the viewer is denied.
 */
export type GetStageModelLayoutInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageModelLayout` (`application/json`, HTTP 200). */
export type GetStageModelLayoutResult = StageModelLayout;

// ------------------------------------------------------------------------------------
// getStagePair - GET /stage-pairs/{stage_pair_id}
// ------------------------------------------------------------------------------------

/** Get Stage Pair */
export type GetStagePairInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStagePair` (`application/json`, HTTP 200). */
export type GetStagePairResult = StagePair;

// ------------------------------------------------------------------------------------
// getStageProfileText - GET /comparison-page-profiles/{comparison_page_profile_id}/stage-text
// ------------------------------------------------------------------------------------

/** Get Profile Text */
export type GetStageProfileTextInput = {
  /** Path parameters, substituted into `/comparison-page-profiles/{comparison_page_profile_id}/stage-text`. */
  path: {
    comparison_page_profile_id: ComparisonPageProfileId;
  };
  /** Query string parameters. */
  query?: {
    query?: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageProfileText` (`application/json`, HTTP 200). */
export type GetStageProfileTextResult = StageProfileText;

// ------------------------------------------------------------------------------------
// getStageQuality - GET /stage-quality
// ------------------------------------------------------------------------------------

/**
 * Get Stage Quality
 *
 * `CRIT-SEAL-53` (plan-v5 section 6, owner ruling Н7): the quality table of the stage plan -- for each cell of the plan and section, how many findings experts decided and how many they accepted; the blocks ensemble is one row of its own, and the model is the cell's. Counts, not a score; no cell with no decision appears, and the table changes no routing. `role:admin`.
 */
export type GetStageQualityInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageQuality` (`application/json`, HTTP 200). */
export type GetStageQualityResult = StageQualityTable;

// ------------------------------------------------------------------------------------
// getStageSheetMap - GET /stage-pairs/{stage_pair_id}/sheet-map
// ------------------------------------------------------------------------------------

/** Get Stage Sheet Map */
export type GetStageSheetMapInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/sheet-map`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageSheetMap` (`application/json`, HTTP 200). */
export type GetStageSheetMapResult = StageLinkRevision;

// ------------------------------------------------------------------------------------
// getStageSheetMapRevision - GET /stage-link-revisions/{stage_link_revision_id}
// ------------------------------------------------------------------------------------

/** Get Stage Sheet Map Revision */
export type GetStageSheetMapRevisionInput = {
  /** Path parameters, substituted into `/stage-link-revisions/{stage_link_revision_id}`. */
  path: {
    stage_link_revision_id: StageLinkRevisionId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageSheetMapRevision` (`application/json`, HTTP 200). */
export type GetStageSheetMapRevisionResult = StageLinkRevision;

// ------------------------------------------------------------------------------------
// getStageSynthesis - GET /stage-chain-runs/{stage_chain_run_id}/synthesis
// ------------------------------------------------------------------------------------

/** Get Synthesis */
export type GetStageSynthesisInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/synthesis`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageSynthesis` (`application/json`, HTTP 200). */
export type GetStageSynthesisResult = StageAiSynthesisPage;

// ------------------------------------------------------------------------------------
// getStageUpload - GET /stage-uploads/{stage_upload_id}
// ------------------------------------------------------------------------------------

/** Get Stage Upload */
export type GetStageUploadInput = {
  /** Path parameters, substituted into `/stage-uploads/{stage_upload_id}`. */
  path: {
    stage_upload_id: StageUploadId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getStageUpload` (`application/json`, HTTP 200). */
export type GetStageUploadResult = StageUpload;

// ------------------------------------------------------------------------------------
// getUser - GET /users/{user_uid}
// ------------------------------------------------------------------------------------

/**
 * Read one account.
 *
 * Requires `admin`. One account, archived or not.
 */
export type GetUserInput = {
  /** Path parameters, substituted into `/users/{user_uid}`. */
  path: {
    user_uid: UserUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getUser` (`application/json`, HTTP 200). */
export type GetUserResult = Account;

// ------------------------------------------------------------------------------------
// getVectorControl - GET /vector-control
// ------------------------------------------------------------------------------------

/**
 * Get Vector Control
 *
 * `CRIT-SEAL-50` (plan-v5 section 5): the pause of the vectors and the state of the night window. The queued and poisoned jobs are shown to an administrator only. `role:admin|expert`; the viewer is denied.
 */
export type GetVectorControlInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getVectorControl` (`application/json`, HTTP 200). */
export type GetVectorControlResult = VectorControl;

// ------------------------------------------------------------------------------------
// getVersionBlocks - GET /versions/{version_uid}/blocks
// ------------------------------------------------------------------------------------

/**
 * Read the page-by-page block index derived for one published version.
 *
 * Keyed by `version_uid`, not by `run_id`. `page_geometry_extraction` carries no model and no provider reference, so its output is a deterministic re-derivation of the source bytes and the published text layer -- identical across every run of this version that reaches the stage successfully. Addressing it by run would ask a caller to already hold a run identity to read a fact about the document.
 *
 * An unknown `version_uid` is `404`. A version that exists but whose most recent successful run never reached `page_geometry_extraction` -- or has no run at all -- answers `200` with `status: "not_produced"` and `blocks: []`; that is a different fact from a version whose geometry was produced and genuinely has no blocks, which answers `200` with `status: "produced"` and `blocks: []`. The two are the same bytes for `blocks` and different bytes for `status`, and a caller reads `status` to tell them apart -- never the length of `blocks`.
 *
 * This operation does not carry crops. `page_geometry_extraction` also publishes a page-crop manifest (`geometry.page_crops`); since `W55B-SEAL-01` it lists the crops this product cuts for the IMAGE blocks of a portal bundle under a non-empty `crop_policy`. That manifest and the portal blocks it describes are served by `listVersionPortalBlocks` and `streamVersionPortalBlockCrop`, not by this operation, which stays the text-line block index.
 */
export type GetVersionBlocksInput = {
  /** Path parameters, substituted into `/versions/{version_uid}/blocks`. */
  path: {
    version_uid: VersionUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getVersionBlocks` (`application/json`, HTTP 200). */
export type GetVersionBlocksResult = VersionBlockIndex;

// ------------------------------------------------------------------------------------
// getVersionPageProfile - GET /page-profiles/{comparison_page_profile_id}
// ------------------------------------------------------------------------------------

/**
 * Read the deterministic profile of one page.
 *
 * The profile the worker computed and stored for the page: its status (`ready`, `needs_review` or `refused`, with a typed `reason`), the stamp fields, counts and the content key. The API never calls PDFium (`ADR-0025` decision 9). A profile that does not exist is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-PROFILE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: version_pages`) and nothing is read or written.
 */
export type GetVersionPageProfileInput = {
  /** Path parameters, substituted into `/page-profiles/{comparison_page_profile_id}`. */
  path: {
    comparison_page_profile_id: ComparisonPageProfileId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getVersionPageProfile` (`application/json`, HTTP 200). */
export type GetVersionPageProfileResult = VersionPageProfile;

// ------------------------------------------------------------------------------------
// getVersionPageSpecPositions - GET /page-profiles/{comparison_page_profile_id}/spec-positions
// ------------------------------------------------------------------------------------

/**
 * Read the positions of a specification page.
 *
 * Part A, deterministic: whether the page is a specification sheet and, when it is, the positions read from the page's words and vector lines (a table by GOST 21.110: columns by the vertical rules of the header, rows by the horizontal rules; every value verbatim, an ambiguous row flagged and never guessed). No model is called. An unknown page profile is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type GetVersionPageSpecPositionsInput = {
  /** Path parameters, substituted into `/page-profiles/{comparison_page_profile_id}/spec-positions`. */
  path: {
    comparison_page_profile_id: ComparisonPageProfileId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getVersionPageSpecPositions` (`application/json`, HTTP 200). */
export type GetVersionPageSpecPositionsResult = ComparisonSpecPage;

// ------------------------------------------------------------------------------------
// getVersionSectionReview - GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/section-review
// ------------------------------------------------------------------------------------

/**
 * Get Version Section Review
 *
 * The fifteen section choices for one version, each with the suggestion evidence its file name and recognised text carry (or `null`) and whether a text profile is registered for it (`executable`), plus the persisted classification or `null`, and the classification's history (`revisions`, oldest first: the original confirmation, then each correction with its expert, time and reason). Display input only: nothing here confirms a section or starts a run. Any one role, `role:admin|expert|viewer`.
 */
export type GetVersionSectionReviewInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/section-review`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    version_uid: VersionUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getVersionSectionReview` (`application/json`, HTTP 200). */
export type GetVersionSectionReviewResult = SectionReview;

// ------------------------------------------------------------------------------------
// getWorkSchedule - GET /work-schedule
// ------------------------------------------------------------------------------------

/**
 * Get Work Schedule
 *
 * `UI-PARITY-P0P` (contract 1.31.0, rulings `R-151x`, `R-152a`…`R-152d`): one month of «График работ» -- the days (Saturday and Sunday off unless the administrator decided otherwise), and for each active expert the month's plan (`plan_is_default` when the stored default applies), the documents that became «Проверено экспертом» in the month credited to the author of their last verdict (`done`, `fact`) and the absent days. An administrator reads every active expert; an expert reads their own row. `role:admin|expert`.
 */
export type GetWorkScheduleInput = {
  /** Query string parameters. */
  query: {
    /** The month, `YYYY-MM`. */
    month: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getWorkSchedule` (`application/json`, HTTP 200). */
export type GetWorkScheduleResult = WorkScheduleMonth;

// ------------------------------------------------------------------------------------
// getWorkScheduleReserve - GET /work-schedule/reserve
// ------------------------------------------------------------------------------------

/**
 * Get Work Schedule Reserve
 *
 * `UI-PARITY-P0P` (rulings `R-150y`, `R-152e`, `R-152f`): «Календарь запаса» -- each active expert's open assignments of «Диспетчер» with their planned date (absent: «без даты»), over `days` days from `start`, and the calendar of those days. No daily limit. An administrator reads every expert; an expert their own. `role:admin|expert`.
 */
export type GetWorkScheduleReserveInput = {
  /** Query string parameters. */
  query: {
    /** How many days from `start`. */
    days?: number;
    /** The first day of the reserve shown. */
    start: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getWorkScheduleReserve` (`application/json`, HTTP 200). */
export type GetWorkScheduleReserveResult = WorkScheduleReserve;

// ------------------------------------------------------------------------------------
// importComparisonZip - POST /projects/{project_uid}/comparison-zip-uploads
// ------------------------------------------------------------------------------------

/** Import Comparison Zip */
export type ImportComparisonZipInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-zip-uploads`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/zip`. */
  body: Blob;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
  /** Additional declared request headers. */
  headers?: {
    'X-Archive-Name'?: string;
  };
};

/** Success body of `importComparisonZip` (`application/json`, HTTP 201). */
export type ImportComparisonZipResult = ComparisonUpload;

// ------------------------------------------------------------------------------------
// importOptimisationProposalDecisions - POST /optimisation-passes/{optimisation_pass_id}/decision-imports
// ------------------------------------------------------------------------------------

/**
 * Import Optimisation Proposal Decisions
 *
 * `UI-B-15` (contract 1.35.0): load back the pass's workbook as `exportOptimisationProposalsXlsx` produced it, with «Решение эксперта» and «Комментарий» edited, at most 10 MiB. Only our export is read: a workbook without a «Предложения» sheet naming the columns «ID предложения», «Решение эксперта» and «Комментарий» is `422 validation_failed` (`field: file`, `constraint: not_our_export`), as is a file that is not a readable XLSX (`unreadable`), is larger (`too_large`) or has more than 20 000 rows (`too_many_rows`); nothing is recorded then. Rows are matched by the proposal's identity, never by «№», and only proposals of this pass. A row whose decision differs from the one in force appends an `accept`, `reject` or `revise` event carrying the row's comment (`revise` requires one), authored by the caller exactly as `decideOptimisationProposal` would; «не решено» over a decision in force appends its withdrawal (`revoke`); the same decision with a new comment appends a new event; a blank decision cell keeps the decision in force. Every row naming an ID or a decision is reported, in sheet order, as `recorded`, `unchanged` or `refused` with a `reason`: `no_proposal_id`, `duplicate_proposal`, `unknown_proposal`, `unknown_decision` (not one of the four labels the export writes), `comment_required` or `comment_too_long`. The proposal's identity is reported only for a proposal of the pass. An unknown pass is `404`. An exact repeat of the `Idempotency-Key` answers the stored report and appends nothing; the same key with another file, pass or caller is `409 idempotency_key_reuse`. `expert` only (`admin` alone is `permission_denied`).
 */
export type ImportOptimisationProposalDecisionsInput = {
  /** Path parameters, substituted into `/optimisation-passes/{optimisation_pass_id}/decision-imports`. */
  path: {
    optimisation_pass_id: OptimisationPassId;
  };
  /** Request body, sent as `multipart/form-data`. */
  body: ImportProposalDecisionsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `importOptimisationProposalDecisions` (`application/json`, HTTP 200). */
export type ImportOptimisationProposalDecisionsResult = ProposalDecisionImportReport;

// ------------------------------------------------------------------------------------
// importRunDecisions - POST /runs/{run_id}/decision-imports
// ------------------------------------------------------------------------------------

/**
 * Import Run Decisions
 *
 * `UI-PARITY-P0L` (contract 1.27.0, ruling `R-151d`): load back the run's workbook as `exportRunXlsx` produced it, with «Решение эксперта» and «Комментарий» edited, at most 10 MiB. Only our export is read: a workbook without a «Замечания» sheet naming the columns «ID замечания», «Решение эксперта» and «Комментарий» is `422 validation_failed` (`field: file`, `constraint: not_our_export`), as is a file that is not a readable XLSX (`unreadable`), is larger (`too_large`) or has more than 20 000 rows (`too_many_rows`); nothing is recorded then. Rows are matched by `finding_uid`, never by «№». A row whose decision changes appends an `accept` or `reject` event carrying the row's comment, a row whose comment alone changes appends a `comment` event, both authored by the caller exactly as `appendDecision` would; the severity columns are not read and nothing is revoked. Every row naming an ID or a decision is reported, in sheet order, as `recorded`, `unchanged` or `refused` with a `reason`: `no_finding_uid`, `duplicate_finding`, `unknown_finding`, `finding_not_in_run`, `unknown_decision` (not one of the four labels the export writes) or `not_importable` («не решено» or «нужен ручной разбор» over another verdict). `finding_uid` is reported only for a published finding. An unknown run is `404`. An exact repeat of the `Idempotency-Key` answers the stored report and appends nothing; the same key with another file, run or caller is `409 idempotency_key_reuse`. `expert` only.
 */
export type ImportRunDecisionsInput = {
  /** Path parameters, substituted into `/runs/{run_id}/decision-imports`. */
  path: {
    run_id: RunId;
  };
  /** Request body, sent as `multipart/form-data`. */
  body: ImportRunDecisionsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `importRunDecisions` (`application/json`, HTTP 200). */
export type ImportRunDecisionsResult = DecisionImportReport;

// ------------------------------------------------------------------------------------
// issueExecutorEnrollment - POST /executor-connections/{connection_id}/enrollments
// ------------------------------------------------------------------------------------

/**
 * Issue Executor Enrollment
 *
 * Issue the one-time enrollment grant of a universal agent for a `pull` connection (`EXEC2-SEAL-1`, ADR-0026 decisions 4, 6 and 9). The grant's secret, the package version and its sha256, and the copyable install command are **shown once**: only a one-way hash of the secret is stored and no operation returns it again. A grant is single-use, expires after 15 minutes and is bound to this connection; issuing a new one revokes the previous unredeemed grant. Issuing one for a connection that already has an online agent is how an agent moves to another host. Refusals use existing codes: `403 permission_denied` for a caller without `admin`; `404 not_found`; `409 conflict` with `conflict_reason` `connection_archived`, `no_revision`, or `enrollment_shown_once` (a repeat of the same Idempotency-Key: the secret was not stored and cannot be shown again); `422 validation_failed` with field `kind` and constraint `kind_not_pull`; `503 dependency_unavailable` with dependency `agent_package` (the image holds no package to install) or `public_origin` (the stand's configured public origin, `AUDITMANAGER_PUBLIC_ORIGIN`, is absent or not a plain `https://host[:port]`; the install command's origin comes from that setting alone and is never guessed from the request).
 *
 * `HOSTS-SEAL-1` (contract 1.45.0): this operation stays the form for a `pull` connection. A server is connected with `issueExecutorHostEnrollment`, which takes no connection and no model.
 */
export type IssueExecutorEnrollmentInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/enrollments`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `issueExecutorEnrollment` (`application/json`, HTTP 201). */
export type IssueExecutorEnrollmentResult = IssuedExecutorEnrollment;

// ------------------------------------------------------------------------------------
// issueExecutorHostEnrollment - POST /executor-hosts/enrollments
// ------------------------------------------------------------------------------------

/**
 * Issue Executor Host Enrollment
 *
 * `HOSTS-SEAL-1` (ADR-0028): connect a server -- create the host and issue the one-time grant of its agent, with no model. Same document as `issueExecutorEnrollment`: the secret, the package version and digest and the copyable install command are **shown once**, only a one-way hash is stored; the grant is single-use, expires after 15 minutes and is bound to the new host (`enrollment.host_id`). Redeeming it (`redeemExecutorEnrollment`) yields a host token. `409 conflict` with `conflict_reason` `enrollment_shown_once` for a repeat of the same key (the secret was not stored). `422 validation_failed` for a name another live server has. `503 dependency_unavailable` with dependency `agent_package` or `public_origin`, as `issueExecutorEnrollment`. `role:admin`, `Idempotency-Key` required.
 */
export type IssueExecutorHostEnrollmentInput = {
  /** Request body, sent as `application/json`. */
  body: IssueExecutorHostEnrollmentRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `issueExecutorHostEnrollment` (`application/json`, HTTP 201). */
export type IssueExecutorHostEnrollmentResult = IssuedExecutorEnrollment;

// ------------------------------------------------------------------------------------
// issueRunnerToken - POST /executor-connections/{connection_id}/runner-tokens
// ------------------------------------------------------------------------------------

/** Issue Runner Token */
export type IssueRunnerTokenInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/runner-tokens`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /** Request body, sent as `application/json`. */
  body: IssueRunnerTokenRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `issueRunnerToken` (`application/json`, HTTP 201). */
export type IssueRunnerTokenResult = IssuedRunnerToken;

// ------------------------------------------------------------------------------------
// issueToken - POST /auth/token
// ------------------------------------------------------------------------------------

/**
 * Exchange a login and a password for a bearer credential.
 *
 * The only operation on this surface that is reachable without a credential, because it is the one that hands one out: its `security` is the empty requirement, which overrides the document root for this operation and for no other.
 *
 * **What this operation says about the credential it returns: nothing.** The response carries an opaque string and how long it stays valid. Its structure, what it encodes, and where the deployment got it are the deployment's own, are not described anywhere in this document, and are never parsed by a caller -- the same rule that keeps `bearerFormat` off `components.securitySchemes.bearerAuth`. A deployment that replaces a static string with something else changes no operation here.
 *
 * Nothing is created and nothing is changed, so there is no idempotency key: a repeat of the same exchange is a second exchange, not a replay of the first. The edge in front of this surface counts the exchange per client address (six a minute, with a burst of ten) and answers `rate_limited` (`429`) itself, before the operation is reached; like the edge's own body-size refusal, that answer is not a response of the operation and is not declared here.
 */
export type IssueTokenInput = {
  /** Request body, sent as `application/json`. */
  body: IssueTokenRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `issueToken` (`application/json`, HTTP 200). */
export type IssueTokenResult = IssueTokenResponse;

// ------------------------------------------------------------------------------------
// listAcceptedOptimisationProposals - GET /optimisation-proposals/accepted
// ------------------------------------------------------------------------------------

/**
 * List Accepted Optimisation Proposals
 *
 * The optimisation proposals whose decision in force is an acceptance, across every pass, newest acceptance first (`cursor`, `limit`), each with where it belongs -- project, document set, version and the version's section -- and the acceptance itself (who, when, the comment). A proposal whose latest decision is a rejection, a revision request or a withdrawal, or that nobody decided, is not listed. `project_uid` narrows to one project and `section_code` to the versions an expert confirmed in that section; neither is a parent, so an empty result is a `200` with no rows. `total` is the number of proposals the filters match, on every page. `D-346` (contract 1.43.0): each row carries `saving_percent`, the share of the current unit price the proposed one saves -- the figure `listOptimisationProposals` states, present where `saving` is `null` and absent only at a zero current price. Any one role, `role:admin|expert|viewer`.
 */
export type ListAcceptedOptimisationProposalsInput = {
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
    project_uid?: ProjectUid;
    section_code?: ProjectSection;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listAcceptedOptimisationProposals` (`application/json`, HTTP 200). */
export type ListAcceptedOptimisationProposalsResult = AcceptedOptimisationProposalPage;

// ------------------------------------------------------------------------------------
// listAnalysisPresets - GET /analysis/presets
// ------------------------------------------------------------------------------------

/**
 * List the analysis presets.
 *
 * The named presets of how a run starts (`R-146av`, `ANALYSIS-PRESETS-01`). A run start selects exactly one setting per run, the executor connection, so a preset is a name plus that connection; the cost ceiling is a process-wide setting and no threshold is an input of a start, so a preset holds neither. Each item is the preset's current revision; every earlier revision is kept and a run records the revision it started with. Archived presets are listed after the active ones. Any one role, `role:admin|expert|viewer`.
 */
export type ListAnalysisPresetsInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listAnalysisPresets` (`application/json`, HTTP 200). */
export type ListAnalysisPresetsResult = AnalysisPresetList;

// ------------------------------------------------------------------------------------
// listAnalysisProfiles - GET /analysis/profiles
// ------------------------------------------------------------------------------------

/**
 * List the analysis profile of every section.
 *
 * The analysis profiles the server routes runs through: all fifteen sections in the project-structure order, each with its registered text profile -- identities, version, status (`draft` or `reviewed`), prompt-bundle and profile hashes and the legacy source of a ported package -- or `null` when no profile is registered, which run start refuses (АР now has a draft original-source text profile). Read-only: no operation edits a profile or its status. Any one role, `role:admin|expert|viewer`.
 */
export type ListAnalysisProfilesInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listAnalysisProfiles` (`application/json`, HTTP 200). */
export type ListAnalysisProfilesResult = AnalysisProfileList;

// ------------------------------------------------------------------------------------
// listAssignments - GET /assignments
// ------------------------------------------------------------------------------------

/**
 * List assignments.
 *
 * Any one role. An administrator reads every assignment (`mine=true` narrows to the ones currently given to them); an expert reads only the assignments currently given to them, whatever `mine` says. `status` and `project_uid` narrow the list; newest first, ordered by `(created_at, assignment_uid)`. `total` is the number of assignments the caller may read under every filter of the request, and `overview` gives each of the five statuses with its count over the scope filters only (`project_uid`, `mine` and what the caller may read), so each count is what choosing that status would list.
 */
export type ListAssignmentsInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    mine?: boolean;
    project_uid?: ProjectUid;
    status?: AssignmentStatus;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listAssignments` (`application/json`, HTTP 200). */
export type ListAssignmentsResult = AssignmentPage;

// ------------------------------------------------------------------------------------
// listAuthEvents - GET /auth-events
// ------------------------------------------------------------------------------------

/**
 * List the access journal.
 *
 * Requires `admin`. The append-only journal of sign-ins and what changes an account's access, newest first: `sign_in_succeeded`, `sign_in_blocked` (a refused attempt that started a cooling-off period, at most one per account per period -- refusals that start none and attempts on an unknown login are not journalled), `password_changed`, `password_reset`, `role_granted`, `role_revoked` and `sessions_ended`. An account is named by identity and by its label now; the journal never holds a password, a token, an address or a login as typed. The cursor is the last event's identity.
 */
export type ListAuthEventsInput = {
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listAuthEvents` (`application/json`, HTTP 200). */
export type ListAuthEventsResult = AuthEventPage;

// ------------------------------------------------------------------------------------
// listComparisonAiLinks - GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-links
// ------------------------------------------------------------------------------------

/**
 * List the accepted AI links of a document set.
 *
 * The accepted AI links, newest first (`ADR-0025` decisions 3 and 14): model answers that the validator accepted, shown labelled «ИИ» and never an expert act. Each binds the algorithmic build it answered and the cell state it answered (`unmatched` or `doubtful`) and is `applied` only while that cell is still in that state, otherwise `superseded`. The table is read-only here; wave C2 writes it, so the list is empty until then. An unknown project, or a document of another project, is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-MATRIX-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_matrix`) until the lane wired it.
 */
export type ListComparisonAiLinksInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-ai-links`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonAiLinks` (`application/json`, HTTP 200). */
export type ListComparisonAiLinksResult = ComparisonAiLinkList;

// ------------------------------------------------------------------------------------
// listComparisonAiPairHints - GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-hints
// ------------------------------------------------------------------------------------

/**
 * List the answers and hints of the AI check of pairs.
 *
 * The answers and hints per matrix cell, newest first: the question, the decision (`link_accepted` or a `hint_*` value, `none`, `answer_mismatch`, `failed`, `medium_*`), the page it concerns, the page «вероятно стр. N», the candidates, the confidence, the accepted link a `link_accepted` decision wrote and whether the question was asked of a matrix build that is no longer the latest. The page is addressed by `cursor` and `limit`. Reading starts nothing. An unknown project, or a document of another project, is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AIPAIR-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_pairs`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ListComparisonAiPairHintsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-hints`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonAiPairHints` (`application/json`, HTTP 200). */
export type ListComparisonAiPairHintsResult = ComparisonAiPairHintPage;

// ------------------------------------------------------------------------------------
// listComparisonMatrixEdits - GET /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits
// ------------------------------------------------------------------------------------

/**
 * List the manual edit history of a document set.
 *
 * The append-only history of manual matrix edits, newest event first, each numbered `edit_no` from 1 without a gap. An event is a `link`, an `unlink`, a `mark_absent` or an `undo` that names the edit it reverses; `source` is `expert` for an edit made through `applyComparisonMatrixEdits` and `migrated_sheet_link` for an approved sheet pairing of `approveSheetPairing` that migration `0039` turned into an edit (`ADR-0025` decision 13; the `0035` ids are in `provenance` and the `0035` rows stay as immutable history). `status` is `applied`, `undone` or `orphaned`. An unknown project, or a document of another project, is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-MATRIX-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_matrix`) until the lane wired it.
 */
export type ListComparisonMatrixEditsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonMatrixEdits` (`application/json`, HTTP 200). */
export type ListComparisonMatrixEditsResult = ComparisonMatrixEditList;

// ------------------------------------------------------------------------------------
// listComparisonReports - GET /comparison-series/{comparison_series_id}/reports
// ------------------------------------------------------------------------------------

/**
 * List the reports of a series.
 *
 * The report history of the series, newest first, each with its state, stage, per-transition progress, usage and downloads. A deleted report is not listed. The page is addressed by `cursor` and `limit`. An unknown series is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ListComparisonReportsInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/reports`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonReports` (`application/json`, HTTP 200). */
export type ListComparisonReportsResult = ComparisonReportPage;

// ------------------------------------------------------------------------------------
// listComparisonReviewSheets - GET /comparison-transitions/{comparison_transition_id}/review-sheets
// ------------------------------------------------------------------------------------

/**
 * List the sheets of a transition to review.
 *
 * The «Проверить» list: the sheets where the AI found no change but the comparison left marks, and the added and removed single sheets of the transition, each with its description state, in the order of the matrix rows. The page is addressed by `cursor` and `limit`. An unknown transition is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ListComparisonReviewSheetsInput = {
  /** Path parameters, substituted into `/comparison-transitions/{comparison_transition_id}/review-sheets`. */
  path: {
    comparison_transition_id: ComparisonTransitionId;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonReviewSheets` (`application/json`, HTTP 200). */
export type ListComparisonReviewSheetsResult = ComparisonReviewSheetPage;

// ------------------------------------------------------------------------------------
// listComparisonSeries - GET /projects/{project_uid}/documents/{document_uid}/comparison-series
// ------------------------------------------------------------------------------------

/**
 * List the series of a document set.
 *
 * The series of a document set, newest first, without their transitions: the state, the order and matrix they ran on, how many transitions have a result and, when the stored input digests no longer match the current order, matrix or profiles, `stale_reasons` («Сохранённая сводка для прежнего порядка версий»). An unknown project, or a document of another project, is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type ListComparisonSeriesInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-series`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonSeries` (`application/json`, HTTP 200). */
export type ListComparisonSeriesResult = ComparisonSeriesPage;

// ------------------------------------------------------------------------------------
// listComparisonSheetDescriptionHistory - GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description-history
// ------------------------------------------------------------------------------------

/**
 * List the earlier descriptions of a sheet pair.
 *
 * «История (N)»: the descriptions of the sheet pair, newest first, each with its state, counts, model and prompt version. The page is addressed by `cursor` and `limit`. An unknown sheet pair is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ListComparisonSheetDescriptionHistoryInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}/description-history`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonSheetDescriptionHistory` (`application/json`, HTTP 200). */
export type ListComparisonSheetDescriptionHistoryResult = ComparisonSheetDescriptionHistory;

// ------------------------------------------------------------------------------------
// listComparisonSheetPairs - GET /comparison-transitions/{comparison_transition_id}/sheet-pairs
// ------------------------------------------------------------------------------------

/**
 * List the sheet pairs of a transition.
 *
 * The sheet pairs of one transition in the order of the matrix rows: the older and the newer page (either absent for an added or removed sheet), the state, the status (`same`, `same_zones_changed`, `different`, `needs_review`, `added`, `removed` or `unmatched`), the link confidence and flags, the forcing reasons, the eight channels, the permit reconciliation and the parts coverage. `status` keeps one status and `only_changes` keeps every status but `same`. The members that carry the raw evidence (`canvas`, `differences`, `text_changes`, `service_notes`, `how_compared`) are absent here and present on `getComparisonSheetPair`. An unknown transition is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type ListComparisonSheetPairsInput = {
  /** Path parameters, substituted into `/comparison-transitions/{comparison_transition_id}/sheet-pairs`. */
  path: {
    comparison_transition_id: ComparisonTransitionId;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    only_changes?: boolean;
    status?: ComparisonSheetStatus;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonSheetPairs` (`application/json`, HTTP 200). */
export type ListComparisonSheetPairsResult = ComparisonSheetPairPage;

// ------------------------------------------------------------------------------------
// listComparisonSpecificationChanges - GET /comparison-transitions/{comparison_transition_id}/specification/changes
// ------------------------------------------------------------------------------------

/**
 * List the changes of a transition's specification.
 *
 * The changes of the whole-specification comparison in the order it lists them (changed, removed, added, unclear, renumbered), optionally of one `kind`. A group unresolved in either version is not compared line by line and is described by the sheet AI instead. The page is addressed by `cursor` and `limit`. An unknown transition is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ListComparisonSpecificationChangesInput = {
  /** Path parameters, substituted into `/comparison-transitions/{comparison_transition_id}/specification/changes`. */
  path: {
    comparison_transition_id: ComparisonTransitionId;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    kind?: ComparisonSpecChangeKind;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonSpecificationChanges` (`application/json`, HTTP 200). */
export type ListComparisonSpecificationChangesResult = ComparisonSpecChangePage;

// ------------------------------------------------------------------------------------
// listComparisonSpecifications - GET /comparison-series/{comparison_series_id}/specifications
// ------------------------------------------------------------------------------------

/**
 * List the specification comparisons of a series.
 *
 * The block «Полные спецификации (СО)»: per transition that has a specification, the method («полное сравнение» or «листовой ИИ»), the specification sheets of the older and the newer version, the coverage, the totals «изменено / +добавлено / −удалено / ?неясно» and the reason. The page is addressed by `cursor` and `limit`. An unknown series is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ListComparisonSpecificationsInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/specifications`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonSpecifications` (`application/json`, HTTP 200). */
export type ListComparisonSpecificationsResult = ComparisonSpecificationPage;

// ------------------------------------------------------------------------------------
// listComparisonUploads - GET /projects/{project_uid}/comparison-uploads
// ------------------------------------------------------------------------------------

/**
 * List the project's upload batches.
 *
 * The project's batches, newest first, without their files, so that an interrupted upload can be found and resumed after a reload. An unknown project is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-02` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type ListComparisonUploadsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-uploads`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonUploads` (`application/json`, HTTP 200). */
export type ListComparisonUploadsResult = ComparisonUploadPage;

// ------------------------------------------------------------------------------------
// listComparisonVersionOrders - GET /projects/{project_uid}/documents/{document_uid}/comparison-version-orders
// ------------------------------------------------------------------------------------

/**
 * List the revisions of the comparison order of a document set.
 *
 * The revisions, newest first, of the order in which the versions of one document set are compared. The order never changes the documents' ordinal that runs and finding carry-over use (`D-5`). An unknown project or document is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_version_orders`) and nothing is read or written.
 */
export type ListComparisonVersionOrdersInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-version-orders`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listComparisonVersionOrders` (`application/json`, HTTP 200). */
export type ListComparisonVersionOrdersResult = ComparisonVersionOrderList;

// ------------------------------------------------------------------------------------
// listDecisionHistory - GET /findings/{finding_uid}/decisions
// ------------------------------------------------------------------------------------

/**
 * Read the decision history of one finding, oldest first.
 *
 * Ordered by `(recorded_at, decision_id)`, which is a total order and is stable across pages. The server's row sequence is never exposed, in a field or inside a cursor.
 */
export type ListDecisionHistoryInput = {
  /** Path parameters, substituted into `/findings/{finding_uid}/decisions`. */
  path: {
    finding_uid: FindingUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listDecisionHistory` (`application/json`, HTTP 200). */
export type ListDecisionHistoryResult = DecisionEventPage;

// ------------------------------------------------------------------------------------
// listDecisionMemoryCases - GET /decision-memory/cases
// ------------------------------------------------------------------------------------

/**
 * List Decision Memory Cases
 *
 * `DECISION-MEMORY-01` phase M2 (contract 1.44.0): the cases of the expert decision memory -- the copy of what an expert saw and said when a decision was taken, kept after the project and the document are gone. Newest capture first (`cursor`, `limit`). Filters, all optional: `section_code` (as of capture), `category`, `verdict` (the latest decision's), `status` (`active`, `withdrawn`, `forgotten`), `data_class` (`test` or `real`, fixed at capture) and `origin_project_uid` (an identity that may resolve nowhere any more). A case is **history, not a verdict in force**: while the source finding exists the ledger decides. `role:admin|expert`.
 */
export type ListDecisionMemoryCasesInput = {
  /** Query string parameters. */
  query?: {
    category?: string;
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    data_class?: "test" | "real";
    /** Page size. */
    limit?: number;
    origin_project_uid?: ProjectUid;
    section_code?: string;
    status?: "active" | "withdrawn" | "forgotten";
    verdict?: "accepted" | "rejected";
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listDecisionMemoryCases` (`application/json`, HTTP 200). */
export type ListDecisionMemoryCasesResult = DecisionMemoryCasePage;

// ------------------------------------------------------------------------------------
// listDecisionPatterns - GET /decision-memory/patterns
// ------------------------------------------------------------------------------------

/**
 * List Decision Patterns
 *
 * `CRIT-SEAL-53` (plan-v5 section 3.7, owner ruling Н4): the failure patterns -- a refusing comment of the representative case of a group of refusals in one section, proposed by an algorithm and approved by an expert. Newest proposal first; `status` and `section_code` are optional filters, `limit` cuts `items` (`total` counts every match). Only an `approved` pattern reaches hint P1. `role:admin|expert`; the viewer is denied.
 */
export type ListDecisionPatternsInput = {
  /** Query string parameters. */
  query?: {
    /** Page size. */
    limit?: number;
    section_code?: string;
    status?: "proposed" | "approved" | "rejected" | "suspended";
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listDecisionPatterns` (`application/json`, HTTP 200). */
export type ListDecisionPatternsResult = DecisionPatternList;

// ------------------------------------------------------------------------------------
// listDecisions - GET /decisions
// ------------------------------------------------------------------------------------

/**
 * Read the decision journal across findings, newest first.
 *
 * Every expert decision this deployment has recorded, in one listing, with the finding context each event was recorded against. `listDecisionHistory` answers *what was decided about this finding*; this answers *what has been decided*, which no operation could answer before and which a client could otherwise reach only by walking every run and every finding.
 *
 * **It is a projection and creates nothing.** `ADR-0012` holds: the current verdict, the reason aggregates and the knowledge-base views are rebuildable projections over the append-only ledger. Every property of `DecisionRecord` is rebuildable from `expert_decision_event`, `finding`, `finding_observation` and the `finding_current_verdict` projection, and this operation is the only place they are read together.
 *
 * Ordered by `(recorded_at, decision_id)` **descending** - the newest decision first, as `listProjects` orders projects - and that is a total order, stable across pages. The server's row sequence is never exposed, in a field or inside a cursor.
 *
 * `category` and `verdict` filter on the **finding**, exactly as they do on `listRunFindings`: the category of the finding the event was recorded against, and the verdict that now stands for it. Neither filters on the event. `project_uid` (`UI-PARITY-P0A`) filters on the finding in the same way: the finding must belong to that project. It is a filter and not a parent, so a project nothing was decided in -- or one that does not exist -- is an empty page. `total` is the number of entries that match all the filters given, on every page of the listing and not the number on this page. There is no parent identity in the path, so an empty journal is an empty page and never `not_found`.
 */
export type ListDecisionsInput = {
  /** Query string parameters. */
  query?: {
    /** Restrict the page to one finding category. */
    category?: FindingCategory;
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    /** Restrict the page to decisions on findings of this project. Absent means no project filter. */
    project_uid?: ProjectUid;
    /** Restrict the page to findings whose current projected verdict is this value. */
    verdict?: Verdict;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listDecisions` (`application/json`, HTTP 200). */
export type ListDecisionsResult = DecisionRecordPage;

// ------------------------------------------------------------------------------------
// listDocumentTags - GET /projects/{project_uid}/document-tags
// ------------------------------------------------------------------------------------

/**
 * List Document Tags
 *
 * `UI-PARITY-P0H` (contract 1.23.0, ruling `R-151e`): every tag the project's documents in use carry, in case-insensitive order, with how many documents carry it; archived documents are not counted. The tag filter of the project page reads it, so it offers every tag and not those of one page. A product read: `expert`, `admin` and `viewer`.
 */
export type ListDocumentTagsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/document-tags`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listDocumentTags` (`application/json`, HTTP 200). */
export type ListDocumentTagsResult = DocumentTagList;

// ------------------------------------------------------------------------------------
// listDocuments - GET /projects/{project_uid}/documents
// ------------------------------------------------------------------------------------

/**
 * List the documents of one project, newest first.
 *
 * One item per document, carrying the version the document currently points at -- the one a reader would open, stream or start a run against. A document with no published version is not listed, because there is nothing to address.
 *
 * The item is a `DocumentVersion` because that is what `uploadDocument` publishes into this same collection: the `GET` of a collection returns a page of exactly what its `POST` returns, which is the rule `listProjects` follows against `createProject`. This surface has no separate `Document` resource and does not acquire one here.
 *
 * An unknown project is `404`, never an empty page: "this project has nothing in it yet" is a different answer from "there is no such project".
 *
 * `UI-PARITY-DOC-AUDIT` (contract 1.34.0): each item carries `audit`, the audit state of the version it shows (`DocumentAudit`), read for the page in one statement and never one request per document. No other operation that returns a `DocumentVersion` carries it. The optional `audit_state` filter and the `order` parameter are applied by the server to the whole listing before it is paged. `UI-A-47` (contract 1.40.0): `audit.active_run` names the run of the version that is in flight, read in the same statement.
 */
export type ListDocumentsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    /** `UI-PARITY-DOC-AUDIT` (contract 1.34.0, `UI-A-38`): only the documents whose current version is in this audit state (`DocumentAudit.state`: `not_run`, `clean`, `awaiting_decision` or `checked`); every document when absent. «Не запускались» is `not_run`. It is applied to the whole listing before the listing is paged, so the cursor and the end of the listing are those of the narrowed listing, and a screen that follows the cursors counts exactly the documents in that state. It composes with `section_code`, `include_archived` and `tag`. */
    audit_state?: "not_run" | "clean" | "awaiting_decision" | "checked";
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Include archived accounts. Absent is `false`. */
    include_archived?: boolean;
    /** Page size. */
    limit?: number;
    /** `UI-PARITY-DOC-AUDIT` (contract 1.34.0, `UI-A-49`): the order of the whole listing. `published` (the default) is the order the operation always had, newest first. `audit` is the original's order of a section, decided by the server so that it holds across pages: documents the expert has checked (`checked`) first, then documents processed and not yet decided on (`clean`, `awaiting_decision`), then documents never audited (`not_run`); within each group by `display_title` in natural Russian order (runs of digits compare as numbers, so «АР1-2» precedes «АР1-10»; letter case and the marks on a letter such as «ё» are ignored), and by `version_uid` among equal names. The cursor is built on the identity and resumes after its row in the ordered listing; presented under another `order` it yields that listing's continuation or an empty page, never a page from another listing. The order follows each document's audit state at the time of the request, so a document that changes state between two pages can appear on both or on neither; a screen that needs the whole listing reads it again from the first page. */
    order?: "published" | "audit";
    /** Only the documents whose current version is confirmed for this section (its `classification.section_code`); every document when absent. A document whose current version has no confirmed classification never matches. `UI-PARITY-P0E` (contract 1.20.0, ruling `R-151l`): the section page lists one section's documents without walking the whole project. A cursor resumes after its row in the filtered listing; presented under another filter it yields that listing's continuation or an empty page, never a page from another listing. */
    section_code?: ProjectSection;
    /** `R-151e`: only the documents carrying this tag, regardless of case. */
    tag?: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listDocuments` (`application/json`, HTTP 200). */
export type ListDocumentsResult = DocumentVersionPage;

// ------------------------------------------------------------------------------------
// listExecutionJournal - GET /execution/journal
// ------------------------------------------------------------------------------------

/** List Journal */
export type ListExecutionJournalInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    run_id?: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutionJournal` (`application/json`, HTTP 200). */
export type ListExecutionJournalResult = ExecutionJournalPage;

// ------------------------------------------------------------------------------------
// listExecutionQueue - GET /execution/queue
// ------------------------------------------------------------------------------------

/** List Queue */
export type ListExecutionQueueInput = {
  /** Query string parameters. */
  query?: {
    /** Only the jobs created at or after this instant (included), an RFC 3339 time with an offset. With `created_to` it bounds the half-open period `[created_from, created_to)` over `created_at`; part of the filters a cursor is bound to. */
    created_from?: string;
    /** Only the jobs created before this instant (not included), an RFC 3339 time with an offset; part of the filters a cursor is bound to. */
    created_to?: string;
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    /** Only the jobs in this state; every state when absent. A cursor is valid only under the filters it was issued under: presented with other filters it is refused as `validation_failed` with `constraint: scope`. */
    state?: "queued" | "leased" | "running" | "retry_wait" | "succeeded" | "failed" | "cancelled" | "dead_letter";
    /** Only the jobs in the states of this group: `active` (`queued`, `leased`, `running`, `retry_wait`), `completed` (`succeeded`, `cancelled`) or `errors` (`failed`, `dead_letter`); every state when absent. Not together with `state` (`422 validation_failed`, `constraint: conflicts_with_state`). Part of the filters a cursor is bound to. */
    state_group?: "active" | "completed" | "errors";
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutionQueue` (`application/json`, HTTP 200). */
export type ListExecutionQueueResult = ExecutionQueuePage;

// ------------------------------------------------------------------------------------
// listExecutorConnections - GET /executor-connections
// ------------------------------------------------------------------------------------

/** List Executor Connections */
export type ListExecutorConnectionsInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutorConnections` (`application/json`, HTTP 200). */
export type ListExecutorConnectionsResult = ExecutorConnectionList;

// ------------------------------------------------------------------------------------
// listExecutorGroups - GET /executor-groups
// ------------------------------------------------------------------------------------

/**
 * List Executor Groups
 *
 * List the executor groups with their current revision, archived ones included (`EXEC2-SEAL-2`, ADR-0026 decision 10). Readable by every role, as `listExecutorConnections` is (`EXEC2-GROUP-STORE-01`).
 */
export type ListExecutorGroupsInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutorGroups` (`application/json`, HTTP 200). */
export type ListExecutorGroupsResult = ExecutorGroupList;

// ------------------------------------------------------------------------------------
// listExecutorHosts - GET /executor-hosts
// ------------------------------------------------------------------------------------

/**
 * List Executor Hosts
 *
 * `HOSTS-SEAL-1` (ADR-0028): every server -- one agent process with its host token -- with the «Использовать» switch, whether it is on line (a report within the last 120 seconds), the models it can serve **now** and its slots, and the summary line of the screen. A server is a host, not a connection: the connections and groups the stand keeps for it are its own and are never listed. `role:admin|expert`; the viewer («Наблюдатель») is denied.
 */
export type ListExecutorHostsInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutorHosts` (`application/json`, HTTP 200). */
export type ListExecutorHostsResult = ExecutorHostList;

// ------------------------------------------------------------------------------------
// listExecutorRoutes - GET /executor-routes
// ------------------------------------------------------------------------------------

/**
 * List Executor Routes
 *
 * The legacy Primary/Standby routes (`EXEC-SEAL-01`). `EXEC2-SEAL-2`: they stay readable in every routing mode, but new work is routed by them only while the mode is `legacy`.
 */
export type ListExecutorRoutesInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutorRoutes` (`application/json`, HTTP 200). */
export type ListExecutorRoutesResult = ExecutorRouteList;

// ------------------------------------------------------------------------------------
// listExecutorRoutingRules - GET /executor-routing-rules
// ------------------------------------------------------------------------------------

/**
 * List Executor Routing Rules
 *
 * The current rule of each work kind that has one, and the current routing mode (`EXEC2-SEAL-2`, ADR-0026 decisions 11 and 17). While the mode is `legacy` the rules exist but are read by nothing. Readable by every role, as `listExecutorConnections` is (`EXEC2-GROUP-STORE-01`).
 */
export type ListExecutorRoutingRulesInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutorRoutingRules` (`application/json`, HTTP 200). */
export type ListExecutorRoutingRulesResult = ExecutorRoutingRuleList;

// ------------------------------------------------------------------------------------
// listKnowledgeBaseEntries - GET /knowledge-base/entries
// ------------------------------------------------------------------------------------

/** List Knowledge Base Entries */
export type ListKnowledgeBaseEntriesInput = {
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
    project_uid?: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listKnowledgeBaseEntries` (`application/json`, HTTP 200). */
export type ListKnowledgeBaseEntriesResult = KnowledgeBaseEntryPage;

// ------------------------------------------------------------------------------------
// listModelCatalogue - GET /model-catalogue
// ------------------------------------------------------------------------------------

/**
 * List Model Catalogue
 *
 * `HOSTS-SEAL-1`: the catalogue of `contracts/analysis/v1/model-catalogue.json` -- the pins of the provider lock the layout offers, with the providers and accesses that can serve each, the efforts that may be asked for and the exact strings an answer may report as its model. A Haiku, an effort above `high` and `low` for Opus are never offered. `role:admin|expert`.
 */
export type ListModelCatalogueInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listModelCatalogue` (`application/json`, HTTP 200). */
export type ListModelCatalogueResult = ModelCatalogue;

// ------------------------------------------------------------------------------------
// listNormDocuments - GET /norm-documents
// ------------------------------------------------------------------------------------

/**
 * List Norm Documents
 *
 * Every document of the current norms snapshot (R-112) as a catalogue, in designation order (natural, case- and homoglyph-folded), then title, then identity. `designation` and `title` are derived for display from the document's stored file name -- dates dotted, designation numbers dotted, a cut edition note closed or shown as `(ред. …)` -- and never alter or replace the stored rows; a name no rule can derive is shown as `getNormDocument` shows it, and `title` is null when the name carries nothing after the designation. `q` (1-200 characters) keeps documents whose designation or title contains it from the start of a word, folded the same way, and a `q` ending in a digit ends a number there; `kind` (1-100 characters) keeps documents whose stored kind equals it, and `kinds` lists every kind of the snapshot with its count. A `q` or `kind` holding a control character or nothing to filter by is `422 validation_failed` (`field` `q` or `kind`, `constraint: format`). The cursor is opaque and bound to `q`, `kind` and the snapshot; another listing refuses it. `total` counts the documents the filters keep. With no current snapshot the answer is `422 required_norm_unavailable` with `reference_kind: norms_snapshot`, never an empty page. Every row carries its `source_attribution` (NORM-Q04). Roles: any one role (`role:admin|expert|viewer`, R-80); an account whose role set is empty is refused `403`. Added by W57B-NORMS-CATALOGUE-XLSX-01.
 */
export type ListNormDocumentsInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** A document kind as the catalogue's `kinds` lists it, matched exactly. */
    kind?: string;
    /** Page size. */
    limit?: number;
    /** Text the designation or title contains from the start of a word. */
    q?: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listNormDocuments` (`application/json`, HTTP 200). */
export type ListNormDocumentsResult = NormCatalogueEntryPage;

// ------------------------------------------------------------------------------------
// listNormParagraphs - GET /norm-documents/{norm_document_id}/paragraphs
// ------------------------------------------------------------------------------------

/**
 * List Norm Paragraphs
 *
 * The document's canonical paragraphs in `ordinal` order, each with `page_label` (the 1-based PDF page), `block_ref`, clause and `text_reliability`; unreliable paragraphs are marked, never hidden. Roles: any one role (`role:admin|expert|viewer`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
 */
export type ListNormParagraphsInput = {
  /** Path parameters, substituted into `/norm-documents/{norm_document_id}/paragraphs`. */
  path: {
    norm_document_id: NormDocumentId;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listNormParagraphs` (`application/json`, HTTP 200). */
export type ListNormParagraphsResult = NormParagraphPage;

// ------------------------------------------------------------------------------------
// listNormSnapshotEvents - GET /norms/snapshots/events
// ------------------------------------------------------------------------------------

/**
 * List Norm Snapshot Events
 *
 * The append-only history of the current snapshot, newest first: who designated which snapshot over which, and when (R-113). Roles: `admin` (`role:admin`). Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
 */
export type ListNormSnapshotEventsInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listNormSnapshotEvents` (`application/json`, HTTP 200). */
export type ListNormSnapshotEventsResult = NormSnapshotEventPage;

// ------------------------------------------------------------------------------------
// listNormSnapshots - GET /norms/snapshots
// ------------------------------------------------------------------------------------

/**
 * List Norm Snapshots
 *
 * Every loaded norms snapshot with its content key, counts, `bge-m3-dense-v1` build state, whether it qualifies to be current (a complete build and a confirmed source binding for every document's PDF) and whether it is current. Roles: any one role (`role:admin|expert|viewer`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
 */
export type ListNormSnapshotsInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listNormSnapshots` (`application/json`, HTTP 200). */
export type ListNormSnapshotsResult = NormSnapshotPage;

// ------------------------------------------------------------------------------------
// listOptimisationPasses - GET /projects/{project_uid}/optimisation-passes
// ------------------------------------------------------------------------------------

/**
 * List Optimisation Passes
 *
 * The project's optimisation passes, newest first (at most `limit`, 100 by default), each with its counts by decision; `document_uid` narrows to one document set of the project. An unknown project or a set of another project is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type ListOptimisationPassesInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/optimisation-passes`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    document_uid?: DocumentUid;
    /** Passes per answer. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listOptimisationPasses` (`application/json`, HTTP 200). */
export type ListOptimisationPassesResult = OptimisationPassList;

// ------------------------------------------------------------------------------------
// listOptimisationProposals - GET /optimisation-passes/{optimisation_pass_id}/proposals
// ------------------------------------------------------------------------------------

/**
 * List Optimisation Proposals
 *
 * One page of a pass's proposals in ordinal order (`offset`, `limit`, `next_offset`), each with its provenance in the specification, the matched and the proposed position, both exact unit prices, the saving where it is computable and its current decision. `decision` narrows to the proposals in one decision state (`pending` for none yet); the pass's `decision_counts` always count every proposal. An unknown pass is `404`. Any one role, `role:admin|expert|viewer`. `UI-B-07` (contract 1.40.0): each proposal carries `saving_percent`, the percent of the current unit price it saves.
 */
export type ListOptimisationProposalsInput = {
  /** Path parameters, substituted into `/optimisation-passes/{optimisation_pass_id}/proposals`. */
  path: {
    optimisation_pass_id: OptimisationPassId;
  };
  /** Query string parameters. */
  query?: {
    decision?: ProposalDecisionState;
    /** Proposals per answer. */
    limit?: number;
    /** Position in the pass's proposals, in ordinal order. */
    offset?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listOptimisationProposals` (`application/json`, HTTP 200). */
export type ListOptimisationProposalsResult = OptimisationProposalPage;

// ------------------------------------------------------------------------------------
// listPrecedentSettings - GET /precedent-settings
// ------------------------------------------------------------------------------------

/**
 * List Precedent Settings
 *
 * `CRIT-SEAL-50` (plan-v5 sections 3.1 and 3.6): the switches (`one_list`, `critic_context`, `section_labels`; every one is off while nothing is journalled), the stop words, the night window and the thresholds, and the journal of their changes. `role:admin`.
 */
export type ListPrecedentSettingsInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listPrecedentSettings` (`application/json`, HTTP 200). */
export type ListPrecedentSettingsResult = PrecedentSettingList;

// ------------------------------------------------------------------------------------
// listPriceListPositions - GET /price-lists/{price_list_id}/positions
// ------------------------------------------------------------------------------------

/**
 * List Price List Positions
 *
 * One page of a price-list revision's positions in source-row order (`offset`, `limit`, `next_offset`), with the revision and its parse report. Each unit price is its exact decimal text. An unknown revision is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type ListPriceListPositionsInput = {
  /** Path parameters, substituted into `/price-lists/{price_list_id}/positions`. */
  path: {
    price_list_id: PriceListId;
  };
  /** Query string parameters. */
  query?: {
    /** Positions per answer. */
    limit?: number;
    /** Position in the revision's positions, in source-row order. */
    offset?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listPriceListPositions` (`application/json`, HTTP 200). */
export type ListPriceListPositionsResult = PriceListPositionPage;

// ------------------------------------------------------------------------------------
// listPriceListRevisions - GET /projects/{project_uid}/price-lists
// ------------------------------------------------------------------------------------

/**
 * List Price List Revisions
 *
 * Every price-list revision of the project, newest first, the first flagged `is_current`. An unknown project is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type ListPriceListRevisionsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/price-lists`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listPriceListRevisions` (`application/json`, HTTP 200). */
export type ListPriceListRevisionsResult = PriceListRevisionList;

// ------------------------------------------------------------------------------------
// listProjects - GET /projects
// ------------------------------------------------------------------------------------

/** List projects, newest first. */
export type ListProjectsInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listProjects` (`application/json`, HTTP 200). */
export type ListProjectsResult = ProjectPage;

// ------------------------------------------------------------------------------------
// listProposalDecisionJournal - GET /proposal-decisions
// ------------------------------------------------------------------------------------

/**
 * List Proposal Decision Journal
 *
 * `UI-PARITY-P0J` (contract 1.25.0, ruling `R-151h`): every expert decision on an optimisation proposal, newest first by `(decided_at, proposal_decision_id)`, with its project, document, version, section, specification row and proposed vendor, and `total`. The original's knowledge base lists both kinds with a «Тип» filter; ours reads this beside `listDecisions`. `project_uid` is a filter, not a parent. A product read.
 */
export type ListProposalDecisionJournalInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    /** Restrict the page to decisions on proposals of this project. Absent means no project filter. */
    project_uid?: ProjectUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listProposalDecisionJournal` (`application/json`, HTTP 200). */
export type ListProposalDecisionJournalResult = ProposalDecisionRecordPage;

// ------------------------------------------------------------------------------------
// listProposalDecisions - GET /optimisation-proposals/{optimisation_proposal_id}/decisions
// ------------------------------------------------------------------------------------

/**
 * List Proposal Decisions
 *
 * The proposal's whole append-only decision history, oldest first, each with its verdict, comment, author and time; the last one is current. An unknown proposal is `404`. Any one role, `role:admin|expert|viewer`.
 */
export type ListProposalDecisionsInput = {
  /** Path parameters, substituted into `/optimisation-proposals/{optimisation_proposal_id}/decisions`. */
  path: {
    optimisation_proposal_id: OptimisationProposalId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listProposalDecisions` (`application/json`, HTTP 200). */
export type ListProposalDecisionsResult = ProposalDecisionList;

// ------------------------------------------------------------------------------------
// listRegistrations - GET /registrations
// ------------------------------------------------------------------------------------

/**
 * List registration requests, oldest first.
 *
 * Requires `admin`. Every request, or those in one status, ordered by `(submitted_at, request_id)`, with `pending_total` -- the number of pending requests whatever the filter.
 */
export type ListRegistrationsInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    /** Restrict the page to requests in this status. */
    status?: RegistrationStatus;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listRegistrations` (`application/json`, HTTP 200). */
export type ListRegistrationsResult = RegistrationRequestPage;

// ------------------------------------------------------------------------------------
// listReleases - GET /releases
// ------------------------------------------------------------------------------------

/**
 * List visible releases and what is new.
 *
 * Requires an active account with a complete profile. Returns releases at or below the running product version, highest revision per release, newest first with the archive last. whats_new contains only non-archive versions loaded after this account was created and above its read mark.
 */
export type ListReleasesInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listReleases` (`application/json`, HTTP 200). */
export type ListReleasesResult = ReleaseList;

// ------------------------------------------------------------------------------------
// listRunFindingBlocks - GET /runs/{run_id}/finding-blocks
// ------------------------------------------------------------------------------------

/**
 * List Run Finding Blocks
 *
 * `UI-PARITY-C6` (contract 1.41.0): which portal blocks a finding's evidence sits in, for the original's block thumbnails under a finding and the number of findings on a block tile. Derived on read, nothing stored: the evidence's characters are located on their page by the run's text-layer block index (the line boxes) and the page inventory (the page sizes), and a portal block holds the evidence when it covers at least half of the evidence's box on that page. One item per published finding, `portal_block_ids` in the portal list's order and empty when no block holds the evidence; `unlinked_pages` are the pages where the portal's raster does not describe the PDF page and no link can be derived (their blocks are unknown, not free of findings). A run without text-layer geometry, or a version without portal geometry, answers `status: "not_produced"` and no items. An unknown run is `404`. Any one role (`R-80`).
 */
export type ListRunFindingBlocksInput = {
  /** Path parameters, substituted into `/runs/{run_id}/finding-blocks`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listRunFindingBlocks` (`application/json`, HTTP 200). */
export type ListRunFindingBlocksResult = RunFindingBlockLinks;

// ------------------------------------------------------------------------------------
// listRunFindings - GET /runs/{run_id}/findings
// ------------------------------------------------------------------------------------

/**
 * List the published findings of one run, with their evidence.
 *
 * Published means grounded: every listed finding's quotations were verified present at their declared anchors. An ungrounded model item is not a finding, does not appear here and is retained only as run diagnostics.
 */
export type ListRunFindingsInput = {
  /** Path parameters, substituted into `/runs/{run_id}/findings`. */
  path: {
    run_id: RunId;
  };
  /** Query string parameters. */
  query?: {
    /** Restrict the page to one finding category. */
    category?: FindingCategory;
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    /** Restrict the page to findings whose current projected verdict is this value. */
    verdict?: Verdict;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listRunFindings` (`application/json`, HTTP 200). */
export type ListRunFindingsResult = FindingPage;

// ------------------------------------------------------------------------------------
// listRuns - GET /versions/{version_uid}/runs
// ------------------------------------------------------------------------------------

/**
 * List the runs of one published version, newest first.
 *
 * Runs hang off the version because `startRun` takes a `version_uid` and nothing else that identifies anything -- the project is derived from it. This is the inverse of that direction and not a second way of addressing a run.
 *
 * Each item is the whole `RunStatus`, identical to what `getRunStatus` answers for that run. There is no lighter list shape: a second shape of one resource is a second thing to drift.
 *
 * An unknown version is `404`, never an empty page.
 */
export type ListRunsInput = {
  /** Path parameters, substituted into `/versions/{version_uid}/runs`. */
  path: {
    version_uid: VersionUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listRuns` (`application/json`, HTTP 200). */
export type ListRunsResult = RunStatusPage;

// ------------------------------------------------------------------------------------
// listStageAiReviews - GET /stage-chain-runs/{stage_chain_run_id}/ai-reviews
// ------------------------------------------------------------------------------------

/** List Ai Reviews */
export type ListStageAiReviewsInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/ai-reviews`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageAiReviews` (`application/json`, HTTP 200). */
export type ListStageAiReviewsResult = StageAiReviewPage;

// ------------------------------------------------------------------------------------
// listStageCardVerdicts - GET /stage-change-cards/{stage_change_card_id}/verdicts
// ------------------------------------------------------------------------------------

/** List Verdicts */
export type ListStageCardVerdictsInput = {
  /** Path parameters, substituted into `/stage-change-cards/{stage_change_card_id}/verdicts`. */
  path: {
    stage_change_card_id: StageChangeCardId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageCardVerdicts` (`application/json`, HTTP 200). */
export type ListStageCardVerdictsResult = StageCardVerdictPage;

// ------------------------------------------------------------------------------------
// listStageChainRuns - GET /stage-pairs/{stage_pair_id}/chain-runs
// ------------------------------------------------------------------------------------

/** List Stage Chain Runs */
export type ListStageChainRunsInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/chain-runs`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageChainRuns` (`application/json`, HTTP 200). */
export type ListStageChainRunsResult = StageChainRunPage;

// ------------------------------------------------------------------------------------
// listStageChangeCards - GET /stage-chain-runs/{stage_chain_run_id}/cards
// ------------------------------------------------------------------------------------

/** List Cards */
export type ListStageChangeCardsInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/cards`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageChangeCards` (`application/json`, HTTP 200). */
export type ListStageChangeCardsResult = StageChangeCardPage;

// ------------------------------------------------------------------------------------
// listStageClassifications - GET /stage-chain-runs/{stage_chain_run_id}/classifications
// ------------------------------------------------------------------------------------

/** List Classifications */
export type ListStageClassificationsInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/classifications`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageClassifications` (`application/json`, HTTP 200). */
export type ListStageClassificationsResult = StageAiClassificationPage;

// ------------------------------------------------------------------------------------
// listStageGraphicEvidence - GET /stage-chain-runs/{stage_chain_run_id}/graphic-evidence
// ------------------------------------------------------------------------------------

/** List Graphics */
export type ListStageGraphicEvidenceInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/graphic-evidence`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageGraphicEvidence` (`application/json`, HTTP 200). */
export type ListStageGraphicEvidenceResult = StageGraphicEvidencePage;

// ------------------------------------------------------------------------------------
// listStageLinkRepairs - GET /stage-chain-runs/{stage_chain_run_id}/sheet-link-repairs
// ------------------------------------------------------------------------------------

/** List Repairs */
export type ListStageLinkRepairsInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/sheet-link-repairs`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageLinkRepairs` (`application/json`, HTTP 200). */
export type ListStageLinkRepairsResult = StageLinkRepairPage;

// ------------------------------------------------------------------------------------
// listStagePairSuggestions - GET /projects/{project_uid}/stage-pair-suggestions
// ------------------------------------------------------------------------------------

/** List Stage Pair Suggestions */
export type ListStagePairSuggestionsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/stage-pair-suggestions`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStagePairSuggestions` (`application/json`, HTTP 200). */
export type ListStagePairSuggestionsResult = StagePairSuggestionPage;

// ------------------------------------------------------------------------------------
// listStagePairs - GET /projects/{project_uid}/stage-pairs
// ------------------------------------------------------------------------------------

/** List Stage Pairs */
export type ListStagePairsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/stage-pairs`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStagePairs` (`application/json`, HTTP 200). */
export type ListStagePairsResult = StagePairPage;

// ------------------------------------------------------------------------------------
// listStageRawDifferences - GET /stage-link-revisions/{stage_link_revision_id}/raw-differences
// ------------------------------------------------------------------------------------

/** List Stage Raw Differences */
export type ListStageRawDifferencesInput = {
  /** Path parameters, substituted into `/stage-link-revisions/{stage_link_revision_id}/raw-differences`. */
  path: {
    stage_link_revision_id: StageLinkRevisionId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageRawDifferences` (`application/json`, HTTP 200). */
export type ListStageRawDifferencesResult = StageTextDifferencePage;

// ------------------------------------------------------------------------------------
// listStageSheetMapHistory - GET /stage-pairs/{stage_pair_id}/sheet-map/revisions
// ------------------------------------------------------------------------------------

/** List Stage Sheet Map History */
export type ListStageSheetMapHistoryInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/sheet-map/revisions`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageSheetMapHistory` (`application/json`, HTTP 200). */
export type ListStageSheetMapHistoryResult = StageLinkRevisionPage;

// ------------------------------------------------------------------------------------
// listStageSheetPassports - GET /stage-pairs/{stage_pair_id}/sheet-passports
// ------------------------------------------------------------------------------------

/** List Stage Sheet Passports */
export type ListStageSheetPassportsInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/sheet-passports`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageSheetPassports` (`application/json`, HTTP 200). */
export type ListStageSheetPassportsResult = StageSheetPassportPage;

// ------------------------------------------------------------------------------------
// listStageSheetSuggestions - GET /stage-pairs/{stage_pair_id}/sheet-suggestions
// ------------------------------------------------------------------------------------

/** List Stage Sheet Suggestions */
export type ListStageSheetSuggestionsInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/sheet-suggestions`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageSheetSuggestions` (`application/json`, HTTP 200). */
export type ListStageSheetSuggestionsResult = StageSheetSuggestionPage;

// ------------------------------------------------------------------------------------
// listStageTextExclusions - GET /stage-link-revisions/{stage_link_revision_id}/text-exclusions
// ------------------------------------------------------------------------------------

/** List Stage Text Exclusions */
export type ListStageTextExclusionsInput = {
  /** Path parameters, substituted into `/stage-link-revisions/{stage_link_revision_id}/text-exclusions`. */
  path: {
    stage_link_revision_id: StageLinkRevisionId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageTextExclusions` (`application/json`, HTTP 200). */
export type ListStageTextExclusionsResult = StageTextExclusionPage;

// ------------------------------------------------------------------------------------
// listStageTextFragments - GET /stage-pairs/{stage_pair_id}/text-fragments
// ------------------------------------------------------------------------------------

/** List Stage Text Fragments */
export type ListStageTextFragmentsInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/text-fragments`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageTextFragments` (`application/json`, HTTP 200). */
export type ListStageTextFragmentsResult = StageTextFragmentPage;

// ------------------------------------------------------------------------------------
// listStageTextHints - GET /stage-link-revisions/{stage_link_revision_id}/text-hints
// ------------------------------------------------------------------------------------

/** List Stage Text Hints */
export type ListStageTextHintsInput = {
  /** Path parameters, substituted into `/stage-link-revisions/{stage_link_revision_id}/text-hints`. */
  path: {
    stage_link_revision_id: StageLinkRevisionId;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageTextHints` (`application/json`, HTTP 200). */
export type ListStageTextHintsResult = StageTextHintPage;

// ------------------------------------------------------------------------------------
// listStageUploads - GET /projects/{project_uid}/stage-uploads
// ------------------------------------------------------------------------------------

/** List Stage Uploads */
export type ListStageUploadsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/stage-uploads`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Query string parameters. */
  query?: {
    cursor?: Cursor;
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listStageUploads` (`application/json`, HTTP 200). */
export type ListStageUploadsResult = StageUploadPage;

// ------------------------------------------------------------------------------------
// listUsers - GET /users
// ------------------------------------------------------------------------------------

/**
 * List accounts, ordered by login.
 *
 * Requires `admin`. Every active account, or every account with `include_archived=true`, ordered by `(login, user_uid)`.
 */
export type ListUsersInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Include archived accounts. Absent is `false`. */
    include_archived?: boolean;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listUsers` (`application/json`, HTTP 200). */
export type ListUsersResult = AccountPage;

// ------------------------------------------------------------------------------------
// listVersionPageProfiles - GET /versions/{version_uid}/page-profiles
// ------------------------------------------------------------------------------------

/**
 * List the stored page profiles of a version.
 *
 * The profiles the worker stored for the pages of a version, by page number ascending, each with its `page_number` and its own identity: a page is addressed by that identity and never by its number. A page whose profile has not been computed is absent; the version's `page_count` says how many pages it has. An unknown version is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-PROFILE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: version_pages`) and nothing is read or written.
 */
export type ListVersionPageProfilesInput = {
  /** Path parameters, substituted into `/versions/{version_uid}/page-profiles`. */
  path: {
    version_uid: VersionUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listVersionPageProfiles` (`application/json`, HTTP 200). */
export type ListVersionPageProfilesResult = VersionPageProfilePage;

// ------------------------------------------------------------------------------------
// listVersionPortalBlocks - GET /versions/{version_uid}/portal-blocks
// ------------------------------------------------------------------------------------

/**
 * List the portal blocks of one published version.
 *
 * What the version's portal bundle brought, page by page: its blocks by type, the text the portal recognised in each TEXT block (marked `recognised`, with quality flags), the portal's description of each IMAGE block (marked, never used in analysis), and for each IMAGE block the crop this product cut itself. Keyed by `version_uid`, not by `run_id`, for the reason `getVersionBlocks` is: the geometry is a deterministic property of the version, read from the most recent run whose `page_geometry_extraction` succeeded.
 *
 * An unknown `version_uid` is `404`. A version that exists but no run of which has produced portal geometry answers `200` with `status: "not_produced"` and no items; that is a different fact from a produced geometry that holds no blocks (`status: "produced"`).
 *
 * Nothing here fetches, stores or serves a portal URL. Roles: any one role (`R-80`).
 */
export type ListVersionPortalBlocksInput = {
  /** Path parameters, substituted into `/versions/{version_uid}/portal-blocks`. */
  path: {
    version_uid: VersionUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listVersionPortalBlocks` (`application/json`, HTTP 200). */
export type ListVersionPortalBlocksResult = PortalBlockPage;

// ------------------------------------------------------------------------------------
// listVersionSheetLabels - GET /versions/{version_uid}/sheet-labels
// ------------------------------------------------------------------------------------

/**
 * List Version Sheet Labels
 *
 * `UI-PARITY-P0O` (contract 1.30.0): the version's pages with the drawing sheet their portal blocks name (`page_label`) and how many blocks each holds, as the original's «Лист» beside a finding's page. Read from the same portal geometry as `listVersionPortalBlocks` (the most recent run whose `page_geometry_extraction` succeeded), one entry per page that has a block; a page whose blocks name different sheets carries no `page_label`, and a page number is never passed off as a sheet. A version no run of which has produced the geometry answers `status: "not_produced"` and no items. An unknown version is `404`. Any one role (`R-80`).
 */
export type ListVersionSheetLabelsInput = {
  /** Path parameters, substituted into `/versions/{version_uid}/sheet-labels`. */
  path: {
    version_uid: VersionUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listVersionSheetLabels` (`application/json`, HTTP 200). */
export type ListVersionSheetLabelsResult = VersionSheetLabelList;

// ------------------------------------------------------------------------------------
// listVersions - GET /documents/{document_uid}/versions
// ------------------------------------------------------------------------------------

/**
 * List the published versions of one document, newest first.
 *
 * Every immutable version of one document, ordered by `version_ordinal` descending. The ordinal is a display and ordering value and is never an identity; the continuation token carries the opaque `version_uid` and nothing else.
 *
 * An unknown document is `404`, never an empty page.
 */
export type ListVersionsInput = {
  /** Path parameters, substituted into `/documents/{document_uid}/versions`. */
  path: {
    document_uid: DocumentUid;
  };
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listVersions` (`application/json`, HTTP 200). */
export type ListVersionsResult = DocumentVersionPage;

// ------------------------------------------------------------------------------------
// listWorkers - GET /execution/workers
// ------------------------------------------------------------------------------------

/** List Workers */
export type ListWorkersInput = {
  /** Query string parameters. */
  query?: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listWorkers` (`application/json`, HTTP 200). */
export type ListWorkersResult = ExecutionWorkerPage;

// ------------------------------------------------------------------------------------
// markReleaseNotesRead - PUT /me/release-notes
// ------------------------------------------------------------------------------------

/**
 * Mark release notes read through a version.
 *
 * Requires an active account with a complete profile, including an administrator without the expert role. The credential names the account; the body cannot name another. A known version at or below the running product version raises its high-water mark; a lower or equal version is a no-op. Unknown or future versions are validation_failed. No idempotency key is required.
 */
export type MarkReleaseNotesReadInput = {
  /** Request body, sent as `application/json`. */
  body: MarkReleaseNotesReadRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `markReleaseNotesRead`. */
export type MarkReleaseNotesReadResult = void;

// ------------------------------------------------------------------------------------
// pauseComparisonAiPairCheck - POST /comparison-ai-pair-checks/{comparison_ai_job_id}/pause
// ------------------------------------------------------------------------------------

/**
 * Pause an AI check of pairs.
 *
 * «Пауза»: stops the job after the call in hand; queued questions wait. A job that is not queued or running is `409 conflict` (`comparison_ai_job_state`). An unknown job, or a job of another method, is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AIPAIR-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_pairs`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type PauseComparisonAiPairCheckInput = {
  /** Path parameters, substituted into `/comparison-ai-pair-checks/{comparison_ai_job_id}/pause`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `pauseComparisonAiPairCheck` (`application/json`, HTTP 200). */
export type PauseComparisonAiPairCheckResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// pauseComparisonAiSheetChanges - POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/pause
// ------------------------------------------------------------------------------------

/**
 * Pause an AI description of changes.
 *
 * «Пауза»: stops the job after the call in hand. A job that is not queued or running is `409 conflict` (`comparison_ai_job_state`). An unknown job, or a job of another method, is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type PauseComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-ai-sheet-jobs/{comparison_ai_job_id}/pause`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `pauseComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type PauseComparisonAiSheetChangesResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// pauseComparisonLaunchQueue - POST /projects/{project_uid}/comparison-launch-queue/pause
// ------------------------------------------------------------------------------------

/**
 * Pause the launch queue.
 *
 * «Пауза очереди»: the step in hand finishes and no further entry starts. A queue that is not running is `409 conflict` (`comparison_launch_queue_state`). An unknown project is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-QUEUE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_launch_queue`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type PauseComparisonLaunchQueueInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-launch-queue/pause`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `pauseComparisonLaunchQueue` (`application/json`, HTTP 200). */
export type PauseComparisonLaunchQueueResult = ComparisonLaunchQueue;

// ------------------------------------------------------------------------------------
// pauseComparisonSeries - POST /comparison-series/{comparison_series_id}/pause
// ------------------------------------------------------------------------------------

/**
 * Pause a series.
 *
 * «Пауза»: stops the series after the items in hand; queued items wait. A series that is not queued or running is `409 conflict` (`comparison_series_state`). An unknown series is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type PauseComparisonSeriesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/pause`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `pauseComparisonSeries` (`application/json`, HTTP 200). */
export type PauseComparisonSeriesResult = ComparisonSeries;

// ------------------------------------------------------------------------------------
// pauseComparisonUpload - POST /comparison-uploads/{comparison_upload_id}/pause
// ------------------------------------------------------------------------------------

/**
 * Pause an upload batch after the set in hand.
 *
 * The batch finishes the set it is processing and then stops. A batch that is not being processed is `409 conflict` (`comparison_upload_state`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-02` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type PauseComparisonUploadInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/pause`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `pauseComparisonUpload` (`application/json`, HTTP 200). */
export type PauseComparisonUploadResult = ComparisonUpload;

// ------------------------------------------------------------------------------------
// pauseStageChainBatch - POST /stage-chain-batches/{stage_chain_batch_id}/pause
// ------------------------------------------------------------------------------------

/** Pause Batch */
export type PauseStageChainBatchInput = {
  /** Path parameters, substituted into `/stage-chain-batches/{stage_chain_batch_id}/pause`. */
  path: {
    stage_chain_batch_id: StageChainBatchId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `pauseStageChainBatch` (`application/json`, HTTP 200). */
export type PauseStageChainBatchResult = StageChainBatch;

// ------------------------------------------------------------------------------------
// pauseStageUpload - POST /stage-uploads/{stage_upload_id}/pause
// ------------------------------------------------------------------------------------

/** Pause Stage Upload */
export type PauseStageUploadInput = {
  /** Path parameters, substituted into `/stage-uploads/{stage_upload_id}/pause`. */
  path: {
    stage_upload_id: StageUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `pauseStageUpload` (`application/json`, HTTP 200). */
export type PauseStageUploadResult = StageUpload;

// ------------------------------------------------------------------------------------
// prepareComparisonClientReport - POST /comparison-reports/{comparison_report_id}/client-report
// ------------------------------------------------------------------------------------

/**
 * Prepare the client report from an analytic report.
 *
 * «Подготовить отчёт для заказчика»: a new `client` draft with its estimate that reads the verified facts of a finished analytic report. An analytic report that is not finished, or a client report, is `409 conflict` (`comparison_report_state`). No model is called. An unknown report is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type PrepareComparisonClientReportInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/client-report`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /** Request body, sent as `application/json`. */
  body: PrepareComparisonClientReportRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `prepareComparisonClientReport` (`application/json`, HTTP 201). */
export type PrepareComparisonClientReportResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// prepareComparisonMatrix - POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/preparation
// ------------------------------------------------------------------------------------

/**
 * Queue the profiles and the build of the matrix of a document set.
 *
 * «Подготовить» and «Повторить»: queues the page profiles of the document set's versions that are missing or failed, then the algorithmic build of the matrix (`ADR-0025` decisions 3 and 14). It is idempotent: a preparation that is already queued or running is returned as it is, and a build that is current is not repeated. It never changes a manual edit. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). An unknown project, or a document of another project, is `404`. Served by `CMP-MATRIX-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_matrix`) until the lane wired it.
 */
export type PrepareComparisonMatrixInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-matrix/preparation`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `prepareComparisonMatrix` (`application/json`, HTTP 200). */
export type PrepareComparisonMatrixResult = ComparisonMatrixPreparation;

// ------------------------------------------------------------------------------------
// previewExecutorRouting - GET /executor-routing/preview
// ------------------------------------------------------------------------------------

/**
 * Preview Executor Routing
 *
 * Propose the cut-over from the legacy routes to rules, writing nothing (`EXEC2-SEAL-2`, ADR-0026 decision 17): per work kind a one-member group made from the primary of its route. A standby is shown and never converted into a member; a route that cannot become a group is flagged `incompatible` with its reason. `preview_digest` binds the proposal. `403 permission_denied` for a caller without `admin`.
 */
export type PreviewExecutorRoutingInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `previewExecutorRouting` (`application/json`, HTTP 200). */
export type PreviewExecutorRoutingResult = ExecutorRoutingPreview;

// ------------------------------------------------------------------------------------
// purgeUser - DELETE /users/{user_uid}
// ------------------------------------------------------------------------------------

/**
 * Purge an archived, unreferenced account.
 *
 * Requires `admin`. Irreversible (R-61): an **archived** account that nothing references is deleted with its roles; the request that created it keeps its row, and the login becomes free. An account that is not archived is `state_transition_not_allowed` against `app_user`; one that archived, granted or decided anything, or authored a decision, is `conflict` with `conflict_reason: account_referenced` and stays archived; oneself is `permission_denied`.
 */
export type PurgeUserInput = {
  /** Path parameters, substituted into `/users/{user_uid}`. */
  path: {
    user_uid: UserUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `purgeUser`. */
export type PurgeUserResult = void;

// ------------------------------------------------------------------------------------
// readRegistrationStatus - POST /registrations/status
// ------------------------------------------------------------------------------------

/**
 * Read whether a login and password pair proves a pending application.
 *
 * Reachable without a credential, like `issueToken`, and called by a client after an exchange was refused. A pair that proves a **pending** application answers `{"status": "pending"}`. **Every other pair answers the same `401 authentication_required` a refused exchange gets** -- an unknown login, a wrong password, and a decided application, whose password was removed at the decision so that nothing can prove the pair. A rejected applicant is told nothing here (R-56 addendum of 2026-10-06); the reason is for administrators. Every path costs the same work, so the timing reveals nothing either, and refused reads are counted on the request with the sign-in brake's rules. `403` is not declared: there is no subject to deny. The edge throttles it per client and answers `rate_limited` (`429`) itself, before the operation is reached.
 */
export type ReadRegistrationStatusInput = {
  /** Request body, sent as `application/json`. */
  body: IssueTokenRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `readRegistrationStatus` (`application/json`, HTTP 200). */
export type ReadRegistrationStatusResult = RegistrationStatusResponse;

// ------------------------------------------------------------------------------------
// reauditRun - POST /runs/{run_id}/reaudit
// ------------------------------------------------------------------------------------

/**
 * Reaudit Run
 *
 * A re-audit runs the same version on the current configuration (R-82), so it faces today's limit (the one-call analysis input budget times the number of windows a run may use), not the source run's: over it, the answer is `422 analysis_input_budget_exceeded` with `details.character_count` and `details.budget_characters`, and no run exists (R-118). `W59-SECTION-SEAL-01`: the new run is routed from the version's persisted classification exactly as `startRun` is, never from the source run's profile; an unclassified version is `422 version_classification_required` and a section with no registered text profile is `422 section_profile_unavailable`. `EXEC-PAR-START-01`: a re-audit of a run whose executor was named at its start runs on that same connection (its current revision), not on today's route; if that connection can no longer serve, the answer is `503 dependency_unavailable` with `details.dependency` `executor_connection` and no run exists. It is never redirected to the standby or to another connection. New served re-audits require fresh confirmed cost consent from estimateRunCost with reaudit_of_run_id before any new spend; the parent approval is never reused. Accepted historical command keys replay their recorded outcome.
 *
 * `HOSTS-SEAL-1` (ADR-0028): while the stage layout is switched on, a re-audit takes today's layout like a new start: a fresh plan, the consent v2 of `startRun` (the digest of the plan, per model the rate digest and access) and the same waiting for a model. With the layout off it is what it was.
 */
export type ReauditRunInput = {
  /** Path parameters, substituted into `/runs/{run_id}/reaudit`. */
  path: {
    run_id: RunId;
  };
  /** Request body, sent as `application/json`. */
  body: ReauditRunRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reauditRun` (`application/json`, HTTP 202). */
export type ReauditRunResult = RunStatus;

// ------------------------------------------------------------------------------------
// rebuildComparisonReportPdf - POST /comparison-reports/{comparison_report_id}/pdf-rebuild
// ------------------------------------------------------------------------------------

/**
 * Write the PDF of a report again.
 *
 * «Пересобрать PDF»: writes the PDF again from the stored text; no model is called and nothing is spent. A report whose text is not complete is `409 conflict` (`comparison_report_state`). An unknown report is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type RebuildComparisonReportPdfInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/pdf-rebuild`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `rebuildComparisonReportPdf` (`application/json`, HTTP 200). */
export type RebuildComparisonReportPdfResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// recomputeStageTextEvidence - POST /stage-link-revisions/{stage_link_revision_id}/text-evidence/recomputation
// ------------------------------------------------------------------------------------

/** Recompute Stage Text Evidence */
export type RecomputeStageTextEvidenceInput = {
  /** Path parameters, substituted into `/stage-link-revisions/{stage_link_revision_id}/text-evidence/recomputation`. */
  path: {
    stage_link_revision_id: StageLinkRevisionId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `recomputeStageTextEvidence` (`application/json`, HTTP 202). */
export type RecomputeStageTextEvidenceResult = StageChainRun;

// ------------------------------------------------------------------------------------
// redeemExecutorEnrollment - POST /runner/enroll
// ------------------------------------------------------------------------------------

/**
 * Redeem Executor Enrollment
 *
 * Exchange an enrollment secret, presented as the bearer credential, for a runner token (`EXEC2-SEAL-1`, ADR-0026 decision 4). The token is returned once, exactly as `issueRunnerToken` returns one. A repeat from the same `runner_instance_id` inside the exchange window is idempotent: an agent that lost the response is not locked out, and the stand never stores the value. A repeat after the window is `409 conflict` with `conflict_reason` `enrollment_redeemed`; `connection_archived` is refused the same way. An unknown, expired or revoked secret is `401 authentication_required`, and the answer does not say which. The secret reaches no other operation: the four task operations refuse it as they refuse any wrong token.
 *
 * `HOSTS-SEAL-1` (ADR-0028, contract 1.45.0): the grant may belong to a **host** (`issueExecutorHostEnrollment`). The exchange then takes no model and answers `token` (a runner token bound to the host, which serves every system connection of it), `host_id` and `catalogue` -- the models the agent may be asked for, each with its provider, `efforts` and `accepted_reported`; `runner_token` (the metadata) is optional in a host document and always present for the grant of a connection. The repeat and `409` rules are unchanged.
 */
export type RedeemExecutorEnrollmentInput = {
  /** Request body, sent as `application/json`. */
  body: RedeemExecutorEnrollmentRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `redeemExecutorEnrollment` (`application/json`, HTTP 201). */
export type RedeemExecutorEnrollmentResult = IssuedRunnerToken;

// ------------------------------------------------------------------------------------
// rejectRegistration - POST /registrations/{request_id}/reject
// ------------------------------------------------------------------------------------

/**
 * Reject a registration request with a reason.
 *
 * Requires `admin`. Decides the request as rejected with the reason, which is stored for administrators only, and removes its password. A request that is no longer pending is `state_transition_not_allowed` against `registration_request`. No account is created.
 */
export type RejectRegistrationInput = {
  /** Path parameters, substituted into `/registrations/{request_id}/reject`. */
  path: {
    request_id: RegistrationRequestId;
  };
  /** Request body, sent as `application/json`. */
  body: RejectRegistrationRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `rejectRegistration` (`application/json`, HTTP 200). */
export type RejectRegistrationResult = RegistrationRequest;

// ------------------------------------------------------------------------------------
// rejectStageUploadCandidate - POST /stage-upload-candidates/{stage_upload_candidate_id}/rejection
// ------------------------------------------------------------------------------------

/** Reject Stage Upload Candidate */
export type RejectStageUploadCandidateInput = {
  /** Path parameters, substituted into `/stage-upload-candidates/{stage_upload_candidate_id}/rejection`. */
  path: {
    stage_upload_candidate_id: StageUploadCandidateId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `rejectStageUploadCandidate` (`application/json`, HTTP 200). */
export type RejectStageUploadCandidateResult = StageUploadCandidate;

// ------------------------------------------------------------------------------------
// removeComparisonLaunchEntry - POST /comparison-launch-entries/{comparison_launch_entry_id}/removal
// ------------------------------------------------------------------------------------

/**
 * Remove one entry from the launch queue.
 *
 * «✕»: one waiting entry leaves the queue. An entry that is running or finished is `409 conflict` (`comparison_launch_entry_state`). An unknown entry is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-QUEUE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_launch_queue`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type RemoveComparisonLaunchEntryInput = {
  /** Path parameters, substituted into `/comparison-launch-entries/{comparison_launch_entry_id}/removal`. */
  path: {
    comparison_launch_entry_id: ComparisonLaunchEntryId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `removeComparisonLaunchEntry` (`application/json`, HTTP 200). */
export type RemoveComparisonLaunchEntryResult = ComparisonLaunchQueue;

// ------------------------------------------------------------------------------------
// renameDocument - PUT /projects/{project_uid}/documents/{document_uid}/title
// ------------------------------------------------------------------------------------

/**
 * Rename Document
 *
 * `UI-PARITY-P0G` (contract 1.22.0, ruling `R-151a`): change the document's display title; `document_uid` stays its identity. The title is trimmed and is 1 to 400 characters. The same title again changes nothing; a change appends `document.renamed` (from, to, actor) to the audit trail. `expert` and `admin`; `viewer` is refused.
 */
export type RenameDocumentInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/title`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: RenameDocumentRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `renameDocument` (`application/json`, HTTP 200). */
export type RenameDocumentResult = DocumentVersion;

// ------------------------------------------------------------------------------------
// reportRunnerHealth - POST /runner/health
// ------------------------------------------------------------------------------------

/**
 * Report Runner Health
 *
 * An agent reports its version, its command-line clients with their sanitised authentication state, its concurrency, execution profile and declared features (`EXEC2-SEAL-1`, ADR-0026 decision 5). The report is stored on the calling runner token and returned in `RunnerTokenMetadata`. Only closed enumerations and bounded strings are accepted: no secret, no path to a credential and no document text is stored. A report that violates the schema is `422 validation_failed`.
 *
 * `HOSTS-SEAL-1` (ADR-0028): a **host token** also sends `providers[]` (each provider found on the host: `access`, `auth_state`, the state of each catalogue model -- `verified`, `not_verified` or `failed` with a `failure_code` -- and `accept_images`), `slots` (an integer 1 to 16 per provider) and, optionally, `key_file` (`ok`, `absent` or `ignored`, with a reason code: diagnostics only). `providers` and `slots` are required of a host token and refused (`422 validation_failed`) for a connection token. `clis` stays required, `execution_profile` is `command` and `concurrency` is the sum of the slots (1 to 16). The stand keeps the latest snapshot per host and writes a new one only when its content changes; the pulse is the token's `last_seen_at` (a report older than 120 seconds is no pulse). The access of a command-line client is read from its own status: a subscription login is `subscription`, a login with a key `api`; a client not signed in is `subscription` with `auth_state` `login_required`; one signed in by an unrecognised method is `api` with `auth_state` `unknown` and no verified model. The answer carries `catalogue` and `enabled`; `enabled: false` is the «Использовать» switch off, which stops new runs being bound to the host and does **not** stop claims.
 */
export type ReportRunnerHealthInput = {
  /** Request body, sent as `application/json`. */
  body: ReportRunnerHealthRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reportRunnerHealth` (`application/json`, HTTP 200). */
export type ReportRunnerHealthResult = RunnerHealthAck;

// ------------------------------------------------------------------------------------
// requestExecutorProbe - POST /executor-connections/{connection_id}/probes
// ------------------------------------------------------------------------------------

/** Request Executor Probe */
export type RequestExecutorProbeInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/probes`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `requestExecutorProbe` (`application/json`, HTTP 202). */
export type RequestExecutorProbeResult = ExecutorProbe;

// ------------------------------------------------------------------------------------
// resetUserPassword - POST /users/{user_uid}/password
// ------------------------------------------------------------------------------------

/**
 * Set a temporary password for an account.
 *
 * Requires `admin`. The account's password becomes the temporary one, held to the password policy; the account must change it at its next sign-in (`is_default_credential` becomes true), its sign-in brake is cleared, and every credential it holds is refused. Not oneself (`permission_denied`): an administrator changes their own password with `changePassword`. That the administrator knows the temporary password is a registered limitation.
 */
export type ResetUserPasswordInput = {
  /** Path parameters, substituted into `/users/{user_uid}/password`. */
  path: {
    user_uid: UserUid;
  };
  /** Request body, sent as `application/json`. */
  body: ResetUserPasswordRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resetUserPassword` (`application/json`, HTTP 200). */
export type ResetUserPasswordResult = Account;

// ------------------------------------------------------------------------------------
// restoreDecisionMemoryCase - POST /decision-memory/cases/{case_id}/restore
// ------------------------------------------------------------------------------------

/**
 * Restore Decision Memory Case
 *
 * `DECISION-MEMORY-01` phase M2: undo a withdraw. Append-only: a `restore` status event with a closed `reason_code` and the caller's account. A case that is not withdrawn is `409 state_transition_not_allowed`; a forgotten case accepts no status event (`409 conflict`, `conflict_reason: memory_case_forgotten`); an unknown case is `404`. An exact repeat of the `Idempotency-Key` answers the first call's event and writes nothing. `role:admin`.
 */
export type RestoreDecisionMemoryCaseInput = {
  /** Path parameters, substituted into `/decision-memory/cases/{case_id}/restore`. */
  path: {
    case_id: DecisionMemoryCaseId;
  };
  /** Request body, sent as `application/json`. */
  body: DecisionMemoryStatusChangeRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `restoreDecisionMemoryCase` (`application/json`, HTTP 200). */
export type RestoreDecisionMemoryCaseResult = DecisionMemoryStatusChange;

// ------------------------------------------------------------------------------------
// restoreUser - POST /users/{user_uid}/restore
// ------------------------------------------------------------------------------------

/**
 * Restore an archived account.
 *
 * Requires `admin`. Returns an archived account to active; it signs in again with its own password. An active account is `state_transition_not_allowed` against `app_user`; a login another active account took meanwhile is `conflict` with `conflict_reason: login_taken`.
 */
export type RestoreUserInput = {
  /** Path parameters, substituted into `/users/{user_uid}/restore`. */
  path: {
    user_uid: UserUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `restoreUser` (`application/json`, HTTP 200). */
export type RestoreUserResult = Account;

// ------------------------------------------------------------------------------------
// resumeComparisonAiPairCheck - POST /comparison-ai-pair-checks/{comparison_ai_job_id}/resume
// ------------------------------------------------------------------------------------

/**
 * Resume an AI check of pairs.
 *
 * «Продолжить»: continues a paused job. After a pause for `overrun` (the actual spend passed 1.2 times the consented estimate) or `route_changed` the request carries a new consent for what is left (`comparison_consent_required` when it does not, `comparison_estimate_stale` when its digest is not the one now computed); after the other reasons the consent is ignored. A job that is not paused is `409 conflict` (`comparison_ai_job_state`). An unknown job is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AIPAIR-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_pairs`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ResumeComparisonAiPairCheckInput = {
  /** Path parameters, substituted into `/comparison-ai-pair-checks/{comparison_ai_job_id}/resume`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /** Request body, sent as `application/json`. */
  body: ResumeComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeComparisonAiPairCheck` (`application/json`, HTTP 200). */
export type ResumeComparisonAiPairCheckResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// resumeComparisonAiSheetChanges - POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/resume
// ------------------------------------------------------------------------------------

/**
 * Resume an AI description of changes.
 *
 * «Продолжить»: continues a paused job. After a pause for `overrun` or `route_changed` the request carries a new consent for what is left; after the other reasons (`user`, `quota`, `auth`, `module_off`) the consent is ignored. A job that is not paused is `409 conflict` (`comparison_ai_job_state`). An unknown job is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ResumeComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-ai-sheet-jobs/{comparison_ai_job_id}/resume`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /** Request body, sent as `application/json`. */
  body: ResumeComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type ResumeComparisonAiSheetChangesResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// resumeComparisonLaunchQueue - POST /projects/{project_uid}/comparison-launch-queue/resume
// ------------------------------------------------------------------------------------

/**
 * Resume the launch queue.
 *
 * «Продолжить очередь»: continues a paused or failed queue. A queue that is running is `409 conflict` (`comparison_launch_queue_state`). An unknown project is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-QUEUE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_launch_queue`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type ResumeComparisonLaunchQueueInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/comparison-launch-queue/resume`. */
  path: {
    project_uid: ProjectUid;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeComparisonLaunchQueue` (`application/json`, HTTP 200). */
export type ResumeComparisonLaunchQueueResult = ComparisonLaunchQueue;

// ------------------------------------------------------------------------------------
// resumeComparisonSeries - POST /comparison-series/{comparison_series_id}/resume
// ------------------------------------------------------------------------------------

/**
 * Resume a paused series.
 *
 * «Продолжить»: queues the paused items again. A series that is not paused is `409 conflict` (`comparison_series_state`). An unknown series is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type ResumeComparisonSeriesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/resume`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeComparisonSeries` (`application/json`, HTTP 200). */
export type ResumeComparisonSeriesResult = ComparisonSeries;

// ------------------------------------------------------------------------------------
// resumeComparisonUpload - POST /comparison-uploads/{comparison_upload_id}/resume
// ------------------------------------------------------------------------------------

/**
 * Resume a paused upload batch.
 *
 * A batch that is not paused is `409 conflict` (`comparison_upload_state`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-02` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type ResumeComparisonUploadInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/resume`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeComparisonUpload` (`application/json`, HTTP 200). */
export type ResumeComparisonUploadResult = ComparisonUpload;

// ------------------------------------------------------------------------------------
// resumeStageChainBatch - POST /stage-chain-batches/{stage_chain_batch_id}/resume
// ------------------------------------------------------------------------------------

/** Resume Batch */
export type ResumeStageChainBatchInput = {
  /** Path parameters, substituted into `/stage-chain-batches/{stage_chain_batch_id}/resume`. */
  path: {
    stage_chain_batch_id: StageChainBatchId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeStageChainBatch` (`application/json`, HTTP 200). */
export type ResumeStageChainBatchResult = StageChainBatch;

// ------------------------------------------------------------------------------------
// resumeStageChainRun - POST /stage-chain-runs/{stage_chain_run_id}/resume
// ------------------------------------------------------------------------------------

/** Resume Run */
export type ResumeStageChainRunInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/resume`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /** Request body, sent as `application/json`. */
  body: ResumeStageChainRunRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeStageChainRun` (`application/json`, HTTP 200). */
export type ResumeStageChainRunResult = StageChainRun;

// ------------------------------------------------------------------------------------
// resumeStageUpload - POST /stage-uploads/{stage_upload_id}/resume
// ------------------------------------------------------------------------------------

/** Resume Stage Upload */
export type ResumeStageUploadInput = {
  /** Path parameters, substituted into `/stage-uploads/{stage_upload_id}/resume`. */
  path: {
    stage_upload_id: StageUploadId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `resumeStageUpload` (`application/json`, HTTP 200). */
export type ResumeStageUploadResult = StageUpload;

// ------------------------------------------------------------------------------------
// retryComparisonAiSheetChanges - POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/retry
// ------------------------------------------------------------------------------------

/**
 * Describe the sheets that failed again.
 *
 * «Повторить листы с ошибкой»: describes again only the sheets that failed, for example after a refusal of the provider. It is a new spend, so the request carries the consent to the estimate of `estimateComparisonAiSheetChanges` with `only_failed` true; the checks of the start apply (`comparison_estimate_stale`, `comparison_consent_required`, `comparison_ceiling_job`, `comparison_ceiling_day`). A job with no failed sheet is `409 conflict` (`comparison_ai_nothing_to_do`). An unknown job is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type RetryComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-ai-sheet-jobs/{comparison_ai_job_id}/retry`. */
  path: {
    comparison_ai_job_id: ComparisonAiJobId;
  };
  /** Request body, sent as `application/json`. */
  body: StartComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `retryComparisonAiSheetChanges` (`application/json`, HTTP 200). */
export type RetryComparisonAiSheetChangesResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// retryComparisonUploadSet - POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/retry
// ------------------------------------------------------------------------------------

/**
 * Queue a failed set again.
 *
 * Only a failed set can be retried. A set in any other state is `409 conflict` (`comparison_set_state`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-02` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type RetryComparisonUploadSetInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/retry`. */
  path: {
    comparison_upload_id: ComparisonUploadId;
    comparison_upload_set_id: ComparisonUploadSetId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `retryComparisonUploadSet` (`application/json`, HTTP 200). */
export type RetryComparisonUploadSetResult = ComparisonProposalSet;

// ------------------------------------------------------------------------------------
// reviewDecisionPattern - POST /decision-memory/patterns/{pattern_id}/review
// ------------------------------------------------------------------------------------

/**
 * Review Decision Pattern
 *
 * `CRIT-SEAL-53` (plan-v5 section 3.7, owner ruling Н4): an expert's decision on a pattern -- `approve` (from `proposed` or `suspended`), `reject` (from `proposed`) or `suspend` (from `approved`); an append-only status event with its actor. `404 not_found` for an unknown pattern, `409 state_conflict` for a transition the status does not allow. `role:admin|expert`, `Idempotency-Key` required.
 */
export type ReviewDecisionPatternInput = {
  /** Path parameters, substituted into `/decision-memory/patterns/{pattern_id}/review`. */
  path: {
    pattern_id: DecisionPatternId;
  };
  /** Request body, sent as `application/json`. */
  body: ReviewDecisionPatternRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reviewDecisionPattern` (`application/json`, HTTP 200). */
export type ReviewDecisionPatternResult = DecisionPattern;

// ------------------------------------------------------------------------------------
// reviseAnalysisPreset - POST /analysis/presets/{preset_id}/revisions
// ------------------------------------------------------------------------------------

/**
 * Revise an analysis preset.
 *
 * Append a revision with the full settings, never a patch; the earlier revision is kept as it was and runs that used it keep pointing at it. An administrator's act (`role:admin`). Refusals: `403`, `404` for an unknown preset, `422 validation_failed` as for creation and `differs_from_current` on `name` when nothing would change, `409 conflict` (`preset_archived`, `preset_name_in_use`, `connection_archived`).
 */
export type ReviseAnalysisPresetInput = {
  /** Path parameters, substituted into `/analysis/presets/{preset_id}/revisions`. */
  path: {
    preset_id: PresetId;
  };
  /** Request body, sent as `application/json`. */
  body: SaveAnalysisPresetRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reviseAnalysisPreset` (`application/json`, HTTP 201). */
export type ReviseAnalysisPresetResult = AnalysisPreset;

// ------------------------------------------------------------------------------------
// reviseExecutorConnection - POST /executor-connections/{connection_id}/revisions
// ------------------------------------------------------------------------------------

/** Revise Executor Connection */
export type ReviseExecutorConnectionInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/revisions`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /** Request body, sent as `application/json`. */
  body: ReviseExecutorConnectionRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reviseExecutorConnection` (`application/json`, HTTP 201). */
export type ReviseExecutorConnectionResult = ExecutorRevision;

// ------------------------------------------------------------------------------------
// reviseExecutorGroup - POST /executor-groups/{group_id}/revisions
// ------------------------------------------------------------------------------------

/**
 * Revise Executor Group
 *
 * Add an immutable revision to a group: the full settings, never a patch (`EXEC2-SEAL-2`, ADR-0026 decision 10). Work already admitted on an earlier revision finishes on it; new work and rules that name the group are not moved. Every member must be of a connection that exists and is not archived, must name a revision of that connection, and that revision must pin exactly `pin_id` and `gateway_model` and share `billing` (and therefore the pinned rates, which the server snapshots from the provider lock): `422 validation_failed` with `details.field` `members` and constraint `unknown_executor_connection`, `member_revision_not_of_connection`, `member_repeated`, `tie_break_order_repeated` or `member_kind_not_served`, or with field `pin_id`, `gateway_model` or `billing` and constraint `member_pin_mismatch`, `member_model_mismatch` or `member_billing_mismatch`; a `pin_id` the provider lock does not hold is `model_not_pinned`; one to 16 members are accepted (`range`). An archived member connection is `409 conflict` with `conflict_reason` `connection_archived`. Mixed groups are not accepted. `409 conflict` with `conflict_reason` `group_archived` for an archived group. `404 not_found`; `403 permission_denied` for a caller without `admin`.
 */
export type ReviseExecutorGroupInput = {
  /** Path parameters, substituted into `/executor-groups/{group_id}/revisions`. */
  path: {
    group_id: ExecutorGroupId;
  };
  /** Request body, sent as `application/json`. */
  body: ReviseExecutorGroupRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reviseExecutorGroup` (`application/json`, HTTP 201). */
export type ReviseExecutorGroupResult = ExecutorGroup;

// ------------------------------------------------------------------------------------
// reviseStageAssembly - POST /stage-assemblies/{stage_assembly_id}/members
// ------------------------------------------------------------------------------------

/** Revise Stage Assembly */
export type ReviseStageAssemblyInput = {
  /** Path parameters, substituted into `/stage-assemblies/{stage_assembly_id}/members`. */
  path: {
    stage_assembly_id: StageAssemblyId;
  };
  /** Request body, sent as `application/json`. */
  body: ReviseStageAssemblyRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reviseStageAssembly` (`application/json`, HTTP 200). */
export type ReviseStageAssemblyResult = StageAssembly;

// ------------------------------------------------------------------------------------
// reviseStageModelLayout - POST /model-layout/revisions
// ------------------------------------------------------------------------------------

/**
 * Revise Stage Model Layout
 *
 * `HOSTS-SEAL-1`: save a new immutable revision of the layout (author and time are kept). Every cell must be a pair of `listModelCatalogue` (model and effort); the blocks row is chosen from the closed list of schemes, never leg by leg; a cell key repeated or missing is `422 validation_failed`. `LIMITS-01` (contract 1.49.0): a cell has no answer limit and no timeout, so a cell (or comparison cell) that still names `max_output_tokens` or `timeout_seconds` is refused `422 validation_failed`, not ignored. A revision changes nothing for runs already started: they froze their plan. `role:admin`, `Idempotency-Key` required.
 */
export type ReviseStageModelLayoutInput = {
  /** Request body, sent as `application/json`. */
  body: ReviseStageModelLayoutRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `reviseStageModelLayout` (`application/json`, HTTP 201). */
export type ReviseStageModelLayoutResult = StageModelLayout;

// ------------------------------------------------------------------------------------
// revokeRunnerToken - POST /executor-connections/{connection_id}/runner-tokens/{token_id}/revoke
// ------------------------------------------------------------------------------------

/** Revoke Runner Token */
export type RevokeRunnerTokenInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/runner-tokens/{token_id}/revoke`. */
  path: {
    connection_id: ExecutorConnectionId;
    token_id: ExecutorRunnerTokenId;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `revokeRunnerToken` (`application/json`, HTTP 200). */
export type RevokeRunnerTokenResult = RunnerTokenMetadata;

// ------------------------------------------------------------------------------------
// scheduleAssignments - POST /work-schedule/reserve/moves
// ------------------------------------------------------------------------------------

/**
 * Schedule Assignments
 *
 * `R-152g`, `R-152h`: move one or several open assignments to a day (`planned_on` absent: «без даты») and, with `assignee_user_uid`, to another active expert (a reassignment in the assignment's history). Each move is a new event with its author; an unchanged date records nothing. Keyed; `role:admin`.
 */
export type ScheduleAssignmentsInput = {
  /** Request body, sent as `application/json`. */
  body: ScheduleAssignmentsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `scheduleAssignments`. */
export type ScheduleAssignmentsResult = void;

// ------------------------------------------------------------------------------------
// searchNorms - GET /norms/search
// ------------------------------------------------------------------------------------

/**
 * Search Norms
 *
 * Text search over the canonical paragraphs of the current norms snapshot (R-112, G-5). `q` is 1-200 characters: an optional designation (`ГОСТ 10140`, `СП 54` -- matched on whole leading tokens, so `СП 54` never finds `СП 542`), an optional clause (`п. 7.1.4`, a dotted-segment prefix) and words (Russian morphology, ranked by `ts_rank_cd`). Unreliable paragraphs never appear. With no current snapshot, or an explicit `norms_snapshot_id` that has never been current, the answer is `422 required_norm_unavailable` with `reference_kind: norms_snapshot` -- never an empty page. A query the statement timeout cancels is `422 validation_failed` with `constraint: norms_search_too_broad`, never an empty or partial page. The cursor is opaque and bound to the query and snapshot; another query or snapshot refuses it, and the result window is capped at 1 000. Every hit carries its `source_attribution` (NORM-Q04); the corpus is internal (D-4.1). Roles: any one role (`role:admin|expert|viewer`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
 */
export type SearchNormsInput = {
  /** Query string parameters. */
  query: {
    /** Opaque continuation token from the previous page's `next_cursor`. Never parsed by a client and never constructed by one. */
    cursor?: Cursor;
    /** Page size. */
    limit?: number;
    norms_snapshot_id?: NormsSnapshotId;
    /** The search text: a designation, a clause, words, or a combination. */
    q: string;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `searchNorms` (`application/json`, HTTP 200). */
export type SearchNormsResult = NormSearchPage;

// ------------------------------------------------------------------------------------
// setCurrentNormSnapshot - PUT /norms/snapshots/current
// ------------------------------------------------------------------------------------

/**
 * Set Current Norm Snapshot
 *
 * Designate a qualifying snapshot as the current one (R-113, G-6), which every new run and re-audit then pins. `expected_current` is the snapshot the caller believes is current (`null` for none); a stale belief is `409 conflict` with `conflict_reason: stale_current_snapshot`. An already-current target answers the current designation as a replay and writes no history row; any other change writes exactly one. A target that does not qualify is `422 required_norm_unavailable` with `reference_kind` `norm_embedding_build` (no complete build) or `norm_source` (a document's PDF has no confirmed binding); an unknown snapshot is `404`. There is no unset. No `Idempotency-Key`: the request is a compare-and-set on durable state. Roles: `admin` (`role:admin`). Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01. W57a may refuse a missing verified retrieval set as 422 required_norm_unavailable with reference_kind norm_retrieval_set; no substitute is selected.
 */
export type SetCurrentNormSnapshotInput = {
  /** Request body, sent as `application/json`. */
  body: SetCurrentNormSnapshotRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setCurrentNormSnapshot` (`application/json`, HTTP 200). */
export type SetCurrentNormSnapshotResult = NormCurrentSnapshot;

// ------------------------------------------------------------------------------------
// setDocumentArchived - PUT /projects/{project_uid}/documents/{document_uid}/archive
// ------------------------------------------------------------------------------------

/**
 * Set Document Archived
 *
 * `UI-PARITY-P0G` (contract 1.22.0, ruling `R-151a`): archive (`archived: true`) or restore (`false`) one document of this project. An archived document is left out of `listDocuments` unless `include_archived` is asked; its versions, runs, findings and decisions are unchanged and stay addressable. Nothing is ever deleted. A document already in the asked state is answered as it is. Every change appends `document.archived` or `document.restored` to the audit trail. `expert` and `admin`; `viewer` is refused.
 */
export type SetDocumentArchivedInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/archive`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: SetDocumentArchivedRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setDocumentArchived` (`application/json`, HTTP 200). */
export type SetDocumentArchivedResult = DocumentVersion;

// ------------------------------------------------------------------------------------
// setDocumentTags - PUT /projects/{project_uid}/documents/{document_uid}/tags
// ------------------------------------------------------------------------------------

/**
 * Set Document Tags
 *
 * `UI-PARITY-P0H` (contract 1.23.0, ruling `R-151e`): replace the document's free tags with the given set (at most ten, each 1 to 40 characters after trimming; inner spaces collapse; a case-insensitive duplicate keeps its first spelling). An empty list removes them all. No order and no group: the original's folders are not built. The same set again changes nothing; a change appends `document.tags_set` to the audit trail. `expert` and `admin`; `viewer` is refused.
 */
export type SetDocumentTagsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/tags`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: SetDocumentTagsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setDocumentTags` (`application/json`, HTTP 200). */
export type SetDocumentTagsResult = DocumentVersion;

// ------------------------------------------------------------------------------------
// setEngineerAbsences - PUT /work-schedule/absences
// ------------------------------------------------------------------------------------

/**
 * Set Engineer Absences
 *
 * `R-152d`: an administrator marks an active expert's days absent or clears them. Every change is kept. Keyed; `role:admin`.
 */
export type SetEngineerAbsencesInput = {
  /** Request body, sent as `application/json`. */
  body: SetEngineerAbsencesRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setEngineerAbsences`. */
export type SetEngineerAbsencesResult = void;

// ------------------------------------------------------------------------------------
// setExecutionPaused - PUT /execution/dispatch
// ------------------------------------------------------------------------------------

/** Set Paused */
export type SetExecutionPausedInput = {
  /** Request body, sent as `application/json`. */
  body: SetExecutionPausedRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutionPaused` (`application/json`, HTTP 200). */
export type SetExecutionPausedResult = ExecutionDispatchStatus;

// ------------------------------------------------------------------------------------
// setExecutorHostEnabled - PUT /executor-hosts/{host_id}/enabled
// ------------------------------------------------------------------------------------

/**
 * Set Executor Host Enabled
 *
 * `HOSTS-SEAL-1`: the «Использовать» switch of a server (`R-149b`: the administrator who connected a server switched it on). Off, the server takes no new run; runs already bound to it finish. Each change is an append-only event with its author and time; setting the value already in force answers the server as it stands. `409 conflict` with `conflict_reason` `host_archived`. `role:admin`, `Idempotency-Key` required.
 */
export type SetExecutorHostEnabledInput = {
  /** Path parameters, substituted into `/executor-hosts/{host_id}/enabled`. */
  path: {
    host_id: ExecutorHostId;
  };
  /** Request body, sent as `application/json`. */
  body: SetExecutorHostEnabledRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutorHostEnabled` (`application/json`, HTTP 200). */
export type SetExecutorHostEnabledResult = ExecutorHost;

// ------------------------------------------------------------------------------------
// setExecutorHostSlots - PUT /executor-hosts/{host_id}/slots
// ------------------------------------------------------------------------------------

/**
 * Set Executor Host Slots
 *
 * `HOSTS-SEAL-1`: how many calls of a provider the server may run at once (1 to 16; default 1 for a subscription, 2 for an API key). A provider the host does not have is `422 validation_failed`. The stand keeps the slots on the host, not on a revision; each change is an append-only event with its author. `409 conflict` with `conflict_reason` `host_archived`. `role:admin`, `Idempotency-Key` required.
 */
export type SetExecutorHostSlotsInput = {
  /** Path parameters, substituted into `/executor-hosts/{host_id}/slots`. */
  path: {
    host_id: ExecutorHostId;
  };
  /** Request body, sent as `application/json`. */
  body: SetExecutorHostSlotsRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutorHostSlots` (`application/json`, HTTP 200). */
export type SetExecutorHostSlotsResult = ExecutorHost;

// ------------------------------------------------------------------------------------
// setExecutorIntegrationAuthorisation - POST /executor-connections/{connection_id}/integration-authorisation
// ------------------------------------------------------------------------------------

/**
 * Set Executor Integration Authorisation
 *
 * Set or clear the administrator's mark that the command-line clients behind a `pull` connection are authorised for this integration (`R-149b`, ADR-0026 decision 8). It is one of four distinct statuses and implies none of the other three; the agent reads authentication only through each client's official mechanism. Returns the connection as it stands. Refusals: `403 permission_denied`; `404 not_found`; `409 conflict` with `conflict_reason` `connection_archived`; `422 validation_failed` with field `kind` and constraint `kind_not_pull`.
 */
export type SetExecutorIntegrationAuthorisationInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/integration-authorisation`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /** Request body, sent as `application/json`. */
  body: SetExecutorIntegrationAuthorisationRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutorIntegrationAuthorisation` (`application/json`, HTTP 200). */
export type SetExecutorIntegrationAuthorisationResult = ExecutorConnection;

// ------------------------------------------------------------------------------------
// setExecutorRoute - PUT /executor-routes
// ------------------------------------------------------------------------------------

/**
 * Set Executor Route
 *
 * Set the Primary and optional Standby of one work kind (`EXEC-SEAL-01`). `EXEC2-SEAL-2` (ADR-0026 decision 17): while the routing mode is `rules` this is refused with `409 conflict` and `conflict_reason` `routing_mode_rules`; roll back to `legacy` with `setExecutorRoutingMode` first.
 */
export type SetExecutorRouteInput = {
  /** Request body, sent as `application/json`. */
  body: SetExecutorRouteRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutorRoute` (`application/json`, HTTP 200). */
export type SetExecutorRouteResult = ExecutorRoute;

// ------------------------------------------------------------------------------------
// setExecutorRoutingMode - POST /executor-routing/mode
// ------------------------------------------------------------------------------------

/**
 * Set Executor Routing Mode
 *
 * Change the routing mode (`EXEC2-SEAL-2`, ADR-0026 decision 17). `rules` is the cut-over: it needs the `preview_digest` that was shown and a `mapping` that confirms each `ready` work kind to be converted, and creates the groups, the rules and the mode in one transaction. `legacy` is the rollback: it takes neither field and does not touch the groups or rules, and work already admitted by rules finishes on its own group revisions and is never read through a legacy route. Each change is journalled. Refusals use existing codes: `422 validation_failed` with field `preview_digest` and constraint `preview_digest_required`, or field `mapping` and constraint `mapping_required`, `mapping_not_accepted`, `mapping_entry_not_ready` or `mapping_work_kind_repeated`; `409 conflict` with `conflict_reason` `routing_mode_unchanged` or `preview_stale`, or `group_name_in_use` for a group name an active group holds. While the mode is `rules`, `setExecutorRoute` answers `409 conflict` with `conflict_reason` `routing_mode_rules`, and a start of a work kind with no rule is `503 dependency_unavailable` with `details.dependency` `no_rule_for_work_kind`. `403 permission_denied` for a caller without `admin`.
 */
export type SetExecutorRoutingModeInput = {
  /** Request body, sent as `application/json`. */
  body: SetExecutorRoutingModeRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutorRoutingMode` (`application/json`, HTTP 200). */
export type SetExecutorRoutingModeResult = ExecutorRoutingModeResult;

// ------------------------------------------------------------------------------------
// setExecutorRoutingRule - PUT /executor-routing-rules/{work_kind}
// ------------------------------------------------------------------------------------

/**
 * Set Executor Routing Rule
 *
 * Point the rule of a work kind at an immutable group revision (`EXEC2-SEAL-2`, ADR-0026 decision 11). Rules are append-only: a change adds a rule revision, and naming the revision that is already current answers the rule as it stands. Work already admitted keeps the rule revision it was admitted on. `404 not_found` for a group revision that does not exist; `409 conflict` with `conflict_reason` `group_archived` for an archived group's revision; `422 validation_failed` for a work kind the enumeration does not name. `403 permission_denied` for a caller without `admin`.
 */
export type SetExecutorRoutingRuleInput = {
  /** Path parameters, substituted into `/executor-routing-rules/{work_kind}`. */
  path: {
    work_kind: ExecutorWorkKind;
  };
  /** Request body, sent as `application/json`. */
  body: SetExecutorRoutingRuleRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutorRoutingRule` (`application/json`, HTTP 200). */
export type SetExecutorRoutingRuleResult = ExecutorRoutingRule;

// ------------------------------------------------------------------------------------
// setExecutorSecret - POST /executor-connections/{connection_id}/secrets
// ------------------------------------------------------------------------------------

/** Set Executor Secret */
export type SetExecutorSecretInput = {
  /** Path parameters, substituted into `/executor-connections/{connection_id}/secrets`. */
  path: {
    connection_id: ExecutorConnectionId;
  };
  /** Request body, sent as `application/json`. */
  body: SetExecutorSecretRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setExecutorSecret` (`application/json`, HTTP 201). */
export type SetExecutorSecretResult = ExecutorSecretMetadata;

// ------------------------------------------------------------------------------------
// setFindingExecutionStatus - PUT /findings/{finding_uid}/execution-status
// ------------------------------------------------------------------------------------

/**
 * Set Finding Execution Status
 *
 * `UI-PARITY-P0I` (contract 1.24.0, ruling `R-151g`): set, or clear with `null`, what the designer did with an accepted finding (the original's SU-10 labels, entered by hand; no registry import). Setting a status on a finding whose current verdict is not `accepted` is `422 validation_failed` (`constraint: finding_not_accepted`); clearing never is. It is not an expert decision: the verdict, the decision journal and every counter are unchanged. The same status again changes nothing; a change appends `finding.execution_status_set` to the audit trail. `expert` only.
 */
export type SetFindingExecutionStatusInput = {
  /** Path parameters, substituted into `/findings/{finding_uid}/execution-status`. */
  path: {
    finding_uid: FindingUid;
  };
  /** Request body, sent as `application/json`. */
  body: SetFindingExecutionStatusRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setFindingExecutionStatus` (`application/json`, HTTP 200). */
export type SetFindingExecutionStatusResult = FindingExecutionState;

// ------------------------------------------------------------------------------------
// setGlobalVendorList - PUT /vendor-lists/{section_code}
// ------------------------------------------------------------------------------------

/**
 * Set Global Vendor List
 *
 * Set a section's global vendor list as a whole new immutable revision with its author and time; an empty list is an explicit "no restriction". An exact repeat of the latest revision writes nothing and answers it. With `expected_vendor_list_id` present (`null`: no revision was read), a different latest revision is `409 conflict` with `conflict_reason: vendor_list_changed` and nothing is written. A section code outside the fifteen addresses no vendor list and is `404`. `admin` is required (`required_capability: role:admin`).
 */
export type SetGlobalVendorListInput = {
  /** Path parameters, substituted into `/vendor-lists/{section_code}`. */
  path: {
    section_code: ProjectSection;
  };
  /** Request body, sent as `application/json`. */
  body: SetGlobalVendorListRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setGlobalVendorList` (`application/json`, HTTP 200). */
export type SetGlobalVendorListResult = VendorListRevision;

// ------------------------------------------------------------------------------------
// setJobPriority - PUT /execution/queue/{job_id}/priority
// ------------------------------------------------------------------------------------

/** Set Priority */
export type SetJobPriorityInput = {
  /** Path parameters, substituted into `/execution/queue/{job_id}/priority`. */
  path: {
    job_id: JobId;
  };
  /** Request body, sent as `application/json`. */
  body: SetJobPriorityRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setJobPriority` (`application/json`, HTTP 200). */
export type SetJobPriorityResult = ExecutionQueueItem;

// ------------------------------------------------------------------------------------
// setProjectVendorList - PUT /projects/{project_uid}/vendor-lists/{section_code}
// ------------------------------------------------------------------------------------

/**
 * Set Project Vendor List
 *
 * Set the project's own vendor list for a section (`mode: list`, possibly empty: no restriction for this project) or remove it (`mode: inherit`, `entries: []`), as a new immutable revision with its author and time; the answer is the section's state for the project afterwards. An exact repeat writes nothing; an `inherit` with no override in force writes nothing. Entries with `inherit` are `422` (`constraint: inherit_has_no_entries`); a stale `expected_vendor_list_id` is `409` (`conflict_reason: vendor_list_changed`). `expert` is required (`admin` alone is `permission_denied`); an unknown project is `404`.
 */
export type SetProjectVendorListInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/vendor-lists/{section_code}`. */
  path: {
    project_uid: ProjectUid;
    section_code: ProjectSection;
  };
  /** Request body, sent as `application/json`. */
  body: SetProjectVendorListRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setProjectVendorList` (`application/json`, HTTP 200). */
export type SetProjectVendorListResult = SectionVendorList;

// ------------------------------------------------------------------------------------
// setStageModelLayoutEnabled - PUT /model-layout/enabled
// ------------------------------------------------------------------------------------

/**
 * Set Stage Model Layout Enabled
 *
 * `HOSTS-SEAL-1`: the switch «Модели по этапам: включены». On, runs started from now on take the layout; off, they follow the route as before. It needs a revision (`409 conflict` with `conflict_reason` `no_layout_revision`) and the database provider source (`409 conflict` with `conflict_reason` `provider_source_not_database`). Read only at the start of a run, so switching off breaks no run in progress. Each change is an append-only event with its author. `role:admin`, `Idempotency-Key` required.
 */
export type SetStageModelLayoutEnabledInput = {
  /** Request body, sent as `application/json`. */
  body: SetStageModelLayoutEnabledRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setStageModelLayoutEnabled` (`application/json`, HTTP 200). */
export type SetStageModelLayoutEnabledResult = StageModelLayout;

// ------------------------------------------------------------------------------------
// setStagePairCompleteness - POST /stage-pairs/{stage_pair_id}/completeness
// ------------------------------------------------------------------------------------

/** Set Stage Pair Completeness */
export type SetStagePairCompletenessInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/completeness`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Request body, sent as `application/json`. */
  body: SetStagePairCompletenessRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setStagePairCompleteness` (`application/json`, HTTP 200). */
export type SetStagePairCompletenessResult = StagePair;

// ------------------------------------------------------------------------------------
// setVectorPaused - PUT /vector-control/paused
// ------------------------------------------------------------------------------------

/**
 * Set Vector Paused
 *
 * `CRIT-SEAL-50` (plan-v5 section 5): pause the vectors or resume them. On a pause the night window does not start and the queue keeps filling. Each change is an append-only event with its actor and time; setting the value already in force answers the control as it stands. `role:admin`, `Idempotency-Key` required.
 */
export type SetVectorPausedInput = {
  /** Request body, sent as `application/json`. */
  body: SetVectorPausedRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setVectorPaused` (`application/json`, HTTP 200). */
export type SetVectorPausedResult = VectorControl;

// ------------------------------------------------------------------------------------
// setWorkCalendarDays - PUT /work-calendar/days
// ------------------------------------------------------------------------------------

/**
 * Set Work Calendar Days
 *
 * `R-152d`: the administrator makes days days off (`day_off`) or working days (`workday`), or returns them to the week's rule (`default`). Every change is kept. Keyed; `role:admin`.
 */
export type SetWorkCalendarDaysInput = {
  /** Request body, sent as `application/json`. */
  body: SetWorkCalendarDaysRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setWorkCalendarDays`. */
export type SetWorkCalendarDaysResult = void;

// ------------------------------------------------------------------------------------
// setWorkSchedulePlans - PUT /work-schedule/plans
// ------------------------------------------------------------------------------------

/**
 * Set Work Schedule Plans
 *
 * `R-151x`, `R-152a`: an administrator sets engineers' plans (0..999) for one month; each change is kept in the plan's history, an unchanged plan records nothing, a user who is not an active expert is `422` (`constraint: active_expert`). Answers the month. Keyed; `role:admin`.
 */
export type SetWorkSchedulePlansInput = {
  /** Request body, sent as `application/json`. */
  body: SetWorkSchedulePlansRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setWorkSchedulePlans` (`application/json`, HTTP 200). */
export type SetWorkSchedulePlansResult = WorkScheduleMonth;

// ------------------------------------------------------------------------------------
// setWorkScheduleSettings - PUT /work-schedule/settings
// ------------------------------------------------------------------------------------

/**
 * Set Work Schedule Settings
 *
 * `R-152b`: the default monthly plan of an engineer without one (0..999, initially 20) and the IANA time zone the schedule's days are cut in (`constraint: unknown_zone` for another). Keyed; `role:admin`.
 */
export type SetWorkScheduleSettingsInput = {
  /** Request body, sent as `application/json`. */
  body: WorkScheduleSettings;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setWorkScheduleSettings` (`application/json`, HTTP 200). */
export type SetWorkScheduleSettingsResult = WorkScheduleSettings;

// ------------------------------------------------------------------------------------
// setWorkerIntake - PUT /execution/workers/{worker_id}/intake
// ------------------------------------------------------------------------------------

/** Set Worker Intake */
export type SetWorkerIntakeInput = {
  /** Path parameters, substituted into `/execution/workers/{worker_id}/intake`. */
  path: {
    worker_id: WorkerId;
  };
  /** Request body, sent as `application/json`. */
  body: SetWorkerIntakeRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `setWorkerIntake` (`application/json`, HTTP 200). */
export type SetWorkerIntakeResult = ExecutionWorker;

// ------------------------------------------------------------------------------------
// startComparisonAiPairCheck - POST /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check
// ------------------------------------------------------------------------------------

/**
 * Start the AI check of the doubtful pairs of a document set.
 *
 * Starts a job (`pair_check`) that asks the model, one question per call, whether a candidate is the same sheet. The start carries the consent: the digest of the estimate that was shown and the explicit confirmation (`ADR-0025` decision 19). A digest that is not the one now computed is `409 conflict` (`comparison_estimate_stale`); a consent that is missing or not confirmed is `422 validation_failed` (`comparison_consent_required`); an estimate over the USD 10 ceiling of one job or the USD 50 ceiling of the installation's day is `409 conflict` (`comparison_ceiling_job`, `comparison_ceiling_day`), and a connection that is not metered has no ceiling; a live job for the same scope is `409 conflict` (`comparison_ai_job_active`); a work kind with no route in «Назначения» is `503 dependency_unavailable` (`executor_route_missing`). Nothing is sent to a model before the consent and the estimate agree, and the text of the answer is model output not confirmed by an engineer. An answer is accepted as an AI link only with high confidence, an agreeing candidate number and page, a sheet outside a multi-sheet specification, a B that no other A claims and a reverse question that returns A with high confidence; any other answer is a hint, and a manual edit always wins. An accepted answer is written as an accepted AI link by the service and never by this call. An unknown project, or a document of another project, is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AIPAIR-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_pairs`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StartComparisonAiPairCheckInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: StartComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startComparisonAiPairCheck` (`application/json`, HTTP 201). */
export type StartComparisonAiPairCheckResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// startComparisonAiSheetChanges - POST /comparison-series/{comparison_series_id}/ai-sheet-changes
// ------------------------------------------------------------------------------------

/**
 * Start the AI description of changes of a series.
 *
 * Queues a job (`sheet_changes`) in the installation's AI queue, one series at a time; it describes the changed sheets of every transition, per sheet a packet of tables, places and shifts with the crops and words around them, and the answer is checked by the program (tiers `from_text`, `from_image`, `unverified`). With `restart` true every sheet is described again (a sheet whose content, prompt version and model did not change keeps its stored answer). The start carries the consent: the digest of the estimate that was shown and the explicit confirmation (`ADR-0025` decision 19). A digest that is not the one now computed is `409 conflict` (`comparison_estimate_stale`); a consent that is missing or not confirmed is `422 validation_failed` (`comparison_consent_required`); an estimate over the USD 10 ceiling of one job or the USD 50 ceiling of the installation's day is `409 conflict` (`comparison_ceiling_job`, `comparison_ceiling_day`), and a connection that is not metered has no ceiling; a live job for the same scope is `409 conflict` (`comparison_ai_job_active`); a work kind with no route in «Назначения» is `503 dependency_unavailable` (`executor_route_missing`). Nothing is sent to a model before the consent and the estimate agree, and the text of the answer is model output not confirmed by an engineer. An unknown series is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StartComparisonAiSheetChangesInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/ai-sheet-changes`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /** Request body, sent as `application/json`. */
  body: StartComparisonAiSheetChangesRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startComparisonAiSheetChanges` (`application/json`, HTTP 201). */
export type StartComparisonAiSheetChangesResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// startComparisonReport - POST /comparison-reports/{comparison_report_id}/start
// ------------------------------------------------------------------------------------

/**
 * Start a report draft.
 *
 * Starts the model work of a `draft` report: for the client kind one call per transition over the facts of the summary with discipline priorities, where a program check drops every point whose number, mark or direction the facts do not confirm; for the analytic kind an analyst, a verifier and a composer. The PDF is written by a program. The start carries the consent: the digest of the estimate that was shown and the explicit confirmation (`ADR-0025` decision 19). A digest that is not the one now computed is `409 conflict` (`comparison_estimate_stale`); a consent that is missing or not confirmed is `422 validation_failed` (`comparison_consent_required`); an estimate over the USD 10 ceiling of one job or the USD 50 ceiling of the installation's day is `409 conflict` (`comparison_ceiling_job`, `comparison_ceiling_day`), and a connection that is not metered has no ceiling; a live job for the same scope is `409 conflict` (`comparison_ai_job_active`); a work kind with no route in «Назначения» is `503 dependency_unavailable` (`executor_route_missing`). Nothing is sent to a model before the consent and the estimate agree, and the text of the answer is model output not confirmed by an engineer. A report that is not a draft is `409 conflict` (`comparison_report_state`). An unknown report is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StartComparisonReportInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/start`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /** Request body, sent as `application/json`. */
  body: StartComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startComparisonReport` (`application/json`, HTTP 200). */
export type StartComparisonReportResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// startComparisonSeries - POST /projects/{project_uid}/documents/{document_uid}/comparison-series
// ------------------------------------------------------------------------------------

/**
 * Start the comparison of every adjacent pair of versions.
 *
 * «Запустить» and «Заново»: compares every adjacent pair of the versions of a document set for the current comparison order (`ADR-0025` decisions 15 and 21), one transition per pair, as durable comparison work. With `restart` true every transition is computed again; sheet pairs whose content did not change are taken from the result cache of the project. `base_order_revision_no` is the revision of the version order the caller saw (`0` for none); a stale one is `409 conflict` (`comparison_version_order_stale`). A series that is still running for the document set is `409 conflict` (`comparison_series_active`). A pair of versions that are not adjacent in the order is never compared. A matrix that is not `ready` (absent, building, stale or failed) is `409 conflict` (`comparison_matrix_stale`); a document set of one version has nothing to compare and is `422 validation_failed` (`comparison_versions_few`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). An unknown project, or a document of another project, is `404`. Served by `CMP-SERIES-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_series`) until the lane wired it.
 */
export type StartComparisonSeriesInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-series`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: StartComparisonSeriesRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startComparisonSeries` (`application/json`, HTTP 201). */
export type StartComparisonSeriesResult = ComparisonSeries;

// ------------------------------------------------------------------------------------
// startComparisonSheetDescription - POST /comparison-sheet-pairs/{comparison_sheet_pair_id}/description
// ------------------------------------------------------------------------------------

/**
 * Describe one sheet with the AI.
 *
 * «Передать и описать»: a job (`sheet_changes`) for one sheet pair, or for one added or removed sheet, cancelled with `cancelComparisonAiSheetChanges`. The start carries the consent: the digest of the estimate that was shown and the explicit confirmation (`ADR-0025` decision 19). A digest that is not the one now computed is `409 conflict` (`comparison_estimate_stale`); a consent that is missing or not confirmed is `422 validation_failed` (`comparison_consent_required`); an estimate over the USD 10 ceiling of one job or the USD 50 ceiling of the installation's day is `409 conflict` (`comparison_ceiling_job`, `comparison_ceiling_day`), and a connection that is not metered has no ceiling; a live job for the same scope is `409 conflict` (`comparison_ai_job_active`); a work kind with no route in «Назначения» is `503 dependency_unavailable` (`executor_route_missing`). Nothing is sent to a model before the consent and the estimate agree, and the text of the answer is model output not confirmed by an engineer. An unknown sheet pair is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StartComparisonSheetDescriptionInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}/description`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /** Request body, sent as `application/json`. */
  body: StartComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startComparisonSheetDescription` (`application/json`, HTTP 201). */
export type StartComparisonSheetDescriptionResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// startComparisonSpecification - POST /comparison-transitions/{comparison_transition_id}/specification
// ------------------------------------------------------------------------------------

/**
 * Start the comparison of the whole specifications of a transition.
 *
 * Starts a job (`spec`) that has a model mark the structure of the whole specification of each version (the program copies the cells and checks the coverage, the quotes and the values) and then compares the two order-independently. A side that cannot be read completely makes the comparison `incomplete` and no addition, removal or absence of change is published. The start carries the consent: the digest of the estimate that was shown and the explicit confirmation (`ADR-0025` decision 19). A digest that is not the one now computed is `409 conflict` (`comparison_estimate_stale`); a consent that is missing or not confirmed is `422 validation_failed` (`comparison_consent_required`); an estimate over the USD 10 ceiling of one job or the USD 50 ceiling of the installation's day is `409 conflict` (`comparison_ceiling_job`, `comparison_ceiling_day`), and a connection that is not metered has no ceiling; a live job for the same scope is `409 conflict` (`comparison_ai_job_active`); a work kind with no route in «Назначения» is `503 dependency_unavailable` (`executor_route_missing`). Nothing is sent to a model before the consent and the estimate agree, and the text of the answer is model output not confirmed by an engineer. An unknown transition is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-SPEC-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_specification`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StartComparisonSpecificationInput = {
  /** Path parameters, substituted into `/comparison-transitions/{comparison_transition_id}/specification`. */
  path: {
    comparison_transition_id: ComparisonTransitionId;
  };
  /** Request body, sent as `application/json`. */
  body: StartComparisonAiJobRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startComparisonSpecification` (`application/json`, HTTP 201). */
export type StartComparisonSpecificationResult = ComparisonAiJob;

// ------------------------------------------------------------------------------------
// startOptimisationPass - POST /projects/{project_uid}/documents/{document_uid}/optimisation-passes
// ------------------------------------------------------------------------------------

/**
 * Start Optimisation Pass
 *
 * Start the optimisation pass of the document set's current version, classified by an expert in any of the fifteen sections. The pass pins the version, its newest published run and that run's saved text layer, the project's current price-list revision and the effective vendor list of the version's own section (the project's own, else the administrator's), reads the specification, matches it against the price list and stores the deterministic proposals `cheaper_analog`: for a row matched to exactly one position, another position of the same revision in the same unit and currency, with a lower unit price, from a vendor on the list, of the same kind of product (at most three per row). The saving is `(current − proposed) × quantity` and is absent when the row's quantity is not a plain number. `expert` is required (`admin` alone is `permission_denied`). A precondition that is not met is `409 conflict` with `conflict_reason` `version_unclassified`, `price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large` or `vendor_list_missing` (neither the project nor the administrator keeps a vendor list for the version's section) and nothing is written, not even the key; `section_not_ar` stays among the registered reasons and is no longer produced for a confirmed section; an unknown project or a set of another project is `404`. An exact repeat of the `Idempotency-Key` answers the stored pass, the same key for another set or caller is `409 idempotency_key_reuse`, and a new key over exactly the same inputs answers the pass already stored instead of writing a second one.
 */
export type StartOptimisationPassInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/optimisation-passes`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startOptimisationPass` (`application/json`, HTTP 201). */
export type StartOptimisationPassResult = OptimisationPass;

// ------------------------------------------------------------------------------------
// startRun - POST /runs
// ------------------------------------------------------------------------------------

/**
 * Start a text-consistency run over one published version.
 *
 * PD-03, in the subset PC-01 exercises. A new idempotency key creates a run. The same key with the same payload returns the existing run and creates nothing, whatever state that run is in, terminal included. The same key with a different payload returns `idempotency_key_reuse` and creates nothing. A new key over a terminal run creates a new run and leaves the terminal one exactly as it was: a terminal run is never reopened.
 *
 * A version whose recorded text is larger than the most a run takes (the analysis input budget of one model call times the number of windows a run may use) is refused up front with `422 analysis_input_budget_exceeded` and no run exists (R-118). A version published before the portal-bundle upload has no recorded count and is not refused by this rule.
 *
 * `W59-SECTION-SEAL-01`: the run's analysis profile is routed from the version's persisted classification through the section-keyed profile registry -- never from a file name, a suggestion or the document's legacy `section`, and never by a file-name fallback. A confirmed АР version resolves the new original-source АР text profile. A version with no classification is refused with `422 version_classification_required`; a confirmed section with no registered text profile is refused with `422 section_profile_unavailable` (`BETA-CONTRACT-SEAL-01`, `D-179`: both used to be `required_norm_unavailable` told apart by `details.reference_kind`). Neither carries details, and both refusals precede the key's claim, so nothing is written. An existing run keeps the profile it pinned.
 *
 * `EXEC-PAR-START-01`: the optional `executor_connection_id` names the connection the run must be on. Absent, the run follows the global route (and its standby rule) exactly as before. Present, the run freezes that connection's current revision if this release serves it, its current key has a passing probe and it is not archived; otherwise the start is refused before the key is claimed, so no run, command record or event exists: `422 validation_failed` with `details.field` `executor_connection_id` for an unknown or malformed id, `503 dependency_unavailable` with `details.dependency` `executor_connection` for a connection that cannot serve now. A named connection never falls back to the route's standby or to another connection. The choice is part of the payload the idempotency key is compared by: the same key with another connection is `idempotency_key_reuse`.
 *
 * `ANALYSIS-PRESETS-01`: the optional `preset_id` names a saved preset instead of a connection. Its current revision is read in the start's transaction and its executor connection is applied exactly as if `executor_connection_id` had named it, so every refusal of that field applies unchanged; the run records the preset revision and `RunStatus.preset` shows it. `422 validation_failed` with `details.field` `preset_id` refuses an unknown preset (`unknown_preset`) and a preset together with `executor_connection_id` (`conflicts_with_executor_connection_id`); `409 conflict` with `details.conflict_reason` `preset_archived` refuses an archived one. All three precede the key's claim, so nothing is written. The preset, not the connection it resolved to, is part of the payload the idempotency key is compared by: a retry after an administrator revised the preset replays the run that exists, and the same key with a hand-chosen connection is `idempotency_key_reuse`. `reauditRun` records no preset.
 *
 * `EXEC2-SEAL-2` (ADR-0026 decisions 12 to 17): the optional `executor_group_id` names an executor group instead of a connection or a preset. The group's current revision is read in the start's transaction and the run is admitted with `binding_state` `pending`: admission freezes the group revision, the planned model (`RunStatus.planned`) and the cost consent, and no connection; dispatch chooses a member and writes the connection revision once, in the worker's claim transaction (`RunStatus.binding`). It is exclusive with `executor_connection_id` and `preset_id` (`422 validation_failed` with `details.field` `executor_group_id` and constraint `conflicts_with_executor_connection_id` or `conflicts_with_preset_id`); an unknown group is `unknown_executor_group`; a run in the `environment` provider source refuses a group (`environment_source`); an archived group is `409 conflict` with `conflict_reason` `group_archived`. All precede the key's claim, so nothing is written. While the routing mode is `rules`, a start that names no connection, group or preset is admitted on the rule of the `text_analysis` work kind; a work kind with no rule is `503 dependency_unavailable` with `details.dependency` `no_rule_for_work_kind`. The group, not the connection it will choose, is part of the payload the idempotency key is compared by. While a run waits for an executor it reports `wait_reason` and `waiting_since`.
 *
 * `HOSTS-SEAL-1` (ADR-0028): while the stage layout is switched on (`setStageModelLayoutEnabled`) the run is started on the **plan** the layout freezes for it, bound cell by cell at dispatch, and the explicit executor selectors (`executor_connection_id`, `preset_id`, `executor_group_id`) are `422 validation_failed` with constraint `stage_layout_enabled`. The consent is the same `{estimate_digest, ceiling_micros, confirmed}`: its estimate (`estimateRunCost`, or `getRunStartReadiness` which carries its digest) binds the digest of the plan and, per model, the digest of the rates and the access; if the access changed between the read and the start the answer is `422 analysis_input_invalid` with `details.reason` `cost_estimate_binding_changed` (before the key is claimed) and the client reads again. When every cell runs on a subscription the estimate is 0 and the press of the button is the consent. A cell no server can serve leaves the run `pending` with `wait_reason` `model_unavailable`, and after 30 minutes `no_executor_online`; nothing has run. With the layout off the run follows the route as before.
 */
export type StartRunInput = {
  /** Request body, sent as `application/json`. */
  body: StartRunRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startRun` (`application/json`, HTTP 202). */
export type StartRunResult = RunStatus;

// ------------------------------------------------------------------------------------
// startRunFromStage - POST /runs/{run_id}/start-from-stage
// ------------------------------------------------------------------------------------

/**
 * Start Run From Stage
 *
 * `R-151i` (`UI-A-60`): a NEW run of the earlier run's document version that reuses the earlier run's completed outputs of every PC-01 stage before `stage_id` and computes `stage_id` and the stages after it. The earlier run is immutable history and is not changed; the new run is linked to it by `started_from_run_id` and `start_stage_id` on its `RunStatus` (not by `reaudit_of_run_id`) and records today's configuration, exactly as a re-audit does (R-82). `stage_id` is one of `page_geometry_extraction`, `document_context_build` or `text_analysis`: the first stage reuses nothing (`422 validation_failed`, `field` `stage_id`, `constraint` `nothing_to_reuse`; use `reauditRun`) and any other stage is not startable (`constraint` `stage_not_startable`). The earlier run must have ended (`409 state_transition_not_allowed`). A stage output that cannot be taken is `422 analysis_input_invalid` with `details.stage_id` (the first stage that cannot) and `details.reason`: `source_stage_not_completed`, `source_stage_version_changed`, `source_stage_output_incomplete`, `source_artifact_unavailable`, `source_artifact_changed` or `source_stage_inputs_changed`. Nothing is recomputed in place of a refused output and nothing is written. Served starts require fresh confirmed cost consent from estimateRunCost with `start_from_run_id` and `start_stage_id`: the price is for the stages the new run computes, and the digest is bound to this earlier run and stage. While a run from this earlier run and stage has not ended, a second is `409 conflict`. Accepted keys replay their recorded outcome.
 *
 * `HOSTS-SEAL-1` (ADR-0028): while the stage layout is switched on, the new run takes **today's** plan and the consent v2 of `startRun`; only the PC-01 stages that use no model are reused from the earlier run. With the layout off it is what it was.
 */
export type StartRunFromStageInput = {
  /** Path parameters, substituted into `/runs/{run_id}/start-from-stage`. */
  path: {
    run_id: RunId;
  };
  /** Request body, sent as `application/json`. */
  body: StartRunFromStageRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startRunFromStage` (`application/json`, HTTP 202). */
export type StartRunFromStageResult = RunStatus;

// ------------------------------------------------------------------------------------
// startStageChainBatch - POST /projects/{project_uid}/stage-chain-batches
// ------------------------------------------------------------------------------------

/** Start Batch */
export type StartStageChainBatchInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/stage-chain-batches`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: StartStageChainBatchRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startStageChainBatch` (`application/json`, HTTP 201). */
export type StartStageChainBatchResult = StageChainBatch;

// ------------------------------------------------------------------------------------
// startStageChainRun - POST /stage-pairs/{stage_pair_id}/chain-runs
// ------------------------------------------------------------------------------------

/** Start Stage Chain Run */
export type StartStageChainRunInput = {
  /** Path parameters, substituted into `/stage-pairs/{stage_pair_id}/chain-runs`. */
  path: {
    stage_pair_id: StagePairId;
  };
  /** Request body, sent as `application/json`. */
  body: StartStageChainRunRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `startStageChainRun` (`application/json`, HTTP 201). */
export type StartStageChainRunResult = StageChainRun;

// ------------------------------------------------------------------------------------
// streamComparisonPairTile - GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/tile
// ------------------------------------------------------------------------------------

/**
 * Stream one tile PNG of a sheet pair.
 *
 * One tile of the pair's overlay (`mode` `overlay`: the older and the newer page on one canvas with the difference layers chosen by the `layers` parameter, a comma-separated list of layer names (`main`, `light_elements`, `color_change`, `line_style`, `moved`, `within_tolerance`, `noise`, `service_zones`)) or of the older (`a`) or newer (`b`) page alone, at the pyramid `level`, `column` and `row` (structural bounds 0..12 and 0..4095). When a level is reduced the maximum of the difference masks is kept, so a small change survives zooming. `align_blocks` aligns the recognised blocks of the newer page onto the older one without changing the PDF. The API never loads PDFium: it reduces what the worker stored. A pair, a mask or a tile that does not exist is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Served by `CMP-VIEWER-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_pair_tiles`) until the lane wired it.
 */
export type StreamComparisonPairTileInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}/tile`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /** Query string parameters. */
  query: {
    align_blocks?: boolean;
    column: number;
    layers?: string;
    level: number;
    mode: ComparisonPairTileMode;
    row: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamComparisonPairTile` (`image/png`, HTTP 200). */
export type StreamComparisonPairTileResult = Blob;

// ------------------------------------------------------------------------------------
// streamComparisonReportPdf - GET /comparison-reports/{comparison_report_id}/pdf
// ------------------------------------------------------------------------------------

/**
 * Download the PDF of a report.
 *
 * «Скачать PDF»: the report's PDF, written by a program with an embedded Cyrillic font; every page carries the label that the text is model output not confirmed by an engineer and the recall line. A report without a PDF is `409 conflict` (`comparison_report_state`). An unknown report is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StreamComparisonReportPdfInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/pdf`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamComparisonReportPdf` (`application/pdf`, HTTP 200). */
export type StreamComparisonReportPdfResult = Blob;

// ------------------------------------------------------------------------------------
// streamComparisonReportSourceMd - GET /comparison-reports/{comparison_report_id}/source-md
// ------------------------------------------------------------------------------------

/**
 * Download the MD a report was built from.
 *
 * «Исходный MD» and «Скачать MD»: the exact bytes of the summary the report was built from. An unknown report is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StreamComparisonReportSourceMdInput = {
  /** Path parameters, substituted into `/comparison-reports/{comparison_report_id}/source-md`. */
  path: {
    comparison_report_id: ComparisonReportId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamComparisonReportSourceMd` (`text/markdown`, HTTP 200). */
export type StreamComparisonReportSourceMdResult = string;

// ------------------------------------------------------------------------------------
// streamComparisonSeriesSummary - GET /comparison-series/{comparison_series_id}/summary-md
// ------------------------------------------------------------------------------------

/**
 * Download the MD summary of a series.
 *
 * «Сводка изменений (MD)»: the deterministic Markdown summary of the series, per transition and per sheet with the pages of both versions, the main change text, the count of open questions and the «Реестр» of categories (computed by the engine, only service zones, described by the AI, whole specification, ambiguous, not processed); the same bytes for the same data. A transition whose pairs depend on an accepted AI link is marked. It is available after a sheet is described or a specification is compared, otherwise `409 conflict` (`comparison_summary_unavailable`). An unknown series is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StreamComparisonSeriesSummaryInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/summary-md`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamComparisonSeriesSummary` (`text/markdown`, HTTP 200). */
export type StreamComparisonSeriesSummaryResult = string;

// ------------------------------------------------------------------------------------
// streamComparisonSheetDescriptionMd - GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description/md
// ------------------------------------------------------------------------------------

/**
 * Download the AI description of a sheet as Markdown.
 *
 * «MD листа»: the stored description of the sheet pair as UTF-8 Markdown. A sheet with no stored description is `409 conflict` (`comparison_description_missing`). An unknown sheet pair is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-AISHEET-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_ai_sheets`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type StreamComparisonSheetDescriptionMdInput = {
  /** Path parameters, substituted into `/comparison-sheet-pairs/{comparison_sheet_pair_id}/description/md`. */
  path: {
    comparison_sheet_pair_id: ComparisonSheetPairId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamComparisonSheetDescriptionMd` (`text/markdown`, HTTP 200). */
export type StreamComparisonSheetDescriptionMdResult = string;

// ------------------------------------------------------------------------------------
// streamComparisonTechnicalReport - GET /comparison-series/{comparison_series_id}/technical-report
// ------------------------------------------------------------------------------------

/** Stream Technical Report */
export type StreamComparisonTechnicalReportInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/technical-report`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /** Query string parameters. */
  query?: {
    format?: "xlsx" | "html";
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamComparisonTechnicalReport` (`application/octet-stream`, HTTP 200). */
export type StreamComparisonTechnicalReportResult = Blob;

// ------------------------------------------------------------------------------------
// streamDocumentVersionContent - GET /versions/{version_uid}/content
// ------------------------------------------------------------------------------------

/**
 * Stream the PDF bytes for the viewer.
 *
 * The server streams the bytes itself. It does not redirect and does not return a presigned link: a URL into object storage is exactly the internal address the contract forbids putting in a response, and it would also outlive the request that authorized it.
 */
export type StreamDocumentVersionContentInput = {
  /** Path parameters, substituted into `/versions/{version_uid}/content`. */
  path: {
    version_uid: VersionUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
  /** Additional declared request headers. */
  headers?: {
    /** Byte range, so the viewer can page a large document without fetching all of it. */
    'Range'?: string;
  };
};

/** Success body of `streamDocumentVersionContent` (`application/pdf`, HTTP 200/206). */
export type StreamDocumentVersionContentResult = Blob;

// ------------------------------------------------------------------------------------
// streamNormDocumentContent - GET /norm-documents/{norm_document_id}/content
// ------------------------------------------------------------------------------------

/**
 * Stream Norm Document Content
 *
 * The document's source PDF, streamed by the server in chunks; never a redirect or a storage link. One `Range` is honoured with `206` and `Content-Range`; an unsatisfiable range is `422`. Served only through a confirmed custody binding; a document without one is `422 required_norm_unavailable` with `reference_kind: norm_source`. A full read verifies the bytes while streaming and stops short on a mismatch (R-115). Roles: any one role (`role:admin|expert|viewer`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
 */
export type StreamNormDocumentContentInput = {
  /** Path parameters, substituted into `/norm-documents/{norm_document_id}/content`. */
  path: {
    norm_document_id: NormDocumentId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
  /** Additional declared request headers. */
  headers?: {
    /** Byte range, so the viewer can page a large document without fetching all of it. */
    'Range'?: string;
  };
};

/** Success body of `streamNormDocumentContent` (`application/pdf`, HTTP 200/206). */
export type StreamNormDocumentContentResult = Blob;

// ------------------------------------------------------------------------------------
// streamStageChangeJournalHtml - GET /stage-chain-runs/{stage_chain_run_id}/journal.html
// ------------------------------------------------------------------------------------

/** Journal Html */
export type StreamStageChangeJournalHtmlInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/journal.html`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamStageChangeJournalHtml` (`text/html`, HTTP 200). */
export type StreamStageChangeJournalHtmlResult = Blob;

// ------------------------------------------------------------------------------------
// streamStageChangeJournalPdf - GET /stage-chain-runs/{stage_chain_run_id}/journal.pdf
// ------------------------------------------------------------------------------------

/** Journal Pdf */
export type StreamStageChangeJournalPdfInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/journal.pdf`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamStageChangeJournalPdf` (`application/pdf`, HTTP 200). */
export type StreamStageChangeJournalPdfResult = Blob;

// ------------------------------------------------------------------------------------
// streamStageChangeJournalXlsx - GET /stage-chain-runs/{stage_chain_run_id}/journal.xlsx
// ------------------------------------------------------------------------------------

/** Journal Xlsx */
export type StreamStageChangeJournalXlsxInput = {
  /** Path parameters, substituted into `/stage-chain-runs/{stage_chain_run_id}/journal.xlsx`. */
  path: {
    stage_chain_run_id: StageChainRunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamStageChangeJournalXlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, HTTP 200). */
export type StreamStageChangeJournalXlsxResult = Blob;

// ------------------------------------------------------------------------------------
// streamVersionPagePreview - GET /page-profiles/{comparison_page_profile_id}/preview
// ------------------------------------------------------------------------------------

/**
 * Stream the stored preview PNG of one page.
 *
 * The bytes the worker stored, with no redirect and no link. A page that has no preview is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-PROFILE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: version_pages`) and nothing is read or written.
 */
export type StreamVersionPagePreviewInput = {
  /** Path parameters, substituted into `/page-profiles/{comparison_page_profile_id}/preview`. */
  path: {
    comparison_page_profile_id: ComparisonPageProfileId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamVersionPagePreview` (`image/png`, HTTP 200). */
export type StreamVersionPagePreviewResult = Blob;

// ------------------------------------------------------------------------------------
// streamVersionPageThumbnail - GET /page-profiles/{comparison_page_profile_id}/thumbnail
// ------------------------------------------------------------------------------------

/**
 * Stream the stored thumbnail PNG of one page.
 *
 * The bytes the worker stored, with no redirect and no link. A page that has no thumbnail is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-PROFILE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: version_pages`) and nothing is read or written.
 */
export type StreamVersionPageThumbnailInput = {
  /** Path parameters, substituted into `/page-profiles/{comparison_page_profile_id}/thumbnail`. */
  path: {
    comparison_page_profile_id: ComparisonPageProfileId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamVersionPageThumbnail` (`image/png`, HTTP 200). */
export type StreamVersionPageThumbnailResult = Blob;

// ------------------------------------------------------------------------------------
// streamVersionPageTile - GET /page-profiles/{comparison_page_profile_id}/tile
// ------------------------------------------------------------------------------------

/**
 * Stream one tile PNG of a page's bounded pyramid.
 *
 * One tile of the bounded pyramid rendered in the worker's child process (`ADR-0025` decision 9), addressed by the query parameters `level`, `column` and `row` (structural bounds 0..12 and 0..4095); whether a level is stored or rendered again on request is `CMP-PROFILE-01`'s to decide, and the address is the same. A tile that does not exist is `404`. Any one role (`role:admin|expert|viewer`, `R-80`). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-PROFILE-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: version_pages`) and nothing is read or written.
 */
export type StreamVersionPageTileInput = {
  /** Path parameters, substituted into `/page-profiles/{comparison_page_profile_id}/tile`. */
  path: {
    comparison_page_profile_id: ComparisonPageProfileId;
  };
  /** Query string parameters. */
  query: {
    column: number;
    level: number;
    row: number;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamVersionPageTile` (`image/png`, HTTP 200). */
export type StreamVersionPageTileResult = Blob;

// ------------------------------------------------------------------------------------
// streamVersionPortalBlockCrop - GET /versions/{version_uid}/portal-blocks/{portal_block_id}/crop
// ------------------------------------------------------------------------------------

/**
 * Stream the PNG this product cut for one IMAGE block.
 *
 * The server streams the bytes itself, with no redirect and no link. The image is the clip of the PDF page that the portal's block describes, rendered by this product and verified against its recorded SHA-256 before it is returned; it is never fetched from the portal. A version, a block or a crop that does not exist, a block that is not an IMAGE block, and a block on a page marked `geometry_mismatch` are all `404`: the caller's question is the same, there is no such image. Roles: any one role (`R-80`).
 */
export type StreamVersionPortalBlockCropInput = {
  /** Path parameters, substituted into `/versions/{version_uid}/portal-blocks/{portal_block_id}/crop`. */
  path: {
    portal_block_id: PortalBlockId;
    version_uid: VersionUid;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `streamVersionPortalBlockCrop` (`image/png`, HTTP 200). */
export type StreamVersionPortalBlockCropResult = Blob;

// ------------------------------------------------------------------------------------
// submitExecutorTaskAnswer - POST /runner/tasks/{task_id}/answer
// ------------------------------------------------------------------------------------

/**
 * Submit Executor Task Answer
 *
 * `HOSTS-SEAL-1` (ADR-0028): the answer of a **host agent** carries `model` (the task's `model_id`), `provider` and `access` (the task's), `reported_model` -- the **exact** string the client or API reported, held against `model_id` and the catalogue's `accepted_reported` and never trimmed (`R-133`) -- and `usage` when the provider gave a count; it sends no top-level `input_tokens` or `output_tokens`. A reported model that is neither is `409 conflict`. The answer is journalled with the stage of its cell, the host and the access.
 */
export type SubmitExecutorTaskAnswerInput = {
  /** Path parameters, substituted into `/runner/tasks/{task_id}/answer`. */
  path: {
    task_id: ExecutorTaskId;
  };
  /** Request body, sent as `application/json`. */
  body: SubmitExecutorTaskAnswerRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `submitExecutorTaskAnswer` (`application/json`, HTTP 200). */
export type SubmitExecutorTaskAnswerResult = ExecutorTaskAck;

// ------------------------------------------------------------------------------------
// submitRegistration - POST /registrations
// ------------------------------------------------------------------------------------

/**
 * Apply for an account.
 *
 * Reachable without a credential: `security` is the empty requirement, as on `issueToken`. Records an application an administrator then approves or rejects; no mail is sent (R-56). The e-mail, the names and the password are validated first, then: an active account holding the login is `conflict` with `conflict_reason: login_taken`, a pending request for it `request_pending`, and `queue_full` both when 100 requests are pending in all and when 40 requests that are pending or approved were submitted within the last rolling 24 hours (a rejected request does not count, so a flood of rejected ones locks nobody out; the answer is the same whatever the login). `SMALL-HARDENING-02` (`R-146ax`, `D-246`, `D-253`). That the first two tell a submitter a login is known is an accepted, registered limitation. Neither `401` nor `403` is declared: there is no credential to refuse and no subject to deny. The edge in front of this surface throttles it per client and answers `rate_limited` (`429`) itself, before the operation is reached; like the edge's own body-size refusal, that answer is not a response of the operation and is not declared here.
 */
export type SubmitRegistrationInput = {
  /** Request body, sent as `application/json`. */
  body: SubmitRegistrationRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `submitRegistration` (`application/json`, HTTP 201). */
export type SubmitRegistrationResult = RegistrationStatusResponse;

// ------------------------------------------------------------------------------------
// transitionAssignment - POST /assignments/{assignment_uid}/transitions
// ------------------------------------------------------------------------------------

/**
 * Move an assignment: start, complete, return, reassign or cancel it.
 *
 * Appends one event. `started`, `completed` and `returned` (with a `reason`) are the current assignee's, holding `expert` (an administrator who is not the assignee is `permission_denied`, `required_capability: assignment:assignee`); `reassigned` (with `new_assignee_user_uid`, an active expert) and `cancelled` (optional `reason`) are an administrator's. A request equal to the latest event answers the assignment unchanged; any other move the `work_assignment` machine does not declare is `state_transition_not_allowed`. An expert addressing an assignment that is not currently theirs gets `not_found`.
 */
export type TransitionAssignmentInput = {
  /** Path parameters, substituted into `/assignments/{assignment_uid}/transitions`. */
  path: {
    assignment_uid: AssignmentUid;
  };
  /** Request body, sent as `application/json`. */
  body: TransitionAssignmentRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `transitionAssignment` (`application/json`, HTTP 200). */
export type TransitionAssignmentResult = Assignment;

// ------------------------------------------------------------------------------------
// undoComparisonMatrixEdit - POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits/undo
// ------------------------------------------------------------------------------------

/**
 * Reverse the latest applied manual matrix edit.
 *
 * «Отменить правку» on a saved edit: appends an `undo` event that reverses the latest applied edit of the document set. `base_revision` is the revision the caller saw, so an edit made meanwhile by someone else is never undone by mistake: a stale one is `409 conflict` (`comparison_matrix_stale`), and a document set with no applied edit is `409 conflict` (`comparison_edit_none`). History is append-only. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). An unknown project, or a document of another project, is `404`. Served by `CMP-MATRIX-01`; sealed by `CMP-SEAL-C1` (`ADR-0025`), which left a stub that answered `503 dependency_unavailable` (`details.dependency: comparison_matrix`) until the lane wired it.
 */
export type UndoComparisonMatrixEditInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits/undo`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `application/json`. */
  body: UndoComparisonMatrixEditRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `undoComparisonMatrixEdit` (`application/json`, HTTP 200). */
export type UndoComparisonMatrixEditResult = ComparisonMatrix;

// ------------------------------------------------------------------------------------
// undoStageLinkRepair - POST /stage-link-repairs/{stage_link_repair_id}/undo
// ------------------------------------------------------------------------------------

/** Undo Repair */
export type UndoStageLinkRepairInput = {
  /** Path parameters, substituted into `/stage-link-repairs/{stage_link_repair_id}/undo`. */
  path: {
    stage_link_repair_id: StageLinkRepairId;
  };
  /** Request body, sent as `application/json`. */
  body: UndoStageLinkRepairRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `undoStageLinkRepair` (`application/json`, HTTP 200). */
export type UndoStageLinkRepairResult = StageLinkRepair;

// ------------------------------------------------------------------------------------
// updateMyProfile - PATCH /me
// ------------------------------------------------------------------------------------

/**
 * Set the signed-in account's names, and complete its profile.
 *
 * **Completion** (R-59): an account whose profile is incomplete gives its names and -- unless its login already is one -- its e-mail address, and the names, the login and the completion are written in **one** update, so there is no instant at which the account has one without the other. **A complete profile** changes its names only; its login is fixed. An e-mail another active account holds is `conflict` with `details.conflict_reason: login_taken`. The account is the one the credential names, never one named in the body. No credential is revoked: names are not rights.
 */
export type UpdateMyProfileInput = {
  /** Request body, sent as `application/json`. */
  body: UpdateMyProfileRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `updateMyProfile` (`application/json`, HTTP 200). */
export type UpdateMyProfileResult = Account;

// ------------------------------------------------------------------------------------
// updateUser - PATCH /users/{user_uid}
// ------------------------------------------------------------------------------------

/**
 * Change an account's names, its role set, or both.
 *
 * Requires `admin`. Names change without revoking anything; a change of the role set revokes every credential the account holds, so it signs in again and only then meets its new rights. An administrator cannot remove a role from themselves (`permission_denied`, no detail), and the last active account holding `admin` cannot lose it (`conflict`, `conflict_reason: last_admin`). An administrator naming an account whose profile is incomplete does not complete it: only the account itself gives its e-mail.
 */
export type UpdateUserInput = {
  /** Path parameters, substituted into `/users/{user_uid}`. */
  path: {
    user_uid: UserUid;
  };
  /** Request body, sent as `application/json`. */
  body: UpdateUserRequest;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `updateUser` (`application/json`, HTTP 200). */
export type UpdateUserResult = Account;

// ------------------------------------------------------------------------------------
// uploadComparisonReportSource - POST /comparison-series/{comparison_series_id}/reports/upload
// ------------------------------------------------------------------------------------

/**
 * Make a report draft from an uploaded MD file.
 *
 * «загрузить MD-файл»: the body is the file (`text/markdown`, UTF-8, at most 20 MiB) and `kind`, `reuse` and `source_name` (a hint, never an identity) are query values. A file that is empty, larger than 20 MiB, not UTF-8 or without a transition headed «## N. … A → B» is `422 validation_failed` (`comparison_report_source_invalid`). Makes a `draft` with its estimate; no model is called. An unknown series is `404`. A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C2` (`ADR-0025`): until `CMP-VC-REPORT-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_reports`, or `comparison_modules` while the versions module is off) and nothing is read or written.
 */
export type UploadComparisonReportSourceInput = {
  /** Path parameters, substituted into `/comparison-series/{comparison_series_id}/reports/upload`. */
  path: {
    comparison_series_id: ComparisonSeriesId;
  };
  /** Query string parameters. */
  query?: {
    kind?: ComparisonReportKind;
    reuse?: boolean;
    source_name?: string;
  };
  /** Request body, sent as `text/markdown`. */
  body: Blob;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `uploadComparisonReportSource` (`application/json`, HTTP 201). */
export type UploadComparisonReportSourceResult = ComparisonReport;

// ------------------------------------------------------------------------------------
// uploadComparisonUploadPart - PUT /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/parts
// ------------------------------------------------------------------------------------

/**
 * Stage one part of one file of an upload batch.
 *
 * The part is named by the query parameter `part_number` (from 1; a part number is an ordinal inside a file and the file is the identity). The body is the raw part, `application/octet-stream`, at most 16 MiB (`ADR-0025` decision 10; the default proxy location, no proxy change). The part has a database owner before its bytes are staged, and the file's multipart token is persisted before the first part. Part numbers run from 1; sending the same part again with the same bytes replays the recorded receipt. Refusals: `404`, `409 conflict` (`comparison_upload_state`), `422 validation_failed` (`comparison_part_number`, `comparison_part_size`). A keyed write: `Idempotency-Key` is required (`ADR-0025` decision 19). An expert's act (`role:expert`, `R-60`; an administrator without the expert role is refused). Sealed as a stub by `CMP-SEAL-C0` (`ADR-0025`): until `CMP-INGEST-01` wires it, every request that passes the credential, the role and the request's own shape answers `503 dependency_unavailable` (`details.dependency: comparison_uploads`) and nothing is read or written.
 */
export type UploadComparisonUploadPartInput = {
  /** Path parameters, substituted into `/comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/parts`. */
  path: {
    comparison_upload_file_id: ComparisonUploadFileId;
    comparison_upload_id: ComparisonUploadId;
  };
  /** Query string parameters. */
  query: {
    part_number: number;
  };
  /** Request body, sent as `application/octet-stream`. */
  body: Blob;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `uploadComparisonUploadPart` (`application/json`, HTTP 200). */
export type UploadComparisonUploadPartResult = ComparisonUploadPartReceipt;

// ------------------------------------------------------------------------------------
// uploadDocument - POST /projects/{project_uid}/documents
// ------------------------------------------------------------------------------------

/**
 * Upload one portal bundle and publish an immutable document version.
 *
 * The whole ingest path. The body is one portal bundle: a ZIP, recognised by its magic bytes whatever label the browser sends, holding exactly one `<stem>.pdf`, one `<stem>_blocks.json` and one `<stem>_results.md`, and optionally one `<stem>_results.html` (kept as a digest only: never stored, served or rendered) and one `<stem>_stamp_audit.json` (stored, and not used in analysis). All members share one stem. Anything else in the archive is refused, and so is any archive that is not what it claims to be (names that escape, links, encrypted members, a compression ratio above the bound, sizes beyond the bounds).
 *
 * A bare PDF is refused with `validation_failed` and the constraint `portal_bundle_required`; the message says how to obtain the bundle. The PDF must be unencrypted; the temporary statistics intake removes application size and page-count ceilings. Every page must carry an embedded text layer or at least one portal block. Every refusal is `validation_failed` (or `storage_integrity_error`) with a `constraint` detail, and the registered values are in the domain error catalog (`error-codes.json`, `validation_failed`).
 *
 * OCR is always marked: the portal's recognised text is kept as its own artifact with quality flags and is never merged into the PDF's text layer (R-116). The portal's descriptions of images are shown, marked, and never used in analysis (R-117). The upload runs no analysis. Which analysis a version gets is decided later, from the classification an expert confirms for it (`classifyDocumentVersion`, one of the fifteen sections): `startRun` routes a section that has a registered text profile (АР included) to its profile and refuses an unclassified version or a section with none. A stated `section` here is the legacy label: it is stored and counted, it neither selects nor refuses an analysis, and it never makes a version classified (D-110, closed by W59-SECTION-SEAL-01).
 *
 * A third upload in flight in one API process is refused before its body is read: `503 dependency_unavailable` with `details.dependency: upload_capacity` and a `Retry-After` header. Nothing was created; the caller sends the same upload again later.
 *
 * On success the version and its input manifest are immutable: there is no update or delete endpoint for either, and the database refuses both. The manifest holds one entry per stored member: `source.document`, `source.structured_companion`, `source.markdown` and, when the bundle had one, `source.stamp_audit`.
 */
export type UploadDocumentInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `multipart/form-data`. */
  body: UploadDocumentRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `uploadDocument` (`application/json`, HTTP 201). */
export type UploadDocumentResult = DocumentVersion;

// ------------------------------------------------------------------------------------
// uploadDocumentVersion - POST /projects/{project_uid}/documents/{document_uid}/versions
// ------------------------------------------------------------------------------------

/**
 * Upload one portal bundle as the next immutable version of an existing document.
 *
 * The same ingest path as `uploadDocument`, into a document that already exists. The body is one portal bundle under exactly `uploadDocument`'s envelope (the same members, bounds, refusals and `constraint` details, a bare PDF refused with `portal_bundle_required`), and the same third-upload-in-flight refusal (`503 dependency_unavailable`, `details.dependency: upload_capacity`, `Retry-After`).
 *
 * The new version gets the document's next `version_ordinal` and becomes its current version; every older version, its classification, runs, findings and decisions are unchanged. It inherits nothing: it takes no display title (the document keeps its own) and no section, and its `classification` is absent until an expert confirms one with `classifyDocumentVersion`. Two uploads into one document at the same time get consecutive ordinals.
 *
 * An unknown project, an unknown document, or a document of another project is `404 not_found` (`details.aggregate_type` `Project` or `Document`), decided before the key is claimed or a byte is read into storage. The `Idempotency-Key` behaves as for `uploadDocument`: an exact repeat answers the version it created, and the same key with another document or another bundle is `409 idempotency_key_reuse`.
 */
export type UploadDocumentVersionInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
  };
  /** Request body, sent as `multipart/form-data`. */
  body: UploadDocumentVersionRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `uploadDocumentVersion` (`application/json`, HTTP 201). */
export type UploadDocumentVersionResult = DocumentVersion;

// ------------------------------------------------------------------------------------
// uploadPriceList - POST /projects/{project_uid}/price-lists
// ------------------------------------------------------------------------------------

/**
 * Upload Price List
 *
 * Upload one price list of the project: a CSV (UTF-8 with or without a byte-order mark, UTF-16 with one, or Windows-1251; `;`, tab or `,` delimited) or an XLSX, whose first sheet is read; at most 10 MiB and 20 000 data rows. It becomes the project's newest immutable revision, bound to the stored file; earlier revisions stay readable. Every data row is accepted as a position or skipped with a reason in the revision's parse report; a price is read only from a plain number and is never guessed. `default_currency` applies to rows whose currency neither their own cell nor the price column's header names. A file that cannot be a price list is `422 validation_failed` with `field: content` and one `constraint`, and creates nothing. `expert` is required (`admin` alone is `permission_denied`); an unknown project is `404`. An exact repeat of the `Idempotency-Key` answers the stored revision; the same key with another file, file name, currency, project or caller is `409 idempotency_key_reuse`.
 */
export type UploadPriceListInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/price-lists`. */
  path: {
    project_uid: ProjectUid;
  };
  /** Request body, sent as `multipart/form-data`. */
  body: UploadPriceListRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `uploadPriceList` (`application/json`, HTTP 201). */
export type UploadPriceListResult = PriceListRevision;

// ------------------------------------------------------------------------------------
// uploadStageUploadPart - PUT /stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/parts
// ------------------------------------------------------------------------------------

/** Upload Stage Upload Part */
export type UploadStageUploadPartInput = {
  /** Path parameters, substituted into `/stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/parts`. */
  path: {
    stage_upload_file_id: StageUploadFileId;
    stage_upload_id: StageUploadId;
  };
  /** Query string parameters. */
  query: {
    part_number: number;
  };
  /** Request body, sent as `application/octet-stream`. */
  body: Blob;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `uploadStageUploadPart` (`application/json`, HTTP 200). */
export type UploadStageUploadPartResult = StageUploadPartReceipt;

// ------------------------------------------------------------------------------------
// withdrawDecisionMemoryCase - POST /decision-memory/cases/{case_id}/withdraw
// ------------------------------------------------------------------------------------

/**
 * Withdraw Decision Memory Case
 *
 * `DECISION-MEMORY-01` phase M2: take a case out of hints, prompts and exports. Append-only: a `withdraw` status event with a closed `reason_code` (no free text) and the caller's account; the case itself is never edited. A case that is already withdrawn is `409 state_transition_not_allowed`; a forgotten case accepts no status event (`409 conflict`, `conflict_reason: memory_case_forgotten`); an unknown case is `404`. An exact repeat of the `Idempotency-Key` answers the first call's event and writes nothing. `role:admin`.
 */
export type WithdrawDecisionMemoryCaseInput = {
  /** Path parameters, substituted into `/decision-memory/cases/{case_id}/withdraw`. */
  path: {
    case_id: DecisionMemoryCaseId;
  };
  /** Request body, sent as `application/json`. */
  body: DecisionMemoryStatusChangeRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `withdrawDecisionMemoryCase` (`application/json`, HTTP 200). */
export type WithdrawDecisionMemoryCaseResult = DecisionMemoryStatusChange;

// ------------------------------------------------------------------------------------
// withdrawSheetPairing - POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings/{sheet_link_id}/withdrawals
// ------------------------------------------------------------------------------------

/**
 * Withdraw Sheet Pairing
 *
 * End one active sheet link of the path's (older) version with a new row of the append-only history: nothing is updated or deleted, and the approval stays in the history. The body names the comparison view the expert was looking at (`mode` and runs): the approved set that remains is sealed over that view's text. A link that is not of this path is `404`; a link already withdrawn is `conflict` with `conflict_reason` `sheet_link_not_active`; a view that cannot be recomputed is `conflict` with `comparison_not_available`. The same key repeated answers the first withdrawal, `replayed: true`. `expert` is required; `admin` alone is refused (`required_capability: role:expert`). While the «Сравнение версий» module is on (`AUDITMANAGER_COMPARISON_MODULES` names `versions`) this operation answers `503 dependency_unavailable` (`details.dependency: comparison_versions_module`) and writes nothing: the effective matrix is the only store of which page of one version is which page of another (`ADR-0025` decision 13; migration `0039` turned the active approvals into manual matrix edits and kept the `0035` rows as history). With the module off it works as before.
 */
export type WithdrawSheetPairingInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings/{sheet_link_id}/withdrawals`. */
  path: {
    document_uid: DocumentUid;
    project_uid: ProjectUid;
    sheet_link_id: SheetLinkId;
    version_uid: VersionUid;
  };
  /** Request body, sent as `application/json`. */
  body: WithdrawSheetPairingRequest;
  /**
   * Required `Idempotency-Key`. Mint it once per intent and reuse the same
   * value on every retry: a new key is a new command, not a retry.
   */
  idempotencyKey: IdempotencyKey;
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `withdrawSheetPairing` (`application/json`, HTTP 201). */
export type WithdrawSheetPairingResult = SheetPairingEvent;

// ------------------------------------------------------------------------------------
// Runtime descriptors
// ------------------------------------------------------------------------------------

/**
 * What the transport needs at runtime to execute an operation. Consumers read this
 * table; they never build a URL, a method or a header name by hand.
 */
export const OPERATIONS = {
  appendComparisonVersionOrder: {
    operationId: 'appendComparisonVersionOrder',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-version-orders',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  appendDecision: {
    operationId: 'appendDecision',
    method: 'POST',
    path: '/findings/{finding_uid}/decisions',
    pathParams: ['finding_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['decisions'],
  },
  appendPrecedentSetting: {
    operationId: 'appendPrecedentSetting',
    method: 'POST',
    path: '/precedent-settings',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  applyComparisonMatrixEdits: {
    operationId: 'applyComparisonMatrixEdits',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  applyStageCardVerdicts: {
    operationId: 'applyStageCardVerdicts',
    method: 'POST',
    path: '/stage-chain-runs/{stage_chain_run_id}/card-verdicts',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  applyStageSheetMap: {
    operationId: 'applyStageSheetMap',
    method: 'POST',
    path: '/stage-pairs/{stage_pair_id}/sheet-map',
    pathParams: ['stage_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  approveRegistration: {
    operationId: 'approveRegistration',
    method: 'POST',
    path: '/registrations/{request_id}/approve',
    pathParams: ['request_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['registrations'],
  },
  approveSheetPairing: {
    operationId: 'approveSheetPairing',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings',
    pathParams: ['document_uid', 'project_uid', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  archiveAnalysisPreset: {
    operationId: 'archiveAnalysisPreset',
    method: 'POST',
    path: '/analysis/presets/{preset_id}/archive',
    pathParams: ['preset_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['analysis'],
  },
  archiveExecutorConnection: {
    operationId: 'archiveExecutorConnection',
    method: 'POST',
    path: '/executor-connections/{connection_id}/archive',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  archiveExecutorGroup: {
    operationId: 'archiveExecutorGroup',
    method: 'POST',
    path: '/executor-groups/{group_id}/archive',
    pathParams: ['group_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  archiveExecutorHost: {
    operationId: 'archiveExecutorHost',
    method: 'POST',
    path: '/executor-hosts/{host_id}/archive',
    pathParams: ['host_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  archiveUser: {
    operationId: 'archiveUser',
    method: 'POST',
    path: '/users/{user_uid}/archive',
    pathParams: ['user_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['users'],
  },
  cancelComparisonAiPairCheck: {
    operationId: 'cancelComparisonAiPairCheck',
    method: 'POST',
    path: '/comparison-ai-pair-checks/{comparison_ai_job_id}/cancellation',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  cancelComparisonAiSheetChanges: {
    operationId: 'cancelComparisonAiSheetChanges',
    method: 'POST',
    path: '/comparison-ai-sheet-jobs/{comparison_ai_job_id}/cancellation',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  cancelComparisonReport: {
    operationId: 'cancelComparisonReport',
    method: 'POST',
    path: '/comparison-reports/{comparison_report_id}/cancellation',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  cancelComparisonSeries: {
    operationId: 'cancelComparisonSeries',
    method: 'POST',
    path: '/comparison-series/{comparison_series_id}/cancellation',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  cancelComparisonSpecification: {
    operationId: 'cancelComparisonSpecification',
    method: 'POST',
    path: '/comparison-ai-spec-jobs/{comparison_ai_job_id}/cancellation',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  cancelComparisonUpload: {
    operationId: 'cancelComparisonUpload',
    method: 'POST',
    path: '/comparison-uploads/{comparison_upload_id}/cancellation',
    pathParams: ['comparison_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  cancelRun: {
    operationId: 'cancelRun',
    method: 'POST',
    path: '/runs/{run_id}/cancel',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  cancelStageChainBatch: {
    operationId: 'cancelStageChainBatch',
    method: 'POST',
    path: '/stage-chain-batches/{stage_chain_batch_id}/cancellation',
    pathParams: ['stage_chain_batch_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  cancelStageChainRun: {
    operationId: 'cancelStageChainRun',
    method: 'POST',
    path: '/stage-chain-runs/{stage_chain_run_id}/cancellation',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  cancelStageUpload: {
    operationId: 'cancelStageUpload',
    method: 'POST',
    path: '/stage-uploads/{stage_upload_id}/cancellation',
    pathParams: ['stage_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  carryOverDecision: {
    operationId: 'carryOverDecision',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/carryovers',
    pathParams: ['document_uid', 'project_uid', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['decisions'],
  },
  carryOverProposalDecisions: {
    operationId: 'carryOverProposalDecisions',
    method: 'POST',
    path: '/optimisation-passes/{optimisation_pass_id}/decision-carryovers',
    pathParams: ['optimisation_pass_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['optimisation'],
  },
  changePassword: {
    operationId: 'changePassword',
    method: 'POST',
    path: '/auth/password',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['auth'],
  },
  claimExecutorTask: {
    operationId: 'claimExecutorTask',
    method: 'POST',
    path: '/runner/tasks/claim',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200, 204],
    errorStatuses: [401, 422, 500, 503],
    tags: ['execution'],
  },
  classifyDocumentVersion: {
    operationId: 'classifyDocumentVersion',
    method: 'PUT',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification',
    pathParams: ['document_uid', 'project_uid', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  clearComparisonLaunchQueue: {
    operationId: 'clearComparisonLaunchQueue',
    method: 'POST',
    path: '/projects/{project_uid}/comparison-launch-queue/clear',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  compareDocumentVersions: {
    operationId: 'compareDocumentVersions',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison',
    pathParams: ['document_uid', 'project_uid', 'version_uid'],
    queryParams: ['diff_limit', 'diff_offset', 'mode', 'source_run_id', 'target_run_id', 'target_version_uid'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['documents'],
  },
  completeComparisonUploadFile: {
    operationId: 'completeComparisonUploadFile',
    method: 'POST',
    path: '/comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/completion',
    pathParams: ['comparison_upload_file_id', 'comparison_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  completeStageUploadFile: {
    operationId: 'completeStageUploadFile',
    method: 'POST',
    path: '/stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/completion',
    pathParams: ['stage_upload_file_id', 'stage_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  confirmComparisonUploadSet: {
    operationId: 'confirmComparisonUploadSet',
    method: 'POST',
    path: '/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/confirmation',
    pathParams: ['comparison_upload_id', 'comparison_upload_set_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  confirmExecutorAgentInstallHostKey: {
    operationId: 'confirmExecutorAgentInstallHostKey',
    method: 'POST',
    path: '/executor-connections/{connection_id}/agent-installs/{install_id}/confirm-host-key',
    pathParams: ['connection_id', 'install_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  confirmExecutorHostAgentInstallHostKey: {
    operationId: 'confirmExecutorHostAgentInstallHostKey',
    method: 'POST',
    path: '/executor-hosts/{host_id}/agent-installs/{install_id}/confirm-host-key',
    pathParams: ['host_id', 'install_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  confirmStagePair: {
    operationId: 'confirmStagePair',
    method: 'POST',
    path: '/projects/{project_uid}/stage-pairs',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  confirmStageUploadCandidate: {
    operationId: 'confirmStageUploadCandidate',
    method: 'POST',
    path: '/stage-upload-candidates/{stage_upload_candidate_id}/confirmation',
    pathParams: ['stage_upload_candidate_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  continueComparisonReport: {
    operationId: 'continueComparisonReport',
    method: 'POST',
    path: '/comparison-reports/{comparison_report_id}/continuation',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  correctVersionClassification: {
    operationId: 'correctVersionClassification',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification/corrections',
    pathParams: ['document_uid', 'project_uid', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  createAnalysisPreset: {
    operationId: 'createAnalysisPreset',
    method: 'POST',
    path: '/analysis/presets',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['analysis'],
  },
  createAssignment: {
    operationId: 'createAssignment',
    method: 'POST',
    path: '/assignments',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['dispatch'],
  },
  createComparisonReport: {
    operationId: 'createComparisonReport',
    method: 'POST',
    path: '/comparison-series/{comparison_series_id}/reports',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  createComparisonUpload: {
    operationId: 'createComparisonUpload',
    method: 'POST',
    path: '/projects/{project_uid}/comparison-uploads',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  createExecutorAgentInstall: {
    operationId: 'createExecutorAgentInstall',
    method: 'POST',
    path: '/executor-connections/{connection_id}/agent-installs',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  createExecutorConnection: {
    operationId: 'createExecutorConnection',
    method: 'POST',
    path: '/executor-connections',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  createExecutorGroup: {
    operationId: 'createExecutorGroup',
    method: 'POST',
    path: '/executor-groups',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  createExecutorHostAgentInstall: {
    operationId: 'createExecutorHostAgentInstall',
    method: 'POST',
    path: '/executor-hosts/agent-installs',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  createProject: {
    operationId: 'createProject',
    method: 'POST',
    path: '/projects',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['projects'],
  },
  createStageAssembly: {
    operationId: 'createStageAssembly',
    method: 'POST',
    path: '/projects/{project_uid}/stage-assemblies',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  createStageReviewCard: {
    operationId: 'createStageReviewCard',
    method: 'POST',
    path: '/stage-chain-runs/{stage_chain_run_id}/review-cards',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  createStageUpload: {
    operationId: 'createStageUpload',
    method: 'POST',
    path: '/projects/{project_uid}/stage-uploads',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  decideOptimisationProposal: {
    operationId: 'decideOptimisationProposal',
    method: 'POST',
    path: '/optimisation-proposals/{optimisation_proposal_id}/decisions',
    pathParams: ['optimisation_proposal_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['optimisation'],
  },
  deleteComparisonReport: {
    operationId: 'deleteComparisonReport',
    method: 'POST',
    path: '/comparison-reports/{comparison_report_id}/deletion',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  dequeueComparisonAiSheetChanges: {
    operationId: 'dequeueComparisonAiSheetChanges',
    method: 'POST',
    path: '/comparison-ai-sheet-jobs/{comparison_ai_job_id}/dequeue',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  downloadAgentPackage: {
    operationId: 'downloadAgentPackage',
    method: 'GET',
    path: '/runner/agent-package/{version}',
    pathParams: ['version'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/gzip',
    successStatuses: [200],
    errorStatuses: [422, 500, 503],
    tags: ['execution'],
  },
  endUserSessions: {
    operationId: 'endUserSessions',
    method: 'POST',
    path: '/users/{user_uid}/sessions/end',
    pathParams: ['user_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['users'],
  },
  enqueueComparisonLaunch: {
    operationId: 'enqueueComparisonLaunch',
    method: 'POST',
    path: '/projects/{project_uid}/comparison-launch-queue/entries',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  estimateComparisonAiPairCheck: {
    operationId: 'estimateComparisonAiPairCheck',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check/estimate',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  estimateComparisonAiSheetChanges: {
    operationId: 'estimateComparisonAiSheetChanges',
    method: 'GET',
    path: '/comparison-series/{comparison_series_id}/ai-sheet-changes/estimate',
    pathParams: ['comparison_series_id'],
    queryParams: ['only_failed'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  estimateComparisonSheetDescription: {
    operationId: 'estimateComparisonSheetDescription',
    method: 'GET',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}/description/estimate',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  estimateComparisonSpecification: {
    operationId: 'estimateComparisonSpecification',
    method: 'GET',
    path: '/comparison-transitions/{comparison_transition_id}/specification/estimate',
    pathParams: ['comparison_transition_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  estimateRunCost: {
    operationId: 'estimateRunCost',
    method: 'POST',
    path: '/runs/cost-estimate',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['runs'],
  },
  estimateStageChainRun: {
    operationId: 'estimateStageChainRun',
    method: 'GET',
    path: '/stage-link-revisions/{stage_link_revision_id}/chain-estimate',
    pathParams: ['stage_link_revision_id'],
    queryParams: ['engine', 'stage_chain_run_id'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  excludeComparisonUploadSet: {
    operationId: 'excludeComparisonUploadSet',
    method: 'POST',
    path: '/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/exclusion',
    pathParams: ['comparison_upload_id', 'comparison_upload_set_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  exportOptimisationProposalsCsv: {
    operationId: 'exportOptimisationProposalsCsv',
    method: 'GET',
    path: '/optimisation-passes/{optimisation_pass_id}/export.csv',
    pathParams: ['optimisation_pass_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'text/csv',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['optimisation'],
  },
  exportOptimisationProposalsXlsx: {
    operationId: 'exportOptimisationProposalsXlsx',
    method: 'GET',
    path: '/optimisation-passes/{optimisation_pass_id}/export.xlsx',
    pathParams: ['optimisation_pass_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['optimisation'],
  },
  exportRunCsv: {
    operationId: 'exportRunCsv',
    method: 'GET',
    path: '/runs/{run_id}/export.csv',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'text/csv',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['export'],
  },
  exportRunXlsx: {
    operationId: 'exportRunXlsx',
    method: 'GET',
    path: '/runs/{run_id}/export.xlsx',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['export'],
  },
  extendExecutorTaskClaim: {
    operationId: 'extendExecutorTaskClaim',
    method: 'POST',
    path: '/runner/tasks/{task_id}/extend',
    pathParams: ['task_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  failExecutorTask: {
    operationId: 'failExecutorTask',
    method: 'POST',
    path: '/runner/tasks/{task_id}/fail',
    pathParams: ['task_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  finishComparisonAiSheetChanges: {
    operationId: 'finishComparisonAiSheetChanges',
    method: 'POST',
    path: '/comparison-ai-sheet-jobs/{comparison_ai_job_id}/finish',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  finishComparisonSeries: {
    operationId: 'finishComparisonSeries',
    method: 'POST',
    path: '/comparison-series/{comparison_series_id}/finish',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  generateComparisonSummary: {
    operationId: 'generateComparisonSummary',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/summaries',
    pathParams: ['document_uid', 'project_uid', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  generateExecutorSshKey: {
    operationId: 'generateExecutorSshKey',
    method: 'POST',
    path: '/executor-connections/{connection_id}/ssh-key',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  getAssignment: {
    operationId: 'getAssignment',
    method: 'GET',
    path: '/assignments/{assignment_uid}',
    pathParams: ['assignment_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['dispatch'],
  },
  getComparisonAiPairCheck: {
    operationId: 'getComparisonAiPairCheck',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonAiQueue: {
    operationId: 'getComparisonAiQueue',
    method: 'GET',
    path: '/execution/comparison-ai-queue',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  getComparisonAiSheetChanges: {
    operationId: 'getComparisonAiSheetChanges',
    method: 'GET',
    path: '/comparison-series/{comparison_series_id}/ai-sheet-changes',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonLaunchQueue: {
    operationId: 'getComparisonLaunchQueue',
    method: 'GET',
    path: '/projects/{project_uid}/comparison-launch-queue',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonMatrix: {
    operationId: 'getComparisonMatrix',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-matrix',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonOverview: {
    operationId: 'getComparisonOverview',
    method: 'GET',
    path: '/projects/{project_uid}/comparison-overview',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonQueueSummary: {
    operationId: 'getComparisonQueueSummary',
    method: 'GET',
    path: '/execution/comparison-queue',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  getComparisonReport: {
    operationId: 'getComparisonReport',
    method: 'GET',
    path: '/comparison-reports/{comparison_report_id}',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonSeries: {
    operationId: 'getComparisonSeries',
    method: 'GET',
    path: '/comparison-series/{comparison_series_id}',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonSheetDescription: {
    operationId: 'getComparisonSheetDescription',
    method: 'GET',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}/description',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonSheetPair: {
    operationId: 'getComparisonSheetPair',
    method: 'GET',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonSheetPairSpecPositions: {
    operationId: 'getComparisonSheetPairSpecPositions',
    method: 'GET',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}/spec-positions',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonSpecification: {
    operationId: 'getComparisonSpecification',
    method: 'GET',
    path: '/comparison-transitions/{comparison_transition_id}/specification',
    pathParams: ['comparison_transition_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonUpload: {
    operationId: 'getComparisonUpload',
    method: 'GET',
    path: '/comparison-uploads/{comparison_upload_id}',
    pathParams: ['comparison_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getComparisonUploadProposal: {
    operationId: 'getComparisonUploadProposal',
    method: 'GET',
    path: '/comparison-uploads/{comparison_upload_id}/proposal',
    pathParams: ['comparison_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getDashboardSummary: {
    operationId: 'getDashboardSummary',
    method: 'GET',
    path: '/dashboard',
    pathParams: [],
    queryParams: ['project_uid'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['dashboard'],
  },
  getDecisionMemoryCase: {
    operationId: 'getDecisionMemoryCase',
    method: 'GET',
    path: '/decision-memory/cases/{case_id}',
    pathParams: ['case_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['decision-memory'],
  },
  getDecisionMemoryStatus: {
    operationId: 'getDecisionMemoryStatus',
    method: 'GET',
    path: '/decision-memory/status',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['decision-memory'],
  },
  getDocumentVersion: {
    operationId: 'getDocumentVersion',
    method: 'GET',
    path: '/versions/{version_uid}',
    pathParams: ['version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['documents'],
  },
  getEffectiveVendorLists: {
    operationId: 'getEffectiveVendorLists',
    method: 'GET',
    path: '/projects/{project_uid}/vendor-lists',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['optimisation'],
  },
  getExecutionDispatch: {
    operationId: 'getExecutionDispatch',
    method: 'GET',
    path: '/execution/dispatch',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  getExecutorAgentInstall: {
    operationId: 'getExecutorAgentInstall',
    method: 'GET',
    path: '/executor-connections/{connection_id}/agent-installs/{install_id}',
    pathParams: ['connection_id', 'install_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorConnection: {
    operationId: 'getExecutorConnection',
    method: 'GET',
    path: '/executor-connections/{connection_id}',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorGroup: {
    operationId: 'getExecutorGroup',
    method: 'GET',
    path: '/executor-groups/{group_id}',
    pathParams: ['group_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorGroupCapacity: {
    operationId: 'getExecutorGroupCapacity',
    method: 'GET',
    path: '/executor-groups/{group_id}/capacity',
    pathParams: ['group_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorHost: {
    operationId: 'getExecutorHost',
    method: 'GET',
    path: '/executor-hosts/{host_id}',
    pathParams: ['host_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorHostAgentInstall: {
    operationId: 'getExecutorHostAgentInstall',
    method: 'GET',
    path: '/executor-hosts/{host_id}/agent-installs/{install_id}',
    pathParams: ['host_id', 'install_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorHostDetails: {
    operationId: 'getExecutorHostDetails',
    method: 'GET',
    path: '/executor-hosts/{host_id}/details',
    pathParams: ['host_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorTaskContext: {
    operationId: 'getExecutorTaskContext',
    method: 'POST',
    path: '/runner/tasks/{task_id}/context',
    pathParams: ['task_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  getExecutorTaskImage: {
    operationId: 'getExecutorTaskImage',
    method: 'GET',
    path: '/runner/tasks/{task_id}/images/{blob_id}',
    pathParams: ['blob_id', 'task_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'image/png',
    successStatuses: [200],
    errorStatuses: [401, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  getExtendedRunReview: {
    operationId: 'getExtendedRunReview',
    method: 'GET',
    path: '/runs/{run_id}/extended-review',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['runs'],
  },
  getFinding: {
    operationId: 'getFinding',
    method: 'GET',
    path: '/findings/{finding_uid}',
    pathParams: ['finding_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['findings'],
  },
  getFindingPrecedents: {
    operationId: 'getFindingPrecedents',
    method: 'GET',
    path: '/findings/{finding_uid}/precedents',
    pathParams: ['finding_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['findings'],
  },
  getMe: {
    operationId: 'getMe',
    method: 'GET',
    path: '/me',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['account'],
  },
  getNormDocument: {
    operationId: 'getNormDocument',
    method: 'GET',
    path: '/norm-documents/{norm_document_id}',
    pathParams: ['norm_document_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['norms'],
  },
  getProductVersion: {
    operationId: 'getProductVersion',
    method: 'GET',
    path: '/system/version',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['releases'],
  },
  getProject: {
    operationId: 'getProject',
    method: 'GET',
    path: '/projects/{project_uid}',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['projects'],
  },
  getRunNormReferences: {
    operationId: 'getRunNormReferences',
    method: 'GET',
    path: '/runs/{run_id}/norm-references',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['runs'],
  },
  getRunPrecedents: {
    operationId: 'getRunPrecedents',
    method: 'GET',
    path: '/runs/{run_id}/precedents',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['findings'],
  },
  getRunStages: {
    operationId: 'getRunStages',
    method: 'GET',
    path: '/runs/{run_id}/stages',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['runs'],
  },
  getRunStartReadiness: {
    operationId: 'getRunStartReadiness',
    method: 'POST',
    path: '/runs/start-readiness',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  getRunStatus: {
    operationId: 'getRunStatus',
    method: 'GET',
    path: '/runs/{run_id}',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['runs'],
  },
  getSectionSpecification: {
    operationId: 'getSectionSpecification',
    method: 'GET',
    path: '/sections/{section_code}/specification',
    pathParams: ['section_code'],
    queryParams: ['limit', 'offset', 'project_uid', 'q'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['optimisation'],
  },
  getSpecificationPrices: {
    operationId: 'getSpecificationPrices',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/specification-prices',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: ['limit', 'offset'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['optimisation'],
  },
  getStageAssembly: {
    operationId: 'getStageAssembly',
    method: 'GET',
    path: '/stage-assemblies/{stage_assembly_id}',
    pathParams: ['stage_assembly_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  getStageChainBatch: {
    operationId: 'getStageChainBatch',
    method: 'GET',
    path: '/stage-chain-batches/{stage_chain_batch_id}',
    pathParams: ['stage_chain_batch_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  getStageChainRun: {
    operationId: 'getStageChainRun',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getStageChangeCard: {
    operationId: 'getStageChangeCard',
    method: 'GET',
    path: '/stage-change-cards/{stage_change_card_id}',
    pathParams: ['stage_change_card_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  getStageChangeJournal: {
    operationId: 'getStageChangeJournal',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/journal',
    pathParams: ['stage_chain_run_id'],
    queryParams: ['grouping'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  getStageModelLayout: {
    operationId: 'getStageModelLayout',
    method: 'GET',
    path: '/model-layout',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  getStagePair: {
    operationId: 'getStagePair',
    method: 'GET',
    path: '/stage-pairs/{stage_pair_id}',
    pathParams: ['stage_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getStageProfileText: {
    operationId: 'getStageProfileText',
    method: 'GET',
    path: '/comparison-page-profiles/{comparison_page_profile_id}/stage-text',
    pathParams: ['comparison_page_profile_id'],
    queryParams: ['query'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  getStageQuality: {
    operationId: 'getStageQuality',
    method: 'GET',
    path: '/stage-quality',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  getStageSheetMap: {
    operationId: 'getStageSheetMap',
    method: 'GET',
    path: '/stage-pairs/{stage_pair_id}/sheet-map',
    pathParams: ['stage_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getStageSheetMapRevision: {
    operationId: 'getStageSheetMapRevision',
    method: 'GET',
    path: '/stage-link-revisions/{stage_link_revision_id}',
    pathParams: ['stage_link_revision_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getStageSynthesis: {
    operationId: 'getStageSynthesis',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/synthesis',
    pathParams: ['stage_chain_run_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  getStageUpload: {
    operationId: 'getStageUpload',
    method: 'GET',
    path: '/stage-uploads/{stage_upload_id}',
    pathParams: ['stage_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getUser: {
    operationId: 'getUser',
    method: 'GET',
    path: '/users/{user_uid}',
    pathParams: ['user_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['users'],
  },
  getVectorControl: {
    operationId: 'getVectorControl',
    method: 'GET',
    path: '/vector-control',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  getVersionBlocks: {
    operationId: 'getVersionBlocks',
    method: 'GET',
    path: '/versions/{version_uid}/blocks',
    pathParams: ['version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['documents'],
  },
  getVersionPageProfile: {
    operationId: 'getVersionPageProfile',
    method: 'GET',
    path: '/page-profiles/{comparison_page_profile_id}',
    pathParams: ['comparison_page_profile_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getVersionPageSpecPositions: {
    operationId: 'getVersionPageSpecPositions',
    method: 'GET',
    path: '/page-profiles/{comparison_page_profile_id}/spec-positions',
    pathParams: ['comparison_page_profile_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  getVersionSectionReview: {
    operationId: 'getVersionSectionReview',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/section-review',
    pathParams: ['document_uid', 'project_uid', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['documents'],
  },
  getWorkSchedule: {
    operationId: 'getWorkSchedule',
    method: 'GET',
    path: '/work-schedule',
    pathParams: [],
    queryParams: ['month'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['schedule'],
  },
  getWorkScheduleReserve: {
    operationId: 'getWorkScheduleReserve',
    method: 'GET',
    path: '/work-schedule/reserve',
    pathParams: [],
    queryParams: ['days', 'start'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['schedule'],
  },
  importComparisonZip: {
    operationId: 'importComparisonZip',
    method: 'POST',
    path: '/projects/{project_uid}/comparison-zip-uploads',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: ['X-Archive-Name'],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/zip',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  importOptimisationProposalDecisions: {
    operationId: 'importOptimisationProposalDecisions',
    method: 'POST',
    path: '/optimisation-passes/{optimisation_pass_id}/decision-imports',
    pathParams: ['optimisation_pass_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'multipart/form-data',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['optimisation'],
  },
  importRunDecisions: {
    operationId: 'importRunDecisions',
    method: 'POST',
    path: '/runs/{run_id}/decision-imports',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'multipart/form-data',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['export'],
  },
  issueExecutorEnrollment: {
    operationId: 'issueExecutorEnrollment',
    method: 'POST',
    path: '/executor-connections/{connection_id}/enrollments',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  issueExecutorHostEnrollment: {
    operationId: 'issueExecutorHostEnrollment',
    method: 'POST',
    path: '/executor-hosts/enrollments',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  issueRunnerToken: {
    operationId: 'issueRunnerToken',
    method: 'POST',
    path: '/executor-connections/{connection_id}/runner-tokens',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  issueToken: {
    operationId: 'issueToken',
    method: 'POST',
    path: '/auth/token',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 422, 500, 503],
    tags: ['auth'],
  },
  listAcceptedOptimisationProposals: {
    operationId: 'listAcceptedOptimisationProposals',
    method: 'GET',
    path: '/optimisation-proposals/accepted',
    pathParams: [],
    queryParams: ['cursor', 'limit', 'project_uid', 'section_code'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['optimisation'],
  },
  listAnalysisPresets: {
    operationId: 'listAnalysisPresets',
    method: 'GET',
    path: '/analysis/presets',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['analysis'],
  },
  listAnalysisProfiles: {
    operationId: 'listAnalysisProfiles',
    method: 'GET',
    path: '/analysis/profiles',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['analysis'],
  },
  listAssignments: {
    operationId: 'listAssignments',
    method: 'GET',
    path: '/assignments',
    pathParams: [],
    queryParams: ['cursor', 'limit', 'mine', 'project_uid', 'status'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['dispatch'],
  },
  listAuthEvents: {
    operationId: 'listAuthEvents',
    method: 'GET',
    path: '/auth-events',
    pathParams: [],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['users'],
  },
  listComparisonAiLinks: {
    operationId: 'listComparisonAiLinks',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-ai-links',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonAiPairHints: {
    operationId: 'listComparisonAiPairHints',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-hints',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonMatrixEdits: {
    operationId: 'listComparisonMatrixEdits',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonReports: {
    operationId: 'listComparisonReports',
    method: 'GET',
    path: '/comparison-series/{comparison_series_id}/reports',
    pathParams: ['comparison_series_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonReviewSheets: {
    operationId: 'listComparisonReviewSheets',
    method: 'GET',
    path: '/comparison-transitions/{comparison_transition_id}/review-sheets',
    pathParams: ['comparison_transition_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonSeries: {
    operationId: 'listComparisonSeries',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-series',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonSheetDescriptionHistory: {
    operationId: 'listComparisonSheetDescriptionHistory',
    method: 'GET',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}/description-history',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonSheetPairs: {
    operationId: 'listComparisonSheetPairs',
    method: 'GET',
    path: '/comparison-transitions/{comparison_transition_id}/sheet-pairs',
    pathParams: ['comparison_transition_id'],
    queryParams: ['cursor', 'limit', 'only_changes', 'status'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonSpecificationChanges: {
    operationId: 'listComparisonSpecificationChanges',
    method: 'GET',
    path: '/comparison-transitions/{comparison_transition_id}/specification/changes',
    pathParams: ['comparison_transition_id'],
    queryParams: ['cursor', 'kind', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonSpecifications: {
    operationId: 'listComparisonSpecifications',
    method: 'GET',
    path: '/comparison-series/{comparison_series_id}/specifications',
    pathParams: ['comparison_series_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonUploads: {
    operationId: 'listComparisonUploads',
    method: 'GET',
    path: '/projects/{project_uid}/comparison-uploads',
    pathParams: ['project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listComparisonVersionOrders: {
    operationId: 'listComparisonVersionOrders',
    method: 'GET',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-version-orders',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listDecisionHistory: {
    operationId: 'listDecisionHistory',
    method: 'GET',
    path: '/findings/{finding_uid}/decisions',
    pathParams: ['finding_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['decisions'],
  },
  listDecisionMemoryCases: {
    operationId: 'listDecisionMemoryCases',
    method: 'GET',
    path: '/decision-memory/cases',
    pathParams: [],
    queryParams: ['category', 'cursor', 'data_class', 'limit', 'origin_project_uid', 'section_code', 'status', 'verdict'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['decision-memory'],
  },
  listDecisionPatterns: {
    operationId: 'listDecisionPatterns',
    method: 'GET',
    path: '/decision-memory/patterns',
    pathParams: [],
    queryParams: ['limit', 'section_code', 'status'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['decision-memory'],
  },
  listDecisions: {
    operationId: 'listDecisions',
    method: 'GET',
    path: '/decisions',
    pathParams: [],
    queryParams: ['category', 'cursor', 'limit', 'project_uid', 'verdict'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['decisions'],
  },
  listDocumentTags: {
    operationId: 'listDocumentTags',
    method: 'GET',
    path: '/projects/{project_uid}/document-tags',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['documents'],
  },
  listDocuments: {
    operationId: 'listDocuments',
    method: 'GET',
    path: '/projects/{project_uid}/documents',
    pathParams: ['project_uid'],
    queryParams: ['audit_state', 'cursor', 'include_archived', 'limit', 'order', 'section_code', 'tag'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['documents'],
  },
  listExecutionJournal: {
    operationId: 'listExecutionJournal',
    method: 'GET',
    path: '/execution/journal',
    pathParams: [],
    queryParams: ['cursor', 'limit', 'run_id'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['execution'],
  },
  listExecutionQueue: {
    operationId: 'listExecutionQueue',
    method: 'GET',
    path: '/execution/queue',
    pathParams: [],
    queryParams: ['created_from', 'created_to', 'cursor', 'limit', 'state', 'state_group'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['execution'],
  },
  listExecutorConnections: {
    operationId: 'listExecutorConnections',
    method: 'GET',
    path: '/executor-connections',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  listExecutorGroups: {
    operationId: 'listExecutorGroups',
    method: 'GET',
    path: '/executor-groups',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  listExecutorHosts: {
    operationId: 'listExecutorHosts',
    method: 'GET',
    path: '/executor-hosts',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  listExecutorRoutes: {
    operationId: 'listExecutorRoutes',
    method: 'GET',
    path: '/executor-routes',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  listExecutorRoutingRules: {
    operationId: 'listExecutorRoutingRules',
    method: 'GET',
    path: '/executor-routing-rules',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  listKnowledgeBaseEntries: {
    operationId: 'listKnowledgeBaseEntries',
    method: 'GET',
    path: '/knowledge-base/entries',
    pathParams: [],
    queryParams: ['cursor', 'limit', 'project_uid'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['decisions'],
  },
  listModelCatalogue: {
    operationId: 'listModelCatalogue',
    method: 'GET',
    path: '/model-catalogue',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  listNormDocuments: {
    operationId: 'listNormDocuments',
    method: 'GET',
    path: '/norm-documents',
    pathParams: [],
    queryParams: ['cursor', 'kind', 'limit', 'q'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['norms'],
  },
  listNormParagraphs: {
    operationId: 'listNormParagraphs',
    method: 'GET',
    path: '/norm-documents/{norm_document_id}/paragraphs',
    pathParams: ['norm_document_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['norms'],
  },
  listNormSnapshotEvents: {
    operationId: 'listNormSnapshotEvents',
    method: 'GET',
    path: '/norms/snapshots/events',
    pathParams: [],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['norms'],
  },
  listNormSnapshots: {
    operationId: 'listNormSnapshots',
    method: 'GET',
    path: '/norms/snapshots',
    pathParams: [],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['norms'],
  },
  listOptimisationPasses: {
    operationId: 'listOptimisationPasses',
    method: 'GET',
    path: '/projects/{project_uid}/optimisation-passes',
    pathParams: ['project_uid'],
    queryParams: ['document_uid', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['optimisation'],
  },
  listOptimisationProposals: {
    operationId: 'listOptimisationProposals',
    method: 'GET',
    path: '/optimisation-passes/{optimisation_pass_id}/proposals',
    pathParams: ['optimisation_pass_id'],
    queryParams: ['decision', 'limit', 'offset'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['optimisation'],
  },
  listPrecedentSettings: {
    operationId: 'listPrecedentSettings',
    method: 'GET',
    path: '/precedent-settings',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  listPriceListPositions: {
    operationId: 'listPriceListPositions',
    method: 'GET',
    path: '/price-lists/{price_list_id}/positions',
    pathParams: ['price_list_id'],
    queryParams: ['limit', 'offset'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['optimisation'],
  },
  listPriceListRevisions: {
    operationId: 'listPriceListRevisions',
    method: 'GET',
    path: '/projects/{project_uid}/price-lists',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['optimisation'],
  },
  listProjects: {
    operationId: 'listProjects',
    method: 'GET',
    path: '/projects',
    pathParams: [],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['projects'],
  },
  listProposalDecisionJournal: {
    operationId: 'listProposalDecisionJournal',
    method: 'GET',
    path: '/proposal-decisions',
    pathParams: [],
    queryParams: ['cursor', 'limit', 'project_uid'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['decisions'],
  },
  listProposalDecisions: {
    operationId: 'listProposalDecisions',
    method: 'GET',
    path: '/optimisation-proposals/{optimisation_proposal_id}/decisions',
    pathParams: ['optimisation_proposal_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['optimisation'],
  },
  listRegistrations: {
    operationId: 'listRegistrations',
    method: 'GET',
    path: '/registrations',
    pathParams: [],
    queryParams: ['cursor', 'limit', 'status'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['registrations'],
  },
  listReleases: {
    operationId: 'listReleases',
    method: 'GET',
    path: '/releases',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['releases'],
  },
  listRunFindingBlocks: {
    operationId: 'listRunFindingBlocks',
    method: 'GET',
    path: '/runs/{run_id}/finding-blocks',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['findings'],
  },
  listRunFindings: {
    operationId: 'listRunFindings',
    method: 'GET',
    path: '/runs/{run_id}/findings',
    pathParams: ['run_id'],
    queryParams: ['category', 'cursor', 'limit', 'verdict'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['findings'],
  },
  listRuns: {
    operationId: 'listRuns',
    method: 'GET',
    path: '/versions/{version_uid}/runs',
    pathParams: ['version_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['runs'],
  },
  listStageAiReviews: {
    operationId: 'listStageAiReviews',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/ai-reviews',
    pathParams: ['stage_chain_run_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageCardVerdicts: {
    operationId: 'listStageCardVerdicts',
    method: 'GET',
    path: '/stage-change-cards/{stage_change_card_id}/verdicts',
    pathParams: ['stage_change_card_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageChainRuns: {
    operationId: 'listStageChainRuns',
    method: 'GET',
    path: '/stage-pairs/{stage_pair_id}/chain-runs',
    pathParams: ['stage_pair_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageChangeCards: {
    operationId: 'listStageChangeCards',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/cards',
    pathParams: ['stage_chain_run_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageClassifications: {
    operationId: 'listStageClassifications',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/classifications',
    pathParams: ['stage_chain_run_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageGraphicEvidence: {
    operationId: 'listStageGraphicEvidence',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/graphic-evidence',
    pathParams: ['stage_chain_run_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageLinkRepairs: {
    operationId: 'listStageLinkRepairs',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/sheet-link-repairs',
    pathParams: ['stage_chain_run_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  listStagePairSuggestions: {
    operationId: 'listStagePairSuggestions',
    method: 'GET',
    path: '/projects/{project_uid}/stage-pair-suggestions',
    pathParams: ['project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStagePairs: {
    operationId: 'listStagePairs',
    method: 'GET',
    path: '/projects/{project_uid}/stage-pairs',
    pathParams: ['project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageRawDifferences: {
    operationId: 'listStageRawDifferences',
    method: 'GET',
    path: '/stage-link-revisions/{stage_link_revision_id}/raw-differences',
    pathParams: ['stage_link_revision_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageSheetMapHistory: {
    operationId: 'listStageSheetMapHistory',
    method: 'GET',
    path: '/stage-pairs/{stage_pair_id}/sheet-map/revisions',
    pathParams: ['stage_pair_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageSheetPassports: {
    operationId: 'listStageSheetPassports',
    method: 'GET',
    path: '/stage-pairs/{stage_pair_id}/sheet-passports',
    pathParams: ['stage_pair_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageSheetSuggestions: {
    operationId: 'listStageSheetSuggestions',
    method: 'GET',
    path: '/stage-pairs/{stage_pair_id}/sheet-suggestions',
    pathParams: ['stage_pair_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageTextExclusions: {
    operationId: 'listStageTextExclusions',
    method: 'GET',
    path: '/stage-link-revisions/{stage_link_revision_id}/text-exclusions',
    pathParams: ['stage_link_revision_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageTextFragments: {
    operationId: 'listStageTextFragments',
    method: 'GET',
    path: '/stage-pairs/{stage_pair_id}/text-fragments',
    pathParams: ['stage_pair_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageTextHints: {
    operationId: 'listStageTextHints',
    method: 'GET',
    path: '/stage-link-revisions/{stage_link_revision_id}/text-hints',
    pathParams: ['stage_link_revision_id'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listStageUploads: {
    operationId: 'listStageUploads',
    method: 'GET',
    path: '/projects/{project_uid}/stage-uploads',
    pathParams: ['project_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listUsers: {
    operationId: 'listUsers',
    method: 'GET',
    path: '/users',
    pathParams: [],
    queryParams: ['cursor', 'include_archived', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['users'],
  },
  listVersionPageProfiles: {
    operationId: 'listVersionPageProfiles',
    method: 'GET',
    path: '/versions/{version_uid}/page-profiles',
    pathParams: ['version_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  listVersionPortalBlocks: {
    operationId: 'listVersionPortalBlocks',
    method: 'GET',
    path: '/versions/{version_uid}/portal-blocks',
    pathParams: ['version_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['documents'],
  },
  listVersionSheetLabels: {
    operationId: 'listVersionSheetLabels',
    method: 'GET',
    path: '/versions/{version_uid}/sheet-labels',
    pathParams: ['version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['documents'],
  },
  listVersions: {
    operationId: 'listVersions',
    method: 'GET',
    path: '/documents/{document_uid}/versions',
    pathParams: ['document_uid'],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['documents'],
  },
  listWorkers: {
    operationId: 'listWorkers',
    method: 'GET',
    path: '/execution/workers',
    pathParams: [],
    queryParams: ['cursor', 'limit'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['execution'],
  },
  markReleaseNotesRead: {
    operationId: 'markReleaseNotesRead',
    method: 'PUT',
    path: '/me/release-notes',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: null,
    successStatuses: [204],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['account'],
  },
  pauseComparisonAiPairCheck: {
    operationId: 'pauseComparisonAiPairCheck',
    method: 'POST',
    path: '/comparison-ai-pair-checks/{comparison_ai_job_id}/pause',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  pauseComparisonAiSheetChanges: {
    operationId: 'pauseComparisonAiSheetChanges',
    method: 'POST',
    path: '/comparison-ai-sheet-jobs/{comparison_ai_job_id}/pause',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  pauseComparisonLaunchQueue: {
    operationId: 'pauseComparisonLaunchQueue',
    method: 'POST',
    path: '/projects/{project_uid}/comparison-launch-queue/pause',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  pauseComparisonSeries: {
    operationId: 'pauseComparisonSeries',
    method: 'POST',
    path: '/comparison-series/{comparison_series_id}/pause',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  pauseComparisonUpload: {
    operationId: 'pauseComparisonUpload',
    method: 'POST',
    path: '/comparison-uploads/{comparison_upload_id}/pause',
    pathParams: ['comparison_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  pauseStageChainBatch: {
    operationId: 'pauseStageChainBatch',
    method: 'POST',
    path: '/stage-chain-batches/{stage_chain_batch_id}/pause',
    pathParams: ['stage_chain_batch_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  pauseStageUpload: {
    operationId: 'pauseStageUpload',
    method: 'POST',
    path: '/stage-uploads/{stage_upload_id}/pause',
    pathParams: ['stage_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  prepareComparisonClientReport: {
    operationId: 'prepareComparisonClientReport',
    method: 'POST',
    path: '/comparison-reports/{comparison_report_id}/client-report',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  prepareComparisonMatrix: {
    operationId: 'prepareComparisonMatrix',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-matrix/preparation',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  previewExecutorRouting: {
    operationId: 'previewExecutorRouting',
    method: 'GET',
    path: '/executor-routing/preview',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['execution'],
  },
  purgeUser: {
    operationId: 'purgeUser',
    method: 'DELETE',
    path: '/users/{user_uid}',
    pathParams: ['user_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: null,
    successStatuses: [204],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['users'],
  },
  readRegistrationStatus: {
    operationId: 'readRegistrationStatus',
    method: 'POST',
    path: '/registrations/status',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 422, 500, 503],
    tags: ['registrations'],
  },
  reauditRun: {
    operationId: 'reauditRun',
    method: 'POST',
    path: '/runs/{run_id}/reaudit',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [202],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  rebuildComparisonReportPdf: {
    operationId: 'rebuildComparisonReportPdf',
    method: 'POST',
    path: '/comparison-reports/{comparison_report_id}/pdf-rebuild',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  recomputeStageTextEvidence: {
    operationId: 'recomputeStageTextEvidence',
    method: 'POST',
    path: '/stage-link-revisions/{stage_link_revision_id}/text-evidence/recomputation',
    pathParams: ['stage_link_revision_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [202],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  redeemExecutorEnrollment: {
    operationId: 'redeemExecutorEnrollment',
    method: 'POST',
    path: '/runner/enroll',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 409, 422, 500, 503],
    tags: ['execution'],
  },
  rejectRegistration: {
    operationId: 'rejectRegistration',
    method: 'POST',
    path: '/registrations/{request_id}/reject',
    pathParams: ['request_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['registrations'],
  },
  rejectStageUploadCandidate: {
    operationId: 'rejectStageUploadCandidate',
    method: 'POST',
    path: '/stage-upload-candidates/{stage_upload_candidate_id}/rejection',
    pathParams: ['stage_upload_candidate_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  removeComparisonLaunchEntry: {
    operationId: 'removeComparisonLaunchEntry',
    method: 'POST',
    path: '/comparison-launch-entries/{comparison_launch_entry_id}/removal',
    pathParams: ['comparison_launch_entry_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  renameDocument: {
    operationId: 'renameDocument',
    method: 'PUT',
    path: '/projects/{project_uid}/documents/{document_uid}/title',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  reportRunnerHealth: {
    operationId: 'reportRunnerHealth',
    method: 'POST',
    path: '/runner/health',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 422, 500, 503],
    tags: ['execution'],
  },
  requestExecutorProbe: {
    operationId: 'requestExecutorProbe',
    method: 'POST',
    path: '/executor-connections/{connection_id}/probes',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [202],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  resetUserPassword: {
    operationId: 'resetUserPassword',
    method: 'POST',
    path: '/users/{user_uid}/password',
    pathParams: ['user_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['users'],
  },
  restoreDecisionMemoryCase: {
    operationId: 'restoreDecisionMemoryCase',
    method: 'POST',
    path: '/decision-memory/cases/{case_id}/restore',
    pathParams: ['case_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['decision-memory'],
  },
  restoreUser: {
    operationId: 'restoreUser',
    method: 'POST',
    path: '/users/{user_uid}/restore',
    pathParams: ['user_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['users'],
  },
  resumeComparisonAiPairCheck: {
    operationId: 'resumeComparisonAiPairCheck',
    method: 'POST',
    path: '/comparison-ai-pair-checks/{comparison_ai_job_id}/resume',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  resumeComparisonAiSheetChanges: {
    operationId: 'resumeComparisonAiSheetChanges',
    method: 'POST',
    path: '/comparison-ai-sheet-jobs/{comparison_ai_job_id}/resume',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  resumeComparisonLaunchQueue: {
    operationId: 'resumeComparisonLaunchQueue',
    method: 'POST',
    path: '/projects/{project_uid}/comparison-launch-queue/resume',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  resumeComparisonSeries: {
    operationId: 'resumeComparisonSeries',
    method: 'POST',
    path: '/comparison-series/{comparison_series_id}/resume',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  resumeComparisonUpload: {
    operationId: 'resumeComparisonUpload',
    method: 'POST',
    path: '/comparison-uploads/{comparison_upload_id}/resume',
    pathParams: ['comparison_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  resumeStageChainBatch: {
    operationId: 'resumeStageChainBatch',
    method: 'POST',
    path: '/stage-chain-batches/{stage_chain_batch_id}/resume',
    pathParams: ['stage_chain_batch_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  resumeStageChainRun: {
    operationId: 'resumeStageChainRun',
    method: 'POST',
    path: '/stage-chain-runs/{stage_chain_run_id}/resume',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  resumeStageUpload: {
    operationId: 'resumeStageUpload',
    method: 'POST',
    path: '/stage-uploads/{stage_upload_id}/resume',
    pathParams: ['stage_upload_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  retryComparisonAiSheetChanges: {
    operationId: 'retryComparisonAiSheetChanges',
    method: 'POST',
    path: '/comparison-ai-sheet-jobs/{comparison_ai_job_id}/retry',
    pathParams: ['comparison_ai_job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  retryComparisonUploadSet: {
    operationId: 'retryComparisonUploadSet',
    method: 'POST',
    path: '/comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/retry',
    pathParams: ['comparison_upload_id', 'comparison_upload_set_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  reviewDecisionPattern: {
    operationId: 'reviewDecisionPattern',
    method: 'POST',
    path: '/decision-memory/patterns/{pattern_id}/review',
    pathParams: ['pattern_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['decision-memory'],
  },
  reviseAnalysisPreset: {
    operationId: 'reviseAnalysisPreset',
    method: 'POST',
    path: '/analysis/presets/{preset_id}/revisions',
    pathParams: ['preset_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['analysis'],
  },
  reviseExecutorConnection: {
    operationId: 'reviseExecutorConnection',
    method: 'POST',
    path: '/executor-connections/{connection_id}/revisions',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  reviseExecutorGroup: {
    operationId: 'reviseExecutorGroup',
    method: 'POST',
    path: '/executor-groups/{group_id}/revisions',
    pathParams: ['group_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  reviseStageAssembly: {
    operationId: 'reviseStageAssembly',
    method: 'POST',
    path: '/stage-assemblies/{stage_assembly_id}/members',
    pathParams: ['stage_assembly_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  reviseStageModelLayout: {
    operationId: 'reviseStageModelLayout',
    method: 'POST',
    path: '/model-layout/revisions',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  revokeRunnerToken: {
    operationId: 'revokeRunnerToken',
    method: 'POST',
    path: '/executor-connections/{connection_id}/runner-tokens/{token_id}/revoke',
    pathParams: ['connection_id', 'token_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  scheduleAssignments: {
    operationId: 'scheduleAssignments',
    method: 'POST',
    path: '/work-schedule/reserve/moves',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: null,
    successStatuses: [204],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['schedule'],
  },
  searchNorms: {
    operationId: 'searchNorms',
    method: 'GET',
    path: '/norms/search',
    pathParams: [],
    queryParams: ['cursor', 'limit', 'norms_snapshot_id', 'q'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['norms'],
  },
  setCurrentNormSnapshot: {
    operationId: 'setCurrentNormSnapshot',
    method: 'PUT',
    path: '/norms/snapshots/current',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['norms'],
  },
  setDocumentArchived: {
    operationId: 'setDocumentArchived',
    method: 'PUT',
    path: '/projects/{project_uid}/documents/{document_uid}/archive',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  setDocumentTags: {
    operationId: 'setDocumentTags',
    method: 'PUT',
    path: '/projects/{project_uid}/documents/{document_uid}/tags',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  setEngineerAbsences: {
    operationId: 'setEngineerAbsences',
    method: 'PUT',
    path: '/work-schedule/absences',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: null,
    successStatuses: [204],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['schedule'],
  },
  setExecutionPaused: {
    operationId: 'setExecutionPaused',
    method: 'PUT',
    path: '/execution/dispatch',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setExecutorHostEnabled: {
    operationId: 'setExecutorHostEnabled',
    method: 'PUT',
    path: '/executor-hosts/{host_id}/enabled',
    pathParams: ['host_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setExecutorHostSlots: {
    operationId: 'setExecutorHostSlots',
    method: 'PUT',
    path: '/executor-hosts/{host_id}/slots',
    pathParams: ['host_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setExecutorIntegrationAuthorisation: {
    operationId: 'setExecutorIntegrationAuthorisation',
    method: 'POST',
    path: '/executor-connections/{connection_id}/integration-authorisation',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setExecutorRoute: {
    operationId: 'setExecutorRoute',
    method: 'PUT',
    path: '/executor-routes',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setExecutorRoutingMode: {
    operationId: 'setExecutorRoutingMode',
    method: 'POST',
    path: '/executor-routing/mode',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setExecutorRoutingRule: {
    operationId: 'setExecutorRoutingRule',
    method: 'PUT',
    path: '/executor-routing-rules/{work_kind}',
    pathParams: ['work_kind'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setExecutorSecret: {
    operationId: 'setExecutorSecret',
    method: 'POST',
    path: '/executor-connections/{connection_id}/secrets',
    pathParams: ['connection_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setFindingExecutionStatus: {
    operationId: 'setFindingExecutionStatus',
    method: 'PUT',
    path: '/findings/{finding_uid}/execution-status',
    pathParams: ['finding_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['findings'],
  },
  setGlobalVendorList: {
    operationId: 'setGlobalVendorList',
    method: 'PUT',
    path: '/vendor-lists/{section_code}',
    pathParams: ['section_code'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['optimisation'],
  },
  setJobPriority: {
    operationId: 'setJobPriority',
    method: 'PUT',
    path: '/execution/queue/{job_id}/priority',
    pathParams: ['job_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setProjectVendorList: {
    operationId: 'setProjectVendorList',
    method: 'PUT',
    path: '/projects/{project_uid}/vendor-lists/{section_code}',
    pathParams: ['project_uid', 'section_code'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['optimisation'],
  },
  setStageModelLayoutEnabled: {
    operationId: 'setStageModelLayoutEnabled',
    method: 'PUT',
    path: '/model-layout/enabled',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setStagePairCompleteness: {
    operationId: 'setStagePairCompleteness',
    method: 'POST',
    path: '/stage-pairs/{stage_pair_id}/completeness',
    pathParams: ['stage_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  setVectorPaused: {
    operationId: 'setVectorPaused',
    method: 'PUT',
    path: '/vector-control/paused',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['execution'],
  },
  setWorkCalendarDays: {
    operationId: 'setWorkCalendarDays',
    method: 'PUT',
    path: '/work-calendar/days',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: null,
    successStatuses: [204],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['schedule'],
  },
  setWorkSchedulePlans: {
    operationId: 'setWorkSchedulePlans',
    method: 'PUT',
    path: '/work-schedule/plans',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['schedule'],
  },
  setWorkScheduleSettings: {
    operationId: 'setWorkScheduleSettings',
    method: 'PUT',
    path: '/work-schedule/settings',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['schedule'],
  },
  setWorkerIntake: {
    operationId: 'setWorkerIntake',
    method: 'PUT',
    path: '/execution/workers/{worker_id}/intake',
    pathParams: ['worker_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  startComparisonAiPairCheck: {
    operationId: 'startComparisonAiPairCheck',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  startComparisonAiSheetChanges: {
    operationId: 'startComparisonAiSheetChanges',
    method: 'POST',
    path: '/comparison-series/{comparison_series_id}/ai-sheet-changes',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  startComparisonReport: {
    operationId: 'startComparisonReport',
    method: 'POST',
    path: '/comparison-reports/{comparison_report_id}/start',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  startComparisonSeries: {
    operationId: 'startComparisonSeries',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-series',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  startComparisonSheetDescription: {
    operationId: 'startComparisonSheetDescription',
    method: 'POST',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}/description',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  startComparisonSpecification: {
    operationId: 'startComparisonSpecification',
    method: 'POST',
    path: '/comparison-transitions/{comparison_transition_id}/specification',
    pathParams: ['comparison_transition_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  startOptimisationPass: {
    operationId: 'startOptimisationPass',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/optimisation-passes',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['optimisation'],
  },
  startRun: {
    operationId: 'startRun',
    method: 'POST',
    path: '/runs',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [202],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['runs'],
  },
  startRunFromStage: {
    operationId: 'startRunFromStage',
    method: 'POST',
    path: '/runs/{run_id}/start-from-stage',
    pathParams: ['run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [202],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  startStageChainBatch: {
    operationId: 'startStageChainBatch',
    method: 'POST',
    path: '/projects/{project_uid}/stage-chain-batches',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  startStageChainRun: {
    operationId: 'startStageChainRun',
    method: 'POST',
    path: '/stage-pairs/{stage_pair_id}/chain-runs',
    pathParams: ['stage_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  streamComparisonPairTile: {
    operationId: 'streamComparisonPairTile',
    method: 'GET',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}/tile',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: ['align_blocks', 'column', 'layers', 'level', 'mode', 'row'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'image/png',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  streamComparisonReportPdf: {
    operationId: 'streamComparisonReportPdf',
    method: 'GET',
    path: '/comparison-reports/{comparison_report_id}/pdf',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/pdf',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  streamComparisonReportSourceMd: {
    operationId: 'streamComparisonReportSourceMd',
    method: 'GET',
    path: '/comparison-reports/{comparison_report_id}/source-md',
    pathParams: ['comparison_report_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'text/markdown',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  streamComparisonSeriesSummary: {
    operationId: 'streamComparisonSeriesSummary',
    method: 'GET',
    path: '/comparison-series/{comparison_series_id}/summary-md',
    pathParams: ['comparison_series_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'text/markdown',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  streamComparisonSheetDescriptionMd: {
    operationId: 'streamComparisonSheetDescriptionMd',
    method: 'GET',
    path: '/comparison-sheet-pairs/{comparison_sheet_pair_id}/description/md',
    pathParams: ['comparison_sheet_pair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'text/markdown',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 500, 503],
    tags: ['comparison'],
  },
  streamComparisonTechnicalReport: {
    operationId: 'streamComparisonTechnicalReport',
    method: 'GET',
    path: '/comparison-series/{comparison_series_id}/technical-report',
    pathParams: ['comparison_series_id'],
    queryParams: ['format'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/octet-stream',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  streamDocumentVersionContent: {
    operationId: 'streamDocumentVersionContent',
    method: 'GET',
    path: '/versions/{version_uid}/content',
    pathParams: ['version_uid'],
    queryParams: [],
    headerParams: ['Range'],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/pdf',
    successStatuses: [200, 206],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['documents'],
  },
  streamNormDocumentContent: {
    operationId: 'streamNormDocumentContent',
    method: 'GET',
    path: '/norm-documents/{norm_document_id}/content',
    pathParams: ['norm_document_id'],
    queryParams: [],
    headerParams: ['Range'],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/pdf',
    successStatuses: [200, 206],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['norms'],
  },
  streamStageChangeJournalHtml: {
    operationId: 'streamStageChangeJournalHtml',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/journal.html',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'text/html',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  streamStageChangeJournalPdf: {
    operationId: 'streamStageChangeJournalPdf',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/journal.pdf',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/pdf',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  streamStageChangeJournalXlsx: {
    operationId: 'streamStageChangeJournalXlsx',
    method: 'GET',
    path: '/stage-chain-runs/{stage_chain_run_id}/journal.xlsx',
    pathParams: ['stage_chain_run_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  streamVersionPagePreview: {
    operationId: 'streamVersionPagePreview',
    method: 'GET',
    path: '/page-profiles/{comparison_page_profile_id}/preview',
    pathParams: ['comparison_page_profile_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'image/png',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  streamVersionPageThumbnail: {
    operationId: 'streamVersionPageThumbnail',
    method: 'GET',
    path: '/page-profiles/{comparison_page_profile_id}/thumbnail',
    pathParams: ['comparison_page_profile_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'image/png',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['comparison'],
  },
  streamVersionPageTile: {
    operationId: 'streamVersionPageTile',
    method: 'GET',
    path: '/page-profiles/{comparison_page_profile_id}/tile',
    pathParams: ['comparison_page_profile_id'],
    queryParams: ['column', 'level', 'row'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'image/png',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 422, 500, 503],
    tags: ['comparison'],
  },
  streamVersionPortalBlockCrop: {
    operationId: 'streamVersionPortalBlockCrop',
    method: 'GET',
    path: '/versions/{version_uid}/portal-blocks/{portal_block_id}/crop',
    pathParams: ['portal_block_id', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'image/png',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 500, 503],
    tags: ['documents'],
  },
  submitExecutorTaskAnswer: {
    operationId: 'submitExecutorTaskAnswer',
    method: 'POST',
    path: '/runner/tasks/{task_id}/answer',
    pathParams: ['task_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 404, 409, 422, 500, 503],
    tags: ['execution'],
  },
  submitRegistration: {
    operationId: 'submitRegistration',
    method: 'POST',
    path: '/registrations',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [409, 422, 500, 503],
    tags: ['registrations'],
  },
  transitionAssignment: {
    operationId: 'transitionAssignment',
    method: 'POST',
    path: '/assignments/{assignment_uid}/transitions',
    pathParams: ['assignment_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['dispatch'],
  },
  undoComparisonMatrixEdit: {
    operationId: 'undoComparisonMatrixEdit',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits/undo',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  undoStageLinkRepair: {
    operationId: 'undoStageLinkRepair',
    method: 'POST',
    path: '/stage-link-repairs/{stage_link_repair_id}/undo',
    pathParams: ['stage_link_repair_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  updateMyProfile: {
    operationId: 'updateMyProfile',
    method: 'PATCH',
    path: '/me',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 409, 422, 500, 503],
    tags: ['account'],
  },
  updateUser: {
    operationId: 'updateUser',
    method: 'PATCH',
    path: '/users/{user_uid}',
    pathParams: ['user_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['users'],
  },
  uploadComparisonReportSource: {
    operationId: 'uploadComparisonReportSource',
    method: 'POST',
    path: '/comparison-series/{comparison_series_id}/reports/upload',
    pathParams: ['comparison_series_id'],
    queryParams: ['kind', 'reuse', 'source_name'],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'text/markdown',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  uploadComparisonUploadPart: {
    operationId: 'uploadComparisonUploadPart',
    method: 'PUT',
    path: '/comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/parts',
    pathParams: ['comparison_upload_file_id', 'comparison_upload_id'],
    queryParams: ['part_number'],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/octet-stream',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  uploadDocument: {
    operationId: 'uploadDocument',
    method: 'POST',
    path: '/projects/{project_uid}/documents',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'multipart/form-data',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  uploadDocumentVersion: {
    operationId: 'uploadDocumentVersion',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/versions',
    pathParams: ['document_uid', 'project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'multipart/form-data',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
  uploadPriceList: {
    operationId: 'uploadPriceList',
    method: 'POST',
    path: '/projects/{project_uid}/price-lists',
    pathParams: ['project_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'multipart/form-data',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['optimisation'],
  },
  uploadStageUploadPart: {
    operationId: 'uploadStageUploadPart',
    method: 'PUT',
    path: '/stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/parts',
    pathParams: ['stage_upload_file_id', 'stage_upload_id'],
    queryParams: ['part_number'],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/octet-stream',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['comparison'],
  },
  withdrawDecisionMemoryCase: {
    operationId: 'withdrawDecisionMemoryCase',
    method: 'POST',
    path: '/decision-memory/cases/{case_id}/withdraw',
    pathParams: ['case_id'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['decision-memory'],
  },
  withdrawSheetPairing: {
    operationId: 'withdrawSheetPairing',
    method: 'POST',
    path: '/projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings/{sheet_link_id}/withdrawals',
    pathParams: ['document_uid', 'project_uid', 'sheet_link_id', 'version_uid'],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: true,
    requestMediaType: 'application/json',
    responseMediaType: 'application/json',
    successStatuses: [201],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
    tags: ['documents'],
  },
} as const;
