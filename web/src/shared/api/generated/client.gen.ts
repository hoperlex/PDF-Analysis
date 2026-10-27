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
 *   AuditManager PC-01 API 1.8.0 (OpenAPI 3.1.0)
 *   sha256 b215912031f940b4cb20da7a80ad66b6ff2deec4274cba6cf2e0c72a29489be3
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

import type { ApiResponse, RequestOptions } from '../transport';
import { request } from '../transport';
import type {
  AppendDecisionInput,
  AppendDecisionResult,
  ApproveRegistrationInput,
  ApproveRegistrationResult,
  ApproveSheetPairingInput,
  ApproveSheetPairingResult,
  ArchiveAnalysisPresetInput,
  ArchiveAnalysisPresetResult,
  ArchiveExecutorConnectionInput,
  ArchiveExecutorConnectionResult,
  ArchiveUserInput,
  ArchiveUserResult,
  CancelRunInput,
  CancelRunResult,
  CarryOverDecisionInput,
  CarryOverDecisionResult,
  ChangePasswordInput,
  ChangePasswordResult,
  ClaimExecutorTaskInput,
  ClaimExecutorTaskResult,
  ClassifyDocumentVersionInput,
  ClassifyDocumentVersionResult,
  CompareDocumentVersionsInput,
  CompareDocumentVersionsResult,
  CorrectVersionClassificationInput,
  CorrectVersionClassificationResult,
  CreateAnalysisPresetInput,
  CreateAnalysisPresetResult,
  CreateAssignmentInput,
  CreateAssignmentResult,
  CreateExecutorConnectionInput,
  CreateExecutorConnectionResult,
  CreateProjectInput,
  CreateProjectResult,
  DecideOptimisationProposalInput,
  DecideOptimisationProposalResult,
  ExportOptimisationProposalsCsvInput,
  ExportOptimisationProposalsCsvResult,
  ExportRunCsvInput,
  ExportRunCsvResult,
  ExportRunXlsxInput,
  ExportRunXlsxResult,
  ExtendExecutorTaskClaimInput,
  ExtendExecutorTaskClaimResult,
  FailExecutorTaskInput,
  FailExecutorTaskResult,
  GenerateComparisonSummaryInput,
  GenerateComparisonSummaryResult,
  GenerateExecutorSshKeyInput,
  GenerateExecutorSshKeyResult,
  GetArV3BetaGroupInput,
  GetArV3BetaGroupResult,
  GetArV3BetaGroupReviewInput,
  GetArV3BetaGroupReviewResult,
  GetArV3BetaPackStatusInput,
  GetArV3BetaPackStatusResult,
  GetAssignmentInput,
  GetAssignmentResult,
  GetDashboardSummaryInput,
  GetDashboardSummaryResult,
  GetDocumentVersionInput,
  GetDocumentVersionResult,
  GetEffectiveVendorListsInput,
  GetEffectiveVendorListsResult,
  GetExecutorConnectionInput,
  GetExecutorConnectionResult,
  GetExecutorTaskImageInput,
  GetExecutorTaskImageResult,
  GetFindingInput,
  GetFindingResult,
  GetMeInput,
  GetMeResult,
  GetNormDocumentInput,
  GetNormDocumentResult,
  GetProductVersionInput,
  GetProductVersionResult,
  GetRunNormReferencesInput,
  GetRunNormReferencesResult,
  GetRunNormVerificationInput,
  GetRunNormVerificationResult,
  GetRunStatusInput,
  GetRunStatusResult,
  GetSectionSpecificationInput,
  GetSectionSpecificationResult,
  GetSpecificationPricesInput,
  GetSpecificationPricesResult,
  GetUserInput,
  GetUserResult,
  GetVersionBlocksInput,
  GetVersionBlocksResult,
  GetVersionSectionReviewInput,
  GetVersionSectionReviewResult,
  IssueRunnerTokenInput,
  IssueRunnerTokenResult,
  IssueTokenInput,
  IssueTokenResult,
  ListAnalysisPresetsInput,
  ListAnalysisPresetsResult,
  ListAnalysisProfilesInput,
  ListAnalysisProfilesResult,
  ListAssignmentsInput,
  ListAssignmentsResult,
  ListDecisionHistoryInput,
  ListDecisionHistoryResult,
  ListDecisionsInput,
  ListDecisionsResult,
  ListDocumentsInput,
  ListDocumentsResult,
  ListExecutionJournalInput,
  ListExecutionJournalResult,
  ListExecutionQueueInput,
  ListExecutionQueueResult,
  ListExecutorConnectionsInput,
  ListExecutorConnectionsResult,
  ListExecutorRoutesInput,
  ListExecutorRoutesResult,
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
  ListPriceListPositionsInput,
  ListPriceListPositionsResult,
  ListPriceListRevisionsInput,
  ListPriceListRevisionsResult,
  ListProjectsInput,
  ListProjectsResult,
  ListProposalDecisionsInput,
  ListProposalDecisionsResult,
  ListRegistrationsInput,
  ListRegistrationsResult,
  ListReleasesInput,
  ListReleasesResult,
  ListRunFindingsInput,
  ListRunFindingsResult,
  ListRunsInput,
  ListRunsResult,
  ListUsersInput,
  ListUsersResult,
  ListVersionPortalBlocksInput,
  ListVersionPortalBlocksResult,
  ListVersionsInput,
  ListVersionsResult,
  ListWorkersInput,
  ListWorkersResult,
  MarkReleaseNotesReadInput,
  MarkReleaseNotesReadResult,
  PurgeUserInput,
  PurgeUserResult,
  ReadRegistrationStatusInput,
  ReadRegistrationStatusResult,
  ReauditRunInput,
  ReauditRunResult,
  RejectRegistrationInput,
  RejectRegistrationResult,
  RequestExecutorProbeInput,
  RequestExecutorProbeResult,
  ResetUserPasswordInput,
  ResetUserPasswordResult,
  RestoreUserInput,
  RestoreUserResult,
  ReviseAnalysisPresetInput,
  ReviseAnalysisPresetResult,
  ReviseExecutorConnectionInput,
  ReviseExecutorConnectionResult,
  RevokeRunnerTokenInput,
  RevokeRunnerTokenResult,
  SearchNormsInput,
  SearchNormsResult,
  SetCurrentNormSnapshotInput,
  SetCurrentNormSnapshotResult,
  SetExecutionPausedInput,
  SetExecutionPausedResult,
  SetExecutorRouteInput,
  SetExecutorRouteResult,
  SetExecutorSecretInput,
  SetExecutorSecretResult,
  SetGlobalVendorListInput,
  SetGlobalVendorListResult,
  SetJobPriorityInput,
  SetJobPriorityResult,
  SetProjectVendorListInput,
  SetProjectVendorListResult,
  SetWorkerIntakeInput,
  SetWorkerIntakeResult,
  StartArV3BetaGroupInput,
  StartArV3BetaGroupResult,
  StartOptimisationPassInput,
  StartOptimisationPassResult,
  StartRunInput,
  StartRunResult,
  StreamDocumentVersionContentInput,
  StreamDocumentVersionContentResult,
  StreamNormDocumentContentInput,
  StreamNormDocumentContentResult,
  StreamVersionPortalBlockCropInput,
  StreamVersionPortalBlockCropResult,
  SubmitExecutorTaskAnswerInput,
  SubmitExecutorTaskAnswerResult,
  SubmitRegistrationInput,
  SubmitRegistrationResult,
  TransitionAssignmentInput,
  TransitionAssignmentResult,
  UpdateMyProfileInput,
  UpdateMyProfileResult,
  UpdateUserInput,
  UpdateUserResult,
  UploadDocumentInput,
  UploadDocumentResult,
  UploadDocumentVersionInput,
  UploadDocumentVersionResult,
  UploadPriceListInput,
  UploadPriceListResult,
  WithdrawSheetPairingInput,
  WithdrawSheetPairingResult,
} from './operations.gen';
import { OPERATIONS } from './operations.gen';

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
 * Get Ar V3 Beta Group
 *
 * `GET /ar-v3-beta/groups/{group_id}`.
 */
export function getArV3BetaGroup(
  input: GetArV3BetaGroupInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetArV3BetaGroupResult>> {
  return request<GetArV3BetaGroupResult>(OPERATIONS.getArV3BetaGroup, input, options);
}

/**
 * Get Ar V3 Beta Group Review
 *
 * `GET /ar-v3-beta/groups/{group_id}/review`.
 */
export function getArV3BetaGroupReview(
  input: GetArV3BetaGroupReviewInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetArV3BetaGroupReviewResult>> {
  return request<GetArV3BetaGroupReviewResult>(OPERATIONS.getArV3BetaGroupReview, input, options);
}

/**
 * Get Ar V3 Beta Pack Status
 *
 * `GET /ar-v3-beta/pack`.
 */
export function getArV3BetaPackStatus(
  input: GetArV3BetaPackStatusInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetArV3BetaPackStatusResult>> {
  return request<GetArV3BetaPackStatusResult>(OPERATIONS.getArV3BetaPackStatus, input, options);
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
 * Get Run Norm Verification
 *
 * `GET /runs/{run_id}/norm-verification`.
 */
export function getRunNormVerification(
  input: GetRunNormVerificationInput,
  options?: RequestOptions,
): Promise<ApiResponse<GetRunNormVerificationResult>> {
  return request<GetRunNormVerificationResult>(OPERATIONS.getRunNormVerification, input, options);
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
 * Start Ar V3 Beta Group
 *
 * `POST /ar-v3-beta/groups` - a write; carries a required Idempotency-Key.
 */
export function startArV3BetaGroup(
  input: StartArV3BetaGroupInput,
  options?: RequestOptions,
): Promise<ApiResponse<StartArV3BetaGroupResult>> {
  return request<StartArV3BetaGroupResult>(OPERATIONS.startArV3BetaGroup, input, options);
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
  appendDecision,
  approveRegistration,
  approveSheetPairing,
  archiveAnalysisPreset,
  archiveExecutorConnection,
  archiveUser,
  cancelRun,
  carryOverDecision,
  changePassword,
  claimExecutorTask,
  classifyDocumentVersion,
  compareDocumentVersions,
  correctVersionClassification,
  createAnalysisPreset,
  createAssignment,
  createExecutorConnection,
  createProject,
  decideOptimisationProposal,
  exportOptimisationProposalsCsv,
  exportRunCsv,
  exportRunXlsx,
  extendExecutorTaskClaim,
  failExecutorTask,
  generateComparisonSummary,
  generateExecutorSshKey,
  getArV3BetaGroup,
  getArV3BetaGroupReview,
  getArV3BetaPackStatus,
  getAssignment,
  getDashboardSummary,
  getDocumentVersion,
  getEffectiveVendorLists,
  getExecutorConnection,
  getExecutorTaskImage,
  getFinding,
  getMe,
  getNormDocument,
  getProductVersion,
  getRunNormReferences,
  getRunNormVerification,
  getRunStatus,
  getSectionSpecification,
  getSpecificationPrices,
  getUser,
  getVersionBlocks,
  getVersionSectionReview,
  issueRunnerToken,
  issueToken,
  listAnalysisPresets,
  listAnalysisProfiles,
  listAssignments,
  listDecisionHistory,
  listDecisions,
  listDocuments,
  listExecutionJournal,
  listExecutionQueue,
  listExecutorConnections,
  listExecutorRoutes,
  listNormDocuments,
  listNormParagraphs,
  listNormSnapshotEvents,
  listNormSnapshots,
  listOptimisationPasses,
  listOptimisationProposals,
  listPriceListPositions,
  listPriceListRevisions,
  listProjects,
  listProposalDecisions,
  listRegistrations,
  listReleases,
  listRunFindings,
  listRuns,
  listUsers,
  listVersionPortalBlocks,
  listVersions,
  listWorkers,
  markReleaseNotesRead,
  purgeUser,
  readRegistrationStatus,
  reauditRun,
  rejectRegistration,
  requestExecutorProbe,
  resetUserPassword,
  restoreUser,
  reviseAnalysisPreset,
  reviseExecutorConnection,
  revokeRunnerToken,
  searchNorms,
  setCurrentNormSnapshot,
  setExecutionPaused,
  setExecutorRoute,
  setExecutorSecret,
  setGlobalVendorList,
  setJobPriority,
  setProjectVendorList,
  setWorkerIntake,
  startArV3BetaGroup,
  startOptimisationPass,
  startRun,
  streamDocumentVersionContent,
  streamNormDocumentContent,
  streamVersionPortalBlockCrop,
  submitExecutorTaskAnswer,
  submitRegistration,
  transitionAssignment,
  updateMyProfile,
  updateUser,
  uploadDocument,
  uploadDocumentVersion,
  uploadPriceList,
  withdrawSheetPairing,
} as const;
