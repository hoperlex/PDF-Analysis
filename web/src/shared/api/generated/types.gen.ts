/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * Every component schema of the PC-01 API as a TypeScript type.
 *
 * Produced by `npm --prefix web run api:generate`
 * (web/scripts/generate-api-client.mjs, generator 1.0.0)
 * from contracts/api/v1/openapi.json
 *   AuditManager PC-01 API 1.0.0-draft.1 (OpenAPI 3.1.0)
 *   sha256 17ece21beb295c0f0893c5f16956401b5a349e4ebfa5f7c9cd2c4260a08611e1
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

/** The `info.version` of the contract these types were generated from. */
export const CONTRACT_VERSION = '1.0.0-draft.1';

/** sha256 of the OpenAPI document these types were generated from. */
export const CONTRACT_DIGEST = '17ece21beb295c0f0893c5f16956401b5a349e4ebfa5f7c9cd2c4260a08611e1';

/** Every component schema name in the contract, sorted. */
export const SCHEMA_NAMES = [
  'AnalysisProfileId',
  'AppendDecisionRequest',
  'AppendDecisionResponse',
  'CorrelationId',
  'CreateProjectRequest',
  'Cursor',
  'DecisionEvent',
  'DecisionEventPage',
  'DecisionEventType',
  'DecisionId',
  'DocumentUid',
  'DocumentVersion',
  'ErrorCode',
  'ErrorEnvelope',
  'Evidence',
  'Finding',
  'FindingCategory',
  'FindingDetail',
  'FindingObservation',
  'FindingObservationId',
  'FindingPage',
  'FindingUid',
  'IdempotencyKey',
  'InputManifestEntry',
  'ModelCallId',
  'ObservationProvenance',
  'PageInfo',
  'Project',
  'ProjectPage',
  'ProjectUid',
  'PromptBundleId',
  'ProviderMode',
  'RunId',
  'RunState',
  'RunStatus',
  'Sha256',
  'StageId',
  'StageState',
  'StageStatus',
  'StartRunRequest',
  'UploadDocumentRequest',
  'Verdict',
  'VersionUid',
] as const;

export type AnalysisProfileId = string;

/** The contract pattern for `AnalysisProfileId`. Anchored; use with `new RegExp()`. */
export const ANALYSIS_PROFILE_ID_PATTERN = "^ap_[0-9A-HJKMNP-TV-Z]{26}$";

export type AppendDecisionRequest = {
  /** Required for `comment`; optional on any other event type. */
  comment?: string | null;
  event_type: DecisionEventType;
  /** The observation the expert actually reviewed. A verdict is recorded against the evidence in front of the reviewer, not against whatever the newest run later produced. */
  finding_observation_id: FindingObservationId;
};

export type AppendDecisionResponse = {
  current_verdict: Verdict;
  event: DecisionEvent;
};

/** Not an entity identity. Never a foreign key and authorizes nothing. */
export type CorrelationId = string;

/** The contract pattern for `CorrelationId`. Anchored; use with `new RegExp()`. */
export const CORRELATION_ID_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$";

export type CreateProjectRequest = {
  /** Display label. Not unique and not an identity. */
  name: string;
};

/** Opaque pagination token. It encodes the sort key of the last item on the page and nothing else; it is never a database row number or sequence value. */
export type Cursor = string;

/** One appended event. Never updated and never removed. */
export type DecisionEvent = {
  /** OD-12: one configured local reviewer label, persisted server-side. It is a label, not a subject identity, and it authorizes nothing. */
  author_label: string;
  comment?: string | null;
  decision_id: DecisionId;
  event_type: DecisionEventType;
  finding_observation_id: FindingObservationId;
  finding_uid: FindingUid;
  recorded_at: string;
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

export type DocumentUid = string;

/** The contract pattern for `DocumentUid`. Anchored; use with `new RegExp()`. */
export const DOCUMENT_UID_PATTERN = "^doc_[0-9A-HJKMNP-TV-Z]{26}$";

/** A published, immutable input state. There is no endpoint that modifies one. */
export type DocumentVersion = {
  byte_size: number;
  display_title?: string;
  document_uid: DocumentUid;
  input_manifest: Array<InputManifestEntry>;
  media_type: "application/pdf";
  page_count: number;
  project_uid: ProjectUid;
  published_at: string;
  sha256: Sha256;
  /** The uploaded file name, for display. Never an identity. */
  source_filename?: string | null;
  /** Display and ordering value only. Never an identity and never accepted as a path parameter. */
  version_ordinal: number;
  version_uid: VersionUid;
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
  'required_norm_unavailable',
  'analysis_input_invalid',
  'analysis_failed',
  'partial_result_not_publishable',
  'cost_budget_exceeded',
  'stale_attempt',
  'execution_token_invalid',
  'internal_error',
] as const;

/** ErrorCode - the closed value set above. */
export type ErrorCode = (typeof ERROR_CODE_VALUES)[number];

/** The single externally visible failure shape, mirroring urn:auditmanager:domain:error-envelope:v1. `retryable` is pinned to the catalog value for the reported code; a caller never infers it from the HTTP status or the message. */
export type ErrorEnvelope = {
  contract_version: "1.0.0-draft.1";
  correlation_id: CorrelationId;
  /** Safe scalar classifiers only, restricted to the safe_detail_keys the catalog declares for the reported code. The catalog's forbidden key set is rejected. */
  details?: {
    [key: string]: string | number | boolean | null;
  };
  error_code: ErrorCode;
  /** Stable caller-safe sentence. No path, object key, URL, credential, token, prompt, payload, query or stack content. */
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

/** A published finding. Every listed finding is grounded: its quotations were verified present at their declared anchors. */
export type Finding = {
  category: FindingCategory;
  current_verdict: Verdict;
  decision_recorded_at?: string | null;
  finding_uid: FindingUid;
  latest_decision_id?: DecisionId | null;
  observation: FindingObservation;
  project_uid: ProjectUid;
  run_id: RunId;
  version_uid: VersionUid;
};

/** The only two questions PC-01 answers. */
export const FINDING_CATEGORY_VALUES = [
  'internal_contradiction',
  'explicit_placeholder',
] as const;

/** FindingCategory - the closed value set above. */
export type FindingCategory = (typeof FINDING_CATEGORY_VALUES)[number];

/** One finding with its full current-verdict projection. Restates `Finding` rather than composing it with `allOf`: under JSON Schema 2020-12 an `additionalProperties: false` is evaluated against its own schema object's property annotations only, so an `allOf` branch over the closed `Finding` would reject the two properties the sibling branch adds. Both shapes stay closed, and tests/contract/api_v1 asserts this property set stays `Finding`'s plus exactly `latest_comment` and `decision_event_count`. */
export type FindingDetail = {
  category: FindingCategory;
  current_verdict: Verdict;
  decision_event_count?: number;
  decision_recorded_at?: string | null;
  finding_uid: FindingUid;
  /** The comment of the most recent event carrying one, whatever its type. */
  latest_comment?: string | null;
  latest_decision_id?: DecisionId | null;
  observation: FindingObservation;
  project_uid: ProjectUid;
  run_id: RunId;
  version_uid: VersionUid;
};

export type FindingObservation = {
  category: FindingCategory;
  evidence: Array<Evidence>;
  finding_observation_id: FindingObservationId;
  finding_text: string;
  provenance: ObservationProvenance;
  recommendation_text: string;
  run_id: RunId;
};

/** Immutable evidence emitted by exactly one run. */
export type FindingObservationId = string;

/** The contract pattern for `FindingObservationId`. Anchored; use with `new RegExp()`. */
export const FINDING_OBSERVATION_ID_PATTERN = "^fobs_[0-9A-HJKMNP-TV-Z]{26}$";

export type FindingPage = {
  items: Array<Finding>;
  page: PageInfo;
};

/** Durable semantic issue identity, carrying expert history across reruns. */
export type FindingUid = string;

/** The contract pattern for `FindingUid`. Anchored; use with `new RegExp()`. */
export const FINDING_UID_PATTERN = "^fnd_[0-9A-HJKMNP-TV-Z]{26}$";

/** Not an entity identity. Never interpreted as, converted into or stored as a system identifier. */
export type IdempotencyKey = string;

/** The contract pattern for `IdempotencyKey`. Anchored; use with `new RegExp()`. */
export const IDEMPOTENCY_KEY_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$";

/** One role of the immutable input manifest. It carries a blob_id and a checksum and never an object key, bucket or URL. */
export type InputManifestEntry = {
  media_type: string;
  role: string;
  sha256: Sha256;
  size_bytes: number;
};

export type ModelCallId = string;

/** The contract pattern for `ModelCallId`. Anchored; use with `new RegExp()`. */
export const MODEL_CALL_ID_PATTERN = "^mc_[0-9A-HJKMNP-TV-Z]{26}$";

/** What produced this observation. Checksums and identities only: never the prompt, the request or the response body. */
export type ObservationProvenance = {
  analysis_profile_id: AnalysisProfileId;
  model_call_id?: ModelCallId | null;
  model_identity?: string | null;
  prompt_bundle_id: PromptBundleId;
  provider_mode: ProviderMode;
  stage_id: StageId;
};

export type PageInfo = {
  /** Token for the next page, or null when this is the last page. */
  next_cursor: Cursor | null;
};

export type Project = {
  created_at: string;
  document_count?: number;
  name: string;
  project_uid: ProjectUid;
};

export type ProjectPage = {
  items: Array<Project>;
  page: PageInfo;
};

/** Opaque project identity. */
export type ProjectUid = string;

/** The contract pattern for `ProjectUid`. Anchored; use with `new RegExp()`. */
export const PROJECT_UID_PATTERN = "^prj_[0-9A-HJKMNP-TV-Z]{26}$";

export type PromptBundleId = string;

/** The contract pattern for `PromptBundleId`. Anchored; use with `new RegExp()`. */
export const PROMPT_BUNDLE_ID_PATTERN = "^pb_[0-9A-HJKMNP-TV-Z]{26}$";

/** Whether the model call was made live or replayed from a recording. Visible in the UI and in the CSV, because a recorded run is not evidence of a live one. */
export const PROVIDER_MODE_VALUES = [
  'live',
  'recorded',
] as const;

/** ProviderMode - the closed value set above. */
export type ProviderMode = (typeof PROVIDER_MODE_VALUES)[number];

export type RunId = string;

/** The contract pattern for `RunId`. Anchored; use with `new RegExp()`. */
export const RUN_ID_PATTERN = "^run_[0-9A-HJKMNP-TV-Z]{26}$";

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

export type RunStatus = {
  analysis_profile_id?: AnalysisProfileId;
  created_at: string;
  /** The explicitly recorded missing or degraded stage set. Non-empty exactly when the run is `partial`; a `published` run carries none. */
  degradation_set?: Array<StageId>;
  /** Ungrounded model items rejected by the grounding gate. They are not findings and appear in no finding list. */
  diagnostic_observation_count?: number;
  /** OD-10: a run left `running` by a crash is reconciled to `failed` with an explicit interrupted reason. There is no `interrupted` state. */
  interrupted_reason?: string | null;
  project_uid: ProjectUid;
  prompt_bundle_id?: PromptBundleId;
  provider_mode: ProviderMode;
  published_finding_count?: number;
  run_id: RunId;
  stages: Array<StageState>;
  state: RunState;
  terminal_at?: string | null;
  /** The catalog code a `failed` run terminated with. Null otherwise. */
  terminal_reason?: ErrorCode | null;
  version_uid: VersionUid;
};

/** A verification value, never an identity. */
export type Sha256 = string;

/** The contract pattern for `Sha256`. Anchored; use with `new RegExp()`. */
export const SHA256_PATTERN = "^[0-9a-f]{64}$";

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

export type StartRunRequest = {
  /** Defaults to the server's configured mode. A client asking for `live` is asking to spend money against the OD-03 ceiling. */
  provider_mode?: ProviderMode;
  version_uid: VersionUid;
};

export type UploadDocumentRequest = {
  /** Optional display label. When absent the server derives one for presentation. Neither this nor the uploaded file name is ever an identity. */
  display_title?: string;
  /** One unencrypted PDF, at most 25 MiB and at most 30 pages, every page carrying extractable embedded text. */
  file: Blob;
};

/** The current projected verdict. `pending` when the ledger holds no verdict-bearing event, and after a revocation. `needs_manual_review` is declared for the closed union and has no PC-01 producer. */
export const VERDICT_VALUES = [
  'pending',
  'accepted',
  'rejected',
  'needs_manual_review',
] as const;

/** Verdict - the closed value set above. */
export type Verdict = (typeof VERDICT_VALUES)[number];

export type VersionUid = string;

/** The contract pattern for `VersionUid`. Anchored; use with `new RegExp()`. */
export const VERSION_UID_PATTERN = "^ver_[0-9A-HJKMNP-TV-Z]{26}$";
