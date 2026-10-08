/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * One typed input and result per operation, plus the runtime descriptor table the
 * transport executes.
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

import type {
  Account,
  AccountPage,
  AppendDecisionRequest,
  AppendDecisionResponse,
  ApproveRegistrationRequest,
  ChangePasswordRequest,
  CorrelationId,
  CreateProjectRequest,
  Cursor,
  DashboardSummary,
  DecisionEventPage,
  DecisionRecordPage,
  DocumentUid,
  DocumentVersion,
  DocumentVersionPage,
  FindingCategory,
  FindingDetail,
  FindingPage,
  FindingUid,
  IdempotencyKey,
  IssueTokenRequest,
  IssueTokenResponse,
  Project,
  ProjectPage,
  ProjectUid,
  RegistrationRequest,
  RegistrationRequestId,
  RegistrationRequestPage,
  RegistrationStatus,
  RegistrationStatusResponse,
  RejectRegistrationRequest,
  ResetUserPasswordRequest,
  RunId,
  RunStatus,
  RunStatusPage,
  StartRunRequest,
  SubmitRegistrationRequest,
  UpdateMyProfileRequest,
  UpdateUserRequest,
  UploadDocumentRequest,
  UserUid,
  Verdict,
  VersionBlockIndex,
  VersionUid,
} from './types.gen';

/** Every operationId in the contract, sorted. */
export const OPERATION_IDS = [
  'appendDecision',
  'approveRegistration',
  'archiveUser',
  'changePassword',
  'createProject',
  'exportRunCsv',
  'getDashboardSummary',
  'getDocumentVersion',
  'getFinding',
  'getMe',
  'getRunStatus',
  'getUser',
  'getVersionBlocks',
  'issueToken',
  'listDecisionHistory',
  'listDecisions',
  'listDocuments',
  'listProjects',
  'listRegistrations',
  'listRunFindings',
  'listRuns',
  'listUsers',
  'listVersions',
  'purgeUser',
  'readRegistrationStatus',
  'rejectRegistration',
  'resetUserPassword',
  'restoreUser',
  'startRun',
  'streamDocumentVersionContent',
  'submitRegistration',
  'updateMyProfile',
  'updateUser',
  'uploadDocument',
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
 * This operation does not carry crops. `page_geometry_extraction` also publishes a page-crop manifest, but this pipeline renders no visual detection and that manifest is unconditionally empty (`crop_policy: "none"`, `crops: []`); it is a separate artifact and is not exposed on this operation at all, rather than being shipped here as a field that is always `[]`.
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
// issueToken - POST /auth/token
// ------------------------------------------------------------------------------------

/**
 * Exchange a login and a password for a bearer credential.
 *
 * The only operation on this surface that is reachable without a credential, because it is the one that hands one out: its `security` is the empty requirement, which overrides the document root for this operation and for no other.
 *
 * **What this operation says about the credential it returns: nothing.** The response carries an opaque string and how long it stays valid. Its structure, what it encodes, and where the deployment got it are the deployment's own, are not described anywhere in this document, and are never parsed by a caller -- the same rule that keeps `bearerFormat` off `components.securitySchemes.bearerAuth`. A deployment that replaces a static string with something else changes no operation here.
 *
 * Nothing is created and nothing is changed, so there is no idempotency key: a repeat of the same exchange is a second exchange, not a replay of the first.
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
// startRun - POST /runs
// ------------------------------------------------------------------------------------

/**
 * Start a text-consistency run over one published version.
 *
 * PD-03, in the subset PC-01 exercises. A new idempotency key creates a run. The same key with the same payload returns the existing run and creates nothing, whatever state that run is in, terminal included. The same key with a different payload returns `idempotency_key_reuse` and creates nothing. A new key over a terminal run creates a new run and leaves the terminal one exactly as it was: a terminal run is never reopened.
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
 * Upload one PDF and publish an immutable document version.
 *
 * The whole PC-01 ingest path. The accepted envelope is one unencrypted PDF, at most 25 MiB and at most 30 pages, every page carrying extractable embedded text. A scanned or image-only file, a password-protected file, a non-PDF, an oversize file, an over-page-count file and a companion or archive upload are each refused with `validation_failed` and a `constraint` detail. OCR is never silently substituted.
 *
 * On success the version and its input manifest are immutable: there is no update or delete endpoint for either, and the database refuses both.
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
} as const;
