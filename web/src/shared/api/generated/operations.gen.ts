/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * One typed input and result per operation, plus the runtime descriptor table the
 * transport executes.
 *
 * Produced by `npm --prefix web run api:generate`
 * (web/scripts/generate-api-client.mjs, generator 1.0.0)
 * from contracts/api/v1/openapi.json
 *   AuditManager PC-01 API 1.0.0 (OpenAPI 3.1.0)
 *   sha256 53d289eceaa4e1b77b1bf86c4bdca0c0be693f81669ded299a02c5122685b9ee
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

import type {
  Account,
  AccountPage,
  AnalysisProfileList,
  AppendDecisionRequest,
  AppendDecisionResponse,
  ApproveRegistrationRequest,
  Assignment,
  AssignmentDetail,
  AssignmentPage,
  AssignmentStatus,
  AssignmentUid,
  CarryOverDecisionRequest,
  CarryOverDecisionResponse,
  ChangePasswordRequest,
  ClaimExecutorTaskRequest,
  ClaimedExecutorTask,
  ClassifyDocumentVersionRequest,
  CorrectVersionClassificationRequest,
  CorrelationId,
  CreateAssignmentRequest,
  CreateExecutorConnectionRequest,
  CreateProjectRequest,
  Cursor,
  DashboardSummary,
  DecideOptimisationProposalRequest,
  DecisionEventPage,
  DecisionRecordPage,
  DocumentUid,
  DocumentVersion,
  DocumentVersionPage,
  EffectiveVendorLists,
  ExecutionDispatchStatus,
  ExecutionJournalPage,
  ExecutionQueueItem,
  ExecutionQueuePage,
  ExecutionWorker,
  ExecutionWorkerPage,
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorConnectionId,
  ExecutorConnectionList,
  ExecutorProbe,
  ExecutorRevision,
  ExecutorRoute,
  ExecutorRouteList,
  ExecutorRunnerTokenId,
  ExecutorSecretMetadata,
  ExecutorSshKey,
  ExecutorTaskAck,
  ExecutorTaskId,
  ExtendedExecutorTaskClaim,
  FailExecutorTaskRequest,
  FindingCategory,
  FindingDetail,
  FindingPage,
  FindingUid,
  IdempotencyKey,
  IssueRunnerTokenRequest,
  IssueTokenRequest,
  IssueTokenResponse,
  IssuedRunnerToken,
  JobId,
  MarkReleaseNotesReadRequest,
  NormCatalogueEntryPage,
  NormCurrentSnapshot,
  NormDocument,
  NormDocumentId,
  NormParagraphPage,
  NormSearchPage,
  NormSnapshotEventPage,
  NormSnapshotPage,
  NormVerificationReport,
  NormsSnapshotId,
  OptimisationPass,
  OptimisationPassId,
  OptimisationPassList,
  OptimisationProposalId,
  OptimisationProposalPage,
  PortalBlockId,
  PortalBlockPage,
  PriceListId,
  PriceListPositionPage,
  PriceListRevision,
  PriceListRevisionList,
  ProductVersion,
  Project,
  ProjectPage,
  ProjectSection,
  ProjectUid,
  ProposalDecisionList,
  ProposalDecisionResult,
  ProposalDecisionState,
  RegistrationRequest,
  RegistrationRequestId,
  RegistrationRequestPage,
  RegistrationStatus,
  RegistrationStatusResponse,
  RejectRegistrationRequest,
  ReleaseList,
  ResetUserPasswordRequest,
  ReviseExecutorConnectionRequest,
  RunId,
  RunNormReferences,
  RunStatus,
  RunStatusPage,
  RunnerTokenMetadata,
  SectionReview,
  SectionSpecification,
  SectionVendorList,
  SetCurrentNormSnapshotRequest,
  SetExecutionPausedRequest,
  SetExecutorRouteRequest,
  SetExecutorSecretRequest,
  SetGlobalVendorListRequest,
  SetJobPriorityRequest,
  SetProjectVendorListRequest,
  SetWorkerIntakeRequest,
  SpecificationPrices,
  StartRunRequest,
  SubmitExecutorTaskAnswerRequest,
  SubmitRegistrationRequest,
  TransitionAssignmentRequest,
  UpdateMyProfileRequest,
  UpdateUserRequest,
  UploadDocumentRequest,
  UploadDocumentVersionRequest,
  UploadPriceListRequest,
  UserUid,
  VendorListRevision,
  Verdict,
  VersionBlockIndex,
  VersionClassification,
  VersionComparison,
  VersionUid,
  WorkerId,
} from './types.gen';

/** Every operationId in the contract, sorted. */
export const OPERATION_IDS = [
  'appendDecision',
  'approveRegistration',
  'archiveExecutorConnection',
  'archiveUser',
  'cancelRun',
  'carryOverDecision',
  'changePassword',
  'claimExecutorTask',
  'classifyDocumentVersion',
  'compareDocumentVersions',
  'correctVersionClassification',
  'createAssignment',
  'createExecutorConnection',
  'createProject',
  'decideOptimisationProposal',
  'exportOptimisationProposalsCsv',
  'exportRunCsv',
  'exportRunXlsx',
  'extendExecutorTaskClaim',
  'failExecutorTask',
  'generateExecutorSshKey',
  'getAssignment',
  'getDashboardSummary',
  'getDocumentVersion',
  'getEffectiveVendorLists',
  'getExecutorConnection',
  'getFinding',
  'getMe',
  'getNormDocument',
  'getProductVersion',
  'getRunNormReferences',
  'getRunNormVerification',
  'getRunStatus',
  'getSectionSpecification',
  'getSpecificationPrices',
  'getUser',
  'getVersionBlocks',
  'getVersionSectionReview',
  'issueRunnerToken',
  'issueToken',
  'listAnalysisProfiles',
  'listAssignments',
  'listDecisionHistory',
  'listDecisions',
  'listDocuments',
  'listExecutionJournal',
  'listExecutionQueue',
  'listExecutorConnections',
  'listExecutorRoutes',
  'listNormDocuments',
  'listNormParagraphs',
  'listNormSnapshotEvents',
  'listNormSnapshots',
  'listOptimisationPasses',
  'listOptimisationProposals',
  'listPriceListPositions',
  'listPriceListRevisions',
  'listProjects',
  'listProposalDecisions',
  'listRegistrations',
  'listReleases',
  'listRunFindings',
  'listRuns',
  'listUsers',
  'listVersionPortalBlocks',
  'listVersions',
  'listWorkers',
  'markReleaseNotesRead',
  'purgeUser',
  'readRegistrationStatus',
  'reauditRun',
  'rejectRegistration',
  'requestExecutorProbe',
  'resetUserPassword',
  'restoreUser',
  'reviseExecutorConnection',
  'revokeRunnerToken',
  'searchNorms',
  'setCurrentNormSnapshot',
  'setExecutionPaused',
  'setExecutorRoute',
  'setExecutorSecret',
  'setGlobalVendorList',
  'setJobPriority',
  'setProjectVendorList',
  'setWorkerIntake',
  'startOptimisationPass',
  'startRun',
  'streamDocumentVersionContent',
  'streamNormDocumentContent',
  'streamVersionPortalBlockCrop',
  'submitExecutorTaskAnswer',
  'submitRegistration',
  'transitionAssignment',
  'updateMyProfile',
  'updateUser',
  'uploadDocument',
  'uploadDocumentVersion',
  'uploadPriceList',
] as const;

/** The closed set of operations this client can perform. */
export type OperationId = (typeof OPERATION_IDS)[number];

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

/** Claim Executor Task */
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
// compareDocumentVersions - GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison
// ------------------------------------------------------------------------------------

/**
 * Compare Document Versions
 *
 * Compare two versions of one document set: the path names the older (source) version and `target_version_uid` the newer one. Both must be published versions of the named document in the named project with the same confirmed section and, with `mode=version` (the default), the same explicit project stage; with `mode=stage` the source must be classified `P` and the target `R` (design to working documentation of one set). Each needs a published run (the newest one, or the one `source_run_id` / `target_run_id` names). A path that names no such version is `404`; otherwise a pair the rule does not admit is `outcome: refused` with one `refusal.reason`, never relabelled. The answer carries proposed sheet pairs with their evidence, one page of raw line differences (`diff_offset`, `diff_limit`, `next_offset`) and proposed matches between the two runs' findings. Every pairing and match is a proposal; nothing is written. Any one role, `role:admin|expert`.
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
// decideOptimisationProposal - POST /optimisation-proposals/{optimisation_proposal_id}/decisions
// ------------------------------------------------------------------------------------

/**
 * Decide Optimisation Proposal
 *
 * Append an expert's decision on a proposal: `accept`, `reject` or `revise` (the comment is required for `revise`, at most 2000 characters). Decisions are only appended, never changed; the latest one is current, and any number may follow. `expert` is required (`admin` alone is `permission_denied`); an unknown proposal is `404`. An exact repeat of the `Idempotency-Key` answers the stored decision; the same key with another verdict, comment, proposal or caller is `409 idempotency_key_reuse`. The decision belongs to the proposal alone: no finding is read or changed.
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
// exportOptimisationProposalsCsv - GET /optimisation-passes/{optimisation_pass_id}/export.csv
// ------------------------------------------------------------------------------------

/**
 * Export Optimisation Proposals Csv
 *
 * Every proposal of the pass as a CSV file, one row each in ordinal order: the pass, the specification row's provenance, both positions, both exact unit prices, the saving (an empty cell when it is absent, never `0`) and the current decision. UTF-8 with a byte-order mark, CRLF line endings, RFC 4180 quoting; every cell that a spreadsheet would read as a formula is prefixed with an apostrophe. Computed on request from the stored rows; separate from the findings' CSV. An unknown pass is `404`. Any one role, `role:admin|expert`.
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
// exportRunCsv - GET /runs/{run_id}/export.csv
// ------------------------------------------------------------------------------------

/**
 * Download the CSV for one run.
 *
 * Synchronous. Nothing is created, so there is no export resource, no export identity and nothing to poll. Repeating the request returns byte-identical bytes.
 *
 * The discriminator is the frozen `terminal_semantics.publishes_result` flag, not a hand-written state list (`OD-11`). A run whose terminal declares `publishes_result: true` - `published` or `partial` - is exported, with the degraded state carried explicitly in the `run_state` column rather than as a silent empty file. Every other state is refused with `state_transition_not_allowed`: a non-terminal run, and the terminal `failed`. `cancelled` is likewise not exportable and is unreachable in PC-01. `partial_result_not_publishable` is never emitted by this surface.
 *
 * Bytes: UTF-8 with a byte-order mark, comma delimiter, CRLF line ending, RFC 4180 quoting. The column list and its order are frozen in `docs/program/P02_SEAMS.md` section 6.
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
 * The workbook is the W57b layout (`docs/program/dispatch/W57-PLAN.md` section B3.5): «Сводка» with the run's identity and the counts by severity (decided, else proposed) and by category, and «Замечания» with one row per finding -- № | Лист/стр. | Категория | Замечание | Рекомендация | Серьёзность (решение эксперта) | Серьёзность (предложение модели) | Норма (документ, пункт) | Цитата нормы | Решение эксперта | Комментарий -- and a «также найдено» row per merged member. Standard-library writer, stored ZIP parts in a fixed order with fixed timestamps, inline strings, no formula; XML-forbidden characters become U+FFFD.
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

/** Extend Executor Task Claim */
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

/** Fail Executor Task */
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
// getDashboardSummary - GET /dashboard
// ------------------------------------------------------------------------------------

/**
 * One aggregate read across the whole deployment: all four dashboard panels.
 *
 * Documents per project, findings by verdict, run activity and spend, and the per-section breakdown -- computed server-side over the whole deployment, never walked client-side (`R-44`). Takes no parameter: it is not a filtered query over the data three narrower operations already answer (`listProjects`, `listDecisions`, `listRuns`), it is the fixed shape of the deployment right now. Absent is not empty throughout: every `Verdict` and `RunState` is present even at zero, every one of the fourteen frozen sections is present even with no documents, and the unclassified documents are their own row.
 */
export type GetDashboardSummaryInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getDashboardSummary` (`application/json`, HTTP 200). */
export type GetDashboardSummaryResult = DashboardSummary;

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
 * All fifteen sections' vendor lists as they apply to the project, in section order. For each: `source` `project` (the project's own latest revision, mode `list`), `global` (the administrator's latest) or `none`; the `effective` revision; and the latest revision of each scope. An unknown project is `404`. Any one role, `role:admin|expert`.
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
 * One norm document of a snapshot, with its attribution (NORM-Q04) and whether its source PDF is available through a confirmed custody binding. Roles: any one role (`role:admin|expert`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
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
// getRunNormReferences - GET /runs/{run_id}/norm-references
// ------------------------------------------------------------------------------------

/**
 * Get Run Norm References
 *
 * «Нормативные ссылки»: the normative documents (СП, ГОСТ, СНиП, СанПиН, ВСН, federal laws and government acts) cited in the run's saved text, each resolved against the norms snapshot the run pinned as `in_corpus`, `newer_edition`, `older_edition_only` (the corpus holds only an earlier edition than the one cited), `not_in_corpus` or `not_recognised`, with the pages each occurs on and the corpus document it points at. Computed per request by the same resolver the W57b rule uses; publishes no finding, proposes no severity and calls no model. A precondition that does not hold is `state` (`snapshot_not_pinned`, `text_unavailable`, `too_many_citations`), never an empty list; the corpus documents whose designation the parser cannot read are listed as `unrecognised`; pages without a text layer are `unread_pages`. An unknown run is `404`. Any one role, `role:admin|expert`.
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
// getRunNormVerification - GET /runs/{run_id}/norm-verification
// ------------------------------------------------------------------------------------

/**
 * Get Run Norm Verification
 *
 * Read a verified v3 normative report for a run. R-80: any one active expert or admin role; an empty role set is refused. A v1/v2 run answers not_found. Until the CITE verified reader is implemented, this endpoint answers typed 503 dependency_unavailable and exposes no unverified citation data (D-151).
 */
export type GetRunNormVerificationInput = {
  /** Path parameters, substituted into `/runs/{run_id}/norm-verification`. */
  path: {
    run_id: RunId;
  };
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `getRunNormVerification` (`application/json`, HTTP 200). */
export type GetRunNormVerificationResult = NormVerificationReport;

// ------------------------------------------------------------------------------------
// getRunStatus - GET /runs/{run_id}
// ------------------------------------------------------------------------------------

/**
 * Read run state and per-stage state.
 *
 * The polling target. `state` is the contract run state; `stages` carries one entry per stage the run scheduled, with the `StageResult` status vocabulary. A client stops polling on any terminal state.
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
 * «Оптимизация разделов»: the Form-7 rows of every project whose document set's current version an expert confirmed in the section, each row priced from its own project's current price list as `matched`, `ambiguous` or `unmatched` with its reason (or `price_list_missing` when the project has none). The section code is a filter, not an identity: every row carries its project, document set, version, page, sheet and line span, rows are never merged across projects, and totals exist per project and per currency only -- there is no section total. A current version nobody classified is listed in `excluded`; one confirmed in another section never appears. `project_uid` narrows the answer to one project (an unknown one is `404`); `q` keeps the rows whose own text contains it and never changes a total; rows are paged (`offset`, `limit`, `next_offset`). A set without a published run or a saved text layer is its own `state`. Over a bound (projects scanned, member sets read, rows held) the answer is `200` with `state: section_too_large`, the bound in `limit_reason`, the membership listed and no rows; narrow to one project. A section code outside the fifteen is `404`. Nothing is written. Any one role, `role:admin|expert`.
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
 * «Спецификация и цены»: the specification rows of the document set's current version, read deterministically from its newest published run's saved text layer, each matched to the project's current price-list revision as `matched`, `ambiguous` or `unmatched` with its reason (code or mark first, then the normalised name, in the same unit; never a fuzzy guess). The version must be classified as section `AR`. A precondition that does not hold is `state` (`version_unclassified`, `section_not_ar`, `price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large`) with the facts read so far; a path naming no such set is `404`. A price and an amount appear only on a matched row with a numeric quantity; totals are per currency over those rows only, with every other row counted by its reason. Rows are paged (`offset`, `limit`, `next_offset`); counts and totals cover every row. Nothing is written. Any one role, `role:admin|expert`.
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
// getVersionSectionReview - GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/section-review
// ------------------------------------------------------------------------------------

/**
 * Get Version Section Review
 *
 * The fifteen section choices for one version, each with the suggestion evidence its file name and recognised text carry (or `null`) and whether a text profile is registered for it (`executable`), plus the persisted classification or `null`, and the classification's history (`revisions`, oldest first: the original confirmation, then each correction with its expert, time and reason). Display input only: nothing here confirms a section or starts a run. Any one role, `role:admin|expert`.
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
// listAnalysisProfiles - GET /analysis/profiles
// ------------------------------------------------------------------------------------

/**
 * List the analysis profile of every section.
 *
 * The analysis profiles the server routes runs through: all fifteen sections in the project-structure order, each with its registered text profile -- identities, version, status (`builtin`, `draft` or `reviewed`), prompt-bundle and profile hashes and the legacy source of a ported package -- or `null` when no profile is registered, which run start refuses. Read-only: no operation edits a profile or its status. Any one role, `role:admin|expert`.
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
 * Any one role. An administrator reads every assignment (`mine=true` narrows to the ones currently given to them); an expert reads only the assignments currently given to them, whatever `mine` says. `status` and `project_uid` narrow the list; newest first, ordered by `(created_at, assignment_uid)`.
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
 * `category` and `verdict` filter on the **finding**, exactly as they do on `listRunFindings`: the category of the finding the event was recorded against, and the verdict that now stands for it. Neither filters on the event. There is no parent identity in the path, so an empty journal is an empty page and never `not_found`.
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
 */
export type ListDocumentsInput = {
  /** Path parameters, substituted into `/projects/{project_uid}/documents`. */
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
// listExecutorRoutes - GET /executor-routes
// ------------------------------------------------------------------------------------

/** List Executor Routes */
export type ListExecutorRoutesInput = {
  /**
   * Optional `X-Correlation-Id`. The edge assigns one when the caller does not.
   */
  correlationId?: CorrelationId;
};

/** Success body of `listExecutorRoutes` (`application/json`, HTTP 200). */
export type ListExecutorRoutesResult = ExecutorRouteList;

// ------------------------------------------------------------------------------------
// listNormDocuments - GET /norm-documents
// ------------------------------------------------------------------------------------

/**
 * List Norm Documents
 *
 * Every document of the current norms snapshot (R-112) as a catalogue, in designation order (natural, case- and homoglyph-folded), then title, then identity. `designation` and `title` are derived for display from the document's stored file name -- dates dotted, designation numbers dotted, a cut edition note closed or shown as `(ред. …)` -- and never alter or replace the stored rows; a name no rule can derive is shown as `getNormDocument` shows it, and `title` is null when the name carries nothing after the designation. `q` (1-200 characters) keeps documents whose designation or title contains it from the start of a word, folded the same way, and a `q` ending in a digit ends a number there; `kind` (1-100 characters) keeps documents whose stored kind equals it, and `kinds` lists every kind of the snapshot with its count. A `q` or `kind` holding a control character or nothing to filter by is `422 validation_failed` (`field` `q` or `kind`, `constraint: format`). The cursor is opaque and bound to `q`, `kind` and the snapshot; another listing refuses it. `total` counts the documents the filters keep. With no current snapshot the answer is `422 required_norm_unavailable` with `reference_kind: norms_snapshot`, never an empty page. Every row carries its `source_attribution` (NORM-Q04). Roles: any one role (`role:admin|expert`, R-80); an account whose role set is empty is refused `403`. Added by W57B-NORMS-CATALOGUE-XLSX-01.
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
 * The document's canonical paragraphs in `ordinal` order, each with `page_label` (the 1-based PDF page), `block_ref`, clause and `text_reliability`; unreliable paragraphs are marked, never hidden. Roles: any one role (`role:admin|expert`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
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
 * Every loaded norms snapshot with its content key, counts, `bge-m3-dense-v1` build state, whether it qualifies to be current (a complete build and a confirmed source binding for every document's PDF) and whether it is current. Roles: any one role (`role:admin|expert`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
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
 * The project's optimisation passes, newest first (at most `limit`, 100 by default), each with its counts by decision; `document_uid` narrows to one document set of the project. An unknown project or a set of another project is `404`. Any one role, `role:admin|expert`.
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
 * One page of a pass's proposals in ordinal order (`offset`, `limit`, `next_offset`), each with its provenance in the specification, the matched and the proposed position, both exact unit prices, the saving where it is computable and its current decision. `decision` narrows to the proposals in one decision state (`pending` for none yet); the pass's `decision_counts` always count every proposal. An unknown pass is `404`. Any one role, `role:admin|expert`.
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
// listPriceListPositions - GET /price-lists/{price_list_id}/positions
// ------------------------------------------------------------------------------------

/**
 * List Price List Positions
 *
 * One page of a price-list revision's positions in source-row order (`offset`, `limit`, `next_offset`), with the revision and its parse report. Each unit price is its exact decimal text. An unknown revision is `404`. Any one role, `role:admin|expert`.
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
 * Every price-list revision of the project, newest first, the first flagged `is_current`. An unknown project is `404`. Any one role, `role:admin|expert`.
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
// listProposalDecisions - GET /optimisation-proposals/{optimisation_proposal_id}/decisions
// ------------------------------------------------------------------------------------

/**
 * List Proposal Decisions
 *
 * The proposal's whole append-only decision history, oldest first, each with its verdict, comment, author and time; the last one is current. An unknown proposal is `404`. Any one role, `role:admin|expert`.
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
 * A re-audit runs the same version on the current configuration (R-82), so it faces today's analysis input budget, not the source run's: over it, the answer is `422 analysis_input_budget_exceeded` with `details.character_count` and `details.budget_characters`, and no run exists (R-118). A v3 re-audit may refuse absent verified retrieval set with 422 required_norm_unavailable and reference_kind norm_retrieval_set. `W59-SECTION-SEAL-01`: the new run is routed from the version's persisted classification exactly as `startRun` is, never from the source run's profile; an unclassified version is `422 version_classification_required` and a section with no registered text profile is `422 section_profile_unavailable`.
 */
export type ReauditRunInput = {
  /** Path parameters, substituted into `/runs/{run_id}/reaudit`. */
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

/** Success body of `reauditRun` (`application/json`, HTTP 202). */
export type ReauditRunResult = RunStatus;

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
// searchNorms - GET /norms/search
// ------------------------------------------------------------------------------------

/**
 * Search Norms
 *
 * Text search over the canonical paragraphs of the current norms snapshot (R-112, G-5). `q` is 1-200 characters: an optional designation (`ГОСТ 10140`, `СП 54` -- matched on whole leading tokens, so `СП 54` never finds `СП 542`), an optional clause (`п. 7.1.4`, a dotted-segment prefix) and words (Russian morphology, ranked by `ts_rank_cd`). Unreliable paragraphs never appear. With no current snapshot, or an explicit `norms_snapshot_id` that has never been current, the answer is `422 required_norm_unavailable` with `reference_kind: norms_snapshot` -- never an empty page. A query the statement timeout cancels is `422 validation_failed` with `constraint: norms_search_too_broad`, never an empty or partial page. The cursor is opaque and bound to the query and snapshot; another query or snapshot refuses it, and the result window is capped at 1 000. Every hit carries its `source_attribution` (NORM-Q04); the corpus is internal (D-4.1). Roles: any one role (`role:admin|expert`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
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
// setExecutorRoute - PUT /executor-routes
// ------------------------------------------------------------------------------------

/** Set Executor Route */
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
// startOptimisationPass - POST /projects/{project_uid}/documents/{document_uid}/optimisation-passes
// ------------------------------------------------------------------------------------

/**
 * Start Optimisation Pass
 *
 * Start the optimisation pass of the document set's current AR version. The pass pins the version, its newest published run and that run's saved text layer, the project's current price-list revision and the effective AR vendor list (the project's own, else the administrator's), reads the specification, matches it against the price list and stores the deterministic proposals `cheaper_analog`: for a row matched to exactly one position, another position of the same revision in the same unit and currency, with a lower unit price, from a vendor on the list, of the same kind of product (at most three per row). The saving is `(current − proposed) × quantity` and is absent when the row's quantity is not a plain number. `expert` is required (`admin` alone is `permission_denied`). A precondition that is not met is `409 conflict` with `conflict_reason` `version_unclassified`, `section_not_ar`, `price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large` or `vendor_list_missing` and nothing is written, not even the key; an unknown project or a set of another project is `404`. An exact repeat of the `Idempotency-Key` answers the stored pass, the same key for another set or caller is `409 idempotency_key_reuse`, and a new key over exactly the same inputs answers the pass already stored instead of writing a second one.
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
 * A version whose recorded text is larger than the analysis input budget is refused up front with `422 analysis_input_budget_exceeded` and no run exists (R-118). A version published before the portal-bundle upload has no recorded count and is not refused by this rule.
 *
 * `W59-SECTION-SEAL-01`: the run's analysis profile is routed from the version's persisted classification through the section-keyed profile registry -- never from a file name, a suggestion or the document's legacy `section`, and never by an AR fallback. A version with no classification is refused with `422 version_classification_required`; a confirmed section with no registered text profile is refused with `422 section_profile_unavailable` (`BETA-CONTRACT-SEAL-01`, `D-179`: both used to be `required_norm_unavailable` told apart by `details.reference_kind`). Neither carries details, and both refusals precede the key's claim, so nothing is written. An existing run keeps the profile it pinned.
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
 * The document's source PDF, streamed by the server in chunks; never a redirect or a storage link. One `Range` is honoured with `206` and `Content-Range`; an unsatisfiable range is `422`. Served only through a confirmed custody binding; a document without one is `422 required_norm_unavailable` with `reference_kind: norm_source`. A full read verifies the bytes while streaming and stops short on a mismatch (R-115). Roles: any one role (`role:admin|expert`, R-80); an account whose role set is empty is refused `403`. Sealed by W55A-SEAL-01 as a stub answering `503 dependency_unavailable` until W55A-SEARCH-01.
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

/** Submit Executor Task Answer */
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
 * Reachable without a credential: `security` is the empty requirement, as on `issueToken`. Records an application an administrator then approves or rejects; no mail is sent (R-56). The e-mail, the names and the password are validated first, then: an active account holding the login is `conflict` with `conflict_reason: login_taken`, a pending request for it `request_pending`, and 100 pending requests in all `queue_full`. That the first two tell a submitter a login is known is an accepted, registered limitation. Neither `401` nor `403` is declared: there is no credential to refuse and no subject to deny. The edge in front of this surface throttles it per client and answers `rate_limited` (`429`) itself, before the operation is reached; like the edge's own body-size refusal, that answer is not a response of the operation and is not declared here.
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
// uploadDocument - POST /projects/{project_uid}/documents
// ------------------------------------------------------------------------------------

/**
 * Upload one portal bundle and publish an immutable document version.
 *
 * The whole ingest path. The body is one portal bundle: a ZIP, recognised by its magic bytes whatever label the browser sends, holding exactly one `<stem>.pdf`, one `<stem>_blocks.json` and one `<stem>_results.md`, and optionally one `<stem>_results.html` (kept as a digest only: never stored, served or rendered) and one `<stem>_stamp_audit.json` (stored, and not used in analysis). All members share one stem. Anything else in the archive is refused, and so is any archive that is not what it claims to be (names that escape, links, encrypted members, a compression ratio above the bound, sizes beyond the bounds).
 *
 * A bare PDF is refused with `validation_failed` and the constraint `portal_bundle_required`; the message says how to obtain the bundle. The PDF must be unencrypted and at most 500 pages, and the whole upload at most 250 MiB; every page must carry an embedded text layer or at least one portal block. Every refusal is `validation_failed` (or `storage_integrity_error`) with a `constraint` detail, and the registered values are in the domain error catalog (`error-codes.json`, `validation_failed`).
 *
 * OCR is always marked: the portal's recognised text is kept as its own artifact with quality flags and is never merged into the PDF's text layer (R-116). The portal's descriptions of images are shown, marked, and never used in analysis (R-117). The analysis is built for AR (architectural solutions) text and is applied to any uploaded document; a stated `section` is stored and counted but neither selects nor refuses the analysis (D-110).
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
// Runtime descriptors
// ------------------------------------------------------------------------------------

/**
 * What the transport needs at runtime to execute an operation. Consumers read this
 * table; they never build a URL, a method or a header name by hand.
 */
export const OPERATIONS = {
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
  getDashboardSummary: {
    operationId: 'getDashboardSummary',
    method: 'GET',
    path: '/dashboard',
    pathParams: [],
    queryParams: [],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 500, 503],
    tags: ['dashboard'],
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
  getRunNormVerification: {
    operationId: 'getRunNormVerification',
    method: 'GET',
    path: '/runs/{run_id}/norm-verification',
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
  listDecisions: {
    operationId: 'listDecisions',
    method: 'GET',
    path: '/decisions',
    pathParams: [],
    queryParams: ['category', 'cursor', 'limit', 'verdict'],
    headerParams: [],
    requiresIdempotencyKey: false,
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [200],
    errorStatuses: [401, 403, 422, 500, 503],
    tags: ['decisions'],
  },
  listDocuments: {
    operationId: 'listDocuments',
    method: 'GET',
    path: '/projects/{project_uid}/documents',
    pathParams: ['project_uid'],
    queryParams: ['cursor', 'limit'],
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
    queryParams: ['cursor', 'limit'],
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
    requestMediaType: null,
    responseMediaType: 'application/json',
    successStatuses: [202],
    errorStatuses: [401, 403, 404, 409, 422, 500, 503],
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
} as const;
