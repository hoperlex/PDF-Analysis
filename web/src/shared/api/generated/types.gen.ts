/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * Every component schema of the PC-01 API as a TypeScript type.
 *
 * Produced by `npm --prefix web run api:generate`
 * (web/scripts/generate-api-client.mjs, generator 1.0.0)
 * from contracts/api/v1/openapi.json
 *   AuditManager PC-01 API 1.50.0 (OpenAPI 3.1.0)
 *   sha256 a67e0b1b205554259d97bd53ea93b48adbe15c49b5d14feb648db40a2d1a8ec6
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

/** The `info.version` of the contract these types were generated from. */
export const CONTRACT_VERSION = '1.50.0';

/** sha256 of the OpenAPI document these types were generated from. */
export const CONTRACT_DIGEST = 'a67e0b1b205554259d97bd53ea93b48adbe15c49b5d14feb648db40a2d1a8ec6';

/** Every component schema name in the contract, sorted. */
export const SCHEMA_NAMES = [
  'AcceptedOptimisationProposal',
  'AcceptedOptimisationProposalPage',
  'Account',
  'AccountPage',
  'AgentPackageVersion',
  'AnalysisPreset',
  'AnalysisPresetList',
  'AnalysisPresetState',
  'AnalysisProfileId',
  'AnalysisProfileList',
  'AnalysisProfileListItem',
  'AnalysisProfileSource',
  'AnalysisProfileSourceFile',
  'AnalysisProfileStatus',
  'AnalysisProfileSummary',
  'AppendComparisonVersionOrderRequest',
  'AppendDecisionRequest',
  'AppendDecisionResponse',
  'ApplyComparisonMatrixEditsRequest',
  'ApplyStageCardVerdictsRequest',
  'ApplyStageSheetMapRequest',
  'ApproveRegistrationRequest',
  'ApproveSheetPairingRequest',
  'ApprovedDiffHunk',
  'ApprovedSheetDiff',
  'ApprovedSheetPair',
  'ApprovedSheetPairs',
  'Assignment',
  'AssignmentDetail',
  'AssignmentEvent',
  'AssignmentEventKind',
  'AssignmentMove',
  'AssignmentPage',
  'AssignmentStatus',
  'AssignmentStatusCount',
  'AssignmentTransitionKind',
  'AssignmentUid',
  'AuthEvent',
  'AuthEventPage',
  'AuthEventType',
  'BlockGeometry',
  'CarryOverDecisionRequest',
  'CarryOverDecisionResponse',
  'CarryOverProposalDecisionsRequest',
  'CarryoverCandidate',
  'CarryoverSourceDecision',
  'ChangePasswordRequest',
  'ClaimExecutorTaskRequest',
  'ClaimedExecutorTask',
  'ClassifyDocumentVersionRequest',
  'ComparedVersion',
  'ComparisonAiCeiling',
  'ComparisonAiCertainty',
  'ComparisonAiChange',
  'ComparisonAiConfidence',
  'ComparisonAiConsent',
  'ComparisonAiCoverage',
  'ComparisonAiDeclaredItem',
  'ComparisonAiDiagnostics',
  'ComparisonAiEstimate',
  'ComparisonAiExcludeReason',
  'ComparisonAiExcluded',
  'ComparisonAiJob',
  'ComparisonAiJobCounts',
  'ComparisonAiJobId',
  'ComparisonAiJobState',
  'ComparisonAiLink',
  'ComparisonAiLinkAnsweredState',
  'ComparisonAiLinkId',
  'ComparisonAiLinkList',
  'ComparisonAiLinkStatus',
  'ComparisonAiMethod',
  'ComparisonAiPairCheck',
  'ComparisonAiPairCounts',
  'ComparisonAiPairDecision',
  'ComparisonAiPairHint',
  'ComparisonAiPairHintPage',
  'ComparisonAiPairQuestionId',
  'ComparisonAiPairQuestionKind',
  'ComparisonAiPauseReason',
  'ComparisonAiQueue',
  'ComparisonAiQueueItem',
  'ComparisonAiRoute',
  'ComparisonAiSheetChanges',
  'ComparisonAiSheetState',
  'ComparisonAiSide',
  'ComparisonAiSpend',
  'ComparisonAiTier',
  'ComparisonAiTransitionProgress',
  'ComparisonAiUnresolved',
  'ComparisonBox',
  'ComparisonCanvas',
  'ComparisonCellConfidence',
  'ComparisonCellFlag',
  'ComparisonCellState',
  'ComparisonChannel',
  'ComparisonChannelState',
  'ComparisonChannels',
  'ComparisonDifference',
  'ComparisonEditProvenance',
  'ComparisonHowCompared',
  'ComparisonId',
  'ComparisonLaunchEntry',
  'ComparisonLaunchEntryId',
  'ComparisonLaunchEntryState',
  'ComparisonLaunchItem',
  'ComparisonLaunchQueue',
  'ComparisonLaunchQueueCounts',
  'ComparisonLaunchQueueState',
  'ComparisonLayer',
  'ComparisonLayoutKind',
  'ComparisonMatrix',
  'ComparisonMatrixCandidate',
  'ComparisonMatrixCell',
  'ComparisonMatrixColumn',
  'ComparisonMatrixCounts',
  'ComparisonMatrixEdit',
  'ComparisonMatrixEditId',
  'ComparisonMatrixEditInput',
  'ComparisonMatrixEditInputKind',
  'ComparisonMatrixEditKind',
  'ComparisonMatrixEditList',
  'ComparisonMatrixEditSource',
  'ComparisonMatrixEditStatus',
  'ComparisonMatrixId',
  'ComparisonMatrixLabelSource',
  'ComparisonMatrixPreparation',
  'ComparisonMatrixProgress',
  'ComparisonMatrixRevision',
  'ComparisonMatrixRow',
  'ComparisonMatrixStaleReason',
  'ComparisonMatrixState',
  'ComparisonModules',
  'ComparisonNoteChange',
  'ComparisonNumberChange',
  'ComparisonOverview',
  'ComparisonOverviewCounters',
  'ComparisonOverviewSet',
  'ComparisonOverviewStep',
  'ComparisonOverviewTotals',
  'ComparisonOverviewUpload',
  'ComparisonPageProfileId',
  'ComparisonPageRef',
  'ComparisonPairPage',
  'ComparisonPairTileMode',
  'ComparisonPartRole',
  'ComparisonPartsCoverage',
  'ComparisonPermit',
  'ComparisonPermitItem',
  'ComparisonPermitState',
  'ComparisonProposalFile',
  'ComparisonProposalSet',
  'ComparisonProposalWarning',
  'ComparisonQueueCounts',
  'ComparisonQueueKind',
  'ComparisonQueueModule',
  'ComparisonQueueSummary',
  'ComparisonRasterSize',
  'ComparisonRefusal',
  'ComparisonReport',
  'ComparisonReportArtifact',
  'ComparisonReportArtifactKind',
  'ComparisonReportFacts',
  'ComparisonReportId',
  'ComparisonReportKind',
  'ComparisonReportPage',
  'ComparisonReportPart',
  'ComparisonReportSource',
  'ComparisonReportStage',
  'ComparisonReportState',
  'ComparisonReportUnitMark',
  'ComparisonReviewSheet',
  'ComparisonReviewSheetKind',
  'ComparisonReviewSheetPage',
  'ComparisonSeries',
  'ComparisonSeriesId',
  'ComparisonSeriesPage',
  'ComparisonSeriesStaleReason',
  'ComparisonSeriesState',
  'ComparisonServiceNote',
  'ComparisonSheetDescription',
  'ComparisonSheetDescriptionHistory',
  'ComparisonSheetDescriptionId',
  'ComparisonSheetDescriptionRevision',
  'ComparisonSheetDescriptionSource',
  'ComparisonSheetPair',
  'ComparisonSheetPairId',
  'ComparisonSheetPairPage',
  'ComparisonSheetPairResultId',
  'ComparisonSheetPairSpecPositions',
  'ComparisonSheetPairState',
  'ComparisonSheetStatus',
  'ComparisonSpecChange',
  'ComparisonSpecChangeKind',
  'ComparisonSpecChangePage',
  'ComparisonSpecComparisonId',
  'ComparisonSpecCoverage',
  'ComparisonSpecExtractionId',
  'ComparisonSpecFieldChange',
  'ComparisonSpecMethod',
  'ComparisonSpecPage',
  'ComparisonSpecPhase',
  'ComparisonSpecPosition',
  'ComparisonSpecState',
  'ComparisonSpecTotals',
  'ComparisonSpecification',
  'ComparisonSpecificationPage',
  'ComparisonStepCounts',
  'ComparisonStepId',
  'ComparisonStepState',
  'ComparisonSummary',
  'ComparisonTextChange',
  'ComparisonTransition',
  'ComparisonTransitionId',
  'ComparisonTransitionState',
  'ComparisonTransitionSummary',
  'ComparisonUpload',
  'ComparisonUploadFile',
  'ComparisonUploadFileDeclaration',
  'ComparisonUploadFileId',
  'ComparisonUploadFileState',
  'ComparisonUploadId',
  'ComparisonUploadPage',
  'ComparisonUploadPartReceipt',
  'ComparisonUploadProposal',
  'ComparisonUploadSetId',
  'ComparisonUploadSetState',
  'ComparisonUploadState',
  'ComparisonVerdictCode',
  'ComparisonVersionOrder',
  'ComparisonVersionOrderId',
  'ComparisonVersionOrderList',
  'ComparisonVersionOrderSource',
  'ConfirmComparisonUploadSetRequest',
  'ConfirmExecutorAgentInstallHostKeyRequest',
  'ConfirmStagePairRequest',
  'ConfirmStageUploadCandidateRequest',
  'ConfirmedComparisonFile',
  'CorrectVersionClassificationRequest',
  'CorrelationId',
  'CostBasis',
  'CreateAssignmentRequest',
  'CreateComparisonReportRequest',
  'CreateComparisonUploadRequest',
  'CreateExecutorAgentInstallRequest',
  'CreateExecutorConnectionRequest',
  'CreateExecutorGroupRequest',
  'CreateExecutorHostAgentInstallRequest',
  'CreateProjectRequest',
  'CreateStageAssemblyRequest',
  'CreateStageReviewCardRequest',
  'CreateStageUploadRequest',
  'Cursor',
  'DashboardSummary',
  'DecideOptimisationProposalRequest',
  'DecisionCarriedFrom',
  'DecisionEvent',
  'DecisionEventPage',
  'DecisionEventType',
  'DecisionId',
  'DecisionImportOutcome',
  'DecisionImportRefusal',
  'DecisionImportReport',
  'DecisionImportRow',
  'DecisionMemoryCase',
  'DecisionMemoryCaseId',
  'DecisionMemoryCasePage',
  'DecisionMemoryCaseSummary',
  'DecisionMemoryContent',
  'DecisionMemoryCountRow',
  'DecisionMemoryCrop',
  'DecisionMemoryDecision',
  'DecisionMemoryEvidence',
  'DecisionMemoryNormRef',
  'DecisionMemoryStatus',
  'DecisionMemoryStatusChange',
  'DecisionMemoryStatusChangeRequest',
  'DecisionMemoryStatusEvent',
  'DecisionRecord',
  'DecisionRecordPage',
  'DiffHunk',
  'DocumentActiveRun',
  'DocumentAudit',
  'DocumentAuditCounts',
  'DocumentTagCount',
  'DocumentTagList',
  'DocumentUid',
  'DocumentVersion',
  'DocumentVersionPage',
  'EffectiveVendorLists',
  'EngineerAbsenceChange',
  'EnqueueComparisonLaunchRequest',
  'ErrorCode',
  'ErrorEnvelope',
  'Evidence',
  'ExecutionDispatchStatus',
  'ExecutionJournalEntry',
  'ExecutionJournalPage',
  'ExecutionQueueItem',
  'ExecutionQueuePage',
  'ExecutionQueueStateCount',
  'ExecutionWorker',
  'ExecutionWorkerPage',
  'ExecutorAgentInstall',
  'ExecutorAgentInstallAccess',
  'ExecutorAgentInstallFailure',
  'ExecutorAgentInstallId',
  'ExecutorAgentInstallState',
  'ExecutorApiFlavour',
  'ExecutorBilling',
  'ExecutorBinding',
  'ExecutorBindingState',
  'ExecutorConnection',
  'ExecutorConnectionDetail',
  'ExecutorConnectionId',
  'ExecutorConnectionList',
  'ExecutorEnrollmentId',
  'ExecutorEnrollmentMetadata',
  'ExecutorEnrollmentState',
  'ExecutorGroup',
  'ExecutorGroupCapacity',
  'ExecutorGroupDetail',
  'ExecutorGroupId',
  'ExecutorGroupList',
  'ExecutorGroupMember',
  'ExecutorGroupMemberIssue',
  'ExecutorGroupMemberStatus',
  'ExecutorGroupPlan',
  'ExecutorGroupRevision',
  'ExecutorGroupRevisionId',
  'ExecutorGroupStrategy',
  'ExecutorHost',
  'ExecutorHostDetails',
  'ExecutorHostId',
  'ExecutorHostList',
  'ExecutorHostModel',
  'ExecutorHostModelStatus',
  'ExecutorHostProviderDetail',
  'ExecutorHostSlotUse',
  'ExecutorHostSlots',
  'ExecutorHostState',
  'ExecutorHostTask',
  'ExecutorIdentityBasis',
  'ExecutorIntegrationAuthorisation',
  'ExecutorKind',
  'ExecutorModelAccess',
  'ExecutorOccupancy',
  'ExecutorPinnedModel',
  'ExecutorProbe',
  'ExecutorProbeId',
  'ExecutorProbeOutcome',
  'ExecutorProbeState',
  'ExecutorProvider',
  'ExecutorPullClient',
  'ExecutorRateCheck',
  'ExecutorRevision',
  'ExecutorRevisionId',
  'ExecutorRoute',
  'ExecutorRouteList',
  'ExecutorRoutingMappingEntry',
  'ExecutorRoutingMode',
  'ExecutorRoutingModeEventId',
  'ExecutorRoutingModeResult',
  'ExecutorRoutingModeState',
  'ExecutorRoutingPreview',
  'ExecutorRoutingPreviewIssue',
  'ExecutorRoutingPreviewItem',
  'ExecutorRoutingPreviewStatus',
  'ExecutorRoutingRule',
  'ExecutorRoutingRuleList',
  'ExecutorRoutingRuleRevisionId',
  'ExecutorRunnerTokenId',
  'ExecutorSecretId',
  'ExecutorSecretMetadata',
  'ExecutorSecretPurpose',
  'ExecutorSshKey',
  'ExecutorSshProfile',
  'ExecutorTaskAck',
  'ExecutorTaskId',
  'ExecutorTaskState',
  'ExecutorTaskUsage',
  'ExecutorTransport',
  'ExecutorWorkKind',
  'ExtendedExecutorTaskClaim',
  'ExtendedRunReview',
  'FailExecutorTaskRequest',
  'Finding',
  'FindingBlockLink',
  'FindingCategory',
  'FindingComparison',
  'FindingDetail',
  'FindingExecutionState',
  'FindingExecutionStatus',
  'FindingMatchProposal',
  'FindingObservation',
  'FindingObservationId',
  'FindingPage',
  'FindingRef',
  'FindingUid',
  'GenerateComparisonSummaryRequest',
  'GenerateComparisonSummaryResponse',
  'IdempotencyKey',
  'ImportProposalDecisionsRequest',
  'ImportRunDecisionsRequest',
  'InputManifestEntry',
  'IssueExecutorHostEnrollmentRequest',
  'IssueRunnerTokenRequest',
  'IssueTokenRequest',
  'IssueTokenResponse',
  'IssuedExecutorEnrollment',
  'IssuedRunnerToken',
  'JobId',
  'KnowledgeBaseEntry',
  'KnowledgeBaseEntryPage',
  'MarkReleaseNotesReadRequest',
  'ModelCallId',
  'ModelCatalogue',
  'ModelCatalogueEntry',
  'ModelEffort',
  'ModelProbeState',
  'ModelUnavailableReason',
  'NormBuildState',
  'NormCatalogueEntry',
  'NormCatalogueEntryPage',
  'NormCitation',
  'NormCitationState',
  'NormCurrentSnapshot',
  'NormDocument',
  'NormDocumentId',
  'NormFragment',
  'NormHighlight',
  'NormKindCount',
  'NormParagraph',
  'NormParagraphId',
  'NormParagraphKind',
  'NormParagraphPage',
  'NormReferenceAnchor',
  'NormReferenceCounts',
  'NormReferenceItem',
  'NormReferenceUnrecognised',
  'NormRetrievalSetId',
  'NormSearchHit',
  'NormSearchPage',
  'NormSnapshot',
  'NormSnapshotEvent',
  'NormSnapshotEventPage',
  'NormSnapshotPage',
  'NormSourceAttribution',
  'NormTextReliability',
  'NormsSnapshotId',
  'ObservationProvenance',
  'OptimisationPass',
  'OptimisationPassId',
  'OptimisationPassList',
  'OptimisationProposal',
  'OptimisationProposalId',
  'OptimisationProposalPage',
  'OptimisationProposalType',
  'PageInfo',
  'PageProfileStatus',
  'PageStamp',
  'PersonNames',
  'PortalBlock',
  'PortalBlockId',
  'PortalBlockPage',
  'PortalBlockType',
  'PortalCrop',
  'PortalGeometryState',
  'PortalRecognisedText',
  'PrepareComparisonClientReportRequest',
  'PresetId',
  'PresetRevisionId',
  'PriceListAmbiguousColumn',
  'PriceListColumn',
  'PriceListCurrencySource',
  'PriceListCurrencySourceCount',
  'PriceListField',
  'PriceListFormat',
  'PriceListId',
  'PriceListParseReport',
  'PriceListPosition',
  'PriceListPositionId',
  'PriceListPositionPage',
  'PriceListReasonCount',
  'PriceListRevision',
  'PriceListRevisionList',
  'PriceListRowNote',
  'PriceListRowReason',
  'ProductVersion',
  'Project',
  'ProjectDocumentCount',
  'ProjectPage',
  'ProjectSection',
  'ProjectStage',
  'ProjectUid',
  'PromptBundleId',
  'ProposalAnalogBasis',
  'ProposalDecision',
  'ProposalDecisionCarriedFrom',
  'ProposalDecisionCarryoverReport',
  'ProposalDecisionCounts',
  'ProposalDecisionId',
  'ProposalDecisionImportRefusal',
  'ProposalDecisionImportReport',
  'ProposalDecisionImportRow',
  'ProposalDecisionList',
  'ProposalDecisionRecord',
  'ProposalDecisionRecordPage',
  'ProposalDecisionResult',
  'ProposalDecisionState',
  'ProposalMatchBasis',
  'ProposalPosition',
  'ProposalVerdict',
  'ProviderAuthState',
  'ProviderMode',
  'ReauditRunRequest',
  'RedeemExecutorEnrollmentRequest',
  'RegistrationRequest',
  'RegistrationRequestId',
  'RegistrationRequestPage',
  'RegistrationStatus',
  'RegistrationStatusResponse',
  'RejectRegistrationRequest',
  'ReleaseEntry',
  'ReleaseList',
  'ReleaseNoteItem',
  'ReleaseNoteKind',
  'RenameDocumentRequest',
  'ReportRunnerHealthRequest',
  'ResetUserPasswordRequest',
  'ResumeComparisonAiJobRequest',
  'ResumeStageChainRunRequest',
  'ReviseExecutorConnectionRequest',
  'ReviseExecutorGroupRequest',
  'ReviseStageAssemblyRequest',
  'ReviseStageModelLayoutRequest',
  'Role',
  'RunActivity',
  'RunActivitySpend',
  'RunCostConsent',
  'RunCostEstimate',
  'RunCostEstimateRequest',
  'RunCostModelLine',
  'RunExecutor',
  'RunFindingBlockLinks',
  'RunId',
  'RunNormReferences',
  'RunPreset',
  'RunQueueReason',
  'RunStage',
  'RunStageCell',
  'RunStageChip',
  'RunStageFacts',
  'RunStagePlanSource',
  'RunStageState',
  'RunStages',
  'RunStartReadiness',
  'RunStartReadinessCell',
  'RunStartRoute',
  'RunState',
  'RunStateCount',
  'RunStatus',
  'RunStatusPage',
  'RunWaitCause',
  'RunWaitCell',
  'RunnerCatalogueEntry',
  'RunnerCliAuthState',
  'RunnerCliHealth',
  'RunnerCliName',
  'RunnerExecutionProfile',
  'RunnerFeature',
  'RunnerHealthAck',
  'RunnerImage',
  'RunnerImageBlobId',
  'RunnerKeyFileReport',
  'RunnerProviderModelState',
  'RunnerProviderReport',
  'RunnerTokenMetadata',
  'SaveAnalysisPresetRequest',
  'ScheduleAssignmentsRequest',
  'SectionDocumentCount',
  'SectionReview',
  'SectionReviewOption',
  'SectionSpecification',
  'SectionSpecificationExcludedVersion',
  'SectionSpecificationProject',
  'SectionSpecificationRow',
  'SectionSpecificationRowPage',
  'SectionSpecificationSource',
  'SectionSuggestion',
  'SectionVendorList',
  'SetCurrentNormSnapshotRequest',
  'SetDocumentArchivedRequest',
  'SetDocumentTagsRequest',
  'SetEngineerAbsencesRequest',
  'SetExecutionPausedRequest',
  'SetExecutorHostEnabledRequest',
  'SetExecutorHostSlotsRequest',
  'SetExecutorIntegrationAuthorisationRequest',
  'SetExecutorRouteRequest',
  'SetExecutorRoutingModeRequest',
  'SetExecutorRoutingRuleRequest',
  'SetExecutorSecretRequest',
  'SetFindingExecutionStatusRequest',
  'SetGlobalVendorListRequest',
  'SetJobPriorityRequest',
  'SetProjectVendorListRequest',
  'SetStageModelLayoutEnabledRequest',
  'SetStagePairCompletenessRequest',
  'SetWorkCalendarDaysRequest',
  'SetWorkSchedulePlansRequest',
  'SetWorkerIntakeRequest',
  'Severity',
  'Sha256',
  'SheetDiff',
  'SheetDiffPage',
  'SheetLinkId',
  'SheetPairing',
  'SheetPairingEvent',
  'SpecificationCurrencyTotal',
  'SpecificationExclusionCounts',
  'SpecificationExtractionSummary',
  'SpecificationMatchCounts',
  'SpecificationMatching',
  'SpecificationPriceListRef',
  'SpecificationPricePosition',
  'SpecificationPriceRow',
  'SpecificationPrices',
  'SpecificationRowPage',
  'SpecificationSkipCounts',
  'SpecificationSkippedLine',
  'SpecificationTable',
  'StageAiClassification',
  'StageAiClassificationId',
  'StageAiClassificationPage',
  'StageAiReview',
  'StageAiReviewId',
  'StageAiReviewPage',
  'StageAiSynthesis',
  'StageAiSynthesisId',
  'StageAiSynthesisPage',
  'StageAiUnitId',
  'StageAssembly',
  'StageAssemblyId',
  'StageAssemblyMember',
  'StageAtomicEvidenceId',
  'StageCardEvidence',
  'StageCardEvidenceId',
  'StageCardVerdict',
  'StageCardVerdictId',
  'StageCardVerdictInput',
  'StageCardVerdictPage',
  'StageCellKey',
  'StageCellRole',
  'StageChainBatch',
  'StageChainBatchId',
  'StageChainBatchItem',
  'StageChainBatchItemId',
  'StageChainBatchSelection',
  'StageChainRun',
  'StageChainRunId',
  'StageChainRunPage',
  'StageChainStep',
  'StageChainStepId',
  'StageChangeCard',
  'StageChangeCardId',
  'StageChangeCardPage',
  'StageChangeCategory',
  'StageChangeJournal',
  'StageClassificationCard',
  'StageComparisonCell',
  'StageGraphicEvidence',
  'StageGraphicEvidenceId',
  'StageGraphicEvidencePage',
  'StageId',
  'StageLayoutCell',
  'StageLayoutRevision',
  'StageLayoutRevisionId',
  'StageLayoutSwitchEvent',
  'StageLinkInput',
  'StageLinkItem',
  'StageLinkItemId',
  'StageLinkRepair',
  'StageLinkRepairId',
  'StageLinkRepairPage',
  'StageLinkRevision',
  'StageLinkRevisionId',
  'StageLinkRevisionPage',
  'StageModelKit',
  'StageModelLayout',
  'StagePair',
  'StagePairId',
  'StagePairPage',
  'StagePairSuggestion',
  'StagePairSuggestionPage',
  'StageProfileText',
  'StageProfileWord',
  'StageReviewDecision',
  'StageRowKey',
  'StageSheetPassport',
  'StageSheetPassportPage',
  'StageSheetSuggestion',
  'StageSheetSuggestionPage',
  'StageState',
  'StageStatus',
  'StageSynthesisResult',
  'StageSystem',
  'StageTextDifference',
  'StageTextDifferenceId',
  'StageTextDifferencePage',
  'StageTextExclusion',
  'StageTextExclusionId',
  'StageTextExclusionPage',
  'StageTextFragment',
  'StageTextFragmentId',
  'StageTextFragmentPage',
  'StageTextHint',
  'StageTextHintId',
  'StageTextHintPage',
  'StageUpload',
  'StageUploadCandidate',
  'StageUploadCandidateId',
  'StageUploadFile',
  'StageUploadFileDeclaration',
  'StageUploadFileId',
  'StageUploadFileKind',
  'StageUploadId',
  'StageUploadPage',
  'StageUploadPartReceipt',
  'StartComparisonAiJobRequest',
  'StartComparisonAiSheetChangesRequest',
  'StartComparisonSeriesRequest',
  'StartRunFromStageRequest',
  'StartRunRequest',
  'StartStageChainBatchRequest',
  'StartStageChainRunRequest',
  'SubmitExecutorTaskAnswerRequest',
  'SubmitRegistrationRequest',
  'SummaryStatement',
  'TransitionAssignmentRequest',
  'UndoComparisonMatrixEditRequest',
  'UndoStageLinkRepairRequest',
  'UpdateMyProfileRequest',
  'UpdateUserRequest',
  'UploadDocumentRequest',
  'UploadDocumentVersionRequest',
  'UploadPriceListRequest',
  'UserUid',
  'VendorListEntry',
  'VendorListId',
  'VendorListMode',
  'VendorListRevision',
  'VendorListScope',
  'VendorListSource',
  'Verdict',
  'VerdictCount',
  'VersionBlockIndex',
  'VersionClassification',
  'VersionClassificationRevision',
  'VersionComparison',
  'VersionPageProfile',
  'VersionPageProfilePage',
  'VersionSheetLabel',
  'VersionSheetLabelList',
  'VersionUid',
  'VersionUploadKind',
  'WithdrawSheetPairingRequest',
  'WorkCalendarDayChange',
  'WorkScheduleDay',
  'WorkScheduleDoneDocument',
  'WorkScheduleEngineer',
  'WorkScheduleMonth',
  'WorkSchedulePlan',
  'WorkScheduleReserve',
  'WorkScheduleReserveEngineer',
  'WorkScheduleReserveItem',
  'WorkScheduleSettings',
  'WorkerId',
  'WorkerState',
] as const;

/**
 * `UI-B-27` (contract 1.35.0): one proposal whose decision in force is an acceptance, with where it belongs
 * (project, document set, version, the version's section) and the acceptance itself.
 *
 * A row is named by its proposal's own identity (``optimisation_proposal_id``); ``page_number`` and ``row_position``
 * locate it in the drawing and are never an identity. The prices and the saving are the proposal's own exact decimal
 * text; ``saving`` is ``null`` -- never ``0`` -- when the row's quantity is not a plain number. `carried_from` (`D-335`, contract 1.39.0) is `null` for an acceptance an expert made directly and names the source decision -- with its pass, version and the version's display ordinal -- when the acceptance was carried over from an earlier version's pass (`UI-B-14`). `saving_percent` (`D-346`, contract 1.43.0) is the proposals read's percent of the current unit price, present where `saving` is `null` too.
 */
export type AcceptedOptimisationProposal = {
  actor_label: string;
  carried_from: ProposalDecisionCarriedFrom | null;
  comment: string | null;
  currency: string;
  current_unit_price: string;
  decided_at: string;
  document_name: string;
  document_uid: DocumentUid;
  matched_name: string;
  optimisation_pass_id: OptimisationPassId;
  optimisation_proposal_id: OptimisationProposalId;
  page_number: number;
  project_name: string;
  project_uid: ProjectUid;
  proposal_decision_id: ProposalDecisionId;
  proposal_type: OptimisationProposalType;
  proposed_name: string;
  proposed_unit_price: string;
  proposed_vendor: string;
  quantity: string | null;
  row_position: string | null;
  row_text: string;
  saving: string | null;
  /** `D-346` (contract 1.43.0): how much cheaper the proposed unit price is than the current one, in percent of the current unit price -- the very figure `listOptimisationProposals` states for the proposal (`OptimisationProposal.saving_percent`): computed exactly and rounded half up to two decimals, written without a trailing zero (`25`, `33.33`). It is present where `saving` is `null` because the quantity is not a plain number; absent only when the current unit price is zero. Never computed by a client. */
  saving_percent?: string;
  section?: ProjectSection;
  unit: string;
  version_uid: VersionUid;
};

/** `UI-B-27`: one page of the accepted proposals, newest acceptance first, and how many match the filters. */
export type AcceptedOptimisationProposalPage = {
  items: Array<AcceptedOptimisationProposal>;
  page: PageInfo;
  total: number;
};

/** One account, as the account itself reads it through `getMe` and an administrator reads it through the account operations. No credential material. */
export type Account = {
  /** Null for an active account. An archived account cannot sign in and none of its credentials is accepted; an administrator may restore it. */
  archived_at: string | null;
  /** The name to show for this account, resolved by the server and never empty: the name form `Last F. M.` when the account has a last and a first name, else the display name an operator chose, else the login. A complete profile always has the name form (R-55). */
  display_label: string;
  /** Null until somebody gives the names. */
  first_name: string | null;
  /** True while the account must change its password: it is still on the password the deployment seeded it with, or an administrator reset it. The same fact `IssueTokenResponse.is_default_credential` reports at sign-in. */
  is_default_credential: boolean;
  /** Null until somebody gives the names. */
  last_name: string | null;
  /** The instant of the account's latest successful sign-in, read from the access journal; null when none is recorded (the account never signed in, or signed in before the journal began). Present on every Account answer, including `getMe`. */
  last_sign_in_at: string | null;
  /** The sign-in identifier: the normalised e-mail address (trimmed, lower-case, ASCII, an internationalised domain in its `xn--` form, at most 254 characters) once the profile is complete, or the legacy login an account created before the identity upgrade keeps until it completes its profile. Not an identity of this surface. */
  login: string;
  /** Optional; null when the person has none. */
  middle_name: string | null;
  /** False for an account that has not given its names and e-mail yet. Such an account reaches only `getMe`, `updateMyProfile` and `changePassword`; every other operation answers `permission_denied` with `required_capability: profile_completed`. */
  profile_complete: boolean;
  /** The role set, sorted. Empty is a valid set: such an account reads product data and changes nothing. */
  roles: Array<Role>;
  user_uid: UserUid;
};

export type AccountPage = {
  items: Array<Account>;
  page: PageInfo;
};

export type AgentPackageVersion = string;

/** The contract pattern for `AgentPackageVersion`. Anchored; use with `new RegExp()`. */
export const AGENT_PACKAGE_VERSION_PATTERN = "^[0-9]{1,4}\\.[0-9]{1,4}\\.[0-9]{1,4}$";

/** The current revision of one preset. `preset_id` is the preset for its whole life; `revision_id` and `revision_no` name this revision. The name is a label, never an identity. */
export type AnalysisPreset = {
  created_at: string;
  executor_connection_id: ExecutorConnectionId;
  name: string;
  preset_id: PresetId;
  revised_at: string;
  revised_by: UserUid;
  revision_id: PresetRevisionId;
  revision_no: number;
  state: AnalysisPresetState;
};

/** Every preset by its current revision: active ones first by name, then archived ones. */
export type AnalysisPresetList = {
  items: Array<AnalysisPreset>;
};

/** `active` can be chosen at run start; `archived` is retired for good. */
export const ANALYSIS_PRESET_STATE_VALUES = [
  'active',
  'archived',
] as const;

/** AnalysisPresetState - the closed value set above. */
export type AnalysisPresetState = (typeof ANALYSIS_PRESET_STATE_VALUES)[number];

export type AnalysisProfileId = string;

/** The contract pattern for `AnalysisProfileId`. Anchored; use with `new RegExp()`. */
export const ANALYSIS_PROFILE_ID_PATTERN = "^ap_[0-9A-HJKMNP-TV-Z]{26}$";

/** All fifteen sections, in the project-structure order, each with its profile or ``null``. */
export type AnalysisProfileList = {
  items: Array<AnalysisProfileListItem>;
};

/** One section and its registered profile, or ``null`` when none is registered. */
export type AnalysisProfileListItem = {
  profile: AnalysisProfileSummary | null;
  section_code: ProjectSection;
  section_name: string;
};

/** The legacy repository, commit and files a package's prompt was ported from. */
export type AnalysisProfileSource = {
  commit: string;
  files: Array<AnalysisProfileSourceFile>;
  repository: string;
};

/** One legacy file a package's prompt was ported from, with its SHA-256. */
export type AnalysisProfileSourceFile = {
  path: string;
  sha256: Sha256;
};

/**
 * `W59-ANALYSIS-SETTINGS-01`. Where a registered text profile stands.
 *
 * ``draft``: a package ported from the legacy prompts, or authored in this repository, whose
 * open questions no lane has answered in writing. ``reviewed``: a package whose open questions a
 * lane answered in writing; no human review (`R-146ag`). Every status is executable; the status is
 * recorded, never hidden. АР has no status because it has no text profile
 * (`PROD-11-AR-V1-V2-REMOVAL-01`): its row carries ``profile: null``.
 */
export const ANALYSIS_PROFILE_STATUS_VALUES = [
  'draft',
  'reviewed',
] as const;

/** AnalysisProfileStatus - the closed value set above. */
export type AnalysisProfileStatus = (typeof ANALYSIS_PROFILE_STATUS_VALUES)[number];

/** One registered text profile: its identities, version, status and content hashes. */
export type AnalysisProfileSummary = {
  analysis_profile_id: AnalysisProfileId;
  content_sha256: Sha256;
  profile_version: string;
  prompt_bundle_id: PromptBundleId;
  prompt_bundle_sha256: Sha256;
  source: AnalysisProfileSource | null;
  status: AnalysisProfileStatus;
};

/**
 * A new revision of the order. ``base_revision_no`` is the latest revision the caller saw
 * (``0`` for none); a mismatch is ``409 conflict`` and the caller rebases.
 */
export type AppendComparisonVersionOrderRequest = {
  base_revision_no: number;
  version_uids: Array<VersionUid>;
};

export type AppendDecisionRequest = {
  /** Required for `comment`; optional on any other event type. */
  comment?: string | null;
  event_type: DecisionEventType;
  /** The observation the expert actually reviewed. A verdict is recorded against the evidence in front of the reviewer, not against whatever the newest run later produced. */
  finding_observation_id: FindingObservationId;
  severity?: Severity;
};

export type AppendDecisionResponse = {
  current_verdict: Verdict;
  event: DecisionEvent;
};

/**
 * «Применить сопоставления (N)»: the batch an expert drafted, with the revision the draft
 * started from. The edits are applied together or not at all.
 */
export type ApplyComparisonMatrixEditsRequest = {
  base_revision: ComparisonMatrixRevision;
  edits: Array<ComparisonMatrixEditInput>;
};

export type ApplyStageCardVerdictsRequest = {
  updates: Array<StageCardVerdictInput>;
};

export type ApplyStageSheetMapRequest = {
  base_revision_id?: StageLinkRevisionId;
  items: Array<StageLinkInput>;
};

export type ApproveRegistrationRequest = {
  /** The roles the new account receives: at least one. */
  roles: Array<Role>;
};

/**
 * `COMPARE-PERSISTED-SUMMARY-01`. One expert confirmation of one proposed sheet pair.
 *
 * The path names the source (older) version; the comparison is recomputed with these values
 * when the confirmation arrives and must still propose exactly these pages under exactly this
 * ``suggestion_sha256``.
 */
export type ApproveSheetPairingRequest = {
  mode: "version" | "stage";
  source_page_number: number;
  source_run_id?: RunId;
  suggestion_sha256: Sha256;
  target_page_number: number;
  target_run_id?: RunId;
  target_version_uid: VersionUid;
};

/**
 * One span of an approved pair's raw line diff; 0-based line indices, end exclusive. A
 * changed span carries ``hunk_id`` (``<sheet_link_id>:<n>``, ``n`` counting the sheet's
 * non-equal spans from 0); an ``equal`` span carries its ranges and neither lines nor an id.
 */
export type ApprovedDiffHunk = {
  hunk_id: string | null;
  source_end: number;
  source_lines: Array<string>;
  source_start: number;
  tag: "equal" | "insert" | "delete" | "replace";
  target_end: number;
  target_lines: Array<string>;
  target_start: number;
};

/** The deterministic differences of one approved pair, recomputed on every read. */
export type ApprovedSheetDiff = {
  added_line_count: number;
  evidence_sha256: Sha256;
  hunks: Array<ApprovedDiffHunk>;
  removed_line_count: number;
  source_line_count: number;
  target_line_count: number;
};

/** One active expert approval of a source page against a target page. */
export type ApprovedSheetPair = {
  approved_at: string;
  approved_by_label: string;
  diff: ApprovedSheetDiff | null;
  link_revision: number;
  sheet_link_id: SheetLinkId;
  source_page_number: number;
  state: "verified" | "text_changed";
  suggestion_sha256: Sha256;
  target_page_number: number;
};

/**
 * `COMPARE-PERSISTED-SUMMARY-01`. The active approvals of the compared pair and their
 * deterministic evidence. ``evidence_state``: ``none`` (no active approval), ``sealed`` (the
 * differences were recomputed and their seal equals the stored one), ``text_changed``,
 * ``seal_changed`` or ``too_large`` (no difference is served, none is truncated).
 */
export type ApprovedSheetPairs = {
  evidence_state: "none" | "sealed" | "text_changed" | "seal_changed" | "too_large";
  items: Array<ApprovedSheetPair>;
  link_revision: number | null;
  raw_evidence_seal_sha256: Sha256 | null;
  summary?: ComparisonSummary | null;
};

/** `W61-DISPATCHER-01`. One assignment as it now stands. */
export type Assignment = {
  assignee_label: string;
  assignee_user_uid: UserUid;
  assignment_uid: AssignmentUid;
  created_at: string;
  created_by_label: string;
  created_by_user_uid: UserUid;
  document_title: string | null;
  document_uid: DocumentUid | null;
  note: string | null;
  project_name: string;
  project_uid: ProjectUid;
  status: AssignmentStatus;
  status_reason: string | null;
  updated_at: string;
};

/** `W61-DISPATCHER-01`. One assignment and its whole history, oldest event first. */
export type AssignmentDetail = {
  assignment: Assignment;
  history: Array<AssignmentEvent>;
};

/** `W61-DISPATCHER-01`. One recorded event; never changed. */
export type AssignmentEvent = {
  actor_label: string;
  actor_user_uid: UserUid;
  event_id: string;
  kind: AssignmentEventKind;
  new_assignee_label: string | null;
  new_assignee_user_uid: UserUid | null;
  occurred_at: string;
  reason: string | null;
};

/** `W61-DISPATCHER-01`. One event of an assignment's append-only history. */
export const ASSIGNMENT_EVENT_KIND_VALUES = [
  'assigned',
  'started',
  'completed',
  'returned',
  'reassigned',
  'cancelled',
] as const;

/** AssignmentEventKind - the closed value set above. */
export type AssignmentEventKind = (typeof ASSIGNMENT_EVENT_KIND_VALUES)[number];

export type AssignmentMove = {
  assignee_user_uid?: UserUid;
  assignment_uid: AssignmentUid;
  planned_on?: string;
};

/** Contract 1.36.0: one page of assignments, the number that match every filter of the request (`total`), and every status with its count over the scope filters only (`overview`). */
export type AssignmentPage = {
  items: Array<Assignment>;
  overview: Array<AssignmentStatusCount>;
  page: PageInfo;
  total: number;
};

/**
 * `W61-DISPATCHER-01`. An assignment's status, derived from its latest event.
 *
 * ``assigned`` (after ``assigned`` or ``reassigned``), ``in_progress`` (``started``),
 * ``done`` (``completed``), ``returned`` and ``cancelled``. ``done`` and ``cancelled`` are
 * terminal.
 */
export const ASSIGNMENT_STATUS_VALUES = [
  'assigned',
  'in_progress',
  'done',
  'returned',
  'cancelled',
] as const;

/** AssignmentStatus - the closed value set above. */
export type AssignmentStatus = (typeof ASSIGNMENT_STATUS_VALUES)[number];

/** Contract 1.36.0: how many assignments stand in one status. */
export type AssignmentStatusCount = {
  count: number;
  status: AssignmentStatus;
};

/** `W61-DISPATCHER-01`. The events a transition may append: every kind but ``assigned``. */
export const ASSIGNMENT_TRANSITION_KIND_VALUES = [
  'started',
  'completed',
  'returned',
  'reassigned',
  'cancelled',
] as const;

/** AssignmentTransitionKind - the closed value set above. */
export type AssignmentTransitionKind = (typeof ASSIGNMENT_TRANSITION_KIND_VALUES)[number];

export type AssignmentUid = string;

/** The contract pattern for `AssignmentUid`. Anchored; use with `new RegExp()`. */
export const ASSIGNMENT_UID_PATTERN = "^asg_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * Contract 1.36.0 (`UI-A-94`): one line of the access journal, as it was recorded; never changed.
 *
 * Never a password, a token, an address or a login as typed: the account is named by identity and by the label it has
 * now, and an event about an account that has since been deleted keeps its identity with a null label.
 */
export type AuthEvent = {
  actor_label: string | null;
  actor_user_uid: UserUid | null;
  default_credential: boolean | null;
  event_id: string;
  event_type: AuthEventType;
  failures: number | null;
  occurred_at: string;
  role: Role | null;
  source: "api" | "host_cli";
  subject_label: string | null;
  subject_user_uid: UserUid;
};

/** Contract 1.36.0 (`UI-A-94`): one page of the access journal, newest first. */
export type AuthEventPage = {
  items: Array<AuthEvent>;
  page: PageInfo;
};

/**
 * Contract 1.36.0 (`UI-A-94`): the kinds of line the access journal holds, the ``access.*`` events of its writer.
 *
 * ``sign_in_succeeded``; ``sign_in_blocked`` (a refused attempt that started a cooling-off period, at most one per
 * account per period); ``password_changed`` (the account's own); ``password_reset`` (an administrator's temporary
 * password); ``role_granted`` and ``role_revoked``; ``sessions_ended`` (an administrator ended every session of the
 * account).
 */
export const AUTH_EVENT_TYPE_VALUES = [
  'sign_in_succeeded',
  'sign_in_blocked',
  'password_changed',
  'password_reset',
  'role_granted',
  'role_revoked',
  'sessions_ended',
] as const;

/** AuthEventType - the closed value set above. */
export type AuthEventType = (typeof AUTH_EVENT_TYPE_VALUES)[number];

/** One derived block, one extracted text line. `block_id` is an anchor inside this artifact -- it matches `Evidence.block_id`'s pattern -- and is never a contract identifier. */
export type BlockGeometry = {
  /** Points, top-left origin, y increasing downward -- see `bbox_unit` and `bbox_origin` beside it. */
  bbox: {
    x0: number;
    x1: number;
    y0: number;
    y1: number;
  };
  bbox_origin: "top_left";
  bbox_unit: "pt";
  block_id: string;
  /** Position of this block within its page, starting at 0. */
  block_ordinal: number;
  char_end: number;
  /** Document-global offset into the version's prepared text layer, counted in Unicode code points -- the same sequence `Evidence.char_start` indexes. */
  char_start: number;
  page_number: number;
};

/**
 * `W59-DECISION-CARRYOVER-01`. One expert confirmation of one proposed pair.
 *
 * The path names the source (older) version; the comparison is recomputed with these
 * values when the confirmation arrives. ``source_decision_id`` is the decision the expert
 * was shown: if the source's current verdict has moved on, nothing is carried.
 */
export type CarryOverDecisionRequest = {
  mode: "version" | "stage";
  source_decision_id: DecisionId;
  source_finding_uid: FindingUid;
  source_run_id?: RunId;
  target_finding_uid: FindingUid;
  target_run_id?: RunId;
  target_version_uid: VersionUid;
};

/**
 * `W59-DECISION-CARRYOVER-01`. The carried event on the target finding and where it
 * came from. ``replayed`` is true when the target already carried exactly this event (an
 * exact repeat): nothing was appended and the first confirmation stands.
 */
export type CarryOverDecisionResponse = {
  current_verdict: Verdict;
  event: DecisionEvent;
  mode: "version" | "stage";
  replayed: boolean;
  source_decision_id: DecisionId;
  source_finding_uid: FindingUid;
  source_version_ordinal: number;
  source_version_uid: VersionUid;
  target_version_uid: VersionUid;
};

/** `UI-B-14` (contract 1.37.0): the pass whose decisions in force are carried into the pass of the path. */
export type CarryOverProposalDecisionsRequest = {
  source_optimisation_pass_id: OptimisationPassId;
};

/**
 * `W59-DECISION-CARRYOVER-01`. An ``unchanged`` proposal whose source finding carries an
 * expert decision and whose target finding has no decision event yet. Listing it carries
 * nothing: only ``carryOverDecision``, confirmed by an expert, does.
 */
export type CarryoverCandidate = {
  proposal_sha256: Sha256;
  source_decision: CarryoverSourceDecision;
  source_finding_uid: FindingUid;
  target_finding_uid: FindingUid;
};

/**
 * `W59-DECISION-CARRYOVER-01`. The source finding's current verdict-bearing event, as
 * the confirming expert is shown it before «Перенести решение».
 */
export type CarryoverSourceDecision = {
  author_label: string;
  comment: string | null;
  decision_id: DecisionId;
  recorded_at: string;
  severity: Severity | null;
  verdict: "accepted" | "rejected";
};

export type ChangePasswordRequest = {
  /** The password the account holds now, proved before anything is changed. It appears in no response body, no error detail and no diagnostic record. A value that is not this account's is `authentication_required` -- the same refusal a missing credential gets, because 'this deployment does not accept this' is one fact. */
  current_password: string;
  /** The password the account will hold. The bounds are mechanical. The deployment enforces a password policy on this operation — a refusal is `validation_failed` and names the rule in `message` — and that policy is not declared here, because it is the deployment's and may differ between them. No history and no expiry are enforced. A value equal to `current_password` is `validation_failed`, because a change that changes nothing would report a password as changed when it was not. */
  new_password: string;
};

/**
 * The long poll holds the request open for up to ``wait_seconds`` (0 to 25, default 25).
 *
 * `EXEC2-SEAL-1` (ADR-0026 decision 3): the optional `runner_instance_id` names the agent process making the claim. A task already held by a token is redelivered only to the instance that claimed it; a claim without the field behaves as before. One token is served by one agent process.
 */
export type ClaimExecutorTaskRequest = {
  max_images?: number;
  runner_instance_id?: string;
  wait_seconds?: number;
};

/**
 * A task, now claimed by the calling token. ``system`` and ``user_text`` are untrusted,
 * document-derived text. ``model`` is the pinned gateway model the answer must declare.
 */
export type ClaimedExecutorTask = {
  access?: ExecutorModelAccess;
  cell_key?: StageCellKey;
  claim_expires_at: string;
  deadline_at: string;
  effort?: ModelEffort;
  images?: Array<RunnerImage>;
  model: string;
  model_id?: string;
  output_schema: Record<string, never>;
  provider?: ExecutorProvider;
  system: string;
  task_id: ExecutorTaskId;
  timeout_seconds?: number;
  user_text: string;
};

/** `W59-SECTION-SEAL-01`. An expert's explicit stage and section for one version. */
export type ClassifyDocumentVersionRequest = {
  project_stage: ProjectStage;
  section_code: ProjectSection;
};

/** One side of a comparison, as far as it was established before any refusal. */
export type ComparedVersion = {
  page_count: number;
  project_stage: ProjectStage | null;
  run_id: RunId | null;
  section_code: ProjectSection | null;
  sha256: Sha256;
  text_layer_sha256: Sha256 | null;
  version_ordinal: number;
  version_uid: VersionUid;
};

/**
 * The hard ceilings of ``Q-CMP-7``: ``job`` USD 10 for one job, ``day`` USD 50 per day for the
 * installation. A connection that is not metered has none.
 */
export const COMPARISON_AI_CEILING_VALUES = [
  'job',
  'day',
] as const;

/** ComparisonAiCeiling - the closed value set above. */
export type ComparisonAiCeiling = (typeof COMPARISON_AI_CEILING_VALUES)[number];

/** ComparisonAiCertainty. */
export const COMPARISON_AI_CERTAINTY_VALUES = [
  'confirmed',
  'unclear',
] as const;

/** ComparisonAiCertainty - the closed value set above. */
export type ComparisonAiCertainty = (typeof COMPARISON_AI_CERTAINTY_VALUES)[number];

/**
 * One change of the description: the construction object and its place, «Было» (only from side A)
 * and «стало» (only from side B), the tier of each value and, for an item the model could not settle,
 * the limitation («Неясно»). ``box`` and ``side`` serve «Показать на чертеже».
 */
export type ComparisonAiChange = {
  box?: ComparisonBox;
  certainty: ComparisonAiCertainty;
  change_id: string;
  kind?: string;
  limitation?: string;
  now?: string;
  now_tier?: ComparisonAiTier;
  object_name: string;
  place?: string;
  side?: ComparisonAiSide;
  was?: string;
  was_tier?: ComparisonAiTier;
};

/** ComparisonAiConfidence. */
export const COMPARISON_AI_CONFIDENCE_VALUES = [
  'high',
  'medium',
  'low',
] as const;

/** ComparisonAiConfidence - the closed value set above. */
export type ComparisonAiConfidence = (typeof COMPARISON_AI_CONFIDENCE_VALUES)[number];

/**
 * The user's consent to one estimate: the digest of the estimate that was shown and the explicit
 * confirmation of the line «Подтверждаю передачу материалов исполнителю». ``confirmed`` false is
 * ``422 validation_failed`` (``comparison_consent_required``). `EXEC2-SEAL-2`: when the estimate's route is a group's, the digest also binds the group revision, the rule revision and the planned model, and dispatch re-checks them against the consent before any call; a mismatch sets `wait_reason` `needs_reconsent` and calls nothing.
 */
export type ComparisonAiConsent = {
  confirmed: boolean;
  estimate_digest: Sha256;
};

/**
 * How many engine candidates the description covers: ``candidates`` offered, ``in_changes`` named in
 * a change, ``not_reviewed`` left unreviewed.
 */
export type ComparisonAiCoverage = {
  candidates: number;
  in_changes: number;
  not_reviewed: number;
};

/** An item under «Заявлено проектировщиком в разрешении (N)», from the permit's stamp. */
export type ComparisonAiDeclaredItem = {
  reference?: string;
  text: string;
};

/**
 * The «Диагностика» panel: kept out of the main report. ``issues`` are the codes of the checks that
 * failed.
 */
export type ComparisonAiDiagnostics = {
  candidates: number;
  excluded_by_program: number;
  issues: Array<string>;
};

/**
 * What an AI start would do and cost, computed without a model call. ``estimate_digest`` binds the
 * route, the pinned model, the ceilings and every figure below: the start carries it, and a start whose
 * digest is not the one now computed is ``409 conflict`` (``comparison_estimate_stale``). ``units`` is
 * what the job works on (questions, sheets, transitions, versions or report parts); ``reused`` of the
 * units already have a stored answer under the same content key and are never sent again. For a
 * connection that is not metered ``estimate_micros`` is ``0`` and no ceiling applies. ``blocked_by`` is
 * present when the start would be refused for a ceiling (``comparison_ceiling_job`` or
 * ``comparison_ceiling_day``).
 */
export type ComparisonAiEstimate = {
  blocked_by?: ComparisonAiCeiling;
  calls: number;
  ceiling_micros: number;
  day_remaining_micros?: number;
  estimate_digest: Sha256;
  estimate_micros: number;
  image_bytes: number;
  images: number;
  input_tokens: number;
  method: ComparisonAiMethod;
  output_tokens: number;
  pairs?: number;
  prompt_chars: number;
  questions?: number;
  reused?: number;
  route: ComparisonAiRoute;
  sheets?: number;
  transitions?: number;
  units: number;
  versions?: number;
};

/** Why an engine pointer is «Не включено в сводку». */
export const COMPARISON_AI_EXCLUDE_REASON_VALUES = [
  'service',
  'formatting',
  'label_move',
  'revision_mark',
  'duplicate',
  'not_construction',
] as const;

/** ComparisonAiExcludeReason - the closed value set above. */
export type ComparisonAiExcludeReason = (typeof COMPARISON_AI_EXCLUDE_REASON_VALUES)[number];

/** An engine pointer the program ruled out of the description, with the reason. */
export type ComparisonAiExcluded = {
  reason: ComparisonAiExcludeReason;
  text?: string;
};

/**
 * One AI job: the consented estimate (frozen), the state, the units and the spend. A job belongs to
 * one document set; ``series_id``, ``transition_id`` and ``sheet_pair_id`` name its scope when it has
 * one. ``queue_position`` is present while the job waits in the installation's AI queue.
 * Every AI text a job produces is model output not confirmed by an engineer.
 * `EXEC2-SEAL-2` (ADR-0026 decisions 12 to 15): `binding_state` (absent is read as `frozen_at_start`) says whether the job's connection was frozen at consent, is still to be chosen (`pending`) or was bound at the job's first dispatched call (`bound`, with `binding`); its later calls stay on that connection. `planned` repeats what the consented route froze for a job admitted by a rule or a group. `wait_reason` and `waiting_since` are present while a `pending` job waits for an executor.
 */
export type ComparisonAiJob = {
  binding?: ExecutorBinding;
  binding_state?: ExecutorBindingState;
  consented_at: string;
  consented_by: UserUid;
  counts: ComparisonAiJobCounts;
  created_at: string;
  document_uid: DocumentUid;
  estimate: ComparisonAiEstimate;
  failure_reason?: string;
  finished_at?: string;
  job_id: ComparisonAiJobId;
  method: ComparisonAiMethod;
  pause_reason?: ComparisonAiPauseReason;
  planned?: ExecutorGroupPlan;
  project_uid: ProjectUid;
  queue_position?: number;
  series_id?: ComparisonSeriesId;
  sheet_pair_id?: ComparisonSheetPairId;
  spend: ComparisonAiSpend;
  state: ComparisonAiJobState;
  transition_id?: ComparisonTransitionId;
  updated_at: string;
  wait_reason?: RunQueueReason;
  waiting_since?: string;
};

/**
 * The units of a job: ``total``, those ``done``, those ``failed`` and those whose call outcome is
 * ``unknown``.
 */
export type ComparisonAiJobCounts = {
  done: number;
  failed: number;
  total: number;
  unknown: number;
};

export type ComparisonAiJobId = string;

/** The contract pattern for `ComparisonAiJobId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_AI_JOB_ID_PATTERN = "^cai_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * ``queued``: waiting, in the installation's AI queue or for a free executor. ``paused``: stopped,
 * see ``pause_reason``. A ``completed`` job whose ``counts.failed`` is not zero is the original's
 * «частично».
 */
export const COMPARISON_AI_JOB_STATE_VALUES = [
  'queued',
  'running',
  'paused',
  'completed',
  'failed',
  'cancelled',
] as const;

/** ComparisonAiJobState - the closed value set above. */
export type ComparisonAiJobState = (typeof COMPARISON_AI_JOB_STATE_VALUES)[number];

/**
 * An accepted AI link (ADR-0025 decisions 3 and 14): a model's answer that the validator
 * accepted, shown labelled «ИИ» and never an expert act. It binds the algorithmic build
 * (``matrix_id``) and the cell state it answered. Written in wave C2; this wave reads.
 */
export type ComparisonAiLink = {
  ai_link_id: ComparisonAiLinkId;
  answered_state: ComparisonAiLinkAnsweredState;
  created_at: string;
  document_uid: DocumentUid;
  matrix_id: ComparisonMatrixId;
  other_page: ComparisonPageRef;
  page: ComparisonPageRef;
  status: ComparisonAiLinkStatus;
};

/** ComparisonAiLinkAnsweredState. */
export const COMPARISON_AI_LINK_ANSWERED_STATE_VALUES = [
  'unmatched',
  'doubtful',
] as const;

/** ComparisonAiLinkAnsweredState - the closed value set above. */
export type ComparisonAiLinkAnsweredState = (typeof COMPARISON_AI_LINK_ANSWERED_STATE_VALUES)[number];

export type ComparisonAiLinkId = string;

/** The contract pattern for `ComparisonAiLinkId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_AI_LINK_ID_PATTERN = "^cak_[0-9A-HJKMNP-TV-Z]{26}$";

/** Newest first. */
export type ComparisonAiLinkList = {
  items: Array<ComparisonAiLink>;
  page: PageInfo;
};

/**
 * ``applied``: the cell it answered is still in the state it answered. ``superseded``: the
 * cell has since been matched otherwise or edited, so the link no longer shapes the matrix.
 */
export const COMPARISON_AI_LINK_STATUS_VALUES = [
  'applied',
  'superseded',
] as const;

/** ComparisonAiLinkStatus - the closed value set above. */
export type ComparisonAiLinkStatus = (typeof COMPARISON_AI_LINK_STATUS_VALUES)[number];

/**
 * The four kinds of model work of the version comparison. Each is also an executor work kind,
 * ``comparison_<method>`` (``ExecutorWorkKind``), routed in «Назначения»: ``pair_check`` the AI check
 * of the doubtful pairs of the matrix, ``sheet_changes`` the AI description of changes, ``spec`` the
 * comparison of whole specifications, ``report`` the report from the summary.
 */
export const COMPARISON_AI_METHOD_VALUES = [
  'pair_check',
  'sheet_changes',
  'spec',
  'report',
  'stage_review',
] as const;

/** ComparisonAiMethod - the closed value set above. */
export type ComparisonAiMethod = (typeof COMPARISON_AI_METHOD_VALUES)[number];

/**
 * The AI check of the doubtful pairs of a document set: the latest job and its figures. Both are
 * absent until a check was started. Accepted answers are written as accepted AI links by the
 * lane's rule and never by a client call (``AGENTS.md`` section 4).
 */
export type ComparisonAiPairCheck = {
  counts?: ComparisonAiPairCounts;
  document_uid: DocumentUid;
  job?: ComparisonAiJob;
};

/**
 * «вопросов · пар · подсказок · против»: ``questions`` asked, ``answered`` of them, ``pairs``
 * accepted as AI links, ``hints`` shown, ``against`` the model said no candidate is the same sheet,
 * ``failed`` without a usable answer, ``reused`` answered from the store without a call.
 */
export type ComparisonAiPairCounts = {
  against: number;
  answered: number;
  failed: number;
  hints: number;
  pairs: number;
  questions: number;
  reused: number;
};

/**
 * What the lane's rule made of the answers. ``link_accepted``: written as an accepted AI link
 * (high confidence, the candidate number and the page agree, the sheet is not inside a multi-sheet
 * specification, B is not linked to another A, no other A chose the same B, the reverse question
 * returned A with high confidence). The ``hint_*`` values are shown as «ИИ ?» or «вероятно стр. N»
 * and change nothing: ``hint_table`` a multi-sheet table, ``hint_confidence`` not high,
 * ``hint_taken`` B is already paired by the algorithm, ``hint_shared`` two sheets chose one,
 * ``hint_reverse`` the reverse question did not confirm. ``none``: no candidate is the same sheet.
 * ``answer_mismatch``: the number and the page disagree and the answer is dropped. ``failed``: no usable
 * answer. ``medium_confirm``, ``medium_weak``, ``medium_other`` and ``medium_none``: the answers to a
 * ``medium`` question (the pair is confirmed, confirmed without confidence, another sheet is
 * named, none is the same sheet). A manual edit always wins over any of them.
 */
export const COMPARISON_AI_PAIR_DECISION_VALUES = [
  'link_accepted',
  'hint_table',
  'hint_confidence',
  'hint_taken',
  'hint_shared',
  'hint_reverse',
  'none',
  'answer_mismatch',
  'failed',
  'medium_confirm',
  'medium_weak',
  'medium_other',
  'medium_none',
] as const;

/** ComparisonAiPairDecision - the closed value set above. */
export type ComparisonAiPairDecision = (typeof COMPARISON_AI_PAIR_DECISION_VALUES)[number];

/**
 * The answer to one question, for the matrix cell it concerns: sheet ``page`` of the older version
 * against the cell of ``version_uid``. ``hint_page`` is «вероятно стр. N». ``link_id`` names the
 * accepted AI link a ``link_accepted`` decision wrote. ``stale`` is true when the question was asked of a
 * matrix build that is no longer the latest. ``reason`` is the model's own sentence, not confirmed by an
 * engineer.
 */
export type ComparisonAiPairHint = {
  candidates: Array<ComparisonPageRef>;
  confidence?: ComparisonAiConfidence;
  created_at: string;
  decision: ComparisonAiPairDecision;
  hint_page?: ComparisonPageRef;
  job_id: ComparisonAiJobId;
  kind: ComparisonAiPairQuestionKind;
  link_id?: ComparisonAiLinkId;
  matrix_id: ComparisonMatrixId;
  page: ComparisonPageRef;
  question_id: ComparisonAiPairQuestionId;
  reason?: string;
  stale: boolean;
  version_uid: VersionUid;
};

/** Newest first. */
export type ComparisonAiPairHintPage = {
  items: Array<ComparisonAiPairHint>;
  page: PageInfo;
};

export type ComparisonAiPairQuestionId = string;

/** The contract pattern for `ComparisonAiPairQuestionId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_AI_PAIR_QUESTION_ID_PATTERN = "^cpq_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * ``no_pair``: sheet A has no pair and the cell of B has candidates («⁇»). ``medium_pair``: the algorithm's
 * pair has medium confidence. Sheets of a multi-sheet table group are not asked.
 */
export const COMPARISON_AI_PAIR_QUESTION_KIND_VALUES = [
  'no_pair',
  'medium_pair',
] as const;

/** ComparisonAiPairQuestionKind - the closed value set above. */
export type ComparisonAiPairQuestionKind = (typeof COMPARISON_AI_PAIR_QUESTION_KIND_VALUES)[number];

/**
 * Why a job is ``paused``: ``user`` asked; ``quota`` the subscription's quota is spent; ``auth`` the
 * executor is not authorised; ``overrun`` the actual spend passed 1.2 times the consented estimate;
 * ``route_changed`` the route or the revision of the connection changed since the consent;
 * ``module_off`` the versions module was turned off. After ``overrun`` and ``route_changed`` a
 * resume carries a new consent.
 */
export const COMPARISON_AI_PAUSE_REASON_VALUES = [
  'user',
  'quota',
  'auth',
  'overrun',
  'route_changed',
  'module_off',
] as const;

/** ComparisonAiPauseReason - the closed value set above. */
export type ComparisonAiPauseReason = (typeof COMPARISON_AI_PAUSE_REASON_VALUES)[number];

/**
 * The AI jobs that are queued, running or paused anywhere in the installation, running first, then
 * in the order they will start. A read for any role; it starts nothing.
 */
export type ComparisonAiQueue = {
  items: Array<ComparisonAiQueueItem>;
  paused: number;
  queued: number;
  running: number;
};

/** One job in the installation's AI queue «Очередь «ИИ-описание изменений»». */
export type ComparisonAiQueueItem = {
  binding_state?: ExecutorBindingState;
  counts: ComparisonAiJobCounts;
  created_at: string;
  document_uid: DocumentUid;
  job_id: ComparisonAiJobId;
  method: ComparisonAiMethod;
  project_uid: ProjectUid;
  queue_position?: number;
  series_id?: ComparisonSeriesId;
  state: ComparisonAiJobState;
  wait_reason?: RunQueueReason;
};

/**
 * What serves the calls of an estimate or a job: the connection and its revision, the model the
 * revision pins (a reply from another model is refused, ``R-133``), how it is billed and whether the
 * process is in recorded mode, in which case every answer is a recorded test answer.
 *
 * `HOSTS-CMP-01` (ADR-0028 decision 19): a route chosen by the stage layout also carries the `cell` of its kind of work -- the
 * model and effort the job froze. The estimate digest binds it, so the consent names what will run.
 */
export type ComparisonAiRoute = {
  billing: ExecutorBilling;
  cell?: StageComparisonCell;
  connection_id?: ExecutorConnectionId;
  executor_group_id?: ExecutorGroupId;
  executor_group_revision_id?: ExecutorGroupRevisionId;
  pinned_model: string;
  provider_mode: ProviderMode;
  revision_id?: ExecutorRevisionId;
  routing_rule_revision_id?: ExecutorRoutingRuleRevisionId;
};

/**
 * The AI description of changes of a series: the latest job (absent until one was started) and the
 * progress of each transition.
 */
export type ComparisonAiSheetChanges = {
  job?: ComparisonAiJob;
  series_id: ComparisonSeriesId;
  transitions: Array<ComparisonAiTransitionProgress>;
};

/**
 * The eleven states of «Изменения в листе»: ``not_processed`` «Не обработано» (not the same as no
 * changes), ``queued`` «В очереди», ``running`` «В обработке», ``done`` «Готово», ``needs_clarification``
 * «Требуется уточнение», ``partial`` «Частично», ``no_construction_changes`` «Строительных изменений не
 * выявлено», ``stale`` «Описание устарело», ``failed`` «Ошибка», ``cancelled`` «Отменено»,
 * ``engine_same`` «По данным сравнения изменений нет».
 */
export const COMPARISON_AI_SHEET_STATE_VALUES = [
  'not_processed',
  'queued',
  'running',
  'done',
  'needs_clarification',
  'partial',
  'no_construction_changes',
  'stale',
  'failed',
  'cancelled',
  'engine_same',
] as const;

/** ComparisonAiSheetState - the closed value set above. */
export type ComparisonAiSheetState = (typeof COMPARISON_AI_SHEET_STATE_VALUES)[number];

/** ComparisonAiSide. */
export const COMPARISON_AI_SIDE_VALUES = [
  'a',
  'b',
] as const;

/** ComparisonAiSide - the closed value set above. */
export type ComparisonAiSide = (typeof COMPARISON_AI_SIDE_VALUES)[number];

/**
 * The spend of a job so far, from the comparison journal. ``reserved_micros`` is what the calls in
 * flight may still cost; ``unknown_calls`` are calls whose outcome is not known and that are never sent
 * again until a person says «Повторить».
 */
export type ComparisonAiSpend = {
  calls: number;
  input_tokens: number;
  output_tokens: number;
  reserved_micros: number;
  spent_micros: number;
  unknown_calls: number;
};

/**
 * How a value of a change was checked by the program: ``from_text`` found in the text layer of its own
 * side, ``from_image`` read from the drawing the model cited («с изображения»), ``unverified`` found in
 * neither («не подтверждено»).
 */
export const COMPARISON_AI_TIER_VALUES = [
  'from_text',
  'from_image',
  'unverified',
] as const;

/** ComparisonAiTier - the closed value set above. */
export type ComparisonAiTier = (typeof COMPARISON_AI_TIER_VALUES)[number];

/**
 * One row of «ИИ-описание изменений»: «Листов» (``sheets`` to describe, ``done`` of them),
 * «Изм.» (``changed``: sheets with changes), «Вопр.» (``questions``), «Ошибок» (``errors``),
 * «Проверить» (``to_review``), «Обращ.» (``calls``), tokens and ``seconds``.
 */
export type ComparisonAiTransitionProgress = {
  calls: number;
  changed: number;
  done: number;
  errors: number;
  input_tokens: number;
  output_tokens: number;
  questions: number;
  seconds: number;
  sheets: number;
  to_review: number;
  transition_id: ComparisonTransitionId;
};

/** An item under «Требует уточнения (N)». */
export type ComparisonAiUnresolved = {
  box?: ComparisonBox;
  question: string;
  side?: ComparisonAiSide;
};

/** A rectangle on the canvas of the older page, in points. */
export type ComparisonBox = {
  height: number;
  width: number;
  x: number;
  y: number;
};

/** The canvas of the older page, in points; the boxes of the differences are on it. */
export type ComparisonCanvas = {
  height_pt: number;
  width_pt: number;
};

/**
 * How a matched cell was linked: ``high`` and ``medium`` by the algorithm, ``group`` as a
 * member of a table-sheet group, ``manual`` by an expert, ``ai`` by an accepted AI link.
 */
export const COMPARISON_CELL_CONFIDENCE_VALUES = [
  'high',
  'medium',
  'group',
  'manual',
  'ai',
] as const;

/** ComparisonCellConfidence - the closed value set above. */
export type ComparisonCellConfidence = (typeof COMPARISON_CELL_CONFIDENCE_VALUES)[number];

/**
 * ``split``: the sheet is split across versions. ``duplicate``: the same content stands on
 * several pages. ``scan``: an image-only page whose text is not compared. ``bridge``: the cell
 * was linked across a version that lacks the sheet.
 */
export const COMPARISON_CELL_FLAG_VALUES = [
  'split',
  'duplicate',
  'scan',
  'bridge',
] as const;

/** ComparisonCellFlag - the closed value set above. */
export type ComparisonCellFlag = (typeof COMPARISON_CELL_FLAG_VALUES)[number];

/**
 * ``matched``: the cell holds a page of this version. ``unmatched``: no page was matched,
 * candidates may be offered. ``absent``: the version has no such sheet (determined, or marked
 * by an expert).
 */
export const COMPARISON_CELL_STATE_VALUES = [
  'matched',
  'unmatched',
  'absent',
] as const;

/** ComparisonCellState - the closed value set above. */
export type ComparisonCellState = (typeof COMPARISON_CELL_STATE_VALUES)[number];

/**
 * One channel of the comparison: ``checked`` with the number of differences it found,
 * ``unchecked`` with the reason it could not look, or ``not_applicable``.
 */
export type ComparisonChannel = {
  diffs?: number;
  reason?: string;
  state: ComparisonChannelState;
};

/** ComparisonChannelState. */
export const COMPARISON_CHANNEL_STATE_VALUES = [
  'checked',
  'unchecked',
  'not_applicable',
] as const;

/** ComparisonChannelState - the closed value set above. */
export type ComparisonChannelState = (typeof COMPARISON_CHANNEL_STATE_VALUES)[number];

/**
 * The eight channels: ``geometry``, ``color``, ``text``, ``text_coverage``, ``zones``,
 * ``annotations``, ``warnings`` and ``spec_positions``. A sheet is «Совпадает» only when every
 * applicable channel is ``checked``.
 */
export type ComparisonChannels = {
  annotations?: ComparisonChannel;
  color?: ComparisonChannel;
  geometry?: ComparisonChannel;
  spec_positions?: ComparisonChannel;
  text?: ComparisonChannel;
  text_coverage?: ComparisonChannel;
  warnings?: ComparisonChannel;
  zones?: ComparisonChannel;
};

/**
 * One entry of «Отличия: N». ``region_class`` is a lower-case word the engine defines
 * (``text``, ``text_moved``, ``graphic_added``, ``graphic_removed``, ``graphic_changed``,
 * ``color_change``, ``light_fill``, ``line_style``, ``block_moved``, ``shifted``).
 */
export type ComparisonDifference = {
  after_text?: string;
  before_text?: string;
  box: ComparisonBox;
  layer: ComparisonLayer;
  region_class: string;
};

/** For a migrated edit, the ``0035`` records it came from. Absent for an expert's edit. */
export type ComparisonEditProvenance = {
  comparison_id: ComparisonId;
  link_revision: number;
  sheet_link_id: string;
};

/**
 * «Как сравнивалось»: the registration transform of the newer page onto the older one (an
 * affine matrix ``[a, b, c, d, e, f]``), the raster resolution, the tolerance and the counts of
 * what was set aside.
 */
export type ComparisonHowCompared = {
  algo_version: string;
  aligned_blocks?: number;
  dpi: number;
  noise_count?: number;
  separated_objects?: number;
  tolerance_pt: number;
  transform?: Array<number>;
  within_tolerance_count?: number;
};

export type ComparisonId = string;

/** The contract pattern for `ComparisonId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_ID_PATTERN = "^cmp_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * One selected step of one document set. The queue runs one step at a time across sets, in the order
 * of ``position`` (``1`` first): the profiles, the matrix, the AI check of pairs, the series, the AI
 * description, the summary and report. ``job_id`` and ``series_id`` name what the entry started.
 */
export type ComparisonLaunchEntry = {
  created_at: string;
  document_uid: DocumentUid;
  entry_id: ComparisonLaunchEntryId;
  job_id?: ComparisonAiJobId;
  position: number;
  reason?: string;
  restart: boolean;
  series_id?: ComparisonSeriesId;
  state: ComparisonLaunchEntryState;
  step: ComparisonStepId;
  updated_at: string;
};

export type ComparisonLaunchEntryId = string;

/** The contract pattern for `ComparisonLaunchEntryId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_LAUNCH_ENTRY_ID_PATTERN = "^cle_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * ``waiting``, ``running``, ``done``, ``skipped`` (the step needed nothing or its set was removed),
 * ``failed``, and ``needs_consent``: an AI step whose estimate now exists and has not been consented
 * to. A queue asks for AI consent per set only when its estimate exists.
 */
export const COMPARISON_LAUNCH_ENTRY_STATE_VALUES = [
  'waiting',
  'running',
  'needs_consent',
  'done',
  'skipped',
  'failed',
] as const;

/** ComparisonLaunchEntryState - the closed value set above. */
export type ComparisonLaunchEntryState = (typeof COMPARISON_LAUNCH_ENTRY_STATE_VALUES)[number];

/**
 * A set and a step to queue. ``consent`` is given for an AI step (``ai_pairs``, ``ai_changes``,
 * ``report``) whose estimate exists, one consent per set; for a step with no estimate yet the entry waits
 * and becomes ``needs_consent``. A consent on a step that is not an AI step is
 * ``422 validation_failed``.
 */
export type ComparisonLaunchItem = {
  consent?: ComparisonAiConsent;
  document_uid: DocumentUid;
  step: ComparisonStepId;
};

/** «Очередь запуска» of a project. A project has one queue; reading it starts nothing. */
export type ComparisonLaunchQueue = {
  counts: ComparisonLaunchQueueCounts;
  entries: Array<ComparisonLaunchEntry>;
  project_uid: ProjectUid;
  state: ComparisonLaunchQueueState;
  updated_at?: string;
};

/**
 * «готово N из M · пропущено K · ошибок E»: ``done`` of ``total``, ``skipped``, ``failed``, and those
 * ``running``, ``waiting`` and ``needs_consent``.
 */
export type ComparisonLaunchQueueCounts = {
  done: number;
  failed: number;
  needs_consent: number;
  running: number;
  skipped: number;
  total: number;
  waiting: number;
};

/** «идёт», «на паузе», «ошибка — процесс остановлен», «выполнена», «пусто». */
export const COMPARISON_LAUNCH_QUEUE_STATE_VALUES = [
  'running',
  'paused',
  'failed',
  'done',
  'idle',
] as const;

/** ComparisonLaunchQueueState - the closed value set above. */
export type ComparisonLaunchQueueState = (typeof COMPARISON_LAUNCH_QUEUE_STATE_VALUES)[number];

/**
 * The layers of the overlay: ``main`` «Основное», ``light_elements`` «Светлые элементы»,
 * ``color_change`` «места, где изменился цвет», ``line_style`` «Оформление линий», ``moved``
 * «Перемещено (сдвиг — не изменение)», ``within_tolerance`` «В пределах допуска», ``noise``
 * «Шум» and ``service_zones`` «Служебные зоны».
 */
export const COMPARISON_LAYER_VALUES = [
  'main',
  'light_elements',
  'color_change',
  'line_style',
  'moved',
  'within_tolerance',
  'noise',
  'service_zones',
] as const;

/** ComparisonLayer - the closed value set above. */
export type ComparisonLayer = (typeof COMPARISON_LAYER_VALUES)[number];

/**
 * A kind of comparison work that the stage layout chooses a model for (`HOSTS-CMP-01`): `comparison_pair_check` (the AI check of
 * doubtful sheet pairs), `comparison_sheet_changes` (the AI description of a sheet's changes), `comparison_spec` (the comparison of whole
 * specifications) and `comparison_report` (the report of a comparison). `comparison_stage_review` has no handler and is not offered.
 */
export const COMPARISON_LAYOUT_KIND_VALUES = [
  'comparison_pair_check',
  'comparison_sheet_changes',
  'comparison_spec',
  'comparison_report',
] as const;

/** ComparisonLayoutKind - the closed value set above. */
export type ComparisonLayoutKind = (typeof COMPARISON_LAYOUT_KIND_VALUES)[number];

/**
 * The effective matrix of a document set: the algorithm, then accepted AI links (labelled,
 * never an expert act), then manual edits (manual wins) (ADR-0025 decision 3). Rows are sheet
 * identities, ``columns`` are the versions in the current comparison order. ``revision``,
 * ``columns``, ``rows`` and ``counts`` are absent while no build exists. ``order_id`` is the
 * version-order revision the build used (absent for the document's own order).
 * ``orphaned_edit_ids`` lists the edits that no longer apply after a reorder: they are never
 * applied silently. ``unassigned_pages`` are the pages no row holds.
 */
export type ComparisonMatrix = {
  built_at?: string;
  columns?: Array<ComparisonMatrixColumn>;
  counts?: ComparisonMatrixCounts;
  document_uid: DocumentUid;
  failure_reason?: string;
  order_id?: ComparisonVersionOrderId;
  orphaned_edit_ids?: Array<ComparisonMatrixEditId>;
  progress: ComparisonMatrixProgress;
  project_uid: ProjectUid;
  revision?: ComparisonMatrixRevision;
  rows?: Array<ComparisonMatrixRow>;
  stale_reasons?: Array<ComparisonMatrixStaleReason>;
  state: ComparisonMatrixState;
  unassigned_pages?: Array<ComparisonPageRef>;
};

/** A page offered for an unmatched cell, with the algorithm's score. */
export type ComparisonMatrixCandidate = {
  page: ComparisonPageRef;
  score: number;
};

/**
 * One cell of a row, for the version column named by ``version_uid``. ``page``,
 * ``confidence`` and ``flags`` belong to a matched cell; ``candidates`` and ``reason`` to an
 * unmatched one. ``edit_id`` names the manual edit that made a ``manual`` cell, ``ai_link_id``
 * the accepted AI link that made an ``ai`` cell.
 */
export type ComparisonMatrixCell = {
  ai_link_id?: ComparisonAiLinkId;
  candidates?: Array<ComparisonMatrixCandidate>;
  confidence?: ComparisonCellConfidence;
  edit_id?: ComparisonMatrixEditId;
  flags?: Array<ComparisonCellFlag>;
  page?: ComparisonPageRef;
  reason?: string;
  state: ComparisonCellState;
  version_uid: VersionUid;
};

/**
 * One version, in the position of the current comparison order. ``label`` is the version's label of
 * the upload proposal (``label_source`` ``proposal``) or, for a version that carried none, its stored
 * file name (``file_name``); both are absent for a version that came from a portal bundle, and the
 * client then writes «Версия №N» for the N-th column (`CMP-SEAL-C2`, from `CMP-MATRIX-01`).
 */
export type ComparisonMatrixColumn = {
  label?: string;
  label_source?: ComparisonMatrixLabelSource;
  page_count: number;
  version_uid: VersionUid;
};

export type ComparisonMatrixCounts = {
  ai: number;
  duplicates: number;
  groups: number;
  manual: number;
  rows: number;
  unmatched: number;
};

/**
 * One event of the append-only edit history of a document set, numbered ``edit_no`` from 1
 * without a gap. ``order_id`` is the version-order revision the edit was made against (absent
 * for the document's own order).
 */
export type ComparisonMatrixEdit = {
  absent_version_uid?: VersionUid;
  created_at: string;
  created_by: UserUid;
  document_uid: DocumentUid;
  edit_id: ComparisonMatrixEditId;
  edit_no: number;
  kind: ComparisonMatrixEditKind;
  order_id?: ComparisonVersionOrderId;
  other_page?: ComparisonPageRef;
  page?: ComparisonPageRef;
  provenance?: ComparisonEditProvenance;
  source: ComparisonMatrixEditSource;
  status: ComparisonMatrixEditStatus;
  undoes_edit_id?: ComparisonMatrixEditId;
};

export type ComparisonMatrixEditId = string;

/** The contract pattern for `ComparisonMatrixEditId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_MATRIX_EDIT_ID_PATTERN = "^cme_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * One edit of a batch. ``link`` needs ``page`` and ``other_page`` (two versions of the
 * document set), ``unlink`` needs ``page``, ``mark_absent`` needs ``page`` and
 * ``absent_version_uid``; any other member is refused as ``validation_failed``.
 */
export type ComparisonMatrixEditInput = {
  absent_version_uid?: VersionUid;
  kind: ComparisonMatrixEditInputKind;
  other_page?: ComparisonPageRef;
  page: ComparisonPageRef;
};

/** ComparisonMatrixEditInputKind. */
export const COMPARISON_MATRIX_EDIT_INPUT_KIND_VALUES = [
  'link',
  'unlink',
  'mark_absent',
] as const;

/** ComparisonMatrixEditInputKind - the closed value set above. */
export type ComparisonMatrixEditInputKind = (typeof COMPARISON_MATRIX_EDIT_INPUT_KIND_VALUES)[number];

/**
 * ``link``: ``page`` and ``other_page`` are one sheet. ``unlink``: ``page`` leaves its row
 * for a row of its own. ``mark_absent``: the row of ``page`` has no sheet in
 * ``absent_version_uid``. ``undo``: the event reverses the edit named by ``undoes_edit_id``
 * (read side only; an undo is asked for with ``undoComparisonMatrixEdit``).
 */
export const COMPARISON_MATRIX_EDIT_KIND_VALUES = [
  'link',
  'unlink',
  'mark_absent',
  'undo',
] as const;

/** ComparisonMatrixEditKind - the closed value set above. */
export type ComparisonMatrixEditKind = (typeof COMPARISON_MATRIX_EDIT_KIND_VALUES)[number];

/** Newest event first. */
export type ComparisonMatrixEditList = {
  items: Array<ComparisonMatrixEdit>;
  page: PageInfo;
};

/**
 * ``expert``: made through ``applyComparisonMatrixEdits``. ``migrated_sheet_link``: the
 * approved pairing of ``approveSheetPairing`` (migration ``0039``, ADR-0025 decision 13); the
 * ``0035`` ids are in ``provenance``.
 */
export const COMPARISON_MATRIX_EDIT_SOURCE_VALUES = [
  'expert',
  'migrated_sheet_link',
] as const;

/** ComparisonMatrixEditSource - the closed value set above. */
export type ComparisonMatrixEditSource = (typeof COMPARISON_MATRIX_EDIT_SOURCE_VALUES)[number];

/**
 * ``applied``: the edit shapes the effective matrix. ``undone``: a later undo reversed it.
 * ``orphaned``: its cells no longer exist in the current order.
 */
export const COMPARISON_MATRIX_EDIT_STATUS_VALUES = [
  'applied',
  'undone',
  'orphaned',
] as const;

/** ComparisonMatrixEditStatus - the closed value set above. */
export type ComparisonMatrixEditStatus = (typeof COMPARISON_MATRIX_EDIT_STATUS_VALUES)[number];

export type ComparisonMatrixId = string;

/** The contract pattern for `ComparisonMatrixId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_MATRIX_ID_PATTERN = "^cmx_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * Where a column label comes from: ``proposal`` the version's label the user confirmed with its
 * upload set (the suggested label of the proposal when the user left it), ``file_name`` the stored file
 * name of the version, which is a hint and never an identity.
 */
export const COMPARISON_MATRIX_LABEL_SOURCE_VALUES = [
  'proposal',
  'file_name',
] as const;

/** ComparisonMatrixLabelSource - the closed value set above. */
export type ComparisonMatrixLabelSource = (typeof COMPARISON_MATRIX_LABEL_SOURCE_VALUES)[number];

/**
 * What ``prepareComparisonMatrix`` queued: the matrix state after the call and the
 * progress of the profiles. Profiles that are missing or failed are queued again, then the
 * matrix is built.
 */
export type ComparisonMatrixPreparation = {
  document_uid: DocumentUid;
  progress: ComparisonMatrixProgress;
  state: ComparisonMatrixState;
};

/** Profiles of the document set's pages: ``ready`` of ``total``, ``failed`` among the rest. */
export type ComparisonMatrixProgress = {
  failed: number;
  ready: number;
  total: number;
};

/**
 * The revision of an effective matrix: the algorithmic build it rests on and the number of
 * manual edit events of the document set up to it (``0`` for none). An edit batch carries the
 * revision the caller saw; a mismatch is ``409 conflict`` and the caller rebases its draft
 * (ADR-0025 decision 14).
 */
export type ComparisonMatrixRevision = {
  edit_no: number;
  matrix_id: ComparisonMatrixId;
};

/**
 * One sheet identity across the versions. ``row_id`` is the identity of the stored profile
 * of the row's first page and is valid within one revision. ``cells`` holds one cell per column,
 * in the order of the columns.
 */
export type ComparisonMatrixRow = {
  cells: Array<ComparisonMatrixCell>;
  row_id: ComparisonPageProfileId;
  sheet_number?: string;
  title?: string;
};

/**
 * Why the latest build no longer matches: ``order_changed`` the version order moved,
 * ``profiles_changed`` a page profile was recomputed, ``algorithm_changed`` the matching algorithm or its
 * rule set (``ALGO_VERSION``, ``RULES_VERSION``) is not the one the build was made with
 * (`CMP-SEAL-C2`, from `CMP-MATRIX-01`).
 */
export const COMPARISON_MATRIX_STALE_REASON_VALUES = [
  'order_changed',
  'profiles_changed',
  'algorithm_changed',
] as const;

/** ComparisonMatrixStaleReason - the closed value set above. */
export type ComparisonMatrixStaleReason = (typeof COMPARISON_MATRIX_STALE_REASON_VALUES)[number];

/**
 * ``absent``: nothing has been built or queued. ``building``: profiles or the matrix are
 * being computed. ``ready``: the build matches the current order and profiles. ``stale``: it
 * does not, see ``stale_reasons``. ``failed``: the last build failed.
 */
export const COMPARISON_MATRIX_STATE_VALUES = [
  'absent',
  'building',
  'ready',
  'stale',
  'failed',
] as const;

/** ComparisonMatrixState - the closed value set above. */
export type ComparisonMatrixState = (typeof COMPARISON_MATRIX_STATE_VALUES)[number];

/**
 * ``none`` serves neither comparison module (the default), ``versions`` «Сравнение
 * версий», ``versions,stages`` both. A module that is off has no menu entry and its
 * operations answer ``dependency_unavailable``.
 */
export const COMPARISON_MODULES_VALUES = [
  'none',
  'versions',
  'versions,stages',
] as const;

/** ComparisonModules - the closed value set above. */
export type ComparisonModules = (typeof COMPARISON_MODULES_VALUES)[number];

/** ComparisonNoteChange. */
export const COMPARISON_NOTE_CHANGE_VALUES = [
  'added',
  'removed',
  'changed',
] as const;

/** ComparisonNoteChange - the closed value set above. */
export type ComparisonNoteChange = (typeof COMPARISON_NOTE_CHANGE_VALUES)[number];

export type ComparisonNumberChange = {
  after: string;
  before: string;
};

/**
 * The overview of a project for «Проекты и этапы»: one entry per document set, the totals
 * and counters, and the batches still being uploaded. Reading it starts nothing.
 */
export type ComparisonOverview = {
  counters: ComparisonOverviewCounters;
  generated_at: string;
  pending_uploads: Array<ComparisonOverviewUpload>;
  project_uid: ProjectUid;
  sets: Array<ComparisonOverviewSet>;
  totals: ComparisonOverviewTotals;
};

/** «Все / Ждут действия / Идут / Ошибки / Готовы». */
export type ComparisonOverviewCounters = {
  all: number;
  failed: number;
  ready: number;
  running: number;
  waiting: number;
};

/**
 * One row of «Проекты и этапы»: a document set («комплект (шифр)»). ``designation`` is the
 * «шифр», metadata and never an identity. ``steps`` lists the seven steps in order;
 * ``next_step`` is the step the chip proposes and is absent when nothing is left to do.
 */
export type ComparisonOverviewSet = {
  designation?: string;
  document_uid: DocumentUid;
  next_step?: ComparisonStepId;
  project_stage?: ProjectStage;
  section_code?: ProjectSection;
  steps: Array<ComparisonOverviewStep>;
  title?: string;
  updated_at?: string;
  version_count: number;
};

export type ComparisonOverviewStep = {
  counts?: ComparisonStepCounts;
  state: ComparisonStepState;
  step: ComparisonStepId;
};

/** «N версий · M переходов». */
export type ComparisonOverviewTotals = {
  transitions: number;
  versions: number;
};

/** A batch that is not finished: «В загрузке, ещё не в списке проектов». */
export type ComparisonOverviewUpload = {
  declared_files: number;
  sets_done: number;
  sets_total: number;
  state: ComparisonUploadState;
  upload_id: ComparisonUploadId;
};

export type ComparisonPageProfileId = string;

/** The contract pattern for `ComparisonPageProfileId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_PAGE_PROFILE_ID_PATTERN = "^cpr_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * A page of a version: the version's identity and the page's coordinate inside that
 * immutable version (never a display number). ``page_profile_id`` is the identity of the page's
 * stored profile once there is one; the cells of a built matrix always carry it.
 */
export type ComparisonPageRef = {
  page_number: number;
  page_profile_id?: ComparisonPageProfileId;
  version_uid: VersionUid;
};

/**
 * One side of a sheet pair: the page, its sheet number and title from the stamp, and
 * whether it is an image-only page. ``raster`` is the size of the page's raster pyramid.
 */
export type ComparisonPairPage = {
  page: ComparisonPageRef;
  raster?: ComparisonRasterSize;
  scan?: boolean;
  sheet_number?: string;
  title?: string;
};

/**
 * ``overlay``: the older and the newer page on one canvas with the difference layers.
 * ``a`` and ``b``: the older or the newer page alone.
 */
export const COMPARISON_PAIR_TILE_MODE_VALUES = [
  'overlay',
  'a',
  'b',
] as const;

/** ComparisonPairTileMode - the closed value set above. */
export type ComparisonPairTileMode = (typeof COMPARISON_PAIR_TILE_MODE_VALUES)[number];

/** ComparisonPartRole. */
export const COMPARISON_PART_ROLE_VALUES = [
  'whole',
  'part',
] as const;

/** ComparisonPartRole - the closed value set above. */
export type ComparisonPartRole = (typeof COMPARISON_PART_ROLE_VALUES)[number];

/**
 * The coverage of a sheet that is split across versions (``◫``, ``⇉``): whether this pair
 * holds the whole sheet or one part, the other parts, and how much of the older sheet the parts
 * cover together.
 */
export type ComparisonPartsCoverage = {
  covered_percent: number;
  parts: Array<ComparisonPageRef>;
  role: ComparisonPartRole;
};

/** «Заявлено проектировщиком в разрешении»: the declared items and how each fared. */
export type ComparisonPermit = {
  items?: Array<ComparisonPermitItem>;
  state: ComparisonPermitState;
};

export type ComparisonPermitItem = {
  state: ComparisonPermitState;
  text: string;
};

/**
 * The reconciliation of the changes a permit stamp declares with the changes found:
 * ``declared_and_found``, ``declared_no_diff``, ``diff_not_declared`` and ``needs_review``.
 */
export const COMPARISON_PERMIT_STATE_VALUES = [
  'declared_and_found',
  'declared_no_diff',
  'diff_not_declared',
  'needs_review',
] as const;

/** ComparisonPermitState - the closed value set above. */
export type ComparisonPermitState = (typeof COMPARISON_PERMIT_STATE_VALUES)[number];

export type ComparisonProposalFile = {
  file_id: ComparisonUploadFileId;
  position: number;
  version_label?: string;
};

/**
 * One proposed document set. ``designation`` is the «шифр» read from the stamp: metadata
 * an expert confirms, never an identity. ``existing_document_uid`` names the document of the
 * project the designation matches, when there is one.
 */
export type ComparisonProposalSet = {
  designation?: string;
  document_uid?: DocumentUid;
  existing_document_uid?: DocumentUid;
  failure_reason?: string;
  files: Array<ComparisonProposalFile>;
  project_stage?: ProjectStage;
  section_code?: ProjectSection;
  set_id: ComparisonUploadSetId;
  state: ComparisonUploadSetState;
  warnings?: Array<ComparisonProposalWarning>;
};

/** What the stamp reader noticed about a proposed set; the user has the final word. */
export const COMPARISON_PROPOSAL_WARNING_VALUES = [
  'designations_differ',
  'order_disagrees_with_file_numbers',
  'duplicate_revision_number',
  'no_stamp_found',
  'scan_without_text',
] as const;

/** ComparisonProposalWarning - the closed value set above. */
export type ComparisonProposalWarning = (typeof COMPARISON_PROPOSAL_WARNING_VALUES)[number];

/** Comparison work items by state. */
export type ComparisonQueueCounts = {
  cancelled: number;
  failed: number;
  leased: number;
  paused: number;
  queued: number;
  retry_wait: number;
  running: number;
  spend_unknown: number;
  succeeded: number;
};

export type ComparisonQueueKind = {
  counts: ComparisonQueueCounts;
  kind: string;
  module: ComparisonQueueModule;
};

/** ComparisonQueueModule. */
export const COMPARISON_QUEUE_MODULE_VALUES = [
  'versions',
  'stages',
] as const;

/** ComparisonQueueModule - the closed value set above. */
export type ComparisonQueueModule = (typeof COMPARISON_QUEUE_MODULE_VALUES)[number];

/**
 * The read-only «Сравнение» block of «Очередь»: the module set, whether execution is
 * paused for the whole installation, the items by state and by kind, and the age of the oldest
 * queued one. Comparison work yields to section runs and honours the pause.
 */
export type ComparisonQueueSummary = {
  counts: ComparisonQueueCounts;
  kinds: Array<ComparisonQueueKind>;
  modules: ComparisonModules;
  oldest_queued_at?: string;
  paused: boolean;
};

/**
 * The size in pixels of the full-resolution raster of a page, the base of its tile pyramid
 * (level 0): the viewer lays tiles on it and need not derive it (`CMP-SEAL-C2`, from
 * `CMP-VIEWER-01`).
 */
export type ComparisonRasterSize = {
  height_px: number;
  width_px: number;
};

/** Why two versions are not compared; ``side`` when the reason is one side's. */
export type ComparisonRefusal = {
  reason: "same_version" | "version_not_found" | "different_set" | "foreign_project" | "version_not_published" | "version_order_invalid" | "stage_unclassified" | "section_unconfirmed" | "project_stage_mismatch" | "confirmed_section_mismatch" | "stage_pair_invalid" | "analysis_missing" | "run_not_of_version" | "run_not_published" | "text_unavailable" | "text_too_large";
  side: "source" | "target" | null;
};

/**
 * A report built from the MD summary of a series. A ``draft`` carries the ``estimate`` the start
 * consents to; once started, ``job`` holds the consented estimate and the spend. ``prepared_from_id``
 * names the analytic report a client report was prepared from. ``reuse`` reuses the finished parts of
 * earlier reports of the same summary. Every page of the PDF carries the unconfirmed-by-an-engineer
 * label and the recall line («изменённых листов N, описано K, отброшено проверкой D»); the label is the
 * client's text, the figures are the report's.
 */
export type ComparisonReport = {
  artifacts: Array<ComparisonReportArtifact>;
  created_at: string;
  document_uid: DocumentUid;
  estimate?: ComparisonAiEstimate;
  failure_reason?: string;
  finished_at?: string;
  job?: ComparisonAiJob;
  kind: ComparisonReportKind;
  parts: Array<ComparisonReportPart>;
  prepared_from_id?: ComparisonReportId;
  project_uid: ProjectUid;
  report_id: ComparisonReportId;
  reuse: boolean;
  series_id: ComparisonSeriesId;
  source: ComparisonReportSource;
  source_name?: string;
  stage?: ComparisonReportStage;
  state: ComparisonReportState;
  updated_at: string;
};

/**
 * A stored file of a report, downloaded by ``streamComparisonReportPdf`` or
 * ``streamComparisonReportSourceMd``.
 */
export type ComparisonReportArtifact = {
  created_at: string;
  kind: ComparisonReportArtifactKind;
  sha256: Sha256;
  size_bytes: number;
};

/** ComparisonReportArtifactKind. */
export const COMPARISON_REPORT_ARTIFACT_KIND_VALUES = [
  'report_pdf',
  'source_md',
] as const;

/** ComparisonReportArtifactKind - the closed value set above. */
export type ComparisonReportArtifactKind = (typeof COMPARISON_REPORT_ARTIFACT_KIND_VALUES)[number];

/**
 * The program's check of the analyst's claims against the source: found, confirmed, contradicted,
 * unconfirmed.
 */
export type ComparisonReportFacts = {
  confirmed: number;
  contradicted: number;
  found: number;
  unconfirmed: number;
};

export type ComparisonReportId = string;

/** The contract pattern for `ComparisonReportId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_REPORT_ID_PATTERN = "^crt_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * ``client``: «Отчёт для заказчика · Изменения проектных решений», one model call per transition over
 * the summary's facts; a program check drops every point whose number, mark or direction the facts do not
 * confirm. ``analytic``: analyst, verifier and composer.
 */
export const COMPARISON_REPORT_KIND_VALUES = [
  'client',
  'analytic',
] as const;

/** ComparisonReportKind - the closed value set above. */
export type ComparisonReportKind = (typeof COMPARISON_REPORT_KIND_VALUES)[number];

/** The report history of a series, newest first. */
export type ComparisonReportPage = {
  items: Array<ComparisonReport>;
  page: PageInfo;
};

/**
 * The progress of one transition of a report. An analytic report fills ``analysis``,
 * ``verification``, ``facts`` and ``warnings`` («Анализ», «Проверка», «Факты», «Предупреждения»); a
 * client report ``selection``, ``points`` and ``questions`` («Отбор», «Пунктов», «Вопросов»).
 */
export type ComparisonReportPart = {
  analysis?: ComparisonReportUnitMark;
  facts?: ComparisonReportFacts;
  points?: number;
  questions?: number;
  selection?: ComparisonReportUnitMark;
  transition_id: ComparisonTransitionId;
  verification?: ComparisonReportUnitMark;
  warnings?: number;
};

/**
 * ``series_summary``: the deterministic MD summary of the series. ``uploaded_md``: an MD file the
 * user uploaded (UTF-8, at most 20 MiB, with the transitions headed «## N. … A → B»).
 */
export const COMPARISON_REPORT_SOURCE_VALUES = [
  'series_summary',
  'uploaded_md',
] as const;

/** ComparisonReportSource - the closed value set above. */
export type ComparisonReportSource = (typeof COMPARISON_REPORT_SOURCE_VALUES)[number];

/**
 * «файл принят, подготовка», «анализ переходов», «проверка выводов», «составление отчёта»,
 * «написание текста для заказчика» (the client kind) and «формирование PDF».
 */
export const COMPARISON_REPORT_STAGE_VALUES = [
  'intake',
  'transition_analysis',
  'verification',
  'composition',
  'client_writing',
  'pdf_writing',
] as const;

/** ComparisonReportStage - the closed value set above. */
export type ComparisonReportStage = (typeof COMPARISON_REPORT_STAGE_VALUES)[number];

/**
 * ``draft``: created with its estimate, not started and nothing spent. ``partial``: finished with a
 * transition missing or a unit failed («неполный результат»).
 */
export const COMPARISON_REPORT_STATE_VALUES = [
  'draft',
  'queued',
  'running',
  'paused',
  'completed',
  'partial',
  'failed',
  'cancelled',
] as const;

/** ComparisonReportState - the closed value set above. */
export type ComparisonReportState = (typeof COMPARISON_REPORT_STATE_VALUES)[number];

/** «✓ ⟳ ✗ ·». */
export const COMPARISON_REPORT_UNIT_MARK_VALUES = [
  'done',
  'running',
  'failed',
  'pending',
] as const;

/** ComparisonReportUnitMark - the closed value set above. */
export type ComparisonReportUnitMark = (typeof COMPARISON_REPORT_UNIT_MARK_VALUES)[number];

export type ComparisonReviewSheet = {
  kind: ComparisonReviewSheetKind;
  page_a?: ComparisonPairPage;
  page_b?: ComparisonPairPage;
  sheet_pair_id: ComparisonSheetPairId;
  state: ComparisonAiSheetState;
};

/**
 * ``to_check``: the AI found no change but the comparison left marks («Проверить»). ``added`` and
 * ``removed``: a single sheet of the transition, described on its own.
 */
export const COMPARISON_REVIEW_SHEET_KIND_VALUES = [
  'to_check',
  'added',
  'removed',
] as const;

/** ComparisonReviewSheetKind - the closed value set above. */
export type ComparisonReviewSheetKind = (typeof COMPARISON_REVIEW_SHEET_KIND_VALUES)[number];

/** In the order of the matrix rows. */
export type ComparisonReviewSheetPage = {
  items: Array<ComparisonReviewSheet>;
  page: PageInfo;
};

/**
 * The comparison of every adjacent pair of the versions of a document set, for one version
 * order (ADR-0025 decisions 15 and 21). ``transitions`` is present on ``getComparisonSeries``
 * and absent in the items of ``listComparisonSeries``. ``stale_reasons`` is present when the
 * stored input digests no longer match the current order, matrix or profiles («Сохранённая
 * сводка для прежнего порядка версий»). ``restarted_from`` names the series a «Заново» replaced.
 * ``order_id`` is the version-order revision the series ran on (absent for the document's own
 * order).
 */
export type ComparisonSeries = {
  created_at: string;
  document_uid: DocumentUid;
  failure_reason?: string;
  matrix_revision?: ComparisonMatrixRevision;
  order_id?: ComparisonVersionOrderId;
  project_uid: ProjectUid;
  restarted_from?: ComparisonSeriesId;
  series_id: ComparisonSeriesId;
  stale_reasons?: Array<ComparisonSeriesStaleReason>;
  state: ComparisonSeriesState;
  transitions?: Array<ComparisonTransition>;
  transitions_done: number;
  transitions_total: number;
  updated_at: string;
};

export type ComparisonSeriesId = string;

/** The contract pattern for `ComparisonSeriesId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_SERIES_ID_PATTERN = "^cser_[0-9A-HJKMNP-TV-Z]{26}$";

/** Newest first. */
export type ComparisonSeriesPage = {
  items: Array<ComparisonSeries>;
  page: PageInfo;
};

/** ComparisonSeriesStaleReason. */
export const COMPARISON_SERIES_STALE_REASON_VALUES = [
  'order_changed',
  'matrix_changed',
  'profiles_changed',
] as const;

/** ComparisonSeriesStaleReason - the closed value set above. */
export type ComparisonSeriesStaleReason = (typeof COMPARISON_SERIES_STALE_REASON_VALUES)[number];

/** ComparisonSeriesState. */
export const COMPARISON_SERIES_STATE_VALUES = [
  'queued',
  'running',
  'paused',
  'completed',
  'failed',
  'cancelled',
] as const;

/** ComparisonSeriesState - the closed value set above. */
export type ComparisonSeriesState = (typeof COMPARISON_SERIES_STATE_VALUES)[number];

/**
 * A change in the service zones: ``zone`` and ``field`` name where, ``kind`` what (a
 * ``stamp``, ``warning``, ``qr`` code, ``field`` or PDF ``annotation``). The disappearance of a
 * warning does not confirm an approval.
 */
export type ComparisonServiceNote = {
  after?: string;
  before?: string;
  change: ComparisonNoteChange;
  field?: string;
  kind: string;
  zone?: string;
};

/**
 * The stored AI description of one sheet pair (or of one added or removed sheet). Reading it never
 * calls a model. ``description_id`` and the members after ``source`` are absent while the state is
 * ``not_processed``, ``queued``, ``running`` or ``engine_same``. ``job_id`` names the job that is
 * queued or running for the sheet. ``recorded`` is true for a recorded (test) answer, which the client
 * labels as such. The description is model output not confirmed by an engineer and never changes the
 * raw comparison of the pair.
 */
export type ComparisonSheetDescription = {
  changes?: Array<ComparisonAiChange>;
  coverage?: ComparisonAiCoverage;
  created_at?: string;
  declared?: Array<ComparisonAiDeclaredItem>;
  description_id?: ComparisonSheetDescriptionId;
  diagnostics?: ComparisonAiDiagnostics;
  excluded?: Array<ComparisonAiExcluded>;
  history_count: number;
  job_id?: ComparisonAiJobId;
  model?: string;
  prompt_version?: string;
  recorded?: boolean;
  sheet_pair_id: ComparisonSheetPairId;
  source?: ComparisonSheetDescriptionSource;
  state: ComparisonAiSheetState;
  unresolved?: Array<ComparisonAiUnresolved>;
};

/** Newest first. */
export type ComparisonSheetDescriptionHistory = {
  items: Array<ComparisonSheetDescriptionRevision>;
  page: PageInfo;
};

export type ComparisonSheetDescriptionId = string;

/** The contract pattern for `ComparisonSheetDescriptionId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_SHEET_DESCRIPTION_ID_PATTERN = "^csd_[0-9A-HJKMNP-TV-Z]{26}$";

/** One entry of «История (N)». */
export type ComparisonSheetDescriptionRevision = {
  changes_count: number;
  created_at: string;
  description_id: ComparisonSheetDescriptionId;
  model?: string;
  prompt_version?: string;
  recorded: boolean;
  state: ComparisonAiSheetState;
  unresolved_count: number;
};

/**
 * ``sheet`` the description of the sheet pair; ``whole_specification`` the changes of this sheet
 * were taken from the comparison of the whole specifications («По полной спецификации · только
 * изменения этого листа»).
 */
export const COMPARISON_SHEET_DESCRIPTION_SOURCE_VALUES = [
  'sheet',
  'whole_specification',
] as const;

/** ComparisonSheetDescriptionSource - the closed value set above. */
export type ComparisonSheetDescriptionSource = (typeof COMPARISON_SHEET_DESCRIPTION_SOURCE_VALUES)[number];

/**
 * One sheet pair of a transition: the older page ``page_a``, the newer ``page_b``, either
 * absent for an ``added`` or ``removed`` sheet. ``status`` and the members after it are absent
 * until the pair has a result. ``result_id`` is the content-keyed result the pair uses
 * (ADR-0025 decision 15); it is shared by pairs of equal content within a project. The members
 * from ``canvas`` on are the raw deterministic evidence and are present on
 * ``getComparisonSheetPair`` only; an AI layer never rewrites them.
 */
export type ComparisonSheetPair = {
  ai_dependent?: boolean;
  canvas?: ComparisonCanvas;
  channels?: ComparisonChannels;
  confidence?: ComparisonCellConfidence;
  differences?: Array<ComparisonDifference>;
  failure_reason?: string;
  flags?: Array<ComparisonCellFlag>;
  how_compared?: ComparisonHowCompared;
  page_a?: ComparisonPairPage;
  page_b?: ComparisonPairPage;
  parts?: ComparisonPartsCoverage;
  permit?: ComparisonPermit;
  reasons?: Array<string>;
  result_id?: ComparisonSheetPairResultId;
  service_notes?: Array<ComparisonServiceNote>;
  sheet_pair_id: ComparisonSheetPairId;
  state: ComparisonSheetPairState;
  status?: ComparisonSheetStatus;
  text_changes?: Array<ComparisonTextChange>;
  transition_id: ComparisonTransitionId;
};

export type ComparisonSheetPairId = string;

/** The contract pattern for `ComparisonSheetPairId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_SHEET_PAIR_ID_PATTERN = "^ctp_[0-9A-HJKMNP-TV-Z]{26}$";

/** The sheet pairs of a transition in the order of the matrix rows. */
export type ComparisonSheetPairPage = {
  items: Array<ComparisonSheetPair>;
  page: PageInfo;
};

export type ComparisonSheetPairResultId = string;

/** The contract pattern for `ComparisonSheetPairResultId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_SHEET_PAIR_RESULT_ID_PATTERN = "^csp_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * «Спецификация по позициям» of a sheet pair: the position changes that fall on the pair's pages,
 * deterministic, from the positions of the whole specification of each version (a position may move
 * between pages without changing).
 */
export type ComparisonSheetPairSpecPositions = {
  changes: Array<ComparisonSpecChange>;
  is_specification: boolean;
  sheet_pair_id: ComparisonSheetPairId;
  totals: ComparisonSpecTotals;
};

/** ComparisonSheetPairState. */
export const COMPARISON_SHEET_PAIR_STATE_VALUES = [
  'queued',
  'computing',
  'done',
  'failed',
] as const;

/** ComparisonSheetPairState - the closed value set above. */
export type ComparisonSheetPairState = (typeof COMPARISON_SHEET_PAIR_STATE_VALUES)[number];

/**
 * The status of one sheet pair (the original's ``result_status``): ``same``, ``same_zones_changed``
 * (the main content is the same, service zones changed), ``different``, ``needs_review``,
 * ``added`` (only in the newer version), ``removed`` (only in the older one) and
 * ``unmatched``.
 */
export const COMPARISON_SHEET_STATUS_VALUES = [
  'same',
  'same_zones_changed',
  'different',
  'needs_review',
  'added',
  'removed',
  'unmatched',
] as const;

/** ComparisonSheetStatus - the closed value set above. */
export type ComparisonSheetStatus = (typeof COMPARISON_SHEET_STATUS_VALUES)[number];

/**
 * One change between two specifications: the position before (``old``) and after (``new``), the
 * fields that differ, and the sentence the comparison renders. A position that exists on one side only
 * is ``added`` or ``removed`` and carries that side.
 */
export type ComparisonSpecChange = {
  change_id: string;
  fields: Array<ComparisonSpecFieldChange>;
  kind: ComparisonSpecChangeKind;
  new?: ComparisonSpecPosition;
  old?: ComparisonSpecPosition;
  text?: string;
};

/**
 * ``changed``, ``added`` «+добавлено», ``removed`` «−удалено», ``unclear`` «?неясно» (the match is
 * ambiguous), ``renumbered`` (only the position number differs) and ``moved`` (the same position under
 * another section, not a change).
 */
export const COMPARISON_SPEC_CHANGE_KIND_VALUES = [
  'changed',
  'added',
  'removed',
  'unclear',
  'renumbered',
  'moved',
] as const;

/** ComparisonSpecChangeKind - the closed value set above. */
export type ComparisonSpecChangeKind = (typeof COMPARISON_SPEC_CHANGE_KIND_VALUES)[number];

/**
 * The changes of a transition's specification comparison, in the order the comparison lists them
 * (changed, removed, added, unclear, renumbered).
 */
export type ComparisonSpecChangePage = {
  items: Array<ComparisonSpecChange>;
  page: PageInfo;
};

export type ComparisonSpecComparisonId = string;

/** The contract pattern for `ComparisonSpecComparisonId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_SPEC_COMPARISON_ID_PATTERN = "^cscp_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * «покрыто»: the blocks of the specification text the model's markup covers and the rows it could
 * not settle. A quote or a value the program cannot find in the source makes that side incomplete.
 */
export type ComparisonSpecCoverage = {
  blocks_covered: number;
  blocks_total: number;
  rows_total: number;
  rows_unresolved: number;
};

export type ComparisonSpecExtractionId = string;

/** The contract pattern for `ComparisonSpecExtractionId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_SPEC_EXTRACTION_ID_PATTERN = "^cse_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * «было → стало» of one field. ``field`` is one of the nine fields of a position of a specification
 * (GOST 21.110): ``pos``, ``name``, ``mark``, ``code``, ``supplier``, ``unit``, ``quantity``, ``mass``
 * and ``note`` (an open word, so that the contract does not freeze the table layout).
 */
export type ComparisonSpecFieldChange = {
  field: string;
  now?: string;
  was?: string;
};

/**
 * ``whole``: «полное сравнение», the whole specification of each version was read by a model and the
 * two were compared order-independently. ``sheet_ai``: «листовой ИИ», the specification sheets are
 * described one by one in the AI description of changes.
 */
export const COMPARISON_SPEC_METHOD_VALUES = [
  'whole',
  'sheet_ai',
] as const;

/** ComparisonSpecMethod - the closed value set above. */
export type ComparisonSpecMethod = (typeof COMPARISON_SPEC_METHOD_VALUES)[number];

/**
 * Part A for one page of a version: whether the page is a specification sheet and, when it is, the
 * positions the deterministic parser reads from the page's words and vector lines (``spec_version`` is
 * the parser's). Deterministic; no model is called.
 */
export type ComparisonSpecPage = {
  ambiguous_rows: number;
  is_specification: boolean;
  page_profile_id: ComparisonPageProfileId;
  positions: Array<ComparisonSpecPosition>;
  spec_version: string;
};

/** ComparisonSpecPhase. */
export const COMPARISON_SPEC_PHASE_VALUES = [
  'preparing',
  'comparing',
  'done',
] as const;

/** ComparisonSpecPhase - the closed value set above. */
export type ComparisonSpecPhase = (typeof COMPARISON_SPEC_PHASE_VALUES)[number];

/**
 * One position of a specification, every value verbatim as the sheet writes it (nothing is summed,
 * rounded or normalised). ``section`` and ``parent`` place the row; ``ambiguous`` marks a row whose type
 * the parser could not decide and did not guess.
 */
export type ComparisonSpecPosition = {
  ambiguous?: boolean;
  code?: string;
  mark?: string;
  mass?: string;
  name: string;
  note?: string;
  page?: ComparisonPageRef;
  parent?: string;
  pos?: string;
  quantity?: string;
  section?: string;
  supplier?: string;
  unit?: string;
};

/**
 * ``not_applicable``: the transition has no specification sheet. ``incomplete``: a side could not be
 * read completely and no addition, removal or absence of change is published. ``running`` and
 * ``paused`` carry the phase.
 */
export const COMPARISON_SPEC_STATE_VALUES = [
  'not_applicable',
  'not_started',
  'running',
  'paused',
  'completed',
  'incomplete',
  'failed',
  'cancelled',
] as const;

/** ComparisonSpecState - the closed value set above. */
export type ComparisonSpecState = (typeof COMPARISON_SPEC_STATE_VALUES)[number];

/** «изменено / +добавлено / −удалено / ?неясно», and the two kinds that are not changes. */
export type ComparisonSpecTotals = {
  added: number;
  changed: number;
  moved: number;
  removed: number;
  renumbered: number;
  unclear: number;
};

/**
 * The comparison of the specifications of one transition: the method, the number of specification
 * sheets of the older and of the newer version, the coverage and the totals once there are any, and the
 * reason a side is incomplete or the comparison failed (an engine-style code). The changes themselves
 * are read page by page. Part B is model output not confirmed by an engineer; the deterministic
 * positions of part A are read per sheet.
 */
export type ComparisonSpecification = {
  comparison_id?: ComparisonSpecComparisonId;
  coverage_a?: ComparisonSpecCoverage;
  coverage_b?: ComparisonSpecCoverage;
  extraction_a_id?: ComparisonSpecExtractionId;
  extraction_b_id?: ComparisonSpecExtractionId;
  job_id?: ComparisonAiJobId;
  method: ComparisonSpecMethod;
  phase?: ComparisonSpecPhase;
  reason?: string;
  sheets_a: number;
  sheets_b: number;
  state: ComparisonSpecState;
  totals?: ComparisonSpecTotals;
  transition_id: ComparisonTransitionId;
  updated_at?: string;
};

/** The transitions of a series that have a specification, in transition order. */
export type ComparisonSpecificationPage = {
  items: Array<ComparisonSpecification>;
  page: PageInfo;
};

/** The figures a step's note quotes; each is absent when the step has no such figure. */
export type ComparisonStepCounts = {
  done?: number;
  failed?: number;
  manual_edits?: number;
  ready?: number;
  rows?: number;
  total?: number;
  unmatched?: number;
  with_changes?: number;
};

/**
 * The seven steps of a document set on «Проекты и этапы», in order: ``upload`` «Загрузка»,
 * ``profile`` «Разбор версий», ``matrix`` «Сопоставление листов», ``ai_pairs`` «ИИ-проверка
 * сомнительных пар», ``series`` «Сравнение соседних», ``ai_changes`` «ИИ-описание изменений»,
 * ``report`` «Сводка и отчёт».
 */
export const COMPARISON_STEP_ID_VALUES = [
  'upload',
  'profile',
  'matrix',
  'ai_pairs',
  'series',
  'ai_changes',
  'report',
] as const;

/** ComparisonStepId - the closed value set above. */
export type ComparisonStepId = (typeof COMPARISON_STEP_ID_VALUES)[number];

/**
 * The state words of the original's seven columns, as codes. ``not_started`` and
 * ``not_applicable`` are the two ways a step has nothing to show; ``attention``, ``partial``,
 * ``stale``, ``interrupted`` and ``paused`` are the amber ones, ``queued``, ``running`` and
 * ``pausing`` the running ones, ``failed`` the red one, ``blocked`` a step waiting for the one
 * before it.
 */
export const COMPARISON_STEP_STATE_VALUES = [
  'not_started',
  'queued',
  'running',
  'pausing',
  'paused',
  'interrupted',
  'done',
  'partial',
  'stale',
  'attention',
  'failed',
  'blocked',
  'not_applicable',
] as const;

/** ComparisonStepState - the closed value set above. */
export type ComparisonStepState = (typeof COMPARISON_STEP_STATE_VALUES)[number];

/**
 * `COMPARE-PERSISTED-SUMMARY-01` (B2). A model's summary of the approved pairs, stored beside
 * their raw differences and never inside them. ``label`` is fixed and shown with it: no human has
 * reviewed the text. ``state`` is ``ready`` or ``rejected`` (the check refused the reply: no
 * statements, one ``rejection_reason``; the reply was paid for, so it is recorded). ``provider_mode``
 * ``recorded`` is a replayed reply, ``model_identity`` ``recorded`` then, and ``cost_basis``
 * ``unmetered``. ``is_current``: it describes the approved set as it stands now.
 */
export type ComparisonSummary = {
  cost_basis: CostBasis;
  created_at: string;
  created_by_label: string;
  input_sha256: Sha256;
  is_current: boolean;
  label: "Сводка подготовлена моделью, проверка человеком не проводилась";
  link_revision: number;
  model_identity: string;
  prompt_version: string;
  provider_mode: "recorded" | "live";
  raw_evidence_seal_sha256: Sha256;
  rejection_reason: "reply_not_json" | "reply_shape_invalid" | "unknown_hunk_reference" | null;
  state: "ready" | "rejected";
  statements: Array<SummaryStatement>;
  summary_id: string;
};

/**
 * «было → стало» of one text fragment; ``numbers`` lists the numeric values that changed
 * inside it, to be highlighted.
 */
export type ComparisonTextChange = {
  after?: string;
  before?: string;
  box?: ComparisonBox;
  kind: string;
  numbers?: Array<ComparisonNumberChange>;
};

/**
 * One adjacent transition of a series: the older version ``source_version_uid`` and the
 * next one ``target_version_uid``. ``items_done`` of ``items_total`` sheet pairs have a result.
 * ``verdict`` is absent until the transition has run.
 */
export type ComparisonTransition = {
  failure_reason?: string;
  items_done: number;
  items_total: number;
  series_id: ComparisonSeriesId;
  source_version_uid: VersionUid;
  state: ComparisonTransitionState;
  summary: ComparisonTransitionSummary;
  target_version_uid: VersionUid;
  transition_id: ComparisonTransitionId;
  verdict?: Array<ComparisonVerdictCode>;
};

export type ComparisonTransitionId = string;

/** The contract pattern for `ComparisonTransitionId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_TRANSITION_ID_PATTERN = "^ctn_[0-9A-HJKMNP-TV-Z]{26}$";

/** ComparisonTransitionState. */
export const COMPARISON_TRANSITION_STATE_VALUES = [
  'queued',
  'running',
  'completed',
  'failed',
  'cancelled',
] as const;

/** ComparisonTransitionState - the closed value set above. */
export type ComparisonTransitionState = (typeof COMPARISON_TRANSITION_STATE_VALUES)[number];

/**
 * The counts of a transition's sheet pairs. ``needs_review`` includes the unmatched ones.
 * ``style_only`` counts the ``different`` sheets whose only difference is line style.
 * ``ai_dependent`` counts the pairs that rest on an accepted AI link.
 */
export type ComparisonTransitionSummary = {
  added: number;
  ai_dependent?: number;
  compared: number;
  different: number;
  failed: number;
  needs_review: number;
  removed: number;
  same: number;
  sheets: number;
  style_only: number;
  zones_only: number;
};

/**
 * One upload batch. ``files`` is present on ``getComparisonUpload`` and absent in the
 * items of ``listComparisonUploads``. ``part_size_bytes`` is the size of every part but the
 * last (16 MiB, ADR-0025 decision 10).
 */
export type ComparisonUpload = {
  compare_after_preparation?: boolean;
  created_at: string;
  declared_bytes: number;
  declared_files: number;
  files?: Array<ComparisonUploadFile>;
  part_size_bytes: number;
  project_uid: ProjectUid;
  state: ComparisonUploadState;
  updated_at: string;
  upload_id: ComparisonUploadId;
};

export type ComparisonUploadFile = {
  display_name: string;
  failure_reason?: string;
  file_id: ComparisonUploadFileId;
  parts_staged: number;
  set_id?: ComparisonUploadSetId;
  sha256: Sha256;
  size_bytes: number;
  state: ComparisonUploadFileState;
};

/**
 * One file the client will send. ``display_name`` is a hint for the proposal and never an
 * identity; ``sha256`` and ``size_bytes`` are checked against the received bytes when the file
 * is completed.
 */
export type ComparisonUploadFileDeclaration = {
  display_name: string;
  page_count?: number;
  sha256: Sha256;
  size_bytes: number;
};

export type ComparisonUploadFileId = string;

/** The contract pattern for `ComparisonUploadFileId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_UPLOAD_FILE_ID_PATTERN = "^cuf_[0-9A-HJKMNP-TV-Z]{26}$";

/** ComparisonUploadFileState. */
export const COMPARISON_UPLOAD_FILE_STATE_VALUES = [
  'declared',
  'uploading',
  'verified',
  'failed',
] as const;

/** ComparisonUploadFileState - the closed value set above. */
export type ComparisonUploadFileState = (typeof COMPARISON_UPLOAD_FILE_STATE_VALUES)[number];

export type ComparisonUploadId = string;

/** The contract pattern for `ComparisonUploadId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_UPLOAD_ID_PATTERN = "^cbt_[0-9A-HJKMNP-TV-Z]{26}$";

export type ComparisonUploadPage = {
  items: Array<ComparisonUpload>;
  page: PageInfo;
};

/**
 * What the server staged for one part: its size and the SHA-256 it computed, which the
 * client may compare with its own.
 */
export type ComparisonUploadPartReceipt = {
  file_id: ComparisonUploadFileId;
  part_number: number;
  sha256: Sha256;
  size_bytes: number;
};

/**
 * The grouping, order, stage and section the reader proposes for an upload. Nothing is
 * admitted as a version until the user confirms a set (``confirmComparisonUploadSet``).
 */
export type ComparisonUploadProposal = {
  sets: Array<ComparisonProposalSet>;
  state: ComparisonUploadState;
  upload_id: ComparisonUploadId;
};

export type ComparisonUploadSetId = string;

/** The contract pattern for `ComparisonUploadSetId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_UPLOAD_SET_ID_PATTERN = "^cus_[0-9A-HJKMNP-TV-Z]{26}$";

/** ComparisonUploadSetState. */
export const COMPARISON_UPLOAD_SET_STATE_VALUES = [
  'uploading',
  'reading',
  'needs_confirmation',
  'ready',
  'admitting',
  'done',
  'failed',
  'excluded',
] as const;

/** ComparisonUploadSetState - the closed value set above. */
export type ComparisonUploadSetState = (typeof COMPARISON_UPLOAD_SET_STATE_VALUES)[number];

/** ComparisonUploadState. */
export const COMPARISON_UPLOAD_STATE_VALUES = [
  'uploading',
  'proposed',
  'processing',
  'paused',
  'completed',
  'cancelled',
] as const;

/** ComparisonUploadState - the closed value set above. */
export type ComparisonUploadState = (typeof COMPARISON_UPLOAD_STATE_VALUES)[number];

/**
 * The parts of the deterministic verdict of a transition, in the order they are shown; the
 * figures they quote are in the transition's ``summary``. A transition has one or more parts.
 * The client renders the sentence.
 */
export const COMPARISON_VERDICT_CODE_VALUES = [
  'incomplete',
  'content_same',
  'zones_only',
  'different',
  'composition_changed',
  'needs_review',
  'calculation_failed',
] as const;

/** ComparisonVerdictCode - the closed value set above. */
export type ComparisonVerdictCode = (typeof COMPARISON_VERDICT_CODE_VALUES)[number];

/**
 * One revision of the order in which the versions of a document set are compared. It
 * never changes the documents' ordinal that runs and finding carry-over use (ADR-0025
 * decision 16, `D-5`).
 */
export type ComparisonVersionOrder = {
  created_at: string;
  created_by: UserUid;
  document_uid: DocumentUid;
  order_id: ComparisonVersionOrderId;
  revision_no: number;
  source: ComparisonVersionOrderSource;
  version_uids: Array<VersionUid>;
};

export type ComparisonVersionOrderId = string;

/** The contract pattern for `ComparisonVersionOrderId`. Anchored; use with `new RegExp()`. */
export const COMPARISON_VERSION_ORDER_ID_PATTERN = "^cvo_[0-9A-HJKMNP-TV-Z]{26}$";

/** Newest revision first. */
export type ComparisonVersionOrderList = {
  items: Array<ComparisonVersionOrder>;
  page: PageInfo;
};

/** ComparisonVersionOrderSource. */
export const COMPARISON_VERSION_ORDER_SOURCE_VALUES = [
  'proposal',
  'expert',
] as const;

/** ComparisonVersionOrderSource - the closed value set above. */
export type ComparisonVersionOrderSource = (typeof COMPARISON_VERSION_ORDER_SOURCE_VALUES)[number];

/**
 * The user's final word on one set: its members in their order (the array order is the
 * version order), the labels, and the designation, stage, section and existing document the
 * set belongs to. The stage and section are a proposal an expert confirms, never inferred.
 */
export type ConfirmComparisonUploadSetRequest = {
  designation?: string;
  existing_document_uid?: DocumentUid;
  files: Array<ConfirmedComparisonFile>;
  project_stage?: ProjectStage;
  section_code?: ProjectSection;
};

/** The fingerprint the administrator read and confirms. It must equal the one the worker observed; there is no trust on first use. */
export type ConfirmExecutorAgentInstallHostKeyRequest = {
  host_key_fingerprint: string;
};

export type ConfirmStagePairRequest = {
  assembly_id?: StageAssemblyId;
  left_document_uid: DocumentUid;
  right_document_uid?: DocumentUid;
};

export type ConfirmStageUploadCandidateRequest = {
  designation: string;
  existing_document_uid?: DocumentUid;
  section_code: string;
  stage: "P" | "R";
};

export type ConfirmedComparisonFile = {
  file_id: ComparisonUploadFileId;
  version_label?: string;
};

/**
 * `CLASSIFICATION-CORRECTION-01`. An expert's correction of one version's classification.
 *
 * The full target pair, why, and the revision the caller was looking at
 * (``expected_revision``): the optimistic-concurrency token that also makes an exact retry
 * safe. At least one of the two values must differ from the current classification.
 */
export type CorrectVersionClassificationRequest = {
  expected_revision: number;
  project_stage: ProjectStage;
  reason: string;
  section_code: ProjectSection;
};

/** Not an entity identity. Never a foreign key and authorizes nothing. */
export type CorrelationId = string;

/** The contract pattern for `CorrelationId`. Anchored; use with `new RegExp()`. */
export const CORRELATION_ID_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$";

/** How well a published cost figure is known. `measured` means every provider call the figure sums reported its own cost; `estimated` means at least one did not, so the total is derived; `unmetered` (`EXEC-SEAL-01`, `R-143f`) means a call ran on a connection that has no per-call cost, so the figure is absent and never a zero. The value is an aggregate over **every** call the figure spans and is never the last call's basis: a run whose first attempt replayed and whose second reported a cost is `estimated`. */
export const COST_BASIS_VALUES = [
  'measured',
  'estimated',
  'unmetered',
] as const;

/** CostBasis - the closed value set above. */
export type CostBasis = (typeof COST_BASIS_VALUES)[number];

/** `W61-DISPATCHER-01`. Give a project, or one document of it, to an active expert. */
export type CreateAssignmentRequest = {
  assignee_user_uid: UserUid;
  document_uid?: DocumentUid;
  note?: string;
  project_uid: ProjectUid;
};

/**
 * Creates a ``draft`` report from the series' MD summary and computes its estimate; no model is
 * called and nothing is spent. ``kind`` defaults to ``client``.
 */
export type CreateComparisonReportRequest = {
  kind?: ComparisonReportKind;
  reuse?: boolean;
};

/**
 * The declared files of one upload batch. The limits of ADR-0025 decision 9 (files, sets,
 * declared bytes and pages, the project's stored bytes, active batches) are refused here,
 * before the first part, as typed reasons under existing error codes.
 */
export type CreateComparisonUploadRequest = {
  compare_after_preparation?: boolean;
  files: Array<ComparisonUploadFileDeclaration>;
};

/** Write-only where it carries a key. `private_key` is required for `pasted_key` and refused for `generated_key`; the API seals it to the stand's public key and never returns it. */
export type CreateExecutorAgentInstallRequest = {
  access: ExecutorAgentInstallAccess;
  private_key?: string;
  ssh_host: string;
  ssh_port: number;
  ssh_user: string;
};

export type CreateExecutorConnectionRequest = {
  display_name: string;
  kind: ExecutorKind;
};

/** A new group and its first revision (`EXEC2-SEAL-2`, ADR-0026 decision 10). The pinned rates are not sent: the server takes them from the provider lock for `pin_id`. `strategy` absent means `least_loaded`. A member names a connection and the revision of it the group should snapshot; every member must match `pin_id`, `gateway_model` and `billing` exactly. */
export type CreateExecutorGroupRequest = {
  billing: ExecutorBilling;
  display_name: string;
  gateway_model: string;
  members: Array<ExecutorGroupMember>;
  pin_id: string;
  strategy?: ExecutorGroupStrategy;
};

/**
 * A new server and an install session of the agent over SSH (path A). As `CreateExecutorAgentInstallRequest`, with a name and
 * no model: `private_key` is required for `pasted_key` and refused for `generated_key`, sealed and never returned.
 */
export type CreateExecutorHostAgentInstallRequest = {
  access: ExecutorAgentInstallAccess;
  display_name: string;
  private_key?: string;
  ssh_host: string;
  ssh_port: number;
  ssh_user: string;
};

export type CreateProjectRequest = {
  /** Display label. Not unique and not an identity. */
  name: string;
};

export type CreateStageAssemblyRequest = {
  document_uids: Array<DocumentUid>;
  label: string;
};

export type CreateStageReviewCardRequest = {
  reason: string;
  source_ids: Array<StageAtomicEvidenceId>;
};

export type CreateStageUploadRequest = {
  files: Array<StageUploadFileDeclaration>;
};

/** Opaque pagination token. It encodes the sort key of the last item on the page and nothing else; it is never a database row number or sequence value. */
export type Cursor = string;

/** `getDashboardSummary`'s whole answer. All four panels, one read, one optional filter: the request's `project_uid` (`UI-PARITY-P0A`) restricts every panel to that project and the answer carries no echo of it. It also carries `awaiting_decision_findings`, the findings still awaiting a decision in the result runs of current versions (`R-150q`). */
export type DashboardSummary = {
  /** Findings whose current verdict is undecided (`pending` or `needs_manual_review`) in the result runs of current versions (`R-150q`). The figure of the tile «Находки, ожидающие решения». Unlike `findings_by_verdict`, which counts every finding of every run («за всё время»), it follows only the current versions, and it is restricted by `project_uid` like every panel. */
  awaiting_decision_findings: number;
  documents_by_project: Array<ProjectDocumentCount>;
  findings_by_verdict: Array<VerdictCount>;
  run_activity: RunActivity;
  section_breakdown: Array<SectionDocumentCount>;
};

/**
 * `W60-OPT-PROPOSALS-01`. An expert's verdict on a proposal, with a comment that
 * ``revise`` requires.
 */
export type DecideOptimisationProposalRequest = {
  comment?: string;
  verdict: ProposalVerdict;
};

/**
 * `UI-A-73` (contract 1.39.0): where a carried decision came from -- the decision of an earlier version's finding
 * that an expert carried over to this finding (`W59-DECISION-CARRYOVER-01`).
 *
 * ``decision_id`` is the source decision's own identity and ``finding_uid`` and ``version_uid`` the finding and the
 * version it was made on. ``version_ordinal`` is the version's display order («V2») and is never an identity.
 */
export type DecisionCarriedFrom = {
  decision_id: DecisionId;
  finding_uid: FindingUid;
  version_ordinal: number;
  version_uid: VersionUid;
};

/** One appended event. Never updated and never removed. `carried_from` (`UI-A-73`, contract 1.39.0) names the decision of an earlier version's finding that an expert carried over to this finding (`DecisionCarriedFrom`); it is absent for an event an expert made directly, and for every event written before migration `0058`, whose rendered `comment` still says where it came from. */
export type DecisionEvent = {
  /** OD-12, as `R-37` now defines it: the display name of the reviewer who recorded the event -- the name they chose, or their login when they have chosen none -- derived server-side from the authenticated credential and **never** taken from a request body. It IS a subject identity: it names which reviewer judged, which is what `P04` needs and what one configured label for every reviewer could not give it. It still authorizes nothing: it is what the ledger records about who judged, not a permission anybody holds, and no client can choose it. The ledger is append-only, so an event keeps the label it was written with even after that reviewer is renamed. */
  author_label: string;
  carried_from?: DecisionCarriedFrom;
  comment?: string | null;
  decision_id: DecisionId;
  event_type: DecisionEventType;
  finding_observation_id: FindingObservationId;
  finding_uid: FindingUid;
  recorded_at: string;
  severity?: Severity;
  /** The verdict this event carries, or null for a comment. */
  verdict?: Verdict | null;
};

export type DecisionEventPage = {
  items: Array<DecisionEvent>;
  page: PageInfo;
};

/** PC-01 emits accept, reject and comment. `revoke` is declared so PD-01 revocation stays implementable without a schema change. */
export const DECISION_EVENT_TYPE_VALUES = [
  'accept',
  'reject',
  'comment',
  'revoke',
] as const;

/** DecisionEventType - the closed value set above. */
export type DecisionEventType = (typeof DECISION_EVENT_TYPE_VALUES)[number];

export type DecisionId = string;

/** The contract pattern for `DecisionId`. Anchored; use with `new RegExp()`. */
export const DECISION_ID_PATTERN = "^dec_[0-9A-HJKMNP-TV-Z]{26}$";

/** ``recorded``: a decision event was appended; ``unchanged``: the ledger already says it; ``refused``. */
export const DECISION_IMPORT_OUTCOME_VALUES = [
  'recorded',
  'unchanged',
  'refused',
] as const;

/** DecisionImportOutcome - the closed value set above. */
export type DecisionImportOutcome = (typeof DECISION_IMPORT_OUTCOME_VALUES)[number];

/** Why a row of the workbook was refused. */
export const DECISION_IMPORT_REFUSAL_VALUES = [
  'no_finding_uid',
  'duplicate_finding',
  'unknown_finding',
  'finding_not_in_run',
  'unknown_decision',
  'not_importable',
] as const;

/** DecisionImportRefusal - the closed value set above. */
export type DecisionImportRefusal = (typeof DECISION_IMPORT_REFUSAL_VALUES)[number];

/** `R-151d`: what an import of edited decisions did, row by row, in sheet order. */
export type DecisionImportReport = {
  recorded: number;
  refused: number;
  rows: Array<DecisionImportRow>;
  run_id: RunId;
  unchanged: number;
};

/** `R-151d`: one row of «Замечания» that names an ID or a decision; ``finding_uid`` only for a known finding. */
export type DecisionImportRow = {
  finding_uid?: FindingUid;
  outcome: DecisionImportOutcome;
  reason?: DecisionImportRefusal;
  row: number;
};

/** A case with everything it keeps. ``content`` is ``null`` and the lists are empty for a forgotten case (its tombstone only). */
export type DecisionMemoryCase = {
  content: DecisionMemoryContent | null;
  crops: Array<DecisionMemoryCrop>;
  decisions: Array<DecisionMemoryDecision>;
  evidence: Array<DecisionMemoryEvidence>;
  norm_refs: Array<DecisionMemoryNormRef>;
  status_events: Array<DecisionMemoryStatusEvent>;
  summary: DecisionMemoryCaseSummary;
};

export type DecisionMemoryCaseId = string;

/** The contract pattern for `DecisionMemoryCaseId`. Anchored; use with `new RegExp()`. */
export const DECISION_MEMORY_CASE_ID_PATTERN = "^dmc_[0-9A-HJKMNP-TV-Z]{26}$";

export type DecisionMemoryCasePage = {
  items: Array<DecisionMemoryCaseSummary>;
  page: PageInfo;
};

/** One case as the list gives it: where it stands (``status``), the verdict of its latest decision and how many decisions it holds. */
export type DecisionMemoryCaseSummary = {
  captured_at: string;
  case_id: DecisionMemoryCaseId;
  category: string;
  crop_state: "referenced" | "none_available";
  current_decided_at: string | null;
  current_origin_kind: "direct" | "carried" | "imported" | null;
  current_severity: Severity | null;
  current_verdict: "accepted" | "rejected" | null;
  data_class: "test" | "real";
  decision_count: number;
  origin_project_uid: ProjectUid;
  section_code: string | null;
  status: "active" | "withdrawn" | "forgotten";
  status_changed_at: string | null;
  status_reason_code: "capture_defect" | "wrong_decision" | "client_request" | "test_data" | "other" | null;
};

/** What the model proposed, as it stood when the decision was taken (immutable, a primary record from capture). */
export type DecisionMemoryContent = {
  analysis_profile_id: AnalysisProfileId;
  finding_text: string;
  proposed_severity: Severity | null;
  provider_mode: "live" | "recorded";
  recommendation_text: string;
  required_value: string | null;
  stage_id: string;
  stated_value: string | null;
};

export type DecisionMemoryCountRow = {
  cases: number;
  data_class: "test" | "real";
  status: "active" | "withdrawn" | "forgotten";
};

/** A crop image the case references (a binding to an existing Blob, never a copy); ``bbox`` is the normalised box on the page. */
export type DecisionMemoryCrop = {
  bbox: Array<number>;
  crop_id: string;
  crop_ordinal: number;
  evidence_ordinal: number | null;
  height_px: number;
  media_type: "image/png";
  page_number: number;
  portal_description: string | null;
  selection_rule: string;
  sha256: string;
  size_bytes: number;
  width_px: number;
};

/** One captured decision. ``comment`` is the expert's own words, ``null`` for a carried decision and for a forgotten case. */
export type DecisionMemoryDecision = {
  comment: string | null;
  decided_at: string;
  event_type: "accept" | "reject";
  memory_decision_id: string;
  origin_kind: "direct" | "carried" | "imported";
  severity: Severity | null;
  verdict: "accepted" | "rejected";
};

/** A quoted span the expert looked at. ``bbox`` is ``[x0, y0, x1, y1]`` in ``bbox_unit`` from ``bbox_origin`` when the block was known. */
export type DecisionMemoryEvidence = {
  bbox: Array<number> | null;
  bbox_origin: string | null;
  bbox_unit: string | null;
  block_ref: string | null;
  char_end: number;
  char_start: number;
  ordinal: number;
  page_number: number;
  quote: string;
};

/** A certified normative reference the finding rested on (ids that stay resolvable, and the quoted norm text). */
export type DecisionMemoryNormRef = {
  citation_state: "verified" | "rebound";
  clause_number: string | null;
  designation: string;
  norm_document_id: NormDocumentId;
  norm_paragraph_id: NormParagraphId;
  ordinal: number;
  page_label: number;
  quote: string;
};

/** What the memory holds and the installation settings in force (nothing journalled means ``test`` and ``off``). */
export type DecisionMemoryStatus = {
  by_status_and_class: Array<DecisionMemoryCountRow>;
  cases: number;
  data_class: "test" | "real";
  decisions: number;
  training_use: "off" | "on";
};

/** What a withdraw or a restore did: the status event written (or, for a replay, the first call's) and the standing after it. */
export type DecisionMemoryStatusChange = {
  case_id: DecisionMemoryCaseId;
  changed_at: string;
  kind: "withdraw" | "restore";
  reason_code: "capture_defect" | "wrong_decision" | "client_request" | "test_data" | "other";
  status: "active" | "withdrawn";
  status_event_id: string;
};

/** Why a case is withdrawn or restored: a closed reason (free text would put personal data into an append-only record). */
export type DecisionMemoryStatusChangeRequest = {
  reason_code: "capture_defect" | "wrong_decision" | "client_request" | "test_data" | "other";
};

/** One change of standing, newest last. A ``forget`` carries the digest of the content that was forgotten, never the content. */
export type DecisionMemoryStatusEvent = {
  created_at: string;
  forgotten_content_sha256: string | null;
  kind: "withdraw" | "restore" | "forget";
  reason_code: "capture_defect" | "wrong_decision" | "client_request" | "test_data" | "other";
  status_event_id: string;
};

/** One event of the decision journal, with the finding context it was recorded against. A rebuildable projection and never a source of truth: every property here is derived from `expert_decision_event`, `finding`, `finding_observation` and the `finding_current_verdict` projection, and nothing is stored in this shape. It restates `DecisionEvent`'s properties rather than composing them with `allOf`, for the reason `FindingDetail` states: under JSON Schema 2020-12 an `additionalProperties: false` is evaluated against its own schema object's property annotations only, so an `allOf` branch over the closed `DecisionEvent` would reject the properties the sibling branch adds. `document_uid`, `version_uid`, `project_name` and `document_name` say where the decision belongs; the two names are joined at read time from the project and the document and are stored nowhere. `section` is the expert-confirmed section of the finding's version and is absent while that version is unclassified (`UI-PARITY-P0A`). `carried_from` (`UI-A-73`) is as on `DecisionEvent`. */
export type DecisionRecord = {
  /** OD-12, as `R-37` now defines it: the display name of the reviewer who recorded the event -- the name they chose, or their login when they have chosen none -- derived server-side from the authenticated credential and **never** taken from a request body. It IS a subject identity: it names which reviewer judged, which is what `P04` needs and what one configured label for every reviewer could not give it. It still authorizes nothing: it is what the ledger records about who judged, not a permission anybody holds, and no client can choose it. The ledger is append-only, so an event keeps the label it was written with even after that reviewer is renamed. */
  author_label: string;
  carried_from?: DecisionCarriedFrom;
  category: FindingCategory;
  comment?: string | null;
  current_verdict: Verdict;
  /** How many events the ledger holds for this finding, including this one. A count greater than one means the expert returned to the finding. */
  decision_event_count: number;
  decision_id: DecisionId;
  document_name: string;
  document_uid: DocumentUid;
  event_type: DecisionEventType;
  finding_observation_id: FindingObservationId;
  /** The observation's own words, as `FindingObservation.finding_text` carries them. It is the analysis's text and not this API's prose, so it is in whatever language the analysis produced. */
  finding_text: string;
  finding_uid: FindingUid;
  project_name: string;
  project_uid: ProjectUid;
  recorded_at: string;
  run_id: RunId;
  section?: ProjectSection;
  severity?: Severity;
  /** The verdict this event carries, or null for a comment. */
  verdict?: Verdict | null;
  version_uid: VersionUid;
};

export type DecisionRecordPage = {
  items: Array<DecisionRecord>;
  page: PageInfo;
  /** The number of decision-journal entries that match the filters, on every page of the listing -- not the number of items on this page. */
  total: number;
};

/**
 * One span of a raw line diff; 0-based line indices, end exclusive. An ``equal`` span
 * carries its ranges and no lines.
 */
export type DiffHunk = {
  source_end: number;
  source_lines: Array<string>;
  source_start: number;
  tag: "equal" | "insert" | "delete" | "replace";
  target_end: number;
  target_lines: Array<string>;
  target_start: number;
};

/**
 * `UI-A-47` (contract 1.40.0): the run of a version that is in flight -- admitted and not yet terminal.
 *
 * `state` is `queued` (waiting for an executor), `running` or `validating`; a `created` run has not been admitted and a terminal run is not active. No progress figure is carried: the run reports its stages, and a figure of «пакет n/m» would need a plan of its own (`D-345`).
 */
export type DocumentActiveRun = {
  run_id: RunId;
  state: "queued" | "running" | "validating";
};

/**
 * The audit of one version, as `listDocuments` shows it on each document (`UI-PARITY-DOC-AUDIT`, `UI-A-46`).
 *
 * The per-document form of the counters of `DocumentAuditCounts`, read by the same rules (`R-150n`, `R-150p`,
 * `R-150r`, `R-150s`, `R-150t`): the version's **result run** is its latest run in state `published` or `partial`,
 * ordered by `(created_at, run_id)` as `listRuns` orders them. A newer run still in flight does not displace it,
 * and a `failed` or `cancelled` run is not a result.
 *
 * `state` is one of four words. `not_run`: no result run (never run, run only to `failed` or `cancelled`, or only
 * in flight); there is then no `result_run_id`, and a failed or cancelled latest run does not change that, so the
 * chip «отказ» (`R-150r`) is a marking of the screen's own and not a fifth state. `clean`: a result run that
 * published no finding, a state of its own (`R-150n`). `awaiting_decision`: a result run with at least one finding
 * whose current verdict is undecided (`pending` or `needs_manual_review`). `checked`: a result run, every finding
 * decided. `partial` is not a fifth state: it is true when the result run is `partial` and marks the document in
 * any of the four states (`R-150s`).
 *
 * `finding_count` is the number of published findings of the result run and `undecided_finding_count` the number of
 * those still undecided; both are zero when there is no result run. Optimisation proposals are not part of any
 * figure (`R-150u`).
 *
 * `active_run` (`UI-A-47`, contract 1.40.0) names the version's run in flight -- its latest run of the standard analysis in state `queued`, `running` or `validating`, by the order of the result run -- and is absent when none is. It is a fact beside the four words and changes none of them: a document whose first run is in flight is still `not_run`, and a `checked` one with a re-run in flight is still `checked`.
 *
 * `optimisation_proposal_count` and `optimisation_undecided_count` (`D-361`, contract 1.43.0) are the proposals of the version's latest optimisation pass and how many of them have no decision in force (none, or a withdrawn one) -- the original's «Оптимизация N» pill. Both are present when a pass was started over the version and both are absent when none was: absent is "no optimisation read", never zero. They are a fact beside the four words and change none of them (`R-150u`).
 */
export type DocumentAudit = {
  active_run?: DocumentActiveRun;
  finding_count: number;
  optimisation_proposal_count?: number;
  optimisation_undecided_count?: number;
  partial: boolean;
  result_run_id?: RunId;
  state: "not_run" | "clean" | "awaiting_decision" | "checked";
  undecided_finding_count: number;
};

/** The audit-state counters of a set of documents (`UI-PARITY-P0B`, `R-150n` ... `R-150u`). Every figure counts documents by their **current version only** (`R-150p`) and reads that version's **result run**: its latest run in state `published` or `partial`, ordered by `(created_at, run_id)` as `listRuns` orders them; a newer run still in flight does not displace it, and a `failed` or `cancelled` run is not a result (`R-150r`). Optimisation proposals are not part of any state (`R-150u`). A document is in exactly one of four states, so `document_count` is `not_run + clean + awaiting_decision + checked`. `partial` is not a fifth state: it counts the documents, in any of the four, whose result run is `partial` (`R-150s`). */
export type DocumentAuditCounts = {
  /** Documents with a result run and at least one finding whose current verdict is undecided (`pending` or `needs_manual_review`). The red badge «ждут решения» (`R-150o`). */
  awaiting_decision: number;
  /** Documents with a result run in which every finding is decided. */
  checked: number;
  /** Documents with a result run that published no finding. A state of its own: neither checked nor awaiting a decision (`R-150n`). */
  clean: number;
  /** Documents with a current version. */
  document_count: number;
  /** `not_run + awaiting_decision`: the original's column «Нет решений эксперта». Everything not closed, documents never run included, but not `clean` (`R-150o`). */
  no_expert_decision: number;
  /** Documents whose current version has no result run: never run, run only to `failed` or `cancelled`, or only in flight (`R-150r`). */
  not_run: number;
  /** Documents, in any of the four states, whose result run is `partial` (`R-150s`). */
  partial: number;
};

/** `R-151e`: one tag of a project's documents in use, and how many documents carry it. */
export type DocumentTagCount = {
  document_count: number;
  tag: string;
};

/** `R-151e`: the project's tag catalogue, in case-insensitive order; archived documents are not counted. */
export type DocumentTagList = {
  items: Array<DocumentTagCount>;
};

export type DocumentUid = string;

/** The contract pattern for `DocumentUid`. Anchored; use with `new RegExp()`. */
export const DOCUMENT_UID_PATTERN = "^doc_[0-9A-HJKMNP-TV-Z]{26}$";

export type DocumentVersion = {
  /** `R-151a` (contract 1.22.0): when the document was archived; absent while it is in use. */
  archived_at?: string;
  audit?: DocumentAudit;
  byte_size: number;
  classification?: VersionClassification;
  display_title?: string;
  document_uid: DocumentUid;
  input_manifest: Array<InputManifestEntry>;
  media_type: "application/pdf";
  page_count: number;
  project_uid: ProjectUid;
  published_at: string;
  section?: ProjectSection;
  sha256: Sha256;
  source_filename?: string | null;
  /** `R-151e` (contract 1.23.0): the document's free tags, on the reads that carry them (`listDocuments`, `listVersions` and the document commands). */
  tags?: Array<string>;
  upload_kind?: VersionUploadKind;
  version_ordinal: number;
  version_uid: VersionUid;
};

export type DocumentVersionPage = {
  items: Array<DocumentVersion>;
  page: PageInfo;
};

/** All fifteen sections' vendor lists as they apply to one project, in section order. */
export type EffectiveVendorLists = {
  items: Array<SectionVendorList>;
  project_uid: ProjectUid;
};

export type EngineerAbsenceChange = {
  absent: boolean;
  day: string;
};

/**
 * «Запустить выбранные по очереди» / «Поставить в очередь». The ``upload`` step cannot be queued
 * (``422 validation_failed``, ``comparison_step_not_queueable``). ``restart`` is «Заново» for the
 * ``series`` and ``ai_changes`` steps.
 */
export type EnqueueComparisonLaunchRequest = {
  items: Array<ComparisonLaunchItem>;
  restart?: boolean;
};

/** Exactly the key set of contracts/domain/v1/error-codes.json. */
export const ERROR_CODE_VALUES = [
  'validation_failed',
  'not_found',
  'authentication_required',
  'permission_denied',
  'conflict',
  'state_transition_not_allowed',
  'idempotency_key_reuse',
  'idempotency_key_in_progress',
  'idempotency_key_stale',
  'unsupported_contract_version',
  'storage_integrity_error',
  'dependency_unavailable',
  'dependency_credential_refused',
  'staged_upload_lost',
  'required_norm_unavailable',
  'version_classification_required',
  'section_profile_unavailable',
  'analysis_input_invalid',
  'analysis_failed',
  'partial_result_not_publishable',
  'cost_budget_exceeded',
  'analysis_input_budget_exceeded',
  'model_identity_mismatch',
  'stale_attempt',
  'execution_token_invalid',
  'rate_limited',
  'internal_error',
] as const;

/** ErrorCode - the closed value set above. */
export type ErrorCode = (typeof ERROR_CODE_VALUES)[number];

/** The one failure shape. Rendered by ``envelope_response`` and by nothing else. */
export type ErrorEnvelope = {
  contract_version: "1.50.0";
  correlation_id: CorrelationId;
  details?: {
    [key: string]: string | number | boolean | null;
  };
  error_code: ErrorCode;
  message: string;
  retryable: boolean;
};

/** One verified quotation. `char_start` and `char_end` index the document-global character sequence of the prepared text layer, counted in Unicode code points after the declared normalization - see docs/program/P02_SEAMS.md section 4. */
export type Evidence = {
  /** Secondary anchor into this version's block index. Not a contract identifier. */
  block_id?: string | null;
  char_end: number;
  char_start: number;
  evidence_ordinal: number;
  page_number: number;
  quote: string;
};

export type ExecutionDispatchStatus = {
  changed_at: string;
  paused: boolean;
};

export type ExecutionJournalEntry = {
  aggregate_id: string;
  aggregate_type: string;
  event_id: string;
  event_type: string;
  occurred_at: string;
  payload: {
    [key: string]: string | number | boolean | null;
  };
  run_id: RunId;
};

export type ExecutionJournalPage = {
  items: Array<ExecutionJournalEntry>;
  page: PageInfo;
};

/** `EXEC2-SEAL-2`: `binding_state` and `wait_reason` are present for a job whose Run was admitted by a rule or a group (`pending` while it waits for an executor). `UI-PARITY-QUEUE-A` (contract 1.18.0): the queue names what it lists. Every job executes exactly one audit run of one version of one document (`job.run_id` is not null and unique), so `project_uid`, `project_name`, `document_uid`, `document_name`, `version_uid` and `version_ordinal` are always present; the two names and the ordinal are joined at read time and stored nowhere. `started_at` is the creation time of the job's first attempt and is absent while no attempt exists; `finished_at` is the time the job reached a terminal state and is absent while it has not; `error_code` is the run's `terminal_reason` and `interrupted_reason` the run's own, each absent when the run records none. An absent property is omitted, never sent as null. */
export type ExecutionQueueItem = {
  attempt_count?: number;
  available_at: string;
  binding_state?: ExecutorBindingState;
  created_at: string;
  document_name: string;
  document_uid: DocumentUid;
  error_code?: ErrorCode;
  /** `R-151u` (contract 1.26.0): a running job's estimated finish -- its first attempt's start plus the median duration of at least three recent completed runs of the same analysis profile and a page count within a quarter of its own; absent without enough history or while the job is not running. Never invented. */
  estimated_finish_at?: string;
  finished_at?: string;
  interrupted_reason?: string;
  job_id: JobId;
  priority: number;
  project_name: string;
  project_uid: ProjectUid;
  queue_position?: number;
  run_id: RunId;
  started_at?: string;
  /** `R-151v` (contract 1.21.0): the display label of the account that started the run; absent for a run created before migration 0051. */
  started_by_label?: string;
  state: string;
  version_ordinal: number;
  version_uid: VersionUid;
  wait_reason?: RunQueueReason;
};

export type ExecutionQueuePage = {
  items: Array<ExecutionQueueItem>;
  /** `D-395` (contract 1.43.0): how many failed jobs (`failed` or `dead_letter`) nothing has answered yet -- those with no later job for a run of the same document version -- over all history, whatever the period or state filter of this page. The original's «ошибки» figure: a failure drops out by being retried or superseded, not by ageing. Independent of the filters, so a one-row page carries it too. */
  live_failure_count?: number;
  overview?: Array<ExecutionQueueStateCount>;
  page: PageInfo;
  paused: boolean;
};

/** `UI-PARITY-P0M` (contract 1.28.0): how many jobs stand in one state. */
export type ExecutionQueueStateCount = {
  count: number;
  state: "queued" | "leased" | "running" | "retry_wait" | "succeeded" | "failed" | "cancelled" | "dead_letter";
};

/** One row of the worker registry (`worker`, migration `0019_execution_workers`) and the runs it currently holds. `intake_enabled` false means it takes no new run. */
export type ExecutionWorker = {
  current_run_ids: Array<RunId>;
  heartbeat_at: string;
  intake_enabled: boolean;
  slots: number;
  started_at: string;
  state: WorkerState;
  version: string;
  worker_id: WorkerId;
};

export type ExecutionWorkerPage = {
  items: Array<ExecutionWorker>;
  page: PageInfo;
};

/**
 * One install session of the universal agent over SSH (path A, `EXEC2-SEAL-1`, ADR-0026 decision 7).
 * For `generated_key` access it carries the public half and its `authorized_keys` line, which the
 * administrator adds to the host; the private half is sealed and never returned.
 * `observed_host_key_fingerprint` is what the worker saw (derived from the stored key line, as
 * `ExecutorRevision.host_key_fingerprint` is); the install does not proceed until the administrator
 * confirms exactly that fingerprint. `key_removed_at` is when the stand's key was removed from the
 * host and its sealed secret destroyed.
 */
export type ExecutorAgentInstall = {
  access: ExecutorAgentInstallAccess;
  authorized_keys_line?: string;
  connection_id?: ExecutorConnectionId;
  created_at: string;
  created_by: UserUid;
  failure_reason?: ExecutorAgentInstallFailure;
  finished_at?: string;
  host_id?: ExecutorHostId;
  host_key_confirmed_at?: string;
  host_key_confirmed_by?: UserUid;
  install_id: ExecutorAgentInstallId;
  key_removed_at?: string;
  observed_host_key_fingerprint?: string;
  package_sha256?: string;
  package_version?: AgentPackageVersion;
  public_key?: string;
  ssh_host: string;
  ssh_port: number;
  ssh_user: string;
  state: ExecutorAgentInstallState;
  updated_at: string;
};

/** How the administrator gives the stand SSH access to the host: a key the stand generates (the administrator adds its public half to the host) or a pasted private key, which is sealed. Passwords are not accepted. */
export const EXECUTOR_AGENT_INSTALL_ACCESS_VALUES = [
  'generated_key',
  'pasted_key',
] as const;

/** ExecutorAgentInstallAccess - the closed value set above. */
export type ExecutorAgentInstallAccess = (typeof EXECUTOR_AGENT_INSTALL_ACCESS_VALUES)[number];

/** The sanitised reason a failed install failed; never a host output, a path or a credential. */
export const EXECUTOR_AGENT_INSTALL_FAILURE_VALUES = [
  'host_unreachable',
  'ssh_refused',
  'host_key_changed',
  'host_key_not_confirmed',
  'sudo_password_required',
  'unsupported_platform',
  'package_unavailable',
  'install_failed',
  'enrollment_failed',
  'secret_unreadable',
  'no_worker',
  'timed_out',
] as const;

/** ExecutorAgentInstallFailure - the closed value set above. */
export type ExecutorAgentInstallFailure = (typeof EXECUTOR_AGENT_INSTALL_FAILURE_VALUES)[number];

export type ExecutorAgentInstallId = string;

/** The contract pattern for `ExecutorAgentInstallId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_AGENT_INSTALL_ID_PATTERN = "^exai_[0-9A-HJKMNP-TV-Z]{26}$";

/** `requested -> scanning -> awaiting_host_key -> installing -> succeeded | failed`. */
export const EXECUTOR_AGENT_INSTALL_STATE_VALUES = [
  'requested',
  'scanning',
  'awaiting_host_key',
  'installing',
  'succeeded',
  'failed',
] as const;

/** ExecutorAgentInstallState - the closed value set above. */
export type ExecutorAgentInstallState = (typeof EXECUTOR_AGENT_INSTALL_STATE_VALUES)[number];

/** ExecutorApiFlavour. */
export const EXECUTOR_API_FLAVOUR_VALUES = [
  'openai_chat',
  'anthropic_messages',
] as const;

/** ExecutorApiFlavour - the closed value set above. */
export type ExecutorApiFlavour = (typeof EXECUTOR_API_FLAVOUR_VALUES)[number];

/** ExecutorBilling. */
export const EXECUTOR_BILLING_VALUES = [
  'metered',
  'not_metered',
] as const;

/** ExecutorBilling - the closed value set above. */
export type ExecutorBilling = (typeof EXECUTOR_BILLING_VALUES)[number];

/** The connection and model work was bound to at dispatch (`EXEC2-SEAL-2`, ADR-0026 decision 14). Present exactly when `binding_state` is `bound`. It never changes afterwards: an Attempt retry stays on this connection revision. */
export type ExecutorBinding = {
  connection_id: ExecutorConnectionId;
  connection_revision_id: ExecutorRevisionId;
  display_name: string;
  gateway_model: string;
  pin_id: string;
};

/** `EXEC2-SEAL-2` (ADR-0026 decision 12): whether the executor of a Run or a comparison AI job was fixed when the work started. `frozen_at_start`: the connection revision was frozen at start (every existing row, an explicit connection and a preset), behaviour unchanged. `pending`: the work was admitted by a rule or a group and no connection is chosen yet. `bound`: dispatch chose a member and wrote the connection revision. The only move is `pending` to `bound`, once; `frozen_at_start` and `bound` are terminal. */
export const EXECUTOR_BINDING_STATE_VALUES = [
  'frozen_at_start',
  'pending',
  'bound',
] as const;

/** ExecutorBindingState - the closed value set above. */
export type ExecutorBindingState = (typeof EXECUTOR_BINDING_STATE_VALUES)[number];

/** A connection: where a process sends model work. Its secrets are metadata only. `occupancy` (`EXEC2-SEAL-1`) is present once the connection has a current revision; `integration_authorisation` is present while the administrator's mark is set (`pull` connections only). */
export type ExecutorConnection = {
  archived_at?: string;
  connection_id: ExecutorConnectionId;
  created_at: string;
  created_by: UserUid;
  current_revision_id?: ExecutorRevisionId;
  current_revision_no?: number;
  display_name: string;
  integration_authorisation?: ExecutorIntegrationAuthorisation;
  kind: ExecutorKind;
  occupancy?: ExecutorOccupancy;
  routed_work_kinds: Array<ExecutorWorkKind>;
  secrets: Array<ExecutorSecretMetadata>;
};

/**
 * One connection with every revision (each with its latest probe) and its last 10 probes.
 *
 * For a ``pull`` connection (`EXEC-PULL-01`) it also carries the runner tokens' metadata and
 * the number of tasks waiting for, or held by, a runner right now. Both are absent for the
 * other kinds. A token's value is never here: it was shown once, when it was issued.
 *
 * `EXEC2-SEAL-1` (ADR-0026 decision 4): for a ``pull`` connection it also carries its last 10 enrollment grants, newest first, as metadata only (state, expiry, redemption time): the grant's secret and its hash are never here, since the secret was shown once, when it was issued. Absent for the other kinds.
 */
export type ExecutorConnectionDetail = {
  connection: ExecutorConnection;
  enrollments?: Array<ExecutorEnrollmentMetadata>;
  open_task_count?: number;
  probes: Array<ExecutorProbe>;
  revisions: Array<ExecutorRevision>;
  runner_tokens?: Array<RunnerTokenMetadata>;
};

export type ExecutorConnectionId = string;

/** The contract pattern for `ExecutorConnectionId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_CONNECTION_ID_PATTERN = "^exc_[0-9A-HJKMNP-TV-Z]{26}$";

export type ExecutorConnectionList = {
  items: Array<ExecutorConnection>;
  pinned_models: Array<ExecutorPinnedModel>;
};

export type ExecutorEnrollmentId = string;

/** The contract pattern for `ExecutorEnrollmentId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_ENROLLMENT_ID_PATTERN = "^exen_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * What the API ever says about an enrollment grant after it was issued (`EXEC2-SEAL-1`, ADR-0026
 * decision 4): that it exists, its non-secret prefix, its derived state and its dates. The secret and
 * its hash are never returned.
 */
export type ExecutorEnrollmentMetadata = {
  connection_id?: ExecutorConnectionId;
  created_at: string;
  created_by: UserUid;
  enrollment_id: ExecutorEnrollmentId;
  expires_at: string;
  host_id?: ExecutorHostId;
  redeemed_at?: string;
  revoked_at?: string;
  revoked_by?: UserUid;
  runner_token_id?: ExecutorRunnerTokenId;
  secret_prefix: string;
  state: ExecutorEnrollmentState;
};

/** Derived at read time: `pending` until redeemed, revoked or past `expires_at`. */
export const EXECUTOR_ENROLLMENT_STATE_VALUES = [
  'pending',
  'redeemed',
  'expired',
  'revoked',
] as const;

/** ExecutorEnrollmentState - the closed value set above. */
export type ExecutorEnrollmentState = (typeof EXECUTOR_ENROLLMENT_STATE_VALUES)[number];

/** A group of interchangeable executors for one model (`EXEC2-SEAL-2`, ADR-0026 decision 10), with its current revision. `routed_work_kinds` are the work kinds whose rule currently targets a revision of this group; a group a rule still names cannot be archived. Archiving is one-way and is not deletion. */
export type ExecutorGroup = {
  archived_at?: string;
  created_at: string;
  created_by: UserUid;
  current_revision: ExecutorGroupRevision;
  display_name: string;
  group_id: ExecutorGroupId;
  routed_work_kinds: Array<ExecutorWorkKind>;
};

/** The capacity of the current revision of a group, derived from the database at read time and stored nowhere (`EXEC2-SEAL-2`). `capacity` sums the capacity of the members still in service (not archived, current revision equal to the snapshot); `used` sums their active Runs and calls; `waiting` counts the Runs and comparison jobs admitted on any revision of this group that are still `pending`. */
export type ExecutorGroupCapacity = {
  capacity: number;
  group_id: ExecutorGroupId;
  group_revision_id: ExecutorGroupRevisionId;
  members: Array<ExecutorGroupMemberStatus>;
  used: number;
  waiting: number;
};

/** One group and every revision of it, newest first. */
export type ExecutorGroupDetail = {
  group: ExecutorGroup;
  revisions: Array<ExecutorGroupRevision>;
};

export type ExecutorGroupId = string;

/** The contract pattern for `ExecutorGroupId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_GROUP_ID_PATTERN = "^exg_[0-9A-HJKMNP-TV-Z]{26}$";

/** Every executor group with its current revision, archived ones included. */
export type ExecutorGroupList = {
  items: Array<ExecutorGroup>;
};

/** One member of a group revision (`EXEC2-SEAL-2`, ADR-0026 decision 10): a connection and the connection **revision** snapshotted into the group revision. Dispatch considers the member only while the connection's current revision is still this snapshot. `tie_break_order` (1 to 16, unique inside the revision) orders members that tie on load before the persisted rotation does. */
export type ExecutorGroupMember = {
  connection_id: ExecutorConnectionId;
  connection_revision_id: ExecutorRevisionId;
  tie_break_order?: number;
};

/**
 * `EXEC2-SEAL-2` (ADR-0026 decision 14): why a group member would not be chosen by dispatch right now.
 * `revision_changed`: the connection's current revision is not the snapshot the group revision holds.
 * `connection_archived`: the connection is archived. `not_served`: this release does not serve the
 * connection. `probe_not_ok`: the probe of the current key is not `ok`. `runner_offline`: a `pull`
 * connection has no runner online. `at_capacity`: every unit of the connection is in use. `HOSTS-SEAL-1` (ADR-0028):
 * `host_disabled`: the member's host is switched off. `model_not_verified`: the agent of the host has not reported the
 * model as verified. `model_cooling_down`: the host took the model out of availability after a real refusal.
 */
export const EXECUTOR_GROUP_MEMBER_ISSUE_VALUES = [
  'revision_changed',
  'connection_archived',
  'not_served',
  'probe_not_ok',
  'runner_offline',
  'at_capacity',
  'host_disabled',
  'model_not_verified',
  'model_cooling_down',
] as const;

/** ExecutorGroupMemberIssue - the closed value set above. */
export type ExecutorGroupMemberIssue = (typeof EXECUTOR_GROUP_MEMBER_ISSUE_VALUES)[number];

/** One member as dispatch sees it right now (`EXEC2-SEAL-2`, ADR-0026 decision 14), derived at read time: the snapshot, the connection's current revision, its occupancy, and whether it would be chosen. `ineligible_reason` is present exactly when `eligible` is false; when several apply the first of the enumeration's order is reported. */
export type ExecutorGroupMemberStatus = {
  connection_id: ExecutorConnectionId;
  current_revision_id?: ExecutorRevisionId;
  eligible: boolean;
  ineligible_reason?: ExecutorGroupMemberIssue;
  occupancy?: ExecutorOccupancy;
  snapshot_revision_id: ExecutorRevisionId;
};

/** What admission froze for a Run or a comparison AI job admitted by a rule or a group (`EXEC2-SEAL-2`, ADR-0026 decision 13): the group and its revision, the rule revision when a rule routed it (absent when the group was named explicitly), and the planned model with its billing. The connection is not here: it is chosen at dispatch (see `ExecutorBinding`). */
export type ExecutorGroupPlan = {
  billing: ExecutorBilling;
  executor_group_id: ExecutorGroupId;
  executor_group_revision_id: ExecutorGroupRevisionId;
  gateway_model: string;
  pin_id: string;
  routing_rule_revision_id?: ExecutorRoutingRuleRevisionId;
};

/** One immutable revision of an executor group (`EXEC2-SEAL-2`, ADR-0026 decision 10). A group is homogeneous: every member revision pins exactly `pin_id` and `gateway_model` and shares `billing` and the pinned rates, which are snapshotted here as USD per million tokens. `strategy` is `least_loaded`. Mixed groups are refused. */
export type ExecutorGroupRevision = {
  billing: ExecutorBilling;
  created_at: string;
  created_by: UserUid;
  gateway_model: string;
  group_id: ExecutorGroupId;
  group_revision_id: ExecutorGroupRevisionId;
  input_per_mtok_usd: number;
  members: Array<ExecutorGroupMember>;
  output_per_mtok_usd: number;
  pin_id: string;
  revision_no: number;
  strategy: ExecutorGroupStrategy;
};

export type ExecutorGroupRevisionId = string;

/** The contract pattern for `ExecutorGroupRevisionId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_GROUP_REVISION_ID_PATTERN = "^exgr_[0-9A-HJKMNP-TV-Z]{26}$";

/** `EXEC2-SEAL-2` (ADR-0026 decision 10): how dispatch picks among the eligible members of a group. `least_loaded`: the lowest used/capacity ratio, ties broken by a rotation kept in the database. */
export const EXECUTOR_GROUP_STRATEGY_VALUES = [
  'least_loaded',
] as const;

/** ExecutorGroupStrategy - the closed value set above. */
export type ExecutorGroupStrategy = (typeof EXECUTOR_GROUP_STRATEGY_VALUES)[number];

/**
 * A server (ADR-0028): its name, the «Использовать» switch, whether it is on line, the models it can serve now and its slots.
 * `models` holds only what can be used (an unavailable model is not listed); the reasons are in `ExecutorHostDetails`.
 */
export type ExecutorHost = {
  agent_version?: string;
  archived_at?: string;
  created_at: string;
  created_by: UserUid;
  display_name: string;
  enabled: boolean;
  host_id: ExecutorHostId;
  last_seen_at?: string;
  models: Array<ExecutorHostModel>;
  slots_in_use: number;
  slots_total: number;
  state: ExecutorHostState;
};

/**
 * «Подробнее» of a server (administrator): its slots, each provider with the reasons its models cannot be used, and the
 * tasks running on it.
 */
export type ExecutorHostDetails = {
  host: ExecutorHost;
  providers: Array<ExecutorHostProviderDetail>;
  slots: Array<ExecutorHostSlotUse>;
  tasks: Array<ExecutorHostTask>;
};

export type ExecutorHostId = string;

/** The contract pattern for `ExecutorHostId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_HOST_ID_PATTERN = "^exh_[0-9A-HJKMNP-TV-Z]{26}$";

/** The servers, newest first, with the summary line of the screen: servers on line of all, free slots of all. */
export type ExecutorHostList = {
  items: Array<ExecutorHost>;
  online: number;
  slots_free: number;
  slots_total: number;
  total: number;
};

/** A model the host can serve now: `available` or, with every slot of its provider in use, `busy`. */
export type ExecutorHostModel = {
  access: ExecutorModelAccess;
  model_id: string;
  provider: ExecutorProvider;
  state: "available" | "busy";
};

/** One model of a provider on a host with the reasons it cannot be used, if it cannot (administrator's view). */
export type ExecutorHostModelStatus = {
  cooldown_until?: string;
  model_id: string;
  reasons: Array<ModelUnavailableReason>;
  state: "available" | "busy" | "unavailable";
};

/** A provider found on the host: its access, its login, its client version and its models. */
export type ExecutorHostProviderDetail = {
  access: ExecutorModelAccess;
  auth_state: ProviderAuthState;
  cli_version?: string;
  models: Array<ExecutorHostModelStatus>;
  provider: ExecutorProvider;
};

/** The slots of a provider on a host: how many may run at once and how many do. */
export type ExecutorHostSlotUse = {
  access: ExecutorModelAccess;
  in_use: number;
  provider: ExecutorProvider;
  slots: number;
};

/**
 * How many calls of a provider the host may run at once (1 to 16). A provider that is absent has its default: 1 for a
 * subscription, 2 for an API key.
 */
export type ExecutorHostSlots = {
  anthropic_api?: number;
  claude_code?: number;
  codex?: number;
  openai_api?: number;
  openrouter_api?: number;
};

/**
 * `online`: the agent reported within the last 120 seconds and a free slot exists. `busy`: online, every slot is in use.
 * `offline`: no report within the last 120 seconds (or never).
 */
export const EXECUTOR_HOST_STATE_VALUES = [
  'online',
  'busy',
  'offline',
] as const;

/** ExecutorHostState - the closed value set above. */
export type ExecutorHostState = (typeof EXECUTOR_HOST_STATE_VALUES)[number];

/** A call running on the host now: the run, the stage and since when. */
export type ExecutorHostTask = {
  model_id: string;
  provider: ExecutorProvider;
  run_id: RunId;
  since: string;
  stage_key?: string;
  task_id: ExecutorTaskId;
};

/** ``reported``: the response named the model. ``declared``: the executor asserted it. */
export const EXECUTOR_IDENTITY_BASIS_VALUES = [
  'reported',
  'declared',
] as const;

/** ExecutorIdentityBasis - the closed value set above. */
export type ExecutorIdentityBasis = (typeof EXECUTOR_IDENTITY_BASIS_VALUES)[number];

/** The administrator's mark that the command-line clients behind a `pull` connection are authorised for this integration (`R-149b`, ADR-0026 decision 8): when it was set and by whom. It is one of four distinct statuses (installed, authentication valid, authorised for this integration, model probe passed) and implies none of the other three. */
export type ExecutorIntegrationAuthorisation = {
  authorised_at: string;
  authorised_by: UserUid;
};

/**
 * How a connection reaches the model: the stand calls an HTTP API, the stand runs a
 * command over SSH, or a remote runner pulls the stand's tasks.
 */
export const EXECUTOR_KIND_VALUES = [
  'http_api',
  'ssh_command',
  'pull',
] as const;

/** ExecutorKind - the closed value set above. */
export type ExecutorKind = (typeof EXECUTOR_KIND_VALUES)[number];

/** How a call is paid: `subscription` (an account, not metered) or `api` (an API key, billed per token). */
export const EXECUTOR_MODEL_ACCESS_VALUES = [
  'subscription',
  'api',
] as const;

/** ExecutorModelAccess - the closed value set above. */
export type ExecutorModelAccess = (typeof EXECUTOR_MODEL_ACCESS_VALUES)[number];

/** Used and total capacity of a connection (`EXEC2-SEAL-1`, ADR-0026 decision 1), derived from the database at read time and stored nowhere. `capacity` is `max_active_runs` of the current revision (1 when absent); `active_runs` counts the connection's Runs in `leased`, `running` or `retry_wait`; `active_calls` counts its comparison model calls in `prepared` or `sent` whose attempt is live. Each counts one unit, so the connection is full when their sum reaches `capacity`. */
export type ExecutorOccupancy = {
  active_calls: number;
  active_runs: number;
  capacity: number;
};

/**
 * One model of the provider lock a revision may name, with its pinned rates (USD per
 * million tokens). The same list validates a revision, so the choice and the refusal agree.
 */
export type ExecutorPinnedModel = {
  input_per_mtok_usd: number;
  output_per_mtok_usd: number;
  pin_id: string;
};

/**
 * One probe of a connection revision. ``requested`` until the worker takes it; a probe
 * nobody takes within 120 seconds ends as ``no_worker``. ``detail`` is scrubbed and never a
 * response body.
 */
export type ExecutorProbe = {
  connection_id: ExecutorConnectionId;
  detail?: string;
  finished_at?: string;
  http_status?: number;
  identity_basis?: ExecutorIdentityBasis;
  latency_ms?: number;
  observed_host_key?: string;
  outcome?: ExecutorProbeOutcome;
  probe_id: ExecutorProbeId;
  rate_check?: ExecutorRateCheck;
  reported_model?: string;
  requested_at: string;
  requested_by: UserUid;
  revision_id: ExecutorRevisionId;
  secret_id?: ExecutorSecretId;
  started_at?: string;
  state: ExecutorProbeState;
};

export type ExecutorProbeId = string;

/** The contract pattern for `ExecutorProbeId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_PROBE_ID_PATTERN = "^epb_[0-9A-HJKMNP-TV-Z]{26}$";

/** ExecutorProbeOutcome. */
export const EXECUTOR_PROBE_OUTCOME_VALUES = [
  'ok',
  'ip_refused',
  'credential_refused',
  'model_mismatch',
  'rate_mismatch',
  'timeout',
  'unreachable',
  'protocol_error',
  'secret_unreadable',
  'host_key_unpinned',
  'host_key_changed',
  'no_runner_online',
  'destination_refused',
  'kind_not_served',
  'no_worker',
] as const;

/** ExecutorProbeOutcome - the closed value set above. */
export type ExecutorProbeOutcome = (typeof EXECUTOR_PROBE_OUTCOME_VALUES)[number];

/** ExecutorProbeState. */
export const EXECUTOR_PROBE_STATE_VALUES = [
  'requested',
  'running',
  'finished',
] as const;

/** ExecutorProbeState - the closed value set above. */
export type ExecutorProbeState = (typeof EXECUTOR_PROBE_STATE_VALUES)[number];

/**
 * Where a model answer comes from. `claude_code` and `codex` are the command-line clients installed on the host (logged in
 * with an account, or with an API key); `anthropic_api`, `openai_api` and `openrouter_api` are direct calls with a key from the
 * service key file of the host.
 */
export const EXECUTOR_PROVIDER_VALUES = [
  'claude_code',
  'codex',
  'anthropic_api',
  'openai_api',
  'openrouter_api',
] as const;

/** ExecutorProvider - the closed value set above. */
export type ExecutorProvider = (typeof EXECUTOR_PROVIDER_VALUES)[number];

/** ExecutorPullClient. */
export const EXECUTOR_PULL_CLIENT_VALUES = [
  'claude_code_session',
  'agent',
] as const;

/** ExecutorPullClient - the closed value set above. */
export type ExecutorPullClient = (typeof EXECUTOR_PULL_CLIENT_VALUES)[number];

/** ExecutorRateCheck. */
export const EXECUTOR_RATE_CHECK_VALUES = [
  'checked',
  'not_reported',
  'mismatch',
  'not_metered',
] as const;

/** ExecutorRateCheck - the closed value set above. */
export type ExecutorRateCheck = (typeof EXECUTOR_RATE_CHECK_VALUES)[number];

/**
 * One immutable revision of a connection, with its latest probe.
 *
 * `EXEC2-SEAL-1` (ADR-0026 decisions 1 and 2): `max_active_runs` (1 to 16, absent means 1) is the most units of this connection that may be in use at once, where a Run in `leased`, `running` or `retry_wait` and a comparison model call in `prepared` or `sent` each count one. A lowered value governs new claims only and never stops work in flight. The coupled limits are validated on the revision and refused as `422 validation_failed`: `max_claimed_tasks` of a `pull` connection and a set `max_parallel_calls` of an `http_api` connection must each be at least `max_active_runs` (field `max_claimed_tasks` or `max_parallel_calls`, constraint `below_max_active_runs`), and an `ssh_command` connection takes a value above one only once its wrappers isolate concurrent invocations (field `max_active_runs`, constraint `capacity_not_supported_for_kind`).
 */
export type ExecutorRevision = {
  allow_client_documents: boolean;
  answer_deadline_seconds?: number;
  api_flavour?: ExecutorApiFlavour;
  base_url?: string;
  billing: ExecutorBilling;
  connection_id: ExecutorConnectionId;
  created_at: string;
  created_by: UserUid;
  gateway_model: string;
  host_key?: string;
  host_key_fingerprint?: string;
  latest_probe?: ExecutorProbe;
  max_active_runs?: number;
  max_claimed_tasks?: number;
  max_parallel_calls?: number;
  pin_id: string;
  pull_client?: ExecutorPullClient;
  revision_id: ExecutorRevisionId;
  revision_no: number;
  ssh_host?: string;
  ssh_port?: number;
  ssh_profile?: ExecutorSshProfile;
  ssh_user?: string;
  timeout_seconds: number;
  transport?: ExecutorTransport;
};

export type ExecutorRevisionId = string;

/** The contract pattern for `ExecutorRevisionId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_REVISION_ID_PATTERN = "^excr_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * Which connection serves one kind of model work, with an optional standby that only an
 * administrator configures. The standby is never used implicitly.
 */
export type ExecutorRoute = {
  primary_connection_id: ExecutorConnectionId;
  set_at: string;
  set_by: UserUid;
  standby_connection_id?: ExecutorConnectionId;
  work_kind: ExecutorWorkKind;
};

export type ExecutorRouteList = {
  items: Array<ExecutorRoute>;
};

/** One confirmed line of a cut-over: the work kind and the name of the one-member group to create for it. */
export type ExecutorRoutingMappingEntry = {
  group_display_name: string;
  work_kind: ExecutorWorkKind;
};

/** `EXEC2-SEAL-2` (ADR-0026 decision 17): which store decides where new model work goes. `legacy` (the default): the Primary/Standby route of `setExecutorRoute`. `rules`: the rule of the work kind, targeting an executor group. Each change is journalled; work already admitted keeps its own routing. */
export const EXECUTOR_ROUTING_MODE_VALUES = [
  'legacy',
  'rules',
] as const;

/** ExecutorRoutingMode - the closed value set above. */
export type ExecutorRoutingMode = (typeof EXECUTOR_ROUTING_MODE_VALUES)[number];

export type ExecutorRoutingModeEventId = string;

/** The contract pattern for `ExecutorRoutingModeEventId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_ROUTING_MODE_EVENT_ID_PATTERN = "^exrm_[0-9A-HJKMNP-TV-Z]{26}$";

/** The routing mode after a change, the groups the change created (a cut-over's one-member groups; none for a rollback) and the rules now current. */
export type ExecutorRoutingModeResult = {
  groups: Array<ExecutorGroup>;
  routing_mode: ExecutorRoutingModeState;
  rules: Array<ExecutorRoutingRule>;
};

/** The routing mode and its last change (`EXEC2-SEAL-2`, ADR-0026 decision 17). Before the first change the mode is `legacy` and the other fields are absent. */
export type ExecutorRoutingModeState = {
  changed_at?: string;
  changed_by?: UserUid;
  mode: ExecutorRoutingMode;
  mode_event_id?: ExecutorRoutingModeEventId;
};

/** The proposed cut-over, computed from the legacy routes without writing anything (`EXEC2-SEAL-2`, ADR-0026 decision 17). `preview_digest` binds every item below; the confirmation carries it, and a confirmation whose digest is not the one now computed is `409 conflict` (`preview_stale`). */
export type ExecutorRoutingPreview = {
  items: Array<ExecutorRoutingPreviewItem>;
  preview_digest: Sha256;
  routing_mode: ExecutorRoutingModeState;
};

/** `EXEC2-SEAL-2`: why a legacy route cannot become a one-member group. `connection_archived`: the primary is archived. `no_revision`: it has no revision. `kind_not_served`: this release does not serve its kind. */
export const EXECUTOR_ROUTING_PREVIEW_ISSUE_VALUES = [
  'connection_archived',
  'no_revision',
  'kind_not_served',
] as const;

/** ExecutorRoutingPreviewIssue - the closed value set above. */
export type ExecutorRoutingPreviewIssue = (typeof EXECUTOR_ROUTING_PREVIEW_ISSUE_VALUES)[number];

/** What the cut-over would do with one work kind (`EXEC2-SEAL-2`, ADR-0026 decision 17): a one-member group made from the primary of the legacy route, named `proposed_group_name`. A standby is shown and never converted into a member. */
export type ExecutorRoutingPreviewItem = {
  billing?: ExecutorBilling;
  connection_revision_id?: ExecutorRevisionId;
  gateway_model?: string;
  incompatible_reason?: ExecutorRoutingPreviewIssue;
  pin_id?: string;
  primary_connection_id?: ExecutorConnectionId;
  proposed_group_name?: string;
  standby_connection_id?: ExecutorConnectionId;
  status: ExecutorRoutingPreviewStatus;
  work_kind: ExecutorWorkKind;
};

/** `EXEC2-SEAL-2` (ADR-0026 decision 17): what the cut-over would do with one work kind. `ready`: a one-member group can be made from the primary of the legacy route. `no_route`: the work kind has no legacy route, so it gets no rule. `incompatible`: the route exists but cannot become a group (see the reason). */
export const EXECUTOR_ROUTING_PREVIEW_STATUS_VALUES = [
  'ready',
  'no_route',
  'incompatible',
] as const;

/** ExecutorRoutingPreviewStatus - the closed value set above. */
export type ExecutorRoutingPreviewStatus = (typeof EXECUTOR_ROUTING_PREVIEW_STATUS_VALUES)[number];

/** The current rule of one work kind (`EXEC2-SEAL-2`, ADR-0026 decision 11): the group revision new work of that kind is admitted on while the routing mode is `rules`. Rules are append-only; `rule_revision_id` identifies this one. */
export type ExecutorRoutingRule = {
  group_id: ExecutorGroupId;
  group_revision_id: ExecutorGroupRevisionId;
  rule_revision_id: ExecutorRoutingRuleRevisionId;
  set_at: string;
  set_by: UserUid;
  work_kind: ExecutorWorkKind;
};

/** The current rule of each work kind that has one, and the current routing mode. */
export type ExecutorRoutingRuleList = {
  items: Array<ExecutorRoutingRule>;
  routing_mode: ExecutorRoutingModeState;
};

export type ExecutorRoutingRuleRevisionId = string;

/** The contract pattern for `ExecutorRoutingRuleRevisionId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_ROUTING_RULE_REVISION_ID_PATTERN = "^exrr_[0-9A-HJKMNP-TV-Z]{26}$";

export type ExecutorRunnerTokenId = string;

/** The contract pattern for `ExecutorRunnerTokenId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_RUNNER_TOKEN_ID_PATTERN = "^ern_[0-9A-HJKMNP-TV-Z]{26}$";

export type ExecutorSecretId = string;

/** The contract pattern for `ExecutorSecretId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_SECRET_ID_PATTERN = "^exs_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * What the API ever says about a secret: that it exists, for what, when and by whom, and
 * its last four characters. The value is write-only; no operation returns it.
 */
export type ExecutorSecretMetadata = {
  bound_to_current_revision: boolean;
  connection_id: ExecutorConnectionId;
  kid: string;
  last4: string;
  public_key?: string;
  purpose: ExecutorSecretPurpose;
  secret_id: ExecutorSecretId;
  set_at: string;
  set_by: UserUid;
};

/** ExecutorSecretPurpose. */
export const EXECUTOR_SECRET_PURPOSE_VALUES = [
  'api_key',
  'ssh_private_key',
] as const;

/** ExecutorSecretPurpose - the closed value set above. */
export type ExecutorSecretPurpose = (typeof EXECUTOR_SECRET_PURPOSE_VALUES)[number];

/**
 * A generated ed25519 pair: the private half is sealed to the connection's SSH endpoint
 * and never returned; the public half and its ``authorized_keys`` line are.
 */
export type ExecutorSshKey = {
  authorized_keys_line: string;
  public_key: string;
  sealed_private_key: ExecutorSecretMetadata;
};

/** ExecutorSshProfile. */
export const EXECUTOR_SSH_PROFILE_VALUES = [
  'claude_code_headless',
  'custom_command',
] as const;

/** ExecutorSshProfile - the closed value set above. */
export type ExecutorSshProfile = (typeof EXECUTOR_SSH_PROFILE_VALUES)[number];

export type ExecutorTaskAck = {
  state: ExecutorTaskState;
  task_id: ExecutorTaskId;
};

export type ExecutorTaskId = string;

/** The contract pattern for `ExecutorTaskId`. Anchored; use with `new RegExp()`. */
export const EXECUTOR_TASK_ID_PATTERN = "^ext_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * ``open -> claimed -> answered | failed``; ``expired`` and ``cancelled`` end an ``open`` or
 * ``claimed`` task. A claim whose lease lapses returns the task to ``open``.
 */
export const EXECUTOR_TASK_STATE_VALUES = [
  'open',
  'claimed',
  'answered',
  'failed',
  'expired',
  'cancelled',
] as const;

/** ExecutorTaskState - the closed value set above. */
export type ExecutorTaskState = (typeof EXECUTOR_TASK_STATE_VALUES)[number];

/** The token counts of the call that produced an answer, as the agent measured them. */
export type ExecutorTaskUsage = {
  input_tokens: number;
  output_tokens: number;
};

/** ExecutorTransport. */
export const EXECUTOR_TRANSPORT_VALUES = [
  'direct',
  'vpn',
  'ssh_tunnel',
] as const;

/** ExecutorTransport - the closed value set above. */
export type ExecutorTransport = (typeof EXECUTOR_TRANSPORT_VALUES)[number];

/**
 * The kind of model work a route serves: the one run stage that calls a model, and (`CMP-SEAL-C2`,
 * ADR-0025 decision 17) the four kinds of model work of the version comparison. Their images ride the
 * image channel of `CMP-EXEC-IMAGES-01`; ``comparison_stage_review`` joins with `CMP-SEAL-C4`.
 */
export const EXECUTOR_WORK_KIND_VALUES = [
  'text_analysis',
  'comparison_pair_check',
  'comparison_sheet_changes',
  'comparison_spec',
  'comparison_report',
  'comparison_stage_review',
] as const;

/** ExecutorWorkKind - the closed value set above. */
export type ExecutorWorkKind = (typeof EXECUTOR_WORK_KIND_VALUES)[number];

export type ExtendedExecutorTaskClaim = {
  claim_expires_at: string;
};

export type ExtendedRunReview = {
  result?: {
    [key: string]: unknown;
  } | null;
  run_id: RunId;
  status: "not_started" | "running" | "completed" | "partial" | "failed" | "unavailable";
};

/** A lower-case code, optionally followed by ``: `` and a short, payload-free detail. */
export type FailExecutorTaskRequest = {
  reason: string;
};

/** A published finding. Every listed finding is grounded: its quotations were verified present at their declared anchors. `current_verdict_carried_from` (`UI-A-73`, contract 1.39.0) names where the decision that carries `current_verdict` came from, when an expert carried it over from an earlier version's finding; it is absent when the verdict was decided directly, was withdrawn, or was carried before migration `0058`. A later verdict an expert gives the finding replaces it, and a comment leaves it standing. */
export type Finding = {
  category: FindingCategory;
  current_verdict: Verdict;
  current_verdict_carried_from?: DecisionCarriedFrom;
  decided_severity?: Severity;
  decision_recorded_at?: string | null;
  execution_status?: FindingExecutionStatus;
  /** `R-151g`: when the execution status was set. */
  execution_status_at?: string;
  finding_uid: FindingUid;
  latest_decision_id?: DecisionId | null;
  merged_observations?: Array<FindingObservation>;
  /** A certified v3 citation partition. An empty array means the CITE gate completed and persisted a checked count of zero; absence on v1/v2 means no certification, never zero. On Finding and FindingDetail this mirrors the canonical observation. */
  norm_citations?: Array<NormCitation>;
  observation: FindingObservation;
  project_uid: ProjectUid;
  /** Deterministically grounded normative requirement; absent for legacy and nonnormative observations. Mirrors the canonical observation. */
  required_value?: string;
  run_id: RunId;
  /** Document value grounded in the project evidence; absent for legacy and nonnormative observations. Mirrors the canonical observation. */
  stated_value?: string;
  version_uid: VersionUid;
};

/** `UI-PARITY-C6` (contract 1.41.0): the portal blocks that hold one finding's evidence. */
export type FindingBlockLink = {
  finding_uid: FindingUid;
  portal_block_ids: Array<PortalBlockId>;
};

/** Closed finding categories: seven prior categories and five v3 normative categories. */
export const FINDING_CATEGORY_VALUES = [
  'internal_contradiction',
  'explicit_placeholder',
  'dimensions',
  'layout',
  'facade',
  'roof',
  'documentation',
  'evacuation',
  'fire_safety',
  'accessibility',
  'insulation',
  'sound',
] as const;

/** FindingCategory - the closed value set above. */
export type FindingCategory = (typeof FINDING_CATEGORY_VALUES)[number];

export type FindingComparison = {
  carryover_candidates: Array<CarryoverCandidate>;
  proposals: Array<FindingMatchProposal>;
  source_finding_count: number;
  status: "compared" | "unavailable";
  target_finding_count: number;
  unavailable_reason: "findings_over_limit" | null;
};

/** One finding with its full current-verdict projection. Restates `Finding` rather than composing it with `allOf`: under JSON Schema 2020-12 an `additionalProperties: false` is evaluated against its own schema object's property annotations only, so an `allOf` branch over the closed `Finding` would reject the two properties the sibling branch adds. Both shapes stay closed, and tests/contract/api_v1 asserts this property set stays `Finding`'s plus exactly `latest_comment` and `decision_event_count`. `current_verdict_carried_from` (`UI-A-73`) is as on `Finding`. */
export type FindingDetail = {
  category: FindingCategory;
  current_verdict: Verdict;
  current_verdict_carried_from?: DecisionCarriedFrom;
  decided_severity?: Severity;
  decision_event_count?: number;
  decision_recorded_at?: string | null;
  execution_status?: FindingExecutionStatus;
  /** `R-151g`: when the execution status was set. */
  execution_status_at?: string;
  finding_uid: FindingUid;
  /** The comment of the most recent event carrying one, whatever its type. */
  latest_comment?: string | null;
  latest_decision_id?: DecisionId | null;
  merged_observations?: Array<FindingObservation>;
  /** A certified v3 citation partition. An empty array means the CITE gate completed and persisted a checked count of zero; absence on v1/v2 means no certification, never zero. On Finding and FindingDetail this mirrors the canonical observation. */
  norm_citations?: Array<NormCitation>;
  observation: FindingObservation;
  project_uid: ProjectUid;
  /** Deterministically grounded normative requirement; absent for legacy and nonnormative observations. Mirrors the canonical observation. */
  required_value?: string;
  run_id: RunId;
  /** Document value grounded in the project evidence; absent for legacy and nonnormative observations. Mirrors the canonical observation. */
  stated_value?: string;
  version_uid: VersionUid;
};

/** `R-151g`: a finding's execution status after the command; `status` and `set_at` are absent when it has none. */
export type FindingExecutionState = {
  finding_uid: FindingUid;
  set_at?: string;
  status?: FindingExecutionStatus;
};

/** `R-151g` (contract 1.24.0): what the designer did with an accepted finding, the original's SU-10 labels: `taken_into_account` «Учтено», `amended` «Внесено», `declined` «Отклонено», `agreed` «По согласованию». Not an expert decision. */
export const FINDING_EXECUTION_STATUS_VALUES = [
  'taken_into_account',
  'amended',
  'declined',
  'agreed',
] as const;

/** FindingExecutionStatus - the closed value set above. */
export type FindingExecutionStatus = (typeof FINDING_EXECUTION_STATUS_VALUES)[number];

/** A proposed label for a finding of either run; never a decision or a carryover. */
export type FindingMatchProposal = {
  basis: "exact_issue_and_quotes" | "quotes_absent_from_paired_sheets" | "quote_still_on_paired_sheet" | "evidence_sheet_unpaired" | "evidence_over_limit" | "no_exact_source_match";
  kind: "unchanged" | "probably_fixed" | "undetermined" | "new";
  proposal_sha256: Sha256 | null;
  source_finding: FindingRef | null;
  target_finding: FindingRef | null;
};

export type FindingObservation = {
  category: FindingCategory;
  evidence: Array<Evidence>;
  finding_observation_id: FindingObservationId;
  finding_text: string;
  /** A certified v3 citation partition. An empty array means the CITE gate completed and persisted a checked count of zero; absence on v1/v2 means no certification, never zero. */
  norm_citations?: Array<NormCitation>;
  proposed_severity?: Severity;
  provenance: ObservationProvenance;
  recommendation_text: string;
  /** Deterministically grounded normative requirement; absent for legacy and nonnormative observations. */
  required_value?: string;
  run_id: RunId;
  /** Document value grounded in the project evidence; absent for legacy and nonnormative observations. */
  stated_value?: string;
};

/** Immutable evidence emitted by exactly one run. */
export type FindingObservationId = string;

/** The contract pattern for `FindingObservationId`. Anchored; use with `new RegExp()`. */
export const FINDING_OBSERVATION_ID_PATTERN = "^fobs_[0-9A-HJKMNP-TV-Z]{26}$";

export type FindingPage = {
  items: Array<Finding>;
  page: PageInfo;
};

export type FindingRef = {
  category: FindingCategory;
  finding_text: string;
  finding_uid: FindingUid;
  page_numbers: Array<number>;
};

/** Durable semantic issue identity, carrying expert history across reruns. */
export type FindingUid = string;

/** The contract pattern for `FindingUid`. Anchored; use with `new RegExp()`. */
export const FINDING_UID_PATTERN = "^fnd_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * `COMPARE-PERSISTED-SUMMARY-01` (B2). The comparison view the expert is looking at; the
 * command recomputes the sealed evidence in its own transaction and takes nothing else from the
 * client: not the input, not the model, not the seal.
 */
export type GenerateComparisonSummaryRequest = {
  mode: "version" | "stage";
  source_run_id?: RunId;
  target_run_id?: RunId;
  target_version_uid: VersionUid;
};

/**
 * `COMPARE-PERSISTED-SUMMARY-01` (B2). The stored summary, new or an exact repeat
 * (``replayed``: nothing was called and nothing was appended).
 */
export type GenerateComparisonSummaryResponse = {
  replayed: boolean;
  summary: ComparisonSummary;
};

/** Not an entity identity. Never interpreted as, converted into or stored as a system identifier. */
export type IdempotencyKey = string;

/** The contract pattern for `IdempotencyKey`. Anchored; use with `new RegExp()`. */
export const IDEMPOTENCY_KEY_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$";

/**
 * `UI-B-15` (contract 1.35.0): the multipart body of ``importOptimisationProposalDecisions``.
 *
 * ``file`` is the pass's workbook as ``exportOptimisationProposalsXlsx`` produced it, edited, at most 10 MiB.
 */
export type ImportProposalDecisionsRequest = {
  file: Blob;
};

/**
 * `R-151d` (contract 1.27.0): the multipart body of ``importRunDecisions``.
 *
 * ``file`` is the run's workbook as ``exportRunXlsx`` produced it, edited, at most 10 MiB.
 */
export type ImportRunDecisionsRequest = {
  file: Blob;
};

/** One role of the immutable input manifest. It carries a blob_id and a checksum and never an object key, bucket or URL. */
export type InputManifestEntry = {
  media_type: string;
  role: string;
  sha256: Sha256;
  size_bytes: number;
};

/** A new server and its one-time grant. The name is the administrator's; no model is asked for. */
export type IssueExecutorHostEnrollmentRequest = {
  display_name: string;
};

/** ``expires_in_days`` defaults to 30 when absent. */
export type IssueRunnerTokenRequest = {
  expires_in_days?: number;
};

export type IssueTokenRequest = {
  /** The caller's login, spelled the way the deployment spells it. Not an identity of this surface: it addresses nothing, appears in no path and is never a foreign key. */
  login: string;
  /** The secret presented with the login. It appears in no response body, no error detail and no diagnostic record. */
  password: string;
};

export type IssueTokenResponse = {
  /** How long the credential stays valid, in seconds counted from this response. A lifetime and never a clock reading, so no clock has to agree between the two sides. A caller exchanges again before it elapses; an elapsed credential is `authentication_required` like any other the deployment does not accept. */
  expires_in: number;
  /** Whether the account this credential was just minted for is still on the password the deployment seeded it with. `true` says the password has never been changed; `false` says it has. It is a fact about the account's password and not a statement about what the subject may do -- what follows from it is declared where refusals are declared: every operation but this one and `changePassword` answers `permission_denied` with `required_capability: password_changed` while it is `true`. Required, not optional, because a caller that could not read it would have to assume a value and the only assumable value is the permissive one. */
  is_default_credential: boolean;
  /** The credential, presented on the authorized operations as `Authorization: Bearer <token>`. Opaque: this document states no format for it, and a caller that reads anything out of it has taken a dependency this contract does not offer. */
  token: string;
};

/** The grant, **shown once**: it is stored only as a one-way hash, so no operation can return the `secret` or the `command` that carries it again. `package_version` and `package_sha256` name the agent package the command downloads and verifies. Copy the command now; a lost one is replaced by a new grant, which revokes this one. */
export type IssuedExecutorEnrollment = {
  command: string;
  enrollment: ExecutorEnrollmentMetadata;
  package_sha256: string;
  package_version: AgentPackageVersion;
  secret: string;
};

/**
 * The token's value, **shown once**: it is stored only as a one-way hash, so no operation
 * can return it again. Copy it now; a lost value is revoked and replaced.
 */
export type IssuedRunnerToken = {
  catalogue?: Array<RunnerCatalogueEntry>;
  host_id?: ExecutorHostId;
  runner_token?: RunnerTokenMetadata;
  token: string;
};

export type JobId = string;

/** The contract pattern for `JobId`. Anchored; use with `new RegExp()`. */
export const JOB_ID_PATTERN = "^job_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * `R-151h`, `D-317`: one row of the knowledge base's «Все».
 *
 * A decision on a finding (``kind: finding``, the ``DecisionRecord`` in ``finding``) or on an optimisation proposal
 * (``kind: proposal``, the ``ProposalDecisionRecord`` in ``proposal``); exactly the one its kind names is present. The
 * two keep their own identities -- a row is named by its kind and that record's id, never by a number of its own.
 * ``occurred_at`` is the record's own time (``recorded_at`` or ``decided_at``), by which the merged journal is ordered.
 */
export type KnowledgeBaseEntry = {
  finding?: DecisionRecord;
  kind: "finding" | "proposal";
  occurred_at: string;
  proposal?: ProposalDecisionRecord;
};

/** `R-151h`, `D-317`: one page of both journals merged, newest first, and how many entries match in both. */
export type KnowledgeBaseEntryPage = {
  items: Array<KnowledgeBaseEntry>;
  page: PageInfo;
  total: number;
};

/** The known release version through which this account has read. Unknown or future versions are refused. */
export type MarkReleaseNotesReadRequest = {
  read_through: string;
};

export type ModelCallId = string;

/** The contract pattern for `ModelCallId`. Anchored; use with `new RegExp()`. */
export const MODEL_CALL_ID_PATTERN = "^mc_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * The models the layout may name. Only pins of the provider lock; Haiku, the efforts above `high` and `low` for Opus are
 * never offered.
 */
export type ModelCatalogue = {
  contract_version: string;
  items: Array<ModelCatalogueEntry>;
};

/**
 * One model and one provider that may serve it: the accesses it can be served with, the efforts that may be asked for and the
 * exact strings an answer may report (`contracts/analysis/v1/model-catalogue.json`).
 */
export type ModelCatalogueEntry = {
  accepted_reported: Array<string>;
  access: Array<ExecutorModelAccess>;
  efforts: Array<ModelEffort>;
  model_id: string;
  provider: ExecutorProvider;
};

/**
 * The reasoning effort a model is asked for. Only these three are ever offered: `xhigh` and `max` are not, and `low` is
 * not offered for Opus (`contracts/analysis/v1/model-catalogue.json`).
 */
export const MODEL_EFFORT_VALUES = [
  'low',
  'medium',
  'high',
] as const;

/** ModelEffort - the closed value set above. */
export type ModelEffort = (typeof MODEL_EFFORT_VALUES)[number];

/**
 * What the agent knows of one model: `verified` by a minimal call that answered with an accepted model string,
 * `not_verified` (not checked yet) or `failed` (the check ended in a refusal, with a code).
 */
export const MODEL_PROBE_STATE_VALUES = [
  'verified',
  'not_verified',
  'failed',
] as const;

/** ModelProbeState - the closed value set above. */
export type ModelProbeState = (typeof MODEL_PROBE_STATE_VALUES)[number];

/**
 * Why a model cannot be used on a host, or anywhere, right now. Lists of servers and models hide what is unavailable; the
 * reasons are shown only where an action is blocked or a run waits, and to the administrator in a server's details.
 */
export const MODEL_UNAVAILABLE_REASON_VALUES = [
  'host_disabled',
  'host_offline',
  'login_required',
  'model_not_verified',
  'model_cooling_down',
  'not_on_any_server',
] as const;

/** ModelUnavailableReason - the closed value set above. */
export type ModelUnavailableReason = (typeof MODEL_UNAVAILABLE_REASON_VALUES)[number];

/** The snapshot's ``bge-m3-dense-v1`` build (D-127) over its reliability-aware chunks. */
export const NORM_BUILD_STATE_VALUES = [
  'complete',
  'incomplete',
  'absent',
] as const;

/** NormBuildState - the closed value set above. */
export type NormBuildState = (typeof NORM_BUILD_STATE_VALUES)[number];

/**
 * One document of the current snapshot as the catalogue lists it
 * (`W57B-NORMS-CATALOGUE-XLSX-01`). ``designation`` and ``title`` are derived for display
 * from the stored file name and are never identities; ``title`` is null when the name
 * carries nothing after the designation. ``kind`` is the stored document type verbatim.
 */
export type NormCatalogueEntry = {
  content_available: boolean;
  designation: string;
  kind: string;
  norm_document_id: NormDocumentId;
  page_count: number;
  paragraph_count: number;
  source_attribution: NormSourceAttribution;
  title: string | null;
};

/**
 * One page of the catalogue; ``total`` counts the documents the filters keep and
 * ``kinds`` lists every kind of the snapshot with its document count.
 */
export type NormCatalogueEntryPage = {
  items: Array<NormCatalogueEntry>;
  kinds: Array<NormKindCount>;
  norms_snapshot_id: NormsSnapshotId;
  page: PageInfo;
  total: number;
};

/** One persisted, verified citation to a labelled paragraph in the run-pinned snapshot and retrieval set. A rebound preserves the cited label and identifies the one matching paragraph. Never inferred from a display designation. */
export type NormCitation = {
  clause_number: string | null;
  designation: string;
  norm_document_id: NormDocumentId;
  norm_paragraph_id: NormParagraphId;
  norms_snapshot_id: NormsSnapshotId;
  page_label: number;
  quote: string;
  source_attribution: NormSourceAttribution;
  state: NormCitationState;
  title: string;
};

/** NormCitationState. */
export const NORM_CITATION_STATE_VALUES = [
  'verified',
  'rebound',
] as const;

/** NormCitationState - the closed value set above. */
export type NormCitationState = (typeof NORM_CITATION_STATE_VALUES)[number];

export type NormCurrentSnapshot = {
  designated_at: string;
  designated_by: UserUid;
  norms_snapshot_id: NormsSnapshotId;
};

/**
 * One document of a snapshot. ``content_available`` is true exactly when its PDF has a
 * confirmed custody binding, which is the only way ``streamNormDocumentContent`` serves it.
 */
export type NormDocument = {
  content_available: boolean;
  designation: string;
  doc_type: string;
  drawn_on: string | null;
  norm_document_id: NormDocumentId;
  norms_snapshot_id: NormsSnapshotId;
  paragraph_count: number;
  pdf_page_count: number;
  source_attribution: NormSourceAttribution;
  title: string;
  unreliable_paragraph_count: number;
};

export type NormDocumentId = string;

/** The contract pattern for `NormDocumentId`. Anchored; use with `new RegExp()`. */
export const NORM_DOCUMENT_ID_PATTERN = "^ndoc_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * `NORM-Q01`. A plain-text excerpt of the canonical paragraph text, with the matched
 * spans as offsets rather than markup.
 */
export type NormFragment = {
  highlights: Array<NormHighlight>;
  text: string;
};

/** One matched span of a fragment, as character offsets into ``NormFragment.text``. */
export type NormHighlight = {
  char_end: number;
  char_start: number;
};

export type NormKindCount = {
  document_count: number;
  kind: string;
};

export type NormParagraph = {
  block_ref: string;
  clause_number: string | null;
  kind: NormParagraphKind;
  norm_paragraph_id: NormParagraphId;
  ordinal: number;
  page_label: number;
  text: string;
  text_reliability: NormTextReliability;
};

export type NormParagraphId = string;

/** The contract pattern for `NormParagraphId`. Anchored; use with `new RegExp()`. */
export const NORM_PARAGRAPH_ID_PATTERN = "^npar_[0-9A-HJKMNP-TV-Z]{26}$";

/** NormParagraphKind. */
export const NORM_PARAGRAPH_KIND_VALUES = [
  'body',
  'heading',
  'table_row',
] as const;

/** NormParagraphKind - the closed value set above. */
export type NormParagraphKind = (typeof NORM_PARAGRAPH_KIND_VALUES)[number];

/** One document's canonical paragraphs in ``ordinal`` order, and its attribution. */
export type NormParagraphPage = {
  items: Array<NormParagraph>;
  page: PageInfo;
  source_attribution: NormSourceAttribution;
};

/** One occurrence of a citation: the PDF page and the offsets inside that page's text. */
export type NormReferenceAnchor = {
  char_end: number;
  char_start: number;
  page_number: number;
  quote: string;
};

/** Distinct cited designations per outcome; every outcome is present, zeros written. */
export type NormReferenceCounts = {
  in_corpus: number;
  newer_edition: number;
  not_in_corpus: number;
  not_recognised: number;
  older_edition_only: number;
};

/** One distinct cited designation and what the pinned snapshot holds for it. `anchors` keeps at most ten occurrences in reading order; `occurrence_count` is the true number. The `matched_*` properties name the corpus document the outcome points at (the same edition, the newer one, or the newest earlier one) and are absent exactly for `not_in_corpus` and `not_recognised`. `matched_designation` and `matched_title` are derived for display from the stored file name and are never identities. */
export type NormReferenceItem = {
  anchors: Array<NormReferenceAnchor>;
  cited: string;
  matched_designation?: string;
  matched_norm_document_id?: NormDocumentId;
  matched_title?: string;
  occurrence_count: number;
  outcome: "in_corpus" | "newer_edition" | "older_edition_only" | "not_in_corpus" | "not_recognised";
};

/** A document of the pinned snapshot whose designation the parser cannot read. Such a document can never be matched by a citation, so the list is explicit rather than inferred. `slug` is the stored file name without `.pdf`; `designation` and `title` are derived for display from it. */
export type NormReferenceUnrecognised = {
  designation: string;
  norm_document_id: NormDocumentId;
  slug: string;
  title?: string;
};

/** Verified immutable retrieval-set identity; never a display label or corpus filename. */
export type NormRetrievalSetId = string;

/** The contract pattern for `NormRetrievalSetId`. Anchored; use with `new RegExp()`. */
export const NORM_RETRIEVAL_SET_ID_PATTERN = "^nrs_[0-9A-HJKMNP-TV-Z]{26}$";

/** One reliable canonical paragraph of the searched snapshot. */
export type NormSearchHit = {
  block_ref: string;
  clause_number: string | null;
  designation: string;
  doc_type: string;
  fragment: NormFragment;
  norm_document_id: NormDocumentId;
  norm_paragraph_id: NormParagraphId;
  norms_snapshot_id: NormsSnapshotId;
  page_label: number;
  source_attribution: NormSourceAttribution;
  title: string;
};

export type NormSearchPage = {
  items: Array<NormSearchHit>;
  page: PageInfo;
};

/**
 * One loaded snapshot. ``qualified`` is the setter's own predicate (a complete build
 * and a confirmed source binding for every document's PDF); ``current`` marks the one
 * current snapshot.
 */
export type NormSnapshot = {
  build_state: NormBuildState;
  content_key: string;
  created_at: string;
  current: boolean;
  document_count: number;
  norms_snapshot_id: NormsSnapshotId;
  paragraph_count: number;
  qualified: boolean;
  unreliable_count: number;
};

/** One row of the append-only history of the current snapshot, newest first. */
export type NormSnapshotEvent = {
  actor_user_uid: UserUid;
  changed_at: string;
  event_id: string;
  from_norms_snapshot_id: NormsSnapshotId | null;
  to_norms_snapshot_id: NormsSnapshotId;
};

export type NormSnapshotEventPage = {
  items: Array<NormSnapshotEvent>;
  page: PageInfo;
};

export type NormSnapshotPage = {
  items: Array<NormSnapshot>;
  page: PageInfo;
};

/**
 * `NORM-Q04`. Where a norm document's text came from, carried exactly on every norms
 * response. The corpus is internal (D-4.1); nothing here is a publication claim.
 */
export const NORM_SOURCE_ATTRIBUTION_VALUES = [
  'consultant_plus',
  'unattributed',
] as const;

/** NormSourceAttribution - the closed value set above. */
export type NormSourceAttribution = (typeof NORM_SOURCE_ATTRIBUTION_VALUES)[number];

/**
 * F-4. An ``unreliable`` paragraph's recognised text did not survive repair; it is
 * shown marked in a document view and is never a search result.
 */
export const NORM_TEXT_RELIABILITY_VALUES = [
  'reliable',
  'unreliable',
] as const;

/** NormTextReliability - the closed value set above. */
export type NormTextReliability = (typeof NORM_TEXT_RELIABILITY_VALUES)[number];

export type NormsSnapshotId = string;

/** The contract pattern for `NormsSnapshotId`. Anchored; use with `new RegExp()`. */
export const NORMS_SNAPSHOT_ID_PATTERN = "^ns_[0-9A-HJKMNP-TV-Z]{26}$";

/** What produced this observation. Checksums and identities only: never the prompt, the request or the response body. */
export type ObservationProvenance = {
  analysis_profile_id: AnalysisProfileId;
  model_call_id?: ModelCallId | null;
  model_identity?: string | null;
  prompt_bundle_id: PromptBundleId;
  provider_mode: ProviderMode;
  stage_id: StageId;
};

/**
 * One optimisation pass, pinned to everything it read: the version, its published run
 * and that run's text layer, the price-list revision and the vendor-list revision (global
 * or the project's own, ``vendor_list_source``), and the three algorithm versions.
 *
 * ``version_ordinal`` (contract 1.37.0, `UI-B-14`) is the display order of the version the pass was started over
 * («V2»), so a screen can name an earlier version's pass; it is never an identity.
 */
export type OptimisationPass = {
  decision_counts: ProposalDecisionCounts;
  document_uid: DocumentUid;
  extraction_algorithm: string;
  generator_version: string;
  match_algorithm: string;
  matched_row_count: number;
  optimisation_pass_id: OptimisationPassId;
  price_list_id: PriceListId;
  project_uid: ProjectUid;
  proposal_count: number;
  proposed_row_count: number;
  run_id: RunId;
  specification_row_count: number;
  started_at: string;
  started_by_label: string;
  started_by_user_uid: UserUid;
  text_layer_sha256: Sha256;
  vendor_list_id: VendorListId;
  vendor_list_source: VendorListScope;
  version_ordinal: number;
  version_uid: VersionUid;
};

export type OptimisationPassId = string;

/** The contract pattern for `OptimisationPassId`. Anchored; use with `new RegExp()`. */
export const OPTIMISATION_PASS_ID_PATTERN = "^opp_[0-9A-HJKMNP-TV-Z]{26}$";

/** A project's passes, newest first. */
export type OptimisationPassList = {
  items: Array<OptimisationPass>;
};

/**
 * One proposal: a specification row matched to ``matched_position`` and a cheaper
 * ``proposed_position`` of the same price-list revision, in the same unit and currency,
 * from a vendor on the pass's vendor list.
 *
 * ``row_text`` is the description as the saved text layer shows it (name, mark, code and
 * manufacturer cells run together); page, sheet and lines say where it is. Both unit prices
 * are the positions' stored prices. ``saving`` is ``(current_unit_price −
 * proposed_unit_price) × quantity`` and is ``null`` -- never ``0`` -- when ``quantity`` is
 * ``null`` because the row's quantity text is not a plain number. ``ordinal`` is a display
 * order inside the pass, never an identity.
 *
 * ``saving_percent`` (`UI-B-07`, contract 1.40.0) is the server's percent of the current unit price that the proposed price saves, to two decimals; optional and absent when the current unit price is zero.
 */
export type OptimisationProposal = {
  analog_basis: ProposalAnalogBasis;
  currency: string;
  current_decision: ProposalDecision | null;
  current_unit_price: string;
  current_verdict: ProposalDecisionState;
  line_end: number;
  line_start: number;
  matched_basis: ProposalMatchBasis;
  matched_position: ProposalPosition;
  name_similarity: string;
  optimisation_pass_id: OptimisationPassId;
  optimisation_proposal_id: OptimisationProposalId;
  ordinal: number;
  page_number: number;
  proposal_type: OptimisationProposalType;
  proposed_position: ProposalPosition;
  proposed_unit_price: string;
  proposed_vendor: string;
  quantity: string | null;
  quantity_text: string | null;
  rationale: string;
  row_position: string | null;
  row_text: string;
  saving: string | null;
  /** `UI-B-07` (contract 1.40.0): how much cheaper the proposed unit price is than the current one, in percent of the current unit price -- `(current_unit_price - proposed_unit_price) / current_unit_price * 100`, computed exactly and rounded half up to two decimals, written without a trailing zero (`25`, `33.33`). It is the share that `saving` is of the cost at the current price, in which the quantity cancels, so it is present where `saving` is `null` because the quantity is not a plain number; absent only when the current unit price is zero. The one figure of a proposal that is rounded. Never computed by a client. */
  saving_percent?: string;
  sheet_label: string | null;
  spec_row_key: string;
  table_ordinal: number;
  unit: string;
};

export type OptimisationProposalId = string;

/** The contract pattern for `OptimisationProposalId`. Anchored; use with `new RegExp()`. */
export const OPTIMISATION_PROPOSAL_ID_PATTERN = "^opr_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * One page of a pass's proposals in ordinal order. ``total`` counts the proposals the
 * ``decision`` filter admits; the pass's ``decision_counts`` count all of them.
 */
export type OptimisationProposalPage = {
  decision: ProposalDecisionState | null;
  items: Array<OptimisationProposal>;
  limit: number;
  next_offset: number | null;
  offset: number;
  optimisation_pass: OptimisationPass;
  total: number;
};

/**
 * The kind of a proposal. Only the deterministic one exists: a cheaper position of the
 * same price list. The legacy ``faster_install``, ``simpler_design`` and ``lifecycle`` need
 * judgement and wait for the model-assisted slice.
 */
export const OPTIMISATION_PROPOSAL_TYPE_VALUES = [
  'cheaper_analog',
] as const;

/** OptimisationProposalType - the closed value set above. */
export type OptimisationProposalType = (typeof OPTIMISATION_PROPOSAL_TYPE_VALUES)[number];

export type PageInfo = {
  /** Token for the next page, or null when this is the last page. */
  next_cursor: Cursor | null;
};

/** PageProfileStatus. */
export const PAGE_PROFILE_STATUS_VALUES = [
  'ready',
  'needs_review',
  'refused',
] as const;

/** PageProfileStatus - the closed value set above. */
export type PageProfileStatus = (typeof PAGE_PROFILE_STATUS_VALUES)[number];

/** The stamp fields read from one page; every member is absent when the page has none. */
export type PageStamp = {
  designation?: string;
  project_stage?: ProjectStage;
  release_date?: string;
  revision_number?: string;
  section_code?: ProjectSection;
  sheet_name?: string;
  sheet_number?: string;
};

/** A person's names, set together. 1-60 characters of letters, separated by single spaces, hyphens or apostrophes, with no word mixing Cyrillic and Latin letters. Surrounding whitespace and invisible characters are removed before the rule is applied. */
export type PersonNames = {
  first_name: string;
  last_name: string;
  /** Optional; absent when the person has none. */
  middle_name?: string;
};

/** One block of the portal's block list. The pair `(version_uid, portal_block_id)` addresses it. `page_number` is the true 1-based PDF page; `page_label` is the portal's own integer label, kept. `ordinal` is the portal's order on the page: not unique, and null for a stamp. `bbox_norm` is `[x0, y0, x1, y1]` in the page's normalised top-left space, each in [0, 1]; `polygon_points`, when the portal gave a polygon, are its `[x, y]` vertices. `crop` exists only for an IMAGE block on a page whose `geometry` is `ok`. `recognised_text` exists for TEXT blocks the markdown holds; `portal_description` is the portal's text for an IMAGE block, shown marked and never used in analysis (R-117). An absent optional member is omitted, never null. */
export type PortalBlock = {
  bbox_norm: Array<number>;
  block_type: PortalBlockType;
  crop?: PortalCrop;
  geometry: PortalGeometryState;
  ordinal: number | null;
  page_label: number;
  page_number: number;
  polygon_points?: Array<Array<number>>;
  portal_block_id: PortalBlockId;
  portal_description?: string;
  recognised_text?: PortalRecognisedText;
  status: string;
};

/** An external identifier: minted by the portal that produced the bundle and carried verbatim from its block list (`blk_` and 32 lowercase hexadecimal digits). It is not an identity this product generates, and it addresses a block only together with a `version_uid`. */
export type PortalBlockId = string;

/** The contract pattern for `PortalBlockId`. Anchored; use with `new RegExp()`. */
export const PORTAL_BLOCK_ID_PATTERN = "^blk_[0-9a-f]{32}$";

/** One page of a version's portal blocks, ordered by `page_number`, `ordinal` (null last) and `portal_block_id`; the continuation token carries that key and nothing else. `status` is the distinction `VersionBlockIndex.status` carries: `not_produced` is a version no run of which has produced portal geometry yet; `produced` is one whose geometry stage succeeded and which may genuinely hold no blocks. `block_count` is the whole version's, not the page's. A caller reads `status`, never the length of `items`. */
export type PortalBlockPage = {
  block_count: number;
  items: Array<PortalBlock>;
  page: PageInfo;
  produced_by_run_id: RunId | null;
  status: "produced" | "not_produced";
  version_uid: VersionUid;
};

/** The portal's own block types, lower-cased. A `stamp` block exists only in the block list: the recognised-text markdown never carries one. */
export const PORTAL_BLOCK_TYPE_VALUES = [
  'text',
  'image',
  'stamp',
] as const;

/** PortalBlockType - the closed value set above. */
export type PortalBlockType = (typeof PORTAL_BLOCK_TYPE_VALUES)[number];

/** A crop this product cut itself from the PDF with a clip render. It is never the portal's `crop_url`, which is a capability URL and is neither fetched, stored nor served. The bytes are `streamVersionPortalBlockCrop`; `sha256` is theirs. */
export type PortalCrop = {
  height_px: number;
  media_type: "image/png";
  sha256: Sha256;
  width_px: number;
};

/** The page-box check. `geometry_mismatch` means the portal's page size and the PDF's page box disagree beyond the frozen tolerance: no crop was cut for that page, and its blocks are shown without one rather than with a wrong one. The stage still reports success. */
export const PORTAL_GEOMETRY_STATE_VALUES = [
  'ok',
  'geometry_mismatch',
] as const;

/** PortalGeometryState - the closed value set above. */
export type PortalGeometryState = (typeof PORTAL_GEOMETRY_STATE_VALUES)[number];

/** The portal's OCR text of a TEXT block. It is always marked `recognised` (R-116): never merged into the PDF text layer. `flags` are the quality signals found in it, a lowercase snake_case vocabulary: mixed-script words, Latin/Cyrillic homoglyphs, CJK characters, doubled list markers and the norms degeneracy signals. Engineering designations (`1.A`, `B25`, `A500C`, `REI 150`) are exempt. `text` is markdown and is rendered as text, never as HTML. */
export type PortalRecognisedText = {
  flags: Array<string>;
  quote_source: "recognised";
  text: string;
};

/**
 * «Подготовить отчёт для заказчика» from a finished analytic report: a new ``client`` draft that
 * reads the analytic report's verified facts.
 */
export type PrepareComparisonClientReportRequest = {
  reuse?: boolean;
};

export type PresetId = string;

/** The contract pattern for `PresetId`. Anchored; use with `new RegExp()`. */
export const PRESET_ID_PATTERN = "^evt_[0-9A-HJKMNP-TV-Z]{26}$";

export type PresetRevisionId = string;

/** The contract pattern for `PresetRevisionId`. Anchored; use with `new RegExp()`. */
export const PRESET_REVISION_ID_PATTERN = "^evt_[0-9A-HJKMNP-TV-Z]{26}$";

/** An optional field two or more columns could be: none of them was read. */
export type PriceListAmbiguousColumn = {
  field: PriceListField;
  headers: Array<string>;
};

/** One header column mapped to a field: its 1-based position and its header text. */
export type PriceListColumn = {
  column: number;
  field: PriceListField;
  header: string;
};

/** Where an accepted row's currency came from: its cell, the price header, the default. */
export const PRICE_LIST_CURRENCY_SOURCE_VALUES = [
  'column',
  'price_header',
  'default',
] as const;

/** PriceListCurrencySource - the closed value set above. */
export type PriceListCurrencySource = (typeof PRICE_LIST_CURRENCY_SOURCE_VALUES)[number];

export type PriceListCurrencySourceCount = {
  count: number;
  source: PriceListCurrencySource;
};

/** A position field a header column was mapped to. */
export const PRICE_LIST_FIELD_VALUES = [
  'name',
  'unit',
  'unit_price',
  'code',
  'mark',
  'currency',
  'vendor',
  'section',
] as const;

/** PriceListField - the closed value set above. */
export type PriceListField = (typeof PRICE_LIST_FIELD_VALUES)[number];

/** The uploaded file's format, recognised by its bytes and never by its name. */
export const PRICE_LIST_FORMAT_VALUES = [
  'csv',
  'xlsx',
] as const;

/** PriceListFormat - the closed value set above. */
export type PriceListFormat = (typeof PRICE_LIST_FORMAT_VALUES)[number];

export type PriceListId = string;

/** The contract pattern for `PriceListId`. Anchored; use with `new RegExp()`. */
export const PRICE_LIST_ID_PATTERN = "^prl_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * How one file was read: deterministic, so the same bytes always report the same.
 *
 * ``skipped`` and ``warnings`` list at most the first 1000 rows each;
 * ``skipped_by_reason`` and ``warnings_by_reason`` always count every one.
 */
export type PriceListParseReport = {
  accepted_rows: number;
  ambiguous_columns: Array<PriceListAmbiguousColumn>;
  blank_rows: number;
  columns: Array<PriceListColumn>;
  currency_sources: Array<PriceListCurrencySourceCount>;
  data_rows: number;
  default_currency: string | null;
  delimiter: ";" | "\t" | "," | null;
  encoding: "utf-8" | "utf-8-sig" | "utf-16" | "cp1251" | null;
  format: PriceListFormat;
  header_row: number;
  ignored_columns: Array<string>;
  preamble_rows: number;
  price_header_currency: string | null;
  report_version: 1;
  sheet: string | null;
  skipped: Array<PriceListRowNote>;
  skipped_by_reason: Array<PriceListReasonCount>;
  skipped_listed_in_full: boolean;
  skipped_rows: number;
  warnings: Array<PriceListRowNote>;
  warnings_by_reason: Array<PriceListReasonCount>;
};

/** One parsed position. ``row_number`` is its source row, never an identity. */
export type PriceListPosition = {
  code: string | null;
  currency: string;
  mark: string | null;
  name: string;
  price_list_position_id: PriceListPositionId;
  row_number: number;
  section_code: ProjectSection | null;
  unit: string;
  unit_price: string;
  vendor: string | null;
};

export type PriceListPositionId = string;

/** The contract pattern for `PriceListPositionId`. Anchored; use with `new RegExp()`. */
export const PRICE_LIST_POSITION_ID_PATTERN = "^prp_[0-9A-HJKMNP-TV-Z]{26}$";

/** One page of a revision's positions in source-row order, with the revision's report. */
export type PriceListPositionPage = {
  items: Array<PriceListPosition>;
  limit: number;
  next_offset: number | null;
  offset: number;
  parse_report: PriceListParseReport;
  revision: PriceListRevision;
  total: number;
};

export type PriceListReasonCount = {
  count: number;
  reason: PriceListRowReason;
};

/**
 * One uploaded price list of a project: an immutable revision; the highest is current.
 *
 * ``revision_number`` orders a project's revisions for display and is never an identity;
 * ``source_filename`` is the uploaded file's name, display only.
 */
export type PriceListRevision = {
  accepted_row_count: number;
  data_row_count: number;
  default_currency: string | null;
  is_current: boolean;
  media_type: "text/csv" | "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  price_list_id: PriceListId;
  project_uid: ProjectUid;
  revision_number: number;
  sha256: Sha256;
  size_bytes: number;
  skipped_row_count: number;
  source_filename: string;
  source_format: PriceListFormat;
  uploaded_at: string;
  uploaded_by_user_uid: UserUid;
};

/** Every price-list revision of one project, newest first; the first one is current. */
export type PriceListRevisionList = {
  items: Array<PriceListRevision>;
};

/** One source row (as the spreadsheet numbers it) and why it is reported. */
export type PriceListRowNote = {
  reason: PriceListRowReason;
  row: number;
};

/**
 * Why a data row was skipped (the first ten), or a warning on an accepted row (the last).
 *
 * A skipped row is never repaired: a price that is not a plain number, not positive, finer
 * than six decimals or not below 10^14 is reported, never guessed or rounded.
 */
export const PRICE_LIST_ROW_REASON_VALUES = [
  'name_missing',
  'unit_missing',
  'price_missing',
  'price_not_a_number',
  'price_not_positive',
  'price_precision',
  'price_too_large',
  'currency_missing',
  'currency_unrecognised',
  'value_too_long',
  'section_unrecognised',
] as const;

/** PriceListRowReason - the closed value set above. */
export type PriceListRowReason = (typeof PRICE_LIST_ROW_REASON_VALUES)[number];

export type ProductVersion = {
  build_id: string;
  comparison_modules?: ComparisonModules;
  contract_version: string;
  product_version: string;
};

export type Project = {
  /** The project's documents by audit state (`UI-PARITY-P0B`). Present on a `listProjects` item; absent from `createProject`'s answer, which reads no documents and claims no count. */
  audit_counts?: DocumentAuditCounts;
  created_at: string;
  document_count?: number;
  name: string;
  project_uid: ProjectUid;
};

/** One row of the "documents per project" panel: the same fact `Project.document_count` already publishes, gathered for every project in one read. */
export type ProjectDocumentCount = {
  document_count: number;
  name: string;
  project_uid: ProjectUid;
};

export type ProjectPage = {
  items: Array<Project>;
  page: PageInfo;
};

/** The fifteen project sections: legacy's fourteen (`D-56`, `R-40`), kept by migration `0011_document_section` as the historical record, and `PS` (the explanatory note, distinct from `PB`, fire safety), added by `W59-SECTION-SEAL-01`. A document or version with no section is not a sixteenth member of this enum -- the property is absent, which is a different, equally real fact. */
export const PROJECT_SECTION_VALUES = [
  'AR',
  'AI',
  'KM',
  'KJ',
  'OV',
  'EOM',
  'VK',
  'PT',
  'PB',
  'SS',
  'ITP',
  'GP',
  'TX',
  'POS',
  'PS',
] as const;

/** ProjectSection - the closed value set above. */
export type ProjectSection = (typeof PROJECT_SECTION_VALUES)[number];

/**
 * `W59-SECTION-SEAL-01`. The explicit project stage of one version.
 *
 * ``P`` (design documentation) or ``R`` (working documentation). Bound to the version, never
 * inferred from a file name, and never the analysis ``stage_id``, which is why the property
 * that carries it is named ``project_stage``.
 */
export const PROJECT_STAGE_VALUES = [
  'P',
  'R',
] as const;

/** ProjectStage - the closed value set above. */
export type ProjectStage = (typeof PROJECT_STAGE_VALUES)[number];

/** Opaque project identity. */
export type ProjectUid = string;

/** The contract pattern for `ProjectUid`. Anchored; use with `new RegExp()`. */
export const PROJECT_UID_PATTERN = "^prj_[0-9A-HJKMNP-TV-Z]{26}$";

export type PromptBundleId = string;

/** The contract pattern for `PromptBundleId`. Anchored; use with `new RegExp()`. */
export const PROMPT_BUNDLE_ID_PATTERN = "^pb_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * Why the proposed position is the same kind of product: one code family (the leading
 * letters of the code or mark, ``ПК 60-12-8`` ~ ``ПК 63-15-8``), or at least half of the
 * words of the two names in common.
 */
export const PROPOSAL_ANALOG_BASIS_VALUES = [
  'code_family',
  'name_similarity',
] as const;

/** ProposalAnalogBasis - the closed value set above. */
export type ProposalAnalogBasis = (typeof PROPOSAL_ANALOG_BASIS_VALUES)[number];

/**
 * One appended expert decision. Never changed; the proposal's latest one is current -- unless
 * that is a ``revoke``, which withdrew the decision before it and left the proposal ``pending``.
 *
 * ``carried_from`` (`UI-B-14`) is ``null`` for a decision an expert made directly and names the source when the
 * expert carried it over from an earlier version's pass; the decision is the confirming expert's own either way
 * (``actor_user_uid``), and a later decision on the proposal supersedes it like any other.
 */
export type ProposalDecision = {
  actor_label: string;
  actor_user_uid: UserUid;
  carried_from: ProposalDecisionCarriedFrom | null;
  comment: string | null;
  decided_at: string;
  optimisation_proposal_id: OptimisationProposalId;
  proposal_decision_id: ProposalDecisionId;
  verdict: ProposalVerdict;
};

/**
 * `UI-B-14` (contract 1.37.0): where a carried decision came from -- the decision of an earlier version's pass
 * that an expert carried over to this proposal.
 *
 * ``proposal_decision_id`` is the source decision's own identity and ``optimisation_pass_id`` and ``version_uid`` the
 * pass and version it was made in. ``version_ordinal`` is the version's display order («V2») and is never an identity.
 */
export type ProposalDecisionCarriedFrom = {
  optimisation_pass_id: OptimisationPassId;
  proposal_decision_id: ProposalDecisionId;
  version_ordinal: number;
  version_uid: VersionUid;
};

/**
 * `UI-B-14`: what a carryover did. Every decision in force of the source pass (``source_decided``) is counted in
 * exactly one of four outcomes: ``carried`` (appended to the target pass), ``target_decided`` (the one proposal of the
 * target with the same content already has an event, which stands), ``ambiguous`` (more than one proposal of either
 * pass has that content, so nothing is guessed) or ``unmatched`` (no proposal of the target pass has it).
 * ``source_version_ordinal`` is the display order of the source's version («V2»), never an identity.
 */
export type ProposalDecisionCarryoverReport = {
  ambiguous: number;
  carried: number;
  optimisation_pass_id: OptimisationPassId;
  source_decided: number;
  source_optimisation_pass_id: OptimisationPassId;
  source_version_ordinal: number;
  target_decided: number;
  unmatched: number;
};

/**
 * How many of a pass's proposals stand in each decision state; the four sum to the
 * pass's ``proposal_count``. These are the proposals' own counts, never finding counts.
 */
export type ProposalDecisionCounts = {
  accept: number;
  pending: number;
  reject: number;
  revise: number;
};

export type ProposalDecisionId = string;

/** The contract pattern for `ProposalDecisionId`. Anchored; use with `new RegExp()`. */
export const PROPOSAL_DECISION_ID_PATTERN = "^opd_[0-9A-HJKMNP-TV-Z]{26}$";

/** Why a row of the proposals workbook was refused. */
export const PROPOSAL_DECISION_IMPORT_REFUSAL_VALUES = [
  'no_proposal_id',
  'duplicate_proposal',
  'unknown_proposal',
  'unknown_decision',
  'comment_required',
  'comment_too_long',
] as const;

/** ProposalDecisionImportRefusal - the closed value set above. */
export type ProposalDecisionImportRefusal = (typeof PROPOSAL_DECISION_IMPORT_REFUSAL_VALUES)[number];

/** `UI-B-15`: what an import of edited proposal decisions did, row by row, in sheet order. */
export type ProposalDecisionImportReport = {
  optimisation_pass_id: OptimisationPassId;
  recorded: number;
  refused: number;
  rows: Array<ProposalDecisionImportRow>;
  unchanged: number;
};

/** `UI-B-15`: one row of «Предложения» that names an ID or a decision; the proposal's identity only for a proposal of the pass. */
export type ProposalDecisionImportRow = {
  optimisation_proposal_id?: OptimisationProposalId;
  outcome: DecisionImportOutcome;
  reason?: ProposalDecisionImportRefusal;
  row: number;
};

/** Every decision of one proposal, oldest first; the last is current. */
export type ProposalDecisionList = {
  items: Array<ProposalDecision>;
};

/**
 * `R-151h` (contract 1.25.0): one expert decision on an optimisation proposal, with where it belongs and what it
 * decided about -- the knowledge base's «Предложения» half, as ``DecisionRecord`` is its «Замечания» half.
 *
 * ``carried_from`` (`D-335`, contract 1.43.0) is present only for a decision an expert carried over from an earlier
 * version's pass, and names the source; it is absent for a decision made directly.
 */
export type ProposalDecisionRecord = {
  actor_label: string;
  carried_from?: ProposalDecisionCarriedFrom;
  comment: string | null;
  decided_at: string;
  document_name: string;
  document_uid: DocumentUid;
  optimisation_pass_id: OptimisationPassId;
  optimisation_proposal_id: OptimisationProposalId;
  project_name: string;
  project_uid: ProjectUid;
  proposal_decision_id: ProposalDecisionId;
  proposed_vendor: string;
  row_text: string;
  section?: ProjectSection;
  unit: string;
  verdict: ProposalVerdict;
  version_uid: VersionUid;
};

/** `R-151h`: one page of the proposal decision journal, newest first, and how many entries match. */
export type ProposalDecisionRecordPage = {
  items: Array<ProposalDecisionRecord>;
  page: PageInfo;
  total: number;
};

/** The decision appended (or replayed) and the proposal as it now stands. */
export type ProposalDecisionResult = {
  decision: ProposalDecision;
  proposal: OptimisationProposal;
};

/**
 * A proposal's current decision: its latest verdict, or ``pending`` when nobody decided.
 * Also the ``decision`` filter of ``listOptimisationProposals``.
 */
export const PROPOSAL_DECISION_STATE_VALUES = [
  'pending',
  'accept',
  'reject',
  'revise',
] as const;

/** ProposalDecisionState - the closed value set above. */
export type ProposalDecisionState = (typeof PROPOSAL_DECISION_STATE_VALUES)[number];

/** How the specification row was matched to its current price-list position. */
export const PROPOSAL_MATCH_BASIS_VALUES = [
  'code',
  'mark',
  'name',
] as const;

/** ProposalMatchBasis - the closed value set above. */
export type ProposalMatchBasis = (typeof PROPOSAL_MATCH_BASIS_VALUES)[number];

/**
 * A price-list position a proposal names. ``row_number`` is its source row, never an
 * identity.
 */
export type ProposalPosition = {
  code: string | null;
  mark: string | null;
  name: string;
  price_list_position_id: PriceListPositionId;
  row_number: number;
  vendor: string | null;
};

/**
 * An expert's verdict on a proposal. ``revise`` says the analog is right in principle
 * and the proposal needs changing; its comment is required. ``revoke`` (`UI-B-12`, contract
 * 1.35.0, «Снять решение») withdraws the decision in force: it is one more appended event, it
 * takes the proposal back to ``pending``, and it is refused (``409 conflict``,
 * ``conflict_reason`` ``no_decision_to_revoke``) when no decision stands.
 */
export const PROPOSAL_VERDICT_VALUES = [
  'accept',
  'reject',
  'revise',
  'revoke',
] as const;

/** ProposalVerdict - the closed value set above. */
export type ProposalVerdict = (typeof PROPOSAL_VERDICT_VALUES)[number];

/** What the agent knows of a provider's login on the host: `valid`, `login_required` or `unknown`. */
export const PROVIDER_AUTH_STATE_VALUES = [
  'valid',
  'login_required',
  'unknown',
] as const;

/** ProviderAuthState - the closed value set above. */
export type ProviderAuthState = (typeof PROVIDER_AUTH_STATE_VALUES)[number];

/** Whether the model call was made live or replayed from a recording. Visible in the UI and in the CSV, because a recorded run is not evidence of a live one. */
export const PROVIDER_MODE_VALUES = [
  'live',
  'recorded',
] as const;

/** ProviderMode - the closed value set above. */
export type ProviderMode = (typeof PROVIDER_MODE_VALUES)[number];

export type ReauditRunRequest = {
  cost_consent?: RunCostConsent;
};

/** The exchange of an enrollment secret for a runner token. `runner_instance_id` names the agent process and makes a repeat of the exchange inside its window idempotent. */
export type RedeemExecutorEnrollmentRequest = {
  agent_version?: string;
  runner_instance_id: string;
};

/** One registration request, as an administrator reads it. No credential material. */
export type RegistrationRequest = {
  /** The account an approval created. Null while pending, on a rejected request, and after that account was purged. */
  created_user_uid: UserUid | null;
  /** Null while the request is pending. */
  decided_at: string | null;
  /** The administrator who decided; null while pending. */
  decided_by: UserUid | null;
  /** The applicant's name form, `Last F. M.`, resolved by the server. */
  display_label: string;
  first_name: string;
  last_name: string;
  /** The normalised e-mail address the applicant gave. */
  login: string;
  /** Null when the applicant gave none. */
  middle_name: string | null;
  /** The administrator's reason, present only on a rejected request. It is read by administrators only and is never shown to the applicant. */
  rejection_reason: string | null;
  request_id: RegistrationRequestId;
  status: RegistrationStatus;
  submitted_at: string;
};

/** Opaque registration request identity. */
export type RegistrationRequestId = string;

/** The contract pattern for `RegistrationRequestId`. Anchored; use with `new RegExp()`. */
export const REGISTRATION_REQUEST_ID_PATTERN = "^reg_[0-9A-HJKMNP-TV-Z]{26}$";

/** One page of requests and the number of pending requests in all, whatever the filter -- the administrator's badge. */
export type RegistrationRequestPage = {
  items: Array<RegistrationRequest>;
  page: PageInfo;
  pending_total: number;
};

/** The states of the `registration_request` machine in `contracts/domain/v1/state-machines.json`: `pending` until an administrator decides, then `approved` or `rejected`, both terminal. */
export const REGISTRATION_STATUS_VALUES = [
  'pending',
  'approved',
  'rejected',
] as const;

/** RegistrationStatus - the closed value set above. */
export type RegistrationStatus = (typeof REGISTRATION_STATUS_VALUES)[number];

/** What an applicant is told: that the application is pending. This is the only status this surface ever shows an applicant (R-56 and its addendum of 2026-10-06); a decided application is answered like an unknown pair. */
export type RegistrationStatusResponse = {
  status: "pending";
};

export type RejectRegistrationRequest = {
  /** Why the request is rejected, 1-256 characters after surrounding whitespace is removed, with no control character but a line feed. Stored for administrators; the applicant is not shown it. */
  reason: string;
};

/** The highest stored revision of one visible release. The archive entry is last; range_label is null for a normal release. */
export type ReleaseEntry = {
  date: string;
  is_archive: boolean;
  items: Array<ReleaseNoteItem>;
  range_label: string | null;
  revision: number;
  title: string;
  version: string;
};

/** Visible releases newest first, archive last, and the versions this account has not yet read. */
export type ReleaseList = {
  items: Array<ReleaseEntry>;
  whats_new: Array<string>;
};

/** One user-facing note; where is the navigation label saved at release time. */
export type ReleaseNoteItem = {
  kind: ReleaseNoteKind;
  screen: string;
  text: string;
  where: string;
};

/** The editorial category of a release note. */
export const RELEASE_NOTE_KIND_VALUES = [
  'new',
  'improved',
  'fixed',
] as const;

/** ReleaseNoteKind - the closed value set above. */
export type ReleaseNoteKind = (typeof RELEASE_NOTE_KIND_VALUES)[number];

/** `R-151a` (contract 1.22.0): the document's new display title; `document_uid` stays its identity. */
export type RenameDocumentRequest = {
  display_title: string;
};

/**
 * An agent's health report (`EXEC2-SEAL-1`, ADR-0026 decision 5): sanitised enumerations and bounded
 * strings only.
 */
export type ReportRunnerHealthRequest = {
  agent_version: string;
  clis: Array<RunnerCliHealth>;
  concurrency: number;
  execution_profile: RunnerExecutionProfile;
  features: Array<RunnerFeature>;
  key_file?: RunnerKeyFileReport;
  providers?: Array<RunnerProviderReport>;
  runner_instance_id?: string;
  slots?: ExecutorHostSlots;
};

export type ResetUserPasswordRequest = {
  /** The password the account signs in with next and must then change. It is held to the deployment's password policy against the account's login, and it appears in no response body, no error detail and no diagnostic record. */
  temporary_password: string;
};

/**
 * Resumes a paused job. ``consent`` is required after ``overrun`` and ``route_changed`` (a new
 * estimate for what is left) and ignored after the other pause reasons.
 */
export type ResumeComparisonAiJobRequest = {
  consent?: ComparisonAiConsent;
};

export type ResumeStageChainRunRequest = {
  consent?: ComparisonAiConsent;
  retry_failed?: boolean;
};

/**
 * A new immutable revision of a connection: the full settings, never a patch.
 *
 * `EXEC2-SEAL-1` (ADR-0026 decisions 1 and 2): `max_active_runs` (1 to 16, absent means 1) is the most units of this connection that may be in use at once, where a Run in `leased`, `running` or `retry_wait` and a comparison model call in `prepared` or `sent` each count one. A lowered value governs new claims only and never stops work in flight. The coupled limits are validated on the revision and refused as `422 validation_failed`: `max_claimed_tasks` of a `pull` connection and a set `max_parallel_calls` of an `http_api` connection must each be at least `max_active_runs` (field `max_claimed_tasks` or `max_parallel_calls`, constraint `below_max_active_runs`), and an `ssh_command` connection takes a value above one only once its wrappers isolate concurrent invocations (field `max_active_runs`, constraint `capacity_not_supported_for_kind`).
 */
export type ReviseExecutorConnectionRequest = {
  allow_client_documents: boolean;
  answer_deadline_seconds?: number;
  api_flavour?: ExecutorApiFlavour;
  base_url?: string;
  billing: ExecutorBilling;
  gateway_model: string;
  host_key?: string;
  max_active_runs?: number;
  max_claimed_tasks?: number;
  max_parallel_calls?: number;
  pin_id: string;
  pull_client?: ExecutorPullClient;
  ssh_host?: string;
  ssh_port?: number;
  ssh_profile?: ExecutorSshProfile;
  ssh_user?: string;
  timeout_seconds: number;
  transport?: ExecutorTransport;
};

/** A new immutable revision of a group: the full settings, never a patch (`EXEC2-SEAL-2`). Work already admitted on an earlier revision finishes on it. */
export type ReviseExecutorGroupRequest = {
  billing: ExecutorBilling;
  gateway_model: string;
  members: Array<ExecutorGroupMember>;
  pin_id: string;
  strategy?: ExecutorGroupStrategy;
};

export type ReviseStageAssemblyRequest = {
  add_document_uids: Array<DocumentUid>;
  base_member_no: number;
  remove_document_uids: Array<DocumentUid>;
};

/**
 * A new revision: the kit and every cell. Only pairs of the catalogue are accepted; a row of the closed list of block schemes
 * is chosen as a whole. `comparison_cells` (`HOSTS-CMP-01`, optional) are the four kinds of comparison work, each once; left out, a named
 * kit follows its table and `custom` has none.
 */
export type ReviseStageModelLayoutRequest = {
  cells: Array<StageLayoutCell>;
  comparison_cells?: Array<StageComparisonCell>;
  kit: StageModelKit;
};

/** One role an account may hold; an account holds a set of them (R-55, R-60). `expert` makes product changes -- projects, uploads, runs, verdicts, comments and the export. `admin` manages accounts and registration requests. `viewer` (R-150e, R-150x, shown as «Наблюдатель») reads and downloads product data and changes nothing; it does not read the execution queue, journal, workers or executors (R-150w), and it is the only role of an account that holds it: a role set combining it with `expert` or `admin` is refused as `validation_failed` (`constraint: viewer_exclusive`). Reading product data needs one of these roles (R-80): an active account whose role set is empty is suspended and reads only its own account, the product version and the release notes. */
export const ROLE_VALUES = [
  'expert',
  'admin',
  'viewer',
] as const;

/** Role - the closed value set above. */
export type Role = (typeof ROLE_VALUES)[number];

export type RunActivity = {
  by_state: Array<RunStateCount>;
  /** Absent when the deployment has made no provider call. */
  spend?: RunActivitySpend;
};

/** What every run, across every project, has spent at the provider so far. `cost_basis` is `measured` only when every contributing `model_call` row reported a measured cost. */
export type RunActivitySpend = {
  cost_basis: CostBasis;
  cost_micros: number;
  model_call_count: number;
};

/**
 * The expert confirms a fresh estimate (`HOSTS-SEAL-1`, consent v2). The body is the same whatever the route: the digest of
 * the estimate that was shown, the ceiling the person approves and `confirmed`. When every cell of a run on the stage layout
 * runs on a subscription the estimate is 0 and pressing the button that says so is the consent, with `ceiling_micros` 0. The
 * consent the stand stores is built from the estimate the digest names and adds to it the digest of the stage plan and, per
 * model, the digest of the rates and the access it was priced at; a start whose plan or access differs from them is refused.
 */
export type RunCostConsent = {
  ceiling_micros: number;
  confirmed: boolean;
  estimate_digest: Sha256;
};

export type RunCostEstimate = {
  billing: "metered" | "unmetered" | "mixed";
  calls: number;
  computed_stage_ids?: Array<StageId>;
  connection_revision_id?: ExecutorRevisionId;
  currency: "USD";
  estimate_digest: Sha256;
  estimated_cost_micros: number;
  executor_group_id?: ExecutorGroupId;
  executor_group_revision_id?: ExecutorGroupRevisionId;
  input_tokens: number;
  model_id: string;
  models?: Array<RunCostModelLine>;
  output_tokens: number;
  page_count: number;
  pin_id?: string;
  preset_revision_id?: PresetRevisionId;
  provider_mode: ProviderMode;
  recommended_ceiling_micros: number;
  relaxed_limits: boolean;
  reused_stage_ids?: Array<StageId>;
  routing_rule_revision_id?: ExecutorRoutingRuleRevisionId;
  scope: "run";
  stage_plan_digest?: Sha256;
  start_from_run_id?: RunId;
  start_stage_id?: StageId;
  text_characters: number;
  version_uid: VersionUid;
  windows: number;
};

export type RunCostEstimateRequest = {
  executor_connection_id?: ExecutorConnectionId;
  executor_group_id?: ExecutorGroupId;
  preset_id?: PresetId;
  reaudit_of_run_id?: RunId;
  relaxed_limits?: boolean;
  start_from_run_id?: RunId;
  start_stage_id?: StageId;
  version_uid: VersionUid;
};

/**
 * One model of a run on the stage layout, priced (`HOSTS-SEAL-1`, consent v2): the digest of the rates it was priced at and
 * the access, so a start that finds another rate or another access refuses with `cost_estimate_binding_changed`.
 */
export type RunCostModelLine = {
  access: ExecutorModelAccess;
  calls: number;
  estimated_cost_micros: number;
  input_tokens: number;
  model_id: string;
  output_tokens: number;
  rate_sha256: Sha256;
};

/** EXEC-PAR-START-01: which executor a run is on. Identity, display name and pinned model only; never a secret, an address or a probe. */
export type RunExecutor = {
  connection_id: ExecutorConnectionId;
  display_name: string;
  pin_id: string;
};

/**
 * `UI-PARITY-C6`: a run's findings and the portal blocks their evidence sits in, derived on read from the run's text
 * layer geometry, its page inventory and the version's portal blocks (``docs/program/UI-PARITY-01.md``); nothing is
 * stored and the evidence is not changed. One item per published finding of the run, ``portal_block_ids`` empty where
 * no block holds the evidence. ``unlinked_pages`` are the pages of the portal geometry on which no link can be derived
 * (the portal's raster does not describe the PDF page): a block of such a page is **unknown**, never "no findings".
 * ``not_produced`` and no items while the run has no text-layer geometry or the version no portal geometry.
 */
export type RunFindingBlockLinks = {
  items: Array<FindingBlockLink>;
  run_id: RunId;
  status: "produced" | "not_produced";
  unlinked_pages: Array<number>;
  version_uid: VersionUid;
};

export type RunId = string;

/** The contract pattern for `RunId`. Anchored; use with `new RegExp()`. */
export const RUN_ID_PATTERN = "^run_[0-9A-HJKMNP-TV-Z]{26}$";

/** The norms a run's text cites, or the explicit reason that cannot be said. `state` is `ready` when the list was computed; `snapshot_not_pinned` when the run pinned no norms snapshot (none was current when it was created); `text_unavailable` when it has no saved text layer; `too_many_citations` when the text cites more than one answer carries (over 1000 distinct designations, or one longer than 300 characters). Everything after `text_layer_sha256` is present exactly when `state` is `ready`. `unread_pages` are pages with no text layer, on which no citation can be found; `occurrence_count` counts every occurrence, not only the anchors kept. */
export type RunNormReferences = {
  counts?: NormReferenceCounts;
  items?: Array<NormReferenceItem>;
  norms_snapshot_id?: NormsSnapshotId;
  occurrence_count?: number;
  page_count: number;
  run_id: RunId;
  snapshot_document_count?: number;
  state: "ready" | "snapshot_not_pinned" | "text_unavailable" | "too_many_citations";
  text_layer_sha256?: Sha256;
  unread_pages?: Array<number>;
  unrecognised?: Array<NormReferenceUnrecognised>;
  version_uid: VersionUid;
};

/** ANALYSIS-PRESETS-01: the preset revision a run was started with: the preset, the number of the revision and the name it had then (a later rename does not change it). */
export type RunPreset = {
  name: string;
  preset_id: PresetId;
  revision_no: number;
};

/**
 * `EXEC2-SEAL-1` (ADR-0026 decisions 1 and 5), widened by `EXEC2-SEAL-2` (decisions 14 and 15): why work
 * is not running. `executor_at_capacity`: every unit of its executor connection (of every eligible member of
 * its group) is in use. `runner_offline`: the connection is a `pull` connection and no runner of it is online
 * (no eligible member has one). `needs_reconsent`: dispatch found the consent envelope no longer holds and
 * called nothing. `model_unavailable` (`HOSTS-SEAL-1`, ADR-0028 decision 15): a run started on the stage layout waits
 * because no available server can serve a model that one of its cells needs. The persisted `wait_reason` of pending
 * work uses the same words.
 */
export const RUN_QUEUE_REASON_VALUES = [
  'executor_at_capacity',
  'runner_offline',
  'needs_reconsent',
  'model_unavailable',
] as const;

/** RunQueueReason - the closed value set above. */
export type RunQueueReason = (typeof RUN_QUEUE_REASON_VALUES)[number];

/** One chip of the run: the code stage and procedure ids it covers, its plan (empty for a chip that calls no model) and its facts. */
export type RunStage = {
  chip: RunStageChip;
  facts: RunStageFacts;
  plan: Array<RunStageCell>;
  stage_ids: Array<string>;
};

/**
 * One line of a chip's plan: the part it plays (`main`, `leg1`, `leg2`, `judge`), the model and the effort the run froze, and -- for an
 * expert and an administrator -- the access and the server the cell is bound to. `LIMITS-01` (contract 1.49.0): no answer limit and no timeout. Of a run
 * without a stage plan the line has `role` `main`, the model of the run's binding and nothing else it does not know.
 * `access` and `server` are omitted for the viewer («Наблюдатель», `R-150w`); `server` is also absent while the cell is not bound.
 */
export type RunStageCell = {
  access?: ExecutorModelAccess;
  cell_key?: StageCellKey;
  effort?: ModelEffort;
  model_id?: string;
  role: StageCellRole;
  server?: string;
};

/**
 * A chip of a run: a reader's name for the phase or phases of code that do one kind of work. The eight chips in the order the
 * rail draws them -- `preparation` (the three PC-01 preparation stages), `text` (analysis of the text), `blocks` (analysis of the
 * blocks), `cross_check` (the complex cross-check and the parameter passport), `merge` (the deterministic merge), `norms` (the
 * norms), `review` (the critic) and `correction` (the refinement).
 * A chip order is a display order, not the order of the stage graph.
 */
export const RUN_STAGE_CHIP_VALUES = [
  'preparation',
  'text',
  'blocks',
  'cross_check',
  'merge',
  'norms',
  'review',
  'correction',
] as const;

/** RunStageChip - the closed value set above. */
export type RunStageChip = (typeof RUN_STAGE_CHIP_VALUES)[number];

/**
 * What happened on a chip. `started_at` and `finished_at` are the earliest and the latest call of a chip that calls a model, or
 * the times of its stage results (`finished_at` only once the chip has finished, and never from a stage taken from an earlier
 * run). `calls_succeeded` and `calls_failed` count the calls the journal ended, `calls_retried` the calls that repeated an earlier
 * call of the same request (a reply replayed from custody is not a call). `input_tokens`, `output_tokens` and `cost_micros` are
 * the totals of the journal; `subscription_input_tokens` and `subscription_output_tokens` are the part of the tokens served by a
 * subscription (not metered, never in `cost_micros`). `planned` and `completed` are the batches of the extended review's
 * `phase_coverage` and are absent where the review keeps none. `last_error_code` is the code of the stage result that failed or,
 * else, of the latest failed call; `reason` the extended review's reason a procedure did not complete.
 */
export type RunStageFacts = {
  calls_failed: number;
  calls_retried: number;
  calls_succeeded: number;
  completed?: number;
  cost_micros: number;
  finished_at?: string;
  input_tokens: number;
  last_error_code?: string;
  output_tokens: number;
  planned?: number;
  reason?: string;
  reused_from_run_id?: RunId;
  started_at?: string;
  state: RunStageState;
  subscription_input_tokens: number;
  subscription_output_tokens: number;
};

/**
 * Where the plan of the chips comes from. `stage_plan`: the plan the run froze at its start, one cell per row and role.
 * `run_binding`: the run froze none (it started on the route as before), so each chip that calls a model has one line, «модель
 * прогона», from the run's binding -- or from the journal when it has none.
 */
export const RUN_STAGE_PLAN_SOURCE_VALUES = [
  'stage_plan',
  'run_binding',
] as const;

/** RunStagePlanSource - the closed value set above. */
export type RunStagePlanSource = (typeof RUN_STAGE_PLAN_SOURCE_VALUES)[number];

/**
 * How a chip stands. `pending`: not started. `running`: the work is under way (a stage or procedure running, or a call in flight).
 * `done`: completed. `partial`: completed with a typed shortfall. `failed`: refused. `skipped`: not run by decision. `unavailable`:
 * could not run (for example, the corpus is missing).
 */
export const RUN_STAGE_STATE_VALUES = [
  'pending',
  'running',
  'done',
  'partial',
  'failed',
  'skipped',
  'unavailable',
] as const;

/** RunStageState - the closed value set above. */
export type RunStageState = (typeof RUN_STAGE_STATE_VALUES)[number];

/**
 * The stages of a run, plan and fact (`HOSTS-SEAL-2`, ADR-0028): each chip the run has, in the order the rail draws them, with
 * what it was planned to run on and what the journal and the stage results say happened. A chip that no stage result, procedure,
 * plan cell or call mentions is not listed. `state` is the run's own, so a reader knows whether a chip that is `running` is still
 * being worked on. `plan_source` says whether the plans are the run's frozen `stage_plan` or the one line of its binding. The
 * examples are: a run in progress on the stage layout; a finished run's norms chip as the viewer reads it (no `access`, no
 * `server`); and a run that started on the route as before.
 */
export type RunStages = {
  items: Array<RunStage>;
  plan_source: RunStagePlanSource;
  run_id: RunId;
  state: RunState;
};

/**
 * What the one button «Запустить» says (ADR-0028): the route, the kit, every cell with its access, whether the start is
 * possible and, when it is, the digest of the estimate to confirm. `access` is the total: all cells on a subscription (the
 * estimate is 0 and the press of the button is the consent), all on an API key, or mixed (one dialog with the estimate by
 * model). An unavailable cell makes `ready` false and names itself in `cells`.
 *
 * `extended_plan` (contract 1.50.0): the extended plan a start would run under -- `v2`, `v3`, or `null` when the extended analysis is off. Under `v2` the critic and the refinement rows are not called, and a client labels them from this field.
 */
export type RunStartReadiness = {
  access?: "subscription" | "api" | "mixed";
  cells: Array<RunStartReadinessCell>;
  estimate_digest?: Sha256;
  estimated_cost_micros?: number;
  /** `AR-V3-BE-RM-01` (contract 1.50.0): the extended plan a start would run under -- `v2`, `v3`, or `null` when the extended analysis is off (text only). Read from the same server setting the estimate prices with, so it cannot disagree with it. Under `v2` the critic and the refinement rows are not called, and a client labels them from this field. Absent from an answer of a server older than 1.50.0. */
  extended_plan?: "v2" | "v3" | null;
  kit?: StageModelKit;
  ready: boolean;
  recommended_ceiling_micros?: number;
  route: RunStartRoute;
  stage_plan_digest?: Sha256;
};

/**
 * One cell of the plan a start would freeze, with the access it would run with (absent when no server can serve it) and
 * why it cannot be served, if it cannot.
 */
export type RunStartReadinessCell = {
  access?: ExecutorModelAccess;
  available: boolean;
  cell_key: StageCellKey;
  effort: ModelEffort;
  model_id: string;
  reasons: Array<ModelUnavailableReason>;
  role: StageCellRole;
  row: StageRowKey;
};

/** `stage_plan`: the run takes the layout. `legacy`: the layout is off and the run follows the automatic route as before. */
export const RUN_START_ROUTE_VALUES = [
  'stage_plan',
  'legacy',
] as const;

/** RunStartRoute - the closed value set above. */
export type RunStartRoute = (typeof RUN_START_ROUTE_VALUES)[number];

/** The audit_run states of contracts/domain/v1/state-machines.json. The success terminal is `published`; there is no `succeeded` run state. `created` is transient and rarely observed by a client. `cancelled` is declared by the contract and is unreachable in PC-01, which has no cancel command. */
export const RUN_STATE_VALUES = [
  'created',
  'queued',
  'running',
  'validating',
  'published',
  'partial',
  'failed',
  'cancelled',
] as const;

/** RunState - the closed value set above. */
export type RunState = (typeof RUN_STATE_VALUES)[number];

/** How many runs, across every project, currently sit in one state. Every member of `RunState` is present, for the same reason `VerdictCount` states. */
export type RunStateCount = {
  count: number;
  state: RunState;
};

export type RunStatus = {
  analysis_profile_id?: AnalysisProfileId;
  /** `EXEC2-SEAL-2`: the connection revision and model dispatch bound the run to; present exactly when `binding_state` is `bound`. `executor` then names the same connection. */
  binding?: ExecutorBinding;
  /** `EXEC2-SEAL-2` (ADR-0026 decision 12): whether the run's executor was frozen at start (`frozen_at_start`), is still to be chosen (`pending`) or was chosen at dispatch (`bound`). Absent is read as `frozen_at_start`. */
  binding_state?: ExecutorBindingState;
  cost_basis?: CostBasis;
  /** What this run spent at the provider, in millionths of the provider currency unit, as an integer. Never a floating-point money value. It is the sum of `cost_micros` over **every** `model_call` row of this run, including every retry attempt, because the per-run budget ceiling is enforced over the same span. Absent when the run made no provider call at all, which is a different fact from a cost of zero. */
  cost_micros?: number;
  created_at: string;
  /** The explicitly recorded missing or degraded stage set. Non-empty exactly when the run is `partial`; a `published` run carries none. */
  degradation_set?: Array<StageId>;
  /** Ungrounded model items rejected by the grounding gate. They are not findings and appear in no finding list. */
  diagnostic_observation_count?: number;
  /** `UI-A-65` / `UI-B-45` (contract 1.40.0): the run's estimated finish, by the rule and the function of `ExecutionQueueItem.estimated_finish_at` (`R-151u`) -- its job's first attempt plus the median duration of at least three recent completed runs of the same analysis profile and a page count within a quarter of its own. Present only while the run's job is leased or running and has started; absent for a queued, waiting or finished run, and without enough similar history. Never invented; the estimate can already lie in the past for a run that is taking longer than the usual one. */
  estimated_finish_at?: string;
  /** EXEC-PAR-START-01: the executor the run froze at start, read-only: the connection, the name an administrator gave it and the model its frozen revision pins. Null (and omitted) for a run that froze no connection. Nothing about the connection's kind, address, key or probe. */
  executor?: RunExecutor | null;
  /** OD-10: a run left `running` by a crash is reconciled to `failed` with an explicit interrupted reason. There is no `interrupted` state. */
  interrupted_reason?: string | null;
  /** How many provider calls `cost_micros` sums. Published rather than left to be inferred: a reader who cannot see it cannot tell a run answered first time from one that was retried, and the two spent differently. Present exactly when `cost_micros` is. */
  model_call_count?: number;
  /** The verified retrieval set frozen for this v3 run; absent for v1/v2. It must belong to norms_snapshot_id. */
  norm_retrieval_set_id?: NormRetrievalSetId;
  /** W55A-SEAL-01 (R-113, CD-6): the norms snapshot this run pinned when it was created -- the current snapshot at that moment. Absent while no snapshot is current, which until W57 is the expected state of every run. */
  norms_snapshot_id?: NormsSnapshotId;
  /** `EXEC2-SEAL-2`: the group, rule and model admission froze, for a run admitted by a rule or a group (`binding_state` `pending` or `bound`). Omitted for a run whose executor was frozen at start. */
  planned?: ExecutorGroupPlan;
  /** ANALYSIS-PRESETS-01: the preset revision the run was started with, read-only: the preset, the revision number and the name it had then. Null (and omitted) for a run started without a preset, which includes every re-audit. */
  preset?: RunPreset | null;
  project_uid: ProjectUid;
  prompt_bundle_id?: PromptBundleId;
  provider_mode: ProviderMode;
  published_finding_count?: number;
  /** `EXEC2-SEAL-1`: why a `queued` Run is waiting for its executor, derived from the database at read time. Null (and omitted) for a Run that is not waiting for one. A Run admitted by a rule or a group (`binding_state` `pending`) reports its stored `wait_reason` instead and carries no `queue_reason`. */
  queue_reason?: RunQueueReason | null;
  reaudit_of_run_id?: RunId;
  run_id: RunId;
  stages: Array<StageState>;
  start_stage_id?: StageId;
  /** `R-151v` (contract 1.21.0): the display label of the account that started the run; absent for a run created before migration 0051. */
  started_by_label?: string;
  started_by_user_uid?: UserUid;
  started_from_run_id?: RunId;
  state: RunState;
  terminal_at?: string | null;
  /** D-46: safe scalar classifiers saying WHICH dependency a `failed` run terminated on, restricted to the `safe_detail_keys` the domain catalog declares for the code in `terminal_reason`. Present only beside a `terminal_reason`, because the allowlist that bounds these keys is a property of the reported code; absent when there is nothing to say, and never an empty object. The same shape and the same rule as `ErrorEnvelope.details`, applied to a 200 run reading rather than to a failure -- which is why it had to be added at all: a run reading is not an error envelope and carried no detail object. It classifies; it never identifies. No path, object key, URL, credential, token, prompt, payload or host appears here, and no error code was added to the catalog for it. */
  terminal_detail?: {
    [key: string]: string | number | boolean | null;
  };
  /** Caller-safe typed stage failure message; absent on v1 and on runs without a typed failure. Never contains a proxy body, URL, credential, prompt or model payload. */
  terminal_message?: string;
  /** The catalog code a `failed` run terminated with. Null otherwise. */
  terminal_reason?: ErrorCode | null;
  version_uid: VersionUid;
  /** `HOSTS-L1` (contract 1.48.0, `D-660`): the cells of a planned (stage-layout) run that cannot be bound now, each with its model, its access and the cause, in the order of the run's frozen plan. Present only while a `pending` planned run is `queued` and waiting (`wait_reason` is present) and at least one cell has no server to take it; omitted otherwise, and never an empty list. It is read at the time of the status, so it can differ from the stored `wait_reason` by one sweep. The run page uses it to name the model a run waits for. */
  wait_cells?: Array<RunWaitCell>;
  /** `EXEC2-SEAL-2` (ADR-0026 decision 15): why a `pending` run is not dispatched, stored with `waiting_since`. Omitted when the run is not waiting for an executor. */
  wait_reason?: RunQueueReason;
  /** `EXEC2-SEAL-2`: when the run began waiting for the reason in `wait_reason`; present exactly when it is. */
  waiting_since?: string;
};

export type RunStatusPage = {
  items: Array<RunStatus>;
  page: PageInfo;
};

/**
 * `HOSTS-L1` (contract 1.48.0): why one cell of a waiting planned run cannot be bound now. The six words of `ModelUnavailableReason` (no
 * available server for the cell's model and access: switched off, off line, not logged in, the model not verified, cooling down, on no
 * server) and `at_capacity`: a server serves the model and every place for it is taken.
 */
export const RUN_WAIT_CAUSE_VALUES = [
  'host_disabled',
  'host_offline',
  'login_required',
  'model_not_verified',
  'model_cooling_down',
  'not_on_any_server',
  'at_capacity',
] as const;

/** RunWaitCause - the closed value set above. */
export type RunWaitCause = (typeof RUN_WAIT_CAUSE_VALUES)[number];

/**
 * `HOSTS-L1` (contract 1.48.0, `D-660`): a cell of the run's frozen stage plan that has no server to take it now, and why. The model
 * and the access are the plan's own; the cause is read at the moment of the status, from the same evaluation that keeps the run's
 * `wait_reason` true. It names a model and a cause, never a server.
 */
export type RunWaitCell = {
  access: ExecutorModelAccess;
  cause: RunWaitCause;
  cell_key: StageCellKey;
  model_id: string;
};

/**
 * One model the stand offers and one provider that may serve it, as handed to an agent: the efforts it may be asked for
 * and the exact strings an answer may report as its model (no prefix or date-suffix rule).
 */
export type RunnerCatalogueEntry = {
  accepted_reported: Array<string>;
  efforts: Array<ModelEffort>;
  model_id: string;
  provider: ExecutorProvider;
};

/** The authentication state of a client, read only through its official mechanism and reported as a closed enumeration: `valid`, `login_required`, or `unknown` (not installed, or the client offers no official way to tell). Never a credential, a path or an account name. */
export const RUNNER_CLI_AUTH_STATE_VALUES = [
  'valid',
  'login_required',
  'unknown',
] as const;

/** RunnerCliAuthState - the closed value set above. */
export type RunnerCliAuthState = (typeof RUNNER_CLI_AUTH_STATE_VALUES)[number];

/** One client's sanitised health as an agent reports it (`EXEC2-SEAL-1`, ADR-0026 decision 5). */
export type RunnerCliHealth = {
  auth_state: RunnerCliAuthState;
  cli: RunnerCliName;
  installed: boolean;
  version?: string;
};

/** The official command-line clients an agent detects (ADR-0026 decision 8). */
export const RUNNER_CLI_NAME_VALUES = [
  'claude',
  'codex',
] as const;

/** RunnerCliName - the closed value set above. */
export type RunnerCliName = (typeof RUNNER_CLI_NAME_VALUES)[number];

/** How the agent answers a task: it runs a command (`command`) or calls a local OpenAI-compatible endpoint (`endpoint`). */
export const RUNNER_EXECUTION_PROFILE_VALUES = [
  'command',
  'endpoint',
] as const;

/** RunnerExecutionProfile - the closed value set above. */
export type RunnerExecutionProfile = (typeof RUNNER_EXECUTION_PROFILE_VALUES)[number];

/** A capability the agent declares; `images` means it serves tasks that carry images. */
export const RUNNER_FEATURE_VALUES = [
  'images',
] as const;

/** RunnerFeature - the closed value set above. */
export type RunnerFeature = (typeof RUNNER_FEATURE_VALUES)[number];

/**
 * The report was stored on the calling runner token. A host token also gets the catalogue it should check and whether the
 * host is switched on («Использовать»).
 */
export type RunnerHealthAck = {
  catalogue?: Array<RunnerCatalogueEntry>;
  enabled?: boolean;
  recorded_at: string;
};

/** One checked saved PNG, retrievable only by the current runner claim. */
export type RunnerImage = {
  blob_id: RunnerImageBlobId;
  crop_id?: string;
  media_type: "image/png";
  portal_block_id?: PortalBlockId;
  sha256: string;
  size_bytes: number;
};

export type RunnerImageBlobId = string;

/** The contract pattern for `RunnerImageBlobId`. Anchored; use with `new RegExp()`. */
export const RUNNER_IMAGE_BLOB_ID_PATTERN = "^blob_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * What the agent found of the service key file of the direct API providers (diagnostics for the server's details; no key and
 * no path): `ok` (read), `absent` (no file) or `ignored` (the file exists but was not read), with a lower-case `reason` code
 * when it was ignored (`mode_is_not_0600`, `not_owned_by_the_service_user`, `not_a_regular_file`, `unreadable`, `too_large`).
 */
export type RunnerKeyFileReport = {
  reason?: string;
  state: "ok" | "absent" | "ignored";
};

/**
 * One model of a provider as the agent last checked it. `failure_code` is a lower-case code (`login_required`,
 * `quota_exceeded`, `model_not_found`, ...), never the provider's text.
 */
export type RunnerProviderModelState = {
  checked_at: string;
  failure_code?: string;
  model_id: string;
  state: ModelProbeState;
};

/**
 * One provider found on the host: how it is paid for, where its client is and which version, whether it is logged in and
 * the state of each model of the catalogue on it. No secret, no key and no path to a credential.
 *
 * `access` of a command-line client is read from the client's own status command: a subscription login is `subscription`, a
 * login with an API key is `api`; a client that is not signed in is reported `subscription` with `auth_state` `login_required`,
 * and one signed in by a method the agent does not recognise `api` with `auth_state` `unknown` and no verified model. A direct
 * API provider is always `api`: its `auth_state` is `valid` once a model has been verified, `login_required` when the provider
 * refused the key, else `unknown`. `cli_path` is left out unless the operator opted in. `accept_images` says whether the
 * provider can take a task that carries images on this host.
 */
export type RunnerProviderReport = {
  accept_images?: boolean;
  access: ExecutorModelAccess;
  auth_state: ProviderAuthState;
  cli_path?: string;
  cli_version?: string;
  models: Array<RunnerProviderModelState>;
  provider: ExecutorProvider;
};

/**
 * What the API ever says about a runner token after it was issued: that it exists, its
 * non-secret prefix, when it expires or was revoked, and when and from where it was last seen.
 * The value and its hash are never returned.
 *
 * `EXEC2-SEAL-1` (ADR-0026 decision 5): the health an agent last reported on this token, as closed enumerations and bounded strings (no secret, no path to a credential and no document text), and `online`, the freshness of `last_seen_at` under a bounded threshold, read at the time of the request. All of them are absent for a token whose runner has not reported.
 */
export type RunnerTokenMetadata = {
  agent_version?: string;
  clis?: Array<RunnerCliHealth>;
  concurrency?: number;
  connection_id?: ExecutorConnectionId;
  created_at: string;
  created_by: UserUid;
  execution_profile?: RunnerExecutionProfile;
  expires_at: string;
  features?: Array<RunnerFeature>;
  health_reported_at?: string;
  host_id?: ExecutorHostId;
  last_seen_address?: string;
  last_seen_at?: string;
  online?: boolean;
  revoked_at?: string;
  revoked_by?: UserUid;
  token_id: ExecutorRunnerTokenId;
  token_prefix: string;
};

/** The full settings of a preset, for a new preset and for a new revision alike (never a patch). */
export type SaveAnalysisPresetRequest = {
  executor_connection_id: ExecutorConnectionId;
  name: string;
};

/**
 * `R-152g`, `R-152h`: move one or several assignments to a day (``planned_on`` absent: «без даты»), and to another
 * engineer when ``assignee_user_uid`` names one (a reassignment).
 */
export type ScheduleAssignmentsRequest = {
  moves: Array<AssignmentMove>;
};

/** How many published documents carry one project section (`R-40`, `D-56`). `section` absent means this row is the unclassified bucket, not a sixteenth section. Every one of the fifteen current codes is present even at `document_count: 0`. `audit_counts` are the section's documents by audit state (`UI-PARITY-P0B`) and `document_count` equals `audit_counts.document_count`; `finding_count` is the number of published findings of those documents' result runs. */
export type SectionDocumentCount = {
  audit_counts: DocumentAuditCounts;
  document_count: number;
  /** Published findings of the result runs of the section's documents. */
  finding_count: number;
  /** One of the fifteen project sections, or absent when the document has not been classified. */
  section?: ProjectSection;
};

/** All fifteen choices for one version, the current classification or ``null``. */
export type SectionReview = {
  classification: VersionClassification | null;
  options: Array<SectionReviewOption>;
  recognised_text_consulted: boolean;
  revisions: Array<VersionClassificationRevision>;
  version_uid: VersionUid;
};

export type SectionReviewOption = {
  executable: boolean;
  name: string;
  section_code: ProjectSection;
  suggestion: SectionSuggestion | null;
};

/**
 * The combined Form-7 specification of one section, project by project.
 *
 * ``state`` is ``ready`` or ``section_too_large`` with ``limit_reason`` naming the bound that
 * stopped it (``projects`` scanned, member ``sources`` read, ``rows`` held); then the
 * membership is still listed with every set ``not_read`` and ``rows`` is ``null`` -- narrowing
 * to one project (``project_filter``) is the way in. ``excluded`` lists the current versions
 * nobody classified (the first 200; ``excluded_count`` is complete). ``row_count`` counts
 * every row in scope and ``rows.total`` the rows the text search keeps. There is no section
 * total: the totals live in each project's ``matching``.
 */
export type SectionSpecification = {
  excluded: Array<SectionSpecificationExcludedVersion>;
  excluded_count: number;
  extraction_algorithm: "specification-text-v1";
  limit_reason: "projects" | "sources" | "rows" | null;
  match_algorithm: "price-match-v1" | "price-match-v2";
  project_filter: ProjectUid | null;
  projects: Array<SectionSpecificationProject>;
  query: string | null;
  row_count: number;
  rows: SectionSpecificationRowPage | null;
  section_code: ProjectSection;
  source_count: number;
  state: "ready" | "section_too_large";
};

/** A current version that cannot be placed in a section yet: nobody classified it. */
export type SectionSpecificationExcludedVersion = {
  display_title: string;
  document_uid: DocumentUid;
  project_name: string;
  project_uid: ProjectUid;
  reason: "version_unclassified";
  version_ordinal: number;
  version_uid: VersionUid;
};

/**
 * One project with member sets: its price list, its sets and its own totals.
 *
 * ``price_state`` is ``priced`` (the current price-list revision was read), ``price_list_missing``
 * (none uploaded: the rows are served without any match and no figure) or ``not_read`` (over a
 * bound). ``matching`` covers this project's rows only and is ``null`` unless ``priced``; its
 * totals are per currency and never mixed with another project's.
 */
export type SectionSpecificationProject = {
  matching: SpecificationMatching | null;
  name: string;
  price_list: SpecificationPriceListRef | null;
  price_state: "priced" | "price_list_missing" | "not_read";
  project_uid: ProjectUid;
  row_count: number;
  sources: Array<SectionSpecificationSource>;
};

/**
 * One Form-7 row with its full address and, where the project has a price list, its match.
 *
 * ``price_status`` is the match (``matched``, ``ambiguous``, ``unmatched``) or
 * ``price_list_missing`` when the row's project has no price list: then every match field is
 * empty and no price or amount exists. ``amount`` only when the row counts in its project's
 * total for its currency.
 */
export type SectionSpecificationRow = {
  amount: string | null;
  basis: "code" | "mark" | "name" | null;
  candidate_count: number;
  candidate_position_ids: Array<PriceListPositionId>;
  document_uid: DocumentUid;
  excluded_reason: "no_position" | "unit_mismatch" | "row_unit_missing" | "ambiguous" | "quantity_not_numeric" | null;
  group: string | null;
  line_end: number;
  line_start: number;
  mass_text: string | null;
  name: string;
  note: string | null;
  page_number: number;
  position: string | null;
  price_position: SpecificationPricePosition | null;
  price_status: "matched" | "ambiguous" | "unmatched" | "price_list_missing";
  project_uid: ProjectUid;
  quantity: string | null;
  quantity_issue: "not_numeric" | "ambiguous" | null;
  quantity_text: string | null;
  reason: "no_position" | "unit_mismatch" | "row_unit_missing" | "several_positions" | null;
  row_id: string;
  sheet_label: string | null;
  table_ordinal: number;
  unit: "шт" | "м" | "м2" | "м3" | "кг" | "т" | "компл" | "п.м" | null;
  unit_text: string | null;
  version_uid: VersionUid;
};

/** One page of the rows that survive the text search; the counts cover every row. */
export type SectionSpecificationRowPage = {
  items: Array<SectionSpecificationRow>;
  limit: number;
  next_offset: number | null;
  offset: number;
  total: number;
};

/**
 * One document set whose current version is confirmed in the section, and how far it read.
 *
 * ``state`` is ``ready`` when the saved text was read and the rows extracted;
 * ``analysis_missing`` (no published run) and ``text_unavailable`` (a run without a saved
 * text layer) name what is missing; ``specification_too_large`` is the extractor's own row
 * bound; ``not_read`` is a set the answer did not read because it is over a bound
 * (``SectionSpecification.limit_reason``). The extraction facts are ``null`` until read.
 */
export type SectionSpecificationSource = {
  display_title: string;
  document_uid: DocumentUid;
  page_count: number;
  project_stage: ProjectStage;
  row_count: number | null;
  run_id: RunId | null;
  skipped_by_reason: SpecificationSkipCounts | null;
  state: "ready" | "analysis_missing" | "text_unavailable" | "specification_too_large" | "not_read";
  table_count: number | null;
  text_layer_sha256: Sha256 | null;
  version_ordinal: number;
  version_uid: VersionUid;
};

/** Display evidence for one section: never a confirmation and never a route. */
export type SectionSuggestion = {
  filename_patterns: Array<string>;
  name_in_text: boolean;
  score: number;
  text_keywords: Array<string>;
};

/** One section's vendor list as it applies to a project, with both scopes' latest. */
export type SectionVendorList = {
  effective: VendorListRevision | null;
  global_revision: VendorListRevision | null;
  project_revision: VendorListRevision | null;
  section_code: ProjectSection;
  source: VendorListSource;
};

/**
 * ``expected_current`` is the snapshot the caller believes is current, ``null`` when it
 * believes none is; a stale belief is ``conflict`` (``stale_current_snapshot``).
 */
export type SetCurrentNormSnapshotRequest = {
  expected_current: NormsSnapshotId | null;
  norms_snapshot_id: NormsSnapshotId;
};

/** `R-151a` (contract 1.22.0): archive (`true`) or restore (`false`) one document. Nothing is deleted. */
export type SetDocumentArchivedRequest = {
  archived: boolean;
};

/** `R-151e` (contract 1.23.0): the document's whole new set of free tags; an empty list removes them all. */
export type SetDocumentTagsRequest = {
  tags: Array<string>;
};

/** `R-152d`: one engineer's absent days, marked (``absent``) or cleared. */
export type SetEngineerAbsencesRequest = {
  days: Array<EngineerAbsenceChange>;
  user_uid: UserUid;
};

export type SetExecutionPausedRequest = {
  paused: boolean;
};

/** `true` switches the server on, `false` off. A server that is off takes no new run; runs already bound to it finish. */
export type SetExecutorHostEnabledRequest = {
  enabled: boolean;
};

/** The providers whose slots change; at least one. Each change is a journalled event with its author. */
export type SetExecutorHostSlotsRequest = {
  slots: ExecutorHostSlots;
};

/** `true` sets the mark, `false` clears it. Setting an already set mark or clearing an absent one answers the connection as it stands. */
export type SetExecutorIntegrationAuthorisationRequest = {
  authorised: boolean;
};

export type SetExecutorRouteRequest = {
  primary_connection_id: ExecutorConnectionId;
  standby_connection_id?: ExecutorConnectionId;
  work_kind: ExecutorWorkKind;
};

/** Change the routing mode (`EXEC2-SEAL-2`, ADR-0026 decision 17). `rules` is the cut-over and needs the `preview_digest` that was shown and a `mapping` that confirms each `ready` work kind to be converted: the groups, the rules and the mode are created in one transaction. `legacy` is the rollback and takes neither field. Work already admitted by rules finishes on its own group revisions. */
export type SetExecutorRoutingModeRequest = {
  mapping?: Array<ExecutorRoutingMappingEntry>;
  mode: ExecutorRoutingMode;
  preview_digest?: Sha256;
};

/** Point the rule of a work kind at an immutable group revision (`EXEC2-SEAL-2`). The path names the work kind. A group revision other than the current one of an active group is accepted; an archived group's is refused. */
export type SetExecutorRoutingRuleRequest = {
  group_revision_id: ExecutorGroupRevisionId;
};

/** Write-only. The API seals ``value`` to the stand's public key and never returns it. */
export type SetExecutorSecretRequest = {
  purpose: ExecutorSecretPurpose;
  value: string;
};

/** `R-151g`: the new execution status, or `null` to clear it. */
export type SetFindingExecutionStatusRequest = {
  status: FindingExecutionStatus | null;
};

/**
 * `W60-PRICE-LIST-01`. A section's global vendor list, as a whole new revision.
 *
 * ``expected_vendor_list_id``, when present, is the revision the caller read (``null``:
 * there was none); a different latest revision is ``conflict`` and nothing is written.
 */
export type SetGlobalVendorListRequest = {
  entries: Array<VendorListEntry>;
  expected_vendor_list_id?: VendorListId | null;
};

export type SetJobPriorityRequest = {
  priority: number;
};

/**
 * `W60-PRICE-LIST-01`. A project's own vendor list for a section, or its removal.
 *
 * ``mode: inherit`` takes ``entries: []`` and removes the override. ``expected_vendor_list_id``
 * as for :class:`SetGlobalVendorListRequest`, for this project's revisions.
 */
export type SetProjectVendorListRequest = {
  entries: Array<VendorListEntry>;
  expected_vendor_list_id?: VendorListId | null;
  mode: VendorListMode;
};

/**
 * `true` puts the layout in force for runs started from now on (it needs a revision and the database provider source);
 * `false` takes it out. Runs already started keep the plan they froze.
 */
export type SetStageModelLayoutEnabledRequest = {
  enabled: boolean;
};

export type SetStagePairCompletenessRequest = {
  completeness: "full" | "partial";
};

/** `R-152d`: days made days off or working days; ``default`` returns a day to the week's rule. */
export type SetWorkCalendarDaysRequest = {
  days: Array<WorkCalendarDayChange>;
};

/** `R-151x`: the administrator's plans for one month; an engineer not named keeps the plan they have. */
export type SetWorkSchedulePlansRequest = {
  month: string;
  plans: Array<WorkSchedulePlan>;
};

export type SetWorkerIntakeRequest = {
  enabled: boolean;
};

/** Severity. */
export const SEVERITY_VALUES = [
  'critical',
  'economic',
  'operational',
  'recommendation',
  'check_adjacent',
] as const;

/** Severity - the closed value set above. */
export type Severity = (typeof SEVERITY_VALUES)[number];

/** A verification value, never an identity. */
export type Sha256 = string;

/** The contract pattern for `Sha256`. Anchored; use with `new RegExp()`. */
export const SHA256_PATTERN = "^[0-9a-f]{64}$";

export type SheetDiff = {
  added_line_count: number | null;
  evidence_sha256: Sha256 | null;
  hunks: Array<DiffHunk>;
  outcome: "computed" | "too_large";
  removed_line_count: number | null;
  source_line_count: number | null;
  source_page_number: number | null;
  status: "changed" | "removed" | "added";
  target_line_count: number | null;
  target_page_number: number | null;
  too_large_reason: "source_text_too_large" | "source_text_too_many_lines" | "target_text_too_large" | "target_text_too_many_lines" | "text_not_utf8_encodable" | null;
};

/** One page of the sheets with text differences; ``next_offset`` is null on the last. */
export type SheetDiffPage = {
  items: Array<SheetDiff>;
  limit: number;
  next_offset: number | null;
  offset: number;
  total: number;
};

export type SheetLinkId = string;

/** The contract pattern for `SheetLinkId`. Anchored; use with `new RegExp()`. */
export const SHEET_LINK_ID_PATTERN = "^sln_[0-9A-HJKMNP-TV-Z]{26}$";

/** One sheet of either version and its proposed counterpart, if any. */
export type SheetPairing = {
  pairing_basis: "exact_text" | "similar_text" | null;
  shared_line_count: number | null;
  similarity_permille: number | null;
  source_page_number: number | null;
  status: "unchanged" | "changed" | "removed" | "added";
  suggestion_sha256: Sha256 | null;
  target_page_number: number | null;
  textless: boolean;
};

/**
 * `COMPARE-PERSISTED-SUMMARY-01`. The stored approval or withdrawal of one sheet link.
 * ``replayed`` is true when this call appended nothing: the same key repeated, or an exact
 * repeat of an active link under another key.
 */
export type SheetPairingEvent = {
  actor_label: string;
  comparison_id: ComparisonId;
  decided_at: string;
  event_kind: "approved" | "withdrawn";
  link_revision: number;
  raw_evidence_seal_sha256: Sha256 | null;
  replayed: boolean;
  sheet_link_id: SheetLinkId;
  source_page_number: number;
  source_version_uid: VersionUid;
  suggestion_sha256: Sha256;
  target_page_number: number;
  target_version_uid: VersionUid;
};

/** The exact sum of the amounts in one currency; never converted, never rounded. */
export type SpecificationCurrencyTotal = {
  amount: string;
  currency: string;
  row_count: number;
};

/** Rows left out of every total, by the one reason each carries. */
export type SpecificationExclusionCounts = {
  ambiguous: number;
  no_position: number;
  quantity_not_numeric: number;
  row_unit_missing: number;
  unit_mismatch: number;
};

/** What the extractor found: counts complete, listings capped at 200 each. */
export type SpecificationExtractionSummary = {
  algorithm: "specification-text-v1";
  row_count: number;
  skipped: Array<SpecificationSkippedLine>;
  skipped_by_reason: SpecificationSkipCounts;
  skipped_count: number;
  table_count: number;
  tables: Array<SpecificationTable>;
};

export type SpecificationMatchCounts = {
  ambiguous: number;
  matched: number;
  unmatched: number;
};

/** Every row's match counted, the totals per currency and what they leave out. */
export type SpecificationMatching = {
  algorithm: "price-match-v1" | "price-match-v2";
  counts: SpecificationMatchCounts;
  excluded: SpecificationExclusionCounts;
  totals: Array<SpecificationCurrencyTotal>;
};

/** The price-list revision the rows were matched against: the project's current one. */
export type SpecificationPriceListRef = {
  default_currency: string | null;
  position_count: number;
  price_list_id: PriceListId;
  revision_number: number;
  source_filename: string;
  uploaded_at: string;
};

/** The one price-list position a row is matched to, as the price list states it. */
export type SpecificationPricePosition = {
  code: string | null;
  currency: string;
  mark: string | null;
  name: string;
  price_list_position_id: PriceListPositionId;
  row_number: number;
  unit: string;
  unit_price: string;
  vendor: string | null;
};

/** One specification row and its match. ``amount`` only when it counts in a total. */
export type SpecificationPriceRow = {
  amount: string | null;
  basis: "code" | "mark" | "name" | null;
  candidate_count: number;
  candidate_position_ids: Array<PriceListPositionId>;
  excluded_reason: "no_position" | "unit_mismatch" | "row_unit_missing" | "ambiguous" | "quantity_not_numeric" | null;
  group: string | null;
  line_end: number;
  line_start: number;
  mass_text: string | null;
  name: string;
  note: string | null;
  page_number: number;
  position: string | null;
  price_position: SpecificationPricePosition | null;
  quantity: string | null;
  quantity_issue: "not_numeric" | "ambiguous" | null;
  quantity_text: string | null;
  reason: "no_position" | "unit_mismatch" | "row_unit_missing" | "several_positions" | null;
  row_id: string;
  sheet_label: string | null;
  status: "matched" | "ambiguous" | "unmatched";
  table_ordinal: number;
  unit: "шт" | "м" | "м2" | "м3" | "кг" | "т" | "компл" | "п.м" | null;
  unit_text: string | null;
};

/**
 * The priced specification of a set's current version, or the state that stops it.
 *
 * The states are checked in order -- ``version_unclassified``, ``section_not_ar``,
 * ``price_list_missing``, ``analysis_missing``, ``text_unavailable``,
 * ``specification_too_large`` -- and each answer carries the facts read before it stopped. ``section_not_ar`` is kept so that no
 * value is removed, but it is no longer produced: a version confirmed in any of the fifteen
 * sections is read.
 */
export type SpecificationPrices = {
  document_uid: DocumentUid;
  extraction: SpecificationExtractionSummary | null;
  matching: SpecificationMatching | null;
  page_count: number;
  price_list: SpecificationPriceListRef | null;
  project_stage: ProjectStage | null;
  project_uid: ProjectUid;
  rows: SpecificationRowPage | null;
  run_id: RunId | null;
  section_code: ProjectSection | null;
  state: "ready" | "version_unclassified" | "section_not_ar" | "price_list_missing" | "analysis_missing" | "text_unavailable" | "specification_too_large";
  text_layer_sha256: Sha256 | null;
  version_ordinal: number;
  version_uid: VersionUid;
};

/** One page of the rows; the counts and totals always cover every row. */
export type SpecificationRowPage = {
  items: Array<SpecificationPriceRow>;
  limit: number;
  next_offset: number | null;
  offset: number;
  total: number;
};

/** Lines inside detected tables that became neither a row nor part of one, by reason. */
export type SpecificationSkipCounts = {
  anchor_ambiguous: number;
  column_numbering: number;
  continuation_limit: number;
  name_missing: number;
  position_missing: number;
  rows_over_limit: number;
  table_header_ambiguous: number;
  text_before_first_row: number;
};

/** One skipped line: where it is, why, and the start of its text. */
export type SpecificationSkippedLine = {
  excerpt: string;
  line: number;
  page_number: number;
  reason: "table_header_ambiguous" | "text_before_first_row" | "continuation_limit" | "anchor_ambiguous" | "position_missing" | "name_missing" | "column_numbering" | "rows_over_limit";
};

/** One detected specification table: its header lines and the Form-7 columns it names. */
export type SpecificationTable = {
  columns: Array<("position" | "name" | "type_mark" | "code" | "manufacturer" | "unit" | "quantity" | "mass" | "note")>;
  header_line_end: number;
  header_line_start: number;
  implicit_unit: "шт" | "м" | "м2" | "м3" | "кг" | "т" | "компл" | "п.м" | null;
  ordinal: number;
  page_number: number;
  row_count: number;
  status: "parsed" | "header_ambiguous";
};

export type StageAiClassification = {
  cards: Array<StageClassificationCard>;
  classification_id: StageAiClassificationId;
  content_key: Sha256;
  created_at: string;
  group_id: string;
  model_identity: {
    [key: string]: unknown;
  };
  run_id: StageChainRunId;
  source_sha256: Sha256;
  unit_id: StageAiUnitId;
};

export type StageAiClassificationId = string;

/** The contract pattern for `StageAiClassificationId`. Anchored; use with `new RegExp()`. */
export const STAGE_AI_CLASSIFICATION_ID_PATTERN = "^sacls_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageAiClassificationPage = {
  items: Array<StageAiClassification>;
  page: PageInfo;
};

export type StageAiReview = {
  content_key: Sha256;
  created_at: string;
  decisions: Array<StageReviewDecision>;
  group_id: string;
  model_identity: {
    [key: string]: unknown;
  };
  review_id: StageAiReviewId;
  run_id: StageChainRunId;
  source_sha256: Sha256;
  unit_id: StageAiUnitId;
};

export type StageAiReviewId = string;

/** The contract pattern for `StageAiReviewId`. Anchored; use with `new RegExp()`. */
export const STAGE_AI_REVIEW_ID_PATTERN = "^sarev_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageAiReviewPage = {
  items: Array<StageAiReview>;
  page: PageInfo;
};

export type StageAiSynthesis = {
  content_key: Sha256;
  created_at: string;
  model_identity: {
    [key: string]: unknown;
  };
  result: StageSynthesisResult;
  run_id: StageChainRunId;
  synthesis_id: StageAiSynthesisId;
  unit_id: StageAiUnitId;
};

export type StageAiSynthesisId = string;

/** The contract pattern for `StageAiSynthesisId`. Anchored; use with `new RegExp()`. */
export const STAGE_AI_SYNTHESIS_ID_PATTERN = "^sasyn_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageAiSynthesisPage = {
  items: Array<StageAiSynthesis>;
  page: PageInfo;
};

export type StageAiUnitId = string;

/** The contract pattern for `StageAiUnitId`. Anchored; use with `new RegExp()`. */
export const STAGE_AI_UNIT_ID_PATTERN = "^saunit_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageAssembly = {
  assembly_id: StageAssemblyId;
  created_at: string;
  label: string;
  member_revision_no: number;
  members: Array<StageAssemblyMember>;
  project_uid: ProjectUid;
};

export type StageAssemblyId = string;

/** The contract pattern for `StageAssemblyId`. Anchored; use with `new RegExp()`. */
export const STAGE_ASSEMBLY_ID_PATTERN = "^sas_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageAssemblyMember = {
  document_uid: DocumentUid;
  member_no: number;
};

export type StageAtomicEvidenceId = string;

/** The contract pattern for `StageAtomicEvidenceId`. Anchored; use with `new RegExp()`. */
export const STAGE_ATOMIC_EVIDENCE_ID_PATTERN = "^(stf|std|sge)_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageCardEvidence = {
  absence_proven?: boolean;
  box_anchor?: {
    [key: string]: number;
  };
  evidence_id: StageCardEvidenceId;
  kind: "TEXT" | "TABLE" | "GRAPHIC";
  profile_id?: ComparisonPageProfileId;
  side: "left" | "right" | "both";
  source_id: StageAtomicEvidenceId;
};

export type StageCardEvidenceId = string;

/** The contract pattern for `StageCardEvidenceId`. Anchored; use with `new RegExp()`. */
export const STAGE_CARD_EVIDENCE_ID_PATTERN = "^sce_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageCardVerdict = {
  card_id: StageChangeCardId;
  created_at: string;
  decision: "accepted" | "rejected";
  evidence_digest: Sha256;
  reason: string;
  revision_no: number;
  verdict_id: StageCardVerdictId;
};

export type StageCardVerdictId = string;

/** The contract pattern for `StageCardVerdictId`. Anchored; use with `new RegExp()`. */
export const STAGE_CARD_VERDICT_ID_PATTERN = "^cdv_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageCardVerdictInput = {
  card_id: StageChangeCardId;
  decision: "accepted" | "rejected";
  expected_revision: number;
  reason: string;
};

export type StageCardVerdictPage = {
  items: Array<StageCardVerdict>;
  page: PageInfo;
};

export type StageCellKey = string;

/** The contract pattern for `StageCellKey`. Anchored; use with `new RegExp()`. */
export const STAGE_CELL_KEY_PATTERN = "^[a-z][a-z0-9_]{0,63}:(main|leg1|leg2|judge)$";

/** The part of a row a cell plays: `main` (the single answer), `leg1` and `leg2` (the two legs of an ensemble) and `judge`. */
export const STAGE_CELL_ROLE_VALUES = [
  'main',
  'leg1',
  'leg2',
  'judge',
] as const;

/** StageCellRole - the closed value set above. */
export type StageCellRole = (typeof STAGE_CELL_ROLE_VALUES)[number];

export type StageChainBatch = {
  batch_id: StageChainBatchId;
  counts: {
    [key: string]: number;
  };
  created_at: string;
  items: Array<StageChainBatchItem>;
  project_uid: ProjectUid;
  state: "queued" | "running" | "paused" | "completed" | "failed" | "cancelled";
  updated_at: string;
};

export type StageChainBatchId = string;

/** The contract pattern for `StageChainBatchId`. Anchored; use with `new RegExp()`. */
export const STAGE_CHAIN_BATCH_ID_PATTERN = "^scb_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageChainBatchItem = {
  item_id: StageChainBatchItemId;
  link_revision_id: StageLinkRevisionId;
  pair_id: StagePairId;
  position: number;
  run_id?: StageChainRunId;
  state: "queued" | "running" | "completed" | "failed" | "cancelled";
};

export type StageChainBatchItemId = string;

/** The contract pattern for `StageChainBatchItemId`. Anchored; use with `new RegExp()`. */
export const STAGE_CHAIN_BATCH_ITEM_ID_PATTERN = "^scbi_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageChainBatchSelection = {
  consent?: ComparisonAiConsent;
  link_revision_id: StageLinkRevisionId;
  pair_id: StagePairId;
};

export type StageChainRun = {
  ai_job_id?: ComparisonAiJobId;
  batch_id?: string;
  created_at: string;
  effective_link_revision_id?: StageLinkRevisionId;
  engine?: "classic" | "v3_native_text_experimental";
  experimental_progress?: {
    [key: string]: unknown;
  } | null;
  failure_reason?: string;
  input_sha256: Sha256;
  kind?: "deterministic" | "full";
  link_revision_id: StageLinkRevisionId;
  pair_id: StagePairId;
  pause_reason?: string;
  pinned_version_uids: Array<VersionUid>;
  run_id: StageChainRunId;
  stale: boolean;
  state: "queued" | "running" | "paused" | "completed" | "failed" | "cancelled";
  steps: Array<StageChainStep>;
  updated_at: string;
  with_ai?: boolean;
};

export type StageChainRunId = string;

/** The contract pattern for `StageChainRunId`. Anchored; use with `new RegExp()`. */
export const STAGE_CHAIN_RUN_ID_PATTERN = "^crn_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageChainRunPage = {
  items: Array<StageChainRun>;
  page: PageInfo;
};

export type StageChainStep = {
  counts: {
    [key: string]: number;
  };
  finished_at?: string;
  started_at?: string;
  state: "queued" | "running" | "paused" | "completed" | "failed" | "cancelled";
  step_id: StageChainStepId;
  step_no: number;
};

export type StageChainStepId = string;

/** The contract pattern for `StageChainStepId`. Anchored; use with `new RegExp()`. */
export const STAGE_CHAIN_STEP_ID_PATTERN = "^cst_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageChangeCard = {
  after: string;
  before: string;
  card_id: StageChangeCardId;
  card_key: Sha256;
  carried_verdict_ids?: Array<StageCardVerdictId>;
  carryover?: "none" | "full" | "partial" | "stale";
  category: StageChangeCategory;
  class_name: "PROJECT_CHANGE" | "SERVICE_STRUCTURE" | "REVIEW";
  detail_increased?: boolean;
  evidence?: Array<StageCardEvidence>;
  evidence_digest: Sha256;
  evidence_ids: Array<StageAtomicEvidenceId>;
  experimental?: {
    [key: string]: unknown;
  } | null;
  importance?: "high" | "normal" | "unknown";
  materiality?: "material" | "non_material" | "unknown";
  run_id: StageChainRunId;
  stale: boolean;
  system: StageSystem;
  title: string;
  verdict?: StageCardVerdict;
};

export type StageChangeCardId = string;

/** The contract pattern for `StageChangeCardId`. Anchored; use with `new RegExp()`. */
export const STAGE_CHANGE_CARD_ID_PATTERN = "^ccd_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageChangeCardPage = {
  counts: {
    [key: string]: number;
  };
  items: Array<StageChangeCard>;
  page: PageInfo;
};

/** StageChangeCategory. */
export const STAGE_CHANGE_CATEGORY_VALUES = [
  'areas',
  'floors',
  'electrical_load',
  'calculation_method',
  'consumer_composition',
  'room_composition',
  'dimensions',
  'materials',
  'equipment_parameters',
  'system_configuration',
  'fire_safety',
  'designation_rename',
  'administrative',
  'documentation_structure',
  'formatting',
  'other_project',
  'other_service',
  'uncertain',
] as const;

/** StageChangeCategory - the closed value set above. */
export type StageChangeCategory = (typeof STAGE_CHANGE_CATEGORY_VALUES)[number];

export type StageChangeJournal = {
  accepted_count: number;
  ai_hidden_same_count: number;
  ai_service_count: number;
  grouping: "designation" | "section" | "system";
  groups: Array<({
    [key: string]: unknown;
  })>;
  run_id: StageChainRunId;
  stale: boolean;
};

export type StageClassificationCard = {
  card_key: Sha256;
  category: StageChangeCategory;
  class_name: "PROJECT_CHANGE" | "SERVICE_STRUCTURE" | "REVIEW";
  detail_increased?: boolean;
  evidence_digest: Sha256;
  evidence_ids: Array<StageAtomicEvidenceId>;
  importance?: "high" | "normal" | "unknown";
  materiality?: "material" | "non_material" | "unknown";
  model_class?: string;
  policy_reasons?: Array<string>;
  system: StageSystem;
  title: string;
};

/**
 * The settings of one kind of comparison work (`HOSTS-CMP-01`): model and effort. The model and the effort must be a pair of
 * `listModelCatalogue`. A comparison job freezes its cell when it starts. `LIMITS-01` (contract 1.49.0): no answer limit and no
 * timeout per cell -- a call carries no answer cap, and its window is the constant of its kind (`R-153n`, `R-153o`).
 */
export type StageComparisonCell = {
  effort: ModelEffort;
  model_id: string;
  work_kind: ComparisonLayoutKind;
};

export type StageGraphicEvidence = {
  content_key: Sha256;
  graphic_id: StageGraphicEvidenceId;
  left_profile_id?: ComparisonPageProfileId;
  link_item_id: StageLinkItemId;
  reason: string;
  regions?: Array<({
    [key: string]: unknown;
  })>;
  result_id?: ComparisonSheetPairResultId;
  right_profile_id?: ComparisonPageProfileId;
  run_id: StageChainRunId;
  status: "not_checked" | "unreliable" | "reliable";
};

export type StageGraphicEvidenceId = string;

/** The contract pattern for `StageGraphicEvidenceId`. Anchored; use with `new RegExp()`. */
export const STAGE_GRAPHIC_EVIDENCE_ID_PATTERN = "^sge_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageGraphicEvidencePage = {
  items: Array<StageGraphicEvidence>;
  page: PageInfo;
};

/** A canonical stage identity from contracts/analysis/v1/stage-registry.json. PC-01 schedules the first four. */
export const STAGE_ID_VALUES = [
  'source_preparation',
  'page_geometry_extraction',
  'document_context_build',
  'text_analysis',
  'block_analysis',
  'finding_merge',
  'finding_review',
  'finding_correction',
  'norm_verification',
] as const;

/** StageId - the closed value set above. */
export type StageId = (typeof STAGE_ID_VALUES)[number];

/**
 * The settings of one cell (a row and a role): model and effort. The model and the effort must be a pair of `listModelCatalogue`.
 * `LIMITS-01` (contract 1.49.0, `R-153n`, `R-153o`): a cell has no answer limit and no timeout -- no answer cap reaches a model, and a
 * call's timeout is a constant of its row. A request that still names either member is refused (`validation_failed`), not ignored.
 */
export type StageLayoutCell = {
  cell_key: StageCellKey;
  effort: ModelEffort;
  model_id: string;
  role: StageCellRole;
  row: StageRowKey;
};

/**
 * One immutable revision of the layout: the kit and every cell, with its author and time. `comparison_cells` are the cells of the four
 * kinds of comparison work in force (`HOSTS-CMP-01`): what the revision stored, else the table of its kit. They are absent only for a
 * `custom` revision that stored none: a comparison is then refused, never served by a model nobody chose.
 */
export type StageLayoutRevision = {
  cells: Array<StageLayoutCell>;
  comparison_cells?: Array<StageComparisonCell>;
  created_at: string;
  created_by: UserUid;
  kit: StageModelKit;
  layout_revision_id: StageLayoutRevisionId;
  revision_no: number;
};

export type StageLayoutRevisionId = string;

/** The contract pattern for `StageLayoutRevisionId`. Anchored; use with `new RegExp()`. */
export const STAGE_LAYOUT_REVISION_ID_PATTERN = "^slr_[0-9A-HJKMNP-TV-Z]{26}$";

/** One change of the switch «Модели по этапам: включены», with its author. */
export type StageLayoutSwitchEvent = {
  enabled: boolean;
  set_at: string;
  set_by: UserUid;
};

export type StageLinkInput = {
  left_profile_id?: ComparisonPageProfileId;
  relation: "paired" | "only_left" | "only_right";
  right_profile_id?: ComparisonPageProfileId;
};

export type StageLinkItem = {
  confidence: "high" | "manual" | "review" | "automatic_repair" | "unpaired";
  item_id: StageLinkItemId;
  left_profile_id?: ComparisonPageProfileId;
  relation: "paired" | "only_left" | "only_right";
  right_profile_id?: ComparisonPageProfileId;
  row_no: number;
};

export type StageLinkItemId = string;

/** The contract pattern for `StageLinkItemId`. Anchored; use with `new RegExp()`. */
export const STAGE_LINK_ITEM_ID_PATTERN = "^sli_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageLinkRepair = {
  after_revision_id: StageLinkRevisionId;
  before_revision_id: StageLinkRevisionId;
  created_at: string;
  proof: {
    [key: string]: unknown;
  };
  repair_id: StageLinkRepairId;
  run_id: StageChainRunId;
  state: "applied" | "undone" | "superseded";
};

export type StageLinkRepairId = string;

/** The contract pattern for `StageLinkRepairId`. Anchored; use with `new RegExp()`. */
export const STAGE_LINK_REPAIR_ID_PATTERN = "^crp_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageLinkRepairPage = {
  items: Array<StageLinkRepair>;
  page: PageInfo;
};

export type StageLinkRevision = {
  base_revision_id?: StageLinkRevisionId;
  created_at: string;
  input_sha256: Sha256;
  items: Array<StageLinkItem>;
  pair_id: StagePairId;
  revision_id: StageLinkRevisionId;
  revision_no: number;
  source: "expert" | "automatic";
};

export type StageLinkRevisionId = string;

/** The contract pattern for `StageLinkRevisionId`. Anchored; use with `new RegExp()`. */
export const STAGE_LINK_REVISION_ID_PATTERN = "^slk_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageLinkRevisionPage = {
  items: Array<StageLinkRevision>;
  page: PageInfo;
};

/** The set the layout is based on: `claude_only`, `codex_only`, or `custom` (any edit of a set). */
export const STAGE_MODEL_KIT_VALUES = [
  'claude_only',
  'codex_only',
  'custom',
] as const;

/** StageModelKit - the closed value set above. */
export type StageModelKit = (typeof STAGE_MODEL_KIT_VALUES)[number];

/**
 * The layout of models over the analysis stages (ADR-0028). `enabled`: runs started now take the layout; off, they follow
 * the route as before. `current` is the revision in force (absent before the first), `history` the revisions newest first and
 * `switch_journal` the switch events newest first. `unavailable_cell_keys` are the cells of `current` whose model no server can
 * serve now (shown as «нет на серверах»).
 */
export type StageModelLayout = {
  current?: StageLayoutRevision;
  enabled: boolean;
  history: Array<StageLayoutRevision>;
  switch_journal: Array<StageLayoutSwitchEvent>;
  unavailable_cell_keys: Array<StageCellKey>;
};

export type StagePair = {
  assembly_id?: StageAssemblyId;
  completeness: "unknown" | "full" | "partial";
  confirmed_at?: string;
  created_at: string;
  left_document_uid: DocumentUid;
  pair_id: StagePairId;
  project_uid: ProjectUid;
  right_document_uid?: DocumentUid;
  state: "suggested" | "confirmed" | "archived";
};

export type StagePairId = string;

/** The contract pattern for `StagePairId`. Anchored; use with `new RegExp()`. */
export const STAGE_PAIR_ID_PATTERN = "^stp_[0-9A-HJKMNP-TV-Z]{26}$";

export type StagePairPage = {
  items: Array<StagePair>;
  page: PageInfo;
};

export type StagePairSuggestion = {
  left_document_uid: DocumentUid;
  reason: string;
  right_document_uid: DocumentUid;
  score: number;
};

export type StagePairSuggestionPage = {
  items: Array<StagePairSuggestion>;
  page: PageInfo;
};

export type StageProfileText = {
  has_text_layer: boolean;
  height_pt: number;
  page_number: number;
  profile_id: ComparisonPageProfileId;
  scan: boolean;
  version_uid: VersionUid;
  width_pt: number;
  words: Array<StageProfileWord>;
};

export type StageProfileWord = {
  bottom: number;
  text: string;
  top: number;
  x0: number;
  x1: number;
};

export type StageReviewDecision = {
  actual_right_profile_ids?: Array<ComparisonPageProfileId>;
  confidence: "high" | "medium" | "low";
  left_fragment_ids: Array<StageTextFragmentId>;
  model_status?: string;
  policy_reasons?: Array<string>;
  reason: string;
  right_fragment_ids: Array<StageTextFragmentId>;
  status: "SAME" | "MOVED" | "CHANGED" | "REMOVED" | "ADDED" | "UNCERTAIN";
  summary: string;
};

/**
 * A row of the stage layout: the analysis stage whose model is chosen. `text` (analysis of the text), `blocks` (analysis of
 * the blocks), `cross_check` (the complex cross-check and the parameter passport), `norms` (the norms), `review` (the critic)
 * and `correction` (the refinement).
 */
export const STAGE_ROW_KEY_VALUES = [
  'text',
  'blocks',
  'cross_check',
  'norms',
  'review',
  'correction',
] as const;

/** StageRowKey - the closed value set above. */
export type StageRowKey = (typeof STAGE_ROW_KEY_VALUES)[number];

export type StageSheetPassport = {
  building?: string;
  floor?: string;
  level?: string;
  page_number: number;
  profile_id: ComparisonPageProfileId;
  sheet_number?: string;
  sheet_type?: string;
  side: "left" | "right";
  version_uid: VersionUid;
};

export type StageSheetPassportPage = {
  items: Array<StageSheetPassport>;
  page: PageInfo;
};

export type StageSheetSuggestion = {
  confidence: "high" | "review";
  left_profile_id: ComparisonPageProfileId;
  reasons: Array<string>;
  right_profile_id: ComparisonPageProfileId;
  score: number;
};

export type StageSheetSuggestionPage = {
  items: Array<StageSheetSuggestion>;
  page: PageInfo;
};

export type StageState = {
  /** The typed reason a non-succeeded stage carries. Null exactly when the status is `succeeded`. */
  error_code?: string | null;
  finished_at?: string | null;
  stage_id: StageId;
  stage_version?: string;
  started_at?: string | null;
  status: StageStatus;
};

/** StageResult statuses from contracts/analysis/v1. A `succeeded` stage carries no error; every other status carries one. */
export const STAGE_STATUS_VALUES = [
  'succeeded',
  'partial',
  'failed',
  'skipped',
] as const;

/** StageStatus - the closed value set above. */
export type StageStatus = (typeof STAGE_STATUS_VALUES)[number];

export type StageSynthesisResult = {
  change_type: string;
  decision: string;
  evidence_ids: Array<StageAtomicEvidenceId>;
  group_id: string;
  reason: string;
  source_sha256: Sha256;
  title: string;
};

/** StageSystem. */
export const STAGE_SYSTEM_VALUES = [
  'unknown',
  'architecture',
  'structural',
  'electrical',
  'heating_ventilation',
  'water_sewage',
  'fire_protection',
  'low_current',
  'technology',
  'site',
  'other',
] as const;

/** StageSystem - the closed value set above. */
export type StageSystem = (typeof STAGE_SYSTEM_VALUES)[number];

export type StageTextDifference = {
  difference_id: StageTextDifferenceId;
  left_fragment_id?: StageTextFragmentId;
  revision_id: StageLinkRevisionId;
  right_fragment_id?: StageTextFragmentId;
  status: "changed" | "removed" | "added";
};

export type StageTextDifferenceId = string;

/** The contract pattern for `StageTextDifferenceId`. Anchored; use with `new RegExp()`. */
export const STAGE_TEXT_DIFFERENCE_ID_PATTERN = "^std_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageTextDifferencePage = {
  items: Array<StageTextDifference>;
  page: PageInfo;
};

export type StageTextExclusion = {
  exclusion_id: StageTextExclusionId;
  left_fragment_id: StageTextFragmentId;
  proof_kind: "same" | "moved";
  revision_id: StageLinkRevisionId;
  right_fragment_id: StageTextFragmentId;
};

export type StageTextExclusionId = string;

/** The contract pattern for `StageTextExclusionId`. Anchored; use with `new RegExp()`. */
export const STAGE_TEXT_EXCLUSION_ID_PATTERN = "^ste_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageTextExclusionPage = {
  items: Array<StageTextExclusion>;
  page: PageInfo;
};

export type StageTextFragment = {
  box_anchor: {
    [key: string]: number;
  };
  content_key: Sha256;
  fragment_id: StageTextFragmentId;
  pair_id: StagePairId;
  profile_id: ComparisonPageProfileId;
  side: "left" | "right";
  text: string;
};

export type StageTextFragmentId = string;

/** The contract pattern for `StageTextFragmentId`. Anchored; use with `new RegExp()`. */
export const STAGE_TEXT_FRAGMENT_ID_PATTERN = "^stf_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageTextFragmentPage = {
  items: Array<StageTextFragment>;
  page: PageInfo;
};

export type StageTextHint = {
  hint_id: StageTextHintId;
  revision_id: StageLinkRevisionId;
  source_fragment_id: StageTextFragmentId;
  source_side?: "left" | "right";
  target_fragment_id: StageTextFragmentId;
};

export type StageTextHintId = string;

/** The contract pattern for `StageTextHintId`. Anchored; use with `new RegExp()`. */
export const STAGE_TEXT_HINT_ID_PATTERN = "^sth_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageTextHintPage = {
  items: Array<StageTextHint>;
  page: PageInfo;
};

export type StageUpload = {
  candidates: Array<StageUploadCandidate>;
  created_at: string;
  files: Array<StageUploadFile>;
  project_uid: ProjectUid;
  state: "uploading" | "paused" | "admitting" | "completed" | "failed" | "cancelled";
  updated_at: string;
  upload_id: StageUploadId;
};

export type StageUploadCandidate = {
  candidate_id: StageUploadCandidateId;
  confirmed_section?: string;
  confirmed_stage?: "P" | "R";
  designation?: string;
  display_name: string;
  document_uid?: DocumentUid;
  failure_reason?: string;
  file_id: StageUploadFileId;
  member_number: number;
  proposed_section?: string;
  proposed_stage?: "P" | "R";
  state: "proposed" | "confirmed" | "admitting" | "published" | "rejected" | "failed";
  version_uid?: VersionUid;
};

export type StageUploadCandidateId = string;

/** The contract pattern for `StageUploadCandidateId`. Anchored; use with `new RegExp()`. */
export const STAGE_UPLOAD_CANDIDATE_ID_PATTERN = "^suc_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageUploadFile = {
  created_at: string;
  declaration: StageUploadFileDeclaration;
  failure_reason?: string;
  file_id: StageUploadFileId;
  received_bytes: number;
  received_parts: number;
  state: "declared" | "receiving" | "received" | "admitting" | "ready" | "failed" | "cancelled";
  upload_id: StageUploadId;
};

export type StageUploadFileDeclaration = {
  display_name: string;
  media_kind: StageUploadFileKind;
  sha256: Sha256;
  size_bytes: number;
};

export type StageUploadFileId = string;

/** The contract pattern for `StageUploadFileId`. Anchored; use with `new RegExp()`. */
export const STAGE_UPLOAD_FILE_ID_PATTERN = "^suf_[0-9A-HJKMNP-TV-Z]{26}$";

/** StageUploadFileKind. */
export const STAGE_UPLOAD_FILE_KIND_VALUES = [
  'pdf',
  'zip',
] as const;

/** StageUploadFileKind - the closed value set above. */
export type StageUploadFileKind = (typeof STAGE_UPLOAD_FILE_KIND_VALUES)[number];

export type StageUploadId = string;

/** The contract pattern for `StageUploadId`. Anchored; use with `new RegExp()`. */
export const STAGE_UPLOAD_ID_PATTERN = "^stu_[0-9A-HJKMNP-TV-Z]{26}$";

export type StageUploadPage = {
  items: Array<StageUpload>;
  page: PageInfo;
};

export type StageUploadPartReceipt = {
  file_id: StageUploadFileId;
  part_number: number;
  received_bytes: number;
  sha256: Sha256;
  size_bytes: number;
  upload_id: StageUploadId;
};

/** Starts an AI job. Refused before anything is read or written when the versions module is off. */
export type StartComparisonAiJobRequest = {
  consent: ComparisonAiConsent;
};

/**
 * «Запустить» (``restart`` false or absent) or «Описать заново» (``restart`` true: every sheet is
 * described again; a sheet whose content, prompt version and model did not change keeps its stored
 * answer and is not sent).
 */
export type StartComparisonAiSheetChangesRequest = {
  consent: ComparisonAiConsent;
  restart?: boolean;
};

/**
 * «Запустить» (``restart`` false or absent) or «Заново» (``restart`` true: every transition
 * is computed again for the current order; sheet pairs whose content did not change come from
 * the result cache). ``base_order_revision_no`` is the revision of the version order the caller
 * saw (``0`` for none); a mismatch is ``409 conflict`` (``comparison_version_order_stale``).
 */
export type StartComparisonSeriesRequest = {
  base_order_revision_no?: number;
  restart?: boolean;
};

/** `R-151i` (contract 1.42.0): the first stage the new run computes; the earlier stages are taken from the run in the path. */
export type StartRunFromStageRequest = {
  cost_consent?: RunCostConsent;
  stage_id: StageId;
};

export type StartRunRequest = {
  /** The expert confirms a fresh estimate and a sufficient explicit ceiling before this start may spend. The approved cap applies independently of the raised output-limit choice. */
  cost_consent?: RunCostConsent;
  /** EXEC-PAR-START-01: the executor connection this run must be on. Absent: the run follows the global route exactly as before. Present: that connection's current revision is frozen when this release serves it, its current key has a passing probe and it is not archived; otherwise the start is refused and no run exists. Never replaced by the route's standby or by another connection. Part of the payload the idempotency key is compared by. */
  executor_connection_id?: ExecutorConnectionId;
  /** `EXEC2-SEAL-2` (ADR-0026 decisions 12 to 14): an executor group (listExecutorGroups) to admit the run on. Absent: the run is what it was. Present: the group's current revision is read in the start's transaction and the run is admitted with `binding_state` `pending`; the connection is chosen at dispatch. Exclusive with executor_connection_id and preset_id. Part of the payload the idempotency key is compared by. */
  executor_group_id?: ExecutorGroupId;
  /** ANALYSIS-PRESETS-01: a saved preset (listAnalysisPresets) to start the run with. Absent: the run is what it was. Present: the preset's current revision is read in the start's transaction and its executor connection is applied exactly as if executor_connection_id had named it (same usability test, same refusals, no fallback to the standby or to another connection), and the run records the preset revision. Exclusive with executor_connection_id. Part of the payload the idempotency key is compared by, as the preset and not as the connection it resolved to. */
  preset_id?: PresetId;
  /** Defaults to the configured mode. A new served paid start requires fresh confirmed cost consent; the approved cap applies in both output-limit modes. */
  provider_mode?: ProviderMode;
  /** Default off. False requests up to16,000 output tokens; true requests up to64,000 using a distinct immutable profile/bundle. A fresh approved cost cap applies in either mode. Explicit consent may approve more than12 whole-page windows. Historical accepted commands retain their original policy; provider context/output bounds still apply. */
  relaxed_limits?: boolean;
  version_uid: VersionUid;
};

export type StartStageChainBatchRequest = {
  engine?: "classic" | "v3_native_text_experimental";
  selections: Array<StageChainBatchSelection>;
  with_ai?: boolean;
};

export type StartStageChainRunRequest = {
  consent?: ComparisonAiConsent;
  engine?: "classic" | "v3_native_text_experimental";
  link_revision_id: StageLinkRevisionId;
  restart?: boolean;
  with_ai?: boolean;
};

/**
 * ``output_text`` is the bare JSON document (no code fence, no commentary) the task's
 * ``output_schema`` describes. ``model`` is the model that produced it, as the runner declares
 * it: an assertion the stand records as such, and holds equal to the connection's pinned model.
 * The token counts are the runner's own; the call is recorded as unmetered.
 */
export type SubmitExecutorTaskAnswerRequest = {
  access?: ExecutorModelAccess;
  input_tokens?: number;
  model: string;
  output_text: string;
  output_tokens?: number;
  provider?: ExecutorProvider;
  reported_model?: string;
  usage?: ExecutorTaskUsage;
};

/** An application for an account. 1-60 characters of letters, separated by single spaces, hyphens or apostrophes, with no word mixing Cyrillic and Latin letters. Surrounding whitespace and invisible characters are removed before the rule is applied. */
export type SubmitRegistrationRequest = {
  first_name: string;
  last_name: string;
  /** The applicant's e-mail address, which becomes the account's login on approval. Normalised by the server (trimmed, lower-case, ASCII, at most 254 characters). */
  login: string;
  /** Optional; absent when the person has none. */
  middle_name?: string;
  /** The account's future password, held to the deployment's password policy with the applicant's names and e-mail local part added to its blocklist. Stored hashed until the decision, which removes it; it appears in no response body, no error detail and no diagnostic record. */
  password: string;
};

/**
 * `COMPARE-PERSISTED-SUMMARY-01` (B2). One statement of a summary and the changed spans of the
 * approved pairs it cites, each ``<sheet_link_id>:<n>`` (``n`` counts the sheet's non-equal spans
 * from 0), the same identities ``ApprovedDiffHunk.hunk_id`` carries.
 */
export type SummaryStatement = {
  hunk_ids: Array<string>;
  text: string;
};

/** `W61-DISPATCHER-01`. One move along an assignment's history. */
export type TransitionAssignmentRequest = {
  kind: AssignmentTransitionKind;
  new_assignee_user_uid?: UserUid;
  reason?: string;
};

/**
 * «Отменить правку»: reverses the latest applied edit. ``base_revision`` is the revision the
 * caller saw, so an edit made meanwhile by someone else is never undone by mistake.
 */
export type UndoComparisonMatrixEditRequest = {
  base_revision: ComparisonMatrixRevision;
};

export type UndoStageLinkRepairRequest = {
  base_revision_id: StageLinkRevisionId;
};

/** The signed-in account's own names, and -- while its profile is incomplete -- the e-mail address that becomes its login. 1-60 characters of letters, separated by single spaces, hyphens or apostrophes, with no word mixing Cyrillic and Latin letters. Surrounding whitespace and invisible characters are removed before the rule is applied. */
export type UpdateMyProfileRequest = {
  /** Required to complete a profile whose login is not yet an e-mail address; it becomes the login in the same write that stores the names. A complete profile's login is fixed: an `email` other than the current login is `validation_failed` with `details.field: login`. */
  email?: string;
  first_name: string;
  last_name: string;
  /** Optional; absent when the person has none. */
  middle_name?: string;
};

/** An administrator's change of an account's names, its role set, or both. An absent property leaves that half unchanged. */
export type UpdateUserRequest = {
  names?: PersonNames;
  /** The whole new role set, not a delta. Removing a role from oneself is `permission_denied`; leaving no active account holding `admin` is `conflict` with `details.conflict_reason: last_admin`. */
  roles?: Array<Role>;
};

export type UploadDocumentRequest = {
  /** Optional display label. When absent the server derives one for presentation. Neither this nor the uploaded file name is ever an identity. */
  display_title?: string;
  /** One portal bundle: a ZIP holding the PDF, its portal block list and its recognised-text markdown, and optionally the portal HTML and the stamp audit. Temporary statistics intake removes application size and page-count ceilings. */
  file: Blob;
  /** One of the fifteen project sections, or absent when the document has not been classified. */
  section?: ProjectSection;
};

/** The next version of an existing document: one portal bundle and nothing else. There is no title and no section, because a further version takes neither; an undeclared part is refused like any other. */
export type UploadDocumentVersionRequest = {
  /** One portal bundle: a ZIP holding the PDF, its portal block list and its recognised-text markdown, and optionally the portal HTML and the stamp audit. Temporary statistics intake removes application size and page-count ceilings. */
  file: Blob;
};

/**
 * `W60-PRICE-LIST-01`. The multipart body of ``uploadPriceList``.
 *
 * ``file`` is the price list (CSV, or an XLSX whose first sheet is read), at most 10 MiB;
 * ``default_currency`` applies to rows whose currency neither their own cell nor the price
 * column's header names.
 */
export type UploadPriceListRequest = {
  default_currency?: string;
  file: Blob;
};

/** Opaque account identity. An e-mail address is the sign-in identifier and a unique key among active accounts; this is the identity every reference names. */
export type UserUid = string;

/** The contract pattern for `UserUid`. Anchored; use with `new RegExp()`. */
export const USER_UID_PATTERN = "^usr_[0-9A-HJKMNP-TV-Z]{26}$";

/** One entry: the material or equipment group it covers, the allowed vendor, a note. */
export type VendorListEntry = {
  material?: string | null;
  note?: string | null;
  vendor: string;
};

export type VendorListId = string;

/** The contract pattern for `VendorListId`. Anchored; use with `new RegExp()`. */
export const VENDOR_LIST_ID_PATTERN = "^vnl_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * ``list``: these entries apply (none at all is an explicit "no restriction").
 * ``inherit``: a project revision that removes the override; the global list applies.
 */
export const VENDOR_LIST_MODE_VALUES = [
  'list',
  'inherit',
] as const;

/** VendorListMode - the closed value set above. */
export type VendorListMode = (typeof VENDOR_LIST_MODE_VALUES)[number];

/** One immutable revision of a section's vendor list, global or of one project. */
export type VendorListRevision = {
  entries: Array<VendorListEntry>;
  mode: VendorListMode;
  project_uid: ProjectUid | null;
  revision_number: number;
  scope: VendorListScope;
  section_code: ProjectSection;
  set_at: string;
  set_by_user_uid: UserUid;
  vendor_list_id: VendorListId;
};

/** VendorListScope. */
export const VENDOR_LIST_SCOPE_VALUES = [
  'global',
  'project',
] as const;

/** VendorListScope - the closed value set above. */
export type VendorListScope = (typeof VENDOR_LIST_SCOPE_VALUES)[number];

/** Which revision applies to a project's section: its own list, the global one, or none. */
export const VENDOR_LIST_SOURCE_VALUES = [
  'project',
  'global',
  'none',
] as const;

/** VendorListSource - the closed value set above. */
export type VendorListSource = (typeof VENDOR_LIST_SOURCE_VALUES)[number];

/** The current projected verdict. `pending` when the ledger holds no verdict-bearing event, and after a revocation. `needs_manual_review` is declared for the closed union and has no PC-01 producer. */
export const VERDICT_VALUES = [
  'pending',
  'accepted',
  'rejected',
  'needs_manual_review',
] as const;

/** Verdict - the closed value set above. */
export type Verdict = (typeof VERDICT_VALUES)[number];

/** How many findings, across every project, currently stand at one verdict -- every finding of every run, «за всё время» (`R-150q`). This is the history of the deployment's verdicts, not the state of the current documents: it counts findings of older versions and of runs that are no longer the result. The findings that still await a decision on current versions are `DashboardSummary.awaiting_decision_findings`, and the two differ whenever a version has more than one run or a document more than one version. Every member of `Verdict` is present -- a verdict nobody has recorded is `count: 0`, not an absent row. */
export type VerdictCount = {
  count: number;
  verdict: Verdict;
};

/** The page-by-page block markup derived for one version. Carries no crops: `page_geometry_extraction` also publishes a page-crop manifest, and this pipeline renders no visual detection, so that manifest is unconditionally empty and is a separate artifact this operation does not expose. */
export type VersionBlockIndex = {
  /** `len(blocks)`, carried rather than left for a caller to recompute. */
  block_count: number;
  blocks: Array<BlockGeometry>;
  /** The run whose `page_geometry_extraction` result this is. Null exactly when `status` is `not_produced`. */
  produced_by_run_id: RunId | null;
  /** `produced`: a run reached `page_geometry_extraction` and this is its output, `blocks` may still be empty for a version that genuinely has none. `not_produced`: no run of this version has published this artifact yet -- absent, not empty -- and `blocks` is `[]` for that reason instead. */
  status: "produced" | "not_produced";
  /** Binds this block index to the exact prepared text layer its spans index. Null exactly when `status` is `not_produced`. */
  text_layer_sha256: Sha256 | null;
  version_uid: VersionUid;
};

/**
 * `W59-SECTION-SEAL-01`. The persisted, expert-confirmed classification of one version.
 *
 * The original confirmation is stored once (``0024_version_classification``) and never
 * changed. `CLASSIFICATION-CORRECTION-01` (``0028_classification_corrections``): an expert
 * may append corrections, each a numbered ``revision`` (1 is the original); this is the
 * latest revision, or, in the answer to a correction retried after someone corrected again,
 * the revision that request created. ``confirmed_by_user_uid`` and ``confirmed_at`` are those
 * of **that revision** -- who stands behind these values.
 */
export type VersionClassification = {
  confirmed_at: string;
  confirmed_by_user_uid: UserUid;
  project_stage: ProjectStage;
  revision: number;
  section_code: ProjectSection;
  version_uid: VersionUid;
};

/**
 * `CLASSIFICATION-CORRECTION-01`. One entry of a version's classification history.
 *
 * Revision 1 is the original expert confirmation (``reason`` is ``null``); revisions 2..
 * are the corrections, each with the expert who made it, when, and why. Never changed.
 */
export type VersionClassificationRevision = {
  actor_user_uid: UserUid;
  at: string;
  project_stage: ProjectStage;
  reason: string | null;
  revision: number;
  section_code: ProjectSection;
};

/** Two versions of one set compared, or the explicit reason they are not. */
export type VersionComparison = {
  approved_pairs?: ApprovedSheetPairs | null;
  comparison_sha256: Sha256 | null;
  document_uid: DocumentUid;
  findings: FindingComparison | null;
  mode: "version" | "stage";
  outcome: "compared" | "refused";
  project_uid: ProjectUid;
  refusal: ComparisonRefusal | null;
  sheet_diffs: SheetDiffPage | null;
  sheets: Array<SheetPairing>;
  source: ComparedVersion | null;
  source_version_uid: VersionUid;
  target: ComparedVersion | null;
  target_version_uid: VersionUid;
};

/**
 * The deterministic profile of one page of one version (raw evidence, never rewritten by
 * an AI layer). ``reason`` is the typed reason of a ``needs_review`` or ``refused`` page, for
 * example ``RENDER_FAILED``. ``content_key`` is the digest the profile is cached under.
 */
export type VersionPageProfile = {
  algo_version: string;
  annotation_count: number;
  content_key: Sha256;
  has_text_layer: boolean;
  height_pt?: number;
  page_number: number;
  page_profile_id: ComparisonPageProfileId;
  preview_available: boolean;
  raster_height_px?: number;
  raster_width_px?: number;
  reason?: string;
  stamp?: PageStamp;
  status: PageProfileStatus;
  thumbnail_available: boolean;
  vector_line_count: number;
  version_uid: VersionUid;
  width_pt?: number;
  word_count: number;
};

/**
 * The profiles stored for a version, by page number ascending. A page whose profile has not
 * been computed is absent; the version's ``page_count`` says how many pages it has.
 */
export type VersionPageProfilePage = {
  items: Array<VersionPageProfile>;
  page: PageInfo;
};

/** `UI-PARITY-P0O` (contract 1.30.0): one page of a version and the drawing sheet its portal blocks name. */
export type VersionSheetLabel = {
  block_count: number;
  page_label?: number;
  page_number: number;
};

/**
 * `UI-PARITY-P0O`: a version's pages with their sheet labels, as the original's «Лист» column, from the same portal
 * geometry `listVersionPortalBlocks` reads; ``not_produced`` and no items while no run has produced it. A page without a
 * portal block is not listed: a page number is never shown as a sheet.
 */
export type VersionSheetLabelList = {
  items: Array<VersionSheetLabel>;
  status: "produced" | "not_produced";
  version_uid: VersionUid;
};

export type VersionUid = string;

/** The contract pattern for `VersionUid`. Anchored; use with `new RegExp()`. */
export const VERSION_UID_PATTERN = "^ver_[0-9A-HJKMNP-TV-Z]{26}$";

/**
 * How a version reached the product. ``comparison_pdf`` is a plain PDF admitted through
 * comparison without a portal bundle. Ordinary section analysis can use its native PDF text and pages;
 * portal-dependent operations still require a bundle.
 */
export const VERSION_UPLOAD_KIND_VALUES = [
  'portal_bundle',
  'comparison_pdf',
] as const;

/** VersionUploadKind - the closed value set above. */
export type VersionUploadKind = (typeof VERSION_UPLOAD_KIND_VALUES)[number];

/**
 * `COMPARE-PERSISTED-SUMMARY-01`. The comparison view the withdrawing expert was looking at:
 * the text the remaining approved set is sealed over is that view's text.
 */
export type WithdrawSheetPairingRequest = {
  mode: "version" | "stage";
  source_run_id?: RunId;
  target_run_id?: RunId;
};

export type WorkCalendarDayChange = {
  day: string;
  kind: "day_off" | "workday" | "default";
};

/** One day of the schedule; ``override`` says the administrator decided it (`R-152d`), absent for the week's rule. */
export type WorkScheduleDay = {
  day: string;
  day_off: boolean;
  override?: "day_off" | "workday";
};

/** `R-151x`: a document that became «Проверено экспертом» on ``day``, credited to the author of its last verdict. */
export type WorkScheduleDoneDocument = {
  day: string;
  document_title: string;
  document_uid: DocumentUid;
  project_name: string;
  project_uid: ProjectUid;
};

/** One engineer's month: the plan (``plan_is_default`` when the stored default applies), done work and absences. */
export type WorkScheduleEngineer = {
  absences: Array<string>;
  done: Array<WorkScheduleDoneDocument>;
  fact: number;
  label: string;
  plan: number;
  plan_is_default: boolean;
  user_uid: UserUid;
};

/** `UI-PARITY-P0P`: «Выполнено» for one month: an administrator reads every active expert, an expert their own. */
export type WorkScheduleMonth = {
  days: Array<WorkScheduleDay>;
  engineers: Array<WorkScheduleEngineer>;
  month: string;
  settings: WorkScheduleSettings;
};

export type WorkSchedulePlan = {
  planned: number;
  user_uid: UserUid;
};

/** `R-150y`, `R-152e`…`R-152h`: «Календарь запаса» -- open assignments by engineer over the days from ``start``. */
export type WorkScheduleReserve = {
  days: Array<WorkScheduleDay>;
  engineers: Array<WorkScheduleReserveEngineer>;
  start: string;
};

export type WorkScheduleReserveEngineer = {
  items: Array<WorkScheduleReserveItem>;
  label: string;
  user_uid: UserUid;
};

/** `R-152e`: an open assignment of «Диспетчер» and its planned date; ``planned_on`` absent is «без даты». */
export type WorkScheduleReserveItem = {
  assignment_uid: AssignmentUid;
  document_title?: string;
  document_uid?: DocumentUid;
  planned_on?: string;
  project_name: string;
  project_uid: ProjectUid;
  status: AssignmentStatus;
};

/** `R-152b`: the default monthly plan of an engineer without one (initially 20) and the time zone of the days. */
export type WorkScheduleSettings = {
  default_monthly_plan: number;
  time_zone: string;
};

export type WorkerId = string;

/** The contract pattern for `WorkerId`. Anchored; use with `new RegExp()`. */
export const WORKER_ID_PATTERN = "^wrk_[0-9A-HJKMNP-TV-Z]{26}$";

/** The state of one registered worker, derived from its last heartbeat (W54-SEAL-01, plan section 3.6): `online` while it heartbeats, `stale` after 90 seconds without a heartbeat, `offline` after 600 seconds. */
export const WORKER_STATE_VALUES = [
  'online',
  'stale',
  'offline',
] as const;

/** WorkerState - the closed value set above. */
export type WorkerState = (typeof WORKER_STATE_VALUES)[number];
