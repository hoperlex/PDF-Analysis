/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * Every component schema of the PC-01 API as a TypeScript type.
 *
 * Produced by `npm --prefix web run api:generate`
 * (web/scripts/generate-api-client.mjs, generator 1.0.0)
 * from contracts/api/v1/openapi.json
 *   AuditManager PC-01 API 1.0.0-draft.1 (OpenAPI 3.1.0)
 *   sha256 f6192e9cb641c10bdfdfa9f05d4e7f67bfe50299cd8c0e9d73b6f4272b0f4bad
 *
 * Hand-editing this file makes the contract drift guard in web/tests/contract go
 * red. The contract belongs to session A1: change it there, then regenerate.
 */

/** The `info.version` of the contract these types were generated from. */
export const CONTRACT_VERSION = '1.0.0-draft.1';

/** sha256 of the OpenAPI document these types were generated from. */
export const CONTRACT_DIGEST = 'f6192e9cb641c10bdfdfa9f05d4e7f67bfe50299cd8c0e9d73b6f4272b0f4bad';

/** Every component schema name in the contract, sorted. */
export const SCHEMA_NAMES = [
  'Account',
  'AccountPage',
  'AnalysisProfileId',
  'AnalysisProfileList',
  'AnalysisProfileListItem',
  'AnalysisProfileSource',
  'AnalysisProfileSourceFile',
  'AnalysisProfileStatus',
  'AnalysisProfileSummary',
  'AppendDecisionRequest',
  'AppendDecisionResponse',
  'ApproveRegistrationRequest',
  'Assignment',
  'AssignmentDetail',
  'AssignmentEvent',
  'AssignmentEventKind',
  'AssignmentPage',
  'AssignmentStatus',
  'AssignmentTransitionKind',
  'AssignmentUid',
  'BlockGeometry',
  'CarryOverDecisionRequest',
  'CarryOverDecisionResponse',
  'CarryoverCandidate',
  'CarryoverSourceDecision',
  'ChangePasswordRequest',
  'ClassifyDocumentVersionRequest',
  'ComparedVersion',
  'ComparisonRefusal',
  'CorrelationId',
  'CostBasis',
  'CreateAssignmentRequest',
  'CreateProjectRequest',
  'Cursor',
  'DashboardSummary',
  'DecisionEvent',
  'DecisionEventPage',
  'DecisionEventType',
  'DecisionId',
  'DecisionRecord',
  'DecisionRecordPage',
  'DiffHunk',
  'DocumentUid',
  'DocumentVersion',
  'DocumentVersionPage',
  'EffectiveVendorLists',
  'ErrorCode',
  'ErrorEnvelope',
  'Evidence',
  'ExecutionDispatchStatus',
  'ExecutionJournalEntry',
  'ExecutionJournalPage',
  'ExecutionQueueItem',
  'ExecutionQueuePage',
  'ExecutionWorker',
  'ExecutionWorkerPage',
  'Finding',
  'FindingCategory',
  'FindingComparison',
  'FindingDetail',
  'FindingMatchProposal',
  'FindingObservation',
  'FindingObservationId',
  'FindingPage',
  'FindingRef',
  'FindingUid',
  'IdempotencyKey',
  'InputManifestEntry',
  'IssueTokenRequest',
  'IssueTokenResponse',
  'JobId',
  'MarkReleaseNotesReadRequest',
  'ModelCallId',
  'NormBuildState',
  'NormCatalogueEntry',
  'NormCatalogueEntryPage',
  'NormCitation',
  'NormCitationState',
  'NormCurrentSnapshot',
  'NormDocument',
  'NormDocumentId',
  'NormFindingVerification',
  'NormFragment',
  'NormHighlight',
  'NormKindCount',
  'NormObservationCitationPartition',
  'NormParagraph',
  'NormParagraphId',
  'NormParagraphKind',
  'NormParagraphPage',
  'NormRetrievalSetId',
  'NormSearchHit',
  'NormSearchPage',
  'NormSnapshot',
  'NormSnapshotEvent',
  'NormSnapshotEventPage',
  'NormSnapshotPage',
  'NormSourceAttribution',
  'NormTextReliability',
  'NormVerificationReport',
  'NormsSnapshotId',
  'ObservationProvenance',
  'PageInfo',
  'PersonNames',
  'PortalBlock',
  'PortalBlockId',
  'PortalBlockPage',
  'PortalBlockType',
  'PortalCrop',
  'PortalGeometryState',
  'PortalRecognisedText',
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
  'ProviderMode',
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
  'ResetUserPasswordRequest',
  'Role',
  'RunActivity',
  'RunActivitySpend',
  'RunId',
  'RunState',
  'RunStateCount',
  'RunStatus',
  'RunStatusPage',
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
  'SetExecutionPausedRequest',
  'SetGlobalVendorListRequest',
  'SetJobPriorityRequest',
  'SetProjectVendorListRequest',
  'SetWorkerIntakeRequest',
  'Severity',
  'Sha256',
  'SheetDiff',
  'SheetDiffPage',
  'SheetPairing',
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
  'StageId',
  'StageState',
  'StageStatus',
  'StartRunRequest',
  'SubmitRegistrationRequest',
  'TransitionAssignmentRequest',
  'UngroundedReason',
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
  'VersionComparison',
  'VersionUid',
  'WorkerId',
  'WorkerState',
] as const;

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
 * ``builtin``: AR's v1 profile, written in this repository. ``draft``: a package ported from
 * the legacy prompts and not yet reviewed by an expert. ``reviewed``: a package an expert has
 * reviewed. Every status is executable; the status is recorded, never hidden.
 */
export const ANALYSIS_PROFILE_STATUS_VALUES = [
  'builtin',
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

export type ApproveRegistrationRequest = {
  /** The roles the new account receives: at least one. */
  roles: Array<Role>;
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

export type AssignmentPage = {
  items: Array<Assignment>;
  page: PageInfo;
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

/** Why two versions are not compared; ``side`` when the reason is one side's. */
export type ComparisonRefusal = {
  reason: "same_version" | "version_not_found" | "different_set" | "foreign_project" | "version_not_published" | "version_order_invalid" | "stage_unclassified" | "section_unconfirmed" | "project_stage_mismatch" | "confirmed_section_mismatch" | "stage_pair_invalid" | "analysis_missing" | "run_not_of_version" | "run_not_published" | "text_unavailable" | "text_too_large";
  side: "source" | "target" | null;
};

/** Not an entity identity. Never a foreign key and authorizes nothing. */
export type CorrelationId = string;

/** The contract pattern for `CorrelationId`. Anchored; use with `new RegExp()`. */
export const CORRELATION_ID_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$";

/** How well a published cost figure is known. `measured` means every provider call the figure sums reported its own cost; `estimated` means at least one did not, so the total is derived. The value is an aggregate over **every** call the figure spans and is never the last call's basis: a run whose first attempt replayed and whose second reported a cost is `estimated`. */
export const COST_BASIS_VALUES = [
  'measured',
  'estimated',
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

export type CreateProjectRequest = {
  /** Display label. Not unique and not an identity. */
  name: string;
};

/** Opaque pagination token. It encodes the sort key of the last item on the page and nothing else; it is never a database row number or sequence value. */
export type Cursor = string;

/** `getDashboardSummary`'s whole answer. All four panels, one read, no filter. */
export type DashboardSummary = {
  documents_by_project: Array<ProjectDocumentCount>;
  findings_by_verdict: Array<VerdictCount>;
  run_activity: RunActivity;
  section_breakdown: Array<SectionDocumentCount>;
};

/** One appended event. Never updated and never removed. */
export type DecisionEvent = {
  /** OD-12, as `R-37` now defines it: the display name of the reviewer who recorded the event -- the name they chose, or their login when they have chosen none -- derived server-side from the authenticated credential and **never** taken from a request body. It IS a subject identity: it names which reviewer judged, which is what `P04` needs and what one configured label for every reviewer could not give it. It still authorizes nothing: it is what the ledger records about who judged, not a permission anybody holds, and no client can choose it. The ledger is append-only, so an event keeps the label it was written with even after that reviewer is renamed. */
  author_label: string;
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

/** One event of the decision journal, with the finding context it was recorded against. A rebuildable projection and never a source of truth: every property here is derived from `expert_decision_event`, `finding`, `finding_observation` and the `finding_current_verdict` projection, and nothing is stored in this shape. It restates `DecisionEvent`'s properties rather than composing them with `allOf`, for the reason `FindingDetail` states: under JSON Schema 2020-12 an `additionalProperties: false` is evaluated against its own schema object's property annotations only, so an `allOf` branch over the closed `DecisionEvent` would reject the properties the sibling branch adds. */
export type DecisionRecord = {
  /** OD-12, as `R-37` now defines it: the display name of the reviewer who recorded the event -- the name they chose, or their login when they have chosen none -- derived server-side from the authenticated credential and **never** taken from a request body. It IS a subject identity: it names which reviewer judged, which is what `P04` needs and what one configured label for every reviewer could not give it. It still authorizes nothing: it is what the ledger records about who judged, not a permission anybody holds, and no client can choose it. The ledger is append-only, so an event keeps the label it was written with even after that reviewer is renamed. */
  author_label: string;
  category: FindingCategory;
  comment?: string | null;
  current_verdict: Verdict;
  /** How many events the ledger holds for this finding, including this one. A count greater than one means the expert returned to the finding. */
  decision_event_count: number;
  decision_id: DecisionId;
  event_type: DecisionEventType;
  finding_observation_id: FindingObservationId;
  /** The observation's own words, as `FindingObservation.finding_text` carries them. It is the analysis's text and not this API's prose, so it is in whatever language the analysis produced. */
  finding_text: string;
  finding_uid: FindingUid;
  project_uid: ProjectUid;
  recorded_at: string;
  run_id: RunId;
  severity?: Severity;
  /** The verdict this event carries, or null for a comment. */
  verdict?: Verdict | null;
};

export type DecisionRecordPage = {
  items: Array<DecisionRecord>;
  page: PageInfo;
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

export type DocumentUid = string;

/** The contract pattern for `DocumentUid`. Anchored; use with `new RegExp()`. */
export const DOCUMENT_UID_PATTERN = "^doc_[0-9A-HJKMNP-TV-Z]{26}$";

/** A published, immutable input state. There is no endpoint that modifies one. */
export type DocumentVersion = {
  byte_size: number;
  /** `W59-SECTION-SEAL-01`. The version's persisted, expert-confirmed project stage and section; absent while no expert has classified this version. Never inherited from another version, the document's `section`, a file name or a suggestion. */
  classification?: VersionClassification;
  display_title?: string;
  document_uid: DocumentUid;
  input_manifest: Array<InputManifestEntry>;
  media_type: "application/pdf";
  page_count: number;
  project_uid: ProjectUid;
  published_at: string;
  /** One of the fifteen project sections, or absent when the document has not been classified. */
  section?: ProjectSection;
  sha256: Sha256;
  /** The uploaded file name, for display. Never an identity. */
  source_filename?: string | null;
  /** Display and ordering value only. Never an identity and never accepted as a path parameter. */
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

export type ExecutionQueueItem = {
  available_at: string;
  created_at: string;
  job_id: JobId;
  priority: number;
  run_id: RunId;
  state: string;
};

export type ExecutionQueuePage = {
  items: Array<ExecutionQueueItem>;
  page: PageInfo;
  paused: boolean;
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

/** A published finding. Every listed finding is grounded: its quotations were verified present at their declared anchors. */
export type Finding = {
  category: FindingCategory;
  current_verdict: Verdict;
  decided_severity?: Severity;
  decision_recorded_at?: string | null;
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

/** One finding with its full current-verdict projection. Restates `Finding` rather than composing it with `allOf`: under JSON Schema 2020-12 an `additionalProperties: false` is evaluated against its own schema object's property annotations only, so an `allOf` branch over the closed `Finding` would reject the two properties the sibling branch adds. Both shapes stay closed, and tests/contract/api_v1 asserts this property set stays `Finding`'s plus exactly `latest_comment` and `decision_event_count`. */
export type FindingDetail = {
  category: FindingCategory;
  current_verdict: Verdict;
  decided_severity?: Severity;
  decision_event_count?: number;
  decision_recorded_at?: string | null;
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

export type JobId = string;

/** The contract pattern for `JobId`. Anchored; use with `new RegExp()`. */
export const JOB_ID_PATTERN = "^job_[0-9A-HJKMNP-TV-Z]{26}$";

/** The known release version through which this account has read. Unknown or future versions are refused. */
export type MarkReleaseNotesReadRequest = {
  read_through: string;
};

export type ModelCallId = string;

/** The contract pattern for `ModelCallId`. Anchored; use with `new RegExp()`. */
export const MODEL_CALL_ID_PATTERN = "^mc_[0-9A-HJKMNP-TV-Z]{26}$";

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

/** Citation partitions of one published finding; canonical and member observations are proved separately. */
export type NormFindingVerification = {
  canonical: NormObservationCitationPartition;
  finding_uid: FindingUid;
  merged_observations: Array<NormObservationCitationPartition>;
};

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

/** One canonical or merged observation with its independently certified citation partition. A zero partition is explicit, never inferred from an empty SQL result. */
export type NormObservationCitationPartition = {
  finding_observation_id: FindingObservationId;
  /** A certified v3 citation partition. An empty array means the CITE gate completed and persisted a checked count of zero; absence on v1/v2 means no certification, never zero. */
  norm_citations: Array<NormCitation>;
  required_value?: string;
  stated_value?: string;
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

/** Read-time report for a v3 run only. A v1/v2 run is not found. A partial v3 run still reports its typed stage error; no unverified or uncertified partition is exposed. textless_pages is context only and never citation evidence. */
export type NormVerificationReport = {
  error_code?: ErrorCode;
  findings: Array<NormFindingVerification>;
  norm_retrieval_set_id: NormRetrievalSetId;
  norms_snapshot_id: NormsSnapshotId;
  run_id: RunId;
  status: "complete" | "partial";
  textless_pages: Array<number>;
  withheld_by_reason: {
    [key: string]: number;
  };
};

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

export type PageInfo = {
  /** Token for the next page, or null when this is the last page. */
  next_cursor: Cursor | null;
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

/** The running product version from VERSION, its content-derived build identifier, and the unchanged API contract version. */
export type ProductVersion = {
  build_id: string;
  contract_version: string;
  product_version: string;
};

export type Project = {
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

/** Whether the model call was made live or replayed from a recording. Visible in the UI and in the CSV, because a recorded run is not evidence of a live one. */
export const PROVIDER_MODE_VALUES = [
  'live',
  'recorded',
] as const;

/** ProviderMode - the closed value set above. */
export type ProviderMode = (typeof PROVIDER_MODE_VALUES)[number];

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

export type ResetUserPasswordRequest = {
  /** The password the account signs in with next and must then change. It is held to the deployment's password policy against the account's login, and it appears in no response body, no error detail and no diagnostic record. */
  temporary_password: string;
};

/** One role an account may hold; an account holds a set of them (R-55, R-60). `expert` makes product changes -- projects, uploads, runs, verdicts, comments and the export. `admin` manages accounts and registration requests. Reading product data needs one of them (R-80): an active account whose role set is empty is suspended and reads only its own account, the product version and the release notes. */
export const ROLE_VALUES = [
  'expert',
  'admin',
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

/** How many runs, across every project, currently sit in one state. Every member of `RunState` is present, for the same reason `VerdictCount` states. */
export type RunStateCount = {
  count: number;
  state: RunState;
};

export type RunStatus = {
  analysis_profile_id?: AnalysisProfileId;
  cost_basis?: CostBasis;
  /** What this run spent at the provider, in millionths of the provider currency unit, as an integer. Never a floating-point money value. It is the sum of `cost_micros` over **every** `model_call` row of this run, including every retry attempt, because the per-run budget ceiling is enforced over the same span. Absent when the run made no provider call at all, which is a different fact from a cost of zero. */
  cost_micros?: number;
  created_at: string;
  /** The explicitly recorded missing or degraded stage set. Non-empty exactly when the run is `partial`; a `published` run carries none. */
  degradation_set?: Array<StageId>;
  /** Ungrounded model items rejected by the grounding gate. They are not findings and appear in no finding list. */
  diagnostic_observation_count?: number;
  /** OD-10: a run left `running` by a crash is reconciled to `failed` with an explicit interrupted reason. There is no `interrupted` state. */
  interrupted_reason?: string | null;
  /** How many provider calls `cost_micros` sums. Published rather than left to be inferred: a reader who cannot see it cannot tell a run answered first time from one that was retried, and the two spent differently. Present exactly when `cost_micros` is. */
  model_call_count?: number;
  /** The verified retrieval set frozen for this v3 run; absent for v1/v2. It must belong to norms_snapshot_id. */
  norm_retrieval_set_id?: NormRetrievalSetId;
  /** W55A-SEAL-01 (R-113, CD-6): the norms snapshot this run pinned when it was created -- the current snapshot at that moment. Absent while no snapshot is current, which until W57 is the expected state of every run. */
  norms_snapshot_id?: NormsSnapshotId;
  project_uid: ProjectUid;
  prompt_bundle_id?: PromptBundleId;
  provider_mode: ProviderMode;
  published_finding_count?: number;
  reaudit_of_run_id?: RunId;
  run_id: RunId;
  stages: Array<StageState>;
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
};

export type RunStatusPage = {
  items: Array<RunStatus>;
  page: PageInfo;
};

/** How many published documents carry one project section (`R-40`, `D-56`). `section` absent means this row is the unclassified bucket, not a sixteenth section. Every one of the fifteen current codes is present even at `document_count: 0`. */
export type SectionDocumentCount = {
  document_count: number;
  /** One of the fifteen project sections, or absent when the document has not been classified. */
  section?: ProjectSection;
};

/** All fifteen choices for one version, the current classification or ``null``. */
export type SectionReview = {
  classification: VersionClassification | null;
  options: Array<SectionReviewOption>;
  recognised_text_consulted: boolean;
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
  match_algorithm: "price-match-v1";
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

export type SetExecutionPausedRequest = {
  paused: boolean;
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
  algorithm: "price-match-v1";
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
 * The priced specification of a set's current AR version, or the state that stops it.
 *
 * The states are checked in order -- ``version_unclassified``, ``section_not_ar``,
 * ``price_list_missing``, ``analysis_missing``, ``text_unavailable``,
 * ``specification_too_large`` -- and each answer carries the facts read before it stopped.
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

/** `W61-DISPATCHER-01`. One move along an assignment's history. */
export type TransitionAssignmentRequest = {
  kind: AssignmentTransitionKind;
  new_assignee_user_uid?: UserUid;
  reason?: string;
};

/** Closed deterministic observation-withholding reasons; a withheld item is never a published finding. */
export const UNGROUNDED_REASON_VALUES = [
  'quotation_absent',
  'quotation_on_different_page',
  'span_outside_page',
  'span_outside_block',
  'span_length_mismatch',
  'quote_in_recognised_text',
  'norm_label_unknown',
  'norm_quote_too_short',
  'norm_quote_ambiguous',
  'norm_quote_absent',
  'norm_value_not_in_quote',
  'stated_value_not_in_evidence',
] as const;

/** UngroundedReason - the closed value set above. */
export type UngroundedReason = (typeof UNGROUNDED_REASON_VALUES)[number];

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
  /** One portal bundle: a ZIP holding the PDF, its portal block list and its recognised-text markdown, and optionally the portal HTML and the stamp audit. At most 250 MiB; the PDF at most 500 pages. */
  file: Blob;
  /** One of the fifteen project sections, or absent when the document has not been classified. */
  section?: ProjectSection;
};

/** The next version of an existing document: one portal bundle and nothing else. There is no title and no section, because a further version takes neither; an undeclared part is refused like any other. */
export type UploadDocumentVersionRequest = {
  /** One portal bundle: a ZIP holding the PDF, its portal block list and its recognised-text markdown, and optionally the portal HTML and the stamp audit. At most 250 MiB; the PDF at most 500 pages. */
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

/** How many findings, across every project, currently stand at one verdict. Every member of `Verdict` is present -- a verdict nobody has recorded is `count: 0`, not an absent row. */
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
 * Written once (``0024_version_classification``); an exact repeat keeps the first
 * confirmer and a different stage or section is refused, not overwritten.
 */
export type VersionClassification = {
  confirmed_at: string;
  confirmed_by_user_uid: UserUid;
  project_stage: ProjectStage;
  section_code: ProjectSection;
  version_uid: VersionUid;
};

/** Two versions of one set compared, or the explicit reason they are not. */
export type VersionComparison = {
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

export type VersionUid = string;

/** The contract pattern for `VersionUid`. Anchored; use with `new RegExp()`. */
export const VERSION_UID_PATTERN = "^ver_[0-9A-HJKMNP-TV-Z]{26}$";

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
