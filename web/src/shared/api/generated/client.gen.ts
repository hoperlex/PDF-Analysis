/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * One typed function per contract operation. Each is a thin, generated binding onto
 * the hand-written transport in `../transport`, which is the only place in `web/`
 * where an HTTP request is actually made.
 *
 * Produced by `npm --prefix web run api:generate`
 * (web/scripts/generate-api-client.mjs, generator 1.0.0)
 * from contracts/api/v1/openapi.json
 *   AuditManager PC-01 API 1.55.0 (OpenAPI 3.1.0)
 *   sha256 800b870f2e490bdd3ef9356fdce0c74bd6a1f5bc03f17ae04511ab479949b469
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

import type { ApiResponse, RequestOptions } from '../transport';
import { request } from '../transport';
import type {
  AppendComparisonVersionOrderInput,
  AppendComparisonVersionOrderResult,
  AppendDecisionInput,
  AppendDecisionResult,
  AppendPrecedentSettingInput,
  AppendPrecedentSettingResult,
  ApplyComparisonMatrixEditsInput,
  ApplyComparisonMatrixEditsResult,
  ApplyStageCardVerdictsInput,
  ApplyStageCardVerdictsResult,
  ApplyStageSheetMapInput,
  ApplyStageSheetMapResult,
  ApproveRegistrationInput,
  ApproveRegistrationResult,
  ApproveSheetPairingInput,
  ApproveSheetPairingResult,
  ArchiveAnalysisPresetInput,
  ArchiveAnalysisPresetResult,
  ArchiveExecutorConnectionInput,
  ArchiveExecutorConnectionResult,
  ArchiveExecutorGroupInput,
  ArchiveExecutorGroupResult,
  ArchiveExecutorHostInput,
  ArchiveExecutorHostResult,
  ArchiveUserInput,
  ArchiveUserResult,
  CancelComparisonAiPairCheckInput,
  CancelComparisonAiPairCheckResult,
  CancelComparisonAiSheetChangesInput,
  CancelComparisonAiSheetChangesResult,
  CancelComparisonReportInput,
  CancelComparisonReportResult,
  CancelComparisonSeriesInput,
  CancelComparisonSeriesResult,
  CancelComparisonSpecificationInput,
  CancelComparisonSpecificationResult,
  CancelComparisonUploadInput,
  CancelComparisonUploadResult,
  CancelRunInput,
  CancelRunResult,
  CancelStageChainBatchInput,
  CancelStageChainBatchResult,
  CancelStageChainRunInput,
  CancelStageChainRunResult,
  CancelStageUploadInput,
  CancelStageUploadResult,
  CarryOverDecisionInput,
  CarryOverDecisionResult,
  CarryOverProposalDecisionsInput,
  CarryOverProposalDecisionsResult,
  ChangePasswordInput,
  ChangePasswordResult,
  ClaimExecutorTaskInput,
  ClaimExecutorTaskResult,
  ClassifyDocumentVersionInput,
  ClassifyDocumentVersionResult,
  ClearComparisonLaunchQueueInput,
  ClearComparisonLaunchQueueResult,
  CompareDocumentVersionsInput,
  CompareDocumentVersionsResult,
  CompleteComparisonUploadFileInput,
  CompleteComparisonUploadFileResult,
  CompleteStageUploadFileInput,
  CompleteStageUploadFileResult,
  ConfirmComparisonUploadSetInput,
  ConfirmComparisonUploadSetResult,
  ConfirmExecutorAgentInstallHostKeyInput,
  ConfirmExecutorAgentInstallHostKeyResult,
  ConfirmExecutorHostAgentInstallHostKeyInput,
  ConfirmExecutorHostAgentInstallHostKeyResult,
  ConfirmStagePairInput,
  ConfirmStagePairResult,
  ConfirmStageUploadCandidateInput,
  ConfirmStageUploadCandidateResult,
  ContinueComparisonReportInput,
  ContinueComparisonReportResult,
  CorrectVersionClassificationInput,
  CorrectVersionClassificationResult,
  CreateAnalysisPresetInput,
  CreateAnalysisPresetResult,
  CreateAssignmentInput,
  CreateAssignmentResult,
  CreateComparisonReportInput,
  CreateComparisonReportResult,
  CreateComparisonUploadInput,
  CreateComparisonUploadResult,
  CreateExecutorAgentInstallInput,
  CreateExecutorAgentInstallResult,
  CreateExecutorConnectionInput,
  CreateExecutorConnectionResult,
  CreateExecutorGroupInput,
  CreateExecutorGroupResult,
  CreateExecutorHostAgentInstallInput,
  CreateExecutorHostAgentInstallResult,
  CreateProjectInput,
  CreateProjectResult,
  CreateStageAssemblyInput,
  CreateStageAssemblyResult,
  CreateStageReviewCardInput,
  CreateStageReviewCardResult,
  CreateStageUploadInput,
  CreateStageUploadResult,
  DecideOptimisationProposalInput,
  DecideOptimisationProposalResult,
  DeleteComparisonReportInput,
  DeleteComparisonReportResult,
  DeleteRunInput,
  DeleteRunResult,
  DequeueComparisonAiSheetChangesInput,
  DequeueComparisonAiSheetChangesResult,
  DownloadAgentPackageInput,
  DownloadAgentPackageResult,
  EndUserSessionsInput,
  EndUserSessionsResult,
  EnqueueComparisonLaunchInput,
  EnqueueComparisonLaunchResult,
  EstimateComparisonAiPairCheckInput,
  EstimateComparisonAiPairCheckResult,
  EstimateComparisonAiSheetChangesInput,
  EstimateComparisonAiSheetChangesResult,
  EstimateComparisonSheetDescriptionInput,
  EstimateComparisonSheetDescriptionResult,
  EstimateComparisonSpecificationInput,
  EstimateComparisonSpecificationResult,
  EstimateRunCostInput,
  EstimateRunCostResult,
  EstimateStageChainRunInput,
  EstimateStageChainRunResult,
  ExcludeComparisonUploadSetInput,
  ExcludeComparisonUploadSetResult,
  ExportOptimisationProposalsCsvInput,
  ExportOptimisationProposalsCsvResult,
  ExportOptimisationProposalsXlsxInput,
  ExportOptimisationProposalsXlsxResult,
  ExportRunCsvInput,
  ExportRunCsvResult,
  ExportRunXlsxInput,
  ExportRunXlsxResult,
  ExtendExecutorTaskClaimInput,
  ExtendExecutorTaskClaimResult,
  FailExecutorTaskInput,
  FailExecutorTaskResult,
  FinishComparisonAiSheetChangesInput,
  FinishComparisonAiSheetChangesResult,
  FinishComparisonSeriesInput,
  FinishComparisonSeriesResult,
  GenerateComparisonSummaryInput,
  GenerateComparisonSummaryResult,
  GenerateExecutorSshKeyInput,
  GenerateExecutorSshKeyResult,
  GetAssignmentInput,
  GetAssignmentResult,
  GetComparisonAiPairCheckInput,
  GetComparisonAiPairCheckResult,
  GetComparisonAiQueueInput,
  GetComparisonAiQueueResult,
  GetComparisonAiSheetChangesInput,
  GetComparisonAiSheetChangesResult,
  GetComparisonLaunchQueueInput,
  GetComparisonLaunchQueueResult,
  GetComparisonMatrixInput,
  GetComparisonMatrixResult,
  GetComparisonOverviewInput,
  GetComparisonOverviewResult,
  GetComparisonQueueSummaryInput,
  GetComparisonQueueSummaryResult,
  GetComparisonReportInput,
  GetComparisonReportResult,
  GetComparisonSeriesInput,
  GetComparisonSeriesResult,
  GetComparisonSheetDescriptionInput,
  GetComparisonSheetDescriptionResult,
  GetComparisonSheetPairInput,
  GetComparisonSheetPairResult,
  GetComparisonSheetPairSpecPositionsInput,
  GetComparisonSheetPairSpecPositionsResult,
  GetComparisonSpecificationInput,
  GetComparisonSpecificationResult,
  GetComparisonUploadInput,
  GetComparisonUploadResult,
  GetComparisonUploadProposalInput,
  GetComparisonUploadProposalResult,
  GetDashboardSummaryInput,
  GetDashboardSummaryResult,
  GetDecisionMemoryCaseInput,
  GetDecisionMemoryCaseResult,
  GetDecisionMemoryStatusInput,
  GetDecisionMemoryStatusResult,
  GetDocumentVersionInput,
  GetDocumentVersionResult,
  GetEffectiveVendorListsInput,
  GetEffectiveVendorListsResult,
  GetExecutionDispatchInput,
  GetExecutionDispatchResult,
  GetExecutorAgentInstallInput,
  GetExecutorAgentInstallResult,
  GetExecutorConnectionInput,
  GetExecutorConnectionResult,
  GetExecutorGroupInput,
  GetExecutorGroupResult,
  GetExecutorGroupCapacityInput,
  GetExecutorGroupCapacityResult,
  GetExecutorHostInput,
  GetExecutorHostResult,
  GetExecutorHostAgentInstallInput,
  GetExecutorHostAgentInstallResult,
  GetExecutorHostDetailsInput,
  GetExecutorHostDetailsResult,
  GetExecutorTaskContextInput,
  GetExecutorTaskContextResult,
  GetExecutorTaskImageInput,
  GetExecutorTaskImageResult,
  GetExtendedRunReviewInput,
  GetExtendedRunReviewResult,
  GetFindingInput,
  GetFindingResult,
  GetFindingPrecedentsInput,
  GetFindingPrecedentsResult,
  GetMeInput,
  GetMeResult,
  GetNormDocumentInput,
  GetNormDocumentResult,
  GetProductVersionInput,
  GetProductVersionResult,
  GetProjectInput,
  GetProjectResult,
  GetQualityTableInput,
  GetQualityTableResult,
  GetRunNormReferencesInput,
  GetRunNormReferencesResult,
  GetRunPrecedentsInput,
  GetRunPrecedentsResult,
  GetRunStagesInput,
  GetRunStagesResult,
  GetRunStartReadinessInput,
  GetRunStartReadinessResult,
  GetRunStatusInput,
  GetRunStatusResult,
  GetSectionSpecificationInput,
  GetSectionSpecificationResult,
  GetSpecificationPricesInput,
  GetSpecificationPricesResult,
  GetStageAssemblyInput,
  GetStageAssemblyResult,
  GetStageChainBatchInput,
  GetStageChainBatchResult,
  GetStageChainRunInput,
  GetStageChainRunResult,
  GetStageChangeCardInput,
  GetStageChangeCardResult,
  GetStageChangeJournalInput,
  GetStageChangeJournalResult,
  GetStageModelLayoutInput,
  GetStageModelLayoutResult,
  GetStagePairInput,
  GetStagePairResult,
  GetStageProfileTextInput,
  GetStageProfileTextResult,
  GetStageSheetMapInput,
  GetStageSheetMapResult,
  GetStageSheetMapRevisionInput,
  GetStageSheetMapRevisionResult,
  GetStageSynthesisInput,
  GetStageSynthesisResult,
  GetStageUploadInput,
  GetStageUploadResult,
  GetUserInput,
  GetUserResult,
  GetVectorControlInput,
  GetVectorControlResult,
  GetVersionBlocksInput,
  GetVersionBlocksResult,
  GetVersionPageProfileInput,
  GetVersionPageProfileResult,
  GetVersionPageSpecPositionsInput,
  GetVersionPageSpecPositionsResult,
  GetVersionSectionReviewInput,
  GetVersionSectionReviewResult,
  GetWorkScheduleInput,
  GetWorkScheduleResult,
  GetWorkScheduleReserveInput,
  GetWorkScheduleReserveResult,
  ImportComparisonZipInput,
  ImportComparisonZipResult,
  ImportOptimisationProposalDecisionsInput,
  ImportOptimisationProposalDecisionsResult,
  ImportRunDecisionsInput,
  ImportRunDecisionsResult,
  IssueExecutorEnrollmentInput,
  IssueExecutorEnrollmentResult,
  IssueExecutorHostEnrollmentInput,
  IssueExecutorHostEnrollmentResult,
  IssueRunnerTokenInput,
  IssueRunnerTokenResult,
  IssueTokenInput,
  IssueTokenResult,
  ListAcceptedOptimisationProposalsInput,
  ListAcceptedOptimisationProposalsResult,
  ListAnalysisPresetsInput,
  ListAnalysisPresetsResult,
  ListAnalysisProfilesInput,
  ListAnalysisProfilesResult,
  ListAssignmentsInput,
  ListAssignmentsResult,
  ListAuthEventsInput,
  ListAuthEventsResult,
  ListComparisonAiLinksInput,
  ListComparisonAiLinksResult,
  ListComparisonAiPairHintsInput,
  ListComparisonAiPairHintsResult,
  ListComparisonMatrixEditsInput,
  ListComparisonMatrixEditsResult,
  ListComparisonReportsInput,
  ListComparisonReportsResult,
  ListComparisonReviewSheetsInput,
  ListComparisonReviewSheetsResult,
  ListComparisonSeriesInput,
  ListComparisonSeriesResult,
  ListComparisonSheetDescriptionHistoryInput,
  ListComparisonSheetDescriptionHistoryResult,
  ListComparisonSheetPairsInput,
  ListComparisonSheetPairsResult,
  ListComparisonSpecificationChangesInput,
  ListComparisonSpecificationChangesResult,
  ListComparisonSpecificationsInput,
  ListComparisonSpecificationsResult,
  ListComparisonUploadsInput,
  ListComparisonUploadsResult,
  ListComparisonVersionOrdersInput,
  ListComparisonVersionOrdersResult,
  ListDecisionHistoryInput,
  ListDecisionHistoryResult,
  ListDecisionMemoryCasesInput,
  ListDecisionMemoryCasesResult,
  ListDecisionPatternsInput,
  ListDecisionPatternsResult,
  ListDecisionsInput,
  ListDecisionsResult,
  ListDocumentTagsInput,
  ListDocumentTagsResult,
  ListDocumentsInput,
  ListDocumentsResult,
  ListExecutionJournalInput,
  ListExecutionJournalResult,
  ListExecutionQueueInput,
  ListExecutionQueueResult,
  ListExecutorConnectionsInput,
  ListExecutorConnectionsResult,
  ListExecutorGroupsInput,
  ListExecutorGroupsResult,
  ListExecutorHostsInput,
  ListExecutorHostsResult,
  ListExecutorRoutesInput,
  ListExecutorRoutesResult,
  ListExecutorRoutingRulesInput,
  ListExecutorRoutingRulesResult,
  ListKnowledgeBaseEntriesInput,
  ListKnowledgeBaseEntriesResult,
  ListModelCatalogueInput,
  ListModelCatalogueResult,
  ListNormDocumentsInput,
  ListNormDocumentsResult,
  ListNormParagraphsInput,
  ListNormParagraphsResult,
  ListNormSnapshotEventsInput,
  ListNormSnapshotEventsResult,
  ListNormSnapshotsInput,
  ListNormSnapshotsResult,
  ListOptimisationPassesInput,
  ListOptimisationPassesResult,
  ListOptimisationProposalsInput,
  ListOptimisationProposalsResult,
  ListPrecedentSettingsInput,
  ListPrecedentSettingsResult,
  ListPriceListPositionsInput,
  ListPriceListPositionsResult,
  ListPriceListRevisionsInput,
  ListPriceListRevisionsResult,
  ListProjectsInput,
  ListProjectsResult,
  ListProposalDecisionJournalInput,
  ListProposalDecisionJournalResult,
  ListProposalDecisionsInput,
  ListProposalDecisionsResult,
  ListRegistrationsInput,
  ListRegistrationsResult,
  ListReleasesInput,
  ListReleasesResult,
  ListRunFindingBlocksInput,
  ListRunFindingBlocksResult,
  ListRunFindingsInput,
  ListRunFindingsResult,
  ListRunsInput,
  ListRunsResult,
  ListStageAiReviewsInput,
  ListStageAiReviewsResult,
  ListStageCardVerdictsInput,
  ListStageCardVerdictsResult,
  ListStageChainRunsInput,
  ListStageChainRunsResult,
  ListStageChangeCardsInput,
  ListStageChangeCardsResult,
  ListStageClassificationsInput,
  ListStageClassificationsResult,
  ListStageGraphicEvidenceInput,
  ListStageGraphicEvidenceResult,
  ListStageLinkRepairsInput,
  ListStageLinkRepairsResult,
  ListStagePairSuggestionsInput,
  ListStagePairSuggestionsResult,
  ListStagePairsInput,
  ListStagePairsResult,
  ListStageRawDifferencesInput,
  ListStageRawDifferencesResult,
  ListStageSheetMapHistoryInput,
  ListStageSheetMapHistoryResult,
  ListStageSheetPassportsInput,
  ListStageSheetPassportsResult,
  ListStageSheetSuggestionsInput,
  ListStageSheetSuggestionsResult,
  ListStageTextExclusionsInput,
  ListStageTextExclusionsResult,
  ListStageTextFragmentsInput,
  ListStageTextFragmentsResult,
  ListStageTextHintsInput,
  ListStageTextHintsResult,
  ListStageUploadsInput,
  ListStageUploadsResult,
  ListUsersInput,
  ListUsersResult,
  ListVersionPageProfilesInput,
  ListVersionPageProfilesResult,
  ListVersionPortalBlocksInput,
  ListVersionPortalBlocksResult,
  ListVersionSheetLabelsInput,
  ListVersionSheetLabelsResult,
  ListVersionsInput,
  ListVersionsResult,
  ListWorkersInput,
  ListWorkersResult,
  MarkReleaseNotesReadInput,
  MarkReleaseNotesReadResult,
  PauseComparisonAiPairCheckInput,
  PauseComparisonAiPairCheckResult,
  PauseComparisonAiSheetChangesInput,
  PauseComparisonAiSheetChangesResult,
  PauseComparisonLaunchQueueInput,
  PauseComparisonLaunchQueueResult,
  PauseComparisonSeriesInput,
  PauseComparisonSeriesResult,
  PauseComparisonUploadInput,
  PauseComparisonUploadResult,
  PauseStageChainBatchInput,
  PauseStageChainBatchResult,
  PauseStageUploadInput,
  PauseStageUploadResult,
  PrepareComparisonClientReportInput,
  PrepareComparisonClientReportResult,
  PrepareComparisonMatrixInput,
  PrepareComparisonMatrixResult,
  PreviewExecutorRoutingInput,
  PreviewExecutorRoutingResult,
  PurgeUserInput,
  PurgeUserResult,
  ReadRegistrationStatusInput,
  ReadRegistrationStatusResult,
  ReauditRunInput,
  ReauditRunResult,
  RebuildComparisonReportPdfInput,
  RebuildComparisonReportPdfResult,
  RecomputeStageTextEvidenceInput,
  RecomputeStageTextEvidenceResult,
  RedeemExecutorEnrollmentInput,
  RedeemExecutorEnrollmentResult,
  RejectRegistrationInput,
  RejectRegistrationResult,
  RejectStageUploadCandidateInput,
  RejectStageUploadCandidateResult,
  RemoveComparisonLaunchEntryInput,
  RemoveComparisonLaunchEntryResult,
  RenameDocumentInput,
  RenameDocumentResult,
  ReportRunnerHealthInput,
  ReportRunnerHealthResult,
  RequestExecutorProbeInput,
  RequestExecutorProbeResult,
  ResetUserPasswordInput,
  ResetUserPasswordResult,
  RestoreDecisionMemoryCaseInput,
  RestoreDecisionMemoryCaseResult,
  RestoreUserInput,
  RestoreUserResult,
  ResumeComparisonAiPairCheckInput,
  ResumeComparisonAiPairCheckResult,
  ResumeComparisonAiSheetChangesInput,
  ResumeComparisonAiSheetChangesResult,
  ResumeComparisonLaunchQueueInput,
  ResumeComparisonLaunchQueueResult,
  ResumeComparisonSeriesInput,
  ResumeComparisonSeriesResult,
  ResumeComparisonUploadInput,
  ResumeComparisonUploadResult,
  ResumeStageChainBatchInput,
  ResumeStageChainBatchResult,
  ResumeStageChainRunInput,
  ResumeStageChainRunResult,
  ResumeStageUploadInput,
  ResumeStageUploadResult,
  RetryComparisonAiSheetChangesInput,
  RetryComparisonAiSheetChangesResult,
  RetryComparisonUploadSetInput,
  RetryComparisonUploadSetResult,
  ReviewDecisionPatternInput,
  ReviewDecisionPatternResult,
  ReviseAnalysisPresetInput,
  ReviseAnalysisPresetResult,
  ReviseExecutorConnectionInput,
  ReviseExecutorConnectionResult,
  ReviseExecutorGroupInput,
  ReviseExecutorGroupResult,
  ReviseStageAssemblyInput,
  ReviseStageAssemblyResult,
  ReviseStageModelLayoutInput,
  ReviseStageModelLayoutResult,
  RevokeRunnerTokenInput,
  RevokeRunnerTokenResult,
  ScheduleAssignmentsInput,
  ScheduleAssignmentsResult,
  SearchNormsInput,
  SearchNormsResult,
  SetCurrentNormSnapshotInput,
  SetCurrentNormSnapshotResult,
  SetDocumentArchivedInput,
  SetDocumentArchivedResult,
  SetDocumentTagsInput,
  SetDocumentTagsResult,
  SetEngineerAbsencesInput,
  SetEngineerAbsencesResult,
  SetExecutionPausedInput,
  SetExecutionPausedResult,
  SetExecutorHostEnabledInput,
  SetExecutorHostEnabledResult,
  SetExecutorHostSlotsInput,
  SetExecutorHostSlotsResult,
  SetExecutorIntegrationAuthorisationInput,
  SetExecutorIntegrationAuthorisationResult,
  SetExecutorRouteInput,
  SetExecutorRouteResult,
  SetExecutorRoutingModeInput,
  SetExecutorRoutingModeResult,
  SetExecutorRoutingRuleInput,
  SetExecutorRoutingRuleResult,
  SetExecutorSecretInput,
  SetExecutorSecretResult,
  SetFindingExecutionStatusInput,
  SetFindingExecutionStatusResult,
  SetGlobalVendorListInput,
  SetGlobalVendorListResult,
  SetJobPriorityInput,
  SetJobPriorityResult,
  SetProjectVendorListInput,
  SetProjectVendorListResult,
  SetStageModelLayoutEnabledInput,
  SetStageModelLayoutEnabledResult,
  SetStagePairCompletenessInput,
  SetStagePairCompletenessResult,
  SetVectorPausedInput,
  SetVectorPausedResult,
  SetWorkCalendarDaysInput,
  SetWorkCalendarDaysResult,
  SetWorkSchedulePlansInput,
  SetWorkSchedulePlansResult,
  SetWorkScheduleSettingsInput,
  SetWorkScheduleSettingsResult,
  SetWorkerIntakeInput,
  SetWorkerIntakeResult,
  StartComparisonAiPairCheckInput,
  StartComparisonAiPairCheckResult,
  StartComparisonAiSheetChangesInput,
  StartComparisonAiSheetChangesResult,
  StartComparisonReportInput,
  StartComparisonReportResult,
  StartComparisonSeriesInput,
  StartComparisonSeriesResult,
  StartComparisonSheetDescriptionInput,
  StartComparisonSheetDescriptionResult,
  StartComparisonSpecificationInput,
  StartComparisonSpecificationResult,
  StartOptimisationPassInput,
  StartOptimisationPassResult,
  StartRunInput,
  StartRunResult,
  StartRunFromStageInput,
  StartRunFromStageResult,
  StartStageChainBatchInput,
  StartStageChainBatchResult,
  StartStageChainRunInput,
  StartStageChainRunResult,
  StreamComparisonPairTileInput,
  StreamComparisonPairTileResult,
  StreamComparisonReportPdfInput,
  StreamComparisonReportPdfResult,
  StreamComparisonReportSourceMdInput,
  StreamComparisonReportSourceMdResult,
  StreamComparisonSeriesSummaryInput,
  StreamComparisonSeriesSummaryResult,
  StreamComparisonSheetDescriptionMdInput,
  StreamComparisonSheetDescriptionMdResult,
  StreamComparisonTechnicalReportInput,
  StreamComparisonTechnicalReportResult,
  StreamDocumentVersionContentInput,
  StreamDocumentVersionContentResult,
  StreamNormDocumentContentInput,
  StreamNormDocumentContentResult,
  StreamStageChangeJournalHtmlInput,
  StreamStageChangeJournalHtmlResult,
  StreamStageChangeJournalPdfInput,
  StreamStageChangeJournalPdfResult,
  StreamStageChangeJournalXlsxInput,
  StreamStageChangeJournalXlsxResult,
  StreamVersionPagePreviewInput,
  StreamVersionPagePreviewResult,
  StreamVersionPageThumbnailInput,
  StreamVersionPageThumbnailResult,
  StreamVersionPageTileInput,
  StreamVersionPageTileResult,
  StreamVersionPortalBlockCropInput,
  StreamVersionPortalBlockCropResult,
  SubmitExecutorTaskAnswerInput,
  SubmitExecutorTaskAnswerResult,
  SubmitRegistrationInput,
  SubmitRegistrationResult,
  TransitionAssignmentInput,
  TransitionAssignmentResult,
  UndoComparisonMatrixEditInput,
  UndoComparisonMatrixEditResult,
  UndoStageLinkRepairInput,
  UndoStageLinkRepairResult,
  UpdateMyProfileInput,
  UpdateMyProfileResult,
  UpdateUserInput,
  UpdateUserResult,
  UploadComparisonReportSourceInput,
  UploadComparisonReportSourceResult,
  UploadComparisonUploadPartInput,
  UploadComparisonUploadPartResult,
  UploadDocumentInput,
  UploadDocumentResult,
  UploadDocumentVersionInput,
  UploadDocumentVersionResult,
  UploadPriceListInput,
  UploadPriceListResult,
  UploadStageUploadPartInput,
  UploadStageUploadPartResult,
  WithdrawDecisionMemoryCaseInput,
  WithdrawDecisionMemoryCaseResult,
  WithdrawSheetPairingInput,
  WithdrawSheetPairingResult,
} from './operations.gen';
import { OPERATIONS } from './operations.gen';

/**
 * Append a revision of the comparison order of a document set.
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/comparison-version-orders` - a write; carries a required Idempotency-Key.
 */
export function appendComparisonVersionOrder(
  input: AppendComparisonVersionOrderInput,
  options?: RequestOptions,
): Promise<ApiResponse<AppendComparisonVersionOrderResult>> {
  return request<AppendComparisonVersionOrderResult>(OPERATIONS.appendComparisonVersionOrder, input, options);
}

/**
 * Append one expert decision event.
 *
 * `POST /findings/{finding_uid}/decisions` - a write; carries a required Idempotency-Key.
 */
export function appendDecision(
  input: AppendDecisionInput,
  options?: RequestOptions,
): Promise<ApiResponse<AppendDecisionResult>> {
  return request<AppendDecisionResult>(OPERATIONS.appendDecision, input, options);
}

/**
 * Append Precedent Setting
 *
 * `POST /precedent-settings` - a write; carries a required Idempotency-Key.
 */
export function appendPrecedentSetting(
  input: AppendPrecedentSettingInput,
  options?: RequestOptions,
): Promise<ApiResponse<AppendPrecedentSettingResult>> {
  return request<AppendPrecedentSettingResult>(OPERATIONS.appendPrecedentSetting, input, options);
}

/**
 * Apply a drafted batch of manual matrix edits.
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits` - a write; carries a required Idempotency-Key.
 */
export function applyComparisonMatrixEdits(
  input: ApplyComparisonMatrixEditsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ApplyComparisonMatrixEditsResult>> {
  return request<ApplyComparisonMatrixEditsResult>(OPERATIONS.applyComparisonMatrixEdits, input, options);
}

/**
 * Apply Verdicts
 *
 * `POST /stage-chain-runs/{stage_chain_run_id}/card-verdicts` - a write; carries a required Idempotency-Key.
 */
export function applyStageCardVerdicts(
  input: ApplyStageCardVerdictsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ApplyStageCardVerdictsResult>> {
  return request<ApplyStageCardVerdictsResult>(OPERATIONS.applyStageCardVerdicts, input, options);
}

/**
 * Apply Stage Sheet Map
 *
 * `POST /stage-pairs/{stage_pair_id}/sheet-map` - a write; carries a required Idempotency-Key.
 */
export function applyStageSheetMap(
  input: ApplyStageSheetMapInput,
  options?: RequestOptions,
): Promise<ApiResponse<ApplyStageSheetMapResult>> {
  return request<ApplyStageSheetMapResult>(OPERATIONS.applyStageSheetMap, input, options);
}

/**
 * Approve a registration request and create the account.
 *
 * `POST /registrations/{request_id}/approve` - a write; carries a required Idempotency-Key.
 */
export function approveRegistration(
  input: ApproveRegistrationInput,
  options?: RequestOptions,
): Promise<ApiResponse<ApproveRegistrationResult>> {
  return request<ApproveRegistrationResult>(OPERATIONS.approveRegistration, input, options);
}

/**
 * Approve Sheet Pairing
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings` - a write; carries a required Idempotency-Key.
 */
export function approveSheetPairing(
  input: ApproveSheetPairingInput,
  options?: RequestOptions,
): Promise<ApiResponse<ApproveSheetPairingResult>> {
  return request<ApproveSheetPairingResult>(OPERATIONS.approveSheetPairing, input, options);
}

/**
 * Archive an analysis preset.
 *
 * `POST /analysis/presets/{preset_id}/archive` - a write; carries a required Idempotency-Key.
 */
export function archiveAnalysisPreset(
  input: ArchiveAnalysisPresetInput,
  options?: RequestOptions,
): Promise<ApiResponse<ArchiveAnalysisPresetResult>> {
  return request<ArchiveAnalysisPresetResult>(OPERATIONS.archiveAnalysisPreset, input, options);
}

/**
 * Archive Executor Connection
 *
 * `POST /executor-connections/{connection_id}/archive` - a write; carries a required Idempotency-Key.
 */
export function archiveExecutorConnection(
  input: ArchiveExecutorConnectionInput,
  options?: RequestOptions,
): Promise<ApiResponse<ArchiveExecutorConnectionResult>> {
  return request<ArchiveExecutorConnectionResult>(OPERATIONS.archiveExecutorConnection, input, options);
}

/**
 * Archive Executor Group
 *
 * `POST /executor-groups/{group_id}/archive` - a write; carries a required Idempotency-Key.
 */
export function archiveExecutorGroup(
  input: ArchiveExecutorGroupInput,
  options?: RequestOptions,
): Promise<ApiResponse<ArchiveExecutorGroupResult>> {
  return request<ArchiveExecutorGroupResult>(OPERATIONS.archiveExecutorGroup, input, options);
}

/**
 * Archive Executor Host
 *
 * `POST /executor-hosts/{host_id}/archive` - a write; carries a required Idempotency-Key.
 */
export function archiveExecutorHost(
  input: ArchiveExecutorHostInput,
  options?: RequestOptions,
): Promise<ApiResponse<ArchiveExecutorHostResult>> {
  return request<ArchiveExecutorHostResult>(OPERATIONS.archiveExecutorHost, input, options);
}

/**
 * Archive an account.
 *
 * `POST /users/{user_uid}/archive`.
 */
export function archiveUser(
  input: ArchiveUserInput,
  options?: RequestOptions,
): Promise<ApiResponse<ArchiveUserResult>> {
  return request<ArchiveUserResult>(OPERATIONS.archiveUser, input, options);
}

/**
 * Cancel an AI check of pairs.
 *
 * `POST /comparison-ai-pair-checks/{comparison_ai_job_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelComparisonAiPairCheck(
  input: CancelComparisonAiPairCheckInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelComparisonAiPairCheckResult>> {
  return request<CancelComparisonAiPairCheckResult>(OPERATIONS.cancelComparisonAiPairCheck, input, options);
}

/**
 * Cancel an AI description of changes.
 *
 * `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelComparisonAiSheetChanges(
  input: CancelComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelComparisonAiSheetChangesResult>> {
  return request<CancelComparisonAiSheetChangesResult>(OPERATIONS.cancelComparisonAiSheetChanges, input, options);
}

/**
 * Cancel a report.
 *
 * `POST /comparison-reports/{comparison_report_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelComparisonReport(
  input: CancelComparisonReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelComparisonReportResult>> {
  return request<CancelComparisonReportResult>(OPERATIONS.cancelComparisonReport, input, options);
}

/**
 * Cancel a series.
 *
 * `POST /comparison-series/{comparison_series_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelComparisonSeries(
  input: CancelComparisonSeriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelComparisonSeriesResult>> {
  return request<CancelComparisonSeriesResult>(OPERATIONS.cancelComparisonSeries, input, options);
}

/**
 * Cancel a specification comparison.
 *
 * `POST /comparison-ai-spec-jobs/{comparison_ai_job_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelComparisonSpecification(
  input: CancelComparisonSpecificationInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelComparisonSpecificationResult>> {
  return request<CancelComparisonSpecificationResult>(OPERATIONS.cancelComparisonSpecification, input, options);
}

/**
 * Cancel an upload batch («Отменить пакет»).
 *
 * `POST /comparison-uploads/{comparison_upload_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelComparisonUpload(
  input: CancelComparisonUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelComparisonUploadResult>> {
  return request<CancelComparisonUploadResult>(OPERATIONS.cancelComparisonUpload, input, options);
}

/**
 * Cancel Run
 *
 * `POST /runs/{run_id}/cancel` - a write; carries a required Idempotency-Key.
 */
export function cancelRun(
  input: CancelRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelRunResult>> {
  return request<CancelRunResult>(OPERATIONS.cancelRun, input, options);
}

/**
 * Cancel Batch
 *
 * `POST /stage-chain-batches/{stage_chain_batch_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelStageChainBatch(
  input: CancelStageChainBatchInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelStageChainBatchResult>> {
  return request<CancelStageChainBatchResult>(OPERATIONS.cancelStageChainBatch, input, options);
}

/**
 * Cancel Stage Chain Run
 *
 * `POST /stage-chain-runs/{stage_chain_run_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelStageChainRun(
  input: CancelStageChainRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelStageChainRunResult>> {
  return request<CancelStageChainRunResult>(OPERATIONS.cancelStageChainRun, input, options);
}

/**
 * Cancel Stage Upload
 *
 * `POST /stage-uploads/{stage_upload_id}/cancellation` - a write; carries a required Idempotency-Key.
 */
export function cancelStageUpload(
  input: CancelStageUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<CancelStageUploadResult>> {
  return request<CancelStageUploadResult>(OPERATIONS.cancelStageUpload, input, options);
}

/**
 * Carry Over Decision
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/carryovers` - a write; carries a required Idempotency-Key.
 */
export function carryOverDecision(
  input: CarryOverDecisionInput,
  options?: RequestOptions,
): Promise<ApiResponse<CarryOverDecisionResult>> {
  return request<CarryOverDecisionResult>(OPERATIONS.carryOverDecision, input, options);
}

/**
 * Carry Over Proposal Decisions
 *
 * `POST /optimisation-passes/{optimisation_pass_id}/decision-carryovers` - a write; carries a required Idempotency-Key.
 */
export function carryOverProposalDecisions(
  input: CarryOverProposalDecisionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<CarryOverProposalDecisionsResult>> {
  return request<CarryOverProposalDecisionsResult>(OPERATIONS.carryOverProposalDecisions, input, options);
}

/**
 * Change the signed-in account's password and revoke its old credentials.
 *
 * `POST /auth/password`.
 */
export function changePassword(
  input: ChangePasswordInput,
  options?: RequestOptions,
): Promise<ApiResponse<ChangePasswordResult>> {
  return request<ChangePasswordResult>(OPERATIONS.changePassword, input, options);
}

/**
 * Claim Executor Task
 *
 * `POST /runner/tasks/claim`.
 */
export function claimExecutorTask(
  input: ClaimExecutorTaskInput,
  options?: RequestOptions,
): Promise<ApiResponse<ClaimExecutorTaskResult>> {
  return request<ClaimExecutorTaskResult>(OPERATIONS.claimExecutorTask, input, options);
}

/**
 * Classify Document Version
 *
 * `PUT /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification`.
 */
export function classifyDocumentVersion(
  input: ClassifyDocumentVersionInput,
  options?: RequestOptions,
): Promise<ApiResponse<ClassifyDocumentVersionResult>> {
  return request<ClassifyDocumentVersionResult>(OPERATIONS.classifyDocumentVersion, input, options);
}

/**
 * Clear the launch queue.
 *
 * `POST /projects/{project_uid}/comparison-launch-queue/clear` - a write; carries a required Idempotency-Key.
 */
export function clearComparisonLaunchQueue(
  input: ClearComparisonLaunchQueueInput,
  options?: RequestOptions,
): Promise<ApiResponse<ClearComparisonLaunchQueueResult>> {
  return request<ClearComparisonLaunchQueueResult>(OPERATIONS.clearComparisonLaunchQueue, input, options);
}

/**
 * Compare Document Versions
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison`.
 */
export function compareDocumentVersions(
  input: CompareDocumentVersionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<CompareDocumentVersionsResult>> {
  return request<CompareDocumentVersionsResult>(OPERATIONS.compareDocumentVersions, input, options);
}

/**
 * Complete one file and check it against its declared values.
 *
 * `POST /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/completion` - a write; carries a required Idempotency-Key.
 */
export function completeComparisonUploadFile(
  input: CompleteComparisonUploadFileInput,
  options?: RequestOptions,
): Promise<ApiResponse<CompleteComparisonUploadFileResult>> {
  return request<CompleteComparisonUploadFileResult>(OPERATIONS.completeComparisonUploadFile, input, options);
}

/**
 * Complete Stage Upload File
 *
 * `POST /stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/completion` - a write; carries a required Idempotency-Key.
 */
export function completeStageUploadFile(
  input: CompleteStageUploadFileInput,
  options?: RequestOptions,
): Promise<ApiResponse<CompleteStageUploadFileResult>> {
  return request<CompleteStageUploadFileResult>(OPERATIONS.completeStageUploadFile, input, options);
}

/**
 * Confirm the membership and order of one proposed set.
 *
 * `POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/confirmation` - a write; carries a required Idempotency-Key.
 */
export function confirmComparisonUploadSet(
  input: ConfirmComparisonUploadSetInput,
  options?: RequestOptions,
): Promise<ApiResponse<ConfirmComparisonUploadSetResult>> {
  return request<ConfirmComparisonUploadSetResult>(OPERATIONS.confirmComparisonUploadSet, input, options);
}

/**
 * Confirm Executor Agent Install Host Key
 *
 * `POST /executor-connections/{connection_id}/agent-installs/{install_id}/confirm-host-key` - a write; carries a required Idempotency-Key.
 */
export function confirmExecutorAgentInstallHostKey(
  input: ConfirmExecutorAgentInstallHostKeyInput,
  options?: RequestOptions,
): Promise<ApiResponse<ConfirmExecutorAgentInstallHostKeyResult>> {
  return request<ConfirmExecutorAgentInstallHostKeyResult>(OPERATIONS.confirmExecutorAgentInstallHostKey, input, options);
}

/**
 * Confirm Executor Host Agent Install Host Key
 *
 * `POST /executor-hosts/{host_id}/agent-installs/{install_id}/confirm-host-key` - a write; carries a required Idempotency-Key.
 */
export function confirmExecutorHostAgentInstallHostKey(
  input: ConfirmExecutorHostAgentInstallHostKeyInput,
  options?: RequestOptions,
): Promise<ApiResponse<ConfirmExecutorHostAgentInstallHostKeyResult>> {
  return request<ConfirmExecutorHostAgentInstallHostKeyResult>(OPERATIONS.confirmExecutorHostAgentInstallHostKey, input, options);
}

/**
 * Confirm Stage Pair
 *
 * `POST /projects/{project_uid}/stage-pairs` - a write; carries a required Idempotency-Key.
 */
export function confirmStagePair(
  input: ConfirmStagePairInput,
  options?: RequestOptions,
): Promise<ApiResponse<ConfirmStagePairResult>> {
  return request<ConfirmStagePairResult>(OPERATIONS.confirmStagePair, input, options);
}

/**
 * Confirm Stage Upload Candidate
 *
 * `POST /stage-upload-candidates/{stage_upload_candidate_id}/confirmation` - a write; carries a required Idempotency-Key.
 */
export function confirmStageUploadCandidate(
  input: ConfirmStageUploadCandidateInput,
  options?: RequestOptions,
): Promise<ApiResponse<ConfirmStageUploadCandidateResult>> {
  return request<ConfirmStageUploadCandidateResult>(OPERATIONS.confirmStageUploadCandidate, input, options);
}

/**
 * Continue a report.
 *
 * `POST /comparison-reports/{comparison_report_id}/continuation` - a write; carries a required Idempotency-Key.
 */
export function continueComparisonReport(
  input: ContinueComparisonReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<ContinueComparisonReportResult>> {
  return request<ContinueComparisonReportResult>(OPERATIONS.continueComparisonReport, input, options);
}

/**
 * Correct Version Classification
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification/corrections`.
 */
export function correctVersionClassification(
  input: CorrectVersionClassificationInput,
  options?: RequestOptions,
): Promise<ApiResponse<CorrectVersionClassificationResult>> {
  return request<CorrectVersionClassificationResult>(OPERATIONS.correctVersionClassification, input, options);
}

/**
 * Save an analysis preset.
 *
 * `POST /analysis/presets` - a write; carries a required Idempotency-Key.
 */
export function createAnalysisPreset(
  input: CreateAnalysisPresetInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateAnalysisPresetResult>> {
  return request<CreateAnalysisPresetResult>(OPERATIONS.createAnalysisPreset, input, options);
}

/**
 * Assign a project, or one document of it, to an expert.
 *
 * `POST /assignments`.
 */
export function createAssignment(
  input: CreateAssignmentInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateAssignmentResult>> {
  return request<CreateAssignmentResult>(OPERATIONS.createAssignment, input, options);
}

/**
 * Make a report draft from the summary of a series.
 *
 * `POST /comparison-series/{comparison_series_id}/reports` - a write; carries a required Idempotency-Key.
 */
export function createComparisonReport(
  input: CreateComparisonReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateComparisonReportResult>> {
  return request<CreateComparisonReportResult>(OPERATIONS.createComparisonReport, input, options);
}

/**
 * Declare an upload batch of plain PDFs for comparison.
 *
 * `POST /projects/{project_uid}/comparison-uploads` - a write; carries a required Idempotency-Key.
 */
export function createComparisonUpload(
  input: CreateComparisonUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateComparisonUploadResult>> {
  return request<CreateComparisonUploadResult>(OPERATIONS.createComparisonUpload, input, options);
}

/**
 * Create Executor Agent Install
 *
 * `POST /executor-connections/{connection_id}/agent-installs` - a write; carries a required Idempotency-Key.
 */
export function createExecutorAgentInstall(
  input: CreateExecutorAgentInstallInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateExecutorAgentInstallResult>> {
  return request<CreateExecutorAgentInstallResult>(OPERATIONS.createExecutorAgentInstall, input, options);
}

/**
 * Create Executor Connection
 *
 * `POST /executor-connections` - a write; carries a required Idempotency-Key.
 */
export function createExecutorConnection(
  input: CreateExecutorConnectionInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateExecutorConnectionResult>> {
  return request<CreateExecutorConnectionResult>(OPERATIONS.createExecutorConnection, input, options);
}

/**
 * Create Executor Group
 *
 * `POST /executor-groups` - a write; carries a required Idempotency-Key.
 */
export function createExecutorGroup(
  input: CreateExecutorGroupInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateExecutorGroupResult>> {
  return request<CreateExecutorGroupResult>(OPERATIONS.createExecutorGroup, input, options);
}

/**
 * Create Executor Host Agent Install
 *
 * `POST /executor-hosts/agent-installs` - a write; carries a required Idempotency-Key.
 */
export function createExecutorHostAgentInstall(
  input: CreateExecutorHostAgentInstallInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateExecutorHostAgentInstallResult>> {
  return request<CreateExecutorHostAgentInstallResult>(OPERATIONS.createExecutorHostAgentInstall, input, options);
}

/**
 * Create a project.
 *
 * `POST /projects` - a write; carries a required Idempotency-Key.
 */
export function createProject(
  input: CreateProjectInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateProjectResult>> {
  return request<CreateProjectResult>(OPERATIONS.createProject, input, options);
}

/**
 * Create Stage Assembly
 *
 * `POST /projects/{project_uid}/stage-assemblies` - a write; carries a required Idempotency-Key.
 */
export function createStageAssembly(
  input: CreateStageAssemblyInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateStageAssemblyResult>> {
  return request<CreateStageAssemblyResult>(OPERATIONS.createStageAssembly, input, options);
}

/**
 * Create Review Card
 *
 * `POST /stage-chain-runs/{stage_chain_run_id}/review-cards` - a write; carries a required Idempotency-Key.
 */
export function createStageReviewCard(
  input: CreateStageReviewCardInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateStageReviewCardResult>> {
  return request<CreateStageReviewCardResult>(OPERATIONS.createStageReviewCard, input, options);
}

/**
 * Create Stage Upload
 *
 * `POST /projects/{project_uid}/stage-uploads` - a write; carries a required Idempotency-Key.
 */
export function createStageUpload(
  input: CreateStageUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<CreateStageUploadResult>> {
  return request<CreateStageUploadResult>(OPERATIONS.createStageUpload, input, options);
}

/**
 * Decide Optimisation Proposal
 *
 * `POST /optimisation-proposals/{optimisation_proposal_id}/decisions` - a write; carries a required Idempotency-Key.
 */
export function decideOptimisationProposal(
  input: DecideOptimisationProposalInput,
  options?: RequestOptions,
): Promise<ApiResponse<DecideOptimisationProposalResult>> {
  return request<DecideOptimisationProposalResult>(OPERATIONS.decideOptimisationProposal, input, options);
}

/**
 * Delete a report.
 *
 * `POST /comparison-reports/{comparison_report_id}/deletion` - a write; carries a required Idempotency-Key.
 */
export function deleteComparisonReport(
  input: DeleteComparisonReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<DeleteComparisonReportResult>> {
  return request<DeleteComparisonReportResult>(OPERATIONS.deleteComparisonReport, input, options);
}

/**
 * Delete Run
 *
 * `POST /runs/{run_id}/deletion` - a write; carries a required Idempotency-Key.
 */
export function deleteRun(
  input: DeleteRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<DeleteRunResult>> {
  return request<DeleteRunResult>(OPERATIONS.deleteRun, input, options);
}

/**
 * Take an AI description of changes out of the AI queue.
 *
 * `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/dequeue` - a write; carries a required Idempotency-Key.
 */
export function dequeueComparisonAiSheetChanges(
  input: DequeueComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<DequeueComparisonAiSheetChangesResult>> {
  return request<DequeueComparisonAiSheetChangesResult>(OPERATIONS.dequeueComparisonAiSheetChanges, input, options);
}

/**
 * Download Agent Package
 *
 * `GET /runner/agent-package/{version}`.
 */
export function downloadAgentPackage(
  input: DownloadAgentPackageInput,
  options?: RequestOptions,
): Promise<ApiResponse<DownloadAgentPackageResult>> {
  return request<DownloadAgentPackageResult>(OPERATIONS.downloadAgentPackage, input, options);
}

/**
 * End every session of an account.
 *
 * `POST /users/{user_uid}/sessions/end` - a write; carries a required Idempotency-Key.
 */
export function endUserSessions(
  input: EndUserSessionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<EndUserSessionsResult>> {
  return request<EndUserSessionsResult>(OPERATIONS.endUserSessions, input, options);
}

/**
 * Queue document sets and steps.
 *
 * `POST /projects/{project_uid}/comparison-launch-queue/entries` - a write; carries a required Idempotency-Key.
 */
export function enqueueComparisonLaunch(
  input: EnqueueComparisonLaunchInput,
  options?: RequestOptions,
): Promise<ApiResponse<EnqueueComparisonLaunchResult>> {
  return request<EnqueueComparisonLaunchResult>(OPERATIONS.enqueueComparisonLaunch, input, options);
}

/**
 * Estimate the AI check of the doubtful pairs of a document set.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check/estimate`.
 */
export function estimateComparisonAiPairCheck(
  input: EstimateComparisonAiPairCheckInput,
  options?: RequestOptions,
): Promise<ApiResponse<EstimateComparisonAiPairCheckResult>> {
  return request<EstimateComparisonAiPairCheckResult>(OPERATIONS.estimateComparisonAiPairCheck, input, options);
}

/**
 * Estimate the AI description of changes of a series.
 *
 * `GET /comparison-series/{comparison_series_id}/ai-sheet-changes/estimate`.
 */
export function estimateComparisonAiSheetChanges(
  input: EstimateComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<EstimateComparisonAiSheetChangesResult>> {
  return request<EstimateComparisonAiSheetChangesResult>(OPERATIONS.estimateComparisonAiSheetChanges, input, options);
}

/**
 * Estimate the AI description of one sheet.
 *
 * `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description/estimate`.
 */
export function estimateComparisonSheetDescription(
  input: EstimateComparisonSheetDescriptionInput,
  options?: RequestOptions,
): Promise<ApiResponse<EstimateComparisonSheetDescriptionResult>> {
  return request<EstimateComparisonSheetDescriptionResult>(OPERATIONS.estimateComparisonSheetDescription, input, options);
}

/**
 * Estimate the comparison of the whole specifications of a transition.
 *
 * `GET /comparison-transitions/{comparison_transition_id}/specification/estimate`.
 */
export function estimateComparisonSpecification(
  input: EstimateComparisonSpecificationInput,
  options?: RequestOptions,
): Promise<ApiResponse<EstimateComparisonSpecificationResult>> {
  return request<EstimateComparisonSpecificationResult>(OPERATIONS.estimateComparisonSpecification, input, options);
}

/**
 * Estimate selected section analysis before spend.
 *
 * `POST /runs/cost-estimate`.
 */
export function estimateRunCost(
  input: EstimateRunCostInput,
  options?: RequestOptions,
): Promise<ApiResponse<EstimateRunCostResult>> {
  return request<EstimateRunCostResult>(OPERATIONS.estimateRunCost, input, options);
}

/**
 * Estimate Run
 *
 * `GET /stage-link-revisions/{stage_link_revision_id}/chain-estimate`.
 */
export function estimateStageChainRun(
  input: EstimateStageChainRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<EstimateStageChainRunResult>> {
  return request<EstimateStageChainRunResult>(OPERATIONS.estimateStageChainRun, input, options);
}

/**
 * Leave one set out of the batch.
 *
 * `POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/exclusion` - a write; carries a required Idempotency-Key.
 */
export function excludeComparisonUploadSet(
  input: ExcludeComparisonUploadSetInput,
  options?: RequestOptions,
): Promise<ApiResponse<ExcludeComparisonUploadSetResult>> {
  return request<ExcludeComparisonUploadSetResult>(OPERATIONS.excludeComparisonUploadSet, input, options);
}

/**
 * Export Optimisation Proposals Csv
 *
 * `GET /optimisation-passes/{optimisation_pass_id}/export.csv`.
 */
export function exportOptimisationProposalsCsv(
  input: ExportOptimisationProposalsCsvInput,
  options?: RequestOptions,
): Promise<ApiResponse<ExportOptimisationProposalsCsvResult>> {
  return request<ExportOptimisationProposalsCsvResult>(OPERATIONS.exportOptimisationProposalsCsv, input, options);
}

/**
 * Export Optimisation Proposals Xlsx
 *
 * `GET /optimisation-passes/{optimisation_pass_id}/export.xlsx`.
 */
export function exportOptimisationProposalsXlsx(
  input: ExportOptimisationProposalsXlsxInput,
  options?: RequestOptions,
): Promise<ApiResponse<ExportOptimisationProposalsXlsxResult>> {
  return request<ExportOptimisationProposalsXlsxResult>(OPERATIONS.exportOptimisationProposalsXlsx, input, options);
}

/**
 * Download the CSV for one run.
 *
 * `GET /runs/{run_id}/export.csv`.
 */
export function exportRunCsv(
  input: ExportRunCsvInput,
  options?: RequestOptions,
): Promise<ApiResponse<ExportRunCsvResult>> {
  return request<ExportRunCsvResult>(OPERATIONS.exportRunCsv, input, options);
}

/**
 * Download the Excel workbook for one run.
 *
 * `GET /runs/{run_id}/export.xlsx`.
 */
export function exportRunXlsx(
  input: ExportRunXlsxInput,
  options?: RequestOptions,
): Promise<ApiResponse<ExportRunXlsxResult>> {
  return request<ExportRunXlsxResult>(OPERATIONS.exportRunXlsx, input, options);
}

/**
 * Extend Executor Task Claim
 *
 * `POST /runner/tasks/{task_id}/extend`.
 */
export function extendExecutorTaskClaim(
  input: ExtendExecutorTaskClaimInput,
  options?: RequestOptions,
): Promise<ApiResponse<ExtendExecutorTaskClaimResult>> {
  return request<ExtendExecutorTaskClaimResult>(OPERATIONS.extendExecutorTaskClaim, input, options);
}

/**
 * Fail Executor Task
 *
 * `POST /runner/tasks/{task_id}/fail`.
 */
export function failExecutorTask(
  input: FailExecutorTaskInput,
  options?: RequestOptions,
): Promise<ApiResponse<FailExecutorTaskResult>> {
  return request<FailExecutorTaskResult>(OPERATIONS.failExecutorTask, input, options);
}

/**
 * Finish an interrupted AI description of changes.
 *
 * `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/finish` - a write; carries a required Idempotency-Key.
 */
export function finishComparisonAiSheetChanges(
  input: FinishComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<FinishComparisonAiSheetChangesResult>> {
  return request<FinishComparisonAiSheetChangesResult>(OPERATIONS.finishComparisonAiSheetChanges, input, options);
}

/**
 * Finish the transitions of a series that have no result.
 *
 * `POST /comparison-series/{comparison_series_id}/finish` - a write; carries a required Idempotency-Key.
 */
export function finishComparisonSeries(
  input: FinishComparisonSeriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<FinishComparisonSeriesResult>> {
  return request<FinishComparisonSeriesResult>(OPERATIONS.finishComparisonSeries, input, options);
}

/**
 * Generate Comparison Summary
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/summaries` - a write; carries a required Idempotency-Key.
 */
export function generateComparisonSummary(
  input: GenerateComparisonSummaryInput,
  options?: RequestOptions,
): Promise<ApiResponse<GenerateComparisonSummaryResult>> {
  return request<GenerateComparisonSummaryResult>(OPERATIONS.generateComparisonSummary, input, options);
}

/**
 * Generate Executor Ssh Key
 *
 * `POST /executor-connections/{connection_id}/ssh-key` - a write; carries a required Idempotency-Key.
 */
export function generateExecutorSshKey(
  input: GenerateExecutorSshKeyInput,
  options?: RequestOptions,
): Promise<ApiResponse<GenerateExecutorSshKeyResult>> {
  return request<GenerateExecutorSshKeyResult>(OPERATIONS.generateExecutorSshKey, input, options);
}

/**
 * Read one assignment with its history.
 *
 * `GET /assignments/{assignment_uid}`.
 */
export function getAssignment(
  input: GetAssignmentInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetAssignmentResult>> {
  return request<GetAssignmentResult>(OPERATIONS.getAssignment, input, options);
}

/**
 * Read the latest AI check of a document set.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check`.
 */
export function getComparisonAiPairCheck(
  input: GetComparisonAiPairCheckInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonAiPairCheckResult>> {
  return request<GetComparisonAiPairCheckResult>(OPERATIONS.getComparisonAiPairCheck, input, options);
}

/**
 * Read the AI queue of the installation.
 *
 * `GET /execution/comparison-ai-queue`.
 */
export function getComparisonAiQueue(
  input: GetComparisonAiQueueInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonAiQueueResult>> {
  return request<GetComparisonAiQueueResult>(OPERATIONS.getComparisonAiQueue, input, options);
}

/**
 * Read the AI description of changes of a series.
 *
 * `GET /comparison-series/{comparison_series_id}/ai-sheet-changes`.
 */
export function getComparisonAiSheetChanges(
  input: GetComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonAiSheetChangesResult>> {
  return request<GetComparisonAiSheetChangesResult>(OPERATIONS.getComparisonAiSheetChanges, input, options);
}

/**
 * Read the launch queue of a project.
 *
 * `GET /projects/{project_uid}/comparison-launch-queue`.
 */
export function getComparisonLaunchQueue(
  input: GetComparisonLaunchQueueInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonLaunchQueueResult>> {
  return request<GetComparisonLaunchQueueResult>(OPERATIONS.getComparisonLaunchQueue, input, options);
}

/**
 * Read the effective matrix of a document set.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-matrix`.
 */
export function getComparisonMatrix(
  input: GetComparisonMatrixInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonMatrixResult>> {
  return request<GetComparisonMatrixResult>(OPERATIONS.getComparisonMatrix, input, options);
}

/**
 * Read the overview of the comparison of a project.
 *
 * `GET /projects/{project_uid}/comparison-overview`.
 */
export function getComparisonOverview(
  input: GetComparisonOverviewInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonOverviewResult>> {
  return request<GetComparisonOverviewResult>(OPERATIONS.getComparisonOverview, input, options);
}

/**
 * Read the comparison work queue.
 *
 * `GET /execution/comparison-queue`.
 */
export function getComparisonQueueSummary(
  input: GetComparisonQueueSummaryInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonQueueSummaryResult>> {
  return request<GetComparisonQueueSummaryResult>(OPERATIONS.getComparisonQueueSummary, input, options);
}

/**
 * Read a report.
 *
 * `GET /comparison-reports/{comparison_report_id}`.
 */
export function getComparisonReport(
  input: GetComparisonReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonReportResult>> {
  return request<GetComparisonReportResult>(OPERATIONS.getComparisonReport, input, options);
}

/**
 * Read a series with its transitions.
 *
 * `GET /comparison-series/{comparison_series_id}`.
 */
export function getComparisonSeries(
  input: GetComparisonSeriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonSeriesResult>> {
  return request<GetComparisonSeriesResult>(OPERATIONS.getComparisonSeries, input, options);
}

/**
 * Read the AI description of a sheet pair.
 *
 * `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description`.
 */
export function getComparisonSheetDescription(
  input: GetComparisonSheetDescriptionInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonSheetDescriptionResult>> {
  return request<GetComparisonSheetDescriptionResult>(OPERATIONS.getComparisonSheetDescription, input, options);
}

/**
 * Read one sheet pair with its raw deterministic evidence.
 *
 * `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}`.
 */
export function getComparisonSheetPair(
  input: GetComparisonSheetPairInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonSheetPairResult>> {
  return request<GetComparisonSheetPairResult>(OPERATIONS.getComparisonSheetPair, input, options);
}

/**
 * Read the positions that changed on a sheet pair.
 *
 * `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/spec-positions`.
 */
export function getComparisonSheetPairSpecPositions(
  input: GetComparisonSheetPairSpecPositionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonSheetPairSpecPositionsResult>> {
  return request<GetComparisonSheetPairSpecPositionsResult>(OPERATIONS.getComparisonSheetPairSpecPositions, input, options);
}

/**
 * Read the specification comparison of a transition.
 *
 * `GET /comparison-transitions/{comparison_transition_id}/specification`.
 */
export function getComparisonSpecification(
  input: GetComparisonSpecificationInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonSpecificationResult>> {
  return request<GetComparisonSpecificationResult>(OPERATIONS.getComparisonSpecification, input, options);
}

/**
 * Read an upload batch with its files.
 *
 * `GET /comparison-uploads/{comparison_upload_id}`.
 */
export function getComparisonUpload(
  input: GetComparisonUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonUploadResult>> {
  return request<GetComparisonUploadResult>(OPERATIONS.getComparisonUpload, input, options);
}

/**
 * Read the grouping proposal of an upload batch.
 *
 * `GET /comparison-uploads/{comparison_upload_id}/proposal`.
 */
export function getComparisonUploadProposal(
  input: GetComparisonUploadProposalInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetComparisonUploadProposalResult>> {
  return request<GetComparisonUploadProposalResult>(OPERATIONS.getComparisonUploadProposal, input, options);
}

/**
 * One aggregate read across the whole deployment: all four dashboard panels.
 *
 * `GET /dashboard`.
 */
export function getDashboardSummary(
  input: GetDashboardSummaryInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetDashboardSummaryResult>> {
  return request<GetDashboardSummaryResult>(OPERATIONS.getDashboardSummary, input, options);
}

/**
 * Get Decision Memory Case
 *
 * `GET /decision-memory/cases/{case_id}`.
 */
export function getDecisionMemoryCase(
  input: GetDecisionMemoryCaseInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetDecisionMemoryCaseResult>> {
  return request<GetDecisionMemoryCaseResult>(OPERATIONS.getDecisionMemoryCase, input, options);
}

/**
 * Get Decision Memory Status
 *
 * `GET /decision-memory/status`.
 */
export function getDecisionMemoryStatus(
  input: GetDecisionMemoryStatusInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetDecisionMemoryStatusResult>> {
  return request<GetDecisionMemoryStatusResult>(OPERATIONS.getDecisionMemoryStatus, input, options);
}

/**
 * Read one published document version.
 *
 * `GET /versions/{version_uid}`.
 */
export function getDocumentVersion(
  input: GetDocumentVersionInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetDocumentVersionResult>> {
  return request<GetDocumentVersionResult>(OPERATIONS.getDocumentVersion, input, options);
}

/**
 * Get Effective Vendor Lists
 *
 * `GET /projects/{project_uid}/vendor-lists`.
 */
export function getEffectiveVendorLists(
  input: GetEffectiveVendorListsInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetEffectiveVendorListsResult>> {
  return request<GetEffectiveVendorListsResult>(OPERATIONS.getEffectiveVendorLists, input, options);
}

/**
 * Get Dispatch
 *
 * `GET /execution/dispatch`.
 */
export function getExecutionDispatch(
  input: GetExecutionDispatchInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutionDispatchResult>> {
  return request<GetExecutionDispatchResult>(OPERATIONS.getExecutionDispatch, input, options);
}

/**
 * Get Executor Agent Install
 *
 * `GET /executor-connections/{connection_id}/agent-installs/{install_id}`.
 */
export function getExecutorAgentInstall(
  input: GetExecutorAgentInstallInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorAgentInstallResult>> {
  return request<GetExecutorAgentInstallResult>(OPERATIONS.getExecutorAgentInstall, input, options);
}

/**
 * Get Executor Connection
 *
 * `GET /executor-connections/{connection_id}`.
 */
export function getExecutorConnection(
  input: GetExecutorConnectionInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorConnectionResult>> {
  return request<GetExecutorConnectionResult>(OPERATIONS.getExecutorConnection, input, options);
}

/**
 * Get Executor Group
 *
 * `GET /executor-groups/{group_id}`.
 */
export function getExecutorGroup(
  input: GetExecutorGroupInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorGroupResult>> {
  return request<GetExecutorGroupResult>(OPERATIONS.getExecutorGroup, input, options);
}

/**
 * Get Executor Group Capacity
 *
 * `GET /executor-groups/{group_id}/capacity`.
 */
export function getExecutorGroupCapacity(
  input: GetExecutorGroupCapacityInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorGroupCapacityResult>> {
  return request<GetExecutorGroupCapacityResult>(OPERATIONS.getExecutorGroupCapacity, input, options);
}

/**
 * Get Executor Host
 *
 * `GET /executor-hosts/{host_id}`.
 */
export function getExecutorHost(
  input: GetExecutorHostInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorHostResult>> {
  return request<GetExecutorHostResult>(OPERATIONS.getExecutorHost, input, options);
}

/**
 * Get Executor Host Agent Install
 *
 * `GET /executor-hosts/{host_id}/agent-installs/{install_id}`.
 */
export function getExecutorHostAgentInstall(
  input: GetExecutorHostAgentInstallInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorHostAgentInstallResult>> {
  return request<GetExecutorHostAgentInstallResult>(OPERATIONS.getExecutorHostAgentInstall, input, options);
}

/**
 * Get Executor Host Details
 *
 * `GET /executor-hosts/{host_id}/details`.
 */
export function getExecutorHostDetails(
  input: GetExecutorHostDetailsInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorHostDetailsResult>> {
  return request<GetExecutorHostDetailsResult>(OPERATIONS.getExecutorHostDetails, input, options);
}

/**
 * Get Executor Task Context
 *
 * `POST /runner/tasks/{task_id}/context`.
 */
export function getExecutorTaskContext(
  input: GetExecutorTaskContextInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorTaskContextResult>> {
  return request<GetExecutorTaskContextResult>(OPERATIONS.getExecutorTaskContext, input, options);
}

/**
 * Get Executor Task Image
 *
 * `GET /runner/tasks/{task_id}/images/{blob_id}`.
 */
export function getExecutorTaskImage(
  input: GetExecutorTaskImageInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExecutorTaskImageResult>> {
  return request<GetExecutorTaskImageResult>(OPERATIONS.getExecutorTaskImage, input, options);
}

/**
 * Get Extended Run Review
 *
 * `GET /runs/{run_id}/extended-review`.
 */
export function getExtendedRunReview(
  input: GetExtendedRunReviewInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetExtendedRunReviewResult>> {
  return request<GetExtendedRunReviewResult>(OPERATIONS.getExtendedRunReview, input, options);
}

/**
 * Read one finding with its observation, evidence and provenance.
 *
 * `GET /findings/{finding_uid}`.
 */
export function getFinding(
  input: GetFindingInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetFindingResult>> {
  return request<GetFindingResult>(OPERATIONS.getFinding, input, options);
}

/**
 * Get Finding Precedents
 *
 * `GET /findings/{finding_uid}/precedents`.
 */
export function getFindingPrecedents(
  input: GetFindingPrecedentsInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetFindingPrecedentsResult>> {
  return request<GetFindingPrecedentsResult>(OPERATIONS.getFindingPrecedents, input, options);
}

/**
 * Read the signed-in account.
 *
 * `GET /me`.
 */
export function getMe(
  input: GetMeInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetMeResult>> {
  return request<GetMeResult>(OPERATIONS.getMe, input, options);
}

/**
 * Get Norm Document
 *
 * `GET /norm-documents/{norm_document_id}`.
 */
export function getNormDocument(
  input: GetNormDocumentInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetNormDocumentResult>> {
  return request<GetNormDocumentResult>(OPERATIONS.getNormDocument, input, options);
}

/**
 * Read the running product version.
 *
 * `GET /system/version`.
 */
export function getProductVersion(
  input: GetProductVersionInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetProductVersionResult>> {
  return request<GetProductVersionResult>(OPERATIONS.getProductVersion, input, options);
}

/**
 * Get Project
 *
 * `GET /projects/{project_uid}`.
 */
export function getProject(
  input: GetProjectInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetProjectResult>> {
  return request<GetProjectResult>(OPERATIONS.getProject, input, options);
}

/**
 * Get Quality Table
 *
 * `GET /quality-table`.
 */
export function getQualityTable(
  input: GetQualityTableInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetQualityTableResult>> {
  return request<GetQualityTableResult>(OPERATIONS.getQualityTable, input, options);
}

/**
 * Get Run Norm References
 *
 * `GET /runs/{run_id}/norm-references`.
 */
export function getRunNormReferences(
  input: GetRunNormReferencesInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetRunNormReferencesResult>> {
  return request<GetRunNormReferencesResult>(OPERATIONS.getRunNormReferences, input, options);
}

/**
 * Get Run Precedents
 *
 * `GET /runs/{run_id}/precedents`.
 */
export function getRunPrecedents(
  input: GetRunPrecedentsInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetRunPrecedentsResult>> {
  return request<GetRunPrecedentsResult>(OPERATIONS.getRunPrecedents, input, options);
}

/**
 * Get Run Stages
 *
 * `GET /runs/{run_id}/stages`.
 */
export function getRunStages(
  input: GetRunStagesInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetRunStagesResult>> {
  return request<GetRunStagesResult>(OPERATIONS.getRunStages, input, options);
}

/**
 * Get Run Start Readiness
 *
 * `POST /runs/start-readiness`.
 */
export function getRunStartReadiness(
  input: GetRunStartReadinessInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetRunStartReadinessResult>> {
  return request<GetRunStartReadinessResult>(OPERATIONS.getRunStartReadiness, input, options);
}

/**
 * Read run state and per-stage state.
 *
 * `GET /runs/{run_id}`.
 */
export function getRunStatus(
  input: GetRunStatusInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetRunStatusResult>> {
  return request<GetRunStatusResult>(OPERATIONS.getRunStatus, input, options);
}

/**
 * Get Section Specification
 *
 * `GET /sections/{section_code}/specification`.
 */
export function getSectionSpecification(
  input: GetSectionSpecificationInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetSectionSpecificationResult>> {
  return request<GetSectionSpecificationResult>(OPERATIONS.getSectionSpecification, input, options);
}

/**
 * Get Specification Prices
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/specification-prices`.
 */
export function getSpecificationPrices(
  input: GetSpecificationPricesInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetSpecificationPricesResult>> {
  return request<GetSpecificationPricesResult>(OPERATIONS.getSpecificationPrices, input, options);
}

/**
 * Get Assembly
 *
 * `GET /stage-assemblies/{stage_assembly_id}`.
 */
export function getStageAssembly(
  input: GetStageAssemblyInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageAssemblyResult>> {
  return request<GetStageAssemblyResult>(OPERATIONS.getStageAssembly, input, options);
}

/**
 * Get Batch
 *
 * `GET /stage-chain-batches/{stage_chain_batch_id}`.
 */
export function getStageChainBatch(
  input: GetStageChainBatchInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageChainBatchResult>> {
  return request<GetStageChainBatchResult>(OPERATIONS.getStageChainBatch, input, options);
}

/**
 * Get Stage Chain Run
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}`.
 */
export function getStageChainRun(
  input: GetStageChainRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageChainRunResult>> {
  return request<GetStageChainRunResult>(OPERATIONS.getStageChainRun, input, options);
}

/**
 * Get Card
 *
 * `GET /stage-change-cards/{stage_change_card_id}`.
 */
export function getStageChangeCard(
  input: GetStageChangeCardInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageChangeCardResult>> {
  return request<GetStageChangeCardResult>(OPERATIONS.getStageChangeCard, input, options);
}

/**
 * Get Journal
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/journal`.
 */
export function getStageChangeJournal(
  input: GetStageChangeJournalInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageChangeJournalResult>> {
  return request<GetStageChangeJournalResult>(OPERATIONS.getStageChangeJournal, input, options);
}

/**
 * Get Stage Model Layout
 *
 * `GET /model-layout`.
 */
export function getStageModelLayout(
  input: GetStageModelLayoutInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageModelLayoutResult>> {
  return request<GetStageModelLayoutResult>(OPERATIONS.getStageModelLayout, input, options);
}

/**
 * Get Stage Pair
 *
 * `GET /stage-pairs/{stage_pair_id}`.
 */
export function getStagePair(
  input: GetStagePairInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStagePairResult>> {
  return request<GetStagePairResult>(OPERATIONS.getStagePair, input, options);
}

/**
 * Get Profile Text
 *
 * `GET /comparison-page-profiles/{comparison_page_profile_id}/stage-text`.
 */
export function getStageProfileText(
  input: GetStageProfileTextInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageProfileTextResult>> {
  return request<GetStageProfileTextResult>(OPERATIONS.getStageProfileText, input, options);
}

/**
 * Get Stage Sheet Map
 *
 * `GET /stage-pairs/{stage_pair_id}/sheet-map`.
 */
export function getStageSheetMap(
  input: GetStageSheetMapInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageSheetMapResult>> {
  return request<GetStageSheetMapResult>(OPERATIONS.getStageSheetMap, input, options);
}

/**
 * Get Stage Sheet Map Revision
 *
 * `GET /stage-link-revisions/{stage_link_revision_id}`.
 */
export function getStageSheetMapRevision(
  input: GetStageSheetMapRevisionInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageSheetMapRevisionResult>> {
  return request<GetStageSheetMapRevisionResult>(OPERATIONS.getStageSheetMapRevision, input, options);
}

/**
 * Get Synthesis
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/synthesis`.
 */
export function getStageSynthesis(
  input: GetStageSynthesisInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageSynthesisResult>> {
  return request<GetStageSynthesisResult>(OPERATIONS.getStageSynthesis, input, options);
}

/**
 * Get Stage Upload
 *
 * `GET /stage-uploads/{stage_upload_id}`.
 */
export function getStageUpload(
  input: GetStageUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetStageUploadResult>> {
  return request<GetStageUploadResult>(OPERATIONS.getStageUpload, input, options);
}

/**
 * Read one account.
 *
 * `GET /users/{user_uid}`.
 */
export function getUser(
  input: GetUserInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetUserResult>> {
  return request<GetUserResult>(OPERATIONS.getUser, input, options);
}

/**
 * Get Vector Control
 *
 * `GET /vector-control`.
 */
export function getVectorControl(
  input: GetVectorControlInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetVectorControlResult>> {
  return request<GetVectorControlResult>(OPERATIONS.getVectorControl, input, options);
}

/**
 * Read the page-by-page block index derived for one published version.
 *
 * `GET /versions/{version_uid}/blocks`.
 */
export function getVersionBlocks(
  input: GetVersionBlocksInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetVersionBlocksResult>> {
  return request<GetVersionBlocksResult>(OPERATIONS.getVersionBlocks, input, options);
}

/**
 * Read the deterministic profile of one page.
 *
 * `GET /page-profiles/{comparison_page_profile_id}`.
 */
export function getVersionPageProfile(
  input: GetVersionPageProfileInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetVersionPageProfileResult>> {
  return request<GetVersionPageProfileResult>(OPERATIONS.getVersionPageProfile, input, options);
}

/**
 * Read the positions of a specification page.
 *
 * `GET /page-profiles/{comparison_page_profile_id}/spec-positions`.
 */
export function getVersionPageSpecPositions(
  input: GetVersionPageSpecPositionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetVersionPageSpecPositionsResult>> {
  return request<GetVersionPageSpecPositionsResult>(OPERATIONS.getVersionPageSpecPositions, input, options);
}

/**
 * Get Version Section Review
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/section-review`.
 */
export function getVersionSectionReview(
  input: GetVersionSectionReviewInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetVersionSectionReviewResult>> {
  return request<GetVersionSectionReviewResult>(OPERATIONS.getVersionSectionReview, input, options);
}

/**
 * Get Work Schedule
 *
 * `GET /work-schedule`.
 */
export function getWorkSchedule(
  input: GetWorkScheduleInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetWorkScheduleResult>> {
  return request<GetWorkScheduleResult>(OPERATIONS.getWorkSchedule, input, options);
}

/**
 * Get Work Schedule Reserve
 *
 * `GET /work-schedule/reserve`.
 */
export function getWorkScheduleReserve(
  input: GetWorkScheduleReserveInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetWorkScheduleReserveResult>> {
  return request<GetWorkScheduleReserveResult>(OPERATIONS.getWorkScheduleReserve, input, options);
}

/**
 * Import Comparison Zip
 *
 * `POST /projects/{project_uid}/comparison-zip-uploads` - a write; carries a required Idempotency-Key.
 */
export function importComparisonZip(
  input: ImportComparisonZipInput,
  options?: RequestOptions,
): Promise<ApiResponse<ImportComparisonZipResult>> {
  return request<ImportComparisonZipResult>(OPERATIONS.importComparisonZip, input, options);
}

/**
 * Import Optimisation Proposal Decisions
 *
 * `POST /optimisation-passes/{optimisation_pass_id}/decision-imports` - a write; carries a required Idempotency-Key.
 */
export function importOptimisationProposalDecisions(
  input: ImportOptimisationProposalDecisionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ImportOptimisationProposalDecisionsResult>> {
  return request<ImportOptimisationProposalDecisionsResult>(OPERATIONS.importOptimisationProposalDecisions, input, options);
}

/**
 * Import Run Decisions
 *
 * `POST /runs/{run_id}/decision-imports` - a write; carries a required Idempotency-Key.
 */
export function importRunDecisions(
  input: ImportRunDecisionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ImportRunDecisionsResult>> {
  return request<ImportRunDecisionsResult>(OPERATIONS.importRunDecisions, input, options);
}

/**
 * Issue Executor Enrollment
 *
 * `POST /executor-connections/{connection_id}/enrollments` - a write; carries a required Idempotency-Key.
 */
export function issueExecutorEnrollment(
  input: IssueExecutorEnrollmentInput,
  options?: RequestOptions,
): Promise<ApiResponse<IssueExecutorEnrollmentResult>> {
  return request<IssueExecutorEnrollmentResult>(OPERATIONS.issueExecutorEnrollment, input, options);
}

/**
 * Issue Executor Host Enrollment
 *
 * `POST /executor-hosts/enrollments` - a write; carries a required Idempotency-Key.
 */
export function issueExecutorHostEnrollment(
  input: IssueExecutorHostEnrollmentInput,
  options?: RequestOptions,
): Promise<ApiResponse<IssueExecutorHostEnrollmentResult>> {
  return request<IssueExecutorHostEnrollmentResult>(OPERATIONS.issueExecutorHostEnrollment, input, options);
}

/**
 * Issue Runner Token
 *
 * `POST /executor-connections/{connection_id}/runner-tokens` - a write; carries a required Idempotency-Key.
 */
export function issueRunnerToken(
  input: IssueRunnerTokenInput,
  options?: RequestOptions,
): Promise<ApiResponse<IssueRunnerTokenResult>> {
  return request<IssueRunnerTokenResult>(OPERATIONS.issueRunnerToken, input, options);
}

/**
 * Exchange a login and a password for a bearer credential.
 *
 * `POST /auth/token`.
 */
export function issueToken(
  input: IssueTokenInput,
  options?: RequestOptions,
): Promise<ApiResponse<IssueTokenResult>> {
  return request<IssueTokenResult>(OPERATIONS.issueToken, input, options);
}

/**
 * List Accepted Optimisation Proposals
 *
 * `GET /optimisation-proposals/accepted`.
 */
export function listAcceptedOptimisationProposals(
  input: ListAcceptedOptimisationProposalsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListAcceptedOptimisationProposalsResult>> {
  return request<ListAcceptedOptimisationProposalsResult>(OPERATIONS.listAcceptedOptimisationProposals, input, options);
}

/**
 * List the analysis presets.
 *
 * `GET /analysis/presets`.
 */
export function listAnalysisPresets(
  input: ListAnalysisPresetsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListAnalysisPresetsResult>> {
  return request<ListAnalysisPresetsResult>(OPERATIONS.listAnalysisPresets, input, options);
}

/**
 * List the analysis profile of every section.
 *
 * `GET /analysis/profiles`.
 */
export function listAnalysisProfiles(
  input: ListAnalysisProfilesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListAnalysisProfilesResult>> {
  return request<ListAnalysisProfilesResult>(OPERATIONS.listAnalysisProfiles, input, options);
}

/**
 * List assignments.
 *
 * `GET /assignments`.
 */
export function listAssignments(
  input: ListAssignmentsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListAssignmentsResult>> {
  return request<ListAssignmentsResult>(OPERATIONS.listAssignments, input, options);
}

/**
 * List the access journal.
 *
 * `GET /auth-events`.
 */
export function listAuthEvents(
  input: ListAuthEventsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListAuthEventsResult>> {
  return request<ListAuthEventsResult>(OPERATIONS.listAuthEvents, input, options);
}

/**
 * List the accepted AI links of a document set.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-links`.
 */
export function listComparisonAiLinks(
  input: ListComparisonAiLinksInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonAiLinksResult>> {
  return request<ListComparisonAiLinksResult>(OPERATIONS.listComparisonAiLinks, input, options);
}

/**
 * List the answers and hints of the AI check of pairs.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-hints`.
 */
export function listComparisonAiPairHints(
  input: ListComparisonAiPairHintsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonAiPairHintsResult>> {
  return request<ListComparisonAiPairHintsResult>(OPERATIONS.listComparisonAiPairHints, input, options);
}

/**
 * List the manual edit history of a document set.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits`.
 */
export function listComparisonMatrixEdits(
  input: ListComparisonMatrixEditsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonMatrixEditsResult>> {
  return request<ListComparisonMatrixEditsResult>(OPERATIONS.listComparisonMatrixEdits, input, options);
}

/**
 * List the reports of a series.
 *
 * `GET /comparison-series/{comparison_series_id}/reports`.
 */
export function listComparisonReports(
  input: ListComparisonReportsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonReportsResult>> {
  return request<ListComparisonReportsResult>(OPERATIONS.listComparisonReports, input, options);
}

/**
 * List the sheets of a transition to review.
 *
 * `GET /comparison-transitions/{comparison_transition_id}/review-sheets`.
 */
export function listComparisonReviewSheets(
  input: ListComparisonReviewSheetsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonReviewSheetsResult>> {
  return request<ListComparisonReviewSheetsResult>(OPERATIONS.listComparisonReviewSheets, input, options);
}

/**
 * List the series of a document set.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-series`.
 */
export function listComparisonSeries(
  input: ListComparisonSeriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonSeriesResult>> {
  return request<ListComparisonSeriesResult>(OPERATIONS.listComparisonSeries, input, options);
}

/**
 * List the earlier descriptions of a sheet pair.
 *
 * `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description-history`.
 */
export function listComparisonSheetDescriptionHistory(
  input: ListComparisonSheetDescriptionHistoryInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonSheetDescriptionHistoryResult>> {
  return request<ListComparisonSheetDescriptionHistoryResult>(OPERATIONS.listComparisonSheetDescriptionHistory, input, options);
}

/**
 * List the sheet pairs of a transition.
 *
 * `GET /comparison-transitions/{comparison_transition_id}/sheet-pairs`.
 */
export function listComparisonSheetPairs(
  input: ListComparisonSheetPairsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonSheetPairsResult>> {
  return request<ListComparisonSheetPairsResult>(OPERATIONS.listComparisonSheetPairs, input, options);
}

/**
 * List the changes of a transition's specification.
 *
 * `GET /comparison-transitions/{comparison_transition_id}/specification/changes`.
 */
export function listComparisonSpecificationChanges(
  input: ListComparisonSpecificationChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonSpecificationChangesResult>> {
  return request<ListComparisonSpecificationChangesResult>(OPERATIONS.listComparisonSpecificationChanges, input, options);
}

/**
 * List the specification comparisons of a series.
 *
 * `GET /comparison-series/{comparison_series_id}/specifications`.
 */
export function listComparisonSpecifications(
  input: ListComparisonSpecificationsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonSpecificationsResult>> {
  return request<ListComparisonSpecificationsResult>(OPERATIONS.listComparisonSpecifications, input, options);
}

/**
 * List the project's upload batches.
 *
 * `GET /projects/{project_uid}/comparison-uploads`.
 */
export function listComparisonUploads(
  input: ListComparisonUploadsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonUploadsResult>> {
  return request<ListComparisonUploadsResult>(OPERATIONS.listComparisonUploads, input, options);
}

/**
 * List the revisions of the comparison order of a document set.
 *
 * `GET /projects/{project_uid}/documents/{document_uid}/comparison-version-orders`.
 */
export function listComparisonVersionOrders(
  input: ListComparisonVersionOrdersInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListComparisonVersionOrdersResult>> {
  return request<ListComparisonVersionOrdersResult>(OPERATIONS.listComparisonVersionOrders, input, options);
}

/**
 * Read the decision history of one finding, oldest first.
 *
 * `GET /findings/{finding_uid}/decisions`.
 */
export function listDecisionHistory(
  input: ListDecisionHistoryInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListDecisionHistoryResult>> {
  return request<ListDecisionHistoryResult>(OPERATIONS.listDecisionHistory, input, options);
}

/**
 * List Decision Memory Cases
 *
 * `GET /decision-memory/cases`.
 */
export function listDecisionMemoryCases(
  input: ListDecisionMemoryCasesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListDecisionMemoryCasesResult>> {
  return request<ListDecisionMemoryCasesResult>(OPERATIONS.listDecisionMemoryCases, input, options);
}

/**
 * List Decision Patterns
 *
 * `GET /decision-memory/patterns`.
 */
export function listDecisionPatterns(
  input: ListDecisionPatternsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListDecisionPatternsResult>> {
  return request<ListDecisionPatternsResult>(OPERATIONS.listDecisionPatterns, input, options);
}

/**
 * Read the decision journal across findings, newest first.
 *
 * `GET /decisions`.
 */
export function listDecisions(
  input: ListDecisionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListDecisionsResult>> {
  return request<ListDecisionsResult>(OPERATIONS.listDecisions, input, options);
}

/**
 * List Document Tags
 *
 * `GET /projects/{project_uid}/document-tags`.
 */
export function listDocumentTags(
  input: ListDocumentTagsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListDocumentTagsResult>> {
  return request<ListDocumentTagsResult>(OPERATIONS.listDocumentTags, input, options);
}

/**
 * List the documents of one project, newest first.
 *
 * `GET /projects/{project_uid}/documents`.
 */
export function listDocuments(
  input: ListDocumentsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListDocumentsResult>> {
  return request<ListDocumentsResult>(OPERATIONS.listDocuments, input, options);
}

/**
 * List Journal
 *
 * `GET /execution/journal`.
 */
export function listExecutionJournal(
  input: ListExecutionJournalInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListExecutionJournalResult>> {
  return request<ListExecutionJournalResult>(OPERATIONS.listExecutionJournal, input, options);
}

/**
 * List Queue
 *
 * `GET /execution/queue`.
 */
export function listExecutionQueue(
  input: ListExecutionQueueInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListExecutionQueueResult>> {
  return request<ListExecutionQueueResult>(OPERATIONS.listExecutionQueue, input, options);
}

/**
 * List Executor Connections
 *
 * `GET /executor-connections`.
 */
export function listExecutorConnections(
  input: ListExecutorConnectionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListExecutorConnectionsResult>> {
  return request<ListExecutorConnectionsResult>(OPERATIONS.listExecutorConnections, input, options);
}

/**
 * List Executor Groups
 *
 * `GET /executor-groups`.
 */
export function listExecutorGroups(
  input: ListExecutorGroupsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListExecutorGroupsResult>> {
  return request<ListExecutorGroupsResult>(OPERATIONS.listExecutorGroups, input, options);
}

/**
 * List Executor Hosts
 *
 * `GET /executor-hosts`.
 */
export function listExecutorHosts(
  input: ListExecutorHostsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListExecutorHostsResult>> {
  return request<ListExecutorHostsResult>(OPERATIONS.listExecutorHosts, input, options);
}

/**
 * List Executor Routes
 *
 * `GET /executor-routes`.
 */
export function listExecutorRoutes(
  input: ListExecutorRoutesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListExecutorRoutesResult>> {
  return request<ListExecutorRoutesResult>(OPERATIONS.listExecutorRoutes, input, options);
}

/**
 * List Executor Routing Rules
 *
 * `GET /executor-routing-rules`.
 */
export function listExecutorRoutingRules(
  input: ListExecutorRoutingRulesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListExecutorRoutingRulesResult>> {
  return request<ListExecutorRoutingRulesResult>(OPERATIONS.listExecutorRoutingRules, input, options);
}

/**
 * List Knowledge Base Entries
 *
 * `GET /knowledge-base/entries`.
 */
export function listKnowledgeBaseEntries(
  input: ListKnowledgeBaseEntriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListKnowledgeBaseEntriesResult>> {
  return request<ListKnowledgeBaseEntriesResult>(OPERATIONS.listKnowledgeBaseEntries, input, options);
}

/**
 * List Model Catalogue
 *
 * `GET /model-catalogue`.
 */
export function listModelCatalogue(
  input: ListModelCatalogueInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListModelCatalogueResult>> {
  return request<ListModelCatalogueResult>(OPERATIONS.listModelCatalogue, input, options);
}

/**
 * List Norm Documents
 *
 * `GET /norm-documents`.
 */
export function listNormDocuments(
  input: ListNormDocumentsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListNormDocumentsResult>> {
  return request<ListNormDocumentsResult>(OPERATIONS.listNormDocuments, input, options);
}

/**
 * List Norm Paragraphs
 *
 * `GET /norm-documents/{norm_document_id}/paragraphs`.
 */
export function listNormParagraphs(
  input: ListNormParagraphsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListNormParagraphsResult>> {
  return request<ListNormParagraphsResult>(OPERATIONS.listNormParagraphs, input, options);
}

/**
 * List Norm Snapshot Events
 *
 * `GET /norms/snapshots/events`.
 */
export function listNormSnapshotEvents(
  input: ListNormSnapshotEventsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListNormSnapshotEventsResult>> {
  return request<ListNormSnapshotEventsResult>(OPERATIONS.listNormSnapshotEvents, input, options);
}

/**
 * List Norm Snapshots
 *
 * `GET /norms/snapshots`.
 */
export function listNormSnapshots(
  input: ListNormSnapshotsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListNormSnapshotsResult>> {
  return request<ListNormSnapshotsResult>(OPERATIONS.listNormSnapshots, input, options);
}

/**
 * List Optimisation Passes
 *
 * `GET /projects/{project_uid}/optimisation-passes`.
 */
export function listOptimisationPasses(
  input: ListOptimisationPassesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListOptimisationPassesResult>> {
  return request<ListOptimisationPassesResult>(OPERATIONS.listOptimisationPasses, input, options);
}

/**
 * List Optimisation Proposals
 *
 * `GET /optimisation-passes/{optimisation_pass_id}/proposals`.
 */
export function listOptimisationProposals(
  input: ListOptimisationProposalsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListOptimisationProposalsResult>> {
  return request<ListOptimisationProposalsResult>(OPERATIONS.listOptimisationProposals, input, options);
}

/**
 * List Precedent Settings
 *
 * `GET /precedent-settings`.
 */
export function listPrecedentSettings(
  input: ListPrecedentSettingsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListPrecedentSettingsResult>> {
  return request<ListPrecedentSettingsResult>(OPERATIONS.listPrecedentSettings, input, options);
}

/**
 * List Price List Positions
 *
 * `GET /price-lists/{price_list_id}/positions`.
 */
export function listPriceListPositions(
  input: ListPriceListPositionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListPriceListPositionsResult>> {
  return request<ListPriceListPositionsResult>(OPERATIONS.listPriceListPositions, input, options);
}

/**
 * List Price List Revisions
 *
 * `GET /projects/{project_uid}/price-lists`.
 */
export function listPriceListRevisions(
  input: ListPriceListRevisionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListPriceListRevisionsResult>> {
  return request<ListPriceListRevisionsResult>(OPERATIONS.listPriceListRevisions, input, options);
}

/**
 * List projects, newest first.
 *
 * `GET /projects`.
 */
export function listProjects(
  input: ListProjectsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListProjectsResult>> {
  return request<ListProjectsResult>(OPERATIONS.listProjects, input, options);
}

/**
 * List Proposal Decision Journal
 *
 * `GET /proposal-decisions`.
 */
export function listProposalDecisionJournal(
  input: ListProposalDecisionJournalInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListProposalDecisionJournalResult>> {
  return request<ListProposalDecisionJournalResult>(OPERATIONS.listProposalDecisionJournal, input, options);
}

/**
 * List Proposal Decisions
 *
 * `GET /optimisation-proposals/{optimisation_proposal_id}/decisions`.
 */
export function listProposalDecisions(
  input: ListProposalDecisionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListProposalDecisionsResult>> {
  return request<ListProposalDecisionsResult>(OPERATIONS.listProposalDecisions, input, options);
}

/**
 * List registration requests, oldest first.
 *
 * `GET /registrations`.
 */
export function listRegistrations(
  input: ListRegistrationsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListRegistrationsResult>> {
  return request<ListRegistrationsResult>(OPERATIONS.listRegistrations, input, options);
}

/**
 * List visible releases and what is new.
 *
 * `GET /releases`.
 */
export function listReleases(
  input: ListReleasesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListReleasesResult>> {
  return request<ListReleasesResult>(OPERATIONS.listReleases, input, options);
}

/**
 * List Run Finding Blocks
 *
 * `GET /runs/{run_id}/finding-blocks`.
 */
export function listRunFindingBlocks(
  input: ListRunFindingBlocksInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListRunFindingBlocksResult>> {
  return request<ListRunFindingBlocksResult>(OPERATIONS.listRunFindingBlocks, input, options);
}

/**
 * List the published findings of one run, with their evidence.
 *
 * `GET /runs/{run_id}/findings`.
 */
export function listRunFindings(
  input: ListRunFindingsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListRunFindingsResult>> {
  return request<ListRunFindingsResult>(OPERATIONS.listRunFindings, input, options);
}

/**
 * List the runs of one published version, newest first.
 *
 * `GET /versions/{version_uid}/runs`.
 */
export function listRuns(
  input: ListRunsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListRunsResult>> {
  return request<ListRunsResult>(OPERATIONS.listRuns, input, options);
}

/**
 * List Ai Reviews
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/ai-reviews`.
 */
export function listStageAiReviews(
  input: ListStageAiReviewsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageAiReviewsResult>> {
  return request<ListStageAiReviewsResult>(OPERATIONS.listStageAiReviews, input, options);
}

/**
 * List Verdicts
 *
 * `GET /stage-change-cards/{stage_change_card_id}/verdicts`.
 */
export function listStageCardVerdicts(
  input: ListStageCardVerdictsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageCardVerdictsResult>> {
  return request<ListStageCardVerdictsResult>(OPERATIONS.listStageCardVerdicts, input, options);
}

/**
 * List Stage Chain Runs
 *
 * `GET /stage-pairs/{stage_pair_id}/chain-runs`.
 */
export function listStageChainRuns(
  input: ListStageChainRunsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageChainRunsResult>> {
  return request<ListStageChainRunsResult>(OPERATIONS.listStageChainRuns, input, options);
}

/**
 * List Cards
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/cards`.
 */
export function listStageChangeCards(
  input: ListStageChangeCardsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageChangeCardsResult>> {
  return request<ListStageChangeCardsResult>(OPERATIONS.listStageChangeCards, input, options);
}

/**
 * List Classifications
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/classifications`.
 */
export function listStageClassifications(
  input: ListStageClassificationsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageClassificationsResult>> {
  return request<ListStageClassificationsResult>(OPERATIONS.listStageClassifications, input, options);
}

/**
 * List Graphics
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/graphic-evidence`.
 */
export function listStageGraphicEvidence(
  input: ListStageGraphicEvidenceInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageGraphicEvidenceResult>> {
  return request<ListStageGraphicEvidenceResult>(OPERATIONS.listStageGraphicEvidence, input, options);
}

/**
 * List Repairs
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/sheet-link-repairs`.
 */
export function listStageLinkRepairs(
  input: ListStageLinkRepairsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageLinkRepairsResult>> {
  return request<ListStageLinkRepairsResult>(OPERATIONS.listStageLinkRepairs, input, options);
}

/**
 * List Stage Pair Suggestions
 *
 * `GET /projects/{project_uid}/stage-pair-suggestions`.
 */
export function listStagePairSuggestions(
  input: ListStagePairSuggestionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStagePairSuggestionsResult>> {
  return request<ListStagePairSuggestionsResult>(OPERATIONS.listStagePairSuggestions, input, options);
}

/**
 * List Stage Pairs
 *
 * `GET /projects/{project_uid}/stage-pairs`.
 */
export function listStagePairs(
  input: ListStagePairsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStagePairsResult>> {
  return request<ListStagePairsResult>(OPERATIONS.listStagePairs, input, options);
}

/**
 * List Stage Raw Differences
 *
 * `GET /stage-link-revisions/{stage_link_revision_id}/raw-differences`.
 */
export function listStageRawDifferences(
  input: ListStageRawDifferencesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageRawDifferencesResult>> {
  return request<ListStageRawDifferencesResult>(OPERATIONS.listStageRawDifferences, input, options);
}

/**
 * List Stage Sheet Map History
 *
 * `GET /stage-pairs/{stage_pair_id}/sheet-map/revisions`.
 */
export function listStageSheetMapHistory(
  input: ListStageSheetMapHistoryInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageSheetMapHistoryResult>> {
  return request<ListStageSheetMapHistoryResult>(OPERATIONS.listStageSheetMapHistory, input, options);
}

/**
 * List Stage Sheet Passports
 *
 * `GET /stage-pairs/{stage_pair_id}/sheet-passports`.
 */
export function listStageSheetPassports(
  input: ListStageSheetPassportsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageSheetPassportsResult>> {
  return request<ListStageSheetPassportsResult>(OPERATIONS.listStageSheetPassports, input, options);
}

/**
 * List Stage Sheet Suggestions
 *
 * `GET /stage-pairs/{stage_pair_id}/sheet-suggestions`.
 */
export function listStageSheetSuggestions(
  input: ListStageSheetSuggestionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageSheetSuggestionsResult>> {
  return request<ListStageSheetSuggestionsResult>(OPERATIONS.listStageSheetSuggestions, input, options);
}

/**
 * List Stage Text Exclusions
 *
 * `GET /stage-link-revisions/{stage_link_revision_id}/text-exclusions`.
 */
export function listStageTextExclusions(
  input: ListStageTextExclusionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageTextExclusionsResult>> {
  return request<ListStageTextExclusionsResult>(OPERATIONS.listStageTextExclusions, input, options);
}

/**
 * List Stage Text Fragments
 *
 * `GET /stage-pairs/{stage_pair_id}/text-fragments`.
 */
export function listStageTextFragments(
  input: ListStageTextFragmentsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageTextFragmentsResult>> {
  return request<ListStageTextFragmentsResult>(OPERATIONS.listStageTextFragments, input, options);
}

/**
 * List Stage Text Hints
 *
 * `GET /stage-link-revisions/{stage_link_revision_id}/text-hints`.
 */
export function listStageTextHints(
  input: ListStageTextHintsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageTextHintsResult>> {
  return request<ListStageTextHintsResult>(OPERATIONS.listStageTextHints, input, options);
}

/**
 * List Stage Uploads
 *
 * `GET /projects/{project_uid}/stage-uploads`.
 */
export function listStageUploads(
  input: ListStageUploadsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListStageUploadsResult>> {
  return request<ListStageUploadsResult>(OPERATIONS.listStageUploads, input, options);
}

/**
 * List accounts, ordered by login.
 *
 * `GET /users`.
 */
export function listUsers(
  input: ListUsersInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListUsersResult>> {
  return request<ListUsersResult>(OPERATIONS.listUsers, input, options);
}

/**
 * List the stored page profiles of a version.
 *
 * `GET /versions/{version_uid}/page-profiles`.
 */
export function listVersionPageProfiles(
  input: ListVersionPageProfilesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListVersionPageProfilesResult>> {
  return request<ListVersionPageProfilesResult>(OPERATIONS.listVersionPageProfiles, input, options);
}

/**
 * List the portal blocks of one published version.
 *
 * `GET /versions/{version_uid}/portal-blocks`.
 */
export function listVersionPortalBlocks(
  input: ListVersionPortalBlocksInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListVersionPortalBlocksResult>> {
  return request<ListVersionPortalBlocksResult>(OPERATIONS.listVersionPortalBlocks, input, options);
}

/**
 * List Version Sheet Labels
 *
 * `GET /versions/{version_uid}/sheet-labels`.
 */
export function listVersionSheetLabels(
  input: ListVersionSheetLabelsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListVersionSheetLabelsResult>> {
  return request<ListVersionSheetLabelsResult>(OPERATIONS.listVersionSheetLabels, input, options);
}

/**
 * List the published versions of one document, newest first.
 *
 * `GET /documents/{document_uid}/versions`.
 */
export function listVersions(
  input: ListVersionsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListVersionsResult>> {
  return request<ListVersionsResult>(OPERATIONS.listVersions, input, options);
}

/**
 * List Workers
 *
 * `GET /execution/workers`.
 */
export function listWorkers(
  input: ListWorkersInput,
  options?: RequestOptions,
): Promise<ApiResponse<ListWorkersResult>> {
  return request<ListWorkersResult>(OPERATIONS.listWorkers, input, options);
}

/**
 * Mark release notes read through a version.
 *
 * `PUT /me/release-notes`.
 */
export function markReleaseNotesRead(
  input: MarkReleaseNotesReadInput,
  options?: RequestOptions,
): Promise<ApiResponse<MarkReleaseNotesReadResult>> {
  return request<MarkReleaseNotesReadResult>(OPERATIONS.markReleaseNotesRead, input, options);
}

/**
 * Pause an AI check of pairs.
 *
 * `POST /comparison-ai-pair-checks/{comparison_ai_job_id}/pause` - a write; carries a required Idempotency-Key.
 */
export function pauseComparisonAiPairCheck(
  input: PauseComparisonAiPairCheckInput,
  options?: RequestOptions,
): Promise<ApiResponse<PauseComparisonAiPairCheckResult>> {
  return request<PauseComparisonAiPairCheckResult>(OPERATIONS.pauseComparisonAiPairCheck, input, options);
}

/**
 * Pause an AI description of changes.
 *
 * `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/pause` - a write; carries a required Idempotency-Key.
 */
export function pauseComparisonAiSheetChanges(
  input: PauseComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<PauseComparisonAiSheetChangesResult>> {
  return request<PauseComparisonAiSheetChangesResult>(OPERATIONS.pauseComparisonAiSheetChanges, input, options);
}

/**
 * Pause the launch queue.
 *
 * `POST /projects/{project_uid}/comparison-launch-queue/pause` - a write; carries a required Idempotency-Key.
 */
export function pauseComparisonLaunchQueue(
  input: PauseComparisonLaunchQueueInput,
  options?: RequestOptions,
): Promise<ApiResponse<PauseComparisonLaunchQueueResult>> {
  return request<PauseComparisonLaunchQueueResult>(OPERATIONS.pauseComparisonLaunchQueue, input, options);
}

/**
 * Pause a series.
 *
 * `POST /comparison-series/{comparison_series_id}/pause` - a write; carries a required Idempotency-Key.
 */
export function pauseComparisonSeries(
  input: PauseComparisonSeriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<PauseComparisonSeriesResult>> {
  return request<PauseComparisonSeriesResult>(OPERATIONS.pauseComparisonSeries, input, options);
}

/**
 * Pause an upload batch after the set in hand.
 *
 * `POST /comparison-uploads/{comparison_upload_id}/pause` - a write; carries a required Idempotency-Key.
 */
export function pauseComparisonUpload(
  input: PauseComparisonUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<PauseComparisonUploadResult>> {
  return request<PauseComparisonUploadResult>(OPERATIONS.pauseComparisonUpload, input, options);
}

/**
 * Pause Batch
 *
 * `POST /stage-chain-batches/{stage_chain_batch_id}/pause` - a write; carries a required Idempotency-Key.
 */
export function pauseStageChainBatch(
  input: PauseStageChainBatchInput,
  options?: RequestOptions,
): Promise<ApiResponse<PauseStageChainBatchResult>> {
  return request<PauseStageChainBatchResult>(OPERATIONS.pauseStageChainBatch, input, options);
}

/**
 * Pause Stage Upload
 *
 * `POST /stage-uploads/{stage_upload_id}/pause` - a write; carries a required Idempotency-Key.
 */
export function pauseStageUpload(
  input: PauseStageUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<PauseStageUploadResult>> {
  return request<PauseStageUploadResult>(OPERATIONS.pauseStageUpload, input, options);
}

/**
 * Prepare the client report from an analytic report.
 *
 * `POST /comparison-reports/{comparison_report_id}/client-report` - a write; carries a required Idempotency-Key.
 */
export function prepareComparisonClientReport(
  input: PrepareComparisonClientReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<PrepareComparisonClientReportResult>> {
  return request<PrepareComparisonClientReportResult>(OPERATIONS.prepareComparisonClientReport, input, options);
}

/**
 * Queue the profiles and the build of the matrix of a document set.
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/preparation` - a write; carries a required Idempotency-Key.
 */
export function prepareComparisonMatrix(
  input: PrepareComparisonMatrixInput,
  options?: RequestOptions,
): Promise<ApiResponse<PrepareComparisonMatrixResult>> {
  return request<PrepareComparisonMatrixResult>(OPERATIONS.prepareComparisonMatrix, input, options);
}

/**
 * Preview Executor Routing
 *
 * `GET /executor-routing/preview`.
 */
export function previewExecutorRouting(
  input: PreviewExecutorRoutingInput,
  options?: RequestOptions,
): Promise<ApiResponse<PreviewExecutorRoutingResult>> {
  return request<PreviewExecutorRoutingResult>(OPERATIONS.previewExecutorRouting, input, options);
}

/**
 * Purge an archived, unreferenced account.
 *
 * `DELETE /users/{user_uid}`.
 */
export function purgeUser(
  input: PurgeUserInput,
  options?: RequestOptions,
): Promise<ApiResponse<PurgeUserResult>> {
  return request<PurgeUserResult>(OPERATIONS.purgeUser, input, options);
}

/**
 * Read whether a login and password pair proves a pending application.
 *
 * `POST /registrations/status`.
 */
export function readRegistrationStatus(
  input: ReadRegistrationStatusInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReadRegistrationStatusResult>> {
  return request<ReadRegistrationStatusResult>(OPERATIONS.readRegistrationStatus, input, options);
}

/**
 * Reaudit Run
 *
 * `POST /runs/{run_id}/reaudit` - a write; carries a required Idempotency-Key.
 */
export function reauditRun(
  input: ReauditRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReauditRunResult>> {
  return request<ReauditRunResult>(OPERATIONS.reauditRun, input, options);
}

/**
 * Write the PDF of a report again.
 *
 * `POST /comparison-reports/{comparison_report_id}/pdf-rebuild` - a write; carries a required Idempotency-Key.
 */
export function rebuildComparisonReportPdf(
  input: RebuildComparisonReportPdfInput,
  options?: RequestOptions,
): Promise<ApiResponse<RebuildComparisonReportPdfResult>> {
  return request<RebuildComparisonReportPdfResult>(OPERATIONS.rebuildComparisonReportPdf, input, options);
}

/**
 * Recompute Stage Text Evidence
 *
 * `POST /stage-link-revisions/{stage_link_revision_id}/text-evidence/recomputation` - a write; carries a required Idempotency-Key.
 */
export function recomputeStageTextEvidence(
  input: RecomputeStageTextEvidenceInput,
  options?: RequestOptions,
): Promise<ApiResponse<RecomputeStageTextEvidenceResult>> {
  return request<RecomputeStageTextEvidenceResult>(OPERATIONS.recomputeStageTextEvidence, input, options);
}

/**
 * Redeem Executor Enrollment
 *
 * `POST /runner/enroll`.
 */
export function redeemExecutorEnrollment(
  input: RedeemExecutorEnrollmentInput,
  options?: RequestOptions,
): Promise<ApiResponse<RedeemExecutorEnrollmentResult>> {
  return request<RedeemExecutorEnrollmentResult>(OPERATIONS.redeemExecutorEnrollment, input, options);
}

/**
 * Reject a registration request with a reason.
 *
 * `POST /registrations/{request_id}/reject`.
 */
export function rejectRegistration(
  input: RejectRegistrationInput,
  options?: RequestOptions,
): Promise<ApiResponse<RejectRegistrationResult>> {
  return request<RejectRegistrationResult>(OPERATIONS.rejectRegistration, input, options);
}

/**
 * Reject Stage Upload Candidate
 *
 * `POST /stage-upload-candidates/{stage_upload_candidate_id}/rejection` - a write; carries a required Idempotency-Key.
 */
export function rejectStageUploadCandidate(
  input: RejectStageUploadCandidateInput,
  options?: RequestOptions,
): Promise<ApiResponse<RejectStageUploadCandidateResult>> {
  return request<RejectStageUploadCandidateResult>(OPERATIONS.rejectStageUploadCandidate, input, options);
}

/**
 * Remove one entry from the launch queue.
 *
 * `POST /comparison-launch-entries/{comparison_launch_entry_id}/removal` - a write; carries a required Idempotency-Key.
 */
export function removeComparisonLaunchEntry(
  input: RemoveComparisonLaunchEntryInput,
  options?: RequestOptions,
): Promise<ApiResponse<RemoveComparisonLaunchEntryResult>> {
  return request<RemoveComparisonLaunchEntryResult>(OPERATIONS.removeComparisonLaunchEntry, input, options);
}

/**
 * Rename Document
 *
 * `PUT /projects/{project_uid}/documents/{document_uid}/title` - a write; carries a required Idempotency-Key.
 */
export function renameDocument(
  input: RenameDocumentInput,
  options?: RequestOptions,
): Promise<ApiResponse<RenameDocumentResult>> {
  return request<RenameDocumentResult>(OPERATIONS.renameDocument, input, options);
}

/**
 * Report Runner Health
 *
 * `POST /runner/health`.
 */
export function reportRunnerHealth(
  input: ReportRunnerHealthInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReportRunnerHealthResult>> {
  return request<ReportRunnerHealthResult>(OPERATIONS.reportRunnerHealth, input, options);
}

/**
 * Request Executor Probe
 *
 * `POST /executor-connections/{connection_id}/probes` - a write; carries a required Idempotency-Key.
 */
export function requestExecutorProbe(
  input: RequestExecutorProbeInput,
  options?: RequestOptions,
): Promise<ApiResponse<RequestExecutorProbeResult>> {
  return request<RequestExecutorProbeResult>(OPERATIONS.requestExecutorProbe, input, options);
}

/**
 * Set a temporary password for an account.
 *
 * `POST /users/{user_uid}/password`.
 */
export function resetUserPassword(
  input: ResetUserPasswordInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResetUserPasswordResult>> {
  return request<ResetUserPasswordResult>(OPERATIONS.resetUserPassword, input, options);
}

/**
 * Restore Decision Memory Case
 *
 * `POST /decision-memory/cases/{case_id}/restore` - a write; carries a required Idempotency-Key.
 */
export function restoreDecisionMemoryCase(
  input: RestoreDecisionMemoryCaseInput,
  options?: RequestOptions,
): Promise<ApiResponse<RestoreDecisionMemoryCaseResult>> {
  return request<RestoreDecisionMemoryCaseResult>(OPERATIONS.restoreDecisionMemoryCase, input, options);
}

/**
 * Restore an archived account.
 *
 * `POST /users/{user_uid}/restore`.
 */
export function restoreUser(
  input: RestoreUserInput,
  options?: RequestOptions,
): Promise<ApiResponse<RestoreUserResult>> {
  return request<RestoreUserResult>(OPERATIONS.restoreUser, input, options);
}

/**
 * Resume an AI check of pairs.
 *
 * `POST /comparison-ai-pair-checks/{comparison_ai_job_id}/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeComparisonAiPairCheck(
  input: ResumeComparisonAiPairCheckInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeComparisonAiPairCheckResult>> {
  return request<ResumeComparisonAiPairCheckResult>(OPERATIONS.resumeComparisonAiPairCheck, input, options);
}

/**
 * Resume an AI description of changes.
 *
 * `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeComparisonAiSheetChanges(
  input: ResumeComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeComparisonAiSheetChangesResult>> {
  return request<ResumeComparisonAiSheetChangesResult>(OPERATIONS.resumeComparisonAiSheetChanges, input, options);
}

/**
 * Resume the launch queue.
 *
 * `POST /projects/{project_uid}/comparison-launch-queue/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeComparisonLaunchQueue(
  input: ResumeComparisonLaunchQueueInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeComparisonLaunchQueueResult>> {
  return request<ResumeComparisonLaunchQueueResult>(OPERATIONS.resumeComparisonLaunchQueue, input, options);
}

/**
 * Resume a paused series.
 *
 * `POST /comparison-series/{comparison_series_id}/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeComparisonSeries(
  input: ResumeComparisonSeriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeComparisonSeriesResult>> {
  return request<ResumeComparisonSeriesResult>(OPERATIONS.resumeComparisonSeries, input, options);
}

/**
 * Resume a paused upload batch.
 *
 * `POST /comparison-uploads/{comparison_upload_id}/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeComparisonUpload(
  input: ResumeComparisonUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeComparisonUploadResult>> {
  return request<ResumeComparisonUploadResult>(OPERATIONS.resumeComparisonUpload, input, options);
}

/**
 * Resume Batch
 *
 * `POST /stage-chain-batches/{stage_chain_batch_id}/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeStageChainBatch(
  input: ResumeStageChainBatchInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeStageChainBatchResult>> {
  return request<ResumeStageChainBatchResult>(OPERATIONS.resumeStageChainBatch, input, options);
}

/**
 * Resume Run
 *
 * `POST /stage-chain-runs/{stage_chain_run_id}/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeStageChainRun(
  input: ResumeStageChainRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeStageChainRunResult>> {
  return request<ResumeStageChainRunResult>(OPERATIONS.resumeStageChainRun, input, options);
}

/**
 * Resume Stage Upload
 *
 * `POST /stage-uploads/{stage_upload_id}/resume` - a write; carries a required Idempotency-Key.
 */
export function resumeStageUpload(
  input: ResumeStageUploadInput,
  options?: RequestOptions,
): Promise<ApiResponse<ResumeStageUploadResult>> {
  return request<ResumeStageUploadResult>(OPERATIONS.resumeStageUpload, input, options);
}

/**
 * Describe the sheets that failed again.
 *
 * `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/retry` - a write; carries a required Idempotency-Key.
 */
export function retryComparisonAiSheetChanges(
  input: RetryComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<RetryComparisonAiSheetChangesResult>> {
  return request<RetryComparisonAiSheetChangesResult>(OPERATIONS.retryComparisonAiSheetChanges, input, options);
}

/**
 * Queue a failed set again.
 *
 * `POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/retry` - a write; carries a required Idempotency-Key.
 */
export function retryComparisonUploadSet(
  input: RetryComparisonUploadSetInput,
  options?: RequestOptions,
): Promise<ApiResponse<RetryComparisonUploadSetResult>> {
  return request<RetryComparisonUploadSetResult>(OPERATIONS.retryComparisonUploadSet, input, options);
}

/**
 * Review Decision Pattern
 *
 * `POST /decision-memory/patterns/{pattern_id}/review` - a write; carries a required Idempotency-Key.
 */
export function reviewDecisionPattern(
  input: ReviewDecisionPatternInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReviewDecisionPatternResult>> {
  return request<ReviewDecisionPatternResult>(OPERATIONS.reviewDecisionPattern, input, options);
}

/**
 * Revise an analysis preset.
 *
 * `POST /analysis/presets/{preset_id}/revisions` - a write; carries a required Idempotency-Key.
 */
export function reviseAnalysisPreset(
  input: ReviseAnalysisPresetInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReviseAnalysisPresetResult>> {
  return request<ReviseAnalysisPresetResult>(OPERATIONS.reviseAnalysisPreset, input, options);
}

/**
 * Revise Executor Connection
 *
 * `POST /executor-connections/{connection_id}/revisions` - a write; carries a required Idempotency-Key.
 */
export function reviseExecutorConnection(
  input: ReviseExecutorConnectionInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReviseExecutorConnectionResult>> {
  return request<ReviseExecutorConnectionResult>(OPERATIONS.reviseExecutorConnection, input, options);
}

/**
 * Revise Executor Group
 *
 * `POST /executor-groups/{group_id}/revisions` - a write; carries a required Idempotency-Key.
 */
export function reviseExecutorGroup(
  input: ReviseExecutorGroupInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReviseExecutorGroupResult>> {
  return request<ReviseExecutorGroupResult>(OPERATIONS.reviseExecutorGroup, input, options);
}

/**
 * Revise Stage Assembly
 *
 * `POST /stage-assemblies/{stage_assembly_id}/members` - a write; carries a required Idempotency-Key.
 */
export function reviseStageAssembly(
  input: ReviseStageAssemblyInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReviseStageAssemblyResult>> {
  return request<ReviseStageAssemblyResult>(OPERATIONS.reviseStageAssembly, input, options);
}

/**
 * Revise Stage Model Layout
 *
 * `POST /model-layout/revisions` - a write; carries a required Idempotency-Key.
 */
export function reviseStageModelLayout(
  input: ReviseStageModelLayoutInput,
  options?: RequestOptions,
): Promise<ApiResponse<ReviseStageModelLayoutResult>> {
  return request<ReviseStageModelLayoutResult>(OPERATIONS.reviseStageModelLayout, input, options);
}

/**
 * Revoke Runner Token
 *
 * `POST /executor-connections/{connection_id}/runner-tokens/{token_id}/revoke` - a write; carries a required Idempotency-Key.
 */
export function revokeRunnerToken(
  input: RevokeRunnerTokenInput,
  options?: RequestOptions,
): Promise<ApiResponse<RevokeRunnerTokenResult>> {
  return request<RevokeRunnerTokenResult>(OPERATIONS.revokeRunnerToken, input, options);
}

/**
 * Schedule Assignments
 *
 * `POST /work-schedule/reserve/moves` - a write; carries a required Idempotency-Key.
 */
export function scheduleAssignments(
  input: ScheduleAssignmentsInput,
  options?: RequestOptions,
): Promise<ApiResponse<ScheduleAssignmentsResult>> {
  return request<ScheduleAssignmentsResult>(OPERATIONS.scheduleAssignments, input, options);
}

/**
 * Search Norms
 *
 * `GET /norms/search`.
 */
export function searchNorms(
  input: SearchNormsInput,
  options?: RequestOptions,
): Promise<ApiResponse<SearchNormsResult>> {
  return request<SearchNormsResult>(OPERATIONS.searchNorms, input, options);
}

/**
 * Set Current Norm Snapshot
 *
 * `PUT /norms/snapshots/current`.
 */
export function setCurrentNormSnapshot(
  input: SetCurrentNormSnapshotInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetCurrentNormSnapshotResult>> {
  return request<SetCurrentNormSnapshotResult>(OPERATIONS.setCurrentNormSnapshot, input, options);
}

/**
 * Set Document Archived
 *
 * `PUT /projects/{project_uid}/documents/{document_uid}/archive` - a write; carries a required Idempotency-Key.
 */
export function setDocumentArchived(
  input: SetDocumentArchivedInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetDocumentArchivedResult>> {
  return request<SetDocumentArchivedResult>(OPERATIONS.setDocumentArchived, input, options);
}

/**
 * Set Document Tags
 *
 * `PUT /projects/{project_uid}/documents/{document_uid}/tags` - a write; carries a required Idempotency-Key.
 */
export function setDocumentTags(
  input: SetDocumentTagsInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetDocumentTagsResult>> {
  return request<SetDocumentTagsResult>(OPERATIONS.setDocumentTags, input, options);
}

/**
 * Set Engineer Absences
 *
 * `PUT /work-schedule/absences` - a write; carries a required Idempotency-Key.
 */
export function setEngineerAbsences(
  input: SetEngineerAbsencesInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetEngineerAbsencesResult>> {
  return request<SetEngineerAbsencesResult>(OPERATIONS.setEngineerAbsences, input, options);
}

/**
 * Set Paused
 *
 * `PUT /execution/dispatch` - a write; carries a required Idempotency-Key.
 */
export function setExecutionPaused(
  input: SetExecutionPausedInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutionPausedResult>> {
  return request<SetExecutionPausedResult>(OPERATIONS.setExecutionPaused, input, options);
}

/**
 * Set Executor Host Enabled
 *
 * `PUT /executor-hosts/{host_id}/enabled` - a write; carries a required Idempotency-Key.
 */
export function setExecutorHostEnabled(
  input: SetExecutorHostEnabledInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutorHostEnabledResult>> {
  return request<SetExecutorHostEnabledResult>(OPERATIONS.setExecutorHostEnabled, input, options);
}

/**
 * Set Executor Host Slots
 *
 * `PUT /executor-hosts/{host_id}/slots` - a write; carries a required Idempotency-Key.
 */
export function setExecutorHostSlots(
  input: SetExecutorHostSlotsInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutorHostSlotsResult>> {
  return request<SetExecutorHostSlotsResult>(OPERATIONS.setExecutorHostSlots, input, options);
}

/**
 * Set Executor Integration Authorisation
 *
 * `POST /executor-connections/{connection_id}/integration-authorisation` - a write; carries a required Idempotency-Key.
 */
export function setExecutorIntegrationAuthorisation(
  input: SetExecutorIntegrationAuthorisationInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutorIntegrationAuthorisationResult>> {
  return request<SetExecutorIntegrationAuthorisationResult>(OPERATIONS.setExecutorIntegrationAuthorisation, input, options);
}

/**
 * Set Executor Route
 *
 * `PUT /executor-routes` - a write; carries a required Idempotency-Key.
 */
export function setExecutorRoute(
  input: SetExecutorRouteInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutorRouteResult>> {
  return request<SetExecutorRouteResult>(OPERATIONS.setExecutorRoute, input, options);
}

/**
 * Set Executor Routing Mode
 *
 * `POST /executor-routing/mode` - a write; carries a required Idempotency-Key.
 */
export function setExecutorRoutingMode(
  input: SetExecutorRoutingModeInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutorRoutingModeResult>> {
  return request<SetExecutorRoutingModeResult>(OPERATIONS.setExecutorRoutingMode, input, options);
}

/**
 * Set Executor Routing Rule
 *
 * `PUT /executor-routing-rules/{work_kind}` - a write; carries a required Idempotency-Key.
 */
export function setExecutorRoutingRule(
  input: SetExecutorRoutingRuleInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutorRoutingRuleResult>> {
  return request<SetExecutorRoutingRuleResult>(OPERATIONS.setExecutorRoutingRule, input, options);
}

/**
 * Set Executor Secret
 *
 * `POST /executor-connections/{connection_id}/secrets` - a write; carries a required Idempotency-Key.
 */
export function setExecutorSecret(
  input: SetExecutorSecretInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetExecutorSecretResult>> {
  return request<SetExecutorSecretResult>(OPERATIONS.setExecutorSecret, input, options);
}

/**
 * Set Finding Execution Status
 *
 * `PUT /findings/{finding_uid}/execution-status` - a write; carries a required Idempotency-Key.
 */
export function setFindingExecutionStatus(
  input: SetFindingExecutionStatusInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetFindingExecutionStatusResult>> {
  return request<SetFindingExecutionStatusResult>(OPERATIONS.setFindingExecutionStatus, input, options);
}

/**
 * Set Global Vendor List
 *
 * `PUT /vendor-lists/{section_code}`.
 */
export function setGlobalVendorList(
  input: SetGlobalVendorListInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetGlobalVendorListResult>> {
  return request<SetGlobalVendorListResult>(OPERATIONS.setGlobalVendorList, input, options);
}

/**
 * Set Priority
 *
 * `PUT /execution/queue/{job_id}/priority` - a write; carries a required Idempotency-Key.
 */
export function setJobPriority(
  input: SetJobPriorityInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetJobPriorityResult>> {
  return request<SetJobPriorityResult>(OPERATIONS.setJobPriority, input, options);
}

/**
 * Set Project Vendor List
 *
 * `PUT /projects/{project_uid}/vendor-lists/{section_code}`.
 */
export function setProjectVendorList(
  input: SetProjectVendorListInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetProjectVendorListResult>> {
  return request<SetProjectVendorListResult>(OPERATIONS.setProjectVendorList, input, options);
}

/**
 * Set Stage Model Layout Enabled
 *
 * `PUT /model-layout/enabled` - a write; carries a required Idempotency-Key.
 */
export function setStageModelLayoutEnabled(
  input: SetStageModelLayoutEnabledInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetStageModelLayoutEnabledResult>> {
  return request<SetStageModelLayoutEnabledResult>(OPERATIONS.setStageModelLayoutEnabled, input, options);
}

/**
 * Set Stage Pair Completeness
 *
 * `POST /stage-pairs/{stage_pair_id}/completeness` - a write; carries a required Idempotency-Key.
 */
export function setStagePairCompleteness(
  input: SetStagePairCompletenessInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetStagePairCompletenessResult>> {
  return request<SetStagePairCompletenessResult>(OPERATIONS.setStagePairCompleteness, input, options);
}

/**
 * Set Vector Paused
 *
 * `PUT /vector-control/paused` - a write; carries a required Idempotency-Key.
 */
export function setVectorPaused(
  input: SetVectorPausedInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetVectorPausedResult>> {
  return request<SetVectorPausedResult>(OPERATIONS.setVectorPaused, input, options);
}

/**
 * Set Work Calendar Days
 *
 * `PUT /work-calendar/days` - a write; carries a required Idempotency-Key.
 */
export function setWorkCalendarDays(
  input: SetWorkCalendarDaysInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetWorkCalendarDaysResult>> {
  return request<SetWorkCalendarDaysResult>(OPERATIONS.setWorkCalendarDays, input, options);
}

/**
 * Set Work Schedule Plans
 *
 * `PUT /work-schedule/plans` - a write; carries a required Idempotency-Key.
 */
export function setWorkSchedulePlans(
  input: SetWorkSchedulePlansInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetWorkSchedulePlansResult>> {
  return request<SetWorkSchedulePlansResult>(OPERATIONS.setWorkSchedulePlans, input, options);
}

/**
 * Set Work Schedule Settings
 *
 * `PUT /work-schedule/settings` - a write; carries a required Idempotency-Key.
 */
export function setWorkScheduleSettings(
  input: SetWorkScheduleSettingsInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetWorkScheduleSettingsResult>> {
  return request<SetWorkScheduleSettingsResult>(OPERATIONS.setWorkScheduleSettings, input, options);
}

/**
 * Set Worker Intake
 *
 * `PUT /execution/workers/{worker_id}/intake` - a write; carries a required Idempotency-Key.
 */
export function setWorkerIntake(
  input: SetWorkerIntakeInput,
  options?: RequestOptions,
): Promise<ApiResponse<SetWorkerIntakeResult>> {
  return request<SetWorkerIntakeResult>(OPERATIONS.setWorkerIntake, input, options);
}

/**
 * Start the AI check of the doubtful pairs of a document set.
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check` - a write; carries a required Idempotency-Key.
 */
export function startComparisonAiPairCheck(
  input: StartComparisonAiPairCheckInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartComparisonAiPairCheckResult>> {
  return request<StartComparisonAiPairCheckResult>(OPERATIONS.startComparisonAiPairCheck, input, options);
}

/**
 * Start the AI description of changes of a series.
 *
 * `POST /comparison-series/{comparison_series_id}/ai-sheet-changes` - a write; carries a required Idempotency-Key.
 */
export function startComparisonAiSheetChanges(
  input: StartComparisonAiSheetChangesInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartComparisonAiSheetChangesResult>> {
  return request<StartComparisonAiSheetChangesResult>(OPERATIONS.startComparisonAiSheetChanges, input, options);
}

/**
 * Start a report draft.
 *
 * `POST /comparison-reports/{comparison_report_id}/start` - a write; carries a required Idempotency-Key.
 */
export function startComparisonReport(
  input: StartComparisonReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartComparisonReportResult>> {
  return request<StartComparisonReportResult>(OPERATIONS.startComparisonReport, input, options);
}

/**
 * Start the comparison of every adjacent pair of versions.
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/comparison-series` - a write; carries a required Idempotency-Key.
 */
export function startComparisonSeries(
  input: StartComparisonSeriesInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartComparisonSeriesResult>> {
  return request<StartComparisonSeriesResult>(OPERATIONS.startComparisonSeries, input, options);
}

/**
 * Describe one sheet with the AI.
 *
 * `POST /comparison-sheet-pairs/{comparison_sheet_pair_id}/description` - a write; carries a required Idempotency-Key.
 */
export function startComparisonSheetDescription(
  input: StartComparisonSheetDescriptionInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartComparisonSheetDescriptionResult>> {
  return request<StartComparisonSheetDescriptionResult>(OPERATIONS.startComparisonSheetDescription, input, options);
}

/**
 * Start the comparison of the whole specifications of a transition.
 *
 * `POST /comparison-transitions/{comparison_transition_id}/specification` - a write; carries a required Idempotency-Key.
 */
export function startComparisonSpecification(
  input: StartComparisonSpecificationInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartComparisonSpecificationResult>> {
  return request<StartComparisonSpecificationResult>(OPERATIONS.startComparisonSpecification, input, options);
}

/**
 * Start Optimisation Pass
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/optimisation-passes` - a write; carries a required Idempotency-Key.
 */
export function startOptimisationPass(
  input: StartOptimisationPassInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartOptimisationPassResult>> {
  return request<StartOptimisationPassResult>(OPERATIONS.startOptimisationPass, input, options);
}

/**
 * Start a text-consistency run over one published version.
 *
 * `POST /runs` - a write; carries a required Idempotency-Key.
 */
export function startRun(
  input: StartRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartRunResult>> {
  return request<StartRunResult>(OPERATIONS.startRun, input, options);
}

/**
 * Start Run From Stage
 *
 * `POST /runs/{run_id}/start-from-stage` - a write; carries a required Idempotency-Key.
 */
export function startRunFromStage(
  input: StartRunFromStageInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartRunFromStageResult>> {
  return request<StartRunFromStageResult>(OPERATIONS.startRunFromStage, input, options);
}

/**
 * Start Batch
 *
 * `POST /projects/{project_uid}/stage-chain-batches` - a write; carries a required Idempotency-Key.
 */
export function startStageChainBatch(
  input: StartStageChainBatchInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartStageChainBatchResult>> {
  return request<StartStageChainBatchResult>(OPERATIONS.startStageChainBatch, input, options);
}

/**
 * Start Stage Chain Run
 *
 * `POST /stage-pairs/{stage_pair_id}/chain-runs` - a write; carries a required Idempotency-Key.
 */
export function startStageChainRun(
  input: StartStageChainRunInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartStageChainRunResult>> {
  return request<StartStageChainRunResult>(OPERATIONS.startStageChainRun, input, options);
}

/**
 * Stream one tile PNG of a sheet pair.
 *
 * `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/tile`.
 */
export function streamComparisonPairTile(
  input: StreamComparisonPairTileInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamComparisonPairTileResult>> {
  return request<StreamComparisonPairTileResult>(OPERATIONS.streamComparisonPairTile, input, options);
}

/**
 * Download the PDF of a report.
 *
 * `GET /comparison-reports/{comparison_report_id}/pdf`.
 */
export function streamComparisonReportPdf(
  input: StreamComparisonReportPdfInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamComparisonReportPdfResult>> {
  return request<StreamComparisonReportPdfResult>(OPERATIONS.streamComparisonReportPdf, input, options);
}

/**
 * Download the MD a report was built from.
 *
 * `GET /comparison-reports/{comparison_report_id}/source-md`.
 */
export function streamComparisonReportSourceMd(
  input: StreamComparisonReportSourceMdInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamComparisonReportSourceMdResult>> {
  return request<StreamComparisonReportSourceMdResult>(OPERATIONS.streamComparisonReportSourceMd, input, options);
}

/**
 * Download the MD summary of a series.
 *
 * `GET /comparison-series/{comparison_series_id}/summary-md`.
 */
export function streamComparisonSeriesSummary(
  input: StreamComparisonSeriesSummaryInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamComparisonSeriesSummaryResult>> {
  return request<StreamComparisonSeriesSummaryResult>(OPERATIONS.streamComparisonSeriesSummary, input, options);
}

/**
 * Download the AI description of a sheet as Markdown.
 *
 * `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description/md`.
 */
export function streamComparisonSheetDescriptionMd(
  input: StreamComparisonSheetDescriptionMdInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamComparisonSheetDescriptionMdResult>> {
  return request<StreamComparisonSheetDescriptionMdResult>(OPERATIONS.streamComparisonSheetDescriptionMd, input, options);
}

/**
 * Stream Technical Report
 *
 * `GET /comparison-series/{comparison_series_id}/technical-report`.
 */
export function streamComparisonTechnicalReport(
  input: StreamComparisonTechnicalReportInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamComparisonTechnicalReportResult>> {
  return request<StreamComparisonTechnicalReportResult>(OPERATIONS.streamComparisonTechnicalReport, input, options);
}

/**
 * Stream the PDF bytes for the viewer.
 *
 * `GET /versions/{version_uid}/content`.
 */
export function streamDocumentVersionContent(
  input: StreamDocumentVersionContentInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamDocumentVersionContentResult>> {
  return request<StreamDocumentVersionContentResult>(OPERATIONS.streamDocumentVersionContent, input, options);
}

/**
 * Stream Norm Document Content
 *
 * `GET /norm-documents/{norm_document_id}/content`.
 */
export function streamNormDocumentContent(
  input: StreamNormDocumentContentInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamNormDocumentContentResult>> {
  return request<StreamNormDocumentContentResult>(OPERATIONS.streamNormDocumentContent, input, options);
}

/**
 * Journal Html
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/journal.html`.
 */
export function streamStageChangeJournalHtml(
  input: StreamStageChangeJournalHtmlInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamStageChangeJournalHtmlResult>> {
  return request<StreamStageChangeJournalHtmlResult>(OPERATIONS.streamStageChangeJournalHtml, input, options);
}

/**
 * Journal Pdf
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/journal.pdf`.
 */
export function streamStageChangeJournalPdf(
  input: StreamStageChangeJournalPdfInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamStageChangeJournalPdfResult>> {
  return request<StreamStageChangeJournalPdfResult>(OPERATIONS.streamStageChangeJournalPdf, input, options);
}

/**
 * Journal Xlsx
 *
 * `GET /stage-chain-runs/{stage_chain_run_id}/journal.xlsx`.
 */
export function streamStageChangeJournalXlsx(
  input: StreamStageChangeJournalXlsxInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamStageChangeJournalXlsxResult>> {
  return request<StreamStageChangeJournalXlsxResult>(OPERATIONS.streamStageChangeJournalXlsx, input, options);
}

/**
 * Stream the stored preview PNG of one page.
 *
 * `GET /page-profiles/{comparison_page_profile_id}/preview`.
 */
export function streamVersionPagePreview(
  input: StreamVersionPagePreviewInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamVersionPagePreviewResult>> {
  return request<StreamVersionPagePreviewResult>(OPERATIONS.streamVersionPagePreview, input, options);
}

/**
 * Stream the stored thumbnail PNG of one page.
 *
 * `GET /page-profiles/{comparison_page_profile_id}/thumbnail`.
 */
export function streamVersionPageThumbnail(
  input: StreamVersionPageThumbnailInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamVersionPageThumbnailResult>> {
  return request<StreamVersionPageThumbnailResult>(OPERATIONS.streamVersionPageThumbnail, input, options);
}

/**
 * Stream one tile PNG of a page's bounded pyramid.
 *
 * `GET /page-profiles/{comparison_page_profile_id}/tile`.
 */
export function streamVersionPageTile(
  input: StreamVersionPageTileInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamVersionPageTileResult>> {
  return request<StreamVersionPageTileResult>(OPERATIONS.streamVersionPageTile, input, options);
}

/**
 * Stream the PNG this product cut for one IMAGE block.
 *
 * `GET /versions/{version_uid}/portal-blocks/{portal_block_id}/crop`.
 */
export function streamVersionPortalBlockCrop(
  input: StreamVersionPortalBlockCropInput,
  options?: RequestOptions,
): Promise<ApiResponse<StreamVersionPortalBlockCropResult>> {
  return request<StreamVersionPortalBlockCropResult>(OPERATIONS.streamVersionPortalBlockCrop, input, options);
}

/**
 * Submit Executor Task Answer
 *
 * `POST /runner/tasks/{task_id}/answer`.
 */
export function submitExecutorTaskAnswer(
  input: SubmitExecutorTaskAnswerInput,
  options?: RequestOptions,
): Promise<ApiResponse<SubmitExecutorTaskAnswerResult>> {
  return request<SubmitExecutorTaskAnswerResult>(OPERATIONS.submitExecutorTaskAnswer, input, options);
}

/**
 * Apply for an account.
 *
 * `POST /registrations`.
 */
export function submitRegistration(
  input: SubmitRegistrationInput,
  options?: RequestOptions,
): Promise<ApiResponse<SubmitRegistrationResult>> {
  return request<SubmitRegistrationResult>(OPERATIONS.submitRegistration, input, options);
}

/**
 * Move an assignment: start, complete, return, reassign or cancel it.
 *
 * `POST /assignments/{assignment_uid}/transitions`.
 */
export function transitionAssignment(
  input: TransitionAssignmentInput,
  options?: RequestOptions,
): Promise<ApiResponse<TransitionAssignmentResult>> {
  return request<TransitionAssignmentResult>(OPERATIONS.transitionAssignment, input, options);
}

/**
 * Reverse the latest applied manual matrix edit.
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits/undo` - a write; carries a required Idempotency-Key.
 */
export function undoComparisonMatrixEdit(
  input: UndoComparisonMatrixEditInput,
  options?: RequestOptions,
): Promise<ApiResponse<UndoComparisonMatrixEditResult>> {
  return request<UndoComparisonMatrixEditResult>(OPERATIONS.undoComparisonMatrixEdit, input, options);
}

/**
 * Undo Repair
 *
 * `POST /stage-link-repairs/{stage_link_repair_id}/undo` - a write; carries a required Idempotency-Key.
 */
export function undoStageLinkRepair(
  input: UndoStageLinkRepairInput,
  options?: RequestOptions,
): Promise<ApiResponse<UndoStageLinkRepairResult>> {
  return request<UndoStageLinkRepairResult>(OPERATIONS.undoStageLinkRepair, input, options);
}

/**
 * Set the signed-in account's names, and complete its profile.
 *
 * `PATCH /me`.
 */
export function updateMyProfile(
  input: UpdateMyProfileInput,
  options?: RequestOptions,
): Promise<ApiResponse<UpdateMyProfileResult>> {
  return request<UpdateMyProfileResult>(OPERATIONS.updateMyProfile, input, options);
}

/**
 * Change an account's names, its role set, or both.
 *
 * `PATCH /users/{user_uid}`.
 */
export function updateUser(
  input: UpdateUserInput,
  options?: RequestOptions,
): Promise<ApiResponse<UpdateUserResult>> {
  return request<UpdateUserResult>(OPERATIONS.updateUser, input, options);
}

/**
 * Make a report draft from an uploaded MD file.
 *
 * `POST /comparison-series/{comparison_series_id}/reports/upload` - a write; carries a required Idempotency-Key.
 */
export function uploadComparisonReportSource(
  input: UploadComparisonReportSourceInput,
  options?: RequestOptions,
): Promise<ApiResponse<UploadComparisonReportSourceResult>> {
  return request<UploadComparisonReportSourceResult>(OPERATIONS.uploadComparisonReportSource, input, options);
}

/**
 * Stage one part of one file of an upload batch.
 *
 * `PUT /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/parts` - a write; carries a required Idempotency-Key.
 */
export function uploadComparisonUploadPart(
  input: UploadComparisonUploadPartInput,
  options?: RequestOptions,
): Promise<ApiResponse<UploadComparisonUploadPartResult>> {
  return request<UploadComparisonUploadPartResult>(OPERATIONS.uploadComparisonUploadPart, input, options);
}

/**
 * Upload one portal bundle and publish an immutable document version.
 *
 * `POST /projects/{project_uid}/documents` - a write; carries a required Idempotency-Key.
 */
export function uploadDocument(
  input: UploadDocumentInput,
  options?: RequestOptions,
): Promise<ApiResponse<UploadDocumentResult>> {
  return request<UploadDocumentResult>(OPERATIONS.uploadDocument, input, options);
}

/**
 * Upload one portal bundle as the next immutable version of an existing document.
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/versions` - a write; carries a required Idempotency-Key.
 */
export function uploadDocumentVersion(
  input: UploadDocumentVersionInput,
  options?: RequestOptions,
): Promise<ApiResponse<UploadDocumentVersionResult>> {
  return request<UploadDocumentVersionResult>(OPERATIONS.uploadDocumentVersion, input, options);
}

/**
 * Upload Price List
 *
 * `POST /projects/{project_uid}/price-lists` - a write; carries a required Idempotency-Key.
 */
export function uploadPriceList(
  input: UploadPriceListInput,
  options?: RequestOptions,
): Promise<ApiResponse<UploadPriceListResult>> {
  return request<UploadPriceListResult>(OPERATIONS.uploadPriceList, input, options);
}

/**
 * Upload Stage Upload Part
 *
 * `PUT /stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/parts` - a write; carries a required Idempotency-Key.
 */
export function uploadStageUploadPart(
  input: UploadStageUploadPartInput,
  options?: RequestOptions,
): Promise<ApiResponse<UploadStageUploadPartResult>> {
  return request<UploadStageUploadPartResult>(OPERATIONS.uploadStageUploadPart, input, options);
}

/**
 * Withdraw Decision Memory Case
 *
 * `POST /decision-memory/cases/{case_id}/withdraw` - a write; carries a required Idempotency-Key.
 */
export function withdrawDecisionMemoryCase(
  input: WithdrawDecisionMemoryCaseInput,
  options?: RequestOptions,
): Promise<ApiResponse<WithdrawDecisionMemoryCaseResult>> {
  return request<WithdrawDecisionMemoryCaseResult>(OPERATIONS.withdrawDecisionMemoryCase, input, options);
}

/**
 * Withdraw Sheet Pairing
 *
 * `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings/{sheet_link_id}/withdrawals` - a write; carries a required Idempotency-Key.
 */
export function withdrawSheetPairing(
  input: WithdrawSheetPairingInput,
  options?: RequestOptions,
): Promise<ApiResponse<WithdrawSheetPairingResult>> {
  return request<WithdrawSheetPairingResult>(OPERATIONS.withdrawSheetPairing, input, options);
}

/**
 * The whole client as one object, for a consumer that would rather inject it than
 * import each function. The named exports above are the ordinary way in.
 */
export const apiClient = {
  appendComparisonVersionOrder,
  appendDecision,
  appendPrecedentSetting,
  applyComparisonMatrixEdits,
  applyStageCardVerdicts,
  applyStageSheetMap,
  approveRegistration,
  approveSheetPairing,
  archiveAnalysisPreset,
  archiveExecutorConnection,
  archiveExecutorGroup,
  archiveExecutorHost,
  archiveUser,
  cancelComparisonAiPairCheck,
  cancelComparisonAiSheetChanges,
  cancelComparisonReport,
  cancelComparisonSeries,
  cancelComparisonSpecification,
  cancelComparisonUpload,
  cancelRun,
  cancelStageChainBatch,
  cancelStageChainRun,
  cancelStageUpload,
  carryOverDecision,
  carryOverProposalDecisions,
  changePassword,
  claimExecutorTask,
  classifyDocumentVersion,
  clearComparisonLaunchQueue,
  compareDocumentVersions,
  completeComparisonUploadFile,
  completeStageUploadFile,
  confirmComparisonUploadSet,
  confirmExecutorAgentInstallHostKey,
  confirmExecutorHostAgentInstallHostKey,
  confirmStagePair,
  confirmStageUploadCandidate,
  continueComparisonReport,
  correctVersionClassification,
  createAnalysisPreset,
  createAssignment,
  createComparisonReport,
  createComparisonUpload,
  createExecutorAgentInstall,
  createExecutorConnection,
  createExecutorGroup,
  createExecutorHostAgentInstall,
  createProject,
  createStageAssembly,
  createStageReviewCard,
  createStageUpload,
  decideOptimisationProposal,
  deleteComparisonReport,
  deleteRun,
  dequeueComparisonAiSheetChanges,
  downloadAgentPackage,
  endUserSessions,
  enqueueComparisonLaunch,
  estimateComparisonAiPairCheck,
  estimateComparisonAiSheetChanges,
  estimateComparisonSheetDescription,
  estimateComparisonSpecification,
  estimateRunCost,
  estimateStageChainRun,
  excludeComparisonUploadSet,
  exportOptimisationProposalsCsv,
  exportOptimisationProposalsXlsx,
  exportRunCsv,
  exportRunXlsx,
  extendExecutorTaskClaim,
  failExecutorTask,
  finishComparisonAiSheetChanges,
  finishComparisonSeries,
  generateComparisonSummary,
  generateExecutorSshKey,
  getAssignment,
  getComparisonAiPairCheck,
  getComparisonAiQueue,
  getComparisonAiSheetChanges,
  getComparisonLaunchQueue,
  getComparisonMatrix,
  getComparisonOverview,
  getComparisonQueueSummary,
  getComparisonReport,
  getComparisonSeries,
  getComparisonSheetDescription,
  getComparisonSheetPair,
  getComparisonSheetPairSpecPositions,
  getComparisonSpecification,
  getComparisonUpload,
  getComparisonUploadProposal,
  getDashboardSummary,
  getDecisionMemoryCase,
  getDecisionMemoryStatus,
  getDocumentVersion,
  getEffectiveVendorLists,
  getExecutionDispatch,
  getExecutorAgentInstall,
  getExecutorConnection,
  getExecutorGroup,
  getExecutorGroupCapacity,
  getExecutorHost,
  getExecutorHostAgentInstall,
  getExecutorHostDetails,
  getExecutorTaskContext,
  getExecutorTaskImage,
  getExtendedRunReview,
  getFinding,
  getFindingPrecedents,
  getMe,
  getNormDocument,
  getProductVersion,
  getProject,
  getQualityTable,
  getRunNormReferences,
  getRunPrecedents,
  getRunStages,
  getRunStartReadiness,
  getRunStatus,
  getSectionSpecification,
  getSpecificationPrices,
  getStageAssembly,
  getStageChainBatch,
  getStageChainRun,
  getStageChangeCard,
  getStageChangeJournal,
  getStageModelLayout,
  getStagePair,
  getStageProfileText,
  getStageSheetMap,
  getStageSheetMapRevision,
  getStageSynthesis,
  getStageUpload,
  getUser,
  getVectorControl,
  getVersionBlocks,
  getVersionPageProfile,
  getVersionPageSpecPositions,
  getVersionSectionReview,
  getWorkSchedule,
  getWorkScheduleReserve,
  importComparisonZip,
  importOptimisationProposalDecisions,
  importRunDecisions,
  issueExecutorEnrollment,
  issueExecutorHostEnrollment,
  issueRunnerToken,
  issueToken,
  listAcceptedOptimisationProposals,
  listAnalysisPresets,
  listAnalysisProfiles,
  listAssignments,
  listAuthEvents,
  listComparisonAiLinks,
  listComparisonAiPairHints,
  listComparisonMatrixEdits,
  listComparisonReports,
  listComparisonReviewSheets,
  listComparisonSeries,
  listComparisonSheetDescriptionHistory,
  listComparisonSheetPairs,
  listComparisonSpecificationChanges,
  listComparisonSpecifications,
  listComparisonUploads,
  listComparisonVersionOrders,
  listDecisionHistory,
  listDecisionMemoryCases,
  listDecisionPatterns,
  listDecisions,
  listDocumentTags,
  listDocuments,
  listExecutionJournal,
  listExecutionQueue,
  listExecutorConnections,
  listExecutorGroups,
  listExecutorHosts,
  listExecutorRoutes,
  listExecutorRoutingRules,
  listKnowledgeBaseEntries,
  listModelCatalogue,
  listNormDocuments,
  listNormParagraphs,
  listNormSnapshotEvents,
  listNormSnapshots,
  listOptimisationPasses,
  listOptimisationProposals,
  listPrecedentSettings,
  listPriceListPositions,
  listPriceListRevisions,
  listProjects,
  listProposalDecisionJournal,
  listProposalDecisions,
  listRegistrations,
  listReleases,
  listRunFindingBlocks,
  listRunFindings,
  listRuns,
  listStageAiReviews,
  listStageCardVerdicts,
  listStageChainRuns,
  listStageChangeCards,
  listStageClassifications,
  listStageGraphicEvidence,
  listStageLinkRepairs,
  listStagePairSuggestions,
  listStagePairs,
  listStageRawDifferences,
  listStageSheetMapHistory,
  listStageSheetPassports,
  listStageSheetSuggestions,
  listStageTextExclusions,
  listStageTextFragments,
  listStageTextHints,
  listStageUploads,
  listUsers,
  listVersionPageProfiles,
  listVersionPortalBlocks,
  listVersionSheetLabels,
  listVersions,
  listWorkers,
  markReleaseNotesRead,
  pauseComparisonAiPairCheck,
  pauseComparisonAiSheetChanges,
  pauseComparisonLaunchQueue,
  pauseComparisonSeries,
  pauseComparisonUpload,
  pauseStageChainBatch,
  pauseStageUpload,
  prepareComparisonClientReport,
  prepareComparisonMatrix,
  previewExecutorRouting,
  purgeUser,
  readRegistrationStatus,
  reauditRun,
  rebuildComparisonReportPdf,
  recomputeStageTextEvidence,
  redeemExecutorEnrollment,
  rejectRegistration,
  rejectStageUploadCandidate,
  removeComparisonLaunchEntry,
  renameDocument,
  reportRunnerHealth,
  requestExecutorProbe,
  resetUserPassword,
  restoreDecisionMemoryCase,
  restoreUser,
  resumeComparisonAiPairCheck,
  resumeComparisonAiSheetChanges,
  resumeComparisonLaunchQueue,
  resumeComparisonSeries,
  resumeComparisonUpload,
  resumeStageChainBatch,
  resumeStageChainRun,
  resumeStageUpload,
  retryComparisonAiSheetChanges,
  retryComparisonUploadSet,
  reviewDecisionPattern,
  reviseAnalysisPreset,
  reviseExecutorConnection,
  reviseExecutorGroup,
  reviseStageAssembly,
  reviseStageModelLayout,
  revokeRunnerToken,
  scheduleAssignments,
  searchNorms,
  setCurrentNormSnapshot,
  setDocumentArchived,
  setDocumentTags,
  setEngineerAbsences,
  setExecutionPaused,
  setExecutorHostEnabled,
  setExecutorHostSlots,
  setExecutorIntegrationAuthorisation,
  setExecutorRoute,
  setExecutorRoutingMode,
  setExecutorRoutingRule,
  setExecutorSecret,
  setFindingExecutionStatus,
  setGlobalVendorList,
  setJobPriority,
  setProjectVendorList,
  setStageModelLayoutEnabled,
  setStagePairCompleteness,
  setVectorPaused,
  setWorkCalendarDays,
  setWorkSchedulePlans,
  setWorkScheduleSettings,
  setWorkerIntake,
  startComparisonAiPairCheck,
  startComparisonAiSheetChanges,
  startComparisonReport,
  startComparisonSeries,
  startComparisonSheetDescription,
  startComparisonSpecification,
  startOptimisationPass,
  startRun,
  startRunFromStage,
  startStageChainBatch,
  startStageChainRun,
  streamComparisonPairTile,
  streamComparisonReportPdf,
  streamComparisonReportSourceMd,
  streamComparisonSeriesSummary,
  streamComparisonSheetDescriptionMd,
  streamComparisonTechnicalReport,
  streamDocumentVersionContent,
  streamNormDocumentContent,
  streamStageChangeJournalHtml,
  streamStageChangeJournalPdf,
  streamStageChangeJournalXlsx,
  streamVersionPagePreview,
  streamVersionPageThumbnail,
  streamVersionPageTile,
  streamVersionPortalBlockCrop,
  submitExecutorTaskAnswer,
  submitRegistration,
  transitionAssignment,
  undoComparisonMatrixEdit,
  undoStageLinkRepair,
  updateMyProfile,
  updateUser,
  uploadComparisonReportSource,
  uploadComparisonUploadPart,
  uploadDocument,
  uploadDocumentVersion,
  uploadPriceList,
  uploadStageUploadPart,
  withdrawDecisionMemoryCase,
  withdrawSheetPairing,
} as const;
