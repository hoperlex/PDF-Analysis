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
 *   AuditManager PC-01 API 1.0.0-draft.1 (OpenAPI 3.1.0)
 *   sha256 633a58a53baf6652625b59d3db9438ae01e8c4ac8da788160882f031123f2e37
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
  ArchiveUserInput,
  ArchiveUserResult,
  ChangePasswordInput,
  ChangePasswordResult,
  CreateProjectInput,
  CreateProjectResult,
  ExportRunCsvInput,
  ExportRunCsvResult,
  GetDashboardSummaryInput,
  GetDashboardSummaryResult,
  GetDocumentVersionInput,
  GetDocumentVersionResult,
  GetFindingInput,
  GetFindingResult,
  GetMeInput,
  GetMeResult,
  GetRunStatusInput,
  GetRunStatusResult,
  GetUserInput,
  GetUserResult,
  GetVersionBlocksInput,
  GetVersionBlocksResult,
  IssueTokenInput,
  IssueTokenResult,
  ListDecisionHistoryInput,
  ListDecisionHistoryResult,
  ListDecisionsInput,
  ListDecisionsResult,
  ListDocumentsInput,
  ListDocumentsResult,
  ListProjectsInput,
  ListProjectsResult,
  ListRegistrationsInput,
  ListRegistrationsResult,
  ListRunFindingsInput,
  ListRunFindingsResult,
  ListRunsInput,
  ListRunsResult,
  ListUsersInput,
  ListUsersResult,
  ListVersionsInput,
  ListVersionsResult,
  PurgeUserInput,
  PurgeUserResult,
  ReadRegistrationStatusInput,
  ReadRegistrationStatusResult,
  RejectRegistrationInput,
  RejectRegistrationResult,
  ResetUserPasswordInput,
  ResetUserPasswordResult,
  RestoreUserInput,
  RestoreUserResult,
  StartRunInput,
  StartRunResult,
  StreamDocumentVersionContentInput,
  StreamDocumentVersionContentResult,
  SubmitRegistrationInput,
  SubmitRegistrationResult,
  UpdateMyProfileInput,
  UpdateMyProfileResult,
  UpdateUserInput,
  UpdateUserResult,
  UploadDocumentInput,
  UploadDocumentResult,
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
 * Upload one PDF and publish an immutable document version.
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
 * The whole client as one object, for a consumer that would rather inject it than
 * import each function. The named exports above are the ordinary way in.
 */
export const apiClient = {
  appendDecision,
  approveRegistration,
  archiveUser,
  changePassword,
  createProject,
  exportRunCsv,
  getDashboardSummary,
  getDocumentVersion,
  getFinding,
  getMe,
  getRunStatus,
  getUser,
  getVersionBlocks,
  issueToken,
  listDecisionHistory,
  listDecisions,
  listDocuments,
  listProjects,
  listRegistrations,
  listRunFindings,
  listRuns,
  listUsers,
  listVersions,
  purgeUser,
  readRegistrationStatus,
  rejectRegistration,
  resetUserPassword,
  restoreUser,
  startRun,
  streamDocumentVersionContent,
  submitRegistration,
  updateMyProfile,
  updateUser,
  uploadDocument,
} as const;
