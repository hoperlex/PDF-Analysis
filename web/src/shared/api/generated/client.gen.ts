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
 *   sha256 37425dffc050db7819710cfd778ec41483a870f2f936461d7fabd5855f6041a9
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

import type { ApiResponse, RequestOptions } from '../transport';
import { request } from '../transport';
import type {
  AppendDecisionInput,
  AppendDecisionResult,
  CreateProjectInput,
  CreateProjectResult,
  ExportRunCsvInput,
  ExportRunCsvResult,
  GetDocumentVersionInput,
  GetDocumentVersionResult,
  GetFindingInput,
  GetFindingResult,
  GetRunStatusInput,
  GetRunStatusResult,
  IssueTokenInput,
  IssueTokenResult,
  ListDecisionHistoryInput,
  ListDecisionHistoryResult,
  ListDocumentsInput,
  ListDocumentsResult,
  ListProjectsInput,
  ListProjectsResult,
  ListRunFindingsInput,
  ListRunFindingsResult,
  ListRunsInput,
  ListRunsResult,
  ListVersionsInput,
  ListVersionsResult,
  StartRunInput,
  StartRunResult,
  StreamDocumentVersionContentInput,
  StreamDocumentVersionContentResult,
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
  createProject,
  exportRunCsv,
  getDocumentVersion,
  getFinding,
  getRunStatus,
  issueToken,
  listDecisionHistory,
  listDocuments,
  listProjects,
  listRunFindings,
  listRuns,
  listVersions,
  startRun,
  streamDocumentVersionContent,
  uploadDocument,
} as const;
