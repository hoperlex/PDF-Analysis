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
 *   sha256 013e22ae46ee528d7a4b5fd2b9f24a22d3cb8754152a28e41977d93029f9ef9d
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

import type {
  AppendDecisionRequest,
  AppendDecisionResponse,
  ChangePasswordRequest,
  CorrelationId,
  CreateProjectRequest,
  Cursor,
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
  RunId,
  RunStatus,
  RunStatusPage,
  StartRunRequest,
  UploadDocumentRequest,
  Verdict,
  VersionUid,
} from './types.gen';

/** Every operationId in the contract, sorted. */
export const OPERATION_IDS = [
  'appendDecision',
  'changePassword',
  'createProject',
  'exportRunCsv',
  'getDocumentVersion',
  'getFinding',
  'getRunStatus',
  'issueToken',
  'listDecisionHistory',
  'listDecisions',
  'listDocuments',
  'listProjects',
  'listRunFindings',
  'listRuns',
  'listVersions',
  'startRun',
  'streamDocumentVersionContent',
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
 * The `403` is declared because every operation behind the seam declares it: `permission_denied` means an authenticated subject was refused, a generated client needs a typed shape for it on every authorized operation, and an operation that omitted it would be claiming a property about a role model this document does not describe. This surface raises it nowhere, here included.
 *
 * Nothing is created, so there is no idempotency key. A repeat of the same request is refused by its own `current_password`, which is no longer current -- it is not replayed and there is no `409` here.
 *
 * Revocation has no operation of its own on this surface. Ending a pilot -- taking credentials away from accounts whose passwords nobody is changing -- is an operator's action taken on the deployment, and publishing it would require deciding who may revoke whom, which is the role vocabulary this document deliberately does not have.
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
